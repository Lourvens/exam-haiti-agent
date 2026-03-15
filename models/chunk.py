"""Chunk model for indexed content."""

from pydantic import BaseModel, Field
from typing import Optional, List


class ChunkInput(BaseModel):
    """Pydantic model for LLM to generate - used with structured output."""
    content: str = Field(..., description="The actual text content of the chunk")
    chunk_type: str = Field(..., description="Type: exam_header, instructions, passage, question_mcq, question_fillin, question_open, sub_question, table, other")
    section: Optional[str] = Field(None, description="Section name (Partie A, Exercice 1, etc.)")
    question_number: Optional[str] = Field(None, description="Question number (1, 2, 3)")
    sub_question: Optional[str] = Field(None, description="Sub-question identifier (a, b, c, d)")
    has_formula: bool = Field(False, description="Whether chunk contains mathematical formulas")
    topic_hint: Optional[str] = Field(None, description="Topic/concept hint for semantic search")
    subject: str = Field(..., description="Subject (Math, SVT, Physique, etc.)")
    year: int = Field(..., description="Exam year")
    serie: str = Field(..., description="Serie (SMP, SMS, SES, LLA)")


class ChunkResponse(BaseModel):
    """Wrapper for list of chunks from structured output."""
    chunks: List[ChunkInput] = Field(..., description="List of chunks extracted from the document")


class Chunk(BaseModel):
    """A chunk of content from an exam document."""
    content: str = Field(..., description="The actual text content of the chunk")
    chunk_type: str = Field(..., description="Type: exam_header, instructions, passage, question_mcq, question_fillin, question_open, sub_question, table, other")
    exam_file: str = Field(..., description="Source PDF file path")
    page_num: int = Field(0, description="Page number where chunk appears")

    # Context that propagates from metadata
    subject: str = Field(..., description="Subject (Math, SVT, etc.)")
    year: int = Field(..., description="Exam year")
    serie: str = Field(..., description="Serie (SMP, SMS, SES, LLA)")

    # Section identification
    section: Optional[str] = Field(None, description="Section name (Partie A, Exercice 1, etc.)")
    question_number: Optional[str] = Field(None, description="Question number (1, 2, 3, or a, b, c)")
    sub_question: Optional[str] = Field(None, description="Sub-question identifier (a, b, c, d)")

    # Additional metadata
    has_formula: bool = Field(False, description="Whether chunk contains mathematical formulas")
    topic_hint: Optional[str] = Field(None, description="Topic/concept hint for semantic search")
    points: Optional[int] = Field(None, description="Point value if specified")

    def to_dict(self) -> dict:
        """Convert to dictionary for indexing."""
        return {
            "content": self.content,
            "chunk_type": self.chunk_type,
            "exam_file": self.exam_file,
            "page_num": self.page_num,
            "subject": self.subject,
            "year": self.year,
            "serie": self.serie,
            "section": self.section or "",
            "question_number": self.question_number or "",
            "sub_question": self.sub_question or "",
            "has_formula": self.has_formula,
            "topic_hint": self.topic_hint or "",
            "points": self.points or 0
        }

    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [
            f"[{self.chunk_type}]",
            f"Subject: {self.subject} {self.year} {self.serie}",
        ]
        if self.section:
            parts.append(f"Section: {self.section}")
        if self.question_number:
            parts.append(f"Q{self.question_number}")
        if self.sub_question:
            parts.append(f"({self.sub_question})")
        if self.topic_hint:
            parts.append(f"Topic: {self.topic_hint}")
        parts.append(f"\n{self.content}")
        return "\n".join(parts)

    def to_metadata_dict(self) -> dict:
        """Convert to metadata dict for ChromaDB."""
        return {
            "exam_file": self.exam_file,
            "chunk_type": self.chunk_type,
            "subject": self.subject,
            "year": str(self.year),
            "serie": self.serie,
            "section": self.section or "",
            "has_formula": str(self.has_formula)
        }
