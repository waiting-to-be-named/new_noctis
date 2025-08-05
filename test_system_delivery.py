#!/usr/bin/env python3
"""
Test script to verify the DICOM system is ready for customer delivery
"""

import os
import sys
import django
import requests
from datetime import datetime

# Setup Django
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage, DicomStudy, WorklistEntry
from django.contrib.auth.models import User

def test_database_connectivity():
    """Test database connectivity and data"""
    print("🔍 Testing Database Connectivity...")
    
    try:
        # Test basic queries
        image_count = DicomImage.objects.count()
        study_count = DicomStudy.objects.count()
        worklist_count = WorklistEntry.objects.count()
        user_count = User.objects.count()
        
        print(f"  ✅ Images: {image_count}")
        print(f"  ✅ Studies: {study_count}")
        print(f"  ✅ Worklist entries: {worklist_count}")
        print(f"  ✅ Users: {user_count}")
        
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def test_dicom_image_loading():
    """Test DICOM image loading functionality"""
    print("\n🖼️ Testing DICOM Image Loading...")
    
    try:
        first_image = DicomImage.objects.first()
        if not first_image:
            print("  ❌ No DICOM images found")
            return False
        
        print(f"  📸 Testing image: {first_image}")
        print(f"  📁 File path: {first_image.file_path}")
        
        # Test image data loading
        image_data = first_image.get_enhanced_processed_image_base64()
        
        if image_data and len(image_data) > 1000:
            print(f"  ✅ Image data loaded successfully ({len(image_data)} chars)")
            return True
        else:
            print(f"  ❌ Image data failed to load (got {len(image_data) if image_data else 0} chars)")
            return False
    except Exception as e:
        print(f"  ❌ Image loading error: {e}")
        return False

def test_worklist_data():
    """Test worklist data"""
    print("\n📋 Testing Worklist Data...")
    
    try:
        entries = WorklistEntry.objects.all()[:5]
        
        if not entries:
            print("  ❌ No worklist entries found")
            return False
        
        for entry in entries:
            print(f"  📝 {entry.patient_name} ({entry.patient_id}) - {entry.modality}")
        
        print(f"  ✅ Found {entries.count()} worklist entries")
        return True
    except Exception as e:
        print(f"  ❌ Worklist error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing API Endpoints...")
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/viewer/",
        "/worklist/",
        "/viewer/api/studies/",
    ]
    
    results = []
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"  ✅ {endpoint} - Status: {response.status_code}")
                results.append(True)
            else:
                print(f"  ⚠️ {endpoint} - Status: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"  ❌ {endpoint} - Error: {e}")
            results.append(False)
    
    return all(results)

def test_image_api():
    """Test image API specifically"""
    print("\n🖼️ Testing Image API...")
    
    try:
        first_image = DicomImage.objects.first()
        if not first_image:
            print("  ❌ No images to test")
            return False
        
        url = f"http://localhost:8000/viewer/api/get-image-data/{first_image.id}/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'image_data' in data and data['image_data']:
                print(f"  ✅ Image API working - returned {len(data['image_data'])} chars")
                return True
            else:
                print(f"  ❌ Image API returned empty data")
                return False
        else:
            print(f"  ❌ Image API failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Image API error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide delivery readiness assessment"""
    print("🚀 DICOM System Delivery Readiness Test")
    print("=" * 50)
    
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("DICOM Image Loading", test_dicom_image_loading),
        ("Worklist Data", test_worklist_data),
        ("API Endpoints", test_api_endpoints),
        ("Image API", test_image_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} - Critical Error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 DELIVERY READINESS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} {test_name}")
        if passed_test:
            passed += 1
    
    print(f"\nScore: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 SYSTEM READY FOR DELIVERY! 🎉")
        print("All critical components are working correctly.")
    elif passed >= total * 0.8:
        print("\n⚠️ SYSTEM MOSTLY READY")
        print("Most components working, minor issues to address.")
    else:
        print("\n❌ SYSTEM NOT READY")
        print("Critical issues need to be resolved before delivery.")
    
    return passed, total

if __name__ == "__main__":
    passed, total = run_comprehensive_test()
    sys.exit(0 if passed == total else 1)