#!/usr/bin/env python3
"""
Service Management Script
Manages RAG platform services and monitoring
"""

import subprocess
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages RAG platform services"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.compose_file = self.project_root / "docker-compose.yml"
    
    def get_service_status(self) -> Dict[str, str]:
        """Get status of all services"""
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                services = json.loads(result.stdout)
                status_dict = {}
                for service in services:
                    status_dict[service["Service"]] = service["State"]
                return status_dict
            else:
                return {}
                
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            # Fallback to table format parsing
            result = subprocess.run(
                ["docker-compose", "ps"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                status_dict = {}
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 4:
                        service_name = parts[0]
                        status = parts[3]
                        status_dict[service_name] = status
                return status_dict
            
            return {}
    
    def start_service(self, service: str) -> bool:
        """Start a specific service"""
        logger.info(f"🚀 Starting service: {service}")
        try:
            subprocess.run(
                ["docker-compose", "up", "-d", service],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )
            logger.info(f"✅ Service {service} started successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to start {service}: {e}")
            return False
    
    def stop_service(self, service: str) -> bool:
        """Stop a specific service"""
        logger.info(f"🛑 Stopping service: {service}")
        try:
            subprocess.run(
                ["docker-compose", "stop", service],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )
            logger.info(f"✅ Service {service} stopped successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to stop {service}: {e}")
            return False
    
    def restart_service(self, service: str) -> bool:
        """Restart a specific service"""
        logger.info(f"🔄 Restarting service: {service}")
        try:
            subprocess.run(
                ["docker-compose", "restart", service],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )
            logger.info(f"✅ Service {service} restarted successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to restart {service}: {e}")
            return False
    
    def view_logs(self, service: Optional[str] = None, follow: bool = False, lines: int = 100):
        """View service logs"""
        cmd = ["docker-compose", "logs"]
        
        if follow:
            cmd.append("-f")
        
        if lines:
            cmd.extend(["--tail", str(lines)])
        
        if service:
            cmd.append(service)
        
        try:
            subprocess.run(cmd, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to view logs: {e}")
    
    def scale_service(self, service: str, replicas: int) -> bool:
        """Scale a service to specified number of replicas"""
        logger.info(f"📈 Scaling service {service} to {replicas} replicas")
        try:
            subprocess.run(
                ["docker-compose", "up", "-d", "--scale", f"{service}={replicas}"],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )
            logger.info(f"✅ Service {service} scaled successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to scale {service}: {e}")
            return False
    
    def exec_command(self, service: str, command: List[str]) -> bool:
        """Execute command in running service container"""
        cmd = ["docker-compose", "exec", service] + command
        try:
            subprocess.run(cmd, cwd=self.project_root, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Command execution failed: {e}")
            return False
    
    def run_command(self, service: str, command: List[str]) -> bool:
        """Run command in new container from service image"""
        cmd = ["docker-compose", "run", "--rm", service] + command
        try:
            subprocess.run(cmd, cwd=self.project_root, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Command run failed: {e}")
            return False

class SystemMonitor:
    """Monitors system resources and service health"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
    
    def get_resource_usage(self) -> Dict[str, Dict[str, str]]:
        """Get resource usage for RAG platform containers"""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", 
                 "{{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            usage_data = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        container_id, cpu, mem_usage, mem_perc, net_io, block_io = parts[:6]
                        # Get container name from ID
                        name_result = subprocess.run(
                            ["docker", "inspect", "--format", "{{.Name}}", container_id],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        container_name = name_result.stdout.strip().lstrip('/')
                        
                        usage_data[container_name] = {
                            "cpu": cpu,
                            "memory": mem_usage,
                            "memory_percent": mem_perc,
                            "network": net_io,
                            "disk": block_io
                        }
            
            return usage_data
        except subprocess.CalledProcessError:
            return {}
    
    def check_disk_space(self) -> Dict[str, str]:
        """Check disk space usage"""
        try:
            result = subprocess.run(
                ["df", "-h", str(self.project_root)],
                capture_output=True,
                text=True,
                check=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    return {
                        "size": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "use_percent": parts[4]
                    }
            return {}
        except subprocess.CalledProcessError:
            return {}
    
    def get_system_info(self) -> Dict[str, str]:
        """Get basic system information"""
        info = {}
        
        # Get system uptime
        try:
            result = subprocess.run(["uptime"], capture_output=True, text=True, check=True)
            info["uptime"] = result.stdout.strip()
        except subprocess.CalledProcessError:
            info["uptime"] = "Unknown"
        
        # Get load average
        try:
            with open("/proc/loadavg", "r") as f:
                info["load_average"] = f.read().strip()
        except FileNotFoundError:
            info["load_average"] = "Unknown"
        
        # Get memory info
        try:
            result = subprocess.run(["free", "-h"], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    info["memory_total"] = parts[1]
                    info["memory_used"] = parts[2]
                    info["memory_free"] = parts[3]
        except subprocess.CalledProcessError:
            pass
        
        return info

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RAG Platform Service Management")
    parser.add_argument(
        "command",
        choices=["status", "start", "stop", "restart", "logs", "scale", "exec", "run", "monitor"],
        help="Command to execute"
    )
    parser.add_argument(
        "--service",
        help="Service name for service-specific commands"
    )
    parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Follow logs in real-time"
    )
    parser.add_argument(
        "--lines",
        "-n",
        type=int,
        default=100,
        help="Number of log lines to show"
    )
    parser.add_argument(
        "--replicas",
        type=int,
        help="Number of replicas for scaling"
    )
    parser.add_argument(
        "--command",
        nargs="+",
        help="Command to execute in container"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Monitoring interval in seconds"
    )
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    import os
    os.chdir(project_root)
    
    service_manager = ServiceManager(str(project_root))
    monitor = SystemMonitor(str(project_root))
    
    if args.command == "status":
        status = service_manager.get_service_status()
        print("RAG Platform Service Status:")
        print("-" * 40)
        for service, state in status.items():
            print(f"{service:15}: {state}")
    
    elif args.command == "start":
        if args.service:
            service_manager.start_service(args.service)
        else:
            print("Please specify a service to start")
    
    elif args.command == "stop":
        if args.service:
            service_manager.stop_service(args.service)
        else:
            print("Please specify a service to stop")
    
    elif args.command == "restart":
        if args.service:
            service_manager.restart_service(args.service)
        else:
            print("Please specify a service to restart")
    
    elif args.command == "logs":
        service_manager.view_logs(
            service=args.service,
            follow=args.follow,
            lines=args.lines
        )
    
    elif args.command == "scale":
        if args.service and args.replicas:
            service_manager.scale_service(args.service, args.replicas)
        else:
            print("Please specify service and number of replicas")
    
    elif args.command == "exec":
        if args.service and args.command:
            service_manager.exec_command(args.service, args.command)
        else:
            print("Please specify service and command to execute")
    
    elif args.command == "run":
        if args.service and args.command:
            service_manager.run_command(args.service, args.command)
        else:
            print("Please specify service and command to run")
    
    elif args.command == "monitor":
        print("RAG Platform System Monitor")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        try:
            while True:
                # Clear screen (works on most terminals)
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("RAG Platform System Monitor")
                print("=" * 50)
                
                # Service status
                status = service_manager.get_service_status()
                print("\nService Status:")
                for service, state in status.items():
                    print(f"  {service:15}: {state}")
                
                # Resource usage
                usage = monitor.get_resource_usage()
                if usage:
                    print("\nResource Usage:")
                    print(f"  {'Service':15} {'CPU':10} {'Memory':20} {'Network':15}")
                    print("-" * 65)
                    for service, data in usage.items():
                        print(f"  {service:15} {data['cpu']:10} {data['memory']:20} {data['network']:15}")
                
                # System info
                sys_info = monitor.get_system_info()
                print("\nSystem Information:")
                for key, value in sys_info.items():
                    print(f"  {key:15}: {value}")
                
                # Disk space
                disk_info = monitor.check_disk_space()
                if disk_info:
                    print(f"  {'Disk Usage':15}: {disk_info.get('use_percent', 'Unknown')}")
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()