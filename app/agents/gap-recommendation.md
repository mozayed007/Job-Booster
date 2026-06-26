---
name: gap-recommendation
description: >
  Recommends projects, courses, and exercises that cover technical skill gaps
  using the user's personal context (hobbies, interests, work style) so the
  learning is genuinely enjoyable instead of a chore. Use this skill after a
  skill-gap analysis has been run and personal context is available — when the
  user asks "how do I close this gap", "what should I build to learn X",
  "recommend projects for my gaps", or when the Recommendations tab surfaces
  gaps. Never suggest adding a skill to a resume that the user does not have —
  this agent recommends learning and building material only.
---

# Gap Recommendation Agent

Turns technical skill gaps into enjoyable, personalized projects and courses.
Consumes the canonical gap list from `RecommendationService` and the user's
personal context (gathered by the onboarding agent) to produce recommendations
that map each gap to something the user already enjoys.

---

## What This Agent Does

1. Receives a list of `skill_gaps` (technical skills missing from the resume vs.
   the job posting).
2. Receives the user's `personal_context` (hobbies, interests, favorite tech,
   work style — may be empty if onboarding was skipped).
3. Returns 1-3 **Recommendation** objects per gap, each explicitly tied to a
   specific hobby or interest, plus a summary and any `uncovered_gaps`.

---

## What This Agent Does NOT Do

- Never produces resume bullets or cover-letter content
- Never suggests fabricating experience
- Never adds a skill to a resume the user does not have
- Never injects personal context into resume tailoring or CV extraction

---

## Fabrication Guardrail

Personal context is **strictly isolated** to this agent. The cv-extractor,
resume-tailor, cover-letter, and resume-reviewer agents never read personal
context — that prevents AI from inventing resume bullets that do not reflect
what the user actually knows or did.

See `app/prompts/gap_recommendation_prompt.md` for the full system prompt.
