import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, Any
import tempfile
import os
from datetime import datetime

# Test fixtures for common test scenarios

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return {
        "content": "This is a sample legal document about contract law and judicial precedent. It contains important case law references and statutory provisions that are relevant for legal research purposes.",
        "metadata": {
            "filename": "sample_legal_doc.pdf",
            "file_size": 1024000,
            "upload_date": datetime.now().isoformat(),
            "document_type": "legal",
            "sensitivity_level": "confidential",
            "tenant_id": "test_tenant_123",
            "mode": "judicial",
            "tags": ["legal", "contract", "case-law"],
            "page_count": 25
        }
    }

@pytest.fixture
def sample_query():
    """Sample query for testing"""
    return "What are the key legal precedents for contract disputes?"

@pytest.fixture
def sample_tenant():
    """Sample tenant data"""
    return {
        "tenant_id": "test_tenant_123",
        "name": "Test Legal Firm",
        "description": "Sample tenant for testing",
        "status": "active",
        "limits": {
            "max_collections": 50,
            "max_documents_per_collection": 5000,
            "max_storage_mb": 5000
        }
    }

@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection"""
    collection = Mock()
    collection.query.return_value = {
        'ids': [['doc1', 'doc2', 'doc3']],
        'documents': [[
            'Legal precedent for contract disputes section 1',
            'Case law regarding liability and damages section 2', 
            'Statutory provisions for contract enforcement section 3'
        ]],
        'metadatas': [[
            {'source': 'legal_doc_1.pdf', 'chunk_index': 0},
            {'source': 'legal_doc_2.pdf', 'chunk_index': 1},
            {'source': 'legal_doc_3.pdf', 'chunk_index': 2}
        ]],
        'distances': [[0.2, 0.3, 0.4]]
    }
    collection.count.return_value = 3
    return collection

@pytest.fixture
def mock_ollama_response():
    """Mock Ollama LLM response"""
    return "Based on the retrieved legal documents, the key precedents for contract disputes include established case law regarding breach of contract, liability assessment, and statutory enforcement provisions. Courts typically consider the terms of the agreement, damages calculation, and precedent cases when making decisions."

@pytest.fixture
def temp_test_directory():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    env_vars = {
        'ENVIRONMENT': 'test',
        'CHROMA_DB_PATH': '/tmp/test_chroma',
        'OLLAMA_HOST': 'http://localhost:11434',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def sample_payment_data():
    """Sample payment data for testing"""
    return {
        "user_id": "test_user_123",
        "amount": 499.0,
        "phone_number": "254712345678",
        "product_info": {
            "name": "Premium Subscription",
            "category": "subscription",
            "price": 499.0
        },
        "collection_name": "premium_docs"
    }

@pytest.fixture
def sample_citation_data():
    """Sample citation data for testing"""
    return {
        "citation_id": "cit_12345678",
        "source_document": "Contract Law Case v. Smith",
        "page_number": 45,
        "section": "2.3",
        "content_snippet": "The court held that...",
        "relevance_score": 0.85
    }

@pytest.fixture
def sample_retrieval_params():
    """Sample retrieval parameters"""
    return {
        "k": 5,
        "similarity_threshold": 0.3,
        "strategy": "contextual",
        "depth": "moderate",
        "diversity_factor": 0.3
    }

# Mock decorators for external services
def mock_chroma_client(func):
    """Decorator to mock ChromaDB client"""
    def wrapper(*args, **kwargs):
        with patch('app.vectorstore.chroma_client') as mock_client:
            mock_client.get_collection.return_value = Mock()
            return func(*args, **kwargs)
    return wrapper

def mock_ollama_client(func):
    """Decorator to mock Ollama client"""
    def wrapper(*args, **kwargs):
        with patch('app.llm.ollama_client') as mock_client:
            mock_client.generate.return_value = "Test response"
            mock_client.chat.return_value = "Test chat response"
            return func(*args, **kwargs)
    return wrapper

def mock_daraja_client(func):
    """Decorator to mock Daraja client"""
    def wrapper(*args, **kwargs):
        with patch('app.payments.daraja_client') as mock_client:
            mock_client.initiate_stk_push.return_value = {
                "success": True,
                "checkout_request_id": "test_checkout_123"
            }
            return func(*args, **kwargs)
    return wrapper

# Test utilities
class TestUtils:
    """Utility methods for tests"""
    
    @staticmethod
    def assert_response_structure(response: Dict[str, Any], required_fields: list):
        """Assert that response contains required fields"""
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
    
    @staticmethod
    def assert_valid_uuid(uuid_string: str):
        """Assert that string is a valid UUID format"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, uuid_string), f"Invalid UUID format: {uuid_string}"
    
    @staticmethod
    def assert_iso_datetime(datetime_string: str):
        """Assert that string is valid ISO datetime format"""
        try:
            datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid ISO datetime format: {datetime_string}")

# Global test utilities
test_utils = TestUtils()