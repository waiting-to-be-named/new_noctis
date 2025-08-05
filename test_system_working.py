#!/usr/bin/env python3
"""
Comprehensive Test Script for Noctis DICOM Viewer System
Tests all major functionalities to ensure the system is working properly.
"""

import os
import sys
import json
import requests
import time
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')

import django
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage

def test_database_connection():
    """Test that Django can connect to the database"""
    print("🔹 Testing database connection...")
    try:
        study_count = DicomStudy.objects.count()
        print(f"✅ Database connected. Found {study_count} studies.")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints are responding"""
    print("🔹 Testing API endpoints...")
    base_url = "http://localhost:8000"
    
    # Test studies endpoint
    try:
        response = requests.get(f"{base_url}/viewer/api/studies/", timeout=10)
        if response.status_code == 200:
            studies = response.json()
            print(f"✅ Studies API working. Found {len(studies)} studies.")
        else:
            print(f"❌ Studies API failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Studies API error: {e}")
        return False
    
    # Test image data endpoint if we have studies
    if studies:
        try:
            # Find the first study with images
            study_with_images = None
            image_id = None
            
            for study in studies:
                if study.get('total_images', 0) > 0:
                    study_with_images = study
                    # Find first image ID
                    for series in study.get('series', []):
                        for image in series.get('images', []):
                            image_id = image['id']
                            break
                        if image_id:
                            break
                    break
            
            if image_id:
                response = requests.get(f"{base_url}/viewer/api/get-image-data/{image_id}/", timeout=15)
                if response.status_code == 200 and len(response.content) > 1000:
                    print(f"✅ Image data API working. Retrieved image {image_id} ({len(response.content)} bytes).")
                else:
                    print(f"❌ Image data API failed for image {image_id}")
                    return False
            else:
                print("⚠️  No images found to test image data API")
        except Exception as e:
            print(f"❌ Image data API error: {e}")
            return False
    
    return True

def test_viewer_pages():
    """Test that viewer pages load correctly"""
    print("🔹 Testing viewer pages...")
    base_url = "http://localhost:8000"
    
    # Test main page
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200 and "Noctis" in response.text:
            print("✅ Main page loading correctly.")
        else:
            print(f"❌ Main page failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page error: {e}")
        return False
    
    # Test viewer page
    try:
        response = requests.get(f"{base_url}/viewer/", timeout=10)
        if response.status_code == 200 and "DICOM Viewer" in response.text:
            print("✅ Viewer page loading correctly.")
        else:
            print(f"❌ Viewer page failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Viewer page error: {e}")
        return False
    
    return True

def test_dicom_files():
    """Test that DICOM files are accessible"""
    print("🔹 Testing DICOM files...")
    
    try:
        images_with_files = DicomImage.objects.exclude(file_path='').exclude(file_path__isnull=True)
        print(f"✅ Found {images_with_files.count()} images with DICOM files.")
        
        # Test if files actually exist
        existing_files = 0
        for image in images_with_files[:5]:  # Test first 5
            if image.file_path and Path(image.file_path.path).exists():
                existing_files += 1
        
        print(f"✅ {existing_files} out of 5 tested DICOM files exist on disk.")
        
        if existing_files > 0:
            return True
        else:
            print("⚠️  No DICOM files found on disk")
            return False
            
    except Exception as e:
        print(f"❌ DICOM files test error: {e}")
        return False

def test_image_processing():
    """Test that image processing is working"""
    print("🔹 Testing image processing...")
    
    try:
        # Get first image with file
        image = DicomImage.objects.exclude(file_path='').exclude(file_path__isnull=True).first()
        if not image:
            print("⚠️  No images with files found for processing test")
            return False
        
        # Try to load DICOM data
        dicom_data = image.load_dicom_data()
        if dicom_data is not None:
            print("✅ DICOM file loading working.")
            
            # Check if pixel data exists
            if hasattr(dicom_data, 'pixel_array'):
                pixel_array = dicom_data.pixel_array
                print(f"✅ Pixel data accessible. Shape: {pixel_array.shape}")
                return True
            else:
                print("⚠️  No pixel data in DICOM file")
                return False
        else:
            print("❌ Could not load DICOM data")
            return False
            
    except Exception as e:
        print(f"❌ Image processing test error: {e}")
        return False

def print_system_summary():
    """Print a summary of the system"""
    print("\n" + "="*60)
    print("📊 SYSTEM SUMMARY")
    print("="*60)
    
    # Database stats
    try:
        studies = DicomStudy.objects.count()
        series = DicomSeries.objects.count()
        images = DicomImage.objects.count()
        images_with_files = DicomImage.objects.exclude(file_path='').exclude(file_path__isnull=True).count()
        
        print(f"📈 Database Statistics:")
        print(f"   • Studies: {studies}")
        print(f"   • Series: {series}")
        print(f"   • Images: {images}")
        print(f"   • Images with files: {images_with_files}")
    except Exception as e:
        print(f"❌ Could not get database stats: {e}")
    
    # Server info
    print(f"\n🌐 Server Information:")
    print(f"   • Main URL: http://localhost:8000")
    print(f"   • Viewer URL: http://localhost:8000/viewer/")
    print(f"   • Worklist URL: http://localhost:8000/worklist/")
    print(f"   • Studies API: http://localhost:8000/viewer/api/studies/")
    
    # Sample study URLs
    try:
        first_study = DicomStudy.objects.first()
        if first_study:
            print(f"   • Sample Study: http://localhost:8000/viewer/?study_id={first_study.id}")
    except:
        pass

def main():
    """Run comprehensive system tests"""
    print("🚀 NOCTIS DICOM VIEWER SYSTEM TEST")
    print("="*50)
    print("Testing all system components...\n")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("API Endpoints", test_api_endpoints),
        ("Viewer Pages", test_viewer_pages),
        ("DICOM Files", test_dicom_files),
        ("Image Processing", test_image_processing),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} test ERROR: {e}")
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS")
    print("="*50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! System is fully working!")
        print("🔥 The DICOM viewer system is ready for use!")
    else:
        print(f"\n⚠️  {failed} tests failed. Please check the issues above.")
    
    print_system_summary()
    
    if failed == 0:
        print("\n🚀 You can now access the system at:")
        print("   • Main interface: http://localhost:8000")
        print("   • DICOM Viewer: http://localhost:8000/viewer/")
        print("   • Upload and view DICOM files through the web interface!")

if __name__ == "__main__":
    main()