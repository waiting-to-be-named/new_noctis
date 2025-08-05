#!/usr/bin/env python3
"""
Enhanced DICOM SCP Server for receiving files from remote machines
"""

import os
import sys
import threading
import time
from pynetdicom import AE, evt, debug_logger
from pynetdicom.sop_class import Verification, CTImageStorage, MRImageStorage, UltrasoundImageStorage, DigitalXRayImagePresentationStorage
import pydicom
from pathlib import Path

# Setup logging
debug_logger()

class EnhancedDicomSCP:
    def __init__(self, ae_title="NOCTIS_SCP", port=11112, storage_dir="/workspace/media/dicom_files"):
        self.ae_title = ae_title
        self.port = port
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create Application Entity
        self.ae = AE(ae_title=ae_title)
        
        # Add supported presentation contexts
        self.ae.add_supported_context(Verification)
        self.ae.add_supported_context(CTImageStorage)
        self.ae.add_supported_context(MRImageStorage)
        self.ae.add_supported_context(UltrasoundImageStorage)
        self.ae.add_supported_context(DigitalXRayImagePresentationStorage)
        
        # Set event handlers
        self.ae.on_c_store = self.handle_store
        self.ae.on_c_echo = self.handle_echo
        
    def handle_store(self, event):
        """Handle incoming DICOM files from remote machines"""
        try:
            # Get the dataset
            ds = event.dataset
            
            # Generate unique filename
            import uuid
            filename = f"{uuid.uuid4()}_{ds.get('StudyInstanceUID', 'unknown')}.dcm"
            file_path = self.storage_dir / filename
            
            # Save the DICOM file
            ds.save_as(str(file_path), write_like_original=False)
            
            print(f"✅ Received and saved DICOM file: {filename}")
            
            # Auto-import to database
            self.import_to_database(str(file_path), ds)
            
            # Return success status
            return 0x0000
            
        except Exception as e:
            print(f"❌ Error storing DICOM file: {e}")
            return 0xA700  # Out of Resources
    
    def handle_echo(self, event):
        """Handle C-ECHO (verification) requests"""
        print("📡 Received C-ECHO request from remote machine")
        return 0x0000
    
    def import_to_database(self, file_path, ds):
        """Import received DICOM file to database"""
        try:
            # Setup Django
            import django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
            django.setup()
            
            from viewer.models import DicomStudy, DicomSeries, DicomImage
            from django.contrib.auth.models import User
            
            # Create or get study
            study_uid = ds.get('StudyInstanceUID', '')
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_uid,
                defaults={
                    'patient_name': str(ds.get('PatientName', 'Unknown')),
                    'patient_id': str(ds.get('PatientID', 'Unknown')),
                    'study_date': ds.get('StudyDate'),
                    'study_description': str(ds.get('StudyDescription', '')),
                    'modality': str(ds.get('Modality', 'OT')),
                    'institution_name': str(ds.get('InstitutionName', ''))
                }
            )
            
            # Create or get series
            series_uid = ds.get('SeriesInstanceUID', '')
            series, created = DicomSeries.objects.get_or_create(
                series_instance_uid=series_uid,
                study=study,
                defaults={
                    'series_number': ds.get('SeriesNumber', 1),
                    'series_description': str(ds.get('SeriesDescription', '')),
                    'modality': str(ds.get('Modality', 'OT')),
                    'body_part_examined': str(ds.get('BodyPartExamined', ''))
                }
            )
            
            # Create image
            relative_path = f"dicom_files/{os.path.basename(file_path)}"
            image = DicomImage.objects.create(
                series=series,
                sop_instance_uid=str(ds.get('SOPInstanceUID', '')),
                instance_number=ds.get('InstanceNumber', 1),
                file_path=relative_path,
                rows=ds.get('Rows'),
                columns=ds.get('Columns'),
                window_width=ds.get('WindowWidth'),
                window_center=ds.get('WindowCenter')
            )
            
            print(f"✅ Imported DICOM file to database: Study {study.id}, Image {image.id}")
            
        except Exception as e:
            print(f"❌ Error importing to database: {e}")
    
    def start_server(self):
        """Start the DICOM SCP server"""
        print(f"🚀 Starting DICOM SCP server on port {self.port}...")
        print(f"   AE Title: {self.ae_title}")
        print(f"   Storage Directory: {self.storage_dir}")
        
        try:
            self.ae.start_server(('0.0.0.0', self.port), block=True)
        except Exception as e:
            print(f"❌ Error starting DICOM server: {e}")

if __name__ == "__main__":
    # Start the enhanced DICOM SCP server
    server = EnhancedDicomSCP()
    server.start_server()
