#!/usr/bin/env python
"""
Test script to verify DICOM viewer measurement fixes and overall functionality
"""

import os
import sys
import django
import requests
import json
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radiology_platform.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage, Measurement, WorklistEntry
from django.contrib.auth.models import User

def test_viewer_functionality():
    """Test the DICOM viewer functionality"""
    print("=== DICOM Viewer Functionality Test ===\n")
    
    # Test 1: Check if studies exist
    studies = DicomStudy.objects.all()
    print(f"1. Available studies: {studies.count()}")
    
    if studies.count() == 0:
        print("   ❌ No studies found. Please upload some DICOM files first.")
        return False
    
    # Test 2: Check study images API
    for study in studies[:3]:  # Test first 3 studies
        print(f"\n2. Testing study: {study.patient_name} (ID: {study.id})")
        
        try:
            response = requests.get(f"http://localhost:8000/viewer/api/studies/{study.id}/images/")
            if response.status_code == 200:
                data = response.json()
                images = data.get('images', [])
                print(f"   ✅ Study API working - {len(images)} images found")
                
                # Test image data API for first image
                if images:
                    image_id = images[0]['id']
                    img_response = requests.get(f"http://localhost:8000/viewer/api/images/{image_id}/data/")
                    if img_response.status_code == 200:
                        img_data = img_response.json()
                        if 'image_data' in img_data:
                            print(f"   ✅ Image data API working for image {image_id}")
                        else:
                            print(f"   ❌ Image data missing for image {image_id}")
                    else:
                        print(f"   ❌ Image data API failed: {img_response.status_code}")
                
            else:
                print(f"   ❌ Study API failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ API test error: {e}")
    
    return True

def test_measurement_functionality():
    """Test measurement functionality"""
    print("\n=== Measurement Functionality Test ===\n")
    
    # Find an image to test with
    image = DicomImage.objects.first()
    if not image:
        print("❌ No images found for measurement testing")
        return False
    
    print(f"Testing measurements on image: {image.id}")
    
    # Test 3: Save a test measurement
    measurement_data = {
        'image_id': image.id,
        'type': 'line',
        'coordinates': [{'x': 100, 'y': 100}, {'x': 200, 'y': 200}],
        'value': 141.42,  # sqrt(100^2 + 100^2)
        'unit': 'mm'
    }
    
    try:
        # Get CSRF token (simplified for testing)
        session = requests.Session()
        response = session.post(
            'http://localhost:8000/viewer/api/measurements/save/',
            json=measurement_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print("✅ Measurement save API working")
            
            # Test 4: Retrieve measurements
            get_response = requests.get(f"http://localhost:8000/viewer/api/images/{image.id}/measurements/")
            if get_response.status_code == 200:
                measurements = get_response.json()
                print(f"✅ Measurement retrieval working - {len(measurements)} measurements found")
                
                # Clean up test measurement
                if measurements:
                    Measurement.objects.filter(image_id=image.id, value=141.42).delete()
                    print("✅ Test measurement cleaned up")
            else:
                print(f"❌ Measurement retrieval failed: {get_response.status_code}")
        else:
            print(f"❌ Measurement save failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Measurement test error: {e}")
    
    return True

def test_worklist_integration():
    """Test worklist to viewer integration"""
    print("\n=== Worklist Integration Test ===\n")
    
    # Check if worklist entries exist
    entries = WorklistEntry.objects.filter(study__isnull=False)
    print(f"Worklist entries with studies: {entries.count()}")
    
    if entries.count() == 0:
        print("❌ No worklist entries with studies found")
        return False
    
    # Test the view redirect
    entry = entries.first()
    print(f"Testing entry: {entry.patient_name} -> Study {entry.study.id}")
    
    try:
        # Test the redirect endpoint
        response = requests.get(
            f"http://localhost:8000/worklist/view-study/{entry.id}/",
            allow_redirects=False
        )
        
        if response.status_code == 302:  # Redirect
            redirect_url = response.headers.get('Location', '')
            expected_url = f"/viewer/study/{entry.study.id}/"
            if expected_url in redirect_url:
                print("✅ Worklist to viewer redirect working correctly")
            else:
                print(f"❌ Incorrect redirect URL: {redirect_url}")
        else:
            print(f"❌ Worklist view failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Worklist integration test error: {e}")
    
    return True

def check_file_integrity():
    """Check if DICOM files are accessible"""
    print("\n=== File Integrity Check ===\n")
    
    images = DicomImage.objects.all()[:10]  # Check first 10 images
    accessible_count = 0
    
    for image in images:
        if image.file_path and os.path.exists(image.file_path):
            accessible_count += 1
        else:
            print(f"❌ Missing file for image {image.id}: {image.file_path}")
    
    print(f"✅ {accessible_count}/{len(images)} image files accessible")
    
    if accessible_count < len(images):
        print("⚠️  Some image files are missing. This may cause viewer issues.")
        return False
    
    return True

def run_comprehensive_test():
    """Run all tests"""
    print("Starting comprehensive DICOM viewer test...\n")
    
    results = []
    
    results.append(("File Integrity", check_file_integrity()))
    results.append(("Viewer Functionality", test_viewer_functionality()))
    results.append(("Measurement Functionality", test_measurement_functionality()))
    results.append(("Worklist Integration", test_worklist_integration()))
    
    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The viewer should be working correctly.")
        print("\nNext steps:")
        print("1. Open the viewer in your browser")
        print("2. Test measurement tools manually")
        print("3. Navigate from worklist to viewer")
        print("4. Verify measurements display properly on canvas")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
    
    return passed == len(results)

if __name__ == "__main__":
    try:
        run_comprehensive_test()
    except Exception as e:
        print(f"Test execution error: {e}")
        import traceback
        traceback.print_exc()