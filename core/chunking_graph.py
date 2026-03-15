"""LangGraph-based chunking pipeline with error handling and logging."""

import json
from typing import TypedDict, List, Optional
from pathlib import Path
from loguru import logger

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from models.chunk import Chunk, ChunkInput, ChunkResponse
from models.exam import Exam
from services.pdf_processor import PDFProcessor
from services.pdf_analyzer import PDFAnalyzer
from core.chunking_strategy import get_auto_strategy


# Define the state for our graph
class ChunkingState(TypedDict):
    """State for the chunking graph."""
    # Input
    pdf_path: str
    text_content: str
    exam: Optional[Exam]

    # Processing
    sections: List[str]
    current_section_index: int
    all_chunks: List[dict]

    # Results
    final_chunks: List[Chunk]
    error: Optional[str]

    # Metadata
    retry_count: int
    verbose: bool


def create_chunking_graph(llm_client):
    """Create a LangGraph for chunking with error handling."""

    # Define nodes
    def analyze_request(state: ChunkingState) -> ChunkingState:
        """Node 1: Analyze the request and prepare data."""
        logger.info("=" * 60)
        logger.info("NODE: analyze_request")
        logger.info("=" * 60)

        pdf_path = state["pdf_path"]
        verbose = state.get("verbose", True)

        if verbose:
            logger.info(f"Analyzing PDF: {pdf_path}")

        # Analyze PDF structure
        analyzer = PDFAnalyzer(pdf_path)
        analysis = analyzer.analyze()

        if verbose:
            logger.info(f"  → {len(analysis.layouts)} pages, layout types: {[l.layout_type for l in analysis.layouts]}")

        # Extract exam metadata
        exam = Exam.from_pdf_analysis(analysis)

        if verbose:
            logger.info(f"  → Subject: {exam.subject}, Year: {exam.year}, Serie: {exam.serie}")

        # Extract text based on layout
        with PDFProcessor(pdf_path) as processor:
            text_content = state.get("text_content", "")
            if not text_content:
                # Extract text respecting layout types
                all_text = []
                for page_num in range(processor.page_count):
                    layout = analysis.layouts[page_num] if page_num < len(analysis.layouts) else None
                    if layout and layout.layout_type in ["B", "C", "multi"]:
                        left, right = processor.extract_two_column(page_num)
                        all_text.append(f"--- Page {page_num + 1} ---\n{left}\n\n{right}")
                    else:
                        text = processor.extract_text_raw(page_num)
                        all_text.append(f"--- Page {page_num + 1} ---\n{text}")
                text_content = "\n\n".join(all_text)

        if verbose:
            logger.info(f"  → Extracted {len(text_content)} characters")

        return {
            **state,
            "exam": exam,
            "text_content": text_content,
            "all_chunks": [],
            "current_section_index": 0,
            "error": None
        }

    def split_into_sections(state: ChunkingState) -> ChunkingState:
        """Node 2: Split text into manageable sections."""
        logger.info("=" * 60)
        logger.info("NODE: split_into_sections")
        logger.info("=" * 60)

        text = state["text_content"]
        verbose = state.get("verbose", True)

        if verbose:
            logger.info(f"Splitting {len(text)} characters into sections...")

        # Split by page markers
        pages = text.split("--- Page ")

        # Further split long pages into smaller chunks (max ~2000 chars per section)
        sections = []
        max_section_size = 2000

        for page in pages:
            if not page.strip():
                continue

            # If page is small enough, add as-is
            if len(page) <= max_section_size:
                sections.append(page)
            else:
                # Split by paragraphs
                paragraphs = page.split("\n\n")
                current_section = ""

                for para in paragraphs:
                    if len(current_section) + len(para) <= max_section_size:
                        current_section += para + "\n\n"
                    else:
                        if current_section:
                            sections.append(current_section.strip())
                        current_section = para + "\n\n"

                if current_section.strip():
                    sections.append(current_section.strip())

        if verbose:
            logger.info(f"  → Created {len(sections)} sections")
            for i, sec in enumerate(sections[:3]):
                logger.info(f"    Section {i+1}: {len(sec)} chars")

        return {
            **state,
            "sections": sections,
            "current_section_index": 0
        }

    def process_section(state: ChunkingState) -> ChunkingState:
        """Node 3: Process a single section with LLM."""
        logger.info("=" * 60)
        logger.info("NODE: process_section")
        logger.info("=" * 60)

        sections = state["sections"]
        current_idx = state["current_section_index"]
        exam = state["exam"]
        verbose = state.get("verbose", True)
        retry_count = state.get("retry_count", 0)

        if current_idx >= len(sections):
            logger.info("  → All sections processed")
            return {**state, "error": None}

        section = sections[current_idx]

        if verbose:
            logger.info(f"Processing section {current_idx + 1}/{len(sections)} ({len(section)} chars)")

        # Get strategy
        strategy = get_auto_strategy(exam.subject if exam else "Unknown")

        # Build prompt
        prompt = f"""{strategy.get_llm_prompt()}

DETECTED EXAM METADATA:
- Subject: {exam.subject if exam else 'Unknown'}
- Year: {exam.year if exam else 'Unknown'}
- Serie: {exam.serie if exam else 'Unknown'}

DOCUMENT SECTION:
{section}

OUTPUT:
Extract chunks from this section. Each chunk must be a complete, meaningful unit.
Return a JSON object with a "chunks" key containing an array of chunks.
"""

        if verbose:
            logger.info(f"  → Prompt length: {len(prompt)} chars")

        try:
            # Use structured output
            structured_llm = llm_client.with_structured_output(
                ChunkResponse,
                method="json_schema"
            )

            response = structured_llm.invoke(prompt)

            if verbose:
                logger.info(f"  → Received {len(response.chunks)} chunks")

            # Add chunks to collection
            current_chunks = state.get("all_chunks", [])
            for chunk_data in response.chunks:
                current_chunks.append({
                    "content": chunk_data.content,
                    "chunk_type": chunk_data.chunk_type,
                    "section": chunk_data.section,
                    "question_number": chunk_data.question_number,
                    "sub_question": chunk_data.sub_question,
                    "has_formula": chunk_data.has_formula,
                    "topic_hint": chunk_data.topic_hint,
                    "subject": chunk_data.subject or (exam.subject if exam else "Unknown"),
                    "year": chunk_data.year or (exam.year if exam else 0),
                    "serie": chunk_data.serie or (exam.serie if exam else "Unknown"),
                })

            if verbose:
                logger.info(f"  → Total chunks so far: {len(current_chunks)}")

            return {
                **state,
                "all_chunks": current_chunks,
                "current_section_index": current_idx + 1,
                "retry_count": 0,
                "error": None
            }

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"  → Error processing section: {error_msg}")

            # Check if it's a length error
            if "length" in error_msg.lower() or "limit" in error_msg.lower():
                # Reduce section size further
                logger.info("  → Length error, will retry with shorter section")

            # Retry up to 3 times
            if retry_count < 3:
                logger.info(f"  → Retry {retry_count + 1}/3")
                return {
                    **state,
                    "retry_count": retry_count + 1
                }
            else:
                # Fail with error - don't use fallback
                error_msg = f"LLM chunking failed after 3 retries: {error_msg}"
                logger.error(f"  → {error_msg}")
                raise RuntimeError(error_msg)

    def should_continue(state: ChunkingState) -> str:
        """Decide whether to continue processing or end."""
        sections = state["sections"]
        current_idx = state["current_section_index"]

        logger.info(f"Checking continue: {current_idx}/{len(sections)}")

        if current_idx < len(sections):
            return "process_section"
        else:
            return "merge_results"

    def merge_results(state: ChunkingState) -> ChunkingState:
        """Node 4: Merge all chunks into final result."""
        logger.info("=" * 60)
        logger.info("NODE: merge_results")
        logger.info("=" * 60)

        exam = state["exam"]
        all_chunks = state.get("all_chunks", [])
        verbose = state.get("verbose", True)

        if verbose:
            logger.info(f"Merging {len(all_chunks)} chunks")

        # Convert to Chunk objects
        final_chunks = []

        for i, chunk_data in enumerate(all_chunks):
            try:
                chunk = Chunk(
                    content=chunk_data.get("content", ""),
                    chunk_type=chunk_data.get("chunk_type", "other"),
                    exam_file=state["pdf_path"],
                    page_num=i % 5 + 1,
                    subject=chunk_data.get("subject", exam.subject if exam else "Unknown"),
                    year=chunk_data.get("year", exam.year if exam else 0),
                    serie=chunk_data.get("serie", exam.serie if exam else "Unknown"),
                    section=chunk_data.get("section"),
                    question_number=chunk_data.get("question_number"),
                    sub_question=chunk_data.get("sub_question"),
                    has_formula=chunk_data.get("has_formula", False),
                    topic_hint=chunk_data.get("topic_hint")
                )
                final_chunks.append(chunk)
            except Exception as e:
                logger.warning(f"  → Error creating chunk {i}: {e}")

        if verbose:
            logger.info(f"  → Created {len(final_chunks)} final chunks")

            # Log chunk type distribution
            from collections import Counter
            type_counts = Counter(c.chunk_type for c in final_chunks)
            logger.info("  → Chunk types:")
            for ct, count in type_counts.most_common():
                logger.info(f"      {ct}: {count}")

        return {
            **state,
            "final_chunks": final_chunks
        }

    def handle_error(state: ChunkingState) -> ChunkingState:
        """Error handler node."""
        logger.error("=" * 60)
        logger.error("NODE: handle_error")
        logger.error("=" * 60)

        error = state.get("error", "Unknown error")
        logger.error(f"Error: {error}")

        # Return empty chunks on error
        return {
            **state,
            "final_chunks": [],
            "error": error
        }

    # Create the graph
    graph = StateGraph(ChunkingState)

    # Add nodes
    graph.add_node("analyze_request", analyze_request)
    graph.add_node("split_into_sections", split_into_sections)
    graph.add_node("process_section", process_section)
    graph.add_node("merge_results", merge_results)
    graph.add_node("handle_error", handle_error)

    # Define edges
    graph.set_entry_point("analyze_request")
    graph.add_edge("analyze_request", "split_into_sections")
    graph.add_edge("split_into_sections", "process_section")

    # Conditional edge - continue processing or merge
    graph.add_conditional_edges(
        "process_section",
        should_continue,
        {
            "process_section": "process_section",
            "merge_results": "merge_results"
        }
    )

    graph.add_edge("merge_results", END)

    return graph.compile()


class LangGraphChunkingEngine:
    """Chunking engine using LangGraph for robust processing."""

    def __init__(self, llm_client, verbose: bool = True):
        """
        Initialize chunking engine.

        Args:
            llm_client: LLM client (required)
            verbose: If True, log detailed progress
        """
        self.llm_client = llm_client
        self.verbose = verbose
        self.graph = create_chunking_graph(llm_client)

    def chunk_pdf(self, pdf_path: str | Path) -> list[Chunk]:
        """
        Chunk a PDF into semantic units using LangGraph.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of Chunk objects
        """
        logger.info(f"Starting LangGraph chunking for: {pdf_path}")

        # Initialize state
        initial_state: ChunkingState = {
            "pdf_path": str(pdf_path),
            "text_content": "",
            "exam": None,
            "sections": [],
            "current_section_index": 0,
            "all_chunks": [],
            "final_chunks": [],
            "error": None,
            "retry_count": 0,
            "verbose": self.verbose
        }

        # Run the graph
        try:
            result = self.graph.invoke(initial_state)

            final_chunks = result.get("final_chunks", [])
            error = result.get("error")

            if error:
                logger.error(f"Graph completed with error: {error}")

            logger.info(f"✓ LangGraph chunking complete: {len(final_chunks)} chunks")

            return final_chunks

        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            raise RuntimeError(f"LangGraph chunking failed: {e}") from e


def chunk_pdf(pdf_path: str | Path, llm_client, verbose: bool = True) -> list[Chunk]:
    """Convenience function to chunk a PDF using LangGraph."""
    engine = LangGraphChunkingEngine(llm_client, verbose=verbose)
    return engine.chunk_pdf(pdf_path)
