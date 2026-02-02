from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
import logging

from app.auth.auth_models import (
    UserCreate, UserLogin, UserLoginResponse, User, UserUpdate,
    UserRole, UserStatus, APIKeyCreate, APIKeyResponse
)
from app.auth.auth_service import auth_service
from app.auth.auth_middleware import (
    get_current_user, get_current_active_user, 
    require_role, require_permission, require_any_permission
)
from app.auth.auth_models import PermissionScope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User)
async def register_user(user_create: UserCreate):
    """Register a new user"""
    try:
        user = auth_service.create_user(user_create)
        logger.info(f"User registered: {user.user_id}")
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=UserLoginResponse)
async def login_user(user_login: UserLogin):
    """Login user and return access token"""
    try:
        login_response = auth_service.login_user(user_login)
        logger.info(f"User login successful: {login_response.user_id}")
        return login_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_active_user)):
    """Logout user (invalidate token on client side)"""
    logger.info(f"User logout: {current_user.user_id}")
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update current user information"""
    try:
        updated_user = auth_service.update_user(current_user.user_id, user_update.dict())
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        logger.info(f"User updated: {current_user.user_id}")
        return updated_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/refresh")
async def refresh_token(refresh_token: str, user_id: str):
    """Refresh access token using refresh token"""
    new_token = auth_service.refresh_access_token(refresh_token, user_id)
    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    return {"access_token": new_token, "token_type": "bearer"}

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user)
):
    """Change user password"""
    # Verify current password
    if not auth_service._verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Change password
    if auth_service.change_user_password(current_user.user_id, new_password):
        logger.info(f"Password changed for user: {current_user.user_id}")
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.post("/reset-password")
async def reset_password(email: str):
    """Reset user password (admin only or via email)"""
    new_password = auth_service.reset_user_password(email)
    if not new_password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # In production, send password reset email instead of returning it
    logger.info(f"Password reset for user with email: {email}")
    return {
        "message": "Password reset successfully",
        "temporary_password": new_password  # Remove in production
    }

# Admin routes
@router.get("/users", response_model=List[User])
async def list_users(
    tenant_id: Optional[str] = None,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """List all users (admin only)"""
    users = auth_service.list_users(tenant_id)
    return users

@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_any_permission([
        PermissionScope.SYSTEM_ADMIN,
        PermissionScope.TENANT_ADMIN
    ]))
):
    """Get user by ID"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """Update user (admin only)"""
    try:
        updated_user = auth_service.update_user(user_id, user_update.dict())
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        logger.info(f"User updated by admin: {user_id}")
        return updated_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """Delete user (admin only)"""
    if auth_service.delete_user(user_id):
        logger.info(f"User deleted by admin: {user_id}")
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.post("/users/{user_id}/tenant/{tenant_id}")
async def add_user_to_tenant(
    user_id: str,
    tenant_id: str,
    role: UserRole = UserRole.TENANT_MEMBER,
    current_user: User = Depends(require_any_permission([
        PermissionScope.SYSTEM_ADMIN,
        PermissionScope.TENANT_ADMIN
    ]))
):
    """Add user to tenant"""
    if auth_service.add_user_to_tenant(user_id, tenant_id, role):
        logger.info(f"User {user_id} added to tenant {tenant_id}")
        return {"message": "User added to tenant successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or tenant not found"
        )

@router.delete("/users/{user_id}/tenant/{tenant_id}")
async def remove_user_from_tenant(
    user_id: str,
    tenant_id: str,
    current_user: User = Depends(require_any_permission([
        PermissionScope.SYSTEM_ADMIN,
        PermissionScope.TENANT_ADMIN
    ]))
):
    """Remove user from tenant"""
    if auth_service.remove_user_from_tenant(user_id, tenant_id):
        logger.info(f"User {user_id} removed from tenant {tenant_id}")
        return {"message": "User removed from tenant successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or tenant not found"
        )

# API Key routes
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_create: APIKeyCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create API key for programmatic access"""
    # Implementation would go here
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="API key management not implemented yet"
    )

@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user)
):
    """List user's API keys"""
    # Implementation would go here
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="API key management not implemented yet"
    )

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete API key"""
    # Implementation would go here
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="API key management not implemented yet"
    )