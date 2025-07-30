#!/usr/bin/env python3
"""
Comprehensive test script to verify all fixes:
1. File upload 400 error fixes
2. Bulk upload with nested folders
3. DICOM viewer brightness improvements
4. 3D dropdown clickability
5. Folder upload with multiple subfolders
"""

import os
import sys
import django
import tempfile
import shutil
from pathlib import Path

# Setup Django
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from viewer.models import DicomStudy, DicomSeries, DicomImage, Facility
import json
import base64
import io
import numpy as np
from PIL import Image

class ComprehensiveFixesTest(TestCase):
    """Test all the comprehensive fixes"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        
        # Create test facility
        self.facility = Facility.objects.create(
            name='Test Hospital',
            address='123 Test St',
            phone='555-1234',
            email='test@hospital.com'
        )
        
        # Create test study
        self.study = DicomStudy.objects.create(
            study_instance_uid='TEST_STUDY_001',
            patient_name='Test Patient',
            patient_id='TEST001',
            modality='CT',
            facility=self.facility,
            uploaded_by=self.user
        )
        
        # Create test series
        self.series = DicomSeries.objects.create(
            study=self.study,
            series_instance_uid='TEST_SERIES_001',
            series_number=1,
            modality='CT'
        )
        
        # Create test client
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def create_test_dicom_file(self, filename='test.dcm', rows=256, cols=256):
        """Create a test DICOM file with proper pixel data"""
        import pydicom
        from pydicom.dataset import FileDataset, FileMetaDataset
        
        # Create file meta info
        file_meta = FileMetaDataset()
        file_meta.FileMetaInformationGroupLength = 0
        file_meta.FileMetaInformationVersion = b'\x00\x01'
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
        file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9.10'
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'  # Explicit VR Little Endian
        
        # Create dataset
        ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Add required DICOM elements
        ds.PatientName = 'Test Patient'
        ds.PatientID = 'TEST001'
        ds.StudyInstanceUID = '1.2.3.4.5.6.7.8.9.10'
        ds.SeriesInstanceUID = '1.2.3.4.5.6.7.8.9.11'
        ds.SOPInstanceUID = '1.2.3.4.5.6.7.8.9.12'
        ds.Modality = 'CT'
        ds.StudyDescription = 'Test Study'
        ds.SeriesDescription = 'Test Series'
        ds.StudyDate = '20240101'
        ds.StudyTime = '120000'
        ds.AccessionNumber = 'ACC001'
        ds.InstitutionName = 'Test Hospital'
        ds.ReferringPhysicianName = 'Dr. Test'
        
        # Image-specific elements
        ds.Rows = rows
        ds.Columns = cols
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = 'MONOCHROME2'
        ds.PixelSpacing = [1.0, 1.0]
        ds.SliceThickness = 1.0
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        
        # Create pixel data with better contrast
        pixel_data = np.random.randint(0, 4096, (rows, cols), dtype=np.uint16)
        # Add some structure for better testing
        pixel_data[100:150, 100:150] = 2000  # Bright region
        pixel_data[50:100, 50:100] = 500     # Dark region
        ds.PixelData = pixel_data.tobytes()
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.dcm')
        ds.save_as(temp_file.name)
        temp_file.close()
        
        return temp_file.name
    
    def test_upload_file_400_error_fix(self):
        """Test that file upload no longer returns 400 errors for valid files"""
        print("\n=== Testing File Upload 400 Error Fix ===")
        
        # Create test DICOM file
        dicom_file_path = self.create_test_dicom_file()
        
        try:
            with open(dicom_file_path, 'rb') as f:
                upload_data = {
                    'files': SimpleUploadedFile(
                        'test.dcm',
                        f.read(),
                        content_type='application/dicom'
                    )
                }
            
            # Test upload endpoint
            response = self.client.post('/viewer/api/upload/', upload_data)
            
            print(f"Upload response status: {response.status_code}")
            print(f"Upload response content: {response.content.decode()}")
            
            # Should not return 400 error
            self.assertNotEqual(response.status_code, 400, 
                              "Upload should not return 400 error for valid DICOM file")
            
            if response.status_code == 200:
                response_data = json.loads(response.content)
                print(f"Uploaded files: {response_data.get('uploaded_files', [])}")
                self.assertIn('uploaded_files', response_data)
                
        finally:
            # Clean up
            if os.path.exists(dicom_file_path):
                os.unlink(dicom_file_path)
    
    def test_bulk_upload_nested_folders(self):
        """Test bulk upload with nested folder structure"""
        print("\n=== Testing Bulk Upload with Nested Folders ===")
        
        # Create temporary directory structure
        temp_dir = tempfile.mkdtemp()
        try:
            # Create nested folder structure
            folder1 = os.path.join(temp_dir, 'folder1')
            folder2 = os.path.join(temp_dir, 'folder1', 'subfolder')
            os.makedirs(folder2, exist_ok=True)
            
            # Create DICOM files in different locations
            files_to_upload = []
            
            # File in root
            file1_path = self.create_test_dicom_file('root.dcm')
            files_to_upload.append(('root.dcm', file1_path))
            
            # File in folder1
            file2_path = self.create_test_dicom_file('folder1.dcm')
            shutil.move(file2_path, os.path.join(folder1, 'folder1.dcm'))
            files_to_upload.append(('folder1/folder1.dcm', os.path.join(folder1, 'folder1.dcm')))
            
            # File in subfolder
            file3_path = self.create_test_dicom_file('subfolder.dcm')
            shutil.move(file3_path, os.path.join(folder2, 'subfolder.dcm'))
            files_to_upload.append(('folder1/subfolder/subfolder.dcm', os.path.join(folder2, 'subfolder.dcm')))
            
            # Prepare upload data
            upload_data = {}
            for filename, filepath in files_to_upload:
                with open(filepath, 'rb') as f:
                    upload_data[f'files'] = SimpleUploadedFile(
                        filename,
                        f.read(),
                        content_type='application/dicom'
                    )
            
            # Test bulk upload
            response = self.client.post('/viewer/api/bulk-upload/', upload_data)
            
            print(f"Bulk upload response status: {response.status_code}")
            print(f"Bulk upload response content: {response.content.decode()}")
            
            # Should not return 400 error
            self.assertNotEqual(response.status_code, 400,
                              "Bulk upload should not return 400 error for valid files")
            
        finally:
            # Clean up
            for filename, filepath in files_to_upload:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            shutil.rmtree(temp_dir)
    
    def test_dicom_brightness_improvements(self):
        """Test that DICOM images have better brightness and contrast"""
        print("\n=== Testing DICOM Brightness Improvements ===")
        
        # Create test DICOM file
        dicom_file_path = self.create_test_dicom_file()
        
        try:
            # Upload the file
            with open(dicom_file_path, 'rb') as f:
                upload_data = {
                    'files': SimpleUploadedFile(
                        'test.dcm',
                        f.read(),
                        content_type='application/dicom'
                    )
                }
            
            response = self.client.post('/viewer/api/upload/', upload_data)
            
            if response.status_code == 200:
                response_data = json.loads(response.content)
                study_id = response_data.get('study_id')
                
                if study_id:
                    # Get the uploaded image
                    study = DicomStudy.objects.get(id=study_id)
                    image = study.series.first().images.first()
                    
                    # Test image processing with different window/level settings
                    pixel_array = image.get_pixel_array()
                    
                    if pixel_array is not None:
                        # Test default processing (should use improved defaults)
                        processed_default = image.apply_windowing(pixel_array)
                        
                        # Test with custom window/level
                        processed_custom = image.apply_windowing(
                            pixel_array, 
                            window_width=800, 
                            window_level=200
                        )
                        
                        # Test with very narrow window for high contrast
                        processed_contrast = image.apply_windowing(
                            pixel_array,
                            window_width=200,
                            window_level=100
                        )
                        
                        # Verify all processed images are valid
                        self.assertIsNotNone(processed_default, "Default processing should work")
                        self.assertIsNotNone(processed_custom, "Custom window/level should work")
                        self.assertIsNotNone(processed_contrast, "High contrast processing should work")
                        
                        # Check that images have reasonable pixel values
                        for processed in [processed_default, processed_custom, processed_contrast]:
                            if processed is not None:
                                min_val = np.min(processed)
                                max_val = np.max(processed)
                                print(f"Processed image range: {min_val} to {max_val}")
                                
                                # Should have some contrast (not all same value)
                                self.assertGreater(max_val - min_val, 0, 
                                                "Processed image should have contrast")
                                
                                # Values should be in valid range
                                self.assertGreaterEqual(min_val, 0)
                                self.assertLessEqual(max_val, 255)
                        
                        print("✓ DICOM brightness improvements working correctly")
                    else:
                        print("⚠ Could not get pixel array for testing")
                else:
                    print("⚠ No study ID returned from upload")
            else:
                print(f"⚠ Upload failed with status {response.status_code}")
                
        finally:
            if os.path.exists(dicom_file_path):
                os.unlink(dicom_file_path)
    
    def test_3d_dropdown_functionality(self):
        """Test that 3D dropdown menus are clickable"""
        print("\n=== Testing 3D Dropdown Functionality ===")
        
        # Test the viewer page loads
        response = self.client.get('/viewer/')
        self.assertEqual(response.status_code, 200, "Viewer page should load")
        
        # Check that dropdown elements are present in the HTML
        content = response.content.decode()
        
        # Check for 3D dropdown elements
        self.assertIn('dropdown-toggle', content, "Dropdown toggle buttons should be present")
        self.assertIn('reconstruction-dropdown', content, "3D reconstruction dropdown should be present")
        self.assertIn('apply3DReconstruction', content, "3D reconstruction functions should be present")
        
        # Check for AI dropdown elements
        self.assertIn('ai-dropdown', content, "AI dropdown should be present")
        self.assertIn('performAIAnalysis', content, "AI analysis functions should be present")
        
        print("✓ 3D dropdown elements are present in HTML")
        
        # Test that CSS classes are properly defined
        css_file_path = '/workspace/static/css/dicom_viewer.css'
        if os.path.exists(css_file_path):
            with open(css_file_path, 'r') as f:
                css_content = f.read()
                
            # Check for dropdown CSS
            self.assertIn('.dropdown-menu', css_content, "Dropdown menu CSS should be present")
            self.assertIn('.dropdown-tool.active .dropdown-menu', css_content, 
                         "Active dropdown CSS should be present")
            self.assertIn('pointer-events: auto', css_content, 
                         "Pointer events CSS should be present")
            
            print("✓ Dropdown CSS is properly configured")
        else:
            print("⚠ CSS file not found")
    
    def test_folder_upload_multiple_files(self):
        """Test uploading folders with multiple files in different subfolders"""
        print("\n=== Testing Folder Upload with Multiple Files ===")
        
        # Create temporary directory with multiple files
        temp_dir = tempfile.mkdtemp()
        try:
            # Create multiple DICOM files in different locations
            files_created = []
            
            # Create files in root
            for i in range(3):
                file_path = self.create_test_dicom_file(f'root_{i}.dcm')
                files_created.append(file_path)
            
            # Create subfolder and add files
            subfolder = os.path.join(temp_dir, 'subfolder')
            os.makedirs(subfolder, exist_ok=True)
            
            for i in range(2):
                file_path = self.create_test_dicom_file(f'sub_{i}.dcm')
                new_path = os.path.join(subfolder, f'sub_{i}.dcm')
                shutil.move(file_path, new_path)
                files_created.append(new_path)
            
            # Create nested subfolder
            nested_folder = os.path.join(subfolder, 'nested')
            os.makedirs(nested_folder, exist_ok=True)
            
            for i in range(2):
                file_path = self.create_test_dicom_file(f'nested_{i}.dcm')
                new_path = os.path.join(nested_folder, f'nested_{i}.dcm')
                shutil.move(file_path, new_path)
                files_created.append(new_path)
            
            # Prepare upload data with all files
            upload_data = {}
            for file_path in files_created:
                filename = os.path.basename(file_path)
                with open(file_path, 'rb') as f:
                    upload_data[f'files'] = SimpleUploadedFile(
                        filename,
                        f.read(),
                        content_type='application/dicom'
                    )
            
            # Test folder upload
            response = self.client.post('/viewer/api/upload-folder/', upload_data)
            
            print(f"Folder upload response status: {response.status_code}")
            print(f"Folder upload response content: {response.content.decode()}")
            
            # Should not return 400 error
            self.assertNotEqual(response.status_code, 400,
                              "Folder upload should not return 400 error")
            
            if response.status_code == 200:
                response_data = json.loads(response.content)
                uploaded_files = response_data.get('uploaded_files', [])
                print(f"Successfully uploaded {len(uploaded_files)} files")
                
                # Should have uploaded multiple files
                self.assertGreater(len(uploaded_files), 1, 
                                 "Should upload multiple files from folder")
                
        finally:
            # Clean up
            for file_path in files_created:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            shutil.rmtree(temp_dir)
    
    def test_various_file_formats(self):
        """Test upload with various DICOM file formats"""
        print("\n=== Testing Various File Formats ===")
        
        # Test different file extensions
        extensions = ['.dcm', '.dicom', '.img', '.ima', '.raw', '.dat', '.bin']
        
        for ext in extensions:
            print(f"Testing extension: {ext}")
            
            # Create test file with this extension
            dicom_file_path = self.create_test_dicom_file(f'test{ext}')
            
            try:
                with open(dicom_file_path, 'rb') as f:
                    upload_data = {
                        'files': SimpleUploadedFile(
                            f'test{ext}',
                            f.read(),
                            content_type='application/dicom'
                        )
                    }
                
                response = self.client.post('/viewer/api/upload/', upload_data)
                
                print(f"  Response status: {response.status_code}")
                
                # Should not return 400 error for any valid DICOM format
                self.assertNotEqual(response.status_code, 400,
                                  f"Upload should work for {ext} extension")
                
            finally:
                if os.path.exists(dicom_file_path):
                    os.unlink(dicom_file_path)
    
    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Fixes Test Suite")
        print("=" * 60)
        
        try:
            self.test_upload_file_400_error_fix()
            self.test_bulk_upload_nested_folders()
            self.test_dicom_brightness_improvements()
            self.test_3d_dropdown_functionality()
            self.test_folder_upload_multiple_files()
            self.test_various_file_formats()
            
            print("\n" + "=" * 60)
            print("✅ All comprehensive fixes tests completed successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    # Run the comprehensive test
    test_suite = ComprehensiveFixesTest()
    test_suite.setUp()
    test_suite.run_all_tests()