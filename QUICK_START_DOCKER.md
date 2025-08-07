# NOCTIS DICOM Viewer - Docker Quick Start Guide

## Prerequisites
- Ubuntu Server 20.04+ or any Linux with Docker support
- Docker and Docker Compose installed
- Domain name (optional, for SSL)
- At least 8GB RAM and 50GB storage

## Quick Deployment (5 Minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/your-org/noctis-dicom-viewer.git
cd noctis-dicom-viewer

# Copy environment template
cp .env.example .env

# Generate Django secret key
echo "DJANGO_SECRET_KEY=$(openssl rand -base64 32)" >> .env
```

### 2. Configure Environment
Edit `.env` file with your settings:
```bash
# Essential settings only
DJANGO_SECRET_KEY=your-generated-key
DB_PASSWORD=choose-strong-password
DJANGO_ALLOWED_HOSTS=localhost,your-domain.com
```

### 3. Deploy
```bash
# Build and start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Access Application
- Web Interface: http://localhost
- Admin Panel: http://localhost/admin
- Default credentials: admin / admin123 (change immediately!)

## Development Setup

### Quick Dev Environment
```bash
# Use development compose file
docker compose -f docker-compose.dev.yml up -d

# Enable hot reload
docker compose -f docker-compose.dev.yml exec web python manage.py runserver 0.0.0.0:8000
```

### Create docker-compose.dev.yml:
```yaml
version: '3.8'

services:
  web:
    build: .
    volumes:
      - .:/app
    environment:
      - DJANGO_DEBUG=True
    ports:
      - "8000:8000"
    command: python manage.py runserver 0.0.0.0:8000

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: noctis_dev
      POSTGRES_USER: noctis
      POSTGRES_PASSWORD: noctis
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Production Setup with SSL

### 1. Prepare SSL Certificate
```bash
# Create SSL directory
mkdir -p docker/ssl

# Option A: Let's Encrypt (recommended)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem docker/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem docker/ssl/key.pem

# Option B: Self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/key.pem \
  -out docker/ssl/cert.pem \
  -subj "/CN=localhost"
```

### 2. Production Environment
```bash
# Update .env for production
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECURE_SSL_REDIRECT=True

# Deploy with production settings
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Common Operations

### Manage Database
```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Access database shell
docker compose exec db psql -U noctis_user noctis_db
```

### Manage Files
```bash
# Backup database
docker compose exec db pg_dump -U noctis_user noctis_db > backup.sql

# Restore database
docker compose exec -T db psql -U noctis_user noctis_db < backup.sql

# Backup DICOM files
tar -czf dicom_backup.tar.gz media/dicom_files/
```

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d

# Run migrations
docker compose exec web python manage.py migrate
```

## Troubleshooting

### Container Issues
```bash
# View all logs
docker compose logs

# Restart specific service
docker compose restart web

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Performance Tuning
```bash
# Scale workers
docker compose up -d --scale celery_worker=4

# Monitor resources
docker stats

# Check container health
docker compose ps
```

### Common Fixes
```bash
# Permission issues
sudo chown -R 1000:1000 media/ logs/ staticfiles/

# Database connection issues
docker compose restart db
docker compose exec web python manage.py dbshell

# Clear cache
docker compose exec redis redis-cli FLUSHALL
```

## Minimal Setup (Single Command)

For the absolute quickest start:
```bash
# One-liner deployment (development only)
curl -sSL https://raw.githubusercontent.com/your-org/noctis/main/install.sh | bash
```

Create `install.sh`:
```bash
#!/bin/bash
git clone https://github.com/your-org/noctis-dicom-viewer.git
cd noctis-dicom-viewer
cp .env.example .env
echo "DJANGO_SECRET_KEY=$(openssl rand -base64 32)" >> .env
docker compose up -d
echo "NOCTIS is running at http://localhost"
echo "Default login: admin / admin123"
```

## Next Steps

1. Change default admin password
2. Configure email settings in `.env`
3. Set up SSL for production
4. Configure backup schedule
5. Review security settings

## Support

- Logs: `docker compose logs -f`
- Documentation: See `UBUNTU_DOCKER_DEPLOYMENT_GUIDE.md`
- Issues: Check `docker compose ps` for service status

---

**Ready in 5 minutes!** 🚀