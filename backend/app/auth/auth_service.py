import hashlib
import secrets
import jwt
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import logging
from jose import JWTError
import bcrypt

from app.auth.auth_models import (
    User, UserCreate, UserLogin, UserLoginResponse, TokenData,
    UserRole, UserStatus, ROLE_PERMISSIONS, PermissionScope
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 30
        
        # In production, this would connect to a database
        self.users: Dict[str, User] = {}
        self.refresh_tokens: Dict[str, str] = {}
        self._initialize_default_users()
    
    def _initialize_default_users(self):
        """Initialize default users for testing"""
        # Create super admin user
        admin_password = self._hash_password("admin123")
        admin_user = User(
            user_id="user_admin_123",
            email="admin@rag-platform.com",
            username="admin",
            full_name="System Administrator",
            password_hash=admin_password,
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            tenant_memberships=["system_tenant"]
        )
        self.users[admin_user.user_id] = admin_user
        logger.info("Created default admin user")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(12)}"
    
    def create_user(self, user_create: UserCreate) -> User:
        """Create a new user"""
        # Check if email or username already exists
        if self._user_exists(user_create.email, user_create.username):
            raise ValueError("User with this email or username already exists")
        
        # Hash password
        password_hash = self._hash_password(user_create.password)
        
        # Create user
        user_id = self._generate_user_id()
        user = User(
            user_id=user_id,
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            password_hash=password_hash,
            role=user_create.role,
            status=UserStatus.ACTIVE if user_create.role == UserRole.SUPER_ADMIN else UserStatus.PENDING
        )
        
        # Auto-assign to tenant if provided
        if user_create.tenant_id:
            user.tenant_memberships.append(user_create.tenant_id)
        
        self.users[user_id] = user
        logger.info(f"Created user: {user_id} ({user.username})")
        return user
    
    def _user_exists(self, email: str, username: str) -> bool:
        """Check if user with email or username exists"""
        for user in self.users.values():
            if user.email == email or user.username == username:
                return True
        return False
    
    def authenticate_user(self, user_login: UserLogin) -> Optional[User]:
        """Authenticate user credentials"""
        # Find user by email
        user = None
        for u in self.users.values():
            if u.email == user_login.email and u.status == UserStatus.ACTIVE:
                user = u
                break
        
        if not user:
            return None
        
        # Verify password
        if not self._verify_password(user_login.password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        logger.info(f"User authenticated: {user.user_id}")
        return user
    
    def create_access_token(self, data: TokenData) -> str:
        """Create JWT access token"""
        to_encode = data.dict()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token"""
        token = secrets.token_urlsafe(32)
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        self.refresh_tokens[user_id] = token
        return token
    
    def refresh_access_token(self, refresh_token: str, user_id: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        if self.refresh_tokens.get(user_id) == refresh_token:
            user = self.users.get(user_id)
            if user and user.status == UserStatus.ACTIVE:
                token_data = TokenData(
                    user_id=user.user_id,
                    username=user.username,
                    role=user.role
                )
                return self.create_access_token(token_data)
        return None
    
    def login_user(self, user_login: UserLogin) -> UserLoginResponse:
        """Handle user login and return tokens"""
        user = self.authenticate_user(user_login)
        if not user:
            raise ValueError("Invalid credentials")
        
        # Create token data
        token_data = TokenData(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            scopes=[perm.value for perm in ROLE_PERMISSIONS[user.role].permissions]
        )
        
        # Create tokens
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(user.user_id)
        
        return UserLoginResponse(
            access_token=access_token,
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            tenant_memberships=user.tenant_memberships,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("user_id")
            if user_id is None:
                return None
            return self.users.get(user_id)
        except JWTError:
            return None
    
    def get_user_permissions(self, user: User) -> List[PermissionScope]:
        """Get user permissions based on role"""
        role_permissions = ROLE_PERMISSIONS.get(user.role)
        return role_permissions.permissions if role_permissions else []
    
    def has_permission(self, user: User, permission: PermissionScope) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_user_permissions(user)
        return permission in permissions
    
    def has_tenant_access(self, user: User, tenant_id: str) -> bool:
        """Check if user has access to specific tenant"""
        # Super admin has access to all tenants
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Check tenant membership
        return tenant_id in user.tenant_memberships
    
    def validate_token(self, token: str) -> Optional[TokenData]:
        """Validate JWT token and return token data"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("user_id")
            username: str = payload.get("username")
            role: str = payload.get("role")
            scopes: List[str] = payload.get("scopes", [])
            
            if user_id is None:
                return None
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=UserRole(role) if role else None,
                scopes=scopes
            )
        except JWTError:
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    def update_user(self, user_id: str, user_update: dict) -> Optional[User]:
        """Update user information"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        # Update allowed fields
        updatable_fields = ['email', 'username', 'full_name', 'role', 'status', 'metadata']
        for field, value in user_update.items():
            if field in updatable_fields and value is not None:
                setattr(user, field, value)
        
        logger.info(f"Updated user: {user_id}")
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        if user_id in self.users:
            del self.users[user_id]
            # Also remove refresh token
            self.refresh_tokens.pop(user_id, None)
            logger.info(f"Deleted user: {user_id}")
            return True
        return False
    
    def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        """List users, optionally filtered by tenant"""
        if tenant_id:
            return [user for user in self.users.values() 
                   if tenant_id in user.tenant_memberships]
        return list(self.users.values())
    
    def add_user_to_tenant(self, user_id: str, tenant_id: str, role: UserRole = UserRole.TENANT_MEMBER) -> bool:
        """Add user to tenant"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        if tenant_id not in user.tenant_memberships:
            user.tenant_memberships.append(tenant_id)
            # Update user role if it's a tenant-specific role
            if role in [UserRole.TENANT_ADMIN, UserRole.TENANT_MEMBER]:
                user.role = role
            logger.info(f"Added user {user_id} to tenant {tenant_id}")
            return True
        return False
    
    def remove_user_from_tenant(self, user_id: str, tenant_id: str) -> bool:
        """Remove user from tenant"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        if tenant_id in user.tenant_memberships:
            user.tenant_memberships.remove(tenant_id)
            logger.info(f"Removed user {user_id} from tenant {tenant_id}")
            return True
        return False
    
    def change_user_password(self, user_id: str, new_password: str) -> bool:
        """Change user password"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.password_hash = self._hash_password(new_password)
        logger.info(f"Changed password for user: {user_id}")
        return True
    
    def reset_user_password(self, email: str) -> Optional[str]:
        """Reset user password and return new password"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        # Generate random password
        new_password = secrets.token_urlsafe(12)
        user.password_hash = self._hash_password(new_password)
        user.status = UserStatus.PENDING  # Require password change on next login
        logger.info(f"Reset password for user: {user.user_id}")
        return new_password

# Global instance
auth_service = AuthService()