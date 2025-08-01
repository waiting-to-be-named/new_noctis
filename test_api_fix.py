#!/usr/bin/env python3
"""
Test API Fix - Verify DICOM viewer API endpoints work correctly
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')

# Configure Django if not already configured
if not settings.configured:
    import django
    django.setup()
else:
    django.setup()

from django.test import Client
from django.contrib.auth.models import User
from viewer.models import DicomStudy, DicomSeries, DicomImage
import json

def test_api_endpoints():
    """Test the API endpoints that the viewer uses"""
    print("🧪 Testing DICOM Viewer API Endpoints")
    print("=" * 50)
    
    # Create a test client
    client = Client()
    
    # Test 1: Studies API
    print("\n1️⃣ Testing Studies API...")
    try:
        response = client.get('/viewer/api/studies/')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Studies Found: {len(data)}")
            if data:
                study = data[0]
                print(f"   First Study: ID={study.get('id')}, Patient={study.get('patient_name')}")
                first_study_id = study['id']
            else:
                print("   ❌ No studies found!")
                return False
        else:
            print(f"   ❌ API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False
    
    # Test 2: Study Details API
    print(f"\n2️⃣ Testing Study Details API for study {first_study_id}...")
    try:
        response = client.get(f'/viewer/api/studies/{first_study_id}/')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Series Found: {len(data.get('series', []))}")
            if data.get('series'):
                series = data['series'][0]
                print(f"   First Series: ID={series.get('id')}, Images={len(series.get('images', []))}")
                if series.get('images'):
                    first_image_id = series['images'][0]['id']
                else:
                    print("   ❌ No images in first series!")
                    return False
            else:
                print("   ❌ No series found!")
                return False
        else:
            print(f"   ❌ API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False
    
    # Test 3: Image Data API
    print(f"\n3️⃣ Testing Image Data API for image {first_image_id}...")
    try:
        response = client.get(f'/viewer/api/images/{first_image_id}/data/')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            image_data = data.get('image_data', '')
            metadata = data.get('metadata', {})
            
            print(f"   Image Data Length: {len(image_data)}")
            print(f"   Metadata Keys: {list(metadata.keys())}")
            
            if image_data:
                if image_data.startswith('data:image'):
                    print("   ✅ Valid image data URL found")
                else:
                    print("   ⚠️ Image data format may be incorrect")
                return True
            else:
                print("   ❌ No image data returned!")
                return False
        else:
            print(f"   ❌ API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def check_database_direct():
    """Direct database check"""
    print("\n🔍 Direct Database Check...")
    
    try:
        studies = DicomStudy.objects.all()
        series = DicomSeries.objects.all()
        images = DicomImage.objects.all()
        
        print(f"   Studies: {studies.count()}")
        print(f"   Series: {series.count()}")
        print(f"   Images: {images.count()}")
        
        if images.exists():
            first_image = images.first()
            print(f"   First Image: ID={first_image.id}")
            print(f"   Has cached data: {bool(first_image.processed_image_cache)}")
            
            # Test image processing
            try:
                image_data = first_image.get_enhanced_processed_image_base64()
                if image_data:
                    print(f"   ✅ Image processing works: {len(image_data)} chars")
                    return True
                else:
                    print("   ❌ Image processing returned None")
                    return False
            except Exception as e:
                print(f"   ❌ Image processing failed: {e}")
                return False
        else:
            print("   ❌ No images in database")
            return False
            
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False

def main():
    print("🏥 DICOM Viewer API Test")
    print("=" * 30)
    
    # Test database directly first
    db_ok = check_database_direct()
    
    if db_ok:
        # Test API endpoints
        api_ok = test_api_endpoints()
        
        if api_ok:
            print("\n✅ All tests passed!")
            print("🚀 The DICOM viewer should now work correctly")
            print("\n📋 Next steps:")
            print("   1. Start Django server: python3 manage.py runserver")
            print("   2. Open browser to: http://localhost:8000/viewer/")
            print("   3. Images should now display correctly")
            return 0
        else:
            print("\n❌ API tests failed")
            return 1
    else:
        print("\n❌ Database tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())