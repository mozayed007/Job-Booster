"""Core parsing capabilities for resumes and job descriptions.

This module contains classes for document text extraction (PDF, DOCX, OCR)
and LLM-based parsing for structuring the extracted text.
"""

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from app.models.job_model import (
    Benefit,
    CompanyInfo,
    JobPosting,
    Requirement,
    Responsibility,
)
from app.models.resume_model import (
    Certification,
    ContactInfo,
    Education,
    Project,
    Resume,
    Skill,
    WorkExperience,
)
from app.services.llm_service import LLMService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
RESUME_PROMPT_FILE = PROMPTS_DIR / "resume_parser_prompt.md"
JOB_PROMPT_FILE = PROMPTS_DIR / "job_parser_prompt.md"


# ---------------------------------------------------------------------------
# Document text extraction helpers
# ---------------------------------------------------------------------------


class DocumentParser:
    """Base class providing static text-extraction utilities."""

    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        """Extract text from a PDF file using PyPDF2, with OCR fallback."""
        try:
            import PyPDF2

            text = ""
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text += page_text
            if text.strip():
                return text
            # Fall through to OCR if no text was extracted
            logger.info("PyPDF2 extracted no text; falling back to OCR.")
        except ImportError:
            logger.warning("PyPDF2 not installed; falling back to OCR.")
        except Exception as exc:
            logger.error(f"PyPDF2 error: {exc}; falling back to OCR.")

        return DocumentParser.extract_text_using_ocr(file_content, is_pdf=True)

    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        """Extract text from a DOCX file using python-docx."""
        try:
            import docx

            doc = docx.Document(io.BytesIO(file_content))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(paragraphs)
        except ImportError:
            logger.error("python-docx is not installed.")
            return ""
        except Exception as exc:
            logger.error(f"DOCX extraction error: {exc}")
            return ""

    @staticmethod
    def extract_text_using_ocr(file_content: bytes, is_pdf: bool = True) -> str:
        """Extract text from a document using Tesseract OCR via pytesseract."""
        try:
            import pytesseract
            from PIL import Image

            images = []
            if is_pdf:
                try:
                    from pdf2image import convert_from_bytes
                    images = convert_from_bytes(file_content)
                except ImportError:
                    logger.error("pdf2image is not installed; cannot do OCR on PDF.")
                    return ""
                except Exception as exc:
                    logger.error(f"pdf2image error: {exc}")
                    return ""
            else:
                images = [Image.open(io.BytesIO(file_content))]

            text_parts = []
            for image in images:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    image.save(tmp.name, format="PNG")
                    try:
                        text_parts.append(pytesseract.image_to_string(Image.open(tmp.name)))
                    finally:
                        os.remove(tmp.name)

            return "\n".join(text_parts)
        except ImportError:
            logger.error("pytesseract/Pillow is not installed; OCR unavailable.")
            return ""
        except Exception as exc:
            logger.error(f"OCR error: {exc}")
            return ""


# ---------------------------------------------------------------------------
# LLM-based parsers
# ---------------------------------------------------------------------------


class ResumeParser(DocumentParser):
    """Parser for resume documents.

    Uses document text extraction + LLM to produce a structured Resume object.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialise the parser.

        Args:
            llm_service: An LLMService instance. If None, one is created.
        """
        self.llm_service = llm_service or LLMService()
        self._prompt_template = self._load_prompt(RESUME_PROMPT_FILE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_prompt(path: Path) -> str:
        """Load a prompt template from disk."""
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {path}")
            return "Extract all information from the following resume and return JSON:"

    def _parse_text_with_llm(self, text: str) -> Dict[str, Any]:
        """Send extracted text to the LLM and return structured JSON."""
        prompt = f"{self._prompt_template}\n\n{text}"
        result = self.llm_service.generate_json(prompt)
        if not result:
            logger.warning("LLM returned empty result for resume parsing.")
        return result

    @staticmethod
    def _build_resume_from_dict(data: Dict[str, Any], raw_text: str) -> Resume:
        """Construct a Resume Pydantic object from the LLM-parsed dict."""
        try:
            contact_data = data.get("contact") or {}
            contact = ContactInfo(**contact_data) if contact_data else None

            work_exp = []
            for item in data.get("work_experience") or []:
                try:
                    work_exp.append(WorkExperience(**item))
                except Exception as exc:
                    logger.warning(f"Skipping invalid work experience entry: {exc}")

            education = []
            for item in data.get("education") or []:
                try:
                    education.append(Education(**item))
                except Exception as exc:
                    logger.warning(f"Skipping invalid education entry: {exc}")

            skills = []
            for item in data.get("skills") or []:
                if isinstance(item, str):
                    skills.append(Skill(name=item))
                elif isinstance(item, dict):
                    try:
                        skills.append(Skill(**item))
                    except Exception as exc:
                        logger.warning(f"Skipping invalid skill entry: {exc}")

            projects = []
            for item in data.get("projects") or []:
                try:
                    projects.append(Project(**item))
                except Exception as exc:
                    logger.warning(f"Skipping invalid project entry: {exc}")

            certifications = []
            for item in data.get("certifications") or []:
                try:
                    certifications.append(Certification(**item))
                except Exception as exc:
                    logger.warning(f"Skipping invalid certification entry: {exc}")

            return Resume(
                contact=contact,
                summary=data.get("summary"),
                objective=data.get("objective"),
                work_experience=work_exp,
                education=education,
                skills=skills,
                projects=projects,
                certifications=certifications,
                languages=data.get("languages") or [],
                awards=data.get("awards") or [],
                publications=data.get("publications") or [],
                raw_text=raw_text,
            )
        except Exception as exc:
            logger.error(f"Failed to build Resume from dict: {exc}")
            return Resume(raw_text=raw_text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def parse_resume_file_content(self, file_content: bytes, filename: str) -> Resume:
        """Parse resume from file bytes.

        Extracts text according to file type, then invokes the LLM to
        structure the result into a Resume object.

        Args:
            file_content: Raw file bytes.
            filename: Original filename (used to infer file type).

        Returns:
            A populated Resume instance.
        """
        ext = Path(filename).suffix.lower()
        text = ""

        if ext == ".pdf":
            text = self.extract_text_from_pdf(file_content)
        elif ext == ".docx":
            text = self.extract_text_from_docx(file_content)
        elif ext in {".txt", ".md"}:
            try:
                text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                text = file_content.decode("latin-1", errors="replace")
        elif ext in {".png", ".jpg", ".jpeg"}:
            text = self.extract_text_using_ocr(file_content, is_pdf=False)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return Resume(summary=f"Unsupported file type: {ext}")

        if not text.strip():
            logger.warning(f"No text extracted from {filename}.")
            return Resume(summary=f"Could not extract text from {filename}.", raw_text="")

        logger.info(f"Extracted {len(text)} characters from {filename}. Sending to LLM…")
        parsed_data = self._parse_text_with_llm(text)

        if parsed_data:
            resume = self._build_resume_from_dict(parsed_data, raw_text=text)
        else:
            logger.warning("LLM parsing failed; returning resume with raw text only.")
            resume = Resume(raw_text=text)

        return resume


class JobParser(DocumentParser):
    """Parser for job description text.

    Uses the LLM to parse a job description string into a structured JobPosting.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialise the parser.

        Args:
            llm_service: An LLMService instance. If None, one is created.
        """
        self.llm_service = llm_service or LLMService()
        self._prompt_template = self._load_prompt(JOB_PROMPT_FILE)

    @staticmethod
    def _load_prompt(path: Path) -> str:
        """Load a prompt template from disk."""
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {path}")
            return "Extract all information from the following job description and return JSON:"

    def _parse_text_with_llm(self, text: str) -> Dict[str, Any]:
        """Send job description text to the LLM and return structured JSON."""
        prompt = f"{self._prompt_template}\n\n{text}"
        result = self.llm_service.generate_json(prompt)
        if not result:
            logger.warning("LLM returned empty result for job parsing.")
        return result

    @staticmethod
    def _build_job_posting_from_dict(data: Dict[str, Any], raw_text: str) -> JobPosting:
        """Construct a JobPosting Pydantic object from the LLM-parsed dict."""
        try:
            company_data = data.get("company") or {}
            company = CompanyInfo(**company_data) if company_data else None

            requirements = []
            for item in data.get("requirements") or []:
                if isinstance(item, str):
                    requirements.append(Requirement(description=item))
                elif isinstance(item, dict):
                    try:
                        requirements.append(Requirement(**item))
                    except Exception as exc:
                        logger.warning(f"Skipping invalid requirement: {exc}")

            responsibilities = []
            for item in data.get("responsibilities") or []:
                if isinstance(item, str):
                    responsibilities.append(Responsibility(description=item))
                elif isinstance(item, dict):
                    try:
                        responsibilities.append(Responsibility(**item))
                    except Exception as exc:
                        logger.warning(f"Skipping invalid responsibility: {exc}")

            benefits = []
            for item in data.get("benefits") or []:
                if isinstance(item, str):
                    benefits.append(Benefit(description=item))
                elif isinstance(item, dict):
                    try:
                        benefits.append(Benefit(**item))
                    except Exception as exc:
                        logger.warning(f"Skipping invalid benefit: {exc}")

            return JobPosting(
                title=data.get("title"),
                company=company,
                location=data.get("location"),
                remote_type=data.get("remote_type"),
                employment_type=data.get("employment_type"),
                experience_level=data.get("experience_level"),
                salary_range=data.get("salary_range"),
                description=data.get("description"),
                requirements=requirements,
                responsibilities=responsibilities,
                benefits=benefits,
                required_skills=data.get("required_skills") or [],
                preferred_skills=data.get("preferred_skills") or [],
                keywords=data.get("keywords") or [],
                raw_text=raw_text,
            )
        except Exception as exc:
            logger.error(f"Failed to build JobPosting from dict: {exc}")
            return JobPosting(raw_text=raw_text)

    def parse_job_text(self, job_text: str) -> JobPosting:
        """Parse a raw job description string.

        Args:
            job_text: The full job description as plain text.

        Returns:
            A populated JobPosting instance.
        """
        if not job_text.strip():
            logger.warning("Empty job description provided.")
            return JobPosting(title="(Empty job description)")

        logger.info(f"Parsing job description ({len(job_text)} chars)…")
        parsed_data = self._parse_text_with_llm(job_text)

        if parsed_data:
            return self._build_job_posting_from_dict(parsed_data, raw_text=job_text)
        else:
            logger.warning("LLM parsing failed; returning job posting with raw text only.")
            return JobPosting(raw_text=job_text)
