# Noctis System Deployment - Quick Reference

## Prerequisites Checklist

- [ ] VirtualBox installed with Extension Pack
- [ ] Windows Server 2012 R2 ISO downloaded
- [ ] At least 8GB RAM available for VM
- [ ] 200GB free disk space
- [ ] Python 3.11 downloaded
- [ ] Git for Windows downloaded

## VirtualBox VM Configuration

### Basic Settings
- **Name**: Noctis-Server-2012
- **Type**: Microsoft Windows
- **Version**: Windows 2012 (64-bit)
- **Memory**: 8192 MB (8GB)
- **Storage**: 200 GB VDI (dynamically allocated)
- **Network**: Bridge Adapter

### Advanced Settings
- **Processors**: 4 cores minimum
- **PAE/NX**: Enabled
- **VT-x/AMD-V**: Enabled
- **Nested Paging**: Enabled
- **3D Acceleration**: Enabled
- **Video Memory**: 128 MB

## Windows Server 2012 R2 Installation

1. **Install Windows Server**
   - Choose "Windows Server 2012 R2 Standard (Server with a GUI)"
   - Set strong administrator password
   - Install all Windows Updates

2. **Install Windows Features**
   - Web Server (IIS)
   - Application Server
   - .NET Framework 4.8
   - Windows PowerShell 4.0

3. **Configure Network**
   - Set static IP address
   - Configure DNS servers
   - Test network connectivity

## Python Environment Setup

### Install Python 3.11
```cmd
# Download from https://www.python.org/downloads/
# Check "Add Python to PATH" during installation
# Install for all users
python --version
pip --version
```

### Install Visual C++ Build Tools
```cmd
# Download Visual Studio Build Tools 2019
# Install with C++ build tools
```

### Install Git
```cmd
# Download from https://git-scm.com/
# Install with default settings
git --version
```

## Noctis System Deployment

### 1. Initial Setup
```cmd
# Run as Administrator
windows_deployment_setup.bat
```

### 2. Clone Repository
```cmd
cd C:\Noctis
git clone <repository-url> .
```

### 3. Setup Virtual Environment
```cmd
cd C:\Noctis
venv\Scripts\activate
pip install -r requirements.txt
pip install python-dotenv pywin32 gunicorn
```

### 4. Database Configuration
```cmd
# For SQLite (default)
python manage.py makemigrations
python manage.py migrate

# For PostgreSQL
# Install PostgreSQL 15
# Create database and user
# Update settings.py
```

### 5. Django Configuration
```cmd
python manage.py createsuperuser
python manage.py collectstatic
```

### 6. Test Development Server
```cmd
python manage.py runserver 0.0.0.0:8000
# Access at http://localhost:8000
```

## Production Deployment

### Option 1: IIS with wfastcgi
```cmd
pip install wfastcgi
wfastcgi-enable
# Configure IIS and web.config
```

### Option 2: Gunicorn with Nginx (Recommended)
```cmd
# Install Nginx for Windows
# Copy nginx.conf.template to C:\nginx\conf\nginx.conf
# Install NSSM
# Create Windows services
```

### PowerShell Deployment Script
```powershell
# Run as Administrator
.\deploy_noctis.ps1 -Environment production -DatabaseType postgresql -WebServer nginx -InstallServices -ConfigureFirewall -OptimizePerformance
```

## Service Management

### Start Services
```cmd
net start NoctisGunicorn
net start NoctisNginx
```

### Stop Services
```cmd
net stop NoctisGunicorn
net stop NoctisNginx
```

### Check Service Status
```cmd
sc query NoctisGunicorn
sc query NoctisNginx
```

## Firewall Configuration

### Manual Configuration
```cmd
netsh advfirewall firewall add rule name="Noctis HTTP" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="Noctis HTTPS" dir=in action=allow protocol=TCP localport=443
netsh advfirewall firewall add rule name="Noctis Django" dir=in action=allow protocol=TCP localport=8000
```

### Using Script
```cmd
configure_firewall.bat
```

## Monitoring and Maintenance

### Check System Status
```cmd
monitor.bat
```

### Create Backup
```cmd
backup.bat
```

### Check Logs
```cmd
# Django logs
type C:\Noctis\logs\django.log

# Windows Event Viewer
eventvwr.msc
```

### Performance Monitoring
```cmd
# Check disk space
dir C:\

# Check memory usage
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:table

# Check CPU usage
wmic cpu get loadpercentage
```

## Troubleshooting Commands

### Check Python Installation
```cmd
python --version
pip list
```

### Check Django Configuration
```cmd
python manage.py check
python manage.py dbshell
```

### Check Network Connectivity
```cmd
ping localhost
ipconfig
netstat -an | findstr :8000
```

### Check File Permissions
```cmd
icacls C:\Noctis
icacls C:\Noctis\media
```

### Restart Services
```cmd
net stop NoctisGunicorn && net start NoctisGunicorn
net stop NoctisNginx && net start NoctisNginx
```

## Security Checklist

- [ ] Change default Django secret key
- [ ] Use HTTPS in production
- [ ] Configure proper file permissions
- [ ] Enable Windows Defender
- [ ] Configure Windows Firewall
- [ ] Install antivirus software
- [ ] Enable Windows Updates
- [ ] Use strong passwords
- [ ] Regular security updates

## Performance Optimization

### VirtualBox Optimization
- Enable hardware virtualization in BIOS
- Allocate sufficient RAM and CPU
- Use SSD storage if available
- Enable 3D acceleration

### Windows Optimization
- Disable unnecessary services
- Optimize virtual memory
- Defragment disk regularly
- Monitor resource usage

### Application Optimization
- Use production database (PostgreSQL)
- Configure caching
- Optimize static files
- Monitor application performance

## Backup and Recovery

### Backup Strategy
1. **Database Backup**
   ```cmd
   # SQLite
   copy C:\Noctis\db.sqlite3 C:\backup\db_backup.sqlite3
   
   # PostgreSQL
   pg_dump -U noctis_user noctis_db > C:\backup\db_backup.sql
   ```

2. **File System Backup**
   ```cmd
   xcopy C:\Noctis\media C:\backup\media /E /I /Y
   xcopy C:\Noctis\staticfiles C:\backup\staticfiles /E /I /Y
   ```

3. **Configuration Backup**
   ```cmd
   copy C:\Noctis\.env C:\backup\env_backup.txt
   copy C:\Noctis\noctisview\settings.py C:\backup\settings_backup.py
   ```

### Recovery Process
1. Stop services
2. Restore database
3. Restore files
4. Restore configuration
5. Start services
6. Test functionality

## Common Issues and Solutions

### Issue: Python not found
**Solution**: Check PATH environment variable, reinstall Python

### Issue: Virtual environment not activating
**Solution**: Run `venv\Scripts\activate` from correct directory

### Issue: Database connection failed
**Solution**: Check database configuration in settings.py

### Issue: Static files not loading
**Solution**: Run `python manage.py collectstatic`

### Issue: Services not starting
**Solution**: Check service configuration, review Windows Event Viewer

### Issue: Network access denied
**Solution**: Configure Windows Firewall, check VirtualBox network settings

## Support Resources

### Documentation
- Django Documentation: https://docs.djangoproject.com/
- Windows Server Documentation: https://docs.microsoft.com/en-us/windows-server/
- VirtualBox Documentation: https://www.virtualbox.org/manual/

### Community Support
- Django Community: https://www.djangoproject.com/community/
- Stack Overflow: https://stackoverflow.com/
- Windows Server Forums: https://social.technet.microsoft.com/Forums/

### Log Files Location
- Django logs: `C:\Noctis\logs\django.log`
- Windows Event Viewer: `eventvwr.msc`
- IIS logs: `C:\inetpub\logs\LogFiles`
- Nginx logs: `C:\nginx\logs`

## Quick Commands Reference

```cmd
# Development
python manage.py runserver 0.0.0.0:8000

# Production
net start NoctisGunicorn
net start NoctisNginx

# Monitoring
monitor.bat
backup.bat

# Troubleshooting
python manage.py check
sc query NoctisGunicorn
netstat -an | findstr :8000
```

## Emergency Procedures

### System Won't Start
1. Check VirtualBox settings
2. Verify Windows installation
3. Check hardware resources
4. Review error logs

### Application Won't Load
1. Check service status
2. Verify network connectivity
3. Check firewall settings
4. Review application logs

### Database Issues
1. Check database service
2. Verify connection settings
3. Restore from backup
4. Check disk space

### Performance Issues
1. Monitor resource usage
2. Optimize VirtualBox settings
3. Disable unnecessary services
4. Increase allocated resources