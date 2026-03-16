"""Neo4j graph builder - syncs from Chroma vector store to Neo4j."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load env vars BEFORE importing settings
load_dotenv()

from app.config import get_settings
from models.graph_nodes import ChunkGraphData


def create_llm_client():
    """Create an LLM client based on settings."""
    from langchain_openai import ChatOpenAI
    from app.config import get_settings

    settings = get_settings()

    llm_kwargs = {"model": settings.openai_model, "api_key": settings.openai_api_key}
    if settings.openai_api_base:
        llm_kwargs["base_url"] = settings.openai_api_base

    return ChatOpenAI(**llm_kwargs)


class Neo4jGraphBuilder:
    """Builds Neo4j graph from Chroma vector store."""

    def __init__(self, driver=None):
        """Initialize graph builder."""
        settings = get_settings()

        if not settings.neo4j_enabled:
            raise ValueError("Neo4j is not enabled. Set NEO4J_ENABLED=true in .env")

        if not settings.neo4j_password:
            raise ValueError("Neo4j password required. Set NEO4J_PASSWORD in .env")

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

    def _get_chunks_from_chroma(self) -> List[Dict[str, Any]]:
        """Get all chunks from Chroma vector store."""
        from langchain_chroma import Chroma
        from services.ingestion_pipeline import EmbeddingProvider

        logger.info("Loading chunks from Chroma...")

        # Create embeddings (needed for Chroma)
        embeddings = EmbeddingProvider.create_embeddings()

        # Load Chroma
        vectorstore = Chroma(
            collection_name=self.settings.chroma_collection_name,
            embedding_function=embeddings,
            persist_directory=str(self.settings.chroma_persist_directory)
        )

        # Get all documents
        results = vectorstore.get(include=["metadatas", "documents"])

        chunks = []
        for i, (doc, meta) in enumerate(zip(
            results.get("documents", []),
            results.get("metadatas", [])
        )):
            chunks.append({
                "content": doc,
                "metadata": meta,
                "chunk_index": meta.get("chunk_index", i)
            })

        logger.info(f"Loaded {len(chunks)} chunks from Chroma")
        return chunks

    def _group_chunks_by_exam(self, chunks: List[Dict]) -> Dict[str, List[Dict]]:
        """Group chunks by exam (PDF source)."""
        exams = {}
        for chunk in chunks:
            pdf_path = chunk["metadata"].get("source", "unknown")
            exam_id = Path(pdf_path).stem

            if exam_id not in exams:
                exams[exam_id] = {
                    "pdf_path": pdf_path,
                    "chunks": []
                }
            exams[exam_id]["chunks"].append(chunk)

        return exams

    def _convert_chunk_to_graph_data(self, chunk: Dict) -> ChunkGraphData:
        """Convert Chroma chunk to graph data model."""
        meta = chunk["metadata"]
        content = chunk["content"]

        # Extract exam info from filename or metadata
        pdf_path = meta.get("source", "")
        exam_id = Path(pdf_path).stem

        # Parse exam ID to get subject, year, serie
        # Format: Subject_Year_Serie or Subject-Year-Serie
        parts = exam_id.replace("-", "_").split("_")
        subject = meta.get("subject", parts[0] if len(parts) > 0 else "Unknown")
        year = int(meta.get("year", parts[1] if len(parts) > 1 else 0))
        serie = meta.get("serie", parts[2] if len(parts) > 2 else "Unknown")

        # Get section info
        section = meta.get("section")
        section_order = 0
        if section and "PARTIE" in section.upper():
            # Extract order: PARTIE A -> 1, PARTIE B -> 2
            section_order = ord(section.split()[-1].upper()[0]) - ord('A') + 1

        return ChunkGraphData(
            exam_id=exam_id,
            exam_subject=subject,
            exam_year=year,
            exam_serie=serie,
            pdf_path=pdf_path,
            section_name=section,
            section_order=section_order,
            question_number=meta.get("question_number"),
            question_type=meta.get("chunk_type"),
            question_topic=meta.get("topic_hint"),
            has_formula=meta.get("has_formula", "False") == "True",
            question_content=content if meta.get("chunk_type", "").startswith("question") else None,
            sub_question_letter=meta.get("sub_question"),
            sub_question_content=content if meta.get("sub_question") else None,
            sub_question_topic=meta.get("topic_hint") if meta.get("sub_question") else None,
            passage_content=content if meta.get("chunk_type") == "passage" else None,
            passage_topic=meta.get("topic_hint") if meta.get("chunk_type") == "passage" else None,
            instruction_content=content if meta.get("chunk_type") == "instructions" else None,
            chunk_type=meta.get("chunk_type", "other"),
            chunk_index=chunk["chunk_index"]
        )

    def _create_exam_node(self, tx, exam_id: str, data: ChunkGraphData):
        """Create or merge Exam node."""
        tx.run("""
            MERGE (e:Exam {id: $exam_id})
            SET e.subject = $subject,
                e.year = $year,
                e.serie = $serie,
                e.pdf_path = $pdf_path
        """, exam_id=exam_id, subject=data.exam_subject, year=data.exam_year,
               serie=data.exam_serie, pdf_path=data.pdf_path)

    def _create_section_node(self, tx, exam_id: str, data: ChunkGraphData):
        """Create Section node and relationship to Exam."""
        if not data.section_name:
            return

        tx.run("""
            MATCH (e:Exam {id: $exam_id})
            MERGE (s:Section {name: $section_name})
            SET s.points = $points, s.order = $section_order
            MERGE (e)-[:has_section]->(s)
        """, exam_id=exam_id, section_name=data.section_name,
               points=None, section_order=data.section_order or 0)

    def _create_question_node(self, tx, exam_id: str, data: ChunkGraphData):
        """Create Question node and relationships."""
        if not data.question_number or not data.question_type:
            return

        # Determine which section this question belongs to
        section_match = ""
        if data.section_name:
            section_match = "MATCH (s:Section {name: $section_name}) "

        query = f"""
            MATCH (e:Exam {{id: $exam_id}})
            {section_match}
            MERGE (q:Question {{id: $q_id}})
            SET q.number = $number,
                q.chunk_type = $chunk_type,
                q.topic_hint = $topic_hint,
                q.has_formula = $has_formula,
                q.content = $content,
                q.chunk_index = $chunk_index,
                q.exam_subject = $exam_subject,
                q.exam_year = $exam_year,
                q.exam_serie = $exam_serie
            MERGE (e)-[:has_question_in_exam]->(q)
        """

        if data.section_name:
            query += """
            MERGE (s)-[:has_question]->(q)
            """

        q_id = f"{exam_id}_{data.section_name}_{data.question_number}"

        tx.run(query, exam_id=exam_id, section_name=data.section_name,
               q_id=q_id, number=data.question_number, chunk_type=data.question_type,
               topic_hint=data.question_topic, has_formula=data.has_formula,
               content=data.question_content or "", chunk_index=data.chunk_index,
               exam_subject=data.exam_subject, exam_year=data.exam_year,
               exam_serie=data.exam_serie)

    def _create_subquestion_node(self, tx, exam_id: str, data: ChunkGraphData):
        """Create SubQuestion node and relationships."""
        if not data.sub_question_letter or not data.question_number:
            return

        q_id = f"{exam_id}_{data.section_name}_{data.question_number}"
        sq_id = f"{q_id}_{data.sub_question_letter}"

        tx.run("""
            MATCH (q:Question {id: $q_id})
            MERGE (sq:SubQuestion {id: $sq_id})
            SET sq.letter = $letter,
                sq.content = $content,
                sq.topic_hint = $topic_hint,
                sq.chunk_index = $chunk_index
            MERGE (q)-[:has_sub]->(sq)
        """, q_id=q_id, sq_id=sq_id, letter=data.sub_question_letter,
               content=data.sub_question_content or "", topic_hint=data.sub_question_topic,
               chunk_index=data.chunk_index)

    def _create_instruction_node(self, tx, exam_id: str, data: ChunkGraphData):
        """Create Instruction node."""
        if data.chunk_type != "instructions" or not data.instruction_content:
            return

        tx.run("""
            MATCH (e:Exam {id: $exam_id})
            MERGE (i:Instruction {id: $inst_id})
            SET i.content = $content,
                i.chunk_index = $chunk_index
            MERGE (e)-[:has_instruction]->(i)
        """, exam_id=exam_id, inst_id=f"{exam_id}_instruction",
               content=data.instruction_content, chunk_index=data.chunk_index)

    def _create_passage_node(self, tx, exam_id: str, data: ChunkGraphData):
        """Create Passage node."""
        if data.chunk_type != "passage" or not data.passage_content:
            return

        section_match = ""
        if data.section_name:
            section_match = "MATCH (s:Section {name: $section_name}) "

        query = f"""
            MATCH (e:Exam {{id: $exam_id}})
            {section_match}
            MERGE (p:Passage {{id: $passage_id}})
            SET p.content = $content,
                p.topic_hint = $topic_hint,
                p.chunk_index = $chunk_index
            MERGE (e)-[:has_passage]->(p)
        """

        if data.section_name:
            query += "MERGE (s)-[:has_passage]->(p)"

        passage_id = f"{exam_id}_passage_{data.chunk_index}"

        tx.run(query, exam_id=exam_id, section_name=data.section_name,
               passage_id=passage_id, content=data.passage_content,
               topic_hint=data.passage_topic, chunk_index=data.chunk_index)

    def _create_cross_document_relationships(self, tx):
        """Create same_subject, same_serie relationships."""
        # Same subject
        tx.run("""
            MATCH (e1:Exam)
            MATCH (e2:Exam)
            WHERE e1.subject = e2.subject AND e1.id <> e2.id
            MERGE (e1)-[:same_subject]->(e2)
        """)

        # Same serie
        tx.run("""
            MATCH (e1:Exam)
            MATCH (e2:Exam)
            WHERE e1.serie = e2.serie AND e1.id <> e2.id
            MERGE (e1)-[:same_serie]->(e2)
        """)

        # Same topic
        tx.run("""
            MATCH (q1:Question)
            MATCH (q2:Question)
            WHERE q1.topic_hint = q2.topic_hint
              AND q1.id <> q2.id
              AND q1.topic_hint IS NOT NULL
            MERGE (q1)-[:same_topic]->(q2)
        """)

    def _create_llm_entities(self, tx, exam_id: str, entities: List):
        """Create LLM-extracted entity nodes."""
        from models.graph_extraction import Entity

        for entity in entities:
            # Determine node label based on entity type
            label_map = {
                "concept": "Concept",
                "topic": "Topic",
                "formula": "Formula",
                "question": "Question",
            }
            label = label_map.get(entity.type, "Entity")

            # Build properties
            props = {
                "id": entity.id,
                "name": entity.name,
                "exam_id": entity.exam_id,
                "chunk_index": entity.chunk_index,
                "entity_type": entity.type
            }

            # Create node
            tx.run(f"""
                MERGE (n:{label} {{id: $id}})
                SET n = $props
            """, id=entity.id, props=props)

            # Connect to exam
            tx.run(f"""
                MATCH (e:Exam {{id: $exam_id}})
                MATCH (n {{id: $id}})
                MERGE (e)-[:has_entity]->(n)
            """, exam_id=exam_id, id=entity.id)

    def _create_llm_relations(self, tx, relations: List):
        """Create LLM-extracted relationship nodes."""
        from models.graph_extraction import Relation

        for rel in relations:
            # Map relation types to Neo4j relationship types
            rel_type_map = {
                "has_concept": "HAS_CONCEPT",
                "has_topic": "HAS_TOPIC",
                "requires": "REQUIRES",
                "same_topic": "SAME_TOPIC",
                "prerequisite": "PREREQUISITE",
                "related_concept": "RELATED_CONCEPT",
                "builds_on": "BUILDS_ON"
            }
            rel_type = rel_type_map.get(rel.relation_type, rel.relation_type.upper())

            # Create relationship
            tx.run(f"""
                MATCH (s {{id: $source_id}})
                MATCH (t {{id: $target_id}})
                MERGE (s)-[r:{rel_type}]->(t)
            """, source_id=rel.source_id, target_id=rel.target_id)

    def sync_from_chroma_llm(self, llm_client) -> Dict[str, Any]:
        """Sync with LLM-enhanced entity extraction."""
        from core.graph_extraction_graph import GraphExtractionEngine

        driver = self._get_driver()

        # Get chunks from Chroma
        chunks = self._get_chunks_from_chroma()

        # Group by exam
        exams = self._group_chunks_by_exam(chunks)

        logger.info(f"Syncing {len(exams)} exams to Neo4j with LLM extraction...")

        # Create extraction engine
        extraction_engine = GraphExtractionEngine(llm_client, verbose=True)

        with driver.session(database=self.settings.neo4j_database) as session:
            # Process each exam with LLM extraction
            for exam_id, exam_data in exams.items():
                logger.info(f"Processing exam with LLM: {exam_id}")

                # Get exam metadata
                first_chunk = exam_data["chunks"][0]
                meta = first_chunk["metadata"]
                pdf_path = meta.get("source", "")
                parts = exam_id.replace("-", "_").split("_")
                exam_subject = meta.get("subject", parts[0] if parts else "Unknown")
                exam_year = int(meta.get("year", parts[1] if len(parts) > 1 else 0))
                exam_serie = meta.get("serie", parts[2] if len(parts) > 2 else "Unknown")

                # First do rule-based sync for basic nodes
                chunks_data = []
                for chunk in exam_data["chunks"]:
                    data = self._convert_chunk_to_graph_data(chunk)
                    chunks_data.append(data)

                    # Create rule-based nodes
                    session.execute_write(self._create_exam_node, exam_id, data)
                    session.execute_write(self._create_section_node, exam_id, data)
                    session.execute_write(self._create_question_node, exam_id, data)
                    session.execute_write(self._create_subquestion_node, exam_id, data)
                    session.execute_write(self._create_instruction_node, exam_id, data)
                    session.execute_write(self._create_passage_node, exam_id, data)

                # Create sequential relationships
                session.execute_write(self._create_next_relationships, exam_id, chunks_data)

                # Now extract with LLM
                # Prepare chunks for extraction
                extract_chunks = []
                for chunk in exam_data["chunks"]:
                    extract_chunks.append({
                        "content": chunk["content"],
                        "metadata": chunk["metadata"]
                    })

                # Run LLM extraction
                try:
                    extraction_result = extraction_engine.extract_from_chunks(
                        chunks=extract_chunks,
                        exam_id=exam_id,
                        exam_subject=exam_subject,
                        exam_year=exam_year,
                        exam_serie=exam_serie
                    )

                    # Create LLM entities
                    if extraction_result["entities"]:
                        session.execute_write(
                            self._create_llm_entities,
                            exam_id,
                            extraction_result["entities"]
                        )

                    # Create LLM relations
                    if extraction_result["relations"]:
                        session.execute_write(
                            self._create_llm_relations,
                            extraction_result["relations"]
                        )

                    logger.info(f"  → Added {len(extraction_result['entities'])} entities")
                    logger.info(f"  → Added {len(extraction_result['relations'])} relations")

                except Exception as e:
                    logger.warning(f"  → LLM extraction failed: {e}")
                    # Continue with rule-based only

            # Create cross-document relationships
            session.execute_write(self._create_cross_document_relationships)

        logger.info("LLM-enhanced sync complete!")

        return {
            "status": "success",
            "exams_synced": len(exams),
            "total_chunks": len(chunks),
            "mode": "llm_enhanced"
        }

    def _create_next_relationships(self, tx, exam_id: str, chunks_data: List[ChunkGraphData]):
        """Create sequential relationships between questions in same section."""
        # Group by section
        sections = {}
        for data in chunks_data:
            if data.section_name and data.question_number:
                if data.section_name not in sections:
                    sections[data.section_name] = []
                sections[data.section_name].append(data)

        # Create next relationships within each section
        for section_name, questions in sections.items():
            # Sort by chunk_index
            questions.sort(key=lambda x: x.chunk_index)

            for i in range(len(questions) - 1):
                q1_id = f"{exam_id}_{section_name}_{questions[i].question_number}"
                q2_id = f"{exam_id}_{section_name}_{questions[i + 1].question_number}"

                tx.run("""
                    MATCH (q1:Question {id: $q1_id})
                    MATCH (q2:Question {id: $q2_id})
                    MERGE (q1)-[:next]->(q2)
                """, q1_id=q1_id, q2_id=q2_id)

    def sync_from_chroma(self) -> Dict[str, Any]:
        """Sync all documents from Chroma to Neo4j."""
        driver = self._get_driver()

        # Get chunks from Chroma
        chunks = self._get_chunks_from_chroma()

        # Group by exam
        exams = self._group_chunks_by_exam(chunks)

        logger.info(f"Syncing {len(exams)} exams to Neo4j...")

        with driver.session(database=self.settings.neo4j_database) as session:
            # Clear existing data (optional - can be made configurable)
            # session.run("MATCH (n) DETACH DELETE n")

            # Process each exam
            for exam_id, exam_data in exams.items():
                logger.info(f"Processing exam: {exam_id}")

                chunks_data = []
                for chunk in exam_data["chunks"]:
                    data = self._convert_chunk_to_graph_data(chunk)
                    chunks_data.append(data)

                    # Create nodes
                    session.execute_write(self._create_exam_node, exam_id, data)
                    session.execute_write(self._create_section_node, exam_id, data)
                    session.execute_write(self._create_question_node, exam_id, data)
                    session.execute_write(self._create_subquestion_node, exam_id, data)
                    session.execute_write(self._create_instruction_node, exam_id, data)
                    session.execute_write(self._create_passage_node, exam_id, data)

                # Create sequential relationships
                session.execute_write(self._create_next_relationships, exam_id, chunks_data)

            # Create cross-document relationships
            session.execute_write(self._create_cross_document_relationships)

        logger.info("Sync complete!")

        return {
            "status": "success",
            "exams_synced": len(exams),
            "total_chunks": len(chunks)
        }


def main():
    """CLI for syncing graph."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync Chroma to Neo4j graph")
    parser.add_argument("--reset", action="store_true", help="Reset Neo4j database first")
    parser.add_argument(
        "--llm", "--llm-enhanced",
        action="store_true",
        help="Enable LLM-enhanced graph extraction for additional entities and relationships"
    )
    args = parser.parse_args()

    settings = get_settings()

    if not settings.neo4j_enabled:
        print("ERROR: Neo4j is not enabled. Set NEO4J_ENABLED=true in .env")
        return

    # Check LLM requirement
    if args.llm and not settings.has_llm_provider:
        print("ERROR: LLM provider required for --llm mode. Set OPENAI_API_KEY in .env")
        return

    builder = Neo4jGraphBuilder()

    if args.reset:
        print("Resetting Neo4j database...")
        driver = builder._get_driver()
        with driver.session(database=settings.neo4j_database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Database reset complete.")

    # Choose sync method
    if args.llm:
        print("Running LLM-enhanced sync...")
        llm_client = create_llm_client()
        result = builder.sync_from_chroma_llm(llm_client)
    else:
        result = builder.sync_from_chroma()

    print(f"\nResult: {result}")

    builder.close()


if __name__ == "__main__":
    main()
