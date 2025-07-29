#!/usr/bin/env python3
"""
Test script for the Noctis DICOM Server
This script tests the DICOM server functionality by sending test DICOM files.
"""

import os
import sys
import time
from pydicom.dataset import Dataset, FileDataset
from pynetdicom import AE
from pynetdicom.sop_class import CTImageStorage
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from dicom_server.models import DicomServerConfig, FacilityAETitle
from viewer.models import Facility


def create_test_dicom():
    """Create a test DICOM dataset"""
    # Create some test data
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9.10'
    file_meta.ImplementationClassUID = '1.2.3.4.5.6.7.8.9.10'
    
    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
    
    # Add required DICOM attributes
    ds.PatientName = "Test^Patient"
    ds.PatientID = "TEST123"
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.11"
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.12"
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.13"
    ds.StudyDate = "20240101"
    ds.StudyTime = "120000"
    ds.Modality = "CT"
    ds.StudyDescription = "Test Study"
    ds.SeriesDescription = "Test Series"
    ds.InstanceNumber = 1
    
    # Add some dummy pixel data
    ds.Rows = 256
    ds.Columns = 256
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = b"\0" * (256 * 256 * 2)  # 16-bit pixels
    
    return ds


def test_dicom_server():
    """Test the DICOM server by sending a test DICOM file"""
    print("Testing Noctis DICOM Server...")
    
    # Get server configuration
    config = DicomServerConfig.objects.filter(is_active=True).first()
    if not config:
        print("No DICOM server configuration found. Creating default config...")
        config = DicomServerConfig.objects.create(
            name='Noctis DICOM Server',
            ae_title='NOCTIS',
            port=11112,
            max_pdu_length=65536
        )
    
    print(f"Server config: {config.ae_title}:{config.port}")
    
    # Create test DICOM dataset
    ds = create_test_dicom()
    
    # Initialize the Application Entity
    ae = AE(ae_title='TEST_CLIENT')
    ae.add_requested_context(CTImageStorage)
    
    print(f"Sending test DICOM to {config.ae_title}:{config.port}...")
    
    try:
        # Associate with peer AE
        assoc = ae.associate('localhost', config.port, ae_title=config.ae_title)
        
        if assoc.is_established:
            print("Association established!")
            
            # Send the C-STORE request
            status = assoc.send_c_store(ds)
            
            if status:
                print(f"C-STORE Status: 0x{status:04x}")
                if status == 0x0000:
                    print("C-STORE successful!")
                else:
                    print("C-STORE failed!")
            else:
                print("C-STORE failed - no status returned")
            
            # Release the association
            assoc.release()
        else:
            print("Association rejected, aborted or never connected")
            
    except Exception as e:
        print(f"Error during DICOM transfer: {e}")
    
    print("Test completed.")


def test_facility_ae_generation():
    """Test facility AE title generation"""
    print("\nTesting Facility AE Title Generation...")
    
    # Get or create a test facility
    facility, created = Facility.objects.get_or_create(
        name='Test Hospital',
        defaults={
            'address': '123 Test Street',
            'phone': '555-0123',
            'email': 'test@hospital.com'
        }
    )
    
    if created:
        print(f"Created test facility: {facility.name}")
    else:
        print(f"Using existing facility: {facility.name}")
    
    # Generate AE title for the facility
    try:
        ae_title = FacilityAETitle.generate_ae_title(facility)
        print(f"Generated AE title: {ae_title.ae_title}:{ae_title.port}")
        print(f"For facility: {ae_title.facility.name}")
    except Exception as e:
        print(f"Error generating AE title: {e}")


if __name__ == '__main__':
    print("Noctis DICOM Server Test")
    print("=" * 40)
    
    # Test facility AE generation
    test_facility_ae_generation()
    
    # Test DICOM server
    test_dicom_server()
    
    print("\nTest completed!")