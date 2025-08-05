"""
Comprehensive testing system for Noctis DICOM viewer.
This module provides unit tests, integration tests, and performance tests.
"""

import os
import tempfile
import shutil
import json
import time
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
import numpy as np
import pydicom
from unittest.mock import patch, MagicMock
import logging

from viewer.models import (
    DicomStudy, DicomSeries, DicomImage, WorklistEntry, 
    Facility, Notification, AIAnalysis
)
from viewer.services import (
    DicomProcessingService, UploadService, ImageProcessingService,
    WorklistService, ErrorHandlingService
)
from noctisview.security import SecurityManager, security_manager
from noctisview.logging_config import error_tracker, performance_monitor

logger = logging.getLogger(__name__)


class ComprehensiveSystemTestCase(TestCase):
    """Comprehensive system test case"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test groups
        self.radiologist_group = Group.objects.create(name='Radiologists')
        self.admin_group = Group.objects.create(name='Administrators')
        self.facility_group = Group.objects.create(name='Facilities')
        
        # Add user to radiologist group
        self.user.groups.add(self.radiologist_group)
        
        # Create test facility
        self.facility = Facility.objects.create(
            name='Test Hospital',
            address='123 Test St',
            phone='555-1234',
            email='test@hospital.com'
        )
        
        # Create test client
        self.client = Client()
        
        # Create test DICOM file
        self.test_dicom_file = self._create_test_dicom_file()
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up test files
        if hasattr(self, 'test_dicom_file') and os.path.exists(self.test_dicom_file):
            os.remove(self.test_dicom_file)
        
        # Clean up test directories
        test_dirs = ['test_uploads', 'test_media', 'test_logs']
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
    
    def _create_test_dicom_file(self):
        """Create a test DICOM file"""
        # Create a simple DICOM dataset
        ds = pydicom.Dataset()
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9"
        ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.1"
        ds.Modality = "CT"
        ds.StudyDate = "20240101"
        ds.StudyDescription = "Test Study"
        ds.SeriesDescription = "Test Series"
        ds.SeriesNumber = 1
        ds.InstanceNumber = 1
        ds.ImagePositionPatient = [0, 0, 0]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.PixelSpacing = [1, 1]
        ds.SliceThickness = 1
        ds.WindowCenter = 0
        ds.WindowWidth = 0
        ds.BitsAllocated = 16
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        
        # Create test image data
        image_data = np.random.randint(0, 65535, (256, 256), dtype=np.uint16)
        ds.PixelData = image_data.tobytes()
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.dcm', delete=False)
        ds.save_as(temp_file.name)
        return temp_file.name


class UploadSystemTestCase(ComprehensiveSystemTestCase):
    """Test upload system functionality"""
    
    def test_single_file_upload(self):
        """Test single DICOM file upload"""
        with open(self.test_dicom_file, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                'test.dcm',
                f.read(),
                content_type='application/dicom'
            )
        
        # Test upload
        response = self.client.post(
            reverse('viewer:upload_dicom_files'),
            {'file': uploaded_file},
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that study was created
        studies = DicomStudy.objects.all()
        self.assertEqual(studies.count(), 1)
        
        study = studies.first()
        self.assertEqual(study.patient_name, "Test^Patient")
        self.assertEqual(study.modality, "CT")
    
    def test_archive_upload(self):
        """Test archive file upload"""
        # Create test archive
        import zipfile
        archive_path = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name
        
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.write(self.test_dicom_file, 'test.dcm')
        
        with open(archive_path, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                'test.zip',
                f.read(),
                content_type='application/zip'
            )
        
        # Test upload
        response = self.client.post(
            reverse('viewer:upload_dicom_folder'),
            {'file': uploaded_file},
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Cleanup
        os.remove(archive_path)
    
    def test_invalid_file_upload(self):
        """Test upload with invalid file"""
        # Create invalid file
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'This is not a DICOM file',
            content_type='text/plain'
        )
        
        response = self.client.post(
            reverse('viewer:upload_dicom_files'),
            {'file': invalid_file},
            follow=True
        )
        
        # Should handle error gracefully
        self.assertNotEqual(response.status_code, 500)
    
    def test_large_file_upload(self):
        """Test large file upload handling"""
        # Create large test file
        large_data = b'0' * (100 * 1024 * 1024)  # 100MB
        large_file = SimpleUploadedFile(
            'large.dcm',
            large_data,
            content_type='application/dicom'
        )
        
        response = self.client.post(
            reverse('viewer:upload_dicom_files'),
            {'file': large_file},
            follow=True
        )
        
        # Should handle large files
        self.assertNotEqual(response.status_code, 500)


class SecurityTestCase(ComprehensiveSystemTestCase):
    """Test security functionality"""
    
    def test_input_validation(self):
        """Test input validation"""
        # Test valid input
        valid_input = "Normal patient name"
        result = security_manager.validate_input(valid_input, 'user_input')
        self.assertTrue(result['valid'])
        
        # Test SQL injection attempt
        sql_injection = "'; DROP TABLE users; --"
        with self.assertRaises(ValueError):
            security_manager.validate_input(sql_injection, 'user_input')
        
        # Test XSS attempt
        xss_attempt = "<script>alert('xss')</script>"
        with self.assertRaises(ValueError):
            security_manager.validate_input(xss_attempt, 'user_input')
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        identifier = "test_ip"
        
        # Should allow requests within limit
        for i in range(50):
            self.assertTrue(security_manager.check_rate_limit(identifier, limit=100))
        
        # Should block after limit exceeded
        for i in range(60):
            if i >= 50:
                self.assertFalse(security_manager.check_rate_limit(identifier, limit=50))
    
    def test_ip_blocking(self):
        """Test IP blocking"""
        test_ip = "192.168.1.100"
        
        # Initially not blocked
        self.assertFalse(security_manager.is_ip_blocked(test_ip))
        
        # Block IP
        security_manager.block_ip(test_ip, "Test blocking")
        self.assertTrue(security_manager.is_ip_blocked(test_ip))
    
    def test_file_validation(self):
        """Test file upload validation"""
        # Test valid DICOM file
        valid_file = MagicMock()
        valid_file.name = "test.dcm"
        valid_file.size = 1024
        
        result = security_manager.validate_input(valid_file, 'dicom_file')
        self.assertTrue(result['valid'])
        
        # Test suspicious filename
        suspicious_file = MagicMock()
        suspicious_file.name = "test..dcm"
        suspicious_file.size = 1024
        
        with self.assertRaises(ValueError):
            security_manager.validate_input(suspicious_file, 'dicom_file')
        
        # Test oversized file
        oversized_file = MagicMock()
        oversized_file.name = "test.dcm"
        oversized_file.size = 10 * 1024 * 1024 * 1024  # 10GB
        
        with self.assertRaises(ValueError):
            security_manager.validate_input(oversized_file, 'dicom_file')


class ImageProcessingTestCase(ComprehensiveSystemTestCase):
    """Test image processing functionality"""
    
    def test_window_level_adjustment(self):
        """Test window/level adjustment"""
        processor = ImageProcessingService()
        
        # Create test image data
        test_data = np.random.randint(0, 65535, (256, 256), dtype=np.uint16)
        
        # Test window/level adjustment
        adjusted = processor.apply_window_level(test_data, 1000, 2000)
        
        self.assertEqual(adjusted.dtype, np.uint8)
        self.assertEqual(adjusted.shape, (256, 256))
    
    def test_image_enhancement(self):
        """Test image enhancement"""
        processor = ImageProcessingService()
        
        # Create test image data
        test_data = np.random.randint(0, 65535, (256, 256), dtype=np.uint16)
        
        # Test different enhancement types
        enhanced_xray = processor.enhance_image(test_data, 'xray')
        enhanced_mri = processor.enhance_image(test_data, 'mri')
        enhanced_ct = processor.enhance_image(test_data, 'ct')
        
        self.assertEqual(enhanced_xray.dtype, np.uint8)
        self.assertEqual(enhanced_mri.dtype, np.uint8)
        self.assertEqual(enhanced_ct.dtype, np.uint8)
    
    def test_error_handling(self):
        """Test error handling in image processing"""
        processor = ImageProcessingService()
        
        # Test with invalid data
        invalid_data = "not an image"
        
        with self.assertRaises(Exception):
            processor.enhance_image(invalid_data, 'xray')


class WorklistTestCase(ComprehensiveSystemTestCase):
    """Test worklist functionality"""
    
    def test_worklist_creation(self):
        """Test worklist entry creation"""
        worklist_service = WorklistService()
        
        # Create test study
        study = DicomStudy.objects.create(
            study_instance_uid="1.2.3.4.5.6.7.8.9",
            patient_name="Test^Patient",
            patient_id="12345",
            modality="CT",
            uploaded_by=self.user
        )
        
        # Create worklist entry
        entry = worklist_service.create_worklist_entry(study, self.user, self.facility)
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.patient_name, "Test^Patient")
        self.assertEqual(entry.modality, "CT")
        self.assertEqual(entry.status, "pending")
    
    def test_worklist_filtering(self):
        """Test worklist filtering"""
        worklist_service = WorklistService()
        
        # Create test entries
        study1 = DicomStudy.objects.create(
            study_instance_uid="1.2.3.4.5.6.7.8.9.1",
            patient_name="Patient^One",
            patient_id="12345",
            modality="CT",
            uploaded_by=self.user
        )
        
        study2 = DicomStudy.objects.create(
            study_instance_uid="1.2.3.4.5.6.7.8.9.2",
            patient_name="Patient^Two",
            patient_id="67890",
            modality="MR",
            uploaded_by=self.user
        )
        
        # Create worklist entries
        entry1 = worklist_service.create_worklist_entry(study1, self.user, self.facility)
        entry2 = worklist_service.create_worklist_entry(study2, self.user, self.facility)
        
        # Test filtering by modality
        ct_entries = worklist_service.get_user_worklist(self.user, {'modality': 'CT'})
        self.assertEqual(ct_entries.count(), 1)
        
        # Test filtering by search
        search_entries = worklist_service.get_user_worklist(self.user, {'search': 'One'})
        self.assertEqual(search_entries.count(), 1)


class ErrorHandlingTestCase(ComprehensiveSystemTestCase):
    """Test error handling functionality"""
    
    def test_error_tracking(self):
        """Test error tracking"""
        # Track some errors
        error_tracker.track_error('test_error', 'Test error message', {'context': 'test'})
        error_tracker.track_error('test_error', 'Another test error', {'context': 'test2'})
        
        # Get error summary
        summary = error_tracker.get_error_summary()
        
        self.assertEqual(summary['total_errors'], 2)
        self.assertEqual(summary['error_types']['test_error'], 2)
    
    def test_performance_monitoring(self):
        """Test performance monitoring"""
        # Record some metrics
        performance_monitor.record_metric('response_time', 0.5, {'endpoint': '/api/test'})
        performance_monitor.record_metric('response_time', 0.3, {'endpoint': '/api/test'})
        performance_monitor.record_metric('upload_time', 2.1, {'file_size': '1MB'})
        
        # Get metric summary
        response_time_summary = performance_monitor.get_metric_summary('response_time')
        
        self.assertEqual(response_time_summary['count'], 2)
        self.assertIsNotNone(response_time_summary['avg'])
        self.assertIsNotNone(response_time_summary['min'])
        self.assertIsNotNone(response_time_summary['max'])


class IntegrationTestCase(ComprehensiveSystemTestCase):
    """Test system integration"""
    
    def test_complete_workflow(self):
        """Test complete workflow from upload to worklist"""
        # 1. Upload DICOM file
        with open(self.test_dicom_file, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                'test.dcm',
                f.read(),
                content_type='application/dicom'
            )
        
        response = self.client.post(
            reverse('viewer:upload_dicom_files'),
            {'file': uploaded_file},
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # 2. Check study was created
        studies = DicomStudy.objects.all()
        self.assertEqual(studies.count(), 1)
        
        study = studies.first()
        
        # 3. Check series was created
        series = DicomSeries.objects.filter(study=study)
        self.assertEqual(series.count(), 1)
        
        # 4. Check images were created
        images = DicomImage.objects.filter(series=series.first())
        self.assertEqual(images.count(), 1)
        
        # 5. Check worklist entry was created
        worklist_entries = WorklistEntry.objects.filter(study=study)
        self.assertEqual(worklist_entries.count(), 1)
        
        # 6. Check notification was created
        notifications = Notification.objects.filter(related_study=study)
        self.assertEqual(notifications.count(), 1)
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        # Test studies endpoint
        response = self.client.get(reverse('viewer:get_studies'))
        self.assertEqual(response.status_code, 200)
        
        # Test worklist endpoint
        response = self.client.get(reverse('viewer:get_worklist'))
        self.assertEqual(response.status_code, 200)
        
        # Test notifications endpoint
        response = self.client.get(reverse('worklist:api_notifications'))
        self.assertEqual(response.status_code, 200)


class PerformanceTestCase(ComprehensiveSystemTestCase):
    """Test system performance"""
    
    def test_upload_performance(self):
        """Test upload performance"""
        start_time = time.time()
        
        with open(self.test_dicom_file, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                'test.dcm',
                f.read(),
                content_type='application/dicom'
            )
        
        response = self.client.post(
            reverse('viewer:upload_dicom_files'),
            {'file': uploaded_file},
            follow=True
        )
        
        end_time = time.time()
        upload_time = end_time - start_time
        
        # Upload should complete within reasonable time
        self.assertLess(upload_time, 10.0)  # 10 seconds
        self.assertEqual(response.status_code, 200)
    
    def test_database_performance(self):
        """Test database performance"""
        # Create multiple studies
        start_time = time.time()
        
        for i in range(10):
            study = DicomStudy.objects.create(
                study_instance_uid=f"1.2.3.4.5.6.7.8.9.{i}",
                patient_name=f"Patient^{i}",
                patient_id=f"1234{i}",
                modality="CT",
                uploaded_by=self.user
            )
            
            # Create worklist entry
            WorklistEntry.objects.create(
                study=study,
                patient_name=study.patient_name,
                patient_id=study.patient_id,
                modality=study.modality,
                status='pending',
                created_by=self.user
            )
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Database operations should be fast
        self.assertLess(creation_time, 5.0)  # 5 seconds
        
        # Query performance
        start_time = time.time()
        studies = DicomStudy.objects.all()
        worklist_entries = WorklistEntry.objects.all()
        end_time = time.time()
        query_time = end_time - start_time
        
        self.assertLess(query_time, 1.0)  # 1 second
        self.assertEqual(studies.count(), 10)
        self.assertEqual(worklist_entries.count(), 10)


class SecurityIntegrationTestCase(ComprehensiveSystemTestCase):
    """Test security integration"""
    
    def test_authentication_required(self):
        """Test that authentication is required for protected endpoints"""
        # Test without authentication
        response = self.client.get(reverse('viewer:get_studies'))
        self.assertEqual(response.status_code, 200)  # API endpoints are public
        
        # Test admin endpoints
        response = self.client.get(reverse('viewer:facility_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_csrf_protection(self):
        """Test CSRF protection"""
        # Test POST without CSRF token
        response = self.client.post(reverse('viewer:upload_dicom_files'))
        self.assertEqual(response.status_code, 403)  # CSRF protection
    
    def test_file_upload_security(self):
        """Test file upload security"""
        # Test upload with malicious filename
        malicious_file = SimpleUploadedFile(
            '../../../etc/passwd',
            b'fake content',
            content_type='application/dicom'
        )
        
        response = self.client.post(
            reverse('viewer:upload_dicom_files'),
            {'file': malicious_file},
            follow=True
        )
        
        # Should handle malicious filename gracefully
        self.assertNotEqual(response.status_code, 500)


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    import unittest
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        UploadSystemTestCase,
        SecurityTestCase,
        ImageProcessingTestCase,
        WorklistTestCase,
        ErrorHandlingTestCase,
        IntegrationTestCase,
        PerformanceTestCase,
        SecurityIntegrationTestCase,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_comprehensive_tests()
    exit(0 if success else 1)