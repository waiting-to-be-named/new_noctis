#!/usr/bin/env python
"""
DICOM Viewer System Test Script
Tests all critical components for deployment readiness
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from viewer.models import DicomStudy, DicomImage
from colorama import init, Fore, Style

init()

def print_success(msg):
    print(f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}")

def print_error(msg):
    print(f"{Fore.RED}✗ {msg}{Style.RESET_ALL}")

def print_warning(msg):
    print(f"{Fore.YELLOW}⚠ {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f"{Fore.CYAN}ℹ {msg}{Style.RESET_ALL}")

def print_header(msg):
    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"{msg}")
    print(f"{'='*60}{Style.RESET_ALL}\n")

class DicomViewerTester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        
    def run_all_tests(self):
        print_header("DICOM VIEWER SYSTEM TEST - DEPLOYMENT READINESS CHECK")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run test suites
        self.test_database_connectivity()
        self.test_authentication()
        self.test_viewer_endpoints()
        self.test_api_endpoints()
        self.test_static_files()
        self.test_dicom_data()
        self.test_viewer_functionality()
        
        # Print summary
        self.print_summary()
        
    def test_database_connectivity(self):
        print_header("Testing Database Connectivity")
        try:
            study_count = DicomStudy.objects.count()
            image_count = DicomImage.objects.count()
            print_success(f"Database connected successfully")
            print_info(f"Found {study_count} studies and {image_count} images")
            self.test_results.append(("Database Connectivity", True))
        except Exception as e:
            print_error(f"Database connection failed: {e}")
            self.test_results.append(("Database Connectivity", False))
    
    def test_authentication(self):
        print_header("Testing Authentication System")
        try:
            # Create test user if doesn't exist
            test_user, created = User.objects.get_or_create(
                username='test_viewer',
                defaults={'email': 'test@example.com'}
            )
            if created:
                test_user.set_password('test123')
                test_user.save()
            
            # Test login
            login_success = self.client.login(username='test_viewer', password='test123')
            if login_success:
                print_success("Authentication system working")
            else:
                print_warning("Login failed - check credentials")
            self.test_results.append(("Authentication", login_success))
        except Exception as e:
            print_error(f"Authentication test failed: {e}")
            self.test_results.append(("Authentication", False))
    
    def test_viewer_endpoints(self):
        print_header("Testing Viewer Endpoints")
        
        endpoints = [
            ('/', 'Main Viewer'),
            ('/viewer/', 'Viewer App'),
            ('/worklist/', 'Worklist'),
        ]
        
        for url, name in endpoints:
            try:
                response = self.client.get(url)
                if response.status_code in [200, 302]:
                    print_success(f"{name} endpoint ({url}): {response.status_code}")
                    self.test_results.append((f"{name} Endpoint", True))
                else:
                    print_error(f"{name} endpoint ({url}): {response.status_code}")
                    self.test_results.append((f"{name} Endpoint", False))
            except Exception as e:
                print_error(f"{name} endpoint error: {e}")
                self.test_results.append((f"{name} Endpoint", False))
    
    def test_api_endpoints(self):
        print_header("Testing API Endpoints")
        
        api_endpoints = [
            ('/viewer/api/test-connectivity/', 'API Connectivity'),
            ('/viewer/api/studies/', 'Studies API'),
            ('/viewer/api/get-study-images/1/', 'Study Images API'),
        ]
        
        for url, name in api_endpoints:
            try:
                response = self.client.get(url)
                if response.status_code in [200, 404]:  # 404 is ok for specific IDs
                    print_success(f"{name} ({url}): {response.status_code}")
                    self.test_results.append((name, True))
                else:
                    print_error(f"{name} ({url}): {response.status_code}")
                    self.test_results.append((name, False))
            except Exception as e:
                print_error(f"{name} error: {e}")
                self.test_results.append((name, False))
    
    def test_static_files(self):
        print_header("Testing Static Files")
        
        static_files = [
            'js/dicom_viewer_fixed.js',
            'css/dicom_viewer_advanced.css',
        ]
        
        for file_path in static_files:
            full_path = os.path.join('/workspace/static', file_path)
            if os.path.exists(full_path):
                print_success(f"Static file found: {file_path}")
                self.test_results.append((f"Static: {file_path}", True))
            else:
                print_error(f"Static file missing: {file_path}")
                self.test_results.append((f"Static: {file_path}", False))
    
    def test_dicom_data(self):
        print_header("Testing DICOM Data Access")
        
        try:
            # Get first study with images
            study = DicomStudy.objects.filter(dicomimage__isnull=False).first()
            if study:
                print_success(f"Found study: {study.patient_name}")
                images = study.dicomimage_set.all()
                print_info(f"Study has {images.count()} images")
                
                # Test image data access
                if images.exists():
                    first_image = images.first()
                    if first_image.file_path and os.path.exists(first_image.file_path):
                        print_success("DICOM file accessible")
                        self.test_results.append(("DICOM File Access", True))
                    else:
                        print_warning("DICOM file path invalid or missing")
                        self.test_results.append(("DICOM File Access", False))
            else:
                print_warning("No DICOM studies found in database")
                self.test_results.append(("DICOM Data", False))
        except Exception as e:
            print_error(f"DICOM data test failed: {e}")
            self.test_results.append(("DICOM Data", False))
    
    def test_viewer_functionality(self):
        print_header("Testing Viewer Core Functionality")
        
        try:
            # Test with a specific study if available
            study = DicomStudy.objects.filter(dicomimage__isnull=False).first()
            if study:
                # Test viewer page with study
                url = f'/viewer/study/{study.id}/'
                response = self.client.get(url)
                
                if response.status_code == 200:
                    print_success(f"Viewer loads with study ID {study.id}")
                    
                    # Check for critical elements in response
                    content = str(response.content)
                    checks = [
                        ('dicom-canvas-advanced' in content, "Canvas element present"),
                        ('FixedDicomViewer' in content, "Viewer JavaScript loaded"),
                        ('tool-btn-advanced' in content, "Tool buttons present"),
                    ]
                    
                    for check, desc in checks:
                        if check:
                            print_success(desc)
                        else:
                            print_warning(desc + " - NOT FOUND")
                    
                    self.test_results.append(("Viewer Functionality", True))
                else:
                    print_error(f"Viewer failed to load: {response.status_code}")
                    self.test_results.append(("Viewer Functionality", False))
            else:
                print_warning("No study available for viewer test")
                self.test_results.append(("Viewer Functionality", False))
                
        except Exception as e:
            print_error(f"Viewer functionality test failed: {e}")
            self.test_results.append(("Viewer Functionality", False))
    
    def print_summary(self):
        print_header("TEST SUMMARY")
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results:
            if result:
                print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {test_name}")
            else:
                print(f"  {Fore.RED}✗{Style.RESET_ALL} {test_name}")
        
        print_header("DEPLOYMENT READINESS")
        if passed == total:
            print_success("✅ SYSTEM IS READY FOR DEPLOYMENT!")
        elif passed >= total * 0.8:
            print_warning("⚠️  System is mostly ready but has some issues to fix")
        else:
            print_error("❌ System has critical issues - NOT ready for deployment")
        
        # Provide recommendations
        print("\nRecommendations:")
        if any(not result for name, result in self.test_results if 'Database' in name):
            print("- Check database connection and migrations")
        if any(not result for name, result in self.test_results if 'Static' in name):
            print("- Run 'python manage.py collectstatic'")
        if any(not result for name, result in self.test_results if 'DICOM' in name):
            print("- Upload DICOM files to test with real data")

if __name__ == "__main__":
    tester = DicomViewerTester()
    tester.run_all_tests()