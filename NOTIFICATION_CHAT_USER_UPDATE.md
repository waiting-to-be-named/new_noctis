# Notification and Chat System - User Integration Update

## Summary
Updated the notification and chat system to properly use actual users instead of generic recipients.

## Changes Made

### 1. Model Updates
- **Facility Model**: Added a many-to-many relationship with User model to track facility staff members
  - Added `staff = models.ManyToManyField(User, related_name='facilities', blank=True)`
  - This allows proper tracking of which users work at each facility

### 2. Admin Interface Updates
- **FacilityAdmin**: Added admin interface for managing facility staff
  - Added filter_horizontal widget for easy staff selection
  - Shows staff count in list view
  - Provides dedicated section for managing staff members

### 3. View Updates

#### Notification Creation
- Updated notification creation to use actual facility staff members:
  - When a report is finalized, notifications are sent to all staff members of the related facility
  - Each staff member receives an individual notification

#### Chat System
- Updated chat message sending to notify all facility staff:
  - When a message is sent to a facility, all staff members (except the sender) receive notifications
  - Individual recipient notifications are also supported

#### Permission Checks
- Updated all permission checks to use the new many-to-many relationship:
  - Changed from `hasattr(user, 'facility_staff')` to `user.facilities.filter(...)`
  - Updated facility filtering in worklist views
  - Updated study upload facility assignment

### 4. Migration
- Created migration `0004_add_facility_staff.py` to add the staff relationship to Facility model

## Usage

### Setting Up Facility Staff
1. Go to Django admin interface
2. Navigate to Facilities
3. Select a facility
4. In the "Staff Members" section, select users who work at that facility
5. Save

### How It Works Now
1. **Notifications**: When events occur (report ready, new study, etc.), notifications are sent to actual users:
   - Facility staff receive notifications for facility-related events
   - Radiologists receive notifications for new studies
   - System administrators receive error notifications

2. **Chat Messages**: 
   - Messages sent to a facility are visible to all staff members
   - Each staff member receives a notification about new messages
   - The sender is excluded from notifications to avoid self-notification

3. **Permissions**:
   - Users can only see worklist entries for facilities they are staff members of
   - Multiple facility membership is supported (users can be staff at multiple facilities)

## Benefits
- Proper user tracking and accountability
- Individual notification preferences can be implemented
- Better security through proper user-based permissions
- Scalable to support multiple facilities and staff configurations