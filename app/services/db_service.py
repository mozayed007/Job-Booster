"""Core database service for Job_Booster application.

Handles SQLite database operations via SQLAlchemy: session management
and CRUD operations for all data models.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.db_models import (
    AnalysisResultDB,
    Base,
    JobPostingDB,
    ResumeDB,
    TailoredResumeDB,
    User,
    create_tables,
)

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job_booster.db")


def get_configured_engine(db_url: str = DATABASE_URL):
    """Create and return a SQLAlchemy engine.

    Ensures the parent directory exists for file-based SQLite databases.
    """
    logger.info(f"Initializing database engine: {db_url}")
    if db_url.startswith("sqlite") and db_url != "sqlite:///:memory:":
        try:
            db_path = db_url.split("sqlite:///", 1)[1]
            parent = Path(db_path).parent
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error(f"Cannot create DB directory: {exc}. Falling back to in-memory SQLite.")
            db_url = "sqlite:///:memory:"

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args)


engine = get_configured_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database_tables() -> None:
    """Create all database tables if they do not already exist."""
    logger.info(f"Ensuring database tables exist for: {engine.url}")
    try:
        create_tables(engine)
        logger.info("Database tables ready.")
    except Exception as exc:
        logger.error(f"Error creating database tables: {exc}")


def get_db_session() -> Session:
    """Return a new SQLAlchemy session.

    Caller is responsible for committing/rolling back and closing.
    """
    return SessionLocal()


# ---------------------------------------------------------------------------
# DTO models (used as function arguments)
# ---------------------------------------------------------------------------


class ResumeCreateData(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None


class JobPostingCreateData(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None


class TailoredResumeCreateData(BaseModel):
    user_id: Optional[str] = None
    original_resume_id: Optional[str] = None
    job_posting_id: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = None
    improvements: Optional[Dict[str, Any]] = None


class AnalysisResultCreateData(BaseModel):
    user_id: Optional[str] = None
    resume_id: Optional[str] = None
    job_posting_id: Optional[str] = None
    match_score: Optional[float] = None
    analysis_data: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# DatabaseService class
# ---------------------------------------------------------------------------


class DatabaseService:
    """CRUD service backed by a SQLAlchemy session."""

    def __init__(self, db_session: Session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    _MODEL_MAP: Dict[str, Any] = {
        "users": User,
        "resumes": ResumeDB,
        "job_postings": JobPostingDB,
        "tailored_resumes": TailoredResumeDB,
        "analysis_results": AnalysisResultDB,
    }

    def _get_model(self, table_name: str):
        model = self._MODEL_MAP.get(table_name.lower())
        if model is None:
            raise ValueError(f"Unknown table: {table_name}")
        return model

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results as a list of dicts."""
        try:
            result = self.db.execute(text(query), params or {})
            rows = result.mappings().all()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error(f"execute_raw_query error: {exc}")
            return []

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> Optional[str]:
        """Insert a record into *table_name* and return the new record ID."""
        try:
            model_class = self._get_model(table_name)
            if "id" not in data or not data["id"]:
                data = {**data, "id": str(uuid4())}
            record = model_class(**data)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record.id
        except Exception as exc:
            self.db.rollback()
            logger.error(f"insert_record into '{table_name}' failed: {exc}")
            return None

    def update_records(
        self,
        table_name: str,
        data: Dict[str, Any],
        condition: Dict[str, Any],
    ) -> int:
        """Update records in *table_name* matching *condition*. Returns affected row count."""
        try:
            model_class = self._get_model(table_name)
            query = self.db.query(model_class)
            for col, val in condition.items():
                query = query.filter(getattr(model_class, col) == val)
            count = query.update(data, synchronize_session="fetch")
            self.db.commit()
            return count
        except Exception as exc:
            self.db.rollback()
            logger.error(f"update_records in '{table_name}' failed: {exc}")
            return 0

    def delete_records(self, table_name: str, condition: Dict[str, Any]) -> int:
        """Delete records in *table_name* matching *condition*. Returns affected row count."""
        try:
            model_class = self._get_model(table_name)
            query = self.db.query(model_class)
            for col, val in condition.items():
                query = query.filter(getattr(model_class, col) == val)
            count = query.delete(synchronize_session="fetch")
            self.db.commit()
            return count
        except Exception as exc:
            self.db.rollback()
            logger.error(f"delete_records from '{table_name}' failed: {exc}")
            return 0

    def query_records(
        self,
        table_name: str,
        limit: int = 100,
        offset: int = 0,
        columns: Optional[List[str]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query records from *table_name* with optional filters, limit and offset."""
        try:
            model_class = self._get_model(table_name)
            query = self.db.query(model_class)
            if filter_conditions:
                for col, val in filter_conditions.items():
                    query = query.filter(getattr(model_class, col) == val)
            records = query.offset(offset).limit(limit).all()

            def _to_dict(record) -> Dict[str, Any]:
                d = {c.name: getattr(record, c.name) for c in record.__table__.columns}
                if columns:
                    d = {k: v for k, v in d.items() if k in columns}
                return d

            return [_to_dict(r) for r in records]
        except Exception as exc:
            logger.error(f"query_records from '{table_name}' failed: {exc}")
            return []

    def get_record_by_id(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single record by ID. Returns None if not found."""
        results = self.query_records(table_name, limit=1, filter_conditions={"id": record_id})
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def store_resume(self, resume_data: ResumeCreateData) -> Optional[str]:
        """Insert a resume record and return its ID."""
        try:
            record = ResumeDB(
                id=str(uuid4()),
                user_id=resume_data.user_id,
                title=resume_data.title,
                content=resume_data.content,
                parsed_data=resume_data.parsed_data,
                file_path=resume_data.file_path,
                file_type=resume_data.file_type,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"Stored resume with ID: {record.id}")
            return record.id
        except Exception as exc:
            self.db.rollback()
            logger.error(f"store_resume failed: {exc}")
            return None

    def store_job_posting(self, job_data: JobPostingCreateData) -> Optional[str]:
        """Insert a job posting record and return its ID."""
        try:
            record = JobPostingDB(
                id=str(uuid4()),
                user_id=job_data.user_id,
                title=job_data.title,
                company=job_data.company,
                description=job_data.description,
                parsed_data=job_data.parsed_data,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"Stored job posting with ID: {record.id}")
            return record.id
        except Exception as exc:
            self.db.rollback()
            logger.error(f"store_job_posting failed: {exc}")
            return None

    def store_tailored_resume(self, tailored_data: TailoredResumeCreateData) -> Optional[str]:
        """Insert a tailored resume record and return its ID."""
        try:
            record = TailoredResumeDB(
                id=str(uuid4()),
                user_id=tailored_data.user_id,
                original_resume_id=tailored_data.original_resume_id,
                job_posting_id=tailored_data.job_posting_id,
                content=tailored_data.content,
                format=tailored_data.format,
                improvements=tailored_data.improvements,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"Stored tailored resume with ID: {record.id}")
            return record.id
        except Exception as exc:
            self.db.rollback()
            logger.error(f"store_tailored_resume failed: {exc}")
            return None

    def store_analysis_result(self, analysis_data: AnalysisResultCreateData) -> Optional[str]:
        """Insert an analysis result record and return its ID."""
        try:
            record = AnalysisResultDB(
                id=str(uuid4()),
                user_id=analysis_data.user_id,
                resume_id=analysis_data.resume_id,
                job_posting_id=analysis_data.job_posting_id,
                match_score=analysis_data.match_score,
                analysis_data=analysis_data.analysis_data,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"Stored analysis result with ID: {record.id}")
            return record.id
        except Exception as exc:
            self.db.rollback()
            logger.error(f"store_analysis_result failed: {exc}")
            return None


# ---------------------------------------------------------------------------
# Module-level initialisation (called at startup via app.main)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Running db_service standalone — initializing tables.")
    initialize_database_tables()
