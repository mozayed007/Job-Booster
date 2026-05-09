"""Core database service for Job_Booster application.

Handles SQLite database operations via SQLAlchemy: setup, session management, CRUD.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.db_models import (
    AnalysisResultDB,
    ApplicationDB,
    CoverLetterDB,
    JobPostingDB,
    ResumeDB,
    ResumeVersionDB,
    ScannedJobDB,
    ScannerStateDB,
    StartupDB,
    TailoredResumeDB,
    User,
    create_tables,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job_booster.db")


def get_configured_engine(db_url: str = DATABASE_URL):
    """Creates and returns a SQLAlchemy engine."""
    logger.info(f"Initializing database engine for URL: {db_url}")
    if db_url.startswith("sqlite") and db_url != "sqlite:///:memory:":
        try:
            db_file = Path(db_url.split("sqlite:///", 1)[1])
            db_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create database directory for {db_url}: {e}")
            db_url = "sqlite:///:memory:"

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args)


engine = get_configured_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database_tables():
    """Creates all tables in the database."""
    logger.info(f"Creating database tables for {engine.url}...")
    try:
        create_tables(engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")


def get_db_session() -> Session:
    """Provides a SQLAlchemy database session. Caller must close it."""
    return SessionLocal()


# --- Pydantic DTOs ---


class ResumeCreateData(BaseModel):
    user_id: Optional[int] = None
    filename: str = ""
    parsed_data: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    version_name: Optional[str] = None
    file_path: Optional[str] = None
    file_format: Optional[str] = None


class JobPostingCreateData(BaseModel):
    title: str = ""
    company: Optional[str] = None
    description: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    source_url: Optional[str] = None


class TailoredResumeCreateData(BaseModel):
    resume_id: int
    job_id: int
    tailored_content: str = ""
    match_score: Optional[float] = None


class AnalysisResultCreateData(BaseModel):
    resume_id: int
    job_id: int
    analysis_data: Optional[Dict[str, Any]] = None


class CoverLetterCreateData(BaseModel):
    resume_id: Optional[int] = None
    job_id: Optional[int] = None
    cover_letter_text: str = ""
    key_highlights: Optional[list] = None
    company_name: Optional[str] = None


class ApplicationCreateData(BaseModel):
    user_id: Optional[int] = None
    job_id: Optional[int] = None
    resume_id: Optional[int] = None
    company_name: str = ""
    position_title: str = ""
    status: str = "applied"
    notes: Optional[str] = None


# --- Database Service ---

TABLE_MODEL_MAP = {
    "users": User,
    "resumes": ResumeDB,
    "resume_versions": ResumeVersionDB,
    "job_postings": JobPostingDB,
    "tailored_resumes": TailoredResumeDB,
    "analysis_results": AnalysisResultDB,
    "cover_letters": CoverLetterDB,
    "startups": StartupDB,
    "scanned_jobs": ScannedJobDB,
    "scanner_state": ScannerStateDB,
    "applications": ApplicationDB,
}


class DatabaseService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def _get_model_by_name(self, table_name: str):
        return TABLE_MODEL_MAP.get(table_name.lower())

    def store_resume(self, data: ResumeCreateData) -> Optional[int]:
        """Store a parsed resume and optionally its version."""
        try:
            resume_db = ResumeDB(
                user_id=data.user_id,
                filename=data.filename,
                content_json=data.parsed_data,
                raw_text=data.raw_text,
            )
            self.db.add(resume_db)
            self.db.flush()

            if data.version_name and data.file_path:
                version_db = ResumeVersionDB(
                    resume_id=resume_db.id,
                    version_name=data.version_name,
                    file_path=data.file_path,
                    file_format=data.file_format or "unknown",
                    raw_text=data.raw_text,
                    is_active=True,
                )
                self.db.add(version_db)

            self.db.commit()
            self.db.refresh(resume_db)
            logger.info(f"Stored resume id={resume_db.id}")
            return resume_db.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing resume: {e}")
            return None

    def store_job_posting(self, data: JobPostingCreateData) -> Optional[int]:
        """Store a parsed job posting."""
        try:
            job_db = JobPostingDB(
                title=data.title,
                company=data.company,
                content_json=data.parsed_data,
                raw_text=data.raw_text,
                source_url=data.source_url,
            )
            self.db.add(job_db)
            self.db.commit()
            self.db.refresh(job_db)
            logger.info(f"Stored job posting id={job_db.id}")
            return job_db.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing job posting: {e}")
            return None

    def store_tailored_resume(self, data: TailoredResumeCreateData) -> Optional[int]:
        """Store a tailored resume."""
        try:
            tailored_db = TailoredResumeDB(
                resume_id=data.resume_id,
                job_id=data.job_id,
                tailored_content=data.tailored_content,
                match_score=data.match_score,
            )
            self.db.add(tailored_db)
            self.db.commit()
            self.db.refresh(tailored_db)
            logger.info(f"Stored tailored resume id={tailored_db.id}")
            return tailored_db.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing tailored resume: {e}")
            return None

    def store_analysis_result(self, data: AnalysisResultCreateData) -> Optional[int]:
        """Store an analysis result."""
        try:
            analysis_db = AnalysisResultDB(
                resume_id=data.resume_id,
                job_id=data.job_id,
                analysis_json=data.analysis_data,
            )
            self.db.add(analysis_db)
            self.db.commit()
            self.db.refresh(analysis_db)
            logger.info(f"Stored analysis result id={analysis_db.id}")
            return analysis_db.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing analysis result: {e}")
            return None

    def store_cover_letter(self, data: CoverLetterCreateData) -> Optional[int]:
        """Store a generated cover letter."""
        try:
            cl_db = CoverLetterDB(
                resume_id=data.resume_id,
                job_id=data.job_id,
                cover_letter_text=data.cover_letter_text,
                key_highlights_json=data.key_highlights,
                company_name=data.company_name,
            )
            self.db.add(cl_db)
            self.db.commit()
            self.db.refresh(cl_db)
            logger.info(f"Stored cover letter id={cl_db.id}")
            return cl_db.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing cover letter: {e}")
            return None

    def get_resume_versions(self, resume_id: int) -> List[Dict[str, Any]]:
        """Get all versions for a resume."""
        try:
            versions = (
                self.db.query(ResumeVersionDB).filter(ResumeVersionDB.resume_id == resume_id).all()
            )
            return [
                {
                    "id": v.id,
                    "version_name": v.version_name,
                    "file_path": v.file_path,
                    "file_format": v.file_format,
                    "is_active": v.is_active,
                    "created_at": str(v.created_at),
                }
                for v in versions
            ]
        except Exception as e:
            logger.error(f"Error getting resume versions: {e}")
            return []

    def get_active_version(self, resume_id: int) -> Optional[Dict[str, Any]]:
        """Get the active version for a resume."""
        try:
            version = (
                self.db.query(ResumeVersionDB)
                .filter(
                    ResumeVersionDB.resume_id == resume_id,
                    ResumeVersionDB.is_active.is_(True),
                )
                .first()
            )
            if version:
                return {
                    "id": version.id,
                    "version_name": version.version_name,
                    "file_path": version.file_path,
                    "file_format": version.file_format,
                    "raw_text": version.raw_text,
                    "created_at": str(version.created_at),
                }
            return None
        except Exception as e:
            logger.error(f"Error getting active version: {e}")
            return None

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> Optional[int]:
        """Insert a record into any table by name."""
        model_class = self._get_model_by_name(table_name)
        if not model_class:
            logger.error(f"Unknown table: {table_name}")
            return None
        try:
            record = model_class(**data)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inserting into {table_name}: {e}")
            return None

    def query_records(
        self,
        table_name: str,
        limit: int = 100,
        offset: int = 0,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query records from any table by name."""
        model_class = self._get_model_by_name(table_name)
        if not model_class:
            logger.error(f"Unknown table: {table_name}")
            return []
        try:
            query = self.db.query(model_class)
            if filter_conditions:
                for key, value in filter_conditions.items():
                    if hasattr(model_class, key):
                        query = query.filter(getattr(model_class, key) == value)
            records = query.offset(offset).limit(limit).all()
            result = []
            for r in records:
                d = {}
                for col in r.__table__.columns:
                    val = getattr(r, col.name)
                    d[col.name] = str(val) if val is not None else None
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"Error querying {table_name}: {e}")
            return []
