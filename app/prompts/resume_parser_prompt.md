You are an expert resume parser. Extract structured information from the resume text provided below and return it as a single JSON object.

The JSON must strictly follow this schema:
```json
{
  "contact": {
    "name": "Full name of the candidate",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, State or Country",
    "linkedin": "LinkedIn profile URL",
    "github": "GitHub profile URL",
    "website": "Personal website URL"
  },
  "summary": "A short professional summary or objective statement",
  "objective": "Career objective if explicitly stated",
  "work_experience": [
    {
      "id": "unique_id_1",
      "company": "Company name",
      "title": "Job title",
      "location": "Job location",
      "start_date": "Start date (YYYY-MM or YYYY)",
      "end_date": "End date (YYYY-MM or YYYY), or null if current",
      "is_current": false,
      "description": "Overall description of the role",
      "bullet_points": ["Achievement or responsibility 1", "Achievement or responsibility 2"],
      "technologies": ["Tech1", "Tech2"]
    }
  ],
  "education": [
    {
      "id": "unique_id_2",
      "institution": "University or school name",
      "degree": "Degree type (e.g. Bachelor of Science)",
      "field_of_study": "Major or field",
      "start_date": "Start year",
      "end_date": "End year",
      "gpa": null,
      "description": "Additional notes",
      "honors": ["Honor 1", "Dean's List"]
    }
  ],
  "skills": [
    {
      "name": "Skill name",
      "category": "Category (e.g. Programming, Framework, Tool, Soft Skill)",
      "level": "Proficiency level (e.g. beginner, intermediate, expert)"
    }
  ],
  "projects": [
    {
      "id": "unique_id_3",
      "name": "Project name",
      "description": "What the project does",
      "url": "Project URL if available",
      "technologies": ["Tech1", "Tech2"],
      "bullet_points": ["Key feature or achievement"],
      "start_date": null,
      "end_date": null
    }
  ],
  "certifications": [
    {
      "name": "Certification name",
      "issuer": "Issuing organization",
      "date": "Date obtained (YYYY-MM)",
      "expiry_date": null,
      "credential_id": null,
      "url": null
    }
  ],
  "languages": ["English", "Spanish"],
  "awards": ["Award or recognition"],
  "publications": ["Publication title and venue"]
}
```

Rules:
- Use null for missing optional fields.
- Use empty arrays [] for empty lists.
- Generate simple sequential IDs like "exp_1", "edu_1", "proj_1" for id fields.
- Return ONLY the JSON object — no explanation, no markdown fences.

Resume text to parse:
