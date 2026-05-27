---
name: cover-letter-generator
description: >
  Generates a tailored, professional cover letter from a job description and a
  resume. Use this skill whenever a user asks for a cover letter, says "write me
  a cover letter", "draft a cover letter for this job", or has a resume and job
  description and wants to apply. Trigger even for casual phrasing like "can you
  write the cover letter too" or "now do the cover letter". Always use this skill
  when cover letter generation is the intent — do not attempt it without the skill.
---

# Cover Letter Generator

Writes a tailored, human-sounding cover letter grounded in the user's actual
resume and the specific job description. No generic filler. No fabrication.

---

## Inputs Required

| Input | Source |
|-------|--------|
| Final resume | From cv-extractor output or user paste |
| Job description | From job-finder output or user paste |
| Company name | Extract from JD |
| Hiring manager name | Ask user; use "Hiring Manager" if unknown |
| User's preferred tone | Default: professional but warm; ask if they want formal/casual |

---

## Step 1: Analyze Both Documents

**From the JD, extract:**
- Role title and team context
- Top 3 responsibilities the company cares most about
- Mission/values language (pull exact phrases from JD to mirror back)
- Any stated "ideal candidate" traits

**From the resume, extract:**
- Most relevant 2–3 experiences that map to those top responsibilities
- Strongest achievement (with metric if available)
- Specific skills that match must-haves in the JD
- Any personal angle: domain passion, relevant project, career trajectory

---

## Step 2: Write the Cover Letter

### Structure (4 paragraphs, ~300–380 words total)

**Paragraph 1 — Hook (3–4 sentences)**
- Open with a specific, genuine reason for interest in *this* company/role
- Reference something concrete from the JD, company mission, or product
- State the role you're applying for
- Do NOT open with "I am writing to apply for…" or "My name is…"

**Paragraph 2 — Best match evidence (4–5 sentences)**
- Lead with your strongest relevant achievement from the resume
- Connect it directly to the top responsibility from the JD
- Use the XYZ structure where a metric exists: accomplished X, measured by Y, by doing Z
- Only use facts from the resume — no invented context

**Paragraph 3 — Second proof point + fit (4–5 sentences)**
- Second relevant experience or skill cluster
- Tie it to another JD responsibility or company need
- Add a sentence on cultural/mission fit using the company's own language from the JD

**Paragraph 4 — Close (2–3 sentences)**
- Express enthusiasm concisely
- Invite next steps (interview)
- Thank them — no desperation, no over-flattery

### Tone Rules
- Sound like a capable human, not a cover letter template
- Vary sentence length; avoid starting consecutive sentences with "I"
- No buzzwords: "passionate", "leverage", "synergy", "dynamic team player"
- Contractions are fine for warm tone (e.g., "I've", "I'm")
- First person throughout — this is personal

---

## Step 3: Output Format

Produce two versions:

### Version A — Plain Text (paste-ready)
Clean text with no formatting, ready to paste into any application portal.

```
[Date]

[Hiring Manager Name or "Hiring Team"]
[Company Name]

Dear [Name / Hiring Manager],

[Body]

Sincerely,
[User's Name]
[Email] | [LinkedIn if on resume]
```

### Version B — .docx file
Professional formatted document using the docx skill
(`/mnt/skills/public/docx/SKILL.md`):
- Matching font/style to the user's resume if possible (Arial 11pt)
- US Letter, 1" margins
- Name + contact header consistent with resume header
- No bullet points in body — flowing paragraphs only

---

## Integrity Rules

- Every claim must trace back to the resume or JD — no invented roles, projects, or metrics
- Do not add skills, companies, or experiences not in the resume
- If the JD mentions a requirement the resume doesn't cover, do not pretend it does — simply omit it or briefly frame a related skill as adjacent

---

## After Generating

Tell the user:

```
✅ Cover letter ready (plain text + .docx)

Tailored to: [Role] at [Company]
Key angles used:
  - [Achievement from resume] → mapped to [JD responsibility]
  - [Skill/experience] → mapped to [JD need]
  - Mirrored company language: "[exact phrase from JD]"

Tip: Personalize the opening line if you know the hiring manager's name
or a recent company announcement — it stands out.
```

---

## Edge Cases

| Situation | Handling |
|-----------|----------|
| No resume provided | Ask for it; offer to use a pasted summary if full resume unavailable |
| Very short JD | Ask user for the 2–3 things most important to the role |
| User wants multiple versions | Generate one strong version; offer to adjust tone or angle |
| User wants "creative" opener | Offer an anecdote-style hook, but keep it grounded and brief |
| Reapplying to same company | Ask if they've applied before; adjust framing accordingly |
