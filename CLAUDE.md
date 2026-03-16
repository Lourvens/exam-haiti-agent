# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Exam Haiti Agent is a RAG-powered exam assistant that processes Haitian Baccalaureate exam PDFs. It uses LangGraph for orchestring the chunking pipeline, Chroma for vector storage, and supports multiple LLM/embedding providers.

## Common Commands

```bash
# Run Streamlit dashboard
uv run streamlit run app.py

# Run FastAPI server
uv run uvicorn app.main:app --reload

# Test chunking on a PDF
uv run ./scripts/test_chunking.py [pdf_path] [model]

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_chunking.py::test_function_name -v

# Sync Chroma to Neo4j graph
uv run python scripts/sync_graph.py
uv run python scripts/sync_graph.py --reset  # Reset database first
```

## Configuration

All configuration is managed via environment variables in `.env` file or environment. Key settings in `app/config.py`:

- `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_API_BASE` - OpenAI or compatible API (Groq)
- `HF_TOKEN` / `HF_API_KEY` - HuggingFace for embeddings
- `EMBEDDING_PROVIDER` - "auto", "openai", or "huggingface"
- `CHROMA_PERSIST_DIRECTORY` - Vector store location (default: data/chroma)
- `SAVE_CHUNKS_TO_FILE` - Save chunks to JSON (default: true)
- `CHUNKS_OUTPUT_PATH` - Where to save chunks (default: data/chunks)
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` / `NEO4J_ENABLED` - Neo4j graph database

## Architecture

### Core Components

- **app/main.py** - FastAPI entry point with CORS and logging middleware
- **app/config.py** - Pydantic Settings with auto-detection for embeddings provider
- **app.py** - Streamlit dashboard (Dashboard, Ingest, Search tabs)
- **services/ingestion_pipeline.py** - PDF → Chunk → Embed → Chroma pipeline
- **services/pdf_processor.py** - PDF text extraction using pymupdf
- **services/pdf_analyzer.py** - PDF layout analysis (detects two-column layouts)
- **core/chunking_graph.py** - LangGraph-based chunking with state management
- **core/chunking_strategy.py** - Subject-specific chunking prompts
- **models/chunk.py** - Pydantic models for chunk data
- **models/graph_nodes.py** - Neo4j node models (Exam, Section, Question, SubQuestion, Passage, Instruction)
- **services/graph_builder.py** - Sync from Chroma to Neo4j
- **services/graph_query.py** - Query Neo4j graph (get exam structure, navigate questions, search by topic)

### Data Flow

1. PDF uploaded → PDFProcessor extracts text (handles two-column layouts)
2. Text → LangGraphChunkingEngine splits into sections → LLM extracts chunks with metadata
3. Chunks → EmbeddingProvider creates embeddings → Chroma stores with metadata
4. Search → Chroma similarity search → Results returned

### Key Files

- `core/chunking_graph.py` - Uses `with_structured_output(ChunkResponse, method="json_schema")` for LLM parsing
- `services/ingestion_pipeline.py` - `EmbeddingProvider` class handles multi-provider embeddings
- `app/config.py` - `effective_embedding_provider` property auto-detects available provider
- `app.py` - Streamlit dashboard with tabs for Dashboard, Ingest, Search

## Dependencies

- langgraph>=0.2.0 - Graph-based LLM orchestration
- langchain-chroma>=0.1.0 - Vector store
- pymupdf>=1.25.0 - PDF processing
- pydantic>=2.10.0 - Data validation
- loguru>=0.7.0 - Logging
- neo4j>=5.0.0 - Graph database driver
