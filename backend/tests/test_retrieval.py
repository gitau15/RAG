import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.retrieval.retrieval_config import (
    RetrievalConfigManager, RetrievalParameters, 
    RetrievalStrategy, SearchDepth
)
from app.retrieval.advanced_retrievers import AdvancedRetriever, RetrievedDocument

class TestRetrievalConfigManager:
    """Test retrieval configuration management"""
    
    @pytest.fixture
    def config_manager(self):
        """Create config manager instance"""
        return RetrievalConfigManager()
    
    def test_get_preset(self, config_manager):
        """Test preset retrieval"""
        legal_config = config_manager.get_preset("legal_research")
        assert legal_config is not None
        assert legal_config.k == 8
        assert legal_config.strategy == RetrievalStrategy.CONTEXTUAL
        assert legal_config.depth == SearchDepth.DEEP
    
    def test_create_custom_config(self, config_manager):
        """Test custom configuration creation"""
        custom_config = config_manager.create_custom_config(
            k=10,
            depth=SearchDepth.EXHAUSTIVE,
            strategy=RetrievalStrategy.MULTI_QUERY,
            similarity_threshold=0.25
        )
        
        assert custom_config.k == 10
        assert custom_config.depth == SearchDepth.EXHAUSTIVE
        assert custom_config.strategy == RetrievalStrategy.MULTI_QUERY
        assert custom_config.similarity_threshold == 0.25
    
    def test_adjust_depth(self, config_manager):
        """Test depth adjustment"""
        params = RetrievalParameters(k=4, depth=SearchDepth.SHALLOW)
        adjusted_params = config_manager.adjust_depth(params, SearchDepth.DEEP)
        
        assert adjusted_params.k == 10
        assert adjusted_params.depth == SearchDepth.DEEP
        assert adjusted_params.similarity_threshold == 0.2
        assert adjusted_params.diversity_factor == 0.5
    
    def test_strategy_recommendation(self, config_manager):
        """Test strategy recommendation"""
        # Legal mode recommendation
        strategy = config_manager.get_strategy_recommendation("legal case law", "judicial")
        assert strategy == RetrievalStrategy.CONTEXTUAL
        
        # Sales mode recommendation
        strategy = config_manager.get_strategy_recommendation("product information", "sales")
        assert strategy == RetrievalStrategy.STANDARD
        
        # Multi-query recommendation
        strategy = config_manager.get_strategy_recommendation("compare products", "research")
        assert strategy == RetrievalStrategy.MULTI_QUERY
    
    def test_optimize_for_latency(self, config_manager):
        """Test latency optimization"""
        params = RetrievalParameters(
            k=12,
            strategy=RetrievalStrategy.MULTI_QUERY,
            diversity_factor=0.7
        )
        
        optimized = config_manager.optimize_for_latency(params)
        
        assert optimized.k <= 6  # Reduced k
        assert optimized.strategy == RetrievalStrategy.STANDARD  # Simplified strategy
        assert optimized.diversity_factor <= 0.4  # Reduced diversity
    
    def test_validate_parameters(self, config_manager):
        """Test parameter validation"""
        # Valid parameters
        valid_params = RetrievalParameters(k=5, similarity_threshold=0.3)
        validation = valid_params.validate_parameters()
        assert validation["valid"] == True
        assert len(validation["issues"]) == 0
        
        # Invalid parameters
        invalid_params = RetrievalParameters(k=100, similarity_threshold=1.5)
        validation = invalid_params.validate_parameters()
        assert validation["valid"] == False
        assert len(validation["issues"]) > 0

class TestAdvancedRetriever:
    """Test advanced retrieval strategies"""
    
    @pytest.fixture
    def retriever(self):
        """Create retriever with mocked dependencies"""
        with patch('app.retrieval.advanced_retrievers.chroma_client'), \
             patch('app.retrieval.advanced_retrievers.embedding_manager'):
            return AdvancedRetriever()
    
    @pytest.fixture
    def sample_params(self):
        """Create sample retrieval parameters"""
        return RetrievalParameters(
            k=5,
            depth=SearchDepth.MODERATE,
            strategy=RetrievalStrategy.STANDARD,
            similarity_threshold=0.3
        )
    
    @patch('app.retrieval.advanced_retrievers.chroma_client')
    def test_standard_retrieval(self, mock_chroma, retriever, sample_params):
        """Test standard retrieval"""
        # Mock ChromaDB response
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'ids': [['doc1', 'doc2', 'doc3']],
            'documents': [['Content 1', 'Content 2', 'Content 3']],
            'metadatas': [[{'source': 'test1'}, {'source': 'test2'}, {'source': 'test3'}]],
            'distances': [[0.2, 0.3, 0.4]]
        }
        mock_chroma.get_collection.return_value = mock_collection
        
        async def run_test():
            results = await retriever._standard_retrieval(
                "test query", 
                "test_collection", 
                sample_params
            )
            
            assert len(results) == 3
            assert results[0]['id'] == 'doc1'
            assert results[0]['similarity_score'] == 0.8  # 1 - 0.2
        
        import asyncio
        asyncio.run(run_test())
    
    def test_generate_query_variations(self, retriever):
        """Test query variation generation"""
        variations = retriever._generate_query_variations("test query", 3)
        assert len(variations) == 3
        assert "test query" in variations
        assert "What is test query?" in variations
        assert "Explain test query" in variations
    
    def test_deduplicate_results(self, retriever):
        """Test result deduplication"""
        results = [
            {'id': 'doc1', 'similarity_score': 0.9},
            {'id': 'doc2', 'similarity_score': 0.8},
            {'id': 'doc1', 'similarity_score': 0.7},  # Duplicate
            {'id': 'doc3', 'similarity_score': 0.6}
        ]
        
        deduplicated = retriever._deduplicate_results(results)
        assert len(deduplicated) == 3
        # Should keep highest scoring duplicate
        assert deduplicated[0]['id'] == 'doc1'
        assert deduplicated[0]['similarity_score'] == 0.9
    
    def test_merge_adjacent_chunks(self, retriever):
        """Test chunk merging for context"""
        main_doc = {
            'content': 'Main content',
            'metadata': {'chunk_index': 5}
        }
        
        adjacent_results = {
            'ids': [['prev1', 'prev2', 'next1']],
            'documents': [['Previous 1', 'Previous 2', 'Next 1']],
            'metadatas': [[
                {'chunk_index': 3},
                {'chunk_index': 4},
                {'chunk_index': 6}
            ]]
        }
        
        merged_content = retriever._merge_adjacent_chunks(main_doc, adjacent_results, 2)
        assert 'Previous 2' in merged_content
        assert 'Main content' in merged_content
        assert 'Next 1' in merged_content
    
    def test_combine_sparse_dense_results(self, retriever):
        """Test hybrid retrieval combination"""
        dense_results = [
            {'id': 'doc1', 'similarity_score': 0.8},
            {'id': 'doc2', 'similarity_score': 0.6}
        ]
        
        sparse_results = {
            'ids': ['doc2', 'doc3'],
            'documents': ['Content 2', 'Content 3'],
            'metadatas': [{'source': 'test2'}, {'source': 'test3'}]
        }
        
        combined = retriever._combine_sparse_dense_results(
            dense_results, sparse_results, 0.3, 0.7
        )
        
        assert len(combined) == 3
        # doc2 should have combined score
        doc2_scores = [doc['similarity_score'] for doc in combined if doc['id'] == 'doc2']
        assert len(doc2_scores) == 1
        assert doc2_scores[0] > 0.6  # Should be higher than original dense score

class TestRetrievedDocument:
    """Test retrieved document data structure"""
    
    def test_retrieved_document_creation(self):
        """Test RetrievedDocument creation"""
        doc = RetrievedDocument(
            id="test_doc",
            content="Test content",
            metadata={"source": "test.pdf"},
            similarity_score=0.85,
            retrieval_rank=1,
            strategy_used="standard",
            retrieval_timestamp=datetime.now(),
            processing_time_ms=150.5
        )
        
        assert doc.id == "test_doc"
        assert doc.content == "Test content"
        assert doc.similarity_score == 0.85
        assert doc.retrieval_rank == 1
        assert doc.strategy_used == "standard"

if __name__ == "__main__":
    pytest.main([__file__])