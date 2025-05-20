"""Core parsing capabilities for resumes and job descriptions.

This module contains classes for document text extraction (PDF, DOCX, OCR)
and LLM-based parsing for structuring the extracted text.
"""

import os
import io
import json
import tempfile
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

import docx
from loguru import logger # Retaining loguru as it was used in the original parser logic
import pytesseract
from PIL import Image
import PyPDF2
from pdf2image import convert_from_bytes # For converting PDF to images

# Attempting to import original model paths, will be updated later
# These will cause errors until imports are fixed globally
# from common.models.resume import Resume, ContactInfo, Education, WorkExperience, Skill
# from common.models.job import JobPosting, CompanyInfo, Requirement, Responsibility
from app.models.resume_model import Resume, ContactInfo, Education, WorkExperience, Skill # Corrected
from app.models.job_model import JobPosting, CompanyInfo, Requirement, Responsibility # Corrected

# Import Google ADK Agent (if used directly by ParserLLM)
# from google.adk.agents import Agent
# from google.adk.common import Message

# Placeholder for ADK Agent, actual import and initialization will depend on final ADK setup
Agent = None 
Message = None

class ParserLLM:
    """LLM client for parsing documents.
    
    This class will be responsible for interacting with the chosen LLM (e.g., Gemini via ADK)
    to parse text extracted from documents into structured data.
    """

    def __init__(self):
        """Initialize the LLM client."""
        # To-Do: Initialize ADK Agent with Gemini model or other LLM client
        logger.info("Stubbed ParserLLM __init__ called.")
        self.agent = None # Placeholder for ADK Agent or other LLM client instance

    def parse_text(self, text: str, prompt_template: str) -> Dict[str, Any]:
        """Parse text using the LLM.

        Args:
            text: The text to parse.
            prompt_template: The prompt template to use.

        Returns:
            The parsed data as a dictionary.
        """
        # To-Do: Implement LLM call via ADK Agent (or other client) to parse text and return structured data
        logger.info(f"Stubbed ParserLLM.parse_text called for text: {text[:100]}...")
        # Example placeholder response structure
        return {
            "status": "to-do", 
            "message": "LLM parsing not implemented in ParserLLM", 
            "parsed_data": {}
        }


class DocumentParser:
    """Base class for document parsers, providing text extraction utilities."""

    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        """Extract text from a PDF file.

        Args:
            file_content: The PDF file content as bytes.

        Returns:
            The extracted text.
        """
        # To-Do: Implement robust PDF text extraction logic, potentially using PyPDF2 for direct extraction
        # and falling back to OCR if needed (or as a primary method if preferred).
        logger.info("Stubbed DocumentParser.extract_text_from_pdf called.")
        # Basic PyPDF2 implementation attempt (will be stubbed due to To-Do)
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page_num in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page_num].extract_text()
            if not text.strip(): # If no text extracted, suggest OCR
                text = "(No text directly extracted, consider OCR)"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            text = "(Error during PDF text extraction)"
        return text if text.strip() else "Text to be extracted from PDF (stub)."

    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        """Extract text from a DOCX file.

        Args:
            file_content: The DOCX file content as bytes.

        Returns:
            The extracted text.
        """
        # To-Do: Implement DOCX text extraction logic using python-docx
        logger.info("Stubbed DocumentParser.extract_text_from_docx called.")
        try:
            doc = docx.Document(io.BytesIO(file_content))
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return "\n".join(full_text) if full_text else "Text to be extracted from DOCX (stub)."
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return "(Error during DOCX text extraction)"

    @staticmethod
    def extract_text_using_ocr(file_content: bytes, is_pdf: bool = True) -> str:
        """Extract text from a document (typically PDF or image) using OCR.
        
        Args:
            file_content: The document file content as bytes.
            is_pdf: Flag indicating if the content is PDF (requires conversion to images first).
            
        Returns:
            The extracted text.
        """
        # To-Do: Implement OCR text extraction logic using Tesseract via pytesseract.
        # Ensure Poppler (for pdf2image on Windows) and Tesseract are installed and in PATH.
        logger.info("Stubbed DocumentParser.extract_text_using_ocr called.")
        text = ""
        try:
            if is_pdf:
                images = convert_from_bytes(file_content) # Requires Poppler
            else: # Assuming file_content is already an image if not PDF
                images = [Image.open(io.BytesIO(file_content))]
            
            for i, image in enumerate(images):
                # Save the image to a temporary file to pass to Tesseract if direct bytes not working well
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image_file:
                    image.save(tmp_image_file.name, format="PNG")
                    try:
                        text += pytesseract.image_to_string(Image.open(tmp_image_file.name)) + "\n"
                    finally:
                        os.remove(tmp_image_file.name) # Clean up temp file
            if not text.strip():
                 text = "(No text extracted via OCR)"
        except Exception as e:
            logger.error(f"Error during OCR: {e}")
            text = "(Error during OCR text extraction)"
        return text if text.strip() else "Text to be extracted using OCR (stub)."


class ResumeParser(DocumentParser):
    """Parser for resume documents."""
    DEFAULT_RESUME_PROMPT_TEMPLATE_FILE = "resume_parser_prompt.md" # Example, adjust path as needed

    def __init__(self, llm_client: ParserLLM, prompts_dir: Path = Path("app/prompts")):
        """Initialize the resume parser.
        
        Args:
            llm_client: An instance of ParserLLM to use for parsing.
            prompts_dir: Directory where prompt templates are stored.
        """
        logger.info("Stubbed ResumeParser __init__ called.")
        self.llm_client = llm_client
        self.prompts_dir = prompts_dir
        self.resume_prompt_template = self._load_prompt_template(self.DEFAULT_RESUME_PROMPT_TEMPLATE_FILE)

    def _load_prompt_template(self, template_file_name: str) -> str:
        """Loads a prompt template from a file."""
        # To-Do: Implement actual file loading
        try:
            prompt_path = self.prompts_dir / template_file_name
            # with open(prompt_path, "r") as f: # This will be enabled post-stubbing
            #     return f.read()
            logger.info(f"Stubbed: Would load prompt from {prompt_path}")
            return f"To-Do: Load prompt from {template_file_name}"
        except FileNotFoundError:
            logger.error(f"Prompt template file not found: {template_file_name}")
            return "To-Do: Default fallback prompt if file not found."

    async def parse_resume_file_content(self, file_content: bytes, filename: str) -> Resume:
        """Parse resume content from bytes.

        Args:
            file_content: The resume file content as bytes.
            filename: The original name of the file, used to determine type.

        Returns:
            A Resume object with the parsed data.
        """
        logger.info(f"ResumeParser.parse_resume_file_content called for file: {filename}")
        text = ""
        file_ext = Path(filename).suffix.lower()

        if file_ext == ".pdf":
            text = self.extract_text_from_pdf(file_content) # Try direct extraction first
            if "(No text directly extracted" in text or "(Error during PDF text extraction)" in text or not text.strip():
                logger.info(f"Direct PDF extraction yielded little/no text for {filename}, trying OCR.")
                text = self.extract_text_using_ocr(file_content, is_pdf=True)
        elif file_ext == ".docx":
            text = self.extract_text_from_docx(file_content)
        elif file_ext in [".txt", ".md"]:
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text = file_content.decode('latin-1', errors='replace')
        elif file_ext in [".png", ".jpg", ".jpeg"]:
             text = self.extract_text_using_ocr(file_content, is_pdf=False)
        else:
            logger.warning(f"Unsupported file type for resume: {filename}")
            # Return a stubbed Resume object with an error or indication
            return Resume(summary=f"Unsupported file type: {file_ext}")

        if not text.strip() or "(Error during" in text or "(No text extracted" in text:
            logger.warning(f"Could not extract usable text from {filename}.")
            return Resume(summary=f"Failed to extract text from document: {filename}")

        # To-Do: Implement actual parsing with LLM client
        # parsed_data = self.llm_client.parse_text(text, self.resume_prompt_template)
        logger.info("Stubbed: LLM parsing step skipped in ResumeParser.parse_resume_file_content.")
        # For now, return a stubbed Resume object, possibly populating a field with raw text for testing
        return Resume(summary="Resume parsing to be implemented.", raw_text=text[:2000]) # Truncate raw_text if needed


class JobParser(DocumentParser):
    """Parser for job description documents/text."""
    DEFAULT_JOB_PROMPT_TEMPLATE_FILE = "job_parser_prompt.md"

    def __init__(self, llm_client: ParserLLM, prompts_dir: Path = Path("app/prompts")):
        """Initialize the job parser.
        
        Args:
            llm_client: An instance of ParserLLM to use for parsing.
            prompts_dir: Directory where prompt templates are stored.
        """
        logger.info("Stubbed JobParser __init__ called.")
        self.llm_client = llm_client
        self.prompts_dir = prompts_dir
        self.job_prompt_template = self._load_prompt_template(self.DEFAULT_JOB_PROMPT_TEMPLATE_FILE)

    def _load_prompt_template(self, template_file_name: str) -> str:
        """Loads a prompt template from a file."""
        # To-Do: Implement actual file loading
        try:
            prompt_path = self.prompts_dir / template_file_name
            # with open(prompt_path, "r") as f: # This will be enabled post-stubbing
            #     return f.read()
            logger.info(f"Stubbed: Would load prompt from {prompt_path}")
            return f"To-Do: Load prompt from {template_file_name}"
        except FileNotFoundError:
            logger.error(f"Prompt template file not found: {template_file_name}")
            return "To-Do: Default fallback prompt if file not found."

    def parse_job_text(self, job_text: str) -> JobPosting:
        """Parse a job description text.

        Args:
            job_text: The job description text.

        Returns:
            A JobPosting object with the parsed data.
        """
        logger.info(f"JobParser.parse_job_text called for text: {job_text[:100]}...")
        if not job_text.strip():
            logger.warning("Job description text is empty.")
            return JobPosting(title="Empty job description provided.")

        # To-Do: Implement actual parsing with LLM client
        # parsed_data = self.llm_client.parse_text(job_text, self.job_prompt_template)
        logger.info("Stubbed: LLM parsing step skipped in JobParser.parse_job_text.")
        # For now, return a stubbed JobPosting object
        return JobPosting(title="Job parsing to be implemented.", description=job_text[:1000]) # Truncate desc if needed
