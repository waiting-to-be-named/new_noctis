#!/usr/bin/env python3
"""
Test script to verify the worklist to viewer flow
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
from django.contrib.auth.models import User
import json

def test_worklist_viewer_flow():
    """Test the complete worklist to viewer flow"""
    print("=== Testing Worklist to Viewer Flow ===")
    
    # Create a test client
    client = Client()
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    client.force_login(user)
    
    # Find a worklist entry with a study
    entry = WorklistEntry.objects.filter(study__isnull=False).first()
    
    if not entry:
        print("No worklist entries with associated studies found")
        return False
    
    print(f"Testing with worklist entry: {entry.patient_name}")
    print(f"  Entry ID: {entry.id}")
    print(f"  Study ID: {entry.study.id}")
    print(f"  Study images: {entry.study.total_images}")
    
    # Test 1: Worklist view
    print("\n1. Testing worklist view...")
    response = client.get('/worklist/')
    if response.status_code == 200:
        print("✓ Worklist view accessible")
    else:
        print(f"✗ Worklist view failed: {response.status_code}")
        return False
    
    # Test 2: View study from worklist
    print("\n2. Testing view study from worklist...")
    response = client.get(f'/worklist/view/{entry.id}/')
    if response.status_code == 302:  # Redirect
        print("✓ Worklist view redirect successful")
        redirect_url = response.url
        print(f"  Redirect URL: {redirect_url}")
        
        # Test 3: Follow redirect to viewer
        print("\n3. Testing viewer with study...")
        response = client.get(redirect_url)
        if response.status_code == 200:
            print("✓ Viewer with study accessible")
            
            # Check if the response contains the study ID
            if str(entry.study.id) in response.content.decode():
                print("✓ Study ID found in viewer response")
            else:
                print("⚠️  Study ID not found in viewer response")
        else:
            print(f"✗ Viewer with study failed: {response.status_code}")
            return False
    else:
        print(f"✗ Worklist view redirect failed: {response.status_code}")
        return False
    
    # Test 4: API call for study images
    print("\n4. Testing study images API...")
    response = client.get(f'/viewer/api/studies/{entry.study.id}/images/')
    if response.status_code == 200:
        data = response.json()
        print("✓ Study images API successful")
        print(f"  Number of images: {len(data.get('images', []))}")
        
        if data.get('images'):
            # Test 5: Image data API
            first_image_id = data['images'][0]['id']
            print(f"\n5. Testing image data API for image {first_image_id}...")
            response = client.get(f'/viewer/api/images/{first_image_id}/data/')
            if response.status_code == 200:
                data = response.json()
                print("✓ Image data API successful")
                print(f"  Image data length: {len(data.get('image_data', ''))}")
                return True
            else:
                print(f"✗ Image data API failed: {response.status_code}")
                return False
        else:
            print("⚠️  No images found in study")
            return False
    else:
        print(f"✗ Study images API failed: {response.status_code}")
        return False

def test_viewer_direct_access():
    """Test direct access to viewer with study ID"""
    print("\n=== Testing Direct Viewer Access ===")
    
    client = Client()
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    client.force_login(user)
    
    # Find a study with images
    study = DicomStudy.objects.filter(series__images__isnull=False).first()
    
    if not study:
        print("No studies with images found")
        return False
    
    print(f"Testing direct viewer access with study: {study.patient_name}")
    print(f"  Study ID: {study.id}")
    print(f"  Study images: {study.total_images}")
    
    # Test direct viewer access
    response = client.get(f'/viewer/study/{study.id}/')
    if response.status_code == 200:
        print("✓ Direct viewer access successful")
        
        # Check if the response contains the study ID
        if str(study.id) in response.content.decode():
            print("✓ Study ID found in viewer response")
            return True
        else:
            print("⚠️  Study ID not found in viewer response")
            return False
    else:
        print(f"✗ Direct viewer access failed: {response.status_code}")
        return False

def main():
    """Main test function"""
    print("=== Worklist-Viewer Flow Test ===")
    print()
    
    # Test the complete flow
    flow_success = test_worklist_viewer_flow()
    
    print()
    
    # Test direct viewer access
    direct_success = test_viewer_direct_access()
    
    print()
    print("=== Test Results ===")
    print(f"Worklist to viewer flow: {'✓ PASS' if flow_success else '✗ FAIL'}")
    print(f"Direct viewer access: {'✓ PASS' if direct_success else '✗ FAIL'}")
    
    if flow_success and direct_success:
        print("\n✓ All tests passed! The worklist-viewer connection should be working.")
    else:
        print("\n✗ Some tests failed. Check the issues above.")

if __name__ == "__main__":
    main()