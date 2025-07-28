# NoctisView DICOM Viewer API Documentation

## Overview

NoctisView is an advanced Django-based DICOM medical image viewer with AI-powered analysis, anonymization capabilities, and batch processing features.

## Table of Contents

1. [Authentication](#authentication)
2. [Core Endpoints](#core-endpoints)
3. [AI Analysis Endpoints](#ai-analysis-endpoints)
4. [Anonymization Endpoints](#anonymization-endpoints)
5. [Export Endpoints](#export-endpoints)
6. [Batch Processing](#batch-processing)
7. [Error Handling](#error-handling)

## Authentication

All API endpoints require authentication except for the upload endpoint. Use Django's session authentication or token-based authentication.

```bash
# Login
POST /api/auth/login/
Content-Type: application/json
{
    "username": "your_username",
    "password": "your_password"
}
```

## Core Endpoints

### Upload DICOM Files

Upload one or more DICOM files to create a new study.

```bash
POST /viewer/api/upload/
Content-Type: multipart/form-data

Form Data:
- files: DICOM file(s) to upload
```

**Response:**
```json
{
    "success": true,
    "study_id": 123,
    "uploaded_files": [
        {
            "filename": "image1.dcm",
            "series_id": 456,
            "image_id": 789
        }
    ]
}
```

### Get Studies

Retrieve a list of all DICOM studies.

```bash
GET /viewer/api/studies/
```

**Response:**
```json
[
    {
        "id": 123,
        "study_instance_uid": "1.2.3.4.5",
        "patient_name": "John Doe",
        "patient_id": "12345",
        "study_date": "2024-01-15",
        "modality": "CT",
        "series_count": 3,
        "total_images": 150
    }
]
```

### Get Study Images

Get all images for a specific study.

```bash
GET /viewer/api/studies/{study_id}/images/
```

**Response:**
```json
{
    "study": {
        "id": 123,
        "patient_name": "John Doe",
        "study_date": "2024-01-15"
    },
    "images": [
        {
            "id": 789,
            "instance_number": 1,
            "series_number": 1,
            "series_description": "Chest CT",
            "rows": 512,
            "columns": 512,
            "window_width": 400,
            "window_center": 40
        }
    ]
}
```

### Get Image Data

Retrieve processed image data for display.

```bash
GET /viewer/api/images/{image_id}/data/
```

**Response:**
```json
{
    "image_data": "data:image/png;base64,iVBORw0KGgoAAAANS...",
    "metadata": {
        "window_width": 400,
        "window_center": 40,
        "pixel_spacing": [0.5, 0.5]
    }
}
```

### Save Measurement

Save a measurement on an image.

```bash
POST /viewer/api/measurements/save/
Content-Type: application/json

{
    "image_id": 789,
    "measurement_type": "line",
    "coordinates": [[100, 100], [200, 200]],
    "value": 141.42,
    "unit": "px",
    "notes": "Lesion measurement"
}
```

### Save Annotation

Add an annotation to an image.

```bash
POST /viewer/api/annotations/save/
Content-Type: application/json

{
    "image_id": 789,
    "x": 150,
    "y": 150,
    "text": "Suspicious area"
}
```

## AI Analysis Endpoints

### Analyze Image

Perform AI analysis on a DICOM image.

```bash
POST /viewer/api/images/{image_id}/analyze/
Content-Type: application/json

{
    "analysis_type": "anomaly_detection"
}
```

**Analysis Types:**
- `anomaly_detection`: Detect potential anomalies
- `enhancement`: Apply image enhancement
- `roi_measurement`: Measure region of interest

**Response (Anomaly Detection):**
```json
{
    "success": true,
    "results": {
        "anomalies_detected": true,
        "anomaly_regions": [
            {
                "id": 0,
                "bbox": [100, 100, 50, 50],
                "confidence": 0.85,
                "mean_intensity": 150.5,
                "texture_score": 0.72
            }
        ],
        "confidence": 0.85
    }
}
```

**Response (Enhancement):**
```json
{
    "success": true,
    "results": {
        "enhanced_image": "data:image/png;base64,iVBORw0KGgoAAAANS...",
        "enhancement_type": "auto"
    }
}
```

### Predict Image

Make AI predictions on DICOM image (requires AI analysis to be enabled).

```bash
POST /viewer/api/images/{image_id}/predict/
Content-Type: application/json

{
    "model_path": "/path/to/model" 
}
```

**Response:**
```json
{
    "success": true,
    "prediction": {
        "prediction": 1,
        "confidence": 0.92,
        "probabilities": [0.08, 0.92]
    }
}
```

## Anonymization Endpoints

### Anonymize Study

Anonymize all DICOM files in a study.

```bash
POST /viewer/api/studies/{study_id}/anonymize/
Content-Type: application/json

{
    "keep_dates": true,
    "keep_uid_structure": true,
    "use_secure": false
}
```

**Response:** ZIP file containing anonymized DICOM files

### Batch Anonymization

Anonymize multiple uploaded DICOM files.

```bash
POST /viewer/api/anonymize/batch/
Content-Type: multipart/form-data

Form Data:
- files: Multiple DICOM files
- keep_dates: true/false
- keep_uid_structure: true/false
```

**Response:** ZIP file containing anonymized DICOM files

## Export Endpoints

### Export Images

Export processed images in various formats.

```bash
POST /viewer/api/export/images/
Content-Type: application/json

{
    "image_ids": [789, 790, 791],
    "format": "png",
    "include_metadata": true
}
```

**Supported Formats:**
- `png`: PNG image format
- `jpeg`: JPEG image format  
- `npy`: NumPy array format

**Response:** ZIP file containing exported images and metadata

## Batch Processing

The batch processing features are available through the `DicomBatchProcessor` class:

```python
from viewer.batch_processor import DicomBatchProcessor, DicomMetadataExtractor

# Process directory of DICOM files
processor = DicomBatchProcessor(num_workers=4)
results = processor.process_directory(
    directory_path="/path/to/dicom/files",
    process_func=anonymize_function,
    output_dir="/path/to/output"
)

# Extract metadata
extractor = DicomMetadataExtractor()
df = extractor.extract_from_directory(
    directory="/path/to/dicom/files",
    output_csv="metadata.csv"
)
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error Response Format:
```json
{
    "error": "Error message describing what went wrong"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour
- File uploads: 50 files/hour

## WebSocket Support

Real-time updates for long-running operations:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/processing/');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.progress);
};
```

## Examples

### Complete Example: Upload, Analyze, and Export

```python
import requests

# 1. Upload DICOM file
files = {'files': open('scan.dcm', 'rb')}
response = requests.post('http://localhost:8000/viewer/api/upload/', files=files)
data = response.json()
image_id = data['uploaded_files'][0]['image_id']

# 2. Analyze for anomalies
analysis = requests.post(
    f'http://localhost:8000/viewer/api/images/{image_id}/analyze/',
    json={'analysis_type': 'anomaly_detection'}
)
results = analysis.json()

# 3. Export as PNG
export = requests.post(
    'http://localhost:8000/viewer/api/export/images/',
    json={
        'image_ids': [image_id],
        'format': 'png',
        'include_metadata': True
    }
)

# Save exported file
with open('export.zip', 'wb') as f:
    f.write(export.content)
```

## Performance Considerations

1. **Large Files**: Files over 100MB may take longer to process
2. **Batch Operations**: Use batch endpoints for multiple files
3. **Caching**: Processed images are cached for 24 hours
4. **Parallel Processing**: Batch processor uses multiple CPU cores

## Security

1. All patient data is encrypted at rest
2. HTTPS is required in production
3. Anonymization removes all PHI
4. Audit logs track all access

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourorg/noctisview/issues
- Email: support@noctisview.example.com
- Documentation: https://docs.noctisview.example.com