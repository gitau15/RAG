import time
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

from app.vectorstore.chroma_client import chroma_client
from app.llm.ollama_client import ollama_client
from app.llm.system_prompts import SystemPrompts
from app.models.schemas import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

class RAGOrchestrator:
    """LangChain-based RAG orchestrator with mode-based routing"""
    
    def __init__(self):
        self.chroma = chroma_client
        self.llm = ollama_client
        self.system_prompts = SystemPrompts()
    
    async def process_query(self, query_request: QueryRequest) -> QueryResponse:
        """
        Process a query through the RAG pipeline with mode-based routing
        
        Args:
            query_request: Query request with parameters
            
        Returns:
            Query response with results and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Route based on mode and retrieve relevant documents
            retrieved_docs = await self._retrieve_documents(query_request)
            
            # Step 2: Format context from retrieved documents
            context = self._format_context(retrieved_docs)
            
            # Step 3: Generate system prompt based on mode
            system_prompt = self.system_prompts.get_prompt_by_mode(query_request.mode)
            
            # Step 4: Generate augmented prompt
            augmented_prompt = self.system_prompts.get_augmented_prompt(
                query_request.mode,
                context,
                query_request.query
            )
            
            # Step 5: Generate response using LLM
            response = await self._generate_response(augmented_prompt, system_prompt)
            
            # Step 6: Format results with citations
            formatted_results = self._format_results_with_citations(
                retrieved_docs, 
                response, 
                query_request
            )
            
            execution_time = time.time() - start_time
            
            return QueryResponse(
                query=query_request.query,
                results=formatted_results,
                collection_name=query_request.collection_name,
                mode=query_request.mode,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"RAG orchestration failed: {str(e)}")
            raise
    
    async def process_query_stream(self, query_request: QueryRequest) -> AsyncGenerator[str, None]:
        """
        Process query with streaming response
        
        Args:
            query_request: Query request with parameters
            
        Yields:
            Streamed response chunks
        """
        try:
            # Retrieve documents
            retrieved_docs = await self._retrieve_documents(query_request)
            context = self._format_context(retrieved_docs)
            
            # Generate prompts
            system_prompt = self.system_prompts.get_prompt_by_mode(query_request.mode)
            augmented_prompt = self.system_prompts.get_augmented_prompt(
                query_request.mode,
                context,
                query_request.query
            )
            
            # Stream response
            async for chunk in self._generate_response_stream(augmented_prompt, system_prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"RAG streaming failed: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def _retrieve_documents(self, query_request: QueryRequest) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents based on query and filters
        
        Args:
            query_request: Query request with filtering parameters
            
        Returns:
            List of retrieved document chunks
        """
        try:
            # Get collection
            collection = self.chroma.get_collection(query_request.collection_name)
            
            # Build metadata filter
            where_clause = {}
            if query_request.tenant_id:
                where_clause["tenant_id"] = query_request.tenant_id
            if query_request.mode:
                where_clause["mode"] = query_request.mode
            if query_request.metadata_filter:
                where_clause.update(query_request.metadata_filter)
            
            # Perform similarity search
            results = collection.query(
                query_texts=[query_request.query],
                n_results=query_request.k,
                where=where_clause if where_clause else None
            )
            
            # Format results
            documents = []
            for i in range(len(results['ids'][0])):
                doc = {
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                }
                documents.append(doc)
            
            logger.info(f"Retrieved {len(documents)} documents for query")
            return documents
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {str(e)}")
            raise
    
    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Format retrieved documents into context string
        
        Args:
            documents: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        if not documents:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc['content'].strip()
            metadata = doc['metadata']
            
            # Format document with metadata
            doc_context = f"Document {i} (Source: {metadata.get('source_file', 'Unknown')}):\n{content}"
            
            # Add citation information
            if 'chunk_index' in metadata:
                doc_context += f"\n[Page/Section: {metadata.get('chunk_index', 'N/A')}]"
            
            context_parts.append(doc_context)
        
        return "\n\n---\n\n".join(context_parts)
    
    async def _generate_response(self, prompt: str, system_prompt: str) -> str:
        """
        Generate response using LLM
        
        Args:
            prompt: Augmented prompt with context
            system_prompt: System instruction
            
        Returns:
            Generated response
        """
        try:
            response = self.llm.generate(prompt, system_prompt)
            return response
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            raise
    
    async def _generate_response_stream(self, prompt: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """
        Generate streaming response using LLM
        
        Args:
            prompt: Augmented prompt with context
            system_prompt: System instruction
            
        Yields:
            Response chunks
        """
        try:
            async for chunk in self.llm.generate_stream(prompt, system_prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming response generation failed: {str(e)}")
            yield f"Error: {str(e)}"
    
    def _format_results_with_citations(self, documents: List[Dict[str, Any]], 
                                     response: str, query_request: QueryRequest) -> List[Dict[str, Any]]:
        """
        Format results with proper citations and metadata
        
        Args:
            documents: Retrieved documents
            response: Generated response
            query_request: Original query request
            
        Returns:
            Formatted results with citations
        """
        results = []
        
        # Add main response
        main_result = {
            "type": "response",
            "content": response,
            "confidence": "high" if documents else "low",
            "citation_count": len(documents)
        }
        results.append(main_result)
        
        # Add document citations
        for doc in documents:
            citation = {
                "type": "citation",
                "document_id": doc['id'],
                "source": doc['metadata'].get('source_file', 'Unknown'),
                "content_snippet": doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                "metadata": {
                    "chunk_index": doc['metadata'].get('chunk_index'),
                    "upload_date": doc['metadata'].get('upload_date'),
                    "tags": doc['metadata'].get('tags', '').split(',') if doc['metadata'].get('tags') else [],
                    "distance": doc.get('distance')
                }
            }
            results.append(citation)
        
        return results
    
    def get_available_modes(self) -> List[str]:
        """Get list of available processing modes"""
        return ["judicial", "sales", "research"]
    
    def validate_query_request(self, query_request: QueryRequest) -> bool:
        """
        Validate query request parameters
        
        Args:
            query_request: Query request to validate
            
        Returns:
            Boolean indicating validity
        """
        if not query_request.query.strip():
            return False
        
        if not query_request.collection_name:
            return False
            
        if query_request.mode not in self.get_available_modes():
            return False
            
        if query_request.k <= 0 or query_request.k > 20:
            return False
            
        return True

# Global instance
rag_orchestrator = RAGOrchestrator()