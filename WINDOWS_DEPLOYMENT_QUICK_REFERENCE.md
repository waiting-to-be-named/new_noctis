# Noctis Windows Server Deployment - Quick Reference

## Quick Start Commands

### 1. Run Automated Deployment Script
```powershell
# Run as Administrator
.\deploy_windows_server.ps1 -RepositoryUrl "https://your-repo-url" -ServerIP "192.168.1.100" -DomainName "noctis.yourdomain.com"
```

### 2. Manual Installation Steps
```powershell
# Enable IIS features
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole -All

# Install Python
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe" -OutFile "python.exe"
Start-Process -FilePath "python.exe" -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait

# Install PostgreSQL
Invoke-WebRequest -Uri "https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe" -OutFile "postgresql.exe"
Start-Process -FilePath "postgresql.exe" -ArgumentList "--unattendedmodeui minimal", "--mode unattended", "--superpassword YourPassword123!" -Wait
```

## Essential Commands

### Application Management
```powershell
# Start/Stop IIS
iisreset
net start w3svc
net stop w3svc

# Check application status
Get-Website -Name "Noctis"
Get-WebAppPool -Name "NoctisAppPool"

# View application logs
Get-Content "C:\Noctis\logs\noctis.log" -Tail 50
Get-Content "C:\inetpub\logs\LogFiles\W3SVC1\u_ex*.log" -Tail 50
```

### Database Management
```powershell
# Connect to PostgreSQL
psql -U postgres -d noctis_db

# Backup database
pg_dump -U noctis_user -h localhost noctis_db > backup.sql

# Restore database
psql -U noctis_user -h localhost noctis_db < backup.sql
```

### Django Management
```powershell
# Activate virtual environment
C:\Noctis\venv\Scripts\Activate.ps1

# Run Django commands
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# Check Django deployment
python manage.py check --deploy
```

## Troubleshooting

### Common Issues & Solutions

#### 1. IIS 500 Error
```powershell
# Check application pool
Get-WebAppPool -Name "NoctisAppPool" | Select-Object Name, State, ProcessModel

# Restart application pool
Restart-WebAppPool -Name "NoctisAppPool"

# Check permissions
icacls "C:\Noctis" /grant "IIS_IUSRS:(OI)(CI)F" /T
```

#### 2. Python Path Issues
```powershell
# Add Python to PATH
$env:PATH += ";C:\Python39;C:\Python39\Scripts"

# Verify Python installation
python --version
pip --version
```

#### 3. Database Connection Issues
```powershell
# Test PostgreSQL connection
psql -U noctis_user -d noctis_db -h localhost

# Check PostgreSQL service
Get-Service -Name "postgresql-x64-15"

# Restart PostgreSQL
Restart-Service -Name "postgresql-x64-15"
```

#### 4. Static Files Not Loading
```powershell
# Recollect static files
python manage.py collectstatic --noinput --clear

# Check static files directory
Get-ChildItem "C:\Noctis\staticfiles"
```

#### 5. Firewall Issues
```powershell
# Check firewall rules
Get-NetFirewallRule -DisplayName "*Noctis*"

# Add firewall rules
New-NetFirewallRule -DisplayName "Noctis HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

## Security Checklist

### Passwords to Change
- [ ] PostgreSQL superuser password
- [ ] Django superuser password
- [ ] Database user password
- [ ] Windows service account passwords

### Security Configurations
```powershell
# Configure HTTPS (if SSL certificate available)
# Use IIS Manager to bind SSL certificate

# Set up Windows Firewall rules
New-NetFirewallRule -DisplayName "Noctis HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow

# Restrict file permissions
icacls "C:\Noctis" /inheritance:r
icacls "C:\Noctis" /grant "IIS_IUSRS:(OI)(CI)RX" /T
```

## Monitoring & Maintenance

### Daily Tasks
```powershell
# Check application logs
Get-Content "C:\Noctis\logs\noctis.log" -Tail 20

# Check disk space
Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace

# Check service status
Get-Service -Name "w3svc", "postgresql-x64-15"
```

### Weekly Tasks
```powershell
# Run backup
C:\Noctis\backup.ps1

# Update Windows
Get-WindowsUpdate -Install -AcceptAll

# Check for Python package updates
pip list --outdated
```

### Monthly Tasks
```powershell
# Review security logs
Get-EventLog -LogName Security -Newest 100 | Where-Object {$_.EventID -eq 4625}

# Check performance
Get-Counter "\Processor(_Total)\% Processor Time"
Get-Counter "\Memory\Available MBytes"
```

## Backup & Recovery

### Automated Backup
```powershell
# Schedule daily backup
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Noctis\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
Register-ScheduledTask -TaskName "NoctisBackup" -Action $action -Trigger $trigger -User "SYSTEM"
```

### Manual Backup
```powershell
# Full system backup
$date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPath = "C:\Backups\Noctis\$date"

# Database backup
pg_dump -U noctis_user -h localhost noctis_db > "$backupPath\database.sql"

# Application backup
Copy-Item -Path "C:\Noctis" -Destination "$backupPath\application" -Recurse -Exclude "venv", "__pycache__"
```

## Performance Tuning

### Database Optimization
```sql
-- PostgreSQL optimization
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
SELECT pg_reload_conf();
```

### IIS Optimization
```powershell
# Configure application pool
Set-ItemProperty -Path "IIS:\AppPools\NoctisAppPool" -Name "processModel" -Value @{maxProcesses=4}
Set-ItemProperty -Path "IIS:\AppPools\NoctisAppPool" -Name "recycling" -Value @{periodicRestart=@{}}
```

## Emergency Procedures

### Application Recovery
```powershell
# Stop all services
Stop-Website -Name "Noctis"
Stop-Service -Name "postgresql-x64-15"

# Restore from backup
# 1. Restore database
psql -U noctis_user -h localhost noctis_db < backup.sql

# 2. Restore application files
Copy-Item -Path "backup\application\*" -Destination "C:\Noctis" -Recurse -Force

# 3. Restart services
Start-Service -Name "postgresql-x64-15"
Start-Website -Name "Noctis"
```

### Complete System Recovery
```powershell
# 1. Reinstall Windows Server
# 2. Run deployment script with same parameters
# 3. Restore from backup
.\deploy_windows_server.ps1 -RepositoryUrl "your-repo" -ServerIP "your-ip"
```

## Contact Information

- **Application Logs**: `C:\Noctis\logs\noctis.log`
- **IIS Logs**: `C:\inetpub\logs\LogFiles`
- **Database**: PostgreSQL on localhost:5432
- **Web Interface**: http://your-server-ip
- **Admin Panel**: http://your-server-ip/admin

## Quick Commands Reference

| Task | Command |
|------|---------|
| Check IIS Status | `Get-Website -Name "Noctis"` |
| Restart IIS | `iisreset` |
| Check PostgreSQL | `Get-Service -Name "postgresql-x64-15"` |
| View Logs | `Get-Content "C:\Noctis\logs\noctis.log" -Tail 20` |
| Backup Database | `pg_dump -U noctis_user -h localhost noctis_db > backup.sql` |
| Check Disk Space | `Get-WmiObject -Class Win32_LogicalDisk` |
| Test Web Access | `Invoke-WebRequest -Uri "http://localhost"` |
| Update Python Packages | `pip install -r requirements.txt --upgrade` |