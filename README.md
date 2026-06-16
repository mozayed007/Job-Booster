# Job Booster

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com/)
[![Gradio](https://img.shields.io/badge/Gradio-5.0%2B-orange)](https://gradio.app/)
[![Pydantic AI](https://img.shields.io/badge/Pydantic%20AI-0.2%2B-purple)](https://ai.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/mozayed007/Job-Booster/actions/workflows/ci.yml/badge.svg)](https://github.com/mozayed007/Job-Booster/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-213%2F24%20files-brightgreen)](tests/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](Dockerfile)

**Stop copy-pasting resumes.** Job Booster is an AI platform that parses, tailors, reviews, and tracks your entire job application pipeline — powered by 9 specialized AI agents that work together.

Feed it a resume and a job description. Get back a tailored resume, a cover letter, interview prep, and a tracked application — in seconds, not hours.

---

## Why This Exists

Job seekers spend 30+ minutes per application: reading the JD, rewriting bullets, drafting a cover letter, researching the company, tracking the status. Multiply that by 50-100 applications and it becomes a full-time job *before* you even get the job.

Job Booster compresses that cycle to under a minute with a **config-driven agent pipeline** — each agent handles one piece of the workflow, passes typed state to the next, and produces output grounded in your actual experience. No generic filler. No fabricated metrics.

---

## The Agent Experience

9 agents, each with a dedicated skill file and system prompt, orchestrated through typed pipelines:

```
┌───────────────────────────────────────────────────────────────────────┐
│                    Full Application Pipeline                          │
│                                                                       │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐    │
│  │    CV    │──▶│   Resume     │──▶│   Cover      │──▶│   Job  │    │
│  │ Extractor│   │   Reviewer   │   │   Letter     │   │  Finder  │    │
│  └──────────┘   └──────────────┘   └──────────────┘   └──────────┘    │
│       │               │                  │                  │         │
│       ▼               ▼                  ▼                  ▼         │
│  Structured      Per-bullet         4-paragraph        Scored         │
│  resume data     health score       tailored letter    listings       │
└───────────────────────────────────────────────────────────────────────┘
```

| Agent | What It Does | Output |
|-------|-------------|--------|
| **CV Extractor** | Parses your resume, maps skills to the JD, rewrites with XYZ formula | Structured CV data, relevance summary, missing metrics |
| **Discovery Sync** | Imports BigSet exports and remote dataset planning before discovery agents | Imported/synchronized job corpus ready for ranking |
| **Resume Reviewer** | Diagnoses every bullet, scores resume health, rewrites weak points | Per-bullet reviews, health score, rewritten resume |
| **Cover Letter Generator** | Writes a grounded 4-paragraph letter — no buzzwords, no fabrication | Plain text + .docx, key angle mapping |
| **Job Finder** | Generates targeted search queries, scores listings across 6 criteria | Scored job listings with visa status |
| **Resume Tailor** | Graph-based workflow that restructures resume for a specific role | Tailored content with improvement notes |
| **Startup Scanner** | Scrapes startup career pages via TinyFish/Crawl4AI, ranks by relevance | Extracted openings with relevance scores |
| **Outreach Agent** | Drafts follow-ups, thank-you notes, cold outreach, referral requests | Ready-to-send emails by type |
| **Interview Coach** | Generates behavioral questions, technical topics, STAR stories from your resume | Full prep kit grounded in your experience |

All agents are **config-driven** — defined in `agents.yaml` with skill files, prompts, and output types. Add or modify agents without touching application code.

---

## Portable Agent Profiles

Job Booster supports a portable agent profile architecture under `profiles/` for cross-platform, field-agnostic deployment:

```
profiles/
├── schema.yaml          # v1.0 profile schema definition
├── providers.yaml       # LLM provider definitions + fallback chains
├── bundle.yaml          # Master bundle with all 9 agent profiles
├── pipelines.yaml       # Portable pipeline definitions
├── agents/              # Individual agent YAML profiles
│   ├── cv-extractor.yaml
│   ├── discovery-sync.yaml
│   ├── resume-reviewer.yaml
│   ├── cover-letter.yaml
│   ├── job-finder.yaml
│   ├── resume-tailor.yaml
│   ├── startup-scanner.yaml
│   ├── outreach.yaml
│   └── interview-coach.yaml
├── adapters/            # Platform-specific adapters (opencode, cursor, etc.)
├── runtimes/            # Runtime configurations
└── tools/               # Tool definitions
```

Load profiles via `app/agents/profile_loader.py` — backward compatible with the existing `BaseAgent` system.

---

## Pipelines

Agents compose into typed workflows defined in `pipelines.yaml`:

| Pipeline | Steps | Trigger |
|----------|-------|---------|
| **Full Application** | CV Extract → Resume Review → Cover Letter → Job Find | On-demand |
| **Resume Only** | CV Extract → Resume Review | On-demand |
| **Discovery Sync Only** | Discovery Sync | On-demand / before import pipelines |
| **Daily Scanner** | Discovery Sync → Startup Scanner | Cron (9 AM daily) |
| **Cover Letter Only** | Cover Letter | On-demand |
| **Job Search Only** | Job Finder | On-demand |
| **Outreach** | Outreach Agent | On-demand |
| **Interview Prep** | Interview Coach | On-demand |

Each pipeline passes a typed `PipelineState` through every step — artifacts collected, errors tracked, results persisted.

---

## Quick Start

### Prerequisites

- **Python** >= 3.10
- **Node.js** >= 18 (required by LiteParse for PDF/document parsing)

### Installation

```bash
# Clone
git clone https://github.com/mozayed007/Job-Booster.git
cd Job-Booster

# Environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -e ".[dev]"

# Install LiteParse CLI (requires Node.js >= 18)
npm install -g @llamaindex/liteparse

# Optional: Crawl4AI (advanced web scraping)
pip install -e ".[crawl4ai]"

# Configure
cp .env.example .env
# Set at least one API key: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY

# Run
python scripts/run_app.py
```

### Access Points

- **Gradio UI**: http://localhost:8050
- **API docs**: http://localhost:8000/docs (set `DEBUG=true` to enable)
- **Health check**: http://localhost:8000/health
- **Model status**: http://localhost:8000/health/models

### Discovery workflow (Gradio)

1. **Account** — sign in; edit profile (skills, locations, BigSet preferences).
2. **Discovery → Imported corpus** — preview CSV/XLSX columns, import or sync `data/bigset_imports/`, load ranked jobs.
3. **Discovery → Job boards** — search external boards and index results.
4. **Pipelines** — run `discovery_sync_only` or `daily_scanner` on demand.
5. **Scanner** — batch-scan company career pages; filter by city.
6. **Apply** — paste a ranked job into the job description field and generate a package.

Optional: enable remote BigSet dataset planning with `BIGSET_REMOTE_ENABLED`, `BIGSET_APP_URL`, and `TINYFISH_API_KEY` (see `.env.example`).

---

## Architecture

```
Gradio UI (8050)
    │
    ▼
FastAPI (8000) ──▶ API Routes (11 routers)
    │
    ├──▶ Pipeline Engine (async loops, typed state)
    │        │
    │        ▼
    │    Config-Driven Agents (agents.yaml / profiles/)
    │        │
    │        ▼
    ├──▶ LiteLLM (100+ models, auto-fallback chains)
    ├──▶ LiteParse + GLM-OCR (document parsing)
    ├──▶ Qdrant (vector semantic search)
    ├──▶ SQLAlchemy + SQLite (persistence)
    └──▶ TinyFish + Crawl4AI (career page scraping)
```

**API Routes (11 routers):**
| Router | Endpoint Prefix | Purpose |
|--------|----------------|---------|
| Scanner | `/api/scanner` | Startup career page scanning |
| Resume | `/api/resume` | Resume parsing, tailoring, review |
| Search | `/api/search` | Semantic search across vectors |
| Auth | `/api/auth` | JWT registration, login, profile |
| Recommendations | `/api/recommendations` | Job/resume matching |
| Tracking | `/api/tracking` | Application tracking |
| Analytics | `/api/analytics` | Dashboard stats & skill trends |
| Pipeline | `/api/pipeline` | Full application pipeline |
| Discovery | `/api/discovery` | Job board aggregation |
| Dashboard | `/api/dashboard` | Overview & top matches |
| Settings | `/api/settings` | User profile and preferences |

**Key modules:**
- `app/agents/agents.yaml` — all agent definitions (prompts, skills, output types)
- `app/agents/base_agent.py` — BaseAgent with YAML-driven config loading
- `app/agents/profile_loader.py` — Portable profile loader for `profiles/`
- `app/core/model_registry.py` — auto-detects providers, builds fallback chains
- `app/core/llm_config.py` — backward-compatible LLM re-exports
- `app/pipelines/` — PipelineEngine orchestrating multi-agent workflows
- `app/pipelines/state.py` — typed PipelineState with artifacts & error tracking
- `app/services/` — 22 service modules (parsing, auth, search, tracking, export, BigSet import/remote)
- `app/ui/api_client.py` — async HTTP client bridging Gradio to backend APIs
- `app/middleware/auth_middleware.py` — JWT extraction dependency

---

## LangChain + LangGraph Comparison Layer

`app/langchain_layer/` is a parallel AI-agent implementation that mirrors the
Pydantic AI layer so you can compare the two stacks side-by-side:

| Pydantic AI | LangChain + LangGraph |
|-------------|----------------------|
| `BaseAgent` + YAML config | `LangChainAgent` base class |
| `app.pipelines.engine.PipelineEngine` | `app.langchain_layer.graph.LangGraphPipeline` |
| `PipelineState` dataclass | `LCGraphState` dataclass |
| `pydantic-ai.Agent` with `output_type` | `ChatLiteLLM` with `with_structured_output()` |
| Async sequential agent calls | Compiled `StateGraph` with async nodes |

The LangChain layer reuses the same LiteLLM model registry, the same pipeline
YAML definitions, and the same Pydantic output models, so comparisons focus on
orchestration and developer experience rather than model access.

```bash
# Run LangChain layer tests only
pytest tests/test_langchain_layer.py -v
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.115+, Python 3.10+ |
| Frontend | Gradio 5.0+ (10 tabs) |
| AI Agents | Pydantic AI 0.2+ + pydantic-graph |
| AI Agents (alt) | LangChain 0.3+ + LangGraph 0.3+ + `langchain-litellm` |
| Agent Config | YAML (`agents.yaml` + `pipelines.yaml`) + Portable Profiles (`profiles/`) |
| LLM Router | LiteLLM (100+ providers, auto-fallback) |
| Document Parsing | LiteParse (LlamaIndex) + GLM-OCR |
| Web Scraping | TinyFish (primary) + Crawl4AI (optional) |
| Vector DB | Qdrant (file-based, hybrid search) |
| Database | SQLAlchemy + SQLite |
| Auth | bcrypt + JWT (python-jose) |
| Scheduling | APScheduler (cron for pipelines) |
| Observability | Logfire + Loguru |
| Export | DOCX, PDF, LaTeX, HTML, plain text |
| HTTP Client | httpx |
| Config | pydantic-settings + python-dotenv |
| YAML Parsing | PyYAML |
| Async Gradio | thread-isolated asyncio.run |
| Build | hatchling |
| Linting | Ruff |
| Testing | pytest + pytest-asyncio |

---

## Docker

```bash
# Build
docker build -t job-booster .

# Run with environment file
docker run -p 8000:8000 -p 8050:8050 --env-file .env job-booster

# Or use docker-compose (mounts data/ and outputs/ as volumes)
docker compose up -d
```

The Dockerfile uses Python 3.12 slim, installs Node.js 18 for LiteParse, and includes a health check via `scripts/healthcheck.sh`.

---

## Testing

```bash
# All unit tests (no API key needed)
pytest tests/ -v

# Specific file
pytest tests/test_api.py -v

# Integration tests (requires GEMINI_API_KEY in .env)
pytest -m integration -v

# Lint
ruff check .
ruff format --check .

# Type check
mypy app/
```

213 tests across 24 files. CI runs on Python 3.10, 3.11, 3.12.

### Integration Tests (requires API key)

Verify your LLM API key works end-to-end:

```bash
# Auto-detects GEMINI_API_KEY, runs real API calls
pytest -m integration -v
```

These tests call the real Gemini API to confirm the full stack works:

- Model registry detects your API key
- Pydantic AI agents produce structured output
- LangChain / LangGraph layer responds
- Pipelines execute end-to-end

**Cost:** ~6 API calls (Gemini 3.1 Flash Lite, free-tier eligible).
Tests are **skipped automatically** if no API key is set — no configuration needed for CI.

---

## Environment Variables

### LLM API Keys (set any combination)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI (GPT-4o, GPT-4o-mini, o1, etc.) |
| `ANTHROPIC_API_KEY` | Anthropic (Claude Sonnet, Claude Opus) |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google Gemini (Gemini 2.0 Flash, Gemini 1.5 Pro) |
| `GROQ_API_KEY` | Groq (fast inference for Llama, Mixtral) |
| `TOGETHER_API_KEY` | Together AI (Llama, Mixtral, CodeLlama) |
| `OPENROUTER_API_KEY` | OpenRouter (access 100+ models via one API key) |

### Local / Self-Hosted Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama local LLM endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `VLLM_BASE_URL` | `http://localhost:8001` | vLLM self-hosted inference endpoint |
| `VLLM_MODEL` | `default` | Default vLLM model |
| `PREFER_LOCAL` | `false` | Prefer Ollama/vLLM over cloud APIs |

### Model Override

| Variable | Description |
|----------|-------------|
| `DEFAULT_MODEL` | Override primary model (`provider:model-name`) |
| `FALLBACK_MODEL` | Prepend to fallback chain |
| `EMBEDDING_MODEL` | Model for vector embeddings |

### Web Scraping

| Variable | Default | Description |
|----------|---------|-------------|
| `TINYFISH_API_KEY` | — | TinyFish API key (primary scraper) |
| `USE_CRAWL4AI` | `false` | Enable Crawl4AI (optional advanced scraping) |

### Database & App

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./job_booster.db` | Database URL |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `API_URL` | `http://localhost:8000` | API base URL |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `False` | Debug mode |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

### Auth

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | random | JWT signing secret (set fixed for production) |
| `JWT_EXPIRY_HOURS` | `24` | JWT token expiry |

### Observability & LiteLLM

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGFIRE_TOKEN` | — | Logfire observability token |
| `LITELLM_VERBOSE` | `false` | Verbose LiteLLM logging |
| `LITELLM_CACHE` | `true` | Enable LiteLLM response caching |

See `.env.example` for the full list with inline documentation.

---

## Project Structure

```
Job_Booster/
├── app/
│   ├── main.py                 # FastAPI entry point (API v0.2.0)
│   ├── frontend.py             # Gradio UI (10 tabs)
│   ├── agents/                 # 9 config-driven AI agents (Pydantic AI)
│   │   ├── agents.yaml         # Agent definitions (prompts, skills, types)
│   │   ├── base_agent.py       # BaseAgent with YAML loading
│   │   ├── profile_loader.py   # Portable profile loader
│   │   ├── web_tools.py        # Web search/fetch Pydantic AI tools
│   │   └── *.md                # Skill files per agent
│   ├── langchain_layer/        # Parallel LangChain + LangGraph AI layer
│   │   ├── agents.py           # Mirrored agents using ChatLiteLLM
│   │   ├── factory.py          # ChatLiteLLM factory from ModelRegistry
│   │   ├── graph.py            # LangGraph pipeline engine
│   │   ├── prompts.py          # Prompt builders
│   │   └── state.py            # LCGraphState dataclass
│   ├── api/                    # 11 FastAPI routers
│   ├── core/                   # Config, ModelRegistry, LLM setup
│   ├── middleware/             # JWT auth middleware
│   ├── pipelines/              # Pipeline engines (sequential + pydantic-graph + LangGraph) + state
│   │   ├── engine.py           # Sequential PipelineEngine
│   │   ├── graph_engine.py     # pydantic-graph backend
│   │   ├── langchain_layer/    # LangGraph backend (see above)
│   │   ├── state.py            # Shared PipelineState
│   │   └── pipelines.yaml      # Pipeline definitions
│   ├── services/               # Business logic (22 modules)
│   ├── models/                 # Pydantic + SQLAlchemy models
│   ├── prompts/                # LLM prompt templates (Markdown)
│   └── ui/                     # Gradio tab components + API client
├── profiles/                   # Portable agent profiles
│   ├── schema.yaml
│   ├── providers.yaml
│   ├── bundle.yaml
│   ├── pipelines.yaml
│   ├── agents/
│   ├── adapters/
│   ├── runtimes/
│   └── tools/
├── data/                       # Sample resumes, jobs, startups
├── docs/                       # Vision, Architecture, Implementation
├── tests/                      # 213 tests, 24 files
├── scripts/
│   ├── run_app.py              # Launch script
│   └── healthcheck.sh          # Docker health check
├── Dockerfile                  # Multi-stage build (Python 3.12 + Node.js 18)
├── docker-compose.yml          # Compose with optional PostgreSQL
├── .env.example                # Full environment variable reference
├── .github/workflows/          # CI (lint + test) + Release (GHCR)
└── pyproject.toml              # Metadata, deps, tool config (v1.0.0)
```

---

## Gradio UI Tabs

The web interface includes 10 tabs for the complete job search workflow:

| # | Tab | Purpose |
|---|-----|---------|
| 1 | **Overview** | Dashboard of your job search at a glance |
| 2 | **Apply** | Full application package: tailored resume + cover letter + analysis |
| 3 | **Discovery** | Imported corpus (BigSet) and external job board search |
| 4 | **Pipelines** | Run discovery sync, daily scanner, and full application pipelines |
| 5 | **Scanner** | Scan AI/ML startup career pages for relevant openings |
| 6 | **Search** | Semantic search across stored resumes and jobs |
| 7 | **Recommendations** | Job recommendations and skill gap analysis |
| 8 | **Applications** | Track and manage job applications with status updates |
| 9 | **Analytics** | Stats, trends, and skill market insights |
| 10 | **Account** | Register, login, and manage your profile |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make changes and add tests
4. Run `python -m ruff check . && python -m mypy app/ && python -m pytest -m "not integration"`
5. Open a PR against `main`

CI runs lint + tests automatically on every PR. Releases auto-push to GitHub Container Registry.

---

## License

MIT — see [LICENSE](LICENSE).
