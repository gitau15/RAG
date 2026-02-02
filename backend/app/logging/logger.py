import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import sys
from pathlib import Path

from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'tenant_id'):
            log_entry["tenant_id"] = record.tenant_id
            
        return json.dumps(log_entry)

class StructuredLogger:
    """Structured logging system with multiple handlers"""
    
    def __init__(self, name: str = "rag_platform"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Console handler (INFO level and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for all logs (rotating)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        json_formatter = JSONFormatter()
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
        
        # Error file handler (separate file for errors)
        error_handler = RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        self.logger.addHandler(error_handler)
        
        # Audit log handler (for security/audit events)
        audit_handler = TimedRotatingFileHandler(
            log_dir / "audit.log",
            when="midnight",
            interval=1,
            backupCount=30
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(json_formatter)
        self.logger.addHandler(audit_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with additional context"""
        # Add context to log record
        extra = {}
        if 'user_id' in kwargs:
            extra['user_id'] = kwargs['user_id']
        if 'request_id' in kwargs:
            extra['request_id'] = kwargs['request_id']
        if 'tenant_id' in kwargs:
            extra['tenant_id'] = kwargs['tenant_id']
            
        self.logger.log(level, message, extra=extra)

class AuditLogger:
    """Specialized logger for audit trails"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Ensure audit handler exists
        if not any(isinstance(h, TimedRotatingFileHandler) and 'audit' in h.baseFilename 
                  for h in self.logger.handlers):
            self._setup_audit_handler()
    
    def _setup_audit_handler(self):
        """Setup audit log handler"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        audit_handler = TimedRotatingFileHandler(
            log_dir / "audit.log",
            when="midnight",
            interval=1,
            backupCount=90  # Keep 90 days of audit logs
        )
        audit_handler.setLevel(logging.INFO)
        json_formatter = JSONFormatter()
        audit_handler.setFormatter(json_formatter)
        self.logger.addHandler(audit_handler)
    
    def log_user_action(self, user_id: str, action: str, resource: str, 
                       success: bool = True, details: Optional[Dict[str, Any]] = None):
        """Log user action for audit trail"""
        message = f"User {user_id} {'successfully' if success else 'failed to'} {action} {resource}"
        extra = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "success": success,
            "details": details or {}
        }
        self.logger.info(message, extra=extra)
    
    def log_security_event(self, event_type: str, description: str, 
                          severity: str = "medium", details: Optional[Dict[str, Any]] = None):
        """Log security-related events"""
        message = f"Security event: {event_type} - {description}"
        extra = {
            "event_type": event_type,
            "description": description,
            "severity": severity,
            "details": details or {}
        }
        self.logger.warning(message, extra=extra)
    
    def log_system_event(self, event_type: str, description: str, 
                        details: Optional[Dict[str, Any]] = None):
        """Log system-level events"""
        message = f"System event: {event_type} - {description}"
        extra = {
            "event_type": event_type,
            "description": description,
            "details": details or {}
        }
        self.logger.info(message, extra=extra)

class PerformanceLogger:
    """Logger for performance metrics and timing"""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.logger.setLevel(logging.INFO)
        
        # Ensure performance handler exists
        if not any('performance' in h.baseFilename for h in self.logger.handlers):
            self._setup_performance_handler()
    
    def _setup_performance_handler(self):
        """Setup performance log handler"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        perf_handler = RotatingFileHandler(
            log_dir / "performance.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        perf_handler.setLevel(logging.INFO)
        json_formatter = JSONFormatter()
        perf_handler.setFormatter(json_formatter)
        self.logger.addHandler(perf_handler)
    
    def log_api_call(self, endpoint: str, method: str, duration: float, 
                    status_code: int, user_id: Optional[str] = None):
        """Log API call performance"""
        message = f"API call: {method} {endpoint} - {status_code} in {duration:.3f}s"
        extra = {
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status_code": status_code,
            "user_id": user_id
        }
        self.logger.info(message, extra=extra)
    
    def log_document_processing(self, document_id: str, processing_time: float, 
                               success: bool = True, error: Optional[str] = None):
        """Log document processing performance"""
        status = "completed" if success else "failed"
        message = f"Document processing {status}: {document_id} in {processing_time:.3f}s"
        extra = {
            "document_id": document_id,
            "processing_time": processing_time,
            "success": success,
            "error": error
        }
        self.logger.info(message, extra=extra)
    
    def log_query_performance(self, query_id: str, query_time: float, 
                             result_count: int, cache_hit: bool = False):
        """Log query performance"""
        message = f"Query executed: {query_id} in {query_time:.3f}s, {result_count} results"
        extra = {
            "query_id": query_id,
            "query_time": query_time,
            "result_count": result_count,
            "cache_hit": cache_hit
        }
        self.logger.info(message, extra=extra)

# Global logger instances
app_logger = StructuredLogger("rag_platform")
audit_logger = AuditLogger()
perf_logger = PerformanceLogger()