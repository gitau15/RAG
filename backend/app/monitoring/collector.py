import psutil
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from collections import defaultdict, deque

from app.monitoring.models import (
    SystemMetrics, ApplicationMetrics, ServiceHealth, 
    SystemHealth, HealthStatus, Metric, MetricType
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and manages system and application metrics"""
    
    def __init__(self):
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.start_time = time.time()
        self.request_counter = 0
        self.error_counter = 0
        self.document_counter = 0
        self.document_errors = 0
        self.query_counter = 0
        self.response_times = deque(maxlen=1000)
        self.processing_times = deque(maxlen=1000)
        self.active_users = set()
        
    def record_request(self, response_time: float, success: bool = True):
        """Record an API request"""
        self.request_counter += 1
        self.response_times.append(response_time)
        if not success:
            self.error_counter += 1
            
    def record_document_processing(self, processing_time: float, success: bool = True):
        """Record document processing"""
        self.document_counter += 1
        self.processing_times.append(processing_time)
        if not success:
            self.document_errors += 1
            
    def record_query(self, query_time: float):
        """Record a query"""
        self.query_counter += 1
        self.response_times.append(query_time)
        
    def add_active_user(self, user_id: str):
        """Add active user"""
        self.active_users.add(user_id)
        
    def remove_active_user(self, user_id: str):
        """Remove active user"""
        self.active_users.discard(user_id)
        
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": float(net_io.bytes_sent),
                "bytes_received": float(net_io.bytes_recv)
            }
            
            # Uptime
            uptime = time.time() - self.start_time
            
            return SystemMetrics(
                cpu_usage=cpu_percent,
                memory_usage=memory_percent,
                disk_usage=disk_percent,
                network_io=network_io,
                uptime_seconds=uptime
            )
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={"bytes_sent": 0.0, "bytes_received": 0.0},
                uptime_seconds=0.0
            )
    
    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics"""
        # Calculate rates and averages
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        error_rate = (self.error_counter / self.request_counter) if self.request_counter > 0 else 0
        requests_per_second = self.request_counter / (time.time() - self.start_time)
        cache_hit_rate = 0.0  # Would be implemented with actual cache
        
        return ApplicationMetrics(
            total_requests=self.request_counter,
            requests_per_second=requests_per_second,
            average_response_time=avg_response_time,
            error_rate=error_rate,
            documents_processed=self.document_counter,
            documents_failed=self.document_errors,
            average_processing_time=avg_processing_time,
            total_queries=self.query_counter,
            average_query_time=avg_response_time,
            cache_hit_rate=cache_hit_rate,
            active_users=len(self.active_users),
            total_users=len(self.active_users)  # This would be from user database in real implementation
        )
    
    def add_metric(self, metric: Metric):
        """Add a metric to history"""
        self.metrics_history[metric.name].append(metric)
        
    def get_metrics_history(self, metric_name: str, hours: int = 1) -> List[Metric]:
        """Get metrics history for a specific metric"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [m for m in self.metrics_history[metric_name] if m.timestamp >= cutoff_time]

class HealthChecker:
    """Checks health of various system components"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.service_checks = {
            "database": self._check_database,
            "vector_store": self._check_vector_store,
            "llm_service": self._check_llm_service,
            "api": self._check_api
        }
        
    async def _check_database(self) -> ServiceHealth:
        """Check database health"""
        try:
            # In a real implementation, this would check actual database connection
            # For now, we'll simulate based on metrics
            metrics = self.metrics_collector.get_system_metrics()
            if metrics.memory_usage > 95:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
                
            return ServiceHealth(
                service_name="database",
                status=status,
                response_time_ms=5.0,  # Simulated
                details={"memory_usage": f"{metrics.memory_usage:.1f}%"}
            )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return ServiceHealth(
                service_name="database",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e)}
            )
    
    async def _check_vector_store(self) -> ServiceHealth:
        """Check vector store health"""
        try:
            # Simulate vector store check
            app_metrics = self.metrics_collector.get_application_metrics()
            if app_metrics.documents_failed > app_metrics.documents_processed * 0.1:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
                
            return ServiceHealth(
                service_name="vector_store",
                status=status,
                response_time_ms=15.0,  # Simulated
                details={
                    "documents_processed": app_metrics.documents_processed,
                    "documents_failed": app_metrics.documents_failed
                }
            )
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return ServiceHealth(
                service_name="vector_store",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e)}
            )
    
    async def _check_llm_service(self) -> ServiceHealth:
        """Check LLM service health"""
        try:
            # Simulate LLM service check
            app_metrics = self.metrics_collector.get_application_metrics()
            if app_metrics.average_query_time > 10.0:  # 10 seconds
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
                
            return ServiceHealth(
                service_name="llm_service",
                status=status,
                response_time_ms=app_metrics.average_query_time * 1000,
                details={"average_query_time": f"{app_metrics.average_query_time:.2f}s"}
            )
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return ServiceHealth(
                service_name="llm_service",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e)}
            )
    
    async def _check_api(self) -> ServiceHealth:
        """Check API health"""
        try:
            app_metrics = self.metrics_collector.get_application_metrics()
            if app_metrics.error_rate > 0.05:  # 5% error rate
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
                
            return ServiceHealth(
                service_name="api",
                status=status,
                response_time_ms=app_metrics.average_response_time * 1000,
                details={
                    "total_requests": app_metrics.total_requests,
                    "error_rate": f"{app_metrics.error_rate:.2%}"
                }
            )
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return ServiceHealth(
                service_name="api",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e)}
            )
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health"""
        try:
            # Run all health checks concurrently
            health_checks = await asyncio.gather(*[
                check_func() for check_func in self.service_checks.values()
            ])
            
            # Determine overall status
            statuses = [check.status for check in health_checks]
            if all(s == HealthStatus.HEALTHY for s in statuses):
                overall_status = HealthStatus.HEALTHY
            elif any(s == HealthStatus.UNHEALTHY for s in statuses):
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.DEGRADED
            
            return SystemHealth(
                overall_status=overall_status,
                services=health_checks,
                system_metrics=self.metrics_collector.get_system_metrics(),
                application_metrics=self.metrics_collector.get_application_metrics()
            )
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return SystemHealth(
                overall_status=HealthStatus.UNKNOWN,
                services=[],
                system_metrics=self.metrics_collector.get_system_metrics(),
                application_metrics=self.metrics_collector.get_application_metrics()
            )

# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker(metrics_collector)