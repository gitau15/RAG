import pytest
from unittest.mock import Mock
from datetime import datetime
from app.citation.citation_engine import CitationEngine, LegalCitation, CitationContext
from app.citation.legal_formatter import LegalFormatter, CitationValidator

class TestCitationEngine:
    """Test citation engine functionality"""
    
    @pytest.fixture
    def citation_engine(self):
        """Create citation engine instance"""
        return CitationEngine()
    
    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing"""
        return {
            "id": "doc_123",
            "content": "This is a sample legal document content with case citation v. Smith and page numbers on page 45.",
            "metadata": {
                "source_file": "sample_case.pdf",
                "file_path": "/documents/sample_case.pdf",
                "chunk_index": 2,
                "page_number": 45,
                "section": "2.3",
                "parser_used": "unstructured",
                "mode": "judicial"
            },
            "distance": 0.15
        }
    
    def test_extract_page_number(self, citation_engine, sample_document):
        """Test page number extraction"""
        content = sample_document["content"]
        metadata = sample_document["metadata"]
        
        page_number = citation_engine._extract_page_number(content, metadata)
        assert page_number == 45
    
    def test_extract_section(self, citation_engine, sample_document):
        """Test section extraction"""
        content = sample_document["content"]
        metadata = sample_document["metadata"]
        
        section = citation_engine._extract_section(content, metadata)
        # Should find "2.3" from metadata
        assert section == "2.3"
    
    def test_create_content_snippet(self, citation_engine):
        """Test content snippet creation"""
        long_content = "This is a very long content that exceeds the maximum length limit and should be truncated appropriately to create a meaningful snippet for citation purposes."
        
        snippet = citation_engine._create_content_snippet(long_content, max_length=100)
        assert len(snippet) <= 103  # 100 + "..."
        assert snippet.endswith("...")
    
    def test_calculate_relevance_score(self, citation_engine, sample_document):
        """Test relevance score calculation"""
        query = "legal document case citation"
        score = citation_engine._calculate_relevance_score(sample_document, query)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_create_citation_from_document(self, citation_engine, sample_document):
        """Test citation creation from document"""
        context = CitationContext(
            query="legal case",
            mode="judicial",
            collection_name="test_collection",
            tenant_id="test_tenant",
            retrieved_documents=[sample_document]
        )
        
        citation = citation_engine._create_citation_from_document(sample_document, context, 0)
        
        assert isinstance(citation, LegalCitation)
        assert citation.source_document == "sample_case.pdf"
        assert citation.page_number == 45
        assert citation.section == "2.3"
        assert citation.chunk_id == "doc_123"
    
    def test_generate_citations(self, citation_engine, sample_document):
        """Test full citation generation"""
        context = CitationContext(
            query="legal case",
            mode="judicial",
            collection_name="test_collection",
            tenant_id="test_tenant",
            retrieved_documents=[sample_document]
        )
        
        citations = citation_engine.generate_citations(context)
        
        assert len(citations) == 1
        assert isinstance(citations[0], LegalCitation)
        assert citations[0].source_document == "sample_case.pdf"

class TestLegalFormatter:
    """Test legal citation formatting"""
    
    @pytest.fixture
    def sample_citation(self):
        """Create sample citation for testing"""
        return LegalCitation(
            citation_id="cit_12345678",
            source_document="Smith v. Jones",
            source_file="/documents/smith_v_jones.pdf",
            page_number=45,
            section="2.3",
            paragraph="a",
            chunk_id="chunk_123",
            content_snippet="The court held that...",
            relevance_score=0.85,
            timestamp=datetime.now()
        )
    
    def test_format_citation_apa(self, sample_citation):
        """Test APA citation formatting"""
        formatted = LegalFormatter.format_citation_apa(sample_citation)
        assert "Smith v. Jones" in formatted
        assert "§ 2.3" in formatted
        assert "p. 45" in formatted
    
    def test_format_citation_bluebook(self, sample_citation):
        """Test Bluebook citation formatting"""
        formatted = LegalFormatter.format_citation_bluebook(sample_citation)
        assert "Smith v. Jones" in formatted
        assert "45" in formatted
    
    def test_format_citation_oscola(self, sample_citation):
        """Test OSCOLA citation formatting"""
        formatted = LegalFormatter.format_citation_oscola(sample_citation)
        assert "[Smith v. Jones]" in formatted
        assert "[2.3]" in formatted
    
    def test_format_citation_chicago(self, sample_citation):
        """Test Chicago citation formatting"""
        formatted = LegalFormatter.format_citation_chicago(sample_citation)
        assert '"Smith v. Jones"' in formatted
        assert "§ 2.3" in formatted

class TestCitationValidator:
    """Test citation validation functionality"""
    
    @pytest.fixture
    def complete_citation(self):
        """Create complete citation for testing"""
        return LegalCitation(
            citation_id="cit_complete",
            source_document="Complete Case",
            source_file="/documents/complete.pdf",
            page_number=10,
            section="5.2",
            paragraph="b",
            chunk_id="chunk_456",
            content_snippet="This is a complete citation with all required information.",
            relevance_score=0.9,
            timestamp=datetime.now()
        )
    
    @pytest.fixture
    def incomplete_citation(self):
        """Create incomplete citation for testing"""
        return LegalCitation(
            citation_id="cit_incomplete",
            source_document="Unknown",
            source_file="",
            page_number=None,
            section=None,
            paragraph=None,
            chunk_id="chunk_789",
            content_snippet="Short",
            relevance_score=0.2,
            timestamp=datetime.now()
        )
    
    def test_validate_complete_citation(self, complete_citation):
        """Test validation of complete citation"""
        result = CitationValidator.validate_citation_completeness(complete_citation)
        
        assert result["valid"] == True
        assert result["completeness_score"] >= 0.8
        assert len(result["issues"]) == 0
    
    def test_validate_incomplete_citation(self, incomplete_citation):
        """Test validation of incomplete citation"""
        result = CitationValidator.validate_citation_completeness(incomplete_citation)
        
        assert result["valid"] == False
        assert result["completeness_score"] < 0.5
        assert len(result["issues"]) > 0
        assert "Missing source document name" in result["issues"]

if __name__ == "__main__":
    pytest.main([__file__])