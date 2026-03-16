"""Agent prompts for the exam agent."""

from typing import Optional


INTENT_FILTER_PROMPT = """
Analyze this query about Haitian Baccalaureate exams and extract any filters:

Query: {query}

Extract:
- subject: What subject (e.g., Chimie, Physique, Mathématiques, Français, etc.)
- year: What year (e.g., 2023, 2022)
- serie: What series (e.g., A, C, D, E, F1, F2, F3, F4, F7)
- topic: Any specific topic or keyword mentioned

Return a JSON object with these fields. If not mentioned, use null.
"""

ANSWER_PROMPT = """
You are an AI assistant for Haitian Baccalaureate exam questions.

User Query: {query}

Search Type: {search_type}

Context from knowledge base:
{context}

Provide a helpful answer based on the context. If the context doesn't contain
relevant information, say so clearly. Be concise but informative.
"""


def get_intent_filter_prompt(query: str) -> str:
    """Get the intent filter extraction prompt."""
    return INTENT_FILTER_PROMPT.format(query=query)


def get_answer_prompt(query: str, search_type: str, context: str) -> str:
    """Get the answer generation prompt."""
    return ANSWER_PROMPT.format(
        query=query,
        search_type=search_type,
        context=context
    )
