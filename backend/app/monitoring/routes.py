from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
import asyncio
from datetime import datetime, timedelta

from app.monitoring.models import SystemHealth, Metric, MetricType, Alert, AlertLevel
from app.monitoring.collector import metrics_collector, health_checker
from app.logging.logger import app_logger, audit_logger
from app.auth.auth_middleware import require_role
from app.auth.auth_models import UserRole

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """Get overall system health status"""
    try:
        health = await health_checker.get_system_health()
        app_logger.info("System health check requested")
        return health
    except Exception as e:
        app_logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )

@router.get("/metrics/system")
async def get_system_metrics():
    """Get current system metrics"""
    try:
        metrics = metrics_collector.get_system_metrics()
        app_logger.debug("System metrics requested")
        return metrics
    except Exception as e:
        app_logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )

@router.get("/metrics/application")
async def get_application_metrics():
    """Get current application metrics"""
    try:
        metrics = metrics_collector.get_application_metrics()
        app_logger.debug("Application metrics requested")
        return metrics
    except Exception as e:
        app_logger.error(f"Failed to get application metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application metrics"
        )

@router.get("/metrics/history/{metric_name}")
async def get_metric_history(
    metric_name: str,
    hours: int = 1,
    current_user: UserRole = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """Get historical metrics (admin only)"""
    try:
        history = metrics_collector.get_metrics_history(metric_name, hours)
        app_logger.info(f"Metrics history requested for {metric_name}")
        return {"metric_name": metric_name, "data": history}
    except Exception as e:
        app_logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics history"
        )

@router.get("/alerts")
async def get_alerts(
    level: Optional[AlertLevel] = None,
    unresolved_only: bool = True,
    limit: int = 50,
    current_user: UserRole = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """Get system alerts (admin only)"""
    try:
        # In a real implementation, this would query a database of alerts
        # For now, we'll return a mock response
        alerts = [
            Alert(
                id="alert_001",
                level=AlertLevel.WARNING,
                title="High Memory Usage",
                message="Memory usage is above 80%",
                service="system",
                timestamp=datetime.utcnow() - timedelta(minutes=5)
            ),
            Alert(
                id="alert_002",
                level=AlertLevel.INFO,
                title="New User Registered",
                message="New user account created",
                service="auth",
                timestamp=datetime.utcnow() - timedelta(minutes=10)
            )
        ]
        
        # Filter by level if specified
        if level:
            alerts = [a for a in alerts if a.level == level]
            
        # Filter unresolved if requested
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]
            
        # Limit results
        alerts = alerts[:limit]
        
        app_logger.info("Alerts requested")
        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        app_logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: UserRole = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """Resolve an alert (admin only)"""
    try:
        # In a real implementation, this would update the alert in database
        app_logger.info(f"Alert {alert_id} resolved by {current_user.username}")
        audit_logger.log_user_action(
            user_id=current_user.user_id,
            action="resolved_alert",
            resource=alert_id,
            success=True
        )
        return {"message": f"Alert {alert_id} resolved successfully"}
    except Exception as e:
        app_logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert"
        )

@router.get("/dashboard")
async def get_monitoring_dashboard(
    current_user: UserRole = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """Get comprehensive monitoring dashboard data (admin only)"""
    try:
        # Get all monitoring data
        health = await health_checker.get_system_health()
        system_metrics = metrics_collector.get_system_metrics()
        app_metrics = metrics_collector.get_application_metrics()
        
        # Get recent alerts
        alerts_response = await get_alerts(unresolved_only=True, limit=10)
        
        dashboard_data = {
            "health": health,
            "system_metrics": system_metrics,
            "application_metrics": app_metrics,
            "recent_alerts": alerts_response["alerts"],
            "timestamp": datetime.utcnow()
        }
        
        app_logger.info("Monitoring dashboard requested")
        return dashboard_data
    except Exception as e:
        app_logger.error(f"Failed to get monitoring dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring dashboard"
        )

@router.get("/status/services")
async def get_service_status():
    """Get individual service status"""
    try:
        health = await health_checker.get_system_health()
        service_status = {
            service.service_name: {
                "status": service.status.value,
                "response_time_ms": service.response_time_ms,
                "last_check": service.last_check.isoformat()
            }
            for service in health.services
        }
        return service_status
    except Exception as e:
        app_logger.error(f"Failed to get service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service status"
        )