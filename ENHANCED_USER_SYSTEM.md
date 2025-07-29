# Enhanced User System for Notifications and Chats

## Overview

The Noctis medical imaging system has been enhanced with a comprehensive user management system that provides actual user functionality for notifications and chats. This system extends Django's default User model with detailed user profiles and role-based access control.

## Key Features

### 1. User Profile System

#### UserProfile Model
- **User Types**: Radiologist, Technologist, Administrator, Facility Staff, Resident, Fellow
- **Professional Information**: Medical license, specialization, phone, bio
- **Facility Assignment**: Users can be assigned to specific healthcare facilities
- **Profile Pictures**: Support for user profile pictures
- **Active Status**: Track whether users are active staff members

#### Key Properties
- `display_name`: Returns full name or username for notifications/chats
- `role_display`: Returns human-readable role name
- `can_access_facility()`: Check if user can access a specific facility

### 2. Enhanced Notification System

#### New Notification Types
- `user_mention`: When users are mentioned in messages
- `facility_update`: Facility-related updates
- `report_assigned`: When reports are assigned to users

#### Enhanced Notification Model
- **Sender Field**: Track who sent the notification
- **Facility Association**: Link notifications to specific facilities
- **Sender Display Name**: Get proper display names for notifications

#### Notification Features
- User-specific notifications with sender information
- Facility-based notification filtering
- Enhanced notification display with user roles

### 3. Enhanced Chat System

#### New Message Types
- `facility_broadcast`: Messages sent to all facility staff
- `study_discussion`: Study-specific discussions
- `user_chat`: Direct user-to-user messages

#### Enhanced Chat Features
- **User Selection**: Choose specific recipients for direct messages
- **Facility Broadcasting**: Send messages to all facility staff
- **Study Discussions**: Link messages to specific studies
- **Role Display**: Show user roles in chat messages
- **Broadcast Indicators**: Visual indicators for broadcast messages

#### Chat Message Properties
- `sender_display_name`: Get proper display names
- `sender_role`: Get user role for display
- `is_facility_broadcast()`: Check if message is a facility broadcast

### 4. User Management Interface

#### Admin Features
- **User Grid View**: Card-based user display
- **Filtering**: Filter by user type, facility, status, and search
- **Statistics**: Display user counts and statistics
- **User Actions**: Edit and view user profiles

#### API Endpoints
- `GET /worklist/api/users/`: List users with filtering
- `GET /worklist/api/users/<id>/profile/`: Get detailed user profile
- `GET /worklist/api/facilities/<id>/staff/`: Get facility staff

### 5. Enhanced Frontend

#### Chat Interface Improvements
- **Message Type Selection**: Choose between direct messages, broadcasts, and study discussions
- **Recipient Selection**: Select specific users for direct messages
- **Facility Selection**: Choose facility for broadcasts
- **Study Selection**: Link messages to studies (optional)
- **Enhanced Display**: Show user roles and broadcast indicators

#### Notification Improvements
- **Sender Information**: Display who sent notifications
- **Facility Context**: Show facility information
- **Enhanced Styling**: Better visual hierarchy

## Database Schema

### UserProfile Model
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    user_type = models.CharField(choices=USER_TYPES, default='radiologist')
    facility = models.ForeignKey(Facility, null=True, blank=True)
    medical_license = models.CharField(max_length=50, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active_staff = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(blank=True)
```

### Enhanced Notification Model
```python
class Notification(models.Model):
    recipient = models.ForeignKey(User, related_name='notifications')
    sender = models.ForeignKey(User, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_study = models.ForeignKey(DicomStudy, null=True, blank=True)
    related_facility = models.ForeignKey(Facility, null=True, blank=True)
    is_read = models.BooleanField(default=False)
```

### Enhanced ChatMessage Model
```python
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages')
    recipient = models.ForeignKey(User, related_name='received_messages', null=True, blank=True)
    facility = models.ForeignKey(Facility, null=True, blank=True)
    message_type = models.CharField(choices=MESSAGE_TYPES, default='user_chat')
    message = models.TextField()
    related_study = models.ForeignKey(DicomStudy, null=True, blank=True)
    is_read = models.BooleanField(default=False)
```

## API Endpoints

### User Management
- `GET /worklist/api/users/` - List users with filtering
- `GET /worklist/api/users/<id>/profile/` - Get user profile details
- `GET /worklist/api/facilities/<id>/staff/` - Get facility staff

### Enhanced Chat
- `GET /worklist/api/chat/` - Get chat messages with enhanced user info
- `POST /worklist/api/chat/send/` - Send messages with user selection

### Enhanced Notifications
- `GET /worklist/api/notifications/` - Get notifications with sender info
- `GET /worklist/api/notifications/count/` - Get notification counts

## Usage Examples

### Creating a User Profile
```python
# Automatically created when User is created
user = User.objects.create_user(username='dr.smith', first_name='John', last_name='Smith')
# UserProfile is automatically created via signal
profile = user.profile
profile.user_type = 'radiologist'
profile.facility = facility
profile.medical_license = 'MD12345'
profile.specialization = 'Cardiothoracic Radiology'
profile.save()
```

### Sending Enhanced Notifications
```python
# Create notification with sender
create_notification(
    user=recipient_user,
    notification_type='user_mention',
    title='You were mentioned',
    message='Dr. Smith mentioned you in a chat',
    sender=sender_user,
    related_facility=facility
)
```

### Sending Chat Messages
```python
# Direct message
ChatMessage.objects.create(
    sender=user,
    recipient=recipient,
    message_type='user_chat',
    message='Hello, how are you?'
)

# Facility broadcast
ChatMessage.objects.create(
    sender=user,
    facility=facility,
    message_type='facility_broadcast',
    message='Important facility update'
)
```

## Frontend Integration

### Chat Interface
```javascript
// Load users for recipient selection
function loadUsers() {
    const facilityId = document.getElementById('chat-facility').value;
    fetch(`/worklist/api/users/?facility_id=${facilityId}`)
        .then(response => response.json())
        .then(data => {
            // Populate recipient dropdown
        });
}

// Send message with user selection
function sendMessage() {
    const recipientId = document.getElementById('chat-recipient').value;
    const messageType = document.getElementById('chat-message-type').value;
    
    fetch('/worklist/api/chat/send/', {
        method: 'POST',
        body: JSON.stringify({
            message: message,
            recipient_id: recipientId,
            message_type: messageType,
            facility_id: facilityId
        })
    });
}
```

## Benefits

1. **Better User Experience**: Users can see who sent messages and notifications
2. **Role-Based Access**: Different user types have different capabilities
3. **Facility Management**: Users are organized by facility
4. **Enhanced Communication**: Support for direct messages, broadcasts, and study discussions
5. **Professional Context**: Medical licenses, specializations, and professional information
6. **Scalability**: System can handle multiple facilities and user types

## Migration Notes

The system includes a migration file (`0004_userprofile_enhanced_notifications.py`) that:
- Creates the UserProfile model
- Adds sender and related_facility fields to Notification model
- Updates notification and chat message types
- Maintains backward compatibility

## Future Enhancements

1. **User Groups**: Support for user groups and permissions
2. **Message Threading**: Support for threaded conversations
3. **File Attachments**: Support for file sharing in chats
4. **Push Notifications**: Real-time notifications
5. **User Activity Tracking**: Track user activity and engagement
6. **Advanced Search**: Search through messages and notifications
7. **Message Encryption**: End-to-end encryption for sensitive communications

## Security Considerations

1. **Access Control**: Users can only access facilities they're assigned to
2. **Permission Checks**: Admin-only features are properly protected
3. **Data Validation**: All user inputs are validated
4. **CSRF Protection**: All forms include CSRF tokens
5. **SQL Injection Prevention**: Using Django ORM for all database operations

This enhanced user system provides a solid foundation for professional medical imaging communication while maintaining security and scalability.