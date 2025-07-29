# Migration from Test Users to Real Users

## Summary

This document outlines the changes made to transition the DICOM Viewer system from test users to real users for production use.

## What Was Changed

### 1. Test Users Removed
The following test users have been removed from the database:
- `admin` (admin@example.com) - Test superuser
- `radiologist` (rad@example.com) - Test radiologist user

### 2. Test Facility Replaced
The test facility "Test Hospital" with fake contact information has been removed and replaced with a real facility configuration.

### 3. New Management Tools Added

#### Management Command: `remove_test_data`
- **Location**: `viewer/management/commands/remove_test_data.py`
- **Purpose**: Remove test users and facilities, create real facility
- **Usage**: 
  ```bash
  # Preview what will be removed
  python manage.py remove_test_data
  
  # Remove test data and create real facility
  python manage.py remove_test_data --confirm \
    --facility-name "Your Hospital" \
    --facility-address "123 Medical Center Dr" \
    --facility-phone "555-123-4567" \
    --facility-email "info@hospital.com"
  ```

#### Interactive Setup Script: `setup_real_users.py`
- **Location**: `setup_real_users.py` (root directory)
- **Purpose**: Interactive script to guide users through the migration process
- **Features**:
  - Detects existing test data
  - Prompts for real facility information
  - Removes test users and facilities
  - Creates real facility
  - Optionally creates admin user
  - Provides post-setup instructions

### 4. Updated Documentation
- **README.md**: Updated setup instructions to include test data removal
- **Setup Instructions**: Added both manual and interactive setup options

### 5. Improved User Interface
- **Radiologist Creation Form**: Added guidance text explaining that real user accounts should be created
- **Admin Interface**: Clarified that the system is for real users, not test data

## Current State

After running the migration:
- ✅ All test users removed
- ✅ Test facility "Test Hospital" removed  
- ✅ Real facility "Medical Center" created with proper contact information
- ✅ Radiologists group preserved
- ✅ System ready for real user accounts

## Next Steps for Production Use

1. **Create Administrator Account**:
   ```bash
   python manage.py createsuperuser
   ```

2. **Access Admin Interface**:
   - Go to `http://localhost:8000/admin/`
   - Login with your administrator credentials

3. **Create Radiologist Accounts**:
   - Navigate to `http://localhost:8000/admin/create-radiologist/`
   - Create real radiologist accounts with actual credentials

4. **Security Considerations**:
   - Change default passwords
   - Use strong passwords for all accounts
   - Configure proper database backups
   - Set up proper SSL/TLS in production

## Files Modified

- `viewer/management/commands/remove_test_data.py` (new)
- `viewer/management/__init__.py` (new)
- `viewer/management/commands/__init__.py` (new)
- `setup_real_users.py` (new)
- `README.md` (updated)
- `templates/admin/radiologist_form.html` (updated)
- `MIGRATION_TO_REAL_USERS.md` (this file)

## Database Changes

### Before Migration:
```sql
-- Users table
admin | admin@example.com | superuser
radiologist | rad@example.com | regular user

-- Facilities table  
Test Hospital | 123 Medical Center Dr | 555-1234 | info@testhospital.com
```

### After Migration:
```sql
-- Users table
(empty - ready for real users)

-- Facilities table
Medical Center | 123 Healthcare Blvd | 555-0123 | admin@medicalcenter.com
```

## Rollback Instructions

If you need to restore test data for development:

1. **Create Test Users Manually**:
   ```python
   # In Django shell
   from django.contrib.auth.models import User, Group
   
   # Create test admin
   admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
   
   # Create test radiologist
   radiologist = User.objects.create_user('radiologist', 'rad@example.com', 'rad123')
   rad_group = Group.objects.get(name='Radiologists')
   radiologist.groups.add(rad_group)
   ```

2. **Create Test Facility**:
   ```python
   from viewer.models import Facility
   
   Facility.objects.create(
       name='Test Hospital',
       address='123 Medical Center Dr',
       phone='555-1234',
       email='info@testhospital.com'
   )
   ```

## Support

For questions or issues related to this migration, refer to:
- Django documentation for user management
- Project README.md for setup instructions
- Admin interface at `/admin/` for user management