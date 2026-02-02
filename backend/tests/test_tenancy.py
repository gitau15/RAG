import pytest
from unittest.mock import Mock
from datetime import datetime
from app.tenancy.tenant_manager import TenantManager, Tenant, TenantUser, AccessLevel, TenantStatus
from app.tenancy.metadata_tagger import MetadataTagger, DocumentType, SensitivityLevel

class TestTenantManager:
    """Test tenant management functionality"""
    
    @pytest.fixture
    def tenant_manager(self):
        """Create tenant manager instance"""
        return TenantManager()
    
    def test_create_tenant(self, tenant_manager):
        """Test tenant creation"""
        tenant = tenant_manager.create_tenant(
            name="Test Company",
            description="Test tenant for RAG platform",
            admin_user_id="user_123"
        )
        
        assert tenant is not None
        assert tenant.name == "Test Company"
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.tenant_id.startswith("tenant_")
        
        # Verify admin user was added
        users = tenant_manager.get_tenant_users(tenant.tenant_id)
        assert len(users) == 1
        assert users[0].user_id == "user_123"
        assert users[0].access_level == AccessLevel.OWNER
    
    def test_get_tenant(self, tenant_manager):
        """Test tenant retrieval"""
        created_tenant = tenant_manager.create_tenant("Test Tenant")
        retrieved_tenant = tenant_manager.get_tenant(created_tenant.tenant_id)
        
        assert retrieved_tenant is not None
        assert retrieved_tenant.tenant_id == created_tenant.tenant_id
        assert retrieved_tenant.name == "Test Tenant"
    
    def test_list_tenants(self, tenant_manager):
        """Test tenant listing"""
        # Create multiple tenants
        tenant1 = tenant_manager.create_tenant("Company A", admin_user_id="user_1")
        tenant2 = tenant_manager.create_tenant("Company B", admin_user_id="user_2")
        
        # List all tenants (admin view)
        all_tenants = tenant_manager.list_tenants()
        assert len(all_tenants) >= 2
        
        # List user-specific tenants
        user1_tenants = tenant_manager.list_tenants("user_1")
        assert len(user1_tenants) == 1
        assert user1_tenants[0].tenant_id == tenant1.tenant_id
    
    def test_user_access_control(self, tenant_manager):
        """Test user access control"""
        tenant = tenant_manager.create_tenant("Access Test")
        tenant_manager.add_user_to_tenant(tenant.tenant_id, "user_member", AccessLevel.MEMBER)
        tenant_manager.add_user_to_tenant(tenant.tenant_id, "user_admin", AccessLevel.ADMIN)
        
        # Test access levels
        assert tenant_manager.check_user_access(tenant.tenant_id, "user_member", AccessLevel.VIEWER) == True
        assert tenant_manager.check_user_access(tenant.tenant_id, "user_member", AccessLevel.MEMBER) == True
        assert tenant_manager.check_user_access(tenant.tenant_id, "user_member", AccessLevel.ADMIN) == False
        
        assert tenant_manager.check_user_access(tenant.tenant_id, "user_admin", AccessLevel.ADMIN) == True
        assert tenant_manager.check_user_access(tenant.tenant_id, "user_admin", AccessLevel.OWNER) == False
    
    def test_collection_metadata(self, tenant_manager):
        """Test collection metadata management"""
        tenant = tenant_manager.create_tenant("Collection Test")
        
        # Create collection metadata
        collection_meta = tenant_manager.create_collection_metadata(
            collection_name="legal_documents",
            tenant_id=tenant.tenant_id,
            mode="judicial",
            created_by="user_123",
            tags=["legal", "court", "kenya"]
        )
        
        assert collection_meta is not None
        assert collection_meta.collection_name == "legal_documents"
        assert collection_meta.tenant_id == tenant.tenant_id
        assert collection_meta.mode == "judicial"
        assert "legal" in collection_meta.tags
        
        # List tenant collections
        collections = tenant_manager.list_tenant_collections(tenant.tenant_id)
        assert len(collections) == 1
        assert collections[0].collection_name == "legal_documents"
    
    def test_tenant_limits(self, tenant_manager):
        """Test tenant resource limits"""
        tenant = tenant_manager.create_tenant("Limits Test")
        
        # Test collection creation within limits
        for i in range(5):
            tenant_manager.create_collection_metadata(
                f"collection_{i}",
                tenant.tenant_id,
                "research",
                "user_123"
            )
        
        # Should be within default limits (100 collections)
        assert tenant_manager.validate_tenant_limits(tenant.tenant_id, "create_collection") == True

class TestMetadataTagger:
    """Test metadata tagging functionality"""
    
    @pytest.fixture
    def metadata_tagger(self):
        """Create metadata tagger instance"""
        return MetadataTagger()
    
    def test_document_type_classification(self, metadata_tagger):
        """Test document type classification"""
        # Legal document
        legal_content = "This court case v. Smith involves constitutional law provisions and judicial precedent."
        doc_type = metadata_tagger._classify_document_type(legal_content)
        assert doc_type == DocumentType.LEGAL
        
        # Commercial document
        commercial_content = "Product catalog with prices ranging from KES 1,000 to KES 5,000 with customer offers."
        doc_type = metadata_tagger._classify_document_type(commercial_content)
        assert doc_type == DocumentType.COMMERCIAL
        
        # General document
        general_content = "This is a general document with no specific domain indicators."
        doc_type = metadata_tagger._classify_document_type(general_content)
        assert doc_type == DocumentType.GENERAL
    
    def test_sensitivity_classification(self, metadata_tagger):
        """Test sensitivity level classification"""
        # Confidential document
        confidential_content = "CONFIDENTIAL: This document contains proprietary information and trade secrets."
        sensitivity = metadata_tagger._classify_sensitivity(confidential_content)
        assert sensitivity == SensitivityLevel.CONFIDENTIAL
        
        # Public document
        public_content = "This is a public announcement about company products."
        sensitivity = metadata_tagger._classify_sensitivity(public_content)
        assert sensitivity == SensitivityLevel.PUBLIC
    
    def test_industry_extraction(self, metadata_tagger):
        """Test industry/sector extraction"""
        content = "Medical research study on hospital patient treatment protocols and healthcare delivery systems."
        industries = metadata_tagger._extract_industries(content)
        
        assert "healthcare" in industries
        assert len(industries) >= 1
    
    def test_date_extraction(self, metadata_tagger):
        """Test date reference extraction"""
        content = "The contract was signed on January 15, 2024 and expires on 12/31/2025."
        dates = metadata_tagger._extract_dates(content)
        
        assert len(dates) >= 2
        assert any("2024" in date for date in dates)
        assert any("2025" in date for date in dates)
    
    def test_generate_document_metadata(self, metadata_tagger):
        """Test complete metadata generation"""
        content = "Legal case study v. Corporation XYZ involving contract law and commercial disputes."
        filename = "legal_case_study.pdf"
        
        metadata = metadata_tagger.generate_document_metadata(
            content=content,
            filename=filename,
            tenant_id="tenant_123",
            user_id="user_456",
            additional_tags=["important", "urgent"]
        )
        
        # Verify required fields
        assert "document_id" in metadata
        assert "filename" in metadata
        assert "tenant_id" in metadata
        assert "document_type" in metadata
        assert "tags" in metadata
        assert "sensitivity_level" in metadata
        
        # Verify content analysis
        assert metadata["document_type"] == "legal"
        assert "legal" in metadata["tags"]
        assert len(metadata["tags"]) >= 5  # Auto-tags plus additional tags
    
    def test_metadata_validation(self, metadata_tagger):
        """Test metadata validation"""
        # Complete metadata
        complete_metadata = {
            "document_id": "doc_123",
            "filename": "test.pdf",
            "tenant_id": "tenant_123",
            "upload_date": "2024-01-01",
            "tags": ["legal", "important", "case"],
            "document_type": "legal",
            "content_length": 1000
        }
        
        validation = metadata_tagger.validate_metadata_completeness(complete_metadata)
        assert validation["complete"] == True
        assert len(validation["missing_fields"]) == 0
        
        # Incomplete metadata
        incomplete_metadata = {
            "filename": "test.pdf"
            # Missing required fields
        }
        
        validation = metadata_tagger.validate_metadata_completeness(incomplete_metadata)
        assert validation["complete"] == False
        assert len(validation["missing_fields"]) > 0

if __name__ == "__main__":
    pytest.main([__file__])