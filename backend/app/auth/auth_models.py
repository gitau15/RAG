from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(Enum):
    """User roles with hierarchical permissions"""
    SUPER_ADMIN = "super_admin"    # System-wide admin
    TENANT_ADMIN = "tenant_admin"  # Tenant administrator
    TENANT_MEMBER = "tenant_member" # Regular tenant user
    VIEWER = "viewer"             # Read-only access

class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class User(BaseModel):
    """User model"""
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    full_name: str = Field(..., description="Full name")
    password_hash: str = Field(..., description="Hashed password")
    role: UserRole = Field(default=UserRole.VIEWER, description="User role")
    status: UserStatus = Field(default=UserStatus.PENDING, description="Account status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")
    tenant_memberships: List[str] = Field(default=[], description="List of tenant IDs")
    metadata: Dict[str, Any] = Field(default={}, description="Additional user metadata")

class UserCreate(BaseModel):
    """User creation request"""
    email: EmailStr
    username: str
    full_name: str
    password: str
    tenant_id: Optional[str] = None  # Auto-assign to tenant if provided
    role: UserRole = UserRole.VIEWER

class UserUpdate(BaseModel):
    """User update request"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    """User login response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: UserRole
    tenant_memberships: List[str]
    expires_in: int  # Token expiration in seconds

class TokenData(BaseModel):
    """Token data for JWT validation"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    tenant_id: Optional[str] = None
    scopes: List[str] = []

class TenantMembership(BaseModel):
    """User membership in a tenant"""
    user_id: str
    tenant_id: str
    role: UserRole
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default={})

class PermissionScope(Enum):
    """Permission scopes for API access"""
    # Document permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"
    
    # Collection permissions
    COLLECTION_READ = "collection:read"
    COLLECTION_WRITE = "collection:write"
    COLLECTION_DELETE = "collection:delete"
    
    # Query permissions
    QUERY_EXECUTE = "query:execute"
    QUERY_STREAM = "query:stream"
    
    # Payment permissions
    PAYMENT_INITIATE = "payment:initiate"
    PAYMENT_VIEW = "payment:view"
    
    # Tenant permissions
    TENANT_ADMIN = "tenant:admin"
    TENANT_MEMBER = "tenant:member"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"

class RolePermissions(BaseModel):
    """Permissions associated with each role"""
    role: UserRole
    permissions: List[PermissionScope]
    description: str

# Default role permissions
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: RolePermissions(
        role=UserRole.SUPER_ADMIN,
        permissions=list(PermissionScope),  # All permissions
        description="Full system administrator with all permissions"
    ),
    UserRole.TENANT_ADMIN: RolePermissions(
        role=UserRole.TENANT_ADMIN,
        permissions=[
            PermissionScope.DOCUMENT_READ,
            PermissionScope.DOCUMENT_WRITE,
            PermissionScope.DOCUMENT_DELETE,
            PermissionScope.COLLECTION_READ,
            PermissionScope.COLLECTION_WRITE,
            PermissionScope.COLLECTION_DELETE,
            PermissionScope.QUERY_EXECUTE,
            PermissionScope.QUERY_STREAM,
            PermissionScope.PAYMENT_INITIATE,
            PermissionScope.PAYMENT_VIEW,
            PermissionScope.TENANT_ADMIN,
            PermissionScope.TENANT_MEMBER
        ],
        description="Tenant administrator with full tenant permissions"
    ),
    UserRole.TENANT_MEMBER: RolePermissions(
        role=UserRole.TENANT_MEMBER,
        permissions=[
            PermissionScope.DOCUMENT_READ,
            PermissionScope.DOCUMENT_WRITE,
            PermissionScope.COLLECTION_READ,
            PermissionScope.COLLECTION_WRITE,
            PermissionScope.QUERY_EXECUTE,
            PermissionScope.QUERY_STREAM,
            PermissionScope.PAYMENT_INITIATE,
            PermissionScope.TENANT_MEMBER
        ],
        description="Regular tenant member with standard permissions"
    ),
    UserRole.VIEWER: RolePermissions(
        role=UserRole.VIEWER,
        permissions=[
            PermissionScope.DOCUMENT_READ,
            PermissionScope.COLLECTION_READ,
            PermissionScope.QUERY_EXECUTE
        ],
        description="Read-only user with limited permissions"
    )
}

class APIKey(BaseModel):
    """API key for programmatic access"""
    key_id: str
    user_id: str
    name: str
    hashed_key: str
    permissions: List[PermissionScope]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    is_active: bool = True

class APIKeyCreate(BaseModel):
    """API key creation request"""
    name: str
    permissions: List[PermissionScope]
    expires_in_days: Optional[int] = 365

class APIKeyResponse(BaseModel):
    """API key response (key only shown once)"""
    key_id: str
    name: str
    key: str  # Only shown once upon creation
    permissions: List[PermissionScope]
    created_at: datetime
    expires_at: Optional[datetime]