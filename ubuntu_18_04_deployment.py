diff --git a/ubuntu_18_04_deployment.py b/ubuntu_18_04_deployment.py
--- a/ubuntu_18_04_deployment.py
+++ b/ubuntu_18_04_deployment.py
@@ -0,0 +1,606 @@
+#!/usr/bin/env python3
+"""
+Ubuntu 18.04 DICOM Viewer Deployment Script
+Includes free domain options and complete server setup
+"""
+
+import os
+import subprocess
+import sys
+from pathlib import Path
+
+class Ubuntu1804Deployer:
+    def __init__(self):
+        self.project_dir = Path("/opt/noctis-dicom")
+        self.user = "noctis"
+        self.free_domains = {
+            "freenom": ["tk", "ml", "ga", "cf"],
+            "noip": "noip.com",
+            "duckdns": "duckdns.org", 
+            "freedns": "freedns.afraid.org",
+            "dynv6": "dynv6.com"
+        }
+    
+    def update_system(self):
+        """Update Ubuntu 18.04 system packages"""
+        print("🔄 Updating Ubuntu 18.04 system...")
+        
+        commands = [
+            "sudo apt update",
+            "sudo apt upgrade -y",
+            "sudo apt install -y software-properties-common curl wget git",
+        ]
+        
+        for cmd in commands:
+            subprocess.run(cmd, shell=True, check=True)
+    
+    def install_python39(self):
+        """Install Python 3.9 on Ubuntu 18.04 (default is 3.6)"""
+        print("🐍 Installing Python 3.9...")
+        
+        commands = [
+            "sudo add-apt-repository ppa:deadsnakes/ppa -y",
+            "sudo apt update",
+            "sudo apt install -y python3.9 python3.9-venv python3.9-dev python3-pip",
+            "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1",
+            "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2",
+            "sudo update-alternatives --config python3"
+        ]
+        
+        for cmd in commands:
+            subprocess.run(cmd, shell=True, check=True)
+    
+    def install_nginx(self):
+        """Install and configure Nginx"""
+        print("🌐 Installing Nginx...")
+        
+        subprocess.run("sudo apt install -y nginx", shell=True, check=True)
+        subprocess.run("sudo systemctl enable nginx", shell=True, check=True)
+        subprocess.run("sudo systemctl start nginx", shell=True, check=True)
+    
+    def install_postgresql(self):
+        """Install PostgreSQL for production database"""
+        print("🗄️ Installing PostgreSQL...")
+        
+        commands = [
+            "sudo apt install -y postgresql postgresql-contrib",
+            "sudo systemctl enable postgresql",
+            "sudo systemctl start postgresql"
+        ]
+        
+        for cmd in commands:
+            subprocess.run(cmd, shell=True, check=True)
+    
+    def setup_database(self):
+        """Setup PostgreSQL database"""
+        print("📊 Setting up database...")
+        
+        db_commands = [
+            "sudo -u postgres createuser --interactive noctis_user",
+            "sudo -u postgres createdb noctis_db -O noctis_user",
+            "sudo -u postgres psql -c \"ALTER USER noctis_user PASSWORD 'secure_password_here';\""
+        ]
+        
+        for cmd in db_commands:
+            try:
+                subprocess.run(cmd, shell=True, check=True)
+            except subprocess.CalledProcessError:
+                print(f"⚠️ Command may have failed (might already exist): {cmd}")
+    
+    def create_system_user(self):
+        """Create system user for the application"""
+        print("👤 Creating system user...")
+        
+        commands = [
+            f"sudo useradd --system --shell /bin/bash --home-dir {self.project_dir} --create-home {self.user}",
+            f"sudo usermod -aG www-data {self.user}"
+        ]
+        
+        for cmd in commands:
+            try:
+                subprocess.run(cmd, shell=True, check=True)
+            except subprocess.CalledProcessError:
+                print(f"⚠️ User may already exist: {cmd}")
+    
+    def setup_project_directory(self):
+        """Setup project directory structure"""
+        print("📁 Setting up project directory...")
+        
+        directories = [
+            self.project_dir,
+            self.project_dir / "logs",
+            self.project_dir / "static",
+            self.project_dir / "media",
+            self.project_dir / "media/dicom_files",
+            self.project_dir / "backups"
+        ]
+        
+        for directory in directories:
+            directory.mkdir(parents=True, exist_ok=True)
+        
+        subprocess.run(f"sudo chown -R {self.user}:www-data {self.project_dir}", shell=True, check=True)
+        subprocess.run(f"sudo chmod -R 755 {self.project_dir}", shell=True, check=True)
+    
+    def create_production_settings(self):
+        """Create production settings for Ubuntu 18.04"""
+        print("⚙️ Creating production settings...")
+        
+        settings_content = '''"""
+Production settings for Ubuntu 18.04 deployment with free domain options
+"""
+
+import os
+from pathlib import Path
+
+# Build paths inside the project like this: BASE_DIR / 'subdir'.
+BASE_DIR = Path(__file__).resolve().parent.parent
+
+# SECURITY WARNING: keep the secret key used in production secret!
+SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'your-very-secure-secret-key-here')
+
+# SECURITY WARNING: don't run with debug turned on in production!
+DEBUG = False
+
+# Free domain options - update with your chosen free domain
+ALLOWED_HOSTS = [
+    'localhost',
+    '127.0.0.1',
+    '10.0.2.15',  # Replace with your server IP
+    # Free domain options:
+    'yourname.tk',        # Freenom .tk domain
+    'yourname.ml',        # Freenom .ml domain  
+    'yourname.ga',        # Freenom .ga domain
+    'yourname.cf',        # Freenom .cf domain
+    'yourname.noip.me',   # No-IP free subdomain
+    'yourname.duckdns.org', # DuckDNS free subdomain
+    'yourname.dynv6.net', # DynV6 free subdomain
+]
+
+INSTALLED_APPS = [
+    'django.contrib.admin',
+    'django.contrib.auth',
+    'django.contrib.contenttypes',
+    'django.contrib.sessions',
+    'django.contrib.messages',
+    'django.contrib.staticfiles',
+    'viewer',
+    'worklist',
+    'rest_framework',
+]
+
+MIDDLEWARE = [
+    'django.middleware.security.SecurityMiddleware',
+    'django.contrib.sessions.middleware.SessionMiddleware',
+    'django.middleware.common.CommonMiddleware',
+    'django.middleware.csrf.CsrfViewMiddleware',
+    'django.contrib.auth.middleware.AuthenticationMiddleware',
+    'django.contrib.messages.middleware.MessageMiddleware',
+    'django.middleware.clickjacking.XFrameOptionsMiddleware',
+    'noctisview.middleware.CORSMiddleware',
+    'noctisview.middleware.SecurityHeadersMiddleware',
+    'noctisview.middleware.RequestLoggingMiddleware',
+    'noctisview.middleware.PerformanceMiddleware',
+    'noctisview.middleware.APIErrorMiddleware',
+    'noctisview.middleware.CSRFMiddleware',
+]
+
+ROOT_URLCONF = 'noctisview.urls'
+
+TEMPLATES = [
+    {
+        'BACKEND': 'django.template.backends.django.DjangoTemplates',
+        'DIRS': [BASE_DIR / 'templates'],
+        'APP_DIRS': True,
+        'OPTIONS': {
+            'context_processors': [
+                'django.template.context_processors.debug',
+                'django.template.context_processors.request',
+                'django.contrib.auth.context_processors.auth',
+                'django.contrib.messages.context_processors.messages',
+            ],
+        },
+    },
+]
+
+WSGI_APPLICATION = 'noctisview.wsgi.application'
+
+# Database for production
+DATABASES = {
+    'default': {
+        'ENGINE': 'django.db.backends.postgresql',
+        'NAME': os.getenv('DB_NAME', 'noctis_db'),
+        'USER': os.getenv('DB_USER', 'noctis_user'),
+        'PASSWORD': os.getenv('DB_PASSWORD', 'secure_password_here'),
+        'HOST': os.getenv('DB_HOST', 'localhost'),
+        'PORT': os.getenv('DB_PORT', '5432'),
+        'OPTIONS': {
+            'connect_timeout': 60,
+        },
+    }
+}
+
+# Password validation
+AUTH_PASSWORD_VALIDATORS = [
+    {
+        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
+    },
+    {
+        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
+    },
+    {
+        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
+    },
+    {
+        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
+    },
+]
+
+# Internationalization
+LANGUAGE_CODE = 'en-us'
+TIME_ZONE = 'UTC'
+USE_I18N = True
+USE_TZ = True
+
+# Static files (CSS, JavaScript, Images)
+STATIC_URL = '/static/'
+STATIC_ROOT = '/opt/noctis-dicom/static'
+STATICFILES_DIRS = [
+    BASE_DIR / 'static',
+]
+
+# Media files
+MEDIA_URL = '/media/'
+MEDIA_ROOT = '/opt/noctis-dicom/media'
+
+# DICOM specific settings
+DICOM_UPLOAD_PATH = 'dicom_files/'
+MAX_DICOM_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
+
+# File upload settings
+FILE_UPLOAD_HANDLERS = [
+    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
+    'django.core.files.uploadhandler.MemoryFileUploadHandler',
+]
+
+DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
+FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024       # 100MB
+DATA_UPLOAD_MAX_NUMBER_FIELDS = None
+DATA_UPLOAD_MAX_NUMBER_FILES = None
+
+# Security settings for production
+SECURE_BROWSER_XSS_FILTER = True
+SECURE_CONTENT_TYPE_NOSNIFF = True
+SECURE_HSTS_SECONDS = 31536000
+SECURE_HSTS_INCLUDE_SUBDOMAINS = True
+SECURE_HSTS_PRELOAD = True
+
+# Only enable SSL redirect if using HTTPS
+# SECURE_SSL_REDIRECT = True
+# SESSION_COOKIE_SECURE = True
+# CSRF_COOKIE_SECURE = True
+
+# REST Framework settings
+REST_FRAMEWORK = {
+    'DEFAULT_PERMISSION_CLASSES': [
+        'rest_framework.permissions.AllowAny',
+    ]
+}
+
+# Logging
+LOGGING = {
+    'version': 1,
+    'disable_existing_loggers': False,
+    'formatters': {
+        'verbose': {
+            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
+            'style': '{',
+        },
+    },
+    'handlers': {
+        'file': {
+            'level': 'INFO',
+            'class': 'logging.FileHandler',
+            'filename': '/opt/noctis-dicom/logs/django.log',
+            'formatter': 'verbose',
+        },
+    },
+    'loggers': {
+        'django': {
+            'handlers': ['file'],
+            'level': 'INFO',
+            'propagate': True,
+        },
+    },
+}
+
+DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
+'''
+        
+        settings_path = self.project_dir / "production_settings.py"
+        with open(settings_path, 'w') as f:
+            f.write(settings_content)
+        
+        subprocess.run(f"sudo chown {self.user}:www-data {settings_path}", shell=True, check=True)
+    
+    def create_nginx_config(self):
+        """Create Nginx configuration for free domains"""
+        print("🌐 Creating Nginx configuration...")
+        
+        nginx_config = '''server {
+    listen 80;
+    server_name localhost your-server-ip yourname.tk yourname.ml yourname.ga yourname.cf yourname.noip.me yourname.duckdns.org yourname.dynv6.net;
+    
+    client_max_body_size 5G;
+    client_body_timeout 300s;
+    client_header_timeout 300s;
+    proxy_connect_timeout 300s;
+    proxy_send_timeout 300s;
+    proxy_read_timeout 300s;
+    
+    location /static/ {
+        alias /opt/noctis-dicom/static/;
+        expires 30d;
+        add_header Cache-Control "public, immutable";
+    }
+    
+    location /media/ {
+        alias /opt/noctis-dicom/media/;
+        expires 7d;
+        add_header Cache-Control "public";
+    }
+    
+    location / {
+        proxy_pass http://127.0.0.1:8000;
+        proxy_set_header Host $host;
+        proxy_set_header X-Real-IP $remote_addr;
+        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
+        proxy_set_header X-Forwarded-Proto $scheme;
+        
+        # WebSocket support
+        proxy_http_version 1.1;
+        proxy_set_header Upgrade $http_upgrade;
+        proxy_set_header Connection "upgrade";
+    }
+}'''
+        
+        config_path = "/etc/nginx/sites-available/noctis-dicom"
+        with open(config_path, 'w') as f:
+            f.write(nginx_config)
+        
+        # Enable site
+        subprocess.run(f"sudo ln -sf {config_path} /etc/nginx/sites-enabled/", shell=True, check=True)
+        subprocess.run("sudo rm -f /etc/nginx/sites-enabled/default", shell=True, check=True)
+        subprocess.run("sudo nginx -t", shell=True, check=True)
+        subprocess.run("sudo systemctl reload nginx", shell=True, check=True)
+    
+    def create_systemd_service(self):
+        """Create systemd service for the Django application"""
+        print("⚙️ Creating systemd service...")
+        
+        service_content = f'''[Unit]
+Description=Noctis DICOM Viewer
+After=network.target postgresql.service
+
+[Service]
+Type=exec
+User={self.user}
+Group=www-data
+WorkingDirectory={self.project_dir}
+Environment=DJANGO_SETTINGS_MODULE=noctisview.production_settings
+Environment=PYTHONPATH={self.project_dir}
+ExecStart={self.project_dir}/venv/bin/python {self.project_dir}/manage.py runserver 127.0.0.1:8000
+ExecReload=/bin/kill -s HUP $MAINPID
+Restart=always
+RestartSec=10
+
+[Install]
+WantedBy=multi-user.target'''
+        
+        service_path = "/etc/systemd/system/noctis-dicom.service"
+        with open(service_path, 'w') as f:
+            f.write(service_content)
+        
+        subprocess.run("sudo systemctl daemon-reload", shell=True, check=True)
+        subprocess.run("sudo systemctl enable noctis-dicom", shell=True, check=True)
+    
+    def create_environment_file(self):
+        """Create environment configuration file"""
+        print("📝 Creating environment file...")
+        
+        env_content = '''# Environment variables for Noctis DICOM Viewer
+DJANGO_SECRET_KEY=your-very-secure-secret-key-here
+DB_NAME=noctis_db
+DB_USER=noctis_user
+DB_PASSWORD=secure_password_here
+DB_HOST=localhost
+DB_PORT=5432
+
+# Free domain options (uncomment and configure as needed)
+# DOMAIN_TYPE=freenom
+# DOMAIN_NAME=yourname.tk
+# NOIP_USERNAME=your_noip_username
+# NOIP_PASSWORD=your_noip_password
+# DUCKDNS_TOKEN=your_duckdns_token
+'''
+        
+        env_path = self.project_dir / ".env"
+        with open(env_path, 'w') as f:
+            f.write(env_content)
+        
+        subprocess.run(f"sudo chown {self.user}:www-data {env_path}", shell=True, check=True)
+        subprocess.run(f"sudo chmod 600 {env_path}", shell=True, check=True)
+    
+    def create_deployment_script(self):
+        """Create deployment and update script"""
+        print("📜 Creating deployment script...")
+        
+        deploy_script = f'''#!/bin/bash
+# Noctis DICOM Viewer Deployment Script for Ubuntu 18.04
+
+set -e
+
+PROJECT_DIR="{self.project_dir}"
+USER="{self.user}"
+
+echo "🚀 Starting deployment..."
+
+# Navigate to project directory
+cd $PROJECT_DIR
+
+# Activate virtual environment
+source venv/bin/activate
+
+# Pull latest code (if using git)
+# git pull origin main
+
+# Install/update dependencies
+pip install -r requirements.txt
+
+# Run database migrations
+python manage.py makemigrations
+python manage.py migrate
+
+# Collect static files
+python manage.py collectstatic --noinput
+
+# Create superuser if it doesn't exist
+echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell
+
+# Restart services
+sudo systemctl restart noctis-dicom
+sudo systemctl reload nginx
+
+echo "✅ Deployment completed successfully!"
+echo "🌐 Access your application at:"
+echo "   - http://localhost"
+echo "   - http://your-server-ip"
+echo "   - http://your-free-domain.tk (configure your free domain)"
+
+# Check service status
+echo "📊 Service status:"
+sudo systemctl status noctis-dicom --no-pager -l
+'''
+        
+        script_path = self.project_dir / "deploy.sh"
+        with open(script_path, 'w') as f:
+            f.write(deploy_script)
+        
+        subprocess.run(f"sudo chmod +x {script_path}", shell=True, check=True)
+        subprocess.run(f"sudo chown {self.user}:www-data {script_path}", shell=True, check=True)
+    
+    def install_free_domain_tools(self):
+        """Install tools for managing free domains"""
+        print("🌍 Installing free domain management tools...")
+        
+        # Install ddclient for dynamic DNS updates
+        subprocess.run("sudo apt install -y ddclient", shell=True, check=True)
+        
+        # Create ddclient configuration template
+        ddclient_config = '''# DuckDNS configuration
+protocol=duckdns
+server=www.duckdns.org
+login=noctisview
+password=9d40387a-ac37-4268-8d51-69985ae32c30
+noctisview.duckdns.org
+
+# No-IP configuration  
+# protocol=noip
+# server=dynupdate.no-ip.com
+# login=your-username
+# password=your-password
+# your-hostname.no-ip.me
+
+# DynV6 configuration
+# protocol=dyndns2
+# server=dynv6.com
+# login=your-hostname
+# password=your-token
+# your-hostname.dynv6.net
+'''
+        
+        with open("/etc/ddclient.conf", 'w') as f:
+            f.write(ddclient_config)
+        
+        subprocess.run("sudo chmod 600 /etc/ddclient.conf", shell=True, check=True)
+    
+    def display_free_domain_options(self):
+        """Display information about free domain options"""
+        print("\n" + "="*60)
+        print("🆓 FREE DOMAIN OPTIONS FOR YOUR DICOM VIEWER")
+        print("="*60)
+        
+        print("\n1. 🌐 FREENOM DOMAINS (Free for 1 year)")
+        print("   - Visit: freenom.com")
+        print("   - Available TLDs: .tk, .ml, .ga, .cf")
+        print("   - How to: Search for available domain → Register → Point to your IP")
+        
+        print("\n2. 🦆 DUCKDNS (Free subdomain)")
+        print("   - Visit: duckdns.org")
+        print("   - Format: yourname.duckdns.org")
+        print("   - How to: Sign up → Create subdomain → Get token")
+        
+        print("\n3. 🌍 NO-IP (Free subdomain)")
+        print("   - Visit: noip.com")
+        print("   - Format: yourname.noip.me")
+        print("   - How to: Create account → Add hostname → Install client")
+        
+        print("\n4. ⚡ DYNV6 (Free IPv6/IPv4)")
+        print("   - Visit: dynv6.com")
+        print("   - Format: yourname.dynv6.net")
+        print("   - How to: Register → Create zone → Get update token")
+        
+        print("\n5. 😱 AFRAID.ORG (Free DNS hosting)")
+        print("   - Visit: freedns.afraid.org")
+        print("   - Multiple subdomain options")
+        print("   - How to: Register → Choose subdomain → Configure")
+        
+        print("\n" + "="*60)
+        print("📋 SETUP STEPS AFTER CHOOSING A FREE DOMAIN:")
+        print("="*60)
+        print("1. Register for your chosen free domain service")
+        print("2. Point the domain to your Ubuntu server IP")
+        print("3. Update ALLOWED_HOSTS in production_settings.py")
+        print("4. Update Nginx configuration with your domain")
+        print("5. Restart Nginx: sudo systemctl reload nginx")
+        print("6. (Optional) Setup SSL with Let's Encrypt")
+    
+    def full_deployment(self):
+        """Run complete deployment process"""
+        print("🚀 Starting Ubuntu 18.04 deployment for Noctis DICOM Viewer")
+        print("=" * 60)
+        
+        try:
+            self.update_system()
+            self.install_python39()
+            self.install_nginx()
+            self.install_postgresql()
+            self.create_system_user()
+            self.setup_project_directory()
+            self.setup_database()
+            self.create_production_settings()
+            self.create_nginx_config()
+            self.create_systemd_service()
+            self.create_environment_file()
+            self.create_deployment_script()
+            self.install_free_domain_tools()
+            
+            print("\n✅ Ubuntu 18.04 deployment setup completed!")
+            print(f"📁 Project directory: {self.project_dir}")
+            print(f"👤 System user: {self.user}")
+            
+            self.display_free_domain_options()
+            
+            print("\n🔧 NEXT STEPS:")
+            print("1. Copy your Django project files to /opt/noctis-dicom/")
+            print("2. Create virtual environment: python3.9 -m venv /opt/noctis-dicom/venv")
+            print("3. Install requirements: /opt/noctis-dicom/venv/bin/pip install -r requirements.txt")
+            print("4. Run deployment script: /opt/noctis-dicom/deploy.sh")
+            print("5. Choose and configure a free domain from the options above")
+            
+        except Exception as e:
+            print(f"❌ Deployment failed: {e}")
+            sys.exit(1)
+
+if __name__ == "__main__":
+    deployer = Ubuntu1804Deployer()
+    deployer.full_deployment()
