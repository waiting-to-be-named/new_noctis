# Upload Error Handling Improvements

## Problem
The application was encountering "Unexpected token '<', "<!DOCTYPE "... is not valid JSON" errors when uploading DICOM files. This occurred because:

1. Django was returning HTML error pages instead of JSON responses when errors occurred
2. The JavaScript code was trying to parse HTML as JSON, causing the parsing error
3. CSRF token issues and server errors were returning HTML instead of proper JSON responses

## Solutions Implemented

### 1. Enhanced JavaScript Error Handling

**Files Modified:**
- `templates/worklist/worklist.html`
- `static/js/dicom_viewer.js`

**Improvements:**
- Added try-catch blocks around `JSON.parse()` calls
- Added detailed error logging to console for debugging
- Improved error messages to be more user-friendly
- Added fallback error handling when JSON parsing fails

**Example:**
```javascript
try {
    const response = JSON.parse(xhr.responseText);
    // Handle success
} catch (parseError) {
    console.error('Failed to parse JSON response:', parseError);
    console.error('Response text:', xhr.responseText);
    fileInfo.textContent = 'Upload failed: Invalid server response. Please try again.';
}
```

### 2. Django View Error Handling

**Files Modified:**
- `viewer/views.py`

**Improvements:**
- Wrapped upload functions in try-catch blocks
- Ensured all error responses return proper JSON
- Added detailed error logging
- Improved error messages for different failure scenarios

**Example:**
```python
try:
    # Upload processing logic
    return JsonResponse({
        'message': f'Uploaded {len(uploaded_files)} files successfully',
        'uploaded_files': uploaded_files,
        'study_id': study.id if study else None
    })
except Exception as e:
    print(f"Unexpected error in upload_dicom_files: {e}")
    return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
```

### 3. Custom Middleware for API Error Handling

**Files Created:**
- `noctisview/middleware.py`

**Improvements:**
- Created `APIErrorMiddleware` to catch exceptions for API endpoints
- Created `CSRFMiddleware` to handle CSRF token issues gracefully
- Ensured all API errors return JSON instead of HTML

**Example:**
```python
class APIErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': str(exception),
                'status': 'error'
            }, status=500)
        return None
```

### 4. Enhanced CSRF Token Handling

**Files Modified:**
- `templates/worklist/worklist.html`
- `static/js/dicom_viewer.js`

**Improvements:**
- Added `getCSRFToken()` function with better error handling
- Added warnings when CSRF token is missing
- Improved token validation

**Example:**
```javascript
function getCSRFToken() {
    const token = getCookie('csrftoken');
    if (!token) {
        console.warn('CSRF token not found. Upload may fail.');
        return '';
    }
    return token;
}
```

### 5. Django Settings Updates

**Files Modified:**
- `noctisview/settings.py`

**Improvements:**
- Added custom middleware to the MIDDLEWARE list
- Ensured proper error handling for API endpoints

## Testing

A test script (`test_upload_error_handling.py`) has been created to verify:
- Upload with no files
- Upload with invalid file types
- CSRF token handling
- API error middleware functionality

## Benefits

1. **Better User Experience**: Users now see meaningful error messages instead of cryptic JSON parsing errors
2. **Improved Debugging**: Detailed error logging helps identify issues
3. **Robust Error Handling**: The application gracefully handles various error scenarios
4. **Consistent API Responses**: All API endpoints now return proper JSON responses
5. **Better CSRF Handling**: Improved token validation and error messages

## Usage

The improvements are automatically applied when the application runs. No additional configuration is required. The error handling will:

1. Catch JSON parsing errors and display user-friendly messages
2. Log detailed error information to the browser console
3. Return proper JSON responses from the server
4. Handle CSRF token issues gracefully

## Future Improvements

1. Add retry logic for failed uploads
2. Implement progress indicators for large file uploads
3. Add file validation before upload
4. Implement upload queue management
5. Add server-side file size limits and validation