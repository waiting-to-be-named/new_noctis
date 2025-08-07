# Noctis Medical Imaging Platform - Windows Server Deployment Script
# Run this script as Administrator on Windows Server

param(
    [string]$RepositoryUrl = "",
    [string]$ServerIP = "",
    [string]$DomainName = "",
    [string]$PostgresPassword = "NoctisSecurePass123!",
    [string]$DjangoSecretKey = "",
    [switch]$SkipDatabase = $false,
    [switch]$SkipSSL = $false
)

# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

Write-Host "=== Noctis Medical Imaging Platform Deployment ===" -ForegroundColor Green
Write-Host "Starting deployment on Windows Server..." -ForegroundColor Yellow

# Step 1: Check prerequisites
Write-Host "`nStep 1: Checking prerequisites..." -ForegroundColor Cyan

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

# Check Windows version
$osInfo = Get-WmiObject -Class Win32_OperatingSystem
Write-Host "OS: $($osInfo.Caption) $($osInfo.OSArchitecture)" -ForegroundColor Green

# Step 2: Install Windows Features
Write-Host "`nStep 2: Installing Windows Features..." -ForegroundColor Cyan

$features = @(
    "IIS-WebServerRole",
    "IIS-WebServer",
    "IIS-CommonHttpFeatures",
    "IIS-HttpErrors",
    "IIS-HttpLogging",
    "IIS-RequestFiltering",
    "IIS-StaticContent",
    "IIS-DefaultDocument",
    "IIS-DirectoryBrowsing",
    "IIS-ASPNET45",
    "IIS-NetFxExtensibility45",
    "IIS-HealthAndDiagnostics",
    "IIS-HttpCompressionDynamic",
    "IIS-WebSockets"
)

foreach ($feature in $features) {
    Write-Host "Installing $feature..." -ForegroundColor Yellow
    Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
}

# Step 3: Install .NET Framework 4.8
Write-Host "`nStep 3: Installing .NET Framework 4.8..." -ForegroundColor Cyan

$dotnetUrl = "https://go.microsoft.com/fwlink/?LinkId=2085150"
$dotnetInstaller = "dotnet48.exe"

if (-not (Test-Path $dotnetInstaller)) {
    Write-Host "Downloading .NET Framework 4.8..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $dotnetUrl -OutFile $dotnetInstaller
}

Write-Host "Installing .NET Framework 4.8..." -ForegroundColor Yellow
Start-Process -FilePath $dotnetInstaller -ArgumentList "/quiet /norestart" -Wait

# Step 4: Install Python
Write-Host "`nStep 4: Installing Python..." -ForegroundColor Cyan

$pythonUrl = "https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe"
$pythonInstaller = "python-3.9.13-amd64.exe"

if (-not (Test-Path $pythonInstaller)) {
    Write-Host "Downloading Python 3.9.13..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
}

Write-Host "Installing Python 3.9.13..." -ForegroundColor Yellow
Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait

# Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verify Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python installation failed" -ForegroundColor Red
    exit 1
}

# Step 5: Install Visual C++ Redistributable
Write-Host "`nStep 5: Installing Visual C++ Redistributable..." -ForegroundColor Cyan

$vcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$vcRedistInstaller = "vc_redist.x64.exe"

if (-not (Test-Path $vcRedistInstaller)) {
    Write-Host "Downloading Visual C++ Redistributable..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $vcRedistUrl -OutFile $vcRedistInstaller
}

Write-Host "Installing Visual C++ Redistributable..." -ForegroundColor Yellow
Start-Process -FilePath $vcRedistInstaller -ArgumentList "/quiet /norestart" -Wait

# Step 6: Create Application Directory
Write-Host "`nStep 6: Setting up application directory..." -ForegroundColor Cyan

$appPath = "C:\Noctis"
New-Item -ItemType Directory -Path $appPath -Force | Out-Null
Set-Location $appPath

# Step 7: Clone Repository
if ($RepositoryUrl) {
    Write-Host "`nStep 7: Cloning repository..." -ForegroundColor Cyan
    Write-Host "Cloning from: $RepositoryUrl" -ForegroundColor Yellow
    
    # Check if Git is installed
    try {
        git --version | Out-Null
    } catch {
        Write-Host "ERROR: Git is not installed. Please install Git for Windows first." -ForegroundColor Red
        Write-Host "Download from: https://git-scm.com/download/win" -ForegroundColor Yellow
        exit 1
    }
    
    git clone $RepositoryUrl .
} else {
    Write-Host "`nStep 7: Skipping repository clone (no URL provided)" -ForegroundColor Yellow
    Write-Host "Please manually copy application files to C:\Noctis" -ForegroundColor Yellow
}

# Step 8: Create Virtual Environment
Write-Host "`nStep 8: Creating virtual environment..." -ForegroundColor Cyan

python -m venv venv
.\venv\Scripts\Activate.ps1

# Step 9: Install Dependencies
Write-Host "`nStep 9: Installing Python dependencies..." -ForegroundColor Cyan

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install wfastcgi psycopg2-binary pywin32

# Step 10: Configure Production Settings
Write-Host "`nStep 10: Configuring production settings..." -ForegroundColor Cyan

# Generate Django secret key if not provided
if (-not $DjangoSecretKey) {
    $DjangoSecretKey = -join ((33..126) | Get-Random -Count 50 | ForEach-Object {[char]$_})
}

# Create production settings
$productionSettings = @"
# Production settings
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = '$DjangoSecretKey'
DEBUG = False
ALLOWED_HOSTS = ['$ServerIP', '$DomainName', 'localhost', '127.0.0.1']

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'noctis_db',
        'USER': 'noctis_user',
        'PASSWORD': '$PostgresPassword',
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

# Include all other settings from settings.py
from .settings import *
"@

$productionSettings | Out-File -FilePath "noctisview\settings_production.py" -Encoding UTF8

# Step 11: Install PostgreSQL (if not skipped)
if (-not $SkipDatabase) {
    Write-Host "`nStep 11: Installing PostgreSQL..." -ForegroundColor Cyan
    
    $postgresUrl = "https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe"
    $postgresInstaller = "postgresql-15.4-1-windows-x64.exe"
    
    if (-not (Test-Path $postgresInstaller)) {
        Write-Host "Downloading PostgreSQL..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $postgresUrl -OutFile $postgresInstaller
    }
    
    Write-Host "Installing PostgreSQL..." -ForegroundColor Yellow
    Start-Process -FilePath $postgresInstaller -ArgumentList "--unattendedmodeui minimal", "--mode unattended", "--superpassword $PostgresPassword", "--serverport 5432" -Wait
    
    # Add PostgreSQL to PATH
    $env:PATH += ";C:\Program Files\PostgreSQL\15\bin"
    
    # Create database and user
    Write-Host "Creating database and user..." -ForegroundColor Yellow
    psql -U postgres -c "CREATE DATABASE noctis_db;" 2>$null
    psql -U postgres -c "CREATE USER noctis_user WITH PASSWORD '$PostgresPassword';" 2>$null
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;" 2>$null
}

# Step 12: Run Django Setup
Write-Host "`nStep 12: Setting up Django..." -ForegroundColor Cyan

$env:DJANGO_SETTINGS_MODULE = "noctisview.settings_production"

# Create logs directory
New-Item -ItemType Directory -Path "logs" -Force | Out-Null

# Run migrations
Write-Host "Running database migrations..." -ForegroundColor Yellow
python manage.py makemigrations
python manage.py migrate

# Create superuser
Write-Host "Creating superuser..." -ForegroundColor Yellow
$superuserPassword = "Admin123!"
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@noctis.com', '$superuserPassword')" | python manage.py shell

# Collect static files
Write-Host "Collecting static files..." -ForegroundColor Yellow
python manage.py collectstatic --noinput

# Step 13: Configure IIS
Write-Host "`nStep 13: Configuring IIS..." -ForegroundColor Cyan

# Install URL Rewrite Module
$rewriteUrl = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
$rewriteInstaller = "rewrite_amd64_en-US.msi"

if (-not (Test-Path $rewriteInstaller)) {
    Write-Host "Downloading URL Rewrite Module..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $rewriteUrl -OutFile $rewriteInstaller
}

Write-Host "Installing URL Rewrite Module..." -ForegroundColor Yellow
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i rewrite_amd64_en-US.msi /quiet" -Wait

# Configure wfastcgi
Write-Host "Configuring wfastcgi..." -ForegroundColor Yellow
wfastcgi-enable

# Create IIS application pool and site
Import-Module WebAdministration

# Remove existing site if it exists
if (Get-Website -Name "Noctis" -ErrorAction SilentlyContinue) {
    Remove-Website -Name "Noctis"
}

# Remove existing app pool if it exists
if (Get-WebAppPool -Name "NoctisAppPool" -ErrorAction SilentlyContinue) {
    Remove-WebAppPool -Name "NoctisAppPool"
}

# Create new app pool and site
New-WebAppPool -Name "NoctisAppPool"
Set-ItemProperty -Path "IIS:\AppPools\NoctisAppPool" -Name "managedRuntimeVersion" -Value ""
New-Website -Name "Noctis" -Port 80 -PhysicalPath $appPath -ApplicationPool "NoctisAppPool"

# Step 14: Create web.config
Write-Host "`nStep 14: Creating web.config..." -ForegroundColor Cyan

$webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <handlers>
            <add name="Python FastCGI" path="*" verb="*" modules="FastCgiModule" scriptProcessor="$appPath\venv\Scripts\python.exe|$appPath\venv\Lib\site-packages\wfastcgi.py" resourceType="Unspecified" requireAccess="Script" />
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
        <add key="PYTHONPATH" value="$appPath" />
        <add key="DJANGO_SETTINGS_MODULE" value="noctisview.settings_production" />
        <add key="WSGI_HANDLER" value="noctisview.wsgi.application" />
    </appSettings>
</configuration>
"@

$webConfig | Out-File -FilePath "$appPath\web.config" -Encoding UTF8

# Step 15: Configure Firewall
Write-Host "`nStep 15: Configuring firewall..." -ForegroundColor Cyan

New-NetFirewallRule -DisplayName "Noctis HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "Noctis HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "Noctis Django" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -ErrorAction SilentlyContinue

# Step 16: Set Permissions
Write-Host "`nStep 16: Setting permissions..." -ForegroundColor Cyan

# Grant IIS_IUSRS permissions
icacls $appPath /grant "IIS_IUSRS:(OI)(CI)F" /T

# Step 17: Create Backup Script
Write-Host "`nStep 17: Creating backup script..." -ForegroundColor Cyan

$backupScript = @"
# Backup script for Noctis
`$date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
`$backupPath = "C:\Backups\Noctis\`$date"

# Create backup directory
New-Item -ItemType Directory -Path `$backupPath -Force

# Backup database
pg_dump -U noctis_user -h localhost noctis_db > "`$backupPath\database.sql"

# Backup media files
Copy-Item -Path "$appPath\media" -Destination "`$backupPath\media" -Recurse

# Backup application files
Copy-Item -Path "$appPath" -Destination "`$backupPath\application" -Recurse -Exclude "venv", "__pycache__"

Write-Host "Backup completed: `$backupPath"
"@

$backupScript | Out-File -FilePath "$appPath\backup.ps1" -Encoding UTF8

# Create backup directory
New-Item -ItemType Directory -Path "C:\Backups\Noctis" -Force | Out-Null

# Step 18: Test Installation
Write-Host "`nStep 18: Testing installation..." -ForegroundColor Cyan

# Test Django application
Write-Host "Testing Django application..." -ForegroundColor Yellow
python manage.py check --deploy

# Test web access
Write-Host "Testing web access..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing -TimeoutSec 10
    Write-Host "Web access test: SUCCESS" -ForegroundColor Green
} catch {
    Write-Host "Web access test: FAILED (this is normal if IIS needs to be restarted)" -ForegroundColor Yellow
}

# Step 19: Final Summary
Write-Host "`n=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
Write-Host "`nInstallation Summary:" -ForegroundColor Cyan
Write-Host "- Application Path: $appPath" -ForegroundColor White
Write-Host "- Web URL: http://$ServerIP" -ForegroundColor White
Write-Host "- Admin Username: admin" -ForegroundColor White
Write-Host "- Admin Password: $superuserPassword" -ForegroundColor White
Write-Host "- Database: PostgreSQL (noctis_db)" -ForegroundColor White
Write-Host "- Database User: noctis_user" -ForegroundColor White
Write-Host "- Database Password: $PostgresPassword" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Restart IIS: iisreset" -ForegroundColor Yellow
Write-Host "2. Access the application at http://$ServerIP" -ForegroundColor Yellow
Write-Host "3. Change default passwords" -ForegroundColor Yellow
Write-Host "4. Configure SSL certificate for production" -ForegroundColor Yellow
Write-Host "5. Set up monitoring and backup schedules" -ForegroundColor Yellow

Write-Host "`nTroubleshooting:" -ForegroundColor Cyan
Write-Host "- Check logs: $appPath\logs\noctis.log" -ForegroundColor White
Write-Host "- IIS logs: C:\inetpub\logs\LogFiles" -ForegroundColor White
Write-Host "- Restart IIS if needed: iisreset" -ForegroundColor White

Write-Host "`nDeployment completed successfully!" -ForegroundColor Green