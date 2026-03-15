"""PDF processor for extracting text from exam PDFs."""

import fitz
from pathlib import Path
from loguru import logger


class PDFProcessor:
    """Handles PDF text extraction using PyMuPDF."""

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.doc = None

    def __enter__(self):
        self.doc = fitz.open(str(self.pdf_path))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()

    @property
    def page_count(self) -> int:
        return len(self.doc)

    @property
    def metadata(self) -> dict:
        """Get PDF metadata."""
        return self.doc.metadata

    def get_page(self, page_num: int) -> fitz.Page:
        """Get a specific page."""
        return self.doc[page_num]

    def extract_text_raw(self, page_num: int = 0) -> str:
        """Extract text from a page using default method."""
        page = self.get_page(page_num)
        return page.get_text("text")

    def extract_text_blocks(self, page_num: int = 0) -> list[dict]:
        """Extract text blocks with metadata from a page."""
        page = self.get_page(page_num)
        blocks = page.get_text("blocks")
        result = []
        for block in blocks:
            result.append({
                "x0": block[0],
                "y0": block[1],
                "x1": block[2],
                "y1": block[3],
                "text": block[4] if len(block) > 4 else "",
                "type": block[5] if len(block) > 5 else 0,
                "block_no": block[6] if len(block) > 6 else 0
            })
        return result

    def detect_columns(self, page_num: int = 0) -> dict:
        """Detect column layout on a page by analyzing x-coordinates of text blocks."""
        blocks = self.extract_text_blocks(page_num)
        if not blocks:
            return {"layout": "unknown", "columns": 0}

        # Get x0 (left edge) of each block
        x_positions = sorted(set(b["x0"] for b in blocks))

        # Cluster similar x positions (within 50 points)
        clusters = []
        for x in x_positions:
            if not clusters or x - clusters[-1] > 50:
                clusters.append(x)
            else:
                clusters[-1] = (clusters[-1] + x) / 2

        # Determine if single or multi-column
        page_width = self.get_page(page_num).rect.width

        if len(clusters) == 1:
            return {"layout": "A", "columns": 1, "clusters": clusters}
        elif len(clusters) == 2:
            # Check if roughly symmetric (50% split)
            mid = page_width / 2
            if abs(clusters[0] - mid) < 100 and abs(clusters[1] - mid) < 100:
                return {"layout": "B", "columns": 2, "clusters": clusters, "split_point": mid}
            else:
                return {"layout": "C", "columns": 2, "clusters": clusters}
        elif len(clusters) > 2:
            return {"layout": "multi", "columns": len(clusters), "clusters": clusters}

        return {"layout": "unknown", "columns": 0}

    def extract_two_column(self, page_num: int = 0) -> tuple[str, str]:
        """Extract text by splitting into left and right columns."""
        page = self.get_page(page_num)
        page_width = page.rect.width
        mid = page_width / 2

        left_text = []
        right_text = []

        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) >= 5:
                x0, y0, x1, y1, text = block[:5]
                if text and text.strip():
                    if x1 <= mid:
                        left_text.append(text)
                    else:
                        right_text.append(text)

        return "\n".join(left_text), "\n".join(right_text)

    def extract_all_pages(self) -> list[str]:
        """Extract text from all pages."""
        return [self.extract_text_raw(i) for i in range(self.page_count)]


def extract_pdf(pdf_path: str | Path) -> str:
    """Convenience function to extract all text from a PDF."""
    with PDFProcessor(pdf_path) as processor:
        pages = processor.extract_all_pages()
        return "\n\n---PAGE BREAK---\n\n".join(pages)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf = sys.argv[1]
        with PDFProcessor(pdf) as p:
            print(f"Pages: {p.page_count}")
            print(f"Layout: {p.detect_columns()}")
            print("\n---TEXT---")
            print(p.extract_text_raw()[:500])
