"""Embedding retrieval tool for Chroma."""

from typing import Optional, Dict, Any, List

from app.config import get_settings

# Subject normalization: French subject names to stored values
SUBJECT_NORMALIZATION = {
    "mathématiques": "Math",
    "mathematiques": "Math",
    "math": "Math",
    "histoire-géographie": "Hist-Geo",
    "histoire geographie": "Hist-Geo",
    "hist-geo": "Hist-Geo",
    "histoire": "Hist-Geo",
    "hg": "Hist-Geo",
    "sciences de la vie et de la terre": "SVT",
    "svt": "SVT",
    "sciences naturelles": "SVT",
    "physique-chimie": "PC",
    "physique": "PC",
    "chimie": "PC",
    "pc": "PC",
}


def normalize_subject(subject: str) -> Optional[str]:
    """Normalize French subject names to stored values.

    Args:
        subject: Raw subject from query (e.g., "Mathématiques")

    Returns:
        Normalized subject (e.g., "Math") or None if not recognized
    """
    if not subject:
        return None
    subject_lower = subject.lower().strip()
    return SUBJECT_NORMALIZATION.get(subject_lower)


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

        Searches both content and metadata fields (topic_hint, subject).
        When filters contain subject/year, prioritizes those over semantic similarity.

        Args:
            query: Search query
            filters: Optional metadata filters
            k: Number of results

        Returns:
            List of matching documents with scores
        """
        vectorstore = self._get_vectorstore()

        # Build filter expressions with subject normalization
        chroma_filter = None
        filter_expressions = []
        has_strong_filters = False  # Bug 2: Track if we have subject/year filters

        if filters:
            # Normalize subject filter (Bug 1)
            if "subject" in filters:
                subject = filters["subject"]
                normalized_subject = normalize_subject(subject)
                if normalized_subject:
                    # Match both original and normalized forms
                    filter_expressions.append({
                        "$or": [
                            {"subject": {"$contains": subject.lower()}},
                            {"subject": {"$contains": normalized_subject.lower()}}
                        ]
                    })
                    has_strong_filters = True
                else:
                    filter_expressions.append({"subject": {"$contains": subject.lower()}})

            if "year" in filters:
                filter_expressions.append({"year": filters["year"]})
                has_strong_filters = True

            if "serie" in filters:
                filter_expressions.append({"serie": {"$contains": filters["serie"].lower()}})

            if "chunk_type" in filters:
                filter_expressions.append({"chunk_type": filters["chunk_type"]})

            if filter_expressions:
                if len(filter_expressions) == 1:
                    chroma_filter = filter_expressions[0]
                else:
                    chroma_filter = {"$and": filter_expressions}

        all_results = []

        # Bug 2: If we have strong filters (subject/year), prioritize filtered search
        # Strategy 1: Search with filters first (prioritized)
        if chroma_filter:
            results = vectorstore.similarity_search_with_score(
                query=query,
                k=k * 2 if has_strong_filters else k,  # Get more results with strong filters
                filter=chroma_filter
            )
            all_results.extend(results)

            # If we have strong filters and got results, return them immediately
            # This prevents semantic similarity from overriding the filters
            if has_strong_filters and all_results:
                # Sort by score and return
                sorted_results = sorted(all_results, key=lambda x: x[1])[:k]
                return self._format_results(sorted_results)

        # Strategy 2: If topic provided, search by topic_hint metadata
        if filters and filters.get("topic"):
            topic_results = vectorstore.similarity_search_with_score(
                query=filters["topic"],
                k=k,
                filter=None  # No filter - search all topics
            )
            all_results.extend(topic_results)

        # Strategy 3: If still no results, fallback to pure semantic search
        if not all_results:
            results = vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=None
            )
            all_results.extend(results)

        # Deduplicate and combine results
        seen = {}
        for doc, score in all_results:
            doc_id = id(doc)
            if doc_id not in seen:
                seen[doc_id] = (doc, score)

        # Sort by score (lower distance = better)
        sorted_results = sorted(seen.values(), key=lambda x: x[1])[:k]

        return self._format_results(sorted_results)

    def _format_results(self, sorted_results: List) -> List[Dict[str, Any]]:
        """Format search results."""
        search_results = []
        for doc, score in sorted_results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "distance": score,
                "score": 1 / (1 + score)
            })
        return search_results

    def get_by_topic(self, topic: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Get documents by topic hint using semantic search.

        Args:
            topic: Topic to search for
            k: Number of results

        Returns:
            List of matching documents
        """
        vectorstore = self._get_vectorstore()

        # Use semantic search to find topics similar to query
        results = vectorstore.similarity_search_with_score(
            query=topic,
            k=k,
            filter=None  # Search all chunks
        )

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": 1 / (1 + score)
            }
            for doc, score in results
        ]


def create_retriever_tool() -> RetrieverTool:
    """Factory function to create a RetrieverTool."""
    return RetrieverTool()
