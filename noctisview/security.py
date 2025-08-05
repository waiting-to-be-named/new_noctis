"""
Comprehensive security system for Noctis DICOM viewer.
This module provides authentication, authorization, input validation, and security monitoring.
"""

import re
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from django.conf import settings
import logging
from functools import wraps
import json

from .logging_config import log_security_event, error_tracker

logger = logging.getLogger(__name__)


class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.rate_limit_store = {}
        self.blocked_ips = set()
        self.suspicious_activities = []
    
    def validate_input(self, data: Any, input_type: str) -> Dict[str, Any]:
        """Validate and sanitize input data"""
        try:
            if input_type == 'dicom_file':
                return self._validate_dicom_file(data)
            elif input_type == 'user_input':
                return self._validate_user_input(data)
            elif input_type == 'api_request':
                return self._validate_api_request(data)
            else:
                raise ValueError(f"Unknown input type: {input_type}")
        except Exception as e:
            error_tracker.track_error('input_validation_error', str(e), {'input_type': input_type})
            log_security_event('input_validation_failed', {'input_type': input_type, 'error': str(e)})
            raise
    
    def _validate_dicom_file(self, file_data: Any) -> Dict[str, Any]:
        """Validate DICOM file upload"""
        if not hasattr(file_data, 'name'):
            raise ValueError("Invalid file object")
        
        # Check file size (max 5GB)
        max_size = 5 * 1024 * 1024 * 1024
        if hasattr(file_data, 'size') and file_data.size > max_size:
            raise ValueError("File too large")
        
        # Check file extension
        allowed_extensions = ['.dcm', '.dicom', '.ima', '.img', '.zip']
        file_extension = file_data.name.lower()
        if not any(file_extension.endswith(ext) for ext in allowed_extensions):
            raise ValueError("Invalid file type")
        
        # Check for suspicious patterns in filename
        suspicious_patterns = ['..', '\\', '//', 'script', 'javascript']
        for pattern in suspicious_patterns:
            if pattern in file_data.name.lower():
                raise ValueError("Suspicious filename detected")
        
        return {
            'valid': True,
            'filename': file_data.name,
            'size': getattr(file_data, 'size', 0),
            'extension': file_extension
        }
    
    def _validate_user_input(self, data: Any) -> Dict[str, Any]:
        """Validate user input data"""
        if isinstance(data, str):
            # Check for SQL injection patterns
            sql_patterns = [
                r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
                r'(\b(or|and)\b\s+\d+\s*[=<>])',
                r'(\b(exec|execute|script)\b)',
                r'(\b(xss|javascript|vbscript)\b)',
                r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    raise ValueError("Suspicious input detected")
            
            # Check for XSS patterns
            xss_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'on\w+\s*=',
                r'<iframe[^>]*>',
                r'<object[^>]*>',
            ]
            
            for pattern in xss_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    raise ValueError("XSS pattern detected")
            
            return {
                'valid': True,
                'sanitized': self._sanitize_string(data)
            }
        
        return {'valid': True, 'data': data}
    
    def _validate_api_request(self, data: Any) -> Dict[str, Any]:
        """Validate API request data"""
        if not isinstance(data, dict):
            raise ValueError("Invalid API request format")
        
        # Check for required fields
        required_fields = ['action', 'timestamp']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate timestamp (prevent replay attacks)
        try:
            timestamp = datetime.fromisoformat(data['timestamp'])
            now = datetime.utcnow()
            if abs((now - timestamp).total_seconds()) > 300:  # 5 minutes
                raise ValueError("Request timestamp too old or too new")
        except (ValueError, TypeError):
            raise ValueError("Invalid timestamp format")
        
        return {'valid': True, 'data': data}
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string input"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        if len(text) > 10000:
            text = text[:10000]
        
        return text.strip()
    
    def check_rate_limit(self, identifier: str, limit: int = 100, window: int = 3600) -> bool:
        """Check rate limiting for an identifier (IP, user, etc.)"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        if identifier not in self.rate_limit_store:
            self.rate_limit_store[identifier] = []
        
        # Remove old entries
        self.rate_limit_store[identifier] = [
            timestamp for timestamp in self.rate_limit_store[identifier]
            if timestamp > window_start
        ]
        
        # Check if limit exceeded
        if len(self.rate_limit_store[identifier]) >= limit:
            log_security_event('rate_limit_exceeded', {'identifier': identifier, 'limit': limit})
            return False
        
        # Add current request
        self.rate_limit_store[identifier].append(now)
        return True
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        return ip_address in self.blocked_ips
    
    def block_ip(self, ip_address: str, reason: str = "Suspicious activity"):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        log_security_event('ip_blocked', {'ip': ip_address, 'reason': reason})
    
    def record_suspicious_activity(self, activity_type: str, details: Dict[str, Any]):
        """Record suspicious activity for analysis"""
        activity = {
            'type': activity_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.suspicious_activities.append(activity)
        log_security_event('suspicious_activity', activity)


# Global security manager instance
security_manager = SecurityManager()


class SecurityMiddleware:
    """Middleware for security monitoring and enforcement"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if security_manager.is_ip_blocked(client_ip):
            log_security_event('blocked_ip_access', {'ip': client_ip})
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check rate limiting
        if not security_manager.check_rate_limit(client_ip):
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        
        # Monitor for suspicious activity
        self._monitor_request(request, client_ip)
        
        response = self.get_response(request)
        
        # Add security headers
        response = self._add_security_headers(response)
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _monitor_request(self, request, client_ip):
        """Monitor request for suspicious activity"""
        suspicious_patterns = [
            r'\.\./',  # Directory traversal
            r'<script',  # XSS
            r'union\s+select',  # SQL injection
            r'javascript:',  # XSS
        ]
        
        # Check URL
        for pattern in suspicious_patterns:
            if re.search(pattern, request.path, re.IGNORECASE):
                security_manager.record_suspicious_activity('suspicious_url', {
                    'ip': client_ip,
                    'url': request.path,
                    'pattern': pattern
                })
                break
        
        # Check headers
        suspicious_headers = ['HTTP_USER_AGENT', 'HTTP_REFERER']
        for header in suspicious_headers:
            if header in request.META:
                value = request.META[header]
                for pattern in suspicious_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        security_manager.record_suspicious_activity('suspicious_header', {
                            'ip': client_ip,
                            'header': header,
                            'value': value,
                            'pattern': pattern
                        })
                        break
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        return response


def require_authentication(view_func):
    """Decorator to require authentication"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            log_security_event('unauthenticated_access', {
                'path': request.path,
                'ip': request.META.get('REMOTE_ADDR')
            })
            return JsonResponse({'error': 'Authentication required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_permission(permission_name):
    """Decorator to require specific permission"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            # Check user permissions
            if not has_permission(request.user, permission_name):
                log_security_event('permission_denied', {
                    'user': request.user.username,
                    'permission': permission_name,
                    'path': request.path
                })
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_group(group_name):
    """Decorator to require user to be in specific group"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not request.user.groups.filter(name=group_name).exists():
                log_security_event('group_access_denied', {
                    'user': request.user.username,
                    'group': group_name,
                    'path': request.path
                })
                return JsonResponse({'error': 'Group access required'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_input(input_type):
    """Decorator to validate input data"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                # Validate request data
                if request.method == 'POST':
                    if hasattr(request, 'FILES') and request.FILES:
                        for file_key, file_obj in request.FILES.items():
                            security_manager.validate_input(file_obj, 'dicom_file')
                    
                    if request.content_type == 'application/json':
                        try:
                            data = json.loads(request.body)
                            security_manager.validate_input(data, 'api_request')
                        except json.JSONDecodeError:
                            return JsonResponse({'error': 'Invalid JSON'}, status=400)
                
                return view_func(request, *args, **kwargs)
                
            except ValueError as e:
                log_security_event('input_validation_failed', {
                    'error': str(e),
                    'input_type': input_type,
                    'path': request.path
                })
                return JsonResponse({'error': str(e)}, status=400)
            except Exception as e:
                error_tracker.track_error('input_validation_exception', str(e))
                return JsonResponse({'error': 'Internal server error'}, status=500)
        
        return wrapper
    return decorator


def has_permission(user: User, permission_name: str) -> bool:
    """Check if user has specific permission"""
    if user.is_superuser:
        return True
    
    # Check group-based permissions
    if permission_name == 'upload_files':
        return user.groups.filter(name__in=['Radiologists', 'Administrators']).exists()
    elif permission_name == 'view_studies':
        return user.groups.filter(name__in=['Radiologists', 'Administrators', 'Facilities']).exists()
    elif permission_name == 'admin_access':
        return user.groups.filter(name='Administrators').exists()
    elif permission_name == 'worklist_access':
        return user.groups.filter(name__in=['Radiologists', 'Administrators']).exists()
    
    return False


def generate_secure_token(data: str, secret_key: str = None) -> str:
    """Generate secure token for API authentication"""
    if secret_key is None:
        secret_key = settings.SECRET_KEY
    
    timestamp = str(int(datetime.utcnow().timestamp()))
    message = f"{data}:{timestamp}"
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{message}:{signature}"


def verify_secure_token(token: str, secret_key: str = None) -> bool:
    """Verify secure token"""
    if secret_key is None:
        secret_key = settings.SECRET_KEY
    
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return False
        
        data, timestamp, signature = parts
        
        # Check if token is expired (5 minutes)
        token_time = int(timestamp)
        now_time = int(datetime.utcnow().timestamp())
        if now_time - token_time > 300:
            return False
        
        # Verify signature
        message = f"{data}:{timestamp}"
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception:
        return False


class APIKeyManager:
    """Manage API keys for external integrations"""
    
    def __init__(self):
        self.api_keys = {}
    
    def generate_api_key(self, user_id: int, description: str = "") -> str:
        """Generate new API key for user"""
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = {
            'user_id': user_id,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'last_used': None
        }
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[int]:
        """Validate API key and return user ID"""
        if api_key in self.api_keys:
            self.api_keys[api_key]['last_used'] = datetime.utcnow().isoformat()
            return self.api_keys[api_key]['user_id']
        return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key"""
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            return True
        return False


# Global API key manager instance
api_key_manager = APIKeyManager()


def require_api_key(view_func):
    """Decorator to require valid API key"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return JsonResponse({'error': 'API key required'}, status=401)
        
        user_id = api_key_manager.validate_api_key(api_key)
        if not user_id:
            log_security_event('invalid_api_key', {'api_key': api_key[:10] + '...'})
            return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        # Add user_id to request for use in view
        request.api_user_id = user_id
        return view_func(request, *args, **kwargs)
    
    return wrapper