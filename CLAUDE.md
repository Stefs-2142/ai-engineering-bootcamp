# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the AI Engineering Bootcamp repository - an educational project focused on building RAG (Retrieval-Augmented Generation) systems with vector databases, LLM APIs, and evaluation frameworks. The project includes a FastAPI backend, Streamlit chatbot UI, and Qdrant vector database for product recommendations based on Amazon dataset.

## Architecture

### Workspace Structure
This is a **uv workspace** monorepo with three main components:
- `apps/api/` - FastAPI backend with RAG pipeline and evaluation tools
- `apps/chatbot_ui/` - Streamlit frontend chatbot interface
- `notebooks/` - Jupyter notebooks for learning and experimentation
  - `notebooks/prerequisites/` - LLM API basics
  - `notebooks/week_1/` - RAG pipeline development, dataset exploration, and evaluation

### Key Components

**Hybrid RAG + SQL Agent Architecture**:
```
┌─────────────────┐    ┌─────────────────────────────────────┐
│   Streamlit UI  │ -> │         Router Agent                │
│   (Chat)        │    │   (LangGraph - intent detection)    │
└─────────────────┘    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    v                 v                 v
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │  RAG Tool    │  │  SQL Tool    │  │  Hybrid Tool │
            │  (Qdrant)    │  │  (Postgres)  │  │  (SQL→RAG)   │
            └──────────────┘  └──────────────┘  └──────────────┘
```

**Agent Modules** (`apps/api/src/api/agents/`):
- `retrieval_generation.py` - Pure semantic RAG pipeline with Qdrant
- `sql_agent.py` - SQL query generation and execution for structured data
- `hybrid.py` - Combined SQL filtering + RAG semantic search
- `router.py` - LangGraph-based intent classification (RAG/SQL/Hybrid)

**RAG Pipeline** (`apps/api/src/api/agents/retrieval_generation.py`):
- Vector-based retrieval using Qdrant with OpenAI embeddings (text-embedding-3-small)
- LLM generation using OpenAI's gpt-5-nano with reasoning capabilities
- Complete LangSmith tracing throughout (embedding, retrieval, prompt formatting, generation)
- Collection name: `Amazon-items-collection-00`
- Retrieves product descriptions, ratings, and IDs for shopping assistant queries

**API Service** (`apps/api/`):
- FastAPI application with CORS middleware and request ID tracking
- POST `/chat` - Smart endpoint with auto-routing to RAG/SQL/Hybrid
- POST `/rag` - Direct RAG pipeline access
- POST `/sql` - Direct SQL query access
- Connected to local Qdrant instance (http://localhost:6333) and PostgreSQL

**UI Service** (`apps/chatbot_ui/`):
- Streamlit chat interface calling the smart `/chat` endpoint
- Shows intent detection badges (Semantic Search / SQL Query / Hybrid)
- Displays extracted filters for hybrid queries
- Session-based message history

**Services Stack**:
- Qdrant vector database (ports 6333, 6334) with persistent storage in `./qdrant_storage`
- PostgreSQL database (port 5432) with persistent storage in `./postgres_data`
- FastAPI on port 8000
- Streamlit on port 8501

## Common Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Copy environment template and configure API keys
cp env.example .env
# Edit .env to add: OPENAI_API_KEY, GOOGLE_API_KEY, GROQ_API_KEY
```

### Running the Application
```bash
# Start all services (Qdrant, PostgreSQL, API, Streamlit)
make run-docker-compose

# Access points:
# - Streamlit UI: http://localhost:8501
# - FastAPI docs: http://localhost:8000/docs
# - Qdrant: http://localhost:6333
# - PostgreSQL: localhost:5432

# After first run, load data into PostgreSQL:
make run-etl-postgres
```

### PostgreSQL Commands
```bash
# Open PostgreSQL shell
make postgres-shell

# Check product count in database
make postgres-count
```

### Evaluation
```bash
# Run retriever evaluation with RAGAS metrics
make run-evals-retriever

# Evaluates against "rag-evaluation-dataset" in LangSmith
# Metrics: Faithfulness, ResponseRelevancy, IDBasedContextPrecision, IDBasedContextRecall
# Results logged to LangSmith with "retriever" experiment prefix
```

### Notebook Management
```bash
# Clear notebook outputs before committing
make clean-notebook-outputs
```

## Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - For embeddings (text-embedding-3-small) and generation (gpt-5-nano)
- `GOOGLE_API_KEY` - For Google Gemini access
- `GROQ_API_KEY` - For Groq models
- `LANGCHAIN_API_KEY` - For LangSmith tracing (automatically used if present)
- `LANGCHAIN_TRACING_V2` - Enable LangSmith tracing
- `LANGCHAIN_PROJECT` - LangSmith project name

PostgreSQL (auto-configured in docker-compose, override for local development):
- `POSTGRES_HOST` - PostgreSQL host (default: postgres in docker, localhost locally)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_DB` - Database name (default: amazon_products)
- `POSTGRES_USER` - Database user (default: bootcamp)
- `POSTGRES_PASSWORD` - Database password (default: bootcamp)

## Python Version & Package Manager

- **Python 3.12+** required (see `.python-version`)
- **uv** is the package manager (not pip or poetry)
- Use `uv sync` to install dependencies
- Use `uv run` to execute Python scripts with proper environment

## Git Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <description>
```

Types:
- `feat` - new feature
- `fix` - bug fix
- `docs` - documentation changes
- `style` - formatting, no code change
- `refactor` - code restructuring without behavior change
- `test` - adding/updating tests
- `chore` - maintenance tasks, dependencies

Examples:
```
feat: add user authentication endpoint
fix: resolve memory leak in RAG pipeline
docs: update API documentation
```

## Important Implementation Details

### Running Evaluations
The evaluation script requires special PYTHONPATH setup:
```bash
PYTHONPATH=${PWD}/apps/api:${PWD}/apps/api/src:$$PYTHONPATH:${PWD} uv run --env-file .env python -m evals.eval_retriever
```

### LangSmith Integration
All RAG pipeline functions use `@traceable` decorators for comprehensive observability:
- Embedding operations track token usage
- Retrieval operations are traced as retriever type
- Prompt formatting tracked separately
- LLM calls include usage metadata (input/output/total tokens)

### Data Citation
This repository uses Amazon product data from the paper "Bridging Language and Items for Retrieval and Recommendation" (Hou et al., 2024). If extending or using this work, cite appropriately.
