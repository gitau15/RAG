from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RetrievalStrategy(Enum):
    """Retrieval strategies for different use cases"""
    STANDARD = "standard"           # Basic similarity search
    HYDE = "hyde"                  # Hypothetical Document Embeddings
    MULTI_QUERY = "multi_query"    # Multiple query variations
    CONTEXTUAL = "contextual"      # Context-aware retrieval
    SPARSE_DENSE = "sparse_dense"  # Hybrid sparse+dense retrieval
    RRF = "rrf"                    # Reciprocal Rank Fusion
    TIME_WEIGHTED = "time_weighted" # Time-based weighting

class SearchDepth(Enum):
    """Search depth levels"""
    SHALLOW = "shallow"    # k=2-4, high precision
    MODERATE = "moderate"  # k=4-8, balanced
    DEEP = "deep"         # k=8-16, high recall
    EXHAUSTIVE = "exhaustive"  # k=16+, comprehensive

@dataclass
class RetrievalParameters:
    """Configuration for retrieval parameters"""
    # Basic parameters
    k: int = 4                    # Number of results to retrieve
    depth: SearchDepth = SearchDepth.MODERATE
    similarity_threshold: float = 0.3  # Minimum similarity score
    
    # Strategy-specific parameters
    strategy: RetrievalStrategy = RetrievalStrategy.STANDARD
    strategy_params: Dict[str, Any] = None
    
    # Filtering parameters
    metadata_filters: Dict[str, Any] = None
    tenant_id: Optional[str] = None
    collection_name: Optional[str] = None
    mode: Optional[str] = None
    
    # Advanced parameters
    diversity_factor: float = 0.0    # 0.0 = no diversity, 1.0 = maximum diversity
    time_decay_factor: float = 0.0   # For time-weighted retrieval
    rerank_top_k: Optional[int] = None  # Reranking parameter
    
    def __post_init__(self):
        if self.strategy_params is None:
            self.strategy_params = {}
        if self.metadata_filters is None:
            self.metadata_filters = {}

class RetrievalConfigManager:
    """Manages retrieval configurations and presets"""
    
    def __init__(self):
        self.presets = self._initialize_presets()
    
    def _initialize_presets(self) -> Dict[str, RetrievalParameters]:
        """Initialize default retrieval presets"""
        return {
            # Legal research - high precision, thorough
            "legal_research": RetrievalParameters(
                k=8,
                depth=SearchDepth.DEEP,
                similarity_threshold=0.4,
                strategy=RetrievalStrategy.CONTEXTUAL,
                strategy_params={
                    "context_window": 3,
                    "expand_context": True
                },
                diversity_factor=0.3
            ),
            
            # Sales mode - balanced recall and precision
            "sales_mode": RetrievalParameters(
                k=6,
                depth=SearchDepth.MODERATE,
                similarity_threshold=0.25,
                strategy=RetrievalStrategy.STANDARD,
                strategy_params={},
                diversity_factor=0.5
            ),
            
            # Quick answers - high precision, fast
            "quick_answer": RetrievalParameters(
                k=3,
                depth=SearchDepth.SHALLOW,
                similarity_threshold=0.5,
                strategy=RetrievalStrategy.STANDARD,
                strategy_params={},
                diversity_factor=0.1
            ),
            
            # Comprehensive research - maximum recall
            "comprehensive_research": RetrievalParameters(
                k=12,
                depth=SearchDepth.EXHAUSTIVE,
                similarity_threshold=0.2,
                strategy=RetrievalStrategy.MULTI_QUERY,
                strategy_params={
                    "query_variations": 3,
                    "expand_terms": True
                },
                diversity_factor=0.7
            ),
            
            # Technical documentation - precise technical terms
            "technical_docs": RetrievalParameters(
                k=5,
                depth=SearchDepth.MODERATE,
                similarity_threshold=0.35,
                strategy=RetrievalStrategy.SPARSE_DENSE,
                strategy_params={
                    "sparse_weight": 0.3,
                    "dense_weight": 0.7
                },
                diversity_factor=0.2
            ),
            
            # Recent documents - time-weighted
            "recent_content": RetrievalParameters(
                k=6,
                depth=SearchDepth.MODERATE,
                similarity_threshold=0.25,
                strategy=RetrievalStrategy.TIME_WEIGHTED,
                strategy_params={
                    "time_decay_days": 30,
                    "recency_boost": 2.0
                },
                time_decay_factor=0.1
            )
        }
    
    def get_preset(self, preset_name: str) -> Optional[RetrievalParameters]:
        """Get retrieval parameters for a preset"""
        return self.presets.get(preset_name)
    
    def create_custom_config(self, **kwargs) -> RetrievalParameters:
        """Create custom retrieval configuration"""
        return RetrievalParameters(**kwargs)
    
    def adjust_depth(self, params: RetrievalParameters, 
                    target_depth: SearchDepth) -> RetrievalParameters:
        """Adjust retrieval parameters based on depth level"""
        depth_configs = {
            SearchDepth.SHALLOW: {"k": 3, "similarity_threshold": 0.5, "diversity_factor": 0.1},
            SearchDepth.MODERATE: {"k": 6, "similarity_threshold": 0.3, "diversity_factor": 0.3},
            SearchDepth.DEEP: {"k": 10, "similarity_threshold": 0.2, "diversity_factor": 0.5},
            SearchDepth.EXHAUSTIVE: {"k": 15, "similarity_threshold": 0.1, "diversity_factor": 0.7}
        }
        
        if target_depth in depth_configs:
            config = depth_configs[target_depth]
            params.k = config["k"]
            params.similarity_threshold = config["similarity_threshold"]
            params.diversity_factor = config["diversity_factor"]
            params.depth = target_depth
        
        return params
    
    def get_strategy_recommendation(self, query: str, mode: str) -> RetrievalStrategy:
        """Recommend retrieval strategy based on query and mode"""
        query_lower = query.lower()
        
        # Strategy recommendations based on query characteristics
        if any(word in query_lower for word in ["compare", "contrast", "difference", "versus"]):
            return RetrievalStrategy.MULTI_QUERY
        elif any(word in query_lower for word in ["explain", "describe", "what is", "how to"]):
            return RetrievalStrategy.CONTEXTUAL
        elif any(word in query_lower for word in ["latest", "recent", "new", "current"]):
            return RetrievalStrategy.TIME_WEIGHTED
        elif mode == "judicial":
            return RetrievalStrategy.CONTEXTUAL
        elif mode == "sales":
            return RetrievalStrategy.STANDARD
        else:
            return RetrievalStrategy.STANDARD
    
    def optimize_for_latency(self, params: RetrievalParameters) -> RetrievalParameters:
        """Optimize parameters for faster retrieval"""
        # Reduce k for faster results
        params.k = max(2, params.k // 2)
        
        # Increase similarity threshold for fewer results
        params.similarity_threshold = min(0.8, params.similarity_threshold + 0.2)
        
        # Disable complex strategies
        if params.strategy in [RetrievalStrategy.MULTI_QUERY, RetrievalStrategy.HYDE]:
            params.strategy = RetrievalStrategy.STANDARD
        
        # Reduce diversity for faster processing
        params.diversity_factor = max(0.0, params.diversity_factor - 0.3)
        
        return params
    
    def optimize_for_recall(self, params: RetrievalParameters) -> RetrievalParameters:
        """Optimize parameters for maximum recall"""
        # Increase k for more results
        params.k = min(20, params.k * 2)
        
        # Lower similarity threshold
        params.similarity_threshold = max(0.05, params.similarity_threshold - 0.1)
        
        # Enable diversity for broader coverage
        params.diversity_factor = min(1.0, params.diversity_factor + 0.3)
        
        # Consider multi-query strategy
        if params.strategy == RetrievalStrategy.STANDARD:
            params.strategy = RetrievalStrategy.MULTI_QUERY
        
        return params
    
    def validate_parameters(self, params: RetrievalParameters) -> Dict[str, Any]:
        """Validate retrieval parameters"""
        issues = []
        
        # Validate k range
        if not (1 <= params.k <= 50):
            issues.append("k must be between 1 and 50")
        
        # Validate similarity threshold
        if not (0.0 <= params.similarity_threshold <= 1.0):
            issues.append("similarity_threshold must be between 0.0 and 1.0")
        
        # Validate diversity factor
        if not (0.0 <= params.diversity_factor <= 1.0):
            issues.append("diversity_factor must be between 0.0 and 1.0")
        
        # Validate time decay factor
        if not (0.0 <= params.time_decay_factor <= 1.0):
            issues.append("time_decay_factor must be between 0.0 and 1.0")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "recommendations": self._generate_recommendations(params, issues)
        }
    
    def _generate_recommendations(self, params: RetrievalParameters, issues: List[str]) -> List[str]:
        """Generate parameter recommendations"""
        recommendations = []
        
        if params.k > 10 and params.strategy in [RetrievalStrategy.HYDE, RetrievalStrategy.MULTI_QUERY]:
            recommendations.append("Consider reducing k for complex strategies to improve performance")
        
        if params.similarity_threshold < 0.2 and params.k > 15:
            recommendations.append("Low threshold with high k may impact performance")
        
        if params.diversity_factor > 0.7 and params.k < 5:
            recommendations.append("High diversity factor with low k may limit results")
        
        return recommendations

# Global instance
retrieval_config_manager = RetrievalConfigManager()