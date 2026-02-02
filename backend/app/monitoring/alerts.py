import asyncio
from typing import List, Dict, Callable, Any
from datetime import datetime
import logging
from enum import Enum

from app.monitoring.models import Alert, AlertLevel, SystemHealth, HealthStatus
from app.logging.logger import app_logger

logger = logging.getLogger(__name__)

class AlertRule:
    """Defines conditions for generating alerts"""
    
    def __init__(self, name: str, level: AlertLevel, condition: Callable, 
                 message_template: str, service: str):
        self.name = name
        self.level = level
        self.condition = condition
        self.message_template = message_template
        self.service = service
        self.enabled = True
        self.last_triggered = None

class AlertManager:
    """Manages alert generation and notification"""
    
    def __init__(self):
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        # High CPU usage alert
        cpu_rule = AlertRule(
            name="high_cpu_usage",
            level=AlertLevel.WARNING,
            condition=lambda metrics: metrics.system_metrics.cpu_usage > 80,
            message_template="CPU usage is {cpu_usage}%, exceeding threshold of 80%",
            service="system"
        )
        self.add_rule(cpu_rule)
        
        # High memory usage alert
        memory_rule = AlertRule(
            name="high_memory_usage",
            level=AlertLevel.WARNING,
            condition=lambda metrics: metrics.system_metrics.memory_usage > 85,
            message_template="Memory usage is {memory_usage}%, exceeding threshold of 85%",
            service="system"
        )
        self.add_rule(memory_rule)
        
        # High error rate alert
        error_rate_rule = AlertRule(
            name="high_error_rate",
            level=AlertLevel.ERROR,
            condition=lambda metrics: metrics.application_metrics.error_rate > 0.05,
            message_template="Error rate is {error_rate:.2%}, exceeding threshold of 5%",
            service="api"
        )
        self.add_rule(error_rate_rule)
        
        # Service unhealthy alert
        service_health_rule = AlertRule(
            name="service_unhealthy",
            level=AlertLevel.CRITICAL,
            condition=lambda health: any(s.status == HealthStatus.UNHEALTHY for s in health.services),
            message_template="Service {unhealthy_services} is reporting unhealthy status",
            service="system"
        )
        self.add_rule(service_health_rule)
        
        # Slow response time alert
        response_time_rule = AlertRule(
            name="slow_response_time",
            level=AlertLevel.WARNING,
            condition=lambda metrics: metrics.application_metrics.average_response_time > 2.0,
            message_template="Average response time is {response_time:.2f}s, exceeding threshold of 2s",
            service="api"
        )
        self.add_rule(response_time_rule)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule"""
        self.alert_rules = [rule for rule in self.alert_rules if rule.name != rule_name]
        logger.info(f"Removed alert rule: {rule_name}")
    
    def add_notification_handler(self, handler: Callable):
        """Add a notification handler"""
        self.notification_handlers.append(handler)
    
    async def check_alerts(self, system_health: SystemHealth):
        """Check all alert rules against current system state"""
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
                
            try:
                # Check if condition is met
                if rule.condition(system_health):
                    # Generate alert
                    alert = self._generate_alert(rule, system_health)
                    if alert.id not in self.active_alerts:
                        await self._trigger_alert(alert)
                        
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")
    
    def _generate_alert(self, rule: AlertRule, system_health: SystemHealth) -> Alert:
        """Generate alert from rule and system state"""
        # Format message with system data
        message_data = {}
        if "cpu_usage" in rule.message_template:
            message_data["cpu_usage"] = system_health.system_metrics.cpu_usage
        if "memory_usage" in rule.message_template:
            message_data["memory_usage"] = system_health.system_metrics.memory_usage
        if "error_rate" in rule.message_template:
            message_data["error_rate"] = system_health.application_metrics.error_rate
        if "response_time" in rule.message_template:
            message_data["response_time"] = system_health.application_metrics.average_response_time
        if "unhealthy_services" in rule.message_template:
            unhealthy_services = [s.service_name for s in system_health.services 
                                if s.status == HealthStatus.UNHEALTHY]
            message_data["unhealthy_services"] = ", ".join(unhealthy_services)
        
        message = rule.message_template.format(**message_data)
        
        # Create alert ID
        alert_id = f"{rule.name}_{int(datetime.utcnow().timestamp())}"
        
        return Alert(
            id=alert_id,
            level=rule.level,
            title=f"Alert: {rule.name}",
            message=message,
            service=rule.service
        )
    
    async def _trigger_alert(self, alert: Alert):
        """Trigger an alert and notify handlers"""
        # Add to active alerts
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # Log the alert
        logger.log(
            logging.ERROR if alert.level == AlertLevel.CRITICAL else logging.WARNING,
            f"ALERT {alert.level.value.upper()}: {alert.title} - {alert.message}"
        )
        
        # Notify handlers
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
        
        # Keep alert history to reasonable size
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get recent alert history"""
        return self.alert_history[-limit:] if len(self.alert_history) > limit else self.alert_history
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert_id}")
            return True
        return False
    
    def get_alert_stats(self) -> Dict[str, int]:
        """Get alert statistics"""
        stats = {
            "total_active": len(self.active_alerts),
            "total_history": len(self.alert_history),
            "critical_count": len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]),
            "error_count": len([a for a in self.active_alerts.values() if a.level == AlertLevel.ERROR]),
            "warning_count": len([a for a in self.active_alerts.values() if a.level == AlertLevel.WARNING]),
        }
        return stats

class ConsoleNotificationHandler:
    """Simple console notification handler for development"""
    
    async def __call__(self, alert: Alert):
        """Handle alert notification"""
        print(f"\n🔔 ALERT: {alert.level.value.upper()}")
        print(f"   Title: {alert.title}")
        print(f"   Message: {alert.message}")
        print(f"   Service: {alert.service}")
        print(f"   Time: {alert.timestamp}")
        print("-" * 50)

# Global alert manager instance
alert_manager = AlertManager()

# Add console notification handler for development
alert_manager.add_notification_handler(ConsoleNotificationHandler())