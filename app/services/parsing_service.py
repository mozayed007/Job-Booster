"""Core parsing capabilities for resumes and job descriptions.

Handles text extraction (PDF, DOCX, MD, TXT, LaTeX) and LLM-based structured parsing.
"""

import io
import re
from pathlib import Path
from typing import Optional

import docx
from loguru import logger

# Resolve prompt directory relative to this file
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

try:
    from liteparse import LiteParse

    _liteparse_parser = LiteParse()
    LITEPARSE_AVAILABLE = True
except Exception:
    LITEPARSE_AVAILABLE = False
    _liteparse_parser = None

try:
    from glmocr import parse as glmocr_parse

    GLMOCR_AVAILABLE = True
except Exception:
    GLMOCR_AVAILABLE = False
    glmocr_parse = None

from app.models.job_model import JobPosting
from app.models.resume_model import (
    Resume,
)


def _extract_latex_text(tex_content: str) -> str:
    """Strip LaTeX commands, extract readable text from .tex files."""
    text = tex_content
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\(sub)?section\*?\{([^}]*)\}", r"\n\2\n", text)
    text = re.sub(r"\\item\s*", "- ", text)
    for cmd in ["textbf", "textit", "emph", "underline", "text"]:
        text = re.sub(rf"\\{cmd}\{{([^}}]*)\}}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})*", "", text)
    text = re.sub(r"\\begin\{[^}]*\}", "", text)
    text = re.sub(r"\\end\{[^}]*\}", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from a PDF using LiteParse, with GLM-OCR fallback for scanned docs."""
    if not LITEPARSE_AVAILABLE or _liteparse_parser is None:
        logger.warning("LiteParse not available, trying GLM-OCR")
        return _glmocr_extract(file_content)

    try:
        result = _liteparse_parser.parse(file_content, ocr_enabled=False)
        text = result.text.strip() if result and result.text else ""
        if text:
            return text
        # LiteParse returned empty — likely a scanned PDF. Try GLM-OCR.
        logger.info("LiteParse returned empty text, trying GLM-OCR for scanned PDF")
        return _glmocr_extract(file_content)
    except Exception as e:
        logger.error(f"LiteParse PDF extraction failed: {e}, trying GLM-OCR")
        return _glmocr_extract(file_content)


def _glmocr_extract(file_content: bytes) -> str:
    """Extract text from a scanned document using GLM-OCR (vision-based OCR)."""
    if not GLMOCR_AVAILABLE or glmocr_parse is None:
        logger.warning("GLM-OCR not available, falling back to raw decode")
        return file_content.decode("utf-8", errors="replace")

    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        result = glmocr_parse(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
        if result and hasattr(result, "text") and result.text:
            return result.text.strip()
        return ""
    except Exception as e:
        logger.error(f"GLM-OCR extraction failed: {e}")
        return ""


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from a DOCX file.

    LiteParse handles DOCX natively when LibreOffice is installed.
    Falls back to python-docx for direct extraction.
    """
    if LITEPARSE_AVAILABLE and _liteparse_parser is not None:
        try:
            result = _liteparse_parser.parse(file_content)
            if result and result.text and result.text.strip():
                return result.text.strip()
        except Exception as e:
            logger.debug(f"LiteParse DOCX extraction failed, falling back: {e}")

    try:
        document = docx.Document(io.BytesIO(file_content))
        return "\n".join(para.text for para in document.paragraphs if para.text)
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        return ""


def extract_text(file_content: bytes, filename: str) -> str:
    """Extract text from any supported file format.

    LiteParse handles PDF, DOCX, XLSX, PPTX, and images natively.
    LaTeX, Markdown, and plain text are handled directly.

    Args:
        file_content: Raw file bytes.
        filename: Original filename (used to determine format).

    Returns:
        Extracted text content.
    """
    file_ext = Path(filename).suffix.lower()

    if file_ext == ".pdf":
        return extract_text_from_pdf(file_content)
    elif file_ext == ".docx":
        return extract_text_from_docx(file_content)
    elif file_ext == ".tex":
        try:
            raw = file_content.decode("utf-8", errors="replace")
            return _extract_latex_text(raw)
        except Exception as e:
            logger.error(f"Error extracting text from LaTeX: {e}")
            return ""
    elif file_ext in (".md", ".txt"):
        try:
            return file_content.decode("utf-8")
        except UnicodeDecodeError:
            return file_content.decode("latin-1", errors="replace")
    elif LITEPARSE_AVAILABLE and _liteparse_parser is not None:
        # LiteParse handles images, Office formats, etc.
        try:
            result = _liteparse_parser.parse(file_content)
            return result.text.strip() if result and result.text else ""
        except Exception as e:
            logger.error(f"LiteParse extraction failed for {filename}: {e}")
            return ""
    else:
        logger.warning(f"Unsupported file type: {file_ext}")
        return ""


class ParserLLM:
    """LLM client for parsing documents into structured data using Pydantic AI."""

    def __init__(self):
        logger.info("ParserLLM initialized (agents created on demand)")

    async def parse_resume(self, text: str) -> Resume:
        """Parse resume text into structured Resume data using Pydantic AI."""
        try:
            from app.core.model_registry import create_agent

            prompt_path = _PROMPTS_DIR / "resume_parser_prompt.md"
            system_prompt = (
                prompt_path.read_text(encoding="utf-8")
                if prompt_path.exists()
                else "Extract structured resume data."
            )

            agent = create_agent(
                output_type=Resume,
                system_prompt=system_prompt,
            )
            result = await agent.run(f"Parse this resume:\n\n{text[:8000]}")
            return result.output
        except Exception as e:
            logger.error(f"Resume parsing failed: {e}")
            return Resume(summary=f"Parsing failed: {e}", raw_text=text[:2000])

    async def parse_job(self, text: str) -> JobPosting:
        """Parse job description text into structured JobPosting data using Pydantic AI."""
        try:
            from app.core.model_registry import create_agent

            prompt_path = _PROMPTS_DIR / "job_parser_prompt.md"
            system_prompt = (
                prompt_path.read_text(encoding="utf-8")
                if prompt_path.exists()
                else "Extract structured job posting data."
            )

            agent = create_agent(
                output_type=JobPosting,
                system_prompt=system_prompt,
            )
            result = await agent.run(f"Parse this job description:\n\n{text[:8000]}")
            return result.output
        except Exception as e:
            logger.error(f"Job parsing failed: {e}")
            return JobPosting(title=f"Parsing failed: {e}", description=text[:1000])


class ResumeParser:
    """Parser for resume documents."""

    def __init__(self, llm_client: Optional[ParserLLM] = None):
        self.llm_client = llm_client or ParserLLM()

    async def parse_resume_file_content(self, file_content: bytes, filename: str) -> Resume:
        """Extract text from file and parse into structured Resume.

        Args:
            file_content: Raw file bytes.
            filename: Original filename.

        Returns:
            Parsed Resume object.
        """
        text = extract_text(file_content, filename)
        if not text.strip():
            logger.warning(f"No text extracted from {filename}")
            return Resume(summary=f"Failed to extract text from: {filename}")

        logger.info(f"Extracted {len(text)} chars from {filename}, sending to LLM...")
        resume = await self.llm_client.parse_resume(text)
        resume.raw_text = text[:5000]
        return resume


class JobParser:
    """Parser for job description documents/text."""

    def __init__(self, llm_client: Optional[ParserLLM] = None):
        self.llm_client = llm_client or ParserLLM()

    async def parse_job_text(self, job_text: str) -> JobPosting:
        """Parse job description text into structured JobPosting.

        Args:
            job_text: The job description text.

        Returns:
            Parsed JobPosting object.
        """
        if not job_text.strip():
            logger.warning("Job description text is empty.")
            return JobPosting(title="Empty job description provided.")

        logger.info(f"Parsing job description ({len(job_text)} chars)...")
        return await self.llm_client.parse_job(job_text)
