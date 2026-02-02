import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import jwt

from app.auth.auth_service import AuthService
from app.auth.auth_models import (
    User, UserCreate, UserLogin, UserRole, UserStatus, PermissionScope
)

class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance for testing"""
        return AuthService()

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return UserCreate(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password="password123",
            role=UserRole.VIEWER
        )

    def test_initialize_default_users(self, auth_service):
        """Test that default users are initialized"""
        # Check that admin user exists
        admin_user = auth_service.get_user_by_email("admin@rag-platform.com")
        assert admin_user is not None
        assert admin_user.role == UserRole.SUPER_ADMIN
        assert admin_user.status == UserStatus.ACTIVE

    def test_hash_password(self, auth_service):
        """Test password hashing"""
        password = "test_password_123"
        hashed = auth_service._hash_password(password)
        
        # Hashed password should be different from original
        assert hashed != password
        # Hashed password should be a string
        assert isinstance(hashed, str)
        # Hashed password should be longer than original
        assert len(hashed) > len(password)

    def test_verify_password(self, auth_service):
        """Test password verification"""
        password = "test_password_123"
        hashed = auth_service._hash_password(password)
        
        # Should verify correct password
        assert auth_service._verify_password(password, hashed) is True
        
        # Should not verify wrong password
        assert auth_service._verify_password("wrong_password", hashed) is False

    def test_generate_user_id(self, auth_service):
        """Test user ID generation"""
        user_id1 = auth_service._generate_user_id()
        user_id2 = auth_service._generate_user_id()
        
        # Should generate unique IDs
        assert user_id1.startswith("user_")
        assert user_id2.startswith("user_")
        assert user_id1 != user_id2

    def test_create_user_success(self, auth_service, sample_user_data):
        """Test successful user creation"""
        user = auth_service.create_user(sample_user_data)
        
        assert user is not None
        assert user.email == sample_user_data.email
        assert user.username == sample_user_data.username
        assert user.full_name == sample_user_data.full_name
        assert user.role == sample_user_data.role
        assert user.status == UserStatus.PENDING
        # Password should be hashed
        assert user.password_hash != sample_user_data.password

    def test_create_user_duplicate_email(self, auth_service, sample_user_data):
        """Test creating user with duplicate email fails"""
        # Create first user
        auth_service.create_user(sample_user_data)
        
        # Try to create user with same email
        with pytest.raises(ValueError, match="User with this email or username already exists"):
            auth_service.create_user(sample_user_data)

    def test_create_user_duplicate_username(self, auth_service, sample_user_data):
        """Test creating user with duplicate username fails"""
        # Create first user
        auth_service.create_user(sample_user_data)
        
        # Create second user with different email but same username
        second_user_data = UserCreate(
            email="different@example.com",
            username=sample_user_data.username,  # Same username
            full_name="Different User",
            password="different123"
        )
        
        with pytest.raises(ValueError, match="User with this email or username already exists"):
            auth_service.create_user(second_user_data)

    def test_create_user_with_tenant_assignment(self, auth_service, sample_user_data):
        """Test creating user with automatic tenant assignment"""
        tenant_id = "tenant_123"
        user_data_with_tenant = UserCreate(
            email="tenant_user@example.com",
            username="tenant_user",
            full_name="Tenant User",
            password="password123",
            tenant_id=tenant_id
        )
        
        user = auth_service.create_user(user_data_with_tenant)
        assert tenant_id in user.tenant_memberships

    def test_create_superuser_is_active(self, auth_service):
        """Test that super admin users are created as active"""
        admin_user_data = UserCreate(
            email="admin@test.com",
            username="admin_user",
            full_name="Admin User",
            password="admin123",
            role=UserRole.SUPER_ADMIN
        )
        
        user = auth_service.create_user(admin_user_data)
        assert user.status == UserStatus.ACTIVE

    def test_authenticate_user_success(self, auth_service, sample_user_data):
        """Test successful user authentication"""
        # Create user first
        user = auth_service.create_user(sample_user_data)
        # Activate user for authentication
        user.status = UserStatus.ACTIVE
        
        # Test authentication
        user_login = UserLogin(
            email=sample_user_data.email,
            password=sample_user_data.password
        )
        
        authenticated_user = auth_service.authenticate_user(user_login)
        assert authenticated_user is not None
        assert authenticated_user.user_id == user.user_id
        assert authenticated_user.last_login is not None

    def test_authenticate_user_wrong_password(self, auth_service, sample_user_data):
        """Test authentication with wrong password"""
        # Create user first
        user = auth_service.create_user(sample_user_data)
        user.status = UserStatus.ACTIVE
        
        # Test authentication with wrong password
        user_login = UserLogin(
            email=sample_user_data.email,
            password="wrong_password"
        )
        
        authenticated_user = auth_service.authenticate_user(user_login)
        assert authenticated_user is None

    def test_authenticate_user_inactive_user(self, auth_service, sample_user_data):
        """Test authentication with inactive user"""
        # Create user (status will be PENDING by default)
        user = auth_service.create_user(sample_user_data)
        # User is PENDING, should not authenticate
        
        user_login = UserLogin(
            email=sample_user_data.email,
            password=sample_user_data.password
        )
        
        authenticated_user = auth_service.authenticate_user(user_login)
        assert authenticated_user is None

    def test_authenticate_user_nonexistent_user(self, auth_service):
        """Test authentication with non-existent user"""
        user_login = UserLogin(
            email="nonexistent@example.com",
            password="password123"
        )
        
        authenticated_user = auth_service.authenticate_user(user_login)
        assert authenticated_user is None

    def test_create_access_token(self, auth_service):
        """Test JWT access token creation"""
        from app.auth.auth_models import TokenData
        
        token_data = TokenData(
            user_id="user_123",
            username="testuser",
            role=UserRole.VIEWER
        )
        
        token = auth_service.create_access_token(token_data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, auth_service):
        """Test refresh token creation"""
        user_id = "user_123"
        refresh_token = auth_service.create_refresh_token(user_id)
        
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0
        # Should be stored in refresh_tokens dict
        assert user_id in auth_service.refresh_tokens

    def test_refresh_access_token_success(self, auth_service):
        """Test successful access token refresh"""
        user_id = "user_123"
        # Create user first
        user = User(
            user_id=user_id,
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password_hash="hashed_password",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE
        )
        auth_service.users[user_id] = user
        
        refresh_token = auth_service.create_refresh_token(user_id)
        new_access_token = auth_service.refresh_access_token(refresh_token, user_id)
        
        assert new_access_token is not None
        assert isinstance(new_access_token, str)

    def test_refresh_access_token_invalid_token(self, auth_service):
        """Test access token refresh with invalid refresh token"""
        user_id = "user_123"
        invalid_refresh_token = "invalid_token"
        
        new_access_token = auth_service.refresh_access_token(invalid_refresh_token, user_id)
        assert new_access_token is None

    def test_login_user_success(self, auth_service, sample_user_data):
        """Test successful user login"""
        # Create and activate user
        user = auth_service.create_user(sample_user_data)
        user.status = UserStatus.ACTIVE
        
        user_login = UserLogin(
            email=sample_user_data.email,
            password=sample_user_data.password
        )
        
        login_response = auth_service.login_user(user_login)
        
        assert login_response.access_token is not None
        assert login_response.user_id == user.user_id
        assert login_response.username == user.username
        assert login_response.role == user.role
        assert login_response.expires_in > 0

    def test_login_user_invalid_credentials(self, auth_service, sample_user_data):
        """Test login with invalid credentials"""
        # Create user
        auth_service.create_user(sample_user_data)
        # Don't activate user - should fail authentication
        
        user_login = UserLogin(
            email=sample_user_data.email,
            password=sample_user_data.password
        )
        
        with pytest.raises(ValueError, match="Invalid credentials"):
            auth_service.login_user(user_login)

    def test_get_current_user_valid_token(self, auth_service, sample_user_data):
        """Test getting current user with valid token"""
        # Create and activate user
        user = auth_service.create_user(sample_user_data)
        user.status = UserStatus.ACTIVE
        
        # Create token
        from app.auth.auth_models import TokenData
        token_data = TokenData(user_id=user.user_id)
        token = auth_service.create_access_token(token_data)
        
        current_user = auth_service.get_current_user(token)
        assert current_user is not None
        assert current_user.user_id == user.user_id

    def test_get_current_user_invalid_token(self, auth_service):
        """Test getting current user with invalid token"""
        invalid_token = "invalid.token.here"
        current_user = auth_service.get_current_user(invalid_token)
        assert current_user is None

    def test_get_user_permissions(self, auth_service):
        """Test getting user permissions based on role"""
        # Test viewer permissions
        viewer_user = User(
            user_id="viewer_123",
            email="viewer@example.com",
            username="viewer",
            full_name="Viewer User",
            password_hash="hashed_password",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE
        )
        
        viewer_permissions = auth_service.get_user_permissions(viewer_user)
        assert PermissionScope.DOCUMENT_READ in viewer_permissions
        assert PermissionScope.DOCUMENT_WRITE not in viewer_permissions

    def test_has_permission(self, auth_service):
        """Test permission checking"""
        user = User(
            user_id="user_123",
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password_hash="hashed_password",
            role=UserRole.TENANT_MEMBER,
            status=UserStatus.ACTIVE
        )
        
        # Should have document read permission
        assert auth_service.has_permission(user, PermissionScope.DOCUMENT_READ) is True
        # Should not have system admin permission
        assert auth_service.has_permission(user, PermissionScope.SYSTEM_ADMIN) is False

    def test_has_tenant_access(self, auth_service):
        """Test tenant access checking"""
        tenant_id = "tenant_123"
        user = User(
            user_id="user_123",
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password_hash="hashed_password",
            role=UserRole.TENANT_MEMBER,
            status=UserStatus.ACTIVE,
            tenant_memberships=[tenant_id]
        )
        
        # Should have access to their tenant
        assert auth_service.has_tenant_access(user, tenant_id) is True
        # Should not have access to other tenant
        assert auth_service.has_tenant_access(user, "other_tenant") is False
        
        # Super admin should have access to all tenants
        admin_user = User(
            user_id="admin_123",
            email="admin@example.com",
            username="admin",
            full_name="Admin User",
            password_hash="hashed_password",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE
        )
        assert auth_service.has_tenant_access(admin_user, "any_tenant") is True

    def test_get_user_by_id(self, auth_service, sample_user_data):
        """Test getting user by ID"""
        user = auth_service.create_user(sample_user_data)
        retrieved_user = auth_service.get_user_by_id(user.user_id)
        
        assert retrieved_user is not None
        assert retrieved_user.user_id == user.user_id

    def test_get_user_by_email(self, auth_service, sample_user_data):
        """Test getting user by email"""
        user = auth_service.create_user(sample_user_data)
        retrieved_user = auth_service.get_user_by_email(user.email)
        
        assert retrieved_user is not None
        assert retrieved_user.email == user.email

    def test_update_user(self, auth_service, sample_user_data):
        """Test updating user information"""
        user = auth_service.create_user(sample_user_data)
        
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com"
        }
        
        updated_user = auth_service.update_user(user.user_id, update_data)
        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.email == "updated@example.com"

    def test_delete_user(self, auth_service, sample_user_data):
        """Test deleting user"""
        user = auth_service.create_user(sample_user_data)
        user_id = user.user_id
        
        # User should exist
        assert auth_service.get_user_by_id(user_id) is not None
        
        # Delete user
        result = auth_service.delete_user(user_id)
        assert result is True
        
        # User should no longer exist
        assert auth_service.get_user_by_id(user_id) is None
        assert user_id not in auth_service.refresh_tokens

    def test_list_users(self, auth_service):
        """Test listing users"""
        # Create multiple users
        user1_data = UserCreate(
            email="user1@example.com",
            username="user1",
            full_name="User One",
            password="password123"
        )
        user2_data = UserCreate(
            email="user2@example.com",
            username="user2",
            full_name="User Two",
            password="password123"
        )
        
        auth_service.create_user(user1_data)
        auth_service.create_user(user2_data)
        
        users = auth_service.list_users()
        assert len(users) >= 2  # At least 2 users plus default admin

    def test_add_user_to_tenant(self, auth_service, sample_user_data):
        """Test adding user to tenant"""
        user = auth_service.create_user(sample_user_data)
        tenant_id = "new_tenant"
        
        result = auth_service.add_user_to_tenant(user.user_id, tenant_id)
        assert result is True
        
        updated_user = auth_service.get_user_by_id(user.user_id)
        assert tenant_id in updated_user.tenant_memberships

    def test_remove_user_from_tenant(self, auth_service, sample_user_data):
        """Test removing user from tenant"""
        user = auth_service.create_user(sample_user_data)
        tenant_id = "tenant_to_remove"
        
        # Add tenant first
        auth_service.add_user_to_tenant(user.user_id, tenant_id)
        assert tenant_id in auth_service.get_user_by_id(user.user_id).tenant_memberships
        
        # Remove tenant
        result = auth_service.remove_user_from_tenant(user.user_id, tenant_id)
        assert result is True
        
        updated_user = auth_service.get_user_by_id(user.user_id)
        assert tenant_id not in updated_user.tenant_memberships

    def test_change_user_password(self, auth_service, sample_user_data):
        """Test changing user password"""
        user = auth_service.create_user(sample_user_data)
        old_hash = user.password_hash
        new_password = "new_password_456"
        
        result = auth_service.change_user_password(user.user_id, new_password)
        assert result is True
        
        updated_user = auth_service.get_user_by_id(user.user_id)
        assert updated_user.password_hash != old_hash
        # Verify new password works
        assert auth_service._verify_password(new_password, updated_user.password_hash) is True

    def test_reset_user_password(self, auth_service, sample_user_data):
        """Test resetting user password"""
        user = auth_service.create_user(sample_user_data)
        old_hash = user.password_hash
        
        new_password = auth_service.reset_user_password(user.email)
        assert new_password is not None
        assert isinstance(new_password, str)
        
        updated_user = auth_service.get_user_by_id(user.user_id)
        assert updated_user.password_hash != old_hash
        assert updated_user.status == UserStatus.PENDING
        assert auth_service._verify_password(new_password, updated_user.password_hash) is True