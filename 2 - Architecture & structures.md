# 🏗️ Job_Booster: Detailed Architecture & System Structure (MVP Refactor)

## 2.1 System Components & Responsibilities (Simplified MVP) 🗺️

For the Minimum Viable Product (MVP), the architecture is consolidated into a single FastAPI application. This simplifies deployment and development while retaining a logical separation of concerns internally.

1. **Job_Booster Application (FastAPI):**
    * **Role:** The unified application handling all user requests, business logic, data processing, and UI interactions (if Gradio is served via FastAPI).
    * **Key Internal Modules (within `app/` directory):**
        * `main.py`: 🚀 FastAPI application entry point, global configurations, startup/shutdown events, and mounting of API routers. May also serve the Gradio UI if integrated.
        * `frontend.py`: 🎨 Gradio user interface definition and logic (if run as part of the FastAPI app or as a separate process pointing to the API).
        * `agents/`: 🤖 Contains the core business logic and intelligent processing (e.g., `resume_tailor.py`). This is where complex workflows like parsing orchestration, resume tailoring, and analysis generation are implemented. Logic previously in separate Pydantic-AI agents is now directly integrated here.
        * `services/`: 🛠️ Provides specialized functionalities previously envisioned as separate MCP servers. These are now Python modules/classes directly called by agents or API handlers.
            * `parsing_service.py`: Handles text extraction from documents (PDF, DOCX) and uses LLM capabilities for structuring the extracted data.
            * `db_service.py`: Manages interactions with the SQLite database. Handles data storage, retrieval, and schema management.
            * `llm_service.py`: Abstracts LLM interactions, using Google ADK for Google Gemini.
        * `core/`: ⚙️ Handles application-wide concerns like loading configuration (`config.py`), setting up logging, and defining shared utilities or exception handling.
        * `models/`: 📝 Defines Pydantic models for various purposes:
            * `api_models.py`: Request/response schemas for the FastAPI endpoints.
            * `job_model.py`, `resume_model.py`: Core business objects (e.g., `Resume`, `JobPosting` - these were previously in `common/src/common/models/`).
            * `db_models.py`: SQLAlchemy models for database tables (previously `sqlite_tables.py` in `common`).
        * `prompts/`: 📄 Stores prompt templates for LLM interactions.

2. **Data Storage:**
    * **SQLite Database File:** A persistent file (e.g., `job_booster.db`) accessed directly by `app/services/db_service.py` using SQLAlchemy. Stores structured data from parsed documents, user information, etc.
    * *(For MVP, vector indexes will be stored as files or within SQLite if feasible for scale).*

## 2.2 Communication Flow & Protocols (Simplified MVP) ↔️

* **User Interaction:** Standard HTTPS requests to the FastAPI application's API endpoints.
* **Internal Communication:** Direct Python function/method calls between components within the `app` module. For instance:
  * An API handler in `app/main.py` (or a router) might call a method in an agent in `app/agents/resume_tailor.py`.
  * The agent would then call methods in `app/services/parsing_service.py` to get data, `app/services/llm_service.py` for AI processing, and `app/services/db_service.py` to store/retrieve results.
* **Direct Function Calls for Core MVP Features:** Core functionalities are implemented as internal Python modules/classes, allowing direct function calls between components.
* **Data Format:** Data is passed as Python objects (instances of Pydantic models defined in `app/models/`).
* **Error Handling:** Standard Python exception handling within the application.
* **Tracing:** OpenTelemetry can be configured in `app/main.py` to trace requests and internal calls across the application components.

## 2.3 Observability Strategy (Simplified MVP) 🕵️‍♀️

* **Logging:** Standard Python logging (`loguru` or `logging` module) configured in `app/core/config.py` or `app/main.py`.
* **Tracing (Optional but Recommended):** OpenTelemetry configured in `app/main.py` for the FastAPI application. This will provide insights into request flows and performance of different internal services.
* **Metrics (Optional):** Prometheus metrics can be exposed by the FastAPI application if needed, using libraries like `starlette-exporter`.

## 2.4 Detailed Project File Structure (MVP Refactor) 📁

```plaintext
Job_Booster/
├── app/                      # Main application source code
│   ├── __init__.py
│   ├── main.py               # FastAPI app definition, startup, routers, and OTel/Logfire setup
│   ├── frontend.py           # Gradio UI app (if served by FastAPI or run standalone)
│   ├── agents/               # Business logic, agent implementations
│   │   ├── __init__.py
│   │   └── resume_tailor.py  # Core agent logic for resume tailoring, analysis, etc.
│   ├── core/                 # Core components like config, logging setup
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models/               # Pydantic and SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── api_models.py     # Pydantic models for API request/response
│   │   ├── job_model.py      # Pydantic models for Job
│   │   ├── resume_model.py   # Pydantic models for Resume
│   │   └── db_models.py      # SQLAlchemy models for database tables
│   ├── services/             # Service layer for parsing, DB, LLM interaction
│   │   ├── __init__.py
│   │   ├── db_service.py      # For database interactions (SQLite via SQLAlchemy)
│   │   ├── llm_service.py     # For interacting with LLMs (Google Gemini via ADK)
│   │   └── parsing_service.py # For document parsing (text, PDF, DOCX, OCR)
│   ├── prompts/              # LLM Prompts (e.g., job_parser_prompt.md, resume_parser_prompt.md)
│   │   └── __init__.py
├── data/                     # Local data like SQLite DB file (e.g., job_booster.db), sample files for testing
├── scripts/                  # Utility scripts
│   └── run_app.py            # Script to run the main FastAPI application
├── tests/                    # Automated tests
│   ├── __init__.py
│   ├── test_api.py           # Tests for FastAPI endpoints in app/main.py or its routers
│   ├── test_agents.py        # Tests for logic in app/agents/
│   ├── test_services.py      # Unit tests for app/services/
│   └── test_models.py        # Tests for Pydantic/SQLAlchemy models in app/models/
├── .env.example              # Example environment variables
├── .gitignore
├── 1 - Vision & Goals.md
├── 2 - Architecutre & structures.md # This file
├── 3 - Implementation Details.md
├── Hackathon_MVP_Plan.md
├── LICENSE
├── README.md
├── requirements.txt          # Python dependencies for the entire project
└── docker-compose.yml        # (Optional for MVP) If containerization is still desired for the single app + DB
└── Dockerfile                # (Optional for MVP) To build the Job_Booster app container
```

This revised structure centralizes the application logic, making it easier to manage for the MVP scope, while still allowing for logical separation of concerns within the `app` directory. Future expansion to a more distributed model can build upon these well-defined internal services.
