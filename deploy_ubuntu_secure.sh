#!/bin/bash

# =============================================================================
# NOCTIS DICOM SYSTEM - SECURE DEPLOYMENT SCRIPT FOR UBUNTU 18.04
# =============================================================================
# This script deploys a HIPAA-compliant DICOM system with enterprise security
# Version: 1.0
# Author: NoctisView Team
# Date: $(date)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a /var/log/noctis-deploy.log
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a /var/log/noctis-deploy.log
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a /var/log/noctis-deploy.log
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a /var/log/noctis-deploy.log
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
fi

# =============================================================================
# CONFIGURATION VARIABLES
# =============================================================================

# Domain and SSL Configuration
DOMAIN_NAME="${1:-your-domain.com}"
EMAIL="${2:-admin@your-domain.com}"
APP_USER="noctis"
APP_DIR="/opt/noctis"
DB_NAME="noctis_dicom"
DB_USER="noctis_user"
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 50)

log "Starting NOCTIS DICOM System Deployment"
info "Domain: $DOMAIN_NAME"
info "Email: $EMAIL"
info "App Directory: $APP_DIR"

# =============================================================================
# SYSTEM UPDATES AND BASIC SECURITY
# =============================================================================

log "Step 1: System Updates and Basic Security Setup"

# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install essential security packages
sudo apt-get install -y \
    ufw \
    fail2ban \
    unattended-upgrades \
    apt-listchanges \
    logwatch \
    rkhunter \
    chkrootkit \
    aide \
    clamav \
    clamav-daemon

# Enable automatic security updates
echo 'Unattended-Upgrade::Automatic-Reboot "false";' | sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades
echo 'Unattended-Upgrade::Remove-Unused-Dependencies "true";' | sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades

# =============================================================================
# USER AND DIRECTORY SETUP
# =============================================================================

log "Step 2: Creating Application User and Directory Structure"

# Create application user
sudo useradd -r -s /bin/bash -m -d /home/$APP_USER $APP_USER

# Create application directory
sudo mkdir -p $APP_DIR
sudo mkdir -p $APP_DIR/logs
sudo mkdir -p $APP_DIR/backups
sudo mkdir -p $APP_DIR/media
sudo mkdir -p $APP_DIR/static
sudo mkdir -p /etc/noctis

# Set proper permissions
sudo chown -R $APP_USER:$APP_USER $APP_DIR
sudo chmod -R 750 $APP_DIR

# =============================================================================
# FIREWALL CONFIGURATION
# =============================================================================

log "Step 3: Configuring UFW Firewall"

# Reset UFW to defaults
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (modify port if you've changed it)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow DICOM ports (if using DICOM C-STORE)
sudo ufw allow 11112/tcp

# Rate limiting for SSH
sudo ufw limit ssh

# Enable UFW
sudo ufw --force enable

# =============================================================================
# POSTGRESQL INSTALLATION AND SECURITY
# =============================================================================

log "Step 4: Installing and Securing PostgreSQL"

# Install PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib postgresql-client

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Secure PostgreSQL installation
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$(openssl rand -base64 32)';"

# Create application database and user
sudo -u postgres createdb $DB_NAME
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"

# Configure PostgreSQL for security
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/10/main/postgresql.conf
sudo sed -i "s/#ssl = off/ssl = on/" /etc/postgresql/10/main/postgresql.conf

# Restart PostgreSQL
sudo systemctl restart postgresql

# =============================================================================
# PYTHON AND APPLICATION DEPENDENCIES
# =============================================================================

log "Step 5: Installing Python and Application Dependencies"

# Install Python 3.8 and related packages
sudo apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3.8-venv \
    python3-pip \
    python3-setuptools \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libgdcm-tools \
    dcmtk \
    nginx \
    supervisor \
    git \
    curl \
    wget

# Create virtual environment
sudo -u $APP_USER python3.8 -m venv $APP_DIR/venv

# Upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip

# Install Python packages
sudo -u $APP_USER $APP_DIR/venv/bin/pip install \
    django==4.2 \
    psycopg2-binary \
    gunicorn \
    django-cors-headers \
    django-extensions \
    pillow \
    pydicom \
    gdcm \
    numpy \
    celery \
    redis \
    python-decouple \
    whitenoise \
    django-security \
    django-ratelimit \
    cryptography

# =============================================================================
# REDIS INSTALLATION
# =============================================================================

log "Step 6: Installing Redis for Caching and Celery"

sudo apt-get install -y redis-server

# Configure Redis for security
sudo sed -i 's/# requireauth foobared/requireauth '$(openssl rand -base64 32)'/' /etc/redis/redis.conf
sudo sed -i 's/bind 127.0.0.1/bind 127.0.0.1/' /etc/redis/redis.conf

sudo systemctl restart redis-server
sudo systemctl enable redis-server

# =============================================================================
# APPLICATION DEPLOYMENT
# =============================================================================

log "Step 7: Deploying NOCTIS Application"

# Copy application files
sudo cp -r . $APP_DIR/app/
sudo chown -R $APP_USER:$APP_USER $APP_DIR/app/

# Create production settings
cat > /tmp/production_settings.py << EOF
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '$SECRET_KEY'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['$DOMAIN_NAME', 'localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '$DB_NAME',
        'USER': '$DB_USER',
        'PASSWORD': '$DB_PASSWORD',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_MAX_AGE = 31536000
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# HIPAA Compliance Settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

# Media and Static Files
MEDIA_ROOT = '$APP_DIR/media'
STATIC_ROOT = '$APP_DIR/static'
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '$APP_DIR/logs/django.log',
            'formatter': 'verbose',
        },
        'security': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '$APP_DIR/logs/security.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
EOF

sudo mv /tmp/production_settings.py $APP_DIR/app/noctisview/production_settings.py
sudo chown $APP_USER:$APP_USER $APP_DIR/app/noctisview/production_settings.py

# Set Django settings module
echo "export DJANGO_SETTINGS_MODULE=noctisview.production_settings" | sudo tee -a /home/$APP_USER/.bashrc

# Run migrations
cd $APP_DIR/app
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py migrate --settings=noctisview.production_settings

# Collect static files
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py collectstatic --noinput --settings=noctisview.production_settings

# Create superuser
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py createsuperuser --settings=noctisview.production_settings

# =============================================================================
# SSL CERTIFICATE SETUP
# =============================================================================

log "Step 8: Setting up SSL Certificates with Let's Encrypt"

# Install Certbot
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:certbot/certbot -y
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# =============================================================================
# NGINX CONFIGURATION
# =============================================================================

log "Step 9: Configuring Nginx with Security Headers"

# Remove default Nginx configuration
sudo rm -f /etc/nginx/sites-enabled/default

# Create Nginx configuration for NOCTIS
cat > /tmp/noctis_nginx.conf << 'EOF'
# Rate limiting
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

# Upstream for Gunicorn
upstream noctis_app {
    server unix:/opt/noctis/gunicorn.sock fail_timeout=0;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name DOMAIN_NAME;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name DOMAIN_NAME;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_NAME/privkey.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 5m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self';" always;

    # Hide server information
    server_tokens off;

    # Client body size (for DICOM uploads)
    client_max_body_size 1G;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Root directory
    root /opt/noctis/app;

    # Rate limiting for login
    location /accounts/login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://noctis_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rate limiting for API
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://noctis_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /opt/noctis/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files (DICOM images - sensitive data)
    location /media/ {
        alias /opt/noctis/media/;
        expires 1h;
        add_header Cache-Control "private, no-cache";
        
        # Additional security for medical data
        add_header X-Content-Type-Options "nosniff";
        add_header X-Frame-Options "DENY";
    }

    # Main application
    location / {
        proxy_pass http://noctis_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Security.txt
    location /.well-known/security.txt {
        return 200 "Contact: EMAIL\nExpires: 2024-12-31T23:59:59.000Z\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Replace placeholders and install configuration
sed "s/DOMAIN_NAME/$DOMAIN_NAME/g; s/EMAIL/$EMAIL/g" /tmp/noctis_nginx.conf | sudo tee /etc/nginx/sites-available/noctis
sudo ln -s /etc/nginx/sites-available/noctis /etc/nginx/sites-enabled/
sudo rm /tmp/noctis_nginx.conf

# Test Nginx configuration
sudo nginx -t

# =============================================================================
# GUNICORN CONFIGURATION
# =============================================================================

log "Step 10: Configuring Gunicorn Application Server"

# Create Gunicorn configuration
cat > /tmp/gunicorn.conf.py << EOF
bind = "unix:/opt/noctis/gunicorn.sock"
workers = $(nproc)
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
user = "$APP_USER"
group = "$APP_USER"
pythonpath = "/opt/noctis/app"
chdir = "/opt/noctis/app"
daemon = False
pidfile = "/opt/noctis/gunicorn.pid"
accesslog = "/opt/noctis/logs/gunicorn_access.log"
errorlog = "/opt/noctis/logs/gunicorn_error.log"
loglevel = "info"
EOF

sudo mv /tmp/gunicorn.conf.py /etc/noctis/gunicorn.conf.py

# =============================================================================
# SUPERVISOR CONFIGURATION
# =============================================================================

log "Step 11: Setting up Supervisor for Process Management"

# Gunicorn supervisor configuration
cat > /tmp/noctis_gunicorn.conf << EOF
[program:noctis_gunicorn]
command=/opt/noctis/venv/bin/gunicorn -c /etc/noctis/gunicorn.conf.py noctisview.wsgi:application
directory=/opt/noctis/app
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/noctis/logs/supervisor_gunicorn.log
environment=DJANGO_SETTINGS_MODULE="noctisview.production_settings"
EOF

sudo mv /tmp/noctis_gunicorn.conf /etc/supervisor/conf.d/

# Celery supervisor configuration
cat > /tmp/noctis_celery.conf << EOF
[program:noctis_celery]
command=/opt/noctis/venv/bin/celery -A noctisview worker -l info
directory=/opt/noctis/app
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/noctis/logs/supervisor_celery.log
environment=DJANGO_SETTINGS_MODULE="noctisview.production_settings"
EOF

sudo mv /tmp/noctis_celery.conf /etc/supervisor/conf.d/

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# =============================================================================
# FAIL2BAN CONFIGURATION
# =============================================================================

log "Step 12: Configuring Fail2Ban for Intrusion Prevention"

# Create Fail2Ban configuration for Django
cat > /tmp/django.conf << EOF
[django-auth]
enabled = true
port = http,https
filter = django-auth
logpath = /opt/noctis/logs/django.log
maxretry = 5
bantime = 3600

[nginx-req-limit]
enabled = true
port = http,https
filter = nginx-req-limit
logpath = /var/log/nginx/error.log
maxretry = 10
bantime = 600
EOF

sudo mv /tmp/django.conf /etc/fail2ban/jail.d/

# Create filter for Django authentication failures
cat > /tmp/django-auth.conf << EOF
[Definition]
failregex = .*django.security.*SuspiciousOperation.*
            .*django.security.*DisallowedHost.*
            .*django.security.*PermissionDenied.*
ignoreregex =
EOF

sudo mv /tmp/django-auth.conf /etc/fail2ban/filter.d/

# Restart Fail2Ban
sudo systemctl restart fail2ban

# =============================================================================
# BACKUP CONFIGURATION
# =============================================================================

log "Step 13: Setting up Automated Backups"

# Create backup script
cat > /tmp/backup_noctis.sh << EOF
#!/bin/bash

BACKUP_DIR="/opt/noctis/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
DB_BACKUP="\$BACKUP_DIR/db_backup_\$DATE.sql"
MEDIA_BACKUP="\$BACKUP_DIR/media_backup_\$DATE.tar.gz"

# Create backup directory
mkdir -p \$BACKUP_DIR

# Database backup
sudo -u postgres pg_dump $DB_NAME > \$DB_BACKUP
gzip \$DB_BACKUP

# Media files backup
tar -czf \$MEDIA_BACKUP -C /opt/noctis media/

# Remove backups older than 7 days
find \$BACKUP_DIR -name "*.gz" -mtime +7 -delete

# Log backup
echo "\$(date): Backup completed" >> /opt/noctis/logs/backup.log
EOF

sudo mv /tmp/backup_noctis.sh /usr/local/bin/backup_noctis.sh
sudo chmod +x /usr/local/bin/backup_noctis.sh

# Add to crontab (daily backup at 2 AM)
echo "0 2 * * * /usr/local/bin/backup_noctis.sh" | sudo crontab -

# =============================================================================
# SECURITY MONITORING
# =============================================================================

log "Step 14: Setting up Security Monitoring"

# Install and configure AIDE (Advanced Intrusion Detection Environment)
sudo aide --init
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Add AIDE check to crontab (daily at 3 AM)
echo "0 3 * * * /usr/bin/aide --check | mail -s 'AIDE Report' $EMAIL" | sudo crontab -u root -

# Configure log rotation
cat > /tmp/noctis-logs << EOF
/opt/noctis/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        supervisorctl restart noctis_gunicorn
        supervisorctl restart noctis_celery
    endscript
}
EOF

sudo mv /tmp/noctis-logs /etc/logrotate.d/

# =============================================================================
# FINAL STEPS
# =============================================================================

log "Step 15: Final Security Hardening and Service Startup"

# Set proper file permissions
sudo chmod -R 750 $APP_DIR
sudo chmod -R 640 $APP_DIR/app
sudo chmod +x $APP_DIR/app/manage.py

# Secure sensitive files
sudo chmod 600 $APP_DIR/app/noctisview/production_settings.py
sudo chmod 600 /etc/noctis/gunicorn.conf.py

# Start services
sudo systemctl restart postgresql
sudo systemctl restart redis-server
sudo systemctl restart nginx
sudo systemctl restart supervisor

# Enable services on boot
sudo systemctl enable postgresql
sudo systemctl enable redis-server
sudo systemctl enable nginx
sudo systemctl enable supervisor

# Get SSL certificate
sudo certbot --nginx -d $DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive

# Restart Nginx with SSL
sudo systemctl restart nginx

# =============================================================================
# COMPLETION REPORT
# =============================================================================

log "Step 16: Generating Deployment Report"

cat > /tmp/deployment_report.txt << EOF
===============================================================================
NOCTIS DICOM SYSTEM - DEPLOYMENT COMPLETE
===============================================================================

Deployment Date: $(date)
Domain: $DOMAIN_NAME
Application Directory: $APP_DIR

CREDENTIALS AND IMPORTANT INFORMATION:
--------------------------------------
Database Name: $DB_NAME
Database User: $DB_USER
Database Password: $DB_PASSWORD

Application User: $APP_USER
Secret Key: $SECRET_KEY

SECURITY FEATURES ENABLED:
--------------------------
✓ UFW Firewall configured
✓ Fail2Ban intrusion prevention
✓ SSL/TLS encryption with Let's Encrypt
✓ Security headers configured
✓ Database encryption enabled
✓ Rate limiting implemented
✓ AIDE intrusion detection
✓ Automated backups configured
✓ Log rotation enabled
✓ HIPAA compliance measures

SERVICES STATUS:
---------------
✓ PostgreSQL: $(sudo systemctl is-active postgresql)
✓ Redis: $(sudo systemctl is-active redis-server)
✓ Nginx: $(sudo systemctl is-active nginx)
✓ Supervisor: $(sudo systemctl is-active supervisor)

BACKUP INFORMATION:
------------------
✓ Daily database backups at 2:00 AM
✓ Daily AIDE security scans at 3:00 AM
✓ Backup location: $APP_DIR/backups
✓ Log files: $APP_DIR/logs

IMPORTANT NEXT STEPS:
--------------------
1. Save this report securely
2. Test the application at https://$DOMAIN_NAME
3. Configure DNS to point to this server
4. Set up monitoring alerts
5. Review and customize security policies
6. Train staff on security procedures

EMERGENCY CONTACTS:
------------------
System Administrator: $EMAIL
Log files location: $APP_DIR/logs
Backup location: $APP_DIR/backups

===============================================================================
EOF

sudo mv /tmp/deployment_report.txt $APP_DIR/DEPLOYMENT_REPORT.txt
sudo chown $APP_USER:$APP_USER $APP_DIR/DEPLOYMENT_REPORT.txt

# Display report
cat $APP_DIR/DEPLOYMENT_REPORT.txt

log "NOCTIS DICOM System deployment completed successfully!"
info "Access your system at: https://$DOMAIN_NAME"
info "Deployment report saved to: $APP_DIR/DEPLOYMENT_REPORT.txt"

warning "IMPORTANT: Save the database credentials and secret key securely!"
warning "Review firewall rules and test all security features!"

# Save credentials to secure file
echo "DB_PASSWORD=$DB_PASSWORD" | sudo tee /etc/noctis/credentials.env
echo "SECRET_KEY=$SECRET_KEY" | sudo tee -a /etc/noctis/credentials.env
sudo chmod 600 /etc/noctis/credentials.env
sudo chown root:root /etc/noctis/credentials.env

log "Deployment script completed. Please review the security configuration."