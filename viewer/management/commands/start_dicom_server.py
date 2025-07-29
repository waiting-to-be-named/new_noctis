"""
Django management command to start DICOM SCP server
"""
import os
import logging
import threading
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from pynetdicom import AE, evt, debug_logger
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind
from pydicom.dataset import Dataset
from viewer.models import Facility, DicomStudy, DicomSeries, DicomImage
from django.contrib.auth.models import User
import pydicom
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DicomSCPServer:
    def __init__(self):
        self.ae = AE(ae_title='NOCTIS_SERVER')
        self.setup_scp()
        
    def setup_scp(self):
        """Setup the SCP with supported contexts"""
        # Add supported presentation contexts
        from pynetdicom.sop_class import (
            CTImageStorage,
            MRImageStorage,
            XRayAngiographicImageStorage,
            DigitalXRayImageStorageForPresentation,
            DigitalXRayImageStorageForProcessing,
            ComputedRadiographyImageStorage,
            UltrasoundImageStorage,
            UltrasoundMultiframeImageStorage,
            SecondaryCaptureImageStorage,
        )
        
        # Storage presentation contexts
        storage_contexts = [
            CTImageStorage,
            MRImageStorage,
            XRayAngiographicImageStorage,
            DigitalXRayImageStorageForPresentation,
            DigitalXRayImageStorageForProcessing,
            ComputedRadiographyImageStorage,
            UltrasoundImageStorage,
            UltrasoundMultiframeImageStorage,
            SecondaryCaptureImageStorage,
        ]
        
        for context in storage_contexts:
            self.ae.add_supported_context(context)
            
        # Query/Retrieve presentation contexts
        self.ae.add_supported_context(PatientRootQueryRetrieveInformationModelFind)
        self.ae.add_supported_context(PatientRootQueryRetrieveInformationModelMove)
        self.ae.add_supported_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_supported_context(StudyRootQueryRetrieveInformationModelMove)
        self.ae.add_supported_context(Verification)
        
        # Bind event handlers
        self.ae.on_c_store = self.handle_store
        self.ae.on_c_echo = self.handle_echo
        self.ae.on_c_find = self.handle_find
        
    def handle_echo(self, event):
        """Handle C-ECHO requests (verification)"""
        logger.info(f"Received C-ECHO from {event.assoc.requestor.ae_title}")
        return 0x0000  # Success
        
    def handle_find(self, event):
        """Handle C-FIND requests (query)"""
        logger.info(f"Received C-FIND from {event.assoc.requestor.ae_title}")
        
        # For now, return empty response - could implement study/patient search later
        yield 0xFF00, None  # Pending with no data
        
    def handle_store(self, event):
        """Handle C-STORE requests (receive DICOM files)"""
        try:
            dataset = event.dataset
            calling_ae = event.assoc.requestor.ae_title
            
            logger.info(f"Received C-STORE from {calling_ae}")
            logger.info(f"Study UID: {dataset.get('StudyInstanceUID', 'Unknown')}")
            logger.info(f"Patient: {dataset.get('PatientName', 'Unknown')}")
            
            # Find facility by AE title
            try:
                facility = Facility.objects.get(ae_title=calling_ae)
                logger.info(f"Matched facility: {facility.name}")
            except Facility.DoesNotExist:
                logger.warning(f"No facility found for AE title: {calling_ae}")
                # Still process the image but without facility association
                facility = None
            
            # Save the DICOM file and create database records
            success = self.save_dicom_file(dataset, facility)
            
            if success:
                logger.info("Successfully stored DICOM image")
                return 0x0000  # Success
            else:
                logger.error("Failed to store DICOM image")
                return 0xA700  # Out of resources
                
        except Exception as e:
            logger.error(f"Error handling C-STORE: {str(e)}")
            return 0xA700  # Out of resources
    
    def save_dicom_file(self, dataset, facility=None):
        """Save DICOM file and create database records"""
        try:
            # Create media directory if it doesn't exist
            media_root = Path(settings.MEDIA_ROOT)
            dicom_dir = media_root / 'dicom_files'
            dicom_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename based on SOP Instance UID
            sop_instance_uid = dataset.get('SOPInstanceUID', 'unknown')
            filename = f"{sop_instance_uid}.dcm"
            file_path = dicom_dir / filename
            
            # Save DICOM file
            dataset.save_as(str(file_path), write_like_original=False)
            
            # Create or get study
            study_uid = dataset.get('StudyInstanceUID')
            if not study_uid:
                logger.error("No StudyInstanceUID found in dataset")
                return False
                
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_uid,
                defaults={
                    'patient_name': str(dataset.get('PatientName', 'Unknown')),
                    'patient_id': str(dataset.get('PatientID', 'Unknown')),
                    'study_date': self.parse_dicom_date(dataset.get('StudyDate')),
                    'study_time': self.parse_dicom_time(dataset.get('StudyTime')),
                    'study_description': str(dataset.get('StudyDescription', '')),
                    'modality': str(dataset.get('Modality', 'OT')),
                    'institution_name': str(dataset.get('InstitutionName', '')),
                    'accession_number': str(dataset.get('AccessionNumber', '')),
                    'referring_physician': str(dataset.get('ReferringPhysicianName', '')),
                    'facility': facility
                }
            )
            
            if created:
                logger.info(f"Created new study: {study_uid}")
            
            # Create or get series
            series_uid = dataset.get('SeriesInstanceUID')
            if not series_uid:
                logger.error("No SeriesInstanceUID found in dataset")
                return False
                
            series, created = DicomSeries.objects.get_or_create(
                series_instance_uid=series_uid,
                study=study,
                defaults={
                    'series_number': dataset.get('SeriesNumber', 1),
                    'series_description': str(dataset.get('SeriesDescription', '')),
                    'modality': str(dataset.get('Modality', 'OT')),
                    'body_part_examined': str(dataset.get('BodyPartExamined', '')),
                    'slice_thickness': self.parse_decimal_string(dataset.get('SliceThickness')),
                    'image_orientation_patient': str(dataset.get('ImageOrientationPatient', '')),
                    'image_position_patient': str(dataset.get('ImagePositionPatient', ''))
                }
            )
            
            if created:
                logger.info(f"Created new series: {series_uid}")
            
            # Create image record
            image = DicomImage.objects.create(
                sop_instance_uid=sop_instance_uid,
                series=series,
                instance_number=dataset.get('InstanceNumber', 1),
                file_path=f'dicom_files/{filename}',
                window_center=self.parse_decimal_string(dataset.get('WindowCenter')),
                window_width=self.parse_decimal_string(dataset.get('WindowWidth')),
                rows=dataset.get('Rows', 512),
                columns=dataset.get('Columns', 512),
                pixel_spacing=str(dataset.get('PixelSpacing', '')),
                slice_location=self.parse_decimal_string(dataset.get('SliceLocation'))
            )
            
            logger.info(f"Created new image: {sop_instance_uid}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving DICOM file: {str(e)}")
            return False
    
    def parse_dicom_date(self, date_str):
        """Parse DICOM date string to Python date"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(str(date_str), '%Y%m%d').date()
        except:
            return None
    
    def parse_dicom_time(self, time_str):
        """Parse DICOM time string to Python time"""
        if not time_str:
            return None
        try:
            from datetime import datetime
            # Handle different time formats
            time_str = str(time_str)
            if '.' in time_str:
                time_str = time_str.split('.')[0]  # Remove fractional seconds
            if len(time_str) == 6:
                return datetime.strptime(time_str, '%H%M%S').time()
            elif len(time_str) == 4:
                return datetime.strptime(time_str, '%H%M').time()
            elif len(time_str) == 2:
                return datetime.strptime(time_str, '%H').time()
        except:
            pass
        return None
    
    def parse_decimal_string(self, value):
        """Parse DICOM decimal string to float"""
        if not value:
            return None
        try:
            if isinstance(value, (list, tuple)) and len(value) > 0:
                return float(value[0])
            return float(value)
        except:
            return None
    
    def start_server(self, port=11112):
        """Start the DICOM SCP server"""
        logger.info(f"Starting DICOM SCP server on port {port}")
        logger.info(f"AE Title: {self.ae.ae_title}")
        
        # Start the server
        self.ae.start_server(('', port), block=True)

class Command(BaseCommand):
    help = 'Start DICOM SCP server to receive images from remote facilities'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=11112,
            help='Port to listen on (default: 11112)'
        )
        parser.add_argument(
            '--ae-title',
            type=str,
            default='NOCTIS_SERVER',
            help='AE Title for the server (default: NOCTIS_SERVER)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )
    
    def handle(self, *args, **options):
        if options['debug']:
            debug_logger()
            logging.getLogger().setLevel(logging.DEBUG)
        
        port = options['port']
        ae_title = options['ae_title']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting DICOM SCP server...')
        )
        self.stdout.write(f'Port: {port}')
        self.stdout.write(f'AE Title: {ae_title}')
        
        # Display facility information
        facilities = Facility.objects.all()
        if facilities:
            self.stdout.write('\nConfigured facilities:')
            for facility in facilities:
                self.stdout.write(f'  - {facility.name}: AE={facility.ae_title}, Port={facility.dicom_port}')
        else:
            self.stdout.write(self.style.WARNING('No facilities configured'))
        
        try:
            server = DicomSCPServer()
            server.ae.ae_title = ae_title
            server.start_server(port)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\nShutting down DICOM server...'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting server: {e}')
            )