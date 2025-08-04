#!/usr/bin/env python3
"""
Comprehensive DICOM Viewer System Test
Tests upload functionality, image display, and data visualization
"""

import os
import sys
import django
import requests
import json
import time
from pathlib import Path

# Add the project directory to Python path
sys.path.insert(0, '/workspace')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from viewer.models import DicomStudy, DicomSeries, DicomImage, Facility
from django.core.files.uploadedfile import SimpleUploadedFile
import io
import base64

def create_test_dicom_file():
    """Create a simple test DICOM file for testing"""
    try:
        import pydicom
        from pydicom.dataset import Dataset, FileDataset
        
        # Create a minimal DICOM dataset
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
        file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9.10'
        file_meta.ImplementationClassUID = '1.2.3.4.5.6.7.8.9'
        
        ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Add required DICOM elements
        ds.PatientName = "Test^Patient"
        ds.PatientID = "TEST123"
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.10"
        ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.11"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.12"
        ds.Modality = "CT"
        ds.StudyDate = "20240101"
        ds.StudyTime = "120000"
        ds.AccessionNumber = "ACC123"
        ds.StudyDescription = "Test Study"
        ds.SeriesDescription = "Test Series"
        ds.Rows = 256
        ds.Columns = 256
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelSpacing = [1.0, 1.0]
        ds.SliceThickness = 1.0
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        
        # Create a simple test image (256x256 with some pattern)
        import numpy as np
        pixel_array = np.zeros((256, 256), dtype=np.uint16)
        
        # Add some test pattern
        for i in range(256):
            for j in range(256):
                pixel_array[i, j] = (i + j) % 1000
        
        ds.PixelData = pixel_array.tobytes()
        
        # Save to bytes
        buffer = io.BytesIO()
        ds.save_as(buffer, write_like_original=False)
        buffer.seek(0)
        
        return buffer.getvalue()
        
    except ImportError:
        print("pydicom not available, creating minimal test file")
        # Create a minimal test file if pydicom is not available
        return b"DICOM\x00\x00" + b"\x00" * 1000

def test_upload_functionality():
    """Test the upload functionality"""
    print("🔧 Testing upload functionality...")
    
    client = Client()
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create a test facility
    facility, created = Facility.objects.get_or_create(
        name='Test Facility',
        defaults={
            'address': '123 Test St',
            'phone': '555-1234',
            'email': 'test@facility.com'
        }
    )
    
    # Login
    client.force_login(user)
    
    # Create test DICOM file
    dicom_content = create_test_dicom_file()
    
    # Test upload endpoint
    upload_url = '/viewer/api/upload/'
    
    # Create file upload
    files = {
        'files': SimpleUploadedFile(
            'test.dcm',
            dicom_content,
            content_type='application/dicom'
        )
    }
    
    try:
        response = client.post(upload_url, files, follow=True)
        print(f"Upload response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Upload result: {result}")
                return result.get('study_id')
            except json.JSONDecodeError:
                print("Response is not JSON")
                return None
        else:
            print(f"Upload failed with status {response.status_code}")
            print(f"Response content: {response.content}")
            return None
            
    except Exception as e:
        print(f"Upload test failed: {e}")
        return None

def test_image_display(study_id):
    """Test image display functionality"""
    print(f"🖼️ Testing image display for study {study_id}...")
    
    if not study_id:
        print("No study ID provided, skipping image display test")
        return False
    
    try:
        # Get the study and its images
        study = DicomStudy.objects.get(id=study_id)
        print(f"Found study: {study.patient_name} ({study.modality})")
        
        # Get first image
        first_image = None
        for series in study.series.all():
            if series.images.exists():
                first_image = series.images.first()
                break
        
        if not first_image:
            print("No images found in study")
            return False
        
        print(f"Testing image display for image {first_image.id}")
        
        # Test image data endpoint
        client = Client()
        image_url = f'/viewer/api/images/{first_image.id}/data/'
        
        response = client.get(image_url)
        print(f"Image data response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'image_data' in result and result['image_data']:
                    print("✅ Image data retrieved successfully")
                    print(f"Image metadata: {result.get('metadata', {})}")
                    return True
                else:
                    print("❌ No image data in response")
                    return False
            except json.JSONDecodeError:
                print("❌ Response is not JSON")
                return False
        else:
            print(f"❌ Image data request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Image display test failed: {e}")
        return False

def test_study_listing():
    """Test study listing functionality"""
    print("📋 Testing study listing...")
    
    client = Client()
    
    try:
        # Test studies endpoint
        studies_url = '/viewer/api/studies/'
        response = client.get(studies_url)
        
        print(f"Studies response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Found {len(result)} studies")
                for study in result:
                    print(f"  - {study.get('patient_name', 'Unknown')} ({study.get('modality', 'Unknown')})")
                return True
            except json.JSONDecodeError:
                print("❌ Studies response is not JSON")
                return False
        else:
            print(f"❌ Studies request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Study listing test failed: {e}")
        return False

def test_viewer_page():
    """Test the viewer page loads correctly"""
    print("🌐 Testing viewer page...")
    
    client = Client()
    
    try:
        # Test viewer page
        viewer_url = '/viewer/advanced/'
        response = client.get(viewer_url)
        
        print(f"Viewer page response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Viewer page loads successfully")
            return True
        else:
            print(f"❌ Viewer page failed to load: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Viewer page test failed: {e}")
        return False

def main():
    """Run comprehensive tests"""
    print("🚀 Starting comprehensive DICOM viewer system test...")
    print("=" * 60)
    
    # Test 1: Upload functionality
    study_id = test_upload_functionality()
    
    # Test 2: Image display
    if study_id:
        image_display_ok = test_image_display(study_id)
    else:
        image_display_ok = False
    
    # Test 3: Study listing
    study_listing_ok = test_study_listing()
    
    # Test 4: Viewer page
    viewer_page_ok = test_viewer_page()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Upload Functionality: {'✅ PASS' if study_id else '❌ FAIL'}")
    print(f"Image Display: {'✅ PASS' if image_display_ok else '❌ FAIL'}")
    print(f"Study Listing: {'✅ PASS' if study_listing_ok else '❌ FAIL'}")
    print(f"Viewer Page: {'✅ PASS' if viewer_page_ok else '❌ FAIL'}")
    
    # Overall result
    all_tests_passed = bool(study_id) and image_display_ok and study_listing_ok and viewer_page_ok
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
    
    if all_tests_passed:
        print("\n🎉 DICOM viewer system is working correctly!")
        print("   - Upload functionality: ✅")
        print("   - Image display: ✅")
        print("   - Data visualization: ✅")
        print("   - All features operational: ✅")
    else:
        print("\n⚠️ Some issues detected. Check the logs above for details.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)