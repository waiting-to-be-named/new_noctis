# Bulk Upload System for Large DICOM Folders

## Overview

The bulk upload system has been enhanced to handle large folders containing over 2000 DICOM images efficiently. This system provides:

- **Chunked Processing**: Files are processed in batches to manage memory usage
- **Background Processing**: Large uploads (>100 files) are processed asynchronously
- **Progress Tracking**: Real-time progress updates for background uploads
- **Memory Optimization**: Automatic garbage collection and memory management
- **Error Recovery**: Robust error handling with detailed error reporting
- **Upload Queue Management**: Support for multiple concurrent uploads

## Key Features

### 1. Automatic Upload Type Selection

The system automatically chooses the appropriate upload method based on file count:

- **Small Uploads** (≤100 files): Immediate processing with instant response
- **Large Uploads** (>100 files): Background processing with progress tracking

### 2. Chunked File Processing

Files are processed in chunks of 50 files to:
- Prevent memory overflow
- Maintain system responsiveness
- Allow for garbage collection between chunks

### 3. Background Processing

Large uploads are processed in background threads to:
- Avoid browser timeout
- Allow users to continue using the system
- Provide real-time progress updates

### 4. Progress Tracking

Real-time progress monitoring includes:
- Total files to process
- Currently processed files
- Successful vs failed files
- Current study being processed
- Detailed error messages

## API Endpoints

### 1. Bulk Upload Endpoint

**URL**: `/viewer/api/bulk-upload/`
**Method**: `POST`
**Content-Type**: `multipart/form-data`

**Parameters**:
- `files`: Array of DICOM files

**Response for Small Uploads**:
```json
{
    "upload_id": "uuid",
    "message": "Successfully processed X files from Y study(ies)",
    "successful_files": ["file1.dcm", "file2.dcm"],
    "failed_files": [],
    "total_files": 50,
    "total_studies": 1,
    "status": "completed"
}
```

**Response for Large Uploads**:
```json
{
    "upload_id": "uuid",
    "message": "Started processing X files in background",
    "status": "processing"
}
```

### 2. Progress Tracking Endpoint

**URL**: `/viewer/api/upload-progress/{upload_id}/`
**Method**: `GET`

**Response**:
```json
{
    "total_files": 2000,
    "processed_files": 1500,
    "successful_files": 1480,
    "failed_files": 20,
    "current_study": "Processing study 1.2.3.4.5.123",
    "status": "processing",
    "errors": [],
    "warnings": []
}
```

### 3. Upload Result Endpoint

**URL**: `/viewer/api/upload-result/{upload_id}/`
**Method**: `GET`

**Response**:
```json
{
    "upload_id": "uuid",
    "successful_files": ["file1.dcm", "file2.dcm"],
    "failed_files": ["corrupted.dcm"],
    "studies": [study_objects],
    "total_files": 2000,
    "total_studies": 5
}
```

## Frontend Integration

### Automatic Upload Type Detection

The frontend automatically detects upload size and uses appropriate endpoints:

```javascript
// Choose upload endpoint based on file count
const uploadUrl = files.length > 100 ? '/viewer/api/bulk-upload/' : '/viewer/api/upload/';
```

### Progress Monitoring

For large uploads, the frontend monitors progress:

```javascript
function monitorUploadProgress(uploadId) {
    const progressInterval = setInterval(() => {
        fetch(`/viewer/api/upload-progress/${uploadId}/`)
            .then(response => response.json())
            .then(progress => {
                if (progress.status === 'completed') {
                    // Get final result
                    fetch(`/viewer/api/upload-result/${uploadId}/`)
                        .then(response => response.json())
                        .then(result => {
                            // Handle completion
                        });
                    clearInterval(progressInterval);
                } else {
                    // Update progress display
                    updateProgressDisplay(progress);
                }
            });
    }, 2000); // Check every 2 seconds
}
```

## System Architecture

### BulkUploadManager Class

The core class that manages bulk uploads:

```python
class BulkUploadManager:
    def __init__(self, user, facility=None):
        self.user = user
        self.facility = facility
        self.upload_id = str(uuid.uuid4())
        self.progress = {...}
        self.lock = threading.Lock()
    
    def process_file_batch(self, files_batch):
        """Process a batch of files efficiently"""
        
    def process_study(self, study_uid, study_data):
        """Process a complete study with all its files"""
        
    def process_upload(self, files):
        """Main upload processing with chunked processing"""
```

### Key Methods

1. **`process_file_batch()`**: Processes files in chunks with memory management
2. **`process_study()`**: Creates studies, series, and images with database transactions
3. **`process_upload()`**: Orchestrates the entire upload process
4. **`update_progress()`**: Thread-safe progress updates with caching

## Memory Management

### Chunked Processing

Files are processed in chunks of 50 to prevent memory issues:

```python
chunk_size = 50  # Process 50 files at a time
for i in range(0, len(files), chunk_size):
    chunk = files[i:i + chunk_size]
    chunk_results = self.process_file_batch(chunk)
    # Force garbage collection to free memory
    gc.collect()
```

### Database Transactions

Each study is processed within a database transaction:

```python
with transaction.atomic():
    study, created = DicomStudy.objects.get_or_create(...)
    # Process all files for this study
```

## Error Handling

### Comprehensive Error Recovery

The system handles various error scenarios:

1. **File Validation Errors**: Invalid DICOM files are skipped
2. **Memory Errors**: Automatic garbage collection and chunked processing
3. **Database Errors**: Transaction rollback and error reporting
4. **Network Errors**: Progress tracking and resume capability

### Error Reporting

Detailed error messages are provided:

```python
batch_results['failed'].append(f"Could not read DICOM data from {file.name}")
```

## Performance Optimizations

### 1. Chunked Processing
- Process files in batches of 50
- Automatic garbage collection between chunks
- Memory usage monitoring

### 2. Background Processing
- Large uploads processed in background threads
- Non-blocking user interface
- Real-time progress updates

### 3. Database Optimization
- Bulk operations where possible
- Transaction management
- Efficient query patterns

### 4. Caching
- Progress information cached for frontend polling
- Upload results cached for retrieval
- Memory-efficient data structures

## Usage Examples

### Small Upload (≤100 files)

```javascript
// Files are processed immediately
const files = document.getElementById('file-input').files;
uploadFiles(Array.from(files));

function uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    fetch('/viewer/api/bulk-upload/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'completed') {
            console.log(`Uploaded ${result.successful_files.length} files`);
        }
    });
}
```

### Large Upload (>100 files)

```javascript
// Files are processed in background with progress tracking
const files = document.getElementById('file-input').files;
uploadFiles(Array.from(files));

function uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    fetch('/viewer/api/bulk-upload/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'processing') {
            monitorUploadProgress(result.upload_id);
        }
    });
}

function monitorUploadProgress(uploadId) {
    const interval = setInterval(() => {
        fetch(`/viewer/api/upload-progress/${uploadId}/`)
            .then(response => response.json())
            .then(progress => {
                updateProgressBar(progress);
                if (progress.status === 'completed') {
                    clearInterval(interval);
                    getUploadResult(uploadId);
                }
            });
    }, 2000);
}
```

## Testing

### Test Script

A comprehensive test script is provided (`test_bulk_upload.py`) that tests:

1. **Small Uploads**: ≤100 files with immediate processing
2. **Large Uploads**: >100 files with background processing
3. **Very Large Uploads**: 500+ files simulating 2000+ image scenarios

### Running Tests

```bash
python test_bulk_upload.py
```

## Configuration

### Django Settings

Ensure the following settings are configured:

```python
# Cache configuration for progress tracking
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
```

### Performance Tuning

Adjust these parameters based on your system:

```python
# In BulkUploadManager
chunk_size = 50  # Adjust based on available memory
progress_cache_timeout = 3600  # 1 hour cache timeout
max_upload_size = 100 * 1024 * 1024  # 100MB per file
```

## Monitoring and Logging

### Progress Monitoring

Monitor upload progress through:

1. **Frontend Progress Bars**: Real-time visual feedback
2. **Backend Logs**: Detailed processing logs
3. **Database Queries**: Monitor study and image creation

### Error Logging

Errors are logged with detailed information:

```python
print(f"Error processing file {file.name}: {e}")
create_system_error_notification(f"Bulk DICOM folder upload error: {str(e)}", request.user)
```

## Future Enhancements

### Planned Improvements

1. **Resume Capability**: Resume interrupted uploads
2. **Parallel Processing**: Multiple uploads simultaneously
3. **Compression Support**: Handle compressed DICOM files
4. **Validation Pipeline**: Pre-upload validation
5. **Storage Optimization**: Efficient file storage strategies

### Scalability Considerations

1. **Database Optimization**: Indexing and query optimization
2. **Storage Scaling**: Distributed file storage
3. **Load Balancing**: Multiple server support
4. **Caching Strategy**: Redis or Memcached integration

## Troubleshooting

### Common Issues

1. **Memory Errors**: Reduce chunk size or increase server memory
2. **Timeout Errors**: Increase timeout settings for large uploads
3. **Database Errors**: Check database connection and transaction settings
4. **File Permission Errors**: Ensure proper file system permissions

### Debug Information

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Conclusion

The bulk upload system provides a robust, scalable solution for handling large DICOM folders with over 2000 images. The system automatically adapts to upload size, provides real-time feedback, and ensures reliable processing even for very large datasets.

The implementation includes comprehensive error handling, memory management, and progress tracking to ensure a smooth user experience regardless of upload size.