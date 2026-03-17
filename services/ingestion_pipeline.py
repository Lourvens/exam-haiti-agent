"""Full ingestion pipeline: PDF -> Chunk -> Embed -> Store in Chroma."""

import os
from pathlib import Path
from typing import List, Optional, Union

from loguru import logger

from models.chunk import Chunk
from core.chunking_graph import LangGraphChunkingEngine
from app.config import get_settings


class EmbeddingProvider:
    """Manages embedding providers (OpenAI, HuggingFace)."""

    # Supported providers and their default models
    PROVIDER_CONFIGS = {
        "openai": {
            "default_model": "text-embedding-3-small",
            "models": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]
        },
        "huggingface": {
            "default_model": "sentence-transformers/all-MiniLM-L6-v2",
            "models": [
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
                "intfloat/e5-base-v2",
                "intfloat/e5-small-v2"
            ]
        }
    }

    @classmethod
    def get_available_provider(cls) -> str:
        """
        Get the available embedding provider using settings.

        Returns:
            Provider name ('openai' or 'huggingface')

        Raises:
            ValueError: If no provider is available
        """
        settings = get_settings()
        return settings.effective_embedding_provider

    @classmethod
    def get_model(cls, provider: Optional[str] = None) -> str:
        """
        Get the embedding model using settings.

        Args:
            provider: Override the provider (optional)

        Returns:
            Model name string
        """
        settings = get_settings()

        if provider is None:
            provider = settings.effective_embedding_provider

        return settings.effective_embedding_model

    @classmethod
    def create_embeddings(cls, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Create embeddings based on settings.

        Priority for model selection:
        1. Explicit model parameter
        2. Settings (embedding_model, openai_embedding_model, hf_embedding_model)
        3. Default model for provider

        Args:
            provider: Force a specific provider ('openai' or 'huggingface')
            model: Override the default model

        Returns:
            LangChain embeddings instance
        """
        # Get settings
        settings = get_settings()

        # Determine provider
        if provider is None or provider == "auto":
            provider = settings.effective_embedding_provider

        # Determine model: explicit > settings > default
        selected_model = model
        if not selected_model:
            selected_model = settings.effective_embedding_model

        logger.info(f"Creating {provider} embeddings with model: {selected_model}")

        if provider == "openai":
            return cls._create_openai_embeddings(
                selected_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base
            )
        elif provider == "huggingface":
            return cls._create_huggingface_embeddings(
                selected_model,
                token=settings.hf_token or settings.hf_api_key
            )

        raise ValueError(f"Unknown provider: {provider}")

    @classmethod
    def _create_openai_embeddings(cls, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Create OpenAI embeddings."""
        from langchain_openai import OpenAIEmbeddings

        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")

        kwargs = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        return OpenAIEmbeddings(**kwargs)

    @classmethod
    def _create_huggingface_embeddings(cls, model: str, token: Optional[str] = None):
        """Create HuggingFace embeddings."""
        from langchain_huggingface import HuggingFaceEmbeddings

        kwargs = {
            "model_name": model,
            "encode_kwargs": {"normalize_embeddings": True}
        }

        if token:
            kwargs["model_kwargs"] = {"token": token}

        return HuggingFaceEmbeddings(**kwargs)


class IngestionPipeline:
    """Full pipeline to ingest PDFs into Chroma vector store."""

    def __init__(
        self,
        llm_client,
        embedding_provider: Optional[str] = None,  # "auto", "openai", or "huggingface"
        embedding_model: Optional[str] = None,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None
    ):
        """
        Initialize ingestion pipeline.

        Args:
            llm_client: LLM client for chunking
            embedding_provider: Embedding provider ('auto', 'openai', or 'huggingface')
            embedding_model: Embedding model name (auto-selected if not specified)
            collection_name: Chroma collection name (default from settings)
            persist_directory: Chroma persistence directory (default from settings)
        """
        # Get settings for defaults
        settings = get_settings()

        self.llm_client = llm_client
        self.embedding_provider = embedding_provider or "auto"
        self.embedding_model = embedding_model
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_directory = persist_directory or str(settings.chroma_persist_directory)
        self.chunks_dir = str(settings.chunks_output_path)
        self.chunking_engine = LangGraphChunkingEngine(llm_client, verbose=True)
        self._vectorstore = None
        self._embeddings = None

    def _save_chunks_to_file(self, chunks: list, pdf_path: str, pdf_name: str):
        """Save chunks to a JSON file in data/chunks folder."""
        import json
        from pathlib import Path

        chunks_dir = Path(self.chunks_dir)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # Convert chunks to serializable format
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
                    "points": int(chunk.points) if chunk.points else 0
                })
            except Exception as e:
                logger.warning(f"  → Error serializing chunk {i}: {e}")
                continue

        # Save to JSON file
        output_file = chunks_dir / f"chunks_{pdf_name}.json"
        data = {
            "pdf_path": str(pdf_path),
            "total_chunks": len(chunks_data),
            "chunks": chunks_data
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"  → Saved {len(chunks_data)} chunks to {output_file}")

    def _get_embeddings(self):
        """Get or create embeddings based on provider configuration."""
        if self._embeddings is None:
            # Determine provider
            if self.embedding_provider == "auto":
                provider = None  # Will auto-detect
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

            # Create embeddings
            embeddings = self._get_embeddings()

            # Create or get vector store
            self._vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_directory
            )

            count = self._vectorstore._collection.count()
            logger.info(f"Collection '{self.collection_name}' ready with {count} existing chunks")

        return self._vectorstore

    def ingest_pdf(
        self,
        pdf_path: str,
        batch_size: int = 100,
        skip_existing: bool = True
    ) -> dict:
        """
        Ingest a PDF into the vector store.

        Args:
            pdf_path: Path to PDF file
            batch_size: Number of chunks to embed per batch
            skip_existing: Skip if PDF already indexed

        Returns:
            Dictionary with ingestion stats
        """
        pdf_path = Path(pdf_path)
        pdf_name = pdf_path.stem

        logger.info("=" * 60)
        logger.info(f"INGESTING: {pdf_path}")
        logger.info("=" * 60)

        vectorstore = self._get_vectorstore()

        # Check if already indexed
        if skip_existing:
            existing = vectorstore.get(where={"source": str(pdf_path)})
            if existing and existing.get("ids"):
                logger.info(f"PDF already indexed with {len(existing['ids'])} chunks. Skipping.")
                return {
                    "status": "skipped",
                    "pdf_path": str(pdf_path),
                    "chunks": len(existing['ids']),
                    "message": "Already indexed"
                }

        # Step 1: Chunk the PDF
        logger.info("Step 1: Chunking PDF...")
        chunks = self.chunking_engine.chunk_pdf(pdf_path)
        logger.info(f"  → Generated {len(chunks)} chunks")

        # Save chunks to file if enabled
        from app.config import get_settings
        settings = get_settings()
        if settings.save_chunks_to_file:
            self._save_chunks_to_file(chunks, pdf_path, pdf_name)

        if not chunks:
            return {
                "status": "error",
                "pdf_path": str(pdf_path),
                "chunks": 0,
                "message": "No chunks generated"
            }

        # Step 2: Prepare documents and metadata
        logger.info("Step 2: Preparing documents and metadata...")

        texts = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            doc_id = f"{pdf_name}_{i}"

            # Document for embedding - clean the text
            text = chunk.to_text()
            # Replace newlines with spaces for cleaner embedding
            text = " ".join(text.split())

            # Skip empty texts
            if not text or len(text.strip()) < 5:
                logger.warning(f"Skipping empty chunk {i}")
                continue

            ids.append(doc_id)
            texts.append(text)

            # Metadata for filtering
            metadatas.append({
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
            })

        # Step 3: Add to vector store
        logger.info("Step 3: Adding to Chroma...")

        # Delete existing chunks for this PDF first
        existing = vectorstore.get(where={"source": str(pdf_path)})
        if existing and existing.get("ids"):
            logger.info(f"  → Deleting {len(existing['ids'])} existing chunks")
            vectorstore.delete(ids=existing["ids"])

        # Debug: Check texts
        logger.info(f"  → Text count: {len(texts)}")
        for j, t in enumerate(texts[:3]):
            logger.info(f"    [{j}] type={type(t)}, len={len(t) if t else 0}, content={str(t)[:50]}")

        # Convert all to strings explicitly
        texts = [str(t) if t else "" for t in texts]

        # Add all at once
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        final_count = vectorstore._collection.count()

        # Bug 4: Sync to Neo4j after ingestion
        self._sync_to_graph()

        logger.info("=" * 60)
        logger.info(f"✓ INGESTION COMPLETE")
        logger.info(f"  → Added: {len(texts)} chunks")
        logger.info(f"  → Total in collection: {final_count}")
        logger.info("=" * 60)

        return {
            "status": "success",
            "pdf_path": str(pdf_path),
            "chunks": len(texts),
            "total_in_collection": final_count
        }

    def _sync_to_graph(self):
        """Sync newly ingested chunks to Neo4j graph."""
        settings = get_settings()

        if not settings.neo4j_enabled:
            logger.info("Neo4j not enabled, skipping graph sync")
            return

        try:
            from services.graph_builder import ChromaToNeo4jSync

            logger.info("Step 4: Syncing to Neo4j graph...")
            syncer = ChromaToNeo4jSync()
            result = syncer.sync_from_chroma()
            logger.info(f"  → Graph sync complete: {result}")
        except Exception as e:
            logger.warning(f"  → Graph sync failed: {e}")

    def ingest_directory(
        self,
        pdf_directory: str,
        pattern: str = "*.pdf",
        **kwargs
    ) -> List[dict]:
        """
        Ingest all PDFs in a directory.

        Args:
            pdf_directory: Directory containing PDFs
            pattern: File pattern to match
            **kwargs: Arguments for ingest_pdf

        Returns:
            List of ingestion results
        """
        pdf_dir = Path(pdf_directory)
        pdf_files = sorted(pdf_dir.glob(pattern))

        logger.info(f"Found {len(pdf_files)} PDF files in {pdf_directory}")

        results = []
        for pdf_file in pdf_files:
            try:
                result = self.ingest_pdf(str(pdf_file), **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to ingest {pdf_file}: {e}")
                results.append({
                    "status": "error",
                    "pdf_path": str(pdf_file),
                    "error": str(e)
                })

        # Summary
        success = sum(1 for r in results if r.get("status") == "success")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        errors = sum(1 for r in results if r.get("status") == "error")

        logger.info("=" * 60)
        logger.info("BATCH INGESTION SUMMARY")
        logger.info(f"  → Success: {success}")
        logger.info(f"  → Skipped: {skipped}")
        logger.info(f"  → Errors: {errors}")
        logger.info("=" * 60)

        return results

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[dict] = None
    ) -> List[dict]:
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

        # Format results
        search_results = []
        for doc, score in results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "distance": score
            })

        return search_results


def main():
    """CLI for ingestion pipeline."""
    import argparse
    from dotenv import load_dotenv

    load_dotenv()

    # Get settings
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Ingest PDFs into vector store")
    parser.add_argument("pdf", nargs="?", help="PDF file or directory")
    parser.add_argument("--model", default=settings.openai_model, help="LLM model for chunking")
    parser.add_argument("--provider", default="auto", choices=["auto", "openai", "huggingface"],
                        help="Embedding provider (auto-detect by default)")
    parser.add_argument("--embedding", default=None, help="Embedding model (auto-selected based on provider)")
    parser.add_argument("--collection", default=settings.chroma_collection_name, help="Collection name")
    parser.add_argument("--reset", action="store_true", help="Reset collection before ingesting")

    args = parser.parse_args()

    # Check for LLM API key
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY not found for LLM")
        print("Please create a .env file with your API key:")
        print("  OPENAI_API_KEY=your_key_here")
        return

    # Create LLM
    from langchain_openai import ChatOpenAI
    llm_kwargs = {"model": args.model, "api_key": settings.openai_api_key}
    if settings.openai_api_base:
        llm_kwargs["base_url"] = settings.openai_api_base

    llm = ChatOpenAI(**llm_kwargs)

    # Show which embedding will be used
    effective_provider = settings.effective_embedding_provider
    effective_model = args.embedding or settings.effective_embedding_model

    print(f"LLM: {args.model}")
    print(f"Embedding provider: {args.provider} ({effective_provider})")
    print(f"Embedding model: {effective_model}")

    # Create pipeline
    pipeline = IngestionPipeline(
        llm_client=llm,
        embedding_provider=args.provider,
        embedding_model=args.embedding,
        collection_name=args.collection
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
            results = pipeline.ingest_directory(str(pdf_path))
            print(f"\nProcessed {len(results)} files")
        else:
            result = pipeline.ingest_pdf(str(pdf_path))
            print(f"\nResult: {result}")
    else:
        # Default: ingest data/pdfs
        results = pipeline.ingest_directory(str(settings.pdf_storage_path))
        print(f"\nProcessed {len(results)} files")


if __name__ == "__main__":
    main()
