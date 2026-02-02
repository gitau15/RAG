from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class MetricType(Enum):
    """Types of metrics that can be collected"""
    COUNTER = "counter"      # Cumulative count (e.g., total requests)
    GAUGE = "gauge"         # Instantaneous value (e.g., current memory usage)
    HISTOGRAM = "histogram" # Distribution of values (e.g., request duration)
    SUMMARY = "summary"     # Quantile-based metrics

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class Metric(BaseModel):
    """Base metric model"""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = {}
    timestamp: datetime = datetime.utcnow()
    description: Optional[str] = None

class SystemMetrics(BaseModel):
    """System-level metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]  # bytes_sent, bytes_received
    uptime_seconds: float
    timestamp: datetime = datetime.utcnow()

class ApplicationMetrics(BaseModel):
    """Application-specific metrics"""
    # API Metrics
    total_requests: int
    requests_per_second: float
    average_response_time: float
    error_rate: float
    
    # Document Processing Metrics
    documents_processed: int
    documents_failed: int
    average_processing_time: float
    
    # Query Metrics
    total_queries: int
    average_query_time: float
    cache_hit_rate: float
    
    # User Metrics
    active_users: int
    total_users: int
    
    timestamp: datetime = datetime.utcnow()

class ServiceHealth(BaseModel):
    """Health status of individual services"""
    service_name: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    last_check: datetime = datetime.utcnow()
    details: Optional[Dict[str, Any]] = None

class SystemHealth(BaseModel):
    """Overall system health"""
    overall_status: HealthStatus
    services: List[ServiceHealth]
    system_metrics: SystemMetrics
    application_metrics: ApplicationMetrics
    timestamp: datetime = datetime.utcnow()
    last_updated: datetime = datetime.utcnow()

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class Alert(BaseModel):
    """Alert model"""
    id: str
    level: AlertLevel
    title: str
    message: str
    service: str
    timestamp: datetime = datetime.utcnow()
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None