"""Prompts for the exam agent."""

from .agent import (
    INTENT_FILTER_PROMPT,
    ANSWER_PROMPT,
    LATEX_INSTRUCTIONS,
    get_intent_filter_prompt,
    get_answer_prompt,
    get_latex_answer_prompt,
)

__all__ = [
    "INTENT_FILTER_PROMPT",
    "ANSWER_PROMPT",
    "LATEX_INSTRUCTIONS",
    "get_intent_filter_prompt",
    "get_answer_prompt",
    "get_latex_answer_prompt",
]
