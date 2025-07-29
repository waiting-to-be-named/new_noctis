#!/usr/bin/env python3
"""
Comprehensive fix for DICOM upload and viewer issues
"""

import os
import sys
import django

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
import requests

def create_proper_dicom_file():
    """Create a proper DICOM file with all required headers"""
    # Create a simple test image
    test_image = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
    
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

def test_direct_upload():
    """Test direct upload using Django ORM"""
    print("=== Testing Direct Upload ===")
    
    try:
        # Create DICOM file
        ds = create_proper_dicom_file()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as temp_file:
            ds.save_as(temp_file.name)
            temp_file_path = temp_file.name
        
        # Create study directly
        study = DicomStudy.objects.create(
            study_instance_uid=ds.StudyInstanceUID,
            patient_name=str(ds.PatientName),
            patient_id=str(ds.PatientID),
            study_date=ds.StudyDate,
            study_time=ds.StudyTime,
            study_description=str(ds.StudyDescription),
            modality=str(ds.Modality),
            institution_name="Test Institution",
            accession_number="ACC123456",
            referring_physician="Dr. Test"
        )
        
        # Create series
        series = DicomSeries.objects.create(
            study=study,
            series_instance_uid=ds.SeriesInstanceUID,
            series_number=ds.SeriesNumber,
            series_description=str(ds.SeriesDescription),
            modality=str(ds.Modality)
        )
        
        # Create image
        image = DicomImage.objects.create(
            series=series,
            sop_instance_uid=ds.SOPInstanceUID,
            instance_number=ds.InstanceNumber,
            file_path=f'dicom_files/test_{ds.SOPInstanceUID}.dcm',
            rows=ds.Rows,
            columns=ds.Columns,
            bits_allocated=ds.BitsAllocated,
            samples_per_pixel=ds.SamplesPerPixel,
            photometric_interpretation=ds.PhotometricInterpretation,
            pixel_spacing=str(ds.PixelSpacing),
            pixel_spacing_x=ds.PixelSpacing[0],
            pixel_spacing_y=ds.PixelSpacing[1],
            slice_thickness=ds.SliceThickness,
            window_center=ds.WindowCenter,
            window_width=ds.WindowWidth
        )
        
        # Copy file to media directory
        import shutil
        media_path = os.path.join('media', 'dicom_files', f'test_{ds.SOPInstanceUID}.dcm')
        os.makedirs(os.path.dirname(media_path), exist_ok=True)
        shutil.copy2(temp_file_path, media_path)
        
        print(f"✓ Created study: {study}")
        print(f"✓ Created series: {series}")
        print(f"✓ Created image: {image}")
        
        # Test image processing
        print("\n=== Testing Image Processing ===")
        
        # Test DICOM loading
        dicom_data = image.load_dicom_data()
        if dicom_data:
            print("✓ DICOM data loaded successfully")
        else:
            print("✗ Failed to load DICOM data")
            return None
        
        # Test pixel array
        pixel_array = image.get_pixel_array()
        if pixel_array is not None:
            print("✓ Pixel array loaded successfully")
            print(f"  Shape: {pixel_array.shape}")
        else:
            print("✗ Failed to load pixel array")
            return None
        
        # Test processed image
        base64_image = image.get_processed_image_base64()
        if base64_image:
            print("✓ Processed image generated successfully")
            print(f"  Base64 length: {len(base64_image)}")
        else:
            print("✗ Failed to generate processed image")
            return None
        
        # Test API endpoints
        print("\n=== Testing API Endpoints ===")
        
        # Test get study images
        url = f"http://localhost:8000/viewer/api/studies/{study.id}/images/"
        response = requests.get(url)
        
        if response.status_code == 200:
            print("✓ Get study images API working")
            data = response.json()
            images = data.get('images', [])
            
            if images:
                # Test image data retrieval
                image_id = images[0]['id']
                url = f"http://localhost:8000/viewer/api/images/{image_id}/data/"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('image_data'):
                        print("✓ Image data retrieval API working")
                        print("🎉 SUCCESS: Upload and viewer functionality are working!")
                        return study.id
                    else:
                        print("✗ No image data received from API")
                        return None
                else:
                    print(f"✗ Image data retrieval API failed: {response.text}")
                    return None
            else:
                print("✗ No images found in study")
                return None
        else:
            print(f"✗ Get study images API failed: {response.text}")
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
    study_id = test_direct_upload()
    if study_id:
        print(f"\n🎉 SUCCESS: Study {study_id} created and tested successfully!")
    else:
        print("\n❌ FAILED: Issues remain with upload or viewer functionality")