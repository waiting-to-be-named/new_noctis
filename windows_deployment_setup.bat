@echo off
REM Noctis System Windows Server 2012 Deployment Setup Script
REM This script automates the initial setup process for Noctis deployment

echo ========================================
echo Noctis System Deployment Setup
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - OK
) else (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo.
echo Step 1: Creating project directory...
if not exist "C:\Noctis" (
    mkdir "C:\Noctis"
    echo Created C:\Noctis directory
) else (
    echo C:\Noctis directory already exists
)

echo.
echo Step 2: Checking Python installation...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo Python is installed
    python --version
) else (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo.
echo Step 3: Checking Git installation...
git --version >nul 2>&1
if %errorLevel% == 0 (
    echo Git is installed
    git --version
) else (
    echo ERROR: Git is not installed
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

echo.
echo Step 4: Creating virtual environment...
cd /d "C:\Noctis"
if not exist "venv" (
    python -m venv venv
    echo Created virtual environment
) else (
    echo Virtual environment already exists
)

echo.
echo Step 5: Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
echo Virtual environment activated

echo.
echo Step 6: Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Step 7: Installing required packages...
pip install python-dotenv
pip install pywin32

echo.
echo Step 8: Creating required directories...
if not exist "media" mkdir media
if not exist "media\dicom_files" mkdir media\dicom_files
if not exist "media\temp" mkdir media\temp
if not exist "logs" mkdir logs

echo.
echo Step 9: Creating environment file template...
if not exist ".env" (
    echo Creating .env file template...
    (
        echo SECRET_KEY=your-secret-key-here-change-this
        echo DEBUG=False
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo DATABASE_URL=sqlite:///db.sqlite3
    ) > .env
    echo Created .env file template
) else (
    echo .env file already exists
)

echo.
echo Step 10: Creating Windows service configuration...
if not exist "gunicorn.conf.py" (
    echo Creating Gunicorn configuration...
    (
        echo bind = "127.0.0.1:8000"
        echo workers = 4
        echo worker_class = "sync"
        echo worker_connections = 1000
        echo timeout = 30
        echo keepalive = 2
        echo max_requests = 1000
        echo max_requests_jitter = 50
        echo preload_app = True
    ) > gunicorn.conf.py
    echo Created gunicorn.conf.py
) else (
    echo gunicorn.conf.py already exists
)

echo.
echo Step 11: Creating Nginx configuration template...
if not exist "nginx.conf.template" (
    echo Creating Nginx configuration template...
    (
        echo worker_processes  1;
        echo.
        echo events {
        echo     worker_connections  1024;
        echo }
        echo.
        echo http {
        echo     include       mime.types;
        echo     default_type  application/octet-stream;
        echo.
        echo     sendfile        on;
        echo     keepalive_timeout  65;
        echo.
        echo     server {
        echo         listen       80;
        echo         server_name  localhost;
        echo.
        echo         location /static/ {
        echo             alias C:/Noctis/staticfiles/;
        echo         }
        echo.
        echo         location /media/ {
        echo             alias C:/Noctis/media/;
        echo         }
        echo.
        echo         location / {
        echo             proxy_pass http://127.0.0.1:8000;
        echo             proxy_set_header Host $host;
        echo             proxy_set_header X-Real-IP $remote_addr;
        echo             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        echo             proxy_set_header X-Forwarded-Proto $scheme;
        echo         }
        echo     }
        echo }
    ) > nginx.conf.template
    echo Created nginx.conf.template
) else (
    echo nginx.conf.template already exists
)

echo.
echo Step 12: Creating service installation script...
if not exist "install_services.bat" (
    echo Creating service installation script...
    (
        echo @echo off
        echo REM Service installation script for Noctis
        echo echo Installing Noctis services...
        echo.
        echo REM Install Gunicorn service
        echo C:\nssm\nssm.exe install NoctisGunicorn "C:\Noctis\venv\Scripts\gunicorn.exe" "noctisview.wsgi:application --config gunicorn.conf.py"
        echo C:\nssm\nssm.exe set NoctisGunicorn AppDirectory "C:\Noctis"
        echo C:\nssm\nssm.exe set NoctisGunicorn AppEnvironmentExtra PYTHONPATH=C:\Noctis
        echo.
        echo REM Install Nginx service
        echo C:\nssm\nssm.exe install NoctisNginx "C:\nginx\nginx.exe"
        echo C:\nssm\nssm.exe set NoctisNginx AppDirectory "C:\nginx"
        echo.
        echo echo Services installed successfully
        echo echo To start services, run: net start NoctisGunicorn ^&^& net start NoctisNginx
        echo pause
    ) > install_services.bat
    echo Created install_services.bat
) else (
    echo install_services.bat already exists
)

echo.
echo Step 13: Creating firewall configuration script...
if not exist "configure_firewall.bat" (
    echo Creating firewall configuration script...
    (
        echo @echo off
        echo REM Firewall configuration for Noctis
        echo echo Configuring Windows Firewall for Noctis...
        echo.
        echo REM Allow HTTP traffic
        echo netsh advfirewall firewall add rule name="Noctis HTTP" dir=in action=allow protocol=TCP localport=80
        echo.
        echo REM Allow HTTPS traffic
        echo netsh advfirewall firewall add rule name="Noctis HTTPS" dir=in action=allow protocol=TCP localport=443
        echo.
        echo REM Allow Django development server
        echo netsh advfirewall firewall add rule name="Noctis Django" dir=in action=allow protocol=TCP localport=8000
        echo.
        echo echo Firewall rules configured successfully
        echo pause
    ) > configure_firewall.bat
    echo Created configure_firewall.bat
) else (
    echo configure_firewall.bat already exists
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Clone your Noctis repository to C:\Noctis
echo 2. Run: cd C:\Noctis ^&^& venv\Scripts\activate
echo 3. Run: pip install -r requirements.txt
echo 4. Run: python manage.py makemigrations
echo 5. Run: python manage.py migrate
echo 6. Run: python manage.py createsuperuser
echo 7. Run: python manage.py collectstatic
echo 8. Test with: python manage.py runserver 0.0.0.0:8000
echo.
echo For production deployment:
echo 1. Install NSSM: https://nssm.cc/
echo 2. Install Nginx for Windows
echo 3. Run: configure_firewall.bat
echo 4. Run: install_services.bat
echo.
echo For detailed instructions, see: WINDOWS_SERVER_2012_DEPLOYMENT_GUIDE.md
echo.
pause