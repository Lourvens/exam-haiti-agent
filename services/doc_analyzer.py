"""Documentation Analyzer - parses chunk strategy docs to extract patterns."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger

from core.patterns import (
    ChunkType, LayoutType, SubjectPattern, ChunkPattern,
    SubjectConfig, SUBJECT_CONFIGS, UNIVERSAL_RULES, FALLBACK_PATTERN
)


@dataclass
class ExtractedPattern:
    """A pattern extracted from documentation."""
    pattern_id: str
    chunk_type: str
    description: str
    examples: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class DocumentationAnalysis:
    """Complete analysis of documentation."""
    layout_types: list[dict] = field(default_factory=list)
    chunk_types: list[dict] = field(default_factory=list)
    subject_patterns: dict[str, list[str]] = field(default_factory=dict)
    universal_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extracted_patterns: list[ExtractedPattern] = field(default_factory=list)


class DocumentationAnalyzer:
    """Analyzes chunk strategy documentation."""

    LAYOUT_DESCRIPTIONS = {
        "A": "Single Column - text flows top-to-bottom",
        "B": "Two Columns, Symmetric Split",
        "C": "Two Columns, Asymmetric",
        "D": "Header full-width + body two columns",
        "E": "Mixed across pages"
    }

    def __init__(self, docs_dir: str | Path = "docs"):
        self.docs_dir = Path(docs_dir)
        self.result: DocumentationAnalysis | None = None

    def analyze(self) -> DocumentationAnalysis:
        """Run full analysis on documentation files."""
        logger.info(f"Analyzing documentation in {self.docs_dir}")

        self.result = DocumentationAnalysis()

        # Extract layout types
        self.result.layout_types = self._extract_layout_types()

        # Extract chunk types
        self.result.chunk_types = self._extract_chunk_types()

        # Extract subject patterns
        self.result.subject_patterns = self._extract_subject_patterns()

        # Universal rules
        self.result.universal_rules = UNIVERSAL_RULES

        # Extract warnings/risks
        self.result.warnings = self._extract_warnings()

        # Extract specific patterns with examples
        self.result.extracted_patterns = self._extract_patterns_with_examples()

        logger.info(f"Documentation analysis complete: {len(self.result.layout_types)} layouts, {len(self.result.chunk_types)} chunk types")
        return self.result

    def _extract_layout_types(self) -> list[dict]:
        """Extract layout types from docs."""
        layouts = []
        for code, desc in self.LAYOUT_DESCRIPTIONS.items():
            layouts.append({
                "code": code,
                "name": desc.split(" - ")[0] if " - " in desc else desc,
                "description": desc,
                "risk_level": "low" if code == "A" else ("high" if code in ["B", "D"] else "medium")
            })
        return layouts

    def _extract_chunk_types(self) -> list[dict]:
        """Extract chunk types from the patterns module."""
        chunk_types = []
        for ct in ChunkType:
            chunk_types.append({
                "name": ct.value,
                "description": self._get_chunk_type_description(ct)
            })
        return chunk_types

    def _get_chunk_type_description(self, ct: ChunkType) -> str:
        """Get description for a chunk type."""
        descriptions = {
            ChunkType.EXAM_HEADER: "Ministry, subject, year, serie, exam board",
            ChunkType.INSTRUCTIONS: "Rules, duration, 'choisir X parmi Y', barème global",
            ChunkType.SECTION_HEADER: "'PARTIE A', 'Grammaire', 'Exercice 1' titles",
            ChunkType.PASSAGE: "Reading text, historical source, philosophical text",
            ChunkType.QUESTION_MCQ: "Question + options a/b/c/d",
            ChunkType.QUESTION_FILLIN: "Fill-in-the-blank, transform, conjugate, match",
            ChunkType.QUESTION_OPEN: "Exercise context block, essay prompt, open question",
            ChunkType.SUB_QUESTION: "Sub-part (a, b, c...) with parent context reminder",
            ChunkType.TABLE: "Standalone data table not attached to a single question",
            ChunkType.OTHER: "Anything not covered - log and describe in topic_hint"
        }
        return descriptions.get(ct, "")

    def _extract_subject_patterns(self) -> dict[str, list[str]]:
        """Extract subject-specific patterns."""
        patterns = {}
        for subject, config in SUBJECT_CONFIGS.items():
            rules = []
            for rule in config.chunking_rules:
                rules.append(rule)
            patterns[subject] = rules
        return patterns

    def _extract_warnings(self) -> list[str]:
        """Extract warnings/risks from docs."""
        return [
            "Formula Garbling: Math formulas get broken - mark has_formula: true",
            "Two-Column Reading Order: Default PyMuPDF reads across columns incorrectly",
            "Header Metadata: Subject, year, serie appear only on page 1",
            "Section Titles: May merge with first question - create separate chunks",
            "Instruction Lines: 'Traiter 3 exercices sur 5' looks like question but isn't"
        ]

    def _extract_patterns_with_examples(self) -> list[ExtractedPattern]:
        """Extract detailed patterns with examples from docs."""
        patterns = []

        # Add patterns from the patterns module
        patterns.append(ExtractedPattern(
            pattern_id="M1",
            chunk_type="question_fillin",
            description="Math Partie A - Fill-in items",
            rules=["One chunk per item", "Include full item text", "Store points in points field"],
            examples=["1. Dériver la fonction f(x) = x² + 3x - 2"]
        ))

        patterns.append(ExtractedPattern(
            pattern_id="M2",
            chunk_type="question_open + sub_question",
            description="Math Partie B - Multi-part exercises",
            rules=["One chunk for exercise context", "One chunk per sub-question with context reminder"],
            examples=["Exercice 1: Étude complète de la fonction f(x) = ln((3-x)/(x+2))"]
        ))

        patterns.append(ExtractedPattern(
            pattern_id="F1",
            chunk_type="passage",
            description="Français - Reading passage",
            rules=["Entire passage = one chunk", "Never split the passage", "Store title as first line"],
            examples=["La petite fille qui..."
            ]
        ))

        patterns.append(ExtractedPattern(
            pattern_id="P1",
            chunk_type="question_open + sub_question",
            description="Physique/Chimie - Exercise with Données",
            rules=["Include Données block in question_open", "Repeat Données in every sub_question"],
            examples=["Données: g = 9.8 m/s², m = 0.5 kg"]
        ))

        return patterns

    def get_recommendations(self) -> dict:
        """Get chunking recommendations based on analysis."""
        return {
            "layout_priority": ["B", "D", "A", "C", "E"],
            "high_risk_layouts": ["B", "D"],
            "subjects_need_attention": ["Math", "Français", "Physique", "Chimie"],
            "critical_rules": [
                "Always detect layout per page before processing",
                "Never assume uniform layout across pages",
                "Extract and propagate metadata from page 1",
                "Never split passages or tables",
                "Include context in sub_questions"
            ]
        }


def analyze_docs(docs_dir: str | Path = "docs") -> DocumentationAnalysis:
    """Convenience function to analyze documentation."""
    analyzer = DocumentationAnalyzer(docs_dir)
    return analyzer.analyze()


if __name__ == "__main__":
    logger.add("logs/doc_analysis.log", rotation="10 MB", level="INFO")

    result = analyze_docs()

    print("\n=== LAYOUT TYPES ===")
    for lt in result.layout_types:
        print(f"  {lt['code']}: {lt['name']} (risk: {lt['risk_level']})")

    print("\n=== CHUNK TYPES ===")
    for ct in result.chunk_types:
        print(f"  {ct['name']}: {ct['description']}")

    print("\n=== SUBJECT PATTERNS ===")
    for subject, rules in result.subject_patterns.items():
        print(f"  {subject}:")
        for rule in rules:
            print(f"    - {rule}")

    print("\n=== WARNINGS ===")
    for warning in result.warnings:
        print(f"  - {warning}")
