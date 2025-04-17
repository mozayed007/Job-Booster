# 🚀 Job_Booster: Project Vision, Goals & Technology Foundation

## 1.1 Introduction: Why This Approach?

In today's competitive job market, tailoring applications is crucial but time-consuming. Job_Booster aims to automate and significantly enhance this process by intelligently leveraging a user's entire work history. Traditional methods often involve manually copying and pasting, leading to inconsistencies and missed opportunities. This project employs a **modern, distributed agentic architecture** using the **Model-Context-Protocol (MCP) Server pattern**. This approach offers several advantages:

* **Modularity & Reusability:** Common tasks (fetching data, interacting with LLMs, managing memory) are handled by specialized, potentially reusable microservices (MCP Servers).
* **Scalability:** Individual components can be scaled independently based on load.
* **Maintainability:** Decouples complex agent reasoning logic from the implementation details of specific tools.
* **Standardization:** Encourages consistent interaction patterns via the MCP protocol and the Python SDK.

This plan outlines the development of Job_Booster, focusing on delivering a powerful, AI-driven assistant for job seekers.

## 1.2 Core Project Goals 🎯

The primary objective is to transform a user's collection of past resumes and a target job description into a highly optimized application package.

1. **Intelligent Input Processing 📄➡️🧱:**
    * Reliably parse resumes and job descriptions from various formats (PDF, DOCX, plain text, URLs), including handling scanned documents via OCR.
    * Extract structured information (contact details, education, experience, skills, projects, job requirements).
    * Persist this structured data using the `sqlite` MCP server for efficient querying and retrieval by agents.

2. **Knowledge Graph Construction & Enrichment 🧠:**
    * Identify key entities (Skills, Technologies, Companies, Job Titles, Project Names, Requirements) and their relationships within the parsed documents.
    * Populate the `memory` (Knowledge Graph) MCP server with these entities and relationships (e.g., `[Skill: Python] <-used_in- [Project: Data Analysis Pipeline] ->at-> [Company: XYZ Corp]`).
    * This creates a rich, interconnected representation of the user's history and the job's demands, enabling deeper analysis than simple keyword matching.

3. **Context-Aware Resume Synthesis ✨📄:**
    * Analyze the target job description's requirements against the user's comprehensive profile stored in the SQLite DB and Knowledge Graph.
    * Identify the most relevant skills, experiences, and projects from *across all* provided source resumes, potentially resolving conflicts or outdated information.
    * Instruct the `llm` MCP server (providing rich context from the KG/DB) to generate a *new, cohesive, tailored resume* optimized for the specific job, adhering to the `Resume` Pydantic model.

4. **Multi-faceted Matching Analysis 📊:**
    * Generate embeddings for the synthesized resume and job description using the `embed` MCP server.
    * Perform vector similarity search (using `vector-memory` or direct DB access) for a quantitative match score.
    * Leverage the Knowledge Graph to identify explicit skill/requirement matches or near-matches.

5. **Actionable Feedback & Gap Analysis 💡:**
    * Go beyond a simple score. Use the KG and `llm` server to:
        * Pinpoint specific skills mentioned in the job description but missing or underrepresented in the synthesized resume.
        * Suggest rephrasing certain experiences to better align with job keywords/responsibilities.
        * Recommend types of personal projects or online courses that could bridge identified skill gaps, based on connections in the KG.

6. **Personalized Cover Letter Generation ✍️:**
    * Use the synthesized resume and job description details, along with insights from the analysis phase, to prompt the `llm` server to generate a compelling, personalized cover letter.

## 1.3 Technology Stack Rationale 💻

The chosen technologies form a cohesive ecosystem for building this distributed agentic system:

* **FastAPI 🚀:** Excellent for building high-performance async APIs (Backend Gateway, Custom Servers, *and potentially Standard Servers if run via Python*). Its Pydantic integration simplifies data validation.
* **Pydantic ✅:** Provides robust data validation and settings management, crucial for defining reliable data structures (`common/models`) and API contracts.
* **Pydantic-AI 🤖:** A framework for structuring the reasoning and state management of the agents hosted within the backend.
* **`modelcontextprotocol/python-sdk` 🐍:** The standardized bridge for communication. Ensures agents interact with all MCP servers consistently, simplifying development and potentially managing complexities like authentication and tracing.
* **MCP Servers (`fetch`🌐, `browser`🕸️, `llm`💬, `embed`📐, `sqlite`🗄️, `memory`🧠, `vector-memory`📉):** Provide essential, decoupled functionalities. **[Update] These standard servers will be sourced (e.g., via Git submodule or package installation) and launched as individual Python processes managed by a central script.** This requires careful dependency management.
* **Custom `mcp-parser-server` 🧩:** Necessary for specialized parsing. Built as a distinct FastAPI application, likely containerized for consistency.
* **Data Storage Backends (SQLite, KG, Vector):** Chosen to support different data types and query patterns. Accessed via the respective MCP servers.
* **Logfire 🪵 & OpenTelemetry 📡:** Essential for observability. **[Update] Configuration needed for the Backend, Custom Parser, *and each standard server process* launched via Python.**
* **Python Process Management (`multiprocessing`, `honcho`, `supervisor`):** ⚙️ **[New] Libraries/tools needed to launch, manage, and monitor the multiple standard MCP server Python processes.**
* **Docker & Docker Compose 🐳:** **[Update] Primarily used for the custom parser server, database backends (if run locally), and potentially for orchestrating the overall development environment (including the Python script that launches other servers), though less central for running the standard MCP servers themselves.**
* **Git & CI/CD (GitHub Actions) 🐙⚙️:** Standard tools for version control, automated testing, and deployment pipelines (deployment strategy needs adjustment for Python processes).
* **`uv` / `pip` 📦:** Modern, fast Python package management (**[Update] Dependency conflicts across servers are a significant risk**).
