# Exam Haiti Agent

A RAG-powered exam assistant that processes Haitian Baccalaureate exam PDFs. Uses LangGraph for orchestrating the chunking pipeline, Chroma for vector storage, and supports multiple LLM/embedding providers.

[![Python](https://img.shields.io/badge/python-3.14+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009970)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Features

- PDF ingestion and processing with layout detection (handles two-column layouts)
- Intelligent chunking using LangGraph with subject-specific strategies
- Hybrid search: Vector similarity (Chroma) + Graph traversal (Neo4j)
- Multiple LLM provider support (OpenAI, Anthropic, Google)
- Auto-detecting embedding providers (OpenAI, HuggingFace)
- Next.js frontend with shadcn/ui for modern UI
- RESTful API with admin authentication

## Architecture

```
                           ┌─────────────────────┐
                           │     Next.js UI      │
                           │   (shadcn/ui)       │
                           └──────────┬──────────┘
                                      │
                                      ▼
                        ┌────────────────────────┐
                        │      FastAPI Backend    │
                        │    http://localhost:8000│
                        └────────────┬───────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
   ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
   │   /admin     │        │   /agent      │        │   /pdfs      │
   │   (auth)     │        │   (query)     │        │   (public)    │
   └───────┬───────┘        └───────┬───────┘        └───────┬───────┘
           │                        │                        │
           ▼                        ▼                        ▼
   ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
   │    Chroma    │        │   LangGraph   │        │  PDF Storage  │
   │  (Vectors)   │        │  (Orchestrate) │        │  (data/pdfs)  │
   └───────┬───────┘        └───────┬───────┘        └───────┬───────┘
           │                        │
           └────────────┬───────────┘
                        ▼
                ┌───────────────┐
                │    Neo4j     │
                │   (Graph)    │
                └───────────────┘
```

## Installation

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) for Python package management
- [bun](https://bun.sh/) for frontend package management
- Neo4j (optional, for graph features)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/exam-haiti-agent.git
cd exam-haiti-agent

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend
bun install
cd ..
```

## Configuration

Create a `.env` file in the project root:

```bash
# Required for LLM features
OPENAI_API_KEY=your_openai_api_key

# Optional: Use alternative LLM providers
# OPENAI_API_BASE=https://api.openai.com/v1  # For compatible APIs like Groq
# ANTHROPIC_API_KEY=your_anthropic_key
# GOOGLE_API_KEY=your_google_key

# Embedding provider (auto-detects if not set)
EMBEDDING_PROVIDER=auto  # Options: auto, openai, huggingface

# Chroma vector store
CHROMA_PERSIST_DIRECTORY=data/chroma

# Neo4j (optional, for graph features)
NEO4J_ENABLED=false
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Admin password for protected endpoints
ADMIN_PASSWORD=your_secure_password
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for LLM and embeddings |
| `OPENAI_MODEL` | gpt-4o-mini | OpenAI model to use |
| `EMBEDDING_PROVIDER` | auto | Embedding provider (auto/openai/huggingface) |
| `CHROMA_PERSIST_DIRECTORY` | data/chroma | Vector store location |
| `NEO4J_ENABLED` | false | Enable Neo4j graph database |
| `ADMIN_PASSWORD` | - | Password for admin endpoints |

## Usage

### Running the Backend

```bash
# Start FastAPI server with auto-reload
uv run uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000` with base path `/api/v1`.

### Running the Frontend

```bash
cd frontend
bun run dev
```

The frontend runs at `http://localhost:3000`.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_chunking.py -v

# Run a specific test
uv run pytest tests/test_chunking.py::test_function_name -v
```

### Testing Chunking on a PDF

```bash
uv run ./scripts/test_chunking.py [pdf_path] [model]
```

### Syncing to Neo4j

```bash
# Sync from Chroma to Neo4j
uv run python scripts/sync_graph.py

# Reset database first, then sync
uv run python scripts/sync_graph.py --reset
```

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root information |
| GET | `/health` | Health check |
| GET | `/api/v1/pdfs` | List available PDFs |
| GET | `/api/v1/pdfs/{exam_id}` | Download PDF file |
| POST | `/api/v1/agent/query` | Query the exam assistant |
| GET | `/api/v1/agent/health` | Agent service health |

### Admin Endpoints (Bearer Auth Required)

Add header: `Authorization: Bearer <ADMIN_PASSWORD>`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/ingest` | Upload and process PDF |
| GET | `/api/v1/admin/chunks` | List chunks from vector store |
| GET | `/api/v1/admin/exams` | List all ingested exams |
| GET | `/api/v1/admin/graph/nodes` | Get Neo4j graph nodes |
| GET | `/api/v1/admin/graph/stats` | Get graph statistics |
| POST | `/api/v1/admin/graph/sync` | Sync Chroma to Neo4j |

### Example: Query the Agent

```bash
curl -X POST http://localhost:8000/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main topics in the 2023 Math exam?",
    "filters": {"subject": "Math", "year": 2023}
  }'
```

### Example: Upload a PDF

```bash
curl -X POST http://localhost:8000/api/v1/admin/ingest \
  -H "Authorization: Bearer your_admin_password" \
  -F "file=@/path/to/exam.pdf"
```

## Project Structure

```
exam-haiti-agent/
├── api/                      # API endpoints
│   ├── admin.py             # Admin endpoints (auth required)
│   ├── agent.py            # Agent query endpoint
│   └── pdf.py              # Public PDF download endpoint
├── app/
│   ├── config.py           # Pydantic settings configuration
│   ├── main.py            # FastAPI application entry point
│   └── deps.py            # FastAPI dependencies
├── core/
│   ├── chunking_graph.py  # LangGraph chunking pipeline
│   ├── chunking_strategy.py   # Subject-specific chunking
│   ├── exam_agent.py     # RAG agent with hybrid search
│   └── graph_extraction_graph.py  # Neo4j extraction
├── models/
│   ├── chunk.py           # Chunk Pydantic models
│   ├── exam.py           # Exam data models
│   └── graph_nodes.py   # Neo4j node models
├── services/
│   ├── ingestion_pipeline.py  # PDF to Chroma pipeline
│   ├── pdf_processor.py      # PDF text extraction (pymupdf)
│   ├── pdf_analyzer.py      # PDF layout analysis
│   ├── graph_builder.py    # Neo4j sync
│   └── agent_tools.py      # LangChain tools for agent
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js app router
│   │   ├── components/   # React components
│   │   ├── features/     # Feature modules
│   │   ├── lib/          # Utilities
│   │   └── types/        # TypeScript types
│   └── package.json
├── docs/                  # Documentation
│   ├── api.md            # API reference
│   ├── chunk_strategy.md # Chunking strategies
│   └── neo4j_graph_implementation.md
├── scripts/
│   ├── test_chunking.py  # Test chunking on a PDF
│   └── sync_graph.py     # Sync Chroma to Neo4j
├── tests/                 # pytest test suite
├── pyproject.toml        # Python dependencies
└── README.md
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| LLM Orchestration | LangGraph |
| Vector Store | Chroma |
| Graph Database | Neo4j |
| PDF Processing | pymupdf |
| Frontend | Next.js 16 |
| UI Components | shadcn/ui |
| Package Manager (Py) | uv |
| Package Manager (JS) | bun |

## License

MIT License - See [LICENSE](LICENSE) for details.
