# ExamHaiti — PDF Structure Analysis & Chunking Strategy Guide

## Purpose

This document describes every PDF structure pattern observed in Haitian
Baccalaureate exam documents and prescribes the exact chunking strategy
to apply for each. It is the reference for anyone building or maintaining
the chunking pipeline.

When a new PDF is encountered, use this document to identify its structure
type, then apply the corresponding strategy. If the structure is not listed,
follow the **Unknown Structure Protocol** at the end.

---

## How to Use This Document

1. Open the PDF and identify its **layout type** (Section 1)
2. Identify its **subject** (Section 2)
3. Find the matching **structure pattern** (Section 3)
4. Apply the prescribed **chunking strategy** for that pattern
5. If unsure, apply the **fallback strategy** (Section 4)

---

## Section 1 — Layout Types

Before looking at content, identify the physical layout of the page.
This determines how the PDF extractor must read it before the LLM sees it.

---

### Layout A — Single Column

```
┌─────────────────────────────┐
│  HEADER                     │
│  Instructions               │
│                             │
│  Question 1 ............... │
│  Question 2 ............... │
│  Question 3 ............... │
│                             │
│  Exercice 1                 │
│    a) ...................   │
│    b) ...................   │
└─────────────────────────────┘
```

**Seen in:** Physique, Chimie, Histoire, Géographie, Économie, Philosophie.
Also common in older MENFP exams across all subjects.

**Extraction:** PyMuPDF default `page.get_text("text")` reads correctly top-to-bottom.
No column splitting needed.

**Risk:** Low. Single reading order, no ambiguity.

---

### Layout B — Two Columns (symmetric split)

```
┌──────────────┬──────────────┐
│  HEADER (full width)        │
├──────────────┬──────────────┤
│ PARTIE A     │ PARTIE B     │
│              │              │
│ Q1 ........  │ Exercice 1   │
│ Q2 ........  │   a) ......  │
│ Q3 ........  │   b) ......  │
│              │              │
│ Q4 ........  │ Exercice 2   │
│              │   a) ......  │
└──────────────┴──────────────┘
```

**Seen in:** Mathématiques (very common), Français/Communication française,
SVT. Dominant layout in recent MENFP exams.

**Extraction:** Must split at page midpoint before reading.
Read full left column first, then full right column.
PyMuPDF default reads left-to-right across columns and produces garbled text.

**Risk:** High if not handled. A question starting on the left column
can get merged mid-sentence with a question from the right column.

---

### Layout C — Two Columns (asymmetric)

```
┌───────────────────┬──────────┐
│  HEADER (full)               │
├───────────────────┬──────────┤
│ Wide column       │ Narrow   │
│ (text/questions)  │ (notes / │
│                   │ barème / │
│                   │ images)  │
└───────────────────┴──────────┘
```

**Seen in:** Some SVT exams with diagrams, some Physique exams with
circuit schemas, occasional Français exams with margin notes.

**Extraction:** Do not split at 50%. Detect the column boundary from
block positions. The narrow column often contains non-essential content
(point values, figure references) — it must still be extracted but can
be appended after the wide column.

**Risk:** Medium. Narrow column content is easy to lose if not detected.

---

### Layout D — Header full width + body two columns

```
┌─────────────────────────────┐
│  HEADER (full width)        │
│  Instructions (full width)  │
│  Reading passage (full)     │
├──────────────┬──────────────┤
│ Questions    │ Grammaire    │
│ on passage   │ section      │
└──────────────┴──────────────┘
```

**Seen in:** Français/Communication française (most common structure).
The reading passage spans full width. Questions below split into columns.

**Extraction:** The page switches between single-column and two-column
within the same page. Must detect where the split begins using block
y-coordinates, not assume the whole page is one layout type.

**Risk:** High. The passage must be read as full-width. The questions
below must be read as two columns. Treating the whole page as two columns
cuts the passage in half.

---

### Layout E — Mixed across pages

The layout changes between pages of the same document.
Common in multi-section exams (e.g. page 1 single column header +
instructions, page 2 two-column questions).

**Extraction:** Detect layout per page independently, not per document.
Never assume all pages share the same layout.

**Risk:** Medium. Handled automatically if the per-page layout detection
runs on every page.

---

## Section 2 — Subject Profiles

Each subject has a predictable internal structure. Knowing the subject
tells you what to expect before reading the content.

---

### Mathématiques

**Typical structure:**
```
HEADER
Instructions
─────────────────────────────────────────────
PARTIE A — Recopier et compléter (fill-in)
  Items 1 to 10, 4 pts each
─────────────────────────────────────────────
PARTIE B — Traiter 3 exercices sur 5
  Exercice 1 — Fonction / Courbe
    a) b) c) d)
  Exercice 2 — Suites
    a) b) c) d)
  Exercice 3 — Nombres complexes
    a) b) c) d)
  Exercice 4 — Probabilité / Statistiques
    a) b) c) d)
  Exercice 5 — Statistiques bivariées
    a) b) c) d)
```

**Layout:** Almost always two columns (Layout B).
Header and instructions span full width. Partie A left, Partie B right,
or both sections interleaved across columns.

**Special challenges:**
- Mathematical formulas get heavily garbled by PDF extraction (integrals,
  fractions, Greek letters, limits, subscripts)
- Tables in statistics exercises (Exercice 4/5) must stay with their question
- "Traiter 3 exercices sur 5" instruction must not be treated as a question

**Chunking strategy:** See Pattern M1, M2, M3 in Section 3.

---

### Français / Communication française

**Typical structure:**
```
HEADER
─────────────────────────────────────────────
I. Compréhension du texte
  [Reading passage — full width]
  Questions 1-3 (MCQ)
  Questions 4-6 (open-ended on passage)
─────────────────────────────────────────────
II. Grammaire
  Items (fill-in, transform, replace)
─────────────────────────────────────────────
III. Vocabulaire / Orthographe / Conjugaison
  Items (match synonyms, antonyms, complete)
─────────────────────────────────────────────
IV. Production écrite (writing prompt)
```

**Layout:** Layout D (passage full width, questions two columns).
Sometimes Layout B throughout.

**Special challenges:**
- Reading passage must never be split — it is always one chunk
- Questions referencing the passage need the passage title in their content
- Grammaire items look similar to Math fill-in but test different skills
- Section headers (Grammaire, Vocabulaire, Conjugaison) vary by year and board

**Chunking strategy:** See Pattern F1, F2, F3 in Section 3.

---

### SVT (Sciences de la Vie et de la Terre)

**Typical structure:**
```
HEADER
─────────────────────────────────────────────
Partie I — Restitution des connaissances
  QCM (4-6 questions)
  Questions vrai/faux or short answer
─────────────────────────────────────────────
Partie II — Application
  Exercice 1 (with data / diagram description)
    a) b) c)
  Exercice 2 (with data table or observation)
    a) b) c)
─────────────────────────────────────────────
Partie III — Synthèse / Rédaction
  One long open question
```

**Layout:** Layout A or B. Often asymmetric (Layout C) when diagrams present.

**Special challenges:**
- Diagrams are described in text ("Le schéma ci-dessous représente...") —
  these descriptions must stay with their question
- Data tables for genetics problems, cell diagrams, etc. need to stay with
  their exercise context
- "Vrai ou Faux" sections need one chunk per item

**Chunking strategy:** See Pattern S1, S2 in Section 3.

---

### Physique / Chimie

**Typical structure:**
```
HEADER
─────────────────────────────────────────────
Exercice 1 — Mécanique / Électricité / Optique
  Données : (list of given values)
  Questions a) b) c) d)
─────────────────────────────────────────────
Exercice 2 — Chimie / Réactions
  Données : (list of given values)
  Questions a) b) c)
─────────────────────────────────────────────
Exercice 3 — ...
```

**Layout:** Usually Layout A (single column). Sometimes Layout B.

**Special challenges:**
- "Données" (given values) block must stay attached to its exercise —
  sub-questions reference these values and are not meaningful without them
- Physical units (N, m/s², Ω, kJ/mol) often get garbled in extraction
- Numbered formulas referenced as "(1)", "(2)" in questions need to stay
  with their exercise context

**Chunking strategy:** See Pattern P1 in Section 3.

---

### Histoire / Géographie

**Typical structure:**
```
HEADER
─────────────────────────────────────────────
PREMIÈRE PARTIE — Histoire
  Sujet 1 — Questions de cours
    1. 2. 3. 4. (short answer)
  Sujet 2 — Commentaire de document
    [Document / source text]
    Questions a) b) c)
─────────────────────────────────────────────
DEUXIÈME PARTIE — Géographie
  Sujet 1 — Questions de cours
  Sujet 2 — Analyse de carte / données
```

**Layout:** Usually Layout A. Sometimes Layout B.

**Special challenges:**
- Source documents / historical excerpts must be chunked as `passage`
  and referenced in the questions that use them
- Questions that are just "définir X" or "expliquer Y" look like fill-in
  but are open-ended — classify as `question_open` not `question_fillin`

**Chunking strategy:** See Pattern H1 in Section 3.

---

### Économie / Philosophie

**Typical structure (Économie):**
```
HEADER
─────────────────────────────────────────────
I. Questions de connaissances
  Short answer questions
─────────────────────────────────────────────
II. Analyse de document
  [Statistical table or graph description]
  Questions on document
─────────────────────────────────────────────
III. Dissertation / Question de synthèse
  One long essay prompt
```

**Typical structure (Philosophie):**
```
HEADER
─────────────────────────────────────────────
Sujet 1 — Dissertation
  [Essay question]
─────────────────────────────────────────────
Sujet 2 — Explication de texte
  [Philosophical text / passage]
  Questions
─────────────────────────────────────────────
Sujet 3 — Dissertation alternative
```

**Layout:** Layout A (single column) for both.

**Special challenges:**
- Essay prompts are single open questions — one chunk each
- Philosophical text must be chunked as `passage`
- "Choisir un sujet parmi" instructions must not be treated as a question

**Chunking strategy:** See Pattern E1 in Section 3.

---

## Section 3 — Structure Patterns and Chunking Strategies

Each pattern describes a specific combination of layout + subject structure
and gives the exact chunking rules to apply.

---

### Pattern M1 — Math Partie A (fill-in items)

**Identified by:** Section titled "PARTIE A", items numbered 1–10,
each asking to complete a formula or expression with "......"

**Chunking rule:**
- One chunk per numbered item → `chunk_type: question_fillin`
- Include the full item text including the incomplete expression
- Do not merge items even if they look similar
- Point value (usually 4 pts each) → store in `points` field

**Embedding note:**
`topic_hint` must name the mathematical concept, not the item number.
The fill-in format hides what the question is really about.

**Example chunk:**
```json
{
  "chunk_type": "question_fillin",
  "section": "Partie A",
  "question_number": "2",
  "content": "La dérivée première de la fonction f définie par f(x) = x²e^(3x+1) est f'(x) = ......",
  "has_formula": true,
  "topic_hint": "Calcul de la dérivée d'un produit fonction polynôme et exponentielle"
}
```

---

### Pattern M2 — Math Partie B (multi-part exercises)

**Identified by:** Section titled "PARTIE B", exercises numbered 1–5,
each with sub-questions a) b) c) d). Usually starts with "Soit..." or "On considère..."

**Chunking rule:**
- One chunk for the exercise context → `chunk_type: question_open`
  Content = the full setup ("Soit f la fonction définie par... a) b) c) d)")
- One chunk per sub-question → `chunk_type: sub_question`
  Content = one-line context reminder + the sub-question only
- If the exercise contains a data table, include it in the `question_open` chunk

**Critical rule for sub_question autonomy:**
Every `sub_question` chunk must include enough context to be understood
without reading the parent. Minimum: the function/sequence/object being studied.

**Example chunk (sub_question):**
```json
{
  "chunk_type": "sub_question",
  "section": "Partie B",
  "question_number": "1",
  "sub_question": "b",
  "content": "Exercice 1 — f(x) = ln((3-x)/(x+2)). b) Étudier les limites de f aux bornes des intervalles du domaine.",
  "has_formula": true,
  "topic_hint": "Calcul des limites aux bornes du domaine d'une fonction logarithmique"
}
```

---

### Pattern M3 — Math statistics table

**Identified by:** A table with rows x and y (or xi and fi),
usually introduced by "On considère la série statistique suivante"
or as part of an exercise on regression or correlation.

**Chunking rule:**
- If the table is inside an exercise: include it in the `question_open` chunk
  and in each `sub_question` chunk that uses it (repeat the table text)
- If the table is standalone (Pattern A fill-in item 10): include it in
  that `question_fillin` chunk

**Why repeat the table:** Sub-questions about the same table are retrieved
independently. Each must carry the data it needs to be answerable.

---

### Pattern F1 — Français reading passage

**Identified by:** A block of continuous prose text, usually 3–6 paragraphs,
with a title and author attribution at the bottom (e.g. "Revu Dauphin, Ed Averbode").
Precedes the comprehension questions.

**Chunking rule:**
- The entire passage = one chunk → `chunk_type: passage`
- Never split the passage. Even if it spans the full page width, it is one unit.
- Store passage title in the `content` field as the first line

**Embedding note:**
`topic_hint` must summarize the passage theme AND the key ideas discussed,
not just the title. Students search by theme, not by title.

---

### Pattern F2 — Français comprehension questions (MCQ)

**Identified by:** Numbered questions with options a) b) c) d),
immediately following the reading passage. Often under "Compréhension du texte".

**Chunking rule:**
- One chunk per question → `chunk_type: question_mcq`
- Include the full question + all options in `content`
- Add a reference to the passage title in `content`:
  "D'après le texte « L'énergie éolienne »..."

**Why reference the passage:** A student searching for comprehension questions
on that passage must find these chunks even when searching by passage topic.

---

### Pattern F3 — Français grammar / vocabulary / orthography items

**Identified by:** Numbered items under sections titled "Grammaire",
"Vocabulaire", "Orthographe", "Conjugaison", "Reliez", "Mettez au..."

**Chunking rule:**
- One chunk per numbered item → `chunk_type: question_fillin` or `question_open`
  depending on whether the answer is short/structured or open-ended
- Use `question_fillin` for: complete the blank, transform the sentence,
  match the synonym, conjugate the verb
- Use `question_open` for: write a paragraph, comment on a quote, justify

**Section header rule:**
Each section title (Grammaire, Vocabulaire, etc.) gets its own
`section_header` chunk. This allows filtering by grammar vs vocabulary
questions during retrieval.

---

### Pattern S1 — SVT with data or diagram description

**Identified by:** An exercise that starts with a description of
what a diagram or experiment shows ("Le document ci-dessous représente...",
"L'expérience suivante a été réalisée..."), followed by questions.

**Chunking rule:**
- The description block + questions = one `question_open` chunk
- Each sub-question = one `sub_question` chunk with the description
  summarized in one line for context
- Never separate the description from the questions that use it

---

### Pattern S2 — SVT true/false or short knowledge questions

**Identified by:** Items that ask to justify true or false, or short
"expliquez pourquoi" questions in Partie I.

**Chunking rule:**
- One chunk per item → `chunk_type: question_open`
  (these are not fill-in — they require a written justification)
- Do not merge multiple "vrai/faux" items into one chunk

---

### Pattern P1 — Physique/Chimie exercise with "Données"

**Identified by:** An exercise block that starts with a "Données:" section
listing physical constants, given values (mass, speed, voltage, etc.),
followed by numbered questions.

**Chunking rule:**
- The "Données" block is NOT a standalone chunk
- Include the full "Données" block inside the `question_open` chunk
  AND inside every `sub_question` chunk of that exercise
- This is the only case where content is intentionally duplicated —
  physical constants are meaningless without the question and vice versa

**Why duplicate:** A student asking "comment calculer la vitesse dans
l'exercice 2" needs both the formula question AND the given values
to get a useful answer from the agent.

---

### Pattern H1 — Histoire/Géo source document

**Identified by:** A block of text presented as a historical source,
official document, map description, or statistical excerpt,
usually preceded by "Document :" or "Source :".

**Chunking rule:**
- The source document = one chunk → `chunk_type: passage`
- Questions about the document = separate chunks referencing the source title
- Same rule as Pattern F1 (reading passage) — never split the source

---

### Pattern E1 — Économie/Philosophie essay prompt

**Identified by:** A single sentence or short paragraph that is the
question itself, e.g. "Analysez les causes du chômage en Haïti"
or "Expliquez la notion de contrat social selon Rousseau".

**Chunking rule:**
- One chunk per essay prompt → `chunk_type: question_open`
- "Choisissez un sujet parmi les suivants" = `instructions` chunk, not a question
- Do not split the prompt from any clarification that follows it

---

## Section 4 — Fallback Strategy for Unknown Structures

When a PDF contains a structure not covered by any pattern above:

### Step 1 — Determine the unit of meaning

Ask: "What is the smallest piece of content a student could usefully
retrieve on its own?" That is your chunk boundary.
- If it is a question with options → one chunk
- If it is a question with sub-parts → one parent + N sub-chunks
- If it is a reference text → one passage chunk
- If it is a data block → one chunk or attach to its question

### Step 2 — Apply universal rules

Regardless of structure type, always:
- Ensure every chunk has enough context to be understood alone
- Propagate year, subject, serie, section to every chunk
- Never produce an empty `content` field
- Use `chunk_type: "other"` and describe in `topic_hint`

### Step 3 — Log it

Record the unknown structure pattern with:
- The subject and exam board it appeared in
- Which year/session
- A description of what it looks like
- How you chunked it

This log feeds back into extending this document and the chunker prompt.

---

## Section 5 — Cross-Cutting Extraction Risks

These risks apply regardless of subject or layout and must be
handled at the extraction stage before the LLM sees the text.

---

### Risk 1 — Formula garbling

**What happens:** PyMuPDF converts math formulas into broken text.
Integrals lose their bounds. Fractions get flattened. Greek letters
become question marks or random characters.

**Example:**
PDF renders: `∫₀² (2x+1)dx = 6`
Extracted as: `(2 1) 6 2 0   I x dx`

**Strategy:** Mark `has_formula: true`. Reproduce as-is.
Do not attempt to reconstruct the formula — the LLM may hallucinate.
The broken text still carries enough signal for embedding (keywords like
"intégrale", "dérivée", variable names survive).

---

### Risk 2 — Two-column reading order corruption

**What happens:** Default PyMuPDF reads left to right across the full
page width. In a two-column layout this interleaves content from both
columns mid-sentence.

**Example:** Left column has "On considère la suite Un définie par"
and right column has "Exercice 3 — Nombres complexes". Default
extraction produces "On considère la suite Un définie parExercice 3".

**Strategy:** Always detect column layout per page. Split at midpoint
(or detected boundary for asymmetric layouts). Read left column fully,
then right column fully.

---

### Risk 3 — Header metadata on page 1 only

**What happens:** Subject, year, serie, exam board appear only in the
page 1 header. Pages 2+ have no header.

**Strategy:** The chunker maintains a running context dict across pages.
Any metadata extracted from page 1 is propagated to all subsequent chunks.
Never leave `year`, `subject`, or `serie` null on a content chunk.

---

### Risk 4 — Section titles merged with first question

**What happens:** "PARTIE B — Traiter 3 exercices sur 5" appears on
the same line or very close to "Exercice 1 — On considère la fonction..."
and gets merged by the extractor.

**Strategy:** The LLM must produce separate chunks for the section header
and the first question even if they appear close together in the raw text.
The chunking prompt enforces this explicitly.

---

### Risk 5 — Instruction lines that look like questions

**What happens:** Lines like "Traiter 3 exercices sur 5 (60 pts)" or
"Entourer la lettre qui correspond à la bonne réponse" look like questions
but are instructions.

**Strategy:** These get `chunk_type: instructions` or `chunk_type: section_header`.
The chunking prompt instructs the LLM to classify by function, not by position.

---

## Section 6 — Decision Tree (Quick Reference)

```
New PDF received
      │
      ├─ Detect layout per page
      │     ├─ All text in one column?          → Layout A — use default extraction
      │     ├─ Two equal columns?               → Layout B — split at midpoint
      │     ├─ Two unequal columns?             → Layout C — detect boundary from blocks
      │     └─ Mixed within page?               → Layout D/E — split by section
      │
      ├─ Identify subject from header
      │     ├─ Mathématiques                    → Expect Partie A (M1) + Partie B (M2/M3)
      │     ├─ Français                         → Expect passage (F1) + MCQ (F2) + items (F3)
      │     ├─ SVT                              → Expect MCQ + exercises with data (S1/S2)
      │     ├─ Physique/Chimie                  → Expect exercises with Données (P1)
      │     ├─ Histoire/Géographie              → Expect source documents (H1) + questions
      │     └─ Économie/Philosophie             → Expect essay prompts (E1)
      │
      └─ Chunk using the matching pattern
            └─ Unknown structure?
                  └─ Apply fallback (Section 4) + log it
```

---

## Section 7 — Chunk Type Quick Reference

| chunk_type | When to use |
|---|---|
| `exam_header` | Ministry, subject, year, serie, exam board |
| `instructions` | Rules, duration, "choisir X parmi Y", barème global |
| `section_header` | "PARTIE A", "Grammaire", "Exercice 1" titles |
| `passage` | Reading text, historical source, philosophical text |
| `question_mcq` | Question + options a/b/c/d, always together |
| `question_fillin` | Fill-in-the-blank, transform, conjugate, match |
| `question_open` | Exercise context block, essay prompt, open question |
| `sub_question` | Sub-part (a, b, c...) with parent context reminder |
| `table` | Standalone data table not attached to a single question |
| `other` | Anything not covered above — log and describe in topic_hint |