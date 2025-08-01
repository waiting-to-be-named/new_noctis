#!/usr/bin/env python3
"""
SCP (Service Class Provider) Server for DICOM Image Reception
Handles incoming DICOM images from remote machines and facilities
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

# Add Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
import django
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import ImplicitVRLittleEndian
from pynetdicom import (
    AE, evt, AllowedPresentationContexts, debug_logger
)
from pynetdicom.sop_class import (
    VerificationSOPClass, CTImageStorage, MRImageStorage,
    SecondaryCaptureImageStorage, UltrasoundImageStorage,
    XRayImageStorage, ComputedRadiographyImageStorage
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DICOM Application Entity
class NoctisSCPServer:
    def __init__(self, host='0.0.0.0', port=11112, ae_title=b'NOCTIS_SCP'):
        self.host = host
        self.port = port
        self.ae_title = ae_title
        self.ae = None
        self.server = None
        self.running = False
        
        # Ensure media directories exist
        self.ensure_directories()
        
    def ensure_directories(self):
        """Ensure required directories exist"""
        try:
            media_root = default_storage.location
            dicom_dir = os.path.join(media_root, 'dicom_files')
            scp_dir = os.path.join(media_root, 'scp_received')
            temp_dir = os.path.join(media_root, 'temp')
            
            for directory in [media_root, dicom_dir, scp_dir, temp_dir]:
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                    
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            # Fallback to current directory
            fallback_media = os.path.join(os.getcwd(), 'media')
            fallback_dicom = os.path.join(fallback_media, 'dicom_files')
            fallback_scp = os.path.join(fallback_media, 'scp_received')
            
            for directory in [fallback_media, fallback_dicom, fallback_scp]:
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created fallback directory: {directory}")
    
    def handle_c_echo(self, event):
        """Handle C-ECHO requests"""
        logger.info("C-ECHO request received")
        return 0x0000  # Success
    
    def handle_c_store(self, event):
        """Handle C-STORE requests - receive DICOM files"""
        try:
            # Get the dataset
            ds = event.dataset
            
            # Add file meta information
            ds.file_meta = event.file_meta
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"scp_{timestamp}_{ds.SOPInstanceUID}.dcm"
            
            # Determine storage path
            media_root = default_storage.location
            scp_dir = os.path.join(media_root, 'scp_received')
            
            # Create subdirectories based on date
            date_dir = datetime.now().strftime("%Y/%m/%d")
            full_path = os.path.join(scp_dir, date_dir)
            os.makedirs(full_path, exist_ok=True)
            
            file_path = os.path.join(full_path, filename)
            
            # Save the DICOM file
            ds.save_as(file_path, write_like_original=False)
            
            logger.info(f"Received DICOM file: {filename}")
            logger.info(f"  - SOP Class: {ds.SOPClassUID}")
            logger.info(f"  - Modality: {getattr(ds, 'Modality', 'Unknown')}")
            logger.info(f"  - Patient: {getattr(ds, 'PatientName', 'Unknown')}")
            logger.info(f"  - Study: {getattr(ds, 'StudyDescription', 'Unknown')}")
            
            # Process the received DICOM file
            self.process_received_dicom(file_path, ds)
            
            return 0x0000  # Success
            
        except Exception as e:
            logger.error(f"Error handling C-STORE: {e}")
            return 0x0110  # Processing failure
    
    def process_received_dicom(self, file_path, ds):
        """Process received DICOM file and integrate with viewer"""
        try:
            from viewer.models import DicomStudy, DicomSeries, DicomImage
            from viewer.views import DicomProcessor
            
            # Create processor instance
            processor = DicomProcessor(user=None)
            
            # Process the DICOM file
            study_data = processor.extract_study_info(ds)
            series_data = processor.extract_series_info(ds)
            
            # Check if study already exists
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_data['study_instance_uid'],
                defaults=study_data
            )
            
            if not created:
                logger.info(f"Study already exists: {study.study_instance_uid}")
            
            # Check if series already exists
            series, created = DicomSeries.objects.get_or_create(
                series_instance_uid=series_data['series_instance_uid'],
                study=study,
                defaults=series_data
            )
            
            if not created:
                logger.info(f"Series already exists: {series.series_instance_uid}")
            
            # Process image
            image_data = processor.process_image(series, ds)
            
            logger.info(f"Successfully processed received DICOM: {file_path}")
            
        except Exception as e:
            logger.error(f"Error processing received DICOM: {e}")
    
    def start_server(self):
        """Start the SCP server"""
        try:
            # Initialize the Application Entity
            self.ae = AE(ae_title=self.ae_title)
            
            # Add supported presentation contexts
            supported_contexts = [
                VerificationSOPClass,
                CTImageStorage,
                MRImageStorage,
                SecondaryCaptureImageStorage,
                UltrasoundImageStorage,
                XRayImageStorage,
                ComputedRadiographyImageStorage
            ]
            
            for sop_class in supported_contexts:
                self.ae.add_supported_context(sop_class)
            
            # Define event handlers
            handlers = [
                (evt.EVT_C_ECHO, self.handle_c_echo),
                (evt.EVT_C_STORE, self.handle_c_store)
            ]
            
            # Start the server
            self.server = self.ae.start_server(
                (self.host, self.port),
                block=False,
                evt_handlers=handlers
            )
            
            self.running = True
            logger.info(f"SCP Server started on {self.host}:{self.port}")
            logger.info(f"AE Title: {self.ae_title}")
            logger.info("Waiting for DICOM connections...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting SCP server: {e}")
            return False
    
    def stop_server(self):
        """Stop the SCP server"""
        if self.server and self.running:
            self.server.shutdown()
            self.running = False
            logger.info("SCP Server stopped")
    
    def get_status(self):
        """Get server status"""
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'ae_title': self.ae_title.decode() if isinstance(self.ae_title, bytes) else self.ae_title
        }

# Server management functions
def start_scp_server(host='0.0.0.0', port=11112, ae_title='NOCTIS_SCP'):
    """Start the SCP server in a separate thread"""
    server = NoctisSCPServer(host=host, port=port, ae_title=ae_title.encode())
    
    if server.start_server():
        # Keep the server running
        try:
            while server.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down SCP server...")
            server.stop_server()
    
    return server

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Noctis SCP Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=11112, help='Port to bind to')
    parser.add_argument('--ae-title', default='NOCTIS_SCP', help='AE Title')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        debug_logger()
        logging.getLogger('pynetdicom').setLevel(logging.DEBUG)
    
    # Start the server
    server = start_scp_server(
        host=args.host,
        port=args.port,
        ae_title=args.ae_title
    )