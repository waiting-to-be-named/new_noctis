# Ubuntu Server Deployment Guide for Noctis DICOM Viewer

This guide provides step-by-step instructions for setting up Ubuntu Server on VirtualBox, hardening it for security, and deploying the Noctis DICOM Viewer system.

## Table of Contents

1. [Ubuntu Server Installation](#ubuntu-server-installation)
2. [Initial Server Setup](#initial-server-setup)
3. [Security Hardening](#security-hardening)
4. [Docker Installation](#docker-installation)
5. [SSL Certificate Setup](#ssl-certificate-setup)
6. [Application Deployment](#application-deployment)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Backup Strategy](#backup-strategy)

## Ubuntu Server Installation

### 1. VirtualBox Setup

1. **Download Ubuntu Server 22.04 LTS**
   ```bash
   wget https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso
   ```

2. **Create Virtual Machine**
   - **Name**: Noctis-Server
   - **Type**: Linux
   - **Version**: Ubuntu (64-bit)
   - **Memory**: 8GB (minimum 4GB)
   - **Storage**: 100GB (minimum 50GB)
   - **CPU**: 4 cores (minimum 2)

3. **Network Configuration**
   - **Adapter 1**: NAT (for internet access)
   - **Adapter 2**: Host-only or Bridged (for local access)

4. **Install Ubuntu Server**
   - Boot from ISO
   - Select "Install Ubuntu Server"
   - Configure network with static IP
   - Create user account (avoid using 'root')
   - Install OpenSSH server
   - Select "Docker" snap package during installation

### 2. Post-Installation Network Setup

```bash
# Check network configuration
ip addr show

# Edit netplan configuration
sudo nano /etc/netplan/01-netcfg.yaml

# Example static IP configuration:
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses:
        - 192.168.56.100/24
      gateway4: 192.168.56.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]

# Apply network configuration
sudo netplan apply
```

## Initial Server Setup

### 1. System Update and Essential Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    logwatch \
    rkhunter \
    chkrootkit \
    aide \
    auditd

# Reboot system
sudo reboot
```

### 2. User Management

```bash
# Create service user for Noctis
sudo useradd -r -s /bin/false -d /opt/noctis noctis

# Add your user to docker group (if Docker was installed)
sudo usermod -aG docker $USER

# Create SSH key pair for secure access
ssh-keygen -t ed25519 -C "noctis-server-$(date +%Y%m%d)"
```

## Security Hardening

### 1. SSH Hardening

```bash
# Backup SSH configuration
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

**SSH Configuration (`/etc/ssh/sshd_config`):**
```
# Basic settings
Port 2222
Protocol 2
PermitRootLogin no
MaxAuthTries 3
MaxSessions 2
MaxStartups 2

# Authentication
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM no

# Timeout settings
ClientAliveInterval 300
ClientAliveCountMax 2
LoginGraceTime 30

# Restrict users
AllowUsers yourusername

# Disable dangerous features
X11Forwarding no
AllowTcpForwarding no
GatewayPorts no
PermitTunnel no
```

```bash
# Restart SSH service
sudo systemctl restart sshd

# Verify SSH configuration
sudo sshd -t
```

### 2. Firewall Configuration

```bash
# Reset UFW to defaults
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH on custom port
sudo ufw allow 2222/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific monitoring ports (only from local network)
sudo ufw allow from 192.168.0.0/16 to any port 3000  # Grafana
sudo ufw allow from 192.168.0.0/16 to any port 9090  # Prometheus

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 3. Fail2Ban Configuration

```bash
# Create local jail configuration
sudo nano /etc/fail2ban/jail.local
```

**Fail2Ban Configuration (`/etc/fail2ban/jail.local`):**
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-dos]
enabled = true
filter = nginx-dos
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 240
findtime = 60
bantime = 600
```

```bash
# Start and enable Fail2Ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status
```

### 4. System Auditing

```bash
# Configure auditd
sudo nano /etc/audit/rules.d/audit.rules
```

**Audit Rules (`/etc/audit/rules.d/audit.rules`):**
```
# Remove any existing rules
-D

# Buffer size
-b 8192

# Ignore current working directory records
-a always,exclude -F msgtype=CWD

# Monitor authentication events
-w /etc/passwd -p wa -k passwd_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/group -p wa -k group_changes
-w /etc/sudoers -p wa -k sudoers_changes

# Monitor network configuration
-w /etc/network/ -p wa -k network_changes

# Monitor SSH configuration
-w /etc/ssh/sshd_config -p wa -k ssh_config_changes

# Monitor Docker events
-w /usr/bin/docker -p x -k docker_exec
-w /var/lib/docker/ -p wa -k docker_changes

# Monitor critical system files
-w /etc/crontab -p wa -k cron_changes
-w /bin/su -p x -k su_usage
-w /usr/bin/sudo -p x -k sudo_usage

# Lock configuration
-e 2
```

```bash
# Restart auditd
sudo systemctl restart auditd

# Check audit status
sudo auditctl -s
```

### 5. File Integrity Monitoring

```bash
# Initialize AIDE database
sudo aideinit

# Move database to proper location
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Create daily AIDE check script
sudo nano /etc/cron.daily/aide-check
```

**AIDE Check Script (`/etc/cron.daily/aide-check`):**
```bash
#!/bin/bash
/usr/bin/aide --check | /usr/bin/mail -s "AIDE Report - $(hostname)" admin@your-domain.com
```

```bash
# Make script executable
sudo chmod +x /etc/cron.daily/aide-check
```

### 6. Kernel Hardening

```bash
# Create sysctl security configuration
sudo nano /etc/sysctl.d/99-security.conf
```

**Sysctl Security Configuration (`/etc/sysctl.d/99-security.conf`):**
```
# IP Spoofing protection
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.rp_filter = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_all = 1

# Ignore Directed pings
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Ignore ICMP redirects from non-GW hosts
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0

# Log martian packets
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# TCP SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Control buffer overflow attacks
kernel.exec-shield = 1
kernel.randomize_va_space = 2

# Reboot on kernel panic
kernel.panic = 10
```

```bash
# Apply sysctl settings
sudo sysctl -p /etc/sysctl.d/99-security.conf
```

## Docker Installation

### 1. Install Docker Engine

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt update

# Install Docker Engine
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
docker compose version
```

### 2. Docker Security Configuration

```bash
# Create Docker daemon configuration
sudo nano /etc/docker/daemon.json
```

**Docker Daemon Configuration (`/etc/docker/daemon.json`):**
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp.json",
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "live-restore": true,
  "experimental": false
}
```

```bash
# Restart Docker
sudo systemctl restart docker

# Verify configuration
sudo docker info
```

## SSL Certificate Setup

### 1. Self-Signed Certificate (Development/Testing)

```bash
# Create SSL directory
sudo mkdir -p /opt/noctis/ssl

# Generate private key
sudo openssl genrsa -out /opt/noctis/ssl/key.pem 4096

# Generate certificate signing request
sudo openssl req -new -key /opt/noctis/ssl/key.pem -out /opt/noctis/ssl/csr.pem

# Generate self-signed certificate
sudo openssl x509 -req -days 365 -in /opt/noctis/ssl/csr.pem -signkey /opt/noctis/ssl/key.pem -out /opt/noctis/ssl/cert.pem

# Set proper permissions
sudo chmod 600 /opt/noctis/ssl/key.pem
sudo chmod 644 /opt/noctis/ssl/cert.pem
sudo chown -R root:root /opt/noctis/ssl
```

### 2. Let's Encrypt Certificate (Production)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Set up automatic renewal
sudo crontab -e
# Add line: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Application Deployment

### 1. Clone and Setup Application

```bash
# Create application directory
sudo mkdir -p /opt/noctis
sudo chown $USER:$USER /opt/noctis

# Clone repository
cd /opt/noctis
git clone https://github.com/your-repo/noctis-dicom-viewer.git .

# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env
```

### 2. Generate Strong Passwords

```bash
# Generate strong passwords
echo "SECRET_KEY=$(openssl rand -base64 64)"
echo "DB_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo "DJANGO_SUPERUSER_PASSWORD=$(openssl rand -base64 16)"
echo "GRAFANA_PASSWORD=$(openssl rand -base64 16)"
```

### 3. Setup SSL Certificates for Docker

```bash
# Copy certificates to Docker directory
sudo cp /opt/noctis/ssl/cert.pem /opt/noctis/docker/ssl/
sudo cp /opt/noctis/ssl/key.pem /opt/noctis/docker/ssl/
sudo chmod 644 /opt/noctis/docker/ssl/cert.pem
sudo chmod 600 /opt/noctis/docker/ssl/key.pem
```

### 4. Deploy Application

```bash
# Build and start services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Check health
docker compose exec app python manage.py check --settings=noctisview.settings_production
```

## Monitoring and Maintenance

### 1. System Monitoring Setup

```bash
# Create monitoring script
sudo nano /usr/local/bin/system-monitor.sh
```

**System Monitor Script (`/usr/local/bin/system-monitor.sh`):**
```bash
#!/bin/bash

# System monitoring script
LOGFILE="/var/log/system-monitor.log"
THRESHOLD_CPU=80
THRESHOLD_MEM=85
THRESHOLD_DISK=90

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOGFILE
}

# Check CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d',' -f1)
if (( $(echo "$CPU_USAGE > $THRESHOLD_CPU" | bc -l) )); then
    log_message "WARNING: High CPU usage: ${CPU_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')
if (( $(echo "$MEM_USAGE > $THRESHOLD_MEM" | bc -l) )); then
    log_message "WARNING: High memory usage: ${MEM_USAGE}%"
fi

# Check disk usage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
if [ $DISK_USAGE -gt $THRESHOLD_DISK ]; then
    log_message "WARNING: High disk usage: ${DISK_USAGE}%"
fi

# Check Docker containers
FAILED_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "status=dead" --format "table {{.Names}}")
if [ -n "$FAILED_CONTAINERS" ]; then
    log_message "WARNING: Failed containers detected: $FAILED_CONTAINERS"
fi

# Check service status
systemctl is-active --quiet docker || log_message "ERROR: Docker service is not running"
systemctl is-active --quiet fail2ban || log_message "ERROR: Fail2Ban service is not running"
systemctl is-active --quiet ufw || log_message "ERROR: UFW service is not running"
```

```bash
# Make script executable
sudo chmod +x /usr/local/bin/system-monitor.sh

# Add to crontab for regular monitoring
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/system-monitor.sh") | crontab -
```

### 2. Log Rotation

```bash
# Create logrotate configuration for Noctis
sudo nano /etc/logrotate.d/noctis
```

**Logrotate Configuration (`/etc/logrotate.d/noctis`):**
```
/opt/noctis/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 noctis noctis
    postrotate
        docker compose -f /opt/noctis/docker-compose.yml restart app
    endscript
}

/var/log/system-monitor.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create 644 root root
}
```

## Backup Strategy

### 1. Database Backup Script

```bash
# Create backup script
sudo nano /usr/local/bin/backup-noctis.sh
```

**Backup Script (`/usr/local/bin/backup-noctis.sh`):**
```bash
#!/bin/bash

# Noctis backup script
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
docker compose -f /opt/noctis/docker-compose.yml exec -T db pg_dump -U noctis noctis | gzip > $BACKUP_DIR/noctis_db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/noctis_media_$DATE.tar.gz -C /opt/noctis/media .

# Configuration backup
tar -czf $BACKUP_DIR/noctis_config_$DATE.tar.gz -C /opt/noctis docker/ .env

# Remove old backups
find $BACKUP_DIR -name "noctis_*" -type f -mtime +$RETENTION_DAYS -delete

# Log backup completion
echo "$(date): Backup completed - DB: noctis_db_$DATE.sql.gz, Media: noctis_media_$DATE.tar.gz" >> /var/log/backup.log
```

```bash
# Make script executable
sudo chmod +x /usr/local/bin/backup-noctis.sh

# Add to crontab for daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-noctis.sh") | crontab -
```

### 2. System Backup

```bash
# Create system backup script
sudo nano /usr/local/bin/system-backup.sh
```

**System Backup Script (`/usr/local/bin/system-backup.sh`):**
```bash
#!/bin/bash

# System configuration backup
BACKUP_DIR="/opt/backups/system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup important system configurations
tar -czf $BACKUP_DIR/system_config_$DATE.tar.gz \
    /etc/ssh/ \
    /etc/ufw/ \
    /etc/fail2ban/ \
    /etc/audit/ \
    /etc/docker/ \
    /etc/nginx/ \
    /etc/crontab \
    /etc/fstab \
    /etc/hosts \
    /etc/hostname \
    /etc/netplan/ \
    /etc/systemd/system/ \
    /etc/sysctl.d/ \
    /home/*/.*rc \
    /home/*/.ssh/

# Remove old system backups (keep 7 days)
find $BACKUP_DIR -name "system_config_*" -type f -mtime +7 -delete

echo "$(date): System backup completed - system_config_$DATE.tar.gz" >> /var/log/backup.log
```

```bash
# Make script executable
sudo chmod +x /usr/local/bin/system-backup.sh

# Add to crontab for weekly system backups
(crontab -l 2>/dev/null; echo "0 3 * * 0 /usr/local/bin/system-backup.sh") | crontab -
```

## Security Checklist

### Daily Tasks
- [ ] Review system logs (`journalctl -f`)
- [ ] Check failed login attempts (`sudo fail2ban-client status sshd`)
- [ ] Monitor system resources (`htop`, `df -h`)
- [ ] Verify backup completion (`tail /var/log/backup.log`)

### Weekly Tasks
- [ ] Update system packages (`sudo apt update && sudo apt upgrade`)
- [ ] Review security logs (`sudo grep -i "fail\|error\|attack" /var/log/auth.log`)
- [ ] Check AIDE integrity (`sudo aide --check`)
- [ ] Review firewall logs (`sudo ufw status verbose`)

### Monthly Tasks
- [ ] Update Docker images (`docker compose pull && docker compose up -d`)
- [ ] Review user accounts (`cat /etc/passwd`)
- [ ] Check for rootkits (`sudo rkhunter --check`)
- [ ] Audit system configurations
- [ ] Test backup restoration procedure

### Emergency Procedures

**If System is Compromised:**
1. Disconnect from network immediately
2. Preserve evidence (memory dump, logs)
3. Analyze compromise using AIDE and audit logs
4. Rebuild system from clean backup
5. Implement additional security measures
6. Document incident and lessons learned

**Service Recovery:**
```bash
# Stop all services
docker compose down

# Check system integrity
sudo aide --check

# Restore from backup if needed
/usr/local/bin/backup-noctis.sh restore

# Start services
docker compose up -d

# Verify functionality
docker compose ps
curl -k https://localhost/health/
```

This guide provides a comprehensive foundation for deploying the Noctis DICOM Viewer on a secure Ubuntu Server. Remember to customize configurations based on your specific requirements and regularly update security measures to address new threats.