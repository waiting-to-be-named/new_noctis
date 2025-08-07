#!/bin/bash

#################################################################
# Automated Ubuntu 18.04 Deployment Script for Noctis DICOM Viewer
# Created: August 7, 2025
# Purpose: Fully automated deployment on Ubuntu 18.04 server
# Based on: UBUNTU_18_04_DEPLOYMENT_ASSESSMENT.md
#################################################################

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Configuration variables
NOCTIS_USER="noctis"
NOCTIS_GROUP="noctis"
NOCTIS_HOME="/opt/noctis"
VENV_PATH="${NOCTIS_HOME}/venv"
APP_PATH="${NOCTIS_HOME}/app"
LOG_FILE="/var/log/noctis_deployment.log"
DB_NAME="noctis_db"
DB_USER="noctis_user"
DB_PASSWORD="$(openssl rand -base64 32)"
DOMAIN_NAME="${1:-localhost}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Create necessary directories and users
setup_user_and_directories() {
    log "Setting up user and directories..."
    
    # Create noctis user if it doesn't exist
    if ! id "$NOCTIS_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$NOCTIS_HOME" -m "$NOCTIS_USER"
        log "Created user: $NOCTIS_USER"
    fi
    
    # Create necessary directories
    mkdir -p "$NOCTIS_HOME"/{app,logs,media,staticfiles}
    mkdir -p /var/log/noctis
    
    # Set ownership
    chown -R "$NOCTIS_USER:$NOCTIS_GROUP" "$NOCTIS_HOME"
    chown -R "$NOCTIS_USER:$NOCTIS_GROUP" /var/log/noctis
    
    log "User and directories setup completed"
}

# Update system packages
update_system() {
    log "Updating system packages..."
    apt update
    apt upgrade -y
    apt install -y software-properties-common curl wget gnupg2 lsb-release
    log "System update completed"
}

# Install Python 3.8+ via deadsnakes PPA
install_python() {
    log "Installing Python 3.8+ via deadsnakes PPA..."
    
    # Add deadsnakes PPA
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    
    # Install Python 3.8 and related packages
    apt install -y python3.8 python3.8-venv python3.8-dev python3.8-distutils
    apt install -y python3-pip build-essential
    
    # Verify installation
    python3.8 --version || error "Python 3.8 installation failed"
    
    log "Python 3.8 installation completed"
}

# Install PostgreSQL 12+ from official repository
install_postgresql() {
    log "Installing PostgreSQL 12+ from official repository..."
    
    # Add PostgreSQL official repository
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    echo "deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    apt update
    
    # Install PostgreSQL 12
    apt install -y postgresql-12 postgresql-client-12 postgresql-contrib-12
    
    # Start and enable PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    log "PostgreSQL 12 installation completed"
}

# Install system dependencies
install_system_dependencies() {
    log "Installing system dependencies..."
    
    apt install -y \
        libpq-dev \
        redis-server \
        nginx \
        supervisor \
        gdcm-tools \
        libgdcm-tools \
        libgdcm-dev \
        python3.8-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        tcl8.6-dev \
        tk8.6-dev \
        python3-tk \
        libharfbuzz-dev \
        libfribidi-dev \
        libxcb1-dev
    
    # Start and enable services
    systemctl start redis-server
    systemctl enable redis-server
    systemctl start nginx
    systemctl enable nginx
    systemctl start supervisor
    systemctl enable supervisor
    
    log "System dependencies installation completed"
}

# Setup virtual environment and install Python packages
setup_python_environment() {
    log "Setting up Python virtual environment..."
    
    # Create virtual environment as noctis user
    sudo -u "$NOCTIS_USER" python3.8 -m venv "$VENV_PATH"
    
    # Copy application files
    if [[ -d "/workspace" ]]; then
        cp -r /workspace/* "$APP_PATH/"
        chown -R "$NOCTIS_USER:$NOCTIS_GROUP" "$APP_PATH"
    else
        warning "Source code not found in /workspace. Please copy manually to $APP_PATH"
    fi
    
    # Install Python packages
    sudo -u "$NOCTIS_USER" bash -c "
        source '$VENV_PATH/bin/activate'
        pip install --upgrade pip
        pip install gunicorn psycopg2-binary whitenoise
        
        if [[ -f '$APP_PATH/requirements.txt' ]]; then
            pip install -r '$APP_PATH/requirements.txt'
        else
            echo 'Warning: requirements.txt not found'
        fi
    "
    
    log "Python environment setup completed"
}

# Configure PostgreSQL database
setup_database() {
    log "Configuring PostgreSQL database..."
    
    # Create database and user
    sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\q
EOF
    
    # Save database credentials
    cat > "$NOCTIS_HOME/.env" <<EOF
# Database Configuration
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

# Django Settings
SECRET_KEY=$(openssl rand -base64 50)
DEBUG=False
ALLOWED_HOSTS=$DOMAIN_NAME,localhost,127.0.0.1
EOF
    
    chown "$NOCTIS_USER:$NOCTIS_GROUP" "$NOCTIS_HOME/.env"
    chmod 600 "$NOCTIS_HOME/.env"
    
    log "Database configuration completed"
    log "Database password saved to $NOCTIS_HOME/.env"
}

# Run Django migrations and setup
setup_django() {
    log "Setting up Django application..."
    
    sudo -u "$NOCTIS_USER" bash -c "
        cd '$APP_PATH'
        source '$VENV_PATH/bin/activate'
        source '$NOCTIS_HOME/.env'
        
        # Check Django configuration
        python manage.py check
        
        # Run migrations
        python manage.py migrate
        
        # Collect static files
        python manage.py collectstatic --noinput
        
        # Create cache tables if needed
        python manage.py createcachetable || true
    "
    
    log "Django application setup completed"
}

# Configure Nginx
setup_nginx() {
    log "Configuring Nginx..."
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Create Noctis site configuration
    cat > /etc/nginx/sites-available/noctis <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
    client_max_body_size 100M;
    
    # Static files
    location /static/ {
        alias $NOCTIS_HOME/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Access-Control-Allow-Origin "*";
    }
    
    # Media files
    location /media/ {
        alias $NOCTIS_HOME/media/;
        expires 1d;
        add_header Cache-Control "public";
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Health check endpoint
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/noctis /etc/nginx/sites-enabled/
    
    # Test configuration
    nginx -t || error "Nginx configuration test failed"
    
    # Reload Nginx
    systemctl reload nginx
    
    log "Nginx configuration completed"
}

# Configure Supervisor for Gunicorn
setup_supervisor() {
    log "Configuring Supervisor for Gunicorn..."
    
    cat > /etc/supervisor/conf.d/noctis.conf <<EOF
[program:noctis-web]
command=$VENV_PATH/bin/gunicorn noctisview.wsgi:application --bind 127.0.0.1:8000 --workers 4 --worker-class gevent --worker-connections 1000 --max-requests 1000 --timeout 300
directory=$APP_PATH
user=$NOCTIS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/noctis/gunicorn.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PATH="$VENV_PATH/bin"

[program:noctis-dicom-scp]
command=$VENV_PATH/bin/python manage.py runserver_dicom_scp
directory=$APP_PATH
user=$NOCTIS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/noctis/dicom_scp.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PATH="$VENV_PATH/bin"

[group:noctis]
programs=noctis-web,noctis-dicom-scp
priority=999
EOF
    
    # Reload supervisor configuration
    supervisorctl reread
    supervisorctl update
    
    log "Supervisor configuration completed"
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Install and configure UFW
    apt install -y ufw
    
    # Default policies
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow essential services
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 11112/tcp  # DICOM SCP
    
    # Enable firewall
    ufw --force enable
    
    log "Firewall configuration completed"
}

# Create systemd service for automatic startup
create_systemd_service() {
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/noctis.service <<EOF
[Unit]
Description=Noctis DICOM Viewer
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=forking
User=root
ExecStart=/usr/bin/supervisorctl start noctis:*
ExecStop=/usr/bin/supervisorctl stop noctis:*
ExecReload=/usr/bin/supervisorctl restart noctis:*
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable noctis.service
    
    log "Systemd service created and enabled"
}

# Perform deployment tests
run_deployment_tests() {
    log "Running deployment tests..."
    
    # Test Django
    sudo -u "$NOCTIS_USER" bash -c "
        cd '$APP_PATH'
        source '$VENV_PATH/bin/activate'
        source '$NOCTIS_HOME/.env'
        
        python manage.py check
        python manage.py collectstatic --dry-run
    "
    
    # Test services
    systemctl is-active postgresql || error "PostgreSQL is not running"
    systemctl is-active redis-server || error "Redis is not running"
    systemctl is-active nginx || error "Nginx is not running"
    systemctl is-active supervisor || error "Supervisor is not running"
    
    # Test network connectivity
    curl -f http://localhost/health/ || warning "Health check endpoint not responding"
    
    log "Deployment tests completed"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start Noctis applications
    supervisorctl start noctis:*
    
    # Restart Nginx to ensure all configurations are loaded
    systemctl restart nginx
    
    log "Services started"
}

# Generate deployment report
generate_report() {
    log "Generating deployment report..."
    
    cat > "$NOCTIS_HOME/deployment_report.txt" <<EOF
=================================================================
Noctis DICOM Viewer - Ubuntu 18.04 Deployment Report
=================================================================

Deployment Date: $(date)
Server: $(hostname)
Ubuntu Version: $(lsb_release -d | cut -f2)

INSTALLATION SUMMARY:
✓ Python 3.8 installed via deadsnakes PPA
✓ PostgreSQL 12 installed and configured
✓ System dependencies installed
✓ Virtual environment created
✓ Database configured: $DB_NAME
✓ Django application migrated
✓ Nginx configured for domain: $DOMAIN_NAME
✓ Supervisor configured for process management
✓ Firewall configured with UFW
✓ Systemd service created

CREDENTIALS:
Database Name: $DB_NAME
Database User: $DB_USER
Database Password: [saved in $NOCTIS_HOME/.env]

IMPORTANT PATHS:
Application: $APP_PATH
Virtual Environment: $VENV_PATH
Logs: /var/log/noctis/
Static Files: $NOCTIS_HOME/staticfiles/
Media Files: $NOCTIS_HOME/media/

SERVICES:
Web Application: http://$DOMAIN_NAME/
DICOM SCP: Port 11112
Health Check: http://$DOMAIN_NAME/health/

NEXT STEPS:
1. Create Django superuser: sudo -u $NOCTIS_USER $VENV_PATH/bin/python $APP_PATH/manage.py createsuperuser
2. Configure SSL/TLS certificates (recommended)
3. Set up backup procedures
4. Configure monitoring and alerting
5. Test DICOM functionality

LOGS AND MONITORING:
- Application logs: /var/log/noctis/
- Nginx logs: /var/log/nginx/
- PostgreSQL logs: /var/log/postgresql/
- System logs: journalctl -u noctis

=================================================================
EOF
    
    chown "$NOCTIS_USER:$NOCTIS_GROUP" "$NOCTIS_HOME/deployment_report.txt"
    
    log "Deployment report generated: $NOCTIS_HOME/deployment_report.txt"
}

# Main deployment function
main() {
    log "Starting automated Ubuntu 18.04 deployment for Noctis DICOM Viewer..."
    log "Domain: $DOMAIN_NAME"
    
    check_root
    setup_user_and_directories
    update_system
    install_python
    install_postgresql
    install_system_dependencies
    setup_python_environment
    setup_database
    setup_django
    setup_nginx
    setup_supervisor
    setup_firewall
    create_systemd_service
    run_deployment_tests
    start_services
    generate_report
    
    log "==================================================================="
    log "DEPLOYMENT COMPLETED SUCCESSFULLY!"
    log "==================================================================="
    log "Access your application at: http://$DOMAIN_NAME/"
    log "Health check: http://$DOMAIN_NAME/health/"
    log "View deployment report: cat $NOCTIS_HOME/deployment_report.txt"
    log "Create admin user: sudo -u $NOCTIS_USER $VENV_PATH/bin/python $APP_PATH/manage.py createsuperuser"
    log "==================================================================="
}

# Handle script interruption
trap 'error "Deployment interrupted by user"' INT TERM

# Run main function
main "$@"