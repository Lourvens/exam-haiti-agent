"""Public API for PDF downloads."""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings


router = APIRouter(prefix="/pdfs", tags=["pdfs"])


@router.get("/{exam_id}")
async def get_pdf(exam_id: str):
    """
    Download a PDF file by exam ID (public, no auth required).

    Args:
        exam_id: The exam ID (e.g., 'Math-NS4-2025-SMP-Graphe')

    Returns:
        PDF file
    """
    settings = get_settings()
    pdf_dir = settings.pdf_storage_path

    # Find PDF matching exam_id
    pdf_files = list(pdf_dir.glob(f"*{exam_id}*.pdf"))

    if not pdf_files:
        # Try without extension
        pdf_files = list(pdf_dir.glob(f"{exam_id}.pdf"))

    if not pdf_files:
        raise HTTPException(status_code=404, detail=f"PDF not found for exam: {exam_id}")

    pdf_path = pdf_files[0]

    return FileResponse(
        path=pdf_path,
        filename=pdf_path.name,
        media_type="application/pdf"
    )


@router.get("/")
async def list_pdfs():
    """
    List all available PDF files (public, no auth required).

    Returns:
        List of PDF files with metadata
    """
    settings = get_settings()
    pdf_dir = settings.pdf_storage_path

    pdfs = []
    for pdf_file in pdf_dir.glob("*.pdf"):
        pdfs.append({
            "exam_id": pdf_file.stem,
            "filename": pdf_file.name,
            "size": pdf_file.stat().st_size,
            "download_url": f"/api/v1/pdfs/{pdf_file.stem}"
        })

    return {
        "pdfs": pdfs,
        "total": len(pdfs)
    }
