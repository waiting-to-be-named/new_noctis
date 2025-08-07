# Noctis System Deployment PowerShell Script
# This script provides advanced deployment and configuration options

param(
    [string]$Environment = "development",
    [string]$DatabaseType = "sqlite",
    [string]$WebServer = "gunicorn",
    [switch]$InstallServices,
    [switch]$ConfigureFirewall,
    [switch]$OptimizePerformance
)

# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

Write-Host "========================================" -ForegroundColor Green
Write-Host "Noctis System Deployment Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as administrator'" -ForegroundColor Yellow
    exit 1
}

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to install Chocolatey if not present
function Install-Chocolatey {
    if (-not (Test-Command choco)) {
        Write-Host "Installing Chocolatey package manager..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    } else {
        Write-Host "Chocolatey is already installed" -ForegroundColor Green
    }
}

# Function to install Python dependencies
function Install-PythonDependencies {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    
    # Install Visual C++ Build Tools
    if (-not (Test-Command cl)) {
        Write-Host "Installing Visual Studio Build Tools..." -ForegroundColor Yellow
        choco install visualstudio2019buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools" -y
    }
    
    # Install Python packages
    if (Test-Path "C:\Noctis\venv\Scripts\Activate.ps1") {
        & "C:\Noctis\venv\Scripts\Activate.ps1"
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install python-dotenv pywin32 gunicorn
    } else {
        Write-Host "Virtual environment not found. Please run the setup script first." -ForegroundColor Red
        exit 1
    }
}

# Function to configure database
function Set-DatabaseConfiguration {
    param($DatabaseType)
    
    Write-Host "Configuring database: $DatabaseType" -ForegroundColor Yellow
    
    if ($DatabaseType -eq "postgresql") {
        # Install PostgreSQL
        if (-not (Test-Command psql)) {
            Write-Host "Installing PostgreSQL..." -ForegroundColor Yellow
            choco install postgresql -y
        }
        
        # Create database and user
        $env:PGPASSWORD = "postgres"
        psql -U postgres -c "CREATE DATABASE noctis_db;"
        psql -U postgres -c "CREATE USER noctis_user WITH PASSWORD 'noctis_password';"
        psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;"
        
        # Update settings
        $settingsContent = @"
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'noctis_db',
        'USER': 'noctis_user',
        'PASSWORD': 'noctis_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
"@
        
        # Update settings.py
        $settingsFile = "C:\Noctis\noctisview\settings.py"
        $content = Get-Content $settingsFile -Raw
        $content = $content -replace 'DATABASES = \{.*?\}', $settingsContent
        Set-Content $settingsFile $content
    }
}

# Function to configure web server
function Set-WebServerConfiguration {
    param($WebServer)
    
    Write-Host "Configuring web server: $WebServer" -ForegroundColor Yellow
    
    if ($WebServer -eq "nginx") {
        # Install Nginx
        if (-not (Test-Path "C:\nginx")) {
            Write-Host "Installing Nginx..." -ForegroundColor Yellow
            $nginxUrl = "http://nginx.org/download/nginx-1.24.0.zip"
            $nginxZip = "C:\nginx.zip"
            Invoke-WebRequest -Uri $nginxUrl -OutFile $nginxZip
            Expand-Archive -Path $nginxZip -DestinationPath "C:\" -Force
            Rename-Item "C:\nginx-1.24.0" "C:\nginx"
            Remove-Item $nginxZip
        }
        
        # Copy Nginx configuration
        if (Test-Path "C:\Noctis\nginx.conf.template") {
            Copy-Item "C:\Noctis\nginx.conf.template" "C:\nginx\conf\nginx.conf"
        }
    }
}

# Function to install Windows services
function Install-WindowsServices {
    Write-Host "Installing Windows services..." -ForegroundColor Yellow
    
    # Install NSSM if not present
    if (-not (Test-Path "C:\nssm\nssm.exe")) {
        Write-Host "Installing NSSM..." -ForegroundColor Yellow
        $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $nssmZip = "C:\nssm.zip"
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        Expand-Archive -Path $nssmZip -DestinationPath "C:\" -Force
        Remove-Item $nssmZip
    }
    
    # Install Gunicorn service
    & "C:\nssm\nssm.exe" install NoctisGunicorn "C:\Noctis\venv\Scripts\gunicorn.exe" "noctisview.wsgi:application --config gunicorn.conf.py"
    & "C:\nssm\nssm.exe" set NoctisGunicorn AppDirectory "C:\Noctis"
    & "C:\nssm\nssm.exe" set NoctisGunicorn AppEnvironmentExtra PYTHONPATH=C:\Noctis
    
    # Install Nginx service
    if (Test-Path "C:\nginx\nginx.exe") {
        & "C:\nssm\nssm.exe" install NoctisNginx "C:\nginx\nginx.exe"
        & "C:\nssm\nssm.exe" set NoctisNginx AppDirectory "C:\nginx"
    }
    
    Write-Host "Services installed successfully" -ForegroundColor Green
}

# Function to configure firewall
function Set-FirewallConfiguration {
    Write-Host "Configuring Windows Firewall..." -ForegroundColor Yellow
    
    # Allow HTTP traffic
    New-NetFirewallRule -DisplayName "Noctis HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
    
    # Allow HTTPS traffic
    New-NetFirewallRule -DisplayName "Noctis HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
    
    # Allow Django development server
    New-NetFirewallRule -DisplayName "Noctis Django" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
    
    Write-Host "Firewall rules configured successfully" -ForegroundColor Green
}

# Function to optimize performance
function Optimize-SystemPerformance {
    Write-Host "Optimizing system performance..." -ForegroundColor Yellow
    
    # Disable unnecessary services
    $servicesToDisable = @(
        "Themes",
        "TabletInputService",
        "WSearch",
        "SysMain"
    )
    
    foreach ($service in $servicesToDisable) {
        Set-Service -Name $service -StartupType Disabled -ErrorAction SilentlyContinue
    }
    
    # Optimize virtual memory
    $computerSystem = Get-WmiObject -Class Win32_ComputerSystem
    $totalMemory = [math]::Round($computerSystem.TotalPhysicalMemory / 1GB)
    $pageFileSize = $totalMemory * 1.5
    
    $pageFile = Get-WmiObject -Class Win32_PageFileSetting
    $pageFile.InitialSize = $pageFileSize
    $pageFile.MaximumSize = $pageFileSize
    $pageFile.Put()
    
    # Optimize disk performance
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
    if ($disk) {
        $disk.Compress = $false
        $disk.Put()
    }
    
    Write-Host "System performance optimized" -ForegroundColor Green
}

# Function to create backup script
function New-BackupScript {
    Write-Host "Creating backup script..." -ForegroundColor Yellow
    
    $backupScript = @"
@echo off
REM Noctis System Backup Script
echo Creating backup...

set BACKUP_DIR=C:\Noctis\backups
set DATE_TIME=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set DATE_TIME=%DATE_TIME: =0%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Backup database
if exist "C:\Noctis\db.sqlite3" (
    copy "C:\Noctis\db.sqlite3" "%BACKUP_DIR%\db_%DATE_TIME%.sqlite3"
)

REM Backup media files
if exist "C:\Noctis\media" (
    xcopy "C:\Noctis\media" "%BACKUP_DIR%\media_%DATE_TIME%\" /E /I /Y
)

REM Backup configuration files
if exist "C:\Noctis\.env" (
    copy "C:\Noctis\.env" "%BACKUP_DIR%\env_%DATE_TIME%.txt"
)

echo Backup completed: %BACKUP_DIR%
pause
"@
    
    Set-Content -Path "C:\Noctis\backup.bat" -Value $backupScript
    Write-Host "Backup script created: C:\Noctis\backup.bat" -ForegroundColor Green
}

# Function to create monitoring script
function New-MonitoringScript {
    Write-Host "Creating monitoring script..." -ForegroundColor Yellow
    
    $monitoringScript = @"
@echo off
REM Noctis System Monitoring Script
echo Checking Noctis system status...

REM Check if services are running
sc query NoctisGunicorn | find "RUNNING" >nul
if %errorlevel% equ 0 (
    echo Gunicorn service: RUNNING
) else (
    echo Gunicorn service: STOPPED
)

sc query NoctisNginx | find "RUNNING" >nul
if %errorlevel% equ 0 (
    echo Nginx service: RUNNING
) else (
    echo Nginx service: STOPPED
)

REM Check disk space
for /f "tokens=3" %%a in ('dir C:\ ^| find "bytes free"') do set FREE_SPACE=%%a
echo Free disk space: %FREE_SPACE%

REM Check memory usage
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:table

REM Check recent log entries
if exist "C:\Noctis\logs\django.log" (
    echo Recent log entries:
    tail -n 10 "C:\Noctis\logs\django.log"
)

pause
"@
    
    Set-Content -Path "C:\Noctis\monitor.bat" -Value $monitoringScript
    Write-Host "Monitoring script created: C:\Noctis\monitor.bat" -ForegroundColor Green
}

# Main execution
try {
    Write-Host "Starting Noctis deployment..." -ForegroundColor Green
    
    # Install Chocolatey
    Install-Chocolatey
    
    # Install Python dependencies
    Install-PythonDependencies
    
    # Configure database
    Set-DatabaseConfiguration -DatabaseType $DatabaseType
    
    # Configure web server
    Set-WebServerConfiguration -WebServer $WebServer
    
    # Install services if requested
    if ($InstallServices) {
        Install-WindowsServices
    }
    
    # Configure firewall if requested
    if ($ConfigureFirewall) {
        Set-FirewallConfiguration
    }
    
    # Optimize performance if requested
    if ($OptimizePerformance) {
        Optimize-SystemPerformance
    }
    
    # Create utility scripts
    New-BackupScript
    New-MonitoringScript
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Deployment completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Run Django migrations: python manage.py migrate" -ForegroundColor White
    Write-Host "2. Create superuser: python manage.py createsuperuser" -ForegroundColor White
    Write-Host "3. Collect static files: python manage.py collectstatic" -ForegroundColor White
    Write-Host "4. Test the application: python manage.py runserver 0.0.0.0:8000" -ForegroundColor White
    Write-Host ""
    Write-Host "Utility scripts created:" -ForegroundColor Yellow
    Write-Host "- C:\Noctis\backup.bat (Backup system)" -ForegroundColor White
    Write-Host "- C:\Noctis\monitor.bat (Monitor system)" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}