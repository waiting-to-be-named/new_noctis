import json
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.deprecation import MiddlewareMixin


class APIErrorMiddleware(MiddlewareMixin):
    """
    Middleware to handle API errors and ensure JSON responses for API endpoints.
    """
    
    def process_exception(self, request, exception):
        """Handle exceptions for API endpoints and return JSON responses."""
        # Check if this is an API request
        if request.path.startswith('/api/'):
            error_message = str(exception)
            return JsonResponse({
                'error': error_message,
                'status': 'error'
            }, status=500)
        return None


class CSRFMiddleware(MiddlewareMixin):
    """
    Custom CSRF middleware that returns JSON errors for API endpoints.
    """
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Skip CSRF check for API endpoints that are marked as csrf_exempt
        if hasattr(callback, '__name__') and 'upload' in callback.__name__:
            return None
            
        # Use Django's built-in CSRF middleware
        csrf_middleware = CsrfViewMiddleware()
        response = csrf_middleware.process_view(request, callback, callback_args, callback_kwargs)
        
        # If CSRF validation failed and this is an API request, return JSON error
        if response and request.path.startswith('/api/'):
            try:
                # Try to parse the response as JSON first
                return response
            except:
                # If it's not JSON, return a JSON error response
                return JsonResponse({
                    'error': 'CSRF token missing or invalid',
                    'status': 'error'
                }, status=403)
        
        return response