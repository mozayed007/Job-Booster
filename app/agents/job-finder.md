---
name: job-finder
description: >
  Searches credible, high-signal job sources for AI/ML roles matching the user's
  resume and applies using browser automation. Use this skill whenever a user
  wants to find jobs, says "find me jobs", "apply to jobs", "look for AI/ML
  roles", "what matches my resume", or has a tailored resume and wants to start
  applying. Trigger even for casual phrasing like "now find me jobs" or "apply
  for me". Always use this skill — do not attempt job searching without it.
compatibility: "Requires web_search tool. Auto-apply agent requires Playwright MCP."
---

# Job Finder & Auto-Apply Agent

Finds current, high-quality AI/ML job listings from credible sources — not
LinkedIn spam — and optionally auto-applies using Playwright browser automation.

---

## Inputs

| Input | Source |
|-------|--------|
| Tailored resume (from cv-extractor) | Required |
| Top skills (5–8) | Extract from resume |
| Target role(s) | Infer or ask |
| Current location / country | Ask — critical for visa filtering |
| Location preference | Ask (remote / hybrid / onsite / specific city or country) |
| Visa sponsorship needed | Ask — filter out roles that don't sponsor if needed |
| Seniority level | Infer from resume |

---

## Tier 1: Credible AI/ML-Specific Sources

These have lower noise, higher signal, and less spam than LinkedIn/Indeed.

### 🎯 Niche AI/ML Job Boards
| Source | URL | Best For |
|--------|-----|----------|
| **AIJobs.net** | aijobs.net | ML engineers, researchers, NLP, CV roles — AI-only board |
| **AI Jobs** | ai-jobs.net | Salary-transparent AI/ML listings globally |
| **Wellfound** | wellfound.com | Startup AI roles, equity-visible, direct founder contact |
| **Remotive** | remotive.com | Vetted remote AI/ML/data science roles, no fake listings |
| **Skima AI** | skima.ai | ML/AI high-intent matching, lower competition |

### 🏢 Direct Company Career Pages (highest quality applications)
Apply directly — bypasses ATS black holes, goes straight to recruiter.

**Frontier AI labs:**
- Anthropic: `anthropic.com/careers`
- OpenAI: `openai.com/careers`
- DeepMind: `deepmind.google/careers`
- Cohere: `cohere.com/careers`
- Mistral: `mistral.ai/careers`
- xAI: `x.ai/careers`
- Inflection / Pi: `inflection.ai`

**Big tech AI divisions:**
- Google Research: `careers.google.com` (filter: Research)
- Meta FAIR: `metacareers.com` (filter: AI Research)
- Apple ML: `jobs.apple.com` (filter: Machine Learning)
- Microsoft Research: `careers.microsoft.com`
- NVIDIA AI: `nvidia.com/en-us/about-nvidia/careers`

**High-growth AI product companies:**
- Hugging Face: `apply.workable.com/huggingface`
- Scale AI: `scale.com/careers`
- Weights & Biases: `wandb.ai/careers`
- Comet ML: `comet.com/careers`
- Databricks: `databricks.com/company/careers`
- Replicate: `replicate.com/careers`

### 🛠️ ATS Boards (search without login)
These power most company career pages — search them directly:
- **Greenhouse**: `job-boards.greenhouse.io` — search any company slug
- **Lever**: `jobs.lever.co` — `jobs.lever.co/[company]`
- **Ashby**: `jobs.ashbyhq.com` — clean, modern ATS used by AI startups

### 💬 Community & Hidden Market Sources
40%+ of roles are never posted publicly. These surface them:

| Source | URL | What it offers |
|--------|-----|----------------|
| **Hacker News Who's Hiring** | `news.ycombinator.com` (monthly thread) | Direct from founders, no recruiters |
| **HN Hiring** | `hnhiring.com` | Searchable/filtered HN job posts |
| **HNHIRING remote** | `hnhiring.com/locations/remote` | Remote-only HN roles |
| **Dice** | `dice.com` | Strong for ML/AI engineering, US-focused |
| **Built In** | `builtin.com` | Tech hubs: SF, NYC, Austin, Boston, Seattle |

---

## Step 1: Build Targeted Search Queries

Use the user's top skills and role to build 4–6 queries:

```
"machine learning engineer" "PyTorch" remote site:wellfound.com
"ML engineer" "LLM" "RAG" jobs 2026 site:aijobs.net
AI researcher "reinforcement learning" "NLP" openai.com OR anthropic.com careers
"data scientist" "MLOps" remote site:remotive.com
site:jobs.lever.co "machine learning" "Python" "transformer"
site:job-boards.greenhouse.io "ML engineer" "deep learning" remote
```

---

## Step 2: Collect & Score Listings

Target 10–15 listings, then score each:

| Criteria | Weight |
|----------|--------|
| Skill overlap with resume | High |
| Role title match | High |
| Location/remote fit | High |
| **Visa sponsorship available** | **High — drop immediately if needed and not offered** |
| Company quality / mission fit | Medium |
| Seniority alignment | Medium |

Keep: Strong on 2+ high-weight criteria
Flag as stretch: 1 gap in must-haves but otherwise strong
Drop: Wrong domain, wrong level, location deal-breaker, no visa sponsorship when required

### Visa Sponsorship Research
For each listing, actively check:
1. JD text for phrases like "visa sponsorship available", "we sponsor H-1B/Tier 2/work visa", "open to international candidates"
2. If unclear, search: `"[Company]" "visa sponsorship" site:greenhouse.io OR site:lever.co`
3. Flag one of three statuses:
   - ✅ **Sponsors** — explicitly stated
   - ❓ **Unknown** — not mentioned; worth emailing HR to confirm
   - ❌ **No sponsorship** — explicitly stated or strong signals (e.g. "must be authorized to work in US without sponsorship")

---

## Step 3: Present Results

```
| # | Role | Company | Location | Visa | Match | Salary | Apply |
|---|------|---------|----------|------|-------|--------|-------|
| 1 | ML Engineer | Cohere | Remote (Global) | ✅ Sponsors | ⭐⭐⭐ | $180–220k | [link] |
| 2 | Research Engineer | Anthropic | SF / Remote US | ❓ Unknown | ⭐⭐⭐ | $200–250k | [link] |
| 3 | AI Engineer | Startup X | Remote (EU) | ✅ Sponsors | ⭐⭐ | $150–170k | [link] |
| 4 | AI Infra Eng | BigCo | NYC Onsite | ❌ No sponsorship | ⭐⭐ | — | [link] |
```

Location format: always specify city/country + remote policy (e.g. "London hybrid", "Remote US only", "Remote Global", "Cairo onsite")

For top 3, include:
- Why it matches (specific resume ↔ JD alignment)
- Any gaps to address
- Visa sponsorship confidence level and any action needed
- Which resume version to use (if multiple were generated)

---

## Step 4: Auto-Apply Agent (Playwright)

### Architecture
Use **Playwright MCP** to drive a real browser — not ATS APIs (which require
recruiter auth keys and reject direct submissions).

```
[Job list] → [Resume matcher] → [Playwright browser] → [Form filler] → [Dedup check] → [Submit]
```

### Key lessons from real implementations:
- **Greenhouse submit API needs recruiter auth** — always use Playwright, not API POST
- **Deduplicate before applying**: store `company_slug + job_id` in a local DB; skip if seen
- **One resume per application**: use keyword matching against JD to pick the right tailored resume
- **Custom ATS questions**: build a profile of standard answers (work auth, salary, visa, etc.)
- **Salary fields**: answer vague when possible; use high end of range when numeric required
- **Token limits on career pages**: save page snapshots and parse offline rather than live

### Playwright MCP Setup
```bash
# Install Playwright MCP in Claude Code
npm install -g @playwright/mcp

# Launch with browser visible (recommended for first runs)
playwright-mcp --browser chromium --headless false
```

### Application Flow per Listing
```
1. Navigate to apply URL
2. Detect ATS type (Greenhouse / Lever / Ashby / custom)
3. Fill standard fields from user profile:
   - Name, email, phone, LinkedIn, GitHub
   - Upload tailored resume PDF (matched to this specific JD)
   - Work authorization, location, salary expectation
4. Answer custom screening questions using profile + role context
5. Submit and log: {company, role, date, url, status: "applied"}
6. Mark job_id as done in dedup DB
```

### Reference Implementation
See: `theblackfemaleengineer.com/blog/building-auto-apply-system-claude-code-playwright`
Open-source pipeline: `github.com/santifer/career-ops` (13k+ stars, Claude Code + Playwright)

---

## After Each Run

Report to user:
```
✅ Applied to 5 roles today

Applied:
  - ML Engineer @ Cohere (Greenhouse) — resume: cohere-tailored.pdf
  - Research Engineer @ Anthropic (Direct) — resume: anthropic-tailored.pdf
  - AI Engineer @ StartupX (Lever) — resume: ml-general.pdf

Skipped (already applied): 2
Skipped (no resume match): 1

Next: Run cover-letter-generator for Cohere and Anthropic — both are high-fit.
```

---

## Integrity Rules

- Only apply to real, currently posted listings — verify before submitting
- Never fabricate resume content or invent credentials in application forms
- If a form requires info not in the user's profile, pause and ask — do not guess
- Log every application with timestamp and URL for the user's records
