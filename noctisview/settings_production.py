"""
Production settings for NOCTIS DICOM Viewer
Extends base settings with production-specific configurations
"""

import os
from pathlib import Path
from .settings import *

# Read environment variables
def env(key, default=None, cast=str):
    """Helper to read environment variables with type casting"""
    value = os.environ.get(key, default)
    if value is None:
        return None
    if cast == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    return cast(value)

# Security Settings
SECRET_KEY = env('DJANGO_SECRET_KEY', SECRET_KEY)
DEBUG = env('DJANGO_DEBUG', False, bool)
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS', '').split(',')

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': env('DB_NAME', 'noctis_db'),
        'USER': env('DB_USER', 'noctis_user'),
        'PASSWORD': env('DB_PASSWORD', 'secure_password'),
        'HOST': env('DB_HOST', 'db'),
        'PORT': env('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Redis Configuration
REDIS_URL = env('REDIS_URL', 'redis://redis:6379/1')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'PICKLE_VERSION': -1,
        },
        'KEY_PREFIX': 'noctis',
        'TIMEOUT': 300,
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE', True, bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hours

# Security Headers
SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT', True, bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', 'DENY')
SECURE_REFERRER_POLICY = 'same-origin'

# CSRF Settings
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE', True, bool)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host]

# Static and Media Files
STATIC_ROOT = env('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
MEDIA_ROOT = env('MEDIA_ROOT', str(BASE_DIR / 'media'))

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = env('EMAIL_PORT', 587, int)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env('EMAIL_USE_TLS', True, bool)
EMAIL_USE_SSL = env('EMAIL_USE_SSL', False, bool)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'noreply@noctis.local')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# DICOM Settings
DICOM_SCP_AE_TITLE = env('DICOM_SCP_AE_TITLE', 'NOCTIS_SCP')
DICOM_SCP_PORT = env('DICOM_SCP_PORT', 11112, int)
DICOM_STORAGE_PATH = env('DICOM_STORAGE_PATH', str(MEDIA_ROOT / 'dicom_files'))
MAX_DICOM_FILE_SIZE = env('MAX_DICOM_FILE_SIZE', 5 * 1024 * 1024 * 1024, int)

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SOFT_TIME_LIMIT = 3600
CELERY_TASK_TIME_LIMIT = 3660
CELERY_WORKER_MAX_TASKS_PER_CHILD = env('CELERY_MAX_TASKS_PER_CHILD', 1000, int)

# Logging Configuration for Production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(BASE_DIR / 'logs' / 'django.log'),
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(BASE_DIR / 'logs' / 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'noctisview': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Performance Settings
CONN_MAX_AGE = 600
DATA_UPLOAD_MAX_MEMORY_SIZE = env('DATA_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024 * 1024, int)
FILE_UPLOAD_MAX_MEMORY_SIZE = env('FILE_UPLOAD_MAX_MEMORY_SIZE', 100 * 1024 * 1024, int)

# Monitoring (Optional)
SENTRY_DSN = env('SENTRY_DSN', None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )

# Health Check Settings
HEALTH_CHECK_APPS = [
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.storage',
]

# Add health check apps if available
try:
    import health_check
    INSTALLED_APPS.extend(HEALTH_CHECK_APPS)
except ImportError:
    pass

# Production-only middleware
MIDDLEWARE.insert(0, 'whitenoise.middleware.WhiteNoiseMiddleware')

# WhiteNoise settings for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_COMPRESS_OFFLINE = True
WHITENOISE_COMPRESSION_QUALITY = 80

# Admin settings
ADMIN_SITE_HEADER = "NOCTIS DICOM Viewer Administration"
ADMIN_SITE_TITLE = "NOCTIS Admin"
ADMIN_INDEX_TITLE = "Welcome to NOCTIS Administration"

# Create required directories
for directory in [MEDIA_ROOT, STATIC_ROOT, BASE_DIR / 'logs']:
    Path(directory).mkdir(parents=True, exist_ok=True)