import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from pathlib import Path

from app.privacy.data_protection import (
    PrivacyManager, DataSensitivity, ProcessingMode, PrivacyPolicy
)
from app.privacy.local_inference import (
    LocalInferenceEngine, InferenceRequest, InferenceResponse
)

class TestPrivacyManager:
    """Test privacy management functionality"""
    
    @pytest.fixture
    def privacy_manager(self):
        """Create privacy manager instance"""
        return PrivacyManager()
    
    def test_get_policy(self, privacy_manager):
        """Test policy retrieval"""
        default_policy = privacy_manager.get_policy("default")
        legal_policy = privacy_manager.get_policy("legal")
        
        assert isinstance(default_policy, PrivacyPolicy)
        assert default_policy.encryption_required == True
        assert legal_policy.data_retention_days == 730
        assert legal_policy.sensitivity_level == DataSensitivity.CONFIDENTIAL
    
    def test_calculate_data_hash(self, privacy_manager):
        """Test data hashing"""
        data = "test content"
        hash_sha256 = privacy_manager.calculate_data_hash(data, "sha256")
        hash_sha512 = privacy_manager.calculate_data_hash(data, "sha512")
        
        assert isinstance(hash_sha256, str)
        assert isinstance(hash_sha512, str)
        assert len(hash_sha256) == 64  # SHA256 hex length
        assert len(hash_sha512) == 128  # SHA512 hex length
        assert hash_sha256 != hash_sha512
    
    def test_anonymize_text(self, privacy_manager):
        """Test text anonymization"""
        test_text = "John Doe's email is john@example.com and phone 123-456-7890"
        anonymized = privacy_manager.anonymize_text(test_text)
        
        assert "[NAME]" in anonymized
        assert "[EMAIL]" in anonymized
        assert "[PHONE]" in anonymized
        assert "John Doe" not in anonymized
        assert "john@example.com" not in anonymized
    
    def test_encrypt_decrypt(self, privacy_manager):
        """Test encryption and decryption"""
        original_data = "sensitive information"
        tenant_id = "test_tenant"
        
        # Encrypt
        encrypted = privacy_manager.encrypt_data(original_data, tenant_id)
        assert encrypted != original_data
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = privacy_manager.decrypt_data(encrypted, tenant_id)
        assert decrypted == original_data
    
    def test_data_retention_check(self, privacy_manager):
        """Test data retention validation"""
        recent_date = datetime.now()
        old_date = datetime.now() - datetime.timedelta(days=400)
        
        default_policy = privacy_manager.get_policy("default")  # 365 days retention
        
        assert privacy_manager.check_data_retention(recent_date, default_policy) == True
        assert privacy_manager.check_data_retention(old_date, default_policy) == False
    
    def test_privacy_validation(self, privacy_manager):
        """Test privacy operation validation"""
        # Public data - no restrictions
        assert privacy_manager.validate_data_handling(
            "document", "read", DataSensitivity.PUBLIC
        ) == True
        
        # Restricted data - export should be blocked
        assert privacy_manager.validate_data_handling(
            "document", "export", DataSensitivity.RESTRICTED
        ) == False
        
        # Confidential data - public access should be blocked
        assert privacy_manager.validate_data_handling(
            "document", "public_access", DataSensitivity.CONFIDENTIAL
        ) == False

class TestLocalInferenceEngine:
    """Test local inference engine functionality"""
    
    @pytest.fixture
    def inference_engine(self):
        """Create inference engine with mocked dependencies"""
        with patch('app.privacy.local_inference.ollama_client'), \
             patch('app.privacy.local_inference.chroma_client'), \
             patch('app.privacy.local_inference.privacy_manager'):
            return LocalInferenceEngine()
    
    @pytest.fixture
    def sample_request(self):
        """Create sample inference request"""
        return InferenceRequest(
            query="What is the legal precedent?",
            collection_name="legal_docs",
            tenant_id="tenant_123",
            mode="judicial",
            processing_mode=ProcessingMode.ENCRYPTED,
            sensitivity_level=DataSensitivity.CONFIDENTIAL,
            user_id="user_456",
            metadata={"source": "web_interface"}
        )
    
    def test_validate_privacy_compliance(self, inference_engine, sample_request):
        """Test privacy compliance validation"""
        with patch.object(inference_engine.privacy, 'validate_data_handling', return_value=True):
            with patch.object(inference_engine.privacy, 'enforce_privacy_by_mode', 
                            return_value=ProcessingMode.ENCRYPTED):
                result = inference_engine._validate_privacy_compliance(sample_request)
                assert result == True
    
    def test_apply_data_protection(self, inference_engine, sample_request):
        """Test data protection application"""
        test_query = "John's sensitive legal query"
        
        async def run_test():
            protected_query = await inference_engine._apply_data_protection(test_query, sample_request)
            # Should contain anonymized content
            assert "John" not in protected_query or "[NAME]" in protected_query
        
        import asyncio
        asyncio.run(run_test())
    
    def test_protect_output(self, inference_engine, sample_request):
        """Test output protection"""
        sensitive_response = "The client's credit card is 1234-5678-9012-3456"
        protected = inference_engine._protect_output(sensitive_response, sample_request)
        
        assert "[CARD_NUMBER]" in protected
        assert "1234-5678-9012-3456" not in protected
    
    def test_filter_sensitive_output(self, inference_engine):
        """Test sensitive information filtering"""
        test_output = "Contact John Doe at john@example.com or call 555-123-4567"
        filtered = inference_engine._filter_sensitive_output(test_output)
        
        assert "[EMAIL]" in filtered
        assert "[PHONE]" in filtered
        assert "john@example.com" not in filtered
        assert "555-123-4567" not in filtered
    
    def test_generate_cache_key(self, inference_engine, sample_request):
        """Test cache key generation"""
        query = "test query"
        cache_key = inference_engine._generate_cache_key(query, sample_request)
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 64  # SHA256 hex length
    
    @patch('app.privacy.local_inference.Path')
    def test_cache_persistence(self, mock_path, inference_engine):
        """Test cache save/load functionality"""
        # Test save
        inference_engine.inference_cache = {"test_key": "test_value"}
        inference_engine._save_cache_to_disk()
        # Should not raise exception
        
        # Test load
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        with patch('builtins.open', mock_open(read_data='{"test_key": "test_value"}')):
            inference_engine._load_cache_from_disk()
            assert "test_key" in inference_engine.inference_cache

class TestInferenceDataStructures:
    """Test inference data structures"""
    
    def test_inference_request_creation(self):
        """Test InferenceRequest creation"""
        request = InferenceRequest(
            query="test query",
            collection_name="test_collection",
            tenant_id="tenant_123",
            mode="research",
            processing_mode=ProcessingMode.ONLINE,
            sensitivity_level=DataSensitivity.INTERNAL,
            user_id="user_456",
            metadata={"test": "value"}
        )
        
        assert request.query == "test query"
        assert request.tenant_id == "tenant_123"
        assert request.processing_mode == ProcessingMode.ONLINE
    
    def test_inference_response_creation(self):
        """Test InferenceResponse creation"""
        response = InferenceResponse(
            response="test response",
            processing_time_ms=150.5,
            tokens_used=10,
            model_used="mistral:7b",
            privacy_compliant=True,
            audit_trail={"test": "trail"},
            timestamp=datetime.now()
        )
        
        assert response.response == "test response"
        assert response.processing_time_ms == 150.5
        assert response.privacy_compliant == True

# Mock for file operations
def mock_open(*args, **kwargs):
    """Mock open function for testing"""
    return Mock()

if __name__ == "__main__":
    pytest.main([__file__])