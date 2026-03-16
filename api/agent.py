"""Agent API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.config import get_settings

# Load environment variables before importing
from dotenv import load_dotenv
load_dotenv()


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    """Request model for agent queries."""
    query: str = Field(..., description="Natural language query about exam content")
    filters: Optional[dict] = Field(default=None, description="Optional filters (subject, year, serie)")


class AgentQueryResponse(BaseModel):
    """Response model for agent queries."""
    answer: str
    sources: list
    search_type: str
    filters: dict


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(request: AgentQueryRequest):
    """
    Query the exam agent with natural language.

    The agent will:
    1. Classify intent (graph/embed/hybrid)
    2. Extract filters from query
    3. Search appropriate sources (Neo4j graph or Chroma vector store)
    4. Generate a helpful answer
    """
    settings = get_settings()

    # Check LLM availability
    if not settings.has_llm_provider:
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. Set OPENAI_API_KEY in .env"
        )

    # Create LLM client
    from langchain_openai import ChatOpenAI

    llm_kwargs = {"model": settings.openai_model, "api_key": settings.openai_api_key}
    if settings.openai_api_base:
        llm_kwargs["base_url"] = settings.openai_api_base

    llm = ChatOpenAI(**llm_kwargs)

    # Create agent and process query
    from core.exam_agent import create_exam_agent

    try:
        agent = create_exam_agent(llm)

        # Apply user-provided filters if any
        filters = request.filters or {}

        result = agent.query(request.query, filters=filters)

        # Merge extracted filters with provided filters
        result_filters = {**result.get("filters", {}), **filters}

        return AgentQueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            search_type=result["search_type"],
            filters=result_filters
        )

    except Exception as e:
        logger.error(f"Agent query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health():
    """Check agent service health."""
    settings = get_settings()

    health = {
        "status": "healthy",
        "llm_configured": settings.has_llm_provider,
        "neo4j_enabled": settings.neo4j_enabled
    }

    # Check Chroma availability
    try:
        from services.ingestion_pipeline import EmbeddingProvider
        embeddings = EmbeddingProvider.create_embeddings()
        health["chroma_available"] = True
    except Exception as e:
        health["chroma_available"] = False
        health["chroma_error"] = str(e)

    # Check Neo4j if enabled
    if settings.neo4j_enabled:
        try:
            from services.agent_tools import create_graph_query_tool
            tool = create_graph_query_tool()
            tool.close()
            health["neo4j_available"] = True
        except Exception as e:
            health["neo4j_available"] = False
            health["neo4j_error"] = str(e)

    return health
