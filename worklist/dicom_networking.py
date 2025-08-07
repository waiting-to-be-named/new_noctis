"""
DICOM Networking Service
Handles DICOM network operations including C-STORE, C-FIND, C-MOVE from remote modalities
"""

import os
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    from pynetdicom import AE, evt, StoragePresentationContexts, QueryRetrievePresentationContexts
    from pynetdicom.sop_class import CTImageStorage, MRImageStorage, DigitalXRayImageStorageForPresentation
    from pydicom import dcmread
    from pydicom.dataset import Dataset
    PYNETDICOM_AVAILABLE = True
except ImportError:
    PYNETDICOM_AVAILABLE = False
    print("Warning: pynetdicom not available. Install with: pip install pynetdicom")

from django.conf import settings
from django.utils import timezone
from .models import Study, Series, DICOMImage

logger = logging.getLogger(__name__)

class DICOMNetworkService:
    """DICOM Network Service for handling remote modality communications"""
    
    def __init__(self):
        self.ae = None
        self.server_thread = None
        self.is_running = False
        self.received_instances = []
        
        # DICOM Application Entity settings
        self.ae_title = getattr(settings, 'DICOM_AE_TITLE', 'NOCTIS_PACS')
        self.port = getattr(settings, 'DICOM_PORT', 11112)
        self.host = getattr(settings, 'DICOM_HOST', '0.0.0.0')
        
        # Storage directory for received DICOM files
        self.storage_dir = Path(getattr(settings, 'DICOM_STORAGE_DIR', 'media/dicom_received'))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        if PYNETDICOM_AVAILABLE:
            self.setup_application_entity()
    
    def setup_application_entity(self):
        """Setup the DICOM Application Entity"""
        self.ae = AE(ae_title=self.ae_title)
        
        # Add supported Storage SOP Classes (what we can receive)
        storage_sop_classes = [
            CTImageStorage,
            MRImageStorage,
            DigitalXRayImageStorageForPresentation,
            # Add more SOP classes as needed
        ]
        
        for sop_class in storage_sop_classes:
            self.ae.add_supported_context(sop_class)
        
        # Add Query/Retrieve SOP Classes (for C-FIND, C-MOVE)
        self.ae.supported_contexts = QueryRetrievePresentationContexts
        
        # Bind event handlers
        self.ae.on_c_store = self.handle_c_store
        self.ae.on_c_find = self.handle_c_find
        self.ae.on_c_move = self.handle_c_move
        
        logger.info(f"DICOM AE '{self.ae_title}' configured with {len(storage_sop_classes)} SOP classes")
    
    def start_server(self):
        """Start the DICOM SCP server"""
        if not PYNETDICOM_AVAILABLE:
            logger.error("Cannot start DICOM server: pynetdicom not available")
            return False
        
        if self.is_running:
            logger.warning("DICOM server is already running")
            return True
        
        try:
            def run_server():
                logger.info(f"Starting DICOM SCP server on {self.host}:{self.port}")
                self.ae.start_server((self.host, self.port), block=True)
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.is_running = True
            
            logger.info(f"DICOM SCP server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start DICOM server: {e}")
            return False
    
    def stop_server(self):
        """Stop the DICOM SCP server"""
        if self.ae and self.is_running:
            self.ae.shutdown()
            self.is_running = False
            logger.info("DICOM SCP server stopped")
    
    def handle_c_store(self, event):
        """Handle incoming C-STORE requests from modalities"""
        try:
            # Get the dataset from the request
            dataset = event.dataset
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sop_instance_uid = dataset.get('SOPInstanceUID', f'unknown_{timestamp}')
            filename = f"{sop_instance_uid}.dcm"
            
            # Create directory structure: StudyInstanceUID/SeriesInstanceUID/
            study_uid = dataset.get('StudyInstanceUID', 'unknown_study')
            series_uid = dataset.get('SeriesInstanceUID', 'unknown_series')
            
            study_dir = self.storage_dir / study_uid
            series_dir = study_dir / series_uid
            series_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the DICOM file
            file_path = series_dir / filename
            dataset.save_as(str(file_path), write_like_original=False)
            
            # Process and store in database
            self.process_received_dicom(file_path, dataset)
            
            logger.info(f"Received and stored DICOM instance: {sop_instance_uid}")
            
            # Return success status
            return 0x0000  # Success
            
        except Exception as e:
            logger.error(f"Error handling C-STORE: {e}")
            return 0xA700  # Out of Resources
    
    def handle_c_find(self, event):
        """Handle C-FIND requests (queries for studies/series/images)"""
        try:
            dataset = event.identifier
            
            # Determine query level
            query_level = dataset.get('QueryRetrieveLevel', '').upper()
            
            if query_level == 'STUDY':
                return self.find_studies(dataset)
            elif query_level == 'SERIES':
                return self.find_series(dataset)
            elif query_level == 'IMAGE':
                return self.find_images(dataset)
            else:
                logger.warning(f"Unsupported query level: {query_level}")
                return 0xA700
                
        except Exception as e:
            logger.error(f"Error handling C-FIND: {e}")
            return 0xA700
    
    def handle_c_move(self, event):
        """Handle C-MOVE requests (retrieve studies/series/images)"""
        try:
            dataset = event.identifier
            move_destination = event.move_destination
            
            # This would implement the logic to send DICOM data to the requesting entity
            # For now, return success but log the request
            logger.info(f"C-MOVE request received for destination: {move_destination}")
            
            return 0x0000  # Success
            
        except Exception as e:
            logger.error(f"Error handling C-MOVE: {e}")
            return 0xA700
    
    def process_received_dicom(self, file_path: Path, dataset: Dataset):
        """Process received DICOM file and store in database"""
        try:
            # Extract metadata
            study_uid = dataset.get('StudyInstanceUID', '')
            series_uid = dataset.get('SeriesInstanceUID', '')
            sop_instance_uid = dataset.get('SOPInstanceUID', '')
            
            patient_name = str(dataset.get('PatientName', 'Unknown'))
            patient_id = dataset.get('PatientID', 'Unknown')
            study_description = dataset.get('StudyDescription', 'Unknown Study')
            series_description = dataset.get('SeriesDescription', 'Unknown Series')
            modality = dataset.get('Modality', 'OT')
            
            # Parse dates
            study_date = None
            if hasattr(dataset, 'StudyDate') and dataset.StudyDate:
                try:
                    study_date = datetime.strptime(dataset.StudyDate, '%Y%m%d').date()
                except:
                    pass
            
            # Get or create Study
            study, created = Study.objects.get_or_create(
                study_instance_uid=study_uid,
                defaults={
                    'patient_name': patient_name,
                    'patient_id': patient_id,
                    'study_description': study_description,
                    'study_date': study_date or timezone.now().date(),
                    'institution_name': dataset.get('InstitutionName', 'Remote Modality'),
                    'accession_number': dataset.get('AccessionNumber', ''),
                }
            )
            
            if created:
                logger.info(f"Created new study: {study_description} for {patient_name}")
            
            # Get or create Series
            series, created = Series.objects.get_or_create(
                study=study,
                series_instance_uid=series_uid,
                defaults={
                    'series_number': dataset.get('SeriesNumber', 1),
                    'series_description': series_description,
                    'modality': modality,
                    'body_part_examined': dataset.get('BodyPartExamined', ''),
                }
            )
            
            if created:
                logger.info(f"Created new series: {series_description}")
            
            # Create DICOMImage entry
            dicom_image, created = DICOMImage.objects.get_or_create(
                series=series,
                sop_instance_uid=sop_instance_uid,
                defaults={
                    'instance_number': dataset.get('InstanceNumber', 1),
                    'file_path': str(file_path.relative_to(self.storage_dir)),
                    'slice_location': float(dataset.get('SliceLocation', 0.0)) if dataset.get('SliceLocation') else None,
                    'image_position_patient': '\\'.join(map(str, dataset.get('ImagePositionPatient', [0, 0, 0]))),
                    'image_orientation_patient': '\\'.join(map(str, dataset.get('ImageOrientationPatient', [1, 0, 0, 0, 1, 0]))),
                    'pixel_spacing': '\\'.join(map(str, dataset.get('PixelSpacing', [1.0, 1.0]))),
                    'slice_thickness': float(dataset.get('SliceThickness', 1.0)) if dataset.get('SliceThickness') else None,
                    'rows': dataset.get('Rows', 512),
                    'columns': dataset.get('Columns', 512),
                    'bits_allocated': dataset.get('BitsAllocated', 16),
                    'bits_stored': dataset.get('BitsStored', 12),
                    'high_bit': dataset.get('HighBit', 11),
                    'window_width': dataset.get('WindowWidth', 400) if hasattr(dataset, 'WindowWidth') else None,
                    'window_center': dataset.get('WindowCenter', 40) if hasattr(dataset, 'WindowCenter') else None,
                }
            )
            
            if created:
                logger.info(f"Stored DICOM image: Instance {dataset.get('InstanceNumber', 1)}")
                self.received_instances.append({
                    'study': study.study_description,
                    'series': series.series_description,
                    'instance': dataset.get('InstanceNumber', 1),
                    'timestamp': timezone.now(),
                    'file_path': str(file_path)
                })
            
        except Exception as e:
            logger.error(f"Error processing received DICOM file {file_path}: {e}")
    
    def find_studies(self, dataset):
        """Find studies matching the query criteria"""
        # Implementation for study-level queries
        return 0x0000
    
    def find_series(self, dataset):
        """Find series matching the query criteria"""
        # Implementation for series-level queries
        return 0x0000
    
    def find_images(self, dataset):
        """Find images matching the query criteria"""
        # Implementation for image-level queries
        return 0x0000
    
    def get_status(self) -> Dict:
        """Get current status of the DICOM service"""
        return {
            'running': self.is_running,
            'ae_title': self.ae_title,
            'host': self.host,
            'port': self.port,
            'received_instances_count': len(self.received_instances),
            'storage_directory': str(self.storage_dir),
            'last_received': self.received_instances[-1] if self.received_instances else None
        }
    
    def send_to_modality(self, host: str, port: int, ae_title: str, datasets: List[Dataset]) -> bool:
        """Send DICOM datasets to a remote modality"""
        if not PYNETDICOM_AVAILABLE:
            logger.error("Cannot send to modality: pynetdicom not available")
            return False
        
        try:
            # Create association with remote AE
            assoc = self.ae.associate(host, port, ae_title=ae_title)
            
            if assoc.is_established:
                success_count = 0
                for dataset in datasets:
                    # Send C-STORE request
                    status = assoc.send_c_store(dataset)
                    if status:
                        success_count += 1
                    else:
                        logger.error(f"Failed to send dataset: {dataset.get('SOPInstanceUID', 'Unknown')}")
                
                assoc.release()
                logger.info(f"Successfully sent {success_count}/{len(datasets)} datasets to {ae_title}@{host}:{port}")
                return success_count == len(datasets)
            else:
                logger.error(f"Failed to establish association with {ae_title}@{host}:{port}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending to modality: {e}")
            return False

# Global DICOM service instance
dicom_service = DICOMNetworkService()

def start_dicom_service():
    """Start the DICOM networking service"""
    return dicom_service.start_server()

def stop_dicom_service():
    """Stop the DICOM networking service"""
    dicom_service.stop_server()

def get_dicom_service_status():
    """Get the status of the DICOM service"""
    return dicom_service.get_status()