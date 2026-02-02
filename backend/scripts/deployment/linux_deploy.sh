#!/bin/bash
# Linux Deployment Script for RAG Platform
# Usage: ./linux_deploy.sh [deploy|start|stop|status|logs|backup|restore]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        print_status "Please install Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        print_status "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_success "Docker Compose is installed"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_status "Please start Docker service"
        exit 1
    fi
    print_success "Docker daemon is running"
}

# Setup directories
setup_directories() {
    print_status "Setting up directories..."
    
    mkdir -p local_storage/{chroma,ollama,logs,backups}
    print_success "Directories created"
}

# Create environment file
create_env_file() {
    if [ ! -f "backend/.env" ]; then
        print_status "Creating environment file..."
        cat > backend/.env << EOF
# RAG Platform Environment Configuration
ENVIRONMENT=production
DEBUG=False
CHROMA_DB_PATH=/home/app/chroma_db
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b
SECRET_KEY=your-secret-key-change-in-production
API_V1_STR=/api/v1
ALLOWED_HOSTS=localhost,127.0.0.1
LOG_LEVEL=INFO
EOF
        print_success "Environment file created"
    fi
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    docker-compose build
    print_success "Docker images built successfully"
}

# Start services
start_services() {
    print_status "Starting services..."
    docker-compose up -d
    print_success "Services started successfully"
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_success "Services stopped successfully"
}

# Check service status
show_status() {
    print_status "Service Status:"
    docker-compose ps
}

# Show logs
show_logs() {
    print_status "Showing service logs..."
    docker-compose logs -f
}

# Create backup
create_backup() {
    print_status "Creating backup..."
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_DIR="local_storage/backups"
    
    # Create backup of data volumes
    for volume in chroma-data ollama-data; do
        BACKUP_FILE="${BACKUP_DIR}/${volume}_${TIMESTAMP}.tar"
        docker run --rm \
            -v ${volume}:/volume \
            -v ${PWD}/${BACKUP_DIR}:/backup \
            alpine tar czf /backup/${volume}_${TIMESTAMP}.tar -C /volume .
        print_success "Backup created: ${BACKUP_FILE}"
    done
    
    print_success "Backup completed"
}

# Restore from backup
restore_backup() {
    if [ -z "$1" ]; then
        print_error "Backup name required for restore"
        print_status "Usage: $0 restore <backup_timestamp>"
        exit 1
    fi
    
    BACKUP_NAME="$1"
    BACKUP_DIR="local_storage/backups"
    
    print_status "Restoring from backup: ${BACKUP_NAME}"
    
    # Stop services first
    docker-compose down
    
    # Restore data volumes
    for volume in chroma-data ollama-data; do
        BACKUP_FILE="${BACKUP_DIR}/${volume}_${BACKUP_NAME}.tar"
        if [ -f "${BACKUP_FILE}" ]; then
            docker run --rm \
                -v ${volume}:/volume \
                -v ${PWD}/${BACKUP_DIR}:/backup \
                alpine tar xzf /backup/${volume}_${BACKUP_NAME}.tar -C /volume
            print_success "Restored ${volume} from ${BACKUP_FILE}"
        else
            print_warning "Backup file not found: ${BACKUP_FILE}"
        fi
    done
    
    # Restart services
    docker-compose up -d
    print_success "Restore completed"
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    # Wait for backend API
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend API is healthy"
            break
        fi
        sleep 2
    done
    
    # Wait for frontend
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_success "Frontend is available"
            break
        fi
        sleep 2
    done
}

# Main deployment function
deploy_platform() {
    print_status "Deploying RAG Platform..."
    
    check_prerequisites
    setup_directories
    create_env_file
    build_images
    start_services
    wait_for_services
    
    print_success "Deployment completed successfully!"
    print_status "Access the platform at:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Documentation: http://localhost:8000/docs"
    echo "  Vector Database: http://localhost:8001"
    echo "  Ollama: http://localhost:11434"
}

# Parse command line arguments
ACTION=${1:-deploy}
BACKUP_NAME=${2:-}

case $ACTION in
    deploy)
        deploy_platform
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    backup)
        create_backup
        ;;
    restore)
        restore_backup "$BACKUP_NAME"
        ;;
    *)
        echo "Usage: $0 [deploy|start|stop|status|logs|backup|restore]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Complete deployment (default)"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  status   - Show service status"
        echo "  logs     - Show service logs"
        echo "  backup   - Create data backup"
        echo "  restore  - Restore from backup"
        exit 1
        ;;
esac