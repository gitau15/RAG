import asyncio
import time
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import tempfile
import os
from datetime import datetime

from app.ingestion.document_parser import DocumentParser
from app.vectorstore.chroma_client import chroma_client
from app.vectorstore.embedding_manager import embedding_manager
from app.models.schemas import DocumentUploadResponse, DocumentMetadata
from app.performance.optimizer import document_processor_optimizer
from app.logging.logger import perf_logger
from app.monitoring.collector import metrics_collector

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """End-to-end document ingestion pipeline"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.chroma = chroma_client
        self.embedder = embedding_manager
    
    async def ingest_document(
        self, 
        file_content: bytes, 
        filename: str,
        collection_name: str,
        tenant_id: Optional[str] = None,
        mode: str = "judicial",
        tags: List[str] = None
    ) -> DocumentUploadResponse:
        """
        Ingest a document through the complete pipeline
        
        Args:
            file_content: Document file content as bytes
            filename: Original filename
            collection_name: Target collection name
            tenant_id: Tenant identifier for isolation
            mode: Processing mode (judicial/sales)
            tags: Document tags
            
        Returns:
            Document upload response with processing details
        """
        start_time = time.time()
        tags = tags or []
        
        try:
            # Optimize based on file size
            file_size = len(file_content)
            chunk_size = document_processor_optimizer.optimize_chunk_size(file_size)
            
            # Step 1: Save temporary file
            temp_file_path = await self._save_temporary_file(file_content, filename)
            logger.info(f"Saved temporary file: {temp_file_path}")
            
            # Step 2: Parse document with optimized parameters
            chunks = self.parser.parse_document(temp_file_path, method="auto")
            logger.info(f"Parsed document into {len(chunks)} chunks")
            
            # Step 3: Create/get collection
            collection = await self._ensure_collection(collection_name, tenant_id, mode)
            
            # Step 4: Generate embeddings with optimized batch size
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings with timeout
            embed_start = time.time()
            embeddings = await self._generate_embeddings_with_timeout(texts, timeout=30.0)
            embed_time = time.time() - embed_start
            logger.info(f"Generated embeddings for {len(embeddings)} chunks in {embed_time:.2f}s")
            
            # Step 5: Prepare metadata
            doc_metadata = self.parser.get_document_metadata(temp_file_path)
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "chunk_id": chunk["id"],
                    "source_file": filename,
                    "file_size": doc_metadata.get("file_size", 0),
                    "upload_date": datetime.utcnow().isoformat(),
                    "collection_name": collection_name,
                    "document_type": doc_metadata.get("file_extension", ""),
                    "tags": ",".join(tags),
                    "tenant_id": tenant_id or "default",
                    "mode": mode,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "parser_used": chunk["metadata"]["parser"]
                }
                chunk_metadatas.append(chunk_metadata)
            
            # Step 6: Store in vector database with timeout
            ids = [f"{filename}_{chunk['id']}" for chunk in chunks]
            await self._store_chunks_with_timeout(collection, ids, texts, embeddings, chunk_metadatas, timeout=10.0)
            
            # Step 7: Cleanup temporary file
            await self._cleanup_temporary_file(temp_file_path)
            
            processing_time = time.time() - start_time
            
            # Log performance metrics
            perf_logger.log_document_processing(
                document_id=f"doc_{int(time.time())}",
                processing_time=processing_time,
                success=True
            )
            
            # Record metrics
            metrics_collector.record_document_processing(processing_time, True)
            
            return DocumentUploadResponse(
                document_id=f"doc_{int(time.time())}",
                filename=filename,
                chunks_created=len(chunks),
                collection_name=collection_name,
                upload_time=processing_time
            )
            
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            logger.warning(f"Document ingestion timed out after {processing_time:.2f}s")
            metrics_collector.record_document_processing(processing_time, False)
            
            # Cleanup on timeout
            if 'temp_file_path' in locals():
                await self._cleanup_temporary_file(temp_file_path)
            
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Ingestion pipeline failed: {str(e)}")
            metrics_collector.record_document_processing(processing_time, False)
            
            # Cleanup on failure
            if 'temp_file_path' in locals():
                await self._cleanup_temporary_file(temp_file_path)
            raise
    
    async def _generate_embeddings_with_timeout(self, texts: List[str], timeout: float = 30.0):
        """Generate embeddings with timeout enforcement"""
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, lambda: self.embedder.embed_documents(texts)),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Embedding generation timed out after {timeout}s")
            raise
    
    async def _store_chunks_with_timeout(self, collection, ids: List[str], texts: List[str], 
                                   embeddings: List[List[float]], metadatas: List[Dict], timeout: float = 10.0):
        """Store chunks with timeout enforcement"""
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
                ),
                timeout=timeout
            )
            logger.info(f"Stored {len(ids)} chunks in collection")
        except asyncio.TimeoutError:
            logger.warning(f"Storing chunks timed out after {timeout}s")
            raise
    
    async def batch_ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str,
        tenant_id: Optional[str] = None,
        mode: str = "judicial"
    ) -> List[DocumentUploadResponse]:
        """
        Ingest multiple documents in batch
        
        Args:
            documents: List of document dictionaries with 'content' and 'filename'
            collection_name: Target collection name
            tenant_id: Tenant identifier
            mode: Processing mode
            
        Returns:
            List of upload responses
        """
        tasks = []
        for doc in documents:
            task = self.ingest_document(
                file_content=doc["content"],
                filename=doc["filename"],
                collection_name=collection_name,
                tenant_id=tenant_id,
                mode=mode,
                tags=doc.get("tags", [])
            )
            tasks.append(task)
        
        # Execute all ingestion tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to ingest document {documents[i]['filename']}: {str(result)}")
            else:
                successful_results.append(result)
        
        return successful_results
    
    async def _save_temporary_file(self, file_content: bytes, filename: str) -> str:
        """Save file content to temporary location"""
        temp_dir = tempfile.gettempdir()
        temp_filename = f"rag_upload_{int(time.time())}_{filename}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        return temp_path
    
    async def _cleanup_temporary_file(self, file_path: str):
        """Remove temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {str(e)}")
    
    async def _ensure_collection(self, collection_name: str, tenant_id: str, mode: str):
        """Create collection if it doesn't exist"""
        try:
            collection = self.chroma.get_collection(collection_name)
            logger.info(f"Using existing collection: {collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            metadata = {
                "tenant_id": tenant_id or "default",
                "mode": mode,
                "created_at": datetime.utcnow().isoformat()
            }
            collection = self.chroma.create_collection(collection_name, metadata)
            logger.info(f"Created new collection: {collection_name}")
        
        return collection
    
    async def _store_chunks(self, collection, ids: List[str], texts: List[str], 
                          embeddings: List[List[float]], metadatas: List[Dict]):
        """Store document chunks in vector database"""
        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Stored {len(ids)} chunks in collection")
        except Exception as e:
            logger.error(f"Failed to store chunks: {str(e)}")
            raise
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection"""
        try:
            collection = self.chroma.get_collection(collection_name)
            count = collection.count()
            
            # Get sample metadata to infer collection properties
            if count > 0:
                sample_result = collection.peek(limit=1)
                sample_metadata = sample_result.get('metadatas', [{}])[0] if sample_result.get('metadatas') else {}
                
                return {
                    "collection_name": collection_name,
                    "document_count": count,
                    "tenant_id": sample_metadata.get("tenant_id", "unknown"),
                    "mode": sample_metadata.get("mode", "unknown"),
                    "sample_tags": sample_metadata.get("tags", "").split(",") if sample_metadata.get("tags") else []
                }
            else:
                return {
                    "collection_name": collection_name,
                    "document_count": 0,
                    "tenant_id": "unknown",
                    "mode": "unknown",
                    "sample_tags": []
                }
                
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}

# Global instance
ingestion_pipeline = IngestionPipeline()