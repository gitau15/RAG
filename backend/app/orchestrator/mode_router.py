from typing import Dict, Any, Optional
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ProcessingMode(Enum):
    JUDICIAL = "judicial"
    SALES = "sales"
    RESEARCH = "research"

class ModeRouter:
    """Intelligent mode routing based on query analysis"""
    
    def __init__(self):
        self.mode_keywords = {
            ProcessingMode.JUDICIAL: {
                "keywords": [
                    "law", "legal", "court", "case", "statute", "regulation",
                    "contract", "precedent", "jurisdiction", "liability",
                    "plaintiff", "defendant", "verdict", "appeal",
                    "constitutional", "legislation", "compliance"
                ],
                "weight": 1.0
            },
            ProcessingMode.SALES: {
                "keywords": [
                    "product", "price", "buy", "purchase", "order",
                    "customer", "client", "deal", "offer", "discount",
                    "catalog", "inventory", "availability", "shipping",
                    "payment", "transaction", "conversion", "sale"
                ],
                "weight": 1.0
            },
            ProcessingMode.RESEARCH: {
                "keywords": [
                    "study", "analysis", "research", "findings", "data",
                    "information", "knowledge", "facts", "evidence",
                    "investigation", "exploration", "discovery"
                ],
                "weight": 0.8
            }
        }
    
    def determine_mode(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Determine the appropriate processing mode based on query content
        
        Args:
            query: User query text
            context: Additional context information
            
        Returns:
            Determined mode as string
        """
        query_lower = query.lower()
        scores = {}
        
        # Score each mode based on keyword matches
        for mode, config in self.mode_keywords.items():
            score = 0
            keywords = config["keywords"]
            weight = config["weight"]
            
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            
            # Apply weight
            scores[mode.value] = score * weight
        
        # Consider context clues
        if context:
            scores = self._adjust_scores_with_context(scores, context)
        
        # Return mode with highest score, default to research
        if any(score > 0 for score in scores.values()):
            determined_mode = max(scores, key=scores.get)
            logger.info(f"Determined mode '{determined_mode}' for query: {query[:50]}...")
            return determined_mode
        else:
            logger.info(f"Defaulting to 'research' mode for query: {query[:50]}...")
            return ProcessingMode.RESEARCH.value
    
    def _adjust_scores_with_context(self, scores: Dict[str, float], context: Dict[str, Any]) -> Dict[str, float]:
        """Adjust mode scores based on contextual information"""
        
        # Adjust based on collection metadata
        if "collection_mode" in context:
            collection_mode = context["collection_mode"]
            if collection_mode in scores:
                scores[collection_mode] += 2.0  # Strong boost for collection mode
        
        # Adjust based on tenant preferences
        if "tenant_preferences" in context:
            preferred_mode = context["tenant_preferences"].get("preferred_mode")
            if preferred_mode and preferred_mode in scores:
                scores[preferred_mode] += 1.0
        
        # Adjust based on recent usage patterns
        if "recent_modes" in context:
            recent_modes = context["recent_modes"]
            for mode in recent_modes:
                if mode in scores:
                    scores[mode] += 0.5
        
        return scores
    
    def get_mode_config(self, mode: str) -> Dict[str, Any]:
        """
        Get configuration for specific mode
        
        Args:
            mode: Processing mode
            
        Returns:
            Mode configuration dictionary
        """
        configs = {
            ProcessingMode.JUDICIAL.value: {
                "system_prompt_type": "judicial",
                "retrieval_k": 6,
                "temperature": 0.1,
                "citation_required": True,
                "formality_level": "high"
            },
            ProcessingMode.SALES.value: {
                "system_prompt_type": "sales",
                "retrieval_k": 4,
                "temperature": 0.7,
                "citation_required": False,
                "formality_level": "medium"
            },
            ProcessingMode.RESEARCH.value: {
                "system_prompt_type": "research",
                "retrieval_k": 8,
                "temperature": 0.5,
                "citation_required": True,
                "formality_level": "medium"
            }
        }
        
        return configs.get(mode, configs[ProcessingMode.RESEARCH.value])
    
    def validate_mode_transition(self, current_mode: str, target_mode: str) -> bool:
        """
        Validate if mode transition is appropriate
        
        Args:
            current_mode: Current processing mode
            target_mode: Target mode
            
        Returns:
            Boolean indicating if transition is valid
        """
        # Define valid transitions
        valid_transitions = {
            ProcessingMode.JUDICIAL.value: [ProcessingMode.JUDICIAL.value, ProcessingMode.RESEARCH.value],
            ProcessingMode.SALES.value: [ProcessingMode.SALES.value, ProcessingMode.RESEARCH.value],
            ProcessingMode.RESEARCH.value: [ProcessingMode.JUDICIAL.value, ProcessingMode.SALES.value, ProcessingMode.RESEARCH.value]
        }
        
        return target_mode in valid_transitions.get(current_mode, [])

# Global instance
mode_router = ModeRouter()