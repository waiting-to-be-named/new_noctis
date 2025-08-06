# Complete Guide: Ubuntu Server Setup with Docker for System Deployment

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Ubuntu Server Setup](#initial-ubuntu-server-setup)
3. [Docker Installation](#docker-installation)
4. [Docker Compose Installation](#docker-compose-installation)
5. [System Security Configuration](#system-security-configuration)
6. [Docker Configuration and Optimization](#docker-configuration-and-optimization)
7. [Deployment Setup](#deployment-setup)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Backup and Recovery](#backup-and-recovery)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

- Ubuntu Server 20.04 LTS or 22.04 LTS (recommended)
- Root or sudo access
- Minimum 2GB RAM (4GB+ recommended)
- At least 20GB disk space
- Active internet connection

## Initial Ubuntu Server Setup

### 1. Update System Packages

```bash
# Update package index
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    curl \
    wget \
    vim \
    git \
    htop \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    apt-transport-https \
    ufw \
    fail2ban
```

### 2. Create a Non-Root User (if not already exists)

```bash
# Create new user
sudo adduser deployuser

# Add user to sudo group
sudo usermod -aG sudo deployuser

# Switch to new user
su - deployuser
```

### 3. Configure SSH Security

```bash
# Backup SSH config
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Edit SSH configuration
sudo vim /etc/ssh/sshd_config
```

Add/modify these settings:
```
Port 2222  # Change default SSH port
PermitRootLogin no
PasswordAuthentication no  # After setting up SSH keys
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
# Restart SSH service
sudo systemctl restart sshd
```

### 4. Setup SSH Key Authentication

On your local machine:
```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy SSH key to server
ssh-copy-id -p 2222 deployuser@your-server-ip
```

### 5. Configure Firewall (UFW)

```bash
# Enable UFW
sudo ufw enable

# Allow SSH on custom port
sudo ufw allow 2222/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow Docker default ports (if needed)
sudo ufw allow 2375/tcp
sudo ufw allow 2376/tcp

# Check status
sudo ufw status
```

## Docker Installation

### 1. Remove Old Docker Versions

```bash
sudo apt remove docker docker-engine docker.io containerd runc
```

### 2. Install Docker

```bash
# Add Docker's official GPG key
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt update

# Install Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Activate changes to groups
newgrp docker

# Verify installation
docker --version
docker run hello-world
```

### 3. Configure Docker Daemon

Create/edit Docker daemon configuration:
```bash
sudo vim /etc/docker/daemon.json
```

Add this configuration:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "userland-proxy": false,
  "default-address-pools": [
    {
      "base": "172.17.0.0/16",
      "size": 24
    }
  ]
}
```

```bash
# Restart Docker
sudo systemctl restart docker

# Enable Docker to start on boot
sudo systemctl enable docker
```

## Docker Compose Installation

### Option 1: Install via Package Manager (Recommended)

```bash
# Docker Compose is included with docker-compose-plugin
docker compose version
```

### Option 2: Install Standalone Docker Compose

```bash
# Download latest Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Create symbolic link
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installation
docker-compose --version
```

## System Security Configuration

### 1. Configure Fail2ban for Docker

Create Docker jail configuration:
```bash
sudo vim /etc/fail2ban/jail.d/docker.conf
```

Add:
```ini
[docker-nginx]
enabled = true
filter = docker-nginx
port = http,https
logpath = /var/lib/docker/containers/*/*-json.log
maxretry = 5
bantime = 3600
findtime = 600
```

### 2. Setup Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt install -y unattended-upgrades

# Configure automatic updates
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 3. Configure System Limits

Edit limits configuration:
```bash
sudo vim /etc/security/limits.conf
```

Add:
```
* soft nofile 65536
* hard nofile 65536
root soft nofile 65536
root hard nofile 65536
```

## Docker Configuration and Optimization

### 1. Docker Network Setup

```bash
# Create custom bridge network
docker network create --driver bridge app-network

# Create network with specific subnet
docker network create --driver bridge --subnet=172.20.0.0/16 --ip-range=172.20.240.0/20 app-network-custom
```

### 2. Docker Volume Management

```bash
# Create named volumes
docker volume create app-data
docker volume create app-logs

# List volumes
docker volume ls

# Inspect volume
docker volume inspect app-data
```

### 3. Docker Cleanup Script

Create cleanup script:
```bash
sudo vim /usr/local/bin/docker-cleanup.sh
```

Add:
```bash
#!/bin/bash
# Docker cleanup script

echo "Cleaning up Docker..."

# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove unused networks
docker network prune -f

# Remove build cache
docker builder prune -f

echo "Docker cleanup completed!"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/docker-cleanup.sh

# Add to crontab (runs daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/docker-cleanup.sh >> /var/log/docker-cleanup.log 2>&1") | crontab -
```

## Deployment Setup

### 1. Create Project Directory Structure

```bash
# Create deployment directory
mkdir -p ~/deployments/myapp
cd ~/deployments/myapp

# Create directory structure
mkdir -p {config,data,logs,scripts,backups}
```

### 2. Sample Docker Compose Configuration

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  # Web Application
  app:
    image: myapp:latest
    container_name: myapp
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
    volumes:
      - ./data/uploads:/app/uploads
      - ./logs/app:/app/logs
    networks:
      - app-network
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: myapp-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=myapp
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups/postgres:/backups
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: myapp-redis
    restart: unless-stopped
    command: redis-server --requirepass yourredispassword
    volumes:
      - redis-data:/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: myapp-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./config/nginx/sites:/etc/nginx/sites-enabled
      - ./data/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    networks:
      - app-network
    depends_on:
      - app

volumes:
  postgres-data:
  redis-data:

networks:
  app-network:
    driver: bridge
```

### 3. Environment Variables Setup

Create `.env` file:
```bash
# Application
NODE_ENV=production
APP_PORT=3000
APP_HOST=0.0.0.0

# Database
DB_HOST=db
DB_PORT=5432
DB_USER=user
DB_PASSWORD=securepassword
DB_NAME=myapp

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=yourredispassword

# Security
JWT_SECRET=your-jwt-secret
SESSION_SECRET=your-session-secret
```

### 4. Deployment Script

Create deployment script:
```bash
vim deploy.sh
```

Add:
```bash
#!/bin/bash

# Deployment script
set -e

echo "Starting deployment..."

# Pull latest images
docker-compose pull

# Stop current containers
docker-compose down

# Start new containers
docker-compose up -d

# Check health
sleep 10
docker-compose ps

# Show logs
docker-compose logs --tail=50

echo "Deployment completed!"
```

```bash
chmod +x deploy.sh
```

## Monitoring and Logging

### 1. Install Monitoring Stack

Create `docker-compose.monitoring.yml`:
```yaml
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - monitoring

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    volumes:
      - grafana-data:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3001:3000"
    networks:
      - monitoring

  # Node Exporter
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    ports:
      - "9100:9100"
    networks:
      - monitoring

  # cAdvisor
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - "8080:8080"
    networks:
      - monitoring

volumes:
  prometheus-data:
  grafana-data:

networks:
  monitoring:
    driver: bridge
```

### 2. Log Aggregation with ELK Stack (Optional)

Create `docker-compose.logging.yml`:
```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - logging

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    volumes:
      - ./config/logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5000:5000"
    environment:
      - "LS_JAVA_OPTS=-Xms256m -Xmx256m"
    depends_on:
      - elasticsearch
    networks:
      - logging

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - logging

volumes:
  elasticsearch-data:

networks:
  logging:
    driver: bridge
```

## Backup and Recovery

### 1. Automated Backup Script

Create backup script:
```bash
vim backup.sh
```

Add:
```bash
#!/bin/bash

# Backup configuration
BACKUP_DIR="/home/deployuser/deployments/myapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "Starting backup at $DATE"

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup PostgreSQL
docker exec myapp-db pg_dump -U user myapp > $BACKUP_DIR/$DATE/database.sql

# Backup volumes
docker run --rm -v myapp_app-data:/data -v $BACKUP_DIR/$DATE:/backup alpine tar czf /backup/app-data.tar.gz -C /data .

# Backup configuration files
tar czf $BACKUP_DIR/$DATE/config.tar.gz config/

# Backup Docker Compose files
cp docker-compose.yml $BACKUP_DIR/$DATE/
cp .env $BACKUP_DIR/$DATE/

# Remove old backups
find $BACKUP_DIR -type d -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "Backup completed!"
```

```bash
chmod +x backup.sh

# Add to crontab (daily at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * * /home/deployuser/deployments/myapp/backup.sh >> /var/log/backup.log 2>&1") | crontab -
```

### 2. Restore Script

Create restore script:
```bash
vim restore.sh
```

Add:
```bash
#!/bin/bash

# Restore script
if [ -z "$1" ]; then
    echo "Usage: ./restore.sh BACKUP_DATE"
    echo "Example: ./restore.sh 20231225_030000"
    exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="/home/deployuser/deployments/myapp/backups/$BACKUP_DATE"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Restoring from backup: $BACKUP_DATE"

# Stop containers
docker-compose down

# Restore database
docker-compose up -d db
sleep 10
docker exec -i myapp-db psql -U user myapp < $BACKUP_DIR/database.sql

# Restore volumes
docker run --rm -v myapp_app-data:/data -v $BACKUP_DIR:/backup alpine tar xzf /backup/app-data.tar.gz -C /data

# Restore configuration
tar xzf $BACKUP_DIR/config.tar.gz

# Start all containers
docker-compose up -d

echo "Restore completed!"
```

```bash
chmod +x restore.sh
```

## Troubleshooting

### Common Docker Issues and Solutions

#### 1. Container Won't Start
```bash
# Check logs
docker logs container-name

# Check detailed inspect
docker inspect container-name

# Check events
docker events --since 10m
```

#### 2. Network Issues
```bash
# List networks
docker network ls

# Inspect network
docker network inspect bridge

# Test connectivity
docker exec container-name ping other-container
```

#### 3. Storage Issues
```bash
# Check disk space
df -h

# Check Docker disk usage
docker system df

# Clean up
docker system prune -a
```

#### 4. Performance Issues
```bash
# Check container resources
docker stats

# Check container processes
docker top container-name

# Limit resources in docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### System Monitoring Commands

```bash
# Check system resources
htop

# Check disk I/O
iotop

# Check network connections
netstat -tulpn

# Check Docker daemon logs
journalctl -u docker.service -f

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Security Audit Commands

```bash
# Check for security updates
sudo apt list --upgradable

# Check open ports
sudo ss -tulpn

# Check failed login attempts
sudo journalctl -u ssh | grep "Failed"

# Check Docker security
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image myapp:latest
```

## Best Practices Summary

1. **Security**
   - Always use non-root users in containers
   - Keep secrets in environment variables or secret management tools
   - Regularly update base images and dependencies
   - Use multi-stage builds to minimize image size
   - Scan images for vulnerabilities

2. **Performance**
   - Use Alpine-based images when possible
   - Implement health checks for all services
   - Set resource limits to prevent container sprawl
   - Use Docker layer caching effectively
   - Monitor resource usage regularly

3. **Reliability**
   - Always use restart policies
   - Implement proper logging and monitoring
   - Regular automated backups
   - Test restore procedures
   - Document your deployment process

4. **Maintenance**
   - Automate routine tasks
   - Keep containers stateless
   - Use named volumes for persistent data
   - Regular cleanup of unused resources
   - Monitor disk space usage

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [12 Factor App Methodology](https://12factor.net/)

---

This guide provides a comprehensive setup for deploying applications on Ubuntu Server with Docker. Adjust configurations based on your specific requirements and always test in a development environment before deploying to production.