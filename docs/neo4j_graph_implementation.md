# Neo4j Graph Implementation for Exam Haiti Agent

## Overview

This document describes the implementation of a Neo4j knowledge graph to represent Haitian Baccalaureate exam documents. The graph enables document structure navigation, subject-based clustering, and semantic traversal.

---

## 1. Graph Schema

### 1.1 Node Types

| Node | Properties | Description |
|------|------------|-------------|
| **Exam** | `id`, `subject`, `year`, `serie`, `pdf_path` | Root node for each exam PDF |
| **Section** | `name`, `points`, `order` | PARTIE A, PARTIE B, etc. |
| **Question** | `number`, `chunk_type`, `topic_hint`, `has_formula`, `content`, `chunk_index` | Questions (A1, A2, C1, etc.) |
| **SubQuestion** | `letter`, `content`, `topic_hint`, `chunk_index` | Sub-questions (a, b, c) |
| **Passage** | `content`, `topic_hint`, `chunk_index` | Reading text sections |
| **Instruction** | `content`, `chunk_index` | General instructions |

### 1.2 Relationship Types

| Relationship | Direction | Description |
|--------------|-----------|-------------|
| `has_section` | Exam → Section | Exam contains section |
| `has_question` | Section → Question | Section contains question |
| `has_sub` | Question → SubQuestion | Question has sub-questions |
| `belongs_to` | SubQuestion → Question | Sub-question belongs to parent |
| `next` | Question → Question | Sequential order in section |
| `next_sub` | SubQuestion → SubQuestion | Sequential sub-questions |
| `has_instruction` | Exam → Instruction | Exam has instructions |
| `has_passage` | Section → Passage | Section has reading passage |
| `same_subject` | Exam → Exam | Same subject across exams |
| `same_serie` | Exam → Exam | Same serie across years |
| `same_topic` | Question → Question | Similar topic hint |

---

## 2. Hierarchical Structure

```
Exam (Document)
├── exam_header
├── instructions
├── Section: PARTIE A
│   └── Question: A1
│   └── Question: A2
│   └── ...
├── Section: PARTIE B
│   └── ...
├── Section: PARTIE C
│   ├── Question: C1
│   ├── Question: C2
│   │   ├── SubQuestion: 2a
│   │   └── SubQuestion: 2b
│   └── ...
├── Section: PARTIE D
│   ├── Passage
│   └── Question: D1, D2, D3
└── ...
```

---

## 3. Cross-Document Connections

### Subject Clustering
```
Exam (Chimie 2020) --same_subject--> Exam (Chimie 2021) --same_subject--> Exam (Chimie 2022)
```

### Serie Progression
```
Exam (Chimie 2020 LLA) --same_serie--> Exam (Chimie 2021 LLA)
```

### Topic Similarity
```
Question (topic_hint: "glucose") --same_topic--> Question (topic_hint: "fermentation")
```

---

## 4. Implementation Components

### 4.1 Graph Builder Service

**File:** `services/graph_builder.py`

```python
class Neo4jGraphBuilder:
    """Builds Neo4j graph from Chroma vector store."""

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    def sync_from_chroma(self):
        """Sync all documents from Chroma vector store to Neo4j."""
        # 1. Get all unique documents from Chroma
        # 2. For each document, extract chunks
        # 3. Create nodes and relationships
        # 4. Create cross-document connections
```

### 4.2 Graph Query Service

**File:** `services/graph_query.py`

```python
class Neo4jQueryService:
    """Query the Neo4j graph."""

    def get_exam_structure(self, subject: str, year: int):
        """Get full exam structure."""

    def get_related_questions(self, topic_hint: str):
        """Find questions with similar topics."""

    def navigate_question_tree(self, section: str, question: str):
        """Navigate to specific question."""
```

### 4.3 Config Updates

**File:** `app/config.py`

Add:
```python
# Neo4j Configuration
neo4j_uri: str = "bolt://localhost:7687"
neo4j_user: str = "neo4j"
neo4j_password: str = ""
neo4j_database: str = "neo4j"
```

---

## 5. Sample Cypher Queries

### 5.1 Get Exam Structure

```cypher
MATCH (e:Exam {subject: $subject, year: $year})
OPTIONAL MATCH (e)-[:has_section]->(s:Section)
OPTIONAL MATCH (s)-[:has_question]->(q:Question)
OPTIONAL MATCH (q)-[:has_sub]->(sq:SubQuestion)
RETURN e, s, q, sq
ORDER BY s.order, q.number, sq.letter
```

### 5.2 Get Questions by Topic

```cypher
MATCH (q:Question)-[:same_topic]->(related:Question)
WHERE q.topic_hint CONTAINS $topic
RETURN DISTINCT related.exam_subject, related.exam_year,
       collect(DISTINCT related.number) as questions
ORDER BY related.exam_year
```

### 5.3 Navigate to Specific Question

```cypher
MATCH (e:Exam {subject: $subject, year: $year})
MATCH (e)-[:has_section]->(s:Section {name: $section})
MATCH (s)-[:has_question]->(q:Question {number: $question})
OPTIONAL MATCH (q)-[:has_sub]->(sq:SubQuestion)
RETURN q, sq
```

### 5.4 Get Subject Progression

```cypher
MATCH (e1:Exam)-[:same_subject]->(e2:Exam)
WHERE e1.subject = e2.subject
RETURN e1.subject, collect(DISTINCT e1.serie) as series,
       collect(DISTINCT e1.year) as years
ORDER BY size(years) DESC
```

---

## 6. Data Sync Strategy

### 6.1 Initial Sync
1. Query Chroma for all unique sources (PDFs)
2. For each source, get all chunks with metadata
3. Create Exam node if not exists
4. Create Section, Question, SubQuestion nodes
5. Create hierarchical relationships
6. Create cross-document relationships (same_subject, same_serie, same_topic)

### 6.2 Incremental Sync
1. On document re-index, delete existing nodes for that document
2. Re-create nodes and relationships
3. Preserve cross-document connections

---

## 7. Dependencies

Add to `pyproject.toml`:
```toml
neo4j>=5.0.0
langchain-neo4j>=0.1.0  # if available
```

---

## 8. Files to Create

| File | Purpose |
|------|---------|
| `services/graph_builder.py` | Sync from Chroma to Neo4j |
| `services/graph_query.py` | Query the graph |
| `models/graph_nodes.py` | Pydantic models for nodes |
| `scripts/sync_graph.py` | CLI to sync graph |
| `tests/test_graph.py` | Unit tests |

---

## 9. Usage

### Sync from Chroma to Neo4j
```bash
uv run python scripts/sync_graph.py
```

### Query via API
```bash
curl "http://localhost:8000/api/v1/graph/exam?subject=Chimie&year=2020"
```

---

## 10. Future Enhancements

- Add embedding similarity relationships in Neo4j
- Implement graph-based retrieval for RAG
- Add weighted relationships based on topic similarity score
- Visualize exam structure in Streamlit dashboard
