#!/usr/bin/env python3
"""
Test script to verify the fixes for upload and worklist issues
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.append(str(project_dir))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, WorklistEntry, Facility, DicomSeries, DicomImage
from django.core.files.storage import default_storage
from viewer.views import ensure_directories

def test_directory_structure():
    """Test that required directories exist"""
    print("=== Testing Directory Structure ===")
    
    try:
        ensure_directories()
        print("✅ Directory creation successful")
        
        # Check media directory
        media_root = default_storage.location
        print(f"Media root: {media_root}")
        
        dicom_dir = os.path.join(media_root, 'dicom_files')
        temp_dir = os.path.join(media_root, 'temp')
        
        for directory in [media_root, dicom_dir, temp_dir]:
            if os.path.exists(directory):
                print(f"✅ Directory exists: {directory}")
            else:
                print(f"❌ Directory missing: {directory}")
                
    except Exception as e:
        print(f"❌ Directory setup failed: {e}")

def test_database_connectivity():
    """Test database connectivity and model access"""
    print("\n=== Testing Database Connectivity ===")
    
    try:
        # Test basic queries
        study_count = DicomStudy.objects.count()
        worklist_count = WorklistEntry.objects.count()
        facility_count = Facility.objects.count()
        
        print(f"✅ Database accessible")
        print(f"   Studies: {study_count}")
        print(f"   Worklist entries: {worklist_count}")
        print(f"   Facilities: {facility_count}")
        
        # Test if there are any studies without worklist entries
        studies_without_worklist = DicomStudy.objects.filter(worklistentry__isnull=True).count()
        if studies_without_worklist > 0:
            print(f"⚠️  {studies_without_worklist} studies found without worklist entries")
        else:
            print("✅ All studies have corresponding worklist entries")
            
    except Exception as e:
        print(f"❌ Database connectivity failed: {e}")

def test_facility_setup():
    """Ensure default facility exists"""
    print("\n=== Testing Facility Setup ===")
    
    try:
        facility, created = Facility.objects.get_or_create(
            name="Default Facility",
            defaults={
                'address': 'Unknown',
                'phone': 'Unknown',
                'email': 'unknown@facility.com'
            }
        )
        
        if created:
            print("✅ Created default facility")
        else:
            print("✅ Default facility already exists")
            
        print(f"   Facility: {facility.name}")
        
    except Exception as e:
        print(f"❌ Facility setup failed: {e}")

def test_file_access():
    """Test file access for existing DICOM images"""
    print("\n=== Testing File Access ===")
    
    try:
        images = DicomImage.objects.all()[:5]  # Test first 5 images
        
        if not images:
            print("ℹ️  No DICOM images found in database")
            return
        
        accessible_count = 0
        for image in images:
            try:
                dicom_data = image.load_dicom_data()
                if dicom_data:
                    accessible_count += 1
                    print(f"✅ Image {image.id}: File accessible")
                else:
                    print(f"❌ Image {image.id}: File not accessible - {image.file_path}")
            except Exception as e:
                print(f"❌ Image {image.id}: Error - {e}")
        
        print(f"✅ {accessible_count}/{len(images)} images accessible")
        
    except Exception as e:
        print(f"❌ File access test failed: {e}")

def test_worklist_queries():
    """Test worklist query functionality"""
    print("\n=== Testing Worklist Queries ===")
    
    try:
        from worklist.views import WorklistView
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        
        # Create a mock request
        request = RequestFactory().get('/worklist/')
        request.user = AnonymousUser()
        
        # Test the view
        view = WorklistView()
        view.request = request
        queryset = view.get_queryset()
        
        print(f"✅ Worklist query successful: {queryset.count()} entries")
        
        # Test individual entries
        for entry in queryset[:3]:
            print(f"   Entry: {entry.patient_name} - {entry.accession_number}")
            if entry.study:
                print(f"     Linked to study: {entry.study.id}")
            else:
                print(f"     ⚠️  No linked study")
                
    except Exception as e:
        print(f"❌ Worklist query test failed: {e}")

def main():
    print("🔧 Testing DICOM Upload and Worklist Fixes")
    print("=" * 50)
    
    test_directory_structure()
    test_database_connectivity()
    test_facility_setup()
    test_file_access()
    test_worklist_queries()
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("   - Check the output above for any ❌ errors")
    print("   - ✅ indicates successful tests")
    print("   - ⚠️  indicates warnings that should be addressed")
    print("   - ℹ️  indicates informational messages")

if __name__ == '__main__':
    main()