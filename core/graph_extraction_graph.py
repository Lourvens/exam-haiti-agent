"""LangGraph-based graph extraction pipeline for Neo4j."""

from typing import TypedDict, List, Optional, Dict, Any
from loguru import logger

from langgraph.graph import StateGraph, END

from models.graph_extraction import Entity, Relation, ExtractionResult, CrossReferenceExtraction


# Define the state for the extraction graph
class GraphExtractionState(TypedDict):
    """State for the graph extraction graph."""
    # Input
    chunks: List[Dict[str, Any]]
    exam_id: str
    exam_subject: str
    exam_year: int
    exam_serie: str

    # Processing
    current_chunk_index: int
    all_entities: List[Entity]
    all_relations: List[Relation]

    # Cross-document
    cross_relations: List[Relation]
    insights: List[str]

    # Results
    error: Optional[str]
    verbose: bool


def create_extraction_graph(llm_client):
    """Create a LangGraph for graph extraction with error handling."""

    def load_chunks(state: GraphExtractionState) -> GraphExtractionState:
        """Node 1: Load and prepare chunks."""
        logger.info("=" * 60)
        logger.info("NODE: load_chunks")
        logger.info("=" * 60)

        chunks = state.get("chunks", [])
        verbose = state.get("verbose", True)

        if verbose:
            logger.info(f"Loaded {len(chunks)} chunks for extraction")

        return {
            **state,
            "current_chunk_index": 0,
            "all_entities": [],
            "all_relations": [],
            "cross_relations": [],
            "insights": [],
            "error": None
        }

    def extract_from_chunk(state: GraphExtractionState) -> GraphExtractionState:
        """Node 2: Extract entities from a single chunk."""
        logger.info("=" * 60)
        logger.info("NODE: extract_from_chunk")
        logger.info("=" * 60)

        chunks = state["chunks"]
        current_idx = state["current_chunk_index"]
        exam_id = state.get("exam_id", "unknown")
        verbose = state.get("verbose", True)

        if current_idx >= len(chunks):
            logger.info("  → All chunks processed")
            return {**state, "error": None}

        chunk = chunks[current_idx]
        content = chunk.get("content", "")
        meta = chunk.get("metadata", {})

        if verbose:
            logger.info(f"Processing chunk {current_idx + 1}/{len(chunks)} ({len(content)} chars)")
            logger.info(f"  Chunk type: {meta.get('chunk_type', 'unknown')}")

        # Skip empty or too short chunks
        if len(content) < 20:
            return {
                **state,
                "current_chunk_index": current_idx + 1
            }

        # Build extraction prompt
        chunk_type = meta.get("chunk_type", "unknown")
        question_num = meta.get("question_number", "")
        section = meta.get("section", "")
        topic_hint = meta.get("topic_hint", "")

        prompt = f"""You are extracting entities and relationships from exam content for a knowledge graph.

EXAM CONTEXT:
- Exam ID: {exam_id}
- Subject: {state.get('exam_subject', 'Unknown')}
- Year: {state.get('exam_year', 'Unknown')}
- Serie: {state.get('exam_serie', 'Unknown')}

CHUNK METADATA:
- Type: {chunk_type}
- Section: {section}
- Question Number: {question_num}
- Topic Hint: {topic_hint}

CHUNK CONTENT:
{content[:2000]}

TASK:
Extract entities and relationships from this content.

1. ENTITY TYPES to extract:
- concept: Key concept or topic (e.g., "Photosynthesis", "Derivatives", "Cell Biology")
- topic: Subject area (e.g., "Algebra", "Mechanics", "Organic Chemistry")
- formula: Mathematical/scientific formula mentioned

2. RELATIONSHIP TYPES:
- has_concept: question → concept
- has_topic: question → topic
- requires: question A → question B (prerequisite relationship)

Return a JSON object with:
- "entities": list of {{"id", "type", "name", "properties"}} objects
- "relations": list of {{"source_id", "target_id", "relation_type"}} objects

Focus on extracting meaningful concepts and topics that could help connect this question to others.
"""

        try:
            # Use structured output
            structured_llm = llm_client.with_structured_output(
                ExtractionResult,
                method="json_schema"
            )

            response = structured_llm.invoke(prompt)

            if verbose and response.entities:
                logger.info(f"  → Extracted {len(response.entities)} entities")
            if verbose and response.relations:
                logger.info(f"  → Found {len(response.relations)} relations")

            # Add entities with proper IDs
            current_entities = state.get("all_entities", [])
            current_relations = state.get("all_relations", [])

            for entity in response.entities:
                # Add exam context to entity
                entity.properties["exam_id"] = exam_id
                entity.properties["chunk_index"] = current_idx
                current_entities.append(entity)

            # Add relations with source/target that include exam context
            for relation in response.relations:
                # Prefix IDs with exam context
                relation.source_id = f"{exam_id}:{relation.source_id}"
                relation.target_id = f"{exam_id}:{relation.target_id}"
                current_relations.append(relation)

            return {
                **state,
                "all_entities": current_entities,
                "all_relations": current_relations,
                "current_chunk_index": current_idx + 1
            }

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"  → Error extracting: {error_msg}")
            # Continue to next chunk on error
            return {
                **state,
                "current_chunk_index": current_idx + 1
            }

    def should_continue_extraction(state: GraphExtractionState) -> str:
        """Decide whether to continue extraction or finish chunk processing."""
        chunks = state["chunks"]
        current_idx = state["current_chunk_index"]

        if current_idx < len(chunks):
            return "extract_from_chunk"
        else:
            return "extract_cross_references"

    def extract_cross_references(state: GraphExtractionState) -> GraphExtractionState:
        """Node 3: Extract cross-document relationships."""
        logger.info("=" * 60)
        logger.info("NODE: extract_cross_references")
        logger.info("=" * 60)

        all_entities = state.get("all_entities", [])
        verbose = state.get("verbose", True)

        if not all_entities:
            logger.info("  → No entities to cross-reference")
            return state

        # Get all questions and concepts from the exam
        questions = [e for e in all_entities if e.type == "question" or "question" in e.id.lower()]
        concepts = [e for e in all_entities if e.type == "concept"]

        if verbose:
            logger.info(f"  → Found {len(questions)} questions and {len(concepts)} concepts")

        # Build prompt for cross-reference extraction
        entities_summary = []
        for e in all_entities[:20]:  # Limit to first 20 for prompt size
            entities_summary.append(f"- {e.type}: {e.name}")

        prompt = f"""Analyze questions and concepts from this exam to find semantic relationships.

EXAM: {state.get('exam_id', 'unknown')}
Subject: {state.get('exam_subject', 'Unknown')}

ENTITIES EXTRACTED:
{chr(10).join(entities_summary)}

TASK:
Identify meaningful relationships between questions that would help students navigate related topics.

RELATIONSHIP TYPES:
1. same_topic: Two questions cover the same topic
2. prerequisite: Question A must be understood before Question B
3. related_concept: Questions share related concepts
4. builds_on: Answering question A helps with question B

Return a JSON object with:
- "relations": list of {{"source_id", "target_id", "relation_type"}} objects
- "insights": list of brief strings explaining key connections

Use exam_id:prefix format for IDs (e.g., "Chimie_2023_SMP:Q1").
"""

        try:
            structured_llm = llm_client.with_structured_output(
                CrossReferenceExtraction,
                method="json_schema"
            )

            response = structured_llm.invoke(prompt)

            if verbose:
                logger.info(f"  → Found {len(response.relations)} cross-references")
                logger.info(f"  → Generated {len(response.insights)} insights")

            return {
                **state,
                "cross_relations": response.relations,
                "insights": response.insights
            }

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"  → Error in cross-reference extraction: {error_msg}")
            return state

    def finalize_extraction(state: GraphExtractionState) -> GraphExtractionState:
        """Node 4: Finalize and clean up extraction results."""
        logger.info("=" * 60)
        logger.info("NODE: finalize_extraction")
        logger.info("=" * 60)

        verbose = state.get("verbose", True)

        all_entities = state.get("all_entities", [])
        all_relations = state.get("all_relations", [])
        cross_relations = state.get("cross_relations", [])

        # Combine all relations
        all_relations.extend(cross_relations)

        if verbose:
            logger.info(f"  → Total entities: {len(all_entities)}")
            logger.info(f"  → Total relations: {len(all_relations)}")

            # Log entity type distribution
            from collections import Counter
            type_counts = Counter(e.type for e in all_entities)
            logger.info("  → Entity types:")
            for etype, count in type_counts.most_common():
                logger.info(f"      {etype}: {count}")

        return {
            **state,
            "all_entities": all_entities,
            "all_relations": all_relations
        }

    # Create the graph
    graph = StateGraph(GraphExtractionState)

    # Add nodes
    graph.add_node("load_chunks", load_chunks)
    graph.add_node("extract_from_chunk", extract_from_chunk)
    graph.add_node("extract_cross_references", extract_cross_references)
    graph.add_node("finalize_extraction", finalize_extraction)

    # Define edges
    graph.set_entry_point("load_chunks")
    graph.add_edge("load_chunks", "extract_from_chunk")

    # Conditional edge - continue extraction or process cross-references
    graph.add_conditional_edges(
        "extract_from_chunk",
        should_continue_extraction,
        {
            "extract_from_chunk": "extract_from_chunk",
            "extract_cross_references": "extract_cross_references"
        }
    )

    graph.add_edge("extract_cross_references", "finalize_extraction")
    graph.add_edge("finalize_extraction", END)

    return graph.compile()


class GraphExtractionEngine:
    """Graph extraction engine using LangGraph."""

    def __init__(self, llm_client, verbose: bool = True):
        """Initialize extraction engine."""
        self.llm_client = llm_client
        self.verbose = verbose
        self.graph = create_extraction_graph(llm_client)

    def extract_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        exam_id: str,
        exam_subject: str,
        exam_year: int,
        exam_serie: str
    ) -> Dict[str, Any]:
        """
        Extract entities and relationships from chunks.

        Args:
            chunks: List of chunk dicts with 'content' and 'metadata'
            exam_id: Exam identifier
            exam_subject: Subject name
            exam_year: Exam year
            exam_serie: Exam serie

        Returns:
            Dict with 'entities', 'relations', 'insights'
        """
        logger.info(f"Starting graph extraction for exam: {exam_id}")

        # Initialize state
        initial_state: GraphExtractionState = {
            "chunks": chunks,
            "exam_id": exam_id,
            "exam_subject": exam_subject,
            "exam_year": exam_year,
            "exam_serie": exam_serie,
            "current_chunk_index": 0,
            "all_entities": [],
            "all_relations": [],
            "cross_relations": [],
            "insights": [],
            "error": None,
            "verbose": self.verbose
        }

        # Run the graph
        try:
            result = self.graph.invoke(initial_state)

            entities = result.get("all_entities", [])
            relations = result.get("all_relations", [])
            insights = result.get("insights", [])

            logger.info(f"✓ Graph extraction complete: {len(entities)} entities, {len(relations)} relations")

            return {
                "entities": entities,
                "relations": relations,
                "insights": insights
            }

        except Exception as e:
            logger.error(f"Graph extraction failed: {e}")
            raise RuntimeError(f"Graph extraction failed: {e}") from e
