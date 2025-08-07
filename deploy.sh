#!/bin/bash

# Production Deployment Script for Noctis DICOM Viewer
set -e

echo "🚀 Starting Noctis DICOM Viewer Production Deployment"
echo "=================================================="

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p media/dicom_files media/temp media/bulk_uploads logs staticfiles

# Set proper permissions
echo "🔐 Setting proper permissions..."
chmod 755 media logs staticfiles
chmod 644 *.py *.yml *.conf

# Generate secret key if not exists
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "🔑 Generating Django secret key..."
    export DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    echo "Generated secret key: $DJANGO_SECRET_KEY"
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
if curl -f http://localhost/health/ > /dev/null 2>&1; then
    echo "✅ Application is healthy!"
else
    echo "⚠️  Application health check failed. Checking logs..."
    docker-compose logs web
fi

# Display service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Access Information:"
echo "   🌐 Main Application: http://localhost"
echo "   🔧 Admin Interface: http://localhost/admin"
echo "   📊 Health Check: http://localhost/health/"
echo "   🐳 Docker Compose: docker-compose ps"
echo ""
echo "👤 Default Admin Credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📝 Useful Commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Update application: ./deploy.sh"
echo ""
echo "🔒 Security Notes:"
echo "   - Change default admin password"
echo "   - Update Django secret key"
echo "   - Configure SSL/TLS for production"
echo "   - Set up proper firewall rules"
echo ""
echo "📚 Documentation:"
echo "   - Production Guide: PRODUCTION_GUIDE.md"
echo "   - Troubleshooting: TROUBLESHOOTING.md"