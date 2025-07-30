#!/usr/bin/env python3
"""
Test script to verify the viewer API is working correctly
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage, WorklistEntry
from django.test import Client
import json

def test_viewer_api():
    """Test the viewer API endpoints"""
    print("=== Testing Viewer API ===")
    
    # Get the first study
    try:
        study = DicomStudy.objects.first()
        if not study:
            print("No studies found in database")
            return
        
        print(f"Testing with study: {study}")
        print(f"Study ID: {study.id}")
        print(f"Patient: {study.patient_name}")
        print(f"Modality: {study.modality}")
        
        # Test the get_study_images API
        print("\n1. Testing get_study_images API...")
        from viewer.views import get_study_images
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth.models import User
        
        # Create a test request
        factory = APIRequestFactory()
        request = factory.get(f'/viewer/api/studies/{study.id}/images/')
        
        # Create a test user
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        request.user = user
        
        # Call the API
        response = get_study_images(request, study.id)
        
        if response.status_code == 200:
            data = response.data
            print("✓ API call successful")
            print(f"  Study data: {data.get('study', {}).get('patient_name', 'N/A')}")
            print(f"  Number of images: {len(data.get('images', []))}")
            
            if data.get('images'):
                first_image = data['images'][0]
                print(f"  First image ID: {first_image.get('id')}")
                print(f"  Image dimensions: {first_image.get('rows')}x{first_image.get('columns')}")
            else:
                print("  No images found in study")
        else:
            print(f"✗ API call failed with status {response.status_code}")
            print(f"  Response: {response.data}")
        
        # Test the get_image_data API if we have images
        if data.get('images'):
            print("\n2. Testing get_image_data API...")
            from viewer.views import get_image_data
            
            first_image_id = data['images'][0]['id']
            request = factory.get(f'/viewer/api/images/{first_image_id}/data/')
            request.user = user
            
            response = get_image_data(request, first_image_id)
            
            if response.status_code == 200:
                print("✓ Image data API call successful")
                print(f"  Image data length: {len(response.data.get('image_data', ''))}")
                print(f"  Metadata: {response.data.get('metadata', {})}")
            else:
                print(f"✗ Image data API call failed with status {response.status_code}")
                print(f"  Response: {response.data}")
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

def test_worklist_entries():
    """Test worklist entries"""
    print("\n=== Testing Worklist Entries ===")
    
    try:
        entries = WorklistEntry.objects.all()
        print(f"Total worklist entries: {entries.count()}")
        
        for entry in entries[:3]:  # Show first 3 entries
            print(f"  Entry: {entry.patient_name} (ID: {entry.id})")
            print(f"    Study: {entry.study}")
            print(f"    Status: {entry.status}")
            print(f"    Accession: {entry.accession_number}")
            
            if entry.study:
                print(f"    Study ID: {entry.study.id}")
                print(f"    Study images: {entry.study.total_images}")
            else:
                print("    No associated study")
            print()
        
    except Exception as e:
        print(f"Error testing worklist entries: {e}")

if __name__ == "__main__":
    test_viewer_api()
    test_worklist_entries()