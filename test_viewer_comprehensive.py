#!/usr/bin/env python3
"""
Comprehensive test script to verify DICOM viewer functionality
"""

import os
import sys
import django
import requests
import json
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage

def test_viewer_comprehensive():
    """Comprehensive test of the DICOM viewer"""
    base_url = "http://localhost:8000"
    
    print("=== Comprehensive DICOM Viewer Test ===")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Server is running (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the server with: python3 manage.py runserver")
        return False
    
    # Test 2: Check database
    try:
        studies = DicomStudy.objects.all()
        images = DicomImage.objects.all()
        print(f"✅ Database: {studies.count()} studies, {images.count()} images")
        
        if not studies.exists():
            print("❌ No studies in database")
            return False
            
        if not images.exists():
            print("❌ No images in database")
            return False
            
        study = studies.first()
        image = images.first()
        print(f"   Sample study: {study.patient_name} (ID: {study.id})")
        print(f"   Sample image: {image.file_path} (ID: {image.id})")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Test 3: Check viewer page
    try:
        response = requests.get(f"{base_url}/viewer/study/{study.id}/")
        print(f"✅ Viewer page loads (status: {response.status_code})")
        
        if "dicom-canvas" in response.text:
            print("✅ Canvas element found in page")
        else:
            print("❌ Canvas element not found in page")
            return False
            
        if "initialStudyId" in response.text:
            print("✅ Initial study ID is set")
        else:
            print("❌ Initial study ID not set")
            return False
    except Exception as e:
        print(f"❌ Error loading viewer page: {e}")
        return False
    
    # Test 4: Check API endpoints
    try:
        response = requests.get(f"{base_url}/viewer/api/studies/{study.id}/images/")
        print(f"✅ Study images API (status: {response.status_code})")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('images', []))} images")
            
            if not data.get('images'):
                print("❌ No images returned by API")
                return False
        else:
            print(f"   Error: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ Error with study images API: {e}")
        return False
    
    # Test 5: Check image data API
    try:
        response = requests.get(f"{base_url}/viewer/api/images/{image.id}/data/?window_width=400&window_level=40")
        print(f"✅ Image data API (status: {response.status_code})")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('image_data'):
                print("✅ Image data received")
                print(f"   Image data length: {len(data['image_data'])}")
                print(f"   Metadata: {data.get('metadata', {})}")
            else:
                print("❌ No image data in response")
                return False
        else:
            print(f"   Error: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ Error with image data API: {e}")
        return False
    
    # Test 6: Check test page
    try:
        response = requests.get(f"{base_url}/viewer/test/")
        print(f"✅ Test page loads (status: {response.status_code})")
        
        if "DICOM Viewer Test" in response.text:
            print("✅ Test page content is correct")
        else:
            print("❌ Test page content is incorrect")
            return False
    except Exception as e:
        print(f"❌ Error loading test page: {e}")
        return False
    
    # Test 7: Check image processing
    try:
        pixel_array = image.get_pixel_array()
        print(f"✅ Image pixel array shape: {pixel_array.shape}")
        
        base64_data = image.get_processed_image_base64(window_width=400, window_level=40)
        print(f"✅ Base64 data length: {len(base64_data)}")
        print("✅ Image processing works")
    except Exception as e:
        print(f"❌ Image processing error: {e}")
        return False
    
    print("\n🎉 All tests passed! The DICOM viewer should be working correctly.")
    print("\nTo test the viewer manually:")
    print(f"1. Open: http://localhost:8000/viewer/study/{study.id}/")
    print(f"2. Open: http://localhost:8000/viewer/test/")
    print("3. Check the browser console for any JavaScript errors")
    
    return True

if __name__ == "__main__":
    success = test_viewer_comprehensive()
    if not success:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed successfully!")