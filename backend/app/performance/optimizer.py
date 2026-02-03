import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import logging
from dataclasses import dataclass
from enum import Enum

from app.monitoring.collector import metrics_collector
from app.logging.logger import perf_logger
from app.retrieval.retrieval_config import retrieval_config_manager, RetrievalParameters

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """Optimization strategies for performance improvement"""
    LATENCY_OPTIMIZED = "latency_optimized"
    BALANCED = "balanced"
    THROUGHPUT_OPTIMIZED = "throughput_optimized"
    AGGRESSIVE = "aggressive"

@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization"""
    query_time: float
    retrieval_time: float
    generation_time: float
    total_time: float
    tokens_generated: int
    context_length: int
    retrieved_documents: int

class PerformanceOptimizer:
    """Performance optimizer for sub-8-second responses"""
    
    def __init__(self):
        self.target_response_time = 8.0  # 8 seconds target
        self.latency_threshold = 0.1  # 100ms for quick operations
        self.aggressive_timeout = 5.0  # 5 seconds for aggressive optimization
        self.performance_history: List[PerformanceMetrics] = []
        
    def optimize_query_parameters(self, params: RetrievalParameters, 
                                 current_performance: PerformanceMetrics = None) -> RetrievalParameters:
        """Optimize retrieval parameters for faster response"""
        # If we have performance history, adapt parameters accordingly
        if current_performance and current_performance.total_time > self.target_response_time:
            # Optimize for speed if we're exceeding target
            params = retrieval_config_manager.optimize_for_latency(params)
        else:
            # Use moderate settings for balanced performance
            params.k = min(6, params.k)  # Limit to 6 for speed
            params.similarity_threshold = max(0.3, params.similarity_threshold)  # Maintain minimum precision
        
        return params
    
    def apply_timeout(self, timeout: float = 8.0):
        """Decorator to enforce timeout on operations"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    # Use asyncio.wait_for to enforce timeout
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    return result
                except asyncio.TimeoutError:
                    logger.warning(f"Function {func.__name__} timed out after {timeout}s")
                    raise TimeoutError(f"Operation timed out after {timeout} seconds")
            return wrapper
        return decorator
    
    def adaptive_retrieval(self, min_k: int = 2, max_k: int = 6):
        """Adaptive retrieval that adjusts based on document availability"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    # Try with minimum k first
                    kwargs['k'] = min_k
                    result = await func(*args, **kwargs)
                    
                    # If response is too fast, we might want more context
                    elapsed = time.time() - start_time
                    if elapsed < 2.0 and kwargs.get('k', min_k) < max_k:
                        # Increase k for better quality if we have time
                        kwargs['k'] = min(max_k, kwargs.get('k', min_k) + 2)
                        result = await func(*args, **kwargs)
                    
                    return result
                except Exception as e:
                    logger.error(f"Adaptive retrieval failed: {e}")
                    raise
            return wrapper
        return decorator
    
    def cache_fallback(self, cache_func: Callable, fallback_func: Callable):
        """Use cache with fallback to computation"""
        async def wrapper(*args, **kwargs):
            try:
                # Try cache first
                cached_result = cache_func(*args, **kwargs)
                if cached_result is not None:
                    return cached_result
            except Exception:
                logger.debug("Cache miss or error, proceeding with computation")
            
            # Fallback to computation
            return await fallback_func(*args, **kwargs)
        return wrapper
    
    def parallel_execution(self, tasks: List[Callable], timeout: float = 6.0):
        """Execute multiple tasks in parallel with timeout"""
        async def execute_parallel():
            start_time = time.time()
            try:
                # Create tasks
                coroutines = [task() for task in tasks]
                results = await asyncio.wait_for(
                    asyncio.gather(*coroutines, return_exceptions=True),
                    timeout=timeout
                )
                return results
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.warning(f"Parallel execution timed out after {elapsed:.2f}s")
                # Return partial results if any completed
                raise TimeoutError(f"Parallel execution timed out after {timeout}s")
        return execute_parallel()
    
    def early_stopping(self, generator_func: Callable, 
                      time_limit: float = 6.0, 
                      token_limit: int = 1000):
        """Apply early stopping to generators"""
        async def wrapped_generator(*args, **kwargs):
            start_time = time.time()
            tokens_generated = 0
            
            async for item in generator_func(*args, **kwargs):
                current_time = time.time()
                
                # Check time limit
                if current_time - start_time > time_limit:
                    logger.info(f"Early stopping due to time limit ({time_limit}s reached)")
                    break
                
                # Check token limit
                if hasattr(item, '__len__'):
                    tokens_generated += len(str(item).split())
                else:
                    tokens_generated += len(str(item).split())
                
                if tokens_generated > token_limit:
                    logger.info(f"Early stopping due to token limit ({token_limit} tokens)")
                    break
                
                yield item
        return wrapped_generator

class QueryOptimizer:
    """Optimizes query processing for performance"""
    
    def __init__(self):
        self.optimizer = PerformanceOptimizer()
        self.response_cache = {}  # Simple in-memory cache
        
    def get_cache_key(self, query: str, collection: str, mode: str) -> str:
        """Generate cache key for query"""
        return f"{query[:50]}_{collection}_{mode}"
    
    def is_cacheable(self, query: str) -> bool:
        """Determine if query is cacheable"""
        # Don't cache queries with personal/real-time info
        non_cacheable_keywords = [
            'my', 'current', 'today', 'now', 'real-time', 'live',
            'personal', 'account', 'user', 'private'
        ]
        query_lower = query.lower()
        return not any(keyword in query_lower for keyword in non_cacheable_keywords)
    
    async def optimize_and_execute(self, query: str, collection_name: str, 
                                  mode: str, k: int = 4) -> Dict[str, Any]:
        """Optimize and execute query with performance considerations"""
        start_time = time.time()
        
        # Check cache first
        cache_key = self.get_cache_key(query, collection_name, mode)
        if self.is_cacheable(query) and cache_key in self.response_cache:
            cached_response = self.response_cache[cache_key]
            cache_time = time.time() - start_time
            perf_logger.log_api_call(
                endpoint="/api/v1/query",
                method="POST",
                duration=cache_time,
                status_code=200,
                user_id="cached"
            )
            metrics_collector.record_request(cache_time, True)
            return cached_response
        
        # Apply optimizations
        retrieval_params = retrieval_config_manager.create_custom_config(
            k=k,
            collection_name=collection_name,
            mode=mode
        )
        
        # Optimize parameters based on performance target
        optimized_params = self.optimizer.optimize_query_parameters(retrieval_params)
        
        # Track performance
        retrieval_start = time.time()
        # This would call the actual retrieval function
        # For now, we'll simulate with placeholders
        retrieved_docs = []  # Placeholder - would call actual retrieval
        retrieval_time = time.time() - retrieval_start
        
        generation_start = time.time()
        # This would call the actual generation function
        response = f"Simulated response for query: {query[:50]}..."  # Placeholder
        generation_time = time.time() - generation_start
        
        total_time = time.time() - start_time
        
        # Cache the result if it's cacheable
        if self.is_cacheable(query) and total_time < 2.0:  # Only cache fast responses
            self.response_cache[cache_key] = response
        
        # Log performance
        perf_logger.log_query_performance(
            query_id=cache_key[:10],
            query_time=total_time,
            result_count=len(retrieved_docs),
            cache_hit=cache_key in self.response_cache
        )
        
        # Record metrics
        metrics_collector.record_request(total_time, True)
        
        return {
            "response": response,
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": total_time,
            "optimized": True
        }

class DocumentProcessorOptimizer:
    """Optimizes document processing for performance"""
    
    def __init__(self):
        self.optimizer = PerformanceOptimizer()
        self.processing_cache = {}
        
    def optimize_chunk_size(self, document_length: int) -> int:
        """Optimize chunk size based on document length"""
        if document_length < 1000:  # Small document
            return 256  # Smaller chunks for better context
        elif document_length < 10000:  # Medium document
            return 512  # Balanced chunks
        else:  # Large document
            return 1024  # Larger chunks for performance
    
    def optimize_embedding_batch_size(self) -> int:
        """Optimize batch size for embedding generation"""
        # Adjust based on system resources
        return 32  # Conservative batch size for performance
    
    async def parallel_process_chunks(self, chunks: List[str], 
                                   process_func: Callable) -> List[Any]:
        """Process document chunks in parallel"""
        semaphore = asyncio.Semaphore(4)  # Limit concurrent operations
        
        async def process_with_semaphore(chunk):
            async with semaphore:
                return await process_func(chunk)
        
        tasks = [process_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=30.0  # 30 second timeout for processing
        )
        return results

class SystemPerformanceMonitor:
    """Monitors system performance and applies optimizations"""
    
    def __init__(self):
        self.optimizer = PerformanceOptimizer()
        self.last_optimization = time.time()
        self.optimization_interval = 60  # seconds
        
    async def should_optimize(self) -> bool:
        """Determine if optimization should be applied"""
        current_time = time.time()
        if current_time - self.last_optimization > self.optimization_interval:
            # Check recent performance metrics
            # This would integrate with the metrics collector
            recent_metrics = metrics_collector.response_times  # Last N responses
            if recent_metrics and len(recent_metrics) >= 5:
                avg_time = sum(recent_metrics) / len(recent_metrics)
                if avg_time > 6.0:  # If average response time > 6s, optimize
                    return True
            self.last_optimization = current_time
        return False
    
    def apply_system_wide_optimizations(self):
        """Apply system-wide performance optimizations"""
        # This would adjust system parameters based on load
        logger.info("Applying system-wide performance optimizations")
        # Could adjust:
        # - Connection pool sizes
        # - Cache sizes
        # - Timeout values
        # - Batch processing sizes

# Global instances
performance_optimizer = PerformanceOptimizer()
query_optimizer = QueryOptimizer()
document_processor_optimizer = DocumentProcessorOptimizer()
system_monitor = SystemPerformanceMonitor()