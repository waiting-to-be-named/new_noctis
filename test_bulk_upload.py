#!/usr/bin/env python3
"""
Test script for bulk upload system with large folders (2000+ images)
This script tests the new bulk upload functionality that can handle large folders efficiently.
"""

import os
import sys
import django
import tempfile
import shutil
from pathlib import Path

# Add the project directory to Python path
sys.path.append('/workspace')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from viewer.models import Facility, DicomStudy, DicomSeries, DicomImage
import pydicom
from pydicom.dataset import Dataset
import numpy as np
import uuid
import time

class BulkUploadTest:
    """Test class for bulk upload functionality"""
    
    def __init__(self):
        self.client = Client()
        self.test_files = []
        self.temp_dir = None
        
    def create_test_dicom_files(self, num_files=50):
        """Create test DICOM files for testing"""
        print(f"Creating {num_files} test DICOM files...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        for i in range(num_files):
            # Create a simple DICOM dataset
            ds = Dataset()
            ds.StudyInstanceUID = f"1.2.3.4.5.{i}"
            ds.SeriesInstanceUID = f"1.2.3.4.5.6.{i}"
            ds.SOPInstanceUID = f"1.2.3.4.5.6.7.{i}"
            ds.PatientName = f"TestPatient{i}"
            ds.PatientID = f"ID{i:06d}"
            ds.StudyDate = "20240101"
            ds.StudyTime = "120000"
            ds.StudyDescription = f"Test Study {i}"
            ds.Modality = "CT"
            ds.InstitutionName = "Test Hospital"
            ds.AccessionNumber = f"ACC{i:06d}"
            ds.ReferringPhysicianName = "Dr. Test"
            ds.SeriesNumber = i
            ds.SeriesDescription = f"Test Series {i}"
            ds.InstanceNumber = i
            ds.Rows = 256
            ds.Columns = 256
            ds.BitsAllocated = 16
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.PixelSpacing = [1.0, 1.0]
            ds.SliceThickness = 5.0
            ds.WindowCenter = 40
            ds.WindowWidth = 400
            
            # Create pixel data
            pixel_data = np.random.randint(0, 65535, (256, 256), dtype=np.uint16)
            ds.PixelData = pixel_data.tobytes()
            
            # Save DICOM file
            filename = f"test_{i:06d}.dcm"
            filepath = os.path.join(self.temp_dir, filename)
            ds.save_as(filepath)
            self.test_files.append(filepath)
            
        print(f"Created {len(self.test_files)} test DICOM files in {self.temp_dir}")
    
    def setup_test_user(self):
        """Setup test user and facility"""
        print("Setting up test user and facility...")
        
        # Create test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create facility
        facility, created = Facility.objects.get_or_create(
            name='Test Facility',
            defaults={
                'address': '123 Test St',
                'phone': '555-1234',
                'email': 'test@facility.com'
            }
        )
        
        # Create radiologist group
        radiologist_group, created = Group.objects.get_or_create(name='Radiologists')
        user.groups.add(radiologist_group)
        
        # Login user
        self.client.force_login(user)
        
        print(f"Test user setup complete: {user.username}")
        return user, facility
    
    def test_small_upload(self):
        """Test small upload (less than 100 files)"""
        print("\n=== Testing Small Upload ===")
        
        # Create 50 test files
        self.create_test_dicom_files(50)
        
        # Prepare upload data
        files = []
        for filepath in self.test_files:
            with open(filepath, 'rb') as f:
                files.append(('files', SimpleUploadedFile(
                    os.path.basename(filepath),
                    f.read(),
                    content_type='application/dicom'
                )))
        
        # Perform upload
        start_time = time.time()
        response = self.client.post('/viewer/api/bulk-upload/', files)
        end_time = time.time()
        
        print(f"Upload completed in {end_time - start_time:.2f} seconds")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload result: {result}")
            print(f"Status: {result.get('status')}")
            if result.get('status') == 'completed':
                print(f"Successfully processed {len(result.get('successful_files', []))} files")
                print(f"Failed files: {len(result.get('failed_files', []))}")
                print(f"Total studies: {result.get('total_studies', 0)}")
        else:
            print(f"Upload failed: {response.content}")
        
        # Cleanup
        self.cleanup()
    
    def test_large_upload(self):
        """Test large upload (more than 100 files) - background processing"""
        print("\n=== Testing Large Upload (Background Processing) ===")
        
        # Create 150 test files
        self.create_test_dicom_files(150)
        
        # Prepare upload data
        files = []
        for filepath in self.test_files:
            with open(filepath, 'rb') as f:
                files.append(('files', SimpleUploadedFile(
                    os.path.basename(filepath),
                    f.read(),
                    content_type='application/dicom'
                )))
        
        # Perform upload
        start_time = time.time()
        response = self.client.post('/viewer/api/bulk-upload/', files)
        end_time = time.time()
        
        print(f"Upload initiated in {end_time - start_time:.2f} seconds")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload result: {result}")
            print(f"Status: {result.get('status')}")
            
            if result.get('status') == 'processing':
                upload_id = result.get('upload_id')
                print(f"Background processing started with ID: {upload_id}")
                
                # Monitor progress
                self.monitor_upload_progress(upload_id)
            else:
                print("Unexpected status for large upload")
        else:
            print(f"Upload failed: {response.content}")
        
        # Cleanup
        self.cleanup()
    
    def monitor_upload_progress(self, upload_id):
        """Monitor upload progress for background uploads"""
        print(f"Monitoring upload progress for ID: {upload_id}")
        
        max_attempts = 60  # 2 minutes max
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # Get progress
                progress_response = self.client.get(f'/viewer/api/upload-progress/{upload_id}/')
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    print(f"Progress: {progress.get('processed_files', 0)}/{progress.get('total_files', 0)} files processed")
                    print(f"Status: {progress.get('status')}")
                    print(f"Current study: {progress.get('current_study', 'N/A')}")
                    
                    if progress.get('status') == 'completed':
                        # Get final result
                        result_response = self.client.get(f'/viewer/api/upload-result/{upload_id}/')
                        if result_response.status_code == 200:
                            result = result_response.json()
                            print(f"Upload completed successfully!")
                            print(f"Successfully processed: {len(result.get('successful_files', []))} files")
                            print(f"Failed files: {len(result.get('failed_files', []))}")
                            print(f"Total studies: {result.get('total_studies', 0)}")
                        else:
                            print(f"Failed to get upload result: {result_response.status_code}")
                        break
                    elif progress.get('status') == 'error':
                        print(f"Upload failed: {progress.get('errors', [])}")
                        break
                else:
                    print(f"Failed to get progress: {progress_response.status_code}")
                    break
                    
            except Exception as e:
                print(f"Error monitoring progress: {e}")
                break
            
            attempts += 1
            time.sleep(2)  # Wait 2 seconds between checks
        
        if attempts >= max_attempts:
            print("Upload monitoring timed out")
    
    def test_very_large_upload(self):
        """Test very large upload (500+ files) to simulate 2000+ image scenario"""
        print("\n=== Testing Very Large Upload (500+ files) ===")
        
        # Create 500 test files (simulating a large study)
        self.create_test_dicom_files(500)
        
        # Prepare upload data
        files = []
        for filepath in self.test_files:
            with open(filepath, 'rb') as f:
                files.append(('files', SimpleUploadedFile(
                    os.path.basename(filepath),
                    f.read(),
                    content_type='application/dicom'
                )))
        
        # Perform upload
        start_time = time.time()
        response = self.client.post('/viewer/api/bulk-upload/', files)
        end_time = time.time()
        
        print(f"Upload initiated in {end_time - start_time:.2f} seconds")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload result: {result}")
            print(f"Status: {result.get('status')}")
            
            if result.get('status') == 'processing':
                upload_id = result.get('upload_id')
                print(f"Background processing started with ID: {upload_id}")
                
                # Monitor progress
                self.monitor_upload_progress(upload_id)
            else:
                print("Unexpected status for large upload")
        else:
            print(f"Upload failed: {response.content}")
        
        # Cleanup
        self.cleanup()
    
    def cleanup(self):
        """Clean up test files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
        self.test_files = []
    
    def run_all_tests(self):
        """Run all bulk upload tests"""
        print("Starting bulk upload system tests...")
        
        # Setup test environment
        user, facility = self.setup_test_user()
        
        try:
            # Test small upload
            self.test_small_upload()
            
            # Test large upload
            self.test_large_upload()
            
            # Test very large upload
            self.test_very_large_upload()
            
            print("\n=== All tests completed ===")
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

def main():
    """Main function to run tests"""
    print("Bulk Upload System Test")
    print("=" * 50)
    
    test = BulkUploadTest()
    test.run_all_tests()

if __name__ == "__main__":
    main()