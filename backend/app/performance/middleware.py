import time
import asyncio
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
import logging

from app.performance.optimizer import performance_optimizer, query_optimizer
from app.logging.logger import perf_logger, app_logger
from app.monitoring.collector import metrics_collector

logger = logging.getLogger(__name__)

class PerformanceMiddleware:
    """Middleware to optimize performance and enforce response time targets"""
    
    def __init__(self):
        self.target_response_time = 8.0  # 8 seconds maximum
    
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.time()
        
        # Skip optimization for health checks and monitoring endpoints
        if request.url.path in ["/health", "/monitoring/health"]:
            response = await call_next(request)
            return response
        
        # Add timeout enforcement to the request
        try:
            # Set timeout based on remaining time to meet target
            remaining_time = self.target_response_time - (time.time() - start_time)
            timeout = min(remaining_time, self.target_response_time)
            
            # Apply timeout to the call_next function
            response = await asyncio.wait_for(call_next(request), timeout=timeout)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Log performance
            perf_logger.log_api_call(
                endpoint=request.url.path,
                method=request.method,
                duration=response_time,
                status_code=response.status_code if hasattr(response, 'status_code') else 200,
                user_id=request.headers.get('user-id', 'anonymous')
            )
            
            # Record metrics
            metrics_collector.record_request(response_time, True)
            
            # Log warning if response time exceeds target
            if response_time > self.target_response_time:
                app_logger.warning(
                    f"Response time exceeded target: {response_time:.2f}s > {self.target_response_time}s",
                    request_path=request.url.path,
                    request_method=request.method
                )
            
            return response
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            app_logger.error(
                f"Request timed out after {response_time:.2f}s",
                request_path=request.url.path,
                request_method=request.method
            )
            
            # Log timeout as an error
            perf_logger.log_api_call(
                endpoint=request.url.path,
                method=request.method,
                duration=response_time,
                status_code=408,  # Request Timeout
                user_id=request.headers.get('user-id', 'anonymous')
            )
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=408,
                content={"error": "Request timeout", "message": "Request took too long to process"}
            )
        except Exception as e:
            response_time = time.time() - start_time
            app_logger.error(f"Request failed: {str(e)}")
            
            # Log failure
            perf_logger.log_api_call(
                endpoint=request.url.path,
                method=request.method,
                duration=response_time,
                status_code=500,
                user_id=request.headers.get('user-id', 'anonymous')
            )
            
            metrics_collector.record_request(response_time, False)
            raise

# Initialize the middleware
performance_middleware = PerformanceMiddleware()