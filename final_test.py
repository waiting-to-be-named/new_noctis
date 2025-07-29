#!/usr/bin/env python3
"""
Final comprehensive test to verify all DICOM functionality is working
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
import requests
import pydicom
import numpy as np
import tempfile

def create_test_dicom():
    """Create a test DICOM file"""
    # Create a simple test image
    test_image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
    
    # Create a basic DICOM dataset
    ds = pydicom.Dataset()
    ds.PatientName = "FINAL^TEST"
    ds.PatientID = "FINAL123"
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.30"  # Unique UID
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.31"  # Unique UID
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.32"     # Unique UID
    ds.Modality = "CT"
    ds.StudyDate = "20240101"
    ds.StudyTime = "120000"
    ds.StudyDescription = "Final Test Study"
    ds.SeriesDescription = "Final Test Series"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.Rows = 64
    ds.Columns = 64
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

def test_complete_functionality():
    """Test complete DICOM functionality"""
    print("=== Final Comprehensive Test ===")
    
    # Test 1: Database Models
    print("\n1. Testing Database Models...")
    studies = DicomStudy.objects.all()
    print(f"   Total studies: {studies.count()}")
    
    for study in studies:
        print(f"   Study {study.id}: {study.patient_name} - {study.modality}")
        print(f"     Series: {study.series_count}, Images: {study.total_images}")
    
    # Test 2: Upload Functionality
    print("\n2. Testing Upload Functionality...")
    try:
        # Create test DICOM file
        ds = create_test_dicom()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as temp_file:
            ds.save_as(temp_file.name)
            temp_file_path = temp_file.name
        
        # Upload file
        url = "http://localhost:8000/viewer/api/upload/"
        
        with open(temp_file_path, 'rb') as f:
            files = {'files': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            study_id = data.get('study_id')
            print(f"   ✓ Upload successful - Study ID: {study_id}")
            
            # Test 3: Viewer Functionality
            print(f"\n3. Testing Viewer Functionality for Study {study_id}...")
            
            # Get study images
            url = f"http://localhost:8000/viewer/api/studies/{study_id}/images/"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                images = data.get('images', [])
                
                if images:
                    print(f"   ✓ Found {len(images)} images")
                    
                    # Test image data retrieval
                    image_id = images[0]['id']
                    url = f"http://localhost:8000/viewer/api/images/{image_id}/data/"
                    response = requests.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('image_data'):
                            print(f"   ✓ Image data retrieval successful")
                            print(f"   ✓ Viewer functionality working!")
                        else:
                            print(f"   ✗ No image data received")
                            return False
                    else:
                        print(f"   ✗ Image data retrieval failed: {response.text}")
                        return False
                else:
                    print(f"   ✗ No images found in study")
                    return False
            else:
                print(f"   ✗ Failed to get study images: {response.text}")
                return False
        else:
            print(f"   ✗ Upload failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed: {e}")
        return False
    finally:
        # Clean up temporary file
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
    
    # Test 4: Image Processing
    print("\n4. Testing Image Processing...")
    try:
        image = DicomImage.objects.first()
        if image:
            # Test DICOM loading
            dicom_data = image.load_dicom_data()
            if dicom_data:
                print("   ✓ DICOM data loading working")
            else:
                print("   ✗ DICOM data loading failed")
                return False
            
            # Test pixel array
            pixel_array = image.get_pixel_array()
            if pixel_array is not None:
                print(f"   ✓ Pixel array loading working - Shape: {pixel_array.shape}")
            else:
                print("   ✗ Pixel array loading failed")
                return False
            
            # Test processed image
            base64_image = image.get_processed_image_base64()
            if base64_image:
                print(f"   ✓ Processed image generation working - Length: {len(base64_image)}")
            else:
                print("   ✗ Processed image generation failed")
                return False
        else:
            print("   ✗ No images found for processing test")
            return False
    except Exception as e:
        print(f"   ✗ Image processing test failed: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED! DICOM functionality is working correctly.")
    return True

if __name__ == "__main__":
    success = test_complete_functionality()
    if success:
        print("\n✅ SUCCESS: All DICOM upload and viewer functionality is working!")
    else:
        print("\n❌ FAILED: Some issues remain with DICOM functionality")