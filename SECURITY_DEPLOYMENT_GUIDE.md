# NOCTIS DICOM System - Secure Deployment Guide for Ubuntu 18.04

## 🛡️ HIPAA-Compliant Medical Imaging Platform Deployment

### Table of Contents
1. [Pre-Deployment Requirements](#pre-deployment-requirements)
2. [Quick Deployment](#quick-deployment)
3. [Security Features](#security-features)
4. [Post-Deployment Checklist](#post-deployment-checklist)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)
6. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Requirements

### System Requirements
- **OS**: Ubuntu 18.04 LTS (Virtual Machine recommended)
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: Minimum 50GB SSD, Recommended 100GB+
- **CPU**: Minimum 2 cores, Recommended 4+ cores
- **Network**: Static IP address with domain name

### Domain and SSL Requirements
- Registered domain name pointing to your server
- Valid email address for SSL certificate notifications
- Open ports: 80 (HTTP), 443 (HTTPS), 22 (SSH)

### Security Prerequisites
- Non-root user with sudo privileges
- SSH key-based authentication (recommended)
- VPN or secure network access for administration

---

## Quick Deployment

### Step 1: Prepare the Server
```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Create a non-root user (if not exists)
sudo adduser noctis-admin
sudo usermod -aG sudo noctis-admin

# Switch to the new user
su - noctis-admin
```

### Step 2: Download and Run Deployment Script
```bash
# Clone the repository
git clone <your-repo-url> noctis-dicom
cd noctis-dicom

# Make the deployment script executable
chmod +x deploy_ubuntu_secure.sh

# Run the deployment script
./deploy_ubuntu_secure.sh your-domain.com admin@your-domain.com
```

### Step 3: Follow Interactive Prompts
The script will prompt you to:
- Create a Django superuser account
- Confirm SSL certificate generation
- Review security settings

---

## Security Features

### 🔒 Enterprise-Level Security Implementation

#### Authentication & Authorization
- **Multi-factor Authentication**: Session-based with secure cookies
- **Role-based Access Control**: Admin, Radiologist, Technician roles
- **Session Management**: 1-hour timeout, secure session handling
- **Password Security**: Strong password requirements

#### Network Security
- **UFW Firewall**: Strict ingress/egress rules
- **Rate Limiting**: Login and API endpoint protection
- **DDoS Protection**: Nginx rate limiting and fail2ban
- **SSL/TLS**: Let's Encrypt certificates with HSTS

#### Data Protection
- **Database Encryption**: PostgreSQL with SSL connections
- **File Encryption**: DICOM images stored securely
- **Backup Encryption**: Automated encrypted backups
- **Audit Logging**: Comprehensive activity tracking

#### HIPAA Compliance Features
- **Access Controls**: Role-based patient data access
- **Audit Trails**: Complete user activity logging
- **Data Integrity**: Cryptographic checksums
- **Secure Transmission**: End-to-end encryption
- **Data Retention**: Configurable retention policies

### Security Headers Implemented
```nginx
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: [Restrictive CSP policy]
```

---

## Post-Deployment Checklist

### ✅ Immediate Security Verification

#### 1. SSL Certificate Verification
```bash
# Check SSL certificate
curl -I https://your-domain.com
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

#### 2. Firewall Status
```bash
sudo ufw status verbose
```

#### 3. Service Health Check
```bash
sudo systemctl status postgresql nginx redis-server supervisor
```

#### 4. Application Access Test
- Visit `https://your-domain.com`
- Verify login functionality
- Test DICOM upload
- Check viewer functionality

#### 5. Security Scan
```bash
# Run security scan
sudo rkhunter --check
sudo chkrootkit
```

### 🔧 Configuration Verification

#### Database Security
```bash
# Verify database encryption
sudo -u postgres psql -c "\l+"
sudo -u postgres psql noctis_dicom -c "SHOW ssl;"
```

#### Log Monitoring
```bash
# Check security logs
sudo tail -f /opt/noctis/logs/security.log
sudo tail -f /var/log/auth.log
sudo tail -f /var/log/fail2ban.log
```

---

## Monitoring and Maintenance

### Daily Monitoring Tasks
1. **Review Security Logs**
   ```bash
   sudo journalctl -u fail2ban -f
   sudo tail -f /opt/noctis/logs/django.log
   ```

2. **Check System Resources**
   ```bash
   htop
   df -h
   free -h
   ```

3. **Verify Backup Status**
   ```bash
   ls -la /opt/noctis/backups/
   tail /opt/noctis/logs/backup.log
   ```

### Weekly Maintenance Tasks
1. **Security Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo reboot
   ```

2. **Security Scan**
   ```bash
   sudo aide --check
   sudo freshclam && sudo clamscan -r /opt/noctis/
   ```

3. **Log Rotation Verification**
   ```bash
   sudo logrotate -d /etc/logrotate.d/noctis-logs
   ```

### Monthly Security Reviews
1. **Access Control Audit**
   - Review user accounts and permissions
   - Check failed login attempts
   - Verify role assignments

2. **Vulnerability Assessment**
   - Update all software packages
   - Review security advisories
   - Test backup and recovery procedures

3. **Performance Optimization**
   - Analyze system performance
   - Clean up old logs and temporary files
   - Optimize database queries

---

## Emergency Procedures

### Security Incident Response
1. **Immediate Actions**
   ```bash
   # Block suspicious IPs
   sudo ufw deny from <suspicious-ip>
   
   # Check active connections
   sudo netstat -an | grep ESTABLISHED
   
   # Review recent logins
   sudo last -n 20
   ```

2. **System Isolation**
   ```bash
   # Temporary network isolation
   sudo ufw default deny incoming
   sudo ufw default deny outgoing
   ```

3. **Forensic Data Collection**
   ```bash
   # Create system snapshot
   sudo tar -czf /tmp/emergency-logs-$(date +%Y%m%d).tar.gz /opt/noctis/logs/ /var/log/
   ```

### Disaster Recovery
1. **Database Restoration**
   ```bash
   # Stop services
   sudo supervisorctl stop all
   
   # Restore database
   sudo -u postgres dropdb noctis_dicom
   sudo -u postgres createdb noctis_dicom
   gunzip -c /opt/noctis/backups/latest_backup.sql.gz | sudo -u postgres psql noctis_dicom
   
   # Restart services
   sudo supervisorctl start all
   ```

2. **Media Files Restoration**
   ```bash
   # Restore media files
   cd /opt/noctis/
   tar -xzf backups/latest_media_backup.tar.gz
   sudo chown -R noctis:noctis media/
   ```

---

## Troubleshooting

### Common Issues and Solutions

#### SSL Certificate Issues
```bash
# Renew SSL certificate
sudo certbot renew --nginx

# Check certificate expiry
sudo certbot certificates
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql noctis_dicom -c "SELECT version();"
```

#### Application Performance Issues
```bash
# Check Gunicorn processes
sudo supervisorctl status noctis_gunicorn

# Monitor system resources
sudo iotop
sudo nethogs
```

#### Upload Issues
```bash
# Check disk space
df -h /opt/noctis/

# Verify file permissions
ls -la /opt/noctis/media/

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Log File Locations
- **Application Logs**: `/opt/noctis/logs/`
- **Nginx Logs**: `/var/log/nginx/`
- **System Logs**: `/var/log/syslog`
- **Security Logs**: `/var/log/auth.log`
- **Fail2Ban Logs**: `/var/log/fail2ban.log`

---

## Support and Documentation

### Contact Information
- **System Administrator**: admin@your-domain.com
- **Emergency Contact**: [Emergency contact information]
- **Documentation**: `/opt/noctis/DEPLOYMENT_REPORT.txt`

### Additional Resources
- [HIPAA Compliance Guidelines](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [Nginx Security Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)

---

**⚠️ IMPORTANT SECURITY NOTICE**
This deployment includes enterprise-level security measures for protecting patient data. Ensure all staff are trained on security procedures and regularly review access controls and audit logs.

**🔐 HIPAA COMPLIANCE**
This system implements technical safeguards required for HIPAA compliance. Regular security assessments and staff training are required to maintain compliance.

---

*Last Updated: December 2024*
*Version: 1.0*