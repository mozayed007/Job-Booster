# 🧩 Job_Booster: Core Implementation Details (MVP Refactor)

## 3.1. Core Service Integration (Simplified MVP) ⚙️

(Note: The following sections describe the implementation details. Current code provides the foundational structure, with detailed logic being progressively developed.)

In the MVP architecture, functionalities previously envisioned as separate MCP servers are integrated as services directly within the main FastAPI application. This simplifies the system by removing inter-process communication overhead for core features.

* **Internal Service Calls:** Agents and API handlers in `app/agents/` and `app/main.py` directly import and call methods from service modules located in `app/services/` (e.g., `parsing_service.py`, `db_service.py`, `llm_service.py`).
* **Integrated Core Services:** Each service module provides specialized functionality within the single FastAPI application:
  * `app/services/db_service.py`: Handles all SQLite database operations directly using SQLAlchemy.
  * `app/services/parsing_service.py`: Contains logic for document parsing and may call an LLM service for understanding content.
  * `app/services/llm_service.py`: Encapsulates all interactions with the chosen LLM (Google Gemini via ADK).
* **Configuration:** Application-wide configurations, including database URLs, API keys for external LLMs, etc., are managed centrally, typically loaded from environment variables (`.env` file) and accessed via `app/core/config.py`.
* **Dependency Management:** All Python dependencies for the application, including those for parsing, database interaction, and LLM SDKs, are managed in a single `requirements.txt` file.

## 3.2. Agent Intelligence & Orchestration (Simplified MVP) 🤖🔥

(Note: The agent workflows and logic described below outline the implementation details being progressively developed.)

* **Agent = Orchestrator + Reasoning Engine:** The agents in `app/agents/` remain the core intelligence. They decide *when* to call various internal services, *what* data to pass, how to *interpret* the results, and how to *combine* information from multiple sources (e.g., database, LLM responses).
* **Workflow Example (ResumeTailor Agent in `app/agents/resume_tailor.py`):**
    1. Receive Trigger (e.g., Job ID, User ID, resume file) from an API endpoint.
    2. Call `parsing_service.parse_resume(file)` to extract text and structure from the uploaded resume.
    3. Call `parsing_service.parse_job_description(job_desc_text_or_url)` to get structured job details.
    4. Call `db_service.store_parsed_resume(...)` and `db_service.store_parsed_job(...)` to save the initial structured data.
    5. Retrieve relevant user profile information or past successful applications from `db_service`.
    6. Prepare a detailed prompt for the `llm_service.generate_tailored_text(...)` method, including:
        * Structured Job Requirements from `parsing_service`.
        * Structured User Resume data from `parsing_service` and `db_service`.
        * Instructions to synthesize a tailored resume, emphasizing specific skills/experiences.
        * Target output structure (potentially guided by Pydantic models like `app/models/resume_model.py` or `app/models/api_models.py`).
    7. Receive the LLM's response from `llm_service`.
    8. Validate/parse the LLM response. Handle potential errors (e.g., retry with modified prompt).
    9. Call `db_service.store_tailored_resume(...)` to save the final output.
    10. Return the tailored resume content or a success indicator to the API layer.

    This workflow occurs through direct Python calls within the single application process.
* **Handling Multiple Resumes/Complex Profiles:** The agent logic must intelligently merge information if a user has multiple resume versions or extensive history. This might involve:
  * Prioritizing experiences that directly match job requirements (identified via LLM analysis or keyword matching within the agent).
  * Using the `llm_service` to synthesize a comprehensive professional summary before tailoring.
  * Building a unified user profile representation within the agent or using `db_service` to store and retrieve a canonical version.
* **Prompt Engineering:** Crafting effective prompts for `llm_service` remains critical. Prompts are stored in `app/prompts/` and loaded by the agents or LLM service.

## 3.3. Ensuring Observability with Logging/Tracing (Simplified MVP) 🪵📚📡

* **Instrumentation:**
  * **Main Application (`app/main.py`):** If using a library like `Logfire` or standard OpenTelemetry, instrument the FastAPI app: `logfire.instrument_fastapi(app)` or equivalent OTel setup. This captures API requests and can trace calls to internal services if they are also instrumented or if auto-instrumentation is effective.
* **Tracing:** With a single-process application, tracing primarily helps understand the flow and performance of requests through different internal modules (API layer -> agents -> services). Context propagation is handled within the process by the tracing library.
* **Logging:** Structured logging (e.g., using `loguru` or the standard `logging` module) should be configured centrally (e.g., in `app/core/config.py` or `app/main.py`) to provide detailed operational logs. This helps in debugging and monitoring application behavior.
* **Goal:** Clear visibility into request handling, agent decision-making, service interactions, and any errors encountered within the application.
