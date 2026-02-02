#!/usr/bin/env python3
"""
Local Server Deployment Script
Automates deployment of RAG platform to local server environment
"""

import subprocess
import sys
import os
import argparse
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LocalDeploymentManager:
    """Manages local server deployment of RAG platform"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        
        # Deployment configuration
        self.config = {
            "services": ["backend", "frontend", "chromadb", "ollama"],
            "ports": {
                "backend": 8000,
                "frontend": 3000,
                "chromadb": 8001,
                "ollama": 11434
            },
            "volumes": {
                "chroma-data": "./local_storage/chroma",
                "ollama-data": "./local_storage/ollama"
            }
        }
    
    def check_prerequisites(self) -> bool:
        """Check system prerequisites for deployment"""
        logger.info("🔍 Checking deployment prerequisites...")
        
        prerequisites = [
            ("Docker", ["docker", "--version"]),
            ("Docker Compose", ["docker-compose", "--version"]),
            ("Python", ["python", "--version"]),
            ("Git", ["git", "--version"])
        ]
        
        missing = []
        for name, command in prerequisites:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"✅ {name}: {result.stdout.strip()}")
                else:
                    logger.error(f"❌ {name}: Command failed")
                    missing.append(name)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.error(f"❌ {name}: Not found or not accessible")
                missing.append(name)
        
        if missing:
            logger.error(f"Missing prerequisites: {', '.join(missing)}")
            return False
        
        return True
    
    def setup_directories(self) -> bool:
        """Setup required directories for deployment"""
        logger.info("📁 Setting up deployment directories...")
        
        required_dirs = [
            self.project_root / "local_storage",
            self.project_root / "local_storage" / "chroma",
            self.project_root / "local_storage" / "ollama",
            self.project_root / "local_storage" / "logs",
            self.project_root / "local_storage" / "backups"
        ]
        
        try:
            for directory in required_dirs:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ Created directory: {directory}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create directories: {e}")
            return False
    
    def build_images(self, no_cache: bool = False) -> bool:
        """Build Docker images"""
        logger.info("🏗️  Building Docker images...")
        
        build_args = ["docker-compose", "build"]
        if no_cache:
            build_args.append("--no-cache")
        
        try:
            result = subprocess.run(
                build_args,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✅ Docker images built successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Docker build failed: {e.stderr}")
            return False
    
    def start_services(self, services: Optional[List[str]] = None) -> bool:
        """Start specified services or all services"""
        logger.info("🚀 Starting services...")
        
        if services:
            service_list = " ".join(services)
            cmd = ["docker-compose", "up", "-d"] + services
            logger.info(f"Starting services: {service_list}")
        else:
            cmd = ["docker-compose", "up", "-d"]
            logger.info("Starting all services")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✅ Services started successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to start services: {e.stderr}")
            return False
    
    def stop_services(self, services: Optional[List[str]] = None) -> bool:
        """Stop specified services or all services"""
        logger.info("🛑 Stopping services...")
        
        if services:
            service_list = " ".join(services)
            cmd = ["docker-compose", "down"] + services
            logger.info(f"Stopping services: {service_list}")
        else:
            cmd = ["docker-compose", "down"]
            logger.info("Stopping all services")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✅ Services stopped successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to stop services: {e.stderr}")
            return False
    
    def check_service_health(self, timeout: int = 300) -> Dict[str, bool]:
        """Check health of all services"""
        logger.info("🩺 Checking service health...")
        
        health_status = {}
        start_time = time.time()
        
        # Services to check with their health endpoints
        service_checks = {
            "backend": ("http://localhost:8000/health", "API Health"),
            "frontend": ("http://localhost:3000", "Frontend Availability"),
            "chromadb": ("http://localhost:8001/api/v1/heartbeat", "Vector DB"),
            "ollama": ("http://localhost:11434/", "LLM Service")
        }
        
        import requests
        
        while time.time() - start_time < timeout:
            all_healthy = True
            
            for service, (endpoint, description) in service_checks.items():
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        health_status[service] = True
                        logger.info(f"✅ {description}: Healthy")
                    else:
                        health_status[service] = False
                        logger.warning(f"⚠️  {description}: Status {response.status_code}")
                        all_healthy = False
                except requests.RequestException:
                    health_status[service] = False
                    logger.warning(f"⚠️  {description}: Unreachable")
                    all_healthy = False
            
            if all_healthy:
                logger.info("🎉 All services are healthy!")
                return health_status
            
            time.sleep(10)  # Wait before next check
        
        logger.error("❌ Services failed to become healthy within timeout")
        return health_status
    
    def setup_ollama_model(self) -> bool:
        """Setup Ollama model after deployment"""
        logger.info("🦙 Setting up Ollama model...")
        
        try:
            # Run the Ollama setup script
            setup_script = self.backend_dir / "scripts" / "setup_ollama.py"
            if setup_script.exists():
                result = subprocess.run(
                    [sys.executable, str(setup_script)],
                    cwd=self.backend_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info("✅ Ollama model setup completed")
                return True
            else:
                logger.warning("⚠️  Ollama setup script not found")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ollama setup failed: {e.stderr}")
            return False
    
    def create_env_file(self) -> bool:
        """Create environment file for deployment"""
        logger.info("⚙️  Creating environment configuration...")
        
        env_content = """
# RAG Platform Local Deployment Configuration

# Environment
ENVIRONMENT=production
DEBUG=False

# Database
CHROMA_DB_PATH=/home/app/chroma_db

# LLM
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b

# API Settings
API_V1_STR=/api/v1

# Security
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Payment (Safaricom Daraja)
DARAJA_CONSUMER_KEY=your_consumer_key
DARAJA_CONSUMER_SECRET=your_consumer_secret
DARAJA_BUSINESS_SHORT_CODE=your_short_code
DARAJA_PASSKEY=your_passkey
DARAJA_ENVIRONMENT=sandbox

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
        """.strip()
        
        env_file = self.backend_dir / ".env"
        try:
            with open(env_file, 'w') as f:
                f.write(env_content)
            logger.info("✅ Environment file created")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create environment file: {e}")
            return False
    
    def backup_data(self) -> bool:
        """Backup persistent data volumes"""
        logger.info("💾 Creating data backup...")
        
        backup_dir = self.project_root / "local_storage" / "backups"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"rag_backup_{timestamp}"
        
        try:
            # Create backup using docker volumes
            volumes = ["chroma-data", "ollama-data"]
            
            for volume in volumes:
                backup_file = backup_dir / f"{volume}_{backup_name}.tar"
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{volume}:/volume",
                    "-v", f"{backup_dir}:/backup",
                    "alpine",
                    "tar", "czf", f"/backup/{volume}_{backup_name}.tar", "-C", "/volume", "."
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"✅ Backed up {volume} to {backup_file}")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
    
    def restore_data(self, backup_name: str) -> bool:
        """Restore data from backup"""
        logger.info(f"🔄 Restoring data from {backup_name}...")
        
        backup_dir = self.project_root / "local_storage" / "backups"
        
        try:
            volumes = ["chroma-data", "ollama-data"]
            
            for volume in volumes:
                backup_file = backup_dir / f"{volume}_{backup_name}.tar"
                if not backup_file.exists():
                    logger.error(f"❌ Backup file not found: {backup_file}")
                    continue
                
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{volume}:/volume",
                    "-v", f"{backup_dir}:/backup",
                    "alpine",
                    "tar", "xzf", f"/backup/{volume}_{backup_name}.tar", "-C", "/volume"
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"✅ Restored {volume} from {backup_file}")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Restore failed: {e}")
            return False
    
    def deploy(self, rebuild: bool = False, setup_model: bool = True) -> bool:
        """Complete deployment workflow"""
        logger.info("🚀 Starting RAG Platform deployment...")
        
        start_time = time.time()
        
        # Step 1: Prerequisites check
        if not self.check_prerequisites():
            logger.error("❌ Prerequisites check failed")
            return False
        
        # Step 2: Setup directories
        if not self.setup_directories():
            logger.error("❌ Directory setup failed")
            return False
        
        # Step 3: Create environment file
        if not self.create_env_file():
            logger.error("❌ Environment setup failed")
            return False
        
        # Step 4: Build images if requested
        if rebuild:
            if not self.build_images(no_cache=True):
                logger.error("❌ Image build failed")
                return False
        
        # Step 5: Start services
        if not self.start_services():
            logger.error("❌ Service startup failed")
            return False
        
        # Step 6: Wait for services to be healthy
        health_status = self.check_service_health()
        if not all(health_status.values()):
            logger.error("❌ Some services are not healthy")
            return False
        
        # Step 7: Setup Ollama model
        if setup_model:
            if not self.setup_ollama_model():
                logger.warning("⚠️  Ollama model setup failed (continuing anyway)")
        
        deployment_time = time.time() - start_time
        logger.info(f"🎉 Deployment completed successfully in {deployment_time:.2f} seconds!")
        
        self.print_deployment_info()
        return True
    
    def print_deployment_info(self):
        """Print deployment information and access details"""
        print("\n" + "="*60)
        print("RAG PLATFORM DEPLOYMENT SUCCESSFUL!")
        print("="*60)
        print("✅ Access the platform at:")
        print("   Frontend: http://localhost:3000")
        print("   Backend API: http://localhost:8000")
        print("   API Documentation: http://localhost:8000/docs")
        print("   Vector Database: http://localhost:8001")
        print("   Ollama: http://localhost:11434")
        print("\n🔧 Management Commands:")
        print("   Start services: docker-compose up -d")
        print("   Stop services: docker-compose down")
        print("   View logs: docker-compose logs -f")
        print("   Check status: docker-compose ps")
        print("\n💾 Data Management:")
        print("   Backup data: python scripts/deployment/local_deploy.py backup")
        print("   Restore data: python scripts/deployment/local_deploy.py restore <backup_name>")
        print("="*60)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RAG Platform Local Deployment")
    parser.add_argument(
        "action",
        choices=["deploy", "start", "stop", "backup", "restore", "status", "health"],
        help="Action to perform"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild Docker images"
    )
    parser.add_argument(
        "--no-model-setup",
        action="store_true",
        help="Skip Ollama model setup"
    )
    parser.add_argument(
        "--services",
        nargs="*",
        help="Specific services to start/stop"
    )
    parser.add_argument(
        "--backup-name",
        help="Backup name for restore operation"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    manager = LocalDeploymentManager(str(project_root))
    
    # Execute requested action
    if args.action == "deploy":
        success = manager.deploy(
            rebuild=args.rebuild,
            setup_model=not args.no_model_setup
        )
        sys.exit(0 if success else 1)
    
    elif args.action == "start":
        success = manager.start_services(args.services)
        sys.exit(0 if success else 1)
    
    elif args.action == "stop":
        success = manager.stop_services(args.services)
        sys.exit(0 if success else 1)
    
    elif args.action == "backup":
        success = manager.backup_data()
        sys.exit(0 if success else 1)
    
    elif args.action == "restore":
        if not args.backup_name:
            print("Error: --backup-name is required for restore operation")
            sys.exit(1)
        success = manager.restore_data(args.backup_name)
        sys.exit(0 if success else 1)
    
    elif args.action == "status":
        # Show docker-compose status
        subprocess.run(["docker-compose", "ps"])
    
    elif args.action == "health":
        health_status = manager.check_service_health()
        for service, healthy in health_status.items():
            status = "✅ Healthy" if healthy else "❌ Unhealthy"
            print(f"{service:12}: {status}")

if __name__ == "__main__":
    main()