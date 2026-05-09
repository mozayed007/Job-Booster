# Job_Booster — Technical Architecture

## High-Level Architecture

```
                           ┌─────────────────────────────┐
                           │       Gradio UI (8050)       │
                           │     app/frontend.py          │
                           └──────────────┬───────────────┘
                                          │ HTTP
                           ┌──────────────▼───────────────┐
                           │     FastAPI Application       │
                           │        app/main.py            │
                           │                              │
                           │  ┌───────────────────────┐   │
                           │  │    API Routes (7)      │   │
                           │  │  app/api/*.py          │   │
                           │  └───────────┬───────────┘   │
                           │              │               │
                           │  ┌───────────▼───────────┐   │
                           │  │    AI Agents (3)       │   │
                           │  │  app/agents/*.py       │   │
                           │  └───────────┬───────────┘   │
                           │              │               │
           ┌───────────────┼──────────────┼───────────────┼───────────────┐
           │               │              │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ LLM Service │ │ Parse Svc   │ │ DB Svc   │ │ Vector Store│ │ Scraper Svc │
    │ (LiteLLM)   │ │(LiteParse/  │ │(SQLAlch.)│ │  (Qdrant)   │ │(TinyFish/   │
    │             │ │ GLM-OCR)    │ │          │ │             │ │ Crawl4AI)   │
    └──────┬──────┘ └─────────────┘ └────┬─────┘ └──────┬──────┘ └─────────────┘
           │                             │               │
    ┌──────▼──────┐               ┌──────▼──────┐ ┌──────▼──────┐
    │  LiteLLM    │               │   SQLite    │ │  Qdrant     │
    │  Providers  │               │  (file DB)  │ │  (file DB)  │
    │ (100+ LLMs) │               │             │ │             │
    └─────────────┘               └─────────────┘ └─────────────┘
```

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Web Framework | FastAPI | 0.115+ |
| AI Agents | Pydantic AI + pydantic-graph | 0.2+ |
| LLM Router | LiteLLM | 1.30+ |
| Vector DB | Qdrant (file-based) | 1.12+ |
| ORM | SQLAlchemy | 2.0+ |
| Frontend | Gradio | 5.0+ |
| Document Parsing | LiteParse (LlamaIndex) | 1.0+ |
| OCR | GLM-OCR | 0.1+ |
| Web Scraping | TinyFish + Crawl4AI | 0.1+ / 0.8+ |
| Auth | bcrypt + python-jose (JWT) | 4.0+ / 3.3+ |
| Observability | Logfire | 0.40+ |
| Config | pydantic-settings | 2.0+ |
| Linting | Ruff | 0.3+ |

## Module Structure

```
app/
├── core/                    # Configuration and LLM setup
│   ├── config.py            # pydantic-settings Settings singleton
│   ├── llm_config.py        # Backward-compat re-exports from model_registry
│   └── model_registry.py    # ModelRegistry singleton, provider detection, fallback chains
│
├── models/                  # Pydantic and SQLAlchemy models
│   ├── api_models.py        # Request/response models for API endpoints
│   ├── base_model.py        # Shared base Pydantic models
│   ├── db_models.py         # SQLAlchemy table definitions (11 tables)
│   ├── job_model.py         # Job description Pydantic model
│   ├── resume_model.py      # Resume Pydantic model
│   └── startup_model.py     # Startup and JobOpening Pydantic models
│
├── services/                # Business logic layer
│   ├── analytics_service.py # Dashboard and statistics aggregation
│   ├── auth_service.py      # bcrypt hashing, JWT token creation/validation
│   ├── career_scraper.py    # Career page scraping logic
│   ├── db_service.py        # SQLAlchemy session management and CRUD
│   ├── embedding_service.py # LiteLLM embedding generation with hash fallback
│   ├── export_service.py    # Multi-format export (text, HTML, DOCX, PDF)
│   ├── llm_service.py       # LiteLLM integration
│   ├── parsing_service.py   # LiteParse + GLM-OCR document parsing
│   ├── recommendation_service.py # Job/resume recommendations via vector search
│   ├── scraper_service.py   # Web scraping orchestration
│   ├── search_service.py    # Hybrid search (vector + keyword)
│   ├── startup_parser.py    # Startup listing extraction from markdown
│   ├── template_engine.py   # Jinja2 LaTeX template rendering
│   ├── tracking_service.py  # Application status lifecycle management
│   └── vector_store.py      # Qdrant file-based vector storage (singleton)
│
├── agents/                  # Pydantic AI agent definitions
│   ├── cover_letter.py      # Cover letter generation agent
│   ├── resume_tailor.py     # Resume tailoring agent (pydantic-graph)
│   └── startup_scanner.py   # Startup career page scanning agent
│
├── api/                     # FastAPI route modules
│   ├── analytics_routes.py  # /api/analytics/*
│   ├── auth_routes.py       # /api/auth/*
│   ├── recommendation_routes.py # /api/recommendations/*
│   ├── resume_routes.py     # /api/parse/*, /api/analyze, /api/tailor, /api/export
│   ├── scanner_routes.py    # /api/scanner/*
│   ├── search_routes.py     # /api/search/*
│   └── tracking_routes.py   # /api/applications/*
│
├── middleware/               # FastAPI middleware
│   └── auth_middleware.py   # JWT token extraction dependency
│
├── prompts/                 # LLM prompt templates (Markdown)
│   ├── cover_letter_prompt.md
│   ├── job_parser_prompt.md
│   └── resume_parser_prompt.md
│
├── ui/                      # Gradio tab modules
│   └── scanner_tab.py       # Startup scanner tab component
│
├── frontend.py              # Gradio UI application (6 tabs)
└── main.py                  # FastAPI entry point, router mounting, lifespan
```

## Data Flow

### Resume Upload and Parsing

```
User uploads file (PDF/DOCX/MD/TXT/TEX)
    │
    ▼
extract_text() — LiteParse for PDF/DOCX, GLM-OCR for scanned images
    │
    ▼
ResumeParser.parse_resume_file_content()
    │
    ▼
LLM structured extraction → Pydantic Resume model (contact, experience, education, skills)
    │
    ▼
DatabaseService.store_resume() → resumes + resume_versions tables
    │
    ▼
Return structured JSON to client
```

### Resume Tailoring

```
Resume file + Job description text
    │
    ▼
extract_text() → resume_text
    │
    ▼
run_tailor_graph(resume_text, job_text, format_type)
    │  ├── pydantic-graph workflow nodes
    │  ├── LLM analysis of resume vs job
    │  └── Type-safe TailorResult output
    ▼
Tailored resume content + improvements list
    │
    ▼ (optional)
Template engine → LaTeX .tex file
    │
    ▼ (optional)
Export service → HTML/DOCX/PDF
```

### Startup Scanner

```
Startups loaded from data/startups/startups.md
    │
    ▼
StartupScannerAgent.process_batch(batch_size)
    │  ├── For each startup with a website:
    │  │   ├── TinyFish/Crawl4AI scrapes career page
    │  │   ├── LLM extracts job listings
    │  │   └── Relevance scoring
    │  └── State persisted to scanner_state table
    ▼
ScannedJobDB entries stored with relevance_score
    │
    ▼
Top jobs ranked by relevance_score
```

## LLM Provider Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ModelRegistry                      │
│                  (singleton)                         │
│                                                     │
│  _detect_providers()                                │
│    ├── Check OPENAI_API_KEY    → openai:gpt-4o      │
│    ├── Check ANTHROPIC_API_KEY → anthropic:claude..  │
│    ├── Check GEMINI_API_KEY    → google-gla:gemini.. │
│    ├── Check GROQ_API_KEY      → groq:llama-3.3..   │
│    ├── Check OPENROUTER_API_KEY → openrouter:...     │
│    ├── Check TOGETHER_API_KEY  → together:llama..    │
│    ├── Ping Ollama (localhost:11434) → ollama:llama  │
│    └── Ping vLLM (localhost:8001)   → openai:...    │
│                                                     │
│  resolve_chain() → ModelChain                       │
│    ├── primary_model_string                          │
│    └── fallback_model_strings[]                      │
│                                                     │
│  get_model() → FallbackModel(primary, ...fallbacks) │
│                                                     │
│  create_agent(output_type, system_prompt) → Agent    │
│    └── THE factory every agent uses                  │
└─────────────────────────────────────────────────────┘
```

**Priority order (cloud-first default):**
Google > OpenAI > Anthropic > Groq > OpenRouter > Together > Ollama > vLLM

**Override via environment:**
- `DEFAULT_MODEL=anthropic:claude-sonnet-4-5` — force primary
- `FALLBACK_MODEL=ollama:llama3.2` — prepend to fallback chain
- `PREFER_LOCAL=true` — Ollama/vLLM first, cloud as fallback

## Vector Search Architecture

```
┌──────────────────────────────────────────────────┐
│              EmbeddingService (singleton)         │
│                                                  │
│  embed_text(text) → list[float]                  │
│    ├── LiteLLM aembedding() (primary)            │
│    └── SHA-256 hash-based fallback (384-dim)     │
│                                                  │
│  embed_batch(texts) → list[list[float]]          │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│              VectorStore (singleton)              │
│              Qdrant file-based                    │
│              data/qdrant/                         │
│                                                  │
│  Collections: resumes, jobs, cover_letters       │
│  Vector dim: 384, Distance: COSINE               │
│                                                  │
│  add_document(collection, doc_id, text, metadata)│
│  search(collection, query_text, n_results)       │
│  delete_document(collection, doc_id)             │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│              SearchService                        │
│                                                  │
│  search_resumes(query, n) — vector similarity    │
│  search_jobs(query, n)    — vector similarity    │
│  hybrid_search(query, collection, n)             │
│    ├── Vector similarity (Qdrant)                │
│    └── Keyword matching (SQLAlchemy LIKE)        │
│    └── Score fusion                              │
└──────────────────────────────────────────────────┘
```

## Auth Architecture

```
┌─────────────────────────────────────────────┐
│            AuthService                       │
│                                             │
│  hash_password(pw) → bcrypt hash            │
│  verify_password(pw, hash) → bool           │
│  create_access_token(data) → JWT string     │
│  decode_token(token) → payload dict         │
│  register_user(email, pw, name) → result    │
│  authenticate_user(email, pw) → User | None │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         auth_middleware.py                   │
│                                             │
│  get_current_user_dependency(token) → User  │
│    └── FastAPI Depends() for protected      │
│        endpoints                            │
└─────────────────────────────────────────────┘

JWT: HS256, 24h expiry, secret from JWT_SECRET_KEY env var
```

## Database Schema

SQLAlchemy declarative models with SQLite (default) or PostgreSQL (optional via docker-compose).

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | User accounts | `id`, `email`, `name`, `profile_json` (stores hashed password) |
| `resumes` | Parsed resume data | `id`, `user_id` (FK→users), `filename`, `content_json`, `raw_text` |
| `resume_versions` | Multiple file versions per resume | `id`, `resume_id` (FK→resumes), `version_name`, `file_path`, `file_format`, `is_active` |
| `job_postings` | Parsed job descriptions | `id`, `title`, `company`, `location`, `content_json`, `raw_text`, `source_url` |
| `tailored_resumes` | Generated tailored resumes | `id`, `resume_id` (FK→resumes), `job_id` (FK→job_postings), `tailored_content`, `match_score` |
| `analysis_results` | Resume-job match analysis | `id`, `resume_id` (FK→resumes), `job_id` (FK→job_postings), `analysis_json` |
| `cover_letters` | Generated cover letters | `id`, `resume_id` (FK→resumes), `job_id` (FK→job_postings), `cover_letter_text`, `key_highlights_json`, `company_name` |
| `startups` | Startup company data | `id`, `name` (unique), `city`, `category`, `website`, `linkedin`, `funding_round` |
| `scanned_jobs` | Discovered job openings | `id`, `startup_id` (FK→startups), `title`, `location`, `requirements_json`, `link`, `relevance_score`, `is_applied` |
| `scanner_state` | Batch processing state | `id`, `state_json`, `batch_number`, `status` |
| `applications` | Application tracking | `id`, `user_id` (FK→users), `job_id` (FK→job_postings), `resume_id` (FK→resumes), `company_name`, `position_title`, `status`, `notes` |

## Deployment

### Docker Multi-Stage Build

The `Dockerfile` uses a two-stage build:

1. **Builder stage** (`python:3.12-slim`): Installs Python dependencies via `pip install`
2. **Runtime stage** (`python:3.12-slim`): Installs Node.js 18 (for LiteParse CLI), copies installed packages and application code

Exposes ports `8000` (FastAPI) and `8050` (Gradio). Health check hits `/health` every 30s.

### docker-compose.yml

- `app` service: Builds from Dockerfile, maps ports 8000/8050, mounts `data/` and `outputs/` as volumes
- Optional PostgreSQL service (commented out): Uncomment and update `DATABASE_URL` to switch from SQLite

### CI/CD

**`.github/workflows/ci.yml`** — Runs on push/PR to `main`:
- **Lint job**: `ruff check .` + `ruff format --check .`
- **Test job**: `pytest tests/ -v` on Python 3.10, 3.11, 3.12 matrix
- **Build job**: Docker image build on main branch push (after lint+test pass)

**`.github/workflows/release.yml`** — Runs on version tags (`v*`):
- Builds and pushes Docker image to GitHub Container Registry (ghcr.io)
- Tags: semver (`1.0.0`, `1.0`), SHA
- Auto-generates changelog and creates GitHub Release
