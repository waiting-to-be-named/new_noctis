#!/usr/bin/env python3
"""
Simple test to verify core DICOM functionality works.
"""

import os
import sys
from io import BytesIO

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')

import django
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage, Facility
import pydicom
from pydicom.dataset import Dataset, FileDataset
import numpy as np
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import uuid

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

def test_model_functionality():
    """Test the core model functionality"""
    print("Testing DICOM model functionality...")
    
    try:
        # Clean up any existing test data
        DicomImage.objects.all().delete()
        DicomSeries.objects.all().delete()
        DicomStudy.objects.all().delete()
        
        # Create test DICOM file
        dicom_data = create_test_dicom()
        if not dicom_data:
            print("❌ Failed to create test DICOM file")
            return False
        
        # Parse DICOM data
        dicom_ds = pydicom.dcmread(BytesIO(dicom_data))
        print(f"✅ DICOM file created and parsed successfully")
        
        # Save DICOM file to storage
        unique_filename = f"{uuid.uuid4()}_test.dcm"
        file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(dicom_data))
        print(f"✅ DICOM file saved to: {file_path}")
        
        # Create facility
        facility, _ = Facility.objects.get_or_create(
            name="Test Facility",
            defaults={
                'address': 'Test Address',
                'phone': '555-1234',
                'email': 'test@facility.com'
            }
        )
        print(f"✅ Facility created: {facility.name}")
        
        # Create study
        study = DicomStudy.objects.create(
            study_instance_uid=str(dicom_ds.StudyInstanceUID),
            patient_name=str(dicom_ds.PatientName),
            patient_id=str(dicom_ds.PatientID),
            study_description=str(dicom_ds.StudyDescription),
            modality=str(dicom_ds.Modality),
            institution_name=str(dicom_ds.InstitutionName),
            facility=facility
        )
        print(f"✅ Study created: {study.patient_name} - {study.study_description}")
        
        # Create series
        series = DicomSeries.objects.create(
            study=study,
            series_instance_uid=str(dicom_ds.SeriesInstanceUID),
            series_number=int(dicom_ds.SeriesNumber),
            series_description=str(dicom_ds.SeriesDescription),
            modality=str(dicom_ds.Modality)
        )
        print(f"✅ Series created: {series.series_description}")
        
        # Create image
        pixel_spacing_x, pixel_spacing_y = None, None
        if hasattr(dicom_ds, 'PixelSpacing') and len(dicom_ds.PixelSpacing) >= 2:
            pixel_spacing_x = float(dicom_ds.PixelSpacing[0])
            pixel_spacing_y = float(dicom_ds.PixelSpacing[1])
        
        window_center = float(dicom_ds.WindowCenter) if hasattr(dicom_ds, 'WindowCenter') else None
        window_width = float(dicom_ds.WindowWidth) if hasattr(dicom_ds, 'WindowWidth') else None
        
        image = DicomImage.objects.create(
            series=series,
            sop_instance_uid=str(dicom_ds.SOPInstanceUID),
            instance_number=int(dicom_ds.InstanceNumber),
            file_path=file_path,
            rows=int(dicom_ds.Rows),
            columns=int(dicom_ds.Columns),
            bits_allocated=int(dicom_ds.BitsAllocated),
            samples_per_pixel=int(dicom_ds.SamplesPerPixel),
            photometric_interpretation=str(dicom_ds.PhotometricInterpretation),
            pixel_spacing_x=pixel_spacing_x,
            pixel_spacing_y=pixel_spacing_y,
            slice_thickness=float(dicom_ds.SliceThickness),
            window_center=window_center,
            window_width=window_width
        )
        print(f"✅ Image created: {image.instance_number} ({image.rows}x{image.columns})")
        
        # Test image loading
        loaded_dicom = image.load_dicom_data()
        if loaded_dicom:
            print("✅ DICOM data loaded successfully from storage")
        else:
            print("❌ Failed to load DICOM data from storage")
            return False
        
        # Test pixel array extraction
        pixel_array = image.get_pixel_array()
        if pixel_array is not None:
            print(f"✅ Pixel array extracted: shape {pixel_array.shape}")
        else:
            print("❌ Failed to extract pixel array")
            return False
        
        # Test image processing
        image_base64 = image.get_processed_image_base64()
        if image_base64:
            print("✅ Image processed to base64 successfully")
            print(f"   Base64 data length: {len(image_base64)} characters")
        else:
            print("❌ Failed to process image to base64")
            return False
        
        print("\n🎉 All core functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    print("🔧 Testing Core DICOM Functionality")
    print("=" * 40)
    
    # Ensure media directory exists
    os.makedirs("media/dicom_files", exist_ok=True)
    
    success = test_model_functionality()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed! The DICOM core functionality is working correctly.")
        print("\nThis means:")
        print("- DICOM files can be created and parsed")
        print("- DICOM data can be saved to storage")
        print("- Database models work correctly")
        print("- DICOM files can be loaded from storage") 
        print("- Pixel arrays can be extracted")
        print("- Images can be processed and converted to base64")
    else:
        print("❌ Some tests failed. Check the error messages above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)