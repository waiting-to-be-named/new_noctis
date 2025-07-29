#!/usr/bin/env python3
"""
Fix upload issue by improving DICOM file creation and upload process
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

import pydicom
import numpy as np
import tempfile
import requests

def create_uploadable_dicom():
    """Create a DICOM file that can be uploaded successfully"""
    # Create a simple test image
    test_image = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
    
    # Create a basic DICOM dataset
    ds = pydicom.Dataset()
    ds.PatientName = "UPLOAD^TEST"
    ds.PatientID = "UPLOAD123"
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.20"  # Different UID
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.21"  # Different UID
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.22"     # Different UID
    ds.Modality = "CT"
    ds.StudyDate = "20240101"
    ds.StudyTime = "120000"
    ds.StudyDescription = "Upload Test Study"
    ds.SeriesDescription = "Upload Test Series"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.Rows = 128
    ds.Columns = 128
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

def test_upload_with_proper_dicom():
    """Test upload with proper DICOM file"""
    print("=== Testing Upload with Proper DICOM ===")
    
    try:
        # Create proper DICOM file
        ds = create_uploadable_dicom()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as temp_file:
            ds.save_as(temp_file.name)
            temp_file_path = temp_file.name
        
        print(f"Created DICOM file: {temp_file_path}")
        print(f"File size: {os.path.getsize(temp_file_path)} bytes")
        
        # Test file upload via API
        url = "http://localhost:8000/viewer/api/upload/"
        
        with open(temp_file_path, 'rb') as f:
            files = {'files': f}
            response = requests.post(url, files=files)
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Upload successful: {data}")
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
                            print("🎉 SUCCESS: Upload and viewer functionality are working!")
                            return study_id
                        else:
                            print("✗ No image data received")
                            return None
                    else:
                        print(f"✗ Image data retrieval failed: {response.text}")
                        return None
                else:
                    print("✗ No images found in study")
                    return None
            else:
                print(f"✗ Failed to get study images: {response.text}")
                return None
        else:
            print(f"✗ Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temporary file
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)

if __name__ == "__main__":
    study_id = test_upload_with_proper_dicom()
    if study_id:
        print(f"\n🎉 SUCCESS: Upload and viewer functionality are working! Study ID: {study_id}")
    else:
        print("\n❌ FAILED: Issues remain with upload functionality")