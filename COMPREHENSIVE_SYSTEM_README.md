# Noctis DICOM Viewer - Comprehensive System

## 🚀 Overview

Noctis is a comprehensive, enterprise-grade DICOM medical imaging platform built with Django. This system provides advanced DICOM processing, AI-powered analysis, 3D reconstruction, and a complete workflow management system for medical professionals.

## ✨ Key Features

### 🔬 Advanced DICOM Processing
- **Multi-format Support**: CT, MRI, X-ray, ultrasound, and more
- **Bulk Upload**: Handle large archives and multiple files simultaneously
- **Real-time Processing**: Stream processing with progress tracking
- **Image Enhancement**: AI-powered image enhancement for different modalities
- **3D Reconstruction**: MPR, MIP, and volume rendering capabilities

### 🤖 AI-Powered Analysis
- **Chest X-ray Analysis**: Automated detection of abnormalities
- **Bone Fracture Detection**: AI-assisted fracture identification
- **Cardiac Analysis**: 4D cardiac imaging analysis
- **Neurological Analysis**: Brain MRI analysis and segmentation
- **Vessel Analysis**: Angiogram and vessel reconstruction

### 📊 Workflow Management
- **Patient Worklist**: Complete patient management system
- **Study Tracking**: Real-time study status monitoring
- **Notification System**: Automated alerts and notifications
- **Reporting**: Comprehensive medical reporting system
- **Multi-facility Support**: Role-based access control

### 🔒 Enterprise Security
- **Input Validation**: Comprehensive security validation
- **Rate Limiting**: Protection against abuse
- **IP Blocking**: Advanced threat detection
- **Audit Logging**: Complete system audit trail
- **API Security**: Secure API key management

### 📈 System Monitoring
- **Real-time Monitoring**: Live system health tracking
- **Performance Metrics**: CPU, memory, disk usage monitoring
- **Error Tracking**: Comprehensive error analysis
- **Health Checks**: Automated system health validation
- **Alerting**: Proactive issue detection and notification

## 🏗️ System Architecture

### Core Components

```
noctisview/
├── viewer/                 # Main DICOM viewer application
│   ├── services.py        # Business logic layer
│   ├── models.py          # Database models
│   ├── views.py           # API endpoints
│   └── templates/         # UI templates
├── worklist/              # Workflow management
│   ├── views.py           # Worklist functionality
│   └── models.py          # Worklist models
├── noctisview/            # Core system
│   ├── security.py        # Security system
│   ├── monitoring.py      # System monitoring
│   ├── logging_config.py  # Logging system
│   └── settings.py        # Django settings
├── tests/                 # Comprehensive testing
│   └── test_comprehensive_system.py
└── manage_comprehensive_system.py  # System management
```

### Service Layer Architecture

The system uses a service-oriented architecture with clear separation of concerns:

- **DicomProcessingService**: Handles DICOM file processing
- **UploadService**: Manages file uploads and progress tracking
- **ImageProcessingService**: Provides image enhancement and analysis
- **WorklistService**: Manages patient workflow
- **ErrorHandlingService**: Centralized error management

## 🚀 Quick Start

### 1. System Requirements

- Python 3.8+
- 4GB RAM minimum
- 10GB free disk space
- Linux/Ubuntu recommended

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd noctisview

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run comprehensive deployment
python manage_comprehensive_system.py deploy
```

### 3. Start the System

```bash
# Start the server
python manage_comprehensive_system.py start

# Or use Django directly
python manage.py runserver 0.0.0.0:8000
```

### 4. Access the System

- **Main Application**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/api/

## 🛠️ System Management

### Comprehensive Management Script

The system includes a powerful management script that handles all aspects of system operation:

```bash
# Deploy the complete system
python manage_comprehensive_system.py deploy

# Run comprehensive tests
python manage_comprehensive_system.py test

# Check system health
python manage_comprehensive_system.py health

# Perform system maintenance
python manage_comprehensive_system.py maintenance

# Start/stop server
python manage_comprehensive_system.py start
python manage_comprehensive_system.py stop

# Generate system report
python manage_comprehensive_system.py report

# Monitor system continuously
python manage_comprehensive_system.py monitor --continuous
```

### Health Monitoring

The system provides comprehensive health monitoring:

```python
from noctisview.monitoring import get_system_status

# Get complete system status
status = get_system_status()
print(f"System Health: {status['health_check']['overall_status']}")
```

## 🔧 Configuration

### Environment Setup

Create a `.env` file for environment-specific settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379
```

### Security Configuration

The system includes comprehensive security features:

```python
# Security thresholds
SECURITY_THRESHOLDS = {
    'rate_limit': 100,  # requests per hour
    'max_file_size': 5 * 1024 * 1024 * 1024,  # 5GB
    'blocked_ips': [],
    'suspicious_patterns': [...]
}
```

## 📊 API Endpoints

### DICOM Processing

```http
POST /api/upload-dicom-files/
POST /api/upload-dicom-folder/
GET /api/upload-progress/{upload_id}/
GET /api/studies/
GET /api/studies/{study_id}/images/
```

### Image Processing

```http
GET /api/images/{image_id}/data/
POST /api/images/{image_id}/enhance-xray/
POST /api/images/{image_id}/reconstruct-mri/
POST /api/images/{image_id}/ai-analysis/
```

### Worklist Management

```http
GET /api/worklist/
POST /api/worklist/create/
PUT /api/worklist/{entry_id}/update/
GET /api/notifications/
```

## 🧪 Testing

### Comprehensive Test Suite

The system includes a comprehensive testing framework:

```bash
# Run all tests
python manage_comprehensive_system.py test

# Run specific test categories
python -m pytest tests/test_comprehensive_system.py::UploadSystemTestCase
python -m pytest tests/test_comprehensive_system.py::SecurityTestCase
python -m pytest tests/test_comprehensive_system.py::PerformanceTestCase
```

### Test Categories

- **Upload System Tests**: File upload functionality
- **Security Tests**: Input validation and security features
- **Image Processing Tests**: Image enhancement and analysis
- **Worklist Tests**: Workflow management
- **Integration Tests**: End-to-end workflows
- **Performance Tests**: System performance validation
- **Security Integration Tests**: Security feature integration

## 📈 Monitoring and Logging

### Real-time Monitoring

The system provides comprehensive monitoring:

```python
from noctisview.monitoring import system_monitor, health_check

# Get system metrics
metrics = system_monitor.metrics

# Run health checks
health_status = health_check.run_health_checks()
```

### Logging System

Structured logging with multiple log levels:

```python
from noctisview.logging_config import (
    log_security_event, log_upload_event, 
    log_processing_event, error_tracker
)

# Log security events
log_security_event('suspicious_activity', {'ip': '192.168.1.100'})

# Log upload events
log_upload_event('file_uploaded', {'filename': 'study.dcm'})

# Track errors
error_tracker.track_error('upload_failed', 'File too large')
```

## 🔒 Security Features

### Input Validation

```python
from noctisview.security import security_manager

# Validate DICOM file
result = security_manager.validate_input(file_obj, 'dicom_file')

# Validate user input
result = security_manager.validate_input(user_input, 'user_input')
```

### Rate Limiting

```python
# Check rate limit
allowed = security_manager.check_rate_limit('user_ip', limit=100)

# Block suspicious IP
security_manager.block_ip('192.168.1.100', 'Suspicious activity')
```

## 🚀 Performance Optimization

### Caching Strategy

The system implements comprehensive caching:

```python
from django.core.cache import cache

# Cache study data
cache.set(f'study_{study_id}', study_data, timeout=3600)

# Cache image data
cache.set(f'image_{image_id}', image_data, timeout=1800)
```

### Database Optimization

```python
# Optimize queries
from django.db.models import Prefetch

studies = DicomStudy.objects.prefetch_related(
    Prefetch('series', queryset=DicomSeries.objects.select_related('study'))
)
```

## 📋 System Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB free space
- **OS**: Linux/Ubuntu 18.04+
- **Python**: 3.8+

### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **OS**: Ubuntu 20.04+
- **Python**: 3.9+

## 🔧 Troubleshooting

### Common Issues

1. **Upload Failures**
   ```bash
   # Check file permissions
   sudo chown -R www-data:www-data media/
   sudo chmod -R 755 media/
   ```

2. **Database Issues**
   ```bash
   # Reset database
   python manage.py flush
   python manage.py migrate
   ```

3. **Performance Issues**
   ```bash
   # Check system resources
   python manage_comprehensive_system.py health
   
   # Optimize database
   python manage_comprehensive_system.py maintenance
   ```

### Log Analysis

```bash
# View system logs
tail -f logs/all.log

# View error logs
tail -f logs/errors.log

# View security logs
tail -f logs/security.log
```

## 📚 Documentation

### API Documentation

Complete API documentation is available at `/api/docs/` when the system is running.

### Code Documentation

All code includes comprehensive docstrings and type hints for easy understanding and maintenance.

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd noctisview

# Setup development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python manage_comprehensive_system.py test
```

### Code Standards

- Follow PEP 8 style guidelines
- Include comprehensive docstrings
- Add type hints for all functions
- Write tests for new features
- Update documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help

1. **Check Documentation**: Review this README and inline documentation
2. **Run Health Check**: `python manage_comprehensive_system.py health`
3. **Check Logs**: Review logs in the `logs/` directory
4. **Run Tests**: `python manage_comprehensive_system.py test`

### Reporting Issues

When reporting issues, please include:

- System health report: `python manage_comprehensive_system.py report`
- Error logs from `logs/errors.log`
- Steps to reproduce the issue
- System specifications

## 🎯 Roadmap

### Upcoming Features

- **Real-time Collaboration**: Multi-user simultaneous viewing
- **Advanced AI Models**: Enhanced AI analysis capabilities
- **Mobile Support**: Native mobile applications
- **PACS Integration**: Direct PACS system integration
- **Cloud Deployment**: Kubernetes deployment support

### Performance Improvements

- **Microservices Architecture**: Service decomposition
- **Load Balancing**: Horizontal scaling support
- **Auto-scaling**: Automatic resource management
- **Edge Computing**: Distributed processing

---

**Noctis DICOM Viewer** - Advanced medical imaging platform for the modern healthcare environment.