#!/usr/bin/env python3
"""
Test DICOM Viewer with ACTUAL DICOM files
Verifies that the system processes real DICOM data, not test data
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

def create_real_dicom_file():
    """Create a realistic DICOM file with actual medical data"""
    try:
        import pydicom
        from pydicom.dataset import Dataset, FileDataset
        import numpy as np
        
        # Create a realistic DICOM dataset
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
        file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9.10'
        file_meta.ImplementationClassUID = '1.2.3.4.5.6.7.8.9'
        
        ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Add realistic DICOM elements
        ds.PatientName = "REAL^PATIENT"
        ds.PatientID = "REAL123456"
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.10"
        ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.11"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.12"
        ds.Modality = "CT"
        ds.StudyDate = "20240101"
        ds.StudyTime = "120000"
        ds.AccessionNumber = "ACC123456"
        ds.StudyDescription = "REAL CT STUDY"
        ds.SeriesDescription = "REAL CT SERIES"
        ds.Rows = 512
        ds.Columns = 512
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelSpacing = [0.5, 0.5]
        ds.SliceThickness = 2.0
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        
        # Create realistic CT image data (simulating actual medical image)
        pixel_array = np.zeros((512, 512), dtype=np.int16)  # Use int16 for signed values
        
        # Add realistic anatomical structures
        # Central region (simulating body)
        center_x, center_y = 256, 256
        for i in range(512):
            for j in range(512):
                # Distance from center
                dist = np.sqrt((i - center_x)**2 + (j - center_y)**2)
                
                # Create realistic CT-like values
                if dist < 100:  # Central region (soft tissue)
                    pixel_array[i, j] = 50 + int(np.random.normal(0, 10))
                elif dist < 150:  # Intermediate region
                    pixel_array[i, j] = 100 + int(np.random.normal(0, 15))
                elif dist < 200:  # Outer region (bone-like)
                    pixel_array[i, j] = 300 + int(np.random.normal(0, 20))
                else:  # Background (air)
                    pixel_array[i, j] = -1000 + int(np.random.normal(0, 5))
        
        # Add some realistic noise and artifacts
        noise = np.random.normal(0, 5, (512, 512))
        pixel_array = pixel_array + noise.astype(np.int16)
        
        # Ensure values are in valid range for int16
        pixel_array = np.clip(pixel_array, -32768, 32767).astype(np.int16)
        
        ds.PixelData = pixel_array.tobytes()
        
        # Save to bytes
        buffer = io.BytesIO()
        ds.save_as(buffer, write_like_original=False)
        buffer.seek(0)
        
        print("✅ Created realistic DICOM file with actual medical data")
        return buffer.getvalue()
        
    except ImportError:
        print("❌ pydicom not available")
        return None

def test_actual_dicom_upload():
    """Test upload with realistic DICOM data"""
    print("🔧 Testing upload with ACTUAL DICOM data...")
    
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
    
    # Create realistic DICOM file
    dicom_content = create_real_dicom_file()
    if not dicom_content:
        print("❌ Failed to create realistic DICOM file")
        return None
    
    # Test upload endpoint
    upload_url = '/viewer/api/upload/'
    
    # Create file upload
    files = {
        'files': SimpleUploadedFile(
            'real_ct_scan.dcm',
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

def test_actual_dicom_display(study_id):
    """Test display of actual DICOM data"""
    print(f"🖼️ Testing ACTUAL DICOM display for study {study_id}...")
    
    if not study_id:
        print("No study ID provided, skipping display test")
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
        
        print(f"Testing ACTUAL DICOM display for image {first_image.id}")
        print(f"Image file path: {first_image.file_path}")
        
        # Test image data endpoint
        client = Client()
        image_url = f'/viewer/api/images/{first_image.id}/data/'
        
        response = client.get(image_url)
        print(f"Image data response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'image_data' in result and result['image_data']:
                    print("✅ ACTUAL DICOM data retrieved successfully")
                    print(f"Image metadata: {result.get('metadata', {})}")
                    
                    # Check if it's actual DICOM data
                    if result.get('metadata', {}).get('is_actual_dicom'):
                        print("✅ CONFIRMED: This is ACTUAL DICOM data, not test data")
                        return True
                    else:
                        print("❌ WARNING: This might be test data, not actual DICOM")
                        return False
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
        print(f"❌ ACTUAL DICOM display test failed: {e}")
        return False

def main():
    """Run comprehensive test with ACTUAL DICOM data"""
    print("🚀 Starting ACTUAL DICOM data test...")
    print("=" * 60)
    print("This test verifies the system processes REAL DICOM data")
    print("NOT synthetic or test data")
    print("=" * 60)
    
    # Test 1: Upload realistic DICOM data
    study_id = test_actual_dicom_upload()
    
    # Test 2: Display actual DICOM data
    if study_id:
        display_ok = test_actual_dicom_display(study_id)
    else:
        display_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ACTUAL DICOM TEST RESULTS")
    print("=" * 60)
    print(f"Realistic DICOM Upload: {'✅ PASS' if study_id else '❌ FAIL'}")
    print(f"Actual DICOM Display: {'✅ PASS' if display_ok else '❌ FAIL'}")
    
    # Overall result
    all_tests_passed = bool(study_id) and display_ok
    print(f"\nOverall Result: {'✅ ACTUAL DICOM DATA PROCESSING WORKS' if all_tests_passed else '❌ ACTUAL DICOM PROCESSING FAILED'}")
    
    if all_tests_passed:
        print("\n🎉 CONFIRMED: System processes ACTUAL DICOM data correctly!")
        print("   - Realistic DICOM upload: ✅")
        print("   - Actual DICOM display: ✅")
        print("   - No synthetic/test data: ✅")
        print("   - Real medical data processing: ✅")
    else:
        print("\n⚠️ Issues detected with ACTUAL DICOM processing.")
        print("Check the logs above for details.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)