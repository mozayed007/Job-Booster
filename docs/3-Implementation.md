# Job_Booster — Implementation Guide

## Project Setup

### Prerequisites

- Python 3.10+ (3.12 recommended)
- Node.js 18+ (required for LiteParse CLI)
- At least one LLM provider API key

### Create Environment

```bash
# Clone
git clone https://github.com/mozayed007/Job-Booster.git
cd Job-Booster

# Create virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install project with dev dependencies
pip install -e ".[dev]"

# Install LiteParse CLI (requires Node.js 18+)
npm install -g @llamaindex/liteparse
```

### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at least one LLM API key:

```
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
# or
GEMINI_API_KEY=...
```

The `ModelRegistry` auto-detects available providers. No additional configuration needed.

## Running Locally

### Option 1: Helper Script (Recommended)

```bash
python scripts/run_app.py
```

Launches both FastAPI (port 8000) and Gradio UI (port 8050) concurrently. Handles graceful shutdown on Ctrl+C.

### Option 2: Direct uvicorn

```bash
uvicorn app.main:app --reload --port 8000
```

Gradio UI must be started separately:

```bash
python -c "from app.frontend import app; app.launch(server_name='0.0.0.0', server_port=8050)"
```

### Endpoints

| URL | Description |
|---|---|
| `http://localhost:8000` | FastAPI root |
| `http://localhost:8000/docs` | Swagger UI (auto-generated) |
| `http://localhost:8000/redoc` | ReDoc (auto-generated) |
| `http://localhost:8050` | Gradio UI |

## API Endpoints

### Health (`/`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | Root — API name, version, docs link |
| GET | `/health` | Health check — returns `{"status": "healthy"}` |
| GET | `/health/models` | LLM provider health — tests each provider with a minimal request |
| GET | `/health/status` | Model registry status — sync, no network calls |

### Resume & Job (`/api`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/parse/resume` | Upload resume file → parse → store → return structured data |
| POST | `/api/parse/job` | Job description text → parse → store → return structured data |
| POST | `/api/analyze` | Resume file + job text → skill match analysis |
| POST | `/api/tailor` | Resume file + job text → tailored resume |
| POST | `/api/tailor-to-template` | Resume + job → LaTeX .tex file from template |
| POST | `/api/cover-letter` | Resume + job → cover letter generation |
| POST | `/api/export` | Content → export to text/HTML/DOCX/PDF |
| GET | `/api/resume-versions` | List all stored resume versions |
| GET | `/api/resume-versions/{id}` | Get specific resume version |

### Startup Scanner (`/api/scanner`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/scanner/startups` | List startups (filter by city, category) |
| GET | `/api/scanner/progress` | Current scanning progress |
| POST | `/api/scanner/scan/batch` | Scan batch of startups synchronously |
| POST | `/api/scanner/scan/background` | Start background scan task |
| GET | `/api/scanner/jobs/top` | Top job openings by relevance score |
| POST | `/api/scanner/reset` | Reset scanner state |
| GET | `/api/scanner/cities` | List cities with startup counts |

### Search (`/api/search`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/search/resumes` | Semantic search across resumes |
| POST | `/api/search/jobs` | Semantic search across job postings |
| POST | `/api/search/hybrid` | Hybrid search (vector + keyword) |
| POST | `/api/search/index/resume/{id}` | Index a resume in vector store |
| POST | `/api/search/index/job/{id}` | Index a job in vector store |
| GET | `/api/search/stats` | Vector store collection statistics |

### Auth (`/api/auth`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user (email + password + name) |
| POST | `/api/auth/login` | Authenticate and receive JWT token |
| GET | `/api/auth/me` | Get current user profile (requires JWT) |
| PUT | `/api/auth/profile` | Update user profile (requires JWT) |
| POST | `/api/auth/refresh` | Refresh JWT token (requires JWT) |

### Recommendations (`/api/recommendations`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/recommendations/jobs/{resume_id}` | Recommend jobs for a resume |
| GET | `/api/recommendations/resumes/{job_id}` | Recommend resumes for a job |
| GET | `/api/recommendations/skill-gap/{resume_id}/{job_id}` | Skill gap analysis |
| GET | `/api/recommendations/career/{resume_id}` | Career suggestions based on skills |

### Application Tracking (`/api/applications`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/applications` | Track a new application |
| GET | `/api/applications` | List applications (filter by user_id, status) |
| PUT | `/api/applications/{id}` | Update application status |
| DELETE | `/api/applications/{id}` | Delete an application |
| GET | `/api/applications/stats` | Application statistics |

### Analytics (`/api/analytics`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/analytics/dashboard` | Full dashboard data |
| GET | `/api/analytics/resumes` | Resume statistics |
| GET | `/api/analytics/jobs` | Job statistics |
| GET | `/api/analytics/skills` | Skill trends across job postings |
| GET | `/api/analytics/scanner` | Startup scanner statistics |

## Testing

### Setup

Tests use pytest with pytest-asyncio. Install dev dependencies:

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests (116 tests)
pytest tests/ -v

# Specific test file
pytest tests/test_api.py -v

# With coverage
pytest tests/ -v --tb=short
```

### Test Files

| File | Coverage |
|---|---|
| `tests/test_api.py` | API endpoint integration tests |
| `tests/test_auth_service.py` | Authentication, JWT, password hashing |
| `tests/test_embedding_service.py` | Embedding generation and fallback |
| `tests/test_vector_store.py` | Qdrant vector store operations |
| `tests/test_job_models.py` | Job description Pydantic model validation |
| `tests/test_resume_models.py` | Resume Pydantic model validation |
| `tests/test_startup_scanner.py` | Startup scanner agent logic |
| `tests/test_recommendation_service.py` | Job/resume recommendation engine |
| `tests/test_tracking_service.py` | Application tracking CRUD |
| `tests/test_analytics_service.py` | Analytics aggregation |

### CI Matrix

Tests run on Python 3.10, 3.11, and 3.12 in GitHub Actions.

## Linting

```bash
# Check
ruff check .

# Format check
ruff format --check .

# Auto-fix
ruff check --fix .
ruff format .
```

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

## Docker Deployment

### Build and Run

```bash
# Build
docker build -t job-booster .

# Run
docker run -p 8000:8000 -p 8050:8050 --env-file .env job-booster
```

### Docker Compose

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f app

# Stop
docker compose down
```

The compose file mounts `data/` and `outputs/` as persistent volumes. Optional PostgreSQL service is available (commented out in `docker-compose.yml`).

### Switch to PostgreSQL

1. Uncomment the `db` service in `docker-compose.yml`
2. Update `.env`: `DATABASE_URL=postgresql+asyncpg://jobbooster:changeme@db:5432/jobbooster`
3. Run: `docker compose up -d`

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (GPT-4o, GPT-4o-mini, o1) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (Claude Sonnet, Opus) |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GOOGLE_API_KEY` | — | Alternative name for Gemini key |
| `GROQ_API_KEY` | — | Groq API key (fast Llama/Mixtral inference) |
| `TOGETHER_API_KEY` | — | Together AI API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key (100+ models) |
| `DEFAULT_MODEL` | (auto-detect) | Override primary model (`provider:model-name`) |
| `FALLBACK_MODEL` | — | Prepend to fallback chain |
| `PREFER_LOCAL` | `false` | Prefer Ollama/vLLM over cloud APIs |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `VLLM_BASE_URL` | `http://localhost:8001` | vLLM server URL |
| `VLLM_MODEL` | `default` | Default vLLM model |
| `EMBEDDING_MODEL` | (auto-detect) | Override embedding model |
| `DATABASE_URL` | `sqlite:///./job_booster.db` | SQLAlchemy database URL |
| `TINYFISH_API_KEY` | — | TinyFish API key for web scraping |
| `USE_CRAWL4AI` | `false` | Use Crawl4AI instead of TinyFish |
| `JWT_SECRET_KEY` | (random) | JWT signing secret |
| `JWT_EXPIRY_HOURS` | `24` | JWT token expiry |
| `LOGFIRE_TOKEN` | — | Logfire observability token |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `API_URL` | `http://localhost:8000` | API URL for Gradio frontend |

## Key Design Patterns

### Singleton Registry

`ModelRegistry` is a singleton accessed via `get_registry()`. It auto-detects providers once, caches the model chain, and provides the `create_agent()` factory. All agents and services use this single entry point.

```python
from app.core.model_registry import get_registry, create_agent

# Get registry status
registry = get_registry()
status = registry.get_status()

# Create agent with auto-configured model
agent = create_agent(output_type=MyModel, system_prompt="...")
```

### Factory Pattern

`create_agent()` is the central factory for all Pydantic AI agents. It wraps model selection, fallback chain construction, and agent instantiation:

```python
agent = create_agent(
    output_type=ResumeData,
    system_prompt="Extract structured resume data...",
    retries=2,
)
result = await agent.run(resume_text)
# result.output is a validated ResumeData instance
```

### Fallback Chains

The `ModelRegistry` builds a `FallbackModel` chain from all detected providers. If the primary provider fails, LiteLLM automatically retries on the next provider:

```
Primary: google-gla:gemini-2.0-flash
Fallback 1: openai:gpt-4o
Fallback 2: anthropic:claude-sonnet-4-5
Fallback 3: groq:llama-3.3-70b-versatile
Fallback 4: ollama:llama3.2
```

### Service Layer Separation

API routes (`app/api/`) handle HTTP concerns (request parsing, response models, error codes). Business logic lives in services (`app/services/`). Agents (`app/agents/`) handle LLM orchestration. This separation enables testing each layer independently.

### Graceful Degradation

Optional dependencies (qdrant-client, bcrypt, python-jose, crawl4ai) are imported with try/except. When unavailable, features degrade gracefully:
- No qdrant-client: Vector search returns empty results, recommendations unavailable
- No bcrypt: Registration disabled
- No python-jose: JWT auth disabled
- No crawl4ai: TinyFish used as primary scraper
