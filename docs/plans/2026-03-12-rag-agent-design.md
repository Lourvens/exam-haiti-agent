# Exam Haiti Agent - Implementation Plan

## Project Overview

- **Project Name**: Exam Haiti Agent
- **Type**: RAG-powered Web Application
- **Core Functionality**: AI agent that helps users find past exam PDFs by topic, year, and subject through natural language queries
- **Target Users**: Students seeking past exam papers

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  API Routes (PDF Upload, Query)                              │
├─────────────────────────────────────────────────────────────┤
│  RAG Graph (LangGraph)                                       │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                    │
│  │ Analyze │ → │ Retrieve│ → │ Generate│                    │
│  └─────────┘   └─────────┘   └─────────┘                    │
├─────────────────────────────────────────────────────────────┤
│  Services: PDF Processor | Vector Store (Chroma) | LLM      │
├─────────────────────────────────────────────────────────────┤
│  Logging: File-based with rotation, auto-save to logs/      │
└─────────────────────────────────────────────────────────────┘
```

---

## Phases

### Phase 1: Foundation & Configuration (Day 1)

**Goal**: Set up project structure, dependencies, logging, and core configuration

**Tasks**:
1.1 Install dependencies (fastapi, langchain, langgraph, chromadb, python-dotenv, pydantic-settings, uvicorn)
1.2 Create `app/config.py` - Pydantic settings for environment variables
1.3 Set up logging system with auto-save to `logs/` folder
1.4 Create `.env.example` template
1.5 Add logging middleware to FastAPI

**Files to Create/Modify**:
- `app/config.py`
- `app/deps.py`
- `logging/config.py`
- `logging/handlers.py`
- `.env.example`
- `pyproject.toml`

**Dependencies**:
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langgraph>=0.2.0",
    "chromadb>=0.5.0",
    "pypdf>=5.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "structlog>=24.0.0",
    "loguru>=0.7.0",
]
```

**Logging Strategy**:
- Use `loguru` for structured logging
- Auto-rotate logs daily (max 30 days retention)
- Logs saved to `logs/app.log`
- Separate log files: `logs/api.log`, `logs/rag.log`, `logs/errors.log`
- Log format: `[{time:YYYY-MM-DD HH:mm:ss}] [{level}] [{name}:{function}:{line}] - {message}`
- Auto-create `logs/` directory on startup

---

### Phase 2: Core Services (Day 2)

**Goal**: Implement PDF processing, Chroma vector store, and LLM configuration

**Tasks**2.1 Implement `services/pdf_processor.py` - Extract text from PDFs
2.2 Implement `db/chroma_client.py` - ChromaDB wrapper with collection management
2.3 Implement `core/llm.py` - LLM factory with configurable provider
2.4 Create `models/document.py` and `models/chunk.py` - Pydantic models

**Files to Create/Modify**:
- `services/pdf_processor.py`
- `db/chroma_client.py`
- `core/llm.py`
- `models/document.py`
- `models/chunk.py`
- `models/exam.py`

**PDF Processing**:
- Use `pypdf` for text extraction
- Extract metadata: title, page_count, file_size
- Store original PDF in `data/pdfs/`

**Chroma Configuration**:
- Collection name: `exam_chunks`
- Metadata fields: `source_file`, `year`, `subject`, `topic`, `page_number`
- Embeddings: OpenAI text-embedding-3-small (configurable)
- Persist to `data/chroma/`

---

### Phase 3: LLM-Based Chunking (Day 3)

**Goal**: Implement intelligent chunking using LLM to identify semantic boundaries

**Tasks**:
3.1 Implement `core/chunking.py` - LLM-based chunking strategy
3.2 Create chunking prompt that identifies: topics, sections, questions
3.3 Add metadata extraction (year, subject from filename or content)
3.4 Implement fallback to traditional chunking if LLM fails

**Files to Create/Modify**:
- `core/chunking.py`
- `services/exam_indexer.py`

**Chunking Strategy**:
- Prompt LLM to identify logical boundaries (topics, sections)
- Max chunk size: ~1000 tokens (configurable)
- Overlap: ~100 tokens for context continuity
- Extract metadata: year, subject, topic tags

---

### Phase 4: RAG Pipeline with LangGraph (Day 4-5)

**Goal**: Build the LangGraph state graph for RAG orchestration

**Tasks**:
4.1 Implement `rag/nodes/analyze.py` - Query analysis (rewrite, expand, determine intent)
4.2 Implement `rag/nodes/retrieve.py` - Retrieve relevant chunks with metadata filtering
4.3 Implement `rag/nodes/generate.py` - Generate response using retrieved context
4.4 Build `rag/graph.py` - LangGraph state machine
4.5 Create `rag/chains/retrieval.py` and `rag/chains/qa.py`

**Files to Create/Modify**:
- `rag/nodes/analyze.py`
- `rag/nodes/retrieve.py`
- `rag/nodes/generate.py`
- `rag/graph.py`
- `rag/chains/retrieval.py`
- `rag/chains/qa.py`

**LangGraph State**:
```python
class RAGState(TypedDict):
    query: str
    analyzed_query: str
    intent: str  # "compare", "find_by_topic", "find_by_year", etc.
    filters: dict  # year, subject filters
    documents: list[Document]
    context: str
    answer: str
    sources: list[str]
```

**Node Flow**:
```
analyze_query → retrieve_docs → generate_answer
```

---

### Phase 5: API Endpoints (Day 6)

**Goal**: Create FastAPI endpoints for PDF upload and querying

**Tasks**:
5.1 Implement `api/routes/pdfs.py` - Upload and list PDFs
5.2 Implement `api/routes/query.py` - Query endpoint with streaming
5.3 Create request/response schemas in `api/schemas/`
5.4 Add error handling and validation

**Files to Create/Modify**:
- `api/routes/pdfs.py`
- `api/routes/query.py`
- `api/schemas/pdf.py`
- `api/schemas/query.py`
- `app/main.py`

**API Endpoints**:
- `POST /api/v1/pdfs/upload` - Upload PDF, process and index
- `GET /api/v1/pdfs` - List uploaded PDFs
- `DELETE /api/v1/pdfs/{id}` - Delete PDF and its chunks
- `POST /api/v1/query` - Query the RAG system
- `GET /api/v1/query/stream` - Streaming query response

---

### Phase 6: Testing & Refinement (Day 7)

**Goal**: Test the complete pipeline and fix issues

**Tasks**:
6.1 Write unit tests for services
6.2 Write integration tests for API
6.3 Test RAG pipeline end-to-end
6.4 Optimize chunking and retrieval
6.5 Add error recovery mechanisms

**Files to Create/Modify**:
- `tests/conftest.py`
- `tests/test_services/`
- `tests/test_api/`
- `tests/test_rag/`

---

## Implementation Order

```
Phase 1: Foundation → Phase 2: Core → Phase 3: Chunking → Phase 4: RAG → Phase 5: API → Phase 6: Testing
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph over LangChain Chains | Better state management, debugging, and flexibility for complex flows |
| LLM-based chunking | More intelligent than fixed-size, captures semantic boundaries |
| Chroma over other vector stores | Lightweight, Python-native, local persistence |
| Pydantic Settings | Type-safe configuration management |
| Loguru | Simpler API, auto-rotation, structured logging |

---

## Future Considerations (Not in Scope)

- User authentication
- Multi-modal PDF support (images, tables)
- Re-ranking pipeline
- WebSocket for real-time updates
- Frontend React app
