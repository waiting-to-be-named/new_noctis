#!/bin/bash

# NOCTIS DICOM Viewer - Ubuntu 24.04.2 Deployment Script
# Automated deployment for production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="noctis"
APP_DIR="/opt/noctis"
DOMAIN="${1:-your-domain.com}"
DB_PASSWORD="${2:-$(openssl rand -base64 32)}"
SECRET_KEY="${3:-$(openssl rand -hex 32)}"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}NOCTIS DICOM Viewer Deployment${NC}"
echo -e "${BLUE}Ubuntu 24.04.2 LTS${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   exit 1
fi

# Check Ubuntu version
UBUNTU_VERSION=$(lsb_release -rs)
if [[ "$UBUNTU_VERSION" != "24.04" ]]; then
    echo -e "${YELLOW}Warning: This script is optimized for Ubuntu 24.04.2${NC}"
    echo -e "${YELLOW}Current version: $UBUNTU_VERSION${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Starting deployment...${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated"

# Install essential packages
print_status "Installing essential packages..."
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
    rsyslog \
    python3.12 \
    python3.12-dev \
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
    libspatialindex-dev \
    postgresql-16 \
    postgresql-contrib-16 \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx
print_success "Essential packages installed"

# Configure automatic security updates
print_status "Configuring automatic security updates..."
sudo dpkg-reconfigure -plow unattended-upgrades
print_success "Automatic updates configured"

# Create application user
print_status "Creating application user..."
sudo adduser --system --group --home $APP_DIR $APP_NAME
sudo usermod -aG sudo $APP_NAME
print_success "Application user created"

# Configure firewall
print_status "Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 11112/tcp
print_success "Firewall configured"

# Configure PostgreSQL
print_status "Configuring PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres createdb ${APP_NAME}_db
sudo -u postgres createuser ${APP_NAME}_user
sudo -u postgres psql -c "ALTER USER ${APP_NAME}_user PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${APP_NAME}_db TO ${APP_NAME}_user;"
sudo -u postgres psql -c "ALTER USER ${APP_NAME}_user CREATEDB;"

# Optimize PostgreSQL for medical imaging
sudo -u postgres psql -c "ALTER SYSTEM SET max_connections = '200';"
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

sudo systemctl restart postgresql
print_success "PostgreSQL configured"

# Configure Redis
print_status "Configuring Redis..."
sudo sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
sudo sed -i 's/# save 900 1/save 900 1/' /etc/redis/redis.conf
sudo sed -i 's/# save 300 10/save 300 10/' /etc/redis/redis.conf
sudo sed -i 's/# save 60 10000/save 60 10000/' /etc/redis/redis.conf

sudo systemctl start redis-server
sudo systemctl enable redis-server
print_success "Redis configured"

# Configure Nginx
print_status "Configuring Nginx..."
sudo sed -i 's/# server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip on;/gzip on;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_vary on;/gzip_vary on;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_min_length 1024;/gzip_min_length 1024;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_proxied any;/gzip_proxied any;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_comp_level 6;/gzip_comp_level 6;/' /etc/nginx/nginx.conf
sudo sed -i 's/# gzip_types/gzip_types/' /etc/nginx/nginx.conf

sudo systemctl start nginx
sudo systemctl enable nginx
print_success "Nginx configured"

# Deploy application
print_status "Deploying application..."
sudo mkdir -p $APP_DIR
sudo chown $APP_NAME:$APP_NAME $APP_DIR

# Copy application files
sudo cp -r . $APP_DIR/
sudo chown -R $APP_NAME:$APP_NAME $APP_DIR
sudo chmod -R 755 $APP_DIR

# Create virtual environment
sudo -u $APP_NAME python3 -m venv $APP_DIR/venv
sudo -u $APP_NAME $APP_DIR/venv/bin/pip install --upgrade pip setuptools wheel
sudo -u $APP_NAME $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt
sudo -u $APP_NAME $APP_DIR/venv/bin/pip install gunicorn psycopg2-binary whitenoise redis celery
print_success "Application deployed"

# Create environment file
print_status "Creating environment configuration..."
sudo -u $APP_NAME cat > $APP_DIR/.env << EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
DB_NAME=${APP_NAME}_db
DB_USER=${APP_NAME}_user
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/1
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=your_email@domain.com
EMAIL_HOST_PASSWORD=your_email_password
EMAIL_USE_TLS=True
EMAIL_PORT=587
STATIC_ROOT=$APP_DIR/staticfiles
MEDIA_ROOT=$APP_DIR/media
LOG_LEVEL=INFO
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/2
EOF

sudo chmod 600 $APP_DIR/.env
print_success "Environment configured"

# Setup Django
print_status "Setting up Django..."
sudo -u $APP_NAME bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py makemigrations"
sudo -u $APP_NAME bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py migrate"
sudo -u $APP_NAME bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py collectstatic --noinput"

# Create necessary directories
sudo -u $APP_NAME mkdir -p $APP_DIR/logs
sudo -u $APP_NAME mkdir -p $APP_DIR/media/dicom_files
sudo -u $APP_DIR/staticfiles
sudo -u $APP_NAME mkdir -p $APP_DIR/temp
sudo -u $APP_NAME mkdir -p $APP_DIR/backup

# Set permissions
sudo chmod -R 755 $APP_DIR/media
sudo chmod -R 755 $APP_DIR/staticfiles
sudo chmod -R 755 $APP_DIR/logs
print_success "Django setup complete"

# Create systemd services
print_status "Creating systemd services..."

# Main application service
sudo tee /etc/systemd/system/$APP_NAME.service > /dev/null << EOF
[Unit]
Description=Noctis DICOM Viewer
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=notify
User=$APP_NAME
Group=$APP_NAME
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.settings"
ExecStart=$APP_DIR/venv/bin/gunicorn -c gunicorn.conf.py noctisview.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/media $APP_DIR/logs $APP_DIR/temp

[Install]
WantedBy=multi-user.target
EOF

# DICOM SCP service
sudo tee /etc/systemd/system/$APP_NAME-scp.service > /dev/null << EOF
[Unit]
Description=Noctis DICOM SCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$APP_NAME
Group=$APP_NAME
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.settings"
ExecStart=$APP_DIR/venv/bin/python enhanced_scp_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME-scp

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/media $APP_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME
sudo systemctl enable $APP_NAME-scp
sudo systemctl start $APP_NAME
sudo systemctl start $APP_NAME-scp
print_success "Systemd services created"

# Configure Nginx site
print_status "Configuring Nginx site..."
sudo tee /etc/nginx/sites-available/$APP_NAME > /dev/null << EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=upload:10m rate=2r/s;

# Upstream for load balancing
upstream ${APP_NAME}_backend {
    server 127.0.0.1:8000;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
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
        
        proxy_pass http://${APP_NAME}_backend;
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
        
        proxy_pass http://${APP_NAME}_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files
    location /static/ {
        alias $APP_DIR/staticfiles/;
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
        alias $APP_DIR/media/;
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

sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
print_success "Nginx site configured"

# Get SSL certificate
if [[ "$DOMAIN" != "your-domain.com" ]]; then
    print_status "Getting SSL certificate..."
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    print_success "SSL certificate obtained"
else
    print_warning "Skipping SSL certificate (using default domain)"
fi

# Create monitoring script
print_status "Creating monitoring script..."
sudo tee $APP_DIR/monitor.sh > /dev/null << 'EOF'
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

sudo chmod +x $APP_DIR/monitor.sh
print_success "Monitoring script created"

# Create backup script
print_status "Creating backup script..."
sudo tee $APP_DIR/backup.sh > /dev/null << EOF
#!/bin/bash
BACKUP_DIR="$APP_DIR/backup"
DATE=\$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p \$BACKUP_DIR

# Database backup
pg_dump -U ${APP_NAME}_user -h localhost ${APP_NAME}_db > \$BACKUP_DIR/db_backup_\$DATE.sql

# DICOM files backup
rsync -av --delete $APP_DIR/media/dicom_files/ \$BACKUP_DIR/dicom_files/

# Application backup
tar -czf \$BACKUP_DIR/app_backup_\$DATE.tar.gz $APP_DIR --exclude=$APP_DIR/venv --exclude=$APP_DIR/logs

# Clean old backups (keep 30 days)
find \$BACKUP_DIR -name "*.sql" -mtime +30 -delete
find \$BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: \$DATE"
EOF

sudo chmod +x $APP_DIR/backup.sh
print_success "Backup script created"

# Configure log rotation
print_status "Configuring log rotation..."
sudo tee /etc/logrotate.d/$APP_NAME > /dev/null << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $APP_NAME $APP_NAME
    postrotate
        systemctl reload $APP_NAME
    endscript
}
EOF
print_success "Log rotation configured"

# Optimize system
print_status "Optimizing system for medical imaging..."
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_ratio=15' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_background_ratio=5' | sudo tee -a /etc/sysctl.conf
echo 'net.core.rmem_max=16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max=16777216' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
print_success "System optimized"

# Final verification
print_status "Performing final verification..."
sleep 5

# Check services
if sudo systemctl is-active --quiet $APP_NAME; then
    print_success "Main application is running"
else
    print_error "Main application failed to start"
    sudo systemctl status $APP_NAME
fi

if sudo systemctl is-active --quiet $APP_NAME-scp; then
    print_success "DICOM SCP server is running"
else
    print_error "DICOM SCP server failed to start"
    sudo systemctl status $APP_NAME-scp
fi

if sudo systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_error "Nginx failed to start"
    sudo systemctl status nginx
fi

if sudo systemctl is-active --quiet postgresql; then
    print_success "PostgreSQL is running"
else
    print_error "PostgreSQL failed to start"
    sudo systemctl status postgresql
fi

if sudo systemctl is-active --quiet redis-server; then
    print_success "Redis is running"
else
    print_error "Redis failed to start"
    sudo systemctl status redis-server
fi

# Test application
if curl -f http://localhost/health/ > /dev/null 2>&1; then
    print_success "Application health check passed"
else
    print_warning "Application health check failed (may need time to start)"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}Application Information:${NC}"
echo -e "  URL: https://$DOMAIN"
echo -e "  Health Check: https://$DOMAIN/health/"
echo -e "  Application Directory: $APP_DIR"
echo -e "  Database: ${APP_NAME}_db"
echo -e "  Database User: ${APP_NAME}_user"
echo -e "  Database Password: $DB_PASSWORD"
echo ""
echo -e "${BLUE}Management Commands:${NC}"
echo -e "  Check Status: sudo systemctl status $APP_NAME"
echo -e "  View Logs: sudo journalctl -u $APP_NAME -f"
echo -e "  Monitor System: $APP_DIR/monitor.sh"
echo -e "  Create Backup: $APP_DIR/backup.sh"
echo -e "  Restart Application: sudo systemctl restart $APP_NAME"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Create superuser: sudo -u $APP_NAME bash -c 'cd $APP_DIR && source venv/bin/activate && python manage.py createsuperuser'"
echo -e "  2. Configure email settings in $APP_DIR/.env"
echo -e "  3. Set up regular backups"
echo -e "  4. Monitor system performance"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo -e "  - Change default passwords"
echo -e "  - Configure firewall rules"
echo -e "  - Set up monitoring and alerting"
echo -e "  - Regular security updates"
echo ""
echo -e "${GREEN}Deployment completed successfully!${NC}"