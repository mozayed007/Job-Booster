"""Core database service for Job_Booster application.

This module handles SQLite database operations, including setup, session management,
and CRUD operations for various data models.
"""

import os
import json
import sqlite3 # Keep for potential direct use, though SQLAlchemy is primary
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Attempting to import original model paths, will be updated later
# These will cause errors until imports are fixed globally
from app.models.db_models import Base, User, ResumeDB, JobPostingDB, TailoredResumeDB, AnalysisResultDB, create_tables

# --- Database Configuration & Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job_booster.db")

def get_configured_engine(db_url: str = DATABASE_URL):
    """Creates and returns a SQLAlchemy engine based on the DATABASE_URL.
    Ensures parent directory exists for file-based SQLite databases.
    """
    logger.info(f"Initializing database engine for URL: {db_url}")
    if db_url.startswith("sqlite") and not db_url == "sqlite:///:memory:":
        try:
            db_file = Path(db_url.split("sqlite:///", 1)[1])
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured database directory exists: {db_file.parent}")
        except Exception as e:
            logger.error(f"Could not create database directory for {db_url}: {e}")
            # Fallback to in-memory if directory creation fails for a file-based DB
            logger.warning("Falling back to in-memory SQLite database due to directory error.")
            db_url = "sqlite:///:memory:"
            
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})
    return engine

engine = get_configured_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def initialize_database_tables():
    """Creates all tables in the database based on SQLAlchemy models."""
    logger.info(f"Creating database tables if they don't exist for {engine.url}...")
    try:
        # Base.metadata.create_all(bind=engine) # This is what create_tables should do
        create_tables(engine) # Uses the function imported from app.models.db_models
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Call at module load time or explicitly from app startup
# initialize_database_tables() # We'll call this from app.main explicitly

# --- Database Session Management ---
def get_db_session() -> Session:
    """Provides a SQLAlchemy database session.
    
    It's the responsibility of the caller to close this session.
    Usage: 
        db = get_db_session()
        try:
            # ... use db ...
            db.commit()
        except:
            db.rollback()
            raise
        finally:
            db.close()
    """
    return SessionLocal()

# --- Pydantic Models for Service Layer (data validation/DTOs) ---
# These were originally for FastAPI request validation.
# They can be reused or adapted for service layer function arguments.

class ResumeCreateData(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None # Raw content if not parsed, or tailored content
    parsed_data: Optional[Dict[str, Any]] = None # Structured data from ResumeParser
    file_path: Optional[str] = None
    file_type: Optional[str] = None

class JobPostingCreateData(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None # Raw job description text
    parsed_data: Optional[Dict[str, Any]] = None # Structured data from JobParser

class TailoredResumeCreateData(BaseModel):
    user_id: Optional[str] = None
    original_resume_id: Optional[str] = None # Link to ResumeDB.id
    job_posting_id: Optional[str] = None   # Link to JobPostingDB.id
    content: Optional[str] = None # The tailored resume content
    format: Optional[str] = None # e.g., 'markdown', 'pdf_path'
    improvements: Optional[Dict[str, Any]] = None # Analysis of improvements

class AnalysisResultCreateData(BaseModel):
    user_id: Optional[str] = None
    resume_id: Optional[str] = None
    job_posting_id: Optional[str] = None
    match_score: Optional[float] = None
    analysis_data: Optional[Dict[str, Any]] = None # Detailed analysis, suggestions

class QueryServiceRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = None

class DataServiceRequest(BaseModel):
    table: str # Table name as string, consider using Enum or model class directly
    data: Dict[str, Any]
    condition: Optional[Dict[str, Any]] = None # For update/delete operations

# --- Database Service Functions (CRUD operations) ---

class DatabaseService:
    def __init__(self, db_session: Session):
        self.db = db_session

    # To-Do: Implement all the following methods using self.db (SQLAlchemy session)
    # The original code had these as FastAPI endpoints with # To-Do comments.
    # They are now service methods.

    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        logger.info(f"Stubbed DatabaseService.execute_raw_query for query: {query}")
        # Example: result = self.db.execute(text(query), params or {}).fetchall()
        # return [dict(row) for row in result] # If using SQLAlchemy 2.0 style
        return [{"status": "to-do", "message": "Raw SQL execution not implemented"}]

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> Optional[Any]:
        logger.info(f"Stubbed DatabaseService.insert_record into table {table_name}")
        # To-Do: Map table_name to SQLAlchemy model, create instance, add, commit, return ID.
        # Example: 
        #   model_class = self._get_model_by_name(table_name)
        #   if not model_class: raise ValueError(f"Table {table_name} not found")
        #   new_record = model_class(**data)
        #   self.db.add(new_record)
        #   self.db.commit()
        #   self.db.refresh(new_record)
        #   return new_record.id
        return None # Placeholder for inserted ID

    def update_records(self, table_name: str, data: Dict[str, Any], condition: Dict[str, Any]) -> int:
        logger.info(f"Stubbed DatabaseService.update_records for table {table_name}")
        # To-Do: Map table_name to model, build query with filter, update, commit, return rowcount.
        return 0 # Placeholder for affected rows

    def delete_records(self, table_name: str, condition: Dict[str, Any]) -> int:
        logger.info(f"Stubbed DatabaseService.delete_records from table {table_name}")
        # To-Do: Map table_name to model, build query with filter, delete, commit, return rowcount.
        return 0 # Placeholder for affected rows

    def query_records(
        self,
        table_name: str,
        limit: int = 100,
        offset: int = 0,
        columns: Optional[List[str]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        logger.info(f"Stubbed DatabaseService.query_records for table {table_name}")
        # To-Do: Map table_name to model, build query with filters, columns, limit, offset.
        return [{"status": "to-do", "message": f"Query for {table_name} not implemented"}]

    # --- MCP-specific service methods ---
    def store_resume(self, resume_data: ResumeCreateData) -> Optional[str]:
        logger.info(f"Stubbed DatabaseService.store_resume for user: {resume_data.user_id}")
        # To-Do: Insert into ResumeDB table.
        # Example: data_to_insert = resume_data.dict()
        # resume_db_entry = ResumeDB(**data_to_insert) # adapt fields
        # self.db.add(resume_db_entry)
        # self.db.commit()
        # return resume_db_entry.id
        return "stub_resume_id"

    def store_job_posting(self, job_data: JobPostingCreateData) -> Optional[str]:
        logger.info(f"Stubbed DatabaseService.store_job_posting for user: {job_data.user_id}")
        # To-Do: Insert into JobPostingDB table.
        return "stub_job_id"

    def store_tailored_resume(self, tailored_resume_data: TailoredResumeCreateData) -> Optional[str]:
        logger.info(f"Stubbed DatabaseService.store_tailored_resume for user: {tailored_resume_data.user_id}")
        # To-Do: Insert into TailoredResumeDB table.
        return "stub_tailored_resume_id"

    def store_analysis_result(self, analysis_data: AnalysisResultCreateData) -> Optional[str]:
        logger.info(f"Stubbed DatabaseService.store_analysis_result for user: {analysis_data.user_id}")
        # To-Do: Insert into AnalysisResultDB table.
        return "stub_analysis_id"

    # Helper to map table names to models (optional, can be done explicitly in each method)
    # def _get_model_by_name(self, table_name: str):
    #     model_map = {
    #         "users": User,
    #         "resumes": ResumeDB,
    #         "job_postings": JobPostingDB,
    #         "tailored_resumes": TailoredResumeDB,
    #         "analysis_results": AnalysisResultDB
    #     }
    #     return model_map.get(table_name.lower())

# Example usage (for testing or direct script use, not part of service typically)
if __name__ == "__main__":
    logger.info("Database service module direct run (for testing/init purposes).")
    
    # This will create tables if initialize_database_tables() is uncommented or called here
    initialize_database_tables() # Make sure this runs if you test directly
    logger.info("Database tables initialized (if not already present).")

    # Example: test inserting and querying (requires implemented methods and correct imports)
    # db_session = get_db_session()
    # service = DatabaseService(db_session)
    # try:
    #     # Test operations here
    #     # user_id = service.insert_record("users", {"email": "test@example.com", "hashed_password": "abc"})
    #     # logger.info(f"Inserted user with ID: {user_id}")
    #     # users = service.query_records("users")
    #     # logger.info(f"Users: {users}")
    #     pass
    # finally:
    #     db_session.close()
