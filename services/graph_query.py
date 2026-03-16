"""Neo4j graph query service."""

from typing import List, Dict, Any, Optional
from loguru import logger

from app.config import get_settings


class Neo4jQueryService:
    """Query the Neo4j graph."""

    def __init__(self, driver=None):
        """Initialize query service."""
        settings = get_settings()

        if not settings.neo4j_enabled:
            raise ValueError("Neo4j is not enabled. Set NEO4J_ENABLED=true in .env")

        self.settings = settings
        self.driver = driver

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self.driver is None:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password)
            )
        return self.driver

    def close(self):
        """Close the driver."""
        if self.driver:
            self.driver.close()

    def get_exam_structure(self, subject: str, year: int) -> Dict[str, Any]:
        """Get full exam structure."""
        driver = self._get_driver()

        query = """
        MATCH (e:Exam {subject: $subject, year: $year})
        OPTIONAL MATCH (e)-[:has_section]->(s:Section)
        OPTIONAL MATCH (s)-[:has_question]->(q:Question)
        OPTIONAL MATCH (q)-[:has_sub]->(sq:SubQuestion)
        OPTIONAL MATCH (e)-[:has_instruction]->(i:Instruction)
        OPTIONAL MATCH (e)-[:has_passage]->(p:Passage)
        RETURN e, collect(DISTINCT s) as sections,
               collect(DISTINCT i) as instructions,
               collect(DISTINCT p) as passages,
               [q IN collect(DISTINCT q) | {
                   number: q.number,
                   type: q.chunk_type,
                   topic: q.topic_hint,
                   content: q.content,
                   sub_questions: [sq IN collect(DISTINCT sq) WHERE (q)-[:has_sub]->(sq) | {
                       letter: sq.letter,
                       content: sq.content
                   }]
               }] as questions
        ORDER BY s.order
        """

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query, subject=subject, year=year)
            record = result.single()

            if not record:
                return {"error": f"Exam not found: {subject} {year}"}

            return {
                "exam": dict(record["e"]) if record["e"] else None,
                "sections": [dict(s) for s in record["sections"] if s],
                "instructions": [dict(i) for i in record["instructions"] if i],
                "passages": [dict(p) for p in record["passages"] if p],
                "questions": record["questions"]
            }

    def get_exams_by_subject(self, subject: str) -> List[Dict[str, Any]]:
        """Get all exams of a subject."""
        driver = self._get_driver()

        query = """
        MATCH (e:Exam {subject: $subject})
        RETURN e
        ORDER BY e.year DESC
        """

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query, subject=subject)
            return [dict(record["e"]) for record in result]

    def get_related_by_topic(self, topic_hint: str) -> List[Dict[str, Any]]:
        """Find questions with similar topics."""
        driver = self._get_driver()

        query = """
        MATCH (q1:Question)-[:same_topic]->(q2:Question)
        WHERE q1.topic_hint CONTAINS $topic OR q2.topic_hint CONTAINS $topic
        RETURN q1, q2
        LIMIT 20
        """

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query, topic=topic_hint)
            related = []
            for record in result:
                related.append({
                    "question_1": dict(record["q1"]),
                    "question_2": dict(record["q2"])
                })
            return related

    def navigate_question_tree(
        self,
        subject: str,
        year: int,
        section: str,
        question_number: str,
        sub_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Navigate to specific question in exam."""
        driver = self._get_driver()

        if sub_question:
            query = """
            MATCH (e:Exam {subject: $subject, year: $year})
            MATCH (e)-[:has_section]->(s:Section {name: $section})
            MATCH (s)-[:has_question]->(q:Question {number: $question_number})
            MATCH (q)-[:has_sub]->(sq:SubQuestion {letter: $sub_question})
            RETURN e, s, q, sq
            """
            params = {
                "subject": subject,
                "year": year,
                "section": section,
                "question_number": question_number,
                "sub_question": sub_question
            }
        else:
            query = """
            MATCH (e:Exam {subject: $subject, year: $year})
            MATCH (e)-[:has_section]->(s:Section {name: $section})
            MATCH (s)-[:has_question]->(q:Question {number: $question_number})
            OPTIONAL MATCH (q)-[:has_sub]->(sq:SubQuestion)
            RETURN e, s, q, collect(sq) as sub_questions
            """
            params = {
                "subject": subject,
                "year": year,
                "section": section,
                "question_number": question_number
            }

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query, **params)
            record = result.single()

            if not record:
                return {"error": f"Question not found: {section} {question_number}"}

            return {
                "exam": dict(record["e"]) if record["e"] else None,
                "section": dict(record["s"]) if record["s"] else None,
                "question": dict(record["q"]) if record["q"] else None,
                "sub_questions": [dict(sq) for sq in record["sub_questions"] if sq]
            }

    def get_subject_progression(self) -> List[Dict[str, Any]]:
        """Get all subjects with their series and years."""
        driver = self._get_driver()

        query = """
        MATCH (e:Exam)
        RETURN e.subject as subject,
               collect(DISTINCT e.serie) as series,
               collect(DISTINCT e.year) as years,
               count(e) as exam_count
        ORDER BY exam_count DESC
        """

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query)
            return [dict(record) for record in result]

    def get_section_questions(self, subject: str, year: int, section: str) -> List[Dict[str, Any]]:
        """Get all questions in a section."""
        driver = self._get_driver()

        query = """
        MATCH (e:Exam {subject: $subject, year: $year})
        MATCH (e)-[:has_section]->(s:Section {name: $section})
        MATCH (s)-[:has_question]->(q:Question)
        OPTIONAL MATCH (q)-[:has_sub]->(sq:SubQuestion)
        OPTIONAL MATCH (q)-[:next]->(next_q:Question)
        RETURN q, collect(sq) as sub_questions, next_q
        ORDER BY q.chunk_index
        """

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query, subject=subject, year=year, section=section)
            questions = []
            for record in result:
                questions.append({
                    "question": dict(record["q"]),
                    "sub_questions": [dict(sq) for sq in record["sub_questions"] if sq],
                    "next": dict(record["next_q"]) if record["next_q"] else None
                })
            return questions

    def search_by_content(self, query_text: str) -> List[Dict[str, Any]]:
        """Search questions by content (case-insensitive)."""
        driver = self._get_driver()

        query = """
        MATCH (q:Question)
        WHERE toLower(q.content) CONTAINS toLower($query)
        RETURN q
        ORDER BY q.chunk_index
        LIMIT 20
        """

        with driver.session(database=self.settings.neo4j_database) as session:
            result = session.run(query, query=query_text)
            return [dict(record["q"]) for record in result]

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        driver = self._get_driver()

        queries = {
            "exams": "MATCH (e:Exam) RETURN count(e) as count",
            "sections": "MATCH (s:Section) RETURN count(s) as count",
            "questions": "MATCH (q:Question) RETURN count(q) as count",
            "sub_questions": "MATCH (sq:SubQuestion) RETURN count(sq) as count",
            "passages": "MATCH (p:Passage) RETURN count(p) as count",
            "instructions": "MATCH (i:Instruction) RETURN count(i) as count",
            "same_subject": "MATCH ()-[r:same_subject]->() RETURN count(r) as count",
            "same_topic": "MATCH ()-[r:same_topic]->() RETURN count(r) as count",
        }

        stats = {}
        with driver.session(database=self.settings.neo4j_database) as session:
            for key, q in queries.items():
                result = session.run(q)
                stats[key] = result.single()["count"]

        return stats
