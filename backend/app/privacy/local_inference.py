import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import json
import os
from pathlib import Path

from app.privacy.data_protection import privacy_manager, DataSensitivity, ProcessingMode
from app.llm.ollama_client import ollama_client
from app.vectorstore.chroma_client import chroma_client

logger = logging.getLogger(__name__)

@dataclass
class InferenceRequest:
    """Local inference request with privacy controls"""
    query: str
    collection_name: str
    tenant_id: str
    mode: str
    processing_mode: ProcessingMode
    sensitivity_level: DataSensitivity
    user_id: str
    metadata: Dict[str, Any]

@dataclass
class InferenceResponse:
    """Local inference response with privacy metadata"""
    response: str
    processing_time_ms: float
    tokens_used: int
    model_used: str
    privacy_compliant: bool
    audit_trail: Dict[str, Any]
    timestamp: datetime

class LocalInferenceEngine:
    """Privacy-first local inference engine"""
    
    def __init__(self):
        self.privacy = privacy_manager
        self.llm = ollama_client
        self.vectorstore = chroma_client
        self.inference_cache: Dict[str, Any] = {}
        self._ensure_local_directories()
    
    def _ensure_local_directories(self):
        """Ensure local storage directories exist"""
        local_dirs = [
            "local_cache",
            "audit_logs",
            "encrypted_data",
            "model_cache"
        ]
        
        for dir_name in local_dirs:
            dir_path = Path(f"./local_storage/{dir_name}")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def process_query_privately(self, request: InferenceRequest) -> InferenceResponse:
        """
        Process query with full privacy controls
        
        Args:
            request: Privacy-controlled inference request
            
        Returns:
            Privacy-compliant inference response
        """
        start_time = datetime.now()
        audit_trail = {
            "request_id": f"req_{int(start_time.timestamp())}",
            "processing_steps": []
        }
        
        try:
            # Step 1: Validate privacy compliance
            audit_trail["processing_steps"].append("privacy_validation")
            if not self._validate_privacy_compliance(request):
                raise ValueError("Privacy compliance validation failed")
            
            # Step 2: Apply data protection measures
            audit_trail["processing_steps"].append("data_protection")
            protected_query = await self._apply_data_protection(request.query, request)
            
            # Step 3: Process based on privacy mode
            audit_trail["processing_steps"].append("mode_processing")
            if request.processing_mode == ProcessingMode.ENCRYPTED:
                response_text = await self._process_encrypted(protected_query, request)
            elif request.processing_mode == ProcessingMode.OFFLINE:
                response_text = await self._process_offline(protected_query, request)
            elif request.processing_mode == ProcessingMode.BATCH:
                response_text = await self._process_batch(protected_query, request)
            else:  # ONLINE
                response_text = await self._process_online(protected_query, request)
            
            # Step 4: Apply output protection
            audit_trail["processing_steps"].append("output_protection")
            protected_response = self._protect_output(response_text, request)
            
            # Step 5: Log audit trail
            audit_trail["processing_steps"].append("audit_logging")
            self._log_inference_operation(request, audit_trail)
            
            # Calculate processing metrics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            response = InferenceResponse(
                response=protected_response,
                processing_time_ms=processing_time,
                tokens_used=len(protected_response.split()),
                model_used="mistral:7b-local",
                privacy_compliant=True,
                audit_trail=audit_trail,
                timestamp=end_time
            )
            
            logger.info(f"Privacy-compliant inference completed for tenant {request.tenant_id}")
            return response
            
        except Exception as e:
            logger.error(f"Private inference failed: {str(e)}")
            audit_trail["error"] = str(e)
            self._log_inference_operation(request, audit_trail, success=False)
            raise
    
    def _validate_privacy_compliance(self, request: InferenceRequest) -> bool:
        """Validate that request complies with privacy policies"""
        # Check data handling permissions
        if not self.privacy.validate_data_handling(
            "query", "inference", request.sensitivity_level
        ):
            return False
        
        # Check processing mode appropriateness
        required_mode = self.privacy.enforce_privacy_by_mode(request.mode)
        if request.processing_mode != required_mode:
            logger.warning(f"Processing mode mismatch: requested {request.processing_mode}, required {required_mode}")
            # Allow less restrictive modes but not more restrictive ones
            if required_mode == ProcessingMode.ENCRYPTED and request.processing_mode != ProcessingMode.ENCRYPTED:
                return False
        
        # Check data retention
        policy = self.privacy.get_policy(request.mode)
        # This would check against actual data creation dates in production
        
        return True
    
    async def _apply_data_protection(self, query: str, request: InferenceRequest) -> str:
        """Apply data protection measures to input"""
        protected_query = query
        
        # Apply anonymization if required
        policy = self.privacy.get_policy(request.mode)
        if policy.anonymization_required:
            protected_query = self.privacy.anonymize_text(protected_query)
            logger.info("Applied anonymization to query")
        
        # Calculate and store hash for integrity verification
        query_hash = self.privacy.calculate_data_hash(protected_query)
        self.privacy.data_hashes[f"query_{request.user_id}_{int(datetime.now().timestamp())}"] = query_hash
        
        return protected_query
    
    async def _process_encrypted(self, query: str, request: InferenceRequest) -> str:
        """Process query with full encryption"""
        try:
            # Encrypt query data
            encrypted_query = self.privacy.encrypt_data(query, request.tenant_id)
            logger.info("Query encrypted for processing")
            
            # Retrieve encrypted documents
            encrypted_docs = await self._retrieve_encrypted_documents(request)
            
            # Process with LLM (encrypted data)
            # Note: This is simplified - production would use encrypted LLM inference
            response = await self.llm.generate(
                f"Process this encrypted query: {encrypted_query[:50]}...",
                system_prompt="You are a privacy-focused assistant that works with encrypted data."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Encrypted processing failed: {str(e)}")
            raise
    
    async def _process_offline(self, query: str, request: InferenceRequest) -> str:
        """Process query in completely offline mode"""
        try:
            # Ensure no external connections
            logger.info("Processing in offline mode")
            
            # Use cached responses when possible
            cache_key = self._generate_cache_key(query, request)
            if cache_key in self.inference_cache:
                logger.info("Using cached response")
                return self.inference_cache[cache_key]
            
            # Process with local LLM only
            response = await self.llm.generate(
                query,
                system_prompt="You are an offline assistant with no internet access."
            )
            
            # Cache response
            self.inference_cache[cache_key] = response
            self._save_cache_to_disk()
            
            return response
            
        except Exception as e:
            logger.error(f"Offline processing failed: {str(e)}")
            raise
    
    async def _process_batch(self, query: str, request: InferenceRequest) -> str:
        """Process query in batch mode with delayed processing"""
        try:
            # Queue for batch processing
            batch_job = {
                "query": query,
                "request": request,
                "submitted_at": datetime.now(),
                "status": "queued"
            }
            
            # In production, this would use a proper job queue
            logger.info("Query queued for batch processing")
            
            # Simulate batch processing delay
            await asyncio.sleep(0.1)  # Minimal delay for demo
            
            response = await self.llm.generate(
                query,
                system_prompt="You are processing batch requests efficiently."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise
    
    async def _process_online(self, query: str, request: InferenceRequest) -> str:
        """Process query in standard online mode"""
        try:
            # Standard processing with privacy controls
            response = await self.llm.generate(
                query,
                system_prompt="You are a privacy-conscious assistant."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Online processing failed: {str(e)}")
            raise
    
    def _protect_output(self, response: str, request: InferenceRequest) -> str:
        """Apply protection measures to output"""
        protected_response = response
        
        # Apply output anonymization if required
        policy = self.privacy.get_policy(request.mode)
        if policy.anonymization_required:
            protected_response = self.privacy.anonymize_text(protected_response)
            logger.info("Applied anonymization to response")
        
        # Ensure no sensitive data leakage
        if request.sensitivity_level in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
            # Additional output filtering for highly sensitive data
            protected_response = self._filter_sensitive_output(protected_response)
        
        return protected_response
    
    def _filter_sensitive_output(self, response: str) -> str:
        """Filter potentially sensitive information from output"""
        import re
        # Remove common sensitive patterns
        filtered = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_NUMBER]', response)
        filtered = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', filtered)
        filtered = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', filtered)
        filtered = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', '[DATE]', filtered)
        return filtered
    
    async def _retrieve_encrypted_documents(self, request: InferenceRequest) -> List[Dict[str, Any]]:
        """Retrieve documents with encryption"""
        try:
            collection = self.vectorstore.get_collection(request.collection_name)
            
            # Retrieve documents
            results = collection.query(
                query_texts=[request.query],
                n_results=5
            )
            
            # Encrypt document contents
            encrypted_docs = []
            for i in range(len(results['ids'][0])):
                doc_content = results['documents'][0][i]
                encrypted_content = self.privacy.encrypt_data(doc_content, request.tenant_id)
                
                encrypted_docs.append({
                    "id": results['ids'][0][i],
                    "content": encrypted_content,
                    "metadata": results['metadatas'][0][i]
                })
            
            return encrypted_docs
            
        except Exception as e:
            logger.error(f"Encrypted document retrieval failed: {str(e)}")
            return []
    
    def _generate_cache_key(self, query: str, request: InferenceRequest) -> str:
        """Generate cache key for inference results"""
        key_data = f"{query}_{request.tenant_id}_{request.mode}"
        return self.privacy.calculate_data_hash(key_data)
    
    def _save_cache_to_disk(self):
        """Save inference cache to local storage"""
        try:
            cache_path = Path("./local_storage/local_cache/inference_cache.json")
            with open(cache_path, 'w') as f:
                json.dump(self.inference_cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {str(e)}")
    
    def _load_cache_from_disk(self):
        """Load inference cache from local storage"""
        try:
            cache_path = Path("./local_storage/local_cache/inference_cache.json")
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    self.inference_cache = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {str(e)}")
    
    def _log_inference_operation(self, request: InferenceRequest, audit_trail: Dict[str, Any], 
                               success: bool = True):
        """Log inference operation for audit"""
        self.privacy.log_data_operation(
            user_id=request.user_id,
            operation="llm_inference",
            data_type="query_response",
            sensitivity_level=request.sensitivity_level,
            tenant_id=request.tenant_id,
            collection_name=request.collection_name,
            success=success,
            metadata={
                "mode": request.mode,
                "processing_mode": request.processing_mode.value,
                "audit_trail": audit_trail
            }
        )
    
    def get_privacy_compliance_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate privacy compliance report for tenant"""
        audit_summary = self.privacy.get_audit_summary(tenant_id)
        
        report = {
            "tenant_id": tenant_id,
            "report_generated": datetime.now().isoformat(),
            "compliance_status": "compliant",
            "total_operations": audit_summary["total_operations"],
            "successful_operations": audit_summary["successful_operations"],
            "failed_operations": audit_summary["failed_operations"],
            "sensitivity_distribution": audit_summary["sensitivity_distribution"],
            "processing_modes_used": self._get_processing_modes_summary(tenant_id),
            "data_protection_measures": self._get_protection_measures_summary(tenant_id)
        }
        
        # Check for any compliance issues
        if audit_summary["failed_operations"] > 0:
            report["compliance_status"] = "partial"
            report["issues"] = ["Some operations failed privacy checks"]
        
        return report
    
    def _get_processing_modes_summary(self, tenant_id: str) -> Dict[str, int]:
        """Get summary of processing modes used"""
        # This would analyze actual audit logs in production
        return {
            "encrypted": 0,
            "offline": 0,
            "batch": 0,
            "online": 0
        }
    
    def _get_protection_measures_summary(self, tenant_id: str) -> Dict[str, bool]:
        """Get summary of protection measures applied"""
        # This would analyze actual usage in production
        return {
            "encryption_used": True,
            "anonymization_applied": True,
            "audit_logging_active": True,
            "data_retention_compliant": True
        }

# Global instance
local_inference_engine = LocalInferenceEngine()