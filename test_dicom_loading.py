#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage

def test_dicom_loading():
    """Test if DICOM files can be loaded properly"""
    print("Testing DICOM file loading...")
    
    images = DicomImage.objects.all()
    print(f"Found {images.count()} images in database")
    
    for img in images:
        print(f"\nTesting image {img.id}: {img.file_path}")
        
        # Check if file exists
        if hasattr(img.file_path, 'path'):
            file_path = img.file_path.path
        else:
            from django.conf import settings
            file_path = os.path.join(settings.MEDIA_ROOT, str(img.file_path))
        
        print(f"Full file path: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        # Try to load DICOM data
        try:
            dicom_data = img.load_dicom_data()
            if dicom_data:
                print(f"✓ DICOM data loaded successfully")
                print(f"  Rows: {getattr(dicom_data, 'Rows', 'N/A')}")
                print(f"  Columns: {getattr(dicom_data, 'Columns', 'N/A')}")
                print(f"  Modality: {getattr(dicom_data, 'Modality', 'N/A')}")
            else:
                print("✗ Failed to load DICOM data")
        except Exception as e:
            print(f"✗ Error loading DICOM data: {e}")

if __name__ == "__main__":
    test_dicom_loading()