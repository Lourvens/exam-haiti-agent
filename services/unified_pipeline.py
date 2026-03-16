"""Unified Ingestion Pipeline - PDF to Chroma + Neo4j in a single pass.

This module provides a unified pipeline that:
1. Extracts text from PDF
2. Chunks using LangGraph
3. Embeds and stores in Chroma
4. Creates Neo4j graph (optional)

The pipeline is designed to be flexible - you can use any subset of outputs.
"""

import os
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from dataclasses import dataclass
from loguru import logger

from models.chunk import Chunk
from core.chunking_graph import LangGraphChunkingEngine
from services.ingestion_pipeline import EmbeddingProvider
from app.config import get_settings


@dataclass
class IngestionResult:
    """Result from unified ingestion pipeline."""
    status: str  # "success", "skipped", "error"
    pdf_path: str
    chunks_generated: int = 0
    chunks_stored: int = 0
    graph_nodes_created: int = 0
    error_message: Optional[str] = None


class UnifiedIngestionPipeline:
    """
    Unified pipeline for PDF ingestion into Chroma and Neo4j.

    This pipeline combines:
    - PDF text extraction
    - LLM-based chunking
    - Chroma vector storage
    - Neo4j graph building (optional)

    Usage:
        pipeline = UnifiedIngestionPipeline(llm_client)
        result = pipeline.ingest_pdf("exam.pdf", sync_to_graph=True)
    """

    def __init__(
        self,
        llm_client,
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        enable_neo4j: bool = True,
        neo4j_driver=None
    ):
        """
        Initialize unified ingestion pipeline.

        Args:
            llm_client: LLM client for chunking
            embedding_provider: Embedding provider ('auto', 'openai', 'huggingface')
            embedding_model: Embedding model name
            collection_name: Chroma collection name
            persist_directory: Chroma persistence directory
            enable_neo4j: Whether to enable Neo4j graph sync
            neo4j_driver: Optional Neo4j driver (created if not provided)
        """
        settings = get_settings()

        self.llm_client = llm_client
        self.embedding_provider = embedding_provider or "auto"
        self.embedding_model = embedding_model
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_directory = persist_directory or str(settings.chroma_persist_directory)
        self.chunks_dir = str(settings.chunks_output_path)
        self.enable_neo4j = enable_neo4j and settings.neo4j_enabled
        self.neo4j_driver = neo4j_driver

        # Initialize components
        self.chunking_engine = LangGraphChunkingEngine(llm_client, verbose=False)
        self._vectorstore = None
        self._embeddings = None
        self._graph_builder = None

        # Track processed chunks for graph sync
        self._current_chunks: List[Dict[str, Any]] = []

    def _get_embeddings(self):
        """Get or create embeddings."""
        if self._embeddings is None:
            if self.embedding_provider == "auto":
                provider = None
            else:
                provider = self.embedding_provider

            self._embeddings = EmbeddingProvider.create_embeddings(
                provider=provider,
                model=self.embedding_model
            )

        return self._embeddings

    def _get_vectorstore(self):
        """Get or initialize Chroma vector store."""
        if self._vectorstore is None:
            from langchain_chroma import Chroma

            logger.info(f"Initializing Chroma at: {self.persist_directory}")

            embeddings = self._get_embeddings()

            self._vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_directory
            )

            count = self._vectorstore._collection.count()
            logger.info(f"Collection '{self.collection_name}' ready with {count} existing chunks")

        return self._vectorstore

    def _get_graph_builder(self):
        """Get or create graph builder."""
        if not self.enable_neo4j:
            return None

        if self._graph_builder is None:
            from services.graph_builder import Neo4jGraphBuilder
            self._graph_builder = Neo4jGraphBuilder(driver=self.neo4j_driver)

        return self._graph_builder

    def _save_chunks_to_file(self, chunks: List[Chunk], pdf_path: str, pdf_name: str):
        """Save chunks to JSON file."""
        import json
        from pathlib import Path

        chunks_dir = Path(self.chunks_dir)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunks_data = []
        for i, chunk in enumerate(chunks):
            try:
                chunks_data.append({
                    "index": i,
                    "chunk_type": str(chunk.chunk_type) if chunk.chunk_type else None,
                    "content": str(chunk.content) if chunk.content else "",
                    "subject": str(chunk.subject) if chunk.subject else None,
                    "year": int(chunk.year) if chunk.year else 0,
                    "serie": str(chunk.serie) if chunk.serie else None,
                    "section": str(chunk.section) if chunk.section else None,
                    "question_number": str(chunk.question_number) if chunk.question_number else None,
                    "sub_question": str(chunk.sub_question) if chunk.sub_question else None,
                    "has_formula": bool(chunk.has_formula),
                    "topic_hint": str(chunk.topic_hint) if chunk.topic_hint else None,
                })
            except Exception as e:
                logger.warning(f"Error serializing chunk {i}: {e}")
                continue

        output_file = chunks_dir / f"chunks_{pdf_name}.json"
        data = {
            "pdf_path": str(pdf_path),
            "total_chunks": len(chunks_data),
            "chunks": chunks_data
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(chunks_data)} chunks to {output_file}")

    def ingest_pdf(
        self,
        pdf_path: str,
        batch_size: int = 100,
        skip_existing: bool = True,
        sync_to_graph: bool = False,
        save_chunks: bool = None
    ) -> IngestionResult:
        """
        Ingest a PDF into Chroma and optionally Neo4j.

        Args:
            pdf_path: Path to PDF file
            batch_size: Number of chunks to embed per batch
            skip_existing: Skip if PDF already indexed in Chroma
            sync_to_graph: Immediately sync to Neo4j after ingestion
            save_chunks: Save chunks to JSON file (default from settings)

        Returns:
            IngestionResult with stats
        """
        pdf_path = Path(pdf_path)
        pdf_name = pdf_path.stem

        logger.info("=" * 60)
        logger.info(f"UNIFIED INGESTION: {pdf_path}")
        logger.info("=" * 60)

        # Determine save_chunks setting
        if save_chunks is None:
            settings = get_settings()
            save_chunks = settings.save_chunks_to_file

        # Check if already indexed
        vectorstore = self._get_vectorstore()

        if skip_existing:
            existing = vectorstore.get(where={"source": str(pdf_path)})
            if existing and existing.get("ids"):
                logger.info(f"PDF already indexed with {len(existing['ids'])} chunks. Skipping.")
                return IngestionResult(
                    status="skipped",
                    pdf_path=str(pdf_path),
                    chunks_stored=len(existing['ids']),
                    error_message="Already indexed in Chroma"
                )

        # Step 1: Chunk the PDF
        logger.info("Step 1: Chunking PDF...")
        try:
            chunks = self.chunking_engine.chunk_pdf(pdf_path)
            chunks_generated = len(chunks)
            logger.info(f"  → Generated {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            return IngestionResult(
                status="error",
                pdf_path=str(pdf_path),
                error_message=f"Chunking failed: {str(e)}"
            )

        if not chunks:
            return IngestionResult(
                status="error",
                pdf_path=str(pdf_path),
                error_message="No chunks generated"
            )

        # Save chunks to file if enabled
        if save_chunks:
            self._save_chunks_to_file(chunks, pdf_path, pdf_name)

        # Step 2: Prepare documents for Chroma
        logger.info("Step 2: Preparing documents for Chroma...")

        texts = []
        metadatas = []
        ids = []

        # Store chunk data for graph sync
        self._current_chunks = []

        for i, chunk in enumerate(chunks):
            doc_id = f"{pdf_name}_{i}"

            text = chunk.to_text()
            text = " ".join(text.split())

            if not text or len(text.strip()) < 5:
                logger.warning(f"Skipping empty chunk {i}")
                continue

            ids.append(doc_id)
            texts.append(text)

            # Store for later graph sync
            chunk_data = {
                "id": doc_id,
                "content": text,
                "metadata": {
                    "source": str(pdf_path),
                    "chunk_type": chunk.chunk_type,
                    "subject": chunk.subject,
                    "year": str(chunk.year),
                    "serie": chunk.serie,
                    "section": chunk.section or "",
                    "question_number": chunk.question_number or "",
                    "has_formula": str(chunk.has_formula),
                    "topic_hint": chunk.topic_hint or "",
                    "chunk_index": i
                }
            }
            self._current_chunks.append(chunk_data)

            metadatas.append(chunk_data["metadata"])

        # Step 3: Add to Chroma
        logger.info("Step 3: Adding to Chroma...")

        # Delete existing chunks for this PDF
        existing = vectorstore.get(where={"source": str(pdf_path)})
        if existing and existing.get("ids"):
            logger.info(f"  → Deleting {len(existing['ids'])} existing chunks")
            vectorstore.delete(ids=existing["ids"])

        # Ensure all texts are strings
        texts = [str(t) if t else "" for t in texts]

        # Add to vector store
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        final_count = vectorstore._collection.count()
        chunks_stored = len(texts)

        logger.info(f"  → Stored {chunks_stored} chunks in Chroma")

        # Step 4: Sync to Neo4j (optional)
        graph_nodes = 0
        if sync_to_graph and self.enable_neo4j:
            logger.info("Step 4: Syncing to Neo4j...")
            try:
                graph_nodes = self._sync_chunks_to_graph(pdf_path, chunks)
                logger.info(f"  → Created {graph_nodes} graph nodes")
            except Exception as e:
                logger.warning(f"Graph sync failed: {e}")
                # Don't fail the whole ingestion for graph errors

        logger.info("=" * 60)
        logger.info("✓ UNIFIED INGESTION COMPLETE")
        logger.info(f"  → Chunks generated: {chunks_generated}")
        logger.info(f"  → Chunks stored: {chunks_stored}")
        if sync_to_graph:
            logger.info(f"  → Graph nodes: {graph_nodes}")
        logger.info("=" * 60)

        return IngestionResult(
            status="success",
            pdf_path=str(pdf_path),
            chunks_generated=chunks_generated,
            chunks_stored=chunks_stored,
            graph_nodes_created=graph_nodes
        )

    def _sync_chunks_to_graph(self, pdf_path: Path, chunks: List[Chunk]) -> int:
        """
        Sync current chunks directly to Neo4j without reloading from Chroma.

        This is more efficient than calling graph_builder.sync_from_chroma()
        because we already have the chunk data in memory.
        """
        from services.graph_builder import Neo4jGraphBuilder
        from models.graph_nodes import ChunkGraphData

        builder = self._get_graph_builder()
        if not builder:
            return 0

        pdf_name = pdf_path.stem

        # Convert chunks to graph data
        chunks_data = []
        for i, chunk in enumerate(chunks):
            # Parse exam info from filename
            parts = pdf_name.replace("-", "_").split("_")
            subject = chunk.subject or (parts[0] if len(parts) > 0 else "Unknown")
            year = int(chunk.year or (parts[1] if len(parts) > 1 else 0))
            serie = chunk.serie or (parts[2] if len(parts) > 2 else "Unknown")

            # Get section order
            section_order = 0
            if chunk.section and "PARTIE" in chunk.section.upper():
                section_order = ord(chunk.section.split()[-1].upper()[0]) - ord('A') + 1

            data = ChunkGraphData(
                exam_id=pdf_name,
                exam_subject=subject,
                exam_year=year,
                exam_serie=serie,
                pdf_path=str(pdf_path),
                section_name=chunk.section,
                section_order=section_order,
                question_number=chunk.question_number,
                question_type=chunk.chunk_type,
                question_topic=chunk.topic_hint,
                has_formula=chunk.has_formula,
                question_content=chunk.content if chunk.chunk_type and chunk.chunk_type.startswith("question") else None,
                sub_question_letter=chunk.sub_question,
                sub_question_content=chunk.content if chunk.sub_question else None,
                sub_question_topic=chunk.topic_hint if chunk.sub_question else None,
                passage_content=chunk.content if chunk.chunk_type == "passage" else None,
                passage_topic=chunk.topic_hint if chunk.chunk_type == "passage" else None,
                instruction_content=chunk.content if chunk.chunk_type == "instructions" else None,
                chunk_type=chunk.chunk_type or "other",
                chunk_index=i
            )
            chunks_data.append(data)

        # Sync to Neo4j
        driver = builder._get_driver()

        with driver.session(database=builder.settings.neo4j_database) as session:
            # Create nodes
            for data in chunks_data:
                session.execute_write(builder._create_exam_node, pdf_name, data)
                session.execute_write(builder._create_section_node, pdf_name, data)
                session.execute_write(builder._create_question_node, pdf_name, data)
                session.execute_write(builder._create_subquestion_node, pdf_name, data)
                session.execute_write(builder._create_instruction_node, pdf_name, data)
                session.execute_write(builder._create_passage_node, pdf_name, data)

            # Create sequential relationships
            session.execute_write(builder._create_next_relationships, pdf_name, chunks_data)

            # Create cross-document relationships
            session.execute_write(builder._create_cross_document_relationships)

        return len(chunks_data)

    def ingest_directory(
        self,
        pdf_directory: str,
        pattern: str = "*.pdf",
        sync_to_graph: bool = False,
        **kwargs
    ) -> List[IngestionResult]:
        """
        Ingest all PDFs in a directory.

        Args:
            pdf_directory: Directory containing PDFs
            pattern: File pattern to match
            sync_to_graph: Sync each PDF to Neo4j after ingestion
            **kwargs: Arguments for ingest_pdf

        Returns:
            List of IngestionResults
        """
        pdf_dir = Path(pdf_directory)
        pdf_files = sorted(pdf_dir.glob(pattern))

        logger.info(f"Found {len(pdf_files)} PDF files in {pdf_directory}")

        results = []
        for pdf_file in pdf_files:
            try:
                result = self.ingest_pdf(
                    str(pdf_file),
                    sync_to_graph=sync_to_graph,
                    **kwargs
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to ingest {pdf_file}: {e}")
                results.append(IngestionResult(
                    status="error",
                    pdf_path=str(pdf_file),
                    error_message=str(e)
                ))

        # Summary
        success = sum(1 for r in results if r.status == "success")
        skipped = sum(1 for r in results if r.status == "skipped")
        errors = sum(1 for r in results if r.status == "error")

        logger.info("=" * 60)
        logger.info("BATCH INGESTION SUMMARY")
        logger.info(f"  → Success: {success}")
        logger.info(f"  → Skipped: {skipped}")
        logger.info(f"  → Errors: {errors}")
        logger.info("=" * 60)

        return results

    def sync_all_to_graph(self) -> Dict[str, Any]:
        """
        Sync all documents from Chroma to Neo4j.

        This is useful when you want to bulk-sync after batch ingestion
        without Neo4j sync during each ingest_pdf call.

        Returns:
            Dict with sync stats
        """
        builder = self._get_graph_builder()
        if not builder:
            return {"status": "error", "message": "Neo4j not enabled"}

        return builder.sync_from_chroma()

    def search(self, query: str, n_results: int = 5, filters: Optional[dict] = None) -> List[dict]:
        """
        Search the vector store.

        Args:
            query: Search query
            n_results: Number of results
            filters: Metadata filters

        Returns:
            List of search results
        """
        vectorstore = self._get_vectorstore()

        results = vectorstore.similarity_search_with_score(
            query=query,
            k=n_results,
            filter=filters
        )

        search_results = []
        for doc, score in results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "distance": score
            })

        return search_results

    def close(self):
        """Close all connections."""
        if self._graph_builder:
            self._graph_builder.close()


def create_pipeline(
    llm_client,
    enable_neo4j: bool = True,
    **kwargs
) -> UnifiedIngestionPipeline:
    """
    Factory function to create a unified ingestion pipeline.

    Args:
        llm_client: LLM client for chunking
        enable_neo4j: Whether to enable Neo4j
        **kwargs: Additional arguments for UnifiedIngestionPipeline

    Returns:
        Configured UnifiedIngestionPipeline instance
    """
    return UnifiedIngestionPipeline(
        llm_client=llm_client,
        enable_neo4j=enable_neo4j,
        **kwargs
    )


# Convenience function for simple usage
def ingest_with_graph(
    pdf_path: str,
    llm_client,
    sync_to_graph: bool = True,
    **kwargs
) -> IngestionResult:
    """
    One-liner to ingest a PDF with optional graph sync.

    Args:
        pdf_path: Path to PDF
        llm_client: LLM client
        sync_to_graph: Whether to sync to Neo4j
        **kwargs: Additional arguments

    Returns:
        IngestionResult
    """
    pipeline = UnifiedIngestionPipeline(
        llm_client=llm_client,
        enable_neo4j=sync_to_graph,
        **kwargs
    )
    return pipeline.ingest_pdf(pdf_path, sync_to_graph=sync_to_graph)


def main():
    """CLI for unified ingestion pipeline."""
    import argparse
    from dotenv import load_dotenv

    load_dotenv()

    settings = get_settings()

    parser = argparse.ArgumentParser(description="Unified PDF ingestion: Chroma + Neo4j")
    parser.add_argument("pdf", nargs="?", help="PDF file or directory")
    parser.add_argument("--model", default=settings.openai_model, help="LLM model for chunking")
    parser.add_argument("--provider", default="auto", choices=["auto", "openai", "huggingface"],
                        help="Embedding provider")
    parser.add_argument("--embedding", default=None, help="Embedding model")
    parser.add_argument("--collection", default=settings.chroma_collection_name, help="Collection name")
    parser.add_argument("--graph", action="store_true", help="Sync to Neo4j")
    parser.add_argument("--no-graph", action="store_true", help="Disable Neo4j sync")
    parser.add_argument("--reset", action="store_true", help="Reset Chroma collection")

    args = parser.parse_args()

    # Validate
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY not found")
        return

    # Create LLM
    from langchain_openai import ChatOpenAI
    llm_kwargs = {"model": args.model, "api_key": settings.openai_api_key}
    if settings.openai_api_base:
        llm_kwargs["base_url"] = settings.openai_api_base

    llm = ChatOpenAI(**llm_kwargs)

    # Determine Neo4j setting
    enable_neo4j = args.graph and not args.no_graph
    if args.no_graph and args.graph:
        print("ERROR: Cannot use both --graph and --no-graph")
        return

    print(f"LLM: {args.model}")
    print(f"Embedding: {args.provider}")
    print(f"Neo4j: {'enabled' if enable_neo4j else 'disabled'}")

    # Create pipeline
    pipeline = UnifiedIngestionPipeline(
        llm_client=llm,
        embedding_provider=args.provider,
        embedding_model=args.embedding,
        collection_name=args.collection,
        enable_neo4j=enable_neo4j
    )

    # Reset if requested
    if args.reset:
        vectorstore = pipeline._get_vectorstore()
        logger.info("Resetting collection...")
        vectorstore.delete(where={})

    # Ingest
    if args.pdf:
        pdf_path = Path(args.pdf)
        if pdf_path.is_dir():
            results = pipeline.ingest_directory(str(pdf_path), sync_to_graph=args.graph)
            print(f"\nProcessed {len(results)} files")
        else:
            result = pipeline.ingest_pdf(str(pdf_path), sync_to_graph=args.graph)
            print(f"\nResult: {result}")
    else:
        results = pipeline.ingest_directory(
            str(settings.pdf_storage_path),
            sync_to_graph=args.graph
        )
        print(f"\nProcessed {len(results)} files")

    pipeline.close()


if __name__ == "__main__":
    main()
