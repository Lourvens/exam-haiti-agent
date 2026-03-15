"""Exam metadata model."""

from pydantic import BaseModel, Field
from typing import Optional


class Exam(BaseModel):
    """Exam document metadata."""
    file_path: str = Field(..., description="Path to the PDF file")
    subject: str = Field(..., description="Subject (Math, SVT, Chimie, etc.)")
    year: int = Field(..., description="Exam year (2025, 2024, etc.)")
    serie: str = Field(..., description="Serie (SMP, SMS, SES, LLA, etc.)")
    exam_center: Optional[str] = Field(None, description="Exam center name")
    duration: Optional[str] = Field(None, description="Duration (3h, 2h30, etc.)")
    session: Optional[str] = Field(None, description="Session (juin, septembre, decembre)")
    page_count: int = Field(0, description="Number of pages")

    @classmethod
    def from_pdf_analysis(cls, analysis_result) -> "Exam":
        """Create Exam from PDF analysis result."""
        return cls(
            file_path=analysis_result.file_path,
            subject=analysis_result.metadata.subject,
            year=analysis_result.metadata.year,
            serie=analysis_result.metadata.serie,
            exam_center=analysis_result.metadata.exam_center,
            duration=analysis_result.metadata.duration,
            session=analysis_result.metadata.session,
            page_count=analysis_result.page_count
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for indexing."""
        return {
            "subject": self.subject,
            "year": self.year,
            "serie": self.serie,
            "exam_center": self.exam_center or "",
            "duration": self.duration or "",
            "session": self.session or "",
            "page_count": self.page_count
        }
