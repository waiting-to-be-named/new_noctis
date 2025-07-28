# NoctisView DICOM System

A comprehensive medical imaging viewer with advanced features including AI-powered analysis, 3D reconstruction, and multi-facility support.

## Features

### Core Functionality
- **DICOM File Support**: Load and view DICOM medical images
- **Advanced Measurements**: 
  - Line measurements with unit conversion (px, mm, cm)
  - Ellipse ROI for Hounsfield Unit analysis
- **Enhanced Annotations**: Draggable, resizable text annotations with customizable appearance
- **Window/Level Presets**: Optimized viewing for different tissue types (lung, bone, soft tissue, brain)

### Advanced Features
- **AI Analysis**: Click on image regions for automated analysis
- **3D Reconstruction**: 
  - MPR (Multi-Planar Reconstruction)
  - 3D Bone visualization
  - Angiography reconstruction
  - Virtual surgery planning
- **Multi-Facility Support**: Separate portals for different healthcare facilities
- **DICOM Worklist**: SCP server integration for remote image reception
- **Report Generation**: Full radiological reporting with facility letterheads
- **Real-time Notifications**: Instant alerts for new studies and completed reports

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd noctisview
```

2. Create a virtual environment:
```bash
python3 -m venv venv
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

## Usage

1. **Access the system**: Navigate to `http://localhost:8000/`
2. **Launch Viewer**: Click "Launch Viewer" from the home page
3. **Load DICOM Files**: 
   - Click "Load DICOM Files" to upload from your computer
   - Or select from the system dropdown for existing studies
4. **View Worklist**: Access the DICOM worklist to see patients from SCP server

### Measurement Tools
- Select measurement unit from the dropdown (px/mm/cm)
- Use the ruler tool for distance measurements
- Use the ellipse tool for ROI analysis and Hounsfield Units

### AI Analysis
1. Click the AI button in the toolbar
2. Click on any region of the image
3. View analysis results in the chat window

### 3D Reconstruction
1. Click the 3D button in the toolbar
2. Select reconstruction type:
   - MPR for multi-planar views
   - 3D Bone for skeletal visualization
   - Angiography for vascular studies
   - Virtual Surgery for surgical planning

### Report Writing (Radiologists/Admins)
1. Click "Write Report" in the viewer
2. Fill in findings, impression, and recommendations
3. Save as draft or sign and finalize

## User Roles

- **Admin**: Full system access, can view all facilities
- **Radiologist**: Can view all facilities and write reports
- **Facility User**: Can only view their facility's patients

## API Endpoints

- `/api/studies/` - List all studies
- `/api/studies/{id}/images/` - Get images for a study
- `/api/measurements/save/` - Save measurements
- `/api/annotations/save/` - Save annotations
- `/api/notifications/` - Get user notifications
- `/worklist/` - View DICOM worklist

## Configuration

### Database
Configure your database in `settings.py`. Default uses SQLite for development.

### DICOM SCP Server
Configure SCP server settings in admin panel under "Facilities".

## Development

### Project Structure
```
noctisview/
├── viewer/              # Main Django app
│   ├── models.py       # Data models
│   ├── views.py        # View controllers
│   ├── urls.py         # URL routing
│   └── admin.py        # Admin configuration
├── templates/          # HTML templates
├── static/            # CSS and JavaScript
└── manage.py          # Django management script
```

### Adding New Features
1. Update models in `viewer/models.py`
2. Create migrations: `python manage.py makemigrations`
3. Apply migrations: `python manage.py migrate`
4. Update views and templates as needed

## License

This project is licensed under the MIT License.

## Support

For issues and feature requests, please create an issue in the repository.