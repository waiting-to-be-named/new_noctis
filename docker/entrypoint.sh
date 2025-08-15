#!/bin/bash
set -e

echo "Starting NOCTIS DICOM Viewer..."

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z ${DB_HOST:-db} ${DB_PORT:-5432}; do
  sleep 1
done
echo "Database is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
  sleep 1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@noctis.local', '${DJANGO_ADMIN_PASSWORD:-admin123}')
    print('Superuser created!')
else:
    print('Superuser already exists.')
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create necessary directories
echo "Creating directories..."
mkdir -p /app/logs /app/media/dicom_files /app/media/temp /app/staticfiles

# Set proper permissions
echo "Setting permissions..."
chown -R noctis:noctis /app/logs /app/media /app/staticfiles

# Create health check endpoint
cat > /app/noctisview/health.py << 'EOF'
from django.http import JsonResponse
from django.db import connection
import redis
from django.conf import settings

def health_check(request):
    health_status = {
        'status': 'healthy',
        'services': {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['services']['database'] = 'healthy'
    except Exception as e:
        health_status['services']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else 'redis://redis:6379/1')
        r.ping()
        health_status['services']['redis'] = 'healthy'
    except Exception as e:
        health_status['services']['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    return JsonResponse(health_status)
EOF

# Update URLs to include health check
if ! grep -q "health_check" /app/noctisview/urls.py; then
    sed -i "/from django.urls import path, include/a from .health import health_check" /app/noctisview/urls.py
    sed -i "/urlpatterns = \[/a \    path('health/', health_check, name='health_check')," /app/noctisview/urls.py
fi

# Start supervisord
echo "Starting services..."
exec "$@"