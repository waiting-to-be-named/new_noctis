"""
Production settings for Noctis DICOM Viewer
"""

import os
from pathlib import Path
from .settings import *

# Production settings
DEBUG = False

# Security settings for production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-production-secret-key-change-this')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# HTTPS settings
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Database configuration for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'noctis_dicom'),
        'USER': os.environ.get('DB_USER', 'noctis_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'charset': 'utf8',
        },
    }
}

# Static files configuration for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'viewer': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# File upload settings for production
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, 'media', 'temp')
FILE_UPLOAD_PERMISSIONS = 0o644

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Performance optimizations
CONN_MAX_AGE = 60
OPTIMIZE_QUERIES = True

# DICOM specific settings
DICOM_UPLOAD_MAX_SIZE = 5 * 1024 * 1024 * 1024  # 5GB per file
DICOM_PROCESSING_TIMEOUT = 300  # 5 minutes
DICOM_CACHE_TIMEOUT = 3600  # 1 hour

# Ensure required directories exist
REQUIRED_DIRECTORIES = [
    os.path.join(BASE_DIR, 'media'),
    os.path.join(BASE_DIR, 'media', 'dicom_files'),
    os.path.join(BASE_DIR, 'media', 'temp'),
    os.path.join(BASE_DIR, 'media', 'bulk_uploads'),
    os.path.join(BASE_DIR, 'logs'),
    os.path.join(BASE_DIR, 'staticfiles'),
]

for directory in REQUIRED_DIRECTORIES:
    os.makedirs(directory, exist_ok=True)
