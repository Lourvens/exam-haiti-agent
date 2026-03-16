"""Graph query tool for Neo4j."""

from typing import Optional, Dict, Any, List

from app.config import get_settings


class GraphQueryTool:
    """Tool for querying the Neo4j knowledge graph."""

    def __init__(self):
        """Initialize the graph query tool."""
        settings = get_settings()

        if not settings.neo4j_enabled:
            raise ValueError("Neo4j is not enabled. Set NEO4J_ENABLED=true in .env")

        self.settings = settings
        self._driver = None

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password)
            )
        return self._driver

    def close(self):
        """Close the driver."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge graph for exam content.

        Args:
            query: Natural language query about exam topics
            filters: Optional filters (subject, year, serie)

        Returns:
            List of matching graph nodes with their properties
        """
        driver = self._get_driver()
        filters = filters or {}

        with driver.session(database=self.settings.neo4j_database) as session:
            results = []

            subject = filters.get("subject")
            year = filters.get("year")
            serie = filters.get("serie")
            topic = filters.get("topic")

            # Build query based on available filters
            # Priority: 1) subject/year/serie filters, 2) topic keyword, 3) query

            # If we have subject or year filters, search questions directly
            if subject or year:
                # Build cypher query with filters
                conditions = []
                params = {}

                if subject:
                    conditions.append("q.exam_subject CONTAINS $subject")
                    params["subject"] = subject

                if year:
                    conditions.append("q.exam_year = $year")
                    params["year"] = year

                if serie:
                    conditions.append("q.exam_serie CONTAINS $serie")
                    params["serie"] = serie

                cypher = f"""
                    MATCH (q:Question)
                    WHERE {' AND '.join(conditions)}
                    RETURN q.id as id, q.number as number, q.topic_hint as topic,
                           q.content as content, q.chunk_type as chunk_type,
                           q.exam_subject as subject, q.exam_year as year,
                           q.exam_serie as serie
                    ORDER BY q.number
                    LIMIT 30
                """

                result = session.run(cypher, **params)
                for record in result:
                    results.append({
                        "type": "question",
                        "id": record["id"],
                        "number": record["number"],
                        "topic": record["topic"],
                        "content": record["content"],
                        "chunk_type": record["chunk_type"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "serie": record["serie"]
                    })

            # If no results from filters, try topic/query search
            if not results and (topic or query):
                search_term = topic or query
                result = session.run("""
                    MATCH (q:Question)
                    WHERE q.topic_hint CONTAINS $search_term
                       OR q.content CONTAINS $search_term
                       OR q.exam_subject CONTAINS $search_term
                    RETURN q.id as id, q.number as number, q.topic_hint as topic,
                           q.content as content, q.chunk_type as chunk_type,
                           q.exam_subject as subject, q.exam_year as year,
                           q.exam_serie as serie
                    LIMIT 20
                """, search_term=search_term)
                for record in result:
                    results.append({
                        "type": "question",
                        "id": record["id"],
                        "number": record["number"],
                        "topic": record["topic"],
                        "content": record["content"],
                        "chunk_type": record["chunk_type"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "serie": record["serie"]
                    })

            # If still no results, get recent exams
            if not results:
                result = session.run("""
                    MATCH (e:Exam)
                    RETURN e.id as id, e.subject as subject, e.year as year, e.serie as serie
                    ORDER BY e.year DESC
                    LIMIT 10
                """)
                for record in result:
                    results.append({
                        "type": "exam",
                        "id": record["id"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "serie": record["serie"]
                    })

            return results

    def get_exam_structure(self, exam_id: str) -> Dict[str, Any]:
        """
        Get the structure of an exam (sections, questions).

        Args:
            exam_id: The exam ID

        Returns:
            Dictionary with exam structure
        """
        driver = self._get_driver()

        with driver.session(database=self.settings.neo4j_database) as session:
            exam_result = session.run("""
                MATCH (e:Exam {id: $exam_id})
                RETURN e.id as id, e.subject as subject, e.year as year, e.serie as serie
            """, exam_id=exam_id)

            exam_record = exam_result.single()
            if not exam_record:
                return {}

            exam = {
                "id": exam_record["id"],
                "subject": exam_record["subject"],
                "year": exam_record["year"],
                "serie": exam_record["serie"],
                "sections": []
            }

            section_result = session.run("""
                MATCH (e:Exam {id: $exam_id})-[:has_section]->(s:Section)
                RETURN s.name as name, s.order as order
                ORDER BY s.order
            """, exam_id=exam_id)

            for record in section_result:
                exam["sections"].append({
                    "name": record["name"],
                    "order": record["order"]
                })

            return exam


def create_graph_query_tool() -> GraphQueryTool:
    """Factory function to create a GraphQueryTool."""
    return GraphQueryTool()
