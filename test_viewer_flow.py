#!/usr/bin/env python3
"""
Test script to verify the viewer flow and identify issues
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/workspace')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage, WorklistEntry
from worklist.models import Facility
from django.contrib.auth.models import User

def test_viewer_flow():
    """Test the viewer flow to identify issues"""
    
    print("=== Testing Viewer Flow ===")
    
    # Check if we have any studies
    studies = DicomStudy.objects.all()
    print(f"Total studies in database: {studies.count()}")
    
    if studies.count() == 0:
        print("No studies found in database")
        return
    
    # Check if we have any worklist entries
    entries = WorklistEntry.objects.all()
    print(f"Total worklist entries: {entries.count()}")
    
    if entries.count() == 0:
        print("No worklist entries found")
        return
    
    # Check a specific entry
    entry = entries.first()
    print(f"\nTesting entry: {entry.id}")
    print(f"Patient: {entry.patient_name}")
    print(f"Study: {entry.study}")
    
    if entry.study:
        print(f"Study ID: {entry.study.id}")
        print(f"Study has series: {entry.study.series_set.count()}")
        
        # Check series and images
        for series in entry.study.series_set.all():
            print(f"  Series {series.series_number}: {series.series_description}")
            print(f"    Images: {series.images.count()}")
            
            for image in series.images.all()[:3]:  # Show first 3 images
                print(f"      Image {image.instance_number}: {image.rows}x{image.columns}")
    else:
        print("Entry has no associated study!")
    
    # Test the API endpoint that should be called
    print(f"\n=== Testing API Endpoint ===")
    print(f"Expected API call: /viewer/api/studies/{entry.study.id}/images/")
    
    # Check if the study has images
    if entry.study:
        images = DicomImage.objects.filter(series__study=entry.study)
        print(f"Total images for study: {images.count()}")
        
        if images.count() > 0:
            print("Study has images - API should work")
        else:
            print("Study has no images - this is the problem!")
    else:
        print("No study associated with entry")

if __name__ == "__main__":
    test_viewer_flow()