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

# Install dependencies
pip install -r requirements.txt
# Or with dev dependencies
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

### Option 2: Direct uvicorn

```bash
uvicorn app.main:app --reload --port 8000
```

### Endpoints

| URL | Description |
|---|---|
| `http://localhost:8000` | FastAPI root |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8050` | Gradio UI |

## Agent System

### Config-Driven Agents

All 8 agents are defined in `app/agents/agents.yaml`:

```python
from app.agents import load_agents, get_agent

# Load all agents from YAML
agents = load_agents()

# Get a specific agent
cv_agent = get_agent("cv_extractor")
result = await cv_agent.extract_and_tailor(cv_text, job_text)

# Hot-reload after YAML changes
from app.agents import reload_agents
reload_agents()
```

### Agent Output Models

| Agent | Output Model | Key Fields |
|-------|-------------|------------|
| CV Extractor | `CVExtractorOutput` | `tailored_resume`, `improvements`, `relevance_summary`, `missing_metrics` |
| Resume Reviewer | `ResumeReviewerOutput` | `bullet_reviews`, `summary`, `full_rewritten_resume`, `metric_questions` |
| Cover Letter | `CoverLetterOutput` | `cover_letter`, `key_highlights`, `tone` |
| Job Finder | `JobFinderOutput` | `search_queries`, `listings`, `summary` |
| Resume Tailor | `TailoredResumeOutput` | `tailored_content`, `improvements`, `format_type` |
| Startup Scanner | `list[JobOpening]` | `title`, `startup_name`, `location`, `requirements`, `relevance_score` |
| Outreach Agent | `OutreachOutput` | `follow_up_email`, `thank_you_note`, `cold_outreach`, `referral_request` |
| Interview Coach | `InterviewCoachOutput` | `behavioral_questions`, `technical_topics`, `star_stories` |

### Adding a New Agent

1. Create a skill file: `app/agents/my-agent.md`
2. Create a prompt file: `app/prompts/my_agent_prompt.md`
3. Create the agent class in `app/agents/my_agent.py` extending `BaseAgent`
4. Add to `agents.yaml`:
```yaml
  my_agent:
    name: "My Agent"
    skill: "my-agent.md"
    system_prompt: "../prompts/my_agent_prompt.md"
    output_type: "MyAgentOutput"
    output_module: "app.agents.my_agent"
```
5. Register in `base_agent.py` `_build_agent_instance()`

## Pipeline System

### Running Pipelines

```python
from app.pipelines import run_pipeline

# Run the full application pipeline
state = await run_pipeline(
    pipeline_key="full_application",
    cv_text=cv_text,
    job_text=job_description,
)

# Access results
print(state.tailored_resume)
print(state.cover_letter)
print(state.job_listings)
print(state.errors)
```

### Available Pipelines

| Key | Name | Steps | Schedule |
|-----|------|-------|----------|
| `full_application` | Full Job Application | CV Extract → Review → Cover Letter → Job Find | On-demand |
| `resume_only` | Resume Tailoring Only | CV Extract → Review | On-demand |
| `daily_scanner` | Daily Startup Scanner | Startup Scanner | `0 9 * * *` |
| `cover_letter_only` | Cover Letter Generation | Cover Letter | On-demand |
| `job_search_only` | Job Search Only | Job Finder | On-demand |
| `outreach` | Post-Application Outreach | Outreach Agent | On-demand |
| `interview_prep` | Interview Preparation | Interview Coach | On-demand |

### Adding a New Pipeline

Add to `app/pipelines/pipelines.yaml`:

```yaml
  my_pipeline:
    name: "My Custom Pipeline"
    description: "Does X then Y"
    enabled: true
    steps:
      - agent: cv_extractor
        description: "Extract and tailor CV"
      - agent: my_agent
        description: "Custom processing"
```

### Scheduling Pipelines

```python
from app.pipelines.scheduler import start_scheduler, schedule_pipeline

# Start scheduler (auto-registers pipelines with schedule configs)
start_scheduler()

# Or schedule manually
schedule_pipeline("resume_only", "0 8 * * 1")  # Mondays at 8 AM
```

### Pipeline Events

```python
from app.pipelines.events import EventBus

# Register a custom handler
def on_complete(event):
    print(f"Pipeline {event.data['pipeline']} completed!")

EventBus.on("pipeline_completed", on_complete)

# View event history
events = EventBus.history(limit=20)
```

## API Endpoints

### Health (`/`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | Root — API name, version |
| GET | `/health` | Health check |
| GET | `/health/models` | LLM provider health |
| GET | `/health/status` | Model registry status |

### Resume & Job (`/api`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/parse/resume` | Upload resume → parse → store |
| POST | `/api/parse/job` | Parse job description |
| POST | `/api/analyze` | Skill match analysis |
| POST | `/api/tailor` | Tailor resume to job |
| POST | `/api/cover-letter` | Generate cover letter |
| POST | `/api/export` | Export to text/HTML/DOCX/PDF/LaTeX |

### Startup Scanner (`/api/scanner`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/scanner/startups` | List startups |
| POST | `/api/scanner/scan/batch` | Scan batch synchronously |
| POST | `/api/scanner/scan/background` | Start background scan |
| GET | `/api/scanner/jobs/top` | Top jobs by relevance |

### Job Discovery (`/api/discovery`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/discovery/search` | Search across job boards |
| GET | `/api/discovery/sources` | List scraper availability (includes `bigset`) |
| POST | `/api/discovery/index` | Index job dicts into DB + vector store |
| GET | `/api/discovery/bigset/mappings` | List BigSet CSV column mapping profiles |
| POST | `/api/discovery/bigset/import` | Multipart CSV/XLSX upload from BigSet export (auth required) |
| POST | `/api/discovery/bigset/sync` | Folder watch import (auth required) |
| GET | `/api/discovery/jobs/ranked` | Profile-fit ranked imported jobs; optional `query` for hybrid search |

**BigSet sync workflow**

1. Build or refresh a dataset in [tinyfish-io/bigset](https://github.com/tinyfish-io/bigset) (UI export CSV/XLSX), or enable `BIGSET_REMOTE_ENABLED` for experimental TinyFish Agent assist against `BIGSET_APP_URL`.
2. Upload via `POST /api/discovery/bigset/import` with optional `mapping_id`, copy files into `data/bigset_imports/`, or run pipeline step `discovery_sync` / cron folder watch.
3. Imports upsert `startups` and `job_postings`, index to Qdrant; agents use tools `search_imported_jobs`, `list_imported_startups`, and ranked prompt context.

**AX (agent experience)**

- Outbound tools: [`profiles/tools/mcp_tools.json`](profiles/tools/mcp_tools.json) plus optional merge of [`mcps/`](mcps/) descriptors (`AX_MERGE_INBOUND_MCPS`).
- Runtime handlers: [`app/ax/tool_registry.py`](app/ax/tool_registry.py); MCP server [`profiles/runtimes/mcp_server.py`](profiles/runtimes/mcp_server.py) calls real handlers (not placeholders) for web and discovery tools.
- Portable profiles: [`profiles/agents/discovery-sync.yaml`](profiles/agents/discovery-sync.yaml), updated job-finder and startup-scanner profiles.

### Search (`/api/search`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/search/resumes` | Semantic search across resumes |
| POST | `/api/search/jobs` | Semantic search across jobs |
| POST | `/api/search/hybrid` | Hybrid search (vector + keyword) |

### Auth (`/api/auth`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Authenticate, get JWT |
| GET | `/api/auth/me` | Current user profile |

### Recommendations (`/api/recommendations`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/recommendations/jobs/{resume_id}` | Recommend jobs for resume |
| GET | `/api/recommendations/skill-gap/{resume_id}/{job_id}` | Skill gap analysis |

### Application Tracking (`/api/applications`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/applications` | Track new application |
| GET | `/api/applications` | List applications |
| PUT | `/api/applications/{id}` | Update status |

## Testing

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --tb=short
```

## Linting

```bash
ruff check .
ruff check --fix .
ruff format .
```

## Docker Deployment

```bash
docker build -t job-booster .
docker run -p 8000:8000 -p 8050:8050 --env-file .env job-booster

# Or with docker-compose
docker compose up -d
```

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROQ_API_KEY` | — | Groq API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `DEFAULT_MODEL` | (auto-detect) | Override primary model |
| `FALLBACK_MODEL` | — | Prepend to fallback chain |
| `PREFER_LOCAL` | `false` | Prefer Ollama/vLLM |
| `DATABASE_URL` | `sqlite:///./job_booster.db` | Database URL |
| `TINYFISH_API_KEY` | — | TinyFish API key |
| `JWT_SECRET_KEY` | (random) | JWT signing secret |
| `LOGFIRE_TOKEN` | — | Logfire observability token |

## Key Design Patterns

### Singleton Registry
`ModelRegistry` auto-detects providers, builds fallback chains, provides `create_agent()` factory.

### Config-Driven Agents
`BaseAgent` loads from `agents.yaml`, resolves prompts from skill.md files, builds pydantic-ai agents.

### Pipeline Engine
`PipelineEngine` loads from `pipelines.yaml`, executes steps as sequential agent calls with shared state, emits events.

### Service Layer Separation
API routes handle HTTP. Services handle business logic. Agents handle LLM orchestration.

### Graceful Degradation
Optional dependencies degrade gracefully — no qdrant → empty search, no bcrypt → auth disabled.
