#!/usr/bin/env python3
"""
DICOM SCP (Storage Class Provider) Server
Receives DICOM images from remote facilities with auto-generated AE titles and ports
"""

import os
import sys
import django
import logging
import hashlib
from datetime import datetime
from pynetdicom import AE, evt, StoragePresentationContexts, debug_logger
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind
from pydicom.dataset import Dataset
from pydicom import dcmread
from pathlib import Path

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage, Facility
from django.contrib.auth.models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('dicom_server')

# Debug mode for pynetdicom
debug_logger()

class DicomServer:
    def __init__(self, ae_title='NOCTIS_SCP', port=11112):
        self.ae_title = ae_title
        self.port = port
        self.ae = AE(ae_title=ae_title)
        
        # Support all standard Storage SOP Classes
        self.ae.supported_contexts = StoragePresentationContexts
        
        # Add Query/Retrieve support
        self.ae.add_supported_context(StudyRootQueryRetrieveInformationModelFind)
        
        # Set up handlers
        handlers = [
            (evt.EVT_C_STORE, self.handle_store),
            (evt.EVT_C_ECHO, self.handle_echo),
            (evt.EVT_ACCEPTED, self.handle_accepted),
            (evt.EVT_RELEASED, self.handle_released),
        ]
        
        # Register handlers
        for event, handler in handlers:
            self.ae.add_event_handler(event, handler)
        
        # Storage directory
        self.storage_path = Path('dicom_storage')
        self.storage_path.mkdir(exist_ok=True)
        
        # Facility AE title mapping (auto-generated based on facility name)
        self.facility_ae_mapping = {}
        self.update_facility_mappings()
        
    def update_facility_mappings(self):
        """Update facility AE title mappings from database"""
        try:
            facilities = Facility.objects.all()
            for facility in facilities:
                # Generate AE title from facility name (max 16 chars, uppercase)
                ae_title = self.generate_ae_title(facility.name)
                self.facility_ae_mapping[ae_title] = facility
                logger.info(f"Registered facility: {facility.name} with AE title: {ae_title}")
        except Exception as e:
            logger.error(f"Error updating facility mappings: {e}")
    
    def generate_ae_title(self, facility_name):
        """Generate a valid AE title from facility name"""
        # Remove special characters and spaces
        clean_name = ''.join(c for c in facility_name.upper() if c.isalnum())
        # Limit to 16 characters (DICOM AE title limit)
        ae_title = clean_name[:16]
        # Pad with facility ID hash if too short
        if len(ae_title) < 4:
            hash_suffix = hashlib.md5(facility_name.encode()).hexdigest()[:4].upper()
            ae_title = f"{ae_title}{hash_suffix}"
        return ae_title
    
    def get_facility_from_ae(self, calling_ae):
        """Get facility from calling AE title"""
        # First check direct mapping
        if calling_ae in self.facility_ae_mapping:
            return self.facility_ae_mapping[calling_ae]
        
        # Try to find facility by partial match
        for ae_title, facility in self.facility_ae_mapping.items():
            if calling_ae.startswith(ae_title[:8]):  # Match first 8 chars
                return facility
        
        # If no match, create or get default facility
        default_facility, created = Facility.objects.get_or_create(
            name=f"Remote Facility ({calling_ae})",
            defaults={
                'ae_title': calling_ae,
                'ip_address': '0.0.0.0',
                'port': 11112,
                'contact_email': 'admin@remote.facility',
                'contact_phone': '000-000-0000'
            }
        )
        
        if created:
            logger.info(f"Created new facility for unknown AE: {calling_ae}")
            self.facility_ae_mapping[calling_ae] = default_facility
        
        return default_facility
    
    def handle_accepted(self, event):
        """Handle association accepted"""
        logger.info(f"Association accepted from {event.assoc.remote.ae_title} at {event.assoc.remote.address}")
    
    def handle_released(self, event):
        """Handle association released"""
        logger.info(f"Association released from {event.assoc.remote.ae_title}")
    
    def handle_echo(self, event):
        """Handle C-ECHO (verification)"""
        logger.info(f"C-ECHO received from {event.assoc.remote.ae_title}")
        return 0x0000  # Success
    
    def handle_store(self, event):
        """Handle C-STORE (storage) requests"""
        try:
            ds = event.dataset
            
            # Get facility from calling AE
            calling_ae = event.assoc.remote.ae_title
            facility = self.get_facility_from_ae(calling_ae)
            
            # Add meta information
            ds.file_meta = event.file_meta
            
            # Extract key information
            patient_id = str(getattr(ds, 'PatientID', 'UNKNOWN'))
            patient_name = str(getattr(ds, 'PatientName', 'Unknown'))
            study_uid = str(getattr(ds, 'StudyInstanceUID', ''))
            series_uid = str(getattr(ds, 'SeriesInstanceUID', ''))
            instance_uid = str(getattr(ds, 'SOPInstanceUID', ''))
            
            # Create storage path
            study_path = self.storage_path / study_uid
            series_path = study_path / series_uid
            series_path.mkdir(parents=True, exist_ok=True)
            
            # Save DICOM file
            filename = f"{instance_uid}.dcm"
            filepath = series_path / filename
            ds.save_as(filepath, write_like_original=False)
            
            logger.info(f"Stored DICOM file: {filename} from {facility.name}")
            
            # Update database
            self.update_database(ds, filepath, facility)
            
            return 0x0000  # Success
            
        except Exception as e:
            logger.error(f"Error storing DICOM: {e}")
            return 0xC001  # Error: cannot understand
    
    def update_database(self, ds, filepath, facility):
        """Update database with new DICOM data"""
        try:
            # Get or create study
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=str(ds.StudyInstanceUID),
                defaults={
                    'patient_id': str(getattr(ds, 'PatientID', 'UNKNOWN')),
                    'patient_name': str(getattr(ds, 'PatientName', 'Unknown')),
                    'patient_birth_date': getattr(ds, 'PatientBirthDate', None),
                    'patient_sex': str(getattr(ds, 'PatientSex', '')),
                    'study_date': getattr(ds, 'StudyDate', None),
                    'study_time': getattr(ds, 'StudyTime', None),
                    'study_description': str(getattr(ds, 'StudyDescription', '')),
                    'accession_number': str(getattr(ds, 'AccessionNumber', '')),
                    'referring_physician': str(getattr(ds, 'ReferringPhysicianName', '')),
                    'facility': facility,
                    'upload_status': 'completed'
                }
            )
            
            if created:
                logger.info(f"Created new study: {study.study_instance_uid}")
            
            # Get or create series
            series, created = DicomSeries.objects.get_or_create(
                series_instance_uid=str(ds.SeriesInstanceUID),
                study=study,
                defaults={
                    'series_number': int(getattr(ds, 'SeriesNumber', 0)),
                    'series_description': str(getattr(ds, 'SeriesDescription', '')),
                    'modality': str(getattr(ds, 'Modality', '')),
                    'body_part': str(getattr(ds, 'BodyPartExamined', '')),
                    'patient_position': str(getattr(ds, 'PatientPosition', '')),
                    'series_date': getattr(ds, 'SeriesDate', None),
                    'series_time': getattr(ds, 'SeriesTime', None),
                }
            )
            
            if created:
                logger.info(f"Created new series: {series.series_instance_uid}")
            
            # Create image
            image = DicomImage.objects.create(
                series=series,
                sop_instance_uid=str(ds.SOPInstanceUID),
                instance_number=int(getattr(ds, 'InstanceNumber', 0)),
                file_path=str(filepath),
                rows=int(getattr(ds, 'Rows', 0)),
                columns=int(getattr(ds, 'Columns', 0)),
                bits_allocated=int(getattr(ds, 'BitsAllocated', 0)),
                bits_stored=int(getattr(ds, 'BitsStored', 0)),
                pixel_representation=int(getattr(ds, 'PixelRepresentation', 0)),
                photometric_interpretation=str(getattr(ds, 'PhotometricInterpretation', '')),
                window_center=float(getattr(ds, 'WindowCenter', 0) if hasattr(ds, 'WindowCenter') else 0),
                window_width=float(getattr(ds, 'WindowWidth', 0) if hasattr(ds, 'WindowWidth') else 0),
            )
            
            logger.info(f"Created new image: {image.sop_instance_uid}")
            
            # Update series image count
            series.num_instances = series.images.count()
            series.save()
            
            # Update study series count
            study.num_series = study.series.count()
            study.num_instances = sum(s.num_instances for s in study.series.all())
            study.save()
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
    
    def start(self):
        """Start the DICOM server"""
        logger.info(f"Starting DICOM SCP on port {self.port} with AE title: {self.ae_title}")
        logger.info("Registered facilities:")
        for ae_title, facility in self.facility_ae_mapping.items():
            logger.info(f"  {ae_title}: {facility.name}")
        
        # Start listening
        self.ae.start_server(('0.0.0.0', self.port), block=True)


class DicomSCU:
    """DICOM SCU (Service Class User) for sending DICOM files"""
    
    def __init__(self, ae_title='NOCTIS_SCU'):
        self.ae_title = ae_title
        self.ae = AE(ae_title=ae_title)
        self.ae.requested_contexts = StoragePresentationContexts
    
    def send_dicom(self, filepath, remote_ae, remote_ip, remote_port):
        """Send a DICOM file to a remote SCP"""
        try:
            # Read DICOM file
            ds = dcmread(filepath)
            
            # Associate with remote AE
            assoc = self.ae.associate(remote_ip, remote_port, ae_title=remote_ae)
            
            if assoc.is_established:
                # Send C-STORE
                status = assoc.send_c_store(ds)
                
                # Check status
                if status:
                    logger.info(f"C-STORE status: 0x{status.Status:04X}")
                    if status.Status == 0x0000:
                        logger.info(f"Successfully sent {filepath} to {remote_ae}")
                        return True
                    else:
                        logger.error(f"Failed to send {filepath}: Status 0x{status.Status:04X}")
                        return False
                
                # Release association
                assoc.release()
            else:
                logger.error(f"Association rejected, aborted or never connected to {remote_ae}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending DICOM: {e}")
            return False
    
    def echo(self, remote_ae, remote_ip, remote_port):
        """Send C-ECHO to verify connectivity"""
        try:
            assoc = self.ae.associate(remote_ip, remote_port, ae_title=remote_ae)
            
            if assoc.is_established:
                status = assoc.send_c_echo()
                
                if status and status.Status == 0x0000:
                    logger.info(f"C-ECHO successful to {remote_ae}")
                    result = True
                else:
                    logger.error(f"C-ECHO failed to {remote_ae}")
                    result = False
                
                assoc.release()
                return result
            else:
                logger.error(f"Could not establish association with {remote_ae}")
                return False
                
        except Exception as e:
            logger.error(f"Error during C-ECHO: {e}")
            return False


def generate_facility_config():
    """Generate and display facility configuration"""
    print("\n=== Facility DICOM Configuration ===\n")
    
    facilities = Facility.objects.all()
    
    for facility in facilities:
        ae_title = DicomServer(None, None).generate_ae_title(facility.name)
        # Generate unique port based on facility ID
        port = 11112 + (facility.id % 1000)
        
        print(f"Facility: {facility.name}")
        print(f"  AE Title: {ae_title}")
        print(f"  Port: {port}")
        print(f"  Server IP: <your-server-ip>")
        print(f"  Configuration for remote PACS:")
        print(f"    - Remote AE Title: {ae_title}")
        print(f"    - Remote IP: <your-server-ip>")
        print(f"    - Remote Port: {port}")
        print()
    
    print("Note: Configure your PACS/modalities to send to these settings")
    print("The server will automatically recognize the facility by AE title\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='DICOM SCP Server')
    parser.add_argument('--port', type=int, default=11112, help='Port to listen on (default: 11112)')
    parser.add_argument('--ae-title', default='NOCTIS_SCP', help='AE Title (default: NOCTIS_SCP)')
    parser.add_argument('--config', action='store_true', help='Show facility configuration')
    
    args = parser.parse_args()
    
    if args.config:
        generate_facility_config()
    else:
        server = DicomServer(ae_title=args.ae_title, port=args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")