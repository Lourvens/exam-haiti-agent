"""Main chunking logic using LLM with structured output and detailed logging."""

import json
import re
from pathlib import Path
from loguru import logger

from models.chunk import Chunk, ChunkInput, ChunkResponse
from models.exam import Exam
from services.pdf_processor import PDFProcessor
from services.pdf_analyzer import PDFAnalyzer
from core.chunking_strategy import get_auto_strategy


class ChunkingEngine:
    """Main chunking engine using LLM for semantic chunking."""

    def __init__(self, llm_client, verbose: bool = True):
        """
        Initialize chunking engine.

        Args:
            llm_client: LLM client (required, e.g., ChatOpenAI)
            verbose: If True, log detailed LLM prompts and responses
        """
        self.llm_client = llm_client
        self.verbose = verbose
        # Create structured output version of the LLM
        self._structured_llm = None

    def _get_structured_llm(self):
        """Get or create structured LLM for JSON output."""
        if self._structured_llm is None:
            # Use ChunkResponse wrapper to handle array response
            self._structured_llm = self.llm_client.with_structured_output(
                ChunkResponse,
                method="json_schema"
            )
        return self._structured_llm

    def chunk_pdf(self, pdf_path: str | Path) -> list[Chunk]:
        """
        Chunk a PDF into semantic units.
        LLM will auto-detect the best chunking strategy.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of Chunk objects

        Raises:
            RuntimeError: If LLM client is not provided
        """
        if not self.llm_client:
            raise RuntimeError("LLM client is required for chunking. Provide an LLM client to ChunkingEngine.")

        pdf_path = Path(pdf_path)
        logger.info(f"Chunking PDF: {pdf_path}")

        # Step 1: Analyze PDF structure (layout detection)
        logger.info("Step 1: Analyzing PDF structure...")
        analyzer = PDFAnalyzer(pdf_path)
        analysis = analyzer.analyze()
        logger.info(f"  → {len(analysis.layouts)} pages, layout types: {[l.layout_type for l in analysis.layouts]}")

        # Step 2: Extract exam metadata (subject, year, serie)
        logger.info("Step 2: Extracting exam metadata...")
        exam = Exam.from_pdf_analysis(analysis)
        logger.info(f"  → Subject: {exam.subject}, Year: {exam.year}, Serie: {exam.serie}")

        # Step 3: Get auto-detection strategy
        logger.info("Step 3: Getting auto-detection strategy...")
        strategy = get_auto_strategy(exam.subject)
        logger.info(f"  → Strategy ready for: {exam.subject}")

        # Step 4: Extract text based on layout
        logger.info("Step 4: Extracting text from PDF...")
        with PDFProcessor(pdf_path) as processor:
            text_content = self._extract_by_layout(processor, analysis.layouts)
        logger.info(f"  → Extracted {len(text_content)} characters")

        # Step 5: Chunk using LLM with structured output
        logger.info("Step 5: Chunking with LLM...")
        chunks = self._chunk_with_structured_output(text_content, exam, strategy)

        logger.info(f"✓ Generated {len(chunks)} chunks")
        return chunks

    def _extract_by_layout(self, processor: PDFProcessor, layouts: list) -> str:
        """Extract text respecting layout types."""
        all_text = []

        for page_num in range(processor.page_count):
            layout = layouts[page_num] if page_num < len(layouts) else None

            if layout and layout.layout_type in ["B", "C", "multi"]:
                # Two-column layout - need to split
                left, right = processor.extract_two_column(page_num)
                all_text.append(f"--- Page {page_num + 1} ---\n{left}\n\n{right}")
            else:
                # Single column
                text = processor.extract_text_raw(page_num)
                all_text.append(f"--- Page {page_num + 1} ---\n{text}")

        return "\n\n".join(all_text)

    def _chunk_with_structured_output(self, text: str, exam: Exam, strategy) -> list[Chunk]:
        """Chunk text using LLM with structured output for guaranteed valid JSON."""
        logger.info("Using LLM with structured output for chunking")

        # Get structured LLM
        structured_llm = self._get_structured_llm()

        # Build prompt
        prompt = self._build_prompt(text, exam, strategy)

        if self.verbose:
            logger.info("=" * 60)
            logger.info("LLM PROMPT (first 1000 chars):")
            logger.info("=" * 60)
            logger.info(prompt[:1000])
            logger.info("..." if len(prompt) > 1000 else "")
            logger.info("=" * 60)

        try:
            # Invoke structured LLM
            logger.info("Invoking structured LLM...")
            response = structured_llm.invoke(prompt)

            if self.verbose:
                logger.info("=" * 60)
                logger.info("LLM RESPONSE:")
                logger.info("=" * 60)
                logger.info(f"Response type: {type(response)}")
                logger.info(f"Response: {response}")
                logger.info("=" * 60)

            # Response is ChunkResponse with chunks list
            chunk_inputs = response.chunks
            logger.info(f"Received {len(chunk_inputs)} chunks from LLM")

            # Convert to Chunk objects
            chunks = []
            for i, chunk_input in enumerate(chunk_inputs):
                if self.verbose:
                    logger.info(f"Chunk {i+1}:")
                    logger.info(f"  - content: {chunk_input.content[:100] if chunk_input.content else 'None'}...")
                    logger.info(f"  - chunk_type: {chunk_input.chunk_type}")
                    logger.info(f"  - subject: {chunk_input.subject}")
                    logger.info(f"  - year: {chunk_input.year}")
                    logger.info(f"  - serie: {chunk_input.serie}")
                    logger.info(f"  - topic_hint: {chunk_input.topic_hint}")

                # Ensure we have required fields
                chunk = Chunk(
                    content=chunk_input.content or "",
                    chunk_type=chunk_input.chunk_type or "other",
                    exam_file=exam.file_path,
                    page_num=i % 5 + 1,
                    subject=chunk_input.subject or exam.subject,
                    year=chunk_input.year or exam.year,
                    serie=chunk_input.serie or exam.serie,
                    section=chunk_input.section,
                    question_number=chunk_input.question_number,
                    sub_question=chunk_input.sub_question,
                    has_formula=chunk_input.has_formula,
                    topic_hint=chunk_input.topic_hint
                )
                chunks.append(chunk)

            logger.info(f"✓ Successfully parsed {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error("=" * 60)
            logger.error("STRUCTURED OUTPUT FAILED:")
            logger.error(f"Error: {e}")
            logger.error("=" * 60)
            # Fall back to regular JSON parsing if structured output fails
            logger.info("Falling back to regular JSON parsing...")
            return self._chunk_with_json_fallback(text, exam, strategy)

    def _build_prompt(self, text: str, exam: Exam, strategy) -> str:
        """Build prompt for chunking."""
        return f"""{strategy.get_llm_prompt()}

DETECTED EXAM METADATA:
- Subject: {exam.subject}
- Year: {exam.year}
- Serie: {exam.serie}

DOCUMENT TEXT:
{text}

OUTPUT:
Extract chunks from the document. Each chunk must be a complete, meaningful unit.
Return a JSON object with a "chunks" key containing an array of chunks.
"""

    def _chunk_with_json_fallback(self, text: str, exam: Exam, strategy) -> list[Chunk]:
        """Fallback to regular JSON parsing with better error handling."""
        logger.info("Using JSON fallback for chunking")

        prompt = self._build_prompt(text, exam, strategy) + """

Respond with a JSON object containing a "chunks" key with an array of chunks.
Example: {{"chunks": [{{"content": "...", "chunk_type": "exam_header", ...}}]}}
"""

        if self.verbose:
            logger.info("=" * 60)
            logger.info("FALLBACK LLM PROMPT (first 1000 chars):")
            logger.info("=" * 60)
            logger.info(prompt[:1000])
            logger.info("..." if len(prompt) > 1000 else "")
            logger.info("=" * 60)

        try:
            logger.info("Invoking LLM with fallback...")
            response = self.llm_client.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            if self.verbose:
                logger.info("=" * 60)
                logger.info("FALLBACK LLM RAW RESPONSE (first 2000 chars):")
                logger.info("=" * 60)
                logger.info(response_text[:2000])
                logger.info("=" * 60)

            # Try to extract JSON from response
            response_text = response_text.strip()

            # Try to find JSON object in response
            try:
                # First try direct parse
                data = json.loads(response_text)
                if "chunks" in data:
                    chunks_data = data["chunks"]
                else:
                    chunks_data = data
                logger.info("✓ Parsed JSON directly")
            except json.JSONDecodeError:
                # Try to find JSON object in response
                logger.info("Trying to extract JSON from response...")

                # Find the JSON object (starts with { and ends with })
                start = response_text.find('{')
                end = response_text.rfind('}')

                if start != -1 and end != -1 and end > start:
                    json_str = response_text[start:end+1]
                    if self.verbose:
                        logger.info(f"Extracted JSON object: {json_str[:500]}...")
                    data = json.loads(json_str)
                    if "chunks" in data:
                        chunks_data = data["chunks"]
                    else:
                        chunks_data = data
                    logger.info("✓ Extracted and parsed JSON from response")
                else:
                    raise ValueError("No JSON object found in response")

            if self.verbose:
                logger.info(f"Parsed {len(chunks_data)} chunks from JSON")

            # Convert to Chunk objects
            chunks = []
            for i, data in enumerate(chunks_data):
                if self.verbose:
                    logger.info(f"Chunk {i+1}: {data.get('chunk_type', 'unknown')} - {data.get('topic_hint', 'no hint')}")

                chunk = Chunk(
                    content=data.get("content", ""),
                    chunk_type=data.get("chunk_type", "other"),
                    exam_file=exam.file_path,
                    page_num=i % 5 + 1,
                    subject=data.get("subject", exam.subject),
                    year=data.get("year", exam.year),
                    serie=data.get("serie", exam.serie),
                    section=data.get("section"),
                    question_number=data.get("question_number"),
                    sub_question=data.get("sub_question"),
                    has_formula=data.get("has_formula", False),
                    topic_hint=data.get("topic_hint")
                )
                chunks.append(chunk)

            logger.info(f"✓ Fallback generated {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error("=" * 60)
            logger.error("FALLBACK ALSO FAILED:")
            logger.error(f"Error: {e}")
            logger.error("=" * 60)
            raise RuntimeError(f"LLM chunking failed: {e}") from e


def chunk_pdf(pdf_path: str | Path, llm_client, verbose: bool = True) -> list[Chunk]:
    """Convenience function to chunk a PDF."""
    engine = ChunkingEngine(llm_client, verbose=verbose)
    return engine.chunk_pdf(pdf_path)
