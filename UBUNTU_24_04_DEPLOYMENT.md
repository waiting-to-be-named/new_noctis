# NOCTIS DICOM Viewer - Ubuntu 24.04.2 Production Deployment Guide

## Ubuntu 24.04.2 LTS Production Setup

### System Requirements for Ubuntu 24.04.2

#### Minimum Hardware Requirements
- **CPU**: 4+ cores (8+ recommended for medical imaging)
- **RAM**: 16GB+ (32GB recommended for large DICOM files)
- **Storage**: 1TB+ NVMe SSD (medical images are large)
- **Network**: 1Gbps+ connection
- **OS**: Ubuntu 24.04.2 LTS (Noble Numbat)

#### Recommended Production Specifications
- **CPU**: 8+ cores (AMD EPYC or Intel Xeon)
- **RAM**: 64GB+ ECC memory
- **Storage**: 2TB+ NVMe SSD with RAID 1
- **Network**: 10Gbps connection
- **Backup**: Separate backup storage

### Initial Ubuntu 24.04.2 Setup

#### 1. System Update and Security
```bash
# Update system to latest packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    iotop \
    nethogs \
    fail2ban \
    ufw \
    unattended-upgrades \
    logrotate \
    rsyslog

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades

# Enable firewall
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 11112/tcp  # DICOM SCP port
```

#### 2. Create Production User
```bash
# Create dedicated user for the application
sudo adduser --system --group --home /opt/noctis noctis
sudo usermod -aG sudo noctis

# Set up SSH key authentication (recommended)
sudo mkdir -p /home/noctis/.ssh
sudo chown noctis:noctis /home/noctis/.ssh
sudo chmod 700 /home/noctis/.ssh
```

#### 3. Install Python 3.12 (Ubuntu 24.04.2 Default)
```bash
# Ubuntu 24.04.2 comes with Python 3.12 by default
python3 --version  # Should show Python 3.12.x

# Install Python development tools
sudo apt install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-wheel \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libopenexr-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libspatialindex-dev
```

#### 4. Install Database (PostgreSQL 16)
```bash
# Install PostgreSQL 16 (latest in Ubuntu 24.04.2)
sudo apt install -y postgresql-16 postgresql-contrib-16

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configure PostgreSQL for production
sudo -u postgres psql -c "ALTER SYSTEM SET max_connections = '200';"
sudo -u postgres psql -c "ALTER SYSTEM SET shared_buffers = '256MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_cache_size = '1GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET maintenance_work_mem = '256MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET checkpoint_completion_target = '0.9';"
sudo -u postgres psql -c "ALTER SYSTEM SET wal_buffers = '16MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET default_statistics_target = '100';"
sudo -u postgres psql -c "ALTER SYSTEM SET random_page_cost = '1.1';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_io_concurrency = '200';"
sudo -u postgres psql -c "ALTER SYSTEM SET work_mem = '4MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET min_wal_size = '1GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET max_wal_size = '4GB';"

# Restart PostgreSQL to apply changes
sudo systemctl restart postgresql
```

#### 5. Install Redis for Caching
```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis for production
sudo sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
sudo sed -i 's/# save 900 1/save 900 1/' /etc/redis/redis.conf
sudo sed -i 's/# save 300 10/save 300 10/' /etc/redis/redis.conf
sudo sed -i 's/# save 60 10000/save 60 10000/' /etc/redis/redis.conf

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### 6. Install Nginx
```bash
# Install Nginx
sudo apt install -y nginx

# Configure Nginx for production
sudo sed -i 's/# server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip on;/gzip on;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_vary on;/gzip_vary on;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_min_length 1024;/gzip_min_length 1024;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_proxied any;/gzip_proxied any;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_comp_level 6;/gzip_comp_level 6;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_types/gzip_types/' /etc/nginx/nginx.conf

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Application Deployment

#### 1. Clone and Setup Application
```bash
# Switch to noctis user
sudo su - noctis

# Clone application (if using git)
cd /opt/noctis
git clone <your-repository-url> .

# Or copy files to /opt/noctis
sudo cp -r /path/to/your/application/* /opt/noctis/

# Set proper permissions
sudo chown -R noctis:noctis /opt/noctis
sudo chmod -R 755 /opt/noctis
```

#### 2. Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv /opt/noctis/venv

# Activate virtual environment
source /opt/noctis/venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn psycopg2-binary whitenoise redis celery
```

#### 3. Database Setup
```bash
# Create database and user
sudo -u postgres createdb noctis_db
sudo -u postgres createuser noctis_user

# Set database password
sudo -u postgres psql -c "ALTER USER noctis_user PASSWORD 'your_very_secure_password_here';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;"
sudo -u postgres psql -c "ALTER USER noctis_user CREATEDB;"

# Test database connection
psql -h localhost -U noctis_user -d noctis_db -c "SELECT version();"
```

#### 4. Environment Configuration
```bash
# Create production environment file
cat > /opt/noctis/.env << EOF
DEBUG=False
SECRET_KEY=your_very_secure_secret_key_here_$(openssl rand -hex 32)
DB_NAME=noctis_db
DB_USER=noctis_user
DB_PASSWORD=your_very_secure_password_here
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/1
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=your_email@domain.com
EMAIL_HOST_PASSWORD=your_email_password
EMAIL_USE_TLS=True
EMAIL_PORT=587
STATIC_ROOT=/opt/noctis/staticfiles
MEDIA_ROOT=/opt/noctis/media
LOG_LEVEL=INFO
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/2
EOF

# Set proper permissions
chmod 600 /opt/noctis/.env
```

#### 5. Django Setup
```bash
# Activate virtual environment
source /opt/noctis/venv/bin/activate

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Create necessary directories
mkdir -p /opt/noctis/logs
mkdir -p /opt/noctis/media/dicom_files
mkdir -p /opt/noctis/staticfiles
mkdir -p /opt/noctis/temp

# Set permissions
chmod -R 755 /opt/noctis/media
chmod -R 755 /opt/noctis/staticfiles
chmod -R 755 /opt/noctis/logs
```

#### 6. Gunicorn Configuration
```bash
# Create gunicorn configuration
cat > /opt/noctis/gunicorn.conf.py << EOF
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 300
keepalive = 2
preload_app = True

# Logging
accesslog = "/opt/noctis/logs/gunicorn_access.log"
errorlog = "/opt/noctis/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "noctis"

# Server mechanics
daemon = False
pidfile = "/opt/noctis/gunicorn.pid"
user = "noctis"
group = "noctis"
tmp_upload_dir = None
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Server hooks
def on_starting(server):
    server.log.info("Starting Noctis DICOM Server")

def on_reload(server):
    server.log.info("Reloading Noctis DICOM Server")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker aborted (pid: %s)", worker.pid)
EOF
```

#### 7. Systemd Services
```bash
# Create main application service
sudo tee /etc/systemd/system/noctis.service > /dev/null << EOF
[Unit]
Description=Noctis DICOM Viewer
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=notify
User=noctis
Group=noctis
WorkingDirectory=/opt/noctis
Environment="PATH=/opt/noctis/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.settings"
ExecStart=/opt/noctis/venv/bin/gunicorn -c gunicorn.conf.py noctisview.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=noctis

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/noctis/media /opt/noctis/logs /opt/noctis/temp

[Install]
WantedBy=multi-user.target
EOF

# Create DICOM SCP service
sudo tee /etc/systemd/system/noctis-scp.service > /dev/null << EOF
[Unit]
Description=Noctis DICOM SCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=noctis
Group=noctis
WorkingDirectory=/opt/noctis
Environment="PATH=/opt/noctis/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.settings"
ExecStart=/opt/noctis/venv/bin/python enhanced_scp_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=noctis-scp

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/noctis/media /opt/noctis/logs

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable noctis
sudo systemctl enable noctis-scp
sudo systemctl start noctis
sudo systemctl start noctis-scp
```

#### 8. Nginx Configuration
```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/noctis > /dev/null << EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=upload:10m rate=2r/s;

# Upstream for load balancing (if needed)
upstream noctis_backend {
    server 127.0.0.1:8000;
    # Add more servers for load balancing
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # File upload limits
    client_max_body_size 2G;
    client_body_timeout 300s;
    client_header_timeout 60s;

    # Proxy settings
    proxy_connect_timeout 75s;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_buffering off;
    proxy_request_buffering off;

    # Main application
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://noctis_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
    }

    # File upload endpoint
    location /upload/ {
        limit_req zone=upload burst=5 nodelay;
        
        proxy_pass http://noctis_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files
    location /static/ {
        alias /opt/noctis/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        
        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_proxied any;
        gzip_comp_level 6;
        gzip_types
            text/plain
            text/css
            text/xml
            text/javascript
            application/json
            application/javascript
            application/xml+rss
            application/atom+xml
            image/svg+xml;
    }

    # Media files
    location /media/ {
        alias /opt/noctis/media/;
        expires 1y;
        add_header Cache-Control "public";
        add_header X-Content-Type-Options nosniff;
        
        # Security for DICOM files
        location ~* \.(dcm|dicom)$ {
            add_header Content-Disposition "attachment";
        }
    }

    # Health check
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
    }
    
    location ~ \.(env|py|pyc|pyo|pyd|log|sql|db|bak|old|tmp)$ {
        deny all;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/noctis /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

#### 9. SSL Certificate (Let's Encrypt)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Set up auto-renewal
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### Monitoring and Logging

#### 1. Log Rotation
```bash
# Configure log rotation
sudo tee /etc/logrotate.d/noctis > /dev/null << EOF
/opt/noctis/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 noctis noctis
    postrotate
        systemctl reload noctis
    endscript
}
EOF
```

#### 2. System Monitoring
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs nginx-full

# Create monitoring script
sudo tee /opt/noctis/monitor.sh > /dev/null << 'EOF'
#!/bin/bash
echo "=== Noctis System Status ==="
echo "Date: $(date)"
echo "Uptime: $(uptime)"
echo "Memory: $(free -h)"
echo "Disk: $(df -h /)"
echo "CPU Load: $(cat /proc/loadavg)"
echo ""
echo "=== Services Status ==="
systemctl status noctis --no-pager -l
echo ""
systemctl status noctis-scp --no-pager -l
echo ""
systemctl status nginx --no-pager -l
echo ""
systemctl status postgresql --no-pager -l
echo ""
systemctl status redis-server --no-pager -l
echo ""
echo "=== Recent Logs ==="
tail -20 /opt/noctis/logs/django.log
EOF

sudo chmod +x /opt/noctis/monitor.sh
```

#### 3. Backup Script
```bash
# Create backup script
sudo tee /opt/noctis/backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/noctis"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U noctis_user -h localhost noctis_db > $BACKUP_DIR/db_backup_$DATE.sql

# DICOM files backup
rsync -av --delete /opt/noctis/media/dicom_files/ $BACKUP_DIR/dicom_files/

# Application backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /opt/noctis --exclude=/opt/noctis/venv --exclude=/opt/noctis/logs

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

sudo chmod +x /opt/noctis/backup.sh

# Add to crontab for daily backups
sudo crontab -e
# Add this line:
# 0 2 * * * /opt/noctis/backup.sh >> /opt/noctis/logs/backup.log 2>&1
```

### Performance Optimization

#### 1. System Tuning
```bash
# Optimize system for medical imaging
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_ratio=15' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_background_ratio=5' | sudo tee -a /etc/sysctl.conf
echo 'net.core.rmem_max=16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max=16777216' | sudo tee -a /etc/sysctl.conf

# Apply changes
sudo sysctl -p
```

#### 2. PostgreSQL Optimization
```bash
# Optimize PostgreSQL for medical imaging workload
sudo -u postgres psql -c "ALTER SYSTEM SET shared_buffers = '1GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_cache_size = '4GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET maintenance_work_mem = '512MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET checkpoint_completion_target = '0.9';"
sudo -u postgres psql -c "ALTER SYSTEM SET wal_buffers = '32MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET default_statistics_target = '500';"
sudo -u postgres psql -c "ALTER SYSTEM SET random_page_cost = '1.1';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_io_concurrency = '400';"
sudo -u postgres psql -c "ALTER SYSTEM SET work_mem = '8MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET min_wal_size = '2GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET max_wal_size = '8GB';"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Security Hardening

#### 1. Firewall Configuration
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 11112/tcp  # DICOM SCP
sudo ufw --force enable
```

#### 2. Fail2ban Configuration
```bash
# Configure Fail2ban for Nginx
sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log

[nginx-botsearch]
enabled = true
filter = nginx-botsearch
port = http,https
logpath = /var/log/nginx/access.log
EOF

sudo systemctl restart fail2ban
```

### Post-Deployment Verification

#### 1. System Health Check
```bash
# Run comprehensive health check
/opt/noctis/monitor.sh

# Check all services
sudo systemctl status noctis noctis-scp nginx postgresql redis-server

# Test database connection
psql -h localhost -U noctis_user -d noctis_db -c "SELECT version();"

# Test Redis connection
redis-cli ping

# Check disk space
df -h

# Check memory usage
free -h
```

#### 2. Application Testing
```bash
# Test web interface
curl -I https://your-domain.com

# Test health endpoint
curl https://your-domain.com/health/

# Test static files
curl -I https://your-domain.com/static/

# Test media files
curl -I https://your-domain.com/media/
```

#### 3. Performance Testing
```bash
# Install Apache Bench for load testing
sudo apt install -y apache2-utils

# Test with 100 requests, 10 concurrent
ab -n 100 -c 10 https://your-domain.com/

# Test file upload endpoint
ab -n 50 -c 5 -p test_file.txt https://your-domain.com/upload/
```

### Maintenance Schedule

#### Daily Tasks
- Check system logs: `sudo journalctl -u noctis -f`
- Monitor disk space: `df -h`
- Check service status: `systemctl status noctis`

#### Weekly Tasks
- Run backup: `/opt/noctis/backup.sh`
- Update system packages: `sudo apt update && sudo apt upgrade`
- Check SSL certificate: `sudo certbot certificates`

#### Monthly Tasks
- Review and rotate logs
- Update Python packages: `pip install --upgrade -r requirements.txt`
- Performance review and optimization

### Troubleshooting

#### Common Issues

1. **Service won't start**
   ```bash
   sudo systemctl status noctis
   sudo journalctl -u noctis -f
   ```

2. **Database connection issues**
   ```bash
   sudo systemctl status postgresql
   sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
   ```

3. **Nginx configuration errors**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

4. **SSL certificate issues**
   ```bash
   sudo certbot certificates
   sudo certbot renew --dry-run
   ```

### Support Information

- **Application Logs**: `/opt/noctis/logs/`
- **System Logs**: `sudo journalctl -u noctis`
- **Nginx Logs**: `/var/log/nginx/`
- **PostgreSQL Logs**: `/var/log/postgresql/`
- **Backup Location**: `/backup/noctis/`
- **Configuration Files**: `/opt/noctis/`

### Ubuntu 24.04.2 Specific Notes

- **Python 3.12**: Latest Python version with improved performance
- **PostgreSQL 16**: Latest stable version with enhanced features
- **Nginx 1.24**: Latest stable version with HTTP/3 support
- **Systemd**: Enhanced service management
- **Security**: Improved security features and updates

---

**Deployment Status: ✅ OPTIMIZED FOR UBUNTU 24.04.2 LTS**

**Last Updated:** $(date)
**Version:** 1.0.0
**Ubuntu Version:** 24.04.2 LTS (Noble Numbat)
**Status:** Production Ready