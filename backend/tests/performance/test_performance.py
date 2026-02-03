import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from app.performance.optimizer import (
    PerformanceOptimizer, QueryOptimizer, DocumentProcessorOptimizer, 
    SystemPerformanceMonitor, OptimizationStrategy
)
from app.performance.middleware import PerformanceMiddleware
from app.performance.config import PERFORMANCE_CONFIG, get_timeout_for_operation

class TestPerformanceOptimizer:
    @pytest.fixture
    def optimizer(self):
        return PerformanceOptimizer()
    
    def test_initialization(self, optimizer):
        """Test optimizer initialization"""
        assert optimizer.target_response_time == 8.0
        assert optimizer.latency_threshold == 0.1
        assert optimizer.aggressive_timeout == 5.0
        assert len(optimizer.performance_history) == 0
    
    def test_optimization_strategies(self):
        """Test optimization strategies enum"""
        strategies = list(OptimizationStrategy)
        assert len(strategies) == 4
        assert OptimizationStrategy.LATENCY_OPTIMIZED.value == "latency_optimized"
        assert OptimizationStrategy.BALANCED.value == "balanced"
        assert OptimizationStrategy.THROUGHPUT_OPTIMIZED.value == "throughput_optimized"
        assert OptimizationStrategy.AGGRESSIVE.value == "aggressive"
    
    def test_timeout_decorator(self, optimizer):
        """Test timeout decorator functionality"""
        @optimizer.apply_timeout(timeout=1.0)
        async def slow_function():
            await asyncio.sleep(2.0)
            return "result"
        
        @optimizer.apply_timeout(timeout=2.0)
        async def fast_function():
            await asyncio.sleep(0.5)
            return "result"
        
        # Test fast function completes within timeout
        async def test_fast():
            result = await fast_function()
            assert result == "result"
        
        # Test slow function times out
        async def test_slow():
            with pytest.raises(TimeoutError):
                await slow_function()
        
        # Run tests
        asyncio.run(test_fast())
        asyncio.run(test_slow())
    
    def test_adaptive_retrieval(self, optimizer):
        """Test adaptive retrieval decorator"""
        @optimizer.adaptive_retrieval(min_k=2, max_k=6)
        async def retrieval_function(*args, **kwargs):
            return f"retrieved with k={kwargs.get('k', 2)}"
        
        async def test_adaptive():
            # Should start with min_k
            result1 = await retrieval_function()
            assert "k=2" in result1
            
            # Should adapt based on timing (mocked in this test)
            result2 = await retrieval_function()
            assert "k=2" in result2  # Still min_k in this simple test
        
        asyncio.run(test_adaptive())
    
    def test_parallel_execution(self, optimizer):
        """Test parallel execution with timeout"""
        async def task1():
            await asyncio.sleep(0.1)
            return "result1"
        
        async def task2():
            await asyncio.sleep(0.2)
            return "result2"
        
        async def test_parallel():
            tasks = [task1, task2]
            results = await optimizer.parallel_execution(tasks, timeout=1.0)
            assert len(results) == 2
            assert "result1" in results
            assert "result2" in results
        
        asyncio.run(test_parallel())
    
    def test_early_stopping(self, optimizer):
        """Test early stopping for generators"""
        async def mock_generator():
            for i in range(10):
                yield f"item_{i}"
        
        async def test_early_stopping():
            # Test with time limit
            limited_gen = optimizer.early_stopping(mock_generator, time_limit=0.1)
            items = []
            async for item in limited_gen():
                items.append(item)
            
            # Should have stopped early due to time limit
            assert len(items) < 10
            
            # Test with token limit
            token_limited_gen = optimizer.early_stopping(mock_generator, token_limit=5)
            items = []
            async for item in token_limited_gen():
                items.append(item)
            
            # Should have stopped early due to token limit
            assert len(items) <= 5
        
        asyncio.run(test_early_stopping())

class TestQueryOptimizer:
    @pytest.fixture
    def query_optimizer(self):
        return QueryOptimizer()
    
    def test_cache_key_generation(self, query_optimizer):
        """Test cache key generation"""
        key1 = query_optimizer.get_cache_key("test query", "collection1", "judicial")
        key2 = query_optimizer.get_cache_key("test query", "collection1", "judicial")
        key3 = query_optimizer.get_cache_key("different query", "collection1", "judicial")
        
        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
    
    def test_cacheability_check(self, query_optimizer):
        """Test cacheability determination"""
        # Cacheable queries
        assert query_optimizer.is_cacheable("What is contract law?") == True
        assert query_optimizer.is_cacheable("Explain legal precedent") == True
        
        # Non-cacheable queries
        assert query_optimizer.is_cacheable("What is my account balance?") == False
        assert query_optimizer.is_cacheable("Show me current documents") == False
        assert query_optimizer.is_cacheable("What's the time now?") == False
    
    @pytest.mark.asyncio
    async def test_optimize_and_execute(self, query_optimizer):
        """Test optimized query execution"""
        with patch.object(query_optimizer, 'response_cache', {}):
            result = await query_optimizer.optimize_and_execute(
                query="test query",
                collection_name="test_collection",
                mode="judicial",
                k=4
            )
            
            assert "response" in result
            assert "total_time" in result
            assert "optimized" in result
            assert result["optimized"] == True

class TestDocumentProcessorOptimizer:
    @pytest.fixture
    def doc_optimizer(self):
        return DocumentProcessorOptimizer()
    
    def test_chunk_size_optimization(self, doc_optimizer):
        """Test chunk size optimization"""
        # Small document
        small_chunk = doc_optimizer.optimize_chunk_size(500)
        assert small_chunk == 256
        
        # Medium document
        medium_chunk = doc_optimizer.optimize_chunk_size(5000)
        assert medium_chunk == 512
        
        # Large document
        large_chunk = doc_optimizer.optimize_chunk_size(15000)
        assert large_chunk == 1024
    
    def test_embedding_batch_size(self, doc_optimizer):
        """Test embedding batch size optimization"""
        batch_size = doc_optimizer.optimize_embedding_batch_size()
        assert batch_size == 32  # Conservative default
    
    @pytest.mark.asyncio
    async def test_parallel_chunk_processing(self, doc_optimizer):
        """Test parallel chunk processing"""
        async def mock_process(chunk):
            await asyncio.sleep(0.1)
            return f"processed_{chunk}"
        
        chunks = ["chunk1", "chunk2", "chunk3", "chunk4"]
        
        results = await doc_optimizer.parallel_process_chunks(chunks, mock_process)
        assert len(results) == 4
        assert "processed_chunk1" in results
        assert "processed_chunk2" in results
        assert "processed_chunk3" in results
        assert "processed_chunk4" in results

class TestSystemPerformanceMonitor:
    @pytest.fixture
    def monitor(self):
        return SystemPerformanceMonitor()
    
    def test_initialization(self, monitor):
        """Test monitor initialization"""
        assert monitor.optimizer is not None
        assert isinstance(monitor.last_optimization, float)
        assert monitor.optimization_interval == 60
    
    @pytest.mark.asyncio
    async def test_should_optimize(self, monitor):
        """Test optimization decision logic"""
        # Should optimize based on time interval
        with patch('time.time', return_value=monitor.last_optimization + 70):
            # Mock metrics collector with slow responses
            with patch('app.performance.optimizer.metrics_collector') as mock_metrics:
                mock_metrics.response_times = [7.0, 8.0, 9.0, 10.0, 11.0]
                should_optimize = await monitor.should_optimize()
                assert should_optimize == True
        
        # Should not optimize if recent
        with patch('time.time', return_value=monitor.last_optimization + 30):
            should_optimize = await monitor.should_optimize()
            assert should_optimize == False

class TestPerformanceMiddleware:
    @pytest.fixture
    def middleware(self):
        return PerformanceMiddleware()
    
    def test_initialization(self, middleware):
        """Test middleware initialization"""
        assert middleware.target_response_time == 8.0
    
    @pytest.mark.asyncio
    async def test_middleware_call(self, middleware):
        """Test middleware execution"""
        mock_request = Mock()
        mock_request.url.path = "/api/v1/query"
        mock_request.method = "POST"
        mock_request.headers = {"user-id": "test_user"}
        
        async def mock_call_next(request):
            await asyncio.sleep(0.1)  # Simulate processing time
            mock_response = Mock()
            mock_response.status_code = 200
            return mock_response
        
        response = await middleware(mock_request, mock_call_next)
        assert response.status_code == 200

class TestPerformanceConfig:
    def test_config_structure(self):
        """Test performance configuration structure"""
        config = PERFORMANCE_CONFIG
        
        # Check required sections
        assert "targets" in config
        assert "timeouts" in config
        assert "optimization" in config
        assert "resources" in config
        assert "monitoring" in config
        assert "adaptive" in config
        
        # Check target values
        assert config["targets"]["max_response_time"] == 8.0
        assert config["targets"]["max_concurrency"] == 10
    
    def test_timeout_lookup(self):
        """Test timeout lookup functionality"""
        # Test known operations
        query_timeout = get_timeout_for_operation("query")
        retrieval_timeout = get_timeout_for_operation("retrieval")
        generation_timeout = get_timeout_for_operation("generation")
        
        assert isinstance(query_timeout, float)
        assert isinstance(retrieval_timeout, float)
        assert isinstance(generation_timeout, float)
        
        # Test unknown operation (should return default)
        default_timeout = get_timeout_for_operation("unknown")
        assert isinstance(default_timeout, float)
        assert default_timeout == 7.5  # Default api_timeout

# Integration Tests
class TestPerformanceIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_optimization(self):
        """Test full performance optimization pipeline"""
        # Test that all components work together
        optimizer = PerformanceOptimizer()
        query_opt = QueryOptimizer()
        doc_opt = DocumentProcessorOptimizer()
        monitor = SystemPerformanceMonitor()
        
        # Test query optimization
        result = await query_opt.optimize_and_execute(
            "test query", "test_collection", "judicial"
        )
        assert result["total_time"] < 8.0  # Should meet target
        
        # Test document processing optimization
        chunk_size = doc_opt.optimize_chunk_size(5000)
        assert chunk_size == 512
        
        # Test system monitoring decision
        should_optimize = await monitor.should_optimize()
        assert isinstance(should_optimize, bool)