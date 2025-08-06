# Noctis PACS Production Deployment Guide for Ubuntu Server 24.04

This guide provides step-by-step instructions for deploying Noctis PACS on Ubuntu Server 24.04 in a production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Requirements](#server-requirements)
3. [Initial Server Setup](#initial-server-setup)
4. [Deployment Process](#deployment-process)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Security Hardening](#security-hardening)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)
10. [Performance Tuning](#performance-tuning)

## Prerequisites

Before starting the deployment, ensure you have:

- Ubuntu Server 24.04 LTS installed
- Root or sudo access to the server
- A registered domain name pointing to your server's IP
- At least 50GB of available storage for DICOM files
- SSL certificate (will be obtained via Let's Encrypt)
- SMTP server credentials for email notifications

## Server Requirements

### Minimum Requirements
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD (50GB for OS and applications, 50GB for DICOM storage)
- Network: 100 Mbps

### Recommended Requirements
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 500GB+ SSD (RAID configuration recommended)
- Network: 1 Gbps

### Port Requirements
- 22 (SSH)
- 80 (HTTP - redirects to HTTPS)
- 443 (HTTPS)
- 104 (DICOM)

## Initial Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 2. Set Hostname

```bash
sudo hostnamectl set-hostname pacs.yourdomain.com
sudo nano /etc/hosts
# Add: 127.0.0.1 pacs.yourdomain.com
```

### 3. Configure Timezone

```bash
sudo timedatectl set-timezone UTC
```

## Deployment Process

### 1. Clone Repository

```bash
cd /tmp
git clone https://github.com/your-org/noctis-pacs.git
cd noctis-pacs
```

### 2. Run Base Deployment Script

```bash
sudo bash deploy_ubuntu_production.sh
```

This script will:
- Install all system dependencies
- Set up PostgreSQL database
- Configure firewall rules
- Create application user and directories
- Install Python dependencies
- Set up backup and monitoring scripts

### 3. Configure Environment Variables

```bash
cd /opt/noctis
sudo cp .env.production.template .env
sudo nano .env
```

Update the following values:
- `SECRET_KEY`: Generate a secure key using `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `ALLOWED_HOSTS`: Your domain name
- `DB_PASSWORD`: Database password you set during deployment
- `EMAIL_*`: SMTP configuration
- `CSRF_TRUSTED_ORIGINS`: https://yourdomain.com

### 4. Set Up Nginx

```bash
# Copy Nginx configuration
sudo cp nginx_noctis.conf /etc/nginx/sites-available/noctis

# Update domain name placeholder
sudo sed -i 's/DOMAIN_NAME_PLACEHOLDER/yourdomain.com/g' /etc/nginx/sites-available/noctis

# Enable the site
sudo ln -s /etc/nginx/sites-available/noctis /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t
```

### 5. Set Up SSL/TLS

```bash
sudo bash setup_ssl.sh yourdomain.com admin@yourdomain.com
```

### 6. Set Up Systemd Services

```bash
# Copy service files
sudo cp gunicorn.socket /etc/systemd/system/
sudo cp gunicorn.service /etc/systemd/system/
sudo cp celery.service /etc/systemd/system/
sudo cp celerybeat.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable gunicorn.socket
sudo systemctl enable gunicorn.service
sudo systemctl enable celery.service
sudo systemctl enable celerybeat.service
```

### 7. Run Django Migrations

```bash
cd /opt/noctis
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=noctisview.settings_production

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 8. Start Services

```bash
# Start all services
sudo systemctl start gunicorn.socket
sudo systemctl start gunicorn.service
sudo systemctl start celery.service
sudo systemctl start celerybeat.service
sudo systemctl restart nginx

# Check status
sudo systemctl status gunicorn
sudo systemctl status celery
sudo systemctl status nginx
```

## Post-Deployment Configuration

### 1. Create Initial Facilities

Access the Django admin at `https://yourdomain.com/admin/` and create:
- Facilities
- User accounts for radiologists and staff
- Configure user permissions

### 2. Test DICOM Upload

```bash
# Test the upload functionality
cd /opt/noctis
source venv/bin/activate
python test_upload_endpoint.py
```

### 3. Configure DICOM Server (Optional)

If you want to receive DICOM files directly from modalities:

```bash
# Edit the DICOM server configuration
sudo nano /opt/noctis/enhanced_scp_server.py

# Create a systemd service for DICOM server
sudo nano /etc/systemd/system/dicom-server.service
```

Add the following content:

```ini
[Unit]
Description=Noctis DICOM Server
After=network.target postgresql.service

[Service]
Type=simple
User=noctis
Group=noctis
WorkingDirectory=/opt/noctis
Environment="PATH=/opt/noctis/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=noctisview.settings_production"
ExecStart=/opt/noctis/venv/bin/python enhanced_scp_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable dicom-server
sudo systemctl start dicom-server
```

## Security Hardening

### 1. Configure Fail2ban

The deployment script already configured basic fail2ban. For additional security:

```bash
sudo nano /etc/fail2ban/jail.local
```

Add custom jails for Django:

```ini
[django-auth]
enabled = true
filter = django-auth
logpath = /var/log/noctis/django.log
maxretry = 5
bantime = 3600

[nginx-noscript]
enabled = true
```

### 2. Set Up Application Firewall

```bash
# Install ModSecurity for Nginx
sudo apt install nginx-module-security

# Configure ModSecurity rules
sudo nano /etc/nginx/modsec/modsecurity.conf
```

### 3. Database Security

```bash
# Restrict PostgreSQL connections
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add:
local   all             all                                     peer
host    noctis_db       noctis_user     127.0.0.1/32           md5
```

### 4. File Permissions

```bash
# Secure sensitive files
sudo chmod 600 /opt/noctis/.env
sudo chmod 600 /etc/systemd/system/gunicorn.service
sudo chmod 600 /etc/nginx/sites-available/noctis
```

## Monitoring and Maintenance

### 1. Log Monitoring

Monitor logs regularly:

```bash
# Application logs
sudo tail -f /var/log/noctis/django.log
sudo tail -f /var/log/noctis/gunicorn.log

# System logs
sudo journalctl -u gunicorn -f
sudo journalctl -u celery -f
```

### 2. Performance Monitoring

The deployment script created monitoring scripts. Check their output:

```bash
# View monitoring logs
sudo cat /var/log/noctis/monitor.log

# Check disk usage
df -h
du -sh /var/www/noctis/media/dicom_files/

# Monitor PostgreSQL
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### 3. Health Checks

Set up external monitoring:

```bash
# Create health check endpoint
curl https://yourdomain.com/health/
```

## Troubleshooting

### Common Issues

#### 1. 502 Bad Gateway

```bash
# Check Gunicorn
sudo systemctl status gunicorn
sudo journalctl -u gunicorn -n 50

# Check socket file
ls -la /run/gunicorn.sock

# Restart services
sudo systemctl restart gunicorn
```

#### 2. Static Files Not Loading

```bash
# Recollect static files
cd /opt/noctis
source venv/bin/activate
python manage.py collectstatic --noinput

# Check permissions
ls -la /var/www/noctis/static/
```

#### 3. Database Connection Errors

```bash
# Check PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -l

# Test connection
cd /opt/noctis
source venv/bin/activate
python manage.py dbshell
```

#### 4. DICOM Upload Issues

```bash
# Check file permissions
ls -la /var/www/noctis/media/dicom_files/

# Check disk space
df -h

# Review upload logs
grep -i error /var/log/noctis/django.log
```

## Backup and Recovery

### Automated Backups

The deployment script set up daily backups at 2 AM. To manually backup:

```bash
sudo /usr/local/bin/noctis-backup.sh
```

### Restore from Backup

```bash
# Stop services
sudo systemctl stop gunicorn celery

# Restore database
cd /var/backups/noctis/YYYYMMDD_HHMMSS/
gunzip -c database.sql.gz | sudo -u postgres psql noctis_db

# Restore media files
sudo tar -xzf media.tar.gz -C /var/www/noctis/media/

# Restore code (if needed)
sudo tar -xzf code.tar.gz -C /opt/noctis/

# Start services
sudo systemctl start gunicorn celery
```

## Performance Tuning

### 1. PostgreSQL Optimization

Edit `/etc/postgresql/*/main/postgresql.conf`:

```ini
# Adjust based on available RAM
shared_buffers = 25% of RAM
effective_cache_size = 75% of RAM
work_mem = RAM / max_connections / 4
maintenance_work_mem = RAM / 16
```

### 2. Gunicorn Workers

Adjust in `/etc/systemd/system/gunicorn.service`:

```bash
# Workers = (2 × CPU cores) + 1
--workers 9  # For 4-core system
```

### 3. Nginx Optimization

Edit `/etc/nginx/nginx.conf`:

```nginx
worker_processes auto;
worker_connections 2048;
use epoll;
multi_accept on;
```

### 4. Redis Optimization

Edit `/etc/redis/redis.conf`:

```ini
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Maintenance Schedule

### Daily
- Monitor logs for errors
- Check disk usage
- Verify backup completion

### Weekly
- Review performance metrics
- Check for security updates
- Test backup restoration (on staging)

### Monthly
- Update system packages
- Review and rotate logs
- Audit user access
- Performance analysis

### Quarterly
- Security audit
- Database optimization
- Capacity planning
- Disaster recovery drill

## Support and Documentation

For additional support:

1. Check application logs in `/var/log/noctis/`
2. Review Django debug information (if enabled)
3. Consult the README.md for feature documentation
4. Contact the development team for critical issues

## Important Commands Reference

```bash
# Service Management
sudo systemctl start/stop/restart gunicorn
sudo systemctl start/stop/restart celery
sudo systemctl start/stop/restart nginx

# Log Viewing
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/noctis/django.log

# Django Management
cd /opt/noctis && source venv/bin/activate
python manage.py shell
python manage.py dbshell
python manage.py migrate
python manage.py collectstatic

# Backup
sudo /usr/local/bin/noctis-backup.sh

# SSL Certificate
sudo certbot renew --dry-run
sudo certbot certificates
```

## Conclusion

Your Noctis PACS system is now deployed and ready for production use. Remember to:

1. Regularly monitor system health
2. Keep backups current and tested
3. Apply security updates promptly
4. Document any customizations
5. Train users on proper system usage

For optimal performance and security, review this guide quarterly and update configurations as needed.