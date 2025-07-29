import json
import logging
import time
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpResponseForbidden
import traceback

logger = logging.getLogger(__name__)


class APIErrorMiddleware(MiddlewareMixin):
    """
    Middleware to handle API errors and ensure JSON responses for API endpoints.
    Provides detailed error logging and consistent error response format.
    """
    
    def process_exception(self, request, exception):
        """Handle exceptions for API endpoints and return JSON responses."""
        # Check if this is an API request
        if request.path.startswith('/api/') or request.path.startswith('/viewer/api/'):
            # Log the exception with full traceback
            logger.error(f"API Exception: {type(exception).__name__}: {str(exception)}")
            logger.error(f"Request path: {request.path}")
            logger.error(f"Request method: {request.method}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Determine appropriate status code and error message
            if isinstance(exception, ValidationError):
                status_code = 400
                error_type = 'validation_error'
                error_message = str(exception)
            elif isinstance(exception, PermissionDenied):
                status_code = 403
                error_type = 'permission_denied'
                error_message = 'Access denied'
            elif isinstance(exception, FileNotFoundError):
                status_code = 404
                error_type = 'not_found'
                error_message = 'Resource not found'
            else:
                status_code = 500
                error_type = 'server_error'
                error_message = 'Internal server error' if not settings.DEBUG else str(exception)
            
            return JsonResponse({
                'error': error_message,
                'error_type': error_type,
                'status': 'error',
                'path': request.path,
                'method': request.method
            }, status=status_code)
        return None


class CSRFMiddleware(MiddlewareMixin):
    """
    Custom CSRF middleware that returns JSON errors for API endpoints.
    Provides better handling for file uploads and API requests.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Create the CSRF middleware instance with proper get_response
        self.csrf_middleware = CsrfViewMiddleware(get_response)
        super().__init__(get_response)
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Skip CSRF check for specific API endpoints that handle file uploads
        if hasattr(callback, '__name__') and any(name in callback.__name__ for name in ['upload', 'save']):
            return None
            
        # Skip CSRF for API endpoints that are explicitly marked as csrf_exempt
        if hasattr(callback, 'csrf_exempt') and callback.csrf_exempt:
            return None
            
        # Use the properly initialized CSRF middleware
        response = self.csrf_middleware.process_view(request, callback, callback_args, callback_kwargs)
        
        # If CSRF validation failed and this is an API request, return JSON error
        if response and (request.path.startswith('/api/') or request.path.startswith('/viewer/api/')):
            return JsonResponse({
                'error': 'CSRF token missing or invalid',
                'error_type': 'csrf_error',
                'status': 'error',
                'path': request.path,
                'method': request.method
            }, status=403)
        
        return response


class CORSMiddleware(MiddlewareMixin):
    """
    CORS middleware to handle cross-origin requests for API endpoints.
    """
    
    def process_response(self, request, response):
        # Add CORS headers for API requests
        if request.path.startswith('/api/') or request.path.startswith('/viewer/api/'):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    def process_request(self, request):
        # Handle preflight OPTIONS requests
        if request.method == 'OPTIONS' and (request.path.startswith('/api/') or request.path.startswith('/viewer/api/')):
            response = JsonResponse({})
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to all responses.
    """
    
    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add Content Security Policy for better security
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self' blob:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response['Content-Security-Policy'] = csp_policy
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses for debugging and monitoring.
    """
    
    def process_request(self, request):
        # Log API requests
        if request.path.startswith('/api/') or request.path.startswith('/viewer/api/'):
            logger.info(f"API Request: {request.method} {request.path}")
            if request.method in ['POST', 'PUT', 'PATCH']:
                logger.debug(f"Request body size: {len(request.body) if request.body else 0} bytes")
        return None
    
    def process_response(self, request, response):
        # Log API responses
        if request.path.startswith('/api/') or request.path.startswith('/viewer/api/'):
            logger.info(f"API Response: {request.method} {request.path} - Status: {response.status_code}")
            if hasattr(response, 'content'):
                logger.debug(f"Response size: {len(response.content)} bytes")
        return response


class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to track request performance and log slow requests.
    """
    
    def process_request(self, request):
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            if duration > 1.0:  # Log requests taking more than 1 second
                logger.warning(f"Slow request: {request.method} {request.path} took {duration:.2f}s")
            elif request.path.startswith('/api/') or request.path.startswith('/viewer/api/'):
                logger.debug(f"Request duration: {request.method} {request.path} took {duration:.3f}s")
        return response