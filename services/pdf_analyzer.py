"""PDF Structure Analyzer - analyzes exam PDF layouts and metadata."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger

from services.pdf_processor import PDFProcessor


@dataclass
class ExamMetadata:
    """Extracted exam metadata."""
    subject: str = ""
    year: int = 0
    serie: str = ""
    exam_center: str = ""
    duration: str = ""
    session: str = ""  # "juin", "septembre", "decembre", etc.


@dataclass
class PageLayout:
    """Layout analysis for a single page."""
    page_num: int
    layout_type: str  # A, B, C, D, E, or unknown
    column_count: int
    has_header: bool = True
    split_point: float = 0.0
    notes: str = ""


@dataclass
class PDFAnalysisResult:
    """Complete analysis of a PDF."""
    file_path: str
    page_count: int
    dimensions: tuple[float, float]
    metadata: ExamMetadata = field(default_factory=ExamMetadata)
    layouts: list[PageLayout] = field(default_factory=list)
    raw_text_preview: str = ""


class PDFAnalyzer:
    """Analyzes PDF structure for exam content."""

    # Subject detection patterns
    SUBJECT_PATTERNS = {
        "Math": [r"mathématiques?\s*(?:ns4)?", r"mathematiques", r"math\s", r"\bmath\b"],
        "SVT": [r"\bsvt\b", r"sciences?\s*(?:de la )?vie et (?:de la )?terre", r"svt\s"],
        "Physique": [r"physique", r"\bphys\b"],
        "Chimie": [r"chimie", r"\bchim\b"],
        "Hist-Geo": [r"histoire", r"géographie", r"hist-geo", r"histoire-géographie"],
        "Français": [r"français", r"communication\s*française", r"francais"],
        "Philosophie": [r"philosophie", r"\bphilo\b"],
        "Économie": [r"économie", r"\becon\b"],
        "Anglais": [r"anglais", r"\bang\b"],
    }

    # Year detection patterns
    YEAR_PATTERN = r"\b(20\d{2}|19\d{2})\b"

    # Serie patterns
    SERIE_PATTERNS = {
        "SMP": [r"\bsmp\b", r"sciences\s*mathématiques?\s*physique"],
        "SMS": [r"\bsms\b", r"sciences\s*mathématiques?\s*svt"],
        "SES": [r"\bses\b", r"sciences\s*économiques?\s*et\s*sociales?"],
        "LLA": [r"\blla\b", r"lettres?\s*langues?\s*anciennes?"],
    }

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.result: PDFAnalysisResult | None = None

    def analyze(self) -> PDFAnalysisResult:
        """Run full analysis on the PDF."""
        logger.info(f"Analyzing PDF: {self.pdf_path}")

        with PDFProcessor(self.pdf_path) as processor:
            self.result = PDFAnalysisResult(
                file_path=str(self.pdf_path),
                page_count=processor.page_count,
                dimensions=(processor.get_page(0).rect.width, processor.get_page(0).rect.height),
                raw_text_preview=processor.extract_text_raw(0)[:1000]
            )

            # Extract metadata from first page
            self.result.metadata = self._extract_metadata(processor.extract_text_raw(0))

            # Analyze layout per page
            self.result.layouts = self._analyze_layouts(processor)

        logger.info(f"Analysis complete: {self.result.metadata.subject} {self.result.metadata.year} ({self.result.metadata.serie})")
        return self.result

    def _extract_metadata(self, text: str) -> ExamMetadata:
        """Extract exam metadata from text."""
        metadata = ExamMetadata()

        # Detect subject
        text_lower = text.lower()
        for subject, patterns in self.SUBJECT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    metadata.subject = subject
                    break
            if metadata.subject:
                break

        # Detect year
        year_match = re.search(self.YEAR_PATTERN, text)
        if year_match:
            metadata.year = int(year_match.group(1))

        # Detect serie
        for serie, patterns in self.SERIE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    if metadata.serie and serie not in metadata.serie:
                        metadata.serie += "/" + serie
                    else:
                        metadata.serie = serie
                    break

        # Detect duration
        duration_match = re.search(r"(\d+h\s*\d*|minutes?)", text_lower)
        if duration_match:
            metadata.duration = duration_match.group(1)

        # Detect session/month
        session_match = re.search(r"(juin|septembre|décembre|decembre|février|fevrier|avril|mars|normal|second)", text_lower)
        if session_match:
            metadata.session = session_match.group(1)

        return metadata

    def _analyze_layouts(self, processor: PDFProcessor) -> list[PageLayout]:
        """Analyze layout for each page."""
        layouts = []

        for page_num in range(processor.page_count):
            layout_info = processor.detect_columns(page_num)
            blocks = processor.extract_text_blocks(page_num)

            page_layout = PageLayout(
                page_num=page_num,
                layout_type=layout_info.get("layout", "unknown"),
                column_count=layout_info.get("columns", 1),
                split_point=layout_info.get("split_point", 0.0)
            )

            # Check for header (full-width content at top)
            if blocks:
                top_blocks = [b for b in blocks if b["y0"] < 100]
                if top_blocks:
                    # Check if top blocks span full width
                    widths = [b["x1"] - b["x0"] for b in top_blocks]
                    page_layout.has_header = any(w > processor.get_page(page_num).rect.width * 0.7 for w in widths)

            layouts.append(page_layout)

        return layouts


def analyze_pdf(pdf_path: str | Path) -> PDFAnalysisResult:
    """Convenience function to analyze a PDF."""
    analyzer = PDFAnalyzer(pdf_path)
    return analyzer.analyze()


def analyze_all_pdfs(pdfs_dir: str | Path) -> list[PDFAnalysisResult]:
    """Analyze all PDFs in a directory."""
    pdfs_dir = Path(pdfs_dir)
    results = []

    for pdf_file in sorted(pdfs_dir.glob("*.pdf")):
        try:
            result = analyze_pdf(pdf_file)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to analyze {pdf_file}: {e}")

    return results


if __name__ == "__main__":
    import sys

    # Add file handler for logging
    logger.add("logs/pdf_analysis.log", rotation="10 MB", level="INFO")

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if Path(path).is_dir():
            results = analyze_all_pdfs(path)
            for r in results:
                print(f"\n=== {Path(r.file_path).name} ===")
                print(f"  Subject: {r.metadata.subject}, Year: {r.metadata.year}, Serie: {r.metadata.serie}")
                print(f"  Pages: {r.page_count}")
                print(f"  Layouts: {[l.layout_type for l in r.layouts]}")
        else:
            result = analyze_pdf(path)
            print(f"\n=== {Path(result.file_path).name} ===")
            print(f"  Subject: {result.metadata.subject}")
            print(f"  Year: {result.metadata.year}")
            print(f"  Serie: {result.metadata.serie}")
            print(f"  Duration: {result.metadata.duration}")
            print(f"  Session: {result.metadata.session}")
            print(f"  Pages: {result.page_count}")
            print(f"  Layouts: {[l.layout_type for l in result.layouts]}")
