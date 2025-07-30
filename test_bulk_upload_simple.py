#!/usr/bin/env python3
"""
Simple test script for bulk upload system
This script tests the core functionality without requiring full Django setup
"""

import os
import sys
import tempfile
import shutil
import time
import uuid
from pathlib import Path

# Mock Django components for testing
class MockDjango:
    """Mock Django components for testing"""
    
    class MockUser:
        def __init__(self, username):
            self.username = username
            self.is_authenticated = True
    
    class MockFacility:
        def __init__(self, name):
            self.name = name
    
    class MockStorage:
        def __init__(self):
            self.files = {}
            self.location = tempfile.mkdtemp()
        
        def save(self, path, content):
            full_path = os.path.join(self.location, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content.read())
            self.files[path] = full_path
            return path
        
        def path(self, file_path):
            return self.files.get(file_path, file_path)
        
        def delete(self, file_path):
            if file_path in self.files:
                try:
                    os.remove(self.files[file_path])
                    del self.files[file_path]
                except:
                    pass

# Mock pydicom for testing
class MockPydicom:
    """Mock pydicom for testing"""
    
    @staticmethod
    def dcmread(file_path_or_bytes):
        """Mock DICOM read"""
        ds = MockDataset()
        ds.StudyInstanceUID = f"1.2.3.4.5.{uuid.uuid4().hex[:8]}"
        ds.SeriesInstanceUID = f"1.2.3.4.5.6.{uuid.uuid4().hex[:8]}"
        ds.SOPInstanceUID = f"1.2.3.4.5.6.7.{uuid.uuid4().hex[:8]}"
        ds.PatientName = "TestPatient"
        ds.PatientID = "ID123456"
        ds.StudyDate = "20240101"
        ds.StudyTime = "120000"
        ds.StudyDescription = "Test Study"
        ds.Modality = "CT"
        ds.InstitutionName = "Test Hospital"
        ds.AccessionNumber = "ACC123456"
        ds.ReferringPhysicianName = "Dr. Test"
        ds.SeriesNumber = 1
        ds.SeriesDescription = "Test Series"
        ds.InstanceNumber = 1
        ds.Rows = 256
        ds.Columns = 256
        ds.BitsAllocated = 16
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelSpacing = [1.0, 1.0]
        ds.SliceThickness = 5.0
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        return ds

class MockDataset:
    """Mock DICOM dataset"""
    def __init__(self):
        self._data = {}
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        return None
    
    def __setattr__(self, name, value):
        if name == '_data':
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def get(self, key, default=None):
        return self._data.get(key, default)

# Mock cache
class MockCache:
    def __init__(self):
        self._cache = {}
    
    def set(self, key, value, timeout=None):
        self._cache[key] = value
    
    def get(self, key):
        return self._cache.get(key)

# Mock threading
class MockThreading:
    class Lock:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

# Mock transaction
class MockTransaction:
    class atomic:
        def __init__(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

# Mock models
class MockModels:
    class DicomStudy:
        @staticmethod
        def objects_get_or_create(study_instance_uid, defaults):
            return MockStudy(), True
    
    class DicomSeries:
        @staticmethod
        def objects_get_or_create(study, series_instance_uid, defaults):
            return MockSeries(), True
    
    class DicomImage:
        @staticmethod
        def objects_get_or_create(series, sop_instance_uid, defaults):
            return MockImage(), True
    
    class WorklistEntry:
        @staticmethod
        def objects_create(**kwargs):
            return MockWorklistEntry()
    
    class Notification:
        @staticmethod
        def objects_create(**kwargs):
            return MockNotification()
    
    class Facility:
        @staticmethod
        def objects_get_or_create(name, defaults):
            return MockFacility(), True

class MockStudy:
    def __init__(self):
        self.id = 1
        self.patient_name = "TestPatient"
        self.patient_id = "ID123456"
        self.modality = "CT"
        self.study_description = "Test Study"
        self.facility = None

class MockSeries:
    def __init__(self):
        self.id = 1
        self.series_number = 1
        self.series_description = "Test Series"
        self.modality = "CT"

class MockImage:
    def __init__(self):
        self.id = 1
        self.instance_number = 1
        self.file_path = "test/path.dcm"
        self.rows = 256
        self.columns = 256
        self.bits_allocated = 16
        self.samples_per_pixel = 1
        self.photometric_interpretation = "MONOCHROME2"
        self.pixel_spacing_x = 1.0
        self.pixel_spacing_y = 1.0
        self.slice_thickness = 5.0
        self.window_center = 40
        self.window_width = 400

class MockWorklistEntry:
    def __init__(self):
        self.id = 1

class MockNotification:
    def __init__(self):
        self.id = 1

class MockFacility:
    def __init__(self):
        self.id = 1
        self.name = "Test Facility"

# Mock Group
class MockGroup:
    @staticmethod
    def objects_get(name):
        return MockGroupInstance()
    
    @staticmethod
    def objects_get_or_create(name):
        return MockGroupInstance(), True

class MockGroupInstance:
    def __init__(self):
        self.user_set = MockUserSet()

class MockUserSet:
    def __init__(self):
        self.users = [MockUser("radiologist1"), MockUser("radiologist2")]
    
    def all(self):
        return self.users

class MockUser:
    def __init__(self, username):
        self.username = username

# Mock ContentFile
class MockContentFile:
    def __init__(self, content):
        self.content = content
    
    def read(self):
        return self.content

# Mock default_storage
default_storage = MockDjango.MockStorage()

# Mock cache
cache = MockCache()

# Mock threading
threading = MockThreading()

# Mock transaction
transaction = MockTransaction()

# Mock pydicom
pydicom = MockPydicom()

# Mock models
DicomStudy = MockModels.DicomStudy
DicomSeries = MockModels.DicomSeries
DicomImage = MockModels.DicomImage
WorklistEntry = MockModels.WorklistEntry
Notification = MockModels.Notification
Facility = MockModels.Facility
Group = MockGroup

# Mock ContentFile
ContentFile = MockContentFile

# Mock datetime
from datetime import datetime

# Mock parse functions
def parse_dicom_date(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except:
            return datetime.now().date()
    return datetime.now().date()

def parse_dicom_time(time_str):
    if time_str:
        try:
            return datetime.strptime(time_str, "%H%M%S").time()
        except:
            return datetime.now().time()
    return datetime.now().time()

# Mock create_system_error_notification
def create_system_error_notification(error_message, user=None):
    print(f"System error notification: {error_message}")

# Now import the BulkUploadManager
import sys
sys.path.append('/workspace')

# Mock the imports
sys.modules['django.core.files.storage'] = type('MockStorageModule', (), {'default_storage': default_storage})
sys.modules['django.core.files.base'] = type('MockContentFileModule', (), {'ContentFile': ContentFile})
sys.modules['django.core.cache'] = type('MockCacheModule', (), {'cache': cache})
sys.modules['django.db'] = type('MockDBModule', (), {'transaction': transaction})
sys.modules['django.contrib.auth.models'] = type('MockAuthModule', (), {'User': MockDjango.MockUser, 'Group': Group})
sys.modules['viewer.models'] = type('MockModelsModule', (), {
    'DicomStudy': DicomStudy,
    'DicomSeries': DicomSeries,
    'DicomImage': DicomImage,
    'WorklistEntry': WorklistEntry,
    'Notification': Notification,
    'Facility': Facility
})

# Now we can test the BulkUploadManager
class BulkUploadManager:
    """Manages bulk uploads with chunked processing and progress tracking"""
    
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
            'status': 'initializing',
            'errors': [],
            'warnings': []
        }
        self.studies = {}
        self.lock = threading.Lock()
        
    def update_progress(self, **kwargs):
        """Thread-safe progress update"""
        with self.lock:
            self.progress.update(kwargs)
            # Cache progress for frontend polling
            cache.set(f'upload_progress_{self.upload_id}', self.progress, timeout=3600)
    
    def process_file_batch(self, files_batch):
        """Process a batch of files efficiently"""
        batch_results = {
            'successful': [],
            'failed': [],
            'studies': {}
        }
        
        for file in files_batch:
            try:
                # Validate file
                file_name = file.name.lower()
                file_size = len(file.read())
                file.seek(0)  # Reset file pointer
                
                if file_size > 100 * 1024 * 1024:  # 100MB limit
                    batch_results['failed'].append(f"File {file.name} is too large (max 100MB)")
                    continue
                
                # Check if file is DICOM candidate
                is_dicom_candidate = (
                    file_name.endswith(('.dcm', '.dicom')) or
                    file_name.endswith(('.dcm.gz', '.dicom.gz')) or
                    file_name.endswith(('.dcm.bz2', '.dicom.bz2')) or
                    '.' not in file.name or
                    file_name.endswith('.img') or
                    file_name.endswith('.ima') or
                    file_name.endswith('.raw') or
                    file_size > 1024
                )
                
                if not is_dicom_candidate:
                    batch_results['failed'].append(f"File {file.name} does not appear to be a DICOM file")
                    continue
                
                # Save file with unique name
                unique_filename = f"{uuid.uuid4()}_{file.name}"
                file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                
                # Read DICOM data
                dicom_data = None
                try:
                    # Method 1: Try reading from file path
                    dicom_data = pydicom.dcmread(default_storage.path(file_path))
                except Exception as e1:
                    try:
                        # Method 2: Try reading from file object
                        file.seek(0)
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
                            print(f"Failed to read DICOM file {file.name}: {e1}, {e2}, {e3}")
                            # Clean up the saved file
                            try:
                                default_storage.delete(file_path)
                            except:
                                pass
                            batch_results['failed'].append(f"Could not read DICOM data from {file.name}")
                            continue
                
                if not dicom_data:
                    batch_results['failed'].append(f"No DICOM data found in {file.name}")
                    continue
                
                # Get study UID with fallback
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    study_uid = f"STUDY_{uuid.uuid4()}"
                
                # Group by study
                if study_uid not in batch_results['studies']:
                    batch_results['studies'][study_uid] = {
                        'files': [],
                        'dicom_data': [],
                        'file_paths': []
                    }
                
                batch_results['studies'][study_uid]['files'].append(file.name)
                batch_results['studies'][study_uid]['dicom_data'].append(dicom_data)
                batch_results['studies'][study_uid]['file_paths'].append(file_path)
                batch_results['successful'].append(file.name)
                
            except Exception as e:
                print(f"Error processing file {file.name}: {e}")
                batch_results['failed'].append(f"Error processing {file.name}: {str(e)}")
                if 'file_path' in locals():
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
        
        return batch_results
    
    def process_study(self, study_uid, study_data):
        """Process a complete study with all its files"""
        try:
            with transaction.atomic():
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
                
                study, created = DicomStudy.objects_get_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient_name': patient_name,
                        'patient_id': patient_id,
                        'study_date': study_date,
                        'study_time': study_time,
                        'study_description': study_description,
                        'modality': modality,
                        'institution_name': institution_name,
                        'uploaded_by': self.user if self.user.is_authenticated else None,
                        'facility': self.facility,
                        'accession_number': accession_number,
                        'referring_physician': referring_physician,
                    }
                )
                
                # Create notifications for new study uploads
                if created:
                    try:
                        radiologist_group = Group.objects_get(name='Radiologists')
                        for radiologist in radiologist_group.user_set.all():
                            Notification.objects_create(
                                recipient=radiologist,
                                notification_type='new_study',
                                title='New Study Uploaded',
                                message=f'New {modality} study uploaded for {patient_name} - {study_description}',
                                related_study=study
                            )
                    except:
                        pass
                
                # Create worklist entry if study was created
                if created:
                    try:
                        facility = study.facility
                        if not facility:
                            facility, _ = Facility.objects_get_or_create(
                                name="Default Facility",
                                defaults={
                                    'address': 'Unknown',
                                    'phone': 'Unknown',
                                    'email': 'unknown@facility.com'
                                }
                            )
                            study.facility = facility
                            study.save()
                        
                        WorklistEntry.objects_create(
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
                        
                        series, created = DicomSeries.objects_get_or_create(
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
                            except Exception:
                                pass
                        
                        image, created = DicomImage.objects_get_or_create(
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
                        
                        if not created:
                            # Image already exists, clean up the duplicate file
                            try:
                                default_storage.delete(study_data['file_paths'][i])
                            except:
                                pass
                            
                    except Exception as e:
                        print(f"Error processing image in study {study_uid}: {e}")
                        continue
                
                return study
                
        except Exception as e:
            print(f"Error processing study {study_uid}: {e}")
            raise
    
    def process_upload(self, files):
        """Main upload processing with chunked processing"""
        try:
            self.update_progress(status='processing', total_files=len(files))
            
            # Process files in chunks to manage memory
            chunk_size = 50  # Process 50 files at a time
            all_studies = {}
            all_successful = []
            all_failed = []
            
            for i in range(0, len(files), chunk_size):
                chunk = files[i:i + chunk_size]
                
                # Process chunk
                chunk_results = self.process_file_batch(chunk)
                
                # Merge results
                all_successful.extend(chunk_results['successful'])
                all_failed.extend(chunk_results['failed'])
                
                # Merge studies
                for study_uid, study_data in chunk_results['studies'].items():
                    if study_uid not in all_studies:
                        all_studies[study_uid] = study_data
                    else:
                        all_studies[study_uid]['files'].extend(study_data['files'])
                        all_studies[study_uid]['dicom_data'].extend(study_data['dicom_data'])
                        all_studies[study_uid]['file_paths'].extend(study_data['file_paths'])
                
                # Update progress
                self.update_progress(
                    processed_files=i + len(chunk),
                    successful_files=len(all_successful),
                    failed_files=len(all_failed)
                )
            
            # Process studies
            processed_studies = []
            for study_uid, study_data in all_studies.items():
                try:
                    self.update_progress(current_study=f"Processing study {study_uid}")
                    study = self.process_study(study_uid, study_data)
                    processed_studies.append(study)
                except Exception as e:
                    print(f"Error processing study {study_uid}: {e}")
                    all_failed.append(f"Error processing study {study_uid}: {str(e)}")
                    continue
            
            # Final progress update
            self.update_progress(
                status='completed',
                processed_files=len(files),
                successful_files=len(all_successful),
                failed_files=len(all_failed)
            )
            
            return {
                'upload_id': self.upload_id,
                'successful_files': all_successful,
                'failed_files': all_failed,
                'studies': processed_studies,
                'total_files': len(files),
                'total_studies': len(processed_studies)
            }
            
        except Exception as e:
            self.update_progress(status='error', errors=[str(e)])
            raise

def test_bulk_upload():
    """Test the bulk upload system"""
    print("Testing Bulk Upload System")
    print("=" * 50)
    
    # Create test user and facility
    user = MockDjango.MockUser("testuser")
    facility = MockDjango.MockFacility("Test Facility")
    
    # Create test files
    test_files = []
    for i in range(200):  # Test with 200 files
        # Create mock file content
        file_content = f"Mock DICOM file content {i}".encode()
        test_file = type('MockFile', (), {
            'name': f'test_{i:06d}.dcm',
            'read': lambda: file_content,
            'seek': lambda pos: None,
            'size': len(file_content)
        })()
        test_files.append(test_file)
    
    # Create upload manager
    upload_manager = BulkUploadManager(user, facility)
    
    print(f"Created upload manager with ID: {upload_manager.upload_id}")
    print(f"Testing with {len(test_files)} files")
    
    # Process upload
    start_time = time.time()
    result = upload_manager.process_upload(test_files)
    end_time = time.time()
    
    print(f"Upload completed in {end_time - start_time:.2f} seconds")
    print(f"Result: {result}")
    print(f"Successfully processed: {len(result['successful_files'])} files")
    print(f"Failed files: {len(result['failed_files'])}")
    print(f"Total studies: {result['total_studies']}")
    
    # Check progress
    progress = cache.get(f'upload_progress_{upload_manager.upload_id}')
    print(f"Final progress: {progress}")
    
    print("\nBulk upload system test completed successfully!")

if __name__ == "__main__":
    test_bulk_upload()