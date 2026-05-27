---
name: cv-extractor
description: >
  Extracts content from a full CV (PDF, Markdown, or LaTeX) and generates a
  tailored one-page resume matched to a specific job description — using ONLY
  real information from the CV, never hallucinating or inventing details. Use
  this skill whenever a user uploads a CV and provides a job description, asks
  to tailor their resume to a role, wants a one-page version of their CV, or
  says things like "make this fit the job", "customize my resume", "trim my CV",
  or "match my experience to this posting". Always trigger this skill when both
  a CV and a job description are present, even if phrased casually.
---

# CV Extractor & Job-Tailored Resume Generator

This skill reads a full CV in any format and generates a clean, tailored one-page
resume that matches a specific job description — using **only real content from
the CV**. Zero hallucination. Zero fabrication.

---

## Inputs Required

1. **CV file** — PDF, Markdown (.md), or LaTeX (.tex)
2. **Job description** — paste or upload; even a partial JD works

If either is missing, ask for it before proceeding.

---

## Step 1: Extract the Full CV

### PDF
```bash
# Check if text-extractable
pdftotext -f 1 -l 1 input.pdf - | head -20

# If extractable — full layout-preserving text
pdftotext -layout input.pdf /tmp/cv_raw.txt

# If scanned/garbled — rasterize and read visually
pdftoppm -jpeg -r 150 -f 1 -l 1 input.pdf /tmp/cv_page
ls /tmp/cv_page-*.jpg  # then view each image
```

Use `pdfplumber` for structured extraction if layout matters:
```python
import pdfplumber
with pdfplumber.open("input.pdf") as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
```

### Markdown
```bash
cat input.md
```

### LaTeX
```bash
# Strip LaTeX commands to get readable text
cat input.tex | sed 's/\\[a-zA-Z]*{//g; s/}//g; s/\\//g'
# Or use pandoc for cleaner extraction:
pandoc input.tex -t plain -o /tmp/cv_raw.txt && cat /tmp/cv_raw.txt
```

---

## Step 2: Parse CV into Structured Sections

Once extracted, mentally (or programmatically) organize the CV into:

| Section | What to capture |
|---------|----------------|
| **Contact** | Name, email, phone, LinkedIn, GitHub, location |
| **Summary/Objective** | If present |
| **Experience** | Company, role, dates, bullet points — ALL of them |
| **Education** | Degree, institution, year, GPA if listed |
| **Skills** | Technical, tools, languages, frameworks |
| **Projects** | Name, description, tech used, impact |
| **Awards/Certs** | Certifications, honors, publications |
| **Other** | Volunteering, languages, interests if present |

**Critical:** Capture everything. Do not summarize at this stage. You'll filter in Step 3.

---

## Step 3: Analyze the Job Description

Extract from the JD:

- **Role title** and seniority level
- **Must-have skills/keywords** (technical and soft)
- **Nice-to-have skills**
- **Industry/domain** (fintech, healthcare, ML, etc.)
- **Key responsibilities** — what will they actually do day-to-day?
- **ATS keywords** — exact terms likely in the system (e.g., "PyTorch", "Agile", "cross-functional")

---

## Step 4: Relevance Scoring & Selection

For each section/bullet in the CV, score its relevance to the JD (High / Medium / Low).

**Selection rules:**
- Always include: Contact, most relevant 2–3 roles, Education, top-matched Skills
- Prioritize: Bullets that match must-have skills or responsibilities
- Include if space: Projects and certs that directly relate to the JD
- Exclude: Irrelevant jobs (unless it fills a gap), outdated tech not in JD, hobbies (unless relevant)

**One-page constraint:** Target ~480–550 words total, ~4–6 bullets per role.

**Integrity rule:** 
> You may SELECT, REORDER, SHORTEN, and EMPHASIZE content from the CV.  
> You may NOT invent metrics, add skills not in the CV, or fabricate any detail.  
> If a bullet lacks a metric, leave it metric-free — do not estimate unless the user explicitly asks you to suggest estimates for them to confirm.

---

## Step 5: Rewrite Selected Bullets

Apply the Google XYZ formula to selected bullets where possible:
> **"Accomplished [X] as measured by [Y], by doing [Z]"**

Rules:
- Only rewrite using information that EXISTS in the CV
- Lead with strong action verbs (Led, Built, Reduced, Achieved, Designed, etc.)
- Mirror JD language where the underlying experience matches (e.g., if CV says "made dashboards" and JD says "data visualization", use "data visualization")
- Keep each bullet to 1–2 lines max
- Use present tense for current role, past tense for all others

---

## Step 6: Generate the One-Page Resume

### Structure (in order):
1. **Header** — Name (large), contact info (email | phone | LinkedIn | GitHub | location)
2. **Summary** (optional, 2–3 lines) — only if the CV has one or if JD calls for a specific profile; tailor it to the role using real CV content
3. **Experience** — most recent first; 2–4 roles max on one page
4. **Skills** — grouped (e.g., Languages: Python, R | Frameworks: PyTorch, TensorFlow | Tools: Git, Docker)
5. **Education** — degree, institution, year
6. **Projects or Certifications** — if space permits and JD-relevant

### Output format:
Produce a `.docx` file using the docx skill (see `/mnt/skills/public/docx/SKILL.md`).

Key formatting specs:
- US Letter page (12240 × 15840 DXA), 0.75" margins (1080 DXA)
- Name: 18pt bold; Section headers: 11pt bold with bottom border rule
- Body: 10pt Arial; Bullets via `LevelFormat.BULLET` (never unicode)
- Single column layout; clean, minimal styling — no colors, tables as layout
- No photos, no icons unless user requests

After generating, validate:
```bash
python scripts/office/validate.py output.docx
```

---

## Step 7: Output Summary to User

After generating the file, provide a brief summary:

```
✅ Resume generated: output.docx

Tailoring decisions:
- Highlighted [X, Y, Z skills] from your CV — direct match to JD
- Prioritized [Role A] over [Role B] — more relevant to this position  
- Excluded [Role C] — predates the domain; kept within one page
- Skills section reordered to lead with [Python, PyTorch] per JD keywords

⚠️ Metrics not added: [list any bullets where metrics were omitted due to missing data]
   → Consider adding: "How many users? What was the % improvement? Team size?"

Suggested next step: Run the resume-reviewer skill on this output for bullet-level polish.
```

---

## Integrity Checklist (run before delivering)

- [ ] Every fact came from the original CV
- [ ] No metric was invented or estimated without user instruction
- [ ] No skill was added that wasn't in the CV
- [ ] All dates, company names, and titles are verbatim from the CV
- [ ] Rewritten bullets changed *phrasing*, not *substance*
- [ ] Output fits on one page

---

## Edge Cases

| Situation | Handling |
|-----------|----------|
| CV has no metrics anywhere | Rewrite for strong verbs and clarity; flag to user |
| CV is 10+ years of experience | Keep last 5–7 years unless older role is highly JD-relevant |
| JD is vague or short | Ask the user for the 2–3 skills most important to the role |
| CV is in LaTeX with custom macros | Use pandoc first; if still garbled, ask user to paste plain text version |
| Multiple CVs or versions uploaded | Ask which is the master/most current |
| User asks to "add" something not in CV | Refuse politely: "I can only use content from your CV to avoid misrepresentation. You can add that detail manually if it's accurate." |
