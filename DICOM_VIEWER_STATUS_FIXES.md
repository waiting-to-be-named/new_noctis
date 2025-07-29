# DICOM Viewer Display and Status System Fixes

## Overview
This document describes the fixes implemented to address:
1. DICOM viewer not displaying images when redirected from the worklist
2. Status system not properly reflecting report progress

## Issues Addressed

### 1. DICOM Viewer Not Displaying Images

**Problem**: When the system redirects to the DICOM viewer from the worklist, no images were displayed in the canvas.

**Root Cause**: The viewer was being initialized before the study ID was available, causing a race condition.

**Solution Implemented**:
- Modified `DicomViewer` constructor to accept an optional `initialStudyId` parameter
- Updated the initialization flow to load the study after all components are set up
- Changed the template to set a global `window.initialStudyId` variable before loading the viewer script
- Added better logging to track image loading progress

**Files Modified**:
- `/workspace/static/js/dicom_viewer.js`
  - Updated constructor to accept initial study ID
  - Made `init()` method async to properly handle asynchronous operations
  - Added automatic loading of initial study if provided
  - Enhanced error handling and logging

- `/workspace/templates/dicom_viewer/viewer.html`
  - Moved study ID assignment to a global variable before script loading
  - Removed the setTimeout delay that was causing timing issues

### 2. Status System Updates

**Problem**: The status system was not properly reflecting:
- "Scheduled" - default status
- "In Progress" - when radiologist opens images
- "Completed" - when report is saved/finalized

**Solution Implemented**:
- Updated `DicomViewerView` to automatically set worklist status to "in_progress" when a radiologist views images
- Modified report saving logic to set worklist status to "completed" when report is finalized
- Ensured proper status transitions throughout the workflow

**Files Modified**:
- `/workspace/viewer/views.py`
  - Added logic to update worklist entry status to 'in_progress' when study is viewed
  
- `/workspace/worklist/views.py`
  - Added logic to update worklist entry status to 'completed' when report is finalized

## Status Flow

1. **Scheduled** (Gray badge #666)
   - Default status when worklist entry is created
   - Indicates exam is scheduled but not yet started

2. **In Progress** (Orange badge #ff9900)
   - Set automatically when radiologist opens the DICOM viewer with a study
   - Indicates radiologist is currently reviewing the images

3. **Completed** (Green badge #00ff00)
   - Set when radiologist finalizes the report
   - Indicates the report is complete and ready for review

## Technical Details

### JavaScript Changes
The viewer initialization now follows this flow:
1. Template sets `window.initialStudyId` if a study ID is provided
2. DicomViewer is instantiated with the initial study ID
3. The `init()` method loads backend studies and then loads the initial study
4. Better error handling ensures any issues are logged and displayed

### Backend Changes
- Worklist entries are automatically updated based on user actions
- Status changes are persisted to the database immediately
- No manual status updates required from users

## Testing Recommendations

1. Test image display:
   - Click "Open DICOM Viewer" from worklist
   - Verify images load and display correctly
   - Check console for any error messages

2. Test status updates:
   - Create a new worklist entry (status should be "Scheduled")
   - Open DICOM viewer for that study (status should change to "In Progress")
   - Create and finalize a report (status should change to "Completed")

## Notes
- The CSS styles for status badges are already properly configured
- All necessary model imports are in place
- The system maintains backward compatibility with existing workflows