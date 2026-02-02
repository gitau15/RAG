import hashlib
import hmac
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import json
from enum import Enum
import os

logger = logging.getLogger(__name__)

class DataSensitivity(Enum):
    """Data sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"

class ProcessingMode(Enum):
    """Processing modes with privacy implications"""
    ONLINE = "online"      # Real-time processing
    BATCH = "batch"        # Batch processing
    OFFLINE = "offline"    # Completely offline
    ENCRYPTED = "encrypted" # Encrypted processing

@dataclass
class PrivacyPolicy:
    """Privacy policy configuration"""
    data_retention_days: int
    encryption_required: bool
    anonymization_required: bool
    audit_logging: bool
    data_export_allowed: bool
    third_party_sharing: bool
    sensitivity_level: DataSensitivity

@dataclass
class DataAuditLog:
    """Audit log entry for data operations"""
    timestamp: datetime
    user_id: str
    operation: str
    data_type: str
    sensitivity_level: DataSensitivity
    tenant_id: str
    collection_name: Optional[str]
    success: bool
    metadata: Dict[str, Any]

class PrivacyManager:
    """Central privacy management system"""
    
    def __init__(self):
        self.policies: Dict[str, PrivacyPolicy] = {}
        self.audit_logs: List[DataAuditLog] = []
        self.encryption_keys: Dict[str, str] = {}
        self.data_hashes: Dict[str, str] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default privacy policies"""
        self.policies["default"] = PrivacyPolicy(
            data_retention_days=365,
            encryption_required=True,
            anonymization_required=False,
            audit_logging=True,
            data_export_allowed=True,
            third_party_sharing=False,
            sensitivity_level=DataSensitivity.INTERNAL
        )
        
        self.policies["legal"] = PrivacyPolicy(
            data_retention_days=730,  # 2 years for legal compliance
            encryption_required=True,
            anonymization_required=True,
            audit_logging=True,
            data_export_allowed=False,
            third_party_sharing=False,
            sensitivity_level=DataSensitivity.CONFIDENTIAL
        )
        
        self.policies["financial"] = PrivacyPolicy(
            data_retention_days=1825,  # 5 years for financial records
            encryption_required=True,
            anonymization_required=True,
            audit_logging=True,
            data_export_allowed=False,
            third_party_sharing=False,
            sensitivity_level=DataSensitivity.RESTRICTED
        )
        
        self.policies["public"] = PrivacyPolicy(
            data_retention_days=90,
            encryption_required=False,
            anonymization_required=False,
            audit_logging=True,
            data_export_allowed=True,
            third_party_sharing=True,
            sensitivity_level=DataSensitivity.PUBLIC
        )
    
    def get_policy(self, policy_name: str = "default") -> PrivacyPolicy:
        """Get privacy policy by name"""
        return self.policies.get(policy_name, self.policies["default"])
    
    def calculate_data_hash(self, data: str, algorithm: str = "sha256") -> str:
        """Calculate cryptographic hash of data for integrity verification"""
        if algorithm == "sha256":
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(data.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    def generate_hmac(self, data: str, key: str, algorithm: str = "sha256") -> str:
        """Generate HMAC for data authentication"""
        if algorithm == "sha256":
            return hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()
        elif algorithm == "sha512":
            return hmac.new(key.encode(), data.encode(), hashlib.sha512).hexdigest()
        else:
            raise ValueError(f"Unsupported HMAC algorithm: {algorithm}")
    
    def anonymize_text(self, text: str, method: str = "basic") -> str:
        """Anonymize text data"""
        if method == "basic":
            # Replace named entities with placeholders
            import re
            # Simple anonymization - replace potential PII patterns
            anonymized = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '[NAME]', text)  # Names
            anonymized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', anonymized)  # Card numbers
            anonymized = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', anonymized)  # Emails
            anonymized = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', anonymized)  # US phones
            return anonymized
        else:
            # Advanced anonymization would require specialized libraries
            return f"[ANONYMIZED-{len(text)}-CHARS]"
    
    def encrypt_data(self, data: str, tenant_id: str) -> str:
        """Encrypt data using tenant-specific key"""
        try:
            # In production, use proper encryption library like cryptography
            key = self._get_or_generate_key(tenant_id)
            # Simple XOR encryption for demonstration - NOT for production
            encrypted = ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))
            return encrypted.encode().hex()  # Hex encoding for safe storage
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: str, tenant_id: str) -> str:
        """Decrypt data using tenant-specific key"""
        try:
            key = self._get_or_generate_key(tenant_id)
            # Decode from hex and decrypt
            encrypted_bytes = bytes.fromhex(encrypted_data)
            decrypted = ''.join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(encrypted_bytes))
            return decrypted
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def _get_or_generate_key(self, tenant_id: str) -> str:
        """Get or generate encryption key for tenant"""
        if tenant_id not in self.encryption_keys:
            # Generate deterministic key based on tenant ID
            # In production, use proper key management system
            key = hashlib.sha256(f"rag-key-{tenant_id}".encode()).hexdigest()[:32]
            self.encryption_keys[tenant_id] = key
        return self.encryption_keys[tenant_id]
    
    def log_data_operation(self, user_id: str, operation: str, data_type: str,
                          sensitivity_level: DataSensitivity, tenant_id: str,
                          collection_name: Optional[str] = None,
                          success: bool = True, metadata: Dict[str, Any] = None):
        """Log data operation for audit purposes"""
        audit_entry = DataAuditLog(
            timestamp=datetime.now(),
            user_id=user_id,
            operation=operation,
            data_type=data_type,
            sensitivity_level=sensitivity_level,
            tenant_id=tenant_id,
            collection_name=collection_name,
            success=success,
            metadata=metadata or {}
        )
        
        self.audit_logs.append(audit_entry)
        logger.info(f"Data operation logged: {operation} on {data_type} by {user_id}")
    
    def check_data_retention(self, creation_date: datetime, policy: PrivacyPolicy) -> bool:
        """Check if data is within retention period"""
        retention_cutoff = datetime.now() - timedelta(days=policy.data_retention_days)
        return creation_date > retention_cutoff
    
    def get_audit_summary(self, tenant_id: Optional[str] = None, 
                         days: int = 30) -> Dict[str, Any]:
        """Get audit log summary"""
        cutoff_date = datetime.now() - timedelta(days=days)
        relevant_logs = [
            log for log in self.audit_logs
            if log.timestamp > cutoff_date and (not tenant_id or log.tenant_id == tenant_id)
        ]
        
        summary = {
            "total_operations": len(relevant_logs),
            "successful_operations": len([log for log in relevant_logs if log.success]),
            "failed_operations": len([log for log in relevant_logs if not log.success]),
            "operations_by_type": {},
            "sensitivity_distribution": {},
            "recent_operations": relevant_logs[-10:]  # Last 10 operations
        }
        
        # Count operations by type
        for log in relevant_logs:
            summary["operations_by_type"][log.operation] = \
                summary["operations_by_type"].get(log.operation, 0) + 1
            summary["sensitivity_distribution"][log.sensitivity_level.value] = \
                summary["sensitivity_distribution"].get(log.sensitivity_level.value, 0) + 1
        
        return summary
    
    def enforce_privacy_by_mode(self, mode: str) -> ProcessingMode:
        """Determine appropriate processing mode based on data sensitivity"""
        mode_processing_map = {
            "judicial": ProcessingMode.ENCRYPTED,
            "financial": ProcessingMode.ENCRYPTED,
            "healthcare": ProcessingMode.ENCRYPTED,
            "sales": ProcessingMode.BATCH,
            "research": ProcessingMode.OFFLINE,
            "public": ProcessingMode.ONLINE
        }
        
        return mode_processing_map.get(mode.lower(), ProcessingMode.BATCH)
    
    def validate_data_handling(self, data_type: str, operation: str, 
                              sensitivity: DataSensitivity) -> bool:
        """Validate if data handling operation is permitted"""
        # Define operation restrictions based on sensitivity
        restrictions = {
            DataSensitivity.PUBLIC: set(),  # No restrictions
            DataSensitivity.INTERNAL: {"export", "share_external"},
            DataSensitivity.CONFIDENTIAL: {"export", "share_external", "public_access"},
            DataSensitivity.RESTRICTED: {"export", "share_external", "public_access", "bulk_processing"},
            DataSensitivity.SECRET: {"export", "share_external", "public_access", "bulk_processing", "api_access"}
        }
        
        prohibited_operations = restrictions.get(sensitivity, set())
        return operation not in prohibited_operations

# Global instance
privacy_manager = PrivacyManager()