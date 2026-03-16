"""LLM-based graph extraction schemas for Neo4j."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Single entity extracted by LLM."""
    id: str = Field(description="Unique ID for the entity")
    type: str = Field(description="Entity type: exam, section, question, subquestion, concept, topic")
    name: str = Field(description="Human-readable name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class Relation(BaseModel):
    """Relationship between entities."""
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    relation_type: str = Field(description="Type: same_topic, prerequisite, related_concept, difficulty_related")


class ExtractionResult(BaseModel):
    """LLM extraction output for a chunk or section."""
    entities: List[Entity] = Field(default_factory=list, description="Entities extracted from content")
    relations: List[Relation] = Field(default_factory=list, description="Relationships between entities")


class CrossReferenceExtraction(BaseModel):
    """LLM extraction of cross-document relationships."""
    relations: List[Relation] = Field(
        default_factory=list,
        description="Cross-document relationships discovered by LLM"
    )
    insights: List[str] = Field(
        default_factory=list,
        description="Key insights about connections between questions/exams"
    )


class LLMGraphConfig(BaseModel):
    """Configuration for LLM-enhanced graph building."""
    extract_concepts: bool = True
    extract_topics: bool = True
    find_prerequisites: bool = True
    find_related_concepts: bool = True
    cross_document_relations: bool = True
