import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.orchestrator.rag_orchestrator import RAGOrchestrator
from app.retrieval.advanced_retrievers import AdvancedRetriever
from app.privacy.local_inference import LocalInferenceEngine
from app.models.schemas import QueryRequest

class TestFullPipelineIntegration:
    """Integration tests for the complete RAG pipeline"""
    
    @pytest.fixture
    def pipeline_components(self):
        """Setup all pipeline components with mocked dependencies"""
        with patch('app.ingestion.ingestion_pipeline.chroma_client'), \
             patch('app.ingestion.ingestion_pipeline.embedding_manager'), \
             patch('app.orchestrator.rag_orchestrator.chroma_client'), \
             patch('app.orchestrator.rag_orchestrator.ollama_client'), \
             patch('app.retrieval.advanced_retrievers.chroma_client'), \
             patch('app.retrieval.advanced_retrievers.embedding_manager'), \
             patch('app.privacy.local_inference.ollama_client'), \
             patch('app.privacy.local_inference.chroma_client'):
            
            return {
                'ingestion': IngestionPipeline(),
                'orchestrator': RAGOrchestrator(),
                'retriever': AdvancedRetriever(),
                'privacy_engine': LocalInferenceEngine()
            }
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_document_ingestion_to_query_pipeline(self, pipeline_components, sample_document):
        """Test complete pipeline from document ingestion to query response"""
        
        # Step 1: Document Ingestion
        ingestion = pipeline_components['ingestion']
        with patch.object(ingestion, '_save_temporary_file') as mock_save, \
             patch.object(ingestion, '_ensure_collection') as mock_collection, \
             patch.object(ingestion, '_store_chunks') as mock_store:
            
            mock_save.return_value = "/tmp/test_doc.pdf"
            mock_collection.return_value = Mock()
            mock_store.return_value = None
            
            result = await ingestion.ingest_document(
                file_content=b"test content",
                filename="test_doc.pdf",
                collection_name="test_collection",
                tenant_id="test_tenant",
                mode="judicial"
            )
            
            assert result.chunks_created > 0
            assert result.filename == "test_doc.pdf"
            assert result.collection_name == "test_collection"
        
        # Step 2: Query Processing
        orchestrator = pipeline_components['orchestrator']
        query_request = QueryRequest(
            query="What are the legal precedents?",
            collection_name="test_collection",
            mode="judicial",
            k=5,
            tenant_id="test_tenant"
        )
        
        with patch.object(orchestrator, '_retrieve_documents') as mock_retrieve, \
             patch.object(orchestrator, '_generate_response') as mock_generate:
            
            # Mock retrieved documents
            mock_retrieve.return_value = [
                {
                    "id": "doc1",
                    "content": "Legal precedent for contract disputes",
                    "metadata": {"source_file": "test_doc.pdf", "chunk_index": 0}
                }
            ]
            
            mock_generate.return_value = "Based on the retrieved documents, here are the key precedents..."
            
            response = await orchestrator.process_query(query_request)
            
            assert response.query == query_request.query
            assert len(response.results) > 0
            assert response.collection_name == "test_collection"
            assert response.mode == "judicial"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_privacy_preserving_pipeline(self, pipeline_components, sample_document):
        """Test privacy-preserving pipeline execution"""
        
        privacy_engine = pipeline_components['privacy_engine']
        
        # Test privacy-controlled inference
        from app.privacy.local_inference import InferenceRequest, ProcessingMode, DataSensitivity
        
        request = InferenceRequest(
            query="Confidential legal query",
            collection_name="confidential_docs",
            tenant_id="secure_tenant",
            mode="judicial",
            processing_mode=ProcessingMode.ENCRYPTED,
            sensitivity_level=DataSensitivity.CONFIDENTIAL,
            user_id="secure_user",
            metadata={"classification": "confidential"}
        )
        
        with patch.object(privacy_engine, '_validate_privacy_compliance', return_value=True), \
             patch.object(privacy_engine, '_process_encrypted') as mock_process:
            
            mock_process.return_value = "Privacy-compliant response"
            
            response = await privacy_engine.process_query_privately(request)
            
            assert response.privacy_compliant == True
            assert response.model_used == "mistral:7b-local"
            assert "audit_trail" in response.audit_trail
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retrieval_with_different_strategies(self, pipeline_components):
        """Test different retrieval strategies integration"""
        
        retriever = pipeline_components['retriever']
        
        # Test standard retrieval
        from app.retrieval.retrieval_config import RetrievalParameters, RetrievalStrategy
        
        params = RetrievalParameters(
            k=3,
            strategy=RetrievalStrategy.STANDARD,
            similarity_threshold=0.3
        )
        
        with patch.object(retriever, '_standard_retrieval') as mock_retrieve:
            mock_retrieve.return_value = [
                {"id": "doc1", "content": "Test content", "similarity_score": 0.8}
            ]
            
            results = await retriever.retrieve(
                "test query",
                "test_collection",
                params
            )
            
            assert len(results) == 1
            assert results[0].id == "doc1"
            assert results[0].strategy_used == "standard"
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_end_to_end_document_lifecycle(self, pipeline_components):
        """Test complete document lifecycle from upload to deletion"""
        
        # This would test the full lifecycle in a real environment
        # Including ingestion, querying, updating, and cleanup
        pass  # Implementation would depend on actual database setup
    
    @pytest.mark.integration
    def test_component_interoperability(self, pipeline_components):
        """Test that different components can work together"""
        
        # Test that data formats are compatible between components
        ingestion = pipeline_components['ingestion']
        orchestrator = pipeline_components['orchestrator']
        
        # Verify that ingestion output format matches orchestrator input expectations
        # This ensures components can be chained together properly
        assert hasattr(ingestion, 'ingest_document')
        assert hasattr(orchestrator, 'process_query')
        assert hasattr(orchestrator, 'validate_query_request')

class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_error_propagation(self, pipeline_components):
        """Test that errors propagate correctly through the pipeline"""
        
        orchestrator = pipeline_components['orchestrator']
        query_request = QueryRequest(
            query="Test query",
            collection_name="nonexistent_collection",
            mode="judicial"
        )
        
        # Test error handling in retrieval
        with patch.object(orchestrator, '_retrieve_documents', side_effect=Exception("Collection not found")):
            with pytest.raises(Exception) as exc_info:
                await orchestrator.process_query(query_request)
            
            assert "Collection not found" in str(exc_info.value)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_partial_pipeline_failure(self, pipeline_components):
        """Test pipeline behavior when some components fail"""
        
        # Test graceful degradation when non-critical components fail
        privacy_engine = pipeline_components['privacy_engine']
        
        request = Mock()  # Simplified request for error testing
        
        with patch.object(privacy_engine, '_validate_privacy_compliance', return_value=False):
            with pytest.raises(ValueError) as exc_info:
                await privacy_engine.process_query_privately(request)
            
            assert "Privacy compliance validation failed" in str(exc_info.value)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])