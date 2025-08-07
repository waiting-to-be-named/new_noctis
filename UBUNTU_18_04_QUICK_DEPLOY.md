# Ubuntu 18.04 Quick Deployment Guide

**Created**: August 7, 2025  
**Purpose**: One-command deployment for Ubuntu 18.04 servers

## 🚀 Quick Start

### Prerequisites
- Fresh Ubuntu 18.04 server with root access
- Internet connection
- At least 8GB RAM and 500GB storage

### One-Command Deployment

```bash
# Download and run the automated deployment script
sudo ./automated_ubuntu_18_04_deployment.sh [your-domain.com]

# Example:
sudo ./automated_ubuntu_18_04_deployment.sh noctis.hospital.com
```

### What the Script Does Automatically

1. **System Updates**: Updates Ubuntu 18.04 packages
2. **Python 3.8 Installation**: Via deadsnakes PPA (required for Django 4.2.7)
3. **PostgreSQL 12 Setup**: Via official PostgreSQL repository
4. **System Dependencies**: Installs all required packages (Redis, Nginx, Supervisor, GDCM tools)
5. **Application Setup**: Creates user, directories, virtual environment
6. **Database Configuration**: Creates database, user, and saves credentials
7. **Django Setup**: Runs migrations, collects static files
8. **Web Server**: Configures Nginx with proper proxy settings
9. **Process Management**: Sets up Supervisor for Gunicorn and DICOM SCP
10. **Security**: Configures UFW firewall
11. **Services**: Creates systemd services for auto-startup
12. **Testing**: Runs deployment validation tests

### Post-Deployment Steps

1. **Create Admin User**:
   ```bash
   sudo -u noctis /opt/noctis/venv/bin/python /opt/noctis/app/manage.py createsuperuser
   ```

2. **Access Application**:
   - Web Interface: `http://your-domain.com/`
   - Health Check: `http://your-domain.com/health/`
   - Admin Panel: `http://your-domain.com/admin/`

3. **View Deployment Report**:
   ```bash
   cat /opt/noctis/deployment_report.txt
   ```

### Important Files and Locations

- **Application**: `/opt/noctis/app/`
- **Virtual Environment**: `/opt/noctis/venv/`
- **Database Credentials**: `/opt/noctis/.env`
- **Logs**: `/var/log/noctis/`
- **Nginx Config**: `/etc/nginx/sites-available/noctis`
- **Supervisor Config**: `/etc/supervisor/conf.d/noctis.conf`

### Service Management

```bash
# Check service status
sudo supervisorctl status noctis:*

# Restart services
sudo supervisorctl restart noctis:*

# View logs
sudo tail -f /var/log/noctis/gunicorn.log
sudo tail -f /var/log/noctis/dicom_scp.log
```

### Troubleshooting

1. **Check deployment log**: `/var/log/noctis_deployment.log`
2. **Verify services**: `sudo systemctl status postgresql redis-server nginx supervisor`
3. **Test connectivity**: `curl http://localhost/health/`
4. **Check Django**: `sudo -u noctis /opt/noctis/venv/bin/python /opt/noctis/app/manage.py check`

### Network Ports

- **80**: HTTP (Nginx)
- **443**: HTTPS (SSL/TLS)
- **11112**: DICOM SCP
- **5432**: PostgreSQL (internal)
- **6379**: Redis (internal)

### Security Notes

- Database password is auto-generated and saved in `/opt/noctis/.env`
- Firewall is configured to allow only necessary ports
- Application runs as non-root user `noctis`
- Production settings are used (DEBUG=False)

### Next Steps

1. **SSL/TLS Setup**: Configure Let's Encrypt certificates
2. **Backup Configuration**: Set up automated backups
3. **Monitoring**: Configure system monitoring
4. **DICOM Testing**: Test DICOM file uploads and SCP functionality
5. **Performance Tuning**: Optimize for your specific load

---

**Total Deployment Time**: ~15-30 minutes (depending on server specs and internet speed)  
**Manual Steps Required**: Minimal (just creating admin user)  
**Automation Level**: 95% automated