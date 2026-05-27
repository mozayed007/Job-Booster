# Job_Booster — Product Vision

## Product Name

**Job_Booster** — AI-Powered Job Application Platform with Config-Driven Agents

## Tagline

Automate your entire job search: parse, tailor, review, write, find, and track applications with AI agents and pipeline orchestration.

## Problem Statement

Job seekers spend hours manually tailoring resumes for each application, writing cover letters, researching companies, and tracking statuses. The process is repetitive, error-prone, and scales poorly. Career switchers face additional challenges identifying transferable skills and understanding gaps against target roles.

Job_Booster eliminates this friction with a **config-driven, pipeline-orchestrated platform** — 8 AI agents working together through typed pipeline workflows to automate the entire job application lifecycle.

## Target Users

| User Segment | Description |
|---|---|
| **Job Seekers** | Active applicants needing tailored resumes, cover letters, and job discovery at scale |
| **Career Switchers** | Professionals pivoting industries who need skill gap analysis and targeted resume rewriting |
| **Startup Hunters** | Candidates targeting early-stage companies with automated career page scanning |
| **Recruiters** | Hiring teams matching candidate resumes against job requirements using semantic search |

## Core Value Propositions

### 1. Config-Driven AI Agents (8 Agents)

All agents are defined in `agents.yaml` — prompts, output types, skill bindings, and model settings in YAML, not code.

| Agent | Skill | Output |
|-------|-------|--------|
| **CV Extractor** | cv-extractor.md | `CVExtractorOutput` — tailored resume, improvements, relevance summary, missing metrics |
| **Resume Reviewer** | resume-reviewer.md | `ResumeReviewerOutput` — per-bullet reviews, health score, full rewritten resume, metric questions |
| **Cover Letter Generator** | cover-letter-generator.md | `CoverLetterOutput` — 4-paragraph letter, key highlights, tone |
| **Job Finder** | job-finder.md | `JobFinderOutput` — search queries, scored listings with visa status, summary |
| **Resume Tailor** | (direct agent) | `TailoredResumeOutput` — tailored content, improvements, format type |
| **Startup Scanner** | (career page scraping) | `list[JobOpening]` — extracted jobs with relevance scores |
| **Outreach Agent** | outreach-agent.md | `OutreachOutput` — follow-up emails, thank-you notes, cold outreach, referral requests |
| **Interview Coach** | interview-coach.md | `InterviewCoachOutput` — behavioral questions, technical topics, STAR stories |

### 2. Pipeline Orchestration

Multi-agent workflows defined in `pipelines.yaml`, executed via the PipelineEngine (plain async loops, no pydantic-graph):

| Pipeline | Steps | Schedule |
|----------|-------|----------|
| **Full Application** | CV Extract → Resume Review → Cover Letter → Job Find | On-demand |
| **Resume Only** | CV Extract → Resume Review | On-demand |
| **Daily Scanner** | Startup Scanner | Daily at 9 AM |
| **Cover Letter Only** | Cover Letter | On-demand |
| **Job Search Only** | Job Finder | On-demand |
| **Outreach** | Outreach Agent | On-demand |
| **Interview Prep** | Interview Coach | On-demand |

### 3. Skill-Aligned Prompts

Each agent's system prompt is derived from its skill.md file, ensuring the LLM receives full domain knowledge:
- Cover Letter: 4-paragraph structure, XYZ formula, tone rules, banned buzzwords
- CV Extractor: Structured extraction → JD analysis → relevance scoring → XYZ rewriting → integrity checklist
- Job Finder: Candidate profiling → targeted queries → 6-criteria scoring → visa research
- Resume Reviewer: 6-type diagnosis → XYZ rewriting → action verb reference → health scoring

### 4. Startup Career Page Scanning

Automated scanning via TinyFish (primary) + Crawl4AI (fallback). Extracts job listings, ranks by relevance, persists state across sessions. Scheduled via APScheduler.

### 5. Multi-Format Export

Resumes and cover letters export to text, HTML, DOCX, PDF, and LaTeX. LaTeX rendering uses a Jinja2 template engine with the project's resume template.

### 6. Vector Semantic Search

Qdrant-based vector search across resumes, jobs, and cover letters. Hybrid search combining vector similarity with keyword matching.

## Key Differentiators

### Config-Driven Architecture
Agents and pipelines are defined in YAML. Add new agents or pipelines without code changes. Hot-reload with `reload_agents()`.

### Pipeline Engine with Typed State
The PipelineEngine uses a `PipelineState` dataclass that flows through every step. Artifacts collected at each step. Errors tracked and surfaced. Config-driven via `pipelines.yaml`.

### Multi-Provider LLM with Fallback
`ModelRegistry` auto-detects providers and builds `FallbackModel` chains. No manual configuration — just set API keys.

### Scheduled Automation
APScheduler runs pipelines on cron schedules defined in YAML. Daily startup scanning, weekly digests.

### Event-Driven Notifications
`EventBus` emits pipeline lifecycle events. Register handlers for logging, webhooks, or custom integrations.

## Success Metrics

| Metric | Target |
|---|---|
| Resume parse accuracy | >90% field extraction correctness |
| Tailoring latency | <30s end-to-end per resume |
| Scanner throughput | >50 startups/batch with <5% failure rate |
| Agent prompt alignment | 100% of agents use skill-derived prompts |
| Pipeline completion rate | >95% for full application pipeline |
| Provider uptime | Automatic fallback ensures <1% request failure |
| Vector search relevance | Top-5 results contain relevant match for >80% of queries |
