from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.routes import router
from app.core.config import settings
from app.monitoring.collector import metrics_collector, health_checker
from app.monitoring.alerts import alert_manager
from app.logging.logger import app_logger
import asyncio
import time

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Universal RAG Platform - Secure, local-first intelligence engine",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Background monitoring task
async def monitoring_background_task():
    """Background task for continuous monitoring"""
    while True:
        try:
            # Get system health
            health = await health_checker.get_system_health()
            
            # Check for alerts
            await alert_manager.check_alerts(health)
            
            # Log system metrics periodically
            if int(time.time()) % 60 == 0:  # Every minute
                system_metrics = metrics_collector.get_system_metrics()
                app_logger.info(f"System metrics - CPU: {system_metrics.cpu_usage:.1f}%, "
                              f"Memory: {system_metrics.memory_usage:.1f}%, "
                              f"Disk: {system_metrics.disk_usage:.1f}%")
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            app_logger.error(f"Error in monitoring background task: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Start background monitoring
@app.on_event("startup")
async def startup_event():
    """Initialize monitoring on startup"""
    app_logger.info("Starting monitoring system")
    # Start background monitoring task
    asyncio.create_task(monitoring_background_task())

@app.get("/")
async def root():
    return {
        "message": "Universal RAG Platform API",
        "version": settings.VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "backend-api"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )