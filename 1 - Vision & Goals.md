# 🚀 Job_Booster: Project Vision, Goals & Technology Foundation (MVP Refactor)

## 1.1 Introduction: Why This Approach?

In today's competitive job market, tailoring applications is crucial but time-consuming. Job_Booster aims to automate and significantly enhance this process by intelligently leveraging a user's entire work history. For the Minimum Viable Product (MVP), we are adopting a **streamlined, integrated agentic architecture** built around a single FastAPI application with a Gradio UI. This approach offers:

* **Modularity:** Core functionalities (parsing, LLM interaction, database management) are encapsulated in distinct service modules within the application, promoting separation of concerns.
* **Simplified Development & Deployment:** A single application is easier to develop, debug, test, and deploy compared to a distributed system of microservices, especially for an MVP.
* **Maintainability:** Clear internal interfaces between components (API layer, agents, services) facilitate easier updates and modifications.

This plan outlines the development of Job_Booster, focusing on delivering a powerful, AI-driven assistant for job seekers within this consolidated structure.

## 1.2 Core Project Goals 🎯

The primary objective is to transform a user's collection of past resumes and a target job description into a highly optimized application package. (Note: The following goals outline the target functionality; current implementations are foundational and in a "To-Do" state for progressive development.)

1. **Intelligent Input Processing 📄➡️🧱:**
    * Reliably parse resumes and job descriptions from various formats (PDF, DOCX, plain text, URLs), including handling scanned documents via OCR using `app/services/parsing_service.py`.
    * Extract structured information (contact details, education, experience, skills, projects, job requirements) via the `parsing_service` (which may leverage an LLM service).
    * Persist this structured data using the `app/services/db_service.py` for efficient querying and retrieval by agents.

2. **Knowledge Base Construction & Enrichment (Simplified for MVP) 🧠:**
    * Identify key entities (Skills, Technologies, Companies, Job Titles, Project Names, Requirements) within parsed documents.
    * Store these entities and their relationships in the SQLite database via `db_service.py`. For the MVP, a full-fledged graph database might be deferred in favor of structured relational storage that can still capture essential connections.
    * This creates a rich representation of the user's history and the job's demands.

3. **Context-Aware Resume Synthesis ✨📄:**
    * Analyze the target job description's requirements against the user's profile (from `db_service.py`).
    * Identify the most relevant skills, experiences, and projects.
    * Instruct the `app/services/llm_service.py` (providing rich context from the `db_service`) to generate a *new, cohesive, tailored resume* optimized for the specific job, adhering to Pydantic models defined in `app/models/resume_model.py` and `app/models/job_model.py`.

4. **Multi-faceted Matching Analysis 📊:**
    * Generate embeddings for the synthesized resume and job description using `llm_service.py` (or a dedicated embedding function within it).
    * Perform vector similarity search (using vector indexes stored as files or within SQLite if feasible for MVP scale) for a quantitative match score.
    * Leverage the structured data in `db_service.py` and LLM analysis via `llm_service.py` to identify explicit skill/requirement matches.

5. **Actionable Feedback & Gap Analysis 💡:**
    * Go beyond a simple score. Use data from `db_service.py` and the `llm_service.py` to:
        * Pinpoint specific skills mentioned in the job description but missing or underrepresented in the synthesized resume.
        * Suggest rephrasing certain experiences to better align with job keywords/responsibilities.

6. **Personalized Cover Letter Generation ✍️:**
    * Use the synthesized resume and job description details, along with insights from the analysis phase, to prompt the `llm_service.py` to generate a compelling, personalized cover letter.

## 1.3 Technology Stack Rationale (MVP Refactor) 💻

The chosen technologies form a cohesive ecosystem for building this integrated application:

* **FastAPI 🚀:** Excellent for building the high-performance async API for the entire Job_Booster application. Its Pydantic integration simplifies data validation.
* **Pydantic ✅:** Provides robust data validation and settings management, crucial for defining reliable data structures (`app/models/`) and API contracts.
* **Google ADK 🤖:** The framework to structure the reasoning and state management of the agents within `app/agents/`. This helps in organizing complex LLM-driven workflows with Google Gemini.
* **Internal Service Modules (`app/services/`)**: Core functionalities like parsing, database interaction, and LLM communication are implemented as internal Python modules/classes within the FastAPI application. This simplifies architecture for the MVP.
  * `db_service.py`: Manages all database operations (CRUD) for SQLite using SQLAlchemy.
  * `llm_service.py`: Abstracts communication with the chosen LLM (Google Gemini via Google ADK).
  * `parsing_service.py`: Handles extraction of text and structured data from resumes and job descriptions (PDF, DOCX, TXT, potentially with OCR).
* **SQLAlchemy & SQLite 🗄️:** Provide the ORM and database engine for persistent storage, accessed via `app/services/db_service.py`.
* **Logfire 🪵 & OpenTelemetry 📡:** Essential for observability. Configured within the single FastAPI application (`app/main.py`) to trace requests and monitor performance.
* **Docker & Docker Compose 🐳:** Useful for creating a consistent development environment and for packaging the application and its database (if needed) for deployment.
* **Git & CI/CD (GitHub Actions) 🐙⚙️:** Standard tools for version control, automated testing, and deployment pipelines.
* **`pip` 📦:** Python package management for the project's single `requirements.txt`.
