#!/usr/bin/env python3
"""
Test script to upload proper DICOM files and test viewer functionality
"""

import os
import sys
import django
import requests
import tempfile
import pydicom
import numpy as np

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

def create_proper_dicom_file():
    """Create a proper DICOM file with correct headers"""
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

def test_new_upload():
    """Test upload with proper DICOM files"""
    print("=== Testing New Upload with Proper DICOM Files ===")
    
    # Create proper DICOM file
    ds = create_proper_dicom_file()
    
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
            study_id = data.get('study_id')
            
            # Test viewer functionality
            print(f"\n=== Testing Viewer for Study {study_id} ===")
            
            # Get study images
            url = f"http://localhost:8000/viewer/api/studies/{study_id}/images/"
            response = requests.get(url)
            
            print(f"Get images response status: {response.status_code}")
            
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
                            print("✓ Viewer functionality working!")
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
        else:
            print(f"Upload failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

if __name__ == "__main__":
    success = test_new_upload()
    if success:
        print("\n🎉 SUCCESS: Upload and viewer functionality are working!")
    else:
        print("\n❌ FAILED: Issues remain with upload or viewer functionality")