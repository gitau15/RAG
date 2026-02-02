# RAG Platform API Documentation

## Overview

The RAG Platform provides a comprehensive RESTful API for document management, query processing, and system administration. All endpoints follow REST conventions and return JSON responses.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently uses API key authentication via `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

## Error Handling

All API responses follow a consistent error format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional error details (optional)"
  }
}
```

## Rate Limiting

- **Default limit**: 1000 requests per hour per IP
- **Authenticated users**: 5000 requests per hour
- **Response headers** include rate limit information

## API Endpoints

### 1. Document Management

#### Upload Document
```
POST /documents/upload
```

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "collection_name=legal_docs" \
  -F "tenant_id=tenant_123" \
  -F "mode=judicial" \
  -F "tags=contract,case-law"
```

**Form Parameters:**
- `file` (required): Document file (PDF, DOC, DOCX, TXT)
- `collection_name` (required): Target collection name
- `tenant_id` (optional): Tenant identifier
- `mode` (optional): Processing mode (judicial/sales/research)
- `tags` (optional): Comma-separated tags

**Response:**
```json
{
  "success": true,
  "document_id": "doc_1234567890",
  "filename": "contract_agreement.pdf",
  "chunks_created": 15,
  "collection_name": "legal_docs",
  "upload_time": 2.34
}
```

#### List Documents
```
GET /documents
```

**Query Parameters:**
- `collection_name` (required): Collection to query
- `tenant_id` (optional): Filter by tenant
- `mode` (optional): Filter by mode
- `limit` (optional): Results limit (default: 50)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_1234567890",
      "filename": "contract_agreement.pdf",
      "file_size": 1024000,
      "upload_date": "2024-01-15T10:30:00Z",
      "document_type": "legal",
      "tags": ["contract", "case-law"],
      "chunk_count": 15
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### Get Document Details
```
GET /documents/{document_id}
```

**Response:**
```json
{
  "id": "doc_1234567890",
  "filename": "contract_agreement.pdf",
  "metadata": {
    "file_size": 1024000,
    "upload_date": "2024-01-15T10:30:00Z",
    "document_type": "legal",
    "sensitivity_level": "confidential",
    "tenant_id": "tenant_123",
    "mode": "judicial"
  },
  "chunks": [
    {
      "id": "chunk_1",
      "content_preview": "This agreement is entered into by and between...",
      "metadata": {
        "chunk_index": 0,
        "page_number": 1
      }
    }
  ]
}
```

#### Delete Document
```
DELETE /documents/{document_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

### 2. Query Processing

#### Process Query
```
POST /query
```

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "What are the key legal precedents for contract disputes?",
    "collection_name": "legal_docs",
    "mode": "judicial",
    "k": 5,
    "tenant_id": "tenant_123"
  }'
```

**Request Body:**
```json
{
  "query": "string (required)",
  "collection_name": "string (required)",
  "mode": "judicial|sales|research (optional, default: research)",
  "k": "integer (optional, default: 4)",
  "tenant_id": "string (optional)",
  "metadata_filter": {
    "tags": ["contract"],
    "document_type": "legal"
  }
}
```

**Response:**
```json
{
  "query": "What are the key legal precedents for contract disputes?",
  "results": [
    {
      "type": "response",
      "content": "Based on the retrieved documents, the key precedents for contract disputes include...",
      "confidence": "high",
      "citation_count": 3
    },
    {
      "type": "citation",
      "document_id": "doc_1234567890",
      "source": "contract_law_case.pdf",
      "content_snippet": "The court held that breach of contract requires...",
      "metadata": {
        "chunk_index": 2,
        "upload_date": "2024-01-15T10:30:00Z",
        "tags": ["contract", "precedent"],
        "distance": 0.15
      }
    }
  ],
  "collection_name": "legal_docs",
  "mode": "judicial",
  "execution_time": 1.25
}
```

#### Stream Query Response
```
POST /query/stream
```

**Response:** Server-Sent Events stream with chunks of the response

### 3. Collection Management

#### Create Collection
```
POST /collections
```

**Request:**
```json
{
  "name": "legal_documents_2024",
  "description": "Legal documents for 2024 cases",
  "tenant_id": "tenant_123",
  "mode": "judicial",
  "metadata": {
    "jurisdiction": "kenya",
    "year": "2024"
  }
}
```

**Response:**
```json
{
  "success": true,
  "name": "legal_documents_2024",
  "description": "Legal documents for 2024 cases",
  "tenant_id": "tenant_123",
  "mode": "judicial",
  "document_count": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### List Collections
```
GET /collections
```

**Query Parameters:**
- `tenant_id` (optional): Filter by tenant
- `mode` (optional): Filter by mode
- `limit` (optional): Results limit

**Response:**
```json
{
  "collections": [
    {
      "name": "legal_documents_2024",
      "description": "Legal documents for 2024 cases",
      "tenant_id": "tenant_123",
      "mode": "judicial",
      "document_count": 25,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Get Collection Details
```
GET /collections/{collection_name}
```

**Response:**
```json
{
  "name": "legal_documents_2024",
  "description": "Legal documents for 2024 cases",
  "metadata": {
    "jurisdiction": "kenya",
    "year": "2024"
  },
  "statistics": {
    "document_count": 25,
    "total_chunks": 342,
    "average_document_size": "1.2MB",
    "last_updated": "2024-01-15T14:22:00Z"
  },
  "access_control": {
    "owners": ["user_123"],
    "readers": ["user_456", "user_789"]
  }
}
```

#### Delete Collection
```
DELETE /collections/{collection_name}
```

### 4. Payment Processing

#### Initiate Payment
```
POST /payments/initiate
```

**Request:**
```json
{
  "user_id": "user_123",
  "amount": 499.0,
  "phone_number": "254712345678",
  "product_info": {
    "name": "Premium Subscription",
    "category": "subscription",
    "price": 499.0,
    "duration": 30
  },
  "collection_name": "premium_docs"
}
```

**Response:**
```json
{
  "success": true,
  "payment_id": "pay_1234567890",
  "merchant_request_id": "mr_1234567890",
  "customer_message": "Request sent to your phone",
  "amount": 499.0
}
```

#### Check Payment Status
```
GET /payments/status/{payment_id}
```

**Response:**
```json
{
  "success": true,
  "payment_id": "pay_1234567890",
  "status": "completed",
  "result_code": "0",
  "result_desc": "Success"
}
```

#### Get Payment History
```
GET /payments/history/{user_id}
```

### 5. Tenant Management

#### Create Tenant
```
POST /tenants
```

**Request:**
```json
{
  "name": "ABC Legal Firm",
  "description": "Premium legal services provider",
  "admin_user_id": "user_123",
  "metadata": {
    "industry": "legal",
    "location": "Nairobi"
  }
}
```

#### List Tenants
```
GET /tenants
```

#### Add User to Tenant
```
POST /tenants/{tenant_id}/users
```

**Request:**
```json
{
  "user_id": "user_456",
  "access_level": "member",
  "metadata": {
    "department": "research"
  }
}
```

### 6. System Administration

#### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "backend-api",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "llm_service": "healthy",
    "vector_store": "healthy"
  }
}
```

#### System Status
```
GET /status
```

**Response:**
```json
{
  "uptime": "2h 30m 15s",
  "memory_usage": "1.2GB",
  "cpu_usage": "45%",
  "active_connections": 23,
  "total_documents": 1250,
  "total_collections": 15
}
```

#### Get API Documentation
```
GET /docs
```

## Webhook Endpoints

### Payment Callback
```
POST /webhooks/payment
```

**Request Body:**
```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "mr_1234567890",
      "CheckoutRequestID": "cr_1234567890",
      "ResultCode": 0,
      "ResultDesc": "Success"
    }
  }
}
```

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Data Models

### Document Metadata
```json
{
  "filename": "string",
  "file_size": "integer",
  "upload_date": "datetime",
  "collection_name": "string",
  "document_type": "string",
  "tags": ["string"],
  "tenant_id": "string",
  "mode": "string",
  "sensitivity_level": "string",
  "page_count": "integer"
}
```

### Query Request
```json
{
  "query": "string",
  "collection_name": "string",
  "mode": "string",
  "k": "integer",
  "tenant_id": "string",
  "metadata_filter": "object"
}
```

### Payment Request
```json
{
  "user_id": "string",
  "amount": "number",
  "phone_number": "string",
  "product_info": "object",
  "collection_name": "string"
}
```

## Examples

### Complete Document Processing Workflow

```bash
# 1. Create collection
curl -X POST "http://localhost:8000/api/v1/collections" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "legal_research_2024",
    "description": "2024 legal research documents",
    "mode": "judicial"
  }'

# 2. Upload document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@contract.pdf" \
  -F "collection_name=legal_research_2024" \
  -F "mode=judicial" \
  -F "tags=contract,precedent"

# 3. Query documents
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "What are the key contract law precedents?",
    "collection_name": "legal_research_2024",
    "mode": "judicial",
    "k": 5
  }'
```

## Client Libraries

### Python Example
```python
import requests

class RAGClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def query(self, query_text, collection_name, **kwargs):
        payload = {
            "query": query_text,
            "collection_name": collection_name,
            **kwargs
        }
        response = requests.post(
            f"{self.base_url}/query",
            json=payload,
            headers=self.headers
        )
        return response.json()
```

## Support

For API support, please contact the system administrator or check the system logs for detailed error information.