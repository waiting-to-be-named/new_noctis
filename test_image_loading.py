#!/usr/bin/env python3
"""
Test script to verify DICOM image loading functionality
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage, DicomSeries
from django.contrib.auth.models import User

def test_image_loading():
    """Test if images can be loaded and processed correctly"""
    print("Testing DICOM image loading...")
    
    # Check if we have any studies
    studies = DicomStudy.objects.all()
    print(f"Found {studies.count()} studies in database")
    
    if studies.count() == 0:
        print("No studies found. Please upload some DICOM files first.")
        return False
    
    # Get the first study
    study = studies.first()
    print(f"Testing with study: {study.patient_name} (ID: {study.id})")
    
    # Check if study has series
    series_list = study.series.all()
    print(f"Study has {series_list.count()} series")
    
    if series_list.count() == 0:
        print("Study has no series. This might indicate an upload issue.")
        return False
    
    # Get the first series
    series = series_list.first()
    print(f"Testing with series: {series.series_description} (ID: {series.id})")
    
    # Check if series has images
    images = series.images.all()
    print(f"Series has {images.count()} images")
    
    if images.count() == 0:
        print("Series has no images. This might indicate an upload issue.")
        return False
    
    # Test the first image
    image = images.first()
    print(f"Testing image: {image.sop_instance_uid} (ID: {image.id})")
    print(f"Image file path: {image.file_path}")
    
    # Check if file exists
    if hasattr(image.file_path, 'path'):
        file_path = image.file_path.path
    else:
        file_path = str(image.file_path)
    
    print(f"Full file path: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist: {file_path}")
        return False
    
    print(f"✓ File exists: {file_path}")
    
    # Test loading DICOM data
    try:
        dicom_data = image.load_dicom_data()
        if dicom_data:
            print("✓ DICOM data loaded successfully")
            print(f"  - Rows: {getattr(dicom_data, 'Rows', 'N/A')}")
            print(f"  - Columns: {getattr(dicom_data, 'Columns', 'N/A')}")
            print(f"  - Modality: {getattr(dicom_data, 'Modality', 'N/A')}")
        else:
            print("✗ Failed to load DICOM data")
            return False
    except Exception as e:
        print(f"✗ Error loading DICOM data: {e}")
        return False
    
    # Test getting pixel array
    try:
        pixel_array = image.get_pixel_array()
        if pixel_array is not None:
            print(f"✓ Pixel array loaded successfully")
            print(f"  - Shape: {pixel_array.shape}")
            print(f"  - Data type: {pixel_array.dtype}")
            print(f"  - Min value: {pixel_array.min()}")
            print(f"  - Max value: {pixel_array.max()}")
        else:
            print("✗ Failed to get pixel array")
            return False
    except Exception as e:
        print(f"✗ Error getting pixel array: {e}")
        return False
    
    # Test image processing
    try:
        base64_image = image.get_processed_image_base64()
        if base64_image:
            print("✓ Image processing successful")
            print(f"  - Base64 length: {len(base64_image)}")
        else:
            print("✗ Failed to process image")
            return False
    except Exception as e:
        print(f"✗ Error processing image: {e}")
        return False
    
    print("\n✓ All image loading tests passed!")
    return True

def test_api_endpoints():
    """Test the API endpoints that the frontend uses"""
    print("\nTesting API endpoints...")
    
    # Check if we have any studies
    studies = DicomStudy.objects.all()
    if studies.count() == 0:
        print("No studies available for API testing")
        return False
    
    study = studies.first()
    print(f"Testing API with study ID: {study.id}")
    
    # Test study images endpoint
    try:
        from django.test import Client
        from django.urls import reverse
        
        client = Client()
        
        # Test study images endpoint
        url = f'/viewer/api/studies/{study.id}/images/'
        response = client.get(url)
        
        if response.status_code == 200:
            print("✓ Study images API endpoint working")
            data = response.json()
            print(f"  - Found {len(data.get('images', []))} images")
        else:
            print(f"✗ Study images API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing API: {e}")
        return False
    
    print("✓ API endpoint tests passed!")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("DICOM Image Loading Test")
    print("=" * 50)
    
    success = True
    
    # Test image loading
    if not test_image_loading():
        success = False
    
    # Test API endpoints
    if not test_api_endpoints():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ ALL TESTS PASSED")
        print("The image loading functionality should work correctly.")
    else:
        print("✗ SOME TESTS FAILED")
        print("There are issues with the image loading functionality.")
    print("=" * 50)