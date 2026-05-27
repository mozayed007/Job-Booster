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
                            │  │   API Routes (10)      │   │
                            │  │   app/api/*.py         │   │
                            │  └───────────┬───────────┘   │
                            │              │               │
                            │  ┌───────────▼───────────┐   │
                            │  │  Pipeline Engine       │   │
                            │  │  app/pipelines/        │   │
                             │  │  (plain async loops)    │   │
                            │  └───────────┬───────────┘   │
                            │              │               │
                            │  ┌───────────▼───────────┐   │
                            │  │  Config-Driven Agents  │   │
                            │  │  agents.yaml (6 agents)│   │
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

     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ APScheduler │  │  EventBus   │  │ Export Svc  │
     │ (cron jobs) │  │ (pipeline   │  │ (DOCX/PDF/  │
     │             │  │  events)    │  │  LaTeX/HTML)│
     └─────────────┘  └─────────────┘  └─────────────┘
```

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Web Framework | FastAPI | 0.115+ |
| AI Agents | Pydantic AI | 0.2+ |
| Agent Config | YAML (agents.yaml) | — |
| Pipeline Config | YAML (pipelines.yaml) | — |
| LLM Router | LiteLLM | 1.30+ |
| Scheduling | APScheduler | 3.10+ |
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
│   ├── db_models.py         # SQLAlchemy tables (12 tables including pipeline_runs)
│   ├── job_model.py         # Job description Pydantic model
│   ├── resume_model.py      # Resume Pydantic model
│   └── startup_model.py     # Startup and JobOpening Pydantic models
│
├── services/                # Business logic layer
│   ├── analytics_service.py # Dashboard and statistics aggregation
│   ├── apply_service.py     # One-click apply pipeline orchestration
│   ├── auth_service.py      # bcrypt hashing, JWT token creation/validation
│   ├── career_scraper.py    # Career page scraping logic (legacy)
│   ├── db_service.py        # SQLAlchemy session management and CRUD
│   ├── embedding_service.py # LiteLLM embedding generation with hash fallback
│   ├── export_service.py    # Multi-format export (text, HTML, DOCX, PDF, LaTeX)
│   ├── job_board_scraper.py # External job board scraping
│   ├── parsing_service.py   # LiteParse + GLM-OCR document parsing
│   ├── recommendation_service.py # Job/resume recommendations via vector search
│   ├── scraper_service.py   # Web scraping orchestration (template method pattern)
│   ├── search_service.py    # Hybrid search (vector + keyword)
│   ├── startup_parser.py    # Startup listing extraction from markdown
│   ├── template_engine.py   # Jinja2 LaTeX template rendering
│   ├── tracking_service.py  # Application status lifecycle management
│   └── vector_store.py      # Qdrant file-based vector storage (singleton)
│
├── agents/                  # Config-driven Pydantic AI agents
│   ├── agents.yaml          # Agent configuration registry (8 agents)
│   ├── base_agent.py        # BaseAgent ABC + AgentConfig + YAML loader
│   ├── cover_letter.py      # Cover Letter Generator agent
│   ├── cv_extractor.py      # CV Extractor agent
│   ├── interview_coach.py   # Interview Coach agent
│   ├── job_finder.py        # Job Finder agent (+ web_search/web_fetch tools)
│   ├── outreach_agent.py    # Outreach Agent (+ web_search tool)
│   ├── resume_reviewer.py   # Resume Reviewer agent
│   ├── resume_tailor.py     # Resume Tailor agent
│   ├── startup_scanner.py   # Startup Scanner agent
│   ├── web_tools.py         # Web search/fetch Pydantic AI tools (TinyFish)
│   ├── cover-letter-generator.md  # Skill definition
│   ├── cv-extractor.md            # Skill definition
│   ├── interview-coach.md         # Skill definition
│   ├── job-finder.md              # Skill definition
│   ├── outreach-agent.md          # Skill definition
│   └── resume-reviewer.md         # Skill definition
│
├── pipelines/               # Pipeline orchestration engine
│   ├── pipelines.yaml       # Pipeline definitions (7 pipelines)
│   ├── engine.py            # PipelineEngine + PipelineState + AgentNode
│   ├── events.py            # EventBus for pipeline lifecycle notifications
│   └── scheduler.py         # APScheduler integration for cron-based execution
│
├── api/                     # FastAPI route modules
│   ├── analytics_routes.py  # /api/analytics/*
│   ├── auth_routes.py       # /api/auth/*
│   ├── dashboard_routes.py  # /api/dashboard/*
│   ├── discovery_routes.py  # /api/discovery/*
│   ├── pipeline_routes.py   # /api/pipeline/* (apply, apply/file)
│   ├── recommendation_routes.py # /api/recommendations/*
│   ├── resume_routes.py     # /api/parse/*, /api/analyze, /api/tailor, /api/export
│   ├── scanner_routes.py    # /api/scanner/*
│   ├── search_routes.py     # /api/search/*
│   └── tracking_routes.py   # /api/applications/*
│
├── middleware/               # FastAPI middleware
│   └── auth_middleware.py   # JWT token extraction dependency
│
├── prompts/                 # LLM prompt templates (aligned to skill.md files)
│   ├── cover_letter_prompt.md    # 4-paragraph structure, XYZ, tone rules
│   ├── cv_extractor_prompt.md    # Extract + tailor + XYZ + integrity checklist
│   ├── interview_coach_prompt.md # Behavioral/technical interview prep
│   ├── job_finder_prompt.md      # Search queries + scoring + visa research (+ web tools)
│   ├── outreach_prompt.md        # Follow-up, thank-you, cold outreach (+ web search)
│   ├── resume_reviewer_prompt.md # 6-type diagnosis + XYZ rewriting
│   ├── resume_tailor_prompt.md   # Resume tailoring instructions
│   ├── resume_parser_prompt.md   # Structured JSON extraction (for parsing service)
│   ├── job_parser_prompt.md      # JD structured extraction (for parsing service)
│   └── job_extraction_prompt.md  # Career page job extraction (for scanner)
│
├── ui/                      # Gradio tab modules
│   └── scanner_tab.py       # Startup scanner tab component
│
├── frontend.py              # Gradio UI application (6 tabs)
└── main.py                  # FastAPI entry point, router mounting, lifespan
```

## Agent Configuration (agents.yaml)

```yaml
agents:
  cover_letter_generator:
    name: "Cover Letter Generator"
    skill: "cover-letter-generator.md"
    system_prompt: "../prompts/cover_letter_prompt.md"

  cv_extractor:
    name: "CV Extractor"
    skill: "cv-extractor.md"
    system_prompt: "../prompts/cv_extractor_prompt.md"

  job_finder:
    name: "Job Finder"
    skill: "job-finder.md"
    system_prompt: "../prompts/job_finder_prompt.md"

  resume_reviewer:
    name: "Resume Reviewer"
    skill: "resume-reviewer.md"
    system_prompt: "../prompts/resume_reviewer_prompt.md"

  resume_tailor:
    name: "Resume Tailor"
    system_prompt: "../prompts/resume_tailor_prompt.md"

  startup_scanner:
    name: "Startup Scanner"
    system_prompt: "../prompts/job_extraction_prompt.md"

  outreach_agent:
    name: "Outreach Agent"
    skill: "outreach-agent.md"
    system_prompt: "../prompts/outreach_prompt.md"

  interview_coach:
    name: "Interview Coach"
    skill: "interview-coach.md"
    system_prompt: "../prompts/interview_coach_prompt.md"
```

## Pipeline Configuration (pipelines.yaml)

```yaml
pipelines:
  full_application:
    name: "Full Job Application Pipeline"
    description: "End-to-end: CV extraction, resume review, cover letter, and job search"
    steps:
      - agent: cv_extractor
      - agent: resume_reviewer
      - agent: cover_letter_generator
      - agent: job_finder

  resume_only:
    name: "Resume Tailoring Only"
    description: "CV extraction and resume review without cover letter or job search"
    steps:
      - agent: cv_extractor
      - agent: resume_reviewer

  daily_scanner:
    name: "Daily Startup Scanner"
    description: "Scan startup career pages for relevant AI/ML job openings"
    schedule: "0 9 * * *"
    steps:
      - agent: startup_scanner

  cover_letter_only:
    name: "Cover Letter Generation"
    description: "Generate a cover letter from existing resume and job description"
    steps:
      - agent: cover_letter_generator

  job_search_only:
    name: "Job Search Only"
    description: "Find job opportunities matching a resume"
    steps:
      - agent: job_finder

  outreach:
    name: "Post-Application Outreach"
    description: "Generate follow-up, thank-you, cold outreach, and referral messages"
    steps:
      - agent: outreach_agent

  interview_prep:
    name: "Interview Preparation"
    description: "Generate behavioral questions, technical topics, and STAR stories"
    steps:
      - agent: interview_coach
```

## Data Flow

### Full Application Pipeline

```
CV Upload (PDF/DOCX/MD/TEX)
    │
    ▼
CV Extractor Agent
    ├── Parse CV into structured sections
    ├── Analyse JD (must-have skills, ATS keywords, responsibilities)
    ├── Score relevance per bullet (High/Medium/Low)
    ├── Rewrite selected bullets using XYZ formula
    └── Output: CVExtractorOutput (tailored_resume, improvements, relevance_summary)
    │
    ▼
Resume Reviewer Agent
    ├── Diagnose each bullet (6 issue types)
    ├── Rewrite using XYZ formula with action verbs
    ├── Flag missing metrics with placeholders
    └── Output: ResumeReviewerOutput (bullet_reviews, health_score, full_rewritten_resume)
    │
    ▼
Cover Letter Agent
    ├── Analyse both documents (top 3 JD responsibilities, mission language)
    ├── Write 4-paragraph letter (Hook, Evidence, Fit, Close)
    ├── Enforce tone rules and banned buzzwords
    └── Output: CoverLetterOutput (cover_letter, key_highlights, tone)
    │
    ▼
Job Finder Agent
    ├── Extract candidate profile (top skills, seniority, domain)
    ├── Generate targeted search queries for credible sources
    ├── Score listings on 6 criteria
    ├── Research visa sponsorship per listing
    └── Output: JobFinderOutput (search_queries, listings, summary)
    │
    ▼
Pipeline Complete → EventBus emits "pipeline_completed"
```

### Startup Scanner Pipeline (Scheduled)

```
APScheduler triggers daily at 9 AM
    │
    ▼
Startup Scanner Agent
    ├── Load startups from data/startups/startups.md
    ├── For each startup with a website:
    │   ├── TinyFish/Crawl4AI scrapes career page
    │   ├── LLM extracts job listings
    │   └── Relevance scoring
    ├── State persisted to scanner_state table
    └── Output: list[JobOpening] with relevance_score
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

## Database Schema

| Table | Purpose |
|---|---|
| `users` | User accounts |
| `resumes` | Parsed resume data |
| `resume_versions` | Multiple file versions per resume |
| `job_postings` | Parsed job descriptions |
| `tailored_resumes` | Generated tailored resumes |
| `analysis_results` | Resume-job match analysis |
| `cover_letters` | Generated cover letters |
| `startups` | Startup company data |
| `scanned_jobs` | Discovered job openings |
| `scanner_state` | Batch processing state |
| `applications` | Application tracking |
| `pipeline_runs` | Pipeline execution history |

## Deployment

### Docker Multi-Stage Build

The `Dockerfile` uses a two-stage build:
1. **Builder stage** (`python:3.12-slim`): Installs Python dependencies
2. **Runtime stage** (`python:3.12-slim`): Installs Node.js 18 (for LiteParse), copies application

Exposes ports `8000` (FastAPI) and `8050` (Gradio).

### CI/CD

**`.github/workflows/ci.yml`** — Lint (ruff), Test (pytest on 3.10/3.11/3.12), Build (Docker)
**`.github/workflows/release.yml`** — Tag-based release with GHCR push and changelog
