#!/usr/bin/env python3
"""
Ubuntu 18.04 Deployment Script for Noctis DICOM Viewer
Created: August 7, 2025
Purpose: Automated deployment setup for Ubuntu 18.04 server

This script automates the deployment process identified in today's
Ubuntu 18.04 compatibility assessment.
"""

import os
import subprocess
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/noctis_deployment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class Ubuntu1804Deployer:
    """
    Automated deployment class for Ubuntu 18.04
    Handles all compatibility issues identified in the assessment
    """
    
    def __init__(self):
        self.python_version = "3.8"
        self.postgresql_version = "12"
        self.project_dir = "/opt/noctis"
        self.user = "noctis"
        self.db_name = "noctis_db"
        self.db_user = "noctis_user"
        
    def run_command(self, command, check=True, shell=True):
        """Execute shell command with logging"""
        logger.info(f"Executing: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=shell, 
                check=check, 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            raise
    
    def check_ubuntu_version(self):
        """Verify we're running on Ubuntu 18.04"""
        logger.info("🔍 Checking Ubuntu version...")
        
        try:
            result = self.run_command("lsb_release -r")
            version = result.stdout.strip()
            
            if "18.04" not in version:
                logger.warning(f"Warning: This script is optimized for Ubuntu 18.04. Detected: {version}")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    sys.exit(1)
            else:
                logger.info("✅ Ubuntu 18.04 detected")
                
        except Exception as e:
            logger.error(f"Could not determine Ubuntu version: {e}")
            sys.exit(1)
    
    def update_system(self):
        """Update system packages"""
        logger.info("📦 Updating system packages...")
        
        self.run_command("sudo apt update")
        self.run_command("sudo apt upgrade -y")
        
        # Install essential packages
        essentials = [
            "software-properties-common",
            "curl", 
            "wget",
            "gnupg2",
            "lsb-release",
            "ca-certificates",
            "build-essential"
        ]
        
        self.run_command(f"sudo apt install -y {' '.join(essentials)}")
        logger.info("✅ System packages updated")
    
    def install_python38(self):
        """Install Python 3.8 using deadsnakes PPA"""
        logger.info("🐍 Installing Python 3.8...")
        
        # Add deadsnakes PPA
        self.run_command("sudo add-apt-repository ppa:deadsnakes/ppa -y")
        self.run_command("sudo apt update")
        
        # Install Python 3.8 and tools
        python_packages = [
            f"python{self.python_version}",
            f"python{self.python_version}-venv",
            f"python{self.python_version}-dev",
            f"python{self.python_version}-distutils",
            "python3-pip"
        ]
        
        self.run_command(f"sudo apt install -y {' '.join(python_packages)}")
        
        # Verify installation
        result = self.run_command(f"python{self.python_version} --version")
        logger.info(f"✅ Python installed: {result.stdout.strip()}")
    
    def install_postgresql12(self):
        """Install PostgreSQL 12 from official repository"""
        logger.info("🗄️ Installing PostgreSQL 12...")
        
        # Add PostgreSQL official repository
        self.run_command(
            "wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -"
        )
        
        self.run_command(
            'echo "deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main" | '
            'sudo tee /etc/apt/sources.list.d/pgdg.list'
        )
        
        self.run_command("sudo apt update")
        
        # Install PostgreSQL 12
        self.run_command(f"sudo apt install -y postgresql-{self.postgresql_version} postgresql-client-{self.postgresql_version}")
        
        # Start and enable PostgreSQL
        self.run_command("sudo systemctl start postgresql")
        self.run_command("sudo systemctl enable postgresql")
        
        # Verify installation
        result = self.run_command("sudo -u postgres psql -c 'SELECT version();'")
        logger.info("✅ PostgreSQL 12 installed and running")
    
    def install_system_dependencies(self):
        """Install system dependencies for DICOM processing"""
        logger.info("🔧 Installing system dependencies...")
        
        dependencies = [
            "nginx",
            "redis-server", 
            "supervisor",
            "libpq-dev",
            "gdcm-tools",
            "libgdcm-tools",
            "libgdcm-dev",
            "python3-gdcm",
            "git"
        ]
        
        self.run_command(f"sudo apt install -y {' '.join(dependencies)}")
        
        # Start and enable services
        services = ["redis-server", "nginx", "supervisor"]
        for service in services:
            self.run_command(f"sudo systemctl start {service}")
            self.run_command(f"sudo systemctl enable {service}")
        
        logger.info("✅ System dependencies installed")
    
    def create_project_structure(self):
        """Create project directory structure"""
        logger.info("📁 Creating project structure...")
        
        # Create project directory
        self.run_command(f"sudo mkdir -p {self.project_dir}")
        self.run_command(f"sudo mkdir -p {self.project_dir}/logs")
        self.run_command(f"sudo mkdir -p /var/log/noctis")
        
        # Create noctis user
        try:
            self.run_command(f"sudo adduser --system --group --home {self.project_dir} {self.user}")
            logger.info(f"✅ Created user: {self.user}")
        except subprocess.CalledProcessError:
            logger.info(f"User {self.user} already exists")
        
        # Set permissions
        self.run_command(f"sudo chown -R {self.user}:{self.user} {self.project_dir}")
        self.run_command(f"sudo chown -R {self.user}:{self.user} /var/log/noctis")
        
        logger.info("✅ Project structure created")
    
    def setup_python_environment(self):
        """Setup Python virtual environment"""
        logger.info("🐍 Setting up Python virtual environment...")
        
        venv_path = f"{self.project_dir}/venv"
        
        # Create virtual environment
        self.run_command(f"sudo -u {self.user} python{self.python_version} -m venv {venv_path}")
        
        # Upgrade pip
        self.run_command(f"sudo -u {self.user} {venv_path}/bin/pip install --upgrade pip")
        
        logger.info("✅ Python virtual environment created")
    
    def setup_database(self):
        """Setup PostgreSQL database"""
        logger.info("🗄️ Setting up database...")
        
        # Create database and user
        commands = [
            f"sudo -u postgres createdb {self.db_name}",
            f"sudo -u postgres createuser {self.db_user}",
            f"sudo -u postgres psql -c \"ALTER USER {self.db_user} PASSWORD 'changeme123!';\"",
            f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {self.db_name} TO {self.db_user};\""
        ]
        
        for cmd in commands:
            try:
                self.run_command(cmd)
            except subprocess.CalledProcessError:
                logger.warning(f"Command might have failed (possibly already exists): {cmd}")
        
        logger.info("✅ Database setup completed")
        logger.warning("⚠️ Remember to change the default database password!")
    
    def create_nginx_config(self):
        """Create Nginx configuration"""
        logger.info("🌐 Creating Nginx configuration...")
        
        nginx_config = f"""
server {{
    listen 80;
    server_name _;
    
    client_max_body_size 1G;
    
    location /static/ {{
        alias {self.project_dir}/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
    
    location /media/ {{
        alias {self.project_dir}/media/;
    }}
    
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }}
}}
"""
        
        # Write Nginx config
        config_path = "/etc/nginx/sites-available/noctis"
        with open("/tmp/noctis_nginx.conf", "w") as f:
            f.write(nginx_config)
        
        self.run_command(f"sudo mv /tmp/noctis_nginx.conf {config_path}")
        self.run_command(f"sudo ln -sf {config_path} /etc/nginx/sites-enabled/")
        self.run_command("sudo rm -f /etc/nginx/sites-enabled/default")
        
        # Test and reload Nginx
        self.run_command("sudo nginx -t")
        self.run_command("sudo systemctl reload nginx")
        
        logger.info("✅ Nginx configuration created")
    
    def create_supervisor_config(self):
        """Create Supervisor configuration"""
        logger.info("👥 Creating Supervisor configuration...")
        
        supervisor_config = f"""
[program:noctis]
command={self.project_dir}/venv/bin/gunicorn noctisview.wsgi:application --bind 127.0.0.1:8000 --workers 4 --timeout 300
directory={self.project_dir}
user={self.user}
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/noctis/gunicorn.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="{self.project_dir}/venv/bin"
"""
        
        # Write supervisor config
        config_path = "/etc/supervisor/conf.d/noctis.conf"
        with open("/tmp/noctis_supervisor.conf", "w") as f:
            f.write(supervisor_config)
        
        self.run_command(f"sudo mv /tmp/noctis_supervisor.conf {config_path}")
        self.run_command("sudo supervisorctl reread")
        self.run_command("sudo supervisorctl update")
        
        logger.info("✅ Supervisor configuration created")
    
    def create_deployment_info(self):
        """Create deployment information file"""
        logger.info("📋 Creating deployment information...")
        
        info = f"""
# Noctis DICOM Viewer - Ubuntu 18.04 Deployment Info
Generated: {os.popen('date').read().strip()}

## System Information
- OS: Ubuntu 18.04
- Python: {self.python_version}
- PostgreSQL: {self.postgresql_version}
- Project Directory: {self.project_dir}
- User: {self.user}

## Next Steps
1. Copy your Django application to {self.project_dir}/
2. Install Python dependencies:
   sudo -u {self.user} {self.project_dir}/venv/bin/pip install -r requirements.txt
   sudo -u {self.user} {self.project_dir}/venv/bin/pip install gunicorn psycopg2-binary

3. Configure Django settings for production
4. Run Django setup:
   sudo -u {self.user} {self.project_dir}/venv/bin/python manage.py migrate
   sudo -u {self.user} {self.project_dir}/venv/bin/python manage.py collectstatic --noinput
   sudo -u {self.user} {self.project_dir}/venv/bin/python manage.py createsuperuser

5. Start the application:
   sudo supervisorctl start noctis

## Important Files
- Nginx config: /etc/nginx/sites-available/noctis
- Supervisor config: /etc/supervisor/conf.d/noctis.conf
- Logs: /var/log/noctis/
- Database: {self.db_name} (user: {self.db_user})

## Default Credentials
- Database password: changeme123! (CHANGE THIS!)
"""
        
        info_file = f"{self.project_dir}/DEPLOYMENT_INFO.txt"
        with open("/tmp/deployment_info.txt", "w") as f:
            f.write(info)
        
        self.run_command(f"sudo mv /tmp/deployment_info.txt {info_file}")
        self.run_command(f"sudo chown {self.user}:{self.user} {info_file}")
        
        logger.info(f"✅ Deployment info saved to {info_file}")
    
    def run_deployment(self):
        """Run complete deployment process"""
        logger.info("🚀 Starting Ubuntu 18.04 deployment for Noctis DICOM Viewer...")
        
        try:
            self.check_ubuntu_version()
            self.update_system()
            self.install_python38()
            self.install_postgresql12()
            self.install_system_dependencies()
            self.create_project_structure()
            self.setup_python_environment()
            self.setup_database()
            self.create_nginx_config()
            self.create_supervisor_config()
            self.create_deployment_info()
            
            logger.info("🎉 Ubuntu 18.04 deployment setup completed successfully!")
            logger.info(f"📋 Check {self.project_dir}/DEPLOYMENT_INFO.txt for next steps")
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            sys.exit(1)

def main():
    """Main deployment function"""
    if os.geteuid() != 0:
        print("This script must be run as root (use sudo)")
        sys.exit(1)
    
    deployer = Ubuntu1804Deployer()
    deployer.run_deployment()

if __name__ == "__main__":
    main()