from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import logging

from app.auth.auth_service import auth_service
from app.auth.auth_models import User, UserRole, PermissionScope, TokenData

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer()

class AuthMiddleware:
    """Authentication and authorization middleware"""
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """Get current authenticated user"""
        token = credentials.credentials
        user = auth_service.get_current_user(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )
        
        return user
    
    async def get_current_active_user(self, current_user: User = Depends(get_current_user)) -> User:
        """Get current active user"""
        if current_user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        return current_user
    
    def require_permission(self, required_permission: PermissionScope):
        """Dependency for requiring specific permission"""
        async def permission_checker(current_user: User = Depends(self.get_current_user)):
            if not auth_service.has_permission(current_user, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{required_permission.value}' required"
                )
            return current_user
        return permission_checker
    
    def require_role(self, required_role: UserRole):
        """Dependency for requiring specific role"""
        async def role_checker(current_user: User = Depends(self.get_current_user)):
            if current_user.role != required_role:
                # Check if user has higher role (hierarchical)
                role_hierarchy = {
                    UserRole.SUPER_ADMIN: 4,
                    UserRole.TENANT_ADMIN: 3,
                    UserRole.TENANT_MEMBER: 2,
                    UserRole.VIEWER: 1
                }
                
                user_level = role_hierarchy.get(current_user.role, 0)
                required_level = role_hierarchy.get(required_role, 0)
                
                if user_level < required_level:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Role '{required_role.value}' or higher required"
                    )
            return current_user
        return role_checker
    
    def require_tenant_access(self, tenant_id: str):
        """Dependency for requiring tenant access"""
        async def tenant_checker(current_user: User = Depends(self.get_current_user)):
            if not auth_service.has_tenant_access(current_user, tenant_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access to tenant '{tenant_id}' required"
                )
            return current_user
        return tenant_checker
    
    def require_any_permission(self, required_permissions: List[PermissionScope]):
        """Dependency for requiring any of the specified permissions"""
        async def permission_checker(current_user: User = Depends(self.get_current_user)):
            user_permissions = auth_service.get_user_permissions(current_user)
            if not any(perm in user_permissions for perm in required_permissions):
                perms_str = ", ".join([perm.value for perm in required_permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these permissions required: {perms_str}"
                )
            return current_user
        return permission_checker
    
    def optional_auth(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
        """Optional authentication - returns user if authenticated, None if not"""
        if not credentials:
            return None
        
        token = credentials.credentials
        user = auth_service.get_current_user(token)
        
        if not user or user.status != "active":
            return None
        
        return user

# Global instance
auth_middleware = AuthMiddleware()

# Convenience dependencies
get_current_user = auth_middleware.get_current_user
get_current_active_user = auth_middleware.get_current_active_user
require_permission = auth_middleware.require_permission
require_role = auth_middleware.require_role
require_tenant_access = auth_middleware.require_tenant_access
require_any_permission = auth_middleware.require_any_permission
optional_auth = auth_middleware.optional_auth