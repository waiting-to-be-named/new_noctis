# NOCTIS DICOM Viewer - Comprehensive Deployment Guide

## 🎯 Overview

This guide provides step-by-step instructions for deploying the NOCTIS DICOM Viewer system on Ubuntu 18.04+ with enterprise-grade security and HIPAA compliance features.

### 🌟 Key Features
- **Role-Based Access Control**: Facilities, Radiologists, Technicians, and Administrators
- **DICOM Networking**: C-STORE, C-FIND, C-MOVE support for remote modalities
- **Advanced DICOM Viewer**: MPR, 3D reconstruction, measurements, annotations
- **Report Management**: Radiologist report creation with facility-specific printing
- **File Attachments**: Universal file attachment with role-based viewing
- **Real-time Notifications**: Email and in-app notifications
- **Enterprise Security**: SSL, firewall, intrusion detection, audit logging
- **Automated Backups**: Daily database and media backups

---

## 📋 Prerequisites

### System Requirements
- **Operating System**: Ubuntu 18.04 LTS or newer
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: Minimum 50GB (500GB+ recommended for DICOM storage)
- **Network**: Static IP address or DDNS setup
- **Domain**: Registered domain name (we'll use DuckDNS in this guide)

### Required Information
- **Domain Name**: Your domain (e.g., `yourname.duckdns.org`)
- **Local IP**: Your server's local IP address
- **Email**: Administrator email for SSL certificates and notifications
- **DuckDNS Token**: If using DuckDNS (free DDNS service)

---

## 🚀 Quick Deployment (Automated)

### Step 1: Download and Prepare
```bash
# Clone the repository
git clone https://github.com/your-repo/noctisview.git
cd noctisview

# Make deployment script executable
chmod +x deploy_ubuntu_secure.sh
```

### Step 2: Configure Domain
If using DuckDNS (recommended for testing):
1. Visit https://www.duckdns.org
2. Create account and get your token
3. Create subdomain (e.g., `yourname.duckdns.org`)
4. Update IP address to your server's public IP

### Step 3: Run Deployment
```bash
# Run the automated deployment script
./deploy_ubuntu_secure.sh
```

The script will:
- ✅ Update system packages
- ✅ Install and configure all dependencies
- ✅ Set up PostgreSQL with SSL
- ✅ Configure Redis caching
- ✅ Deploy Django application
- ✅ Set up Nginx with security headers
- ✅ Obtain SSL certificate via Let's Encrypt
- ✅ Configure Gunicorn application server
- ✅ Set up process management with Supervisor
- ✅ Configure Fail2Ban intrusion prevention
- ✅ Set up automated backups
- ✅ Create admin account

---

## 🛠️ Manual Deployment (Step-by-Step)

### Step 1: System Preparation

#### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

#### Install Essential Packages
```bash
sudo apt install -y \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    nginx redis-server supervisor \
    ufw fail2ban certbot python3-certbot-nginx \
    build-essential libpq-dev libssl-dev libffi-dev \
    git curl htop unzip
```

### Step 2: Security Configuration

#### Configure Firewall
```bash
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 11112/tcp  # DICOM port
sudo ufw --force enable
```

#### Configure Fail2Ban
```bash
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
logpath = /opt/noctisview/logs/noctisview.log
maxretry = 5
bantime = 1800
EOF

sudo tee /etc/fail2ban/filter.d/django-auth.conf > /dev/null << EOF
[Definition]
failregex = ^.*Invalid login attempt from <HOST>.*$
ignoreregex =
EOF

sudo systemctl restart fail2ban
```

### Step 3: Database Setup

#### Configure PostgreSQL
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Generate random password
DB_PASSWORD=$(openssl rand -base64 32)
DB_NAME="noctisview_db"
DB_USER="noctisview_user"

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Secure PostgreSQL
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/10/main/postgresql.conf
sudo sed -i "s/#ssl = off/ssl = on/" /etc/postgresql/10/main/postgresql.conf
sudo systemctl restart postgresql
```

#### Configure Redis
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo sed -i 's/# requirepass foobared/requirepass noctis_redis_2024/' /etc/redis/redis.conf
sudo systemctl restart redis-server
```

### Step 4: Application Setup

#### Create Application User and Directory
```bash
APP_USER="noctis"
APP_DIR="/opt/noctisview"

sudo adduser --disabled-password --gecos "" $APP_USER
sudo usermod -aG www-data $APP_USER
sudo mkdir -p $APP_DIR
sudo chown $APP_USER:$APP_USER $APP_DIR
```

#### Deploy Application Code
```bash
# Copy application files
sudo cp -r /path/to/noctisview/* $APP_DIR/
sudo chown -R $APP_USER:$APP_USER $APP_DIR

# Create Python virtual environment
sudo -u $APP_USER python3 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements_production.txt
```

#### Configure Django Settings
```bash
# Generate secret key
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Create production settings
sudo -u $APP_USER tee $APP_DIR/noctisview/production_settings.py > /dev/null << EOF
from .settings import *
import os

# Security Settings
DEBUG = False
ALLOWED_HOSTS = ['noctisview.duckdns.org', 'YOUR_IP_ADDRESS', 'localhost', '127.0.0.1']

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

# Security
SECRET_KEY = '$SECRET_KEY'
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

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
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

os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
EOF
```

#### Initialize Django Application
```bash
cd $APP_DIR
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py makemigrations
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py migrate
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py collectstatic --noinput
```

#### Create Admin User and Default Facility
```bash
sudo -u $APP_USER DJANGO_SETTINGS_MODULE=noctisview.production_settings $APP_DIR/venv/bin/python manage.py shell << 'EOF'
from worklist.models import CustomUser, UserRole, Facility

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
```

### Step 5: Web Server Configuration

#### Configure Nginx
```bash
DOMAIN="noctisview.duckdns.org"

sudo tee /etc/nginx/sites-available/noctisview > /dev/null << EOF
upstream noctisview_app {
    server unix:$APP_DIR/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    
    client_max_body_size 10G;
    client_body_timeout 300s;
    client_header_timeout 300s;
    keepalive_timeout 300s;
    send_timeout 300s;
    
    # SSL Configuration (will be updated by Certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
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

sudo ln -sf /etc/nginx/sites-available/noctisview /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
```

#### Obtain SSL Certificate
```bash
sudo mkdir -p /var/www/html
sudo systemctl reload nginx

sudo certbot certonly --webroot \
    --webroot-path=/var/www/html \
    --email admin@$DOMAIN \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN
```

### Step 6: Application Server Configuration

#### Configure Gunicorn
```bash
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
```

#### Configure Supervisor
```bash
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
```

### Step 7: Backup Configuration

#### Setup Automated Backups
```bash
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
```

### Step 8: Start Services

```bash
sudo systemctl reload nginx
sudo systemctl restart supervisor
sudo systemctl enable supervisor
sudo systemctl restart fail2ban
```

---

## 🔧 Configuration

### User Roles and Permissions

#### Administrator
- **Access**: All studies, all facilities
- **Permissions**: Full system access, user management, reports, configurations
- **Features**: System monitoring, audit logs, backup management

#### Radiologist
- **Access**: All studies, all facilities
- **Permissions**: Create/edit reports, view all DICOM data, print reports
- **Features**: Advanced DICOM tools, reporting workflow, study assignment

#### Facility User
- **Access**: Only their facility's studies
- **Permissions**: Upload DICOM, view finalized reports, print own reports
- **Features**: Basic DICOM viewing, file attachments, notifications

#### Technician
- **Access**: Only their facility's studies
- **Permissions**: Upload DICOM, basic study management
- **Features**: DICOM upload, quality control, annotations

### DICOM Networking Configuration

To connect modalities to the PACS:

#### Modality Configuration
```
AE Title: NOCTIS_PACS
Host: your-domain.com (or IP address)
Port: 11112
```

#### Start DICOM Service
```bash
# Via Django management command
python manage.py start_dicom_service

# Or via Supervisor (already configured)
sudo supervisorctl start noctisview_dicom
```

### Email Notifications

Configure email settings in `production_settings.py`:

```python
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use app password for Gmail
DEFAULT_FROM_EMAIL = 'noreply@noctisview.duckdns.org'
```

---

## 🔐 Security Features

### Network Security
- **UFW Firewall**: Blocks unauthorized access
- **Fail2Ban**: Prevents brute force attacks
- **Rate Limiting**: Protects against DDoS
- **SSL/TLS**: Encrypts all communications

### Application Security
- **Role-Based Access**: Facility data isolation
- **Audit Logging**: Tracks all user actions
- **Session Security**: Secure session management
- **Input Validation**: Prevents injection attacks

### Data Security
- **Database Encryption**: PostgreSQL with SSL
- **File Permissions**: Restricted access to sensitive files
- **Secure Headers**: Prevents XSS and clickjacking
- **Data Anonymization**: Optional patient data protection

---

## 📊 Monitoring and Maintenance

### System Status Commands
```bash
# Check all services
sudo systemctl status nginx postgresql redis-server supervisor

# View application logs
sudo tail -f /var/log/supervisor/noctisview.log

# View DICOM service logs
sudo tail -f /var/log/supervisor/noctisview_dicom.log

# Check Fail2Ban status
sudo fail2ban-client status

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Maintenance Commands
```bash
# Restart application
sudo supervisorctl restart noctisview

# Restart DICOM service
sudo supervisorctl restart noctisview_dicom

# Manual backup
/opt/backups/backup_noctisview.sh

# Update SSL certificate
sudo certbot renew

# Clear Django cache
python manage.py clear_cache
```

### Performance Monitoring
```bash
# Database performance
sudo -u postgres psql -d noctisview_db -c "\dx"

# Disk usage
df -h
du -sh /opt/noctisview/media/

# Memory usage
free -h
htop
```

---

## 🔧 Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
sudo tail -f /var/log/supervisor/noctisview.log

# Check configuration
sudo nginx -t
sudo supervisorctl status

# Restart services
sudo systemctl restart nginx
sudo supervisorctl restart noctisview
```

#### DICOM Connection Issues
```bash
# Check DICOM service
sudo supervisorctl status noctisview_dicom

# Check firewall
sudo ufw status
sudo netstat -tlnp | grep 11112

# Test DICOM connectivity
telnet your-domain.com 11112
```

#### Database Issues
```bash
# Check PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -l

# Check connections
sudo -u postgres psql -d noctisview_db -c "SELECT * FROM pg_stat_activity;"
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --dry-run

# Check nginx SSL configuration
sudo nginx -t
```

### Log Locations
- **Application**: `/var/log/supervisor/noctisview.log`
- **DICOM Service**: `/var/log/supervisor/noctisview_dicom.log`
- **Nginx**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/`
- **Fail2Ban**: `/var/log/fail2ban.log`

---

## 🆙 Updates and Upgrades

### Application Updates
```bash
# Backup before update
/opt/backups/backup_noctisview.sh

# Pull latest code
cd /opt/noctisview
git pull origin main

# Update dependencies
sudo -u noctis /opt/noctisview/venv/bin/pip install -r requirements_production.txt

# Run migrations
sudo -u noctis DJANGO_SETTINGS_MODULE=noctisview.production_settings /opt/noctisview/venv/bin/python manage.py migrate

# Collect static files
sudo -u noctis DJANGO_SETTINGS_MODULE=noctisview.production_settings /opt/noctisview/venv/bin/python manage.py collectstatic --noinput

# Restart application
sudo supervisorctl restart noctisview
```

### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update SSL certificates
sudo certbot renew

# Restart services if needed
sudo systemctl restart nginx postgresql redis-server
```

---

## 📞 Support and Documentation

### Quick Reference
- **Application URL**: `https://noctisview.duckdns.org`
- **Admin Panel**: `https://noctisview.duckdns.org/admin`
- **Worklist**: `https://noctisview.duckdns.org/worklist`
- **DICOM Viewer**: `https://noctisview.duckdns.org/viewer`

### Default Credentials
- **Username**: `admin`
- **Password**: `NoctisAdmin2024!`

**⚠️ IMPORTANT**: Change the default password immediately after first login!

### Next Steps After Deployment
1. ✅ Change default admin password
2. ✅ Configure email settings
3. ✅ Create facility accounts
4. ✅ Create radiologist accounts
5. ✅ Test DICOM upload functionality
6. ✅ Configure modality connections
7. ✅ Test reporting workflow
8. ✅ Verify backup functionality
9. ✅ Set up monitoring alerts
10. ✅ Train users on the system

---

## 🎉 Conclusion

Your NOCTIS DICOM Viewer system is now deployed with enterprise-grade security and HIPAA compliance features. The system includes:

- ✅ **Secure Web Interface** with role-based access
- ✅ **Advanced DICOM Viewer** with measurement tools
- ✅ **Report Management System** with printing capabilities
- ✅ **File Attachment System** accessible to all users
- ✅ **DICOM Networking** for remote modalities
- ✅ **Real-time Notifications** for workflow management
- ✅ **Automated Backups** for data protection
- ✅ **Intrusion Detection** and monitoring
- ✅ **SSL Encryption** for all communications

The system is ready for production use in medical imaging environments. Remember to keep the system updated and monitor the logs regularly for optimal performance and security.

For additional support or customizations, refer to the application logs and monitoring tools configured during deployment.