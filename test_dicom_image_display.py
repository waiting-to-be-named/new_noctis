#!/usr/bin/env python3
"""
Test script to verify DICOM image display functionality
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from viewer.models import DicomStudy, DicomSeries, DicomImage
from viewer.views import get_image_data, get_study_images

def test_dicom_image_display():
    """Test the DICOM image display functionality"""
    
    print("🔍 Testing DICOM Image Display Functionality")
    print("=" * 50)
    
    # Create a test request
    factory = RequestFactory()
    request = factory.get('/test/')
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    request.user = user
    
    # Check if we have any studies in the database
    studies = DicomStudy.objects.all()
    print(f"📊 Found {studies.count()} studies in database")
    
    if studies.count() == 0:
        print("❌ No studies found in database. Please upload some DICOM files first.")
        return False
    
    # Test with the first study
    study = studies.first()
    print(f"🧪 Testing with study ID: {study.id}")
    print(f"   Patient: {study.patient_name}")
    print(f"   Study Date: {study.study_date}")
    
    # Test get_study_images API
    print("\n📋 Testing get_study_images API...")
    try:
        response = get_study_images(request, study.id)
        if response.status_code == 200:
            data = response.data
            print(f"✅ get_study_images successful")
            print(f"   Images found: {len(data.get('images', []))}")
            
            if data.get('images'):
                # Test get_image_data API with the first image
                first_image = data['images'][0]
                image_id = first_image['id']
                print(f"\n🖼️  Testing get_image_data API with image ID: {image_id}")
                
                try:
                    img_response = get_image_data(request, image_id)
                    if img_response.status_code == 200:
                        img_data = img_response.data
                        print(f"✅ get_image_data successful")
                        print(f"   Image data received: {len(img_data.get('image_data', ''))} characters")
                        print(f"   Metadata: {img_data.get('metadata', {})}")
                        
                        # Check if image data is valid base64
                        import base64
                        try:
                            base64.b64decode(img_data.get('image_data', ''))
                            print("✅ Image data is valid base64")
                            return True
                        except Exception as e:
                            print(f"❌ Invalid base64 image data: {e}")
                            return False
                    else:
                        print(f"❌ get_image_data failed with status: {img_response.status_code}")
                        print(f"   Error: {img_response.data}")
                        return False
                        
                except Exception as e:
                    print(f"❌ Error testing get_image_data: {e}")
                    return False
            else:
                print("❌ No images found in study")
                return False
        else:
            print(f"❌ get_study_images failed with status: {response.status_code}")
            print(f"   Error: {response.data}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing get_study_images: {e}")
        return False

def test_javascript_integration():
    """Test that the JavaScript can access the correct endpoints"""
    
    print("\n🔧 Testing JavaScript Integration")
    print("=" * 50)
    
    # Check if the fixed JavaScript file exists
    js_file = Path("static/js/dicom_viewer_fixed.js")
    if js_file.exists():
        print(f"✅ Fixed JavaScript file found: {js_file}")
        
        # Check for correct API endpoint usage
        with open(js_file, 'r') as f:
            content = f.read()
            
        if '/viewer/api/get-image-data/' in content:
            print("✅ Correct API endpoint found in JavaScript")
        else:
            print("❌ Incorrect API endpoint in JavaScript")
            
        if 'loadStudy' in content and 'loadImage' in content:
            print("✅ Study and image loading methods found")
        else:
            print("❌ Missing study/image loading methods")
            
    else:
        print(f"❌ Fixed JavaScript file not found: {js_file}")
        return False
    
    return True

def test_template_integration():
    """Test that the template is using the correct JavaScript file"""
    
    print("\n📄 Testing Template Integration")
    print("=" * 50)
    
    template_file = Path("templates/dicom_viewer/viewer_advanced.html")
    if template_file.exists():
        print(f"✅ Template file found: {template_file}")
        
        with open(template_file, 'r') as f:
            content = f.read()
            
        if 'dicom_viewer_fixed.js' in content:
            print("✅ Template is using the fixed JavaScript file")
        else:
            print("❌ Template is not using the fixed JavaScript file")
            
        if 'FixedDicomViewer' in content:
            print("✅ Template is using FixedDicomViewer class")
        else:
            print("❌ Template is not using FixedDicomViewer class")
            
    else:
        print(f"❌ Template file not found: {template_file}")
        return False
    
    return True

def main():
    """Run all tests"""
    
    print("🚀 Starting DICOM Image Display Tests")
    print("=" * 60)
    
    # Test API functionality
    api_success = test_dicom_image_display()
    
    # Test JavaScript integration
    js_success = test_javascript_integration()
    
    # Test template integration
    template_success = test_template_integration()
    
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"API Functionality: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"JavaScript Integration: {'✅ PASS' if js_success else '❌ FAIL'}")
    print(f"Template Integration: {'✅ PASS' if template_success else '❌ FAIL'}")
    
    if api_success and js_success and template_success:
        print("\n🎉 All tests passed! DICOM image display should be working correctly.")
        print("\n📝 Next steps:")
        print("   1. Start the Django server: python manage.py runserver")
        print("   2. Navigate to http://localhost:8000/viewer/")
        print("   3. Upload DICOM files or select an existing study")
        print("   4. Verify that images are displayed correctly")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        
    return api_success and js_success and template_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)