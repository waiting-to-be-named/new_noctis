# Noctis DICOM Viewer - Production Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- 10GB+ disk space for DICOM files
- Linux/Unix system (Ubuntu 20.04+ recommended)

### One-Command Deployment
```bash
chmod +x deploy.sh
./deploy.sh
```

## 📋 System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Network**: 100Mbps

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 100GB+ SSD
- **Network**: 1Gbps

## 🔧 Installation Options

### Option 1: Docker Compose (Recommended)
```bash
# Clone repository
git clone <repository-url>
cd noctis-dicom-viewer

# Deploy
./deploy.sh
```

### Option 2: Manual Installation
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-dev python3.11-venv
sudo apt-get install -y postgresql postgresql-contrib redis-server nginx

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements_production.txt

# Configure database
sudo -u postgres createdb noctis_dicom
sudo -u postgres createuser noctis_user

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start services
sudo systemctl start redis
sudo systemctl enable redis
gunicorn --config gunicorn.conf.py noctisview.wsgi:application
```

## 🌐 Configuration

### Environment Variables
Create a `.env` file in the project root:

```bash
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=noctis_dicom
DB_USER=noctis_user
DB_PASSWORD=your-secure-password

# Redis
REDIS_URL=redis://localhost:6379/1

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

### SSL/TLS Configuration
For production, configure SSL certificates:

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔒 Security Checklist

### Essential Security Measures
- [ ] Change default admin password
- [ ] Update Django secret key
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable HTTPS redirect
- [ ] Configure proper file permissions
- [ ] Set up backup strategy
- [ ] Monitor system resources

### Firewall Configuration
```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block other ports
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Enable firewall
sudo ufw enable
```

## 📊 Monitoring and Logging

### Health Checks
```bash
# Application health
curl http://your-domain.com/health/

# Service status
docker-compose ps

# Log monitoring
docker-compose logs -f web
```

### Performance Monitoring
```bash
# System resources
htop
df -h
free -h

# Application metrics
docker stats
```

## 🔄 Backup Strategy

### Database Backup
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker-compose exec db pg_dump -U noctis_user noctis_dicom > $BACKUP_DIR/db_$DATE.sql

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup.sh
```

### Automated Backups
```bash
# Add to crontab
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Upload Not Working
```bash
# Check file permissions
ls -la media/
chmod 755 media/dicom_files media/temp media/bulk_uploads

# Check upload limits
docker-compose logs web | grep "upload"
```

#### 2. Database Connection Issues
```bash
# Check database status
docker-compose exec db psql -U noctis_user -d noctis_dicom -c "SELECT 1;"

# Restart database
docker-compose restart db
```

#### 3. Memory Issues
```bash
# Check memory usage
docker stats

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Performance Issues
```bash
# Optimize database
docker-compose exec db psql -U noctis_user -d noctis_dicom -c "VACUUM ANALYZE;"

# Clear cache
docker-compose exec redis redis-cli FLUSHALL
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale web workers
docker-compose up -d --scale web=3

# Load balancer configuration
# Add nginx load balancer configuration
```

### Vertical Scaling
- Increase Docker memory limits
- Add more CPU cores
- Upgrade to SSD storage
- Increase database connections

## 🔧 Maintenance

### Regular Maintenance Tasks
```bash
# Weekly
docker-compose exec db psql -U noctis_user -d noctis_dicom -c "VACUUM ANALYZE;"
docker-compose exec redis redis-cli FLUSHALL

# Monthly
docker system prune -f
docker image prune -f

# Quarterly
Update system packages
Review security patches
Test backup restoration
```

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate
```

## 📞 Support

### Log Locations
- Application logs: `logs/django.log`
- Nginx logs: `/var/log/nginx/`
- Docker logs: `docker-compose logs`
- System logs: `/var/log/syslog`

### Contact Information
- Documentation: [GitHub Wiki]
- Issues: [GitHub Issues]
- Email: support@noctis-dicom.com

## 📚 Additional Resources

- [Django Production Deployment](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [PostgreSQL Tuning](https://www.postgresql.org/docs/current/runtime-config.html)