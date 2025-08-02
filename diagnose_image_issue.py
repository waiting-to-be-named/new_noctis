#!/usr/bin/env python3
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage, DicomSeries, DicomStudy
from django.conf import settings
import pydicom

def diagnose_images():
    print("=" * 80)
    print("DICOM IMAGE DIAGNOSTIC REPORT")
    print("=" * 80)
    
    # Check media root
    print(f"\nMEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"MEDIA_ROOT exists: {os.path.exists(settings.MEDIA_ROOT)}")
    
    # Get all images
    images = DicomImage.objects.all()
    print(f"\nTotal DicomImage records in database: {images.count()}")
    
    if images.count() == 0:
        print("\nNo images found in database!")
        return
    
    # Check each image
    working_images = 0
    failed_images = 0
    
    print("\nChecking each image:")
    print("-" * 80)
    
    for img in images[:10]:  # Check first 10 images
        print(f"\nImage ID: {img.id}")
        print(f"Series: {img.series.series_description if img.series else 'None'}")
        print(f"Study: {img.series.study.study_description if img.series and img.series.study else 'None'}")
        print(f"File path field: {img.file_path}")
        
        # Check if file exists
        if img.file_path:
            # Get the actual file path
            if hasattr(img.file_path, 'path'):
                file_path = img.file_path.path
            else:
                file_path = os.path.join(settings.MEDIA_ROOT, str(img.file_path))
            
            print(f"Full file path: {file_path}")
            print(f"File exists: {os.path.exists(file_path)}")
            
            if os.path.exists(file_path):
                # Try to load the DICOM file
                try:
                    dcm = pydicom.dcmread(file_path)
                    print(f"✓ DICOM file readable")
                    print(f"  - Modality: {getattr(dcm, 'Modality', 'Unknown')}")
                    print(f"  - Rows: {getattr(dcm, 'Rows', 'Unknown')}")
                    print(f"  - Columns: {getattr(dcm, 'Columns', 'Unknown')}")
                    
                    # Check for pixel data
                    if hasattr(dcm, 'pixel_array'):
                        print(f"  - Has pixel data: Yes")
                        print(f"  - Pixel array shape: {dcm.pixel_array.shape}")
                    else:
                        print(f"  - Has pixel data: No")
                    
                    # Check cached data
                    if img.processed_image_cache:
                        print(f"  - Has cached image data: Yes (length: {len(img.processed_image_cache)})")
                    else:
                        print(f"  - Has cached image data: No")
                    
                    working_images += 1
                except Exception as e:
                    print(f"✗ Error reading DICOM file: {e}")
                    failed_images += 1
            else:
                print(f"✗ File does not exist!")
                failed_images += 1
                
                # Check alternative paths
                alt_paths = [
                    os.path.join(os.getcwd(), 'media', str(img.file_path)),
                    os.path.join(os.getcwd(), str(img.file_path)),
                    str(img.file_path)
                ]
                
                print("  Checking alternative paths:")
                for alt_path in alt_paths:
                    print(f"    - {alt_path}: {'EXISTS' if os.path.exists(alt_path) else 'NOT FOUND'}")
        else:
            print(f"✗ No file path set in database!")
            failed_images += 1
    
    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"  - Working images: {working_images}")
    print(f"  - Failed images: {failed_images}")
    print(f"  - Total checked: {working_images + failed_images}")
    
    # List all files in media/dicom_files
    dicom_dir = os.path.join(settings.MEDIA_ROOT, 'dicom_files')
    if os.path.exists(dicom_dir):
        print(f"\nFiles in {dicom_dir}:")
        for file in os.listdir(dicom_dir):
            print(f"  - {file}")

if __name__ == "__main__":
    diagnose_images()