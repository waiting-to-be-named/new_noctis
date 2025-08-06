# Noctis PACS Production Deployment Checklist

## Pre-Deployment
- [ ] Ubuntu Server 24.04 LTS installed
- [ ] Domain name configured and pointing to server IP
- [ ] SSH access configured
- [ ] Minimum 100GB storage available
- [ ] Backup of any existing data

## Deployment Steps

### 1. Initial Setup
- [ ] Update system: `sudo apt update && sudo apt upgrade -y`
- [ ] Set hostname: `sudo hostnamectl set-hostname pacs.yourdomain.com`
- [ ] Configure timezone: `sudo timedatectl set-timezone UTC`

### 2. Run Deployment Scripts
- [ ] Clone repository to `/tmp`
- [ ] Run: `sudo bash deploy_ubuntu_production.sh`
- [ ] Enter domain name when prompted
- [ ] Enter admin email when prompted
- [ ] Enter database password when prompted

### 3. Configure Environment
- [ ] Copy `.env.production.template` to `.env`
- [ ] Generate SECRET_KEY
- [ ] Update ALLOWED_HOSTS
- [ ] Configure email settings
- [ ] Set CSRF_TRUSTED_ORIGINS

### 4. Set Up Web Server
- [ ] Copy Nginx configuration to `/etc/nginx/sites-available/`
- [ ] Update domain placeholders in Nginx config
- [ ] Enable site and remove default
- [ ] Test Nginx configuration

### 5. SSL/TLS Setup
- [ ] Run: `sudo bash setup_ssl.sh yourdomain.com admin@yourdomain.com`
- [ ] Verify certificate installation
- [ ] Test automatic renewal

### 6. Install Services
- [ ] Copy systemd service files
- [ ] Enable all services (gunicorn, celery, celerybeat)
- [ ] Set proper permissions

### 7. Django Setup
- [ ] Activate virtual environment
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Collect static files: `python manage.py collectstatic`

### 8. Start Services
- [ ] Start gunicorn: `sudo systemctl start gunicorn`
- [ ] Start celery: `sudo systemctl start celery`
- [ ] Start celerybeat: `sudo systemctl start celerybeat`
- [ ] Restart nginx: `sudo systemctl restart nginx`

## Post-Deployment Verification

### Functionality Tests
- [ ] Access site via HTTPS
- [ ] Login to admin interface
- [ ] Create test facility
- [ ] Create test users
- [ ] Upload test DICOM file
- [ ] View uploaded DICOM in viewer
- [ ] Test measurement tools
- [ ] Test report generation

### Security Checks
- [ ] SSL certificate valid
- [ ] Firewall rules active
- [ ] fail2ban running
- [ ] File permissions correct
- [ ] Database access restricted

### Monitoring Setup
- [ ] Backup script scheduled
- [ ] Monitoring script running
- [ ] Log rotation configured
- [ ] Health endpoint accessible

## Final Steps
- [ ] Document any custom configurations
- [ ] Set up external monitoring
- [ ] Configure email alerts
- [ ] Train initial users
- [ ] Schedule first backup test

## Emergency Contacts
- System Administrator: _______________
- Database Administrator: _____________
- Network Administrator: ______________
- Development Team: __________________

## Important URLs
- Production Site: https://___________
- Admin Interface: https://___________/admin/
- Health Check: https://___________/health/
- Documentation: /workspace/PRODUCTION_DEPLOYMENT_GUIDE.md