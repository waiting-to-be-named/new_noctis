# NoctisView - Advanced DICOM Viewer

NoctisView is a comprehensive web-based DICOM viewer with advanced measurement capabilities, AI analysis, 3D reconstruction, and multi-facility management.

## 🚀 Enhanced Features

### 📏 Advanced Measurements
- **Multiple Units**: Support for millimeters (mm), centimeters (cm), and pixels (px)
- **Ellipse Measurements**: Draw elliptical regions for area calculations
- **Hounsfield Units**: Measure Hounsfield Units (HU) in CT images with elliptical ROI
- **Draggable Annotations**: Annotations can be moved and resized
- **Enhanced Font Sizes**: Configurable annotation text sizes

### 🤖 AI Analysis
- **Anomaly Detection**: AI-powered analysis to highlight potential abnormalities
- **Results Panel**: Interactive chat-like window showing AI findings
- **Copy & Paste**: Copy AI results to clipboard for easy sharing
- **Confidence Scores**: View AI analysis confidence levels

### 🎯 3D Reconstruction
- **Multi-Planar Reconstruction (MPR)**: Advanced MPR views
- **3D Bone Reconstruction**: Specialized bone visualization
- **Angiography Reconstruction**: Vascular imaging support
- **Virtual Surgery Planning**: Tools for surgical planning

### 🏥 Multi-Facility Management
- **Facility Isolation**: Each facility sees only their own patients
- **Radiologist Access**: Radiologists and admins can access all facilities
- **Custom Letterheads**: Facility-specific report letterheads
- **Print Reports**: Professional report printing with facility branding

### 📋 Patient Worklist
- **Grey Background with Green Highlights**: Modern medical interface design
- **Priority-based Color Coding**: Visual priority indicators
- **Real-time Filtering**: Filter by status, priority, date, and search terms
- **Clinical Information Management**: Add and edit clinical details
- **DICOM SCP Server**: Receive remote DICOM images

### 📊 Reporting System
- **Role-based Access**: Only radiologists and admins can create reports
- **Draft/Preliminary/Final**: Report status management
- **Print with Letterhead**: Professional report output
- **Digital Signatures**: Electronic signature support

### 🔔 Notifications
- **Real-time Notifications**: Instant alerts for new uploads
- **Role-based Delivery**: Notifications sent to appropriate users
- **Interactive Alerts**: Click to view and dismiss notifications

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Django 5.2+
- Node.js (for frontend build tools)

### Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd noctisview
```

2. Install Python dependencies:
```bash
pip install django djangorestframework pydicom pillow numpy
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Set up demo data:
```bash
python manage.py setup_demo_data
```

5. Run the development server:
```bash
python manage.py runserver
```

## 🔐 User Roles & Access

### Administrator
- **Username**: `admin`
- **Password**: `admin123`
- **Access**: Full system access, all facilities, user management

### Radiologist
- **Username**: `radiologist`
- **Password**: `radio123`
- **Access**: All studies, report creation, notifications

### Facility Users
- **City General**: `facility1` / `facility123`
- **Regional Medical**: `facility2` / `facility123`
- **Access**: Facility-specific studies only

## 🌐 System Access

### Main Applications
- **DICOM Viewer**: http://localhost:8000/
- **Patient Worklist**: http://localhost:8000/worklist/
- **Admin Panel**: http://localhost:8000/admin/

### Key Features by URL
- `/` - Main DICOM viewer with all measurement tools
- `/worklist/` - Patient worklist with filtering and management
- `/worklist/facility/` - Facility-specific dashboard
- `/worklist/radiologist/` - Radiologist dashboard with notifications

## 📱 User Interface

### DICOM Viewer
- **Dark Theme**: Professional medical imaging interface
- **Tool Palette**: Left sidebar with measurement and analysis tools
- **Control Panel**: Right sidebar with settings and information
- **Overlay Information**: Window/level, zoom, and slice information

### Worklist Interface
- **Grey Background**: Easy on the eyes for long sessions
- **Green Highlights**: Selected rows highlighted in green
- **Priority Badges**: Color-coded priority indicators
- **Action Buttons**: View, Clinical Info, and Report actions

## 🔧 Technical Architecture

### Backend
- **Django Framework**: Python web framework
- **Django REST Framework**: API development
- **SQLite Database**: Default database (can be changed to PostgreSQL/MySQL)
- **DICOM Processing**: pydicom library for DICOM file handling

### Frontend
- **Vanilla JavaScript**: No external frameworks for maximum compatibility
- **HTML5 Canvas**: Image rendering and overlay drawing
- **CSS Grid/Flexbox**: Modern responsive layouts
- **Font Awesome**: Professional medical icons

### Database Models
- **Facility**: Healthcare facility management
- **UserProfile**: Extended user roles and permissions
- **DicomStudy/Series/Image**: DICOM data hierarchy
- **Measurement/Annotation**: User annotations and measurements
- **Report**: Radiology reports with workflow
- **Notification**: Real-time notification system
- **AIAnalysis**: AI analysis results storage
- **WorklistEntry**: Patient worklist management

## 🎨 Measurement Tools

### Line Measurement
- Click and drag to measure distances
- Automatic unit conversion based on pixel spacing
- Support for mm, cm, and pixel units

### Ellipse Measurement
- Draw elliptical regions of interest
- Calculate area measurements
- Hounsfield Unit analysis for CT images

### Annotation Tools
- Text annotations with customizable font sizes
- Draggable and resizable annotations
- Persistent storage across sessions

## 🧠 AI Integration

### Current Capabilities
- Simulated anomaly detection (ready for real AI integration)
- Confidence scoring
- Region highlighting
- Results export

### Integration Points
- REST API endpoints for AI services
- Asynchronous processing support
- Results visualization and interaction

## 📈 3D Reconstruction Features

### Available Modes
1. **MPR (Multi-Planar Reconstruction)**
   - Axial, Sagittal, and Coronal views
   - Real-time slice navigation

2. **3D Bone Reconstruction**
   - Volume rendering for bone structures
   - Adjustable opacity and windowing

3. **Angiography Reconstruction**
   - Vascular structure visualization
   - Maximum Intensity Projection (MIP)

4. **Virtual Surgery Planning**
   - Surgical planning tools
   - Measurement and annotation in 3D space

## 🔐 Security & Compliance

### Data Protection
- Role-based access control
- Facility data isolation
- Secure file upload handling
- Session management

### HIPAA Considerations
- Patient data anonymization options
- Audit trail logging
- Secure report generation
- Access control logging

## 🚀 Deployment

### Production Considerations
- Use PostgreSQL or MySQL for production
- Configure proper media file serving
- Set up SSL/TLS encryption
- Configure backup strategies
- Monitor system performance

### Environment Variables
```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=your-database-url
MEDIA_ROOT=/path/to/media/files
STATIC_ROOT=/path/to/static/files
```

## 🔧 Customization

### Adding New Measurement Types
1. Update the `Measurement` model in `viewer/models.py`
2. Add new measurement logic in `dicom_viewer.js`
3. Update the UI controls in the viewer template

### Custom AI Integration
1. Implement AI analysis endpoints in `viewer/views.py`
2. Update the frontend AI analysis functions
3. Configure AI service connections

### Facility Branding
1. Upload facility logos through the admin panel
2. Customize report templates in `templates/reports/`
3. Modify CSS for facility-specific styling

## 📞 Support & Documentation

### Key Files
- `viewer/models.py` - Database models
- `viewer/views.py` - Main application logic
- `worklist/views.py` - Worklist functionality
- `static/js/dicom_viewer.js` - Frontend logic
- `static/css/dicom_viewer.css` - Viewer styling
- `static/css/worklist.css` - Worklist styling

### API Endpoints
- `/api/studies/` - Study management
- `/api/measurements/` - Measurement operations
- `/api/annotations/` - Annotation management
- `/api/reports/` - Report generation
- `/api/notifications/` - Notification system
- `/worklist/api/worklist/` - Worklist operations

## 🎯 Future Enhancements

### Planned Features
- Real AI model integration
- Advanced 3D rendering
- Mobile responsive design
- Multi-language support
- Advanced reporting templates
- Integration with hospital systems (HL7, FHIR)
- Advanced user management
- Performance monitoring
- Automated backup systems

### Contributing
This system is designed to be extensible. New features can be added by:
1. Extending the Django models
2. Adding new API endpoints
3. Implementing frontend functionality
4. Adding appropriate tests

## 📝 License

This project is designed for medical imaging applications. Please ensure compliance with local healthcare regulations and data protection laws when deploying in production environments.

---

**NoctisView** - Advanced DICOM Viewing for Modern Healthcare