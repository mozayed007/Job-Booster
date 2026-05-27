---
type: personal
status: active
topic: personal
date-created: 2026-03-06
tags: [personal]
---

# Mohamed Zayed Ahmed

**Contact Information**  
+201284907633  
<moh.z.ahmed007@gmail.com>  
[linkedin.com/in/mozayed007](https://linkedin.com/in/mozayed007)  
[github.com/mozayed007](https://github.com/mozayed007)

## Experience

### Sprints AI

**Cairo, EG**  
**Research Engineer - R&D**  
*Sep 2025 - Present*  

- Architected and implemented a multi-tenant AI Learning Companion platform with production FastAPI services, org-scoped authentication, Supabase/Postgres persistence, Qdrant retrieval, and Redis-backed state management.  
- Built a precision content-ingestion pipeline for videos, PDFs, code, markdown, and curriculum maps, preserving timestamps, spatial coordinates, line ranges, and hierarchy metadata to support exact citations and navigation.  
- Developed production agent workflows for tutoring, career coaching, study tools, and educational games, combining persona-based orchestration, curriculum-aware context, hybrid retrieval, and backend-switchable Qdrant/HelixDB search.  
- Implemented neuroscience-inspired memory, guardrails, and resource-safety layers for personalized learning flows, including episodic/semantic/procedural memory, preference recall, and VPS-safe ingestion under constrained infrastructure.

### Dark Entry

**Research Engineer (Contractor)**  
*Jun 2025 - Dec 2025*  

- Architected and delivered three production platforms from zero to production, implementing high-throughput parsing engines, multi-source ingestion pipelines, and internal intelligence systems handling 50+ concurrent data feeds.
- Developed a dual-implementation (Python/Rust) data processing engine with tiered pattern matching, per-pattern timeout guards, and a high-performance Rust port using Rayon and Crossbeam for 3x throughput gains over the Python baseline.
- Engineered an ingestion orchestrator with custom adapters (Telegram/Discord), automated file-type classification, SHA256 content fingerprinting, and Redis-backed queuing for downstream processing stages.
- Built a health-tracking system for 50+ data feeds with automated failure detection, configurable cooldown periods, and self-healing auto-recovery logic, reducing manual intervention by 80%.
- Implemented distributed system patterns including Circuit Breaker state machines, adaptive rate limiters with sliding windows, and semaphore-based concurrency control for external API integrations.
- Refactored legacy monolithic services into modular FastAPI architectures, reducing database query volume by 70% via bulk operations and memory-efficient NDJSON streaming for multi-terabyte datasets.
- Hardened production infrastructure using Docker/Compose, Celery/Redis task orchestration, and structured observability with Prometheus metrics and OpenTelemetry tracing.

### Freelance Consulting & Contracts

**Remote**  
**ML Engineer (part-time) - (selected projects alongside full-time roles)**  
*Sep 2023 - Present*  

- Architected a multi-agent research framework using MCP servers and sequential pipelines to orchestrate autonomous information gathering and synthesis workflows.
- Designed and built an autonomous NER pipeline for unstructured data using spaCy and transformer models, featuring responsible AI guardrails, continuous fine-tuning via active learning, and automated ingestion.
- Developed and benchmarked oblique decision tree (ODT) controllers for pharmaceutical process control, extracting explicit control laws and comparing learned decision regions against MPC baselines.
- Built a pharmaceutical process optimization framework using GP, DKL, BART, and CVAE models for experiment selection, design-space analysis, and inverse recipe generation.
- Implemented a multi-process async benchmark system (for Stakpak) to evaluate and optimize LLMs, boosting experimentation velocity by 3x and enabling seamless provider switching across OpenAI, Anthropic, GDM and open-source models.

### Proteinea

**Cairo, EG**  
**Deep Learning Intern**  
*Aug 2022 - Nov 2022*  

- Developed initial T5-based models for antigen-antibody interactions, laying foundation for graduation thesis that later surpassed SoTA baselines.  
- Automated evaluation pipelines and created TensorBoard visualizations, reducing analysis time by 30%.

## Projects

### Antigen-Antibody Translation/Generation - PyTorch, HuggingFace, T5, Pandas, AWS

**Graduation Research Thesis**  

- Developed a custom T5 Transformer that achieved 10% higher performance than 2022 SoTA baselines on the SABDAB dataset (building on insights from Proteinea internship) using AWS NVIDIA A10G GPUs.  
- Enabled real-time monitoring with TensorBoard dashboards and facilitated team collaboration using Termius Vault and Tmux.

### Multi-Agent Research System - Google ADK, Pydantic, Asyncio, FastAPI, Gradio

- Migrated a research workflow to Google's Agent Development Kit (ADK), creating a SequentialAgent pipeline for data collection, analysis, and report synthesis.  
- Integrated external APIs (BraveSearch, ArXiv, Wikipedia) and SQLite persistence to enhance system modularity and data gathering capabilities.  
- Drafted architecture diagrams and communication patterns to streamline development and ensure scalability.

### LiveMem / THEN (Independent Research) - PyTorch, nanochat, NumPy, Attention Hooks

- Architected a stateful "live memory" extension for `nanochat` (`THEN` architecture) that decouples weight training from post-training episodic memory ingestion and query-time recall.
- Implemented a disk-tiered memory manager using `numpy.memmap` and chunked top-k retrieval to stream long-horizon traces from disk with bounded device-memory usage.  
- Built ingestion and query pipelines for frozen-model memory population and stateful recall, including persistence validation and synthetic long-horizon episode generation for benchmarking.

## Skills

**Programming Languages:** Python (Advanced), Rust (Intermediate), C++ (learning CUDA), Triton.

**Frameworks & Libraries:** PyTorch, TensorFlow, FastAPI, SQLAlchemy, Celery, Redis, Scrapy, Selenium, Playwright, Pydantic, Pandas, NumPy, Hugging Face, Scikit-Learn, OpenTelemetry, Prometheus, structlog

**Domain skills:** Distributed Systems, System Architecture, ML/DL, NLP (NER, LLMs, RAG), Computer Vision, Generative AI, Statistical Inference, Data Analysis, Vector Databases (Qdrant, Milvus)

**Tools & Platforms:** Git, Docker, AWS, GCP, Azure, Ollama, Linux, WSL, SQLite, REST APIs, Kaggle

## Education

**University of Science and Technology - Zewail City**  
**Giza, EG**  
**Bachelor of Science, Communication and Information Engineering**  
*Jun 2024*
