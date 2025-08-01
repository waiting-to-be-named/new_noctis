# Enhanced Access Control System

## Overview

The system now implements a comprehensive access control mechanism that ensures:

1. **Facilities can only see their own uploaded images**
2. **Radiologists and admins can see all uploaded images from all facilities**
3. **Enhanced notifications for new uploads**
4. **Proper permission checks throughout the system**

## Access Control Functions

### Core Functions

#### `get_user_study_queryset(user)`
Returns the appropriate study queryset based on user permissions:
- **Admins**: All studies from all facilities
- **Radiologists**: All studies from all facilities  
- **Facility users**: Only studies from their assigned facility
- **Others**: No studies

#### `can_access_study(user, study)`
Checks if a user can access a specific study:
- **Admins and Radiologists**: Can access any study
- **Facility users**: Can only access studies from their facility
- **Others**: Cannot access any studies

#### `notify_new_study_upload(study, uploaded_by_user)`
Creates comprehensive notifications for new study uploads:
- **Radiologists**: Notified about all new studies
- **Admins**: Notified about all new studies with uploader information
- **Facility staff**: Confirmation notifications for their own uploads

## User Types and Permissions

### 1. Administrators (`is_superuser=True`)
- **Access**: All studies from all facilities
- **Actions**: All administrative functions
- **Notifications**: Receive notifications for all new uploads

### 2. Radiologists (Group: 'Radiologists')
- **Access**: All studies from all facilities
- **Actions**: Create reports, add clinical info, perform measurements
- **Notifications**: Receive notifications for all new uploads

### 3. Facility Users (Group: 'Facilities' + assigned facility)
- **Access**: Only studies from their assigned facility
- **Actions**: Upload studies, view their own studies
- **Notifications**: Confirmation notifications for their uploads

### 4. Other Users
- **Access**: No studies
- **Actions**: Limited functionality
- **Notifications**: None

## Implementation Details

### Study Filtering

#### Main Viewer (`DicomViewerView`)
```python
# Uses the new access control system
context['studies'] = get_user_study_queryset(self.request.user)[:10]
```

#### API Endpoints
```python
# get_studies API
studies = get_user_study_queryset(request.user)[:20]

# get_study_images API
if not can_access_study(request.user, study):
    return Response({'error': 'Access denied'}, status=403)
```

### Worklist Access Control

#### Main Worklist (`WorklistView`)
- Facility users see only their facility's worklist entries
- Radiologists and admins see all worklist entries
- Proper filtering based on user permissions

#### Worklist Functions
- `view_study_from_worklist`: Access control before redirecting
- `add_clinical_info`: Permission checks for clinical info updates
- `create_report`: Only radiologists and admins can create reports

### Image Access Control

#### Image Operations
All image-related functions now include access control:
- `get_image_data`: Check study access before serving images
- `save_measurement`: Verify access before saving measurements
- `save_annotation`: Verify access before saving annotations
- `get_measurements`: Check access before retrieving measurements
- `get_annotations`: Check access before retrieving annotations
- `clear_measurements`: Verify access before clearing data

### Notification System

#### Enhanced Notifications
When a new study is uploaded:

1. **Radiologists** receive notifications with:
   - Study modality
   - Patient name
   - Study description

2. **Admins** receive notifications with:
   - Study modality
   - Patient name
   - Uploader information

3. **Facility staff** receive confirmation notifications:
   - Confirmation of successful upload
   - Study details
   - Ready for review status

### Chat System Access Control

#### Chat Permissions
- Users can only send messages to facilities they have access to
- Facility users can only message their own facility
- Radiologists and admins can message any facility

## Security Features

### 1. Study-Level Access Control
- Every study access is verified through `can_access_study()`
- No bypassing of permission checks
- Consistent access control across all endpoints

### 2. Image-Level Access Control
- All image operations verify study access
- Measurements and annotations are protected
- Clear error messages for unauthorized access

### 3. Worklist Access Control
- Worklist entries filtered by facility
- Proper permission checks for all worklist operations
- Secure study viewing from worklist

### 4. Notification Security
- Notifications only sent to authorized users
- No information leakage between facilities
- Proper recipient filtering

## Error Handling

### Access Denied Responses
All access control violations return consistent error responses:
```json
{
    "error": "Access denied. You do not have permission to access this study."
}
```

### HTTP Status Codes
- `403 Forbidden`: Access denied due to permissions
- `404 Not Found`: Resource not found (after access check)
- `200 OK`: Successful access

## Testing the System

### Facility User Testing
1. Login as facility user
2. Upload a study
3. Verify only own studies are visible
4. Confirm notification received
5. Verify cannot access other facility studies

### Radiologist Testing
1. Login as radiologist
2. Verify all studies from all facilities are visible
3. Test report creation
4. Verify notifications for new uploads
5. Test measurements and annotations

### Admin Testing
1. Login as admin
2. Verify all studies visible
3. Test administrative functions
4. Verify comprehensive notifications
5. Test facility management

## Benefits

### 1. Data Isolation
- Facilities can only see their own data
- Complete separation between facilities
- No cross-facility data leakage

### 2. Enhanced Security
- Comprehensive permission checks
- Consistent access control
- Secure notification system

### 3. Improved User Experience
- Clear access boundaries
- Appropriate notifications
- Intuitive permission system

### 4. Scalability
- Easy to add new user types
- Flexible permission system
- Maintainable code structure

## Future Enhancements

### 1. Role-Based Permissions
- More granular permission system
- Custom roles for different user types
- Permission inheritance

### 2. Audit Logging
- Track all access attempts
- Log permission violations
- User activity monitoring

### 3. Advanced Notifications
- Real-time notifications
- Email notifications
- Custom notification preferences

### 4. API Rate Limiting
- Prevent abuse of API endpoints
- Rate limiting per user
- API usage monitoring