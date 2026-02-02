import pytest
from datetime import datetime
from app.auth.auth_models import (
    User, UserCreate, UserLogin, UserLoginResponse, TokenData,
    UserRole, UserStatus, PermissionScope, RolePermissions, ROLE_PERMISSIONS
)

class TestAuthModels:
    def test_user_role_enum(self):
        """Test UserRole enum values"""
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.TENANT_ADMIN.value == "tenant_admin"
        assert UserRole.TENANT_MEMBER.value == "tenant_member"
        assert UserRole.VIEWER.value == "viewer"
        
        # Test all roles exist
        all_roles = list(UserRole)
        assert len(all_roles) == 4

    def test_user_status_enum(self):
        """Test UserStatus enum values"""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.PENDING.value == "pending"
        
        # Test all statuses exist
        all_statuses = list(UserStatus)
        assert len(all_statuses) == 4

    def test_permission_scope_enum(self):
        """Test PermissionScope enum values"""
        # Test some key permissions
        assert PermissionScope.DOCUMENT_READ.value == "document:read"
        assert PermissionScope.DOCUMENT_WRITE.value == "document:write"
        assert PermissionScope.DOCUMENT_DELETE.value == "document:delete"
        assert PermissionScope.SYSTEM_ADMIN.value == "system:admin"
        
        # Test that we have all expected permission categories
        all_permissions = list(PermissionScope)
        assert len(all_permissions) > 10  # Should have many permissions

    def test_role_permissions_mapping(self):
        """Test role to permissions mapping"""
        # Test SUPER_ADMIN has all permissions
        super_admin_perms = ROLE_PERMISSIONS[UserRole.SUPER_ADMIN].permissions
        assert len(super_admin_perms) == len(list(PermissionScope))
        
        # Test VIEWER has limited permissions
        viewer_perms = ROLE_PERMISSIONS[UserRole.VIEWER].permissions
        assert len(viewer_perms) < len(list(PermissionScope))
        assert PermissionScope.DOCUMENT_READ in viewer_perms
        assert PermissionScope.DOCUMENT_WRITE not in viewer_perms
        
        # Test TENANT_ADMIN has appropriate permissions
        tenant_admin_perms = ROLE_PERMISSIONS[UserRole.TENANT_ADMIN].permissions
        assert PermissionScope.TENANT_ADMIN in tenant_admin_perms
        assert PermissionScope.SYSTEM_ADMIN not in tenant_admin_perms

    def test_user_model_creation(self):
        """Test User model creation"""
        user = User(
            user_id="user_123",
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password_hash="hashed_password",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE
        )
        
        assert user.user_id == "user_123"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.role == UserRole.VIEWER
        assert user.status == UserStatus.ACTIVE
        assert isinstance(user.created_at, datetime)
        assert user.tenant_memberships == []

    def test_user_create_model(self):
        """Test UserCreate model"""
        user_create = UserCreate(
            email="newuser@example.com",
            username="newuser",
            full_name="New User",
            password="password123",
            role=UserRole.TENANT_MEMBER
        )
        
        assert user_create.email == "newuser@example.com"
        assert user_create.username == "newuser"
        assert user_create.full_name == "New User"
        assert user_create.password == "password123"
        assert user_create.role == UserRole.TENANT_MEMBER
        assert user_create.tenant_id is None

    def test_user_login_model(self):
        """Test UserLogin model"""
        user_login = UserLogin(
            email="test@example.com",
            password="password123"
        )
        
        assert user_login.email == "test@example.com"
        assert user_login.password == "password123"

    def test_token_data_model(self):
        """Test TokenData model"""
        token_data = TokenData(
            user_id="user_123",
            username="testuser",
            role=UserRole.VIEWER,
            tenant_id="tenant_456",
            scopes=["document:read", "collection:read"]
        )
        
        assert token_data.user_id == "user_123"
        assert token_data.username == "testuser"
        assert token_data.role == UserRole.VIEWER
        assert token_data.tenant_id == "tenant_456"
        assert "document:read" in token_data.scopes
        assert "collection:read" in token_data.scopes

    def test_role_permissions_model(self):
        """Test RolePermissions model"""
        permissions = [PermissionScope.DOCUMENT_READ, PermissionScope.COLLECTION_READ]
        role_permissions = RolePermissions(
            role=UserRole.VIEWER,
            permissions=permissions,
            description="Viewer role with read permissions"
        )
        
        assert role_permissions.role == UserRole.VIEWER
        assert role_permissions.permissions == permissions
        assert role_permissions.description == "Viewer role with read permissions"