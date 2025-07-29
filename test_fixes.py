#!/usr/bin/env python3
"""
Test script to verify the fixes work correctly
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.views import ensure_worklist_entries
from viewer.models import DicomStudy, WorklistEntry, Facility

def test_worklist_fix():
    """Test the worklist entry fix"""
    print("Testing worklist entry fix...")
    
    # Count before
    studies_before = DicomStudy.objects.count()
    entries_before = WorklistEntry.objects.count()
    
    print(f"Before: {studies_before} studies, {entries_before} worklist entries")
    
    # Run the fix
    created_count = ensure_worklist_entries()
    
    # Count after
    studies_after = DicomStudy.objects.count()
    entries_after = WorklistEntry.objects.count()
    
    print(f"After: {studies_after} studies, {entries_after} worklist entries")
    print(f"Created {created_count} worklist entries")
    
    # Verify all studies have entries
    studies_without_entries = []
    for study in DicomStudy.objects.all():
        if not WorklistEntry.objects.filter(study=study).exists():
            studies_without_entries.append(study)
    
    if studies_without_entries:
        print(f"ERROR: {len(studies_without_entries)} studies still without worklist entries")
        for study in studies_without_entries:
            print(f"  - {study.patient_name} (ID: {study.id})")
    else:
        print("SUCCESS: All studies now have worklist entries")

def test_facility_creation():
    """Test facility creation"""
    print("\nTesting facility creation...")
    
    # Delete all facilities
    Facility.objects.all().delete()
    print("Deleted all facilities")
    
    # Try to create a worklist entry (should create a default facility)
    from datetime import datetime
    from django.contrib.auth.models import User
    
    # Create a test study
    study = DicomStudy.objects.create(
        study_instance_uid="TEST_UID_123",
        patient_name="Test Patient",
        patient_id="TEST123",
        modality="CT",
        study_description="Test study"
    )
    
    # Create worklist entry (should create default facility)
    try:
        WorklistEntry.objects.create(
            patient_name=study.patient_name,
            patient_id=study.patient_id,
            accession_number="TEST123",
            scheduled_station_ae_title="UPLOAD",
            scheduled_procedure_step_start_date=datetime.now().date(),
            scheduled_procedure_step_start_time=datetime.now().time(),
            modality=study.modality,
            scheduled_performing_physician="Test Doctor",
            procedure_description=study.study_description,
            facility=None,  # This should trigger facility creation
            study=study,
            status='completed'
        )
        print("SUCCESS: Worklist entry created with automatic facility creation")
    except Exception as e:
        print(f"ERROR: Failed to create worklist entry: {e}")
    
    # Check if facility was created
    facilities = Facility.objects.all()
    print(f"Facilities after test: {facilities.count()}")
    for facility in facilities:
        print(f"  - {facility.name}")

def main():
    """Run all tests"""
    print("Testing Noctis DICOM System Fixes")
    print("=" * 40)
    
    test_worklist_fix()
    test_facility_creation()
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()