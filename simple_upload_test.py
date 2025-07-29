#!/usr/bin/env python3
"""
Simple upload test that works like curl
"""

import requests
import tempfile
import os
import pydicom
import numpy as np

def create_simple_dicom():
    """Create a very simple DICOM file"""
    # Create a simple test image
    test_image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
    
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
    
    return ds

def test_simple_upload():
    """Test simple upload"""
    print("=== Testing Simple Upload ===")
    
    # Create DICOM file
    ds = create_simple_dicom()
    
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
            print(f"✓ Upload successful: {data}")
            return data.get('study_id')
        else:
            print(f"✗ Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Test failed: {e}")
        return None
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

if __name__ == "__main__":
    study_id = test_simple_upload()
    if study_id:
        print(f"\n🎉 SUCCESS: Upload worked! Study ID: {study_id}")
    else:
        print("\n❌ FAILED: Upload failed")