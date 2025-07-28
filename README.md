# Advanced DICOM Medical Viewer

A comprehensive medical imaging system built with Django for healthcare facilities to manage, view, and analyze DICOM studies with advanced features including AI integration, 3D visualization, and role-based access control.

## Features

### Core DICOM Viewing
- **Advanced Image Viewer**: High-performance DICOM image display with zoom, pan, and window/level controls
- **Multi-format Support**: Native DICOM file support with automatic metadata extraction
- **Series Navigation**: Easy navigation through study series and individual images
- **Cross-platform Compatibility**: Web-based viewer accessible from any device

### Enhanced Measurement Tools
- **Multiple Units**: Measurements in millimeters, centimeters, and pixels
- **Distance Measurements**: Precise linear measurements with calibrated pixel spacing
- **Ellipse ROI Tool**: Region of interest measurements with Hounsfield unit analysis
- **Draggable Annotations**: Enhanced text annotations that can be moved and enlarged
- **Measurement History**: Save and review all measurements with user attribution

### 3D Visualization and Reconstruction
- **MPR (Multi-Planar Reconstruction)**: Sagittal, coronal, and axial views
- **3D Bone Visualization**: Volume rendering for orthopedic applications
- **Angiography Reconstruction**: MIP (Maximum Intensity Projection) for vascular studies
- **Virtual Surgery Mode**: AI-assisted surgical planning with anatomical highlighting

### AI Integration
- **Real-time Analysis**: AI-powered image analysis with confidence scoring
- **Virtual Surgery Assistant**: Intelligent surgical planning recommendations
- **Hounsfield Unit Analysis**: Automated tissue density analysis
- **Interactive Chat Interface**: Copy-paste functionality for AI insights
- **Analysis History**: Track all AI analyses with user context

### Patient Worklist Management
- **Comprehensive Patient Database**: Store and manage patient information
- **Study Status Tracking**: Monitor study workflow from upload to reporting
- **Search and Filtering**: Advanced search by patient name, ID, modality, and date
- **Clinical Information**: Add and edit clinical notes and patient history
- **Report Generation**: Create and manage radiology reports

### Role-Based Access Control
- **Multi-level Security**: Radiologist, Admin, and Facility user roles
- **Facility Isolation**: Facilities only see their own patients (configurable)
- **Admin Oversight**: Administrators can access all facilities
- **Radiologist Access**: Cross-facility access for reading specialists
- **Audit Trail**: Track user access and modifications

### Advanced Reporting
- **Professional Reports**: Generate reports with facility letterheads
- **Print Functionality**: High-quality PDF generation for physical copies
- **Digital Signatures**: Electronic signature support for radiologists
- **Report Templates**: Standardized reporting formats
- **Multi-facility Support**: Separate report generation per facility

### Notification System
- **Real-time Alerts**: Instant notifications for new uploads
- **Role-based Notifications**: Targeted alerts for radiologists and admins
- **Study Status Updates**: Notifications for report completion
- **Priority Handling**: Urgent findings flagging system

## Installation

### Prerequisites
- Python 3.8+
- Django 3.1+
- Modern web browser with HTML5 support

### Quick Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd advanced-dicom-viewer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   - Main application: http://localhost:8000/
   - Admin interface: http://localhost:8000/admin/

## Usage

### Getting Started
1. **Setup Facilities**: Create healthcare facilities in the admin panel
2. **Create User Profiles**: Assign roles and facilities to users
3. **Upload DICOM Studies**: Use the upload interface or API endpoints
4. **Access Worklist**: View and manage patient studies
5. **Launch Viewer**: Open studies in the advanced DICOM viewer

### User Roles

#### Facility Users
- View patients from their facility only
- Add clinical information
- Upload new studies
- Print reports

#### Radiologists
- Access patients from all facilities
- Write and finalize reports
- Receive notifications for new uploads
- Access all measurement and AI tools

#### Administrators
- Full system access
- Manage facilities and users
- System configuration
- Cross-facility oversight

### Workflow

1. **Study Upload**: DICOM files uploaded to the system
2. **Notification**: Radiologists notified of new studies
3. **Review**: Studies reviewed using the advanced viewer
4. **Measurement**: Precise measurements and ROI analysis
5. **AI Analysis**: Optional AI-assisted diagnosis
6. **Reporting**: Generate professional reports
7. **Distribution**: Reports distributed to facilities

## API Documentation

### Study Management
- `GET /api/studies/` - List all studies
- `GET /api/studies/{id}/images/` - Get study images
- `POST /api/upload/` - Upload DICOM files

### Image Processing
- `GET /api/images/{id}/data/` - Get processed image data
- `POST /api/measurements/save/` - Save measurements
- `POST /api/annotations/save/` - Save annotations

### AI Integration
- `POST /api/ai-analysis/` - Request AI analysis
- `GET /api/check-new-uploads/` - Check for notifications

### Reporting
- `POST /api/patients/{id}/clinical-info/` - Save clinical information
- `POST /api/patients/{id}/report/` - Save reports
- `GET /reports/print/{id}/` - Generate printable reports

## Configuration

### Settings
Key configuration options in `settings.py`:

```python
# Media files for DICOM storage
MEDIA_ROOT = '/path/to/dicom/storage'

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024   # 100MB

# Security settings
SECURE_SSL_REDIRECT = True  # For production
SECURE_HSTS_SECONDS = 31536000  # For production
```

### Database
The system supports PostgreSQL, MySQL, and SQLite. For production use:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dicom_viewer',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Technology Stack

- **Backend**: Django 3.1+ with Django REST Framework
- **Frontend**: Modern JavaScript (ES6+) with HTML5 Canvas
- **DICOM Processing**: pydicom library
- **Image Processing**: Pillow and NumPy
- **3D Visualization**: Three.js (optional)
- **Database**: PostgreSQL/MySQL/SQLite
- **Authentication**: Django's built-in authentication system

## Security Features

- **CSRF Protection**: Built-in Django CSRF middleware
- **User Authentication**: Secure login/logout system
- **Role-based Permissions**: Granular access control
- **Facility Isolation**: Data segregation by facility
- **Audit Logging**: Track all user actions
- **Secure File Upload**: Validated DICOM file uploads

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the documentation
- Create an issue on GitHub
- Contact the development team

## Compliance

This system is designed to comply with:
- HIPAA regulations for healthcare data
- DICOM standards for medical imaging
- HL7 standards for healthcare interoperability
- FDA guidelines for medical software (Class II)

**Note**: This software is intended for use by qualified medical professionals only. It should not be used as the sole basis for medical diagnosis or treatment decisions.