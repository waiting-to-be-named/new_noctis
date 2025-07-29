import os
import sys
import time
import threading
from datetime import datetime
from pydicom.dataset import Dataset
from pynetdicom import (
    AE, evt, AllowedPresentationContexts, debug_logger
)
from pynetdicom.sop_class import (
    VerificationSOPClass, CTImageStorage, MRImageStorage,
    CRImageStorage, DXImageStorage, USImageStorage,
    SecondaryCaptureImageStorage, ComputedRadiographyImageStorage
)
from pynetdicom.pdu_primitives import A_ASSOCIATE_RQ
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.utils import timezone
from .models import DicomServerConfig, FacilityAETitle, DicomTransferLog
from viewer.models import DicomStudy, DicomSeries, DicomImage, Facility
import pydicom


class NoctisDicomServer:
    """DICOM SCP/SCU server for Noctis"""
    
    def __init__(self):
        self.ae = None
        self.server = None
        self.is_running = False
        self.config = None
        self.load_config()
    
    def load_config(self):
        """Load server configuration from database"""
        self.config = DicomServerConfig.objects.filter(is_active=True).first()
        if not self.config:
            self.config = DicomServerConfig.objects.create(
                name='Noctis DICOM Server',
                ae_title='NOCTIS',
                port=11112,
                max_pdu_length=65536
            )
    
    def start_server(self):
        """Start the DICOM server"""
        if self.is_running:
            return False
        
        try:
            # Initialize the Application Entity
            self.ae = AE(ae_title=self.config.ae_title)
            
            # Add supported presentation contexts
            self.ae.add_supported_context(VerificationSOPClass)
            self.ae.add_supported_context(CTImageStorage)
            self.ae.add_supported_context(MRImageStorage)
            self.ae.add_supported_context(CRImageStorage)
            self.ae.add_supported_context(DXImageStorage)
            self.ae.add_supported_context(USImageStorage)
            self.ae.add_supported_context(SecondaryCaptureImageStorage)
            self.ae.add_supported_context(ComputedRadiographyImageStorage)
            
            # Start listening for incoming association requests
            self.server = self.ae.start_server(
                ('0.0.0.0', self.config.port),
                block=False,
                evt_handlers=[
                    (evt.EVT_C_STORE, self.handle_c_store),
                    (evt.EVT_C_ECHO, self.handle_c_echo),
                    (evt.EVT_C_FIND, self.handle_c_find),
                    (evt.EVT_C_MOVE, self.handle_c_move),
                    (evt.EVT_ACCEPTED, self.handle_accepted),
                    (evt.EVT_REJECTED, self.handle_rejected),
                    (evt.EVT_ABORTED, self.handle_aborted),
                ]
            )
            
            self.is_running = True
            print(f"DICOM server started on port {self.config.port}")
            return True
            
        except Exception as e:
            print(f"Error starting DICOM server: {e}")
            return False
    
    def stop_server(self):
        """Stop the DICOM server"""
        if self.server:
            self.server.shutdown()
            self.is_running = False
            print("DICOM server stopped")
    
    def handle_c_store(self, event):
        """Handle C-STORE requests"""
        start_time = time.time()
        
        try:
            # Get the C-STORE request dataset
            ds = event.dataset
            
            # Extract patient information
            patient_name = str(ds.get('PatientName', 'Unknown'))
            patient_id = str(ds.get('PatientID', 'Unknown'))
            study_instance_uid = str(ds.get('StudyInstanceUID', ''))
            series_instance_uid = str(ds.get('SeriesInstanceUID', ''))
            sop_instance_uid = str(ds.get('SOPInstanceUID', ''))
            
            # Create transfer log entry
            transfer_log = DicomTransferLog.objects.create(
                transfer_type='C_STORE',
                calling_ae_title=event.assoc.requesting_ae_title,
                called_ae_title=event.assoc.accepted_ae_title,
                study_instance_uid=study_instance_uid,
                patient_name=patient_name,
                patient_id=patient_id,
                status='IN_PROGRESS'
            )
            
            # Save DICOM file
            file_path = self.save_dicom_file(ds, patient_id, study_instance_uid, series_instance_uid, sop_instance_uid)
            
            # Update database
            self.update_database(ds, file_path)
            
            # Update transfer log
            transfer_log.status = 'SUCCESS'
            transfer_log.bytes_transferred = len(ds)
            transfer_log.transfer_time = time.time() - start_time
            transfer_log.save()
            
            # Return success
            return 0x0000  # Success
            
        except Exception as e:
            # Log error
            if 'transfer_log' in locals():
                transfer_log.status = 'FAILED'
                transfer_log.error_message = str(e)
                transfer_log.transfer_time = time.time() - start_time
                transfer_log.save()
            
            print(f"Error handling C-STORE: {e}")
            return 0x0110  # Processing failure
    
    def save_dicom_file(self, ds, patient_id, study_instance_uid, series_instance_uid, sop_instance_uid):
        """Save DICOM file to disk"""
        # Create directory structure
        base_dir = 'dicom_files'
        study_dir = os.path.join(base_dir, patient_id, study_instance_uid)
        series_dir = os.path.join(study_dir, series_instance_uid)
        
        os.makedirs(series_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(series_dir, f"{sop_instance_uid}.dcm")
        ds.save_as(file_path, write_like_original=False)
        
        return file_path
    
    def update_database(self, ds, file_path):
        """Update database with DICOM information"""
        try:
            # Extract DICOM attributes
            patient_name = str(ds.get('PatientName', 'Unknown'))
            patient_id = str(ds.get('PatientID', 'Unknown'))
            study_instance_uid = str(ds.get('StudyInstanceUID', ''))
            series_instance_uid = str(ds.get('SeriesInstanceUID', ''))
            sop_instance_uid = str(ds.get('SOPInstanceUID', ''))
            study_date = ds.get('StudyDate', '')
            study_time = ds.get('StudyTime', '')
            modality = str(ds.get('Modality', 'Unknown'))
            study_description = str(ds.get('StudyDescription', ''))
            series_description = str(ds.get('SeriesDescription', ''))
            
            # Get or create facility (try to match by AE title)
            facility = None
            calling_ae = ds.get('SourceApplicationEntityTitle', '')
            if calling_ae:
                ae_title_obj = FacilityAETitle.objects.filter(
                    ae_title=calling_ae, is_active=True
                ).first()
                if ae_title_obj:
                    facility = ae_title_obj.facility
            
            # Get or create study
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_instance_uid,
                defaults={
                    'patient_name': patient_name,
                    'patient_id': patient_id,
                    'study_date': study_date,
                    'study_time': study_time,
                    'modality': modality,
                    'study_description': study_description,
                    'facility': facility
                }
            )
            
            # Get or create series
            series, created = DicomSeries.objects.get_or_create(
                series_instance_uid=series_instance_uid,
                study=study,
                defaults={
                    'series_description': series_description,
                    'modality': modality
                }
            )
            
            # Create image record
            DicomImage.objects.get_or_create(
                sop_instance_uid=sop_instance_uid,
                series=series,
                defaults={
                    'file_path': file_path,
                    'image_number': ds.get('InstanceNumber', 1)
                }
            )
            
        except Exception as e:
            print(f"Error updating database: {e}")
    
    def handle_c_echo(self, event):
        """Handle C-ECHO requests"""
        try:
            # Log the echo request
            DicomTransferLog.objects.create(
                transfer_type='C_ECHO',
                calling_ae_title=event.assoc.requesting_ae_title,
                called_ae_title=event.assoc.accepted_ae_title,
                status='SUCCESS',
                transfer_time=0.0
            )
            
            return 0x0000  # Success
        except Exception as e:
            print(f"Error handling C-ECHO: {e}")
            return 0x0110  # Processing failure
    
    def handle_c_find(self, event):
        """Handle C-FIND requests"""
        try:
            # Log the find request
            DicomTransferLog.objects.create(
                transfer_type='C_FIND',
                calling_ae_title=event.assoc.requesting_ae_title,
                called_ae_title=event.assoc.accepted_ae_title,
                status='SUCCESS',
                transfer_time=0.0
            )
            
            # Return empty dataset for now (can be enhanced later)
            return []
        except Exception as e:
            print(f"Error handling C-FIND: {e}")
            return []
    
    def handle_c_move(self, event):
        """Handle C-MOVE requests"""
        try:
            # Log the move request
            DicomTransferLog.objects.create(
                transfer_type='C_MOVE',
                calling_ae_title=event.assoc.requesting_ae_title,
                called_ae_title=event.assoc.accepted_ae_title,
                status='SUCCESS',
                transfer_time=0.0
            )
            
            return 0x0000  # Success
        except Exception as e:
            print(f"Error handling C-MOVE: {e}")
            return 0x0110  # Processing failure
    
    def handle_accepted(self, event):
        """Handle accepted association"""
        print(f"Association accepted from {event.assoc.requesting_ae_title}")
    
    def handle_rejected(self, event):
        """Handle rejected association"""
        print(f"Association rejected from {event.assoc.requesting_ae_title}")
    
    def handle_aborted(self, event):
        """Handle aborted association"""
        print(f"Association aborted from {event.assoc.requesting_ae_title}")


def start_dicom_server():
    """Start the DICOM server in a separate thread"""
    server = NoctisDicomServer()
    if server.start_server():
        return server
    return None


if __name__ == '__main__':
    # Enable debug logging
    debug_logger()
    
    # Start server
    server = start_dicom_server()
    
    if server:
        try:
            # Keep the server running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop_server()
    else:
        print("Failed to start DICOM server")