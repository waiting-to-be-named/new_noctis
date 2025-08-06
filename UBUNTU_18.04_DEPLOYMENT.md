# NOCTIS DICOM Viewer - Ubuntu 18.04 VM Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the NOCTIS DICOM Viewer on Ubuntu 18.04 LTS virtual machine.

## Prerequisites

### System Requirements
- **OS**: Ubuntu 18.04 LTS (Bionic Beaver)
- **CPU**: Minimum 2 cores, recommended 4 cores
- **RAM**: Minimum 4GB, recommended 8GB
- **Storage**: Minimum 50GB, recommended 100GB SSD
- **Network**: Static IP address recommended

### Pre-deployment Checklist
1. Fresh Ubuntu 18.04 installation
2. Root or sudo access
3. Internet connectivity
4. VM network configured (bridged or NAT with port forwarding)

## Quick Deployment

### Option 1: Automated Deployment Script

1. **Transfer the application files to your VM**:
   ```bash
   # From your local machine
   scp -r /path/to/noctis-dicom-viewer/ user@vm-ip:/home/user/
   ```

2. **Run the deployment script**:
   ```bash
   # SSH into your VM
   ssh user@vm-ip
   
   # Navigate to the application directory
   cd /home/user/noctis-dicom-viewer/
   
   # Make the script executable
   chmod +x deploy_ubuntu_18.04.sh
   
   # Run the deployment script
   sudo ./deploy_ubuntu_18.04.sh
   ```

3. **Follow the prompts** to create a Django superuser when asked.

### Option 2: Manual Deployment

If you prefer manual deployment or need to customize the installation:

#### Step 1: System Update and Python 3.8 Installation

Ubuntu 18.04 comes with Python 3.6, but we need Python 3.8:

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python 3.8
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev
```

#### Step 2: Install System Dependencies

```bash
sudo apt install -y \
    build-essential \
    nginx \
    postgresql \
    postgresql-contrib \
    redis-server \
    git \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk
```

#### Step 3: Create Application User

```bash
# Create noctis user
sudo useradd -m -s /bin/bash noctis

# Create application directories
sudo mkdir -p /opt/noctis
sudo mkdir -p /opt/noctis/logs
sudo mkdir -p /opt/noctis/media/dicom_files
sudo mkdir -p /opt/noctis/staticfiles
```

#### Step 4: Copy Application Files

```bash
# Copy your application files to /opt/noctis
sudo cp -r /path/to/your/app/* /opt/noctis/
sudo chown -R noctis:noctis /opt/noctis
```

#### Step 5: Setup Python Environment

```bash
# Switch to noctis user
sudo su - noctis
cd /opt/noctis

# Create virtual environment
python3.8 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python packages
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn psycopg2-binary whitenoise

# Exit noctis user
exit
```

#### Step 6: PostgreSQL Setup

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE noctis_db;
CREATE USER noctis_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;
ALTER DATABASE noctis_db OWNER TO noctis_user;
\q
```

#### Step 7: Configure Application

Create `/opt/noctis/.env` file:

```bash
sudo nano /opt/noctis/.env
```

Add the following content:

```env
# Django settings
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key

# Database settings
DB_NAME=noctis_db
DB_USER=noctis_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis settings
REDIS_URL=redis://localhost:6379/1

# Allowed hosts (update with your VM's IP)
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_VM_IP

# DICOM settings
DICOM_STORAGE_PATH=/opt/noctis/media/dicom_files
SCP_AE_TITLE=NOCTIS_SCP
SCP_PORT=11112
```

Set proper permissions:
```bash
sudo chown noctis:noctis /opt/noctis/.env
sudo chmod 600 /opt/noctis/.env
```

#### Step 8: Django Setup

```bash
# Run as noctis user
sudo -u noctis bash -c "cd /opt/noctis && source venv/bin/activate && python manage.py makemigrations"
sudo -u noctis bash -c "cd /opt/noctis && source venv/bin/activate && python manage.py migrate"
sudo -u noctis bash -c "cd /opt/noctis && source venv/bin/activate && python manage.py createsuperuser"
sudo -u noctis bash -c "cd /opt/noctis && source venv/bin/activate && python manage.py collectstatic --noinput"
```

#### Step 9: Configure Services

Create systemd service files as shown in the deployment script, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable noctis noctis-scp
sudo systemctl start noctis noctis-scp
```

#### Step 10: Configure Nginx

Configure Nginx as shown in the deployment script, then:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## Post-Installation Configuration

### 1. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (if using SSL)
sudo ufw allow 11112/tcp # DICOM SCP
sudo ufw enable
```

### 2. Network Configuration for VM

If using VirtualBox:
- **Bridged Adapter**: Application accessible from network directly
- **NAT with Port Forwarding**: Configure port forwarding:
  - Host Port 8080 → Guest Port 80 (Web)
  - Host Port 11112 → Guest Port 11112 (DICOM)

If using VMware:
- Use **Bridged** networking for direct network access
- Or configure **NAT** with port forwarding similar to VirtualBox

### 3. SSL Certificate (Optional but Recommended)

For production use, install SSL certificate:

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com
```

## Accessing the Application

### Web Interface
- **URL**: `http://YOUR_VM_IP` or `http://localhost:8080` (if using port forwarding)
- **Admin Panel**: `http://YOUR_VM_IP/admin`

### DICOM SCP Configuration
- **AE Title**: NOCTIS_SCP
- **Port**: 11112
- **IP**: Your VM's IP address

## Testing the Deployment

### 1. Web Interface Test
```bash
# Check if services are running
sudo systemctl status noctis
sudo systemctl status nginx

# Test web access
curl http://localhost
```

### 2. DICOM Upload Test
1. Access the web interface
2. Navigate to the upload section
3. Upload a test DICOM file
4. Verify it appears in the worklist

### 3. DICOM SCP Test
```bash
# Check if SCP is listening
sudo netstat -tlnp | grep 11112

# Check SCP logs
tail -f /opt/noctis/logs/django.log
```

## Maintenance

### Log Files
```bash
# Application logs
tail -f /opt/noctis/logs/django.log

# Gunicorn logs
tail -f /opt/noctis/logs/gunicorn_access.log
tail -f /opt/noctis/logs/gunicorn_error.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Service Management
```bash
# Restart services
sudo systemctl restart noctis
sudo systemctl restart noctis-scp
sudo systemctl restart nginx

# Check service status
sudo systemctl status noctis
sudo systemctl status noctis-scp
```

### Database Backup
```bash
# Manual backup
pg_dump -U noctis_user -h localhost noctis_db > backup_$(date +%Y%m%d).sql

# Or use the provided backup script
/opt/noctis/backup.sh
```

### Updates
```bash
# Use the provided update script
/opt/noctis/update_app.sh
```

## Troubleshooting

### Common Issues

1. **Port 80 already in use**:
   ```bash
   sudo lsof -i :80
   sudo systemctl stop apache2  # If Apache is running
   ```

2. **Database connection errors**:
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Test database connection
   sudo -u noctis psql -U noctis_user -d noctis_db -h localhost
   ```

3. **Static files not loading**:
   ```bash
   # Re-collect static files
   cd /opt/noctis
   sudo -u noctis venv/bin/python manage.py collectstatic --noinput
   ```

4. **Permission errors**:
   ```bash
   # Fix ownership
   sudo chown -R noctis:noctis /opt/noctis
   ```

### Performance Tuning

For better performance on Ubuntu 18.04:

1. **PostgreSQL tuning** (`/etc/postgresql/10/main/postgresql.conf`):
   ```
   shared_buffers = 256MB
   effective_cache_size = 1GB
   work_mem = 4MB
   ```

2. **Nginx tuning** (`/etc/nginx/nginx.conf`):
   ```
   worker_processes auto;
   worker_connections 1024;
   ```

3. **System limits** (`/etc/security/limits.conf`):
   ```
   noctis soft nofile 65536
   noctis hard nofile 65536
   ```

## Security Considerations

1. **Change default passwords** immediately after installation
2. **Configure firewall** to restrict access
3. **Enable SSL/TLS** for production use
4. **Regular security updates**:
   ```bash
   sudo apt update
   sudo apt upgrade
   ```
5. **Monitor logs** for suspicious activity

## Support

If you encounter issues:
1. Check the log files first
2. Verify all services are running
3. Ensure firewall rules are correct
4. Check VM network configuration

## VM-Specific Optimizations

### VirtualBox Guest Additions (if using VirtualBox)
```bash
sudo apt install -y virtualbox-guest-dkms virtualbox-guest-utils
```

### VMware Tools (if using VMware)
```bash
sudo apt install -y open-vm-tools
```

These tools improve performance and integration with the host system.

---

**Note**: This deployment is configured for Ubuntu 18.04 LTS specifically. While the application supports newer Ubuntu versions, this guide addresses the specific requirements and limitations of Ubuntu 18.04.