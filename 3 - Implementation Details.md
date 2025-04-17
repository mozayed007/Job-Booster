
# 🧩 Job_Booster: Core Implementation Details

## 5.1. Leveraging the MCP Ecosystem ⚙️

* **`MCP Python SDK` Usage:** 🐍 Central to agent-server interaction via the `MCPClientFactory` in the backend.
* **Standard Server Launch & Management:** **[Update]**
  * **Source:** Standard server code is included in the project (e.g., via submodule in `mcp_servers/standard_servers/modelcontextprotocol_servers_src/`).
  * **Launch Script (`run_servers.py`):** A Python script is responsible for:
    * Reading configuration (ports, keys, paths) for each standard server from `configs/services.yaml` or environment variables.
    * Importing the main application/entry point for each standard server (e.g., `from modelcontextprotocol_servers_src.fetch.app import main as fetch_main`).
    * Launching each server as a separate process using `multiprocessing.Process` or `subprocess.Popen`. Requires careful handling of arguments, environment variables, and process lifecycle (startup, shutdown).
    * **Dependency Hell:** Managing dependencies listed in `mcp_servers/requirements_servers.txt` for all servers simultaneously is a major challenge. Using separate virtual environments per server, managed by the script, adds complexity.
  * **Configuration:** Each server process needs its environment correctly set up by `run_servers.py`.
* **Custom `mcp-parser-server` Rationale & Design:** 🧩 (Same rationale, likely still run as a container via Docker Compose for simplicity).
* **`sqlite` Server Usage:** 🗄️ Launched as a Python process via `run_servers.py`. Needs the path to the SQLite DB file configured. Accessed via SDK client.
* **`memory` (KG) Server Usage:** 🧠 Launched as a Python process via `run_servers.py`. Needs configuration for its backend store. Accessed via SDK client.
* **Vector Storage Decision (`vector-memory` vs. Direct):** 📉 Evaluation still needed. If `vector-memory` is used, it's launched via `run_servers.py`. If direct, the backend uses the DB SDK directly.

## 5.2. Agent Intelligence & Orchestration 🤖🔥

* **Agent = Orchestrator + Reasoning Engine:** The Pydantic-AI agents are not just calling tools; they are deciding *when* to call them, *what* context to provide, how to *interpret* the results, and how to *combine* information from multiple sources (`sqlite`, `memory`, `llm`, `vector-memory`).
* **Workflow Example (Synthesizer Agent):**
    1. Receive Trigger (Job ID, User ID).
    2. Query `sqlite` (via SDK) for parsed Job Desc schema.
    3. Query `sqlite` & `memory` (via SDK) for relevant User skills/experience based on Job Desc keywords/entities.
    4. Prepare detailed prompt for `llm` (via SDK) including:
        * Job Requirements.
        * Relevant user data retrieved from KG/SQLite (potentially summarized).
        * Instructions to synthesize a tailored resume, emphasizing specific skills/experiences.
        * Target output structure (mentioning the `Resume` model fields).
    5. Receive LLM response.
    6. Validate/parse the LLM response into the `Resume` Pydantic model. Handle potential validation errors (e.g., instruct LLM to retry with corrections).
    7. Store/return the synthesized `Resume` object.
* **Handling Multiple Resumes:** The core synthesis logic must intelligently merge information. This could involve:
  * Using timestamps/recency if available.
  * Prioritizing experiences explicitly matching job requirements (identified via KG/Vector search/LLM analysis).
  * Asking the LLM to resolve conflicting information based on context.
  * Building a comprehensive profile in the KG/SQLite first, then synthesizing from that unified view.
* **Prompt Engineering:** Crafting effective prompts for the `llm` server (passed via the SDK client) is critical for quality synthesis, analysis, and generation. Store prompts potentially in `backend/agents/prompts`.

## 5.3. Ensuring Observability with Logfire 🪵📡

* **Instrumentation:**
  * **Backend:** `logfire.instrument_fastapi(app)`, SDK instrumentation.
  * **Custom Parser Server:** `logfire.instrument_fastapi(app)`.
  * **Standard Servers (Python Processes):** **[Update] The `run_servers.py` script OR the entry point of each standard server *must* call `logfire.configure()` with a unique `service_name` and apply necessary instrumentation (e.g., `logfire.instrument_fastapi`) before starting the server's web framework (e.g., Uvicorn/FastAPI).** This requires modifying/wrapping the standard server startup if not already supported.
* **Tracing:** SDK handles propagation *if* configured correctly in *all* participating processes (Backend + All Server Processes).
* **Logging:** Structured logging needed in Backend, Custom Parser, and potentially adding more within standard servers if needed.
* **Goal:** Full end-to-end trace visibility, requiring successful instrumentation across all Python processes.
