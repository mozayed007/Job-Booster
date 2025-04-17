# Job_Booster

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)] [![FastAPI](https://img.shields.io/badge/fastapi-%3E%3D0.75-green)] [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)]

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Overview

Job_Booster automates and optimizes your job applications by:

- Parsing resumes & job postings from PDF/DOCX/text/URLs (with OCR support).
- Building a Knowledge Graph of skills, projects, companies.
- Synthesizing a tailored resume via LLMs.
- Generating match scores & gap‑analysis.
- Producing a personalized cover letter.

## Features

- **Intelligent Parsing**: PDF, Word, plain text & OCR.
- **Knowledge Graph Construction**: Semantic relationships (skills, projects, companies).
- **Resume Synthesis**: Context‑aware, model‑validated output.
- **Matching & Analysis**: Embeddings + graph queries for scores & feedback.
- **Cover Letter Generation**: Personalized, high‑impact letters.

## Architecture

![Architecture Diagram](docs/architecture.png)  

1. **FastAPI Backend** hosts Pydantic‑AI agents  
2. **Standard MCP Servers** (`fetch`, `llm`, `embed`, `sqlite`, `memory`, `vector‑memory`) run as separate processes  
3. **Custom Parser Server** (FastAPI + OCR, Word/PDF logic)  
4. **Common Library** for shared Pydantic models  
5. **Docker Compose** orchestrates backend, parser & data stores  

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, Pydantic, Pydantic‑AI  
- **MCP SDK**: `modelcontextprotocol/python-sdk`  
- **Servers**: Custom & standard MCP servers (launched via `run_servers.py`)  
- **Data Stores**: SQLite, graph DB (via `memory` server), vector store (ChromaDB/Pinecone)  
- **Observability**: Logfire & OpenTelemetry  
- **Containerization**: Docker & Docker Compose  

## Getting Started

### Prerequisites

- Python 3.9+  
- Docker & Docker Compose  
- (Optional) `venv` or `conda` for isolation  

### Installation

```bash
# clone the repo
git clone https://github.com/<your‑org>/Job_Booster.git
cd Job_Booster

# create venv & install
python -m venv .venv
source .venv/bin/activate   # mac/linux
.\.venv\Scripts\activate    # windows
pip install -r requirements.txt

# install common lib
pip install -e common/src/common
```

### Launch Services

```bash
# start backend & parser via Docker Compose
docker-compose up -d

# in a separate shell, launch standard MCP servers
python mcp_servers/run_servers.py
```

### Run the App

```bash
# backend runs on http://localhost:8000
curl http://localhost:8000/docs
```

## Usage

1. **Upload resumes:** `POST /upload_resume`  
2. **Process job URL or description:** `POST /process_job_url`  
3. **Get synthesized resume:** `GET /get_synthesized_resume/{jobId}`  
4. **Fetch analysis & feedback:** `GET /get_analysis/{jobId}`  

See OpenAPI docs at `/docs` for full endpoints and schemas.

## Project Structure

```
Job_Booster/
├── backend/                  # FastAPI & agents
├── common/                   # Shared Pydantic models
├── mcp_servers/              # Custom parser & run_servers.py
├── configs/                  # services.yaml
├── docker-compose.yml
├── requirements.txt
├── scripts/                  # DB migrations, utils
├── data/                     # SQLite, KG, vector data
├── outputs/                  # Generated resumes, letters
└── tests/                    # Unit & integration tests
```

## Contributing

1. Fork & clone  
2. Create a feature branch  
3. Write tests & update docs  
4. Submit a PR  

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
