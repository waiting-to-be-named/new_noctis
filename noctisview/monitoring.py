"""
Comprehensive system monitoring and health check system for Noctis DICOM viewer.
This module provides real-time monitoring, health checks, and alerting capabilities.
"""

import os
import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.core.cache import cache
from django.db import connection
import logging
import json
from pathlib import Path

from .logging_config import performance_monitor, error_tracker, log_security_event

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Comprehensive system monitoring"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.health_status = 'healthy'
        self.last_check = None
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Thresholds for alerts
        self.thresholds = {
            'cpu_usage': 80.0,  # 80% CPU usage
            'memory_usage': 85.0,  # 85% memory usage
            'disk_usage': 90.0,  # 90% disk usage
            'response_time': 5.0,  # 5 seconds
            'error_rate': 10.0,  # 10% error rate
            'upload_failure_rate': 5.0,  # 5% upload failure rate
        }
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self.collect_system_metrics()
                self.check_health_status()
                self.check_alerts()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Database connections
            db_connections = len(connection.queries) if hasattr(connection, 'queries') else 0
            
            # Cache status
            cache_status = self._check_cache_status()
            
            # Store metrics
            self.metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'memory_available': memory.available,
                'disk_usage': disk_percent,
                'disk_free': disk.free,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'db_connections': db_connections,
                'cache_status': cache_status,
                'process_count': len(psutil.pids()),
            }
            
            # Record performance metrics
            performance_monitor.record_metric('cpu_usage', cpu_percent)
            performance_monitor.record_metric('memory_usage', memory_percent)
            performance_monitor.record_metric('disk_usage', disk_percent)
            
            self.last_check = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _check_cache_status(self) -> Dict[str, Any]:
        """Check cache status"""
        try:
            # Test cache functionality
            test_key = f"health_check_{int(time.time())}"
            cache.set(test_key, "test_value", 60)
            test_result = cache.get(test_key)
            cache.delete(test_key)
            
            return {
                'status': 'healthy' if test_result == "test_value" else 'unhealthy',
                'test_passed': test_result == "test_value"
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_health_status(self):
        """Check overall system health"""
        if not self.metrics:
            return
        
        health_checks = []
        
        # CPU check
        if self.metrics['cpu_usage'] > self.thresholds['cpu_usage']:
            health_checks.append(f"High CPU usage: {self.metrics['cpu_usage']}%")
        
        # Memory check
        if self.metrics['memory_usage'] > self.thresholds['memory_usage']:
            health_checks.append(f"High memory usage: {self.metrics['memory_usage']}%")
        
        # Disk check
        if self.metrics['disk_usage'] > self.thresholds['disk_usage']:
            health_checks.append(f"High disk usage: {self.metrics['disk_usage']}%")
        
        # Cache check
        if self.metrics['cache_status']['status'] != 'healthy':
            health_checks.append(f"Cache issues: {self.metrics['cache_status']}")
        
        # Determine overall health
        if health_checks:
            self.health_status = 'warning' if len(health_checks) <= 2 else 'critical'
            logger.warning(f"Health issues detected: {', '.join(health_checks)}")
        else:
            self.health_status = 'healthy'
    
    def check_alerts(self):
        """Check for alert conditions"""
        if not self.metrics:
            return
        
        alerts = []
        
        # CPU alert
        if self.metrics['cpu_usage'] > self.thresholds['cpu_usage']:
            alerts.append({
                'type': 'high_cpu_usage',
                'severity': 'warning',
                'message': f"CPU usage is {self.metrics['cpu_usage']}%",
                'value': self.metrics['cpu_usage'],
                'threshold': self.thresholds['cpu_usage'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Memory alert
        if self.metrics['memory_usage'] > self.thresholds['memory_usage']:
            alerts.append({
                'type': 'high_memory_usage',
                'severity': 'warning',
                'message': f"Memory usage is {self.metrics['memory_usage']}%",
                'value': self.metrics['memory_usage'],
                'threshold': self.thresholds['memory_usage'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Disk alert
        if self.metrics['disk_usage'] > self.thresholds['disk_usage']:
            alerts.append({
                'type': 'high_disk_usage',
                'severity': 'critical',
                'message': f"Disk usage is {self.metrics['disk_usage']}%",
                'value': self.metrics['disk_usage'],
                'threshold': self.thresholds['disk_usage'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Add new alerts
        for alert in alerts:
            if not self._is_duplicate_alert(alert):
                self.alerts.append(alert)
                self._send_alert(alert)
    
    def _is_duplicate_alert(self, new_alert: Dict[str, Any]) -> bool:
        """Check if alert is duplicate (within last 5 minutes)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        for alert in self.alerts:
            if (alert['type'] == new_alert['type'] and 
                datetime.fromisoformat(alert['timestamp']) > cutoff_time):
                return True
        
        return False
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert notification"""
        logger.warning(f"ALERT: {alert['message']}")
        
        # Log security event for critical alerts
        if alert['severity'] == 'critical':
            log_security_event('system_critical_alert', alert)
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return {
            'status': self.health_status,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'metrics': self.metrics,
            'alerts': self.alerts[-10:],  # Last 10 alerts
            'thresholds': self.thresholds,
            'monitoring_active': self.monitoring_active,
        }


class DatabaseMonitor:
    """Monitor database performance and health"""
    
    def __init__(self):
        self.query_log = []
        self.slow_queries = []
        self.connection_issues = []
    
    def log_query(self, query: str, execution_time: float):
        """Log database query"""
        query_info = {
            'query': query,
            'execution_time': execution_time,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.query_log.append(query_info)
        
        # Track slow queries
        if execution_time > 1.0:  # Queries taking more than 1 second
            self.slow_queries.append(query_info)
            logger.warning(f"Slow query detected: {execution_time}s - {query[:100]}...")
        
        # Keep only last 1000 queries
        if len(self.query_log) > 1000:
            self.query_log = self.query_log[-1000:]
        
        # Keep only last 100 slow queries
        if len(self.slow_queries) > 100:
            self.slow_queries = self.slow_queries[-100:]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with connection.cursor() as cursor:
                # Get table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        attname,
                        n_distinct,
                        correlation
                    FROM pg_stats 
                    WHERE schemaname = 'public'
                    LIMIT 10
                """)
                stats = cursor.fetchall()
                
                # Get connection info
                cursor.execute("""
                    SELECT 
                        count(*) as active_connections,
                        state
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                    GROUP BY state
                """)
                connections = cursor.fetchall()
                
                return {
                    'total_queries': len(self.query_log),
                    'slow_queries': len(self.slow_queries),
                    'avg_query_time': sum(q['execution_time'] for q in self.query_log) / len(self.query_log) if self.query_log else 0,
                    'active_connections': sum(c[0] for c in connections),
                    'table_stats': stats,
                    'last_slow_query': self.slow_queries[-1] if self.slow_queries else None,
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}


class UploadMonitor:
    """Monitor upload system performance"""
    
    def __init__(self):
        self.upload_stats = {
            'total_uploads': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'total_files_processed': 0,
            'total_size_uploaded': 0,
            'upload_times': [],
        }
    
    def log_upload(self, success: bool, file_count: int = 1, size_bytes: int = 0, duration: float = 0):
        """Log upload attempt"""
        self.upload_stats['total_uploads'] += 1
        
        if success:
            self.upload_stats['successful_uploads'] += 1
            self.upload_stats['total_files_processed'] += file_count
            self.upload_stats['total_size_uploaded'] += size_bytes
            self.upload_stats['upload_times'].append(duration)
        else:
            self.upload_stats['failed_uploads'] += 1
        
        # Keep only last 100 upload times
        if len(self.upload_stats['upload_times']) > 100:
            self.upload_stats['upload_times'] = self.upload_stats['upload_times'][-100:]
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        if not self.upload_stats['upload_times']:
            avg_time = 0
        else:
            avg_time = sum(self.upload_stats['upload_times']) / len(self.upload_stats['upload_times'])
        
        success_rate = (self.upload_stats['successful_uploads'] / self.upload_stats['total_uploads'] * 100) if self.upload_stats['total_uploads'] > 0 else 0
        
        return {
            'total_uploads': self.upload_stats['total_uploads'],
            'successful_uploads': self.upload_stats['successful_uploads'],
            'failed_uploads': self.upload_stats['failed_uploads'],
            'success_rate': success_rate,
            'total_files_processed': self.upload_stats['total_files_processed'],
            'total_size_uploaded_mb': self.upload_stats['total_size_uploaded'] / (1024 * 1024),
            'average_upload_time': avg_time,
            'recent_upload_times': self.upload_stats['upload_times'][-10:],
        }


class HealthCheck:
    """Comprehensive health check system"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.db_monitor = DatabaseMonitor()
        self.upload_monitor = UploadMonitor()
        self.checks = []
    
    def add_check(self, name: str, check_func, critical: bool = False):
        """Add a health check"""
        self.checks.append({
            'name': name,
            'function': check_func,
            'critical': critical
        })
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': [],
            'system_metrics': self.system_monitor.get_health_report(),
            'database_stats': self.db_monitor.get_database_stats(),
            'upload_stats': self.upload_monitor.get_upload_stats(),
        }
        
        critical_failures = 0
        
        for check in self.checks:
            try:
                check_result = check['function']()
                status = 'pass' if check_result else 'fail'
                
                if status == 'fail' and check['critical']:
                    critical_failures += 1
                
                results['checks'].append({
                    'name': check['name'],
                    'status': status,
                    'critical': check['critical'],
                    'result': check_result
                })
                
            except Exception as e:
                logger.error(f"Health check '{check['name']}' failed: {e}")
                results['checks'].append({
                    'name': check['name'],
                    'status': 'error',
                    'critical': check['critical'],
                    'error': str(e)
                })
                
                if check['critical']:
                    critical_failures += 1
        
        # Determine overall status
        if critical_failures > 0:
            results['overall_status'] = 'critical'
        elif any(check['status'] == 'fail' for check in results['checks']):
            results['overall_status'] = 'warning'
        else:
            results['overall_status'] = 'healthy'
        
        return results
    
    def setup_default_checks(self):
        """Setup default health checks"""
        
        def check_database_connection():
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
            except Exception:
                return False
        
        def check_cache_functionality():
            try:
                test_key = f"health_check_{int(time.time())}"
                cache.set(test_key, "test", 60)
                result = cache.get(test_key)
                cache.delete(test_key)
                return result == "test"
            except Exception:
                return False
        
        def check_disk_space():
            try:
                disk = psutil.disk_usage('/')
                return (disk.free / disk.total) > 0.1  # At least 10% free
            except Exception:
                return False
        
        def check_memory_usage():
            try:
                memory = psutil.virtual_memory()
                return memory.percent < 90  # Less than 90% usage
            except Exception:
                return False
        
        def check_upload_directory():
            try:
                upload_dir = Path(settings.MEDIA_ROOT) / 'dicom_files'
                return upload_dir.exists() and os.access(upload_dir, os.W_OK)
            except Exception:
                return False
        
        # Add checks
        self.add_check("Database Connection", check_database_connection, critical=True)
        self.add_check("Cache Functionality", check_cache_functionality, critical=True)
        self.add_check("Disk Space", check_disk_space, critical=True)
        self.add_check("Memory Usage", check_memory_usage, critical=False)
        self.add_check("Upload Directory", check_upload_directory, critical=True)


# Global instances
system_monitor = SystemMonitor()
db_monitor = DatabaseMonitor()
upload_monitor = UploadMonitor()
health_check = HealthCheck()

# Setup default health checks
health_check.setup_default_checks()

# Start monitoring
system_monitor.start_monitoring()


def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status"""
    return {
        'health_check': health_check.run_health_checks(),
        'error_summary': error_tracker.get_error_summary(),
        'performance_summary': {
            'cpu_usage': performance_monitor.get_metric_summary('cpu_usage'),
            'memory_usage': performance_monitor.get_metric_summary('memory_usage'),
            'disk_usage': performance_monitor.get_metric_summary('disk_usage'),
        }
    }


def log_upload_attempt(success: bool, file_count: int = 1, size_bytes: int = 0, duration: float = 0):
    """Log upload attempt for monitoring"""
    upload_monitor.log_upload(success, file_count, size_bytes, duration)


def log_database_query(query: str, execution_time: float):
    """Log database query for monitoring"""
    db_monitor.log_query(query, execution_time)