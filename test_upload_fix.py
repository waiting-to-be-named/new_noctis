#!/usr/bin/env python3
"""
Simple test script to verify DICOM upload functionality works correctly.
"""

import os
import sys
from io import BytesIO
import tempfile

# Setup Django - configure settings first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')

import django
from django.conf import settings
django.setup()

from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from viewer.models import DicomStudy, DicomSeries, DicomImage
import pydicom
from pydicom.dataset import Dataset, FileDataset
import numpy as np

def create_test_dicom():
    """Create a simple test DICOM file"""
    try:
        # Create a simple DICOM dataset
        meta = pydicom.Dataset()
        meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
        meta.MediaStorageSOPInstanceUID = "1.2.3.4.5.6.7.8.9.0.1.2.3.4.5.6.7.8.9.0"
        meta.ImplementationClassUID = "1.2.3.4.5.6.7.8.9.0"
        meta.TransferSyntaxUID = "1.2.840.10008.1.2"  # Implicit VR Little Endian

        ds = FileDataset("test.dcm", {}, file_meta=meta, preamble=b"\0" * 128)
        
        # Add required DICOM tags
        ds.PatientName = "Test^Patient"
        ds.PatientID = "TEST001"
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.0.1.2.3.4.5.6.7.8.9.0.1"
        ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.0.1.2.3.4.5.6.7.8.9.0.2"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.0.1.2.3.4.5.6.7.8.9.0.3"
        ds.StudyDate = "20240101"
        ds.StudyTime = "120000"
        ds.Modality = "CT"
        ds.SeriesNumber = 1
        ds.InstanceNumber = 1
        ds.StudyDescription = "Test Study"
        ds.SeriesDescription = "Test Series"
        ds.InstitutionName = "Test Hospital"
        
        # Add image data
        ds.Rows = 64
        ds.Columns = 64
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelSpacing = [1.0, 1.0]
        ds.SliceThickness = 5.0
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        
        # Create pixel data (simple gradient)
        pixel_array = np.zeros((64, 64), dtype=np.uint16)
        for i in range(64):
            for j in range(64):
                pixel_array[i, j] = (i + j) * 100
        
        ds.PixelData = pixel_array.tobytes()
        
        # Save to BytesIO
        buffer = BytesIO()
        ds.save_as(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        print(f"Error creating test DICOM: {e}")
        return None

def test_upload_functionality():
    """Test the DICOM upload functionality"""
    print("Testing DICOM upload functionality...")
    
    # Create test client
    client = Client()
    
    # Create test DICOM file
    dicom_data = create_test_dicom()
    if not dicom_data:
        print("❌ Failed to create test DICOM file")
        return False
    
    # Create uploaded file
    uploaded_file = SimpleUploadedFile(
        name="test.dcm",
        content=dicom_data,
        content_type="application/dicom"
    )
    
    try:
        # Test upload endpoint
        response = client.post('/viewer/api/upload/', {
            'files': [uploaded_file]
        })
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.content.decode()}")
        
        if response.status_code == 200:
            print("✅ Upload successful!")
            
            # Check if data was saved to database
            studies = DicomStudy.objects.all()
            if studies.exists():
                study = studies.first()
                print(f"✅ Study created: {study.patient_name} - {study.study_description}")
                
                images = DicomImage.objects.filter(series__study=study)
                if images.exists():
                    image = images.first()
                    print(f"✅ Image created: {image.instance_number} ({image.rows}x{image.columns})")
                    
                    # Test image data retrieval
                    response = client.get(f'/viewer/api/images/{image.id}/data/')
                    if response.status_code == 200:
                        print("✅ Image data retrieval successful!")
                        return True
                    else:
                        print(f"❌ Image data retrieval failed: {response.status_code}")
                        print(f"Response: {response.content.decode()}")
                else:
                    print("❌ No images created")
            else:
                print("❌ No studies created")
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Upload test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def test_image_display():
    """Test the image display functionality"""
    print("\nTesting image display functionality...")
    
    # Check if we have any studies
    studies = DicomStudy.objects.all()
    if not studies.exists():
        print("❌ No studies found for testing image display")
        return False
    
    study = studies.first()
    client = Client()
    
    try:
        # Test studies endpoint
        response = client.get(f'/viewer/api/studies/{study.id}/images/')
        print(f"Studies API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('images'):
                print(f"✅ Found {len(data['images'])} images in study")
                
                # Test first image
                image_data = data['images'][0]
                image_response = client.get(f'/viewer/api/images/{image_data["id"]}/data/')
                
                if image_response.status_code == 200:
                    image_result = image_response.json()
                    if image_result.get('image_data'):
                        print("✅ Image display functionality working!")
                        return True
                    else:
                        print("❌ No image data in response")
                        print(f"Response: {image_result}")
                else:
                    print(f"❌ Image data request failed: {image_response.status_code}")
                    print(f"Response: {image_response.content.decode()}")
            else:
                print("❌ No images found in study")
        else:
            print(f"❌ Studies API failed: {response.status_code}")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Image display test failed: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def main():
    """Run all tests"""
    print("🔧 Testing DICOM Upload and Viewer Fixes")
    print("=" * 50)
    
    # Clean up any existing test data
    DicomImage.objects.all().delete()
    DicomSeries.objects.all().delete()
    DicomStudy.objects.all().delete()
    
    upload_success = test_upload_functionality()
    display_success = test_image_display()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Upload functionality: {'✅ PASS' if upload_success else '❌ FAIL'}")
    print(f"Image display: {'✅ PASS' if display_success else '❌ FAIL'}")
    
    if upload_success and display_success:
        print("\n🎉 All tests passed! The DICOM upload and viewer fixes are working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)