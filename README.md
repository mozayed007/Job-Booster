# Job_Booster

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/mozayed007/Job-Booster/actions/workflows/ci.yml/badge.svg)](https://github.com/mozayed007/Job-Booster/actions/workflows/ci.yml)

AI-powered resume tailoring, startup job scanning, and application tracking platform. v1.0.0 — all 12 phases complete.

## Features

| Phase | Feature | Description |
|---|---|---|
| 1 | Multi-format Resume Parsing | PDF, DOCX, MD, TXT, LaTeX via LiteParse; scanned documents via GLM-OCR |
| 2 | AI Structured Extraction | Pydantic AI agents produce type-safe, validated Pydantic models from parsed text |
| 3 | Job Description Parsing | Extract structured requirements, skills, and metadata from job postings |
| 4 | Resume-Job Match Analysis | Skill matching, gap identification, match scoring, and actionable suggestions |
| 5 | AI Resume Tailoring | Graph-based workflows via pydantic-graph generate targeted resumes |
| 6 | Startup Career Page Scraping | TinyFish and Crawl4AI scrape startup career pages with batch processing |
| 7 | Multi-provider LLM Support | 100+ models via LiteLLM with automatic fallback chains |
| 8 | Resume Versioning | Track multiple file versions per resume with database-backed storage |
| 9 | Cover Letter Generation | AI-generated cover letters with key highlights extraction |
| 10 | Vector Semantic Search | Qdrant-based hybrid search (vector similarity + keyword matching) |
| 11 | Application Tracking | Full CRUD with status lifecycle and statistics dashboard |
| 12 | Analytics Dashboard | Resume stats, job stats, skill trends, scanner metrics |

## Quick Start

```bash
# Clone
git clone https://github.com/mozayed007/Job-Booster.git
cd Job-Booster

# Create environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install
pip install -e ".[dev]"
npm install -g @llamaindex/liteparse

# Configure
cp .env.example .env
# Edit .env — set at least one API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY)

# Run
python scripts/run_app.py
```

- **Gradio UI**: http://localhost:8050
- **API docs**: http://localhost:8000/docs

## Architecture

Single FastAPI application with internal service layers, Gradio frontend, and SQLite database:

```
Gradio UI (8050) → FastAPI (8000) → API Routes → AI Agents → Services
                                                        ↓
                                          ┌─────────────┼─────────────┐
                                          ↓             ↓             ↓
                                    LiteLLM        SQLAlchemy      Qdrant
                                   (100+ LLMs)     (SQLite)    (vector search)
```

**Key components:**
- `app/core/model_registry.py` — Singleton ModelRegistry auto-detects providers, builds fallback chains, provides `create_agent()` factory
- `app/agents/` — Pydantic AI agents for resume tailoring, cover letters, startup scanning
- `app/services/` — Business logic: parsing, auth, search, tracking, analytics, export
- `app/api/` — 7 FastAPI routers: resume, scanner, search, auth, recommendations, tracking, analytics

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.10+ |
| Frontend | Gradio |
| AI Agents | Pydantic AI + pydantic-graph |
| LLM Router | LiteLLM (100+ providers) |
| Document Parsing | LiteParse (LlamaIndex) + GLM-OCR |
| Web Scraping | TinyFish + Crawl4AI |
| Vector DB | Qdrant (file-based) |
| Database | SQLAlchemy + SQLite |
| Auth | bcrypt + JWT (python-jose) |
| Observability | Logfire |
| Linting | Ruff |

## API Documentation

Full interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

7 route groups: Resume/Job parsing, Startup Scanner, Search, Auth, Recommendations, Application Tracking, Analytics.

## Testing

```bash
# Run all 116 tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Lint
ruff check .
ruff format --check .
```

Tests run on Python 3.10, 3.11, 3.12 in CI. See `tests/` for test files covering API endpoints, auth, embeddings, vector store, models, scanner, recommendations, tracking, and analytics.

## Docker

```bash
# Build and run
docker build -t job-booster .
docker run -p 8000:8000 -p 8050:8050 --env-file .env job-booster

# Or use docker-compose
docker compose up -d
```

Docker Compose mounts `data/` and `outputs/` as volumes. Optional PostgreSQL service available (see `docker-compose.yml`).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROQ_API_KEY` | — | Groq API key |
| `TOGETHER_API_KEY` | — | Together AI API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `DEFAULT_MODEL` | auto | Override primary model (`provider:model`) |
| `FALLBACK_MODEL` | — | Prepend to fallback chain |
| `PREFER_LOCAL` | `false` | Prefer Ollama/vLLM over cloud |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `DATABASE_URL` | `sqlite:///./job_booster.db` | Database URL |
| `TINYFISH_API_KEY` | — | TinyFish API key |
| `JWT_SECRET_KEY` | random | JWT signing secret |
| `LOGFIRE_TOKEN` | — | Logfire observability token |
| `LOG_LEVEL` | `INFO` | Logging level |

See `.env.example` for the full list with descriptions.

## Project Structure

```
Job_Booster/
├── app/
│   ├── main.py                 # FastAPI entry point, router mounting
│   ├── frontend.py             # Gradio UI (6 tabs)
│   ├── agents/                 # Pydantic AI agents (resume tailor, cover letter, scanner)
│   ├── api/                    # FastAPI routers (7 route modules)
│   ├── core/                   # Config, ModelRegistry, LLM setup
│   ├── middleware/              # JWT auth middleware
│   ├── models/                 # Pydantic + SQLAlchemy models
│   ├── prompts/                # LLM prompt templates (Markdown)
│   ├── services/               # Business logic (15 service modules)
│   └── ui/                     # Gradio tab components
├── data/                       # Sample resumes, jobs, startups
├── docs/                       # Documentation (Vision, Architecture, Implementation)
├── outputs/                    # Generated output files
├── scripts/run_app.py          # Launch script (FastAPI + Gradio)
├── tests/                      # Test suite (116 tests, 10 files)
├── .github/workflows/          # CI (lint+test+build) and Release (GHCR)
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Docker Compose with optional PostgreSQL
├── pyproject.toml              # Project metadata, dependencies, tool config
└── .env.example                # Environment variable template
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make changes and add tests
4. Run lint and tests: `ruff check . && pytest tests/ -v`
5. Commit with conventional commit messages
6. Open a pull request against `main`

CI will run lint checks (Ruff) and tests (pytest on Python 3.10/3.11/3.12) automatically on PR.

## License

MIT License — see [LICENSE](LICENSE) for details.
