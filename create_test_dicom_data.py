#!/usr/bin/env python3
"""
DICOM Data Processing Utility
Provides utilities for processing and managing DICOM files
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')

try:
    django.setup()
    from worklist.models import Study, Series, DICOMImage
    print("✅ DICOM processing utilities loaded successfully")
    print("📁 System ready for DICOM file uploads")
    print("🔧 Use the web interface to upload and manage DICOM files")
except Exception as e:
    print(f"❌ Error loading DICOM utilities: {e}")
    sys.exit(1)

def process_dicom_file(file_path):
    """Process a DICOM file and extract metadata"""
    try:
        import pydicom
        ds = pydicom.dcmread(file_path)
        
        metadata = {
            'patient_name': getattr(ds, 'PatientName', 'Unknown'),
            'patient_id': getattr(ds, 'PatientID', 'Unknown'),
            'study_description': getattr(ds, 'StudyDescription', 'Unknown'),
            'series_description': getattr(ds, 'SeriesDescription', 'Unknown'),
            'modality': getattr(ds, 'Modality', 'Unknown'),
            'study_date': getattr(ds, 'StudyDate', 'Unknown'),
            'institution': getattr(ds, 'InstitutionName', 'Unknown')
        }
        
        return metadata
    except Exception as e:
        print(f"Error processing DICOM file {file_path}: {e}")
        return None

if __name__ == "__main__":
    print("NOCTIS DICOM Viewer - Processing Utility")
    print("========================================")
    print("System initialized and ready for DICOM uploads")
    print("Access the web interface to upload your DICOM files")