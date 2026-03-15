"""Tests for chunking system."""

import pytest
from pathlib import Path

from core.chunking import ChunkingEngine
from core.chunking_strategy import get_auto_strategy, ChunkingStrategy
from models.chunk import Chunk
from models.exam import Exam


class TestChunkingStrategy:
    """Tests for chunking strategy."""

    def test_get_auto_strategy(self):
        """Test auto strategy creation."""
        strategy = get_auto_strategy("Math")
        assert strategy is not None
        assert isinstance(strategy, ChunkingStrategy)
        assert strategy.subject == "Math"

    def test_strategy_has_prompt(self):
        """Test strategy has LLM prompt."""
        strategy = get_auto_strategy("SVT")
        prompt = strategy.get_llm_prompt()
        assert prompt is not None
        assert "MATHEMATIQUES" in prompt
        assert "SVT" in prompt
        assert "chunk_type" in prompt.lower()


class TestChunkModel:
    """Tests for chunk model."""

    def test_chunk_to_dict(self):
        """Test chunk to dict conversion."""
        chunk = Chunk(
            content="Test content",
            chunk_type="question_open",
            exam_file="test.pdf",
            page_num=1,
            subject="Math",
            year=2025,
            serie="SMP"
        )

        d = chunk.to_dict()
        assert d["content"] == "Test content"
        assert d["chunk_type"] == "question_open"
        assert d["subject"] == "Math"

    def test_chunk_to_text(self):
        """Test chunk to text for embedding."""
        chunk = Chunk(
            content="Solve for x",
            chunk_type="question_open",
            exam_file="test.pdf",
            page_num=1,
            subject="Math",
            year=2025,
            serie="SMP",
            section="Partie A",
            question_number="1"
        )

        text = chunk.to_text()
        assert "question_open" in text
        assert "Math" in text
        assert "Solve for x" in text

    def test_chunk_to_metadata_dict(self):
        """Test chunk to metadata dict for ChromaDB."""
        chunk = Chunk(
            content="Test",
            chunk_type="question_open",
            exam_file="test.pdf",
            page_num=1,
            subject="Math",
            year=2025,
            serie="SMP",
            has_formula=True
        )

        meta = chunk.to_metadata_dict()
        assert meta["chunk_type"] == "question_open"
        assert meta["subject"] == "Math"
        assert meta["has_formula"] == "True"


class TestExamModel:
    """Tests for exam model."""

    def test_exam_to_dict(self):
        """Test exam to dict conversion."""
        exam = Exam(
            file_path="test.pdf",
            subject="Math",
            year=2025,
            serie="SMP",
            page_count=5
        )

        d = exam.to_dict()
        assert d["subject"] == "Math"
        assert d["year"] == 2025
        assert d["serie"] == "SMP"
