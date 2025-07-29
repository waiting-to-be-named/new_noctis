# AE Title Implementation for Facilities

## Overview
This implementation adds automatic AE Title (Application Entity Title) generation for facilities in the PACS system. The AE Title is a unique identifier used in DICOM networking that allows modalities to send their studies to the correct PACS server.

## Features Implemented

### 1. Database Changes
- Added `ae_title` field to the Facility model
  - Maximum length: 16 characters (DICOM standard)
  - Unique constraint to ensure no duplicates
  - Help text explaining its purpose

### 2. Automatic Generation
- AE Titles are automatically generated from the facility name when creating a new facility
- Generation rules:
  - Removes all special characters and spaces
  - Converts to uppercase
  - Truncates to 16 characters maximum
  - Adds numeric suffix if needed to ensure uniqueness

### 3. Form Validation
- Custom form validation ensures:
  - Only uppercase letters and numbers are allowed
  - Maximum 16 characters
  - Unique across all facilities
  - Real-time preview in the create form

### 4. User Interface
- AE Title field added to facility creation/edit forms
- Read-only during creation (auto-generated)
- Editable during updates with validation
- JavaScript preview shows generated AE Title as user types facility name
- AE Title displayed in facility list view with distinctive styling

## Usage

### For Administrators
1. When creating a new facility, the AE Title is automatically generated based on the facility name
2. The generated AE Title is displayed in real-time as you type the facility name
3. For existing facilities, the AE Title can be edited if needed

### For DICOM Modalities
Configure your modalities to use the facility's AE Title as the destination when sending studies:
- Host: [Your PACS Server IP]
- Port: [Your DICOM Port, typically 104]
- AE Title: [The facility's AE Title shown in the admin panel]

## Example
- Facility Name: "St. Mary's Hospital"
- Generated AE Title: "STMARYSHOSPITAL"

If another facility already uses "STMARYSHOSPITAL", it would become "STMARYSHOSPITA1", "STMARYSHOSPITA2", etc.

## Migration Required
Run the following command to apply the database changes:
```bash
python manage.py migrate viewer
```