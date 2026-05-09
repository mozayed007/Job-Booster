# 🏗️ Job_Booster: Architecture & System Structure

## 2.1 System Components & Responsibilities 🗺️

The application is a single FastAPI backend with modular internal services, a Gradio web frontend, and Pydantic AI agents for intelligent document processing and job scanning.

### Core Modules (within `app/`)

| Module | File(s) | Responsibility |
|--------|---------|----------------|
| **Entry** | `main.py` | FastAPI app, lifespan events, router mounting, CORS |
| **Frontend** | `frontend.py` | Gradio 5-tab UI, communicates with API via httpx |
| **Agents** | `agents/resume_tailor.py` | Pydantic AI agent + pydantic-graph workflow for resume tailoring |
| | `agents/startup_scanner.py` | Pydantic AI agent for extracting job postings from startup pages |
| **API** | `api/resume_routes.py` | `POST /parse/resume`, `/parse/job`, `/analyze`, `/tailor` |
| | `api/scanner_routes.py` | `GET/POST /scanner/*`, `/jobs/top`, `/progress` |
| **Core** | `core/config.py` | pydantic-settings, environment variable loading |
| | `core/llm_config.py` | LiteLLM + Logfire configuration |
| **Models** | `models/base_model.py` | `JobBoosterBase` (UUID PK), `BaseResponse` |
| | `models/resume_model.py` | `Resume`, `ContactInfo`, `Education`, `WorkExperience`, `Skill` |
| | `models/job_model.py` | `JobPosting`, `CompanyInfo`, `Requirement`, `Responsibility`, `Benefit` |
| | `models/api_models.py` | Request/response DTOs for all endpoints |
| | `models/db_models.py` | SQLAlchemy tables (`ResumeDB`, `JobPostingDB`, `ResumeVersionDB`) |
| | `models/startup_model.py` | `Startup`, `JobOpening`, `ScannerState` |
| **Prompts** | `prompts/resume_parser_prompt.md` | Prompt for resume document structuring |
| | `prompts/job_parser_prompt.md` | Prompt for job posting extraction |
| **Services** | `services/parsing_service.py` | LiteParse (PDF/DOCX/image) + GLM-OCR + python-docx + LaTeX |
| | `services/db_service.py` | SQLAlchemy CRUD via `DatabaseService` class |
| | `services/llm_service.py` | LiteLLM async completion with provider fallback chains |
| | `services/scraper_service.py` | TinyFish (primary) + Crawl4AI (fallback) scraper factory |
| | `services/career_scraper.py` | Crawl4AI implementation (backward compatibility) |
| | `services/startup_parser.py` | Markdown parser for `startups.md` database |
| **UI** | `ui/scanner_tab.py` | Gradio scanner tab component |

### Data Storage

* **SQLite** via SQLAlchemy — stores parsed resumes, job postings, resume versions, and scan state.
* **`data/resumes/`** — sample resumes (PDF, DOCX, MD, TXT, TEX) for testing.
* **`data/startups/startups.md`** — curated startup/company database consumed by the scanner.

## 2.2 Communication Flow & Protocols ↔️

```
User → Gradio UI → httpx → FastAPI endpoints → Agents → Services → DB / LLM
```

* **Frontend ↔ Backend:** Gradio UI calls FastAPI endpoints over HTTP using `httpx`. The UI runs as a separate process (or co-located) and communicates with the API layer.
* **API → Agents:** Route handlers invoke Pydantic AI agents directly via Python function calls. Agents return structured Pydantic model instances.
* **Agents → Services:** Agents call service-layer methods (parsing, LLM, scraping, DB) as direct Python calls. All inter-module data is passed as typed Pydantic models.
* **Services → External:** Services interact with external systems — LiteLLM for LLM providers, LiteParse/GLM-OCR for document parsing, TinyFish/Crawl4AI for scraping, SQLite for persistence.
* **Error Handling:** Standard Python exception handling with structured logging via loguru. API errors surface as FastAPI `HTTPException` with typed error responses.

## 2.3 Observability Strategy 🕵️‍♀️

* **Logfire** is instrumented at the LiteLLM level with success/failure callbacks, providing per-request tracing of LLM calls (latency, token usage, errors).
* **Logfire spans** are placed in agents and services for distributed tracing across the full request lifecycle.
* **loguru** provides structured application logging (parsing events, DB operations, scraper activity).
* All observability is configured in `core/llm_config.py` and initialized at app startup in `main.py`.

## 2.4 Detailed Project File Structure 📁

```plaintext
Job_Booster/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, lifespan, routers, CORS
│   ├── frontend.py           # Gradio UI (5 tabs)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── resume_tailor.py  # Pydantic AI agent + pydantic-graph workflow
│   │   └── startup_scanner.py # Pydantic AI agent for job extraction
│   ├── api/
│   │   ├── __init__.py
│   │   ├── resume_routes.py  # POST /parse/resume, /parse/job, /analyze, /tailor
│   │   └── scanner_routes.py # GET/POST /scanner/*, /jobs/top, /progress
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # pydantic-settings, env loading
│   │   └── llm_config.py     # LiteLLM + Logfire configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_model.py     # JobBoosterBase (UUID), BaseResponse
│   │   ├── resume_model.py   # Resume, ContactInfo, Education, WorkExperience, Skill, etc.
│   │   ├── job_model.py      # JobPosting, CompanyInfo, Requirement, Responsibility, Benefit
│   │   ├── api_models.py     # Request/response DTOs
│   │   ├── db_models.py      # SQLAlchemy tables (ResumeDB, JobPostingDB, ResumeVersionDB, etc.)
│   │   └── startup_model.py  # Startup, JobOpening, ScannerState
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── resume_parser_prompt.md
│   │   └── job_parser_prompt.md
│   ├── services/
│   │   ├── __init__.py
│   │   ├── parsing_service.py  # LiteParse + GLM-OCR + python-docx + LaTeX
│   │   ├── db_service.py       # SQLAlchemy CRUD (DatabaseService class)
│   │   ├── llm_service.py      # LiteLLM async completion with fallback
│   │   ├── scraper_service.py  # TinyFish (primary) + Crawl4AI (fallback) factory
│   │   ├── career_scraper.py   # Crawl4AI implementation (backward compat)
│   │   └── startup_parser.py   # Markdown parser for startups.md
│   └── ui/
│       └── scanner_tab.py    # Gradio scanner tab component
├── data/
│   ├── resumes/              # Sample resumes (PDF, DOCX, MD, TXT, TEX)
│   └── startups/             # startups.md database
├── scripts/
│   └── run_app.py            # Server launcher with dependency checks
├── tests/
│   ├── test_resume_models.py
│   ├── test_job_models.py
│   ├── test_api.py
│   └── test_startup_scanner.py
├── pyproject.toml
├── .env.example
└── .gitignore
```

## 2.5 Technology Stack 🧰

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | FastAPI | Async API, Pydantic integration |
| Frontend | Gradio | 5-tab web UI |
| Agents | Pydantic AI | Type-safe LLM agents with structured output |
| Workflows | pydantic-graph | Typed graph state machines |
| LLM | LiteLLM | Multi-provider (100+ models), fallback chains |
| Parsing | LiteParse | Fast PDF/DOCX/image parsing (Node.js CLI) |
| OCR | GLM-OCR | Vision-based OCR for scanned documents |
| Scraping | TinyFish + Crawl4AI | Career page scraping |
| Database | SQLAlchemy + SQLite | ORM, persistence |
| Observability | Logfire | Tracing, logging |
| Config | pydantic-settings | Environment management |
