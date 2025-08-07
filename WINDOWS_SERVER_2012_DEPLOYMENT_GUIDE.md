# Noctis System Deployment Guide for Windows Server 2012 R2 in VirtualBox

## Overview

This guide provides detailed instructions for deploying the Noctis Advanced Medical Imaging Platform on Windows Server 2012 R2 running in VirtualBox. The system is a Django-based web application with DICOM medical imaging capabilities.

## System Requirements

### VirtualBox Configuration
- **RAM**: Minimum 8GB, Recommended 16GB
- **CPU**: Minimum 4 cores, Recommended 8 cores
- **Storage**: Minimum 100GB, Recommended 200GB (SSD preferred)
- **Network**: Bridge adapter for external access

### Windows Server 2012 R2 Requirements
- **OS**: Windows Server 2012 R2 Standard or Datacenter
- **Architecture**: 64-bit
- **Updates**: Latest service pack and security updates
- **Roles**: Web Server (IIS), Application Server

## Pre-Deployment Setup

### 1. VirtualBox Installation and Configuration

#### Install VirtualBox
1. Download VirtualBox from https://www.virtualbox.org/
2. Install with default settings
3. Install VirtualBox Extension Pack for USB 3.0 support

#### Create Virtual Machine
1. Open VirtualBox Manager
2. Click "New" → "Expert Mode"
3. Configure VM settings:
   - **Name**: Noctis-Server-2012
   - **Type**: Microsoft Windows
   - **Version**: Windows 2012 (64-bit)
   - **Memory**: 8192 MB (8GB)
   - **Hard disk**: Create a virtual hard disk now
   - **File location**: Choose SSD location if available
   - **File size**: 200 GB
   - **Hard disk file type**: VDI
   - **Storage on physical hard disk**: Dynamically allocated

#### Configure VM Settings
1. Select the VM and click "Settings"
2. **System** tab:
   - **Base Memory**: 8192 MB
   - **Processor(s)**: 4 (or more if available)
   - **Enable PAE/NX**: Checked
   - **Enable VT-x/AMD-V**: Checked
   - **Enable Nested Paging**: Checked
3. **Display** tab:
   - **Video Memory**: 128 MB
   - **Enable 3D Acceleration**: Checked
4. **Storage** tab:
   - Add SATA controller if not present
   - Attach Windows Server 2012 R2 ISO
5. **Network** tab:
   - **Attached to**: Bridge Adapter
   - **Name**: Select your network adapter
6. **Advanced** tab:
   - **Shared Clipboard**: Bidirectional
   - **Drag'n'Drop**: Bidirectional

### 2. Windows Server 2012 R2 Installation

#### Install Windows Server
1. Start the VM and boot from ISO
2. Choose language and keyboard layout
3. Click "Install Now"
4. Select "Windows Server 2012 R2 Standard (Server with a GUI)"
5. Accept license terms
6. Choose "Custom: Install Windows only (advanced)"
7. Select the virtual disk and click "Next"
8. Wait for installation to complete (20-30 minutes)

#### Initial Windows Configuration
1. Set administrator password (use strong password)
2. Press Ctrl+Alt+Del to log in
3. Set up Windows with default settings
4. Install Windows Updates (may take several reboots)

### 3. Windows Server Configuration

#### Install Windows Features
1. Open Server Manager
2. Click "Add roles and features"
3. Select "Role-based or feature-based installation"
4. Select the local server
5. Install the following roles:
   - **Web Server (IIS)**
   - **Application Server**
6. Install the following features:
   - **.NET Framework 4.8**
   - **Windows PowerShell 4.0**
   - **Windows Identity Foundation 3.5**

#### Configure Windows Firewall
1. Open Windows Firewall with Advanced Security
2. Create inbound rules for:
   - **Port 80** (HTTP)
   - **Port 443** (HTTPS)
   - **Port 8000** (Django development server)
   - **Port 22** (SSH if using)

#### Configure Network Settings
1. Open Network and Sharing Center
2. Configure static IP address (recommended)
3. Set DNS servers
4. Test network connectivity

## Python Environment Setup

### 1. Install Python 3.11

#### Download and Install Python
1. Download Python 3.11 from https://www.python.org/downloads/
2. Run installer as Administrator
3. **Important**: Check "Add Python to PATH"
4. Check "Install for all users"
5. Choose "Customize installation"
6. Select all optional features
7. Install to `C:\Python311\`

#### Verify Installation
```cmd
python --version
pip --version
```

### 2. Install Visual C++ Build Tools
1. Download Visual Studio Build Tools 2019
2. Install with C++ build tools
3. This is required for some Python packages

### 3. Install Git
1. Download Git for Windows from https://git-scm.com/
2. Install with default settings
3. Verify installation: `git --version`

## Noctis System Deployment

### 1. Clone and Setup Project

#### Create Project Directory
```cmd
mkdir C:\Noctis
cd C:\Noctis
```

#### Clone Repository
```cmd
git clone <repository-url> .
```

#### Create Virtual Environment
```cmd
python -m venv venv
venv\Scripts\activate
```

#### Install Dependencies
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Database Setup

#### SQLite Configuration (Default)
The system uses SQLite by default, which is suitable for development and small deployments.

#### PostgreSQL Configuration (Recommended for Production)
1. Download PostgreSQL 15 from https://www.postgresql.org/download/windows/
2. Install with default settings
3. Set password for postgres user
4. Create database:
```sql
CREATE DATABASE noctis_db;
CREATE USER noctis_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;
```

5. Update `noctisview/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'noctis_db',
        'USER': 'noctis_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 3. Django Configuration

#### Run Migrations
```cmd
python manage.py makemigrations
python manage.py migrate
```

#### Create Superuser
```cmd
python manage.py createsuperuser
```

#### Collect Static Files
```cmd
python manage.py collectstatic
```

#### Create Required Directories
```cmd
mkdir media
mkdir media\dicom_files
mkdir media\temp
mkdir logs
```

### 4. Environment Configuration

#### Create Environment File
Create `C:\Noctis\.env`:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip
DATABASE_URL=postgresql://noctis_user:your_password@localhost:5432/noctis_db
```

#### Update Settings
Modify `noctisview/settings.py`:
```python
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Update settings
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Production settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 5. Install Additional Dependencies

#### Install python-dotenv
```cmd
pip install python-dotenv
```

#### Install Windows-specific packages
```cmd
pip install pywin32
```

## Web Server Configuration

### Option 1: Development Server (Testing Only)
```cmd
python manage.py runserver 0.0.0.0:8000
```

### Option 2: IIS with wfastcgi (Production)

#### Install wfastcgi
```cmd
pip install wfastcgi
wfastcgi-enable
```

#### Configure IIS
1. Open IIS Manager
2. Create new website "Noctis"
3. Set physical path to `C:\Noctis`
4. Set port to 80 (or 443 for HTTPS)
5. Configure application pool:
   - .NET CLR Version: "No Managed Code"
   - Managed Pipeline Mode: "Integrated"

#### Create web.config
Create `C:\Noctis\web.config`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <handlers>
            <add name="Python FastCGI" 
                 path="*" 
                 verb="*" 
                 modules="FastCgiModule" 
                 scriptProcessor="C:\Noctis\venv\Scripts\python.exe|C:\Noctis\venv\Lib\site-packages\wfastcgi.py" 
                 resourceType="Unspecified" 
                 requireAccess="Script" />
        </handlers>
    </system.webServer>
    <appSettings>
        <add key="PYTHONPATH" value="C:\Noctis" />
        <add key="WSGI_HANDLER" value="noctisview.wsgi.application" />
        <add key="DJANGO_SETTINGS_MODULE" value="noctisview.settings" />
    </appSettings>
</configuration>
```

### Option 3: Gunicorn with Nginx (Recommended)

#### Install Gunicorn
```cmd
pip install gunicorn
```

#### Create Gunicorn Configuration
Create `C:\Noctis\gunicorn.conf.py`:
```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

#### Install Nginx for Windows
1. Download Nginx for Windows
2. Extract to `C:\nginx`
3. Configure `C:\nginx\conf\nginx.conf`:
```nginx
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    server {
        listen       80;
        server_name  localhost;

        location /static/ {
            alias C:/Noctis/staticfiles/;
        }

        location /media/ {
            alias C:/Noctis/media/;
        }

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Service Configuration

### Create Windows Service

#### Install NSSM (Non-Sucking Service Manager)
1. Download NSSM from https://nssm.cc/
2. Extract to `C:\nssm`

#### Create Gunicorn Service
```cmd
C:\nssm\nssm.exe install NoctisGunicorn "C:\Noctis\venv\Scripts\gunicorn.exe" "noctisview.wsgi:application --config gunicorn.conf.py"
C:\nssm\nssm.exe set NoctisGunicorn AppDirectory "C:\Noctis"
C:\nssm\nssm.exe set NoctisGunicorn AppEnvironmentExtra PYTHONPATH=C:\Noctis
```

#### Create Nginx Service
```cmd
C:\nssm\nssm.exe install NoctisNginx "C:\nginx\nginx.exe"
C:\nssm\nssm.exe set NoctisNginx AppDirectory "C:\nginx"
```

#### Start Services
```cmd
net start NoctisGunicorn
net start NoctisNginx
```

## Security Configuration

### 1. Windows Security
1. Enable Windows Defender
2. Configure Windows Firewall rules
3. Install antivirus software
4. Enable Windows Updates

### 2. Application Security
1. Change default Django secret key
2. Use HTTPS in production
3. Configure proper file permissions
4. Regular security updates

### 3. Database Security
1. Use strong passwords
2. Limit database access
3. Regular backups
4. Encrypt sensitive data

## Performance Optimization

### 1. VirtualBox Optimization
1. Enable hardware virtualization
2. Allocate sufficient RAM and CPU
3. Use SSD storage if available
4. Enable 3D acceleration

### 2. Windows Optimization
1. Disable unnecessary services
2. Optimize virtual memory
3. Defragment disk regularly
4. Monitor resource usage

### 3. Application Optimization
1. Use production database
2. Configure caching
3. Optimize static files
4. Monitor application performance

## Monitoring and Maintenance

### 1. Log Monitoring
1. Check Django logs in `C:\Noctis\logs\`
2. Monitor Windows Event Viewer
3. Set up log rotation
4. Configure alerts

### 2. Backup Strategy
1. Regular database backups
2. File system backups
3. Configuration backups
4. Test restore procedures

### 3. Updates and Patches
1. Regular Windows Updates
2. Python package updates
3. Django security updates
4. Application updates

## Troubleshooting

### Common Issues

#### VirtualBox Performance Issues
1. Enable hardware virtualization in BIOS
2. Allocate more RAM/CPU
3. Use SSD storage
4. Disable unnecessary features

#### Python Installation Issues
1. Check PATH environment variable
2. Install Visual C++ Build Tools
3. Use compatible Python version
4. Check Windows compatibility

#### Django Configuration Issues
1. Verify virtual environment activation
2. Check database configuration
3. Verify file permissions
4. Check log files for errors

#### Network Access Issues
1. Configure Windows Firewall
2. Check VirtualBox network settings
3. Verify IP configuration
4. Test network connectivity

### Debug Commands
```cmd
# Check Python installation
python --version
pip list

# Check Django configuration
python manage.py check

# Test database connection
python manage.py dbshell

# Check static files
python manage.py collectstatic --dry-run

# Test web server
curl http://localhost:8000
```

## Production Checklist

- [ ] Windows Server 2012 R2 installed and updated
- [ ] Python 3.11 installed and configured
- [ ] Virtual environment created and activated
- [ ] All dependencies installed
- [ ] Database configured and migrated
- [ ] Static files collected
- [ ] Web server configured (IIS/Nginx)
- [ ] Windows services configured
- [ ] Firewall rules configured
- [ ] SSL certificate installed (production)
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] Security measures implemented
- [ ] Performance optimized
- [ ] Documentation completed

## Support and Resources

### Documentation
- Django Documentation: https://docs.djangoproject.com/
- Windows Server Documentation: https://docs.microsoft.com/en-us/windows-server/
- VirtualBox Documentation: https://www.virtualbox.org/manual/

### Community Support
- Django Community: https://www.djangoproject.com/community/
- Stack Overflow: https://stackoverflow.com/
- Windows Server Forums: https://social.technet.microsoft.com/Forums/

### Professional Support
- Contact the Noctis development team
- Windows Server support from Microsoft
- VirtualBox community support

## Conclusion

This deployment guide provides comprehensive instructions for deploying the Noctis medical imaging system on Windows Server 2012 R2 in VirtualBox. Follow each section carefully and test thoroughly before moving to production. Regular maintenance and monitoring are essential for reliable operation.

For additional support or custom configurations, contact the development team.