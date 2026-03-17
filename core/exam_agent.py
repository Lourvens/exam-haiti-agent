"""LangGraph-based exam agent for intelligent RAG."""

from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional
from loguru import logger

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool

from app.config import get_settings
from core.prompts import get_intent_filter_prompt, get_latex_answer_prompt


# Define the state for our agent
class ExamAgentState(TypedDict):
    """State for the exam agent graph."""
    # Input
    query: str

    # Processing
    intent: str  # graph / embed / hybrid
    filters: Dict[str, Any]  # {subject, year, topic}
    search_type: str  # Which search was performed

    # Results
    graph_results: List[Dict[str, Any]]
    embed_results: List[Dict[str, Any]]

    # Output
    answer: str
    sources: List[Dict[str, Any]]


# Tool definitions for the agent
@tool
def graph_search(query: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """Search the knowledge graph for exam structure and relationships.

    Args:
        query: Natural language query about exam topics
        filters: Optional filters (subject, year, serie)
    """
    from services.agent_tools import create_graph_query_tool

    tool = create_graph_query_tool()
    try:
        results = tool.search(query, filters)
        tool.close()

        if not results:
            return "No graph results found."

        # Format results
        formatted = []
        for r in results[:10]:
            if r.get("type") == "question":
                formatted.append(
                    f"Question {r.get('number')}: {r.get('content', '')[:200]}... "
                    f"(Topic: {r.get('topic')}, Subject: {r.get('subject')}, Year: {r.get('year')})"
                )
            elif r.get("type") == "exam":
                formatted.append(
                    f"Exam: {r.get('subject')} {r.get('year')} {r.get('serie')}"
                )

        return "\n\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Graph search error: {str(e)}"


@tool
def embed_search(query: str, filters: Optional[Dict[str, Any]] = None, k: int = 5) -> str:
    """Semantic search in exam chunks using embeddings.

    Args:
        query: Search query
        filters: Optional metadata filters
        k: Number of results (default 5)
    """
    from services.agent_tools import create_retriever_tool

    tool = create_retriever_tool()
    try:
        results = tool.search(query, filters, k)

        if not results:
            return "No embedding results found."

        # Format results
        formatted = []
        for r in results:
            meta = r.get("metadata", {})
            content = r.get("content", "")[:300]
            formatted.append(
                f"[{meta.get('chunk_type', 'unknown')}] "
                f"{meta.get('subject', '')} {meta.get('year', '')} "
                f"Q{meta.get('question_number', '')}: {content}..."
            )

        return "\n\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Embedding search error: {str(e)}"


def create_exam_agent_graph(llm_client):
    """Create the LangGraph for the exam agent."""

    # Bind tools to LLM
    tools = [graph_search, embed_search]
    llm_with_tools = llm_client.bind_tools(tools)

    def classify_intent(state: ExamAgentState) -> ExamAgentState:
        """Node 1: Classify user intent and extract filters."""
        logger.info("=" * 60)
        logger.info("NODE: classify_intent")
        logger.info("=" * 60)

        query = state["query"]
        logger.info(f"Query: {query}")

        # Extract filters from query using LLM
        filter_prompt = get_intent_filter_prompt(query)

        try:
            # Use the LLM to extract filters
            structured_llm = llm_client.with_structured_output(
                IntentFilters,
                method="json_schema"
            )
            filter_result = structured_llm.invoke(filter_prompt)

            filters = {
                "subject": filter_result.subject,
                "year": filter_result.year,
                "serie": filter_result.serie,
                "topic": filter_result.topic
            }
            # Remove None values
            filters = {k: v for k, v in filters.items() if v}

        except Exception as e:
            logger.warning(f"Filter extraction failed: {e}")
            filters = {}

        # Merge with user-provided filters (user filters take precedence)
        user_filters = state.get("filters", {})
        if user_filters:
            filters = {**filters, **user_filters}
            logger.info(f"  → Merged filters: {filters}")

        # Determine search strategy
        # Graph is better for structural queries, embeddings for semantic search
        query_lower = query.lower()

        # Keywords that suggest graph search
        graph_keywords = [
            "structure", "exam", "year", "serie", "section",
            "question", "how many", "list all", "show me the",
            "what questions", "find questions"
        ]

        # Keywords that suggest embedding search
        embed_keywords = [
            "explain", "what is", "how does", "what are",
            "define", "describe", "meaning", "example",
            "help me", "solve", "calculate"
        ]

        # Check for hybrid
        is_graph = any(kw in query_lower for kw in graph_keywords)
        is_embed = any(kw in query_lower for kw in embed_keywords)

        if is_graph and is_embed:
            intent = "hybrid"
        elif is_graph:
            intent = "graph"
        else:
            intent = "embed"

        logger.info(f"  → Intent: {intent}")
        logger.info(f"  → Filters: {filters}")

        return {
            **state,
            "intent": intent,
            "filters": filters,
            "graph_results": [],
            "embed_results": []
        }

    def execute_graph_search(state: ExamAgentState) -> ExamAgentState:
        """Execute graph search."""
        logger.info("=" * 60)
        logger.info("NODE: execute_graph_search")
        logger.info("=" * 60)

        query = state["query"]
        filters = state["filters"]

        try:
            from services.agent_tools import create_graph_query_tool
            tool = create_graph_query_tool()
            results = tool.search(query, filters)
            tool.close()

            logger.info(f"  → Graph results: {len(results)}")
            return {
                **state,
                "graph_results": results,
                "search_type": "graph"
            }
        except Exception as e:
            logger.error(f"Graph search error: {e}")
            return {
                **state,
                "graph_results": [],
                "search_type": "graph"
            }

    def execute_embed_search(state: ExamAgentState) -> ExamAgentState:
        """Execute embedding search."""
        logger.info("=" * 60)
        logger.info("NODE: execute_embed_search")
        logger.info("=" * 60)

        query = state["query"]
        filters = state["filters"]

        try:
            from services.agent_tools import create_retriever_tool
            tool = create_retriever_tool()
            # Use higher k for hybrid
            k = 5 if state.get("search_type") != "hybrid" else 10
            results = tool.search(query, filters, k=k)

            logger.info(f"  → Embed results: {len(results)}")
            return {
                **state,
                "embed_results": results,
                "search_type": state.get("intent", "embed")
            }
        except Exception as e:
            logger.error(f"Embed search error: {e}")
            return {
                **state,
                "embed_results": [],
                "search_type": "embed"
            }

    def execute_hybrid_search(state: ExamAgentState) -> ExamAgentState:
        """Execute both searches."""
        # First do graph
        state = execute_graph_search(state)
        # Then do embed
        state = execute_embed_search(state)
        state["search_type"] = "hybrid"
        return state

    def format_response(state: ExamAgentState) -> ExamAgentState:
        """Format the final response using LLM."""
        logger.info("=" * 60)
        logger.info("NODE: format_response")
        logger.info("=" * 60)

        query = state["query"]
        graph_results = state.get("graph_results", [])
        embed_results = state.get("embed_results", [])
        search_type = state.get("search_type", "unknown")

        # Prepare context from results
        context_parts = []

        if graph_results:
            context_parts.append("=== GRAPH RESULTS ===")
            for r in graph_results[:5]:
                if r.get("type") == "question":
                    context_parts.append(
                        f"Question {r.get('number')}: {r.get('content', '')[:300]}"
                    )
                elif r.get("type") == "exam":
                    context_parts.append(
                        f"Exam: {r.get('subject')} {r.get('year')} {r.get('serie')}"
                    )

        if embed_results:
            context_parts.append("\n=== EMBEDDING RESULTS ===")
            for r in embed_results[:5]:
                meta = r.get("metadata", {})
                content = r.get("content", "")[:300]
                context_parts.append(
                    f"[{meta.get('chunk_type', 'unknown')}] "
                    f"{meta.get('subject', '')} {meta.get('year', '')}: {content}"
                )

        context = "\n\n".join(context_parts) if context_parts else "No results found."

        # Generate answer with LLM
        answer_prompt = get_latex_answer_prompt(query, search_type, context)

        try:
            answer = llm_client.invoke(answer_prompt)
            answer_text = answer.content if hasattr(answer, "content") else str(answer)
        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            answer_text = f"I found {len(graph_results)} graph results and {len(embed_results)} embedding results, but had trouble generating a response."

        # Collect sources with PDF URLs
        sources = []

        # Extract exam IDs from results for PDF URLs
        exam_ids = set()
        for r in graph_results[:3]:
            r_id = r.get("id", "")
            # Extract exam_id from question id (e.g., "Math-NS4-2025-SMP-Graphe_PARTIE A_1" -> "Math-NS4-2025-SMP-Graphe")
            exam_id = r_id.split("_PARTIE")[0].split("_Exercice")[0].split("_Texte")[0]
            if exam_id:
                exam_ids.add(exam_id)

            sources.append({
                "type": "graph",
                "id": r.get("id"),
                "content": r.get("content", "")[:100],
                "exam_id": exam_id
            })

        for r in embed_results[:3]:
            meta = r.get("metadata", {})
            source = meta.get("source", "")
            # Extract exam_id from source path
            if source:
                exam_id = Path(source).stem
                exam_ids.add(exam_id)
            else:
                exam_id = None

            sources.append({
                "type": "embed",
                "metadata": meta,
                "exam_id": exam_id
            })

        # Add PDF download URLs
        pdf_urls = [f"/api/v1/pdfs/{eid}" for eid in exam_ids if eid]

        return {
            **state,
            "answer": answer_text,
            "sources": sources,
            "pdf_urls": pdf_urls
        }

    # Create the graph
    graph = StateGraph(ExamAgentState)

    # Add nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("execute_graph_search", execute_graph_search)
    graph.add_node("execute_embed_search", execute_embed_search)
    graph.add_node("execute_hybrid_search", execute_hybrid_search)
    graph.add_node("format_response", format_response)

    # Set entry point
    graph.set_entry_point("classify_intent")

    # Conditional routing - route directly from classify_intent based on intent
    graph.add_conditional_edges(
        "classify_intent",
        lambda state: state["intent"],
        {
            "graph": "execute_graph_search",
            "embed": "execute_embed_search",
            "hybrid": "execute_hybrid_search"
        }
    )

    # All search nodes go to format_response
    graph.add_edge("execute_graph_search", "format_response")
    graph.add_edge("execute_embed_search", "format_response")
    graph.add_edge("execute_hybrid_search", "format_response")

    # End
    graph.add_edge("format_response", END)

    return graph.compile()


# Helper class for filter extraction
from pydantic import BaseModel


class IntentFilters(BaseModel):
    """Schema for intent filter extraction."""
    subject: Optional[str] = None
    year: Optional[int] = None
    serie: Optional[str] = None
    topic: Optional[str] = None


class ExamAgent:
    """Exam agent that uses LangGraph for intelligent RAG."""

    def __init__(self, llm_client):
        """
        Initialize the exam agent.

        Args:
            llm_client: LLM client for the agent
        """
        self.llm_client = llm_client
        self.graph = create_exam_agent_graph(llm_client)

    def query(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query.

        Args:
            query: User query string
            filters: Optional filters to apply to search

        Returns:
            Dictionary with answer, sources, and search_type
        """
        logger.info(f"Processing query: {query}")

        # Initialize state
        initial_state: ExamAgentState = {
            "query": query,
            "intent": "",
            "filters": filters or {},
            "search_type": "",
            "graph_results": [],
            "embed_results": [],
            "answer": "",
            "sources": []
        }

        # Run the graph
        result = self.graph.invoke(initial_state)

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "search_type": result.get("search_type", "unknown"),
            "filters": result.get("filters", {})
        }


def create_exam_agent(llm_client) -> ExamAgent:
    """Factory function to create an ExamAgent."""
    return ExamAgent(llm_client)
