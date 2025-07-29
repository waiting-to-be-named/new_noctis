#!/usr/bin/env python3
"""
Manual test script to check DICOM viewer functionality
"""

import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage

def test_viewer_manually():
    """Test the viewer manually by making HTTP requests"""
    base_url = "http://localhost:8000"
    
    print("=== Manual DICOM Viewer Test ===")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Server is running (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the server with: python3 manage.py runserver")
        return
    
    # Test 2: Check viewer page
    try:
        response = requests.get(f"{base_url}/viewer/study/5/")
        print(f"✅ Viewer page loads (status: {response.status_code})")
        if "dicom-canvas" in response.text:
            print("✅ Canvas element found in page")
        else:
            print("❌ Canvas element not found in page")
    except Exception as e:
        print(f"❌ Error loading viewer page: {e}")
    
    # Test 3: Check API endpoints
    try:
        response = requests.get(f"{base_url}/viewer/api/studies/5/images/")
        print(f"✅ Study images API (status: {response.status_code})")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('images', []))} images")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"❌ Error with study images API: {e}")
    
    # Test 4: Check image data API
    try:
        response = requests.get(f"{base_url}/viewer/api/images/4/data/?window_width=400&window_level=40")
        print(f"✅ Image data API (status: {response.status_code})")
        if response.status_code == 200:
            data = response.json()
            if data.get('image_data'):
                print("✅ Image data received")
                print(f"   Image data length: {len(data['image_data'])}")
                print(f"   Metadata: {data.get('metadata', {})}")
            else:
                print("❌ No image data in response")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"❌ Error with image data API: {e}")
    
    # Test 5: Check database
    try:
        studies = DicomStudy.objects.all()
        images = DicomImage.objects.all()
        print(f"✅ Database: {studies.count()} studies, {images.count()} images")
        
        if studies.exists():
            study = studies.first()
            print(f"   Sample study: {study.patient_name} (ID: {study.id})")
        
        if images.exists():
            image = images.first()
            print(f"   Sample image: {image.file_path} (ID: {image.id})")
            
            # Test image processing
            try:
                pixel_array = image.get_pixel_array()
                print(f"   Image pixel array shape: {pixel_array.shape}")
                
                # Test base64 conversion
                base64_data = image.get_processed_image_base64(window_width=400, window_level=40)
                print(f"   Base64 data length: {len(base64_data)}")
                print("✅ Image processing works")
            except Exception as e:
                print(f"❌ Image processing error: {e}")
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    test_viewer_manually()