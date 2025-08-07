#!/bin/bash

# NOCTIS DICOM Viewer - Secure Ubuntu 18.04 Deployment Script
# Domain: noctisview.duckdns.org
# Updated for DuckDNS configuration

set -e

# Configuration
DOMAIN="noctisview.duckdns.org"
LOCAL_IP="192.168.1.98"
APP_USER="noctis"
APP_DIR="/opt/noctisview"
PROJECT_NAME="noctisview"
DB_NAME="noctisview_db"
DB_USER="noctisview_user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root. Please run as a regular user with sudo privileges."
fi

log "🚀 Starting NOCTIS DICOM Viewer deployment for ${DOMAIN}"
log "📍 Local IP: ${LOCAL_IP}"

# Update system
log "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
log "⚙️ Installing essential packages..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    nginx \
    redis-server \
    supervisor \
    ufw \
    fail2ban \
    certbot \
    python3-certbot-nginx \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    git \
    curl \
    htop \
    unzip

# Create application user
log "👤 Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    sudo adduser --disabled-password --gecos "" $APP_USER
    sudo usermod -aG www-data $APP_USER
fi

# Configure UFW Firewall
log "🔥 Configuring UFW firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 11112/tcp  # DICOM port
sudo ufw --force enable

# Configure PostgreSQL
log "🗄️ Configuring PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Generate random password
DB_PASSWORD=$(openssl rand -base64 32)

sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Configure PostgreSQL for security
log "🔒 Securing PostgreSQL..."
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/10/main/postgresql.conf
sudo sed -i "s/#ssl = off/ssl = on/" /etc/postgresql/10/main/postgresql.conf

# Configure Redis
log "📊 Configuring Redis..."
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo sed -i 's/# requirepass foobared/requirepass noctis_redis_2024/' /etc/redis/redis.conf
sudo systemctl restart redis-server

# Create application directory
log "📁 Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown $APP_USER:$APP_USER $APP_DIR

# Copy application files
log "📋 Copying application files..."
sudo cp -r /workspace/* $APP_DIR/
sudo chown -R $APP_USER:$APP_USER $APP_DIR

# Create Python virtual environment
log "🐍 Setting up Python environment..."
sudo -u $APP_USER python3 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements_production.txt

# Generate Django secret key
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Create production settings
log "⚙️ Creating production settings..."
sudo -u $APP_USER tee $APP_DIR/noctisview/production_settings.py > /dev/null << EOF
from .settings import *
import os

# Security Settings
DEBUG = False
ALLOWED_HOSTS = ['${DOMAIN}', '${LOCAL_IP}', 'localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${DB_NAME}',
        'USER': '${DB_USER}',
        'PASSWORD': '${DB_PASSWORD}',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Security
SECRET_KEY = '${SECRET_KEY}'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Custom User Model
AUTH_USER_MODEL = 'worklist.CustomUser'

# DICOM Configuration
DICOM_AE_TITLE = 'NOCTIS_PACS'
DICOM_HOST = '0.0.0.0'
DICOM_PORT = 11112
DICOM_STORAGE_DIR = os.path.join(BASE_DIR, 'media', 'dicom_received')

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': 'noctis_redis_2024',
        }
    }
}

# Email configuration (configure as needed)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Configure your SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'noctisview.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'worklist': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
EOF

# Run Django setup
log "🔧 Setting up Django application..."
cd $APP_DIR
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py makemigrations
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py migrate
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py collectstatic --noinput

# Create Django superuser
log "👑 Creating Django superuser..."
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py shell << 'EOF'
from worklist.models import CustomUser, UserRole, Facility
import os

# Create default facility
facility, created = Facility.objects.get_or_create(
    name="Default Medical Center",
    defaults={
        'address': 'Main Healthcare Facility',
        'phone': '+1-555-0123',
        'email': 'admin@noctisview.duckdns.org',
        'dicom_ae_title': 'NOCTIS_PACS'
    }
)

# Create admin user
if not CustomUser.objects.filter(username='admin').exists():
    admin = CustomUser.objects.create_superuser(
        username='admin',
        email='admin@noctisview.duckdns.org',
        password='NoctisAdmin2024!',
        role=UserRole.ADMIN,
        facility=facility
    )
    print("Admin user created: admin / NoctisAdmin2024!")
else:
    print("Admin user already exists")
EOF

# Configure Nginx
log "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null << EOF
upstream noctisview_app {
    server unix:$APP_DIR/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name ${DOMAIN} ${LOCAL_IP};
    
    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN} ${LOCAL_IP};
    
    client_max_body_size 10G;  # Large DICOM uploads
    client_body_timeout 300s;
    client_header_timeout 300s;
    keepalive_timeout 300s;
    send_timeout 300s;
    
    # SSL Configuration (will be updated by Certbot)
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone \$binary_remote_addr zone=api:10m rate=100r/m;
    
    location / {
        proxy_pass http://noctisview_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    location /accounts/login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://noctisview_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://noctisview_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias $APP_DIR/media/;
        expires 1y;
        add_header Cache-Control "private";
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

# Obtain SSL certificate
log "🔐 Obtaining SSL certificate..."
sudo mkdir -p /var/www/html
sudo systemctl reload nginx

# For DuckDNS, we'll use HTTP validation
sudo certbot certonly --webroot \
    --webroot-path=/var/www/html \
    --email admin@${DOMAIN} \
    --agree-tos \
    --no-eff-email \
    -d ${DOMAIN}

# Configure Gunicorn
log "🦄 Configuring Gunicorn..."
sudo tee $APP_DIR/gunicorn_config.py > /dev/null << EOF
bind = "unix:$APP_DIR/gunicorn.sock"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 300
keepalive = 5
user = "$APP_USER"
group = "www-data"
tmp_upload_dir = None
EOF

# Configure Supervisor
log "👨‍💼 Configuring Supervisor..."
sudo tee /etc/supervisor/conf.d/noctisview.conf > /dev/null << EOF
[program:noctisview]
command=$APP_DIR/venv/bin/gunicorn noctisview.wsgi:application -c $APP_DIR/gunicorn_config.py
directory=$APP_DIR
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/noctisview.log
environment=DJANGO_SETTINGS_MODULE="noctisview.production_settings"

[program:noctisview_dicom]
command=$APP_DIR/venv/bin/python manage.py start_dicom_service
directory=$APP_DIR
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/noctisview_dicom.log
environment=DJANGO_SETTINGS_MODULE="noctisview.production_settings"
EOF

# Configure Fail2Ban
log "🛡️ Configuring Fail2Ban..."
sudo tee /etc/fail2ban/jail.d/noctisview.conf > /dev/null << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10

[django-auth]
enabled = true
filter = django-auth
logpath = $APP_DIR/logs/noctisview.log
maxretry = 5
bantime = 1800
EOF

sudo tee /etc/fail2ban/filter.d/django-auth.conf > /dev/null << EOF
[Definition]
failregex = ^.*Invalid login attempt from <HOST>.*$
ignoreregex =
EOF

# Setup automated backups
log "💾 Setting up automated backups..."
sudo mkdir -p /opt/backups
sudo tee /opt/backups/backup_noctisview.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="noctisview_db"
APP_DIR="/opt/noctisview"

# Database backup
sudo -u postgres pg_dump $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Media files backup
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C $APP_DIR media/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

sudo chmod +x /opt/backups/backup_noctisview.sh
echo "0 2 * * * /opt/backups/backup_noctisview.sh" | sudo crontab -

# Start services
log "🚀 Starting services..."
sudo systemctl reload nginx
sudo systemctl restart supervisor
sudo systemctl enable supervisor
sudo systemctl restart fail2ban

# Generate deployment report
log "📊 Generating deployment report..."
cat > $APP_DIR/DEPLOYMENT_REPORT.md << EOF
# NOCTIS DICOM Viewer - Deployment Report

## 🌐 Domain Configuration
- **Domain**: ${DOMAIN}
- **Local IP**: ${LOCAL_IP}
- **DuckDNS Token**: ${DUCKDNS_TOKEN:-"<configure-manually>"}

## 🔐 Security Configuration
- **SSL Certificate**: ✅ Let's Encrypt
- **Firewall**: ✅ UFW configured
- **Fail2Ban**: ✅ Active protection
- **Database**: ✅ PostgreSQL with SSL

## 👤 Admin Credentials
- **Username**: admin
- **Password**: NoctisAdmin2024!
- **Email**: admin@${DOMAIN}

## 🗄️ Database
- **Database**: ${DB_NAME}
- **User**: ${DB_USER}
- **Password**: ${DB_PASSWORD}

## 🏥 DICOM Configuration
- **AE Title**: NOCTIS_PACS
- **Host**: 0.0.0.0
- **Port**: 11112

## 📱 Access URLs
- **Main Application**: https://${DOMAIN}
- **Admin Panel**: https://${DOMAIN}/admin
- **Worklist**: https://${DOMAIN}/worklist
- **DICOM Viewer**: https://${DOMAIN}/viewer

## 🔧 System Services
- **Web Server**: Nginx (Port 80/443)
- **Application**: Gunicorn + Django
- **Database**: PostgreSQL
- **Cache**: Redis
- **DICOM Service**: Port 11112
- **Process Manager**: Supervisor

## 📋 Post-Deployment Tasks
1. Configure email settings in production_settings.py
2. Set up DuckDNS auto-update (if needed)
3. Configure modality connections
4. Create facility and radiologist accounts
5. Test DICOM upload functionality

## 🔄 Maintenance Commands
- **Restart Application**: sudo supervisorctl restart noctisview
- **Restart DICOM Service**: sudo supervisorctl restart noctisview_dicom
- **View Logs**: sudo tail -f /var/log/supervisor/noctisview.log
- **Database Backup**: /opt/backups/backup_noctisview.sh
- **SSL Renewal**: sudo certbot renew

## 📊 Monitoring
- **System Status**: sudo systemctl status nginx postgresql redis-server supervisor
- **Application Logs**: /var/log/supervisor/noctisview.log
- **DICOM Logs**: /var/log/supervisor/noctisview_dicom.log
- **Nginx Logs**: /var/log/nginx/
- **Fail2Ban Status**: sudo fail2ban-client status

Generated on: $(date)
EOF

log "✅ Deployment completed successfully!"
log "🌐 Your NOCTIS DICOM Viewer is now accessible at: https://${DOMAIN}"
log "👤 Admin login: admin / NoctisAdmin2024!"
log "📋 See $APP_DIR/DEPLOYMENT_REPORT.md for detailed information"

warn "⚠️ IMPORTANT: Change the default admin password after first login!"
warn "⚠️ Configure email settings in production_settings.py for notifications"
warn "⚠️ Test all functionality before production use"

log "🎉 Deployment completed! Your secure DICOM viewer is ready for production use."