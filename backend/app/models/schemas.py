from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Schema for document metadata"""
    filename: str
    file_size: int
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    collection_name: str
    document_type: str
    tags: List[str] = []
    tenant_id: Optional[str] = None
    mode: str = "judicial"  # judicial or sales

class DocumentChunk(BaseModel):
    """Schema for document chunks"""
    id: str
    content: str
    metadata: DocumentMetadata
    embedding: Optional[List[float]] = None

class QueryRequest(BaseModel):
    """Schema for query requests"""
    query: str
    collection_name: str
    mode: str = "judicial"
    k: int = 4  # Number of results to return
    tenant_id: Optional[str] = None
    metadata_filter: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    """Schema for query responses"""
    query: str
    results: List[Dict[str, Any]]
    collection_name: str
    mode: str
    execution_time: float

class CollectionCreateRequest(BaseModel):
    """Schema for collection creation requests"""
    name: str
    description: Optional[str] = None
    tenant_id: Optional[str] = None
    mode: str = "judicial"
    metadata: Optional[Dict[str, Any]] = None

class CollectionResponse(BaseModel):
    """Schema for collection responses"""
    name: str
    description: Optional[str]
    tenant_id: Optional[str]
    mode: str
    document_count: int
    created_at: datetime

class DocumentUploadRequest(BaseModel):
    """Schema for document upload requests"""
    collection_name: str
    tenant_id: Optional[str] = None
    mode: str = "judicial"
    tags: List[str] = []

class DocumentUploadResponse(BaseModel):
    """Schema for document upload responses"""
    document_id: str
    filename: str
    chunks_created: int
    collection_name: str
    upload_time: float