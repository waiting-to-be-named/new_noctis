# Noctis Medical Imaging Platform - Windows Server 12 Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Noctis Advanced Medical Imaging Platform on Windows Server 12. The system includes DICOM viewer capabilities, AI analysis, 3D reconstruction, worklist management, and reporting features.

## Prerequisites

### System Requirements
- **OS**: Windows Server 2012 R2 or later (Windows Server 2022 recommended)
- **CPU**: 4+ cores (8+ cores recommended for production)
- **RAM**: 16GB minimum (32GB+ recommended for production)
- **Storage**: 100GB+ available space (SSD recommended)
- **Network**: Gigabit Ethernet connection
- **Firewall**: Ports 80, 443, 8000 (if using Django dev server)

### Software Requirements
- Windows Server 2012 R2/2016/2019/2022
- Internet Information Services (IIS) 8.0+
- .NET Framework 4.8+
- Python 3.9+ (64-bit)
- Git for Windows
- Visual C++ Redistributable 2015-2022

## Step 1: Server Preparation

### 1.1 Windows Updates
```powershell
# Run Windows Update
Get-WindowsUpdate -Install -AcceptAll
Restart-Computer -Force
```

### 1.2 Enable Required Windows Features
```powershell
# Install IIS and required features
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer
Enable-WindowsOptionalFeature -Online -FeatureName IIS-CommonHttpFeatures
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpErrors
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpLogging
Enable-WindowsOptionalFeature -Online -FeatureName IIS-RequestFiltering
Enable-WindowsOptionalFeature -Online -FeatureName IIS-StaticContent
Enable-WindowsOptionalFeature -Online -FeatureName IIS-DefaultDocument
Enable-WindowsOptionalFeature -Online -FeatureName IIS-DirectoryBrowsing
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ASPNET45
Enable-WindowsOptionalFeature -Online -FeatureName IIS-NetFxExtensibility45
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HealthAndDiagnostics
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpCompressionDynamic
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebSockets
```

### 1.3 Install .NET Framework 4.8
```powershell
# Download and install .NET Framework 4.8
Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/?LinkId=2085150" -OutFile "dotnet48.exe"
Start-Process -FilePath "dotnet48.exe" -ArgumentList "/quiet /norestart" -Wait
```

## Step 2: Python Installation

### 2.1 Download Python 3.9+
```powershell
# Download Python 3.9+ (64-bit)
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe" -OutFile "python-3.9.13-amd64.exe"
```

### 2.2 Install Python
```powershell
# Install Python with required options
Start-Process -FilePath "python-3.9.13-amd64.exe" -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
```

### 2.3 Verify Python Installation
```powershell
# Verify Python installation
python --version
pip --version
```

## Step 3: Install Visual C++ Redistributable

```powershell
# Download and install Visual C++ Redistributable
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile "vc_redist.x64.exe"
Start-Process -FilePath "vc_redist.x64.exe" -ArgumentList "/quiet /norestart" -Wait
```

## Step 4: Application Deployment

### 4.1 Create Application Directory
```powershell
# Create application directory
New-Item -ItemType Directory -Path "C:\Noctis" -Force
Set-Location "C:\Noctis"
```

### 4.2 Clone Repository
```powershell
# Install Git for Windows if not already installed
# Download from: https://git-scm.com/download/win

# Clone the repository
git clone <your-repository-url> .
```

### 4.3 Create Virtual Environment
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4.4 Install Dependencies
```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install additional Windows-specific packages
pip install wfastcgi
```

### 4.5 Configure Django Settings for Production

Create a production settings file:

```powershell
# Copy settings file
Copy-Item "noctisview\settings.py" "noctisview\settings_production.py"
```

Edit `noctisview\settings_production.py`:

```python
# Production settings
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = 'your-production-secret-key-here'
DEBUG = False
ALLOWED_HOSTS = ['your-server-ip', 'your-domain.com', 'localhost']

# Database configuration (PostgreSQL recommended for production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'noctis_db',
        'USER': 'noctis_user',
        'PASSWORD': 'your-secure-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Static files configuration
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Media files configuration
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'noctis.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 4.6 Run Database Migrations
```powershell
# Set Django settings
$env:DJANGO_SETTINGS_MODULE = "noctisview.settings_production"

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

## Step 5: Database Setup (PostgreSQL Recommended)

### 5.1 Install PostgreSQL
```powershell
# Download PostgreSQL
Invoke-WebRequest -Uri "https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe" -OutFile "postgresql-15.4-1-windows-x64.exe"

# Install PostgreSQL
Start-Process -FilePath "postgresql-15.4-1-windows-x64.exe" -ArgumentList "--unattendedmodeui minimal", "--mode unattended", "--superpassword your-postgres-password", "--serverport 5432" -Wait
```

### 5.2 Create Database and User
```powershell
# Add PostgreSQL to PATH
$env:PATH += ";C:\Program Files\PostgreSQL\15\bin"

# Create database and user
psql -U postgres -c "CREATE DATABASE noctis_db;"
psql -U postgres -c "CREATE USER noctis_user WITH PASSWORD 'your-secure-password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;"
```

### 5.3 Install PostgreSQL Python Adapter
```powershell
# Install psycopg2
pip install psycopg2-binary
```

## Step 6: IIS Configuration

### 6.1 Install URL Rewrite Module
```powershell
# Download URL Rewrite Module
Invoke-WebRequest -Uri "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi" -OutFile "rewrite_amd64_en-US.msi"

# Install URL Rewrite Module
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i rewrite_amd64_en-US.msi /quiet" -Wait
```

### 6.2 Configure FastCGI
```powershell
# Configure wfastcgi
wfastcgi-enable
```

### 6.3 Create IIS Application
```powershell
# Create IIS application pool
Import-Module WebAdministration
New-WebAppPool -Name "NoctisAppPool"
Set-ItemProperty -Path "IIS:\AppPools\NoctisAppPool" -Name "managedRuntimeVersion" -Value ""

# Create IIS site
New-Website -Name "Noctis" -Port 80 -PhysicalPath "C:\Noctis" -ApplicationPool "NoctisAppPool"
```

### 6.4 Create web.config
Create `C:\Noctis\web.config`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <handlers>
            <add name="Python FastCGI" path="*" verb="*" modules="FastCgiModule" scriptProcessor="C:\Noctis\venv\Scripts\python.exe|C:\Noctis\venv\Lib\site-packages\wfastcgi.py" resourceType="Unspecified" requireAccess="Script" />
        </handlers>
        <rewrite>
            <rules>
                <rule name="Static Files" stopProcessing="true">
                    <match url="^(static|media)/" />
                    <action type="Rewrite" url="{R:0}" />
                </rule>
                <rule name="Django URLs" stopProcessing="true">
                    <match url=".*" />
                    <conditions logicalGrouping="MatchAll">
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="noctisview/wsgi.py" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
    <appSettings>
        <add key="PYTHONPATH" value="C:\Noctis" />
        <add key="DJANGO_SETTINGS_MODULE" value="noctisview.settings_production" />
        <add key="WSGI_HANDLER" value="noctisview.wsgi.application" />
    </appSettings>
</configuration>
```

## Step 7: Windows Service Configuration

### 7.1 Install Windows Service
```powershell
# Install pywin32 for Windows service support
pip install pywin32

# Create service script
@"
import os
import sys
import django
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings_production')
django.setup()

if __name__ == '__main__':
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])
"@ | Out-File -FilePath "C:\Noctis\service_runner.py" -Encoding UTF8

# Install as Windows service using NSSM
# Download NSSM from: https://nssm.cc/download
# nssm install NoctisService "C:\Noctis\venv\Scripts\python.exe" "C:\Noctis\service_runner.py"
# nssm set NoctisService AppDirectory "C:\Noctis"
# nssm start NoctisService
```

## Step 8: Firewall Configuration

```powershell
# Configure Windows Firewall
New-NetFirewallRule -DisplayName "Noctis HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "Noctis HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
New-NetFirewallRule -DisplayName "Noctis Django" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

## Step 9: SSL Certificate (Production)

### 9.1 Install Let's Encrypt (Optional)
```powershell
# Install Certbot for Let's Encrypt
pip install certbot
certbot --webroot -w C:\Noctis\staticfiles -d your-domain.com
```

### 9.2 Configure HTTPS in IIS
```powershell
# Bind SSL certificate to IIS site
# Use IIS Manager or PowerShell to configure SSL binding
```

## Step 10: Monitoring and Logging

### 10.1 Create Log Directory
```powershell
# Create logs directory
New-Item -ItemType Directory -Path "C:\Noctis\logs" -Force
```

### 10.2 Configure Windows Event Log
```powershell
# Create custom event log
New-EventLog -LogName "Noctis" -Source "NoctisApp"
```

### 10.3 Performance Monitoring
```powershell
# Configure performance counters
# Use Windows Performance Monitor or PowerShell to set up monitoring
```

## Step 11: Backup Configuration

### 11.1 Create Backup Script
```powershell
# Create backup script
@"
# Backup script for Noctis
$date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPath = "C:\Backups\Noctis\$date"

# Create backup directory
New-Item -ItemType Directory -Path $backupPath -Force

# Backup database
pg_dump -U noctis_user -h localhost noctis_db > "$backupPath\database.sql"

# Backup media files
Copy-Item -Path "C:\Noctis\media" -Destination "$backupPath\media" -Recurse

# Backup application files
Copy-Item -Path "C:\Noctis" -Destination "$backupPath\application" -Recurse -Exclude "venv", "__pycache__"

Write-Host "Backup completed: $backupPath"
"@ | Out-File -FilePath "C:\Noctis\backup.ps1" -Encoding UTF8
```

### 11.2 Schedule Backup Task
```powershell
# Create scheduled task for daily backup
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Noctis\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
Register-ScheduledTask -TaskName "NoctisBackup" -Action $action -Trigger $trigger -User "SYSTEM"
```

## Step 12: Testing and Verification

### 12.1 Test Application
```powershell
# Test Django application
python manage.py check --deploy

# Test static files
python manage.py collectstatic --noinput

# Test database connection
python manage.py dbshell
```

### 12.2 Verify Services
```powershell
# Check if services are running
Get-Service -Name "NoctisService"
Get-Service -Name "postgresql-x64-15"
```

### 12.3 Test Web Access
```powershell
# Test web access
Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing
```

## Troubleshooting

### Common Issues

1. **Python Path Issues**
   ```powershell
   # Ensure Python is in PATH
   $env:PATH += ";C:\Python39;C:\Python39\Scripts"
   ```

2. **Permission Issues**
   ```powershell
   # Grant IIS_IUSRS permissions
   icacls "C:\Noctis" /grant "IIS_IUSRS:(OI)(CI)F"
   ```

3. **Database Connection Issues**
   ```powershell
   # Test PostgreSQL connection
   psql -U noctis_user -d noctis_db -h localhost
   ```

4. **Static Files Not Loading**
   ```powershell
   # Recollect static files
   python manage.py collectstatic --noinput --clear
   ```

### Log Files Location
- Application logs: `C:\Noctis\logs\noctis.log`
- IIS logs: `C:\inetpub\logs\LogFiles`
- Windows Event Log: Event Viewer > Windows Logs > Application

## Security Considerations

1. **Change Default Passwords**
   - PostgreSQL password
   - Django superuser password
   - Windows service account passwords

2. **Network Security**
   - Configure firewall rules
   - Use HTTPS in production
   - Implement IP restrictions if needed

3. **File Permissions**
   - Restrict access to sensitive directories
   - Use least privilege principle

4. **Regular Updates**
   - Keep Windows Server updated
   - Update Python packages regularly
   - Monitor security advisories

## Performance Optimization

1. **Database Optimization**
   - Configure PostgreSQL for production
   - Set appropriate connection pooling
   - Regular database maintenance

2. **Static File Serving**
   - Use CDN for static files
   - Configure proper caching headers

3. **Application Optimization**
   - Use production WSGI server (Gunicorn/uWSGI)
   - Configure proper worker processes
   - Monitor memory usage

## Maintenance

### Regular Maintenance Tasks
1. **Daily**: Check application logs
2. **Weekly**: Database backups
3. **Monthly**: Security updates
4. **Quarterly**: Performance review

### Update Procedures
1. Stop services
2. Backup current installation
3. Update code and dependencies
4. Run migrations
5. Restart services
6. Verify functionality

## Support and Documentation

- Application logs: `C:\Noctis\logs\`
- Configuration files: `C:\Noctis\noctisview\`
- Database: PostgreSQL on localhost:5432
- Web interface: http://your-server-ip

For additional support, refer to the application documentation or contact the development team.