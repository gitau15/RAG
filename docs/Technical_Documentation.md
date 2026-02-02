# RAG Platform Technical Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Installation Guide](#installation-guide)
4. [Configuration](#configuration)
5. [Development Setup](#development-setup)
6. [Deployment](#deployment)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)
10. [Security Guidelines](#security-guidelines)

## System Overview

The RAG Platform is a comprehensive document intelligence system that combines:
- **Retrieval-Augmented Generation** for intelligent document querying
- **Multi-tenant architecture** for secure data isolation
- **Privacy-first design** with local inference capabilities
- **Payment integration** for commercial deployment
- **Legal compliance** with citation tracking and document provenance

## Technology Stack

### Backend
- **Python 3.10+** - Core programming language
- **FastAPI** - High-performance web framework
- **LangChain** - RAG orchestration framework
- **ChromaDB** - Vector database for similarity search
- **Ollama** - Local LLM inference engine
- **Sentence Transformers** - Document embedding generation

### Frontend
- **React.js 18+** - Component-based UI framework
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client library

### Infrastructure
- **Docker** - Containerization platform
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy and web server
- **Safaricom Daraja API** - M-Pesa payment processing

### Development Tools
- **Pytest** - Testing framework
- **Black** - Code formatting
- **Flake8** - Code linting
- **Git** - Version control

## Installation Guide

### Prerequisites

**Windows:**
```bash
# Install Docker Desktop
# Install Python 3.10+
# Install Git
```

**Linux/macOS:**
```bash
# Install Docker Engine
# Install Docker Compose
# Install Python 3.10+
# Install Git
```

### Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/gitau15/RAG.git
cd RAG
```

2. **Deploy the platform:**
```bash
# Windows
backend\scripts\deployment\windows_deploy.bat deploy

# Linux/macOS
chmod +x backend/scripts/deployment/linux_deploy.sh
./backend/scripts/deployment/linux_deploy.sh deploy

# Cross-platform (Python)
python backend/scripts/deployment/local_deploy.py deploy
```

3. **Access the platform:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Configuration

### Environment Variables

Create `backend/.env` file:

```env
# Application Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-secret-key-change-in-production

# Database Configuration
CHROMA_DB_PATH=/home/app/chroma_db

# LLM Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b

# API Settings
API_V1_STR=/api/v1
ALLOWED_HOSTS=localhost,127.0.0.1

# Payment Configuration (Safaricom Daraja)
DARAJA_CONSUMER_KEY=your_consumer_key
DARAJA_CONSUMER_SECRET=your_consumer_secret
DARAJA_BUSINESS_SHORT_CODE=your_short_code
DARAJA_PASSKEY=your_passkey
DARAJA_ENVIRONMENT=sandbox

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
```

### Docker Configuration

Main configuration in `docker-compose.yml`:

```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    depends_on:
      - chromadb
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma-data:/chroma/chroma/

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
```

## Development Setup

### Local Development Environment

1. **Setup Python environment:**
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
pip install -r test_requirements.txt
```

2. **Setup frontend:**
```bash
cd frontend
npm install
```

3. **Run development servers:**
```bash
# Backend (terminal 1)
cd backend
uvicorn main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm start

# Vector DB (terminal 3)
docker run -d -p 8001:8000 chromadb/chroma:latest

# LLM (terminal 4)
docker run -d -p 11434:11434 ollama/ollama:latest
```

### Development Commands

```bash
# Run tests
python -m pytest tests/ -v

# Run specific test types
python -m pytest tests/ -m "unit"
python -m pytest tests/ -m "integration"

# Generate coverage report
python -m pytest tests/ --cov=app --cov-report=html

# Format code
black .
flake8 .

# Run linter
flake8 --max-line-length=100

# Type checking
mypy app/
```

## Deployment

### Production Deployment

1. **Prepare production environment:**
```bash
# Set production environment variables
export ENVIRONMENT=production
export SECRET_KEY=your-production-secret-key

# Build production images
docker-compose build --no-cache
```

2. **Deploy services:**
```bash
# Start all services
docker-compose up -d

# Monitor deployment
docker-compose logs -f

# Check service status
docker-compose ps
```

3. **Post-deployment setup:**
```bash
# Setup Ollama model
python backend/scripts/setup_ollama.py

# Run health checks
python backend/scripts/deployment/local_deploy.py health
```

### Backup and Recovery

```bash
# Create backup
python backend/scripts/deployment/local_deploy.py backup

# List backups
ls local_storage/backups/

# Restore from backup
python backend/scripts/deployment/local_deploy.py restore --backup-name 20240101_120000
```

## API Reference

### Core Endpoints

**Document Management:**
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document

**Query Processing:**
- `POST /api/v1/query` - Process query
- `POST /api/v1/query/stream` - Stream query response

**Collection Management:**
- `POST /api/v1/collections` - Create collection
- `GET /api/v1/collections` - List collections
- `GET /api/v1/collections/{name}` - Get collection details

**Payment Processing:**
- `POST /api/v1/payments/initiate` - Initiate payment
- `GET /api/v1/payments/status/{id}` - Check payment status

### Example Usage

```python
import requests

# Initialize client
base_url = "http://localhost:8000/api/v1"
headers = {"Authorization": "Bearer YOUR_API_KEY"}

# Upload document
with open("document.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "collection_name": "legal_docs",
        "mode": "judicial",
        "tags": "contract,precedent"
    }
    response = requests.post(
        f"{base_url}/documents/upload",
        files=files,
        data=data,
        headers=headers
    )

# Process query
query_data = {
    "query": "What are the key legal precedents?",
    "collection_name": "legal_docs",
    "mode": "judicial",
    "k": 5
}
response = requests.post(
    f"{base_url}/query",
    json=query_data,
    headers=headers
)
```

## Troubleshooting

### Common Issues

**1. Docker Services Not Starting**
```bash
# Check Docker status
docker info

# View service logs
docker-compose logs <service_name>

# Restart services
docker-compose down
docker-compose up -d
```

**2. Ollama Model Issues**
```bash
# Check Ollama status
curl http://localhost:11434/

# Reinstall model
python backend/scripts/setup_ollama.py --reinstall

# Check available models
curl http://localhost:11434/api/tags
```

**3. Database Connection Errors**
```bash
# Check ChromaDB status
curl http://localhost:8001/api/v1/heartbeat

# Restart database
docker-compose restart chromadb

# Check volumes
docker volume ls
```

**4. API Response Issues**
```bash
# Check backend logs
docker-compose logs backend

# Test health endpoint
curl http://localhost:8000/health

# Check API documentation
http://localhost:8000/docs
```

### Debugging Commands

```bash
# View all containers
docker ps -a

# View container logs
docker logs <container_name>

# Execute command in container
docker exec -it <container_name> /bin/bash

# Check system resources
docker stats

# Clean up unused resources
docker system prune -a
```

## Performance Optimization

### Resource Allocation

```yaml
# docker-compose.yml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
  
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
```

### Caching Strategies

```python
# Enable Redis caching (future enhancement)
REDIS_URL = "redis://localhost:6379"
CACHE_TTL = 3600  # 1 hour
```

### Database Optimization

```python
# ChromaDB configuration
CHROMA_SETTINGS = {
    "persist_directory": "/home/app/chroma_db",
    "anonymized_telemetry": False,
    "allow_reset": True
}
```

## Security Guidelines

### Production Security Checklist

- [ ] Change default passwords and API keys
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure firewall rules
- [ ] Set up regular security updates
- [ ] Implement proper backup strategy
- [ ] Configure monitoring and alerting
- [ ] Review and test access controls
- [ ] Validate input sanitization
- [ ] Enable audit logging
- [ ] Test disaster recovery procedures

### Security Best Practices

```python
# Input validation
from pydantic import BaseModel, validator

class SecureRequest(BaseModel):
    query: str
    collection_name: str
    
    @validator('query')
    def validate_query(cls, v):
        if len(v) > 1000:
            raise ValueError('Query too long')
        # Sanitize input
        return v.strip()

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/query")
@limiter.limit("100/minute")
async def process_query(request: Request, query_data: QueryRequest):
    # Process query
    pass
```

## Monitoring and Maintenance

### Health Checks

```bash
# Automated health monitoring
python backend/scripts/deployment/local_deploy.py health

# Service status
docker-compose ps

# Resource usage
docker stats
```

### Log Management

```bash
# View recent logs
docker-compose logs --tail=100

# Follow logs in real-time
docker-compose logs -f

# Export logs
docker-compose logs > system_logs.txt
```

### Performance Monitoring

```python
# Add performance metrics (future enhancement)
import time
from prometheus_client import Counter, Histogram

QUERY_DURATION = Histogram('query_duration_seconds', 'Query processing time')
QUERIES_PROCESSED = Counter('queries_processed_total', 'Total queries processed')

@QUERY_DURATION.time()
async def process_query(query_data):
    start_time = time.time()
    # Process query
    QUERIES_PROCESSED.inc()
    return result
```

This documentation provides a comprehensive guide for installing, configuring, developing, and maintaining the RAG Platform. For additional support, please refer to the specific component documentation or contact the development team.