# 🏗️ Job_Booster: Detailed Architecture & System Structure

## 3.1 System Components & Responsibilities 🗺️

This architecture distributes responsibilities across specialized components, interacting via the MCP standard.

1. **FastAPI Backend (Orchestrator & Agent Host):**
    * **Role:** The central nervous system. It receives user requests through its REST API, manages the overall job application workflow state (e.g., which job is being processed for which user), hosts and executes the Pydantic-AI agents, and orchestrates the sequence of calls to various MCP servers using the `MCP Python SDK`.
    * **Key Internal Modules:**
        * `api/`: 🌐 Defines user-facing endpoints (e.g., `/upload_resume`, `/process_job_url`, `/get_synthesized_resume`, `/get_analysis`). Handles request validation using Pydantic models.
        * `agents/`: 🤖 Contains the core intelligence. Includes agent definitions (e.g., `KnowledgeBuilderAgent`, `ResumeSynthesizerAgent`, `AnalysisAgent`) using Pydantic-AI. These agents manage their internal state and implement the complex reasoning for parsing orchestration, KG building, synthesis, analysis, and generation by leveraging the SDK clients.
        * `clients/`: 🐍 Provides configured instances of MCP clients obtained via the `modelcontextprotocol/python-sdk`. A factory pattern (`mcp_client_factory.py`) centralizes client creation and configuration (e.g., setting server base URLs from config). This abstracts the raw SDK usage from the agents.
        * `core/`: ⚙️ Handles application-wide concerns like loading configuration (`configs/services.yaml`), setting up Logfire/OpenTelemetry instrumentation, and defining shared utilities or exception handling.
        * `models/`: 📝 Defines Pydantic models specifically for the backend's external API layer (request/response bodies).

2. **MCP Servers (Capability Providers):** 🛠️
    * **Standard Servers (from `modelcontextprotocol/servers`):** `fetch` 🌐, `browser` 🕸️, `llm` 💬, `embed` 📐, `sqlite` 🗄️, `memory` 🧠, `vector-memory` 📉 (**Evaluate**). **[Update] These are run as separate Python processes, launched and managed by a dedicated Python script (e.g., `run_servers.py`). Each process loads its specific configuration (port, keys, paths) likely via environment variables or dedicated config sections.** Source code potentially included via Git submodule or installed packages.
    * **Custom Servers:**
        * `mcp-parser-server` 🧩: Built specifically for Job_Booster. Runs as a separate service (likely a container managed by Docker Compose). Exposes its API for parsing.

3. **Data Storage Services (Backends):** 💾
    * **SQLite Database File:** A persistent file (e.g., mapped via a Docker volume) accessed *exclusively* by the `sqlite` MCP server. Stores structured, normalized data from parsed documents.
    * **Knowledge Graph Store:** The underlying database (e.g., a file, another container running a graph DB) accessed *exclusively* by the `memory` MCP server. Stores semantic relationships.
    * **Vector Store:** The database (e.g., ChromaDB container, Pinecone cloud instance) accessed either by the `vector-memory` MCP server or directly by the Backend service. Stores embeddings for similarity search.

4. **Common Library:** 🧱
    * **Role:** A shared Python package containing definitions used across services, primarily the Backend and the Custom Parser Server. Ensures consistency.
    * **Key Modules:**
        * `models/`: Defines core Pydantic data structures: `Resume`, `JobPosting` (detailed schemas), schemas for data stored in the `sqlite` server (matching table structures), schemas for nodes and edges in the `memory` (KG) server, and potentially shared API request/response schemas for the custom parser.

## 3.2 Communication Flow & Protocols ↔️

* **User Interaction:** Standard HTTPS requests to the FastAPI Backend API.
* **Internal MCP Communication:** Backend agents use the `MCP Python SDK` clients. The SDK translates agent calls into appropriate network requests (likely async HTTP/REST or potentially gRPC, depending on the server implementations) to the target MCP server endpoints defined in the configuration.
  * **Data Format:** Payloads are typically JSON, structured according to Pydantic models defined in `common` or specific to the server's API.
  * **Error Handling:** The SDK should ideally provide standardized ways to handle server errors (e.g., specific exceptions for unavailable servers, bad requests, server-side errors). Agents need robust error handling logic.
  * **Tracing:** The SDK (ideally integrated with Logfire/OpenTelemetry) propagates trace context headers (`traceparent`) automatically with each outgoing request.

## 3.3 Observability Strategy 🕵️‍♀️

* **Logfire/OpenTelemetry:** Configured in the **FastAPI Backend**, the **Custom `mcp-parser-server`**, **and programmatically within the Python script that launches *each standard MCP server process***. The SDK should handle trace propagation, but instrumentation must be initialized for every server process.
* **Centralized Viewing:** 📈 Logs and traces from all services/processes correlated in Logfire UI / Grafana. Service names must be distinct for clarity.
* **Metrics:** ⏱️ Prometheus metrics exposed by instrumented services/processes. Python servers will need instrumentation added if not already present.

## 4. Detailed Project File Structure 📁

## 4. Project File Structure 📁

```plaintext
Job_Booster/
├── backend/                      # Main FastAPI application (Orchestrator & Agent Host)
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, Logfire setup, middleware
│   │   ├── api/                  # User-facing REST API endpoints (routers, e.g., ingest, synthesize)
│   │   ├── agents/               # Agent logic (using Pydantic-AI)
│   │   │   ├── __init__.py
│   │   │   └── impl/             # Agent implementations (e.g., knowledge_builder.py, synthesizer.py, analyzer.py)
│   │   │   └── prompts/          # Directory for storing reusable prompt templates (e.g., synthesize_prompt.txt)
│   │   ├── clients/              # Configures & provides access to MCP SDK clients
│   │   │   ├── __init__.py
│   │   │   └── mcp_client_factory.py # Central place to get configured SDK client instances (using modelcontextprotocol-sdk)
│   │   ├── core/                 # App config loading (services.yaml), telemetry setup (Logfire/OTel), global utils
│   │   └── models/               # Pydantic models specifically for the external API layer (e.g., SynthesizeRequest, AnalysisResponse)
│   ├── Dockerfile                # Builds the backend service container (useful even if standard servers run via Python)
│   └── requirements.txt          # Python dependencies for the backend: fastapi, pydantic, pydantic-ai, logfire, modelcontextprotocol-sdk, [vector-db-sdk if direct]
│
├── mcp_servers/                  # Configuration/code related to MCP Servers
│   ├── mcp_parser_server/        # ★ Custom-built parser service ★ (Likely still run via Docker Compose)
│   │   ├── app/                  # FastAPI application for the parser
│   │   │   ├── main.py           # Parser service entry point + Logfire setup
│   │   │   ├── api.py            # Defines the /parse API endpoint logic
│   │   │   ├── logic.py          # Core parsing/OCR implementation details (using pdfminer, python-docx, pytesseract)
│   │   │   └── core/             # Parser-specific config loading, telemetry setup
│   │   ├── Dockerfile            # Builds the custom parser service container
│   │   └── requirements.txt      # Python dependencies for the parser: fastapi, logfire, pdfminer.six, python-docx, pytesseract, Pillow, etc.
│   │
│   ├── standard_servers/         # [New] Location for standard server source & launch logic (if managed via Python)
│   │   ├── modelcontextprotocol_servers_src/ # E.g., Git submodule pointing to `modelcontextprotocol/servers` repo checkout
│   │   └── run_servers.py        # ★ Python script using multiprocessing/subprocess to launch standard server processes (fetch, llm, embed, sqlite, etc.) ★
│   └── requirements_servers.txt  # [New] Combined/managed Python dependencies for ALL standard servers sourced from the repo (⚠️ High Risk of Conflicts!)
│
├── common/                       # Shared Python library (installable package, dependency for backend & custom parser)
│   └── src/common/               # Source directory for the common package
│       ├── __init__.py
│       └── models/               # Shared Pydantic models used across services
│           ├── __init__.py
│           ├── base.py           # Base model configurations (e.g., ORM mode for SQLite models)
│           ├── resume.py         # Detailed structured Resume schema
│           ├── job.py            # Detailed structured JobPosting schema
│           ├── knowledge_graph.py # Schemas for KG nodes (Skill, Company, Project) & edges (USES, REQUIRES, WORKED_AT)
│           ├── sqlite_tables.py  # Pydantic models representing SQLite table structures (for validation/ORM mapping)
│           └── api_schemas.py    # Shared request/response schemas (e.g., ParserRequest, ParserResponse)
│   └── pyproject.toml            # Build configuration (e.g., using PDM, Poetry, or Hatch) for the common library
│
├── configs/                      # Runtime configurations (mounted into containers or read by scripts)
│   └── services.yaml             # Service URLs/ports (ensure no conflicts!), DB paths/connections, API keys, model names, feature flags
│
├── docker-compose.yml            # [Update] Main orchestration file. Defines backend, custom parser, DB backends (VectorDB, KG store if needed).
│                                 # Might define a service to run `run_servers.py` OR might be less central if Python script manages most servers.
├── scripts/                      # Utility scripts (e.g., DB initialization/migration, test data loading, manual KG queries)
├── data/                         # Persistent data volumes mapped here (e.g., SQLite DB file, KG data dir, vector index files if local)
├── outputs/                      # Directory where generated files (resumes, letters) might be stored locally (if needed)
├── requirements.txt              # Top-level development requirements only (e.g., pytest, pre-commit hooks, linters)
└── tests/                        # Automated tests
    ├── backend_tests/            # Unit tests (mocking SDK clients) & integration tests (calling actual APIs) for the backend & agents
    ├── mcp_parser_server_tests/  # Unit & integration tests for the custom parser service
    ├── common_tests/             # Unit tests for the shared common library models/utilities
    ├── integration/              # End-to-end tests simulating full user workflows, requiring multiple services to be running
    └── standard_servers_tests/   # [New] Tests specifically for the `run_servers.py` script (e.g., verifies processes start, basic checks)
```
