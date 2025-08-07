# 🚀 NOCTIS DICOM System - Quick Deployment for Ubuntu 18.04

## ⚡ One-Command Deployment

### Prerequisites
- Ubuntu 18.04 LTS VM
- Domain name pointing to your server
- Non-root user with sudo privileges

### Deployment Command
```bash
wget -O deploy.sh https://your-repo-url/deploy_ubuntu_secure.sh && chmod +x deploy.sh && ./deploy.sh your-domain.com admin@your-domain.com
```

Or clone and run:
```bash
git clone https://your-repo-url.git noctis-dicom
cd noctis-dicom
chmod +x deploy_ubuntu_secure.sh
./deploy_ubuntu_secure.sh your-domain.com admin@your-domain.com
```

## 🔐 What Gets Deployed

### Security Features (Enterprise-Grade)
- ✅ **UFW Firewall** - Blocks all unnecessary ports
- ✅ **SSL/HTTPS** - Let's Encrypt certificates
- ✅ **Fail2Ban** - Intrusion prevention system
- ✅ **Rate Limiting** - DDoS protection
- ✅ **Database Encryption** - PostgreSQL with SSL
- ✅ **Security Headers** - HSTS, CSP, XSS protection
- ✅ **Automated Backups** - Daily encrypted backups
- ✅ **Audit Logging** - Complete activity tracking
- ✅ **AIDE** - File integrity monitoring
- ✅ **Session Security** - 1-hour timeouts, secure cookies

### Application Stack
- **Web Server**: Nginx (reverse proxy)
- **Application Server**: Gunicorn
- **Database**: PostgreSQL with encryption
- **Cache/Queue**: Redis
- **Process Manager**: Supervisor
- **Background Tasks**: Celery

### HIPAA Compliance Features
- 🏥 **Access Controls** - Role-based permissions
- 🏥 **Audit Trails** - Complete user activity logs
- 🏥 **Data Encryption** - At rest and in transit
- 🏥 **Secure Authentication** - Session management
- 🏥 **Data Integrity** - Cryptographic checksums

## 📋 Post-Deployment Checklist

### 1. Verify SSL Certificate
```bash
curl -I https://your-domain.com
```

### 2. Test Login
- Visit `https://your-domain.com`
- Login with created admin account

### 3. Check Security Status
```bash
sudo ufw status
sudo systemctl status fail2ban
sudo systemctl status postgresql nginx redis-server
```

### 4. Test DICOM Upload
- Upload a sample DICOM file
- Verify viewer functionality

## 🛡️ Security Credentials

**IMPORTANT**: Save these securely after deployment!

- **Database Password**: Generated automatically (saved in `/etc/noctis/credentials.env`)
- **Django Secret Key**: Generated automatically
- **Admin Account**: Created during deployment
- **SSL Certificate**: Auto-renewed via Let's Encrypt

## 📞 Support

### System Logs
```bash
# Application logs
sudo tail -f /opt/noctis/logs/django.log

# Security logs
sudo tail -f /var/log/auth.log
sudo tail -f /var/log/fail2ban.log

# Web server logs
sudo tail -f /var/log/nginx/error.log
```

### Emergency Commands
```bash
# Restart services
sudo systemctl restart nginx postgresql redis-server supervisor

# Check service status
sudo systemctl status nginx postgresql redis-server supervisor

# View deployment report
cat /opt/noctis/DEPLOYMENT_REPORT.txt
```

## 🚨 Security Alerts

### Immediate Actions Required
1. **Change Default Passwords** - Update admin account password
2. **Configure Monitoring** - Set up log monitoring alerts
3. **Backup Testing** - Test backup restoration procedure
4. **Network Security** - Configure VPN access if needed
5. **Staff Training** - Train users on security procedures

### Regular Maintenance
- **Daily**: Review security logs
- **Weekly**: Apply security updates
- **Monthly**: Security audit and vulnerability scan

---

## 📊 System Architecture

```
Internet → [UFW Firewall] → [Nginx + SSL] → [Gunicorn] → [Django App]
                                            ↓
                           [PostgreSQL] ← [Redis] → [Celery Workers]
                                ↓
                           [Encrypted Storage]
```

## 🔧 Configuration Files

- **Nginx**: `/etc/nginx/sites-available/noctis`
- **Gunicorn**: `/etc/noctis/gunicorn.conf.py`
- **Supervisor**: `/etc/supervisor/conf.d/noctis_*.conf`
- **Application**: `/opt/noctis/app/noctisview/production_settings.py`
- **Credentials**: `/etc/noctis/credentials.env` (root only)

---

**⚠️ CRITICAL SECURITY NOTICE**
This system handles patient medical data. Ensure compliance with local healthcare regulations (HIPAA, GDPR, etc.) and implement appropriate business associate agreements.

**Deployment Time**: ~30-45 minutes
**System Status**: Production-Ready with Enterprise Security
**HIPAA Compliance**: Technical Safeguards Implemented