#!/usr/bin/env python3
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage

def test_api_endpoints():
    """Test the API endpoints"""
    print("Testing API endpoints...")
    
    # Get the first study
    study = DicomStudy.objects.first()
    if not study:
        print("No studies found in database")
        return
    
    print(f"Testing with study ID: {study.id}")
    
    # Test study images endpoint
    try:
        response = requests.get(f'http://localhost:8000/viewer/api/studies/{study.id}/images/')
        print(f"Study images endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Study images endpoint working")
            print(f"  Study: {data.get('study', {}).get('patient_name', 'N/A')}")
            print(f"  Images: {len(data.get('images', []))}")
        else:
            print(f"✗ Study images endpoint failed: {response.text}")
    except Exception as e:
        print(f"✗ Error testing study images endpoint: {e}")
    
    # Test image data endpoint
    image = DicomImage.objects.first()
    if image:
        print(f"\nTesting with image ID: {image.id}")
        try:
            response = requests.get(f'http://localhost:8000/viewer/api/images/{image.id}/data/?window_width=400&window_level=40&inverted=false')
            print(f"Image data endpoint status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Image data endpoint working")
                print(f"  Has image data: {bool(data.get('image_data'))}")
                print(f"  Has metadata: {bool(data.get('metadata'))}")
                if data.get('image_data'):
                    print(f"  Image data length: {len(data['image_data'])}")
            else:
                print(f"✗ Image data endpoint failed: {response.text}")
        except Exception as e:
            print(f"✗ Error testing image data endpoint: {e}")

if __name__ == "__main__":
    test_api_endpoints()