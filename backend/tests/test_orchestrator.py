import pytest
from unittest.mock import Mock, patch
from app.orchestrator.rag_orchestrator import RAGOrchestrator
from app.orchestrator.mode_router import ModeRouter, ProcessingMode
from app.models.schemas import QueryRequest

class TestModeRouter:
    """Test mode routing functionality"""
    
    def test_determine_mode_judicial(self):
        """Test judicial mode detection"""
        router = ModeRouter()
        
        judicial_queries = [
            "What is the legal precedent for contract disputes?",
            "Find case law regarding liability",
            "Analyze constitutional provisions",
            "Research court decisions on compliance"
        ]
        
        for query in judicial_queries:
            mode = router.determine_mode(query)
            assert mode == ProcessingMode.JUDICIAL.value
    
    def test_determine_mode_sales(self):
        """Test sales mode detection"""
        router = ModeRouter()
        
        sales_queries = [
            "Show me product catalog with prices",
            "What are the available discounts?",
            "Process customer order",
            "Check inventory availability"
        ]
        
        for query in sales_queries:
            mode = router.determine_mode(query)
            assert mode == ProcessingMode.SALES.value
    
    def test_determine_mode_research(self):
        """Test research mode detection"""
        router = ModeRouter()
        
        research_queries = [
            "Analyze market trends",
            "Study user behavior patterns",
            "Research competitive landscape",
            "Investigate technical documentation"
        ]
        
        for query in research_queries:
            mode = router.determine_mode(query)
            assert mode == ProcessingMode.RESEARCH.value
    
    def test_get_mode_config(self):
        """Test mode configuration retrieval"""
        router = ModeRouter()
        
        judicial_config = router.get_mode_config(ProcessingMode.JUDICIAL.value)
        assert judicial_config["system_prompt_type"] == "judicial"
        assert judicial_config["citation_required"] == True
        assert judicial_config["temperature"] == 0.1
    
    def test_validate_mode_transition(self):
        """Test mode transition validation"""
        router = ModeRouter()
        
        # Valid transitions
        assert router.validate_mode_transition(ProcessingMode.JUDICIAL.value, ProcessingMode.RESEARCH.value) == True
        assert router.validate_mode_transition(ProcessingMode.SALES.value, ProcessingMode.RESEARCH.value) == True
        assert router.validate_mode_transition(ProcessingMode.RESEARCH.value, ProcessingMode.JUDICIAL.value) == True
        
        # Invalid transition (example)
        # This would depend on your business rules

class TestRAGOrchestrator:
    """Test RAG orchestrator functionality"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies"""
        with patch('app.orchestrator.rag_orchestrator.chroma_client'), \
             patch('app.orchestrator.rag_orchestrator.ollama_client'), \
             patch('app.orchestrator.rag_orchestrator.SystemPrompts'):
            return RAGOrchestrator()
    
    def test_validate_query_request_valid(self, orchestrator):
        """Test valid query request validation"""
        query_request = QueryRequest(
            query="Valid query",
            collection_name="test_collection",
            mode="judicial",
            k=4
        )
        
        assert orchestrator.validate_query_request(query_request) == True
    
    def test_validate_query_request_invalid(self, orchestrator):
        """Test invalid query request validation"""
        # Empty query
        invalid_request1 = QueryRequest(
            query="",
            collection_name="test_collection",
            mode="judicial"
        )
        assert orchestrator.validate_query_request(invalid_request1) == False
        
        # Invalid mode
        invalid_request2 = QueryRequest(
            query="Valid query",
            collection_name="test_collection",
            mode="invalid_mode"
        )
        assert orchestrator.validate_query_request(invalid_request2) == False
        
        # Invalid k value
        invalid_request3 = QueryRequest(
            query="Valid query",
            collection_name="test_collection",
            mode="judicial",
            k=-1
        )
        assert orchestrator.validate_query_request(invalid_request3) == False
    
    @patch('app.orchestrator.rag_orchestrator.chroma_client')
    def test_format_context(self, mock_chroma, orchestrator):
        """Test context formatting"""
        documents = [
            {
                "id": "doc1",
                "content": "First document content",
                "metadata": {
                    "source_file": "test1.pdf",
                    "chunk_index": 0
                }
            },
            {
                "id": "doc2", 
                "content": "Second document content",
                "metadata": {
                    "source_file": "test2.pdf", 
                    "chunk_index": 1
                }
            }
        ]
        
        context = orchestrator._format_context(documents)
        assert "First document content" in context
        assert "Second document content" in context
        assert "test1.pdf" in context
        assert "test2.pdf" in context

if __name__ == "__main__":
    pytest.main([__file__])