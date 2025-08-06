#!/bin/bash
#
# Noctis PACS Production Deployment Script for Ubuntu Server 24.04
# This script sets up a complete production environment for Noctis PACS
#
# Usage: sudo bash deploy_ubuntu_production.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration variables
DOMAIN_NAME=""
ADMIN_EMAIL=""
DB_NAME="noctis_db"
DB_USER="noctis_user"
DB_PASSWORD=""
APP_USER="noctis"
APP_DIR="/opt/noctis"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/noctis"
BACKUP_DIR="/var/backups/noctis"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# Get configuration from user
read -p "Enter domain name (e.g., pacs.example.com): " DOMAIN_NAME
read -p "Enter admin email for SSL certificates: " ADMIN_EMAIL
read -sp "Enter database password for noctis_user: " DB_PASSWORD
echo

# Update system
print_status "Updating system packages..."
apt update && apt upgrade -y

# Install system dependencies
print_status "Installing system dependencies..."
apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    redis-server \
    supervisor \
    certbot \
    python3-certbot-nginx \
    git \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff5-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk \
    ufw \
    fail2ban \
    htop \
    iotop \
    ncdu \
    tmux

# Configure firewall
print_status "Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 104/tcp  # DICOM port
ufw reload

# Create application user
print_status "Creating application user..."
if ! id -u $APP_USER > /dev/null 2>&1; then
    useradd -m -s /bin/bash $APP_USER
    usermod -aG sudo $APP_USER
fi

# Create directories
print_status "Creating application directories..."
mkdir -p $APP_DIR
mkdir -p $LOG_DIR
mkdir -p $BACKUP_DIR
mkdir -p /var/www/noctis/static
mkdir -p /var/www/noctis/media
mkdir -p /var/www/noctis/media/dicom_files
mkdir -p /var/www/noctis/media/temp

# Set up PostgreSQL
print_status "Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
\q
EOF

# Configure PostgreSQL for production
print_status "Configuring PostgreSQL for production..."
PG_VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | grep -oP '\d+\.\d+' | head -1)
PG_CONFIG="/etc/postgresql/$PG_VERSION/main/postgresql.conf"

# Backup original config
cp $PG_CONFIG $PG_CONFIG.backup

# Update PostgreSQL configuration
cat >> $PG_CONFIG <<EOF

# Noctis PACS Production Settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
max_parallel_maintenance_workers = 2
EOF

# Restart PostgreSQL
systemctl restart postgresql

# Clone or copy application code
print_status "Setting up application code..."
if [ -d "/workspace/.git" ]; then
    # If we're in a git repository, clone it
    cd $APP_DIR
    git clone /workspace .
else
    # Otherwise, copy the files
    cp -r /workspace/* $APP_DIR/
    cp -r /workspace/.* $APP_DIR/ 2>/dev/null || true
fi

# Set up Python virtual environment
print_status "Setting up Python virtual environment..."
cd $APP_DIR
python3.12 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Upgrade pip and install wheel
pip install --upgrade pip wheel setuptools

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Install production-specific packages
pip install \
    gunicorn==23.0.0 \
    psycopg2-binary==2.9.10 \
    redis==5.2.1 \
    celery==5.4.0 \
    django-redis==5.4.0 \
    django-storages==1.15.3 \
    boto3==1.36.9 \
    sentry-sdk==2.21.2 \
    django-environ==0.12.0 \
    whitenoise==6.8.2 \
    django-compressor==5.1 \
    django-debug-toolbar==5.1.0

# Set permissions
print_status "Setting file permissions..."
chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER /var/www/noctis
chown -R $APP_USER:$APP_USER $LOG_DIR
chmod -R 755 $APP_DIR
chmod -R 775 /var/www/noctis/media
chmod -R 775 $LOG_DIR

# Create log files
touch $LOG_DIR/django.log
touch $LOG_DIR/gunicorn.log
touch $LOG_DIR/nginx_access.log
touch $LOG_DIR/nginx_error.log
chown $APP_USER:$APP_USER $LOG_DIR/*.log

# Configure fail2ban
print_status "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 60
bantime = 600
EOF

systemctl restart fail2ban

# Create backup script
print_status "Creating backup script..."
cat > /usr/local/bin/noctis-backup.sh <<'EOF'
#!/bin/bash
# Noctis PACS Backup Script

BACKUP_DIR="/var/backups/noctis"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="noctis_db"
DB_USER="noctis_user"
MEDIA_DIR="/var/www/noctis/media"

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup database
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/$DATE/database.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/$DATE/media.tar.gz -C $MEDIA_DIR .

# Backup application code
tar -czf $BACKUP_DIR/$DATE/code.tar.gz -C /opt/noctis . --exclude=venv --exclude=__pycache__

# Remove backups older than 30 days
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR/$DATE"
EOF

chmod +x /usr/local/bin/noctis-backup.sh

# Create cron job for daily backups
print_status "Setting up automated backups..."
echo "0 2 * * * /usr/local/bin/noctis-backup.sh >> $LOG_DIR/backup.log 2>&1" | crontab -u root -

# Create monitoring script
print_status "Creating monitoring script..."
cat > /usr/local/bin/noctis-monitor.sh <<'EOF'
#!/bin/bash
# Noctis PACS Monitoring Script

LOG_FILE="/var/log/noctis/monitor.log"
DISK_THRESHOLD=90
CPU_THRESHOLD=80
MEM_THRESHOLD=80

# Check disk usage
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt $DISK_THRESHOLD ]; then
    echo "$(date) - WARNING: Disk usage is at ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}' | cut -d. -f1)
if [ $CPU_USAGE -gt $CPU_THRESHOLD ]; then
    echo "$(date) - WARNING: CPU usage is at ${CPU_USAGE}%" >> $LOG_FILE
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{print ($2-$7)/$2 * 100.0}' | cut -d. -f1)
if [ $MEM_USAGE -gt $MEM_THRESHOLD ]; then
    echo "$(date) - WARNING: Memory usage is at ${MEM_USAGE}%" >> $LOG_FILE
fi

# Check if services are running
services=("postgresql" "nginx" "redis-server" "supervisor")
for service in "${services[@]}"; do
    if ! systemctl is-active --quiet $service; then
        echo "$(date) - ERROR: $service is not running" >> $LOG_FILE
        systemctl start $service
    fi
done
EOF

chmod +x /usr/local/bin/noctis-monitor.sh

# Add monitoring to cron
echo "*/5 * * * * /usr/local/bin/noctis-monitor.sh" | crontab -u root -

# Create DICOM cleanup script
print_status "Creating DICOM cleanup script..."
cat > /usr/local/bin/noctis-cleanup.sh <<'EOF'
#!/bin/bash
# Noctis PACS DICOM Cleanup Script

# Remove temporary files older than 7 days
find /var/www/noctis/media/temp -type f -mtime +7 -delete

# Remove orphaned DICOM files (implement based on your business logic)
# This is a placeholder - customize based on your retention policy

echo "$(date) - Cleanup completed" >> /var/log/noctis/cleanup.log
EOF

chmod +x /usr/local/bin/noctis-cleanup.sh

# Add cleanup to cron
echo "0 3 * * * /usr/local/bin/noctis-cleanup.sh" | crontab -u root -

print_status "Basic system setup completed!"
print_status "Next steps:"
print_status "1. Create production settings file"
print_status "2. Configure Nginx"
print_status "3. Set up Gunicorn with systemd"
print_status "4. Configure SSL certificates"
print_status "5. Run database migrations"
print_status "6. Collect static files"
print_status "7. Create superuser"
print_status "8. Test the deployment"