#!/bin/bash

# Start script for Noctis DICOM Viewer
set -e

echo "🚀 Starting Noctis DICOM Viewer..."

# Wait for database to be ready (if using external database)
if [ "$DB_HOST" != "localhost" ]; then
    echo "⏳ Waiting for database to be ready..."
    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 1
    done
    echo "✅ Database is ready"
fi

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Create superuser if not exists
echo "👤 Creating superuser if not exists..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@noctis.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Start Redis
echo "🔴 Starting Redis..."
redis-server --daemonize yes

# Start Celery worker
echo "🐌 Starting Celery worker..."
celery -A noctisview worker --loglevel=info --detach

# Start Celery beat
echo "⏰ Starting Celery beat..."
celery -A noctisview beat --loglevel=info --detach

# Start Gunicorn
echo "🦄 Starting Gunicorn..."
gunicorn --config gunicorn.conf.py noctisview.wsgi:application --daemon

# Start Nginx
echo "🌐 Starting Nginx..."
nginx

# Start Supervisor
echo "👨‍💼 Starting Supervisor..."
supervisord -c /etc/supervisor/supervisord.conf

echo "✅ All services started successfully!"
echo "🌍 Noctis DICOM Viewer is running on http://localhost"
echo "📊 Health check: http://localhost/health/"

# Keep container running
tail -f /dev/null