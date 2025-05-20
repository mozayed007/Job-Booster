"""Configuration settings for Job_Booster application."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv 
# from pydantic import validator # To-Do: Re-add if pydantic validators are used
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv() 

class Settings(BaseSettings):
    """Application settings."""
    # Core FastAPI settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite:///./job_booster.db"

    # LLM Configuration (Example for Gemini)
    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-pro"

    # API URL (if frontend needs to know where backend is)
    API_URL: str = "http://localhost:8000"

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True
        extra = "ignore" # Allow extra fields from .env without failing

settings = Settings() 

# To-Do: Add more specific configurations as needed for services (parsing, db, llm)
