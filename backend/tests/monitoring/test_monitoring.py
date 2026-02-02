import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.monitoring.models import (
    MetricType, HealthStatus, Metric, SystemMetrics, 
    ApplicationMetrics, ServiceHealth, SystemHealth, AlertLevel, Alert
)
from app.monitoring.collector import MetricsCollector, HealthChecker
from app.monitoring.alerts import AlertManager, AlertRule

class TestMonitoringModels:
    def test_metric_type_enum(self):
        """Test MetricType enum values"""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"
        
        all_types = list(MetricType)
        assert len(all_types) == 4

    def test_health_status_enum(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"
        
        all_statuses = list(HealthStatus)
        assert len(all_statuses) == 4

    def test_alert_level_enum(self):
        """Test AlertLevel enum values"""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"
        
        all_levels = list(AlertLevel)
        assert len(all_levels) == 4

    def test_metric_creation(self):
        """Test Metric model creation"""
        metric = Metric(
            name="test_metric",
            type=MetricType.GAUGE,
            value=42.5,
            labels={"environment": "test"},
            description="Test metric"
        )
        
        assert metric.name == "test_metric"
        assert metric.type == MetricType.GAUGE
        assert metric.value == 42.5
        assert metric.labels == {"environment": "test"}
        assert metric.description == "Test metric"
        assert isinstance(metric.timestamp, datetime)

    def test_system_metrics_creation(self):
        """Test SystemMetrics model creation"""
        network_io = {"bytes_sent": 1000.0, "bytes_received": 2000.0}
        
        metrics = SystemMetrics(
            cpu_usage=75.5,
            memory_usage=60.2,
            disk_usage=45.8,
            network_io=network_io,
            uptime_seconds=3600.0
        )
        
        assert metrics.cpu_usage == 75.5
        assert metrics.memory_usage == 60.2
        assert metrics.disk_usage == 45.8
        assert metrics.network_io == network_io
        assert metrics.uptime_seconds == 3600.0

    def test_application_metrics_creation(self):
        """Test ApplicationMetrics model creation"""
        metrics = ApplicationMetrics(
            total_requests=1000,
            requests_per_second=5.5,
            average_response_time=0.8,
            error_rate=0.02,
            documents_processed=50,
            documents_failed=2,
            average_processing_time=2.3,
            total_queries=200,
            average_query_time=1.2,
            cache_hit_rate=0.85,
            active_users=15,
            total_users=100
        )
        
        assert metrics.total_requests == 1000
        assert metrics.requests_per_second == 5.5
        assert metrics.average_response_time == 0.8
        assert metrics.error_rate == 0.02
        assert metrics.documents_processed == 50
        assert metrics.documents_failed == 2
        assert metrics.average_processing_time == 2.3
        assert metrics.total_queries == 200
        assert metrics.average_query_time == 1.2
        assert metrics.cache_hit_rate == 0.85
        assert metrics.active_users == 15
        assert metrics.total_users == 100

    def test_service_health_creation(self):
        """Test ServiceHealth model creation"""
        details = {"version": "1.0.0", "endpoint": "/health"}
        
        health = ServiceHealth(
            service_name="test_service",
            status=HealthStatus.HEALTHY,
            response_time_ms=15.5,
            details=details
        )
        
        assert health.service_name == "test_service"
        assert health.status == HealthStatus.HEALTHY
        assert health.response_time_ms == 15.5
        assert health.details == details
        assert isinstance(health.last_check, datetime)

    def test_system_health_creation(self):
        """Test SystemHealth model creation"""
        # Create mock data
        system_metrics = SystemMetrics(
            cpu_usage=50.0, memory_usage=60.0, disk_usage=40.0,
            network_io={"bytes_sent": 1000.0, "bytes_received": 2000.0},
            uptime_seconds=3600.0
        )
        
        app_metrics = ApplicationMetrics(
            total_requests=100, requests_per_second=1.0,
            average_response_time=0.5, error_rate=0.01,
            documents_processed=10, documents_failed=0,
            average_processing_time=1.0, total_queries=50,
            average_query_time=0.3, cache_hit_rate=0.9,
            active_users=5, total_users=20
        )
        
        services = [
            ServiceHealth(
                service_name="api",
                status=HealthStatus.HEALTHY,
                response_time_ms=10.0
            )
        ]
        
        health = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            services=services,
            system_metrics=system_metrics,
            application_metrics=app_metrics
        )
        
        assert health.overall_status == HealthStatus.HEALTHY
        assert len(health.services) == 1
        assert health.services[0].service_name == "api"
        assert health.system_metrics.cpu_usage == 50.0
        assert health.application_metrics.total_requests == 100

    def test_alert_creation(self):
        """Test Alert model creation"""
        metadata = {"threshold": 80, "current_value": 85}
        
        alert = Alert(
            id="alert_123",
            level=AlertLevel.WARNING,
            title="High CPU Usage",
            message="CPU usage exceeded 80%",
            service="system",
            metadata=metadata
        )
        
        assert alert.id == "alert_123"
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "High CPU Usage"
        assert alert.message == "CPU usage exceeded 80%"
        assert alert.service == "system"
        assert alert.metadata == metadata
        assert alert.resolved == False
        assert alert.resolved_at is None
        assert isinstance(alert.timestamp, datetime)

class TestMetricsCollector:
    @pytest.fixture
    def metrics_collector(self):
        """Create MetricsCollector instance for testing"""
        return MetricsCollector()

    def test_initial_state(self, metrics_collector):
        """Test initial state of metrics collector"""
        assert metrics_collector.request_counter == 0
        assert metrics_collector.error_counter == 0
        assert metrics_collector.document_counter == 0
        assert metrics_collector.document_errors == 0
        assert metrics_collector.query_counter == 0
        assert len(metrics_collector.active_users) == 0

    def test_record_request(self, metrics_collector):
        """Test recording API requests"""
        metrics_collector.record_request(0.5, True)
        metrics_collector.record_request(1.2, False)
        metrics_collector.record_request(0.8, True)
        
        assert metrics_collector.request_counter == 3
        assert metrics_collector.error_counter == 1
        assert len(metrics_collector.response_times) == 3

    def test_record_document_processing(self, metrics_collector):
        """Test recording document processing"""
        metrics_collector.record_document_processing(2.5, True)
        metrics_collector.record_document_processing(3.0, False)
        metrics_collector.record_document_processing(1.8, True)
        
        assert metrics_collector.document_counter == 3
        assert metrics_collector.document_errors == 1
        assert len(metrics_collector.processing_times) == 3

    def test_record_query(self, metrics_collector):
        """Test recording queries"""
        metrics_collector.record_query(0.3)
        metrics_collector.record_query(0.7)
        metrics_collector.record_query(0.5)
        
        assert metrics_collector.query_counter == 3
        assert len(metrics_collector.response_times) == 3

    def test_active_users_management(self, metrics_collector):
        """Test active users management"""
        metrics_collector.add_active_user("user_1")
        metrics_collector.add_active_user("user_2")
        metrics_collector.add_active_user("user_1")  # Duplicate
        
        assert len(metrics_collector.active_users) == 2
        assert "user_1" in metrics_collector.active_users
        assert "user_2" in metrics_collector.active_users
        
        metrics_collector.remove_active_user("user_1")
        assert len(metrics_collector.active_users) == 1
        assert "user_1" not in metrics_collector.active_users

    def test_get_system_metrics(self, metrics_collector):
        """Test getting system metrics"""
        metrics = metrics_collector.get_system_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert 0 <= metrics.cpu_usage <= 100
        assert 0 <= metrics.memory_usage <= 100
        assert 0 <= metrics.disk_usage <= 100
        assert metrics.uptime_seconds >= 0
        assert "bytes_sent" in metrics.network_io
        assert "bytes_received" in metrics.network_io

    def test_get_application_metrics(self, metrics_collector):
        """Test getting application metrics"""
        # Add some test data
        metrics_collector.record_request(0.5, True)
        metrics_collector.record_request(1.0, False)
        metrics_collector.record_document_processing(2.0, True)
        metrics_collector.record_query(0.3)
        metrics_collector.add_active_user("user_1")
        
        metrics = metrics_collector.get_application_metrics()
        
        assert isinstance(metrics, ApplicationMetrics)
        assert metrics.total_requests == 2
        assert metrics.error_rate == 0.5  # 1 error out of 2 requests
        assert metrics.documents_processed == 1
        assert metrics.documents_failed == 0
        assert metrics.total_queries == 1
        assert metrics.active_users == 1

    def test_add_metric(self, metrics_collector):
        """Test adding metrics to history"""
        metric = Metric(
            name="test_metric",
            type=MetricType.GAUGE,
            value=42.0
        )
        
        metrics_collector.add_metric(metric)
        history = metrics_collector.get_metrics_history("test_metric")
        
        assert len(history) == 1
        assert history[0].name == "test_metric"
        assert history[0].value == 42.0

    def test_metrics_history_limit(self, metrics_collector):
        """Test metrics history limit"""
        # Add more metrics than the history limit
        for i in range(1005):
            metric = Metric(
                name="limited_metric",
                type=MetricType.COUNTER,
                value=float(i)
            )
            metrics_collector.add_metric(metric)
        
        history = metrics_collector.get_metrics_history("limited_metric")
        # Should be limited to 1000 entries
        assert len(history) <= 1000

class TestHealthChecker:
    @pytest.fixture
    def health_checker(self):
        """Create HealthChecker instance for testing"""
        collector = MetricsCollector()
        return HealthChecker(collector)

    @pytest.mark.asyncio
    async def test_get_system_health(self, health_checker):
        """Test getting system health"""
        health = await health_checker.get_system_health()
        
        assert isinstance(health, SystemHealth)
        assert health.overall_status in list(HealthStatus)
        assert len(health.services) > 0
        assert isinstance(health.system_metrics, SystemMetrics)
        assert isinstance(health.application_metrics, ApplicationMetrics)

    @pytest.mark.asyncio
    async def test_service_health_checks(self, health_checker):
        """Test individual service health checks"""
        # Test database check
        db_health = await health_checker._check_database()
        assert isinstance(db_health, ServiceHealth)
        assert db_health.service_name == "database"
        assert db_health.status in list(HealthStatus)
        
        # Test vector store check
        vector_health = await health_checker._check_vector_store()
        assert isinstance(vector_health, ServiceHealth)
        assert vector_health.service_name == "vector_store"
        assert vector_health.status in list(HealthStatus)
        
        # Test LLM service check
        llm_health = await health_checker._check_llm_service()
        assert isinstance(llm_health, ServiceHealth)
        assert llm_health.service_name == "llm_service"
        assert llm_health.status in list(HealthStatus)
        
        # Test API check
        api_health = await health_checker._check_api()
        assert isinstance(api_health, ServiceHealth)
        assert api_health.service_name == "api"
        assert api_health.status in list(HealthStatus)

class TestAlertManager:
    @pytest.fixture
    def alert_manager(self):
        """Create AlertManager instance for testing"""
        return AlertManager()

    def test_alert_rule_creation(self):
        """Test AlertRule creation"""
        def test_condition(metrics):
            return True
            
        rule = AlertRule(
            name="test_rule",
            level=AlertLevel.WARNING,
            condition=test_condition,
            message_template="Test alert",
            service="test"
        )
        
        assert rule.name == "test_rule"
        assert rule.level == AlertLevel.WARNING
        assert rule.condition == test_condition
        assert rule.message_template == "Test alert"
        assert rule.service == "test"
        assert rule.enabled == True

    def test_add_remove_rule(self, alert_manager):
        """Test adding and removing alert rules"""
        initial_count = len(alert_manager.alert_rules)
        
        # Add rule
        def condition(metrics):
            return False
        rule = AlertRule("test_rule", AlertLevel.INFO, condition, "Test", "test")
        alert_manager.add_rule(rule)
        
        assert len(alert_manager.alert_rules) == initial_count + 1
        
        # Remove rule
        alert_manager.remove_rule("test_rule")
        assert len(alert_manager.alert_rules) == initial_count

    @pytest.mark.asyncio
    async def test_alert_generation(self, alert_manager):
        """Test alert generation"""
        # Create mock system health with issues
        system_metrics = SystemMetrics(
            cpu_usage=85.0,  # Should trigger high CPU alert
            memory_usage=60.0,
            disk_usage=40.0,
            network_io={"bytes_sent": 1000.0, "bytes_received": 2000.0},
            uptime_seconds=3600.0
        )
        
        app_metrics = ApplicationMetrics(
            total_requests=100,
            requests_per_second=1.0,
            average_response_time=0.5,
            error_rate=0.01,
            documents_processed=10,
            documents_failed=0,
            average_processing_time=1.0,
            total_queries=50,
            average_query_time=0.3,
            cache_hit_rate=0.9,
            active_users=5,
            total_users=20
        )
        
        services = [
            ServiceHealth(
                service_name="api",
                status=HealthStatus.HEALTHY,
                response_time_ms=10.0
            )
        ]
        
        health = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            services=services,
            system_metrics=system_metrics,
            application_metrics=app_metrics
        )
        
        # Check alerts
        await alert_manager.check_alerts(health)
        
        # Should have generated alerts for high CPU usage
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        
        # Check that we have a high CPU alert
        cpu_alerts = [a for a in active_alerts if "high_cpu_usage" in a.id]
        assert len(cpu_alerts) > 0

    def test_alert_resolution(self, alert_manager):
        """Test alert resolution"""
        # Create a mock alert
        alert = Alert(
            id="test_alert_123",
            level=AlertLevel.WARNING,
            title="Test Alert",
            message="Test message",
            service="test"
        )
        
        # Add to active alerts manually
        alert_manager.active_alerts[alert.id] = alert
        
        # Verify it's active
        assert alert.id in alert_manager.active_alerts
        
        # Resolve the alert
        result = alert_manager.resolve_alert(alert.id)
        assert result == True
        
        # Verify it's no longer active
        assert alert.id not in alert_manager.active_alerts
        assert alert.resolved == True
        assert alert.resolved_at is not None

    def test_alert_stats(self, alert_manager):
        """Test alert statistics"""
        # Add some mock alerts
        alert1 = Alert(
            id="critical_1",
            level=AlertLevel.CRITICAL,
            title="Critical Alert",
            message="Critical message",
            service="system"
        )
        alert2 = Alert(
            id="error_1",
            level=AlertLevel.ERROR,
            title="Error Alert",
            message="Error message",
            service="api"
        )
        alert3 = Alert(
            id="warning_1",
            level=AlertLevel.WARNING,
            title="Warning Alert",
            message="Warning message",
            service="database"
        )
        
        # Add to active alerts
        alert_manager.active_alerts.update({
            alert1.id: alert1,
            alert2.id: alert2,
            alert3.id: alert3
        })
        
        # Get stats
        stats = alert_manager.get_alert_stats()
        
        assert stats["total_active"] == 3
        assert stats["critical_count"] == 1
        assert stats["error_count"] == 1
        assert stats["warning_count"] == 1