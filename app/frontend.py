"""Gradio UI for Job_Booster application."""

import os
import io
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import gradio as gr
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# API configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Configure logging
logger.info("Initializing Job_Booster UI")


def parse_resume(resume_file: str) -> Dict[str, str]:
    """Parse a resume file using the backend API.
    
    Args:
        resume_file: Path to the resume file.
        
    Returns:
        Structured resume data.
    """
    try:
        logger.info(f"Parsing resume: {resume_file} (stubbed)")
        # To-Do: Implement resume parsing logic by calling the backend API.
        # Placeholder for parsed data:
        return {
            "Name": "To-Do: Parsed Name",
            "Email": "To-Do: Parsed Email",
            "Phone": "To-Do: Parsed Phone",
            "Summary": "To-Do: Parsed Summary",
            "Skills": "To-Do: Skill1, Skill2",
            "Work Experience": "To-Do: Work Experience Details",
            "Education": "To-Do: Education Details",
            "Status": "Stubbed: Resume parsing not implemented"
        }
    except Exception as e:
        logger.error(f"Error in stubbed parse_resume: {e}")
        return {"Error": f"Error in stubbed parse_resume: {str(e)}"}


def parse_job(job_description: str) -> Dict[str, str]:
    """Parse a job description using the backend API.
    
    Args:
        job_description: Job description text.
        
    Returns:
        Structured job data.
    """
    try:
        logger.info("Parsing job description (stubbed)")
        # To-Do: Implement job description parsing logic by calling the backend API.
        # Placeholder for parsed data:
        return {
            "Title": "To-Do: Parsed Title",
            "Company": "To-Do: Parsed Company",
            "Location": "To-Do: Parsed Location",
            "Required Skills": "To-Do: SkillA, SkillB",
            "Description": "To-Do: Parsed Job Description",
            "Status": "Stubbed: Job parsing not implemented",
            "_raw_data": {} # Keep for analyze_resume_job_match compatibility
        }
    except Exception as e:
        logger.error(f"Error in stubbed parse_job: {e}")
        return {"Error": f"Error in stubbed parse_job: {str(e)}"}


def analyze_resume_job_match(
    resume_file: str,
    job_description: str
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """Analyze the match between a resume and job description.
    
    Args:
        resume_file: Path to the resume file.
        job_description: Job description text.
        
    Returns:
        A tuple of (match details, resume data, job data).
    """
    try:
        logger.info("Analyzing resume-job match (stubbed)")
        # To-Do: Implement resume-job match analysis by calling the backend API.
        # This would involve calling parse_resume and parse_job (or their stubs)
        # and then the analysis endpoint.
        
        # Placeholder return values:
        parsed_resume_stub = parse_resume(resume_file) # Use stubbed version
        parsed_job_stub = parse_job(job_description)   # Use stubbed version
        
        match_details_stub = {
            "Overall Match Score": "To-Do: Score %",
            "Strengths": "To-Do: List strengths",
            "Areas for Improvement": "To-Do: List areas for improvement",
            "Status": "Stubbed: Analysis not implemented"
        }
        return match_details_stub, parsed_resume_stub, parsed_job_stub
    except Exception as e:
        logger.error(f"Error in stubbed analyze_resume_job_match: {e}")
        return (
            {"Error": f"Error in stubbed analyze_resume_job_match: {str(e)}"},
            {"Error": "Resume parsing failed in stub"},
            {"Error": "Job parsing failed in stub"}
        )


def generate_tailored_resume(
    resume_file: str,
    job_description: str,
    format_type: str
) -> Tuple[Union[str, Path], Dict[str, str], Dict[str, str], Dict[str, str]]: # Adjusted Union for Path
    """Generate a tailored resume based on a resume and job description.
    
    Args:
        resume_file: Path to the resume file.
        job_description: Job description text.
        format_type: Output format type.
        
    Returns:
        A tuple of (tailored resume content or path, match details, resume data, job data).
    """
    try:
        logger.info(f"Generating tailored resume (stubbed) for format: {format_type}")
        # To-Do: Implement tailored resume generation logic by calling the backend API.
        # This would involve calling parse_resume, parse_job, analysis (or their stubs)
        # and then the tailoring endpoint.
        
        # Placeholder return values:
        match_details_stub, parsed_resume_stub, parsed_job_stub = analyze_resume_job_match(resume_file, job_description)
        
        tailored_resume_content_stub = f"To-Do: Tailored resume content for {format_type} format. \nBased on {Path(resume_file).name} and provided job description."
        
        # If format_type implies a file, return a placeholder path or string
        if format_type.lower() in ["pdf", "docx"]:
            # For simplicity, returning a string message instead of a dummy file path
            # In a real stub, you might create a dummy temp file if Gradio expects a Path object
            output_content_stub = f"To-Do: Path to {format_type.lower()} file will be here: tailored_resume_stub.{format_type.lower()}"
        else:
            output_content_stub = tailored_resume_content_stub
            
        return output_content_stub, match_details_stub, parsed_resume_stub, parsed_job_stub
    except Exception as e:
        logger.error(f"Error in stubbed generate_tailored_resume: {e}")
        return (
            f"Error in stubbed generate_tailored_resume: {str(e)}",
            {"Error": "Analysis failed in stub"},
            {"Error": "Resume parsing failed in stub"},
            {"Error": "Job parsing failed in stub"}
        )


# Create the Gradio interface
with gr.Blocks(title="Job_Booster - Resume Tailoring Assistant") as app:
    gr.Markdown(
        """
        # 🚀 Job_Booster
        ### AI-Powered Resume Tailoring Assistant
        
        Upload your resume and a job description to get a tailored resume optimized for the specific job.
        """
    )
    
    with gr.Tabs():
        # Tab 1: Resume Parser
        with gr.TabItem("Parse Resume"):
            with gr.Row():
                with gr.Column():
                    resume_input = gr.File(label="Upload Resume (PDF, DOCX, or TXT)")
                    parse_resume_button = gr.Button("Parse Resume")
                
                with gr.Column():
                    resume_output = gr.JSON(label="Parsed Resume Data")
            
            parse_resume_button.click(
                fn=parse_resume,
                inputs=[resume_input],
                outputs=[resume_output]
            )
        
        # Tab 2: Job Description Parser
        with gr.TabItem("Parse Job Description"):
            with gr.Row():
                with gr.Column():
                    job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10
                    )
                    parse_job_button = gr.Button("Parse Job Description")
                
                with gr.Column():
                    job_output = gr.JSON(label="Parsed Job Data")
            
            parse_job_button.click(
                fn=parse_job,
                inputs=[job_input],
                outputs=[job_output]
            )
        
        # Tab 3: Resume-Job Analysis
        with gr.TabItem("Analyze Match"):
            with gr.Row():
                with gr.Column():
                    analysis_resume_input = gr.File(label="Upload Resume (PDF, DOCX, or TXT)")
                    analysis_job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10
                    )
                    analyze_button = gr.Button("Analyze Match")
                
                with gr.Column():
                    match_output = gr.JSON(label="Match Analysis")
                    analysis_resume_output = gr.JSON(label="Resume Data")
                    analysis_job_output = gr.JSON(label="Job Data")
            
            analyze_button.click(
                fn=analyze_resume_job_match,
                inputs=[analysis_resume_input, analysis_job_input],
                outputs=[match_output, analysis_resume_output, analysis_job_output]
            )
        
        # Tab 4: Tailor Resume
        with gr.TabItem("Tailor Resume"):
            with gr.Row():
                with gr.Column():
                    tailor_resume_input = gr.File(label="Upload Resume (PDF, DOCX, or TXT)")
                    tailor_job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10
                    )
                    format_input = gr.Radio(
                        label="Output Format",
                        choices=["text", "html", "docx", "pdf"],
                        value="text"
                    )
                    tailor_button = gr.Button("Generate Tailored Resume")
                
                with gr.Column():
                    tailor_output = gr.Textbox(
                        label="Tailored Resume",
                        lines=20
                    )
                    tailor_match_output = gr.JSON(label="Match Analysis")
                    tailor_resume_output = gr.JSON(label="Resume Data")
                    tailor_job_output = gr.JSON(label="Job Data")
            
            tailor_button.click(
                fn=generate_tailored_resume,
                inputs=[tailor_resume_input, tailor_job_input, format_input],
                outputs=[tailor_output, tailor_match_output, tailor_resume_output, tailor_job_output]
            )
    
    gr.Markdown(
        """
        ## How It Works
        1. **Parse Resume**: Upload your resume to extract structured information
        2. **Parse Job Description**: Enter a job description to extract key requirements
        3. **Analyze Match**: Compare your resume against the job description
        4. **Tailor Resume**: Generate an optimized version of your resume for the job
        
        Powered by AI agents using Google ADK and Google Gemini 🧠✨
        """
    )


# Launch the app
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=8050)
