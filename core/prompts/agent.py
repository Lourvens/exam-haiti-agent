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

# Basic answer prompt
ANSWER_PROMPT = """You are an AI assistant for Haitian Baccalaureate exam questions.

User Query: {query}

Search Type: {search_type}

Context from knowledge base:
{context}

Provide a helpful answer based on the context. If the context doesn't contain
relevant information, say so clearly. Be concise but informative.
"""

# LaTeX instructions (plain text, not a template)
LATEX_INSTRUCTIONS = """
IMPORTANT FORMATTING RULES:
1. When showing mathematical formulas or expressions, use LaTeX format:
   - Inline: $formula$ or (formula)
   - Display: $$formula$$ or [formula]
   - Fractions: use frac{num}{denom}
   - Superscripts: x^2, subscripts: x_2

2. Format examples:
   - f(x) = x^2 -> $f(x) = x^2$
   - a/b -> $frac{a}{b}$
   - e^x -> $e^x$

3. Use markdown tables for structured data when appropriate.
"""


def get_intent_filter_prompt(query: str) -> str:
    """Get the intent filter extraction prompt."""
    return INTENT_FILTER_PROMPT.format(query=query)


def get_answer_prompt(query: str, search_type: str, context: str) -> str:
    """Get the basic answer generation prompt."""
    return ANSWER_PROMPT.format(
        query=query,
        search_type=search_type,
        context=context
    )


def get_latex_answer_prompt(query: str, search_type: str, context: str) -> str:
    """Get the LaTeX-enhanced answer prompt."""
    prompt = f"""You are an AI assistant for Haitian Baccalaureate exam questions.

User Query: {query}

Search Type: {search_type}

Context from knowledge base:
{context}

{LATEX_INSTRUCTIONS}

Provide a helpful answer based on the context. If the context doesn't contain
relevant information, say so clearly."""
    return prompt
