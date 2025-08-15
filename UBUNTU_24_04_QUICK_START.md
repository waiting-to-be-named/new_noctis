# NOCTIS DICOM Viewer - Ubuntu 24.04.2 Quick Start Guide

## 🚀 Quick Deployment Options

### Option 1: Automated Script (Recommended)
```bash
# Clone your repository to Ubuntu 24.04.2 server
git clone <your-repo-url>
cd <your-repo-directory>

# Run automated deployment
./deploy_ubuntu24.04.sh your-domain.com

# Or with custom passwords
./deploy_ubuntu24.04.sh your-domain.com your_db_password your_secret_key
```

### Option 2: Docker Compose
```bash
# Deploy with Docker Compose
docker-compose -f docker-compose.ubuntu24.04.yml up -d

# With custom environment
export DB_PASSWORD=your_secure_password
export SECRET_KEY=your_secret_key
export ALLOWED_HOSTS=your-domain.com
docker-compose -f docker-compose.ubuntu24.04.yml up -d
```

### Option 3: Manual Deployment
Follow the detailed guide in `UBUNTU_24_04_DEPLOYMENT.md`

## 📋 System Requirements

### Minimum Requirements
- **OS**: Ubuntu 24.04.2 LTS
- **CPU**: 4+ cores
- **RAM**: 16GB+
- **Storage**: 1TB+ SSD
- **Network**: 1Gbps+

### Recommended Production
- **CPU**: 8+ cores (AMD EPYC or Intel Xeon)
- **RAM**: 64GB+ ECC memory
- **Storage**: 2TB+ NVMe SSD with RAID 1
- **Network**: 10Gbps connection

## 🔧 Pre-Deployment Checklist

### Server Preparation
- [ ] Ubuntu 24.04.2 LTS installed
- [ ] System updated (`sudo apt update && sudo apt upgrade`)
- [ ] Domain name configured (DNS pointing to server)
- [ ] Firewall configured (SSH, HTTP, HTTPS, DICOM ports)
- [ ] SSL certificate ready (Let's Encrypt recommended)

### Application Preparation
- [ ] DICOM files ready for upload
- [ ] Database backup strategy planned
- [ ] Monitoring solution configured
- [ ] Backup storage allocated

## 🚀 Deployment Commands

### Quick Deploy
```bash
# 1. Clone repository
git clone <your-repo-url>
cd <your-repo-directory>

# 2. Run deployment script
./deploy_ubuntu24.04.sh your-domain.com

# 3. Create superuser
sudo -u noctis bash -c 'cd /opt/noctis && source venv/bin/activate && python manage.py createsuperuser'
```

### Docker Deploy
```bash
# 1. Install Docker and Docker Compose
sudo apt install docker.io docker-compose

# 2. Deploy with Docker Compose
docker-compose -f docker-compose.ubuntu24.04.yml up -d

# 3. Check status
docker-compose -f docker-compose.ubuntu24.04.yml ps
```

## 🔍 Post-Deployment Verification

### Health Checks
```bash
# Check application health
curl https://your-domain.com/health/

# Check services
sudo systemctl status noctis noctis-scp nginx postgresql redis-server

# Monitor system
/opt/noctis/monitor.sh
```

### Performance Tests
```bash
# Load test
ab -n 100 -c 10 https://your-domain.com/

# Upload test
curl -X POST -F "file=@test.dcm" https://your-domain.com/upload/
```

## 📊 Monitoring & Maintenance

### Daily Tasks
```bash
# Check logs
sudo journalctl -u noctis -f

# Monitor disk space
df -h

# Check service status
sudo systemctl status noctis
```

### Weekly Tasks
```bash
# Create backup
/opt/noctis/backup.sh

# Update system
sudo apt update && sudo apt upgrade

# Check SSL certificate
sudo certbot certificates
```

### Monthly Tasks
```bash
# Update Python packages
sudo -u noctis bash -c 'cd /opt/noctis && source venv/bin/activate && pip install --upgrade -r requirements.txt'

# Review logs
sudo logrotate -f /etc/logrotate.d/noctis

# Performance review
/opt/noctis/monitor.sh
```

## 🔧 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status noctis

# View logs
sudo journalctl -u noctis -f

# Check configuration
sudo nginx -t
```

#### Database Connection Issues
```bash
# Test database connection
psql -h localhost -U noctis_user -d noctis_db -c "SELECT version();"

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --dry-run
```

#### Performance Issues
```bash
# Check system resources
htop
iotop
df -h

# Monitor application
/opt/noctis/monitor.sh
```

## 📁 File Locations

### Application Files
- **Application**: `/opt/noctis/`
- **Logs**: `/opt/noctis/logs/`
- **Media**: `/opt/noctis/media/`
- **Static Files**: `/opt/noctis/staticfiles/`
- **Backups**: `/opt/noctis/backup/`

### Configuration Files
- **Environment**: `/opt/noctis/.env`
- **Nginx**: `/etc/nginx/sites-available/noctis`
- **Systemd**: `/etc/systemd/system/noctis.service`
- **PostgreSQL**: `/etc/postgresql/16/main/`
- **Redis**: `/etc/redis/redis.conf`

### Log Files
- **Application**: `/opt/noctis/logs/django.log`
- **Gunicorn**: `/opt/noctis/logs/gunicorn_*.log`
- **Nginx**: `/var/log/nginx/`
- **System**: `sudo journalctl -u noctis`

## 🔐 Security Checklist

### Essential Security
- [ ] Change default passwords
- [ ] Configure firewall (UFW)
- [ ] Enable automatic security updates
- [ ] Set up SSL/TLS certificates
- [ ] Configure fail2ban
- [ ] Regular security audits

### Advanced Security
- [ ] Set up intrusion detection
- [ ] Configure monitoring and alerting
- [ ] Implement backup encryption
- [ ] Set up VPN access
- [ ] Regular penetration testing

## 📈 Performance Optimization

### System Tuning
```bash
# Optimize for medical imaging
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_ratio=15' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Database Optimization
```bash
# PostgreSQL optimization for medical imaging
sudo -u postgres psql -c "ALTER SYSTEM SET shared_buffers = '1GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_cache_size = '4GB';"
sudo systemctl restart postgresql
```

### Application Optimization
```bash
# Enable Redis caching
# Configure Celery for background tasks
# Optimize static file serving
# Enable Gzip compression
```

## 🆘 Support Information

### Log Locations
- **Application Logs**: `/opt/noctis/logs/`
- **System Logs**: `sudo journalctl -u noctis`
- **Nginx Logs**: `/var/log/nginx/`
- **Database Logs**: `/var/log/postgresql/`

### Management Commands
```bash
# Restart application
sudo systemctl restart noctis

# View real-time logs
sudo journalctl -u noctis -f

# Monitor system
/opt/noctis/monitor.sh

# Create backup
/opt/noctis/backup.sh

# Update application
sudo -u noctis bash -c 'cd /opt/noctis && git pull && source venv/bin/activate && python manage.py migrate'
```

### Emergency Procedures
```bash
# Stop all services
sudo systemctl stop noctis noctis-scp nginx

# Start services
sudo systemctl start nginx postgresql redis-server noctis noctis-scp

# Emergency backup
pg_dump -U noctis_user -h localhost noctis_db > emergency_backup.sql
```

## 📞 Contact & Support

### Documentation
- **Detailed Guide**: `UBUNTU_24_04_DEPLOYMENT.md`
- **Docker Guide**: `docker-compose.ubuntu24.04.yml`
- **Dockerfile**: `Dockerfile.ubuntu24.04`

### Version Information
- **Ubuntu**: 24.04.2 LTS (Noble Numbat)
- **Python**: 3.12.x
- **PostgreSQL**: 16.x
- **Nginx**: 1.24.x
- **Redis**: 7.x

---

**Status**: ✅ Production Ready for Ubuntu 24.04.2 LTS
**Last Updated**: $(date)
**Version**: 1.0.0