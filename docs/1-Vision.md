# Job_Booster — Product Vision

## Product Name

**Job_Booster** — AI-Powered Resume Tailoring & Startup Job Scanner

## Tagline

Automate your job search: parse, tailor, match, and track applications with AI agents.

## Problem Statement

Job seekers spend hours manually tailoring resumes for each application, researching startup career pages, writing cover letters, and tracking application statuses across spreadsheets. The process is repetitive, error-prone, and scales poorly. Career switchers face an additional challenge: identifying transferable skills and understanding gaps against target roles.

Job_Booster eliminates this friction by automating the entire job application pipeline — from resume parsing and AI-driven tailoring to startup career page scanning and application tracking.

## Target Users

| User Segment | Description |
|---|---|
| **Job Seekers** | Active applicants applying to multiple positions who need tailored resumes and cover letters at scale |
| **Career Switchers** | Professionals pivoting industries who need skill gap analysis and targeted resume rewriting |
| **Startup Hunters** | Candidates targeting early-stage companies who need automated scanning of startup career pages |
| **Recruiters** | Hiring teams matching candidate resumes against job requirements using semantic search |

## Core Value Propositions

### 1. AI Resume Tailoring

Upload a resume (PDF, DOCX, MD, TXT, LaTeX, or scanned document) and a job description. Pydantic AI agents produce a tailored resume optimized for the specific role, with graph-based workflows ensuring structured, type-safe output.

### 2. Startup Career Page Scanning

Automatically scan startup career pages via TinyFish and Crawl4AI. The scanner agent extracts job listings, ranks them by relevance, and persists discovered openings across sessions with batch processing support.

### 3. Cover Letter Generation

Generate personalized cover letters from a resume and job description. The agent extracts key highlights, matches them to job requirements, and produces professional copy with configurable tone.

### 4. Skill Gap Analysis

Compare parsed resume skills against job requirements. Returns matched skills, missing skills, confidence scores, and actionable suggestions for improvement. Powers both the analysis dashboard and recommendation engine.

### 5. Application Tracking

Full CRUD for job applications with status lifecycle management (applied, interviewing, offered, rejected, accepted). Statistics dashboard with per-user filtering.

### 6. Vector Semantic Search

Qdrant-based vector search across resumes, jobs, and cover letters. Supports hybrid search combining vector similarity with keyword matching. Powers job recommendations and resume-job matching.

## Key Differentiators

### Multi-Provider LLM with Fallback

The `ModelRegistry` auto-detects available LLM providers from environment variables (OpenAI, Anthropic, Google, Groq, Together, OpenRouter, Ollama, vLLM) and builds a `FallbackModel` chain. If the primary provider fails, requests automatically route to the next available provider. No manual configuration required — just set API keys.

### Qdrant Vector Search

File-based Qdrant instance requires no external server. Three collections (resumes, jobs, cover_letters) with 384-dimensional cosine similarity. Embeddings generated via LiteLLM with deterministic hash-based fallback for offline/dev environments.

### Pydantic AI Type-Safe Agents

All LLM interactions use Pydantic AI agents with typed output models. Structured extraction produces validated Pydantic models, not raw text. The `create_agent()` factory in `ModelRegistry` is the single entry point for all agent creation.

### Template-Based LaTeX Generation

Resume tailoring can produce `.tex` output rendered through a Jinja2 template engine. Combined with the export service, output is available in text, HTML, DOCX, PDF, and LaTeX formats.

## Success Metrics

| Metric | Target |
|---|---|
| Resume parse accuracy | >90% field extraction correctness |
| Tailoring latency | <30s end-to-end per resume |
| Scanner throughput | >50 startups/batch with <5% failure rate |
| Test coverage | 116 tests passing across Python 3.10, 3.11, 3.12 |
| Provider uptime | Automatic fallback ensures <1% request failure |
| Vector search relevance | Top-5 results contain relevant match for >80% of queries |
