"""
Performance Tuning Configuration for Sub-8-Second Response Times
==============================================================

This configuration optimizes the RAG platform for sub-8-second response times
by adjusting various system parameters and timeouts.
"""

import os
from typing import Dict, Any

# Performance Target Configuration
PERFORMANCE_TARGETS = {
    "max_response_time": 8.0,  # Maximum response time in seconds
    "max_ingestion_time": 60.0,  # Maximum ingestion time in seconds
    "min_throughput": 10,  # Minimum requests per minute
    "max_concurrency": 10,  # Maximum concurrent requests
}

# Timeout Configuration
TIMEOUT_CONFIG = {
    # API Level
    "api_timeout": 7.5,  # Leave buffer for processing overhead
    
    # Document Retrieval
    "retrieval_timeout": 4.0,  # Time to retrieve relevant documents
    "vector_search_timeout": 3.0,  # Time for vector similarity search
    "collection_lookup_timeout": 1.0,  # Time to get collection
    
    # LLM Generation
    "llm_generation_timeout": 6.0,  # Time for LLM to generate response
    "llm_stream_timeout": 10.0,  # Time for streaming responses
    
    # Document Processing
    "embedding_generation_timeout": 30.0,  # Time to generate embeddings
    "document_parsing_timeout": 15.0,  # Time to parse documents
    "chunk_storage_timeout": 10.0,  # Time to store chunks in vector DB
    
    # System Operations
    "health_check_timeout": 2.0,  # Time for health checks
    "database_operation_timeout": 5.0,  # Time for database ops
}

# Optimization Parameters
OPTIMIZATION_PARAMS = {
    # Query Processing
    "max_k_results": 6,  # Maximum number of results to retrieve
    "min_similarity_threshold": 0.3,  # Minimum similarity for relevant results
    "max_context_length": 2000,  # Maximum context length in tokens
    "max_query_complexity": 500,  # Maximum query length in characters
    
    # Document Processing
    "max_chunk_size": 1024,  # Maximum chunk size in characters
    "min_chunk_size": 256,  # Minimum chunk size in characters
    "max_concurrent_ingestion": 3,  # Max concurrent document ingestion
    "batch_size_embeddings": 32,  # Batch size for embedding generation
    
    # Caching
    "cache_ttl_short": 300,  # Short-term cache TTL in seconds (5 minutes)
    "cache_ttl_medium": 3600,  # Medium-term cache TTL in seconds (1 hour)
    "cache_ttl_long": 86400,  # Long-term cache TTL in seconds (24 hours)
    "max_cache_size": 1000,  # Maximum number of cached items
    
    # Memory Management
    "max_memory_usage_percent": 80,  # Maximum memory usage percentage
    "gc_threshold_multiplier": 2.0,  # Garbage collection threshold multiplier
}

# Resource Limits
RESOURCE_LIMITS = {
    "max_upload_size": 50 * 1024 * 1024,  # 50MB max upload size
    "max_concurrent_connections": 100,  # Max concurrent connections
    "max_workers": os.cpu_count(),  # Number of worker processes
    "worker_class": "uvicorn.workers.UvicornWorker",  # Worker class for gunicorn
    "keep_alive": 5,  # Keep-alive timeout in seconds
    "timeout_keep_alive": 5,  # Keep-alive timeout for worker
}

# Performance Monitoring
MONITORING_CONFIG = {
    "metrics_collection_interval": 30,  # Seconds between metrics collection
    "alert_threshold_response_time": 6.0,  # Alert if response time exceeds this
    "alert_threshold_error_rate": 0.05,  # Alert if error rate exceeds this
    "performance_sampling_rate": 0.1,  # Fraction of requests to sample for performance
    "slow_query_threshold": 2.0,  # Threshold for slow query logging
}

# Adaptive Parameters
ADAPTIVE_PARAMS = {
    "enable_adaptive_optimization": True,  # Enable adaptive optimization
    "load_balancing_enabled": False,  # Enable load balancing
    "auto_scaling_enabled": False,  # Enable auto scaling
    "dynamic_timeout_adjustment": True,  # Adjust timeouts based on load
    "performance_feedback_loop": True,  # Enable performance feedback
}

def get_performance_config() -> Dict[str, Any]:
    """Get the complete performance configuration"""
    return {
        "targets": PERFORMANCE_TARGETS,
        "timeouts": TIMEOUT_CONFIG,
        "optimization": OPTIMIZATION_PARAMS,
        "resources": RESOURCE_LIMITS,
        "monitoring": MONITORING_CONFIG,
        "adaptive": ADAPTIVE_PARAMS,
    }

def get_timeout_for_operation(operation: str) -> float:
    """Get appropriate timeout for a specific operation"""
    operation_timeouts = {
        'query': TIMEOUT_CONFIG['api_timeout'],
        'retrieval': TIMEOUT_CONFIG['retrieval_timeout'],
        'generation': TIMEOUT_CONFIG['llm_generation_timeout'],
        'ingestion': TIMEOUT_CONFIG['document_parsing_timeout'],
        'embedding': TIMEOUT_CONFIG['embedding_generation_timeout'],
        'storage': TIMEOUT_CONFIG['chunk_storage_timeout'],
        'health': TIMEOUT_CONFIG['health_check_timeout'],
    }
    return operation_timeouts.get(operation, TIMEOUT_CONFIG['api_timeout'])

def adjust_for_production(config: Dict[str, Any]) -> Dict[str, Any]:
    """Adjust configuration for production environment"""
    # Reduce verbose settings for production
    config['monitoring']['performance_sampling_rate'] = 0.05  # Less sampling
    config['targets']['max_concurrency'] = 20  # Higher concurrency in prod
    
    # Increase timeouts slightly for production stability
    for key in config['timeouts']:
        if isinstance(config['timeouts'][key], (int, float)):
            config['timeouts'][key] *= 1.2  # 20% increase for production
    
    return config

# Default configuration
PERFORMANCE_CONFIG = get_performance_config()