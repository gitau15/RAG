# RAG Platform Deployment Scripts

This directory contains scripts for deploying the RAG Platform to local servers.

## Prerequisites

### Windows
- Docker Desktop for Windows
- Python 3.10+
- Git

### Linux/macOS
- Docker Engine
- Docker Compose
- Python 3.10+
- Git

## Deployment Scripts

### 1. Python Deployment Manager (`local_deploy.py`)

**Features:**
- Complete deployment automation
- Health checking and monitoring
- Backup and restore functionality
- Service management
- Comprehensive logging

**Usage:**
```bash
# Complete deployment
python scripts/deployment/local_deploy.py deploy

# Deploy with rebuild
python scripts/deployment/local_deploy.py deploy --rebuild

# Start specific services
python scripts/deployment/local_deploy.py start --services backend frontend

# Stop services
python scripts/deployment/local_deploy.py stop

# Create backup
python scripts/deployment/local_deploy.py backup

# Restore from backup
python scripts/deployment/local_deploy.py restore --backup-name 20240101_120000

# Check service health
python scripts/deployment/local_deploy.py health
```

### 2. Service Manager (`service_manager.py`)

**Features:**
- Service status monitoring
- Log viewing and following
- Service scaling
- Command execution in containers
- System resource monitoring

**Usage:**
```bash
# Check service status
python scripts/deployment/service_manager.py status

# View logs
python scripts/deployment/service_manager.py logs --service backend

# Follow logs in real-time
python scripts/deployment/service_manager.py logs --service backend --follow

# Scale service
python scripts/deployment/service_manager.py scale --service backend --replicas 2

# Execute command in container
python scripts/deployment/service_manager.py exec --service backend --command "ls -la"

# Monitor system resources
python scripts/deployment/service_manager.py monitor --interval 5
```

### 3. Windows Batch Script (`windows_deploy.bat`)

**Features:**
- Simple Windows deployment
- Basic service management
- Environment setup

**Usage:**
```cmd
# Deploy platform
windows_deploy.bat deploy

# Start services
windows_deploy.bat start

# Stop services
windows_deploy.bat stop

# Check status
windows_deploy.bat status

# View logs
windows_deploy.bat logs
```

### 4. Linux Shell Script (`linux_deploy.sh`)

**Features:**
- Complete Linux deployment
- Colored output
- Backup and restore
- Health checking

**Usage:**
```bash
# Make executable
chmod +x linux_deploy.sh

# Deploy platform
./linux_deploy.sh deploy

# Start services
./linux_deploy.sh start

# Stop services
./linux_deploy.sh stop

# Create backup
./linux_deploy.sh backup

# Restore backup
./linux_deploy.sh restore 20240101_120000

# View status
./linux_deploy.sh status
```

## Deployment Process

### 1. Initial Setup
```bash
# Run deployment script
python scripts/deployment/local_deploy.py deploy

# Or on Windows
windows_deploy.bat deploy

# Or on Linux
./linux_deploy.sh deploy
```

### 2. Post-Deployment Steps
1. **Access the Platform:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

2. **Setup Ollama Model:**
   ```bash
   python backend/scripts/setup_ollama.py
   ```

3. **Verify Services:**
   ```bash
   python scripts/deployment/local_deploy.py health
   ```

## Management Commands

### Service Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend

# View service logs
docker-compose logs -f backend

# Check service status
docker-compose ps
```

### Data Management
```bash
# Create backup
python scripts/deployment/local_deploy.py backup

# List backups
ls local_storage/backups/

# Restore backup
python scripts/deployment/local_deploy.py restore --backup-name <backup_name>
```

### Monitoring
```bash
# Monitor services with Python manager
python scripts/deployment/service_manager.py monitor

# View resource usage
docker stats

# Check disk space
df -h
```

## Configuration

### Environment Variables
The deployment scripts will create a `.env` file in the `backend` directory with default configuration. You can modify these settings:

```bash
# backend/.env
ENVIRONMENT=production
DEBUG=False
CHROMA_DB_PATH=/home/app/chroma_db
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b
SECRET_KEY=your-secret-key-change-in-production
```

### Docker Compose Configuration
The main `docker-compose.yml` file in the project root controls service configuration:

```yaml
version: '3.8'
services:
  backend:
    # Backend configuration
  frontend:
    # Frontend configuration
  chromadb:
    # Vector database configuration
  ollama:
    # LLM service configuration
```

## Troubleshooting

### Common Issues

1. **Docker not running:**
   ```bash
   # Start Docker service
   sudo systemctl start docker  # Linux
   # Or start Docker Desktop on Windows/macOS
   ```

2. **Port conflicts:**
   ```bash
   # Check which ports are in use
   netstat -tulpn | grep :8000
   # Or change ports in docker-compose.yml
   ```

3. **Insufficient resources:**
   ```bash
   # Check system resources
   free -h  # Linux
   # Adjust Docker resource limits in Docker Desktop
   ```

4. **Service not starting:**
   ```bash
   # Check service logs
   docker-compose logs <service_name>
   
   # Check container status
   docker-compose ps
   
   # Rebuild and restart
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Health Checks

```bash
# Check if services are responding
curl http://localhost:8000/health
curl http://localhost:3000

# Check Docker container health
docker-compose ps

# Run comprehensive health check
python scripts/deployment/local_deploy.py health
```

## Backup and Recovery

### Automatic Backups
```bash
# Create backup
python scripts/deployment/local_deploy.py backup

# Backup location
ls local_storage/backups/
```

### Manual Backup
```bash
# Backup ChromaDB data
docker run --rm -v chroma-data:/volume -v $(pwd)/backups:/backup alpine tar czf /backup/chroma_backup.tar.gz -C /volume .

# Backup Ollama data
docker run --rm -v ollama-data:/volume -v $(pwd)/backups:/backup alpine tar czf /backup/ollama_backup.tar.gz -C /volume .
```

### Restore Process
```bash
# Stop services
docker-compose down

# Restore data
python scripts/deployment/local_deploy.py restore --backup-name <backup_name>

# Start services
docker-compose up -d
```

## Security Considerations

1. **Change default passwords** in `.env` file
2. **Use HTTPS** in production environments
3. **Regular backups** of sensitive data
4. **Monitor logs** for suspicious activity
5. **Update dependencies** regularly

## Performance Optimization

### Resource Allocation
Adjust Docker resource limits in `docker-compose.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
```

### Caching
Enable build caching for faster deployments:

```bash
# Use cache for builds
docker-compose build

# Force rebuild without cache
docker-compose build --no-cache
```

## Support

For issues with deployment scripts, please check:
1. System requirements are met
2. Docker is properly installed and running
3. Sufficient system resources are available
4. No port conflicts exist
5. Environment variables are correctly configured

The deployment logs are stored in `deployment.log` in the project root directory.