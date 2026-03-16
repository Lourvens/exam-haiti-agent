# Unified Ingestion Pipeline Integration

## Overview

This document describes the integration between the ingestion pipeline (PDF → Chunks → Chroma) and the Neo4j graph builder.

## Architecture

### Previous Architecture (Two-Step)

```
Step 1: IngestionPipeline
PDF → LangGraphChunkingEngine → Chunks → Chroma

Step 2: Neo4jGraphBuilder (separate)
Chroma → Read chunks → Create graph nodes
```

### New Architecture (Unified Pipeline)

```
UnifiedIngestionPipeline
├── PDF
├── LangGraphChunkingEngine → Chunks
├── Chroma (vector store)
└── Neo4j (optional, can sync during or after ingestion)
```

## Files

| File | Purpose |
|------|---------|
| `services/unified_pipeline.py` | Main unified pipeline implementation |
| `services/ingestion_pipeline.py` | Original Chroma-only pipeline |
| `services/graph_builder.py` | Neo4j graph builder (reads from Chroma) |
| `services/graph_query.py` | Query Neo4j graph |

## Usage

### Basic Usage (Chroma only)

```python
from langchain_openai import ChatOpenAI
from services import UnifiedIngestionPipeline

# Create LLM client
llm = ChatOpenAI(model="gpt-4o-mini")

# Create pipeline
pipeline = UnifiedIngestionPipeline(llm_client=llm, enable_neo4j=False)

# Ingest PDF
result = pipeline.ingest_pdf("exams/math_2023.pdf")

print(f"Status: {result.status}")
print(f"Chunks stored: {result.chunks_stored}")
```

### With Neo4j Sync (during ingestion)

```python
from services import UnifiedIngestionPipeline

pipeline = UnifiedIngestionPipeline(
    llm_client=llm,
    enable_neo4j=True
)

# Ingest and immediately sync to graph
result = pipeline.ingest_pdf(
    "exams/math_2023.pdf",
    sync_to_graph=True
)

print(f"Graph nodes created: {result.graph_nodes_created}")
```

### Batch Ingestion with Post-Sync

```python
# Ingest all PDFs without graph sync
pipeline = UnifiedIngestionPipeline(llm_client=llm, enable_neo4j=True)

results = pipeline.ingest_directory(
    "exams/",
    sync_to_graph=False  # Don't sync during each ingest
)

# Then bulk sync all to Neo4j
sync_result = pipeline.sync_all_to_graph()
print(f"Synced {sync_result['exams_synced']} exams to Neo4j")
```

### Using the convenience function

```python
from services import ingest_with_graph

# One-liner for quick ingestion
result = ingest_with_graph(
    pdf_path="exams/math_2023.pdf",
    llm_client=llm,
    sync_to_graph=True
)
```

### Using the factory function

```python
from services import create_pipeline

pipeline = create_pipeline(
    llm_client=llm,
    enable_neo4j=True,
    collection_name="my_exams"
)
```

## CLI Usage

```bash
# Ingest to Chroma only
python -m services.unified_pipeline data/pdfs

# Ingest and sync to Neo4j
python -m services.unified_pipeline data/pdfs --graph

# Disable Neo4j even if enabled
python -m services.unified_pipeline data/pdfs --no-graph
```

## Configuration

The unified pipeline inherits settings from `app.config`:

- `chroma_collection_name` - Chroma collection name
- `chroma_persist_directory` - Chroma storage path
- `neo4j_enabled` - Whether Neo4j is enabled
- `neo4j_uri`, `neo4j_user`, `neo4j_password` - Neo4j connection
- `save_chunks_to_file` - Whether to save chunks JSON

## Design Decisions

### Why Unified Pipeline?

1. **Single Pass**: Process PDF once, store in both Chroma and Neo4j
2. **Efficiency**: No need to re-read from Chroma for graph creation
3. **Flexibility**: Can use Chroma-only or Chroma+Neo4j
4. **Optional Neo4j**: Disable graph sync when not needed

### Why Keep Separate Services?

The original `IngestionPipeline` and `Neo4jGraphBuilder` are kept for:

1. **Backward compatibility**: Existing code continues to work
2. **Standalone graph sync**: Can re-sync from Chroma without re-ingesting
3. **Independent scaling**: Use each component separately if needed

### Graph Sync Options

| Option | When to Use |
|--------|-------------|
| `sync_to_graph=True` in `ingest_pdf` | Real-time sync per PDF |
| `sync_all_to_graph()` after batch | Bulk sync after ingestion |
| Separate `Neo4jGraphBuilder` | Manual/full re-sync |

## Integration Benefits

1. **Consistent Data Flow**: Single pipeline ensures consistency
2. **Reduced Redundancy**: Don't reload from Chroma for graph
3. **Unified Configuration**: Single source of truth for settings
4. **Transaction Support**: Can wrap in transaction if needed

## Error Handling

- If Neo4j sync fails, the pipeline continues (doesn't fail ingestion)
- Chunk storage errors will fail the whole operation
- Graph sync failures are logged but non-blocking
