# DICOM Viewer Fixes Summary

## Overview
Fixed two main issues in the DICOM viewer:
1. Patient information not displaying when redirected to the viewer
2. Uploaded studies showing "completed" status instead of "scheduled"

## Changes Made

### 1. Fixed Patient Information Display

**File**: `/workspace/viewer/views.py`
- **Line 963**: Added `institution_name` to the study data returned by the `get_study_images` API endpoint

```python
'study': {
    'id': study.id,
    'patient_name': study.patient_name,
    'study_date': study.study_date,
    'modality': study.modality,
    'study_description': study.study_description,
    'institution_name': study.institution_name,  # Added this line
},
```

This ensures that when the DICOM viewer loads a study, it receives all the necessary patient information including the institution name.

### 2. Fixed Status Display for Uploaded Studies

**File**: `/workspace/viewer/views.py`
- **Line 451**: Changed the status from 'completed' to 'scheduled' when creating WorklistEntry during upload
- **Line 788**: Same change in the second location where WorklistEntry is created

```python
WorklistEntry.objects.create(
    # ... other fields ...
    status='scheduled'  # Changed from 'completed' to 'scheduled'
)
```

This ensures that newly uploaded studies appear with the correct "scheduled" status in the worklist.

## How the DICOM Viewer Works

1. **When redirected to `/viewer/study/<id>/`**:
   - The `DicomViewerView` sets `initial_study_id` in the template context
   - The template renders this as a JavaScript variable: `window.initialStudyId`
   - The `DicomViewer` class is instantiated with this initial study ID
   - The viewer automatically calls `loadStudy()` to load the study data

2. **Patient Information Display**:
   - The `loadStudy()` function fetches data from `/viewer/api/studies/<id>/images/`
   - The API returns study information including patient name, study date, modality, and institution name
   - The `updatePatientInfo()` function updates the UI with this information

3. **Status Management**:
   - When files are uploaded, a `WorklistEntry` is created with status='scheduled'
   - When a radiologist views the images, the status is updated to 'in_progress'
   - The radiologist can then complete the study and change the status to 'completed'

## Testing the Fixes

To verify the fixes are working:

1. **Upload a DICOM study**:
   - The study should appear in the worklist with "Scheduled" status

2. **Click on a study in the worklist**:
   - You should be redirected to `/viewer/study/<id>/`
   - The patient information should display immediately in the top bar
   - The status should change to "In Progress"

3. **Check the patient information display**:
   - Should show: "Patient: [Name] | Study Date: [Date] | Modality: [Modality]"
   - Institution name is available in the study data for display in the info panel