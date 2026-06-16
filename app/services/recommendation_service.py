"""Job recommendation engine using vector similarity + skill analysis."""

from typing import Any

from loguru import logger

from app.services.db_service import DatabaseService, get_db_session
from app.services.search_service import SearchService


class RecommendationService:
    def __init__(
        self,
        search_service: SearchService,
        db_service: DatabaseService | None = None,
    ):
        self.search_service = search_service
        self.db_service = db_service

    async def recommend_jobs_for_resume(
        self, resume_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        resume = self._get_record("resumes", resume_id)
        if not resume:
            logger.warning(f"Resume {resume_id} not found")
            return []

        query_text = resume.get("raw_text") or self._extract_text_from_json(
            resume.get("content_json")
        )
        if not query_text:
            logger.warning(f"Resume {resume_id} has no text content")
            return []

        results = await self.search_service.search_jobs(query_text, n_results=limit)
        return self._enrich_with_db_data(results, "jobs", "job_id")

    async def recommend_resumes_for_job(self, job_id: int, limit: int = 10) -> list[dict[str, Any]]:
        job = self._get_record("job_postings", job_id)
        if not job:
            logger.warning(f"Job {job_id} not found")
            return []

        query_text = job.get("raw_text") or self._extract_text_from_json(job.get("content_json"))
        if not query_text:
            logger.warning(f"Job {job_id} has no text content")
            return []

        results = await self.search_service.search_resumes(query_text, n_results=limit)
        return self._enrich_with_db_data(results, "resumes", "resume_id")

    def get_skill_gap_analysis(self, resume_id: int, job_id: int) -> dict[str, Any]:
        resume = self._get_record("resumes", resume_id)
        job = self._get_record("job_postings", job_id)

        if not resume or not job:
            return {
                "error": "Resume or job not found",
                "matches": [],
                "gaps": [],
                "extra_skills": [],
            }

        resume_skills = self._extract_skills(resume.get("content_json"))
        job_skills = self._extract_skills(job.get("content_json"))

        resume_set = {s.lower() for s in resume_skills}
        job_set = {s.lower() for s in job_skills}

        matched = sorted(resume_set & job_set)
        gaps = sorted(job_set - resume_set)
        extras = sorted(resume_set - job_set)

        coverage = len(matched) / len(job_set) * 100 if job_set else 0

        return {
            "resume_id": resume_id,
            "job_id": job_id,
            "matches": matched,
            "gaps": gaps,
            "extra_skills": extras,
            "coverage_pct": round(coverage, 1),
            "total_resume_skills": len(resume_set),
            "total_job_skills": len(job_set),
        }

    def get_career_suggestions(self, resume_id: int) -> dict[str, Any]:
        resume = self._get_record("resumes", resume_id)
        if not resume:
            return {
                "error": "Resume not found",
                "current_skills": [],
                "suggested_skills": [],
                "trending_skills": [],
            }

        resume_skills = {s.lower() for s in self._extract_skills(resume.get("content_json"))}
        trending = self._get_trending_skills()

        trending_set = {s.lower() for s in trending}
        missing_trending = sorted(trending_set - resume_skills)

        related = self._find_related_skills(resume_skills, trending)

        return {
            "resume_id": resume_id,
            "current_skills": sorted(resume_skills),
            "trending_skills": sorted(trending_set),
            "suggested_skills": missing_trending[:20],
            "related_suggestions": related[:10],
        }

    def _get_record(self, table: str, record_id: int) -> dict[str, Any] | None:
        if not self.db_service:
            return None
        try:
            records = self.db_service.query_records(
                table, limit=1, filter_conditions={"id": record_id}
            )
            return records[0] if records else None
        except Exception as e:
            logger.error(f"Error fetching {table} {record_id}: {e}")
            return None

    def _extract_text_from_json(self, content_json: Any) -> str:
        if not content_json or not isinstance(content_json, dict):
            return ""
        parts = []
        for key in ("summary", "objective", "description", "about"):
            if key in content_json and isinstance(content_json[key], str):
                parts.append(content_json[key])
        for key in ("skills", "technologies", "tools"):
            if key in content_json:
                val = content_json[key]
                if isinstance(val, list):
                    parts.extend(str(v) for v in val)
                elif isinstance(val, str):
                    parts.append(val)
        for key in ("experience", "work_experience", "positions"):
            if key in content_json and isinstance(content_json[key], list):
                for exp in content_json[key]:
                    if isinstance(exp, dict):
                        parts.append(exp.get("title", ""))
                        parts.append(exp.get("description", ""))
                        parts.append(exp.get("company", ""))
        return " ".join(filter(None, parts))

    def _extract_skills(self, content_json: Any) -> list[str]:
        if not content_json or not isinstance(content_json, dict):
            return []
        skills: list[str] = []
        for key in ("skills", "technologies", "tools", "languages", "frameworks"):
            if key in content_json:
                val = content_json[key]
                if isinstance(val, list):
                    skills.extend(str(v) for v in val)
                elif isinstance(val, str):
                    skills.extend(s.strip() for s in val.split(",") if s.strip())
        if not skills and "technical_skills" in content_json:
            val = content_json["technical_skills"]
            if isinstance(val, list):
                skills.extend(str(v) for v in val)
            elif isinstance(val, str):
                skills.extend(s.strip() for s in val.split(",") if s.strip())
        return skills

    def _enrich_with_db_data(
        self, results: list[dict], db_table: str, id_key: str
    ) -> list[dict[str, Any]]:
        if not self.db_service:
            return results

        # Collect record IDs first to avoid N+1 DB queries.
        id_to_item: dict[int, list[dict]] = {}
        for item in results:
            meta = item.get("metadata", {})
            record_id = meta.get(id_key) or meta.get("id")
            if record_id:
                try:
                    record_id_int = int(str(record_id).split("_")[-1])
                    id_to_item.setdefault(record_id_int, []).append(item)
                except (ValueError, Exception):
                    pass

        if id_to_item:
            records = self.db_service.query_records_by_ids(db_table, list(id_to_item.keys()))
            for record in records:
                record_id = record.get("id")
                if record_id is not None:
                    for item in id_to_item.get(int(record_id), []):
                        item["db_record"] = record

        enriched = []
        for item in results:
            score = item.get("score")
            distance = item.get("distance")
            if score is None and distance is not None:
                item["score"] = round(1.0 - distance, 4)
            enriched.append(item)
        return enriched

    def _get_trending_skills(self) -> list[str]:
        if not self.db_service:
            return []
        try:
            jobs = self.db_service.query_records("job_postings", limit=500)
            skill_counts: dict[str, int] = {}
            for job in jobs:
                skills = self._extract_skills(job.get("content_json"))
                for skill in skills:
                    key = skill.lower().strip()
                    if key:
                        skill_counts[key] = skill_counts.get(key, 0) + 1
            sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
            return [s[0] for s in sorted_skills[:50]]
        except Exception as e:
            logger.error(f"Error computing trending skills: {e}")
            return []

    def _find_related_skills(self, current: set[str], trending: list[str]) -> list[str]:
        related = []
        for skill in trending:
            skill_lower = skill.lower()
            if skill_lower not in current:
                for cur in current:
                    if cur in skill_lower or skill_lower in cur:
                        related.append(skill_lower)
                        break
        return related


def get_recommendation_service(
    search_service: SearchService | None = None,
    db_service: DatabaseService | None = None,
) -> RecommendationService:
    if search_service is None:
        from app.services.search_service import get_search_service

        search_service = get_search_service()
    if db_service is None:
        db = get_db_session()
        db_service = DatabaseService(db)
    return RecommendationService(search_service=search_service, db_service=db_service)
