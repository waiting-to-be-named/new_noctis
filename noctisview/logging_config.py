"""
Comprehensive logging configuration for Noctis DICOM viewer.
This module provides structured logging for all system events, errors, and performance metrics.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
import json
from django.conf import settings

# Create logs directory if it doesn't exist
LOGS_DIR = Path(settings.BASE_DIR) / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Custom formatter for structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)

# Custom logger that adds extra fields
class StructuredLogger(logging.Logger):
    """Custom logger that supports structured logging with extra fields"""
    
    def log_with_context(self, level, message, extra_fields=None, exc_info=None):
        """Log with additional context fields"""
        if extra_fields is None:
            extra_fields = {}
        
        record = self.makeRecord(
            self.name, level, __file__, 0, message, (), exc_info
        )
        record.extra_fields = extra_fields
        self.handle(record)

# Register custom logger class
logging.setLoggerClass(StructuredLogger)

def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create formatters
    structured_formatter = StructuredFormatter()
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create handlers
    handlers = []
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    handlers.append(console_handler)
    
    # File handler for all logs
    all_logs_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'all.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(structured_formatter)
    handlers.append(all_logs_handler)
    
    # Error logs handler
    error_logs_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'errors.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(structured_formatter)
    handlers.append(error_logs_handler)
    
    # Upload logs handler
    upload_logs_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'uploads.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    upload_logs_handler.setLevel(logging.INFO)
    upload_logs_handler.setFormatter(structured_formatter)
    handlers.append(upload_logs_handler)
    
    # Performance logs handler
    performance_logs_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'performance.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    performance_logs_handler.setLevel(logging.INFO)
    performance_logs_handler.setFormatter(structured_formatter)
    handlers.append(performance_logs_handler)
    
    # Security logs handler
    security_logs_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'security.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    security_logs_handler.setLevel(logging.WARNING)
    security_logs_handler.setFormatter(structured_formatter)
    handlers.append(security_logs_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure specific loggers
    loggers = {
        'django': {'level': logging.INFO},
        'django.request': {'level': logging.WARNING},
        'django.security': {'level': logging.WARNING},
        'viewer': {'level': logging.DEBUG},
        'worklist': {'level': logging.DEBUG},
        'noctisview': {'level': logging.DEBUG},
        'viewer.services': {'level': logging.DEBUG},
        'viewer.upload': {'level': logging.INFO},
        'viewer.processing': {'level': logging.INFO},
        'viewer.security': {'level': logging.WARNING},
        'viewer.performance': {'level': logging.INFO},
    }
    
    for logger_name, config in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config['level'])
        logger.propagate = True

# Logging decorators for performance monitoring
def log_performance(func):
    """Decorator to log function performance"""
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger = logging.getLogger('viewer.performance')
            logger.log_with_context(
                logging.INFO,
                f"Function {func.__name__} completed successfully",
                {
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'status': 'success'
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger = logging.getLogger('viewer.performance')
            logger.log_with_context(
                logging.ERROR,
                f"Function {func.__name__} failed",
                {
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'status': 'error',
                    'error': str(e)
                }
            )
            raise
    
    return wrapper

def log_security_event(event_type, details=None):
    """Log security-related events"""
    logger = logging.getLogger('viewer.security')
    logger.log_with_context(
        logging.WARNING,
        f"Security event: {event_type}",
        {
            'event_type': event_type,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    )

def log_upload_event(event_type, file_info=None, user_info=None, details=None):
    """Log upload-related events"""
    logger = logging.getLogger('viewer.upload')
    logger.log_with_context(
        logging.INFO,
        f"Upload event: {event_type}",
        {
            'event_type': event_type,
            'file_info': file_info or {},
            'user_info': user_info or {},
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    )

def log_processing_event(event_type, study_info=None, series_info=None, details=None):
    """Log DICOM processing events"""
    logger = logging.getLogger('viewer.processing')
    logger.log_with_context(
        logging.INFO,
        f"Processing event: {event_type}",
        {
            'event_type': event_type,
            'study_info': study_info or {},
            'series_info': series_info or {},
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    )

# Error tracking and reporting
class ErrorTracker:
    """Track and report errors for analysis"""
    
    def __init__(self):
        self.error_counts = {}
        self.error_logger = logging.getLogger('viewer.errors')
    
    def track_error(self, error_type, error_message, context=None):
        """Track an error occurrence"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        
        self.error_counts[error_type] += 1
        
        self.error_logger.log_with_context(
            logging.ERROR,
            f"Error tracked: {error_type}",
            {
                'error_type': error_type,
                'error_message': error_message,
                'context': context or {},
                'count': self.error_counts[error_type],
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def get_error_summary(self):
        """Get summary of tracked errors"""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_types': self.error_counts,
            'timestamp': datetime.utcnow().isoformat()
        }

# Global error tracker instance
error_tracker = ErrorTracker()

# Performance monitoring
class PerformanceMonitor:
    """Monitor system performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.performance_logger = logging.getLogger('viewer.performance')
    
    def record_metric(self, metric_name, value, context=None):
        """Record a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            'value': value,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        })
        
        self.performance_logger.log_with_context(
            logging.INFO,
            f"Performance metric: {metric_name}",
            {
                'metric_name': metric_name,
                'value': value,
                'context': context or {},
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def get_metric_summary(self, metric_name):
        """Get summary for a specific metric"""
        if metric_name not in self.metrics:
            return None
        
        values = [m['value'] for m in self.metrics[metric_name]]
        return {
            'metric_name': metric_name,
            'count': len(values),
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'avg': sum(values) / len(values) if values else None,
            'latest': values[-1] if values else None
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Initialize logging when module is imported
setup_logging()