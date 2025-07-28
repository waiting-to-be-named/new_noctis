# Enhanced DICOM Medical Viewer

A comprehensive medical imaging platform with advanced features for DICOM viewing, analysis, and reporting.

## 🚀 Features

### Core DICOM Viewer
- **Multi-planar DICOM viewing** with window/level adjustment
- **Advanced measurements** with unit selection (mm/cm)
- **Hounsfield Unit analysis** using ellipse regions
- **Draggable annotations** with customizable colors and sizes
- **Crosshair and zoom tools** for precise navigation
- **Image inversion and preset windowing** (Lung, Bone, Soft, Brain)

### Worklist Management
- **Patient worklist** with grey background and green highlights
- **Facility-based access control** - users only see their facility's patients
- **Search and filter** functionality
- **Clinical information management** for each patient
- **Real-time notifications** for new uploads

### AI Analysis Features
- **Lung nodule detection**
- **Brain lesion detection**
- **Bone fracture detection**
- **Tumor segmentation**
- **Interactive chat interface** for AI analysis results
- **Copy-paste functionality** for analysis results

### 3D Reconstruction
- **MPR (Multi-Planar Reconstruction)**
- **3D Bone Reconstruction**
- **Angio Reconstruction**
- **Virtual Surgery Planning**
- **Export capabilities** for 3D models

### Report Generation
- **Radiology report writing** with hospital letterhead
- **Clinical information integration**
- **Print functionality** with professional formatting
- **Draft, preliminary, and final** report statuses
- **Auto-save functionality**

### User Management
- **Role-based access control** (Radiologist, Admin, Regular User)
- **Facility-based patient filtering**
- **Notification system** for radiologists and admins
- **Secure authentication**

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dicom-viewer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
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

## 📁 Project Structure

```
dicom-viewer/
├── manage.py
├── requirements.txt
├── noctisview/          # Django project settings
├── viewer/              # Main app
│   ├── models.py        # Database models
│   ├── views.py         # API views
│   ├── urls.py          # URL routing
│   └── serializers.py   # API serializers
├── static/
│   ├── css/
│   │   └── dicom_viewer.css
│   └── js/
│       └── dicom_viewer.js
└── templates/
    └── dicom_viewer/
        ├── launcher.html
        ├── viewer.html
        ├── worklist.html
        └── report.html
```

## 🎯 Usage

### Launcher Page
Access the main launcher at `/` to choose between:
- **Patient Worklist** - View and manage patient studies
- **DICOM Viewer** - Advanced image viewing and analysis
- **Report Writing** - Create radiology reports (admin/radiologist only)

### Worklist Features
- **Grey background** with **green highlights** for patient rows
- **Facility filtering** - users only see their facility's patients
- **Search functionality** by patient name, ID, or study description
- **Clinical information** management for each patient
- **View button** launches the DICOM viewer with selected study
- **Report button** for radiologists to write reports

### DICOM Viewer Features
- **Measurement tools** with unit selection (mm/cm)
- **Ellipse tool** for Hounsfield Unit analysis
- **Draggable annotations** with color and size customization
- **AI analysis** with interactive chat window
- **3D reconstruction** options with export capabilities
- **Window/level adjustment** with presets
- **Zoom and pan** functionality

### Report Writing
- **Hospital letterhead** integration
- **Clinical information** display
- **Professional formatting** for printing
- **Auto-save** functionality
- **Multiple status** options (draft, preliminary, final)

## 🔧 Configuration

### Database Models

#### Facility
- Hospital/facility information
- Letterhead logo support
- Contact information

#### DicomStudy
- Patient and study information
- Facility association
- Processing status

#### ClinicalInformation
- Chief complaint
- Clinical history
- Physical examination
- Clinical diagnosis
- Referring physician

#### Report
- Radiology report content
- Status management
- Professional formatting

#### Notification
- Real-time notifications
- User-specific alerts
- Study association

### API Endpoints

#### DICOM Management
- `POST /api/upload/` - Upload DICOM files
- `GET /api/studies/` - Get patient studies
- `GET /api/studies/{id}/images/` - Get study images
- `GET /api/images/{id}/` - Get processed image data

#### Measurements & Annotations
- `POST /api/measurements/` - Save measurements
- `POST /api/annotations/` - Save annotations
- `POST /api/measure-hu/` - Measure Hounsfield units
- `GET /api/images/{id}/measurements/` - Get measurements
- `GET /api/images/{id}/annotations/` - Get annotations

#### Clinical Information
- `GET /api/studies/{id}/clinical-info/` - Get clinical info
- `POST /api/studies/{id}/clinical-info/save/` - Save clinical info

#### Reports
- `GET /api/studies/{id}/report/` - Get report
- `POST /api/studies/{id}/report/save/` - Save report

#### Notifications
- `GET /api/notifications/` - Get user notifications
- `POST /api/notifications/{id}/read/` - Mark notification as read

#### AI & 3D Features
- `GET /api/ai-analysis-types/` - Get AI analysis options
- `GET /api/3d-reconstruction-types/` - Get 3D reconstruction options

## 🎨 UI Features

### Color Scheme
- **Grey background** (#f5f5f5) for worklist
- **Green highlights** (#e8f5e8) for patient rows
- **Professional dark theme** for viewer
- **Consistent blue accent** (#007acc) for primary actions

### Responsive Design
- **Mobile-friendly** layout
- **Touch-optimized** controls
- **Adaptive panels** for different screen sizes

### Interactive Elements
- **Hover effects** for better UX
- **Smooth transitions** and animations
- **Loading states** for better feedback

## 🔒 Security Features

### Access Control
- **Role-based permissions** (Radiologist, Admin, User)
- **Facility-based data isolation**
- **Authentication required** for sensitive operations

### Data Protection
- **CSRF protection** on all forms
- **Input validation** and sanitization
- **Secure file uploads** with type checking

## 🚀 Deployment

### Production Setup
1. **Configure database** (PostgreSQL recommended)
2. **Set up static files** serving
3. **Configure media storage** for DICOM files
4. **Set environment variables** for security
5. **Configure web server** (nginx + gunicorn)

### Environment Variables
```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:pass@host:port/db
```

## 📊 Performance

### Optimizations
- **Image caching** for processed DICOM data
- **Lazy loading** for large datasets
- **Efficient database queries** with proper indexing
- **Compressed static assets**

### Scalability
- **Modular architecture** for easy scaling
- **API-first design** for frontend flexibility
- **Database optimization** for large datasets

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests** for new features
5. **Submit a pull request**

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- **Create an issue** on GitHub
- **Check the documentation** for common questions
- **Review the API documentation** for integration help

## 🔄 Version History

### v2.0.0 (Current)
- ✅ Enhanced measurement tools with unit selection
- ✅ Hounsfield Unit analysis with ellipse regions
- ✅ Draggable annotations with customization
- ✅ AI analysis features with chat interface
- ✅ 3D reconstruction capabilities
- ✅ Worklist with facility-based access
- ✅ Clinical information management
- ✅ Radiology report generation
- ✅ Real-time notifications
- ✅ Professional UI with responsive design

### v1.0.0
- ✅ Basic DICOM viewing
- ✅ Window/level adjustment
- ✅ Basic measurements
- ✅ Simple annotations

---

**Note**: This is a medical imaging application. Ensure compliance with local healthcare regulations and data protection laws when deploying in clinical environments.