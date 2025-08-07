# Dockerfile for Noctis DICOM Viewer
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=noctisview.production_settings

# Set work directory
WORKDIR /opt/noctis-dicom-viewer

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenexr-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    redis-server \
    nginx \
    supervisor \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements_production.txt .
RUN pip install --no-cache-dir -r requirements_production.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p /opt/noctis-dicom-viewer/media/dicom_files \
    /opt/noctis-dicom-viewer/media/temp \
    /opt/noctis-dicom-viewer/media/bulk_uploads \
    /opt/noctis-dicom-viewer/staticfiles \
    /opt/noctis-dicom-viewer/logs \
    /var/log/supervisor

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN useradd -m -u 1000 noctis && \
    chown -R noctis:noctis /opt/noctis-dicom-viewer

# Copy configuration files
COPY nginx.conf /etc/nginx/sites-available/noctis
COPY supervisor.conf /etc/supervisor/conf.d/noctis.conf
COPY gunicorn.conf.py /opt/noctis-dicom-viewer/

# Enable nginx site
RUN ln -s /etc/nginx/sites-available/noctis /etc/nginx/sites-enabled/ && \
    rm /etc/nginx/sites-enabled/default

# Set permissions
RUN chown -R noctis:noctis /opt/noctis-dicom-viewer && \
    chmod +x /opt/noctis-dicom-viewer/manage.py

# Expose ports
EXPOSE 80 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health/ || exit 1

# Start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

USER noctis

# Run migrations and start services
CMD ["/start.sh"]