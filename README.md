# DICOM Viewer System

A comprehensive web-based DICOM medical imaging viewer with advanced features including AI analysis, 3D reconstruction, measurements, and worklist management.

## Features

### DICOM Viewer
- **Advanced Measurements**: Support for line measurements in pixels, millimeters, and centimeters
- **Ellipse Tool**: Measure Hounsfield Units (HU) with mean, min, max, and standard deviation
- **Annotations**: Create draggable, resizable annotations with customizable font size and color
- **Window/Level Presets**: Quick presets for lung, bone, soft tissue, and brain
- **Zoom & Pan**: Interactive image navigation
- **Crosshair**: Reference lines for precise positioning
- **Image Inversion**: Toggle image negative/positive

### AI Analysis
- Automatic abnormality detection with highlighted regions
- Confidence scores for findings
- Interactive chat interface for AI results
- Copy/paste functionality for analysis results

### 3D Reconstruction
- Multi-Planar Reconstruction (MPR)
- 3D Bone visualization
- Angiography reconstruction
- Virtual surgery planning interface

### Worklist Management
- Grey-themed interface with green patient row highlights
- Patient scheduling and tracking
- Clinical information management
- Multi-facility support with separate views
- Status tracking (scheduled, in progress, completed)

### Reporting System
- Radiologist report creation and editing
- Report status workflow (draft, finalized, printed)
- PDF generation with facility letterhead
- Print functionality for facilities

### Notifications
- Real-time notifications for new study uploads
- Automatic alerts for radiologists and administrators
- Facility-specific notifications

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dicom-viewer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Access the system at `http://localhost:8000`

## Usage

### Home Page
- Click "Launch DICOM Viewer" to open the viewer
- Click "Worklist" to access patient management

### DICOM Viewer
1. **Loading Images**:
   - Click "Load DICOM Files" to upload local files
   - Select "Open Worklist" from dropdown to load from system

2. **Measurements**:
   - Select measurement tool
   - Choose unit (px, mm, cm) from dropdown
   - Click and drag to measure

3. **Ellipse HU Measurement**:
   - Select ellipse tool
   - Draw ellipse around region of interest
   - View HU statistics in popup

4. **Annotations**:
   - Select annotation tool
   - Click to place annotation
   - Enter text, font size, and color
   - Drag annotations to reposition

5. **AI Analysis**:
   - Click AI button
   - View results in side panel
   - Copy results to clipboard

6. **3D Reconstruction**:
   - Click 3D button
   - Select reconstruction type
   - Click "Apply 3D"

### Worklist
1. **Viewing Patients**:
   - Green highlight on hover
   - Click rows to select
   - Use filters for search

2. **Clinical Information**:
   - Click "Clinical" button
   - Enter information in modal
   - Save to patient record

3. **Reports**:
   - Radiologists click "Report" to create/edit
   - Facilities can print finalized reports

## User Roles

### Administrator
- Full system access
- Manage all facilities
- View all notifications
- Create/edit all reports

### Radiologist
- Access all patient studies
- Create and finalize reports
- Receive new study notifications
- Access all facilities

### Facility Staff
- View only their facility's patients
- Print finalized reports
- Add clinical information
- Cannot create reports

## Architecture

### Backend
- Django 5.0 with Django REST Framework
- PostgreSQL database (configurable)
- Pydicom for DICOM file handling
- ReportLab for PDF generation

### Frontend
- Vanilla JavaScript for high performance
- HTML5 Canvas for image rendering
- CSS3 with modern dark theme
- Font Awesome icons

### Models
- `Facility`: Healthcare facility management
- `DicomStudy`: Study metadata
- `DicomSeries`: Series organization
- `DicomImage`: Individual image data
- `Measurement`: Stored measurements with HU support
- `Annotation`: Text annotations
- `Report`: Radiology reports
- `WorklistEntry`: Patient scheduling
- `AIAnalysis`: AI findings storage
- `Notification`: System notifications

## Configuration

### Settings
Edit `noctisview/settings.py` for:
- Database configuration
- Media file storage
- DICOM storage paths
- User authentication

### DICOM Storage
- Files stored in `MEDIA_ROOT/dicom_files/`
- Organized by study/series structure
- Automatic metadata extraction

## Security

- CSRF protection enabled
- User authentication required
- Role-based access control
- Facility-level data isolation

## Performance

- Lazy loading of DICOM images
- Client-side caching
- Optimized canvas rendering
- Asynchronous file uploads

## Browser Support

- Chrome 90+ (recommended)
- Firefox 88+
- Safari 14+
- Edge 90+

## License

This project is proprietary software. All rights reserved.

## Support

For support and documentation, contact the development team.