"""Neo4j graph node and relationship models."""

from typing import Optional, List
from pydantic import BaseModel, Field


class ExamNode(BaseModel):
    """Exam document node."""
    id: str = Field(description="Unique ID (filename without extension)")
    subject: str = Field(description="Subject (Chimie, Math, SVT, etc.)")
    year: int = Field(description="Exam year")
    serie: str = Field(description="Serie (LLA, SES, SMP, etc.)")
    pdf_path: str = Field(description="Path to PDF file")


class SectionNode(BaseModel):
    """Section node (PARTIE A, PARTIE B, etc.)."""
    name: str = Field(description="Section name (PARTIE A, etc.)")
    points: Optional[int] = Field(default=None, description="Point value")
    order: int = Field(description="Order in exam")


class QuestionNode(BaseModel):
    """Question node."""
    number: str = Field(description="Question number (A1, 2, C1, etc.)")
    chunk_type: str = Field(description="Type (question_fillin, question_open, etc.)")
    topic_hint: Optional[str] = Field(default=None, description="Topic/concept hint")
    has_formula: bool = Field(default=False, description="Contains formulas")
    content: str = Field(description="Question content")
    chunk_index: int = Field(description="Index in chunks array")


class SubQuestionNode(BaseModel):
    """Sub-question node."""
    letter: str = Field(description="Sub-question letter (a, b, c)")
    content: str = Field(description="Sub-question content")
    topic_hint: Optional[str] = Field(default=None, description="Topic hint")
    chunk_index: int = Field(description="Index in chunks array")


class PassageNode(BaseModel):
    """Passage/reading text node."""
    content: str = Field(description="Passage content")
    topic_hint: Optional[str] = Field(default=None, description="Topic hint")
    chunk_index: int = Field(description="Index in chunks array")


class InstructionNode(BaseModel):
    """Instruction node."""
    content: str = Field(description="Instruction content")
    chunk_index: int = Field(description="Index in chunks array")


# Graph relationship data
class ChunkGraphData(BaseModel):
    """Chunk data formatted for graph creation."""
    exam_id: str
    exam_subject: str
    exam_year: int
    exam_serie: str
    pdf_path: str
    section_name: Optional[str] = None
    section_order: Optional[int] = None
    question_number: Optional[str] = None
    question_type: Optional[str] = None
    question_topic: Optional[str] = None
    has_formula: bool = False
    question_content: Optional[str] = None
    sub_question_letter: Optional[str] = None
    sub_question_content: Optional[str] = None
    sub_question_topic: Optional[str] = None
    passage_content: Optional[str] = None
    passage_topic: Optional[str] = None
    instruction_content: Optional[str] = None
    chunk_type: str
    chunk_index: int
