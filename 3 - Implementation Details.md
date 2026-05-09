# 🧩 Job Booster: Core Implementation Details

## 3.1. Core Service Integration ⚙️

Services are Python modules within `app/services/`, called directly by agents and API handlers:

* **`app/services/parsing_service.py`**:
  * `extract_text(file_content, filename)` — dispatcher by file extension
  * `extract_text_from_pdf()` — LiteParse primary, GLM-OCR fallback for scanned documents
  * `extract_text_from_docx()` — LiteParse primary, python-docx fallback
  * `_extract_latex_text()` — regex-based LaTeX command stripping
  * `ParserLLM` class — Pydantic AI agents for structured extraction (`Resume`, `JobPosting`)
  * `ResumeParser` / `JobParser` — high-level classes combining extraction + LLM parsing

* **`app/services/db_service.py`**:
  * `DatabaseService` class with SQLAlchemy session management
  * Full CRUD: `store_resume`, `store_job_posting`, `store_tailored_resume`, `store_analysis_result`
  * `get_resume_versions`, `get_active_version` for version management
  * `initialize_database_tables()` called at app startup via lifespan

* **`app/services/llm_service.py`**:
  * `LLMService` class wrapping LiteLLM
  * `generate()` — async completion with primary + fallback model
  * `generate_structured()` — adds JSON formatting instructions
  * Logfire callbacks configured at LiteLLM level

* **`app/services/scraper_service.py`**:
  * `BaseCareerScraper` ABC with `scrape_careers()` and `scrape_multiple()`
  * `TinyFishScraper` — cloud API, primary
  * `Crawl4AIScraper` — local Playwright, optional fallback
  * `get_scraper()` factory — TinyFish by default, Crawl4AI if `USE_CRAWL4AI=true`

## 3.2. Agent Intelligence & Orchestration 🤖🔥

* **Resume Tailor Agent** (`app/agents/resume_tailor.py`):
  * Pydantic AI Agent with `TailoredResumeOutput` typed output
  * `pydantic-graph` workflow: `ParseInput` → `GenerateTailored` → `ValidateOutput`
  * Graceful fallback to direct agent call if `pydantic-graph` unavailable
  * System prompt emphasizes truthfulness, keyword optimization, action verbs

* **Startup Scanner Agent** (`app/agents/startup_scanner.py`):
  * Pydantic AI Agent with `list[JobOpening]` typed output
  * Scrapes career pages via `get_scraper()`
  * Extracts jobs with relevance scoring (0.0–1.0)
  * Batch processing with state persistence (`ScannerState`)
  * Progress tracking across sessions

* **Prompt Engineering**: Templates in `app/prompts/` loaded at runtime, providing structured extraction instructions with field specifications.

## 3.3. API Layer 🌐

* **`app/api/resume_routes.py`**:
  * `POST /api/parse/resume` — upload file → extract → LLM parse → store → return `Resume`
  * `POST /api/parse/job` — text → LLM parse → store → return `JobPosting`
  * `POST /api/analyze` — file + job text → parse both → skill matching → return `AnalysisData`
  * `POST /api/tailor` — file + job text + format → graph workflow → return `TailoredResumeData`
  * `GET /api/resume-versions` — list stored versions
  * `GET /api/resume-versions/{id}` — get specific version

* **`app/api/scanner_routes.py`**:
  * `GET /api/scanner/startups` — list startups with filters
  * `GET /api/scanner/progress` — scanning progress
  * `POST /api/scanner/scan/batch` — scan batch synchronously
  * `POST /api/scanner/scan/background` — scan in background
  * `GET /api/scanner/jobs/top` — top jobs by relevance
  * `POST /api/scanner/reset` — reset state

## 3.4. Observability 🪵📚📡

* **Logfire** instrumented at LiteLLM level — success/failure callbacks in `app/core/llm_config.py`
* `logfire.span()` decorators in agents and services for request tracing
* **Loguru** for structured logging throughout
* Logfire auto-instruments FastAPI via `logfire.instrument_fastapi(app)`
* Tracing provides visibility into request handling, agent decision-making, service interactions, and errors

## 3.5. Document Processing Pipeline 📄⚙️

1. File upload → `extract_text(file_content, filename)` dispatcher
2. PDF → LiteParse (fast, spatial) → if empty → GLM-OCR (vision, handles scans)
3. DOCX → LiteParse → if fails → python-docx
4. LaTeX → regex stripping → plain text
5. MD / TXT → direct decode
6. Other formats → LiteParse (handles images, Office, etc.)
7. Extracted text → Pydantic AI agent → structured `Resume` / `JobPosting` model
8. Model → SQLite persistence via `DatabaseService`
