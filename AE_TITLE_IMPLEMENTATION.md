# AE Title Implementation for Facility Management

## Overview

This implementation adds automatic DICOM AE (Application Entity) title generation to the facility creation form. AE titles are essential for DICOM network communication, allowing modalities (CT scanners, MRI machines, etc.) to send studies to this PACS server.

## What is an AE Title?

An AE Title is a DICOM identifier used for network communication between DICOM devices. It's typically 1-16 characters long and contains only uppercase letters and numbers. Each facility needs a unique AE title so that modalities can send studies to the correct PACS destination.

## Implementation Details

### 1. Database Changes

**Model Update (`viewer/models.py`):**
- Added `ae_title` field to the `Facility` model
- Field is unique, max length 16 characters
- Includes help text for clarity

**Migration (`viewer/migrations/0004_add_facility_ae_title.py`):**
- Adds the new field to existing database
- Allows null values for existing records

### 2. Automatic Generation Logic

The `generate_ae_title()` method in the Facility model:

1. **Cleans the facility name**: Removes special characters, converts to uppercase
2. **Creates base title**: Takes first 8 characters of cleaned name
3. **Handles edge cases**: Uses "FACILITY" if name is too short
4. **Ensures uniqueness**: Adds numeric suffix if title already exists
5. **Fallback mechanism**: Uses random characters if too many conflicts

### 3. Form Integration

**Create/Update Views (`viewer/views.py`):**
- Added `ae_title` to form fields
- Maintains existing functionality

**Form Template (`templates/admin/facility_form.html`):**
- Added AE title input field with validation
- Auto-generation button with JavaScript functionality
- Real-time generation when facility name changes
- Visual feedback for generated titles

### 4. Display Updates

**Facility List (`templates/admin/facility_list.html`):**
- Added AE title column to facility table
- Displays AE title in monospace font with highlighting

**Facility Worklist (`templates/worklist/facility_worklist.html`):**
- Shows AE title in facility header
- Helps users identify the correct AE title for modalities

## Usage

### For Administrators

1. **Creating a New Facility:**
   - Fill in facility name
   - AE title will auto-generate based on the name
   - Can manually edit the AE title if needed
   - Click "Auto-Generate" button to regenerate

2. **Editing Existing Facility:**
   - Can view and modify the AE title
   - Auto-generation still available

### For Modality Technicians

The AE title displayed in the facility worklist should be configured in the modality's DICOM settings:

1. **CT Scanner Configuration:**
   - Set destination AE title to the facility's AE title
   - Configure IP address and port of this PACS server

2. **MRI Machine Configuration:**
   - Same process as CT scanner
   - Ensure unique AE title per facility

## Technical Specifications

### AE Title Rules
- **Length**: 1-16 characters
- **Characters**: Uppercase letters (A-Z) and numbers (0-9) only
- **Uniqueness**: Must be unique across all facilities
- **Format**: No spaces, special characters, or lowercase letters

### Generation Algorithm
1. Clean facility name: Remove special chars, convert to uppercase
2. Take first 8 characters as base
3. If base < 3 characters, use "FACILITY"
4. Check for uniqueness, add numeric suffix if needed
5. If too many conflicts, add random characters

### Examples
- "General Hospital" → "GENERAL"
- "St. Mary's Medical Center" → "STMARYS"
- "ABC" → "FACILITY"
- "University of California" → "UNIVERSI"

## JavaScript Functionality

The form includes client-side JavaScript for:
- **Auto-generation**: Creates AE title from facility name
- **Real-time updates**: Generates when facility name changes
- **Visual feedback**: Highlights generated titles
- **Validation**: Ensures proper format (uppercase, alphanumeric)

## Database Migration

To apply the changes to an existing database:

```bash
python manage.py migrate viewer 0004_add_facility_ae_title
```

For existing facilities without AE titles, they will be generated automatically when the facility is next saved.

## Testing

A test script (`test_ae_title.py`) is provided to verify the generation logic:

```bash
python test_ae_title.py
```

This tests various scenarios including:
- Basic facility names
- Names with special characters
- Short names
- Long names
- Duplicate names
- Manual AE titles

## Security Considerations

- AE titles are validated server-side
- Client-side validation provides immediate feedback
- Unique constraint prevents duplicate AE titles
- No sensitive information in AE titles

## Future Enhancements

Potential improvements:
1. **AE Title Validation**: Check against common DICOM standards
2. **Bulk Generation**: Generate AE titles for existing facilities
3. **Network Testing**: Verify AE title connectivity
4. **Modality Integration**: Direct modality configuration interface

## Troubleshooting

### Common Issues

1. **AE Title Already Exists**
   - The system will automatically add a suffix
   - Check facility list for existing titles

2. **Invalid Characters**
   - Only uppercase letters and numbers allowed
   - Form will show validation error

3. **Migration Issues**
   - Ensure Django environment is properly set up
   - Check database permissions

### Debugging

- Check browser console for JavaScript errors
- Verify database migration was applied
- Test AE title generation with test script