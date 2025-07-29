#!/usr/bin/env python3
"""
Test script to debug DICOM viewer issue
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage, DicomSeries
from django.test import Client
from django.contrib.auth.models import User
import json

def test_dicom_loading():
    """Test if DICOM files can be loaded and processed"""
    print("=== Testing DICOM Loading ===")
    
    # Get all images
    images = DicomImage.objects.all()
    print(f"Found {images.count()} images in database")
    
    for img in images:
        print(f"\n--- Testing Image {img.id} ---")
        print(f"File path: {img.file_path}")
        
        # Check if file exists
        if hasattr(img.file_path, 'path'):
            file_path = img.file_path.path
            exists = os.path.exists(file_path)
            print(f"File exists: {exists}")
            if exists:
                print(f"File size: {os.path.getsize(file_path)} bytes")
        
        # Test loading DICOM data
        try:
            dicom_data = img.load_dicom_data()
            if dicom_data:
                print(f"DICOM loaded successfully")
                print(f"Rows: {getattr(dicom_data, 'Rows', 'N/A')}")
                print(f"Columns: {getattr(dicom_data, 'Columns', 'N/A')}")
                print(f"Modality: {getattr(dicom_data, 'Modality', 'N/A')}")
                
                # Test pixel array
                if hasattr(dicom_data, 'pixel_array'):
                    pixel_array = dicom_data.pixel_array
                    print(f"Pixel array shape: {pixel_array.shape}")
                    print(f"Pixel array dtype: {pixel_array.dtype}")
                    print(f"Pixel array min/max: {pixel_array.min()}/{pixel_array.max()}")
                else:
                    print("No pixel array found")
            else:
                print("Failed to load DICOM data")
        except Exception as e:
            print(f"Error loading DICOM: {e}")
            import traceback
            traceback.print_exc()

def test_api_endpoints():
    """Test the API endpoints that the viewer uses"""
    print("\n=== Testing API Endpoints ===")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    client = Client()
    client.force_login(user)
    
    # Test studies endpoint
    print("\n--- Testing Studies Endpoint ---")
    response = client.get('/viewer/api/studies/')
    print(f"Studies endpoint status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data)} studies")
        for study in data[:3]:
            print(f"  Study {study['id']}: {study['patient_name']} - {study['modality']}")
    
    # Test study images endpoint
    studies = DicomStudy.objects.all()
    if studies.exists():
        study = studies.first()
        print(f"\n--- Testing Study Images Endpoint for Study {study.id} ---")
        response = client.get(f'/viewer/api/studies/{study.id}/images/')
        print(f"Study images endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Study: {data['study']['patient_name']}")
            print(f"Images: {len(data['images'])}")
            for img in data['images']:
                print(f"  Image {img['id']}: {img['rows']}x{img['columns']}")
        else:
            print(f"Error response: {response.content}")
    
    # Test image data endpoint
    images = DicomImage.objects.all()
    if images.exists():
        image = images.first()
        print(f"\n--- Testing Image Data Endpoint for Image {image.id} ---")
        response = client.get(f'/viewer/api/images/{image.id}/data/')
        print(f"Image data endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Image data received: {'image_data' in data}")
            if 'image_data' in data:
                print(f"Image data length: {len(data['image_data'])}")
                print(f"Metadata: {data['metadata']}")
        else:
            print(f"Error response: {response.content}")

def test_viewer_initialization():
    """Test the viewer initialization with a study"""
    print("\n=== Testing Viewer Initialization ===")
    
    studies = DicomStudy.objects.all()
    if studies.exists():
        study = studies.first()
        print(f"Testing viewer with study {study.id}: {study.patient_name}")
        
        # Test the viewer URL
        client = Client()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )
        client.force_login(user)
        
        response = client.get(f'/viewer/study/{study.id}/')
        print(f"Viewer page status: {response.status_code}")
        if response.status_code == 200:
            print("Viewer page loaded successfully")
            # Check if initial study ID is in the response
            content = response.content.decode()
            if f'initialStudyId = {study.id}' in content:
                print("Initial study ID found in page")
            else:
                print("Initial study ID NOT found in page")
        else:
            print(f"Error loading viewer page: {response.content}")

if __name__ == '__main__':
    test_dicom_loading()
    test_api_endpoints()
    test_viewer_initialization()