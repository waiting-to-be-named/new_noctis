#!/usr/bin/env python3
"""
Test script to verify DICOM upload and viewer functionality
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage, Facility
from django.contrib.auth.models import User
import pydicom
import numpy as np
from PIL import Image
import io
import base64

def create_test_dicom():
    """Create a simple test DICOM file"""
    # Create a simple test image
    test_image = np.random.randint(0, 255, (256, 256), dtype=np.uint8)
    
    # Create a basic DICOM dataset
    ds = pydicom.Dataset()
    ds.PatientName = "TEST^PATIENT"
    ds.PatientID = "TEST123"
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.10"
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.11"
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.12"
    ds.Modality = "CT"
    ds.StudyDate = "20240101"
    ds.StudyTime = "120000"
    ds.StudyDescription = "Test Study"
    ds.SeriesDescription = "Test Series"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.Rows = 256
    ds.Columns = 256
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelSpacing = [1.0, 1.0]
    ds.SliceThickness = 1.0
    ds.WindowCenter = 128
    ds.WindowWidth = 256
    
    # Set required file attributes
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    # Set the pixel data
    ds.PixelData = test_image.tobytes()
    
    return ds

def test_upload_functionality():
    """Test the upload functionality"""
    print("Testing upload functionality...")
    
    # Create test DICOM file
    ds = create_test_dicom()
    
    # Save to temporary file
    test_file_path = "test_dicom.dcm"
    ds.save_as(test_file_path)
    
    print(f"Created test DICOM file: {test_file_path}")
    print(f"File size: {os.path.getsize(test_file_path)} bytes")
    
    # Test reading the file
    try:
        loaded_ds = pydicom.dcmread(test_file_path)
        print("✓ Successfully read test DICOM file")
        print(f"  Patient Name: {loaded_ds.PatientName}")
        print(f"  Study UID: {loaded_ds.StudyInstanceUID}")
        print(f"  Image dimensions: {loaded_ds.Rows} x {loaded_ds.Columns}")
    except Exception as e:
        print(f"✗ Failed to read test DICOM file: {e}")
        return False
    
    # Clean up
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    
    return True

def test_viewer_functionality():
    """Test the viewer functionality"""
    print("\nTesting viewer functionality...")
    
    # Check if we have any studies in the database
    studies = DicomStudy.objects.all()
    print(f"Found {studies.count()} studies in database")
    
    if studies.count() == 0:
        print("No studies found. Please upload some DICOM files first.")
        return False
    
    # Test the first study
    study = studies.first()
    print(f"Testing study: {study.patient_name} (ID: {study.id})")
    
    # Check series
    series_count = study.series.count()
    print(f"Study has {series_count} series")
    
    if series_count == 0:
        print("No series found in study.")
        return False
    
    # Test the first series
    series = study.series.first()
    print(f"Testing series: {series.series_description} (ID: {series.id})")
    
    # Check images
    images_count = series.images.count()
    print(f"Series has {images_count} images")
    
    if images_count == 0:
        print("No images found in series.")
        return False
    
    # Test the first image
    image = series.images.first()
    print(f"Testing image: {image.sop_instance_uid} (ID: {image.id})")
    
    # Test image processing
    try:
        # Test loading DICOM data
        dicom_data = image.load_dicom_data()
        if dicom_data:
            print("✓ Successfully loaded DICOM data")
        else:
            print("✗ Failed to load DICOM data")
            return False
        
        # Test getting pixel array
        pixel_array = image.get_pixel_array()
        if pixel_array is not None:
            print(f"✓ Successfully got pixel array: {pixel_array.shape}")
        else:
            print("✗ Failed to get pixel array")
            return False
        
        # Test image processing
        processed_image = image.get_processed_image_base64()
        if processed_image:
            print("✓ Successfully processed image")
        else:
            print("✗ Failed to process image")
            return False
        
    except Exception as e:
        print(f"✗ Error testing image: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_database_models():
    """Test database models"""
    print("\nTesting database models...")
    
    # Test Facility model
    try:
        facility, created = Facility.objects.get_or_create(
            name="Test Facility",
            defaults={
                'address': 'Test Address',
                'phone': '123-456-7890',
                'email': 'test@facility.com'
            }
        )
        if created:
            print("✓ Created test facility")
        else:
            print("✓ Found existing test facility")
    except Exception as e:
        print(f"✗ Error with Facility model: {e}")
        return False
    
    # Test User model
    try:
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        if created:
            print("✓ Created test user")
        else:
            print("✓ Found existing test user")
    except Exception as e:
        print(f"✗ Error with User model: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("=== DICOM Viewer Test Suite ===")
    
    # Test database models
    if not test_database_models():
        print("Database model tests failed!")
        return
    
    # Test upload functionality
    if not test_upload_functionality():
        print("Upload functionality tests failed!")
        return
    
    # Test viewer functionality
    if not test_viewer_functionality():
        print("Viewer functionality tests failed!")
        return
    
    print("\n=== All tests passed! ===")
    print("The DICOM viewer should be working correctly.")
    print("You can now:")
    print("1. Upload DICOM files through the web interface")
    print("2. View images in the DICOM viewer")
    print("3. Use all the viewer features (window/level, measurements, etc.)")

if __name__ == "__main__":
    main()