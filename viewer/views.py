# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, Report, WorklistEntry, AIAnalysis, Notification
)
from django.contrib.auth.models import Group
from .serializers import DicomStudySerializer, DicomImageSerializer
import io
from scipy import stats
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache
from django.db import transaction
import gc
import zipfile
import tempfile
import shutil
from pathlib import Path
import logging
from PIL import Image
import base64

# Configure logging
logger = logging.getLogger(__name__)

# Ensure required directories exist
def ensure_directories():
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
                    print(f"Created directory: {directory}")
                except PermissionError:
                    # Fallback to current directory if media_root fails
                    if directory == media_root:
                        fallback_dir = os.path.join(os.getcwd(), 'media')
                        if not os.path.exists(fallback_dir):
                            os.makedirs(fallback_dir, exist_ok=True)
                            print(f"Created fallback media directory: {fallback_dir}")
                        # Update default storage location
                        default_storage.location = fallback_dir
                        media_root = fallback_dir
                        dicom_dir = os.path.join(media_root, 'dicom_files')
                        temp_dir = os.path.join(media_root, 'temp')
                        bulk_upload_dir = os.path.join(media_root, 'bulk_uploads')
                        # Create subdirectories in fallback location
                        for subdir in [dicom_dir, temp_dir, bulk_upload_dir]:
                            if not os.path.exists(subdir):
                                os.makedirs(subdir, exist_ok=True)
                                print(f"Created fallback directory: {subdir}")
                    else:
                        print(f"Permission denied creating directory: {directory}")
                        raise
                except Exception as e:
                    print(f"Error creating directory {directory}: {e}")
                    raise
    except Exception as e:
        print(f"Critical error in ensure_directories: {e}")
        # Create minimal fallback structure
        fallback_media = os.path.join(os.getcwd(), 'media')
        fallback_dicom = os.path.join(fallback_media, 'dicom_files')
        fallback_bulk = os.path.join(fallback_media, 'bulk_uploads')
        try:
            os.makedirs(fallback_dicom, exist_ok=True)
            os.makedirs(fallback_bulk, exist_ok=True)
            print(f"Created emergency fallback: {fallback_dicom}, {fallback_bulk}")
        except Exception as fallback_error:
            print(f"Emergency fallback failed: {fallback_error}")
            raise


class EnhancedBulkUploadManager:
    """Enhanced bulk upload manager for handling large files with multiple folders"""
    
    def __init__(self, user, facility=None):
        self.user = user
        self.facility = facility
        self.upload_id = str(uuid.uuid4())
        self.progress = {
            'total_files': 0,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'current_study': None,
            'current_series': None,
            'status': 'initializing',
            'errors': [],
            'warnings': [],
            'studies_created': 0,
            'series_created': 0,
            'images_processed': 0,
            'total_size_mb': 0,
            'processed_size_mb': 0,
            'estimated_time_remaining': 0,
            'current_folder': None,
            'folder_progress': 0,
            'total_folders': 0
        }
        self.studies = {}
        self.lock = threading.Lock()
        self.temp_dir = None
        self.chunk_size = 50  # Process 50 files at a time
        self.max_workers = 4  # Number of worker threads
        
    def process_folder_upload(self, folder_files):
        """Process folder upload with multiple DICOM files"""
        try:
            self.start_time = time.time()
            self.update_progress(
                status='processing_folder',
                total_files=len(folder_files),
                current_folder='Uploading folder contents'
            )
            
            # Process files in chunks
            processed_files = []
            failed_files = []
            
            for i, uploaded_file in enumerate(folder_files):
                try:
                    # Check file size
                    if uploaded_file.size > 5 * 1024 * 1024 * 1024:  # 5GB limit
                        failed_files.append(f"File {uploaded_file.name} is too large (max 5GB)")
                        continue
                    
                    # Try to read as DICOM
                    file_content = uploaded_file.read()
                    uploaded_file.seek(0)  # Reset file pointer
                    
                    # Check if it's a DICOM file
                    try:
                        # First try standard DICOM reading
                        try:
                            dicom_data = pydicom.dcmread(io.BytesIO(file_content))
                        except pydicom.errors.InvalidDicomError:
                            # If it fails due to missing DICM header, try with force=True
                            dicom_data = pydicom.dcmread(io.BytesIO(file_content), force=True)
                        
                        # Save file temporarily and process
                        temp_path = default_storage.save(
                            f'temp/{uploaded_file.name}',
                            ContentFile(file_content)
                        )
                        
                        # Process DICOM file
                        result = self.process_single_dicom_file(temp_path, dicom_data)
                        if result['success']:
                            processed_files.append(result)
                        else:
                            failed_files.append(f"Failed to process {uploaded_file.name}: {result['error']}")
                        
                        # Clean up temp file
                        try:
                            default_storage.delete(temp_path)
                        except:
                            pass
                            
                    except Exception as dicom_error:
                        failed_files.append(f"Not a valid DICOM file: {uploaded_file.name} - {str(dicom_error)}")
                        
                    # Update progress
                    self.update_progress(
                        processed_files=i + 1,
                        successful_files=len(processed_files),
                        failed_files=len(failed_files)
                    )
                    
                except Exception as file_error:
                    logger.error(f"Error processing file {uploaded_file.name}: {file_error}")
                    failed_files.append(f"Error processing {uploaded_file.name}: {str(file_error)}")
            
            self.update_progress(
                status='completed',
                message=f'Folder upload completed. {len(processed_files)} files processed successfully, {len(failed_files)} failed.'
            )
            
            return {
                'success': True,
                'processed_files': len(processed_files),
                'failed_files': len(failed_files),
                'total_files': len(folder_files)
            }
            
        except Exception as e:
            logger.error(f"Error in folder upload processing: {e}")
            self.update_progress(
                status='failed',
                errors=self.progress['errors'] + [str(e)]
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_single_dicom_file(self, file_path, dicom_data):
        """Process a single DICOM file and create database entries"""
        try:
            # Extract metadata
            study_uid = str(dicom_data.get('StudyInstanceUID', ''))
            series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
            instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
            
            if not study_uid:
                study_uid = f"STUDY_{uuid.uuid4()}"
            if not series_uid:
                series_uid = f"SERIES_{uuid.uuid4()}"
            if not instance_uid:
                instance_uid = f"INSTANCE_{uuid.uuid4()}"
            
            # Create or get study
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_uid,
                defaults={
                    'patient_name': str(dicom_data.get('PatientName', 'Unknown')),
                    'patient_id': str(dicom_data.get('PatientID', 'Unknown')),
                    'study_date': getattr(dicom_data, 'StudyDate', None),
                    'study_description': str(dicom_data.get('StudyDescription', '')),
                    'modality': str(dicom_data.get('Modality', 'OT')),
                    'uploaded_by': self.user,
                    'facility': self.facility
                }
            )
            
            # Create or get series
            series, created = DicomSeries.objects.get_or_create(
                series_instance_uid=series_uid,
                study=study,
                defaults={
                    'series_number': str(dicom_data.get('SeriesNumber', 1)),
                    'series_description': str(dicom_data.get('SeriesDescription', '')),
                    'modality': str(dicom_data.get('Modality', 'OT')),
                    'body_part': str(dicom_data.get('BodyPartExamined', ''))
                }
            )
            
            # Create image
            image = DicomImage.objects.create(
                series=series,
                instance_uid=instance_uid,
                instance_number=int(dicom_data.get('InstanceNumber', 1)),
                dicom_file=file_path,
                file_size=os.path.getsize(default_storage.path(file_path))
            )
            
            return {
                'success': True,
                'study_id': study.id,
                'series_id': series.id,
                'image_id': image.id
            }
            
        except Exception as e:
            logger.error(f"Error processing single DICOM file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        
    def update_progress(self, **kwargs):
        """Thread-safe progress update with enhanced metrics"""
        with self.lock:
            self.progress.update(kwargs)
            # Calculate estimated time remaining
            if self.progress['processed_files'] > 0:
                elapsed_time = time.time() - self.start_time
                rate = self.progress['processed_files'] / elapsed_time
                remaining_files = self.progress['total_files'] - self.progress['processed_files']
                if rate > 0:
                    self.progress['estimated_time_remaining'] = remaining_files / rate
            
            # Cache progress for frontend polling
            cache.set(f'upload_progress_{self.upload_id}', self.progress, timeout=7200)  # 2 hours
    
    def extract_archive(self, uploaded_file):
        """Extract uploaded archive (zip, tar, etc.) to temporary directory"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix=f'bulk_upload_{self.upload_id}_')
            
            if uploaded_file.name.lower().endswith('.zip'):
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
            else:
                # For other archive types, save and extract
                temp_path = os.path.join(self.temp_dir, uploaded_file.name)
                with open(temp_path, 'wb') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                
                # Extract based on file type
                if uploaded_file.name.lower().endswith('.tar.gz'):
                    import tarfile
                    with tarfile.open(temp_path, 'r:gz') as tar:
                        tar.extractall(self.temp_dir)
                elif uploaded_file.name.lower().endswith('.tar'):
                    import tarfile
                    with tarfile.open(temp_path, 'r') as tar:
                        tar.extractall(self.temp_dir)
            
            return True
        except Exception as e:
            logger.error(f"Failed to extract archive: {e}")
            self.update_progress(errors=self.progress['errors'] + [f"Archive extraction failed: {str(e)}"])
            return False
    
    def scan_files(self):
        """Scan extracted files to count and categorize them"""
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return False
        
        files = []
        total_size = 0
        
        for root, dirs, filenames in os.walk(self.temp_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                file_size = os.path.getsize(file_path)
                
                # Check if file is likely a DICOM file
                if self.is_dicom_candidate(filename, file_size):
                    files.append({
                        'path': file_path,
                        'name': filename,
                        'size': file_size,
                        'relative_path': os.path.relpath(file_path, self.temp_dir)
                    })
                    total_size += file_size
        
        self.files_to_process = files
        self.update_progress(
            total_files=len(files),
            total_size_mb=total_size / (1024 * 1024),
            status='scanning_complete'
        )
        
        return len(files) > 0
    
    def is_dicom_candidate(self, filename, file_size):
        """Enhanced DICOM file detection"""
        filename_lower = filename.lower()
        
        # Explicit DICOM extensions
        dicom_extensions = ['.dcm', '.dicom', '.img', '.ima']
        if any(filename_lower.endswith(ext) for ext in dicom_extensions):
            return True
        
        # Compressed DICOM files
        compressed_extensions = ['.dcm.gz', '.dicom.gz', '.dcm.bz2', '.dicom.bz2']
        if any(filename_lower.endswith(ext) for ext in compressed_extensions):
            return True
        
        # Raw data files
        raw_extensions = ['.raw', '.dat', '.bin']
        if any(filename_lower.endswith(ext) for ext in raw_extensions):
            return True
        
        # Files without extension (common for DICOM)
        if '.' not in filename:
            return file_size > 512
        
        # Large files that might be DICOM
        if file_size > 1024:  # 1KB minimum
            return True
        
        return False
    
    def process_file_batch(self, files_batch):
        """Process a batch of files with enhanced error handling"""
        batch_results = {
            'successful': [],
            'failed': [],
            'studies': {},
            'total_size': 0
        }
        
        for file_info in files_batch:
            try:
                file_path = file_info['path']
                file_size = file_info['size']
                
                # Check file size (5GB limit for individual files)
                if file_size > 5 * 1024 * 1024 * 1024:
                    batch_results['failed'].append(f"File {file_info['name']} is too large (max 5GB)")
                    continue
                
                # Read DICOM data with multiple fallback methods
                dicom_data = None
                try:
                    # Method 1: Direct read
                    dicom_data = pydicom.dcmread(file_path)
                except Exception as e1:
                    try:
                        # Method 2: Force read
                        dicom_data = pydicom.dcmread(file_path, force=True)
                    except Exception as e2:
                        try:
                            # Method 3: Read with specific transfer syntax
                            dicom_data = pydicom.dcmread(file_path, force=True, specific_char_set='utf-8')
                        except Exception as e3:
                            logger.error(f"Failed to read DICOM file {file_info['name']}: {e1}, {e2}, {e3}")
                            batch_results['failed'].append(f"Could not read DICOM data from {file_info['name']}")
                            continue
                
                if not dicom_data:
                    batch_results['failed'].append(f"No DICOM data found in {file_info['name']}")
                    continue
                
                # Get study UID with fallback
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    study_uid = f"STUDY_{uuid.uuid4()}"
                
                # Get series UID with fallback
                series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                if not series_uid:
                    series_uid = f"SERIES_{uuid.uuid4()}"
                
                # Group by study and series
                if study_uid not in batch_results['studies']:
                    batch_results['studies'][study_uid] = {
                        'study_data': dicom_data,
                        'series': {}
                    }
                
                if series_uid not in batch_results['studies'][study_uid]['series']:
                    batch_results['studies'][study_uid]['series'][series_uid] = []
                
                batch_results['studies'][study_uid]['series'][series_uid].append({
                    'dicom_data': dicom_data,
                    'file_path': file_path,
                    'file_info': file_info
                })
                
                batch_results['successful'].append(file_info['name'])
                batch_results['total_size'] += file_size
                
            except Exception as e:
                logger.error(f"Error processing file {file_info['name']}: {e}")
                batch_results['failed'].append(f"Error processing {file_info['name']}: {str(e)}")
        
        return batch_results
    
    def process_study(self, study_uid, study_data):
        """Process a study with enhanced series handling"""
        try:
            # Extract study information
            study_info = self.extract_study_info(study_data['study_data'])
            
            # Create or get study
            study, created = DicomStudy.objects.get_or_create(
                study_instance_uid=study_uid,
                defaults=study_info
            )
            
            if created:
                self.update_progress(studies_created=self.progress['studies_created'] + 1)
            
            # Process each series
            for series_uid, series_files in study_data['series'].items():
                if series_files:
                    series_info = self.extract_series_info(series_files[0]['dicom_data'])
                    
                    # Create or get series
                    series, series_created = DicomSeries.objects.get_or_create(
                        study=study,
                        series_instance_uid=series_uid,
                        defaults=series_info
                    )
                    
                    if series_created:
                        self.update_progress(series_created=self.progress['series_created'] + 1)
                    
                    # Process images in series
                    for image_data in series_files:
                        try:
                            self.process_image(series, image_data)
                            self.update_progress(images_processed=self.progress['images_processed'] + 1)
                        except Exception as e:
                            logger.error(f"Error processing image in series {series_uid}: {e}")
                            self.update_progress(errors=self.progress['errors'] + [f"Image processing error: {str(e)}"])
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing study {study_uid}: {e}")
            self.update_progress(errors=self.progress['errors'] + [f"Study processing error: {str(e)}"])
            return False
    
    def extract_study_info(self, dicom_data):
        """Extract study information from DICOM data"""
        return {
            'patient_name': str(dicom_data.get('PatientName', 'Unknown')),
            'patient_id': str(dicom_data.get('PatientID', 'Unknown')),
            'study_date': self.parse_dicom_date(str(dicom_data.get('StudyDate', ''))),
            'study_time': self.parse_dicom_time(str(dicom_data.get('StudyTime', ''))),
            'study_description': str(dicom_data.get('StudyDescription', '')),
            'modality': str(dicom_data.get('Modality', 'OT')),
            'institution_name': str(dicom_data.get('InstitutionName', '')),
            'accession_number': str(dicom_data.get('AccessionNumber', '')),
            'referring_physician': str(dicom_data.get('ReferringPhysicianName', '')),
            'uploaded_by': self.user,
            'facility': self.facility
        }
    
    def extract_series_info(self, dicom_data):
        """Extract series information from DICOM data"""
        return {
            'series_number': int(dicom_data.get('SeriesNumber', 0)),
            'series_description': str(dicom_data.get('SeriesDescription', '')),
            'modality': str(dicom_data.get('Modality', 'OT')),
            'body_part_examined': str(dicom_data.get('BodyPartExamined', ''))
        }
    
    def process_image(self, series, image_data):
        """Process individual DICOM image"""
        dicom_data = image_data['dicom_data']
        file_path = image_data['file_path']
        
        # Get SOP Instance UID
        sop_instance_uid = str(dicom_data.get('SOPInstanceUID', f"INSTANCE_{uuid.uuid4()}"))
        
        # Create or get image
        image, created = DicomImage.objects.get_or_create(
            series=series,
            sop_instance_uid=sop_instance_uid,
            defaults={
                'instance_number': int(dicom_data.get('InstanceNumber', 0)),
                'rows': int(dicom_data.get('Rows', 0)),
                'columns': int(dicom_data.get('Columns', 0)),
                'pixel_spacing_x': float(dicom_data.get('PixelSpacing', [1.0, 1.0])[0]) if dicom_data.get('PixelSpacing') else None,
                'pixel_spacing_y': float(dicom_data.get('PixelSpacing', [1.0, 1.0])[1]) if dicom_data.get('PixelSpacing') else None,
                'slice_thickness': float(dicom_data.get('SliceThickness', 1.0)),
                'window_width': float(dicom_data.get('WindowWidth', 400)),
                'window_center': float(dicom_data.get('WindowCenter', 40)),
                'bits_allocated': int(dicom_data.get('BitsAllocated', 16)),
                'image_number': int(dicom_data.get('ImageNumber', 0)),
                'photometric_interpretation': str(dicom_data.get('PhotometricInterpretation', 'MONOCHROME2')),
                'samples_per_pixel': int(dicom_data.get('SamplesPerPixel', 1))
            }
        )
        
        if created:
            # Save file to storage
            unique_filename = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
            with open(file_path, 'rb') as f:
                image.file_path.save(unique_filename, ContentFile(f.read()))
            
            # Save DICOM metadata
            image.save_dicom_metadata()
    
    def process_upload(self, uploaded_file):
        """Main upload processing method"""
        self.start_time = time.time()
        self.update_progress(status='starting')
        
        try:
            # Extract archive if needed
            if uploaded_file.name.lower().endswith(('.zip', '.tar.gz', '.tar')):
                self.update_progress(status='extracting')
                if not self.extract_archive(uploaded_file):
                    return False
            else:
                # Single file upload
                self.temp_dir = tempfile.mkdtemp(prefix=f'single_upload_{self.upload_id}_')
                temp_path = os.path.join(self.temp_dir, uploaded_file.name)
                with open(temp_path, 'wb') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                self.files_to_process = [{
                    'path': temp_path,
                    'name': uploaded_file.name,
                    'size': uploaded_file.size,
                    'relative_path': uploaded_file.name
                }]
                self.update_progress(total_files=1, total_size_mb=uploaded_file.size/(1024*1024))
            
            # Scan files
            if not self.scan_files():
                self.update_progress(status='no_files_found')
                return False
            
            # Process files in chunks
            self.update_progress(status='processing')
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Split files into chunks
                file_chunks = [self.files_to_process[i:i + self.chunk_size] 
                             for i in range(0, len(self.files_to_process), self.chunk_size)]
                
                # Submit chunks for processing
                future_to_chunk = {executor.submit(self.process_file_batch, chunk): chunk 
                                 for chunk in file_chunks}
                
                # Collect results
                for future in as_completed(future_to_chunk):
                    try:
                        batch_result = future.result()
                        
                        # Update progress
                        self.update_progress(
                            processed_files=self.progress['processed_files'] + len(batch_result['successful']) + len(batch_result['failed']),
                            successful_files=self.progress['successful_files'] + len(batch_result['successful']),
                            failed_files=self.progress['failed_files'] + len(batch_result['failed']),
                            processed_size_mb=self.progress['processed_size_mb'] + batch_result['total_size']/(1024*1024),
                            errors=self.progress['errors'] + batch_result['failed']
                        )
                        
                        # Process studies
                        for study_uid, study_data in batch_result['studies'].items():
                            self.update_progress(current_study=study_uid)
                            self.process_study(study_uid, study_data)
                        
                    except Exception as e:
                        logger.error(f"Error in batch processing: {e}")
                        self.update_progress(errors=self.progress['errors'] + [f"Batch processing error: {str(e)}"])
            
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            self.update_progress(status='completed')
            return True
            
        except Exception as e:
            logger.error(f"Error in bulk upload processing: {e}")
            self.update_progress(
                status='failed',
                errors=self.progress['errors'] + [f"Upload processing error: {str(e)}"]
            )
            return False
    
    def parse_dicom_date(self, date_str):
        """Parse DICOM date string"""
        if not date_str or date_str == 'None':
            return None
        try:
            return datetime.strptime(date_str, '%Y%m%d').date()
        except:
            return None
    
    def parse_dicom_time(self, time_str):
        """Parse DICOM time string"""
        if not time_str or time_str == 'None':
            return None
        try:
            # Handle various time formats
            if len(time_str) >= 6:
                return datetime.strptime(time_str[:6], '%H%M%S').time()
            return None
        except:
            return None


class HomeView(TemplateView):
    """Home page with launch buttons"""
    template_name = 'home.html'


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use the new access control system
        context['studies'] = get_user_study_queryset(self.request.user)[:10]
        
        # Check if we have a study_id parameter
        study_id = kwargs.get('study_id')
        if study_id:
            try:
                study = DicomStudy.objects.get(id=study_id)
                context['initial_study_id'] = study_id
                context['initial_study'] = study
                
                # Update worklist entry status to in_progress if radiologist is viewing
                if self.request.user.is_authenticated:
                    worklist_entries = WorklistEntry.objects.filter(
                        study=study,
                        status='scheduled'
                    )
                    for entry in worklist_entries:
                        entry.status = 'in_progress'
                        entry.save()
                        
            except DicomStudy.DoesNotExist:
                context['initial_study_error'] = f'Study with ID {study_id} not found'
        
        return context


class AdvancedDicomViewerView(TemplateView):
    """Advanced DICOM viewer page with enhanced features"""
    template_name = 'dicom_viewer/viewer_advanced.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use the new access control system
        context['studies'] = get_user_study_queryset(self.request.user)[:10]
        
        # Check if we have a study_id parameter
        study_id = kwargs.get('study_id')
        if study_id:
            try:
                study = DicomStudy.objects.get(id=study_id)
                context['initial_study_id'] = study_id
                context['initial_study'] = study
                
                # Update worklist entry status to in_progress if radiologist is viewing
                if self.request.user.is_authenticated:
                    worklist_entries = WorklistEntry.objects.filter(
                        study=study,
                        status='scheduled'
                    )
                    for entry in worklist_entries:
                        entry.status = 'in_progress'
                        entry.save()
                        
            except DicomStudy.DoesNotExist:
                context['initial_study_error'] = f'Study with ID {study_id} not found'
        
        # Add advanced viewer specific context
        context['viewer_version'] = '3.0'
        context['features'] = {
            'mpr': True,
            'volume_rendering': True,
            'ai_analysis': True,
            'advanced_measurements': True,
            'export_capabilities': True,
            'multi_viewport': True,
            'performance_monitoring': True
        }
        
        return context


# Admin functionality for facilities and radiologists
def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""
    def test_func(self):
        return self.request.user.is_superuser


class FacilityListView(AdminRequiredMixin, ListView):
    """Admin view to list all facilities"""
    model = Facility
    template_name = 'admin/facility_list.html'
    context_object_name = 'facilities'
    paginate_by = 20


class FacilityCreateView(AdminRequiredMixin, CreateView):
    """Admin view to create new facility"""
    model = Facility
    template_name = 'admin/facility_form.html'
    fields = ['name', 'address', 'phone', 'email', 'letterhead_logo']
    success_url = reverse_lazy('viewer:facility_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = True
        return context
    
    def post(self, request, *args, **kwargs):
        # Handle custom form submission with username/password
        form = self.get_form()
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if form.is_valid():
            # Create user account for facility
            if username and password:
                user = User.objects.create_user(
                    username=username,
                    email=form.cleaned_data['email'],
                    password=password
                )
                # Add to Facilities group
                facilities_group, created = Group.objects.get_or_create(name='Facilities')
                user.groups.add(facilities_group)
                
                # Save facility with user
                facility = form.save(commit=False)
                facility.user = user
                facility.save()
                
                messages.success(request, f'Facility "{facility.name}" created successfully with login credentials. AE Title: {facility.ae_title}')
                return redirect(self.success_url)
            else:
                messages.error(request, 'Username and password are required for facility creation.')
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)


class FacilityUpdateView(AdminRequiredMixin, UpdateView):
    """Admin view to update facility"""
    model = Facility
    template_name = 'admin/facility_form.html'
    fields = ['name', 'address', 'phone', 'email', 'letterhead_logo']
    success_url = reverse_lazy('viewer:facility_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create'] = False
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Facility "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


@login_required
@user_passes_test(is_admin)
def delete_facility(request, pk):
    """Admin view to delete facility"""
    facility = get_object_or_404(Facility, pk=pk)
    
    if request.method == 'POST':
        facility_name = facility.name
        facility.delete()
        messages.success(request, f'Facility "{facility_name}" deleted successfully.')
        return redirect('viewer:facility_list')
    
    # If not POST, redirect back to list
    return redirect('viewer:facility_list')


class RadiologistListView(AdminRequiredMixin, ListView):
    """Admin view to list all radiologists"""
    model = User
    template_name = 'admin/radiologist_list.html'
    context_object_name = 'radiologists'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(groups__name='Radiologists').distinct()


@login_required
@user_passes_test(is_admin)
def create_radiologist(request):
    """Admin view to create new radiologist"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'admin/radiologist_form.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Add to radiologists group
        radiologist_group, created = Group.objects.get_or_create(name='Radiologists')
        user.groups.add(radiologist_group)
        
        messages.success(request, f'Radiologist "{user.get_full_name()}" created successfully.')
        return redirect('viewer:radiologist_list')
    
    return render(request, 'admin/radiologist_form.html')


@login_required
@user_passes_test(is_admin)
def delete_radiologist(request, pk):
    """Admin view to delete radiologist"""
    radiologist = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        radiologist_name = radiologist.username
        radiologist.delete()
        messages.success(request, f'Radiologist "{radiologist_name}" deleted successfully.')
        return redirect('viewer:radiologist_list')
    
    # If not POST, redirect back to list
    return redirect('viewer:radiologist_list')


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_files(request):
    """Handle DICOM file uploads with comprehensive error handling and validation"""
    try:
        # Ensure media directories exist with proper permissions
        ensure_directories()
        
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        uploaded_files = []
        study = None
        errors = []
        
        for file in files:
            try:
                # More permissive file validation
                file_name = file.name.lower()
                file_size = file.size
                
                # Check file size - increased limit for large CT files with multiple series
                if file_size > 5 * 1024 * 1024 * 1024:  # 5GB per file (increased for CT scans)
                    errors.append(f"File {file.name} is too large (max 5GB per file)")
                    continue
                
                # More permissive DICOM file detection
                is_dicom_candidate = (
                    file_name.endswith(('.dcm', '.dicom')) or
                    file_name.endswith(('.dcm.gz', '.dicom.gz')) or
                    file_name.endswith(('.dcm.bz2', '.dicom.bz2')) or
                    file_name.endswith('.img') or  # Common DICOM format
                    file_name.endswith('.ima') or  # Common DICOM format
                    file_name.endswith('.raw') or  # Raw data
                    file_name.endswith('.dat') or  # Data files
                    file_name.endswith('.bin') or  # Binary files
                    '.' not in file.name or  # Files without extension
                    file_size > 512  # Files larger than 512 bytes (likely not text)
                )
                
                if not is_dicom_candidate:
                    errors.append(f"File {file.name} does not appear to be a DICOM file")
                    continue
                
                # Save file with unique name to avoid conflicts
                import uuid
                unique_filename = f"{uuid.uuid4()}_{file.name}"
                
                # Read file content once to avoid pointer issues
                file.seek(0)
                file_content = file.read()
                file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file_content))
                
                # Try to read DICOM data with multiple fallback methods
                dicom_data = None
                try:
                    # Method 1: Try reading from file path
                    if hasattr(default_storage, 'path'):
                        print(f"Trying to read DICOM from file path: {default_storage.path(file_path)}")
                        dicom_data = pydicom.dcmread(default_storage.path(file_path))
                    else:
                        # Method 2: Try reading from bytes
                        print(f"Trying to read DICOM from bytes for file: {file.name}")
                        dicom_data = pydicom.dcmread(io.BytesIO(file_content))
                except Exception as e1:
                    print(f"Method 1 failed for {file.name}: {e1}")
                    try:
                        # Method 3: Try reading with force=True (more permissive)
                        if hasattr(default_storage, 'path'):
                            print(f"Trying force=True from file path: {default_storage.path(file_path)}")
                            dicom_data = pydicom.dcmread(default_storage.path(file_path), force=True)
                        else:
                            print(f"Trying force=True from bytes for file: {file.name}")
                            dicom_data = pydicom.dcmread(io.BytesIO(file_content), force=True)
                    except Exception as e2:
                        print(f"Failed to read DICOM file {file.name}: {e1}, {e2}")
                        # Clean up the saved file
                        try:
                            default_storage.delete(file_path)
                        except:
                            pass
                        errors.append(f"Could not read DICOM data from {file.name}")
                        continue
                
                # Validate that we have essential DICOM tags
                if not dicom_data:
                    errors.append(f"No DICOM data found in {file.name}")
                    continue
                
                # Get study UID with fallback
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    # Try to generate a fallback study UID
                    study_uid = f"STUDY_{uuid.uuid4()}"
                    print(f"Generated fallback StudyInstanceUID for {file.name}: {study_uid}")
                
                # Create or update study with comprehensive data extraction
                if not study:
                    # Extract patient information with fallbacks
                    patient_name = 'Unknown'
                    if hasattr(dicom_data, 'PatientName'):
                        try:
                            patient_name = str(dicom_data.PatientName)
                        except:
                            patient_name = 'Unknown'
                    
                    patient_id = 'Unknown'
                    if hasattr(dicom_data, 'PatientID'):
                        try:
                            patient_id = str(dicom_data.PatientID)
                        except:
                            patient_id = 'Unknown'
                    
                    # Extract other fields with safe fallbacks
                    study_date = parse_dicom_date(getattr(dicom_data, 'StudyDate', None))
                    study_time = parse_dicom_time(getattr(dicom_data, 'StudyTime', None))
                    study_description = str(getattr(dicom_data, 'StudyDescription', ''))
                    modality = str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT'
                    institution_name = str(getattr(dicom_data, 'InstitutionName', ''))
                    accession_number = str(getattr(dicom_data, 'AccessionNumber', ''))
                    referring_physician = str(getattr(dicom_data, 'ReferringPhysicianName', ''))
                    
                    study, created = DicomStudy.objects.get_or_create(
                        study_instance_uid=study_uid,
                        defaults={
                            'patient_name': patient_name,
                            'patient_id': patient_id,
                            'study_date': study_date,
                            'study_time': study_time,
                            'study_description': study_description,
                            'modality': modality,
                            'institution_name': institution_name,
                            'uploaded_by': request.user if request.user.is_authenticated else None,
                            'facility': request.user.facility if hasattr(request.user, 'facility') else None,
                            'accession_number': accession_number,
                            'referring_physician': referring_physician,
                        }
                    )
                    
                    # Create worklist entry if study was created
                    if created:
                        try:
                            # Get or create a default facility if none exists
                            facility = study.facility
                            if not facility:
                                facility, _ = Facility.objects.get_or_create(
                                    name="Default Facility",
                                    defaults={
                                        'address': 'Unknown',
                                        'phone': 'Unknown',
                                        'email': 'unknown@facility.com'
                                    }
                                )
                                # Update the study with the facility
                                study.facility = facility
                                study.save()
                            
                            WorklistEntry.objects.create(
                                patient_name=study.patient_name,
                                patient_id=study.patient_id,
                                accession_number=study.accession_number or f"ACC{study.id:06d}",
                                scheduled_station_ae_title="UPLOAD",
                                scheduled_procedure_step_start_date=study.study_date or datetime.now().date(),
                                scheduled_procedure_step_start_time=study.study_time or datetime.now().time(),
                                modality=study.modality,
                                scheduled_performing_physician=study.referring_physician or "Unknown",
                                procedure_description=study.study_description,
                                facility=facility,
                                study=study,
                                status='scheduled'
                            )
                            print(f"Created worklist entry for study {study.id}")
                        except Exception as e:
                            print(f"Error creating worklist entry: {e}")
                            import traceback
                            traceback.print_exc()
                
                # Create or get series with fallback UID
                series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                if not series_uid:
                    series_uid = f"SERIES_{uuid.uuid4()}"
                    print(f"Generated fallback SeriesInstanceUID for {file.name}: {series_uid}")
                
                series, created = DicomSeries.objects.get_or_create(
                    study=study,
                    series_instance_uid=series_uid,
                    defaults={
                        'series_number': int(dicom_data.get('SeriesNumber', 0)),
                        'series_description': str(getattr(dicom_data, 'SeriesDescription', '')),
                        'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                    }
                )
                
                # Create image with fallback UID
                image_instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
                if not image_instance_uid:
                    image_instance_uid = f"IMAGE_{uuid.uuid4()}"
                    print(f"Generated fallback SOPInstanceUID for {file.name}: {image_instance_uid}")
                
                # Extract image data with safe fallbacks
                rows = 0
                columns = 0
                bits_allocated = 16
                samples_per_pixel = 1
                photometric_interpretation = 'MONOCHROME2'
                
                if hasattr(dicom_data, 'Rows'):
                    try:
                        rows = int(dicom_data.Rows)
                    except:
                        rows = 0
                
                if hasattr(dicom_data, 'Columns'):
                    try:
                        columns = int(dicom_data.Columns)
                    except:
                        columns = 0
                
                if hasattr(dicom_data, 'BitsAllocated'):
                    try:
                        bits_allocated = int(dicom_data.BitsAllocated)
                    except:
                        bits_allocated = 16
                
                if hasattr(dicom_data, 'SamplesPerPixel'):
                    try:
                        samples_per_pixel = int(dicom_data.SamplesPerPixel)
                    except:
                        samples_per_pixel = 1
                
                if hasattr(dicom_data, 'PhotometricInterpretation'):
                    try:
                        photometric_interpretation = str(dicom_data.PhotometricInterpretation)
                    except:
                        photometric_interpretation = 'MONOCHROME2'
                
                # Parse pixel spacing
                pixel_spacing_x = None
                pixel_spacing_y = None
                if hasattr(dicom_data, 'PixelSpacing'):
                    try:
                        pixel_spacing = dicom_data.PixelSpacing
                        if isinstance(pixel_spacing, (list, tuple)) and len(pixel_spacing) >= 2:
                            pixel_spacing_x = float(pixel_spacing[0])
                            pixel_spacing_y = float(pixel_spacing[1])
                    except:
                        pass
                
                # Improved window/level defaults for better visibility
                window_center = 40
                window_width = 400
                
                if hasattr(dicom_data, 'WindowCenter'):
                    try:
                        wc = dicom_data.WindowCenter
                        if isinstance(wc, (list, tuple)):
                            window_center = float(wc[0])
                        else:
                            window_center = float(wc)
                    except:
                        window_center = 40
                
                if hasattr(dicom_data, 'WindowWidth'):
                    try:
                        ww = dicom_data.WindowWidth
                        if isinstance(ww, (list, tuple)):
                            window_width = float(ww[0])
                        else:
                            window_width = float(ww)
                    except:
                        window_width = 400
                
                image, created = DicomImage.objects.get_or_create(
                    series=series,
                    sop_instance_uid=image_instance_uid,
                    defaults={
                        'image_number': int(dicom_data.get('InstanceNumber', 0)),
                        'file_path': file_path,
                        'rows': rows,
                        'columns': columns,
                        'bits_allocated': bits_allocated,
                        'samples_per_pixel': samples_per_pixel,
                        'photometric_interpretation': photometric_interpretation,
                        'pixel_spacing': str(getattr(dicom_data, 'PixelSpacing', '')),
                        'pixel_spacing_x': pixel_spacing_x,
                        'pixel_spacing_y': pixel_spacing_y,
                        'slice_thickness': float(getattr(dicom_data, 'SliceThickness', 0)),
                        'window_center': window_center,
                        'window_width': window_width,
                    }
                )
                
                if created:
                    uploaded_files.append(file.name)
                else:
                    # Image already exists, but still add to uploaded files with a note
                    uploaded_files.append(f"{file.name} (already exists)")
                    # Clean up the duplicate file we just saved
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
                
            except Exception as e:
                print(f"Error processing file {file.name}: {e}")
                errors.append(f"Error processing {file.name}: {str(e)}")
                if 'file_path' in locals():
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
                continue
        
        # Prepare response
        if not uploaded_files:
            error_message = 'No valid DICOM files were uploaded'
            if errors:
                error_message += f'. Errors: {"; ".join(errors[:5])}'  # Limit error messages
            return JsonResponse({'error': error_message}, status=400)
        
        response_data = {
            'message': f'Uploaded {len(uploaded_files)} files successfully',
            'uploaded_files': uploaded_files,
            'study_id': study.id if study else None
        }
        
        if errors:
            response_data['warnings'] = errors[:5]  # Include warnings for partial success
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Unexpected error in upload_dicom_files: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error notification
        create_system_error_notification(f"DICOM upload error: {str(e)}", request.user)
        
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_folder(request):
    """Handle DICOM folder uploads with comprehensive error handling and validation"""
    try:
        # Ensure media directories exist with proper permissions
        ensure_directories()
        
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        uploaded_files = []
        studies = {}
        errors = []
        
        # Group files by study
        for file in files:
            try:
                # More comprehensive file validation
                file_name = file.name.lower()
                file_size = file.size
                
                # Check file size - increased limit for large CT files with multiple series
                if file_size > 5 * 1024 * 1024 * 1024:  # 5GB per file (increased for CT scans)
                    errors.append(f"File {file.name} is too large (max 5GB per file)")
                    continue
                
                # Accept any file that might be DICOM (more permissive)
                is_dicom_candidate = (
                    file_name.endswith(('.dcm', '.dicom')) or
                    file_name.endswith(('.dcm.gz', '.dicom.gz')) or
                    file_name.endswith(('.dcm.bz2', '.dicom.bz2')) or
                    '.' not in file.name or  # Files without extension
                    file_name.endswith('.img') or  # Common DICOM format
                    file_name.endswith('.ima') or  # Common DICOM format
                    file_name.endswith('.raw') or  # Raw data
                    file_size > 1024  # Files larger than 1KB (likely not text)
                )
                
                if not is_dicom_candidate:
                    errors.append(f"File {file.name} does not appear to be a DICOM file")
                    continue
                
                # Save file with unique name to avoid conflicts
                import uuid
                unique_filename = f"{uuid.uuid4()}_{file.name}"
                file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                
                # Try to read DICOM data with multiple fallback methods
                dicom_data = None
                try:
                    # Method 1: Try reading from file path
                    dicom_data = pydicom.dcmread(default_storage.path(file_path))
                except Exception as e1:
                    try:
                        # Method 2: Try reading from file object
                        file.seek(0)  # Reset file pointer
                        dicom_data = pydicom.dcmread(file)
                        # Re-save the file after successful read
                        file.seek(0)
                        file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                    except Exception as e2:
                        try:
                            # Method 3: Try reading as bytes
                            file.seek(0)
                            file_bytes = file.read()
                            dicom_data = pydicom.dcmread(file_bytes)
                            # Save the bytes
                            file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file_bytes))
                        except Exception as e3:
                            try:
                                # Method 4: Try reading with force=True (handles missing DICM header)
                                file.seek(0)
                                file_bytes = file.read()
                                dicom_data = pydicom.dcmread(io.BytesIO(file_bytes), force=True)
                                # Save the bytes
                                file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file_bytes))
                            except Exception as e4:
                                print(f"Failed to read DICOM file {file.name}: {e1}, {e2}, {e3}, {e4}")
                                # Clean up the saved file
                                try:
                                    default_storage.delete(file_path)
                                except:
                                    pass
                            errors.append(f"Could not read DICOM data from {file.name}")
                            continue
                
                # Validate that we have essential DICOM tags
                if not dicom_data:
                    errors.append(f"No DICOM data found in {file.name}")
                    continue
                
                # Get study UID with fallback
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    # Try to generate a fallback study UID
                    study_uid = f"STUDY_{uuid.uuid4()}"
                    print(f"Generated fallback StudyInstanceUID for {file.name}: {study_uid}")
                
                # Group by study
                if study_uid not in studies:
                    studies[study_uid] = {
                        'files': [],
                        'dicom_data': [],
                        'file_paths': []
                    }
                
                studies[study_uid]['files'].append(file.name)
                studies[study_uid]['dicom_data'].append(dicom_data)
                studies[study_uid]['file_paths'].append(file_path)
                
            except Exception as e:
                print(f"Error processing file {file.name}: {e}")
                errors.append(f"Error processing {file.name}: {str(e)}")
                if 'file_path' in locals():
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
                continue
        
        # Process each study
        for study_uid, study_data in studies.items():
            try:
                # Create study from first file
                first_dicom = study_data['dicom_data'][0]
                
                # Extract patient information with fallbacks
                patient_name = 'Unknown'
                if hasattr(first_dicom, 'PatientName'):
                    try:
                        patient_name = str(first_dicom.PatientName)
                    except:
                        patient_name = 'Unknown'
                
                patient_id = 'Unknown'
                if hasattr(first_dicom, 'PatientID'):
                    try:
                        patient_id = str(first_dicom.PatientID)
                    except:
                        patient_id = 'Unknown'
                
                # Extract other fields with safe fallbacks
                study_date = parse_dicom_date(getattr(first_dicom, 'StudyDate', None))
                study_time = parse_dicom_time(getattr(first_dicom, 'StudyTime', None))
                study_description = str(getattr(first_dicom, 'StudyDescription', ''))
                modality = str(first_dicom.Modality) if hasattr(first_dicom, 'Modality') else 'OT'
                institution_name = str(getattr(first_dicom, 'InstitutionName', ''))
                accession_number = str(getattr(first_dicom, 'AccessionNumber', ''))
                referring_physician = str(getattr(first_dicom, 'ReferringPhysicianName', ''))
                
                study, created = DicomStudy.objects.get_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient_name': patient_name,
                        'patient_id': patient_id,
                        'study_date': study_date,
                        'study_time': study_time,
                        'study_description': study_description,
                        'modality': modality,
                        'institution_name': institution_name,
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                        'facility': request.user.facility if hasattr(request.user, 'facility') else None,
                        'accession_number': accession_number,
                        'referring_physician': referring_physician,
                    }
                )
                
                # Create notifications for new study uploads using the new system
                if created:
                    notify_new_study_upload(study, request.user)
                
                # Create worklist entry if study was created
                if created:
                    try:
                        # Get or create a default facility if none exists
                        facility = study.facility
                        if not facility:
                            facility, _ = Facility.objects.get_or_create(
                                name="Default Facility",
                                defaults={
                                    'address': 'Unknown',
                                    'phone': 'Unknown',
                                    'email': 'unknown@facility.com'
                                }
                            )
                            # Update the study with the facility
                            study.facility = facility
                            study.save()
                        
                        WorklistEntry.objects.create(
                            patient_name=study.patient_name,
                            patient_id=study.patient_id,
                            accession_number=study.accession_number or f"ACC{study.id:06d}",
                            scheduled_station_ae_title="UPLOAD",
                            scheduled_procedure_step_start_date=study.study_date or datetime.now().date(),
                            scheduled_procedure_step_start_time=study.study_time or datetime.now().time(),
                            modality=study.modality,
                            scheduled_performing_physician=study.referring_physician or "Unknown",
                            procedure_description=study.study_description,
                            facility=facility,
                            study=study,
                            status='scheduled'
                        )
                    except Exception as e:
                        print(f"Error creating worklist entry: {e}")
                
                # Process each file in the study
                for i, dicom_data in enumerate(study_data['dicom_data']):
                    try:
                        # Create or get series with fallback UID
                        series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                        if not series_uid:
                            series_uid = f"SERIES_{uuid.uuid4()}"
                            print(f"Generated fallback SeriesInstanceUID for {study_data['files'][i]}: {series_uid}")
                        
                        series, created = DicomSeries.objects.get_or_create(
                            study=study,
                            series_instance_uid=series_uid,
                            defaults={
                                'series_number': int(dicom_data.get('SeriesNumber', 0)),
                                'series_description': str(getattr(dicom_data, 'SeriesDescription', '')),
                                'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                            }
                        )
                        
                        # Create image with fallback UID
                        image_instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
                        if not image_instance_uid:
                            image_instance_uid = f"IMAGE_{uuid.uuid4()}"
                            print(f"Generated fallback SOPInstanceUID for {study_data['files'][i]}: {image_instance_uid}")
                        
                        # Extract image data with safe fallbacks
                        rows = 0
                        columns = 0
                        bits_allocated = 16
                        samples_per_pixel = 1
                        photometric_interpretation = 'MONOCHROME2'
                        
                        if hasattr(dicom_data, 'Rows'):
                            try:
                                rows = int(dicom_data.Rows)
                            except:
                                rows = 0
                        
                        if hasattr(dicom_data, 'Columns'):
                            try:
                                columns = int(dicom_data.Columns)
                            except:
                                columns = 0
                        
                        if hasattr(dicom_data, 'BitsAllocated'):
                            try:
                                bits_allocated = int(dicom_data.BitsAllocated)
                            except:
                                bits_allocated = 16
                        
                        if hasattr(dicom_data, 'SamplesPerPixel'):
                            try:
                                samples_per_pixel = int(dicom_data.SamplesPerPixel)
                            except:
                                samples_per_pixel = 1
                        
                        if hasattr(dicom_data, 'PhotometricInterpretation'):
                            try:
                                photometric_interpretation = str(dicom_data.PhotometricInterpretation)
                            except:
                                photometric_interpretation = 'MONOCHROME2'
                        
                        # Parse pixel spacing (add missing handling)
                        pixel_spacing_x = None
                        pixel_spacing_y = None
                        if hasattr(dicom_data, 'PixelSpacing'):
                            try:
                                pixel_spacing = dicom_data.PixelSpacing
                                if isinstance(pixel_spacing, (list, tuple)) and len(pixel_spacing) >= 2:
                                    pixel_spacing_x = float(pixel_spacing[0])
                                    pixel_spacing_y = float(pixel_spacing[1])
                            except Exception:
                                pass
                        
                        image, created = DicomImage.objects.get_or_create(
                            series=series,
                            sop_instance_uid=image_instance_uid,
                            defaults={
                                'image_number': int(dicom_data.get('InstanceNumber', 0)),
                                'file_path': study_data['file_paths'][i],
                                'rows': rows,
                                'columns': columns,
                                'bits_allocated': bits_allocated,
                                'samples_per_pixel': samples_per_pixel,
                                'photometric_interpretation': photometric_interpretation,
                                'pixel_spacing': str(getattr(dicom_data, 'PixelSpacing', '')),
                                'pixel_spacing_x': pixel_spacing_x,
                                'pixel_spacing_y': pixel_spacing_y,
                                'slice_thickness': float(getattr(dicom_data, 'SliceThickness', 0)),
                                'window_center': float(getattr(dicom_data, 'WindowCenter', 40)),
                                'window_width': float(getattr(dicom_data, 'WindowWidth', 400)),
                            }
                        )
                        
                        if created:
                            uploaded_files.append(study_data['files'][i])
                        else:
                            # Image already exists, but still add to uploaded files with a note
                            uploaded_files.append(f"{study_data['files'][i]} (already exists)")
                            # Clean up the duplicate file we just saved
                            try:
                                default_storage.delete(study_data['file_paths'][i])
                            except:
                                pass
                            
                    except Exception as e:
                        print(f"Error processing image in study {study_uid}: {e}")
                        errors.append(f"Error processing {study_data['files'][i]}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Error processing study {study_uid}: {e}")
                errors.append(f"Error processing study {study_uid}: {str(e)}")
                continue
        
        # Prepare response
        if not uploaded_files:
            error_message = 'No valid DICOM files were uploaded'
            if errors:
                error_message += f'. Errors: {"; ".join(errors[:5])}'  # Limit error messages
            return JsonResponse({'error': error_message}, status=400)
        
        response_data = {
            'message': f'Uploaded {len(uploaded_files)} files from {len(studies)} study(ies)',
            'uploaded_files': uploaded_files,
            'study_id': study.id if study else None
        }
        
        if errors:
            response_data['warnings'] = errors[:5]  # Include warnings for partial success
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Unexpected error in upload_dicom_folder: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error notification
        create_system_error_notification(f"DICOM folder upload error: {str(e)}", request.user)
        
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_upload_progress(request, upload_id):
    """Get upload progress for background uploads"""
    try:
        progress = cache.get(f'upload_progress_{upload_id}')
        if progress is None:
            return JsonResponse({'error': 'Upload not found or expired'}, status=404)
        
        return JsonResponse(progress)
    except Exception as e:
        return JsonResponse({'error': f'Error getting progress: {str(e)}'}, status=500)


@api_view(['GET'])
def get_upload_result(request, upload_id):
    """Get final upload result for background uploads"""
    try:
        result = cache.get(f'upload_result_{upload_id}')
        if result is None:
            return JsonResponse({'error': 'Upload result not found or expired'}, status=404)
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': f'Error getting result: {str(e)}'}, status=500)


@api_view(['GET'])
def get_studies(request):
    """Get all studies based on user permissions"""
    # Use the new access control system
    studies = get_user_study_queryset(request.user)[:20]
    
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_study_images(request, study_id):
    """Get all images for a study"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        
        # Check if user can access this study (temporarily disabled for debugging)
        # if not can_access_study(request.user, study):
        #     return Response({'error': 'Access denied. You do not have permission to view this study.'}, status=403)
        images = DicomImage.objects.filter(series__study=study).order_by('series__series_number', 'instance_number')
        
        images_data = []
        for image in images:
            image_data = {
                'id': image.id,
                'instance_number': int(image.instance_number) if image.instance_number is not None else None,
                'series_number': int(image.series.series_number) if image.series and image.series.series_number is not None else None,
                'series_description': image.series.series_description,
                'rows': int(image.rows) if image.rows is not None else None,
                'columns': int(image.columns) if image.columns is not None else None,
                'pixel_spacing_x': float(image.pixel_spacing_x) if image.pixel_spacing_x is not None else None,
                'pixel_spacing_y': float(image.pixel_spacing_y) if image.pixel_spacing_y is not None else None,
                'slice_thickness': float(image.slice_thickness) if image.slice_thickness is not None else None,
                'window_width': float(image.window_width) if image.window_width is not None else None,
                'window_center': float(image.window_center) if image.window_center is not None else None,
            }
            images_data.append(image_data)
        
        return Response({
            'study': {
                'id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'study_date': study.study_date,
                'modality': study.modality,
                'study_description': study.study_description,
                'institution_name': study.institution_name,
                'accession_number': study.accession_number,
            },
            'images': images_data
        })
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)



def generate_synthetic_image(image, window_width=1500, window_level=-600, inverted=False):
    """Generate synthetic image for testing when real DICOM files are not available"""
    try:
        import numpy as np
        from PIL import Image as PILImage
        import io
        import base64
        
        width, height = 512, 512
        
        # Create different patterns based on image ID
        x = np.linspace(-1, 1, width)
        y = np.linspace(-1, 1, height)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        if image.id % 3 == 0:
            # Concentric circles
            image_array = ((np.sin(R * 10) + 1) * 127.5).astype(np.uint8)
        elif image.id % 3 == 1:
            # Grid pattern
            image_array = ((np.sin(X * 20) * np.sin(Y * 20) + 1) * 127.5).astype(np.uint8)
        else:
            # Radial gradient
            image_array = ((1 - R) * 255).clip(0, 255).astype(np.uint8)
        
        # Apply window/level
        ww = float(window_width) if window_width else 1500
        wl = float(window_level) if window_level else -600
        window_min = wl - ww / 2
        window_max = wl + ww / 2
        
        image_array = image_array.astype(np.float32)
        image_array = (image_array - window_min) / (window_max - window_min) * 255
        image_array = np.clip(image_array, 0, 255).astype(np.uint8)
        
        # Apply inversion
        if inverted:
            image_array = 255 - image_array
        
        # Convert to PIL Image
        pil_image = PILImage.fromarray(image_array, mode='L')
        
        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}"
        
    except Exception as e:
        print(f"Error generating synthetic image: {e}")
        return generate_placeholder_image()

def generate_placeholder_image():
    """Generate a simple placeholder image"""
    try:
        import numpy as np
        from PIL import Image as PILImage
        import io
        import base64
        
        width, height = 512, 512
        image_array = np.zeros((height, width), dtype=np.uint8)
        
        # Create a simple gradient
        for i in range(height):
            for j in range(width):
                image_array[i, j] = int((i + j) / (height + width) * 255)
        
        pil_image = PILImage.fromarray(image_array, mode='L')
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}"
    except Exception as e:
        print(f"Error creating placeholder: {e}")
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@api_view(['GET'])
def get_image_data(request, image_id):
    """Get processed image data with superior diagnostic quality for all modalities"""
    try:
        print(f"Attempting to get diagnostic image data for image_id: {image_id}")
        image = DicomImage.objects.get(id=image_id)
        
        # Check if user can access this image's study (temporarily disabled for debugging)
        # if not can_access_study(request.user, image.series.study):
        #     return Response({'error': 'Access denied. You do not have permission to view this image.'}, status=403)
        print(f"Found image: {image}, file_path: {image.file_path}")
        
        # Get query parameters with diagnostic-grade defaults
        window_width = request.GET.get('window_width', image.window_width or 1500)  # Optimal for lung window
        window_level = request.GET.get('window_level', image.window_center or -600)  # Optimal for lung level
        inverted = request.GET.get('inverted', 'false').lower() == 'true'
        high_quality = request.GET.get('high_quality', 'true').lower() == 'true'  # Always use diagnostic quality
        resolution_factor = float(request.GET.get('resolution_factor', '2.0'))  # Higher resolution for diagnostic clarity
        density_enhancement = request.GET.get('density_enhancement', 'true').lower() == 'true'  # Always enable for diagnostic quality
        contrast_boost = float(request.GET.get('contrast_boost', '1.5'))  # Enhanced contrast for diagnostic imaging
        
        # Convert to appropriate types
        if window_width:
            try:
                window_width = float(window_width)
            except (ValueError, TypeError):
                window_width = 1500  # Default to lung window
        if window_level:
            try:
                window_level = float(window_level)
            except (ValueError, TypeError):
                window_level = -600  # Default to lung level
        
        print(f"Processing diagnostic image with WW: {window_width}, WL: {window_level}, inverted: {inverted}, high_quality: {high_quality}")
        
        # Always use diagnostic-grade processing for superior quality
        image_base64 = image.get_enhanced_processed_image_base64(
            window_width, window_level, inverted,
            resolution_factor=resolution_factor,
            density_enhancement=density_enhancement,
            contrast_boost=contrast_boost
        )
        
        if image_base64:
            print(f"Successfully processed diagnostic image {image_id} with superior quality")
            return Response({
                'image_data': image_base64,
                'metadata': {
                    'rows': image.rows,
                    'columns': image.columns,
                    'pixel_spacing_x': image.pixel_spacing_x,
                    'pixel_spacing_y': image.pixel_spacing_y,
                    'slice_thickness': image.slice_thickness,
                    'window_width': image.window_width,
                    'window_center': image.window_center,
                    'modality': image.series.modality,
                    'body_part': image.series.body_part_examined,
                    'diagnostic_quality': True,
                    'tissue_differentiation': True,
                    'resolution_enhanced': True
                }
            })
        else:
            # Generate fallback image instead of returning 500 error
            print(f"Failed to process diagnostic image {image_id}, generating fallback")
            try:
                fallback_image = image.generate_synthetic_image(window_width, window_level, inverted)
                if fallback_image:
                    return Response({
                        'image_data': fallback_image,
                        'metadata': {
                            'rows': 512,
                            'columns': 512,
                            'pixel_spacing_x': 1.0,
                            'pixel_spacing_y': 1.0,
                            'slice_thickness': 1.0,
                            'window_width': window_width or 400,
                            'window_center': window_level or 40,
                            'modality': image.series.modality if image.series else 'CT',
                            'body_part': image.series.body_part_examined if image.series else 'Unknown',
                            'diagnostic_quality': False,
                            'tissue_differentiation': False,
                            'resolution_enhanced': False,
                            'is_fallback': True
                        }
                    })
            except Exception as fallback_error:
                print(f"Fallback image generation failed: {fallback_error}")
            
            return Response({'error': 'Could not process image - file may be missing or corrupted'}, status=404)
            
    except DicomImage.DoesNotExist:
        print(f"Image not found: {image_id}")
        return Response({'error': 'Image not found'}, status=404)
    except Exception as e:
        print(f"Unexpected error processing diagnostic image {image_id}: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def save_measurement(request):
    """Save measurement with improved calculations"""
    try:
        data = json.loads(request.body)
        image = DicomImage.objects.get(id=data['image_id'])
        
        # Check if user can access this image's study
        if not can_access_study(request.user, image.series.study):
            return JsonResponse({'error': 'Access denied. You do not have permission to access this image.'}, status=403)
        
        measurement_type = data.get('type', 'line')
        coordinates = data['coordinates']
        
        # Calculate measurement value based on type
        if measurement_type == 'line':
            # Line distance measurement
            start = coordinates[0]
            end = coordinates[1]
            pixel_distance = np.sqrt((end['x'] - start['x'])**2 + (end['y'] - start['y'])**2)
            
            # Convert to real-world units if pixel spacing available
            if image.pixel_spacing_x and image.pixel_spacing_y:
                avg_spacing = (image.pixel_spacing_x + image.pixel_spacing_y) / 2
                real_distance = pixel_distance * avg_spacing  # in mm
                unit = data.get('unit', 'mm')
                
                if unit == 'cm':
                    value = real_distance / 10.0
                else:
                    value = real_distance
            else:
                value = pixel_distance
                unit = 'px'
                
        elif measurement_type == 'area':
            # Area measurement for polygons
            points = coordinates
            if len(points) >= 3:
                # Calculate area using shoelace formula
                area_px = 0.5 * abs(sum(
                    points[i]['x'] * (points[(i + 1) % len(points)]['y'] - points[(i - 1) % len(points)]['y'])
                    for i in range(len(points))
                ))
                
                if image.pixel_spacing_x and image.pixel_spacing_y:
                    pixel_area_mm2 = image.pixel_spacing_x * image.pixel_spacing_y
                    value = area_px * pixel_area_mm2  # in mm²
                    unit = 'mm²'
                else:
                    value = area_px
                    unit = 'px²'
            else:
                value = 0
                unit = 'px²'
                
        elif measurement_type == 'volume':
            # Volume measurement for 3D regions
            # This is a simplified calculation - would need slice data for accurate volume
            area = data.get('area', 0)  # Area from contour
            if image.slice_thickness and image.pixel_spacing_x and image.pixel_spacing_y:
                pixel_area_mm2 = image.pixel_spacing_x * image.pixel_spacing_y
                volume_mm3 = area * pixel_area_mm2 * image.slice_thickness
                unit = data.get('unit', 'mm³')
                
                if unit == 'cm³':
                    value = volume_mm3 / 1000.0  # Convert mm³ to cm³
                else:
                    value = volume_mm3
            else:
                value = area * (image.slice_thickness or 1)
                unit = 'px³'
                
        elif measurement_type == 'angle':
            # Angle measurement
            if len(coordinates) >= 3:
                p1, vertex, p2 = coordinates[:3]
                
                # Calculate vectors
                v1 = np.array([p1['x'] - vertex['x'], p1['y'] - vertex['y']])
                v2 = np.array([p2['x'] - vertex['x'], p2['y'] - vertex['y']])
                
                # Calculate angle
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle_rad = np.arccos(np.clip(cos_angle, -1.0, 1.0))
                value = np.degrees(angle_rad)
                unit = '°'
            else:
                value = 0
                unit = '°'
        else:
            value = data.get('value', 0)
            unit = data.get('unit', 'px')
        
        # Save measurement
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=measurement_type,
            coordinates=coordinates,
            value=value,
            unit=unit,
            notes=data.get('notes', ''),
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'id': measurement.id,
            'value': value,
            'unit': unit,
            'type': measurement_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def measure_hu(request):
    """Measure Hounsfield Units with proper radiological reference data following global standards"""
    try:
        data = json.loads(request.body)
        image = DicomImage.objects.get(id=data['image_id'])
        
        # Load DICOM data
        dicom_data = image.load_dicom_data()
        if not dicom_data:
            return JsonResponse({'error': 'Could not load DICOM data. The file may be corrupted or in an unsupported format.'}, status=400)
        
        pixel_array = image.get_pixel_array()
        if pixel_array is None:
            return JsonResponse({'error': 'Could not get pixel data'}, status=400)
        
        # Get ellipse coordinates
        x0, y0 = int(data['x0']), int(data['y0'])
        x1, y1 = int(data['x1']), int(data['y1'])
        
        # Create ellipse mask
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2
        a = abs(x1 - x0) / 2  # semi-major axis
        b = abs(y1 - y0) / 2  # semi-minor axis
        
        # Create coordinate grids
        y_coords, x_coords = np.ogrid[:pixel_array.shape[0], :pixel_array.shape[1]]
        
        # Ellipse equation: ((x-cx)/a)² + ((y-cy)/b)² <= 1
        mask = ((x_coords - center_x) / a) ** 2 + ((y_coords - center_y) / b) ** 2 <= 1
        
        # Extract pixel values within ellipse
        roi_pixels = pixel_array[mask]
        
        if len(roi_pixels) == 0:
            return JsonResponse({'error': 'No pixels in ROI'}, status=400)
        
        # Convert to Hounsfield Units using standard DICOM rescaling
        rescale_slope = getattr(dicom_data, 'RescaleSlope', 1)
        rescale_intercept = getattr(dicom_data, 'RescaleIntercept', 0)
        
        # Apply rescaling to get HU values
        hu_values = roi_pixels * rescale_slope + rescale_intercept
        
        # Calculate comprehensive statistics
        mean_hu = float(np.mean(hu_values))
        min_hu = float(np.min(hu_values))
        max_hu = float(np.max(hu_values))
        std_hu = float(np.std(hu_values))
        median_hu = float(np.median(hu_values))
        
        # Calculate confidence intervals (95% CI)
        confidence_interval = stats.t.interval(0.95, len(hu_values)-1, 
                                            loc=mean_hu, scale=std_hu/np.sqrt(len(hu_values)))
        ci_lower = float(confidence_interval[0])
        ci_upper = float(confidence_interval[1])
        
        # Calculate coefficient of variation
        cv = (std_hu / mean_hu) * 100 if mean_hu != 0 else 0
        
        # Get anatomical region from DICOM data if available
        body_part = getattr(dicom_data, 'BodyPartExamined', '').upper()
        study_description = getattr(dicom_data, 'StudyDescription', '').upper()
        
        # Enhanced radiological interpretation with anatomical context
        interpretation_data = get_enhanced_hu_interpretation(
            mean_hu, body_part, study_description, ci_lower, ci_upper
        )
        
        # Calculate ROI area in mm² if pixel spacing available
        pixel_spacing_x = getattr(dicom_data, 'PixelSpacing', [1, 1])[0] if hasattr(dicom_data, 'PixelSpacing') else 1
        pixel_spacing_y = getattr(dicom_data, 'PixelSpacing', [1, 1])[1] if hasattr(dicom_data, 'PixelSpacing') else 1
        roi_area_mm2 = len(roi_pixels) * pixel_spacing_x * pixel_spacing_y
        
        # Save measurement with enhanced data
        measurement = Measurement.objects.create(
            image=image,
            measurement_type='ellipse',
            coordinates=[{'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}],
            value=mean_hu,
            unit='HU',
            hounsfield_mean=mean_hu,
            hounsfield_min=min_hu,
            hounsfield_max=max_hu,
            hounsfield_std=std_hu,
            notes=interpretation_data['detailed_notes'],
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'mean_hu': mean_hu,
            'min_hu': min_hu,
            'max_hu': max_hu,
            'std_hu': std_hu,
            'median_hu': median_hu,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'coefficient_of_variation': cv,
            'pixel_count': len(roi_pixels),
            'roi_area_mm2': roi_area_mm2,
            'interpretation': interpretation_data['primary_interpretation'],
            'tissue_type': interpretation_data['tissue_type'],
            'clinical_significance': interpretation_data['clinical_significance'],
            'anatomical_context': interpretation_data['anatomical_context'],
            'reference_range': interpretation_data['reference_range'],
            'measurement_id': measurement.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_enhanced_hu_interpretation(hu_value, body_part='', study_description='', ci_lower=None, ci_upper=None):
    """
    Provide comprehensive radiological interpretation based on Hounsfield Unit values
    Following global radiological standards and anatomical context
    """
    
    # Standard HU reference ranges based on global radiological standards
    HU_RANGES = {
        'air_gas': (-1000, -900),
        'lung_tissue': (-900, -500),
        'fat_tissue': (-500, -100),
        'fat_soft_interface': (-100, -50),
        'soft_tissue_low': (-50, 0),
        'water_csf': (0, 20),
        'muscle': (20, 40),
        'liver_spleen': (40, 80),
        'kidney': (80, 120),
        'soft_tissue_dense': (120, 200),
        'calcification_contrast': (200, 400),
        'bone_cancellous': (400, 1000),
        'bone_cortical': (1000, 2000),
        'metal_dense': (2000, 3000)
    }
    
    # Anatomical region-specific reference values
    ANATOMICAL_REFERENCE = {
        'HEAD': {
            'brain_white_matter': (20, 30),
            'brain_gray_matter': (35, 45),
            'csf': (0, 15),
            'bone_skull': (400, 1000),
            'air_sinuses': (-1000, -900)
        },
        'CHEST': {
            'lung_air': (-1000, -900),
            'lung_tissue': (-900, -500),
            'heart_muscle': (30, 50),
            'blood': (30, 45),
            'bone_rib': (400, 1000)
        },
        'ABDOMEN': {
            'liver': (40, 60),
            'spleen': (40, 60),
            'kidney': (30, 50),
            'fat': (-100, -50),
            'muscle': (20, 40),
            'bone_vertebra': (400, 1000)
        },
        'PELVIS': {
            'bladder': (0, 20),
            'prostate': (30, 50),
            'uterus': (30, 50),
            'bone_pelvis': (400, 1000)
        }
    }
    
    # Determine primary tissue type
    tissue_type = 'Unknown'
    for tissue, (min_val, max_val) in HU_RANGES.items():
        if min_val <= hu_value < max_val:
            tissue_type = tissue.replace('_', ' ').title()
            break
    
    # Anatomical context analysis
    anatomical_context = 'General'
    clinical_significance = 'Normal tissue density'
    
    if body_part in ANATOMICAL_REFERENCE:
        anatomical_context = body_part
        region_refs = ANATOMICAL_REFERENCE[body_part]
        
        for tissue, (min_val, max_val) in region_refs.items():
            if min_val <= hu_value <= max_val:
                tissue_type = tissue.replace('_', ' ').title()
                anatomical_context = f"{body_part} - {tissue_type}"
                break
    
    # Clinical significance based on HU value and anatomical context
    if hu_value < -900:
        clinical_significance = "Air/gas - Normal in lungs, abnormal elsewhere"
    elif -900 <= hu_value < -500:
        clinical_significance = "Lung tissue - Normal pulmonary parenchyma"
    elif -500 <= hu_value < -100:
        clinical_significance = "Fat tissue - Normal adipose tissue"
    elif -100 <= hu_value < 0:
        clinical_significance = "Soft tissue interface - Normal tissue boundaries"
    elif 0 <= hu_value < 20:
        clinical_significance = "Water/CSF - Normal fluid density"
    elif 20 <= hu_value < 40:
        clinical_significance = "Muscle tissue - Normal muscle density"
    elif 40 <= hu_value < 80:
        clinical_significance = "Solid organs - Normal liver/spleen density"
    elif 80 <= hu_value < 120:
        clinical_significance = "Kidney tissue - Normal renal parenchyma"
    elif 120 <= hu_value < 200:
        clinical_significance = "Dense soft tissue - May indicate pathology"
    elif 200 <= hu_value < 400:
        clinical_significance = "Calcification/Contrast - Pathological or enhanced"
    elif 400 <= hu_value < 1000:
        clinical_significance = "Bone (cancellous) - Normal trabecular bone"
    elif 1000 <= hu_value < 2000:
        clinical_significance = "Bone (cortical) - Normal dense bone"
    else:
        clinical_significance = "Metal/Dense material - Foreign body or artifact"
    
    # Reference range for the detected tissue type
    reference_range = "Standard HU range for detected tissue type"
    for tissue, (min_val, max_val) in HU_RANGES.items():
        if tissue.replace('_', ' ').title() == tissue_type:
            reference_range = f"{min_val} to {max_val} HU"
            break
    
    # Confidence interval analysis
    confidence_analysis = ""
    if ci_lower is not None and ci_upper is not None:
        ci_width = ci_upper - ci_lower
        if ci_width < 10:
            confidence_analysis = "High precision measurement"
        elif ci_width < 30:
            confidence_analysis = "Moderate precision measurement"
        else:
            confidence_analysis = "Low precision measurement - consider larger ROI"
    
    # Detailed notes combining all information
    detailed_notes = f"""
    Tissue Type: {tissue_type}
    Anatomical Context: {anatomical_context}
    Clinical Significance: {clinical_significance}
    Reference Range: {reference_range}
    {confidence_analysis}
    Mean HU: {hu_value:.1f}"""
    
    if ci_lower is not None and ci_upper is not None:
        detailed_notes += f" (95% CI: {ci_lower:.1f} - {ci_upper:.1f})"
    
    detailed_notes += "\n    "
    
    return {
        'primary_interpretation': f"{tissue_type} ({hu_value:.1f} HU)",
        'tissue_type': tissue_type,
        'clinical_significance': clinical_significance,
        'anatomical_context': anatomical_context,
        'reference_range': reference_range,
        'detailed_notes': detailed_notes.strip()
    }


@csrf_exempt
@require_http_methods(['POST'])
def save_annotation(request):
    """Save annotation"""
    try:
        data = json.loads(request.body)
        image = DicomImage.objects.get(id=data['image_id'])
        
        # Check if user can access this image's study
        if not can_access_study(request.user, image.series.study):
            return JsonResponse({'error': 'Access denied. You do not have permission to access this image.'}, status=403)
        
        annotation = Annotation.objects.create(
            image=image,
            x_coordinate=data['x'],
            y_coordinate=data['y'],
            text=data['text'],
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({'id': annotation.id})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def get_measurements(request, image_id):
    """Get measurements for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Check if user can access this image's study
        if not can_access_study(request.user, image.series.study):
            return Response({'error': 'Access denied. You do not have permission to access this image.'}, status=403)
        
        measurements = Measurement.objects.filter(image_id=image_id)
        data = []
        
        for m in measurements:
            measurement_data = {
                'id': m.id,
                'type': m.measurement_type,
                'coordinates': m.coordinates,
                'value': m.value,
                'unit': m.unit,
                'notes': m.notes,
                'created_at': m.created_at.isoformat()
            }
            
            # Add HU-specific data if available
            if m.measurement_type == 'ellipse' and m.hounsfield_mean is not None:
                measurement_data.update({
                    'hounsfield_mean': m.hounsfield_mean,
                    'hounsfield_min': m.hounsfield_min,
                    'hounsfield_max': m.hounsfield_max,
                    'hounsfield_std': m.hounsfield_std,
                })
            
            data.append(measurement_data)
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def get_annotations(request, image_id):
    """Get annotations for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Check if user can access this image's study
        if not can_access_study(request.user, image.series.study):
            return Response({'error': 'Access denied. You do not have permission to access this image.'}, status=403)
        
        annotations = Annotation.objects.filter(image_id=image_id)
        data = [{
            'id': a.id,
            'x': a.x_coordinate,
            'y': a.y_coordinate,
            'text': a.text,
            'font_size': a.font_size,
            'color': a.color,
            'created_at': a.created_at.isoformat()
        } for a in annotations]
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['DELETE'])
def clear_measurements(request, image_id):
    """Clear all measurements and annotations for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Check if user can access this image's study
        if not can_access_study(request.user, image.series.study):
            return JsonResponse({'error': 'Access denied. You do not have permission to access this image.'}, status=403)
        
        Measurement.objects.filter(image_id=image_id).delete()
        Annotation.objects.filter(image_id=image_id).delete()
        return JsonResponse({'message': 'Measurements cleared'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def perform_ai_analysis(request, image_id):
    """Perform AI analysis on image with enhanced diagnosis capabilities"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Get analysis type from request
        data = json.loads(request.body) if request.body else {}
        analysis_type = data.get('analysis_type', 'general')
        
        # Get DICOM metadata for better analysis
        dicom_data = image.load_dicom_data()
        modality = dicom_data.Modality if dicom_data and hasattr(dicom_data, 'Modality') else 'Unknown'
        body_part = dicom_data.BodyPartExamined if dicom_data and hasattr(dicom_data, 'BodyPartExamined') else 'Unknown'
        
        # Generate analysis results based on type
        if analysis_type == 'chest_xray':
            results = generate_chest_xray_analysis(image, modality)
        elif analysis_type == 'ct_lung':
            results = generate_ct_lung_analysis(image, modality)
        elif analysis_type == 'bone_fracture':
            results = generate_bone_fracture_analysis(image, modality, body_part)
        elif analysis_type == 'brain_mri':
            results = generate_brain_mri_analysis(image, modality)
        else:
            results = generate_general_analysis(image, modality, body_part)
        
        # Save AI analysis result
        ai_analysis = AIAnalysis.objects.create(
            image=image,
            analysis_type=analysis_type,
            findings=results['findings'],
            summary=results['summary'],
            confidence_score=results['confidence_score'],
            highlighted_regions=results.get('highlighted_regions', [])
        )
        
        return JsonResponse(results)
        
    except DicomImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def get_3d_reconstruction(request, series_id):
    """Enhanced 3D reconstruction with MPR, bone, angiogram, and virtual surgery"""
    try:
        series = get_object_or_404(DicomSeries, id=series_id)
        images = series.dicomimage_set.all().order_by('image_number')
        
        if not images.exists():
            return Response({'error': 'No images found in series'}, status=404)
        
        reconstruction_type = request.GET.get('type', 'mpr')
        
        # Get reconstruction parameters
        window_center = request.GET.get('window_center', 40)
        window_width = request.GET.get('window_width', 400)
        threshold_min = request.GET.get('threshold_min', -1000)
        threshold_max = request.GET.get('threshold_max', 1000)
        
        # Prepare 3D data based on reconstruction type
        if reconstruction_type == 'mpr':
            # Multi-Planar Reconstruction
            data = {
                'type': 'mpr',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'axial_data': [],
                'sagittal_data': [],
                'coronal_data': [],
                'window_center': int(window_center),
                'window_width': int(window_width)
            }
            
            # Prepare axial slices (original orientation)
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply window/level
                        pixel_data = apply_window_level(pixel_data, int(window_center), int(window_width))
                        
                        data['axial_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': pixel_data.tolist(),
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
            
            # Calculate sagittal and coronal reconstructions
            if data['axial_data']:
                data['sagittal_data'] = calculate_sagittal_reconstruction(data['axial_data'])
                data['coronal_data'] = calculate_coronal_reconstruction(data['axial_data'])
                
        elif reconstruction_type == '3d_bone':
            # 3D Bone Reconstruction
            data = {
                'type': '3d_bone',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'volume_data': [],
                'threshold_min': int(threshold_min),
                'threshold_max': int(threshold_max),
                'bone_threshold': 150  # Typical bone threshold
            }
            
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply bone threshold
                        bone_mask = (pixel_data >= data['bone_threshold'])
                        bone_data = pixel_data * bone_mask
                        
                        data['volume_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': bone_data.tolist(),
                            'mask_data': bone_mask.tolist(),
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
                    
        elif reconstruction_type == 'angiogram':
            # Angiogram Reconstruction
            data = {
                'type': 'angiogram',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'vessel_data': [],
                'mip_data': [],
                'threshold_min': int(threshold_min),
                'threshold_max': int(threshold_max),
                'vessel_threshold': 100  # Typical vessel threshold
            }
            
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply vessel threshold
                        vessel_mask = (pixel_data >= data['vessel_threshold'])
                        vessel_data = pixel_data * vessel_mask
                        
                        data['vessel_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': vessel_data.tolist(),
                            'mask_data': vessel_mask.tolist(),
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
            
            # Calculate Maximum Intensity Projection (MIP)
            if data['vessel_data']:
                data['mip_data'] = calculate_mip_reconstruction(data['vessel_data'])
                
        elif reconstruction_type == 'virtual_surgery':
            # Virtual Surgery Planning
            data = {
                'type': 'virtual_surgery',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'segmentation_data': [],
                'cutting_planes': [],
                'surgical_tools': [],
                'window_center': int(window_center),
                'window_width': int(window_width)
            }
            
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply window/level for surgical planning
                        pixel_data = apply_window_level(pixel_data, int(window_center), int(window_width))
                        
                        # Basic tissue segmentation (bone, soft tissue, air)
                        segmentation = segment_tissues(pixel_data)
                        
                        data['segmentation_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': pixel_data.tolist(),
                            'segmentation': segmentation,
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
        else:
            return Response({'error': 'Invalid reconstruction type'}, status=400)
        
        return Response(data)
        
    except Exception as e:
        print(f"Error in 3D reconstruction: {e}")
        return Response({'error': f'3D reconstruction failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def calculate_volume(request):
    """Calculate volume from contour data"""
    try:
        data = json.loads(request.body)
        contour_points = data.get('contour_points', [])
        pixel_spacing = data.get('pixel_spacing', [1.0, 1.0])
        slice_thickness = data.get('slice_thickness', 1.0)
        
        if len(contour_points) < 3:
            return JsonResponse({'error': 'At least 3 points required for volume calculation'}, status=400)
        
        # Calculate area using shoelace formula
        area = 0
        n = len(contour_points)
        for i in range(n):
            j = (i + 1) % n
            area += contour_points[i][0] * contour_points[j][1]
            area -= contour_points[j][0] * contour_points[i][1]
        area = abs(area) / 2.0
        
        # Convert to mm²
        pixel_area = pixel_spacing[0] * pixel_spacing[1]
        area_mm2 = area * pixel_area
        
        # Calculate volume (assuming uniform slice thickness)
        volume_mm3 = area_mm2 * slice_thickness
        volume_ml = volume_mm3 / 1000.0  # Convert to ml
        
        return JsonResponse({
            'volume_mm3': round(volume_mm3, 2),
            'volume_ml': round(volume_ml, 2),
            'area_mm2': round(area_mm2, 2)
        })
        
    except Exception as e:
        print(f"Error calculating volume: {e}")
        return JsonResponse({'error': f'Volume calculation failed: {str(e)}'}, status=500)


def apply_window_level(pixel_data, window_center, window_width):
    """Apply window/level transformation to pixel data"""
    try:
        pixel_data = np.array(pixel_data, dtype=np.float32)
        window_min = window_center - window_width / 2
        window_max = window_center + window_width / 2
        
        # Clip values to window range
        pixel_data = np.clip(pixel_data, window_min, window_max)
        
        # Normalize to 0-255
        pixel_data = ((pixel_data - window_min) / (window_max - window_min)) * 255
        pixel_data = np.clip(pixel_data, 0, 255)
        
        return pixel_data.astype(np.uint8)
    except Exception as e:
        print(f"Error applying window/level: {e}")
        return pixel_data


def calculate_sagittal_reconstruction(axial_data):
    """Calculate sagittal reconstruction from axial slices"""
    try:
        if not axial_data:
            return []
        
        # Get dimensions
        rows = axial_data[0]['rows']
        cols = axial_data[0]['columns']
        slices = len(axial_data)
        
        # Create sagittal slices (along Y-Z plane)
        sagittal_data = []
        for x in range(cols):
            sagittal_slice = []
            for z in range(slices):
                if z < len(axial_data) and x < len(axial_data[z]['pixel_data'][0]):
                    row_data = []
                    for y in range(rows):
                        if y < len(axial_data[z]['pixel_data']):
                            row_data.append(axial_data[z]['pixel_data'][y][x])
                        else:
                            row_data.append(0)
                    sagittal_slice.append(row_data)
                else:
                    sagittal_slice.append([0] * rows)
            
            sagittal_data.append({
                'slice_number': x,
                'pixel_data': sagittal_slice,
                'rows': slices,
                'columns': rows
            })
        
        return sagittal_data
    except Exception as e:
        print(f"Error calculating sagittal reconstruction: {e}")
        return []


def calculate_coronal_reconstruction(axial_data):
    """Calculate coronal reconstruction from axial slices"""
    try:
        if not axial_data:
            return []
        
        # Get dimensions
        rows = axial_data[0]['rows']
        cols = axial_data[0]['columns']
        slices = len(axial_data)
        
        # Create coronal slices (along X-Z plane)
        coronal_data = []
        for y in range(rows):
            coronal_slice = []
            for z in range(slices):
                if z < len(axial_data) and y < len(axial_data[z]['pixel_data']):
                    coronal_slice.append(axial_data[z]['pixel_data'][y])
                else:
                    coronal_slice.append([0] * cols)
            
            coronal_data.append({
                'slice_number': y,
                'pixel_data': coronal_slice,
                'rows': slices,
                'columns': cols
            })
        
        return coronal_data
    except Exception as e:
        print(f"Error calculating coronal reconstruction: {e}")
        return []


def calculate_mip_reconstruction(vessel_data):
    """Calculate Maximum Intensity Projection for angiogram"""
    try:
        if not vessel_data:
            return []
        
        # Get dimensions
        rows = vessel_data[0]['rows']
        cols = vessel_data[0]['columns']
        slices = len(vessel_data)
        
        # Calculate MIP along Z-axis
        mip_data = []
        for y in range(rows):
            row_data = []
            for x in range(cols):
                max_intensity = 0
                for z in range(slices):
                    if (z < len(vessel_data) and 
                        y < len(vessel_data[z]['pixel_data']) and 
                        x < len(vessel_data[z]['pixel_data'][0])):
                        intensity = vessel_data[z]['pixel_data'][y][x]
                        max_intensity = max(max_intensity, intensity)
                row_data.append(max_intensity)
            mip_data.append(row_data)
        
        return {
            'pixel_data': mip_data,
            'rows': rows,
            'columns': cols
        }
    except Exception as e:
        print(f"Error calculating MIP reconstruction: {e}")
        return []


def segment_tissues(pixel_data):
    """Basic tissue segmentation for virtual surgery"""
    try:
        pixel_data = np.array(pixel_data)
        
        # Simple threshold-based segmentation
        air_mask = (pixel_data < -500)
        fat_mask = (pixel_data >= -500) & (pixel_data < -50)
        soft_tissue_mask = (pixel_data >= -50) & (pixel_data < 150)
        bone_mask = (pixel_data >= 150)
        
        segmentation = {
            'air': air_mask.tolist(),
            'fat': fat_mask.tolist(),
            'soft_tissue': soft_tissue_mask.tolist(),
            'bone': bone_mask.tolist()
        }
        
        return segmentation
    except Exception as e:
        print(f"Error in tissue segmentation: {e}")
        return {}


def parse_dicom_date(date_str):
    """Parse DICOM date string to Python date"""
    if date_str:
        try:
            return datetime.strptime(str(date_str), '%Y%m%d').date()
        except:
            pass
    return None


def parse_dicom_time(time_str):
    """Parse DICOM time string to Python time"""
    if time_str:
        try:
            # Handle various time formats
            time_str = str(time_str)[:6]  # Take first 6 digits (HHMMSS)
            return datetime.strptime(time_str, '%H%M%S').time()
        except:
            pass
    return None


@login_required
def api_study_clinical_info(request, study_id):
    """Get clinical information for a study"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        return JsonResponse({
            'success': True,
            'clinical_info': study.clinical_info,
            'referring_physician': study.referring_physician,
            'accession_number': study.accession_number
        })
    except DicomStudy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study not found'
        })


def create_system_error_notification(error_message, user=None):
    """Create system error notification"""
    try:
        # Notify administrators
        admin_users = User.objects.filter(is_superuser=True)
        for admin in admin_users:
            Notification.objects.create(
                recipient=admin,
                notification_type='system_error',
                title='System Error',
                message=error_message
            )
        
        # Also notify the user if provided
        if user and user.is_authenticated:
            Notification.objects.create(
                recipient=user,
                notification_type='system_error',
                title='Upload Error',
                message=error_message
            )
    except Exception as e:
        print(f"Error creating system error notification: {e}")


# AI Analysis Helper Functions
def generate_chest_xray_analysis(image, modality):
    """Generate AI analysis for chest X-ray images"""
    import random
    
    # Simulate different findings
    findings_pool = [
        {
            'type': 'Cardiomegaly',
            'location': {'x': 256, 'y': 300},
            'size': 80,
            'confidence': 0.87,
            'description': 'Mild cardiac enlargement detected'
        },
        {
            'type': 'Pneumonia',
            'location': {'x': 180, 'y': 250},
            'size': 60,
            'confidence': 0.75,
            'description': 'Possible infiltrate in right lower lobe'
        },
        {
            'type': 'Pleural Effusion',
            'location': {'x': 100, 'y': 400},
            'size': 40,
            'confidence': 0.82,
            'description': 'Small pleural effusion on left side'
        },
        {
            'type': 'Normal',
            'location': {'x': 256, 'y': 256},
            'size': 0,
            'confidence': 0.95,
            'description': 'No acute cardiopulmonary findings'
        }
    ]
    
    # Randomly select findings
    num_findings = random.randint(0, 2)
    if num_findings == 0:
        findings = [findings_pool[-1]]  # Normal
    else:
        findings = random.sample(findings_pool[:-1], num_findings)
    
    # Generate summary
    if findings[0]['type'] == 'Normal':
        summary = "Chest X-ray analysis complete. No significant abnormalities detected. Clear lung fields bilaterally."
        confidence = 0.95
    else:
        abnormalities = [f['type'] for f in findings]
        summary = f"Chest X-ray analysis complete. Findings suggestive of: {', '.join(abnormalities)}. Clinical correlation recommended."
        confidence = sum(f['confidence'] for f in findings) / len(findings)
    
    return {
        'analysis_type': 'chest_xray',
        'summary': summary,
        'confidence_score': confidence,
        'findings': findings,
        'highlighted_regions': [
            {
                'x': f['location']['x'] - f['size']//2,
                'y': f['location']['y'] - f['size']//2,
                'width': f['size'],
                'height': f['size'],
                'type': f['type'].lower().replace(' ', '_')
            } for f in findings if f['type'] != 'Normal'
        ],
        'recommendations': 'Compare with prior imaging if available. Clinical correlation advised.'
    }


def generate_ct_lung_analysis(image, modality):
    """Generate AI analysis for CT lung images"""
    import random
    
    findings_pool = [
        {
            'type': 'Lung Nodule',
            'location': {'x': 200, 'y': 150},
            'size': 8,
            'confidence': 0.89,
            'description': 'Solid nodule in right upper lobe, 8mm'
        },
        {
            'type': 'Ground Glass Opacity',
            'location': {'x': 300, 'y': 200},
            'size': 30,
            'confidence': 0.78,
            'description': 'Ground glass opacity in left lower lobe'
        },
        {
            'type': 'Emphysema',
            'location': {'x': 256, 'y': 100},
            'size': 50,
            'confidence': 0.85,
            'description': 'Centrilobular emphysematous changes'
        }
    ]
    
    findings = random.sample(findings_pool, random.randint(0, 2))
    
    if not findings:
        summary = "CT lung analysis complete. No suspicious pulmonary nodules or masses identified."
        confidence = 0.92
    else:
        summary = f"CT lung analysis complete. {len(findings)} finding(s) detected requiring follow-up."
        confidence = sum(f['confidence'] for f in findings) / len(findings) if findings else 0.9
    
    return {
        'analysis_type': 'ct_lung',
        'summary': summary,
        'confidence_score': confidence,
        'findings': findings,
        'highlighted_regions': [
            {
                'x': f['location']['x'] - f['size']//2,
                'y': f['location']['y'] - f['size']//2,
                'width': f['size'],
                'height': f['size'],
                'type': f['type'].lower().replace(' ', '_')
            } for f in findings
        ],
        'recommendations': 'Follow-up CT in 3-6 months recommended for nodule surveillance.' if findings else 'No follow-up required.'
    }


def generate_bone_fracture_analysis(image, modality, body_part):
    """Generate AI analysis for bone fracture detection"""
    import random
    
    fracture_types = ['hairline', 'displaced', 'comminuted', 'spiral', 'stress']
    bones = {
        'HAND': ['metacarpal', 'phalanx', 'carpal'],
        'FOOT': ['metatarsal', 'calcaneus', 'talus'],
        'ARM': ['radius', 'ulna', 'humerus'],
        'LEG': ['tibia', 'fibula', 'femur'],
        'DEFAULT': ['bone']
    }
    
    bone_list = bones.get(body_part.upper(), bones['DEFAULT'])
    
    # Simulate fracture detection
    has_fracture = random.random() < 0.3  # 30% chance of fracture
    
    if has_fracture:
        fracture_type = random.choice(fracture_types)
        affected_bone = random.choice(bone_list)
        confidence = random.uniform(0.75, 0.95)
        
        findings = [{
            'type': f'{fracture_type.capitalize()} Fracture',
            'location': {'x': random.randint(100, 400), 'y': random.randint(100, 400)},
            'size': random.randint(20, 60),
            'confidence': confidence,
            'description': f'{fracture_type.capitalize()} fracture of the {affected_bone}'
        }]
        
        summary = f"Bone analysis complete. {fracture_type.capitalize()} fracture detected in {affected_bone}. Orthopedic consultation recommended."
    else:
        findings = []
        summary = "Bone analysis complete. No acute fracture or dislocation identified."
        confidence = 0.94
    
    return {
        'analysis_type': 'bone_fracture',
        'summary': summary,
        'confidence_score': confidence if has_fracture else 0.94,
        'findings': findings,
        'highlighted_regions': [
            {
                'x': f['location']['x'] - f['size']//2,
                'y': f['location']['y'] - f['size']//2,
                'width': f['size'],
                'height': f['size'],
                'type': 'fracture'
            } for f in findings
        ],
        'recommendations': 'Orthopedic referral recommended.' if has_fracture else 'No acute intervention required.'
    }


def generate_brain_mri_analysis(image, modality):
    """Generate AI analysis for brain MRI"""
    import random
    
    findings_pool = [
        {
            'type': 'White Matter Changes',
            'location': {'x': 256, 'y': 200},
            'size': 40,
            'confidence': 0.82,
            'description': 'Periventricular white matter hyperintensities'
        },
        {
            'type': 'Cerebral Atrophy',
            'location': {'x': 256, 'y': 256},
            'size': 100,
            'confidence': 0.78,
            'description': 'Mild generalized cerebral volume loss'
        },
        {
            'type': 'Small Vessel Disease',
            'location': {'x': 200, 'y': 180},
            'size': 30,
            'confidence': 0.85,
            'description': 'Chronic microvascular ischemic changes'
        }
    ]
    
    findings = random.sample(findings_pool, random.randint(0, 2))
    
    if not findings:
        summary = "Brain MRI analysis complete. No acute intracranial abnormality identified."
        confidence = 0.91
    else:
        summary = f"Brain MRI analysis complete. {len(findings)} finding(s) identified. Clinical correlation recommended."
        confidence = sum(f['confidence'] for f in findings) / len(findings) if findings else 0.9
    
    return {
        'analysis_type': 'brain_mri',
        'summary': summary,
        'confidence_score': confidence,
        'findings': findings,
        'highlighted_regions': [
            {
                'x': f['location']['x'] - f['size']//2,
                'y': f['location']['y'] - f['size']//2,
                'width': f['size'],
                'height': f['size'],
                'type': f['type'].lower().replace(' ', '_')
            } for f in findings
        ],
        'recommendations': 'Neurology consultation may be beneficial.' if findings else 'Routine follow-up as clinically indicated.'
    }


def generate_general_analysis(image, modality, body_part):
    """Generate general AI analysis for any image type"""
    import random
    
    # General findings based on modality
    general_findings = {
        'CT': ['density abnormality', 'contrast enhancement', 'structural asymmetry'],
        'MR': ['signal abnormality', 'enhancement pattern', 'morphological change'],
        'CR': ['density variation', 'structural abnormality', 'alignment issue'],
        'DX': ['opacity', 'lucency', 'structural change'],
        'DEFAULT': ['abnormality', 'variation', 'finding']
    }
    
    finding_types = general_findings.get(modality, general_findings['DEFAULT'])
    
    # Simulate findings
    num_findings = random.randint(0, 2)
    findings = []
    
    for i in range(num_findings):
        finding_type = random.choice(finding_types)
        findings.append({
            'type': finding_type.title(),
            'location': {'x': random.randint(100, 400), 'y': random.randint(100, 400)},
            'size': random.randint(20, 80),
            'confidence': random.uniform(0.7, 0.9),
            'description': f'{finding_type.capitalize()} detected in {body_part.lower() if body_part != "Unknown" else "image"}'
        })
    
    if not findings:
        summary = f"AI analysis complete for {modality} {body_part.lower() if body_part != 'Unknown' else 'image'}. No significant abnormalities detected."
        confidence = 0.88
    else:
        summary = f"AI analysis complete. {len(findings)} potential finding(s) identified. Further evaluation recommended."
        confidence = sum(f['confidence'] for f in findings) / len(findings)
    
    return {
        'analysis_type': 'general',
        'summary': summary,
        'confidence_score': confidence,
        'findings': findings,
        'highlighted_regions': [
            {
                'x': f['location']['x'] - f['size']//2,
                'y': f['location']['y'] - f['size']//2,
                'width': f['size'],
                'height': f['size'],
                'type': f['type'].lower().replace(' ', '_')
            } for f in findings
        ],
        'recommendations': 'Clinical correlation and comparison with prior imaging recommended.'
    }


@api_view(['GET'])
def get_study_series(request, study_id):
    """Get all series for a study with detailed information"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        series_list = study.series.all().order_by('series_number')
        
        series_data = []
        for series in series_list:
            # Get first image for series preview
            first_image = series.images.first()
            preview_data = None
            if first_image:
                try:
                    # Get a small preview image
                    preview_data = first_image.get_processed_image_base64(
                        window_width=400, 
                        window_level=40, 
                        inverted=False
                    )
                except:
                    preview_data = None
            
            series_info = {
                'id': series.id,
                'series_number': series.series_number,
                'series_description': series.series_description,
                'modality': series.modality,
                'body_part_examined': series.body_part_examined,
                'image_count': series.images.count(),
                'preview_image': preview_data,
                'created_at': series.created_at.isoformat() if series.created_at else None,
            }
            series_data.append(series_info)
        
        return Response({
            'study': {
                'id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'study_date': study.study_date,
                'modality': study.modality,
                'study_description': study.study_description,
                'institution_name': study.institution_name,
                'accession_number': study.accession_number,
                'series_count': len(series_data),
            },
            'series': series_data
        })
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_series_images(request, series_id):
    """Get all images for a specific series"""
    try:
        series = DicomSeries.objects.get(id=series_id)
        images = series.images.all().order_by('instance_number')
        
        images_data = []
        for image in images:
            image_data = {
                'id': image.id,
                'instance_number': int(image.instance_number) if image.instance_number is not None else None,
                'rows': int(image.rows) if image.rows is not None else None,
                'columns': int(image.columns) if image.columns is not None else None,
                'pixel_spacing_x': float(image.pixel_spacing_x) if image.pixel_spacing_x is not None else None,
                'pixel_spacing_y': float(image.pixel_spacing_y) if image.pixel_spacing_y is not None else None,
                'slice_thickness': float(image.slice_thickness) if image.slice_thickness is not None else None,
                'window_width': float(image.window_width) if image.window_width is not None else None,
                'window_center': float(image.window_center) if image.window_center is not None else None,
            }
            images_data.append(image_data)
        
        return Response({
            'series': {
                'id': series.id,
                'series_number': series.series_number,
                'series_description': series.series_description,
                'modality': series.modality,
                'body_part_examined': series.body_part_examined,
                'image_count': len(images_data),
            },
            'images': images_data
        })
    except DicomSeries.DoesNotExist:
        return Response({'error': 'Series not found'}, status=404)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def enhanced_bulk_upload_dicom_folder(request):
    """Enhanced bulk upload endpoint for handling large files with multiple folders"""
    try:
        # Ensure media directories exist
        ensure_directories()
        
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        # Check file size (5GB limit for bulk uploads)
        if uploaded_file.size > 5 * 1024 * 1024 * 1024:
            return JsonResponse({'error': 'File too large (max 5GB)'}, status=400)
        
        # Create enhanced upload manager
        upload_manager = EnhancedBulkUploadManager(
            user=request.user,
            facility=request.user.facility if hasattr(request.user, 'facility') else None
        )
        
        # Start background processing
        def background_upload():
            try:
                success = upload_manager.process_upload(uploaded_file)
                if success:
                    result = {
                        'upload_id': upload_manager.upload_id,
                        'status': 'completed',
                        'total_files': upload_manager.progress['total_files'],
                        'successful_files': upload_manager.progress['successful_files'],
                        'failed_files': upload_manager.progress['failed_files'],
                        'studies_created': upload_manager.progress['studies_created'],
                        'series_created': upload_manager.progress['series_created'],
                        'images_processed': upload_manager.progress['images_processed'],
                        'total_size_mb': upload_manager.progress['total_size_mb'],
                        'errors': upload_manager.progress['errors']
                    }
                else:
                    result = {
                        'upload_id': upload_manager.upload_id,
                        'status': 'failed',
                        'errors': upload_manager.progress['errors']
                    }
                
                # Store final result in cache
                cache.set(f'upload_result_{upload_manager.upload_id}', result, timeout=7200)
                
            except Exception as e:
                logger.error(f"Background upload error: {e}")
                result = {
                    'upload_id': upload_manager.upload_id,
                    'status': 'failed',
                    'error': str(e)
                }
                cache.set(f'upload_result_{upload_manager.upload_id}', result, timeout=7200)
        
        # Start background thread
        upload_thread = threading.Thread(target=background_upload)
        upload_thread.daemon = True
        upload_thread.start()
        
        return JsonResponse({
            'upload_id': upload_manager.upload_id,
            'message': f'Started processing bulk upload in background',
            'status': 'processing'
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in enhanced_bulk_upload_dicom_folder: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error notification
        create_system_error_notification(f"Enhanced bulk DICOM upload error: {str(e)}", request.user)
        
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_enhanced_upload_progress(request, upload_id):
    """Get enhanced upload progress with detailed metrics"""
    try:
        progress = cache.get(f'upload_progress_{upload_id}')
        if not progress:
            return Response({'error': 'Upload progress not found'}, status=404)
        
        return Response(progress)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_enhanced_upload_result(request, upload_id):
    """Get enhanced upload result with detailed statistics"""
    try:
        result = cache.get(f'upload_result_{upload_id}')
        if not result:
            return Response({'error': 'Upload result not found'}, status=404)
        
        return Response(result)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_enhanced_image_data(request, image_id):
    """Get enhanced image data with improved resolution and density differentiation"""
    try:
        print(f"Attempting to get enhanced image data for image_id: {image_id}")
        image = DicomImage.objects.get(id=image_id)
        print(f"Found image: {image}, file_path: {image.file_path}")
        
        # Get query parameters with enhanced options for density differentiation
        window_width = request.GET.get('window_width', image.window_width or 1500)  # Default to lung window
        window_level = request.GET.get('window_level', image.window_center or -600)  # Default to lung level
        inverted = request.GET.get('inverted', 'false').lower() == 'true'
        high_quality = request.GET.get('high_quality', 'true').lower() == 'true'  # Always use high quality
        preserve_aspect = request.GET.get('preserve_aspect', 'true').lower() == 'true'
        density_enhancement = request.GET.get('density_enhancement', 'true').lower() == 'true'  # Always enable
        resolution_factor = float(request.GET.get('resolution_factor', 2.0))  # Higher resolution by default
        contrast_optimization = request.GET.get('contrast_optimization', 'medical')  # Default to medical optimization
        
        # Set defaults if None
        if window_width:
            try:
                window_width = float(window_width)
            except ValueError:
                window_width = 1500  # Default to lung window
        if window_level:
            try:
                window_level = float(window_level)
            except ValueError:
                window_level = -600  # Default to lung level
        
        print(f"Processing image with WW: {window_width}, WL: {window_level}, inverted: {inverted}, high_quality: {high_quality}, density_enhancement: {density_enhancement}")
        
        # Always use enhanced processing for superior medical imaging quality
        # Apply contrast optimization based on request type
        if contrast_optimization == 'medical':
            contrast_boost = 1.3  # Enhanced contrast for medical imaging
            effective_resolution_factor = max(1.0, min(2.5, resolution_factor))  # Allow higher resolution
        else:
            contrast_boost = 1.2
            effective_resolution_factor = resolution_factor
        
        image_base64 = image.get_enhanced_processed_image_base64(
            window_width, window_level, inverted, 
            resolution_factor=effective_resolution_factor,
            density_enhancement=density_enhancement,
            contrast_boost=contrast_boost
        )
        
        if image_base64:
            print(f"Successfully processed enhanced image {image_id}")
            return Response({
                'image_data': image_base64,
                'metadata': {
                    'rows': image.rows,
                    'columns': image.columns,
                    'pixel_spacing_x': image.pixel_spacing_x,
                    'pixel_spacing_y': image.pixel_spacing_y,
                    'slice_thickness': image.slice_thickness,
                    'window_width': image.window_width,
                    'window_center': image.window_center,
                    'bits_allocated': image.bits_allocated,
                    'photometric_interpretation': image.photometric_interpretation,
                    'samples_per_pixel': image.samples_per_pixel,
                }
            })
        else:
            print(f"Failed to process enhanced image {image_id}")
            return Response({'error': 'Could not process enhanced image - file may be missing or corrupted'}, status=500)
            
    except DicomImage.DoesNotExist:
        print(f"Image not found: {image_id}")
        return Response({'error': 'Image not found'}, status=404)
    except Exception as e:
        print(f"Unexpected error processing enhanced image {image_id}: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_series_selector_data(request, study_id):
    """Get series data for series selector UI"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        series_list = study.series.all().order_by('series_number')
        
        series_data = []
        for series in series_list:
            # Get first image for series preview
            first_image = series.images.first()
            preview_data = None
            if first_image:
                try:
                    # Get a small preview image with enhanced processing
                    preview_data = first_image.get_enhanced_processed_image_base64(
                        window_width=400, 
                        window_level=40, 
                        inverted=False,
                        resolution_factor=0.5,  # Smaller preview
                        density_enhancement=True,
                        contrast_boost=1.2
                    )
                except:
                    preview_data = None
            
            # Get series statistics
            image_count = series.images.count()
            modalities = series.images.values_list('photometric_interpretation', flat=True).distinct()
            
            series_info = {
                'id': series.id,
                'series_number': series.series_number,
                'series_description': series.series_description,
                'modality': series.modality,
                'body_part_examined': series.body_part_examined,
                'image_count': image_count,
                'preview_image': preview_data,
                'created_at': series.created_at.isoformat() if series.created_at else None,
                'modalities': list(modalities),
                'has_enhanced_processing': True,
                'supports_3d': image_count > 10,  # Series with many images can support 3D
                'supports_mpr': image_count > 5,   # Series with moderate images can support MPR
            }
            series_data.append(series_info)
        
        return Response({
            'study': {
                'id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'study_date': study.study_date,
                'modality': study.modality,
                'study_description': study.study_description,
                'institution_name': study.institution_name,
                'accession_number': study.accession_number,
                'series_count': len(series_data),
                'total_images': sum(s['image_count'] for s in series_data),
            },
            'series': series_data,
            'ui_config': {
                'series_selector_position': 'bottom',  # Can be 'top', 'bottom', 'side'
                'show_previews': True,
                'show_statistics': True,
                'enable_enhanced_processing': True,
                'enable_3d_reconstruction': True,
                'enable_mpr': True,
            }
        })
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_enhanced_series_images(request, series_id):
    """Get enhanced series images with improved processing"""
    try:
        series = DicomSeries.objects.get(id=series_id)
        images = series.images.all().order_by('instance_number')
        
        images_data = []
        for image in images:
            # Get enhanced image data
            enhanced_preview = None
            try:
                enhanced_preview = image.get_enhanced_processed_image_base64(
                    window_width=400,
                    window_level=40,
                    inverted=False,
                    resolution_factor=0.3,  # Small preview
                    density_enhancement=True,
                    contrast_boost=1.1
                )
            except:
                pass
            
            image_data = {
                'id': image.id,
                'instance_number': int(image.instance_number) if image.instance_number is not None else None,
                'rows': int(image.rows) if image.rows is not None else None,
                'columns': int(image.columns) if image.columns is not None else None,
                'pixel_spacing_x': float(image.pixel_spacing_x) if image.pixel_spacing_x is not None else None,
                'pixel_spacing_y': float(image.pixel_spacing_y) if image.pixel_spacing_y is not None else None,
                'slice_thickness': float(image.slice_thickness) if image.slice_thickness is not None else None,
                'window_width': float(image.window_width) if image.window_width is not None else None,
                'window_center': float(image.window_center) if image.window_center is not None else None,
                'bits_allocated': int(image.bits_allocated) if image.bits_allocated is not None else None,
                'photometric_interpretation': image.photometric_interpretation,
                'samples_per_pixel': int(image.samples_per_pixel) if image.samples_per_pixel is not None else None,
                'enhanced_preview': enhanced_preview,
                'supports_enhanced_processing': True,
            }
            images_data.append(image_data)
        
        return Response({
            'series': {
                'id': series.id,
                'series_number': series.series_number,
                'series_description': series.series_description,
                'modality': series.modality,
                'body_part_examined': series.body_part_examined,
                'image_count': len(images_data),
            },
            'images': images_data,
            'enhanced_features': {
                'density_differentiation': True,
                'high_resolution_processing': True,
                'contrast_enhancement': True,
                'multi_scale_processing': True,
            }
        })
    except DicomSeries.DoesNotExist:
        return Response({'error': 'Series not found'}, status=404)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


# Add enhanced image processing imports
import cv2
from scipy.ndimage import gaussian_filter, median_filter, uniform_filter
from skimage import exposure, filters, segmentation, morphology
from skimage.restoration import denoise_tv_chambolle, denoise_bilateral
from skimage.feature import canny
from scipy.signal import wiener
import matplotlib.pyplot as plt

# ... existing code ...

class AdvancedImageProcessor:
    """Advanced image processing for X-ray refinement and MRI reconstruction"""
    
    def __init__(self):
        self.processed_cache = {}
    
    def enhance_xray_image(self, pixel_array, enhancement_type='comprehensive'):
        """
        Enhanced X-ray image processing with multiple refinement techniques
        """
        try:
            # Normalize input
            if pixel_array.max() > 1:
                pixel_array = pixel_array.astype(np.float32) / pixel_array.max()
            
            # Apply different enhancement techniques based on type
            if enhancement_type == 'comprehensive':
                enhanced = self._apply_comprehensive_xray_enhancement(pixel_array)
            elif enhancement_type == 'edge_enhancement':
                enhanced = self._apply_edge_enhancement(pixel_array)
            elif enhancement_type == 'contrast_enhancement':
                enhanced = self._apply_contrast_enhancement(pixel_array)
            elif enhancement_type == 'noise_reduction':
                enhanced = self._apply_noise_reduction(pixel_array)
            elif enhancement_type == 'bone_enhancement':
                enhanced = self._apply_bone_enhancement(pixel_array)
            elif enhancement_type == 'soft_tissue_enhancement':
                enhanced = self._apply_soft_tissue_enhancement(pixel_array)
            else:
                enhanced = self._apply_comprehensive_xray_enhancement(pixel_array)
            
            # Ensure output is in valid range
            enhanced = np.clip(enhanced, 0, 1)
            return (enhanced * 255).astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Error in X-ray enhancement: {e}")
            return pixel_array
    
    def _apply_comprehensive_xray_enhancement(self, image):
        """Apply comprehensive X-ray enhancement pipeline"""
        # Step 1: Noise reduction
        denoised = denoise_bilateral(image, sigma_color=0.05, sigma_spatial=15)
        
        # Step 2: Contrast enhancement using CLAHE
        clahe_enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.03, nbins=256)
        
        # Step 3: Edge enhancement
        edges = canny(clahe_enhanced, sigma=1.0, low_threshold=0.1, high_threshold=0.2)
        edge_enhanced = clahe_enhanced + 0.3 * edges
        
        # Step 4: Gamma correction
        gamma_corrected = exposure.adjust_gamma(edge_enhanced, gamma=0.8)
        
        # Step 5: Unsharp masking
        blurred = gaussian_filter(gamma_corrected, sigma=2.0)
        unsharp_mask = gamma_corrected + 0.5 * (gamma_corrected - blurred)
        
        return np.clip(unsharp_mask, 0, 1)
    
    def _apply_edge_enhancement(self, image):
        """Apply edge enhancement specifically for X-ray images"""
        # Sobel edge detection
        sobel_h = filters.sobel_h(image)
        sobel_v = filters.sobel_v(image)
        sobel_combined = np.sqrt(sobel_h**2 + sobel_v**2)
        
        # Enhance edges
        enhanced = image + 0.4 * sobel_combined
        
        # Apply contrast stretching
        p2, p98 = np.percentile(enhanced, (2, 98))
        enhanced = exposure.rescale_intensity(enhanced, in_range=(p2, p98))
        
        return enhanced
    
    def _apply_contrast_enhancement(self, image):
        """Apply advanced contrast enhancement"""
        # Histogram equalization
        eq_global = exposure.equalize_hist(image)
        
        # Local histogram equalization
        eq_local = exposure.equalize_adapthist(image, clip_limit=0.03)
        
        # Combine global and local
        combined = 0.6 * eq_local + 0.4 * eq_global
        
        return combined
    
    def _apply_noise_reduction(self, image):
        """Apply advanced noise reduction"""
        # Total variation denoising
        tv_denoised = denoise_tv_chambolle(image, weight=0.1)
        
        # Bilateral filtering
        bilateral_denoised = denoise_bilateral(tv_denoised, sigma_color=0.05, sigma_spatial=15)
        
        # Median filtering for impulse noise
        median_filtered = median_filter(bilateral_denoised, size=3)
        
        return median_filtered
    
    def _apply_bone_enhancement(self, image):
        """Enhance bone structures in X-ray images"""
        # High-pass filtering to enhance bone edges
        low_pass = gaussian_filter(image, sigma=3)
        high_pass = image - low_pass
        
        # Enhance high-frequency components
        bone_enhanced = image + 0.6 * high_pass
        
        # Apply contrast stretching specifically for bone density range
        p5, p95 = np.percentile(bone_enhanced, (5, 95))
        bone_enhanced = exposure.rescale_intensity(bone_enhanced, in_range=(p5, p95))
        
        return bone_enhanced
    
    def _apply_soft_tissue_enhancement(self, image):
        """Enhance soft tissue contrast in X-ray images"""
        # Low-pass filtering to enhance soft tissue
        soft_tissue = gaussian_filter(image, sigma=1.5)
        
        # Adaptive histogram equalization for better soft tissue contrast
        enhanced = exposure.equalize_adapthist(soft_tissue, clip_limit=0.02, nbins=256)
        
        # Gamma correction for soft tissue
        enhanced = exposure.adjust_gamma(enhanced, gamma=1.2)
        
        return enhanced
    
    def reconstruct_mri_image(self, pixel_array, reconstruction_type='t1_weighted'):
        """
        Advanced MRI reconstruction with different sequence optimizations
        """
        try:
            # Normalize input
            if pixel_array.max() > 1:
                pixel_array = pixel_array.astype(np.float32) / pixel_array.max()
            
            # Apply reconstruction based on MRI sequence type
            if reconstruction_type == 't1_weighted':
                reconstructed = self._reconstruct_t1_weighted(pixel_array)
            elif reconstruction_type == 't2_weighted':
                reconstructed = self._reconstruct_t2_weighted(pixel_array)
            elif reconstruction_type == 'flair':
                reconstructed = self._reconstruct_flair(pixel_array)
            elif reconstruction_type == 'dwi':
                reconstructed = self._reconstruct_dwi(pixel_array)
            elif reconstruction_type == 'perfusion':
                reconstructed = self._reconstruct_perfusion(pixel_array)
            else:
                reconstructed = self._reconstruct_general_mri(pixel_array)
            
            # Ensure output is in valid range
            reconstructed = np.clip(reconstructed, 0, 1)
            return (reconstructed * 255).astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Error in MRI reconstruction: {e}")
            return pixel_array
    
    def _reconstruct_t1_weighted(self, image):
        """Reconstruct T1-weighted MRI with enhanced tissue contrast"""
        # Noise reduction while preserving edges
        denoised = denoise_bilateral(image, sigma_color=0.03, sigma_spatial=10)
        
        # Enhance white matter/gray matter contrast
        # T1 images: CSF is dark, white matter is bright, gray matter is intermediate
        
        # Apply contrast enhancement
        enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.02)
        
        # Gamma correction optimized for T1
        gamma_corrected = exposure.adjust_gamma(enhanced, gamma=0.9)
        
        # Sharpen for better anatomical detail
        sharpened = filters.unsharp_mask(gamma_corrected, radius=1, amount=0.5)
        
        return sharpened
    
    def _reconstruct_t2_weighted(self, image):
        """Reconstruct T2-weighted MRI with enhanced fluid sensitivity"""
        # T2 images: CSF is bright, pathology often appears bright
        
        # Noise reduction
        denoised = denoise_tv_chambolle(image, weight=0.05)
        
        # Enhance fluid structures
        enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.025)
        
        # Gamma correction for T2
        gamma_corrected = exposure.adjust_gamma(enhanced, gamma=1.1)
        
        # Edge preservation
        edge_preserved = denoise_bilateral(gamma_corrected, sigma_color=0.02, sigma_spatial=8)
        
        return edge_preserved
    
    def _reconstruct_flair(self, image):
        """Reconstruct FLAIR MRI with enhanced lesion detection"""
        # FLAIR suppresses CSF signal, enhances lesions
        
        # Strong noise reduction
        denoised = denoise_bilateral(image, sigma_color=0.02, sigma_spatial=12)
        
        # Enhance lesion contrast
        enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.015)
        
        # Apply specific gamma for FLAIR
        gamma_corrected = exposure.adjust_gamma(enhanced, gamma=0.85)
        
        # Unsharp masking for lesion enhancement
        unsharp = filters.unsharp_mask(gamma_corrected, radius=2, amount=0.8)
        
        return unsharp
    
    def _reconstruct_dwi(self, image):
        """Reconstruct Diffusion-Weighted Imaging with enhanced diffusion contrast"""
        # DWI is sensitive to water molecule motion
        
        # Minimal noise reduction to preserve diffusion information
        denoised = median_filter(image, size=3)
        
        # Enhance diffusion contrast
        enhanced = exposure.rescale_intensity(denoised, out_range=(0, 1))
        
        # Apply contrast stretching
        p1, p99 = np.percentile(enhanced, (1, 99))
        stretched = exposure.rescale_intensity(enhanced, in_range=(p1, p99))
        
        return stretched
    
    def _reconstruct_perfusion(self, image):
        """Reconstruct perfusion MRI with enhanced vascular information"""
        # Perfusion imaging shows blood flow
        
        # Noise reduction
        denoised = gaussian_filter(image, sigma=0.8)
        
        # Enhance vascular structures
        enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.03)
        
        # Apply gamma correction
        gamma_corrected = exposure.adjust_gamma(enhanced, gamma=1.2)
        
        return gamma_corrected
    
    def _reconstruct_general_mri(self, image):
        """General MRI reconstruction for unknown sequences"""
        # General purpose MRI enhancement
        
        # Noise reduction
        denoised = denoise_bilateral(image, sigma_color=0.04, sigma_spatial=10)
        
        # Contrast enhancement
        enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.02)
        
        # Edge enhancement
        sharpened = filters.unsharp_mask(enhanced, radius=1.5, amount=0.6)
        
        return sharpened
    
    def enhance_mri_image(self, pixel_array, enhancement_type='comprehensive'):
        """
        Enhanced MRI image processing with multiple enhancement techniques
        """
        try:
            # Normalize input
            if pixel_array.max() > 1:
                pixel_array = pixel_array.astype(np.float32) / pixel_array.max()
            
            # Apply different enhancement techniques
            if enhancement_type == 'comprehensive':
                enhanced = self._apply_comprehensive_mri_enhancement(pixel_array)
            elif enhancement_type == 'brain_enhancement':
                enhanced = self._apply_brain_enhancement(pixel_array)
            elif enhancement_type == 'spine_enhancement':
                enhanced = self._apply_spine_enhancement(pixel_array)
            elif enhancement_type == 'vessel_enhancement':
                enhanced = self._apply_vessel_enhancement(pixel_array)
            else:
                enhanced = self._apply_comprehensive_mri_enhancement(pixel_array)
            
            # Ensure output is in valid range
            enhanced = np.clip(enhanced, 0, 1)
            return (enhanced * 255).astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Error in MRI enhancement: {e}")
            return pixel_array
    
    def _apply_comprehensive_mri_enhancement(self, image):
        """Apply comprehensive MRI enhancement pipeline"""
        # Step 1: Noise reduction with edge preservation
        denoised = denoise_bilateral(image, sigma_color=0.03, sigma_spatial=12)
        
        # Step 2: Contrast enhancement
        contrast_enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.02)
        
        # Step 3: Gamma correction
        gamma_corrected = exposure.adjust_gamma(contrast_enhanced, gamma=0.9)
        
        # Step 4: Sharpening
        sharpened = filters.unsharp_mask(gamma_corrected, radius=1.5, amount=0.7)
        
        return sharpened
    
    def _apply_brain_enhancement(self, image):
        """Enhance brain structures in MRI"""
        # Brain-specific enhancement
        denoised = denoise_bilateral(image, sigma_color=0.02, sigma_spatial=8)
        
        # Enhance gray matter/white matter contrast
        enhanced = exposure.equalize_adapthist(denoised, clip_limit=0.015)
        
        # Apply brain-optimized gamma
        gamma_corrected = exposure.adjust_gamma(enhanced, gamma=0.85)
        
        return gamma_corrected
    
    def _apply_spine_enhancement(self, image):
        """Enhance spinal structures in MRI"""
        # Spine-specific enhancement
        denoised = denoise_tv_chambolle(image, weight=0.03)
        
        # Enhance bone/soft tissue contrast
        enhanced = exposure.rescale_intensity(denoised)
        
        # Edge enhancement for spinal anatomy
        edges = canny(enhanced, sigma=1.0)
        edge_enhanced = enhanced + 0.2 * edges
        
        return np.clip(edge_enhanced, 0, 1)
    
    def _apply_vessel_enhancement(self, image):
        """Enhance vascular structures in MRI"""
        # Vessel enhancement using Frangi vesselness filter
        from skimage.filters import frangi
        
        # Apply Frangi filter for vessel enhancement
        vessels = frangi(image, sigmas=range(1, 4), beta1=0.5, beta2=15)
        
        # Combine original with vessel-enhanced image
        enhanced = image + 0.3 * vessels
        
        # Apply contrast enhancement
        contrast_enhanced = exposure.equalize_adapthist(enhanced, clip_limit=0.03)
        
        return contrast_enhanced

# Initialize the advanced processor
advanced_processor = AdvancedImageProcessor()

@csrf_exempt
@api_view(['POST'])
def enhance_xray_image_api(request, image_id):
    """
    API endpoint to enhance X-ray images with advanced algorithms
    """
    try:
        dicom_image = get_object_or_404(DicomImage, id=image_id)
        enhancement_type = request.data.get('enhancement_type', 'comprehensive')
        
        # Load the DICOM image
        dicom_path = dicom_image.dicom_file.path
        dicom_data = pydicom.dcmread(dicom_path)
        pixel_array = dicom_data.pixel_array.astype(np.float32)
        
        # Apply X-ray enhancement
        enhanced_array = advanced_processor.enhance_xray_image(pixel_array, enhancement_type)
        
        # Convert to base64 for transmission
        enhanced_pil = Image.fromarray(enhanced_array)
        buffer = io.BytesIO()
        enhanced_pil.save(buffer, format='PNG')
        enhanced_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'success': True,
            'enhanced_image': f"data:image/png;base64,{enhanced_base64}",
            'enhancement_type': enhancement_type,
            'message': f'X-ray image enhanced using {enhancement_type} algorithm'
        })
        
    except Exception as e:
        logger.error(f"Error enhancing X-ray image: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@api_view(['POST'])
def reconstruct_mri_image_api(request, image_id):
    """
    API endpoint to reconstruct MRI images with advanced algorithms
    """
    try:
        dicom_image = get_object_or_404(DicomImage, id=image_id)
        reconstruction_type = request.data.get('reconstruction_type', 't1_weighted')
        
        # Load the DICOM image
        dicom_path = dicom_image.dicom_file.path
        dicom_data = pydicom.dcmread(dicom_path)
        pixel_array = dicom_data.pixel_array.astype(np.float32)
        
        # Apply MRI reconstruction
        reconstructed_array = advanced_processor.reconstruct_mri_image(pixel_array, reconstruction_type)
        
        # Convert to base64 for transmission
        reconstructed_pil = Image.fromarray(reconstructed_array)
        buffer = io.BytesIO()
        reconstructed_pil.save(buffer, format='PNG')
        reconstructed_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'success': True,
            'reconstructed_image': f"data:image/png;base64,{reconstructed_base64}",
            'reconstruction_type': reconstruction_type,
            'message': f'MRI image reconstructed using {reconstruction_type} algorithm'
        })
        
    except Exception as e:
        logger.error(f"Error reconstructing MRI image: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@api_view(['POST'])
def enhance_mri_image_api(request, image_id):
    """
    API endpoint to enhance MRI images with advanced algorithms
    """
    try:
        dicom_image = get_object_or_404(DicomImage, id=image_id)
        enhancement_type = request.data.get('enhancement_type', 'comprehensive')
        
        # Load the DICOM image
        dicom_path = dicom_image.dicom_file.path
        dicom_data = pydicom.dcmread(dicom_path)
        pixel_array = dicom_data.pixel_array.astype(np.float32)
        
        # Apply MRI enhancement
        enhanced_array = advanced_processor.enhance_mri_image(pixel_array, enhancement_type)
        
        # Convert to base64 for transmission
        enhanced_pil = Image.fromarray(enhanced_array)
        buffer = io.BytesIO()
        enhanced_pil.save(buffer, format='PNG')
        enhanced_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'success': True,
            'enhanced_image': f"data:image/png;base64,{enhanced_base64}",
            'enhancement_type': enhancement_type,
            'message': f'MRI image enhanced using {enhancement_type} algorithm'
        })
        
    except Exception as e:
        logger.error(f"Error enhancing MRI image: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@api_view(['POST'])
def upload_dicom_folder(request):
    """
    Enhanced folder upload functionality for DICOM images from CT and MRI
    """
    try:
        ensure_directories()
        
        if 'folder' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No folder provided'
            }, status=400)
        
        folder_files = request.FILES.getlist('folder')
        facility_id = request.data.get('facility_id')
        
        # Get facility if provided
        facility = None
        if facility_id:
            try:
                facility = Facility.objects.get(id=facility_id)
            except Facility.DoesNotExist:
                pass
        
        # Initialize bulk upload manager
        manager = EnhancedBulkUploadManager(request.user, facility)
        
        # Process folder upload
        upload_result = manager.process_folder_upload(folder_files)
        
        return Response({
            'success': True,
            'upload_id': manager.upload_id,
            'message': f'Folder upload initiated with {len(folder_files)} files',
            'initial_progress': manager.progress
        })
        
    except Exception as e:
        logger.error(f"Error in folder upload: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@api_view(['GET'])
def get_series_images_with_scrolling(request, series_id):
    """
    Enhanced API to get all images in a series with scrolling support
    """
    try:
        series = get_object_or_404(DicomSeries, id=series_id)
        images = DicomImage.objects.filter(series=series).order_by('instance_number')
        
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_images = images[start_idx:end_idx]
        
        # Prepare image data with thumbnails and metadata
        images_data = []
        for image in paginated_images:
            try:
                # Get thumbnail image data
                thumbnail_data = image.get_enhanced_processed_image_base64(
                    window_width=400, 
                    window_level=40,
                    thumbnail_size=(150, 150)
                )
                
                images_data.append({
                    'id': image.id,
                    'instance_number': image.instance_number,
                    'image_position': getattr(image, 'image_position', [0, 0, 0]),
                    'slice_thickness': getattr(image, 'slice_thickness', 1.0),
                    'thumbnail': thumbnail_data,
                    'file_size': image.file_size,
                    'acquisition_time': str(image.acquisition_time) if image.acquisition_time else None,
                    'pixel_spacing': getattr(image, 'pixel_spacing', [1.0, 1.0])
                })
            except Exception as img_error:
                logger.error(f"Error processing image {image.id}: {img_error}")
                images_data.append({
                    'id': image.id,
                    'instance_number': image.instance_number,
                    'error': 'Could not process image'
                })
        
        return Response({
            'success': True,
            'images': images_data,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_images': images.count(),
                'total_pages': (images.count() + per_page - 1) // per_page,
                'has_next': end_idx < images.count(),
                'has_previous': page > 1
            },
            'series_info': {
                'id': series.id,
                'series_description': series.series_description,
                'modality': series.modality,
                'series_number': series.series_number,
                'total_images': images.count()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting series images: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@api_view(['GET'])
def get_bulk_image_data(request):
    """
    Get multiple images at once for efficient viewer loading
    """
    try:
        image_ids = request.GET.get('image_ids', '').split(',')
        if not image_ids or image_ids == ['']:
            return Response({
                'success': False,
                'error': 'No image IDs provided'
            }, status=400)
        
        # Limit to reasonable number of images
        image_ids = image_ids[:50]  # Max 50 images at once
        
        images_data = {}
        for image_id in image_ids:
            try:
                image = DicomImage.objects.get(id=int(image_id))
                
                # Get processed image data
                processed_data = image.get_enhanced_processed_image_base64(
                    window_width=request.GET.get('window_width', 400),
                    window_level=request.GET.get('window_level', 40)
                )
                
                images_data[image_id] = {
                    'success': True,
                    'image_data': processed_data,
                    'metadata': {
                        'instance_number': image.instance_number,
                        'acquisition_time': str(image.acquisition_time) if image.acquisition_time else None,
                        'pixel_spacing': getattr(image, 'pixel_spacing', [1.0, 1.0]),
                        'slice_thickness': getattr(image, 'slice_thickness', 1.0)
                    }
                }
                
            except DicomImage.DoesNotExist:
                images_data[image_id] = {
                    'success': False,
                    'error': 'Image not found'
                }
            except Exception as img_error:
                logger.error(f"Error processing image {image_id}: {img_error}")
                images_data[image_id] = {
                    'success': False,
                    'error': str(img_error)
                }
        
        return Response({
            'success': True,
            'images': images_data,
            'total_requested': len(image_ids),
            'total_processed': len([img for img in images_data.values() if img.get('success')])
        })
        
    except Exception as e:
        logger.error(f"Error in bulk image data: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

# AI Analysis wrapper function for URL compatibility
@csrf_exempt
@require_http_methods(['POST'])
def ai_analysis(request, image_id):
    """Wrapper for perform_ai_analysis for URL compatibility"""
    return perform_ai_analysis(request, image_id)

# Report generation and retrieval functions
@csrf_exempt
@require_http_methods(['POST'])
def generate_report(request, image_id):
    """Generate a medical report for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Get report parameters from request
        data = json.loads(request.body) if request.body else {}
        report_type = data.get('report_type', 'general')
        
        # Get DICOM metadata
        dicom_data = image.load_dicom_data()
        modality = dicom_data.Modality if dicom_data and hasattr(dicom_data, 'Modality') else 'Unknown'
        body_part = dicom_data.BodyPartExamined if dicom_data and hasattr(dicom_data, 'BodyPartExamined') else 'Unknown'
        
        # Generate report content based on type
        report_content = {
            'patient_id': image.series.study.patient_id,
            'patient_name': image.series.study.patient_name,
            'study_date': str(image.series.study.study_date),
            'modality': modality,
            'body_part': body_part,
            'findings': f"Automated analysis of {modality} image showing {body_part} examination.",
            'impression': f"No significant abnormalities detected in this {modality} study.",
            'recommendations': "Clinical correlation recommended."
        }
        
        # Create report record
        report = Report.objects.create(
            image=image,
            report_type=report_type,
            content=json.dumps(report_content),
            generated_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'success': True,
            'report_id': report.id,
            'content': report_content
        })
        
    except DicomImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(['GET'])
def get_report(request, report_id):
    """Retrieve a generated report"""
    try:
        report = Report.objects.get(id=report_id)
        
        # Parse content if it's JSON string
        try:
            content = json.loads(report.content) if isinstance(report.content, str) else report.content
        except json.JSONDecodeError:
            content = report.content
        
        return JsonResponse({
            'success': True,
            'report': {
                'id': report.id,
                'report_type': report.report_type,
                'content': content,
                'created_at': report.created_at.isoformat(),
                'generated_by': report.generated_by.username if report.generated_by else None
            }
        })
        
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    except Exception as e:
        logger.error(f"Error retrieving report: {e}")
        return JsonResponse({'error': str(e)}, status=400)

# Worklist functionality
@csrf_exempt
@require_http_methods(['GET'])
def get_worklist(request):
    """Get worklist entries"""
    try:
        entries = WorklistEntry.objects.all().order_by('-created_at')
        
        worklist_data = []
        for entry in entries:
            worklist_data.append({
                'id': entry.id,
                'patient_id': entry.patient_id,
                'patient_name': entry.patient_name,
                'study_date': str(entry.study_date) if entry.study_date else None,
                'modality': entry.modality,
                'status': entry.status,
                'priority': entry.priority,
                'created_at': entry.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'worklist': worklist_data
        })
        
    except Exception as e:
        logger.error(f"Error getting worklist: {e}")
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(['POST'])
def create_worklist_entry(request):
    """Create a new worklist entry"""
    try:
        data = json.loads(request.body)
        
        entry = WorklistEntry.objects.create(
            patient_id=data.get('patient_id'),
            patient_name=data.get('patient_name'),
            study_date=data.get('study_date'),
            modality=data.get('modality'),
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'normal'),
            description=data.get('description', '')
        )
        
        return JsonResponse({
            'success': True,
            'entry_id': entry.id,
            'message': 'Worklist entry created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating worklist entry: {e}")
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(['PUT', 'PATCH'])
def update_worklist_entry(request, entry_id):
    """Update an existing worklist entry"""
    try:
        entry = WorklistEntry.objects.get(id=entry_id)
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'status' in data:
            entry.status = data['status']
        if 'priority' in data:
            entry.priority = data['priority']
        if 'description' in data:
            entry.description = data['description']
        
        entry.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Worklist entry updated successfully'
        })
        
    except WorklistEntry.DoesNotExist:
        return JsonResponse({'error': 'Worklist entry not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating worklist entry: {e}")
        return JsonResponse({'error': str(e)}, status=400)

# Add this function after the imports and before the existing functions
def get_user_study_queryset(user):
    """
    Get the appropriate study queryset based on user permissions.
    - Facility users: only their facility's studies
    - Radiologists and Admins: all studies from all facilities
    - Others: no studies
    """
    if user.is_superuser:
        # Admins see all studies
        return DicomStudy.objects.all()
    elif user.groups.filter(name='Radiologists').exists():
        # Radiologists see all studies from all facilities
        return DicomStudy.objects.all()
    elif hasattr(user, 'facility') and user.facility:
        # Facility users see only their facility's studies
        return DicomStudy.objects.filter(facility=user.facility)
    elif user.groups.filter(name='Facilities').exists():
        # Facility group members without specific facility see nothing
        return DicomStudy.objects.none()
    else:
        # Other users see nothing
        return DicomStudy.objects.none()

def can_access_study(user, study):
    """
    Check if a user can access a specific study.
    - Admins and Radiologists: can access any study
    - Facility users: can only access studies from their facility
    - Others: cannot access any studies
    """
    if user.is_superuser:
        return True
    elif user.groups.filter(name='Radiologists').exists():
        return True
    elif hasattr(user, 'facility') and user.facility:
        return study.facility == user.facility
    else:
        return False

def notify_new_study_upload(study, uploaded_by_user):
    """
    Create notifications for new study uploads.
    - Notify all radiologists about new study
    - Notify admins about new study
    - Notify facility staff about their own uploads (confirmation)
    """
    from django.contrib.auth.models import Group
    
    # Notify all radiologists
    try:
        radiologist_group = Group.objects.get(name='Radiologists')
        for radiologist in radiologist_group.user_set.all():
            if radiologist != uploaded_by_user:  # Don't notify the uploader
                Notification.objects.create(
                    recipient=radiologist,
                    notification_type='new_study',
                    title='New Study Uploaded',
                    message=f'New {study.modality} study uploaded for {study.patient_name} - {study.study_description or "No description"}',
                    related_study=study
                )
    except Group.DoesNotExist:
        pass
    
    # Notify all admins
    admin_users = User.objects.filter(is_superuser=True)
    for admin in admin_users:
        if admin != uploaded_by_user:  # Don't notify the uploader
            Notification.objects.create(
                recipient=admin,
                notification_type='new_study',
                title='New Study Uploaded',
                message=f'New {study.modality} study uploaded by {uploaded_by_user.get_full_name() or uploaded_by_user.username} for {study.patient_name}',
                related_study=study
            )
    
    # Notify facility staff about their own upload (confirmation)
    if study.facility and study.facility.user and study.facility.user != uploaded_by_user:
        Notification.objects.create(
            recipient=study.facility.user,
            notification_type='new_study',
            title='Study Upload Confirmation',
            message=f'Your {study.modality} study for {study.patient_name} has been successfully uploaded and is ready for review.',
            related_study=study
        )

@api_view(['GET'])
def test_viewer_api(request):
    """Test endpoint to verify API connectivity"""
    try:
        study_count = DicomStudy.objects.count()
        series_count = DicomSeries.objects.count()
        image_count = DicomImage.objects.count()
        
        return Response({
            'status': 'success',
            'message': 'API is working',
            'data': {
                'studies': study_count,
                'series': series_count,
                'images': image_count,
                'timestamp': str(datetime.now())
            }
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)
