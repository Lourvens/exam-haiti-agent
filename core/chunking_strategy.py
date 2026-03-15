"""Chunking strategy definitions - LLM auto-detects strategy."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ChunkingStrategy:
    """Dynamic chunking strategy - LLM determines the best approach."""
    subject: str
    detected_pattern: Optional[str] = None

    def get_llm_prompt(self) -> str:
        """Generate LLM prompt for auto-detection with comprehensive rules."""
        prompt = """You are an expert at analyzing Haitian Baccalaureate exam documents.

Your task is to:
1. Analyze the document structure
2. Detect the subject, year, and serie from the header
3. Identify the logical sections (PARTIE, Exercice, etc.)
4. Determine the best way to chunk this document for RAG

EXAM METADATA TO EXTRACT:
- subject: The exam subject (e.g., Mathématiques, SVT, Physique, Chimie, Histoire, Géographie, Français, Philosophie, Économie)
- year: The exam year (4 digits)
- serie: The serie (e.g., LLA, SES, SMP, SVT, etc.)

CHUNK TYPES (choose appropriate ones):
- exam_header: Ministry header, exam info
- instructions: General instructions ("Choisissez", "Durée", etc.)
- section_header: PARTIE A/B, Exercice 1, etc.
- passage: Reading passage or document to analyze
- question_mcq: Multiple choice questions
- question_fillin: Fill-in-the-blank questions
- question_open: Open-ended questions/exercises
- sub_question: Sub-questions (a, b, c...)
- table: Data tables or statistics
- other: Content that doesn't fit above

SUBJECT-SPECIFIC RULES (apply based on detected subject):

**MATHÉMATIQUES:**
- Partie A: One chunk per fill-in item (question_fillin)
- Partie B: One chunk for exercise context (question_open) + one per sub_question (a, b, c...)
- Include statistics tables in context AND each sub_question that uses them
- Mark has_formula: true for all math content
- Look for: derivée, integrale, limite, fonction, suite, probabilite, geometrie, algebre

**SVT (Sciences de la Vie et de la Terre):**
- Partie I: Restitution (QCM, vrai/faux) - one chunk per item
- Partie II: Application - description + questions in one question_open, sub_questions separate
- Partie III: Synthese - one question_open chunk
- Track discipline boundaries (BIOLOGIE, GEOLOGIE)
- Look for: cellule, ADN, mitose, meiose, photosynthese, ecosysteme genetique

**PHYSIQUE:**
- Each exercice: Donnees block goes in question_open AND each sub_question that uses it
- Physical constants meaningless without the question context
- Include diagrams/descriptions in the chunk
- Mark has_formula: true for physics formulas

**CHIMIE:**
- Each exercice: Donnees block goes in question_open AND each sub_question
- Include chemical equations in the chunk
- Mark has_formula: true for chemical formulas
- Look for: reaction, molecule, atome, liaison, oxydoreduction

**HISTOIRE/GÉOGRAPHIE:**
- Source document = one passage chunk (NEVER split)
- Questions about document = separate question_open chunks
- Partie I: Questions de cours, Commentaire de document
- Partie II: Analyse de carte/donnees
- Look for: guerre, revolution, traite, carte, population

**FRANÇAIS:**
- I. Comprehension: entire passage = one passage chunk (NEVER split)
- II. Grammaire: one chunk per item (question_fillin)
- III. Vocabulaire/Orthographe: one chunk per item
- IV. Production ecrite: one question_open chunk per sujet

**PHILOSOPHIE:**
- Each sujet (Dissertation, Explication de texte) = one question_open chunk
- "Choisissez un sujet parmi" = instructions chunk, NOT question
- Include full text of sujet to analyze

**ÉCONOMIE:**
- I. Questions de connaissances - one question_open per question
- II. Analyse de document - passage chunk + question_open
- III. Dissertation - one question_open per sujet

GENERAL RULES:
- NEVER split reading passages (keep them as one chunk)
- Include "Donnees" (given data) in the same chunk as questions that use it
- Propagate metadata (subject, year, serie) to ALL chunks
- Mark has_formula: true for math/chemical content
- For sub_questions, include context from parent question
- If subject cannot be determined, analyze content patterns and infer subject

IMPORTANT - RULES MAY VARY:
- The rules above are GUIDELINES, not strict rules
- Each exam may have DIFFERENT structure than expected
- ALWAYS analyze the ACTUAL document structure first
- Adapt your chunking based on what you see in the document
- If the document doesn't match expected patterns, create sensible chunks anyway
- Trust your analysis of the document over these guidelines

Respond ONLY with a JSON array of chunks. Each chunk must have:
- content (string, the actual text, never empty)
- chunk_type (one of the types above)
- section (string, section name if applicable)
- question_number (string, question number if applicable)
- sub_question (string, sub-question letter if applicable)
- has_formula (boolean, true if contains math/chemical formulas)
- topic_hint (brief description of the topic/concept)
- subject (the exam subject)
- year (the exam year)
- serie (the exam serie)

If you cannot determine subject/year/serie, infer from content patterns.
"""
        return prompt


def get_auto_strategy(subject: str = "Unknown") -> ChunkingStrategy:
    """Get a dynamic strategy - LLM will auto-detect."""
    return ChunkingStrategy(subject=subject)

