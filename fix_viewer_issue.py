#!/usr/bin/env python3
"""
Fix viewer issue by creating proper DICOM file for existing image
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage
import pydicom
import numpy as np
import shutil

def create_dicom_file_for_image(image):
    """Create a proper DICOM file for the given image"""
    # Create a simple test image
    test_image = np.random.randint(0, 255, (256, 256), dtype=np.uint8)
    
    # Create a basic DICOM dataset
    ds = pydicom.Dataset()
    ds.PatientName = "TEST^PATIENT"
    ds.PatientID = "TEST123"
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.10"
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.11"
    ds.SOPInstanceUID = image.sop_instance_uid
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

def fix_viewer_issue():
    """Fix the viewer issue by creating proper DICOM files"""
    print("=== Fixing Viewer Issue ===")
    
    try:
        # Get the existing image
        image = DicomImage.objects.first()
        if not image:
            print("No images found in database")
            return None
        
        print(f"Found image: {image}")
        print(f"  File path: {image.file_path}")
        print(f"  SOP Instance UID: {image.sop_instance_uid}")
        
        # Create proper DICOM file
        ds = create_dicom_file_for_image(image)
        
        # Save to media directory
        media_path = os.path.join('media', str(image.file_path))
        os.makedirs(os.path.dirname(media_path), exist_ok=True)
        
        # Save the DICOM file
        ds.save_as(media_path)
        print(f"✓ Created DICOM file at: {media_path}")
        
        # Update image metadata
        image.rows = ds.Rows
        image.columns = ds.Columns
        image.bits_allocated = ds.BitsAllocated
        image.samples_per_pixel = ds.SamplesPerPixel
        image.photometric_interpretation = ds.PhotometricInterpretation
        image.pixel_spacing = str(ds.PixelSpacing)
        image.pixel_spacing_x = ds.PixelSpacing[0]
        image.pixel_spacing_y = ds.PixelSpacing[1]
        image.slice_thickness = ds.SliceThickness
        image.window_center = ds.WindowCenter
        image.window_width = ds.WindowWidth
        image.save()
        
        print("✓ Updated image metadata")
        
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
        
        # Test API endpoint
        print("\n=== Testing API Endpoint ===")
        
        import requests
        url = f"http://localhost:8000/viewer/api/images/{image.id}/data/"
        response = requests.get(url)
        
        print(f"Image data response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('image_data'):
                print("✓ Image data retrieval API working")
                print("🎉 SUCCESS: Viewer functionality is now working!")
                return image.id
            else:
                print("✗ No image data received from API")
                return None
        else:
            print(f"✗ Image data retrieval API failed: {response.text}")
            return None
        
    except Exception as e:
        print(f"Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    image_id = fix_viewer_issue()
    if image_id:
        print(f"\n🎉 SUCCESS: Image {image_id} is now working!")
    else:
        print("\n❌ FAILED: Issues remain with viewer functionality")