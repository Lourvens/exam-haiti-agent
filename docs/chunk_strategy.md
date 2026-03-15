# ExamHaiti — PDF Structure Analysis & Chunking Strategy Guide

> **Version 2** — Rewritten from direct analysis of 5 real MENFP exam PDFs:
> Math LLA 2025 (Distance), Math SMP 2025 (Graphe), Hist-Geo 2022 (Dessalines),
> SVT 2021 (Gamète), Chimie 2023 (Covalente)
>
> Every rule, example, and risk in this document is sourced from actual exam content.

---

## How to Use This Document

1. Open the PDF → identify its **layout type** (Section 1)
2. Read the **subject profile** (Section 2) — know what to expect before chunking
3. Apply the matching **pattern** (Section 3) — concrete rules per structure
4. Use the **LLM prompt guidance** (Section 4) — how to write instructions for the chunker
5. Consult **extraction risks** (Section 5) — what will silently break if ignored
6. Unknown structure → **Section 6** fallback

---

## Section 1 — Page Layout Types

Detect layout **per page**, not per document. The same exam can switch layouts
between pages. Always run layout detection before sending text to the LLM.

---

### Layout A — Single Column

```
┌─────────────────────────────┐
│  HEADER        (full width) │
│  Instructions  (full width) │
│                             │
│  SECTION TITLE              │
│  Question 1                 │
│  Question 2                 │
│  Question 3                 │
│                             │
│  NEXT SECTION               │
│  Question 1                 │
└─────────────────────────────┘
```

**Confirmed in:** SVT 2021 (Gamète) — full document, single column.

**Extraction:** PyMuPDF `page.get_text("text")` reads top-to-bottom correctly.
No splitting needed.

**Watch for:** Discipline boundary changes (BIOLOGIE → GEOLOGIE) within a single
column — these look like ordinary section headers but reset the subject context.

**Risk:** Low for extraction. Medium for chunking if subject context not tracked.

---

### Layout B — Two Columns, Symmetric Split

```
┌───────────────────────────────────────┐
│   HEADER               (full width)   │
│   N.B. / Instructions  (full width)   │
├───────────────────────┬───────────────┤
│ LEFT COLUMN           │ RIGHT COLUMN  │
│                       │               │
│ PARTIE A box header   │ PARTIE B box  │
│ Item 1 .............. │ Exercice 1    │
│ Item 2 .............. │   a) .......  │
│ Item 3 .............. │   b) .......  │
│ ...                   │   c) .......  │
│ Item 10 ............. │ Exercice 2    │
│                       │   a) .......  │
└───────────────────────┴───────────────┘
```

**Confirmed in:** Math LLA 2025 (Distance), Math SMP 2025 (Graphe),
Chimie 2023 (Covalente), Hist-Geo 2022 (Dessalines).
**This is the dominant layout — 4 of 5 exams confirmed.**

**Extraction:** MUST split at page midpoint. Read full left column completely,
then read full right column. PyMuPDF default reads left-to-right across both
columns, producing interleaved garbage like:
"Item 2 — La dérivée de f...1. Soit la fonction numérique f définie par..."

**Critical detail confirmed from Math exams:** The header block (MENFP logo,
title, série, year) and the N.B. paragraph span full width above the split.
The two-column section starts below them. Detect the y-coordinate where the
two-column layout begins — do not split the header block.

**In Chimie 2023:** PARTIE A appears as a shaded full-width box before the
two-column body starts. Same principle — extract the box as a unit, then handle
columns below it.

**Risk:** High. Most common source of chunking failures in this codebase.

---

### Layout D — Single Column, Multiple Disciplines

**Confirmed in:** SVT 2021 (Gamète) — appears as Layout A visually but contains
two completely separate disciplines (Biologie + Géologie) treated as sub-subjects.

**Extraction:** Default extraction works. The challenge is purely semantic:
detecting the BIOLOGIE / GEOLOGIE boundary and updating the running subject context.

**Trigger words that reset subject context:**
- "BIOLOGIE" → subject becomes "SVT - Biologie"
- "GEOLOGIE" → subject becomes "SVT - Géologie"

**Risk:** Medium. Easy to miss the subject switch if scanning for question patterns only.

---

## Section 2 — Subject Profiles

Read the subject profile before chunking any document from that subject.
It tells you what structure to expect, what chunk types appear, and what traps to avoid.

---

### Mathématiques

**Series confirmed:** LLA (Distance 2025), SMP (Graphe 2025)

**Full structure map:**
```
HEADER
  MENFP + logo + "BACCALAURÉAT RÉGULIER – JUILLET 2025" + "SÉRIE : LLA/SMP"
  Exam center name (Distance / Graphe) — top right, large font
  → chunk_type: exam_header

N.B. paragraph (full width):
  "Le sujet est composé de deux parties A et B. Dans chaque exercice,
   le candidat est invité éventuellement à faire figurer sur la copie..."
  → chunk_type: instructions

Instructions line (full width):
  "Consignes : 1. L'usage de la calculatrice... 2. Le téléphone... 3. Le silence..."
  "Durée de l'épreuve : 3 heures"
  → chunk_type: instructions (merge with N.B. or keep separate — either fine)

──── TWO COLUMNS START ────────────────────────────────────────────────

LEFT COLUMN:                          RIGHT COLUMN:
┌──────────────────────┐              ┌────────────────────────────┐
│ PARTIE A box header  │              │ PARTIE B box header        │
│ "Recopier et         │              │ "Traiter trois (3) des     │
│ compléter... (40pts)"│              │ quatre (4) exercices(60pts)"│
│                      │              │  → section_header           │
│ Items 1–10           │              │                             │
│ (4 pts each)         │              │ 1. [Exercice 1]             │
│  → question_fillin   │              │    a) b) c) d)              │
│                      │              │  → question_open            │
│                      │              │  → sub_question ×4          │
│                      │              │                             │
│                      │              │ 2. [Exercice 2]             │
│                      │              │    a) b) c) d)              │
│                      │              │ ...                         │
└──────────────────────┘              └────────────────────────────┘
```

**Confirmed Partie A items (real content from both exams):**

| # | LLA 2025 (Distance) | SMP 2025 (Graphe) | Concept |
|---|---|---|---|
| 1 | Equation 2(ln x)²−ln x−6=0, S=? | Domain of f(x)=(3−ln x)/(2−eˣ) | Log equation / Domain |
| 2 | Derivative of ln((eˣ−1)/(eˣ+1)) | Primitive of e^(2x) vanishing at ln2 | Derivative / Primitive |
| 3 | Simplify 2e^(ln3)−4e^(ln5)+7ln e^5+3 | Geometric series U0=−9, q=2/5, lim Sn | Exponential simplification / Series |
| 4 | Geometric series U0=−9, q=2/5, lim Sn | Reason of Un=2n+3 | Series limit / Arithmetic reason |
| 5 | Arithmetic Un, r=−0.5, U2=7, Un=? | Complex number z=√2·e^(iπ/2)+1 algebraic form | Arithmetic expression / Complex |
| 6 | Sequence (2n−6)/(n+1) bounded by? | Barycentre G of A(1,2), B(4,0), C(1,−1) coefficients 2,3,5 | Bounded sequence / Barycentre |
| 7 | E(X) for X∈{1,2,3,5} with given probs | var(3X) if σ(X)=5 | Expected value / Variance |
| 8 | P(B) given P(A)=0.6, P(A∩B)=0.35, A,B independent | P(A∩B) given P(A), P(B), P_A(B) | Independence / Conditional |
| 9 | var(x) from regression y=−3x+1, cov(x,y)=−27 | Missing b in stats table, G=(16;15) | Regression / Point moyen |
| 10 | Missing a,b in table, G=(7.8;122) | Correlation coefficient formula ρ(x,y)=? | Point moyen / Correlation formula |

**Confirmed Partie B exercises:**

| # | LLA 2025 (Distance) | SMP 2025 (Graphe) |
|---|---|---|
| 1 | f(x)=(x−1)/(x−2), study+graph | f(x)=(2x+1)e^(3x), study+primitive |
| 2 | Joseph savings (arithmetic, 200k gourdes) | Joseph savings (arithmetic, 200k gourdes) — **identical** |
| 3 | Vania tokens 1–6, discrete probability | Complex equation z³−2iz²+4(1+i)z+16i=0 |
| 4 | Chicken/egg regression (6 hens) | Balls urne (5 black, 2 green, 1 red), P(X) |
| 5 | *(LLA has only 4 exercises)* | Chicken/egg regression (6 hens) — **identical to LLA Ex.4** |

**Key observations:**
- Items 3 and 4 in LLA and Graphe (geometric series, identical) → same chunk with different metadata
- Joseph savings exercise and chicken/egg exercise appear verbatim in both series
- SMP has 1 extra exercise (complex numbers, degree 3 equation) that LLA does not

**Layout:** Layout B. Split at midpoint after full-width header+N.B.

**Formula garbling — confirmed raw extraction output from these exams:**
```
PDF: f(x) = ln((eˣ-1)/(eˣ+1))     → Extracted: "1 1 ( ) ln x x e e f x"
PDF: lim(n→+∞) Sn = .....          → Extracted: "lim  ..... n n S"
PDF: z = √2·e^(iπ/2) + 1           → Extracted: "2 1 2  i z e"
PDF: A = 2e^(ln3)−4e^(ln5)+7ln e^5 → Extracted: "2 4 7ln 3. ln3 ln5 5 A e e e"
PDF: Un = (2n−6)/(n+1)             → Extracted: "1 2 6 n n Un"
PDF: ρ(x,y) formula                → Extracted: "(x, y)"
```

All of Partie A is affected. Mark every item `has_formula: true`. Reproduce as-is.

---

### Histoire-Géographie

**Series confirmed:** SES/LLA (Dessalines 2022)

**Full structure map:**
```
HEADER
  "HISTOIRE-GÉOGRAPHIE | SERIES : SES/LLA | FEVRIER 2022"
  "Dessalines" — exam center, large stylized font
  → chunk_type: exam_header

Instructions (3 numbered rules + duration)
  → chunk_type: instructions

──── TWO COLUMNS ────────────────────────────────────────────────────

LEFT COLUMN:                          RIGHT COLUMN:
A-PREMIÈRE PARTIE : Histoire          (continues)
Nationale (60%)
  → section_header

"Dissertation historique :
 traiter l'un des trois sujets"
  → instructions

Texte 1 (US occupation/Convention)   [Texte 3 continues into right column]
  → passage                          Sujet 3 → question_open
Sujet 1 → question_open
                                     DEUXIEME PARTIE (40%)
Texte 2 (army/Lescot)                  → section_header
  → passage
Sujet 2 → question_open              Texte 1 (Nagasaki doctor) → passage
                                     Texte 2 (EU regional policy) → passage
Texte 3 (Estimé/fiscal policy)
  → passage                          Questions 1–4 (with pts)
                                        → question_open ×4
```

**Confirmed source texts and essay questions:**

| Block | Content | Chunk type | topic_hint |
|---|---|---|---|
| Texte 1 | Convention 1915: US occupation, control of finances/customs/army; Constitution 1918 by referendum. Source: Geneviève D. Auguste | passage | "Document historique sur la Convention américano-haïtienne de 1915 et la Constitution de 1918 sous l'occupation américaine" |
| Sujet 1 | "Dégagez le rôle joué par la Convention de 1915 et la Constitution de 1918 dans l'occupation américaine d'Haïti." | question_open | "Dissertation : rôle de la Convention de 1915 et de la Constitution de 1918 dans l'établissement de l'occupation américaine d'Haïti" |
| Texte 2 | Renversement Lescot jan. 1946, role of army, reaction of political parties. Source: Dr Raymond Bernardin | passage | "Document historique sur le rôle de l'armée haïtienne dans le renversement du président Lescot en janvier 1946" |
| Sujet 2 | "Analysez le rôle de l'armée dans la vie politique haïtienne de 1934 à 1957." | question_open | "Dissertation : analyse du rôle de l'armée haïtienne dans la vie politique de 1934 à 1957" |
| Texte 3 | Estimé: impôt progressif 1947, bicentenaire, opposition bourgeoise. Source: Anthony Georges Pierre | passage | "Document historique sur les réalisations et les limites du gouvernement de Dumarsais Estimé (1946-1950)" |
| Sujet 3 | "Présentez les faits qui ont permis à Dumarsais Estimé de gagner l'estime du peuple..." | question_open | "Dissertation : faits marquants du gouvernement Estimé lui ayant valu le soutien populaire malgré son élection indifférente" |
| Texte 1 (2e Partie) | Nagasaki doctor testimony — ruins, burned bodies, city destroyed. Source: Le Monde, 7 août 1970 | passage | "Témoignage d'un médecin de Nagasaki sur les effets immédiats du bombardement atomique d'août 1945" |
| Texte 2 (2e Partie) | EU regional solidarity policy, 2007–2013 structural funds, sustainable development. Source: europa.eu.int | passage | "Extrait sur la politique régionale de l'Union européenne : solidarité financière, fonds structurels, développement durable" |

**Confirmed questions with point values:**

| Q | Text reference | Points | topic_hint |
|---|---|---|---|
| Q1 | Texte 1 | 6 pts | "Identification de l'événement historique évoqué dans le témoignage de Nagasaki et explication d'une cause" |
| Q2 | Texte 1 | 10 pts | "Analyse du caractère non-ordinaire de l'arme atomique à partir du témoignage médical de Nagasaki" |
| Q3 | Texte 2 | 12 pts | "Explication de la contribution de la solidarité financière régionale à la cohésion de l'Union européenne" |
| Q4 | standalone | 12 pts | "Définition du concept de développement durable" |

**Critical rule:** Q4 has no text reference. Do not add one. Its topic_hint must carry the concept clearly because there is no passage to link it to.

---

### SVT (Sciences de la Vie et de la Terre)

**Series confirmed:** SES/SMP (Gamète 2021)

**Full structure map:**
```
HEADER
  "SÉRIES : (SES-SMP) | BAC PERMANENT - MARS 2021 | SVT"
  "Gamète" — exam center
  → chunk_type: exam_header (subject: "SVT")

Instructions (3 rules + duration 2 heures)
  → chunk_type: instructions

══════════════════════════════════════════════════
BIOLOGIE                                          ← triggers subject: "SVT - Biologie"
  → section_header
══════════════════════════════════════════════════

A - PREMIERE PARTIE
  → section_header

Thème I : Les glandes hormonales (20 pts)
  → section_header
  Q1: "Nommer trois glandes hormonales ; Situer les dans l'organisme."
      → question_open (two tasks, keep together — naming + locating)
  Q2: "Citer les hormones libérées par le pancréas. Expliquer pourquoi elles
       sont dites antagonistes, puis nommer les cellules qui les secrètent."
      → question_open (three tasks on one topic — keep together)
  Q3: "Quelle est l'origine de la testostérone et de l'œstrogène ?"
      → question_open
  Q4: "Qu'est-ce qu'une neurohormone ?"
      → question_open

Thème II : Mutation (15 pts)
  → section_header

  Context block:
  "Le biologiste américain Thomas Morgan (20e siècle) a étudié les mutations
   sur la drosophile. Les scientifiques ont identifié et étudié ainsi des
   mutations chez les humains."
  → This is NOT a question. Classify as section_header or include in the
    section_header chunk for Thème II. Do not create a question_open for it.

  Q1: "Différencier mutation somatique de mutation germinale."
      → question_open
  Q2: "Nommer une pathologie courante en Amérique et en Afrique due à une
       mutation ? Indiquer son effet sur :
       a) la protéine concernée  b) la forme des cellules qui en dérivent."
      → PARENT: question_open ("Nommer la pathologie due à mutation...")
      → 2a: sub_question ("SVT Biologie — Mutation. Q2: pathologie = drépanocytose.
             a) Effet sur la protéine concernée.")
      → 2b: sub_question ("SVT Biologie — Mutation. Q2: pathologie = drépanocytose.
             b) Effet sur la forme des cellules qui en dérivent.")
  Q3: "Distinguer délétion d'inversion."
      → question_open

B- Généralités (15 pts)
  → section_header
  Q1: "Différencier gamète de gonie."
      → question_open
  Q2: "Définir : - Locus – Crossing over."
      → question_open (two definitions, one chunk — they are listed together)
  Q3: "Quelle vitamine retrouve-t-on dans :
       a) Le foie de poisson.  b) Les cerises et les oranges."
      → PARENT: question_open
      → 3a: sub_question ("SVT Biologie — Généralités. Q3: vitamines dans aliments.
             a) Vitamine présente dans le foie de poisson.")
      → 3b: sub_question ("SVT Biologie — Généralités. Q3: vitamines dans aliments.
             b) Vitamine présente dans les cerises et oranges.")

══════════════════════════════════════════════════
GEOLOGIE                                          ← triggers subject: "SVT - Géologie"
  → section_header
══════════════════════════════════════════════════

A - PREMIERE PARTIE
  → section_header

Thème I : La Globe terrestre (20 pts)
  → section_header

  "Répondre aux questions suivantes."
  → Do NOT classify as a question. It is a task instruction.
    Include in the Thème I section_header chunk.

  Q1: "Définir : - Microfossiles, Fossile de faciès, Fossile stratigraphique."
      → question_open (three definitions, one chunk)
  Q2: "Enumérer les principes fondamentaux de la stratigraphie."
      → question_open
  Q3: "Définir la notion de Crise Biologique."
      → question_open
  Q4: "L'extinction de dinosaures a eu lieu, il y a……………………… et expliquer le phénomène."
      → question_fillin (fill in date + open explanation — keep as one chunk)
      → has_formula: false, content includes the blank

Thème II : Les ères géologiques (15 pts)
  → section_header
  Q1: "Déterminer l'ère qui caractérise la prolifération des forêts."
      → question_open
  Q2: "Le quaternaire a vu l'apparition de………………………………… sur la Terre."
      → question_fillin
  Q3: "Le permien est caractérisé par…………………………………………………"
      → question_fillin

B- DEUXIEME PARTIE — Généralités (15 pts)
  → section_header
  Q1: "Expliquer le modèle géothermique de la Terre."
      → question_open
  Q2: "Où et à quelle période et dans quel climat évoluait l'homme de Neandertal ?"
      → question_open (three sub-questions in one — keep together)
  Q3: "Enumérer les causes et les conséquences du changement climatique."
      → question_open
```

**Special rule for SVT multi-task questions:**
Q2 in Thème I Biologie ("Citer les hormones... Expliquer... Nommer les cellules") contains
three tasks but they all relate to the same organ (pancreas). Keep as one `question_open`.
Only split into sub_question when the question explicitly uses a) b) lettering.

---

### Chimie

**Series confirmed:** SVT/SMP (Covalente 2023)

**Full structure map:**
```
HEADER
  "BACCALAURÉAT – JUILLET 2023 | SÉRIES : (SVT, SMP) | CHIMIE"
  "Covalente" — exam center
  "Durée de l'évaluation : SVT 3 heures  SMP : 2h30"  ← two durations in one line
  → chunk_type: exam_header
  Note: Store both durations. This exam has different time limits per série.

Instructions (3 rules including the "5 parties" note)
  → chunk_type: instructions

──── TWO COLUMNS ────────────────────────────────────────────────────

LEFT COLUMN                           RIGHT COLUMN

PARTIE A (full-width shaded box):
"Recopier et compléter judicieusement les phrases suivantes. (20 pts)"
  → section_header

  10 bullet items (fill-in)           PARTIE D – (15pts)  → section_header
    → question_fillin ×10             "Bien lire l'extrait..."
                                        Passage: "Les ressources planétaires"
PARTIE B (full-width box in col):       → passage
"Ecrire et équilibrer les équations   Questions 1–3
 chimiques suivantes. (20 pts)"          → question_open ×3
  → section_header
  5 bullet reactions                  PARTIE E – (30 pts)  → section_header
    → question_open ×5               "Résoudre : SVT : deux (2) des trois (3)
                                       problèmes. SMP : un (1) des trois (3)."
PARTIE C (box):                          → section_header (serie-specific)
"Traiter une (1) des deux (2)         Problème I (methane combustion)
 questions suivantes. (15 pts)"          → question_open
  → section_header                      a) b) c) d) → sub_question ×4
  Q1 (redox identification)
    → question_open                   Problème II (glucose fermentation)
    a) part → sub_question              → question_open
  Q2 (secondary alcohols)               a) b) c) → sub_question ×3
    → question_open
    a) b) parts → sub_question ×2    Problème III (benzene/chlorine)
                                        → question_open
                                        a) b) c) d) → sub_question ×4

                                      "On donne en g/mol : C:12; H:1; O:16; Cl:35,5"
                                         → NOT a chunk. Attach to every Partie E chunk.
```

**Confirmed Partie A items with topic_hints:**

| Bullet | Content | topic_hint |
|---|---|---|
| 1 | Hydrocarbures acycliques, 2 carbones trigonaux → ___; formule brute générale ___ | "Identification des alcènes : caractéristique du carbone trigonal et formule brute CnH2n" |
| 2 | 2,4-DNPH met en évidence le groupement ___ de formule brute ___ | "Réactif 2,4-DNPH comme indicateur du groupement carbonyle (aldéhyde ou cétone)" |
| 3 | Alcool dans boissons = ___; provient de fermentation d'un sucre ___ | "Identification de l'éthanol et du glucose comme substrat de la fermentation alcoolique" |
| 4 | Dispositif énergie chimique → électrique = ___; résulte d'un transfert ___ | "Définition d'une pile électrochimique et notion de transfert d'électrons" |
| 5 | HCl + acétylène → ___ de formule semi-développée ___ | "Réaction d'addition de HCl sur l'acétylène et produit chloroéthylène" |
| 6 | Un oxydant est capable de ___ un ou plusieurs ___ | "Définition d'un oxydant comme espèce capable de capter des électrons" |
| 7 | Isomères monofonctionnels de C3H6O ont formules semi-développées ___ et ___ | "Identification des deux isomères fonctionnels de C3H6O : propanone et propanal" |
| 8 | Hydrolyse d'ester carboxylique → ___ et ___ | "Produits de l'hydrolyse d'un ester carboxylique : acide carboxylique et alcool" |
| 9 | À 25°C, produit ionique de l'eau noté ___ égal à ___ | "Produit ionique de l'eau Ke à 25°C et sa valeur numérique" |
| 10 | Caractère insaturé du benzène dû à ___ électrons pi; réactions ___ | "Caractère insaturé du benzène : électrons pi et réactions de substitution aromatique" |

**Confirmed Partie B reactions with topic_hints:**

| Reaction | topic_hint |
|---|---|
| Neutralisation acide acétique / soude | "Équation de neutralisation : acide acétique + soude → acétate de sodium + eau" |
| Hydrolyse carbure de calcium | "Équation d'hydrolyse du carbure de calcium produisant l'acétylène" |
| Hydrogénation propanone | "Équation d'hydrogénation de la propanone en propan-2-ol" |
| Hydratation éthylène | "Équation d'hydratation de l'éthylène en éthanol" |
| Dimérisation éthanal | "Équation de dimérisation de l'éthanal (aldol condensation)" |

**Partie C — ionic equation garbling (confirmed from PDF):**
The two equations in Q1 contain ionic notation that PyMuPDF garbles severely.
Equation (a): `NH3(aq) + HCl(aq) → NH4+(aq) + Cl-(aq)` extracted as:
`( ) ( ) 3( ) ( ) 4aq aq NH aq HCl aq NH Cl`
Equation (b): `2Fe3+(aq) + 2I-(aq) → 2Fe2+(aq) + I2(aq)` similarly garbled.
Mark `has_formula: true`. The words "oxydo-réduction", "demi-équations",
"électroniques" survive and carry retrieval signal.

---

## Section 3 — Chunking Patterns (Rules + Examples)

---

### Pattern M1 — Math Partie A fill-in items

**Signal:** Section box "PARTIE A.- Recopier et compléter les phrases suivantes
(1 à 10). (40 pts / 4 pts par question)."

**Rules:**
- One `question_fillin` chunk per numbered item (1 through 10)
- `points: 4` on every item
- `has_formula: true` on every item (confirmed — all items contain formulas)
- Reproduce full text as-is including all garbled formula fragments
- Never merge two items into one chunk
- Never split one item's text at a formula fragment

**topic_hint — the most important field for these chunks:**
Formulas are unreadable after garbling. The topic_hint is what makes these
chunks retrievable. It must name the mathematical concept, not describe the format.

```
✅ "Résolution d'une équation du second degré en ln x par changement de variable"
✅ "Calcul de la dérivée d'une fonction composée de type ln((eˣ−1)/(eˣ+1))"
✅ "Simplification d'expressions exponentielles et logarithmiques : e^(ln a) = a"
✅ "Calcul de la limite de la somme d'une série géométrique de raison q=2/5"
✅ "Expression de Un en fonction de n pour une suite arithmétique de raison r=−0.5"
✅ "Encadrement d'une suite convergente définie par récurrence"
✅ "Calcul de l'espérance mathématique d'une variable aléatoire discrète"
✅ "Probabilité d'intersection de deux événements indépendants"
✅ "Calcul de var(x) à partir de la droite de régression et de la covariance"
✅ "Détermination des valeurs manquantes dans un tableau statistique à partir du point moyen"

❌ "Item 4 de la Partie A"
❌ "Question de mathématiques sur les suites"
❌ "Compléter la phrase sur la limite"
```

---

### Pattern M2 — Math Partie B exercises (parent chunks)

**Signal:** "PARTIE B.- Traiter trois (3) des quatre/cinq (4/5) exercices. (60 pts)"

**Rules for the section_header chunk:**
- Content: full text of the "Traiter N des M exercices" instruction
- topic_hint: null (it is structural, not content)

**Rules for question_open (exercise parent):**
- Content: full exercise setup + all sub-questions listed
- This chunk gives context. A student who retrieves it gets the full picture.
- topic_hint: name the mathematical domain and the specific object studied

```
LLA Exercice 1:
  topic_hint: "Étude complète d'une fonction rationnelle f(x)=(x−1)/(x−2) : domaine, limites, variations, courbe"

LLA Exercice 2:
  topic_hint: "Modélisation d'une suite arithmétique : capital en caisse d'épargne (Joseph, 200 000 gourdes, intérêts simples)"

LLA Exercice 3:
  topic_hint: "Probabilité discrète : tirage simultané de deux jetons parmi six, loi de X = différence en valeur absolue"

LLA Exercice 4:
  topic_hint: "Régression linéaire sur données biologiques : poids et production d'œufs de 6 pondeuses (droite G1G2)"

SMP Exercice 3:
  topic_hint: "Résolution dans ℂ d'une équation du troisième degré à coefficients complexes, géométrie du triangle ABC"

SMP Exercice 4:
  topic_hint: "Loi de probabilité d'une variable X = nombre de boules vertes dans un tirage de 3 boules d'une urne"
```

---

### Pattern M3 — Math sub_question (exercise sub-parts)

**Signal:** Sub-questions labeled a) b) c) d) within a Partie B exercise.

**Rules:**
- One `sub_question` chunk per lettered sub-part
- Content MUST include: exercise number + one-line context summary + the sub-question
- Never produce a sub_question chunk that could not be understood without the parent

**Confirmed content examples:**

```json
{
  "chunk_type": "sub_question",
  "subject": "Mathématiques",
  "serie": "LLA",
  "section": "Partie B",
  "question_number": "1",
  "sub_question": "b",
  "content": "Exercice 1 — Fonction f(x) = (x−1)/(x−2), courbe (C) dans repère orthonormal.\nb) Déterminer les limites de f aux bornes des intervalles du domaine.",
  "has_formula": true,
  "topic_hint": "Calcul des limites aux bornes du domaine d'une fonction rationnelle avec asymptotes"
}
```

```json
{
  "chunk_type": "sub_question",
  "subject": "Mathématiques",
  "serie": "LLA",
  "section": "Partie B",
  "question_number": "4",
  "sub_question": "b",
  "content": "Exercice 4 — Élevage de 6 pondeuses, tableau poids xi / œufs yi (2;150)(2.25;175)(2.5;200)(2.75;268)(2.9;275)(3;300).\nb) Déterminer les coordonnées de G1, point moyen des 3 premiers points de la série.",
  "has_formula": false,
  "has_table": true,
  "topic_hint": "Calcul des coordonnées du premier point moyen G1 pour la méthode des deux points en régression"
}
```

**Table repetition rule (confirmed for Partie B Exercice 4/5):**
The chicken/egg table must appear in the question_open chunk AND in every
sub_question chunk. Sub-questions b, c, d all require the data. Repeat it.

---

### Pattern H1 — Histoire Nationale (Texte + Sujet pairs)

**Signal:** "A-PREMIÈRE PARTIE : Histoire Nationale (60%)" + "Dissertation historique :
traiter l'un des trois sujets"

**Rules:**
- "Dissertation historique : traiter l'un des trois sujets" → `instructions`
- Each Texte → `passage` chunk
- Each Sujet → separate `question_open` chunk
- Sujet content must reference its Texte: "D'après le Texte N ([attribution]) :"

**Why never merge Texte and Sujet:**
A student searching "Convention de 1915 histoire" should retrieve the source text.
A student searching "dissertation occupation américaine sujet bac" should retrieve
the essay question. These are different retrieval intents.

**Confirmed examples:**
```json
{
  "chunk_type": "passage",
  "subject": "Histoire-Géographie",
  "section": "Première Partie",
  "content": "Texte 1 — Source : Geneviève D. Auguste, Histoire d'Haïti, Tome II, 1915-1986, pp. 22-35-36\n\nLa convention présentée au gouvernement par les Américains légalisait l'intervention et plaçait le pays sous la tutelle des États-Unis. Elle leur accordait le contrôle des finances, des douanes et de l'armée. [...] Le 12 juin 1918, cette nouvelle charte fut adoptée par référendum.",
  "topic_hint": "Document historique sur la Convention américano-haïtienne de 1915 : tutelle US sur finances, douanes, armée, et adoption de la Constitution de 1918 par référendum"
}
```

```json
{
  "chunk_type": "question_open",
  "subject": "Histoire-Géographie",
  "section": "Première Partie",
  "question_number": "1",
  "content": "D'après le Texte 1 (Geneviève D. Auguste, Histoire d'Haïti, 1915-1986) :\nDégagez le rôle joué par la Convention de 1915 et la Constitution de 1918 dans l'occupation américaine d'Haïti.",
  "topic_hint": "Dissertation historique : rôle de la Convention de 1915 et de la Constitution de 1918 dans la consolidation de l'occupation américaine d'Haïti"
}
```

---

### Pattern H2 — Deuxième Partie (questions with inline point values)

**Signal:** "DEUXIEME PARTIE (40%) — Histoire Universelle et Géographie (Obligatoires)"
Point values embedded inline: "(6 pts)", "(10 pts)", "(12 pts)".

**Rules:**
- Extract point value from parenthetical → `points` field
- Remove point value from `content` text
- Questions referencing "le texte 1" or "le texte 2" → include reference in content
- Q4 "Qu'entendez-vous par 'développement durable'?" → no text reference, standalone

```json
{
  "chunk_type": "question_open",
  "subject": "Histoire-Géographie",
  "section": "Deuxième Partie",
  "question_number": "1",
  "points": 6,
  "content": "D'après le Texte 1 (témoignage d'un médecin de Nagasaki, Le Monde, 7 août 1970) :\n1- À quel événement le texte 1 fait-il allusion ? Indiquez-en une (1) cause.",
  "topic_hint": "Identification du bombardement atomique de Nagasaki (août 1945) et d'une cause de cet événement"
}
```

---

### Pattern S1 — SVT Biologie questions

**Rules:**
- subject always "SVT - Biologie" for all chunks under BIOLOGIE section
- Multi-task questions (several tasks, no lettering) → one `question_open`
- Explicitly lettered sub-parts a) b) → parent `question_open` + `sub_question` per letter
- Context blocks (Morgan intro) → include in Thème section_header, not a separate question

**Confirmed sub_question example:**
```json
{
  "chunk_type": "sub_question",
  "subject": "SVT - Biologie",
  "section": "Thème II : Mutation",
  "question_number": "2",
  "sub_question": "a",
  "content": "SVT Biologie — Thème Mutation. Question 2 : pathologie due à une mutation courante en Amérique et en Afrique.\na) Indiquer l'effet de cette mutation sur la protéine concernée.",
  "topic_hint": "Effet moléculaire de la drépanocytose sur l'hémoglobine : substitution d'acide aminé dans la chaîne bêta"
}
```

---

### Pattern S2 — SVT Géologie fill-in questions

**Signal:** Questions ending with "…………………………………" (long dashes or dots to fill in).

**Rules:**
- Classify as `question_fillin` even if the item also asks to explain
- Keep the explanation part in the same chunk — do not split at the blank
- Example: "L'extinction de dinosaures a eu lieu, il y a ……… et expliquer le phénomène."
  → one `question_fillin` chunk (fill the date AND write explanation)

```json
{
  "chunk_type": "question_fillin",
  "subject": "SVT - Géologie",
  "section": "Thème I : La Globe terrestre",
  "question_number": "4",
  "content": "L'extinction de dinosaures a eu lieu, il y a ……………………………… et expliquer le phénomène.",
  "topic_hint": "Datation de l'extinction des dinosaures à la fin du Crétacé (−66 Ma) et explication des causes (impact météoritique, volcanisme)"
}
```

---

### Pattern C1 — Chimie Partie A (bullet fill-in)

**Signal:** Shaded/framed box with bullet list, each bullet = sentence with blanks (___).

**Rules:**
- One `question_fillin` chunk per bullet
- Keep all blanks within one bullet in the same chunk
- Never split a bullet at its first blank

**Specific formatting:** Chimie 2023 uses underlines (___) not dots (……).
Both are treated identically as fill-in markers.

---

### Pattern C2 — Chimie Partie B (write and balance reactions)

**Signal:** Bullet list of reaction names, no blanks, no question marks.

**Rules:**
- One `question_open` per bullet
- chunk_type is `question_open` not `question_fillin` — the task is to produce content,
  not fill a blank in a given sentence

---

### Pattern C5 — Chimie Partie E (calculation problems with shared data)

**Rules for "On donne en g/mol":**
This line always appears at the bottom of Partie E. It is not a standalone chunk.
It must be injected into every `question_open` and `sub_question` in Partie E.

**Confirmed format:**
```
"On donne en g/mol : C :12 ; H :1 ; O :16 ; Cl :35,5."
```

Include this line at the end of every Partie E content field:
```json
{
  "chunk_type": "sub_question",
  "subject": "Chimie",
  "section": "Partie E — Problème III",
  "question_number": "III",
  "sub_question": "d",
  "content": "Problème III — Destruction de 0,25 mol de benzène dans 0,8 mol de dichlore.\nd) Quelle masse de carbone se forme ?\nDonnées : C:12 g/mol ; H:1 g/mol ; O:16 g/mol ; Cl:35,5 g/mol.",
  "has_formula": true,
  "topic_hint": "Calcul de la masse de carbone formée lors de la chloration du benzène à partir du bilan d'avancement"
}
```

---

## Section 4 — LLM Prompt Guidance

This section tells you how to write the chunker system prompt effectively,
based on what was learned from processing these 5 exams.

---

### 4.1 — What to put in the system prompt vs. the user message

**System prompt:** General chunking rules, chunk_type definitions, output schema,
universal principles (autonomy, metadata propagation, no empty content),
topic_hint writing rules. This never changes between exams.

**User message:** The raw page text for the current page + running context
(what has been extracted so far: subject, year, serie, section, last question number).

**Running context format (inject at top of user message):**
```
CONTEXTE CONNU:
  subject: "Mathématiques"
  year: "2025"
  serie: "SMP"
  exam_center: "Graphe"
  current_section: "Partie B"
  last_question_number: "3"
  sub_questions_seen: ["a", "b", "c"]

TEXTE DE LA PAGE À DÉCOUPER:
[raw page text here]
```

This prevents the LLM from losing metadata when processing pages 2+ that have no header.

---

### 4.2 — How to write topic_hint instructions in the prompt

The topic_hint is the single most important field for retrieval quality.
The prompt must be explicit about how to write it.

**Include this rule block in your system prompt:**
```
RÈGLE TOPIC_HINT:
Le topic_hint est le champ le plus important pour la recherche.
Il doit décrire CE QUE LA QUESTION TESTE, pas où elle se trouve dans le document.

Format attendu : "[type de tâche] + [concept mathématique/scientifique/historique précis]"

Exemples validés :
  ✅ "Calcul de la limite de la somme d'une série géométrique de raison q=2/5"
  ✅ "Dissertation : rôle de la Convention de 1915 dans l'occupation américaine d'Haïti"
  ✅ "Identification des alcènes par leur carbone trigonal et formule brute CnH2n"
  ✅ "Effet moléculaire de la drépanocytose sur la structure de l'hémoglobine"
  ✅ "Témoignage de Nagasaki : description des effets immédiats du bombardement atomique"
  ❌ "Item 4 Partie A"
  ❌ "Question de mathématiques"
  ❌ "Exercice sur les suites"
  ❌ "Question de biologie sur les hormones"

Pour les formules garblées (has_formula: true) : le topic_hint est encore
plus critique car le contenu du chunk est illisible. Il doit permettre
à lui seul de retrouver le chunk depuis une requête en langage naturel.
```

---

### 4.3 — How to instruct the LLM to handle formula garbling

```
RÈGLE FORMULES:
Les formules mathématiques et chimiques sont souvent corrompues par l'extraction PDF.
Exemple : f(x) = ln((eˣ-1)/(eˣ+1)) peut devenir "1 1 ( ) ln x x e e f x".

JAMAIS tenter de reconstruire la formule. Reproduire le texte tel quel.
Marquer has_formula: true sur tout chunk contenant une formule, même garblée.
Le topic_hint doit exprimer la formule correctement en langage naturel.

Exemple :
  content: "2) La dérivée première f' de la fonction numérique f définie par 1 1 ( ) ln x x e e f x est f'(x) = ......."
  has_formula: true
  topic_hint: "Calcul de la dérivée d'une fonction composée logarithme-exponentielle de type ln((eˣ−1)/(eˣ+1))"
```

---

### 4.4 — How to instruct the LLM to handle the SVT discipline boundary

```
RÈGLE DISCIPLINES SVT:
Quand le sujet est SVT, le PDF contient deux disciplines distinctes.
Quand tu vois le titre "BIOLOGIE" → mettre subject: "SVT - Biologie" pour tous les chunks suivants.
Quand tu vois le titre "GEOLOGIE" → mettre subject: "SVT - Géologie" pour tous les chunks suivants.
Ne jamais mettre subject: "SVT" seul sur un chunk de contenu.
```

---

### 4.5 — How to instruct the LLM on autonomy

```
RÈGLE AUTONOMIE:
Chaque chunk doit être compréhensible seul, sans lire les chunks précédents.

Pour sub_question: toujours inclure dans content:
  - Le numéro et thème de l'exercice parent
  - Le contexte minimal (quelle fonction, quelle suite, quel problème)
  - La sous-question elle-même

Mauvais exemple (non autonome):
  content: "b) Déterminer les limites de f aux bornes."
  → Impossible à comprendre sans savoir ce qu'est f.

Bon exemple (autonome):
  content: "Exercice 1 — f(x) = (x−1)/(x−2), courbe (C) dans repère orthonormal.
            b) Déterminer les limites de f aux bornes des intervalles du domaine."
```

---

### 4.6 — Token budget and page splitting

The Groq llama-3.3-70b model handles long pages well but degrades on very dense content.

**Recommended page splitting strategy:**
- Chimie exams: split pages into left column / right column before sending
  (reduces token count AND eliminates column interleaving)
- Math exams: same — send left column (Partie A items) and right column (Partie B exercises)
  as separate LLM calls
- SVT/Histoire exams: send full page (single column, no split needed)

**Benefits:**
- Smaller input → faster response, fewer errors
- Column split done at extraction stage means LLM never sees interleaved content
- Each call handles one semantic section (Partie A OR Partie B, not both)

---

## Section 5 — Cross-Cutting Extraction Risks

---

### Risk 1 — Two-column reading order corruption (severity: critical)

**Confirmed from Math 2025 exams.** PyMuPDF default (`get_text("text")`) reads
left-to-right across the full page width. In a two-column layout it produces:

```
"1) L'ensemble des solutions réelles de l'équation 2(ln x)² − ln x − 6 = 0 est S = ………
1. Soit la fonction numérique f de variable réelle x définie par f(x) = (x−1)/(x−2)..."
```

This is Partie A item 1 merged with Partie B Exercice 1 — unworkable.

**Fix:** Detect column boundary (x-midpoint of page blocks), then:
1. Extract all text blocks with x < midpoint → left column text
2. Extract all text blocks with x >= midpoint → right column text
3. Concatenate: left column + right column
4. Send to LLM

**Note:** Header and N.B. blocks span full width. Their x range covers both halves.
Detect them by their y-position (above the column split start) and keep them before
the left column text, not mixed into it.

---

### Risk 2 — Formula garbling (severity: very high in Math and Chimie)

**Confirmed garbling patterns:**
- Subscripts and superscripts lost or converted to inline text
- Fractions flattened: `(eˣ-1)/(eˣ+1)` → `1 1 x x e e`
- Limits lost: `lim(n→∞)` → `lim  .....  n n`
- Complex numbers: `√2·e^(iπ/2)` → `2  i  2`
- Ionic charges: `Fe3+(aq)` → `( )  3 Fe aq`
- Greek letters: `Ω` often lost or becomes `(` or `)`

**Every Partie A item in Math exams is affected.**
**Partie C in Chimie (ionic equations) is severely affected.**

**Strategy:** `has_formula: true` + reproduce as-is + topic_hint carries the meaning.

---

### Risk 3 — SVT discipline boundary (severity: medium)

Single column layout. No visual cue separates BIOLOGIE from GEOLOGIE except
the bold all-caps section title. PyMuPDF reads it correctly but the chunker
must detect it and update the running subject context.

**Trigger detection:** If a line is exactly "BIOLOGIE" or "GEOLOGIE"
(all-caps, possibly bold), update `current_discipline` in running context.
All subsequent chunks inherit `subject: "SVT - [discipline]"`.

---

### Risk 4 — Context blocks that look like questions (severity: medium)

**Confirmed in SVT 2021:**
"Le biologiste américain Thomas Morgan (20e siècle) a étudié les mutations
sur la drosophile. Les scientifiques ont identifié et étudié ainsi des
mutations chez les humains."

This is a contextual setup paragraph, NOT a question. It precedes Thème II questions.
If classified as `question_open`, it becomes an empty chunk with no answer.

**Detection rule:** No interrogative form, no numbered label, no task verb
(Définir, Expliquer, Citer, Nommer, Distinguer) → not a question.
Include in the preceding section_header chunk.

**Similarly in Géologie:** "Répondre aux questions suivantes." is a task instruction,
not a question. Include in the Thème section_header.

---

### Risk 5 — Serie-specific instructions embedded in content (severity: medium)

**Confirmed in Chimie 2023 Partie E:**
"Résoudre : SVT : deux (2) des trois (3) problèmes. SMP : un (1) des trois (3) problèmes."

This looks like content but is an instruction. Classify as `section_header`.
Preserve the full text — a student might ask "how many problems do I solve in SMP Chimie?"
and this chunk should surface.

---

### Risk 6 — "On donne" / "Données" blocks (severity: high for calculation subjects)

**Confirmed in Chimie 2023 Partie E:**
`"On donne en g/mol : C :12 ; H :1 ; O :16 ; Cl :35,5."`

This appears at the bottom of the page, after all three problems. Without it,
every calculation sub_question in Partie E is unsolvable. It must be injected
into every affected chunk, not stored as a standalone chunk.

**Same pattern in Physique:** "Données:" block at start of each exercise.
Always include in question_open AND each sub_question.

---

### Risk 7 — Exam center name vs. serie (severity: low but causes confusion)

The large stylized name in the top-right of the header (Distance, Graphe,
Dessalines, Gamète, Covalente) is the **exam center name**, not a serie.

| Filename suffix | Header serie |
|---|---|
| Distance | SÉRIE : LLA |
| Graphe | SÉRIE : SMP |
| Dessalines | SERIES : SES/LLA |
| Gamète | SÉRIES : (SES-SMP) |
| Covalente | SÉRIES : (SVT, SMP) |

Always extract `serie` from the header text. Store the exam center name in a
separate `exam_center` metadata field (or `source_pdf` filename reference).

---

### Risk 8 — Point values inline in questions (severity: low but affects retrieval)

**Confirmed in Hist-Geo 2022 Deuxième Partie:**
"1- A quel événement le texte 1 fait-il allusion ? Indiquez-en une (1) cause. (6 pts)"

The `(6 pts)` is structural metadata, not question content. A student searching
for this question does not include "(6 pts)" in their query.

**Rule:** Extract to `points: 6`. Remove from `content` field.

---

## Section 6 — Fallback Strategy for Unknown Structures

When a PDF contains a structure not matching any pattern above:

**Step 1:** Find the unit of meaning — the smallest piece a student could usefully retrieve.

**Step 2:** Apply universal rules:
- Every chunk is self-contained (sufficient context to understand without neighbors)
- Metadata propagated from running context dict (year, subject, serie, section)
- `content` never empty or null
- `has_formula` and `has_table` flags set correctly

**Step 3:** Use `chunk_type: "other"`, describe what it is in `topic_hint`.

**Step 4:** Log it:
- Subject, year, session (BAC PERMANENT / BACCALAURÉAT RÉGULIER)
- Description of the structure
- How you chunked it
- Which topic_hint you used

**The "other" type is a detection mechanism.** After ingesting a batch,
query Chroma for `chunk_type = "other"` and read the `topic_hint` descriptions.
These tell you what new patterns to formalize next.

---

## Section 7 — Chunk Type Confirmed Usage by Subject

| chunk_type      | Math | Hist-Geo | SVT Biologie | SVT Géologie | Chimie | Physique |
|-----------------|------|----------|--------------|--------------|--------|----------|
| exam_header     |  ✅  |    ✅    |      ✅      |      —       |   ✅   |    ✅    |
| instructions    |  ✅  |    ✅    |      ✅      |      —       |   ✅   |    ✅    |
| section_header  |  ✅  |    ✅    |      ✅      |      ✅      |   ✅   |    ✅    |
| passage         |  ❌  |    ✅    |      ❌      |      ❌      |   ✅   |    ❌    |
| question_mcq    |  ❌  |    ❌    |      ❌      |      ❌      |   ❌   |   rare   |
| question_fillin |  ✅  |    ❌    |      ❌      |      ✅      |   ✅   |    ❌    |
| question_open   |  ✅  |    ✅    |      ✅      |      ✅      |   ✅   |    ✅    |
| sub_question    |  ✅  |    ❌    |      ✅      |      ❌      |   ✅   |    ✅    |
| table           |  ✅  |    ❌    |      ❌      |      ❌      |   ❌   |    ❌    |
| other           | net  |   net    |     net      |     net      |   net  |    net   |

*net = detection net for new patterns*

---

## Section 8 — Decision Tree (Quick Reference)

```
New PDF received
      │
      ├─ 1. READ HEADER
      │       Extract: subject, year, serie, exam_center, duration(s)
      │       Check: single serie or multiple? (SES/LLA vs just SMP)
      │       Check: single duration or serie-specific? (SVT 3h / SMP 2h30)
      │
      ├─ 2. DETECT LAYOUT PER PAGE
      │       ├─ All blocks in one x-range?      → Layout A — default extraction
      │       ├─ Blocks split left/right?         → Layout B — split at midpoint
      │       │   Check: where does split start?  (after full-width header)
      │       └─ Single col but "BIOLOGIE"/"GEOLOGIE" found?  → Layout D
      │
      ├─ 3. IDENTIFY SUBJECT → APPLY PATTERNS
      │       ├─ Mathématiques
      │       │     "PARTIE A... Recopier et compléter"   → Pattern M1 (question_fillin ×10)
      │       │     "PARTIE B... Traiter N des M"         → Pattern M2/M3 (question_open + sub_question)
      │       │     Tables in Partie B stats exercise     → Pattern M3 variant (repeat table)
      │       │
      │       ├─ Histoire-Géographie
      │       │     "Texte N" + "Sujet N" pairs           → Pattern H1 (passage + question_open)
      │       │     "DEUXIEME PARTIE" numbered Qs with pts → Pattern H2 (question_open, extract pts)
      │       │
      │       ├─ SVT
      │       │     "BIOLOGIE" title                      → Pattern S1 (subject: "SVT - Biologie")
      │       │     "GEOLOGIE" title                      → Pattern S2 (subject: "SVT - Géologie")
      │       │     Fill-in blanks (……)                   → question_fillin
      │       │     Multi-task, no lettering              → one question_open
      │       │     Lettered a) b) sub-parts              → parent + sub_question ×N
      │       │
      │       ├─ Chimie
      │       │     "PARTIE A" bullet fill-in             → Pattern C1 (question_fillin ×N)
      │       │     "PARTIE B" reaction names             → Pattern C2 (question_open ×N)
      │       │     "PARTIE C" choice question            → Pattern C3
      │       │     "PARTIE D" passage + questions        → Pattern C4 (passage + question_open)
      │       │     "PARTIE E" calculation problems       → Pattern C5 (inject molar masses)
      │       │
      │       ├─ Physique
      │       │     "Données:" block                      → inject in question_open AND sub_questions
      │       │     Sub-questions a) b) c) d)             → sub_question with Données repeated
      │       │
      │       └─ Philosophie / Économie
      │             Essay prompts                         → question_open
      │             Source documents                      → passage
      │
      └─ 4. UNKNOWN STRUCTURE
                chunk_type: "other" + topic_hint description + log it
```

---

## Section 9 — Chunk Type Quick Reference

| chunk_type       | When to use | topic_hint |
|------------------|-------------|------------|
| `exam_header`    | Ministry, subject, year, serie, exam center, duration | null |
| `instructions`   | Rules, N.B., duration, "traiter N des M", "choisir un sujet" | null |
| `section_header` | Part titles, discipline titles, theme titles, context blocks, serie-specific task instructions | null |
| `passage`        | Source text, historical document, philosophical text, scientific extract | Required — describe theme + key ideas |
| `question_mcq`   | Question + ALL options a/b/c/d together always | Required |
| `question_fillin`| Fill-in-blank, complete sentence, fill table cell, fill+explain combo | Required — name the concept |
| `question_open`  | Essay prompt, definition, explanation, open calculation, equation to write, exercise parent | Required |
| `sub_question`   | Lettered sub-part a/b/c/d — ALWAYS includes parent context in content | Required — name specific skill tested |
| `table`          | Standalone data table shared across questions | Required |
| `other`          | Anything not above — log and describe | Required — describe what it is |