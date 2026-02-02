import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.auth.auth_models import User, UserRole, UserStatus

client = TestClient(app)

class TestAuthRoutes:
    @pytest.fixture
    def mock_user_data(self):
        """Sample user data for testing"""
        return {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "password123",
            "role": "viewer"
        }

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user for testing"""
        return User(
            user_id="admin_123",
            email="admin@example.com",
            username="admin",
            full_name="Admin User",
            password_hash="hashed_password",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE
        )

    @pytest.fixture
    def mock_regular_user(self):
        """Mock regular user for testing"""
        return User(
            user_id="user_123",
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password_hash="hashed_password",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE
        )

    def test_register_user_success(self, mock_user_data):
        """Test successful user registration"""
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_user = Mock()
            mock_user.user_id = "user_123"
            mock_user.email = mock_user_data["email"]
            mock_user.username = mock_user_data["username"]
            mock_user.full_name = mock_user_data["full_name"]
            mock_user.role = UserRole.VIEWER
            mock_user.status = UserStatus.PENDING
            
            mock_service.create_user.return_value = mock_user
            
            response = client.post("/api/v1/auth/register", json=mock_user_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == mock_user_data["email"]
            assert data["username"] == mock_user_data["username"]
            mock_service.create_user.assert_called_once()

    def test_register_user_duplicate_email(self, mock_user_data):
        """Test user registration with duplicate email"""
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.create_user.side_effect = ValueError("User with this email or username already exists")
            
            response = client.post("/api/v1/auth/register", json=mock_user_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "User with this email or username already exists" in response.json()["detail"]

    def test_login_user_success(self, mock_user_data):
        """Test successful user login"""
        login_data = {
            "email": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        
        mock_login_response = Mock()
        mock_login_response.access_token = "test_token"
        mock_login_response.user_id = "user_123"
        mock_login_response.username = "testuser"
        mock_login_response.role = UserRole.VIEWER
        mock_login_response.tenant_memberships = []
        mock_login_response.expires_in = 1800
        
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.login_user.return_value = mock_login_response
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "test_token"
            assert data["user_id"] == "user_123"
            mock_service.login_user.assert_called_once()

    def test_login_user_invalid_credentials(self, mock_user_data):
        """Test user login with invalid credentials"""
        login_data = {
            "email": mock_user_data["email"],
            "password": "wrong_password"
        }
        
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.login_user.side_effect = ValueError("Invalid credentials")
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid credentials" in response.json()["detail"]

    def test_logout_user_success(self):
        """Test successful user logout"""
        with patch('app.auth.auth_routes.get_current_active_user') as mock_current_user:
            mock_user = Mock()
            mock_user.user_id = "user_123"
            mock_current_user.return_value = mock_user
            
            response = client.post("/api/v1/auth/logout")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Successfully logged out"

    def test_get_current_user_info(self):
        """Test getting current user information"""
        mock_user = Mock()
        mock_user.user_id = "user_123"
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"
        mock_user.role = UserRole.VIEWER
        mock_user.status = UserStatus.ACTIVE
        
        with patch('app.auth.auth_routes.get_current_active_user') as mock_current_user:
            mock_current_user.return_value = mock_user
            
            response = client.get("/api/v1/auth/me")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["username"] == "testuser"

    def test_update_current_user(self):
        """Test updating current user information"""
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com"
        }
        
        mock_updated_user = Mock()
        mock_updated_user.user_id = "user_123"
        mock_updated_user.email = "updated@example.com"
        mock_updated_user.full_name = "Updated Name"
        
        with patch('app.auth.auth_routes.get_current_active_user') as mock_current_user:
            mock_current_user.return_value = Mock(user_id="user_123")
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.update_user.return_value = mock_updated_user
                
                response = client.put("/api/v1/auth/me", json=update_data)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["email"] == "updated@example.com"
                assert data["full_name"] == "Updated Name"

    def test_update_current_user_error(self):
        """Test updating current user with error"""
        update_data = {"full_name": "Updated Name"}
        
        with patch('app.auth.auth_routes.get_current_active_user') as mock_current_user:
            mock_current_user.return_value = Mock(user_id="user_123")
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.update_user.return_value = None  # Simulate user not found
                
                response = client.put("/api/v1/auth/me", json=update_data)
                
                assert response.status_code == status.HTTP_404_NOT_FOUND
                assert "User not found" in response.json()["detail"]

    def test_refresh_token_success(self):
        """Test successful token refresh"""
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.refresh_access_token.return_value = "new_access_token"
            
            response = client.post("/api/v1/auth/refresh", 
                                params={"refresh_token": "refresh_123", "user_id": "user_123"})
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self):
        """Test token refresh with invalid refresh token"""
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.refresh_access_token.return_value = None
            
            response = client.post("/api/v1/auth/refresh",
                                params={"refresh_token": "invalid_token", "user_id": "user_123"})
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid refresh token" in response.json()["detail"]

    def test_change_password_success(self):
        """Test successful password change"""
        with patch('app.auth.auth_routes.get_current_active_user') as mock_current_user:
            mock_user = Mock()
            mock_user.user_id = "user_123"
            mock_user.password_hash = "old_hashed_password"
            mock_current_user.return_value = mock_user
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service._verify_password.return_value = True
                mock_service.change_user_password.return_value = True
                
                response = client.post("/api/v1/auth/change-password",
                                     params={"current_password": "old_password", 
                                           "new_password": "new_password"})
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "Password changed successfully"

    def test_change_password_wrong_current(self):
        """Test password change with wrong current password"""
        with patch('app.auth.auth_routes.get_current_active_user') as mock_current_user:
            mock_user = Mock()
            mock_user.password_hash = "old_hashed_password"
            mock_current_user.return_value = mock_user
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service._verify_password.return_value = False  # Wrong password
                
                response = client.post("/api/v1/auth/change-password",
                                     params={"current_password": "wrong_password",
                                           "new_password": "new_password"})
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "Current password is incorrect" in response.json()["detail"]

    def test_reset_password_success(self):
        """Test successful password reset"""
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.reset_user_password.return_value = "temporary_password123"
            
            response = client.post("/api/v1/auth/reset-password", 
                                 params={"email": "test@example.com"})
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Password reset successfully"
            assert "temporary_password" in data

    def test_reset_password_user_not_found(self):
        """Test password reset for non-existent user"""
        with patch('app.auth.auth_routes.auth_service') as mock_service:
            mock_service.reset_user_password.return_value = None
            
            response = client.post("/api/v1/auth/reset-password",
                                 params={"email": "nonexistent@example.com"})
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in response.json()["detail"]

    def test_list_users_admin_only(self):
        """Test listing users (admin only)"""
        mock_users = [
            Mock(user_id="user_1", email="user1@example.com", username="user1"),
            Mock(user_id="user_2", email="user2@example.com", username="user2")
        ]
        
        with patch('app.auth.auth_routes.require_role') as mock_require_role:
            # Mock the role requirement to pass
            mock_require_role.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.list_users.return_value = mock_users
                
                response = client.get("/api/v1/auth/users")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data) == 2

    def test_get_user_by_id(self):
        """Test getting user by ID"""
        mock_user = Mock(user_id="user_123", email="test@example.com", username="testuser")
        
        with patch('app.auth.auth_routes.require_any_permission') as mock_require_permission:
            # Mock the permission requirement to pass
            mock_require_permission.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.get_user_by_id.return_value = mock_user
                
                response = client.get("/api/v1/auth/users/user_123")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["user_id"] == "user_123"

    def test_get_user_not_found(self):
        """Test getting non-existent user"""
        with patch('app.auth.auth_routes.require_any_permission') as mock_require_permission:
            mock_require_permission.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.get_user_by_id.return_value = None
                
                response = client.get("/api/v1/auth/users/nonexistent")
                
                assert response.status_code == status.HTTP_404_NOT_FOUND
                assert "User not found" in response.json()["detail"]

    def test_update_user_admin(self):
        """Test updating user (admin only)"""
        update_data = {"full_name": "Updated Name"}
        mock_updated_user = Mock(user_id="user_123", full_name="Updated Name")
        
        with patch('app.auth.auth_routes.require_role') as mock_require_role:
            mock_require_role.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.update_user.return_value = mock_updated_user
                
                response = client.put("/api/v1/auth/users/user_123", json=update_data)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["full_name"] == "Updated Name"

    def test_delete_user_admin(self):
        """Test deleting user (admin only)"""
        with patch('app.auth.auth_routes.require_role') as mock_require_role:
            mock_require_role.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.delete_user.return_value = True
                
                response = client.delete("/api/v1/auth/users/user_123")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "User deleted successfully"

    def test_add_user_to_tenant(self):
        """Test adding user to tenant"""
        with patch('app.auth.auth_routes.require_any_permission') as mock_require_permission:
            mock_require_permission.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.add_user_to_tenant.return_value = True
                
                response = client.post("/api/v1/auth/users/user_123/tenant/tenant_456")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "User added to tenant successfully"

    def test_remove_user_from_tenant(self):
        """Test removing user from tenant"""
        with patch('app.auth.auth_routes.require_any_permission') as mock_require_permission:
            mock_require_permission.return_value = lambda x: x
            
            with patch('app.auth.auth_routes.auth_service') as mock_service:
                mock_service.remove_user_from_tenant.return_value = True
                
                response = client.delete("/api/v1/auth/users/user_123/tenant/tenant_456")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "User removed from tenant successfully"

    def test_api_key_routes_not_implemented(self):
        """Test that API key routes return not implemented"""
        # Test create API key
        response = client.post("/api/v1/auth/api-keys", json={"name": "test_key", "permissions": []})
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        
        # Test list API keys
        response = client.get("/api/v1/auth/api-keys")
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        
        # Test delete API key
        response = client.delete("/api/v1/auth/api-keys/key_123")
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED