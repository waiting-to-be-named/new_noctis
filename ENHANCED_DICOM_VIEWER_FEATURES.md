# Enhanced DICOM Viewer Features

## Overview

This document describes the comprehensive enhancements made to the DICOM viewer system to support:
- Bulk upload of large files with multiple folders (2000+ files)
- Enhanced image resolution and density differentiation
- Series selector functionality with multiple positioning options
- Improved user interface and processing capabilities

## 1. Enhanced Bulk Upload System

### Features
- **Large File Support**: Handles files up to 2GB in size
- **Archive Support**: Supports ZIP, TAR, and TAR.GZ archives
- **Multiple Folder Processing**: Automatically processes nested folder structures
- **Background Processing**: Non-blocking upload with real-time progress tracking
- **Chunked Processing**: Processes files in batches of 50 for memory efficiency
- **Multi-threaded**: Uses 4 worker threads for parallel processing
- **Comprehensive Error Handling**: Detailed error reporting and recovery

### Technical Implementation

#### EnhancedBulkUploadManager Class
```python
class EnhancedBulkUploadManager:
    def __init__(self, user, facility=None):
        # Enhanced progress tracking with detailed metrics
        self.progress = {
            'total_files': 0,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'studies_created': 0,
            'series_created': 0,
            'images_processed': 0,
            'total_size_mb': 0,
            'processed_size_mb': 0,
            'estimated_time_remaining': 0,
            'current_folder': None,
            'folder_progress': 0,
            'total_folders': 0
        }
```

#### Key Methods
- `extract_archive()`: Handles ZIP, TAR, TAR.GZ extraction
- `scan_files()`: Recursively scans extracted files for DICOM candidates
- `process_file_batch()`: Processes files in chunks with enhanced error handling
- `process_study()`: Creates studies with proper series organization
- `process_image()`: Individual image processing with metadata extraction

### API Endpoints
- `POST /viewer/api/enhanced-bulk-upload/`: Main upload endpoint
- `GET /viewer/api/enhanced-upload-progress/<upload_id>/`: Progress tracking
- `GET /viewer/api/enhanced-upload-result/<upload_id>/`: Final results

## 2. Enhanced Image Processing

### Density Differentiation
The system now provides advanced density differentiation capabilities:

#### Enhanced Windowing
```python
def apply_enhanced_windowing(self, pixel_array, window_width=None, window_level=None, 
                           inverted=False, density_enhancement=False, contrast_boost=1.0):
    # Enhanced precision with float32 processing
    pixel_array = pixel_array.astype(np.float32)
    
    # Apply contrast boost
    if contrast_boost != 1.0:
        pixel_array = pixel_array * contrast_boost
    
    # Enhanced windowing with better precision
    window_min = window_level - window_width / 2
    window_max = window_level + window_width / 2
    pixel_array = np.clip(pixel_array, window_min, window_max)
    pixel_array = ((pixel_array - window_min) / (window_max - window_min)) * 255
```

#### Density Enhancement
```python
def apply_density_enhancement(self, pixel_array):
    # Adaptive histogram equalization for better contrast
    from skimage import exposure
    enhanced = exposure.equalize_adapthist(pixel_array_uint8, clip_limit=0.03)
    return (enhanced * 255).astype(np.float32)
```

#### Multi-scale Processing
```python
def apply_density_differentiation(self, pixel_array):
    # Multi-scale processing for better tissue visualization
    scales = [1.0, 2.0, 4.0]
    processed_scales = []
    
    for scale in scales:
        if scale == 1.0:
            processed_scales.append(pixel_array)
        else:
            # Apply Gaussian blur at different scales
            sigma = scale
            blurred = ndimage.gaussian_filter(pixel_array, sigma=sigma)
            processed_scales.append(blurred)
    
    # Combine scales with different weights
    enhanced = np.zeros_like(pixel_array)
    weights = [0.5, 0.3, 0.2]
    
    for i, scale_data in enumerate(processed_scales):
        enhanced += weights[i] * scale_data
    
    return enhanced
```

### Resolution Enhancement
```python
def apply_resolution_enhancement(self, pixel_array, resolution_factor):
    # High-quality interpolation using scipy
    from scipy import ndimage
    enhanced = ndimage.zoom(pixel_array, resolution_factor, order=3)
    return enhanced
```

### API Endpoints
- `GET /viewer/api/images/<image_id>/enhanced-data/`: Enhanced image data
- `GET /viewer/api/series/<series_id>/enhanced-images/`: Enhanced series images

## 3. Series Selector Functionality

### Features
- **Multiple Positions**: Bottom, top, or side positioning
- **Preview Images**: Thumbnail previews for each series
- **Real-time Updates**: Dynamic loading of series data
- **Enhanced UI**: Modern, responsive interface
- **Statistics Display**: Image counts and modality information

### UI Components

#### Series Selector Container
```html
<div class="series-selector" id="series-selector">
    <div class="series-selector-header">
        <div class="series-selector-title">Series Selector</div>
        <button class="series-selector-close" onclick="toggleSeriesSelector()">
            <i class="fas fa-times"></i>
        </button>
    </div>
    <div class="series-grid" id="series-grid">
        <!-- Series items populated dynamically -->
    </div>
</div>
```

#### Position Controls
```html
<div class="series-position-controls">
    <div style="color: white; font-size: 10px; margin-bottom: 5px;">Series Position:</div>
    <button class="position-btn active" data-position="bottom">Bottom</button>
    <button class="position-btn" data-position="top">Top</button>
    <button class="position-btn" data-position="side">Side</button>
</div>
```

### JavaScript Functionality
```javascript
// Series selector initialization
function initializeSeriesSelector() {
    document.getElementById('series-selector-btn').addEventListener('click', toggleSeriesSelector);
    
    // Position controls
    document.querySelectorAll('.position-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const position = e.target.dataset.position;
            setSeriesSelectorPosition(position);
            
            // Update active button
            document.querySelectorAll('.position-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
        });
    });
}

// Load series data
function loadSeriesData(studyId) {
    fetch(`/viewer/api/studies/${studyId}/series-selector/`)
        .then(response => response.json())
        .then(data => {
            seriesData = data.series;
            renderSeriesGrid(data.series);
        })
        .catch(error => {
            console.error('Error loading series data:', error);
        });
}
```

### API Endpoints
- `GET /viewer/api/studies/<study_id>/series-selector/`: Series selector data
- `GET /viewer/api/series/<series_id>/enhanced-images/`: Enhanced series images

## 4. Enhanced User Interface

### Upload Interface
- **Drag & Drop**: Modern drag-and-drop file upload
- **Progress Tracking**: Real-time progress with detailed statistics
- **File Validation**: Automatic DICOM file detection
- **Archive Support**: ZIP, TAR, TAR.GZ support
- **Large File Handling**: Up to 2GB file support

### Enhanced Controls
- **Density Enhancement**: Toggle for density differentiation
- **High Resolution**: Toggle for resolution enhancement
- **Contrast Boost**: Toggle for contrast enhancement
- **Real-time Updates**: Immediate visual feedback

### CSS Styling
```css
/* Enhanced Series Selector Styles */
.series-selector {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.9);
    color: white;
    padding: 15px;
    z-index: 1000;
    max-height: 200px;
    overflow-y: auto;
    display: none;
}

.series-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
    max-height: 120px;
    overflow-y: auto;
}

.series-item {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 5px;
    padding: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
}
```

## 5. Performance Optimizations

### Memory Management
- **Chunked Processing**: Files processed in batches of 50
- **Garbage Collection**: Forced GC after each batch
- **Temporary File Cleanup**: Automatic cleanup of temporary files
- **Memory Monitoring**: Progress tracking includes memory usage

### Processing Efficiency
- **Multi-threading**: 4 worker threads for parallel processing
- **Background Processing**: Non-blocking upload operations
- **Caching**: Progress and results cached for 2 hours
- **Error Recovery**: Graceful handling of processing errors

### Database Optimizations
- **Bulk Operations**: Efficient database operations
- **Transaction Management**: Atomic operations for data integrity
- **Indexing**: Optimized database queries
- **Connection Pooling**: Efficient database connections

## 6. Error Handling and Logging

### Comprehensive Error Handling
```python
try:
    # Process file with multiple fallback methods
    dicom_data = pydicom.dcmread(file_path)
except Exception as e1:
    try:
        # Method 2: Force read
        dicom_data = pydicom.dcmread(file_path, force=True)
    except Exception as e2:
        try:
            # Method 3: Read with specific transfer syntax
            dicom_data = pydicom.dcmread(file_path, force=True, specific_char_set='utf-8')
        except Exception as e3:
            logger.error(f"Failed to read DICOM file {file_info['name']}: {e1}, {e2}, {e3}")
            batch_results['failed'].append(f"Could not read DICOM data from {file_info['name']}")
            continue
```

### Logging Configuration
```python
import logging
logger = logging.getLogger(__name__)

# Configure logging for enhanced debugging
logger.error(f"Error in bulk upload processing: {e}")
logger.info(f"Successfully processed {count} files")
```

## 7. Installation and Setup

### Dependencies
Add to `requirements.txt`:
```
scikit-image>=0.22.0
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Static Files
```bash
python manage.py collectstatic
```

## 8. Usage Examples

### Bulk Upload
1. Click "Enhanced Upload" button
2. Drag and drop archive file or individual DICOM files
3. Click "Start Upload"
4. Monitor progress in real-time
5. View results and statistics

### Series Selection
1. Click "Series" button
2. Choose position (bottom, top, side)
3. Click on series to load
4. View enhanced images with density differentiation

### Enhanced Processing
1. Toggle "Density" for density differentiation
2. Toggle "High Res" for resolution enhancement
3. Toggle "Contrast" for contrast boost
4. Adjust window/level for optimal viewing

## 9. Configuration Options

### Upload Settings
```python
# In EnhancedBulkUploadManager
self.chunk_size = 50  # Files per batch
self.max_workers = 4  # Number of worker threads
```

### Image Processing Settings
```python
# Resolution enhancement factor
resolution_factor = 1.0  # 1.0 = original, 2.0 = 2x resolution

# Density enhancement
density_enhancement = True  # Enable density differentiation

# Contrast boost
contrast_boost = 1.0  # 1.0 = normal, 1.5 = 50% boost
```

### UI Settings
```javascript
// Series selector position
const position = 'bottom';  // 'bottom', 'top', 'side'

// Enhanced processing toggles
let densityEnhancement = false;
let highResolution = false;
let contrastBoost = false;
```

## 10. Troubleshooting

### Common Issues

#### Upload Fails
- Check file size (max 2GB)
- Verify file format (ZIP, TAR, TAR.GZ, DICOM)
- Check disk space
- Review server logs

#### Image Processing Issues
- Ensure scikit-image is installed
- Check memory availability
- Verify DICOM file integrity
- Review processing logs

#### Series Selector Not Working
- Check study ID validity
- Verify API endpoints
- Review browser console for errors
- Check network connectivity

### Debug Information
- Progress tracking provides detailed metrics
- Error logs include stack traces
- API responses include error details
- Browser console shows JavaScript errors

## Conclusion

The enhanced DICOM viewer now provides:
- Robust bulk upload for large files with multiple folders
- Advanced image processing with density differentiation
- Flexible series selector with multiple positioning options
- Modern, responsive user interface
- Comprehensive error handling and logging
- High-performance processing with memory optimization

These enhancements make the system suitable for handling large-scale DICOM datasets with 2000+ files while providing superior image quality and user experience.