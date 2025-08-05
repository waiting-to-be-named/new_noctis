"""
Service layer for DICOM viewer business logic.
This module contains all the business logic that was previously mixed in views.
"""

import os
import logging
import pydicom
import numpy as np
from datetime import datetime
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth.models import User
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import uuid
import zipfile
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import base64
from scipy import stats
import gc
from django.db.models import Q

from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, Report, WorklistEntry, AIAnalysis, Notification, 
    BoneReconstruction, AngiogramAnalysis, CardiacAnalysis, 
    NeurologicalAnalysis, OrthopedicAnalysis, VolumeRendering
)

logger = logging.getLogger(__name__)


class DicomProcessingService:
    """Service for handling DICOM file processing"""
    
    def __init__(self):
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure that required media directories exist"""
        try:
            media_root = default_storage.location
            dicom_dir = os.path.join(media_root, 'dicom_files')
            temp_dir = os.path.join(media_root, 'temp')
            bulk_upload_dir = os.path.join(media_root, 'bulk_uploads')
            
            for directory in [media_root, dicom_dir, temp_dir, bulk_upload_dir]:
                if not os.path.exists(directory):
                    try:
                        os.makedirs(directory, exist_ok=True)
                        logger.info(f"Created directory: {directory}")
                    except PermissionError:
                        logger.error(f"Permission denied creating directory: {directory}")
                        raise
                    except Exception as e:
                        logger.error(f"Error creating directory {directory}: {e}")
                        raise
        except Exception as e:
            logger.error(f"Critical error in ensure_directories: {e}")
            # Create minimal fallback structure
            fallback_media = os.path.join(os.getcwd(), 'media')
            fallback_dicom = os.path.join(fallback_media, 'dicom_files')
            fallback_bulk = os.path.join(fallback_media, 'bulk_uploads')
            try:
                os.makedirs(fallback_dicom, exist_ok=True)
                os.makedirs(fallback_bulk, exist_ok=True)
                logger.info(f"Created emergency fallback: {fallback_dicom}, {fallback_bulk}")
            except Exception as fallback_error:
                logger.error(f"Emergency fallback failed: {fallback_error}")
                raise
    
    def process_dicom_file(self, file_path, user):
        """Process a single DICOM file"""
        try:
            # Read DICOM file
            dicom_data = pydicom.dcmread(file_path)
            
            # Extract study information
            study_info = self.extract_study_info(dicom_data)
            
            # Get or create study
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_info['study_instance_uid'],
                defaults={
                    'patient_name': study_info['patient_name'],
                    'patient_id': study_info['patient_id'],
                    'study_date': study_info['study_date'],
                    'study_description': study_info['study_description'],
                    'modality': study_info['modality'],
                    'uploaded_by': user,
                    'upload_date': datetime.now(),
                }
            )
            
            # Extract series information
            series_info = self.extract_series_info(dicom_data)
            
            # Get or create series
            series, series_created = DicomSeries.objects.get_or_create(
                series_instance_uid=series_info['series_instance_uid'],
                study=study,
                defaults={
                    'series_number': series_info['series_number'],
                    'series_description': series_info['series_description'],
                    'modality': series_info['modality'],
                    'body_part_examined': series_info.get('body_part_examined', ''),
                }
            )
            
            # Process image
            image = self.process_image(series, dicom_data)
            
            return {
                'study': study,
                'series': series,
                'image': image,
                'created': created or series_created
            }
            
        except Exception as e:
            logger.error(f"Error processing DICOM file {file_path}: {e}")
            raise
    
    def extract_study_info(self, dicom_data):
        """Extract study information from DICOM data"""
        return {
            'study_instance_uid': str(dicom_data.get('StudyInstanceUID', '')),
            'patient_name': str(dicom_data.get('PatientName', '')),
            'patient_id': str(dicom_data.get('PatientID', '')),
            'study_date': self.parse_dicom_date(str(dicom_data.get('StudyDate', ''))),
            'study_description': str(dicom_data.get('StudyDescription', '')),
            'modality': str(dicom_data.get('Modality', '')),
        }
    
    def extract_series_info(self, dicom_data):
        """Extract series information from DICOM data"""
        return {
            'series_instance_uid': str(dicom_data.get('SeriesInstanceUID', '')),
            'series_number': int(dicom_data.get('SeriesNumber', 0)),
            'series_description': str(dicom_data.get('SeriesDescription', '')),
            'modality': str(dicom_data.get('Modality', '')),
            'body_part_examined': str(dicom_data.get('BodyPartExamined', '')),
        }
    
    def process_image(self, series, dicom_data):
        """Process DICOM image data"""
        try:
            # Extract pixel data
            pixel_array = dicom_data.pixel_array
            
            # Get image position and orientation
            image_position = dicom_data.get('ImagePositionPatient', [0, 0, 0])
            image_orientation = dicom_data.get('ImageOrientationPatient', [1, 0, 0, 0, 1, 0])
            
            # Create image record
            image = DicomImage.objects.create(
                series=series,
                image_number=int(dicom_data.get('InstanceNumber', 0)),
                image_position_x=float(image_position[0]) if len(image_position) > 0 else 0,
                image_position_y=float(image_position[1]) if len(image_position) > 1 else 0,
                image_position_z=float(image_position[2]) if len(image_position) > 2 else 0,
                pixel_spacing_x=float(dicom_data.get('PixelSpacing', [1, 1])[0]) if dicom_data.get('PixelSpacing') else 1,
                pixel_spacing_y=float(dicom_data.get('PixelSpacing', [1, 1])[1]) if dicom_data.get('PixelSpacing') else 1,
                slice_thickness=float(dicom_data.get('SliceThickness', 1)),
                window_center=float(dicom_data.get('WindowCenter', 0)),
                window_width=float(dicom_data.get('WindowWidth', 0)),
                rows=pixel_array.shape[0],
                columns=pixel_array.shape[1],
                bits_allocated=int(dicom_data.get('BitsAllocated', 16)),
                samples_per_pixel=int(dicom_data.get('SamplesPerPixel', 1)),
                photometric_interpretation=str(dicom_data.get('PhotometricInterpretation', 'MONOCHROME2')),
            )
            
            # Save pixel data as numpy array
            image.pixel_data = pixel_array.tobytes()
            image.save()
            
            return image
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def parse_dicom_date(self, date_str):
        """Parse DICOM date string"""
        try:
            if date_str and len(date_str) >= 8:
                return datetime.strptime(date_str[:8], '%Y%m%d').date()
            return None
        except:
            return None
    
    def parse_dicom_time(self, time_str):
        """Parse DICOM time string"""
        try:
            if time_str and len(time_str) >= 6:
                return datetime.strptime(time_str[:6], '%H%M%S').time()
            return None
        except:
            return None


class UploadService:
    """Service for handling file uploads"""
    
    def __init__(self, user):
        self.user = user
        self.processing_service = DicomProcessingService()
        self.upload_id = str(uuid.uuid4())
        self.progress = {
            'status': 'initializing',
            'total_files': 0,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'errors': [],
            'start_time': time.time(),
        }
    
    def process_upload(self, uploaded_file):
        """Process uploaded file (single file or archive)"""
        try:
            self.progress['status'] = 'processing'
            self.progress['start_time'] = time.time()
            
            # Check if it's a zip file
            if uploaded_file.name.lower().endswith('.zip'):
                return self.process_archive_upload(uploaded_file)
            else:
                return self.process_single_file_upload(uploaded_file)
                
        except Exception as e:
            logger.error(f"Error in upload processing: {e}")
            self.progress['status'] = 'error'
            self.progress['errors'].append(str(e))
            raise
    
    def process_archive_upload(self, uploaded_file):
        """Process uploaded archive file"""
        try:
            # Save uploaded file temporarily
            temp_path = default_storage.save(f'temp/{self.upload_id}_{uploaded_file.name}', uploaded_file)
            temp_file_path = default_storage.path(temp_path)
            
            # Extract archive
            extracted_files = self.extract_archive(temp_file_path)
            self.progress['total_files'] = len(extracted_files)
            
            # Process files
            results = self.process_files_batch(extracted_files)
            
            # Cleanup
            self.cleanup_temp_files(temp_file_path, extracted_files)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing archive upload: {e}")
            raise
    
    def process_single_file_upload(self, uploaded_file):
        """Process single file upload"""
        try:
            # Save file temporarily
            temp_path = default_storage.save(f'temp/{self.upload_id}_{uploaded_file.name}', uploaded_file)
            temp_file_path = default_storage.path(temp_path)
            
            # Process single file
            result = self.processing_service.process_dicom_file(temp_file_path, self.user)
            
            # Cleanup
            os.remove(temp_file_path)
            
            self.progress['total_files'] = 1
            self.progress['processed_files'] = 1
            self.progress['successful_files'] = 1
            self.progress['status'] = 'completed'
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing single file upload: {e}")
            raise
    
    def extract_archive(self, archive_path):
        """Extract archive and return list of file paths"""
        extracted_files = []
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Extract to temporary directory
                temp_dir = tempfile.mkdtemp()
                zip_ref.extractall(temp_dir)
                
                # Find all files
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self.is_dicom_candidate(file, os.path.getsize(file_path)):
                            extracted_files.append(file_path)
                
                return extracted_files
                
        except Exception as e:
            logger.error(f"Error extracting archive: {e}")
            raise
    
    def is_dicom_candidate(self, filename, file_size):
        """Check if file is a potential DICOM file"""
        # Check file extension
        dicom_extensions = ['.dcm', '.dicom', '.ima', '.img']
        if any(filename.lower().endswith(ext) for ext in dicom_extensions):
            return True
        
        # Check file size (DICOM files are typically > 1KB)
        if file_size < 1024:
            return False
        
        # Check if file has no extension (common for DICOM files)
        if '.' not in filename:
            return True
        
        return False
    
    def process_files_batch(self, files):
        """Process multiple files in batches"""
        results = []
        batch_size = 10
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            # Process batch in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_file = {
                    executor.submit(self.processing_service.process_dicom_file, file_path, self.user): file_path
                    for file_path in batch
                }
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)
                        self.progress['successful_files'] += 1
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
                        self.progress['failed_files'] += 1
                        self.progress['errors'].append(f"Error processing {os.path.basename(file_path)}: {str(e)}")
                    
                    self.progress['processed_files'] += 1
        
        self.progress['status'] = 'completed'
        return results
    
    def cleanup_temp_files(self, archive_path, extracted_files):
        """Clean up temporary files"""
        try:
            # Remove extracted files
            for file_path in extracted_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Remove archive file
            if os.path.exists(archive_path):
                os.remove(archive_path)
            
            # Remove temp directory
            temp_dir = os.path.dirname(extracted_files[0]) if extracted_files else None
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
    
    def get_progress(self):
        """Get current upload progress"""
        if self.progress['status'] == 'completed':
            elapsed_time = time.time() - self.progress['start_time']
            self.progress['elapsed_time'] = elapsed_time
            self.progress['files_per_second'] = self.progress['processed_files'] / elapsed_time if elapsed_time > 0 else 0
        
        return self.progress


class ImageProcessingService:
    """Service for image processing and enhancement"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def apply_window_level(self, pixel_data, window_center, window_width):
        """Apply window/level adjustment to image"""
        try:
            # Convert to numpy array if needed
            if isinstance(pixel_data, bytes):
                pixel_data = np.frombuffer(pixel_data, dtype=np.uint16)
            
            # Apply window/level
            min_val = window_center - window_width / 2
            max_val = window_center + window_width / 2
            
            # Clip values
            pixel_data = np.clip(pixel_data, min_val, max_val)
            
            # Normalize to 0-255
            pixel_data = ((pixel_data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            
            return pixel_data
            
        except Exception as e:
            self.logger.error(f"Error applying window/level: {e}")
            raise
    
    def enhance_image(self, pixel_data, enhancement_type='standard'):
        """Enhance image based on type"""
        try:
            if enhancement_type == 'xray':
                return self.enhance_xray_image(pixel_data)
            elif enhancement_type == 'mri':
                return self.enhance_mri_image(pixel_data)
            elif enhancement_type == 'ct':
                return self.enhance_ct_image(pixel_data)
            else:
                return self.enhance_standard_image(pixel_data)
                
        except Exception as e:
            self.logger.error(f"Error enhancing image: {e}")
            raise
    
    def enhance_xray_image(self, pixel_data):
        """Enhance X-ray image"""
        try:
            # Convert to numpy array if needed
            if isinstance(pixel_data, bytes):
                pixel_data = np.frombuffer(pixel_data, dtype=np.uint16)
            
            # Apply histogram equalization
            from skimage import exposure
            enhanced = exposure.equalize_hist(pixel_data)
            
            # Apply edge enhancement
            from scipy import ndimage
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            enhanced = ndimage.convolve(enhanced, kernel)
            
            # Normalize
            enhanced = np.clip(enhanced, 0, 1)
            enhanced = (enhanced * 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Error enhancing X-ray image: {e}")
            raise
    
    def enhance_mri_image(self, pixel_data):
        """Enhance MRI image"""
        try:
            # Convert to numpy array if needed
            if isinstance(pixel_data, bytes):
                pixel_data = np.frombuffer(pixel_data, dtype=np.uint16)
            
            # Apply contrast enhancement
            from skimage import exposure
            enhanced = exposure.adjust_gamma(pixel_data, gamma=0.8)
            
            # Apply noise reduction
            from scipy import ndimage
            enhanced = ndimage.gaussian_filter(enhanced, sigma=0.5)
            
            # Normalize
            enhanced = np.clip(enhanced, 0, 1)
            enhanced = (enhanced * 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Error enhancing MRI image: {e}")
            raise
    
    def enhance_ct_image(self, pixel_data):
        """Enhance CT image"""
        try:
            # Convert to numpy array if needed
            if isinstance(pixel_data, bytes):
                pixel_data = np.frombuffer(pixel_data, dtype=np.uint16)
            
            # Apply bone window
            bone_min = 400
            bone_max = 1800
            enhanced = np.clip(pixel_data, bone_min, bone_max)
            
            # Normalize
            enhanced = ((enhanced - bone_min) / (bone_max - bone_min) * 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Error enhancing CT image: {e}")
            raise
    
    def enhance_standard_image(self, pixel_data):
        """Standard image enhancement"""
        try:
            # Convert to numpy array if needed
            if isinstance(pixel_data, bytes):
                pixel_data = np.frombuffer(pixel_data, dtype=np.uint16)
            
            # Apply histogram equalization
            from skimage import exposure
            enhanced = exposure.equalize_hist(pixel_data)
            
            # Normalize
            enhanced = np.clip(enhanced, 0, 1)
            enhanced = (enhanced * 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Error in standard image enhancement: {e}")
            raise


class WorklistService:
    """Service for worklist management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_worklist_entry(self, study, user, facility=None):
        """Create worklist entry for a study"""
        try:
            entry = WorklistEntry.objects.create(
                study=study,
                patient_name=study.patient_name,
                patient_id=study.patient_id,
                accession_number=study.accession_number,
                modality=study.modality,
                scheduled_procedure_step_start_date=study.study_date,
                scheduled_procedure_step_start_time=study.study_time,
                status='pending',
                priority='routine',
                facility=facility,
                created_by=user,
            )
            
            # Create notification
            self.create_notification(
                user=user,
                notification_type='new_study',
                title=f'New Study: {study.patient_name}',
                message=f'New {study.modality} study uploaded for {study.patient_name}',
                related_study=study
            )
            
            return entry
            
        except Exception as e:
            self.logger.error(f"Error creating worklist entry: {e}")
            raise
    
    def create_notification(self, user, notification_type, title, message, related_study=None):
        """Create notification for user"""
        try:
            Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                related_study=related_study,
                is_read=False,
                created_at=datetime.now(),
            )
        except Exception as e:
            self.logger.error(f"Error creating notification: {e}")
    
    def get_user_worklist(self, user, filters=None):
        """Get worklist entries for user with filters"""
        try:
            queryset = WorklistEntry.objects.all()
            
            # Filter by facility if user is facility staff
            if hasattr(user, 'facility') and user.facility:
                queryset = queryset.filter(facility=user.facility)
            elif user.groups.filter(name='Facilities').exists():
                queryset = queryset.none()
            
            # Apply additional filters
            if filters:
                if filters.get('status'):
                    queryset = queryset.filter(status=filters['status'])
                if filters.get('modality'):
                    queryset = queryset.filter(modality=filters['modality'])
                if filters.get('search'):
                    search = filters['search']
                    queryset = queryset.filter(
                        Q(patient_name__icontains=search) |
                        Q(patient_id__icontains=search) |
                        Q(accession_number__icontains=search)
                    )
            
            return queryset.order_by('-scheduled_procedure_step_start_date')
            
        except Exception as e:
            self.logger.error(f"Error getting user worklist: {e}")
            raise


class ErrorHandlingService:
    """Service for consistent error handling"""
    
    @staticmethod
    def handle_upload_error(error, context=""):
        """Handle upload-related errors"""
        error_message = f"Upload error in {context}: {str(error)}"
        logger.error(error_message)
        
        return {
            'success': False,
            'error': error_message,
            'error_type': 'upload_error',
            'timestamp': datetime.now().isoformat(),
        }
    
    @staticmethod
    def handle_processing_error(error, context=""):
        """Handle processing-related errors"""
        error_message = f"Processing error in {context}: {str(error)}"
        logger.error(error_message)
        
        return {
            'success': False,
            'error': error_message,
            'error_type': 'processing_error',
            'timestamp': datetime.now().isoformat(),
        }
    
    @staticmethod
    def handle_database_error(error, context=""):
        """Handle database-related errors"""
        error_message = f"Database error in {context}: {str(error)}"
        logger.error(error_message)
        
        return {
            'success': False,
            'error': error_message,
            'error_type': 'database_error',
            'timestamp': datetime.now().isoformat(),
        }
    
    @staticmethod
    def handle_security_error(error, context=""):
        """Handle security-related errors"""
        error_message = f"Security error in {context}: {str(error)}"
        logger.error(error_message)
        
        return {
            'success': False,
            'error': error_message,
            'error_type': 'security_error',
            'timestamp': datetime.now().isoformat(),
        }