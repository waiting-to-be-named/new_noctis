# NOCTIS DICOM Viewer - Ubuntu Server & Docker Deployment Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Ubuntu Server Preparation](#ubuntu-server-preparation)
3. [Docker Installation](#docker-installation)
4. [SSL Certificate Setup](#ssl-certificate-setup)
5. [Deployment with Docker Compose](#deployment-with-docker-compose)
6. [Production Configuration](#production-configuration)
7. [System Management](#system-management)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Security Best Practices](#security-best-practices)

## System Requirements

### Minimum Hardware Requirements
- **CPU**: 4 cores (8+ cores recommended)
- **RAM**: 8GB (16GB+ recommended)
- **Storage**: 500GB SSD (1TB+ recommended for DICOM storage)
- **Network**: 1Gbps connection
- **OS**: Ubuntu Server 20.04 LTS or 22.04 LTS

### Software Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- SSL certificates (Let's Encrypt or commercial)

## Ubuntu Server Preparation

### 1. Update System
```bash
# Update package list and upgrade system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    iotop \
    net-tools \
    ufw \
    fail2ban \
    unattended-upgrades \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

### 2. Configure Firewall
```bash
# Enable UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if using custom SSH port)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow DICOM SCP port
sudo ufw allow 11112/tcp

# Enable firewall
sudo ufw --force enable
sudo ufw status
```

### 3. Configure System Limits
```bash
# Edit system limits
sudo tee -a /etc/security/limits.conf << EOF
# NOCTIS DICOM Viewer limits
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF

# Edit sysctl settings
sudo tee -a /etc/sysctl.conf << EOF
# NOCTIS DICOM Viewer optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
vm.overcommit_memory = 1
vm.swappiness = 10
EOF

# Apply sysctl settings
sudo sysctl -p
```

### 4. Create Application User
```bash
# Create noctis user
sudo useradd -m -s /bin/bash noctis
sudo usermod -aG docker noctis

# Create application directory
sudo mkdir -p /opt/noctis
sudo chown -R noctis:noctis /opt/noctis
```

## Docker Installation

### 1. Install Docker Engine
```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify installation
sudo docker run hello-world
```

### 2. Configure Docker
```bash
# Configure Docker daemon
sudo tee /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "10"
  },
  "storage-driver": "overlay2",
  "metrics-addr": "127.0.0.1:9323",
  "experimental": false
}
EOF

# Restart Docker
sudo systemctl restart docker
sudo systemctl enable docker
```

### 3. Install Docker Compose
```bash
# Install Docker Compose V2
sudo apt install docker-compose-plugin

# Verify installation
docker compose version
```

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install -y certbot

# Create SSL directory
sudo mkdir -p /opt/noctis/docker/ssl

# Generate certificates (replace your-domain.com)
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --agree-tos \
  --non-interactive \
  --email admin@your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/noctis/docker/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/noctis/docker/ssl/key.pem
sudo chown -R noctis:noctis /opt/noctis/docker/ssl

# Setup auto-renewal
sudo tee /etc/cron.d/certbot-renewal << EOF
0 2 * * * root certbot renew --quiet --post-hook "cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/noctis/docker/ssl/cert.pem && cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/noctis/docker/ssl/key.pem && docker restart noctis_nginx"
EOF
```

### Option 2: Self-Signed Certificate (Development Only)
```bash
# Generate self-signed certificate
sudo mkdir -p /opt/noctis/docker/ssl
cd /opt/noctis/docker/ssl

sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=noctis.local"

sudo chown -R noctis:noctis /opt/noctis/docker/ssl
```

## Deployment with Docker Compose

### 1. Clone Repository
```bash
# Switch to noctis user
sudo su - noctis

# Clone repository
cd /opt/noctis
git clone https://github.com/your-org/noctis-dicom-viewer.git .

# Or copy files if you have them locally
# scp -r /path/to/noctis/* noctis@server:/opt/noctis/
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables
vim .env

# Required changes:
# - DJANGO_SECRET_KEY: Generate a secure key
# - DB_PASSWORD: Set a strong database password
# - DJANGO_ALLOWED_HOSTS: Add your domain
# - EMAIL_*: Configure email settings
# - LETSENCRYPT_EMAIL: Your email
# - LETSENCRYPT_DOMAINS: Your domains
```

### 3. Generate Secret Key
```bash
# Generate Django secret key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 4. Build and Deploy
```bash
# Build Docker images
docker compose build

# Start services
docker compose up -d

# Check logs
docker compose logs -f

# Verify all services are running
docker compose ps
```

### 5. Initial Setup
```bash
# Create superuser (if not created automatically)
docker compose exec web python manage.py createsuperuser

# Collect static files (if needed)
docker compose exec web python manage.py collectstatic --noinput

# Run migrations (if needed)
docker compose exec web python manage.py migrate
```

## Production Configuration

### 1. Environment Variables
Create production `.env` file:
```bash
# Django Settings
DJANGO_SECRET_KEY=your-generated-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_ADMIN_PASSWORD=strong-admin-password

# Database
DB_NAME=noctis_db
DB_USER=noctis_user
DB_PASSWORD=strong-database-password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/1

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# DICOM Settings
DICOM_SCP_AE_TITLE=NOCTIS_SCP
DICOM_SCP_PORT=11112
MAX_DICOM_FILE_SIZE=5368709120

# Performance
GUNICORN_WORKERS=8
CELERY_WORKERS=4
```

### 2. Docker Compose Production Override
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  web:
    restart: always
    environment:
      - DJANGO_DEBUG=False
    
  nginx:
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
    ports:
      - "80:80"
      - "443:443"
    
  db:
    volumes:
      - /data/postgres:/var/lib/postgresql/data
    
  redis:
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
```

Deploy with:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## System Management

### 1. Service Management
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart web

# View logs
docker compose logs -f web
docker compose logs --tail=100 nginx

# Execute commands in container
docker compose exec web python manage.py shell
docker compose exec db psql -U noctis_user noctis_db
```

### 2. Backup Management
```bash
# Manual backup
docker compose exec backup /backup.sh

# Schedule automatic backups
sudo tee /etc/cron.d/noctis-backup << EOF
0 2 * * * noctis cd /opt/noctis && docker compose exec -T backup /backup.sh >> /opt/noctis/logs/backup.log 2>&1
EOF

# Restore from backup
docker compose exec -T db psql -U noctis_user noctis_db < /backups/database/noctis_db_20231215_020000.sql
```

### 3. Update Deployment
```bash
# Pull latest changes
cd /opt/noctis
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d

# Run migrations if needed
docker compose exec web python manage.py migrate
```

## Monitoring & Maintenance

### 1. Health Checks
```bash
# Check application health
curl https://your-domain.com/health/

# Check Docker containers
docker compose ps
docker stats

# Check system resources
htop
df -h
free -h
```

### 2. Log Management
```bash
# View application logs
tail -f /opt/noctis/logs/django.log
tail -f /opt/noctis/logs/gunicorn-access.log

# View Docker logs
docker compose logs -f --tail=100

# Log rotation is handled automatically by logrotate
```

### 3. Performance Monitoring
```bash
# Install monitoring tools
sudo apt install -y prometheus node-exporter grafana

# Or use Docker-based monitoring
docker run -d \
  --name=netdata \
  -p 19999:19999 \
  -v /etc/passwd:/host/etc/passwd:ro \
  -v /etc/group:/host/etc/group:ro \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --cap-add SYS_PTRACE \
  --security-opt apparmor=unconfined \
  netdata/netdata
```

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check logs
docker compose logs web

# Check permissions
ls -la /opt/noctis
chown -R noctis:noctis /opt/noctis

# Check disk space
df -h
```

#### 2. Database Connection Issues
```bash
# Test database connection
docker compose exec web python manage.py dbshell

# Check database logs
docker compose logs db

# Restart database
docker compose restart db
```

#### 3. DICOM Upload Issues
```bash
# Check file permissions
docker compose exec web ls -la /app/media/dicom_files

# Check upload limits in nginx
docker compose exec nginx cat /etc/nginx/nginx.conf | grep client_max_body_size

# Monitor upload directory
watch -n 1 'du -sh /opt/noctis/media/dicom_files'
```

#### 4. Performance Issues
```bash
# Check resource usage
docker stats

# Increase workers
vim .env  # Adjust GUNICORN_WORKERS and CELERY_WORKERS

# Restart services
docker compose restart web celery_worker
```

## Security Best Practices

### 1. Regular Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker compose pull
docker compose up -d

# Update Python packages
docker compose exec web pip install --upgrade -r requirements.txt
```

### 2. Security Hardening
```bash
# Configure fail2ban
sudo tee /etc/fail2ban/jail.d/noctis.conf << EOF
[noctis-auth]
enabled = true
filter = noctis-auth
logpath = /opt/noctis/logs/django.log
maxretry = 5
bantime = 3600
EOF

# Implement rate limiting (already in nginx config)
# Configure ModSecurity for WAF protection
```

### 3. Backup Security
```bash
# Encrypt backups
# Add to backup script:
openssl enc -aes-256-cbc -salt -in backup.sql -out backup.sql.enc -k $BACKUP_PASSWORD

# Secure backup storage
chmod 600 /opt/noctis/backups/*
```

### 4. Monitoring Security
```bash
# Install security monitoring
sudo apt install -y aide rkhunter

# Configure AIDE
sudo aideinit
sudo cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Schedule security scans
sudo tee /etc/cron.d/security-scan << EOF
0 3 * * * root /usr/bin/aide --check >> /var/log/aide.log 2>&1
0 4 * * * root /usr/bin/rkhunter --check --skip-keypress >> /var/log/rkhunter.log 2>&1
EOF
```

## Maintenance Schedule

### Daily Tasks
- Monitor system health and logs
- Check backup completion
- Review error logs

### Weekly Tasks
- Review security logs
- Check disk usage
- Update system packages

### Monthly Tasks
- Review and rotate logs
- Test backup restoration
- Performance analysis
- Security audit

### Quarterly Tasks
- Update Docker images
- Review and update configurations
- Capacity planning
- Disaster recovery drill

## Support Information

For issues or questions:
1. Check logs in `/opt/noctis/logs/`
2. Review Docker container logs: `docker compose logs`
3. Consult documentation in `/opt/noctis/docs/`
4. Contact support with relevant log excerpts

---

**Important**: Always test configuration changes in a staging environment before applying to production.