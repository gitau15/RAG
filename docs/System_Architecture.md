# RAG Platform System Architecture

## Overview

The RAG Platform is a privacy-first, local inference system designed for secure document processing and intelligent query answering. The architecture follows a modular, service-oriented design with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Web App   │  │ Mobile App  │  │  API Client │  │  CLI    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS/API
┌─────────────────────────▼───────────────────────────────────────┐
│                      Load Balancer (Optional)                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    API Gateway / Reverse Proxy                 │
│                    (NGINX / Traefik)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│   Frontend    │ │   Backend     │ │  Monitoring   │
│   (React)     │ │   (FastAPI)   │ │   (Prometheus)│
└───────────────┘ └───────┬───────┘ └───────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  Vector DB    │ │    LLM        │ │  Payment      │
│  (ChromaDB)   │ │  (Ollama)     │ │   (Daraja)    │
└───────────────┘ └───────────────┘ └───────────────┘
```

## Component Architecture

### 1. Frontend Layer

**Technology:** React.js with Tailwind CSS

**Components:**
- **Dashboard** - System overview and statistics
- **Chat Interface** - Interactive query processing
- **Document Manager** - Upload and document management
- **Collection Manager** - Collection organization
- **Settings Panel** - User preferences and configuration

**Features:**
- Responsive design for all device sizes
- Dark mode theme
- Real-time updates via WebSockets
- Form validation and error handling
- Loading states and progress indicators

### 2. API Layer

**Technology:** FastAPI (Python 3.10+)

**Core Modules:**

#### Main Application (`main.py`)
- Application initialization and configuration
- CORS middleware setup
- API router registration
- Health check endpoints
- Error handling middleware

#### Core Components (`app/core/`)
- **Configuration Management** - Environment-based settings
- **Logging** - Structured logging with multiple handlers
- **Security** - Authentication and authorization middleware

#### API Routes (`app/api/`)
- **Document Endpoints** - Upload, list, retrieve, delete
- **Query Endpoints** - Process queries, streaming responses
- **Collection Endpoints** - CRUD operations for collections
- **Payment Endpoints** - Payment initiation and status
- **Tenant Endpoints** - Multi-tenant management
- **System Endpoints** - Health, status, monitoring

### 3. Business Logic Layer

#### Document Processing (`app/ingestion/`)
- **Document Parser** - Multi-format document parsing (PDF, DOC, TXT)
- **Ingestion Pipeline** - End-to-end document processing
- **Chunking Engine** - Intelligent text segmentation
- **Metadata Extractor** - Document metadata analysis

#### Retrieval System (`app/retrieval/`)
- **Retrieval Config Manager** - Parameterized retrieval strategies
- **Advanced Retrievers** - Multiple retrieval algorithms
- **Query Processing** - Query enhancement and expansion
- **Result Ranking** - Relevance scoring and sorting

#### RAG Orchestrator (`app/orchestrator/`)
- **Mode Router** - Intelligent mode detection and routing
- **Query Processor** - Complete RAG pipeline orchestration
- **Context Builder** - Document context assembly
- **Response Generator** - LLM response formatting

#### Legal Processing (`app/citation/`)
- **Citation Engine** - Legal document citation tracking
- **Legal Formatter** - Multiple citation style formatting
- **Citation Validator** - Quality and completeness checking

#### Payment Processing (`app/payments/`)
- **Daraja Client** - Safaricom API integration
- **Payment Processor** - Payment workflow management
- **Callback Handler** - Payment notification processing

#### Multi-tenancy (`app/tenancy/`)
- **Tenant Manager** - Tenant lifecycle management
- **Metadata Tagger** - Intelligent document tagging
- **Access Control** - Role-based permissions
- **Data Isolation** - Tenant data separation

#### Privacy System (`app/privacy/`)
- **Privacy Manager** - Data protection policies
- **Local Inference** - Privacy-preserving processing
- **Data Encryption** - Tenant-specific encryption
- **Audit Logging** - Compliance tracking

### 4. Data Layer

#### Vector Database (`app/vectorstore/`)
- **ChromaDB Client** - Vector storage and retrieval
- **Embedding Manager** - Document embedding generation
- **Collection Management** - Multi-tenant collections
- **Similarity Search** - Vector-based document retrieval

#### LLM Integration (`app/llm/`)
- **Ollama Client** - Local LLM inference
- **System Prompts** - Mode-specific prompt engineering
- **Response Processing** - Output formatting and filtering
- **Model Management** - Model loading and health checks

### 5. External Services

#### Payment Gateway
- **Safaricom Daraja API** - M-Pesa STK Push integration
- **Payment Validation** - Transaction verification
- **Callback Processing** - Payment status updates

#### Infrastructure Services
- **Docker** - Containerization and deployment
- **Docker Compose** - Multi-service orchestration
- **Nginx** - Reverse proxy and static file serving

## Data Flow Architecture

### Document Ingestion Flow

```
1. Document Upload
   ↓
2. File Validation & Metadata Extraction
   ↓
3. Document Parsing (PyPDF/Unstructured)
   ↓
4. Text Chunking & Processing
   ↓
5. Embedding Generation (Sentence Transformers)
   ↓
6. Vector Storage (ChromaDB)
   ↓
7. Metadata Indexing
   ↓
8. Completion Notification
```

### Query Processing Flow

```
1. Query Reception
   ↓
2. Mode Detection & Routing
   ↓
3. Parameter Configuration
   ↓
4. Vector Similarity Search
   ↓
5. Document Retrieval & Filtering
   ↓
6. Context Assembly
   ↓
7. Prompt Augmentation
   ↓
8. LLM Inference (Ollama)
   ↓
9. Response Processing & Citation
   ↓
10. Result Formatting & Delivery
```

### Payment Processing Flow

```
1. Payment Request
   ↓
2. Request Validation
   ↓
3. STK Push Initiation (Daraja)
   ↓
4. User Authentication (M-Pesa App)
   ↓
5. Payment Processing
   ↓
6. Callback Notification
   ↓
7. Payment Verification
   ↓
8. Service Fulfillment
   ↓
9. Confirmation Delivery
```

## Security Architecture

### Data Protection Layers

1. **Network Security**
   - HTTPS encryption
   - API rate limiting
   - IP whitelisting
   - DDoS protection

2. **Authentication & Authorization**
   - JWT token-based authentication
   - Role-based access control
   - Tenant isolation
   - Session management

3. **Data Security**
   - End-to-end encryption
   - Tenant-specific encryption keys
   - Data anonymization
   - Secure data disposal

4. **Application Security**
   - Input validation and sanitization
   - SQL injection prevention
   - XSS protection
   - CSRF protection

### Privacy Compliance

- **Data Minimization** - Only necessary data collection
- **Purpose Limitation** - Specific use case processing
- **Storage Limitation** - Automated data retention policies
- **Integrity & Confidentiality** - Encryption and access controls
- **Accountability** - Comprehensive audit logging

## Deployment Architecture

### Container Orchestration

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                       │
├─────────────────────────────────────────────────────────┤
│  Services:                                              │
│  ├── backend     (Python/FastAPI)                      │
│  ├── frontend    (React/Node.js)                       │
│  ├── chromadb    (Vector Database)                     │
│  ├── ollama      (LLM Service)                         │
│  └── nginx       (Reverse Proxy)                       │
└─────────────────────────────────────────────────────────┘
```

### Volume Management

```
Persistent Data Volumes:
├── chroma-data/     → ChromaDB vector storage
├── ollama-data/     → Ollama model cache
├── logs/           → Application logs
└── backups/        → Data backup storage
```

### Network Configuration

```
Port Mappings:
- 3000 → Frontend (React App)
- 8000 → Backend API (FastAPI)
- 8001 → ChromaDB API
- 11434 → Ollama API
```

## Scalability Architecture

### Horizontal Scaling

- **Load Balancing** - Multiple backend instances
- **Database Sharding** - Collection-based data distribution
- **Caching Layer** - Redis for frequently accessed data
- **CDN Integration** - Static asset distribution

### Vertical Scaling

- **Resource Allocation** - CPU/Memory limits per service
- **Auto-scaling** - Docker Compose scale commands
- **Performance Monitoring** - Resource usage tracking

### Multi-tenancy Scaling

- **Tenant Isolation** - Separate data collections
- **Resource Quotas** - Per-tenant resource limits
- **Concurrent Processing** - Parallel document processing

## Monitoring & Observability

### Logging System

```
Log Levels:
├── DEBUG    → Detailed diagnostic information
├── INFO     → General operational information
├── WARNING  → Warning conditions
├── ERROR    → Error conditions
└── CRITICAL → Critical error conditions

Log Destinations:
├── File     → Persistent log storage
├── Console  → Development output
└── Syslog   → System log integration
```

### Metrics Collection

**Key Metrics Tracked:**
- API response times
- Query processing latency
- Document processing throughput
- System resource usage
- Error rates and patterns
- User activity and engagement

### Health Monitoring

**Health Check Endpoints:**
- `/health` → Basic service health
- `/status` → Detailed system status
- Component-specific health checks
- Dependency health verification

## Backup & Recovery

### Backup Strategy

```
Backup Types:
├── Full Backup     → Complete system state
├── Incremental     → Changes since last backup
└── Differential    → Changes since last full backup

Backup Schedule:
├── Daily           → Incremental backups
├── Weekly          → Full backups
└── Monthly         → Archive backups
```

### Recovery Process

1. **Service Shutdown**
2. **Data Restoration**
3. **Configuration Recovery**
4. **Service Validation**
5. **Gradual Service Startup**

## Development Architecture

### Development Environment

```
Local Development Setup:
├── Docker Desktop
├── Python 3.10+
├── Node.js 18+
├── VS Code Extensions
└── Git Version Control
```

### Testing Architecture

```
Test Layers:
├── Unit Tests      → Individual component testing
├── Integration     → Component interaction testing
├── End-to-End      → Complete workflow testing
└── Performance     → Load and stress testing
```

### CI/CD Pipeline

```
GitHub Actions Workflow:
├── Code Quality    → Linting and formatting
├── Automated Tests → Unit and integration tests
├── Security Scan   → Vulnerability assessment
├── Docker Build    → Container image creation
└── Deployment      → Automated deployment
```

## Future Architecture Enhancements

### Planned Improvements

1. **Microservices Architecture**
   - Service decomposition
   - Message queue integration
   - Event-driven processing

2. **Advanced Analytics**
   - Usage analytics dashboard
   - Performance optimization
   - User behavior insights

3. **Enhanced Security**
   - Multi-factor authentication
   - Advanced encryption
   - Compliance automation

4. **Cloud Integration**
   - Hybrid deployment options
   - Cloud backup solutions
   - Multi-region deployment

This architecture provides a solid foundation for a scalable, secure, and maintainable RAG platform that can evolve with changing requirements and technology advances.