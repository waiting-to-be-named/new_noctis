#!/bin/bash
set -e

echo "Starting Noctis DICOM Viewer..."

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
done
echo "Database is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
redis_host=$(echo $REDIS_URL | cut -d'@' -f2 | cut -d':' -f1)
redis_port=$(echo $REDIS_URL | cut -d':' -f3 | cut -d'/' -f1)
while ! nc -z $redis_host $redis_port; do
    sleep 1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput --settings=noctisview.settings_production

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell --settings=noctisview.settings_production << END
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@noctis.local')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created successfully')
else:
    print(f'Superuser {username} already exists')
END

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=noctisview.settings_production

# Create required directories
mkdir -p /app/logs /app/media/dicom_files /app/media/temp

# Set proper permissions
chown -R noctis:noctis /app/logs /app/media

echo "Noctis setup complete!"

# Execute the main command
exec "$@"