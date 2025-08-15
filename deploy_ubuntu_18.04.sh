#!/bin/bash

# NOCTIS DICOM Viewer Deployment Script for Ubuntu 18.04
# This script automates the deployment process on Ubuntu 18.04 VM

set -e  # Exit on error

echo "==================================================="
echo "NOCTIS DICOM Viewer Deployment Script"
echo "Target: Ubuntu 18.04 Virtual Machine"
echo "==================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running on Ubuntu 18.04
if [[ ! -f /etc/os-release ]]; then
    print_error "Cannot determine OS version"
    exit 1
fi

source /etc/os-release
if [[ "$VERSION_ID" != "18.04" ]]; then
    print_warning "This script is designed for Ubuntu 18.04. Current version: $VERSION_ID"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system packages
print_status "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Step 2: Install Python 3.8 (Ubuntu 18.04 comes with Python 3.6)
print_status "Installing Python 3.8..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev

# Step 3: Install system dependencies
print_status "Installing system dependencies..."
sudo apt install -y \
    build-essential \
    nginx \
    postgresql \
    postgresql-contrib \
    redis-server \
    git \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk \
    libgirepository1.0-dev \
    gcc \
    g++ \
    make \
    wget \
    curl

# Step 4: Create application user and directories
print_status "Creating application user and directories..."
if ! id -u noctis > /dev/null 2>&1; then
    sudo useradd -m -s /bin/bash noctis
fi

# Create application directories
sudo mkdir -p /opt/noctis
sudo mkdir -p /opt/noctis/logs
sudo mkdir -p /opt/noctis/media/dicom_files
sudo mkdir -p /opt/noctis/staticfiles

# Step 5: Clone/Copy application code
print_status "Setting up application code..."
if [ -d "/workspace" ] && [ -f "/workspace/manage.py" ]; then
    # If running from the workspace, copy files
    print_status "Copying files from workspace..."
    sudo cp -r /workspace/* /opt/noctis/
else
    # Otherwise, prompt for source
    print_error "Application files not found in /workspace"
    echo "Please ensure the application files are in /opt/noctis/"
    exit 1
fi

# Set ownership
sudo chown -R noctis:noctis /opt/noctis

# Step 6: Setup Python virtual environment
print_status "Setting up Python virtual environment..."
cd /opt/noctis
sudo -u noctis python3.8 -m venv venv

# Step 7: Install Python dependencies
print_status "Installing Python dependencies..."
sudo -u noctis venv/bin/pip install --upgrade pip setuptools wheel
sudo -u noctis venv/bin/pip install -r requirements.txt
sudo -u noctis venv/bin/pip install gunicorn psycopg2-binary whitenoise

# Step 8: Setup PostgreSQL database
print_status "Setting up PostgreSQL database..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Generate secure passwords
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 48)

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE noctis_db;
CREATE USER noctis_user WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;
ALTER DATABASE noctis_db OWNER TO noctis_user;
EOF

# Step 9: Create environment configuration
print_status "Creating environment configuration..."
cat > /opt/noctis/.env << EOF
# Django settings
DEBUG=False
SECRET_KEY=$SECRET_KEY

# Database settings
DB_NAME=noctis_db
DB_USER=noctis_user
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

# Redis settings
REDIS_URL=redis://localhost:6379/1

# Allowed hosts (update with your VM's IP or domain)
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | awk '{print $1}')

# DICOM settings
DICOM_STORAGE_PATH=/opt/noctis/media/dicom_files
SCP_AE_TITLE=NOCTIS_SCP
SCP_PORT=11112

# Email settings (optional - configure if needed)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF

sudo chown noctis:noctis /opt/noctis/.env
sudo chmod 600 /opt/noctis/.env

# Step 10: Update Django settings for production
print_status "Updating Django settings..."
cat > /opt/noctis/noctisview/production_settings.py << 'EOF'
from .settings import *
import os
from pathlib import Path

# Load environment variables
from decouple import config

# Security settings
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

# Static files
STATIC_ROOT = '/opt/noctis/staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_ROOT = '/opt/noctis/media'

# Security
SECURE_SSL_REDIRECT = False  # Set to True when SSL is configured
SESSION_COOKIE_SECURE = False  # Set to True when SSL is configured
CSRF_COOKIE_SECURE = False  # Set to True when SSL is configured
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/opt/noctis/logs/django.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
EOF

# Step 11: Run Django migrations
print_status "Running Django migrations..."
cd /opt/noctis
sudo -u noctis venv/bin/python manage.py makemigrations --settings=noctisview.production_settings
sudo -u noctis venv/bin/python manage.py migrate --settings=noctisview.production_settings

# Step 12: Create superuser
print_status "Creating Django superuser..."
echo "Please create a superuser account for Django admin:"
sudo -u noctis venv/bin/python manage.py createsuperuser --settings=noctisview.production_settings

# Step 13: Collect static files
print_status "Collecting static files..."
sudo -u noctis venv/bin/python manage.py collectstatic --noinput --settings=noctisview.production_settings

# Step 14: Create Gunicorn configuration
print_status "Creating Gunicorn configuration..."
cat > /opt/noctis/gunicorn_config.py << EOF
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 300
keepalive = 2
preload_app = True
accesslog = "/opt/noctis/logs/gunicorn_access.log"
errorlog = "/opt/noctis/logs/gunicorn_error.log"
EOF

# Step 15: Create systemd service for Django
print_status "Creating systemd service for Django..."
sudo tee /etc/systemd/system/noctis.service > /dev/null << EOF
[Unit]
Description=NOCTIS DICOM Viewer Django Application
After=network.target postgresql.service

[Service]
Type=notify
User=noctis
Group=noctis
WorkingDirectory=/opt/noctis
Environment="PATH=/opt/noctis/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.production_settings"
ExecStart=/opt/noctis/venv/bin/gunicorn \
    --config /opt/noctis/gunicorn_config.py \
    noctisview.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Step 16: Create systemd service for DICOM SCP server
print_status "Creating systemd service for DICOM SCP server..."
sudo tee /etc/systemd/system/noctis-scp.service > /dev/null << EOF
[Unit]
Description=NOCTIS DICOM SCP Server
After=network.target

[Service]
Type=simple
User=noctis
Group=noctis
WorkingDirectory=/opt/noctis
Environment="PATH=/opt/noctis/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.production_settings"
ExecStart=/opt/noctis/venv/bin/python enhanced_scp_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Step 17: Configure Nginx
print_status "Configuring Nginx..."
VM_IP=$(hostname -I | awk '{print $1}')

sudo tee /etc/nginx/sites-available/noctis > /dev/null << EOF
server {
    listen 80;
    server_name $VM_IP localhost;
    
    client_max_body_size 1G;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    location /static/ {
        alias /opt/noctis/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    location /media/ {
        alias /opt/noctis/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/noctis /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Step 18: Configure firewall (ufw)
print_status "Configuring firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 11112/tcp # DICOM SCP
sudo ufw --force enable

# Step 19: Start and enable services
print_status "Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable postgresql redis-server nginx noctis noctis-scp
sudo systemctl start redis-server
sudo systemctl restart postgresql
sudo systemctl restart noctis
sudo systemctl restart noctis-scp
sudo systemctl restart nginx

# Step 20: Create helpful scripts
print_status "Creating management scripts..."

# Create update script
cat > /opt/noctis/update_app.sh << 'EOF'
#!/bin/bash
cd /opt/noctis
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --settings=noctisview.production_settings
python manage.py collectstatic --noinput --settings=noctisview.production_settings
sudo systemctl restart noctis
sudo systemctl restart noctis-scp
EOF
chmod +x /opt/noctis/update_app.sh

# Create backup script
cat > /opt/noctis/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/noctis/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -U noctis_user -h localhost noctis_db > "$BACKUP_DIR/database.sql"

# Backup media files
tar -czf "$BACKUP_DIR/media.tar.gz" /opt/noctis/media/

# Backup environment file
cp /opt/noctis/.env "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
EOF
chmod +x /opt/noctis/backup.sh

# Set ownership
sudo chown -R noctis:noctis /opt/noctis

# Step 21: Display deployment summary
print_status "Deployment completed successfully!"
echo
echo "==================================================="
echo "DEPLOYMENT SUMMARY"
echo "==================================================="
echo "Application URL: http://$VM_IP"
echo "Django Admin: http://$VM_IP/admin"
echo "DICOM SCP Port: 11112"
echo
echo "Database Credentials:"
echo "  Database: noctis_db"
echo "  Username: noctis_user"
echo "  Password: $DB_PASSWORD"
echo
echo "Application Path: /opt/noctis"
echo "Logs: /opt/noctis/logs/"
echo
echo "Service Management:"
echo "  sudo systemctl status noctis      # Django app status"
echo "  sudo systemctl status noctis-scp  # DICOM SCP status"
echo "  sudo systemctl restart noctis     # Restart Django app"
echo "  sudo systemctl restart noctis-scp # Restart DICOM SCP"
echo
echo "Logs:"
echo "  tail -f /opt/noctis/logs/django.log"
echo "  tail -f /opt/noctis/logs/gunicorn_access.log"
echo "  tail -f /opt/noctis/logs/gunicorn_error.log"
echo
echo "==================================================="
echo
echo "Next steps:"
echo "1. Access the application at http://$VM_IP"
echo "2. Login to Django admin with your superuser credentials"
echo "3. Configure DICOM nodes to send to port 11112"
echo "4. Test file upload functionality"
echo
print_warning "Remember to save the database password shown above!"