#!/usr/bin/env python3
"""
Direct API test to verify study images are being returned correctly
"""

import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage

def test_api_directly():
    """Test the API directly"""
    print("🧪 Testing API directly...")
    
    # Test study 6 which has actual DICOM files
    study_id = 6
    url = f"http://localhost:8000/viewer/api/get-study-images/{study_id}/"
    
    try:
        print(f"📡 Testing URL: {url}")
        response = requests.get(url, timeout=10)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API call successful!")
            print(f"📊 Study data: {data.get('study', {}).get('patient_name', 'Unknown')}")
            print(f"📊 Number of images: {len(data.get('images', []))}")
            
            # Test first image
            if data.get('images'):
                first_image = data['images'][0]
                print(f"🖼️  First image ID: {first_image.get('id')}")
                
                # Test getting image data
                image_id = first_image['id']
                image_url = f"http://localhost:8000/viewer/api/get-image-data/{image_id}/"
                print(f"📡 Testing image data URL: {image_url}")
                
                image_response = requests.get(image_url, timeout=30)
                print(f"📊 Image response status: {image_response.status_code}")
                
                if image_response.status_code == 200:
                    image_data = image_response.json()
                    if image_data.get('image_data'):
                        print(f"✅ Image data received successfully!")
                        print(f"📊 Image data length: {len(image_data['image_data'])} characters")
                        print(f"📊 Image data starts with: {image_data['image_data'][:50]}...")
                    else:
                        print(f"❌ No image data in response")
                else:
                    print(f"❌ Image data request failed: {image_response.text}")
        else:
            print(f"❌ API call failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

def test_database_directly():
    """Test database directly"""
    print("\n🗄️  Testing database directly...")
    
    try:
        study = DicomStudy.objects.get(id=6)
        print(f"📖 Found study: {study.patient_name}")
        
        images = DicomImage.objects.filter(series__study=study)
        print(f"📊 Found {images.count()} images in study")
        
        for image in images:
            print(f"🖼️  Image {image.id}: {image.file_path}")
            
            # Test image processing
            try:
                result = image.get_enhanced_processed_image_base64()
                if result and result.startswith('data:image'):
                    print(f"  ✅ Image {image.id} processed successfully")
                else:
                    print(f"  ❌ Image {image.id} processing failed")
            except Exception as e:
                print(f"  ❌ Image {image.id} error: {e}")
                
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("🚨 DIRECT API TESTING")
    print("=" * 50)
    
    test_database_directly()
    test_api_directly()
    
    print("\n" + "=" * 50)
    print("✅ Testing completed!")