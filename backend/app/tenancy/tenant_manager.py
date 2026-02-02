import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class TenantStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class AccessLevel(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

@dataclass
class Tenant:
    """Tenant information"""
    tenant_id: str
    name: str
    description: Optional[str]
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    limits: Dict[str, int]  # Resource limits

@dataclass
class TenantUser:
    """Tenant user membership"""
    user_id: str
    tenant_id: str
    access_level: AccessLevel
    joined_at: datetime
    metadata: Dict[str, Any]

@dataclass
class CollectionMetadata:
    """Enhanced collection metadata for tenancy"""
    collection_name: str
    tenant_id: str
    mode: str
    visibility: str  # public, private, shared
    tags: List[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    document_count: int
    size_bytes: int
    access_control: Dict[str, Any]  # User permissions
    metadata: Dict[str, Any]

class TenantManager:
    """Multi-tenant data segmentation and management"""
    
    def __init__(self):
        # In production, this would connect to a database
        self.tenants: Dict[str, Tenant] = {}
        self.tenant_users: Dict[str, List[TenantUser]] = {}
        self.collection_metadata: Dict[str, CollectionMetadata] = {}
        self.default_limits = {
            "max_collections": 100,
            "max_documents_per_collection": 10000,
            "max_storage_mb": 10000,
            "max_users": 50
        }
    
    def create_tenant(self, name: str, description: Optional[str] = None, 
                     admin_user_id: str = None, metadata: Dict[str, Any] = None) -> Tenant:
        """
        Create a new tenant
        
        Args:
            name: Tenant name
            description: Tenant description
            admin_user_id: User ID of tenant administrator
            metadata: Additional tenant metadata
            
        Returns:
            Created tenant object
        """
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            description=description,
            status=TenantStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {},
            limits=self.default_limits.copy()
        )
        
        self.tenants[tenant_id] = tenant
        logger.info(f"Created tenant: {tenant_id} ({name})")
        
        # Add admin user if provided
        if admin_user_id:
            self.add_user_to_tenant(tenant_id, admin_user_id, AccessLevel.OWNER)
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    def list_tenants(self, user_id: str = None) -> List[Tenant]:
        """
        List tenants accessible to user
        
        Args:
            user_id: User ID to filter by (None for all tenants)
            
        Returns:
            List of accessible tenants
        """
        if user_id:
            # Return tenants where user has membership
            accessible_tenant_ids = {
                membership.tenant_id 
                for memberships in self.tenant_users.values() 
                for membership in memberships 
                if membership.user_id == user_id
            }
            return [self.tenants[tid] for tid in accessible_tenant_ids if tid in self.tenants]
        else:
            # Return all tenants (admin only)
            return list(self.tenants.values())
    
    def update_tenant(self, tenant_id: str, **updates) -> Optional[Tenant]:
        """Update tenant information"""
        if tenant_id not in self.tenants:
            return None
        
        tenant = self.tenants[tenant_id]
        tenant.updated_at = datetime.now()
        
        # Update allowed fields
        updatable_fields = ['name', 'description', 'status', 'metadata', 'limits']
        for field, value in updates.items():
            if field in updatable_fields:
                setattr(tenant, field, value)
        
        logger.info(f"Updated tenant: {tenant_id}")
        return tenant
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete tenant and all associated data"""
        if tenant_id not in self.tenants:
            return False
        
        # Remove tenant
        del self.tenants[tenant_id]
        
        # Remove user memberships
        self.tenant_users.pop(tenant_id, None)
        
        # Remove collection metadata
        collections_to_remove = [
            name for name, meta in self.collection_metadata.items() 
            if meta.tenant_id == tenant_id
        ]
        for collection_name in collections_to_remove:
            del self.collection_metadata[collection_name]
        
        logger.info(f"Deleted tenant: {tenant_id}")
        return True
    
    def add_user_to_tenant(self, tenant_id: str, user_id: str, 
                          access_level: AccessLevel, metadata: Dict[str, Any] = None) -> bool:
        """
        Add user to tenant with specified access level
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            access_level: Access level for user
            metadata: Additional user metadata
            
        Returns:
            Boolean indicating success
        """
        if tenant_id not in self.tenants:
            return False
        
        # Check if user already exists in tenant
        if tenant_id in self.tenant_users:
            existing_users = [u.user_id for u in self.tenant_users[tenant_id]]
            if user_id in existing_users:
                return False  # User already exists
        
        tenant_user = TenantUser(
            user_id=user_id,
            tenant_id=tenant_id,
            access_level=access_level,
            joined_at=datetime.now(),
            metadata=metadata or {}
        )
        
        if tenant_id not in self.tenant_users:
            self.tenant_users[tenant_id] = []
        
        self.tenant_users[tenant_id].append(tenant_user)
        logger.info(f"Added user {user_id} to tenant {tenant_id} with {access_level.value} access")
        return True
    
    def remove_user_from_tenant(self, tenant_id: str, user_id: str) -> bool:
        """Remove user from tenant"""
        if tenant_id not in self.tenant_users:
            return False
        
        users = self.tenant_users[tenant_id]
        user_index = next((i for i, u in enumerate(users) if u.user_id == user_id), None)
        
        if user_index is not None:
            users.pop(user_index)
            logger.info(f"Removed user {user_id} from tenant {tenant_id}")
            return True
        
        return False
    
    def get_tenant_users(self, tenant_id: str) -> List[TenantUser]:
        """Get all users in tenant"""
        return self.tenant_users.get(tenant_id, [])
    
    def get_user_tenants(self, user_id: str) -> List[Tenant]:
        """Get all tenants for user"""
        tenant_ids = {
            membership.tenant_id 
            for memberships in self.tenant_users.values() 
            for membership in memberships 
            if membership.user_id == user_id
        }
        return [self.tenants[tid] for tid in tenant_ids if tid in self.tenants]
    
    def check_user_access(self, tenant_id: str, user_id: str, 
                         required_level: AccessLevel = AccessLevel.VIEWER) -> bool:
        """
        Check if user has required access level to tenant
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            required_level: Required access level
            
        Returns:
            Boolean indicating access permission
        """
        if tenant_id not in self.tenant_users:
            return False
        
        # Access level hierarchy
        level_hierarchy = {
            AccessLevel.VIEWER: 1,
            AccessLevel.MEMBER: 2,
            AccessLevel.ADMIN: 3,
            AccessLevel.OWNER: 4
        }
        
        required_rank = level_hierarchy[required_level]
        
        for user_membership in self.tenant_users[tenant_id]:
            if user_membership.user_id == user_id:
                user_rank = level_hierarchy[user_membership.access_level]
                return user_rank >= required_rank
        
        return False
    
    def create_collection_metadata(self, collection_name: str, tenant_id: str, 
                                 mode: str, created_by: str, tags: List[str] = None,
                                 visibility: str = "private", metadata: Dict[str, Any] = None) -> CollectionMetadata:
        """
        Create metadata for a collection
        
        Args:
            collection_name: Name of collection
            tenant_id: Associated tenant
            mode: Processing mode (judicial/sales/research)
            created_by: User who created collection
            tags: Collection tags
            visibility: Collection visibility
            metadata: Additional metadata
            
        Returns:
            Collection metadata object
        """
        collection_metadata = CollectionMetadata(
            collection_name=collection_name,
            tenant_id=tenant_id,
            mode=mode,
            visibility=visibility,
            tags=tags or [],
            created_by=created_by,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            document_count=0,
            size_bytes=0,
            access_control={"owners": [created_by], "readers": [], "writers": []},
            metadata=metadata or {}
        )
        
        self.collection_metadata[collection_name] = collection_metadata
        logger.info(f"Created collection metadata: {collection_name} for tenant {tenant_id}")
        return collection_metadata
    
    def get_collection_metadata(self, collection_name: str) -> Optional[CollectionMetadata]:
        """Get collection metadata"""
        return self.collection_metadata.get(collection_name)
    
    def list_tenant_collections(self, tenant_id: str, mode: str = None) -> List[CollectionMetadata]:
        """List collections for tenant"""
        collections = [
            meta for meta in self.collection_metadata.values()
            if meta.tenant_id == tenant_id
        ]
        
        if mode:
            collections = [c for c in collections if c.mode == mode]
        
        return collections
    
    def update_collection_metadata(self, collection_name: str, **updates) -> Optional[CollectionMetadata]:
        """Update collection metadata"""
        if collection_name not in self.collection_metadata:
            return None
        
        collection = self.collection_metadata[collection_name]
        collection.updated_at = datetime.now()
        
        # Update allowed fields
        updatable_fields = ['tags', 'visibility', 'access_control', 'metadata', 'document_count', 'size_bytes']
        for field, value in updates.items():
            if field in updatable_fields:
                setattr(collection, field, value)
        
        logger.info(f"Updated collection metadata: {collection_name}")
        return collection
    
    def delete_collection_metadata(self, collection_name: str) -> bool:
        """Delete collection metadata"""
        if collection_name in self.collection_metadata:
            del self.collection_metadata[collection_name]
            logger.info(f"Deleted collection metadata: {collection_name}")
            return True
        return False
    
    def validate_tenant_limits(self, tenant_id: str, operation: str) -> bool:
        """
        Validate tenant resource limits
        
        Args:
            tenant_id: Tenant ID
            operation: Operation type to validate
            
        Returns:
            Boolean indicating if operation is within limits
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        limits = tenant.limits
        
        if operation == "create_collection":
            current_collections = len(self.list_tenant_collections(tenant_id))
            return current_collections < limits.get("max_collections", 100)
        
        elif operation == "add_document":
            # Would check document limits per collection
            return True  # Simplified for now
        
        return True

# Global instance
tenant_manager = TenantManager()