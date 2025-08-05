#!/usr/bin/env python3
"""
Comprehensive System Management Script for Noctis DICOM Viewer
This script provides complete system management including deployment, testing, monitoring, and maintenance.
"""

import os
import sys
import subprocess
import time
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
import psutil
import requests
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')

import django
django.setup()

from django.core.management import execute_from_command_line
from django.conf import settings
from noctisview.monitoring import get_system_status, system_monitor, health_check
from noctisview.logging_config import error_tracker, performance_monitor
from noctisview.security import security_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system_management.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ComprehensiveSystemManager:
    """Comprehensive system management class"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.logs_dir = self.project_root / 'logs'
        self.logs_dir.mkdir(exist_ok=True)
        
        # System status
        self.system_healthy = True
        self.last_maintenance = None
        self.maintenance_interval = 24 * 60 * 60  # 24 hours
    
    def run_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return result"""
        try:
            logger.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=check)
            if result.stdout:
                logger.info(f"Command output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            raise
    
    def check_system_requirements(self) -> bool:
        """Check if system meets requirements"""
        logger.info("Checking system requirements...")
        
        requirements = {
            'python_version': '3.8+',
            'django_version': '4.2+',
            'disk_space_gb': 10,
            'memory_gb': 4,
        }
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            logger.error(f"Python version {python_version.major}.{python_version.minor} is too old. Required: 3.8+")
            return False
        
        # Check Django version
        try:
            import django
            django_version = django.get_version()
            logger.info(f"Django version: {django_version}")
        except ImportError:
            logger.error("Django not installed")
            return False
        
        # Check disk space
        disk = psutil.disk_usage('/')
        disk_gb = disk.free / (1024**3)
        if disk_gb < requirements['disk_space_gb']:
            logger.error(f"Insufficient disk space: {disk_gb:.1f}GB available, {requirements['disk_space_gb']}GB required")
            return False
        
        # Check memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        if memory_gb < requirements['memory_gb']:
            logger.error(f"Insufficient memory: {memory_gb:.1f}GB available, {requirements['memory_gb']}GB required")
            return False
        
        logger.info("System requirements check passed")
        return True
    
    def install_dependencies(self) -> bool:
        """Install system dependencies"""
        logger.info("Installing system dependencies...")
        
        try:
            # Install Python packages
            self.run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            
            # Install system packages
            system_packages = [
                'python3-venv',
                'python3-pip',
                'build-essential',
                'libpq-dev',
                'redis-server',
            ]
            
            for package in system_packages:
                try:
                    self.run_command(['sudo', 'apt-get', 'install', '-y', package])
                except subprocess.CalledProcessError:
                    logger.warning(f"Failed to install {package}, continuing...")
            
            logger.info("Dependencies installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def setup_database(self) -> bool:
        """Setup and migrate database"""
        logger.info("Setting up database...")
        
        try:
            # Run migrations
            execute_from_command_line(['manage.py', 'makemigrations'])
            execute_from_command_line(['manage.py', 'migrate'])
            
            # Create superuser if not exists
            from django.contrib.auth.models import User
            if not User.objects.filter(username='admin').exists():
                execute_from_command_line(['manage.py', 'shell', '-c', 
                    'from django.contrib.auth.models import User; '
                    'User.objects.create_superuser("admin", "admin@example.com", "admin123")'])
            
            logger.info("Database setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            return False
    
    def setup_static_files(self) -> bool:
        """Setup static files"""
        logger.info("Setting up static files...")
        
        try:
            execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
            logger.info("Static files setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Static files setup failed: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run comprehensive tests"""
        logger.info("Running comprehensive tests...")
        
        try:
            # Run Django tests
            result = execute_from_command_line(['manage.py', 'test', 'tests.test_comprehensive_system'])
            
            # Run custom test suite
            from tests.test_comprehensive_system import run_comprehensive_tests
            test_success = run_comprehensive_tests()
            
            if test_success:
                logger.info("All tests passed")
                return True
            else:
                logger.error("Some tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return False
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check system health"""
        logger.info("Checking system health...")
        
        try:
            health_status = get_system_status()
            
            # Log health status
            overall_status = health_status['health_check']['overall_status']
            logger.info(f"System health status: {overall_status}")
            
            # Check for critical issues
            if overall_status == 'critical':
                logger.error("CRITICAL: System health check failed")
                self.system_healthy = False
            elif overall_status == 'warning':
                logger.warning("WARNING: System health check shows warnings")
            else:
                logger.info("System health check passed")
                self.system_healthy = True
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'error': str(e)}
    
    def perform_maintenance(self) -> bool:
        """Perform system maintenance"""
        logger.info("Performing system maintenance...")
        
        try:
            # Clean up old logs
            self._cleanup_old_logs()
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            # Optimize database
            self._optimize_database()
            
            # Update last maintenance time
            self.last_maintenance = datetime.now()
            
            logger.info("System maintenance completed")
            return True
            
        except Exception as e:
            logger.error(f"Maintenance failed: {e}")
            return False
    
    def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            log_files = list(self.logs_dir.glob('*.log'))
            cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7 days
            
            for log_file in log_files:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logger.info(f"Removed old log file: {log_file}")
                    
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
    
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_dirs = ['media/temp', 'media/bulk_uploads']
            
            for temp_dir in temp_dirs:
                temp_path = self.project_root / temp_dir
                if temp_path.exists():
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            # Remove files older than 1 hour
                            if datetime.now().timestamp() - file_path.stat().st_mtime > 3600:
                                file_path.unlink()
                                logger.info(f"Removed temp file: {file_path}")
                                
        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}")
    
    def _optimize_database(self):
        """Optimize database"""
        try:
            # Run Django's database optimization
            execute_from_command_line(['manage.py', 'dbshell', '-c', 'VACUUM ANALYZE;'])
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    def start_server(self, host: str = '0.0.0.0', port: int = 8000) -> bool:
        """Start the Django development server"""
        logger.info(f"Starting server on {host}:{port}...")
        
        try:
            # Check if server is already running
            if self._is_server_running(port):
                logger.warning(f"Server already running on port {port}")
                return True
            
            # Start server in background
            server_process = subprocess.Popen([
                sys.executable, 'manage.py', 'runserver', f'{host}:{port}'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if server started successfully
            if self._is_server_running(port):
                logger.info(f"Server started successfully on {host}:{port}")
                return True
            else:
                logger.error("Server failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    def _is_server_running(self, port: int) -> bool:
        """Check if server is running on port"""
        try:
            response = requests.get(f'http://localhost:{port}/', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def stop_server(self) -> bool:
        """Stop the Django development server"""
        logger.info("Stopping server...")
        
        try:
            # Find and kill Django processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'manage.py' in ' '.join(proc.info['cmdline'] or []):
                        proc.terminate()
                        logger.info(f"Terminated Django process: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            logger.info("Server stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report"""
        logger.info("Generating system report...")
        
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'system_info': {
                    'python_version': sys.version,
                    'django_version': django.get_version(),
                    'project_root': str(self.project_root),
                    'settings_module': settings.SETTINGS_MODULE,
                },
                'health_status': self.check_system_health(),
                'error_summary': error_tracker.get_error_summary(),
                'performance_summary': {
                    'cpu_usage': performance_monitor.get_metric_summary('cpu_usage'),
                    'memory_usage': performance_monitor.get_metric_summary('memory_usage'),
                    'disk_usage': performance_monitor.get_metric_summary('disk_usage'),
                },
                'security_status': {
                    'blocked_ips': len(security_manager.blocked_ips),
                    'suspicious_activities': len(security_manager.suspicious_activities),
                },
                'maintenance': {
                    'last_maintenance': self.last_maintenance.isoformat() if self.last_maintenance else None,
                    'maintenance_needed': self._is_maintenance_needed(),
                }
            }
            
            # Save report to file
            report_file = self.logs_dir / f'system_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"System report generated: {report_file}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {'error': str(e)}
    
    def _is_maintenance_needed(self) -> bool:
        """Check if maintenance is needed"""
        if not self.last_maintenance:
            return True
        
        time_since_maintenance = (datetime.now() - self.last_maintenance).total_seconds()
        return time_since_maintenance > self.maintenance_interval
    
    def deploy_system(self) -> bool:
        """Complete system deployment"""
        logger.info("Starting comprehensive system deployment...")
        
        try:
            # Check requirements
            if not self.check_system_requirements():
                logger.error("System requirements check failed")
                return False
            
            # Install dependencies
            if not self.install_dependencies():
                logger.error("Dependency installation failed")
                return False
            
            # Setup database
            if not self.setup_database():
                logger.error("Database setup failed")
                return False
            
            # Setup static files
            if not self.setup_static_files():
                logger.error("Static files setup failed")
                return False
            
            # Run tests
            if not self.run_tests():
                logger.error("Test execution failed")
                return False
            
            # Perform initial maintenance
            if not self.perform_maintenance():
                logger.error("Initial maintenance failed")
                return False
            
            logger.info("System deployment completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"System deployment failed: {e}")
            return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Comprehensive System Management')
    parser.add_argument('command', choices=[
        'deploy', 'test', 'health', 'maintenance', 'start', 'stop', 'report', 'monitor'
    ], help='Command to execute')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')
    parser.add_argument('--continuous', action='store_true', help='Run monitoring continuously')
    
    args = parser.parse_args()
    
    manager = ComprehensiveSystemManager()
    
    try:
        if args.command == 'deploy':
            success = manager.deploy_system()
            sys.exit(0 if success else 1)
            
        elif args.command == 'test':
            success = manager.run_tests()
            sys.exit(0 if success else 1)
            
        elif args.command == 'health':
            health_status = manager.check_system_health()
            print(json.dumps(health_status, indent=2))
            
        elif args.command == 'maintenance':
            success = manager.perform_maintenance()
            sys.exit(0 if success else 1)
            
        elif args.command == 'start':
            success = manager.start_server(args.host, args.port)
            sys.exit(0 if success else 1)
            
        elif args.command == 'stop':
            success = manager.stop_server()
            sys.exit(0 if success else 1)
            
        elif args.command == 'report':
            report = manager.generate_report()
            print(json.dumps(report, indent=2))
            
        elif args.command == 'monitor':
            if args.continuous:
                print("Starting continuous monitoring...")
                while True:
                    health_status = manager.check_system_health()
                    print(f"[{datetime.now()}] Health: {health_status['health_check']['overall_status']}")
                    time.sleep(30)
            else:
                health_status = manager.check_system_health()
                print(json.dumps(health_status, indent=2))
                
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()