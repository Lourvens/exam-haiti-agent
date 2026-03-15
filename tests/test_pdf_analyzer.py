"""Tests for PDF analyzer."""

import pytest
from pathlib import Path

from services.pdf_analyzer import PDFAnalyzer, analyze_pdf


class TestPDFAnalyzer:
    """Tests for PDF analyzer."""

    @pytest.fixture
    def pdf_path(self) -> Path:
        """Path to test PDF."""
        return Path("data/pdfs/Math-NS4-2025-LLA-Distance.pdf")

    def test_analyze_pdf(self, pdf_path: Path):
        """Test PDF analysis returns valid result."""
        result = analyze_pdf(pdf_path)

        assert result is not None
        assert result.file_path == str(pdf_path)
        assert result.page_count > 0
        assert result.metadata.subject == "Math"
        assert result.metadata.year == 2025

    def test_metadata_extraction(self, pdf_path: Path):
        """Test metadata extraction."""
        analyzer = PDFAnalyzer(pdf_path)
        result = analyzer.analyze()

        assert result.metadata.subject == "Math"
        assert result.metadata.year == 2025
        assert result.metadata.serie == "LLA"

    def test_layout_detection(self, pdf_path: Path):
        """Test layout detection."""
        analyzer = PDFAnalyzer(pdf_path)
        result = analyzer.analyze()

        assert len(result.layouts) > 0
        assert result.layouts[0].page_num == 0


class TestMultiplePDFs:
    """Tests for analyzing multiple PDFs."""

    def test_analyze_svt(self):
        """Test SVT PDF analysis."""
        result = analyze_pdf("data/pdfs/SVT_2021_SES-SMP_Gamete-1.pdf")

        assert result is not None
        assert result.metadata.subject == "SVT"
        assert result.metadata.year == 2021

    def test_analyze_chimie(self):
        """Test Chimie PDF analysis."""
        result = analyze_pdf("data/pdfs/Chimie-2023-SMP-SVT-covalente.pdf")

        assert result is not None
        # Note: This PDF contains both SVT and Chimie in content
        assert result.metadata.subject in ["Chimie", "SVT"]
        assert result.metadata.year == 2023

    def test_analyze_hist_geo(self):
        """Test Hist-Geo PDF analysis."""
        result = analyze_pdf("data/pdfs/Hist-Geo_2022_LLA-SES_Dessalines.pdf")

        assert result is not None
        assert result.metadata.subject == "Hist-Geo"
        assert result.metadata.year == 2022
