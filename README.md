# NoctisView - Advanced DICOM Medical Image Viewer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Django 5.0](https://img.shields.io/badge/django-5.0-green.svg)](https://www.djangoproject.com/)

NoctisView is a powerful, web-based DICOM medical image viewer with advanced features including AI-powered analysis, patient data anonymization, batch processing, and comprehensive image export capabilities.

## 🌟 Features

### Core Features
- **DICOM File Support**: Full support for DICOM medical image format
- **Web-Based Viewer**: Modern, responsive web interface
- **Multi-Study Management**: Organize and manage multiple patient studies
- **Measurement Tools**: Line, angle, and area measurements with pixel-to-mm conversion
- **Annotations**: Add notes and markers to images
- **Window/Level Adjustment**: Real-time brightness and contrast control

### Advanced Features
- **AI-Powered Analysis**
  - Anomaly detection using computer vision
  - Automatic image enhancement
  - Region of Interest (ROI) analysis
  - Deep learning predictions (with custom models)

- **Patient Data Protection**
  - DICOM anonymization with configurable options
  - Batch anonymization for multiple files
  - UID mapping preservation
  - Date shifting for temporal studies

- **Batch Processing**
  - Process entire directories of DICOM files
  - Parallel processing for performance
  - Metadata extraction to CSV
  - Progress tracking and reporting

- **Export Capabilities**
  - Export to PNG, JPEG, or NumPy formats
  - Batch export with metadata
  - Preserve window/level settings

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (optional, SQLite for development)
- Redis (for Celery tasks)
- 4GB+ RAM recommended

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourorg/noctisview.git
cd noctisview
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Collect static files**
```bash
python manage.py collectstatic
```

8. **Run the development server**
```bash
python manage.py runserver
```

Visit http://localhost:8000 to access the application.

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Build and start services**
```bash
docker-compose up -d
```

2. **Run migrations**
```bash
docker-compose exec web python manage.py migrate
```

3. **Create superuser**
```bash
docker-compose exec web python manage.py createsuperuser
```

The application will be available at http://localhost

### Manual Docker Build

```bash
# Build image
docker build -t noctisview .

# Run container
docker run -d -p 8000:8000 --env-file .env noctisview
```

## 📖 Usage

### Uploading DICOM Files

1. Click "Upload Files" in the main interface
2. Select one or more DICOM files
3. Files are automatically organized by study and series

### Using AI Analysis

1. Open a DICOM image
2. Click the AI button in the toolbar
3. Select analysis type:
   - **Anomaly Detection**: Identifies potential areas of interest
   - **Enhancement**: Improves image quality
   - **ROI Measurement**: Analyzes selected regions

### Anonymizing Patient Data

1. Select a study or upload files
2. Choose "Anonymize" from the menu
3. Configure options:
   - Keep dates (shifts them randomly)
   - Preserve UID structure
   - Use secure mode for extra protection

### Batch Processing

```python
from viewer.batch_processor import DicomBatchProcessor

processor = DicomBatchProcessor(num_workers=4)
results = processor.process_directory(
    directory_path="/path/to/dicom/files",
    process_func=your_processing_function,
    output_dir="/path/to/output"
)
```

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```env
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=noctisview_db
DB_USER=postgres
DB_PASSWORD=secure-password

# AI Features
ENABLE_AI_ANALYSIS=True
AI_MODEL_PATH=/app/models/

# File Storage
DICOM_STORAGE_PATH=media/dicom_files
MAX_UPLOAD_SIZE=104857600  # 100MB
```

### AI Model Configuration

To use custom AI models:

1. Place your trained models in the `models/ai_models/` directory
2. Update the model path in your API calls
3. Ensure model compatibility with the predictor interface

## 📊 API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.

### Quick Examples

**Upload DICOM file:**
```bash
curl -X POST -F "files=@scan.dcm" http://localhost:8000/viewer/api/upload/
```

**Analyze image:**
```bash
curl -X POST http://localhost:8000/viewer/api/images/123/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "anomaly_detection"}'
```

## 🧪 Testing

Run the test suite:

```bash
python manage.py test
```

With coverage:
```bash
coverage run --source='.' manage.py test
coverage report
```

## 🔒 Security

- All patient data is encrypted at rest
- HTTPS required in production
- Session-based authentication
- CSRF protection enabled
- Comprehensive audit logging
- PHI removal through anonymization

## 📈 Performance

- Supports files up to 100MB by default
- Parallel processing for batch operations
- Redis caching for processed images
- Optimized for multi-core systems
- WebSocket support for real-time updates

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [pydicom](https://pydicom.github.io/) - DICOM file handling
- [OpenCV](https://opencv.org/) - Image processing
- [PyTorch](https://pytorch.org/) - Deep learning framework
- [Django](https://www.djangoproject.com/) - Web framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourorg/noctisview/issues)
- **Email**: support@noctisview.example.com
- **Documentation**: [https://docs.noctisview.example.com](https://docs.noctisview.example.com)

## 🚦 Status

- Build: ![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
- Tests: ![Test Status](https://img.shields.io/badge/tests-passing-brightgreen)
- Coverage: ![Coverage](https://img.shields.io/badge/coverage-85%25-yellow)

---

Made with ❤️ by the NoctisView Team