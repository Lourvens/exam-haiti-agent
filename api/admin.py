"""Admin API for Exam Haiti Agent - PDF ingestion and graph management."""

import io
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

# Load env vars BEFORE importing settings and services
load_dotenv()

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.config import get_settings
from services.ingestion_pipeline import IngestionPipeline


# Security
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate admin password from Bearer token."""
    settings = get_settings()

    if not settings.admin_password:
        raise HTTPException(status_code=500, detail="Admin password not configured")

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    # The token should be the password
    if credentials.credentials != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    return {"authenticated": True}


def get_llm_client():
    """Create LLM client for chunking."""
    from langchain_openai import ChatOpenAI
    from app.config import get_settings

    settings = get_settings()

    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    llm_kwargs = {"model": settings.openai_model, "api_key": settings.openai_api_key}
    if settings.openai_api_base:
        llm_kwargs["base_url"] = settings.openai_api_base

    return ChatOpenAI(**llm_kwargs)


def get_chroma_vectorstore():
    """Get Chroma vector store."""
    from langchain_chroma import Chroma
    from services.ingestion_pipeline import EmbeddingProvider
    from app.config import get_settings

    settings = get_settings()

    embeddings = EmbeddingProvider.create_embeddings()

    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.chroma_persist_directory)
    )


def get_neo4j_driver():
    """Get Neo4j driver."""
    from neo4j import GraphDatabase
    from app.config import get_settings

    settings = get_settings()

    if not settings.neo4j_enabled:
        raise HTTPException(status_code=503, detail="Neo4j is not enabled")

    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )


# Create router
router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/ingest")
async def ingest_pdf(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user)
):
    """
    Upload and ingest a PDF file.

    - Accepts multipart file upload
    - Runs through IngestionPipeline
    - Returns status with chunk count
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file to temp location
    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Create LLM client
        llm = get_llm_client()

        # Create ingestion pipeline
        pipeline = IngestionPipeline(llm_client=llm)

        # Ingest the PDF
        result = pipeline.ingest_pdf(tmp_path)

        return {
            "status": result.get("status", "success"),
            "filename": file.filename,
            "chunks": result.get("chunks", 0),
            "total_in_collection": result.get("total_in_collection", 0),
            "message": result.get("message", "")
        }

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/chunks")
async def get_chunks(
    exam_id: Optional[str] = Query(None, description="Filter by exam ID"),
    limit: int = Query(50, ge=1, le=1000, description="Number of chunks to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _: dict = Depends(get_current_user)
):
    """
    Preview chunks from Chroma.

    - Optional query params: exam_id, limit, offset
    - Returns list of chunks with metadata
    """
    try:
        vectorstore = get_chroma_vectorstore()

        # Build filter
        filter_dict = {}
        if exam_id:
            # Filter by source containing exam_id
            filter_dict = {"source": {"$contains": exam_id}}

        # Get results
        results = vectorstore.get(
            where=filter_dict if filter_dict else None,
            limit=limit,
            offset=offset,
            include=["metadatas", "documents"]
        )

        chunks = []
        for i, (doc, meta) in enumerate(zip(
            results.get("documents", []),
            results.get("metadatas", [])
        )):
            chunks.append({
                "id": results.get("ids", [])[i] if i < len(results.get("ids", [])) else f"chunk_{i}",
                "content": doc[:500] + "..." if len(doc) > 500 else doc,  # Truncate long content
                "metadata": meta
            })

        total_count = vectorstore._collection.count()

        return {
            "chunks": chunks,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to get chunks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")


@router.get("/graph/nodes")
async def get_graph_nodes(
    type: Optional[str] = Query(None, description="Node type: Exam, Question, Concept, Topic, etc."),
    limit: int = Query(100, ge=1, le=1000, description="Number of nodes to return"),
    _: dict = Depends(get_current_user)
):
    """
    Get graph nodes from Neo4j.

    - Query params: type (Exam, Question, Concept, Topic, etc.), limit
    - Returns nodes with properties
    """
    settings = get_settings()

    if not settings.neo4j_enabled:
        raise HTTPException(status_code=503, detail="Neo4j is not enabled")

    driver = get_neo4j_driver()

    try:
        with driver.session(database=settings.neo4j_database) as session:
            # Build query
            if type:
                query = f"MATCH (n:{type}) RETURN n LIMIT {limit}"
            else:
                query = f"MATCH (n) RETURN n LIMIT {limit}"

            result = session.run(query)

            nodes = []
            for record in result:
                node = record["n"]
                nodes.append({
                    "id": node.element_id,
                    "labels": list(node.labels),
                    "properties": dict(node)
                })

            return {
                "nodes": nodes,
                "count": len(nodes),
                "type_filter": type
            }

    except Exception as e:
        logger.error(f"Failed to get graph nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get nodes: {str(e)}")

    finally:
        driver.close()


@router.get("/graph/stats")
async def get_graph_stats(
    _: dict = Depends(get_current_user)
):
    """
    Get graph statistics.

    - Returns counts of each node type and relationship type
    """
    settings = get_settings()

    if not settings.neo4j_enabled:
        raise HTTPException(status_code=503, detail="Neo4j is not enabled")

    driver = get_neo4j_driver()

    try:
        with driver.session(database=settings.neo4j_database) as session:
            # Get node counts by type
            node_query = """
            CALL db.labels() YIELD label
            RETURN label
            """
            labels_result = session.run(node_query)
            labels = [record["label"] for record in labels_result]

            node_counts = {}
            for label in labels:
                count_query = f"MATCH (n:{label}) RETURN count(n) as count"
                result = session.run(count_query)
                node_counts[label] = result.single()["count"]

            # Get relationship counts by type
            rel_query = """
            CALL db.relationshipTypes() YIELD relationshipType
            RETURN relationshipType
            """
            rels_result = session.run(rel_query)
            rel_types = [record["relationshipType"] for record in rels_result]

            rel_counts = {}
            for rel_type in rel_types:
                count_query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
                result = session.run(count_query)
                rel_counts[rel_type] = result.single()["count"]

            return {
                "nodes": node_counts,
                "relationships": rel_counts,
                "total_nodes": sum(node_counts.values()),
                "total_relationships": sum(rel_counts.values())
            }

    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

    finally:
        driver.close()


@router.post("/graph/sync")
async def sync_graph(
    llm: bool = Query(False, description="Enable LLM extraction for entities and relationships"),
    _: dict = Depends(get_current_user)
):
    """
    Run graph sync from Chroma to Neo4j.

    - Query param: llm (bool) - enable LLM extraction
    - Runs sync_from_chroma or sync_from_chroma_llm
    - Returns sync result
    """
    settings = get_settings()

    if not settings.neo4j_enabled:
        raise HTTPException(status_code=503, detail="Neo4j is not enabled")

    # Import here to avoid circular imports
    from services.graph_builder import Neo4jGraphBuilder

    builder = None

    try:
        # Create graph builder
        builder = Neo4jGraphBuilder()

        if llm:
            # Check for LLM provider
            if not settings.has_llm_provider:
                raise HTTPException(
                    status_code=400,
                    detail="LLM provider required for LLM-enhanced sync. Set OPENAI_API_KEY in .env"
                )

            # Create LLM client
            from services.graph_builder import create_llm_client
            llm_client = create_llm_client()

            # Run LLM-enhanced sync
            result = builder.sync_from_chroma_llm(llm_client)
        else:
            # Run standard sync
            result = builder.sync_from_chroma()

        return {
            "status": "success",
            "mode": "llm_enhanced" if llm else "standard",
            "result": result
        }

    except Exception as e:
        logger.error(f"Graph sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

    finally:
        if builder:
            builder.close()


@router.get("/exams")
async def list_exams(
    _: dict = Depends(get_current_user)
):
    """
    List all exams from Chroma.

    - Returns exam metadata from Chroma
    """
    try:
        vectorstore = get_chroma_vectorstore()

        # Get all documents with metadata
        results = vectorstore.get(include=["metadatas"])

        # Extract unique exams from metadata
        exams = {}
        for meta in results.get("metadatas", []):
            source = meta.get("source", "")
            if source:
                # Extract exam_id from source path
                exam_id = Path(source).stem

                if exam_id not in exams:
                    exams[exam_id] = {
                        "exam_id": exam_id,
                        "source": source,
                        "subject": meta.get("subject", ""),
                        "year": meta.get("year", ""),
                        "serie": meta.get("serie", ""),
                        "chunk_count": 0
                    }

                exams[exam_id]["chunk_count"] += 1

        return {
            "exams": list(exams.values()),
            "total": len(exams)
        }

    except Exception as e:
        logger.error(f"Failed to list exams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list exams: {str(e)}")


@router.get("/pdfs/{exam_id}")
async def get_pdf(
    exam_id: str,
    _: dict = Depends(get_current_user)
):
    """
    Download a PDF file by exam ID.

    Args:
        exam_id: The exam ID (e.g., 'Math-NS4-2025-SMP-Graphe')

    Returns:
        PDF file
    """
    settings = get_settings()
    pdf_dir = settings.pdf_storage_path

    # Find PDF matching exam_id
    pdf_files = list(pdf_dir.glob(f"*{exam_id}*.pdf"))

    if not pdf_files:
        # Try without extension
        pdf_files = list(pdf_dir.glob(f"{exam_id}.pdf"))

    if not pdf_files:
        raise HTTPException(status_code=404, detail=f"PDF not found for exam: {exam_id}")

    pdf_path = pdf_files[0]

    return FileResponse(
        path=pdf_path,
        filename=pdf_path.name,
        media_type="application/pdf"
    )


@router.get("/pdfs")
async def list_pdfs(
    _: dict = Depends(get_current_user)
):
    """
    List all available PDF files.

    Returns:
        List of PDF files with metadata
    """
    settings = get_settings()
    pdf_dir = settings.pdf_storage_path

    pdfs = []
    for pdf_file in pdf_dir.glob("*.pdf"):
        pdfs.append({
            "exam_id": pdf_file.stem,
            "filename": pdf_file.name,
            "size": pdf_file.stat().st_size
        })

    return {
        "pdfs": pdfs,
        "total": len(pdfs)
    }