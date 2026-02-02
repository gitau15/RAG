import asyncio
from typing import List, Dict, Any, Optional, Union
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.retrieval.retrieval_config import RetrievalParameters, RetrievalStrategy
from app.vectorstore.chroma_client import chroma_client
from app.vectorstore.embedding_manager import embedding_manager

logger = logging.getLogger(__name__)

@dataclass
class RetrievedDocument:
    """Enhanced document with retrieval metadata"""
    id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    retrieval_rank: int
    strategy_used: str
    retrieval_timestamp: datetime
    processing_time_ms: float

class AdvancedRetriever:
    """Advanced retrieval strategies with parameterized depth control"""
    
    def __init__(self):
        self.chroma = chroma_client
        self.embedder = embedding_manager
    
    async def retrieve(self, query: str, collection_name: str, 
                      params: RetrievalParameters) -> List[RetrievedDocument]:
        """
        Main retrieval method that dispatches to appropriate strategy
        
        Args:
            query: User query
            collection_name: Target collection
            params: Retrieval parameters
            
        Returns:
            List of retrieved documents with metadata
        """
        start_time = datetime.now()
        
        try:
            # Validate parameters
            validation = params.validate_parameters()
            if not validation["valid"]:
                logger.warning(f"Invalid retrieval parameters: {validation['issues']}")
            
            # Dispatch to appropriate strategy
            strategy_results = await self._execute_strategy(query, collection_name, params)
            
            # Apply post-processing
            processed_results = await self._post_process_results(
                strategy_results, params, query
            )
            
            # Add timing metadata
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            # Enrich with metadata
            enriched_results = []
            for i, doc in enumerate(processed_results):
                enriched_doc = RetrievedDocument(
                    id=doc["id"],
                    content=doc["content"],
                    metadata=doc["metadata"],
                    similarity_score=doc.get("similarity_score", 0.0),
                    retrieval_rank=i + 1,
                    strategy_used=params.strategy.value,
                    retrieval_timestamp=end_time,
                    processing_time_ms=processing_time
                )
                enriched_results.append(enriched_doc)
            
            logger.info(f"Retrieved {len(enriched_results)} documents using {params.strategy.value} strategy")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Retrieval failed: {str(e)}")
            raise
    
    async def _execute_strategy(self, query: str, collection_name: str, 
                              params: RetrievalParameters) -> List[Dict[str, Any]]:
        """Execute the appropriate retrieval strategy"""
        
        strategy_map = {
            RetrievalStrategy.STANDARD: self._standard_retrieval,
            RetrievalStrategy.MULTI_QUERY: self._multi_query_retrieval,
            RetrievalStrategy.CONTEXTUAL: self._contextual_retrieval,
            RetrievalStrategy.TIME_WEIGHTED: self._time_weighted_retrieval,
            RetrievalStrategy.SPARSE_DENSE: self._sparse_dense_retrieval
        }
        
        strategy_func = strategy_map.get(params.strategy, self._standard_retrieval)
        return await strategy_func(query, collection_name, params)
    
    async def _standard_retrieval(self, query: str, collection_name: str, 
                                params: RetrievalParameters) -> List[Dict[str, Any]]:
        """Standard similarity-based retrieval"""
        try:
            collection = self.chroma.get_collection(collection_name)
            
            # Build metadata filters
            where_clause = self._build_metadata_filters(params)
            
            # Perform similarity search
            results = collection.query(
                query_texts=[query],
                n_results=params.k,
                where=where_clause
            )
            
            # Format results
            documents = []
            for i in range(len(results['ids'][0])):
                if results['distances'][0][i] <= (1 - params.similarity_threshold):
                    doc = {
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "similarity_score": 1 - results['distances'][0][i]
                    }
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Standard retrieval failed: {str(e)}")
            return []
    
    async def _multi_query_retrieval(self, query: str, collection_name: str, 
                                   params: RetrievalParameters) -> List[Dict[str, Any]]:
        """Multi-query retrieval with query variations"""
        try:
            # Generate query variations
            query_variations = self._generate_query_variations(
                query, 
                params.strategy_params.get("query_variations", 3)
            )
            
            # Retrieve for each variation
            all_results = []
            for variation in query_variations:
                variation_results = await self._standard_retrieval(
                    variation, collection_name, params
                )
                all_results.extend(variation_results)
            
            # Deduplicate and rank results
            unique_results = self._deduplicate_results(all_results)
            return unique_results[:params.k]
            
        except Exception as e:
            logger.error(f"Multi-query retrieval failed: {str(e)}")
            return []
    
    async def _contextual_retrieval(self, query: str, collection_name: str, 
                                  params: RetrievalParameters) -> List[Dict[str, Any]]:
        """Contextual retrieval with expanded context"""
        try:
            # Get initial results
            initial_results = await self._standard_retrieval(query, collection_name, params)
            
            # Expand context for each result
            expanded_results = []
            context_window = params.strategy_params.get("context_window", 2)
            
            collection = self.chroma.get_collection(collection_name)
            
            for doc in initial_results:
                # Get adjacent chunks for context
                chunk_index = doc["metadata"].get("chunk_index", 0)
                tenant_id = doc["metadata"].get("tenant_id")
                
                # Search for adjacent chunks
                adjacent_results = collection.query(
                    query_texts=[query],
                    n_results=context_window * 2,
                    where={
                        "tenant_id": tenant_id,
                        "chunk_index": {"$gte": max(0, chunk_index - context_window),
                                      "$lte": chunk_index + context_window}
                    }
                )
                
                # Combine content with context
                context_content = self._merge_adjacent_chunks(
                    doc, adjacent_results, context_window
                )
                doc["content"] = context_content
                doc["context_expanded"] = True
                expanded_results.append(doc)
            
            return expanded_results
            
        except Exception as e:
            logger.error(f"Contextual retrieval failed: {str(e)}")
            return []
    
    async def _time_weighted_retrieval(self, query: str, collection_name: str, 
                                     params: RetrievalParameters) -> List[Dict[str, Any]]:
        """Time-weighted retrieval considering document recency"""
        try:
            # Get standard results
            results = await self._standard_retrieval(query, collection_name, params)
            
            # Apply time weighting
            decay_days = params.strategy_params.get("time_decay_days", 30)
            recency_boost = params.strategy_params.get("recency_boost", 2.0)
            
            weighted_results = []
            current_time = datetime.now()
            
            for doc in results:
                # Calculate time-based weight
                upload_date_str = doc["metadata"].get("upload_date")
                if upload_date_str:
                    try:
                        upload_date = datetime.fromisoformat(upload_date_str.replace('Z', '+00:00'))
                        days_old = (current_time - upload_date).days
                        
                        # Exponential decay function
                        time_weight = recency_boost * (0.5 ** (days_old / decay_days))
                        weighted_score = doc["similarity_score"] * (1 + time_weight * params.time_decay_factor)
                        
                        doc["time_weighted_score"] = weighted_score
                        doc["days_old"] = days_old
                        weighted_results.append(doc)
                    except Exception as e:
                        logger.warning(f"Could not parse upload date: {str(e)}")
                        weighted_results.append(doc)
                else:
                    weighted_results.append(doc)
            
            # Re-sort by weighted score
            weighted_results.sort(
                key=lambda x: x.get("time_weighted_score", x["similarity_score"]), 
                reverse=True
            )
            
            return weighted_results
            
        except Exception as e:
            logger.error(f"Time-weighted retrieval failed: {str(e)}")
            return []
    
    async def _sparse_dense_retrieval(self, query: str, collection_name: str, 
                                    params: RetrievalParameters) -> List[Dict[str, Any]]:
        """Hybrid sparse + dense retrieval"""
        try:
            # Sparse (keyword) matching
            sparse_weight = params.strategy_params.get("sparse_weight", 0.3)
            dense_weight = params.strategy_params.get("dense_weight", 0.7)
            
            # Get dense retrieval results
            dense_results = await self._standard_retrieval(query, collection_name, params)
            
            # Get keyword-based results (simplified - in production would use BM25)
            collection = self.chroma.get_collection(collection_name)
            keyword_results = collection.get(
                where={"$contains": query.lower()}
            )
            
            # Combine and weight results
            combined_results = self._combine_sparse_dense_results(
                dense_results, keyword_results, sparse_weight, dense_weight
            )
            
            return combined_results[:params.k]
            
        except Exception as e:
            logger.error(f"Sparse-dense retrieval failed: {str(e)}")
            return []
    
    def _build_metadata_filters(self, params: RetrievalParameters) -> Dict[str, Any]:
        """Build metadata filters for ChromaDB query"""
        filters = {}
        
        # Add tenant filter
        if params.tenant_id:
            filters["tenant_id"] = params.tenant_id
        
        # Add mode filter
        if params.mode:
            filters["mode"] = params.mode
        
        # Add custom metadata filters
        if params.metadata_filters:
            filters.update(params.metadata_filters)
        
        return filters if filters else None
    
    def _generate_query_variations(self, query: str, num_variations: int) -> List[str]:
        """Generate variations of the query for multi-query retrieval"""
        variations = [query]
        
        # Simple variations - in production, use more sophisticated methods
        query_lower = query.lower()
        
        if num_variations >= 2:
            # Add question form
            if not query_lower.endswith('?'):
                variations.append(f"What is {query_lower}?")
        
        if num_variations >= 3:
            # Add explanation form
            variations.append(f"Explain {query_lower}")
        
        if num_variations >= 4:
            # Add definition form
            variations.append(f"Define {query_lower}")
        
        return variations[:num_variations]
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results and rank by score"""
        seen_ids = set()
        unique_results = []
        
        # Sort by similarity score first
        results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        for result in results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                unique_results.append(result)
        
        return unique_results
    
    def _merge_adjacent_chunks(self, main_doc: Dict[str, Any], 
                             adjacent_results: Dict[str, Any], 
                             context_window: int) -> str:
        """Merge adjacent document chunks for context"""
        main_content = main_doc["content"]
        chunk_index = main_doc["metadata"].get("chunk_index", 0)
        
        # Extract adjacent chunks
        adjacent_chunks = []
        for i in range(len(adjacent_results['ids'][0])):
            adj_chunk_index = adjacent_results['metadatas'][0][i].get("chunk_index", 0)
            if adj_chunk_index != chunk_index:  # Exclude main chunk
                adjacent_chunks.append({
                    "content": adjacent_results['documents'][0][i],
                    "chunk_index": adj_chunk_index,
                    "distance": abs(adj_chunk_index - chunk_index)
                })
        
        # Sort by proximity to main chunk
        adjacent_chunks.sort(key=lambda x: x["distance"])
        
        # Merge content (simplified - production would be more sophisticated)
        merged_content = main_content
        
        # Add previous context
        prev_chunks = [c for c in adjacent_chunks if c["chunk_index"] < chunk_index]
        prev_chunks.sort(key=lambda x: x["chunk_index"], reverse=True)
        
        for chunk in prev_chunks[:context_window]:
            merged_content = chunk["content"] + " " + merged_content
        
        # Add next context
        next_chunks = [c for c in adjacent_chunks if c["chunk_index"] > chunk_index]
        next_chunks.sort(key=lambda x: x["chunk_index"])
        
        for chunk in next_chunks[:context_window]:
            merged_content = merged_content + " " + chunk["content"]
        
        return merged_content.strip()
    
    def _combine_sparse_dense_results(self, dense_results: List[Dict[str, Any]], 
                                    sparse_results: Dict[str, Any], 
                                    sparse_weight: float, 
                                    dense_weight: float) -> List[Dict[str, Any]]:
        """Combine sparse and dense retrieval results"""
        # Convert sparse results to standard format
        sparse_docs = []
        if sparse_results and sparse_results.get('ids'):
            for i in range(len(sparse_results['ids'])):
                sparse_docs.append({
                    "id": sparse_results['ids'][i],
                    "content": sparse_results['documents'][i],
                    "metadata": sparse_results['metadatas'][i],
                    "similarity_score": 0.5  # Placeholder score
                })
        
        # Combine results with weighting
        combined_scores = {}
        
        # Add dense scores
        for doc in dense_results:
            combined_scores[doc["id"]] = doc["similarity_score"] * dense_weight
        
        # Add sparse scores
        for doc in sparse_docs:
            if doc["id"] in combined_scores:
                combined_scores[doc["id"]] += 0.5 * sparse_weight
            else:
                combined_scores[doc["id"]] = 0.5 * sparse_weight
        
        # Rebuild document list with combined scores
        combined_results = []
        all_docs = {doc["id"]: doc for doc in dense_results + sparse_docs}
        
        for doc_id, combined_score in combined_scores.items():
            if doc_id in all_docs:
                doc = all_docs[doc_id].copy()
                doc["similarity_score"] = combined_score
                combined_results.append(doc)
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return combined_results
    
    async def _post_process_results(self, results: List[Dict[str, Any]], 
                                  params: RetrievalParameters, 
                                  query: str) -> List[Dict[str, Any]]:
        """Apply post-processing to retrieval results"""
        
        # Apply diversity if requested
        if params.diversity_factor > 0:
            results = self._apply_diversity_filtering(results, params.diversity_factor)
        
        # Apply reranking if requested
        if params.rerank_top_k:
            results = await self._rerank_results(results, query, params.rerank_top_k)
        
        # Apply final k limit
        return results[:params.k]
    
    def _apply_diversity_filtering(self, results: List[Dict[str, Any]], 
                                 diversity_factor: float) -> List[Dict[str, Any]]:
        """Apply diversity-based filtering to results"""
        if not results or diversity_factor <= 0:
            return results
        
        # Simple diversity implementation - remove very similar documents
        filtered_results = []
        seen_contents = set()
        
        for result in results:
            content_hash = hash(result["content"][:100])  # Simplified content hashing
            if content_hash not in seen_contents:
                filtered_results.append(result)
                seen_contents.add(content_hash)
        
        return filtered_results
    
    async def _rerank_results(self, results: List[Dict[str, Any]], 
                            query: str, top_k: int) -> List[Dict[str, Any]]:
        """Rerank results using cross-encoder or other method"""
        # Simplified reranking - in production, use proper cross-encoder
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

# Global instance
advanced_retriever = AdvancedRetriever()