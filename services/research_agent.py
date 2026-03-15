"""Research Agent - coordinates analyses and generates chunking strategy recommendations."""

from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger
import json

from services.pdf_analyzer import PDFAnalyzer, analyze_all_pdfs
from services.doc_analyzer import DocumentationAnalyzer, analyze_docs
from core.patterns import SUBJECT_CONFIGS, UNIVERSAL_RULES


@dataclass
class ResearchReport:
    """Complete research report combining all analyses."""
    pdf_analyses: list = field(default_factory=list)
    doc_analysis: dict = field(default_factory=dict)
    recommendations: dict = field(default_factory=list)
    strategy_summary: str = ""


class ResearchAgent:
    """Coordinates PDF analysis, documentation analysis, and generates recommendations."""

    def __init__(self, pdfs_dir: str | Path = "data/pdfs", docs_dir: str | Path = "docs"):
        self.pdfs_dir = Path(pdfs_dir)
        self.docs_dir = Path(docs_dir)
        self.report: ResearchReport | None = None

    def run_research(self) -> ResearchReport:
        """Run complete research workflow."""
        logger.info("Starting research workflow...")

        self.report = ResearchReport()

        # Step 1: Analyze documentation
        logger.info("Step 1: Analyzing documentation...")
        doc_analyzer = DocumentationAnalyzer(self.docs_dir)
        self.report.doc_analysis = doc_analyzer.analyze()
        self.report.recommendations = doc_analyzer.get_recommendations()

        # Step 2: Analyze PDFs
        logger.info("Step 2: Analyzing PDFs...")
        self.report.pdf_analyses = analyze_all_pdfs(self.pdfs_dir)

        # Step 3: Generate strategy summary
        logger.info("Step 3: Generating strategy summary...")
        self.report.strategy_summary = self._generate_strategy_summary()

        logger.info("Research complete!")
        return self.report

    def _generate_strategy_summary(self) -> str:
        """Generate a comprehensive strategy summary."""
        # Count layout types found
        layout_counts = {}
        subject_counts = {}

        for pdf in self.report.pdf_analyses:
            for layout in pdf.layouts:
                layout_type = layout.layout_type
                layout_counts[layout_type] = layout_counts.get(layout_type, 0) + 1

            subject = pdf.metadata.subject
            subject_counts[subject] = subject_counts.get(subject, 0) + 1

        summary = f"""
# Chunking Strategy Research Summary

## PDF Analysis Results
- Total PDFs analyzed: {len(self.report.pdf_analyses)}
- Page count: {sum(p.page_count for p in self.report.pdf_analyses)}

### Layout Types Found:
"""
        for layout, count in sorted(layout_counts.items()):
            summary += f"- Layout {layout}: {count} pages\n"

        summary += f"""
### Subjects Found:
"""
        for subject, count in sorted(subject_counts.items()):
            summary += f"- {subject}: {count} PDFs\n"

        summary += f"""
## Recommended Strategy

### High Priority Layouts (require special handling):
1. **Layout B (Two-column symmetric)**: Most common - requires column splitting
2. **Layout D (Header + two-column)**: Common in Français - requires y-coordinate detection

### Subject-Specific Strategies:
"""
        for subject, config in SUBJECT_CONFIGS.items():
            summary += f"#### {subject}:\n"
            for rule in config.chunking_rules:
                summary += f"- {rule}\n"
            if config.warnings:
                summary += f"**Warnings:** {', '.join(config.warnings)}\n"
            summary += "\n"

        summary += f"""
## Universal Rules (apply to all):
"""
        for rule in UNIVERSAL_RULES:
            summary += f"- {rule}\n"

        summary += f"""
## Implementation Priority:
1. **Phase 1**: Basic PDF text extraction + layout detection
2. **Phase 2**: Metadata extraction (subject, year, serie)
3. **Phase 3**: Subject-specific pattern application
4. **Phase 4**: LLM-based semantic chunking

## Critical Success Factors:
1. Always detect layout per page (never assume uniform)
2. Split columns before extraction for Layout B/D
3. Extract and propagate metadata from page 1
4. Never split passages or standalone tables
5. Include context in sub_questions for understanding
"""
        return summary

    def save_report(self, output_path: str | Path = "logs/research_report.md"):
        """Save research report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(self.report.strategy_summary)

        logger.info(f"Report saved to {output_path}")


def run_research(pdfs_dir: str | Path = "data/pdfs", docs_dir: str | Path = "docs") -> ResearchReport:
    """Convenience function to run research."""
    agent = ResearchAgent(pdfs_dir, docs_dir)
    report = agent.run_research()
    agent.save_report()
    return report


if __name__ == "__main__":
    logger.add("logs/research.log", rotation="10 MB", level="INFO")

    report = run_research()
    print(report.strategy_summary)
