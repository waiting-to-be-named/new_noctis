#!/usr/bin/env python3
"""
Comprehensive test script to identify and fix DICOM upload and viewer issues
"""

import os
import sys
import django
from django.conf import settings
import requests
import json
import time

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
import tempfile

def create_test_dicom_file():
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
    ds.WindowWidth = 400
    ds.WindowCenter = 40
    
    # Set required attributes for saving
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    
    # Set the pixel data
    ds.PixelData = test_image.tobytes()
    
    # Add file meta information
    ds.file_meta = pydicom.dataset.FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = pydicom.uid.ImplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta.ImplementationClassUID = pydicom.uid.PYDICOM_IMPLEMENTATION_UID
    ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
    
    return ds

def test_upload_functionality():
    """Test the upload functionality"""
    print("=== Testing Upload Functionality ===")
    
    # Create test DICOM file
    ds = create_test_dicom_file()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as temp_file:
        ds.save_as(temp_file.name)
        temp_file_path = temp_file.name
    
    try:
        # Test file upload via API
        url = "http://localhost:8000/viewer/api/upload/"
        
        with open(temp_file_path, 'rb') as f:
            files = {'files': f}
            response = requests.post(url, files=files)
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Upload successful: {data}")
            return data.get('study_id')
        else:
            print(f"Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Upload test failed: {e}")
        return None
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

def test_viewer_functionality(study_id):
    """Test the viewer functionality"""
    print(f"\n=== Testing Viewer Functionality for Study {study_id} ===")
    
    try:
        # Get study images
        url = f"http://localhost:8000/viewer/api/studies/{study_id}/images/"
        response = requests.get(url)
        
        print(f"Get images response status: {response.status_code}")
        print(f"Get images response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            images = data.get('images', [])
            
            if images:
                # Test image data retrieval
                image_id = images[0]['id']
                url = f"http://localhost:8000/viewer/api/images/{image_id}/data/"
                response = requests.get(url)
                
                print(f"Get image data response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('image_data'):
                        print("✓ Image data retrieval successful")
                        return True
                    else:
                        print("✗ No image data received")
                        return False
                else:
                    print(f"✗ Image data retrieval failed: {response.text}")
                    return False
            else:
                print("✗ No images found in study")
                return False
        else:
            print(f"✗ Failed to get study images: {response.text}")
            return False
            
    except Exception as e:
        print(f"Viewer test failed: {e}")
        return False

def test_database_models():
    """Test database models and relationships"""
    print("\n=== Testing Database Models ===")
    
    try:
        # Check if we have any studies
        studies = DicomStudy.objects.all()
        print(f"Total studies in database: {studies.count()}")
        
        for study in studies[:3]:  # Check first 3 studies
            print(f"\nStudy: {study}")
            print(f"  Patient: {study.patient_name}")
            print(f"  Series count: {study.series_count}")
            print(f"  Total images: {study.total_images}")
            
            for series in study.series.all()[:2]:  # Check first 2 series
                print(f"  Series: {series}")
                print(f"    Image count: {series.image_count}")
                
                for image in series.images.all()[:1]:  # Check first image
                    print(f"    Image: {image}")
                    print(f"      File path: {image.file_path}")
                    print(f"      Rows: {image.rows}, Columns: {image.columns}")
                    
                    # Test image processing
                    try:
                        pixel_array = image.get_pixel_array()
                        if pixel_array is not None:
                            print(f"      ✓ Pixel array loaded successfully")
                            print(f"      Shape: {pixel_array.shape}")
                        else:
                            print(f"      ✗ Failed to load pixel array")
                    except Exception as e:
                        print(f"      ✗ Error loading pixel array: {e}")
                    
                    # Test processed image
                    try:
                        base64_image = image.get_processed_image_base64()
                        if base64_image:
                            print(f"      ✓ Processed image generated successfully")
                        else:
                            print(f"      ✗ Failed to generate processed image")
                    except Exception as e:
                        print(f"      ✗ Error generating processed image: {e}")
        
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

def test_file_system():
    """Test file system and media directory"""
    print("\n=== Testing File System ===")
    
    try:
        from django.conf import settings
        
        # Check media directory
        media_root = settings.MEDIA_ROOT
        print(f"Media root: {media_root}")
        
        if os.path.exists(media_root):
            print("✓ Media root exists")
            
            # Check dicom_files directory
            dicom_dir = os.path.join(media_root, 'dicom_files')
            if os.path.exists(dicom_dir):
                print("✓ DICOM files directory exists")
                
                # List some files
                files = os.listdir(dicom_dir)
                print(f"Files in DICOM directory: {len(files)}")
                
                for file in files[:5]:  # Show first 5 files
                    file_path = os.path.join(dicom_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        print(f"  {file}: {size} bytes")
            else:
                print("✗ DICOM files directory does not exist")
                return False
        else:
            print("✗ Media root does not exist")
            return False
            
        return True
        
    except Exception as e:
        print(f"File system test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting comprehensive DICOM upload and viewer test...")
    
    # Test file system
    file_system_ok = test_file_system()
    
    # Test database models
    models_ok = test_database_models()
    
    # Test upload functionality
    study_id = test_upload_functionality()
    
    # Test viewer functionality if upload was successful
    viewer_ok = False
    if study_id:
        viewer_ok = test_viewer_functionality(study_id)
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"File system: {'✓ OK' if file_system_ok else '✗ FAILED'}")
    print(f"Database models: {'✓ OK' if models_ok else '✗ FAILED'}")
    print(f"Upload functionality: {'✓ OK' if study_id else '✗ FAILED'}")
    print(f"Viewer functionality: {'✓ OK' if viewer_ok else '✗ FAILED'}")
    
    if not file_system_ok:
        print("\n🔧 FIX NEEDED: File system issues detected")
    if not models_ok:
        print("\n🔧 FIX NEEDED: Database model issues detected")
    if not study_id:
        print("\n🔧 FIX NEEDED: Upload functionality issues detected")
    if not viewer_ok:
        print("\n🔧 FIX NEEDED: Viewer functionality issues detected")

if __name__ == "__main__":
    main()