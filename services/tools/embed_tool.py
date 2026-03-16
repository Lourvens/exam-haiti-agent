"""Embedding retrieval tool for Chroma."""

from typing import Optional, Dict, Any, List

from app.config import get_settings


class RetrieverTool:
    """Tool for semantic search in Chroma vector store."""

    def __init__(self):
        """Initialize the retriever tool."""
        settings = get_settings()
        self.settings = settings
        self._vectorstore = None
        self._embeddings = None

    def _get_embeddings(self):
        """Get or create embeddings."""
        if self._embeddings is None:
            from services.ingestion_pipeline import EmbeddingProvider
            self._embeddings = EmbeddingProvider.create_embeddings()
        return self._embeddings

    def _get_vectorstore(self):
        """Get or initialize Chroma vector store."""
        if self._vectorstore is None:
            from langchain_chroma import Chroma
            embeddings = self._get_embeddings()

            self._vectorstore = Chroma(
                collection_name=self.settings.chroma_collection_name,
                embedding_function=embeddings,
                persist_directory=str(self.settings.chroma_persist_directory)
            )
        return self._vectorstore

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in exam chunks using embeddings.

        Args:
            query: Search query
            filters: Optional metadata filters
            k: Number of results

        Returns:
            List of matching documents with scores
        """
        vectorstore = self._get_vectorstore()

        # Convert filters to Chroma format
        chroma_filter = None
        if filters:
            chroma_filter = {}
            if "subject" in filters:
                chroma_filter["subject"] = filters["subject"]
            if "year" in filters:
                chroma_filter["year"] = str(filters["year"])
            if "serie" in filters:
                chroma_filter["serie"] = filters["serie"]
            if "chunk_type" in filters:
                chroma_filter["chunk_type"] = filters["chunk_type"]

        results = vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=chroma_filter
        )

        # Format results
        search_results = []
        for doc, score in results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "distance": score,
                "score": 1 / (1 + score)  # Convert distance to similarity score
            })

        return search_results

    def get_by_topic(self, topic: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Get documents by topic hint.

        Args:
            topic: Topic to search for
            k: Number of results

        Returns:
            List of matching documents
        """
        vectorstore = self._get_vectorstore()

        results = vectorstore.similarity_search(
            query=topic,
            k=k,
            filter={"topic_hint": topic}
        )

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]


def create_retriever_tool() -> RetrieverTool:
    """Factory function to create a RetrieverTool."""
    return RetrieverTool()
