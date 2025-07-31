#!/bin/bash

# Noctis DICOM Viewer Deployment Script
# Usage: ./deploy.sh [action]
# Actions: build, deploy, update, stop, restart, logs, status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
PROJECT_NAME="noctis"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found. Please copy .env.example to .env and configure it."
        exit 1
    fi
    
    # Check if SSL certificates exist
    if [ ! -f "docker/ssl/cert.pem" ] || [ ! -f "docker/ssl/key.pem" ]; then
        log_warn "SSL certificates not found. Please generate SSL certificates or use self-signed certificates."
        read -p "Do you want to generate self-signed certificates? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            generate_ssl_certificates
        else
            log_error "SSL certificates are required for deployment."
            exit 1
        fi
    fi
    
    log_info "Prerequisites check completed."
}

# Generate self-signed SSL certificates
generate_ssl_certificates() {
    log_info "Generating self-signed SSL certificates..."
    
    mkdir -p docker/ssl
    
    # Generate private key
    openssl genrsa -out docker/ssl/key.pem 4096
    
    # Generate certificate signing request
    openssl req -new -key docker/ssl/key.pem -out docker/ssl/csr.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=noctis.local"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 -in docker/ssl/csr.pem \
        -signkey docker/ssl/key.pem -out docker/ssl/cert.pem
    
    # Set proper permissions
    chmod 600 docker/ssl/key.pem
    chmod 644 docker/ssl/cert.pem
    
    # Clean up CSR
    rm docker/ssl/csr.pem
    
    log_info "SSL certificates generated successfully."
}

# Generate secure passwords
generate_passwords() {
    log_info "Generating secure passwords..."
    
    # Check if .env already has passwords
    if grep -q "change-this" "$ENV_FILE" || grep -q "secure-" "$ENV_FILE"; then
        log_warn "Default passwords detected in $ENV_FILE"
        read -p "Do you want to generate new secure passwords? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Generate new passwords
            SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
            DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
            REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
            DJANGO_SUPERUSER_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')
            GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')
            
            # Update .env file
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$ENV_FILE"
            sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" "$ENV_FILE"
            sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" "$ENV_FILE"
            sed -i "s/DJANGO_SUPERUSER_PASSWORD=.*/DJANGO_SUPERUSER_PASSWORD=$DJANGO_SUPERUSER_PASSWORD/" "$ENV_FILE"
            sed -i "s/GRAFANA_PASSWORD=.*/GRAFANA_PASSWORD=$GRAFANA_PASSWORD/" "$ENV_FILE"
            
            log_info "Passwords updated in $ENV_FILE"
            log_warn "Please save these credentials securely:"
            echo "Django Admin Password: $DJANGO_SUPERUSER_PASSWORD"
            echo "Grafana Admin Password: $GRAFANA_PASSWORD"
        fi
    fi
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    log_info "Docker images built successfully."
}

# Deploy the application
deploy() {
    log_info "Deploying Noctis DICOM Viewer..."
    
    check_prerequisites
    generate_passwords
    
    # Pull latest images
    log_info "Pulling latest base images..."
    docker compose -f "$COMPOSE_FILE" pull
    
    # Build application image
    build_images
    
    # Start services
    log_info "Starting services..."
    docker compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service status
    check_status
    
    log_info "Deployment completed successfully!"
    log_info "Application is available at: https://localhost"
    log_info "Grafana dashboard: https://localhost:3000"
    log_info "Prometheus metrics: https://localhost:9090"
}

# Update the application
update() {
    log_info "Updating Noctis DICOM Viewer..."
    
    # Pull latest code (if using git)
    if [ -d ".git" ]; then
        log_info "Pulling latest code..."
        git pull
    fi
    
    # Pull latest images
    log_info "Pulling latest base images..."
    docker compose -f "$COMPOSE_FILE" pull
    
    # Rebuild application image
    build_images
    
    # Rolling update
    log_info "Performing rolling update..."
    docker compose -f "$COMPOSE_FILE" up -d --force-recreate
    
    # Check status
    check_status
    
    log_info "Update completed successfully!"
}

# Stop the application
stop() {
    log_info "Stopping Noctis DICOM Viewer..."
    docker compose -f "$COMPOSE_FILE" down
    log_info "Application stopped."
}

# Restart the application
restart() {
    log_info "Restarting Noctis DICOM Viewer..."
    docker compose -f "$COMPOSE_FILE" restart
    log_info "Application restarted."
}

# Show logs
show_logs() {
    docker compose -f "$COMPOSE_FILE" logs -f --tail=100
}

# Check status
check_status() {
    log_info "Checking service status..."
    
    # Show container status
    docker compose -f "$COMPOSE_FILE" ps
    
    # Check health
    log_info "Checking application health..."
    
    # Wait a moment for services to start
    sleep 5
    
    # Check database
    if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U noctis >/dev/null 2>&1; then
        log_info "✓ Database is healthy"
    else
        log_error "✗ Database is not healthy"
    fi
    
    # Check Redis
    if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping >/dev/null 2>&1; then
        log_info "✓ Redis is healthy"
    else
        log_error "✗ Redis is not healthy"
    fi
    
    # Check application
    if curl -k -s https://localhost/health/ >/dev/null 2>&1; then
        log_info "✓ Application is healthy"
    else
        log_error "✗ Application is not healthy"
    fi
}

# Backup data
backup() {
    log_info "Creating backup..."
    
    # Create backup directory
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    log_info "Backing up database..."
    docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U noctis noctis | gzip > "$BACKUP_DIR/database.sql.gz"
    
    # Backup media files
    log_info "Backing up media files..."
    docker run --rm -v noctis_media_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/media.tar.gz -C /data .
    
    # Backup configuration
    log_info "Backing up configuration..."
    tar czf "$BACKUP_DIR/config.tar.gz" docker/ .env
    
    log_info "Backup completed: $BACKUP_DIR"
}

# Show help
show_help() {
    echo "Noctis DICOM Viewer Deployment Script"
    echo
    echo "Usage: $0 [action]"
    echo
    echo "Actions:"
    echo "  deploy    - Deploy the application (first time setup)"
    echo "  build     - Build Docker images"
    echo "  update    - Update the application"
    echo "  stop      - Stop the application"
    echo "  restart   - Restart the application"
    echo "  logs      - Show application logs"
    echo "  status    - Check service status"
    echo "  backup    - Create backup of data and configuration"
    echo "  help      - Show this help message"
    echo
    echo "Examples:"
    echo "  $0 deploy     # First time deployment"
    echo "  $0 update     # Update to latest version"
    echo "  $0 logs       # View real-time logs"
}

# Main script logic
case "${1:-help}" in
    "deploy")
        deploy
        ;;
    "build")
        check_prerequisites
        build_images
        ;;
    "update")
        update
        ;;
    "stop")
        stop
        ;;
    "restart")
        restart
        ;;
    "logs")
        show_logs
        ;;
    "status")
        check_status
        ;;
    "backup")
        backup
        ;;
    "help"|*)
        show_help
        ;;
esac