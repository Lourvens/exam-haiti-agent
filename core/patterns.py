"""Data models for chunking patterns."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChunkType(str, Enum):
    """Types of chunks in exam documents."""
    EXAM_HEADER = "exam_header"
    INSTRUCTIONS = "instructions"
    SECTION_HEADER = "section_header"
    PASSAGE = "passage"
    QUESTION_MCQ = "question_mcq"
    QUESTION_FILLIN = "question_fillin"
    QUESTION_OPEN = "question_open"
    SUB_QUESTION = "sub_question"
    TABLE = "table"
    OTHER = "other"


class LayoutType(str, Enum):
    """PDF layout types."""
    SINGLE_COLUMN = "A"  # Single column
    TWO_COL_SYM = "B"    # Two columns symmetric
    TWO_COL_ASYM = "C"   # Two columns asymmetric
    HEADER_BODY = "D"    # Header full-width, body two columns
    MIXED = "E"          # Mixed across pages


class SubjectPattern(str, Enum):
    """Subject-specific patterns."""
    # Math
    M1 = "M1"  # Partie A - fill-in items
    M2 = "M2"  # Partie B - multi-part exercises
    M3 = "M3"  # Statistics table

    # Français
    F1 = "F1"  # Reading passage
    F2 = "F2"  # Comprehension questions (MCQ)
    F3 = "F3"  # Grammar/Vocabulary items

    # SVT
    S1 = "S1"  # With data/diagram description
    S2 = "S2"  # True/false or short knowledge

    # Physique/Chimie
    P1 = "P1"  # Exercise with "Données"

    # Histoire/Géo
    H1 = "H1"  # Source document

    # Économie/Philosophie
    E1 = "E1"  # Essay prompt


@dataclass
class ChunkPattern:
    """A pattern for chunking a specific section type."""
    pattern_id: str
    chunk_type: ChunkType
    description: str
    detection_rules: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)


@dataclass
class SubjectConfig:
    """Configuration for a specific subject."""
    subject: str
    patterns: list[SubjectPattern] = field(default_factory=list)
    chunking_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Subject configurations
SUBJECT_CONFIGS: dict[str, SubjectConfig] = {
    "Math": SubjectConfig(
        subject="Mathématiques",
        patterns=[SubjectPattern.M1, SubjectPattern.M2, SubjectPattern.M3],
        chunking_rules=[
            "Partie A: One chunk per fill-in item (question_fillin)",
            "Partie B: One chunk for exercise context + one per sub-question",
            "Statistics tables: Include in context and each sub_question"
        ],
        warnings=["Formula garbling - mark has_formula: true"]
    ),
    "SVT": SubjectConfig(
        subject="SVT",
        patterns=[SubjectPattern.S1, SubjectPattern.S2],
        chunking_rules=[
            "Partie I: Restitution (QCM, vrai/faux)",
            "Partie II: Application with data/diagrams",
            "Partie III: Synthèse"
        ],
        warnings=["Discipline boundary changes within single column"]
    ),
    "Français": SubjectConfig(
        subject="Français/Communication française",
        patterns=[SubjectPattern.F1, SubjectPattern.F2, SubjectPattern.F3],
        chunking_rules=[
            "I. Compréhension: passage + questions",
            "II. Grammaire: items",
            "III. Vocabulaire/Orthographe/Conjugaison",
            "IV. Production écrite"
        ],
        warnings=["Never split reading passages"]
    ),
    "Physique": SubjectConfig(
        subject="Physique",
        patterns=[SubjectPattern.P1],
        chunking_rules=[
            "Exercice with Données block: include in question_open",
            "Repeat Données in each sub_question"
        ],
        warnings=["Physical constants meaningless without question"]
    ),
    "Chimie": SubjectConfig(
        subject="Chimie",
        patterns=[SubjectPattern.P1],
        chunking_rules=[
            "Exercice with Données block: include in question_open",
            "Repeat Données in each sub_question"
        ],
        warnings=["Formula notation may vary"]
    ),
    "Hist-Geo": SubjectConfig(
        subject="Histoire/Géographie",
        patterns=[SubjectPattern.H1],
        chunking_rules=[
            "Partie I: Questions de cours, Commentaire de document",
            "Partie II: Analyse de carte/données"
        ],
        warnings=["Source document = one passage chunk"]
    ),
    "Économie": SubjectConfig(
        subject="Économie",
        patterns=[SubjectPattern.E1],
        chunking_rules=[
            "I. Questions de connaissances",
            "II. Analyse de document",
            "III. Dissertation/Question de synthèse"
        ],
        warnings=[]
    ),
    "Philosophie": SubjectConfig(
        subject="Philosophie",
        patterns=[SubjectPattern.E1],
        chunking_rules=[
            "Sujet 1: Dissertation",
            "Sujet 2: Explication de texte",
            "Sujet 3: Dissertation alternative"
        ],
        warnings=["Instructions 'choisir un sujet' = instructions, not question"]
    ),
}


# Universal rules for all subjects
UNIVERSAL_RULES = [
    "Detect layout per page (A/B/C/D/E)",
    "Extract subject, year, serie from page 1 header",
    "Never produce empty content field",
    "Propagate metadata (year, subject, serie) to all chunks",
    "For unknown structures: determine 'unit of meaning'",
    "Log unknown patterns with subject, year, exam board, description"
]


# Fallback pattern for unknown structures
FALLBACK_PATTERN = ChunkPattern(
    pattern_id="fallback",
    chunk_type=ChunkType.OTHER,
    description="Used when no specific pattern matches",
    detection_rules=["No pattern matched from subject-specific rules"],
    examples=[],
    required_fields=["content", "topic_hint", "chunk_type"]
)
