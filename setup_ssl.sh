#!/bin/bash
#
# Noctis PACS SSL/TLS Setup Script
# This script configures SSL certificates using Let's Encrypt
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# Get configuration
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <domain_name> <admin_email>"
    echo "Example: $0 pacs.example.com admin@example.com"
    exit 1
fi

DOMAIN_NAME=$1
ADMIN_EMAIL=$2

# Create certbot webroot directory
print_status "Creating certbot webroot directory..."
mkdir -p /var/www/certbot

# Stop nginx temporarily
print_status "Stopping Nginx temporarily..."
systemctl stop nginx

# Get initial certificate
print_status "Obtaining SSL certificate from Let's Encrypt..."
certbot certonly \
    --standalone \
    --preferred-challenges http \
    --agree-tos \
    --no-eff-email \
    --email $ADMIN_EMAIL \
    -d $DOMAIN_NAME

# Check if certificate was obtained successfully
if [ ! -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
    print_error "Failed to obtain SSL certificate"
    exit 1
fi

print_status "SSL certificate obtained successfully!"

# Generate DH parameters for additional security
print_status "Generating DH parameters (this may take a while)..."
openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048

# Update Nginx configuration with the domain name
print_status "Updating Nginx configuration..."
sed -i "s/DOMAIN_NAME_PLACEHOLDER/$DOMAIN_NAME/g" /etc/nginx/sites-available/noctis

# Create SSL snippet for Nginx
print_status "Creating SSL configuration snippet..."
cat > /etc/nginx/snippets/ssl-params.conf <<EOF
# SSL Parameters
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

# DH Parameters
ssl_dhparam /etc/ssl/certs/dhparam.pem;

# SSL Session Settings
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security Headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
EOF

# Start Nginx
print_status "Starting Nginx..."
systemctl start nginx

# Test Nginx configuration
print_status "Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    print_status "Nginx configuration is valid"
    systemctl reload nginx
else
    print_error "Nginx configuration is invalid"
    exit 1
fi

# Set up automatic renewal
print_status "Setting up automatic certificate renewal..."
cat > /etc/systemd/system/certbot-renewal.service <<EOF
[Unit]
Description=Certbot Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
User=root
EOF

cat > /etc/systemd/system/certbot-renewal.timer <<EOF
[Unit]
Description=Run certbot renewal twice daily
After=network.target

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the renewal timer
systemctl daemon-reload
systemctl enable certbot-renewal.timer
systemctl start certbot-renewal.timer

# Test renewal
print_status "Testing certificate renewal..."
certbot renew --dry-run

if [ $? -eq 0 ]; then
    print_status "Certificate renewal test successful"
else
    print_warning "Certificate renewal test failed - please check manually"
fi

# Create SSL monitoring script
print_status "Creating SSL certificate monitoring script..."
cat > /usr/local/bin/check-ssl-cert.sh <<'EOF'
#!/bin/bash
# Check SSL certificate expiration

DOMAIN="$1"
DAYS_WARNING=30

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain>"
    exit 1
fi

CERT_FILE="/etc/letsencrypt/live/$DOMAIN/cert.pem"

if [ ! -f "$CERT_FILE" ]; then
    echo "Certificate file not found: $CERT_FILE"
    exit 1
fi

EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
    echo "WARNING: SSL certificate for $DOMAIN expires in $DAYS_LEFT days"
    # Send alert email or notification here
else
    echo "SSL certificate for $DOMAIN is valid for $DAYS_LEFT more days"
fi
EOF

chmod +x /usr/local/bin/check-ssl-cert.sh

# Add SSL check to monitoring cron
echo "0 9 * * * /usr/local/bin/check-ssl-cert.sh $DOMAIN_NAME >> /var/log/noctis/ssl-monitor.log 2>&1" | crontab -l | crontab -

print_status "SSL/TLS configuration completed successfully!"
print_status "Your site is now accessible at: https://$DOMAIN_NAME"
print_warning "Important: Update your Django settings with:"
print_warning "- ALLOWED_HOSTS to include $DOMAIN_NAME"
print_warning "- CSRF_TRUSTED_ORIGINS to include https://$DOMAIN_NAME"
print_warning "- Update your .env file accordingly"