#!/usr/bin/env python3
"""
Fix patient data display issues and create proper worklist entries
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Setup Django
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import WorklistEntry, DicomStudy, DicomSeries, DicomImage, Facility
from django.contrib.auth.models import User


def create_realistic_patient_data():
    """Create realistic patient data for testing"""
    
    # Ensure we have a facility
    facility, created = Facility.objects.get_or_create(
        name="Main Hospital",
        defaults={
            'address': '123 Medical Center Drive',
            'phone': '555-123-4567',
            'email': 'info@mainhospital.com',
            'ae_title': 'MAIN_HOSPITAL',
            'dicom_port': 11112
        }
    )
    
    # Sample patient data
    patients = [
        {
            'patient_name': 'Smith, John',
            'patient_id': 'PAT001',
            'accession_number': 'ACC001',
            'modality': 'CT',
            'study_description': 'CT HEAD WITHOUT CONTRAST',
            'age': 45,
            'sex': 'M'
        },
        {
            'patient_name': 'Johnson, Sarah',
            'patient_id': 'PAT002',
            'accession_number': 'ACC002',
            'modality': 'MR',
            'study_description': 'MRI BRAIN WITH CONTRAST',
            'age': 32,
            'sex': 'F'
        },
        {
            'patient_name': 'Williams, Robert',
            'patient_id': 'PAT003',
            'accession_number': 'ACC003',
            'modality': 'CR',
            'study_description': 'CHEST X-RAY 2 VIEWS',
            'age': 67,
            'sex': 'M'
        },
        {
            'patient_name': 'Brown, Lisa',
            'patient_id': 'PAT004',
            'accession_number': 'ACC004',
            'modality': 'US',
            'study_description': 'ABDOMINAL ULTRASOUND',
            'age': 28,
            'sex': 'F'
        },
        {
            'patient_name': 'Davis, Michael',
            'patient_id': 'PAT005',
            'accession_number': 'ACC005',
            'modality': 'CT',
            'study_description': 'CT ABDOMEN AND PELVIS WITH CONTRAST',
            'age': 54,
            'sex': 'M'
        }
    ]
    
    print("Creating realistic patient data...")
    
    for i, patient_data in enumerate(patients):
        # Create or update worklist entry
        entry, created = WorklistEntry.objects.update_or_create(
            accession_number=patient_data['accession_number'],
            defaults={
                'patient_name': patient_data['patient_name'],
                'patient_id': patient_data['patient_id'],
                'modality': patient_data['modality'],
                'study_description': patient_data['study_description'],
                'facility': facility,
                'status': random.choice(['scheduled', 'in_progress', 'completed']),
                'scheduled_procedure_step_start_date': datetime.now() - timedelta(days=random.randint(0, 30)),
                'scheduled_procedure_step_start_time': datetime.now().time(),
                'referring_physician': f'Dr. {random.choice(["Anderson", "Wilson", "Taylor", "Moore", "Jackson"])}',
                'patient_age': patient_data['age'],
                'patient_sex': patient_data['sex'],
                'clinical_information': f'Clinical evaluation for {patient_data["study_description"].lower()}'
            }
        )
        
        if created:
            print(f"✅ Created worklist entry: {patient_data['patient_name']}")
        else:
            print(f"📋 Updated worklist entry: {patient_data['patient_name']}")
    
    print(f"\n📊 Total worklist entries: {WorklistEntry.objects.count()}")


def link_studies_to_worklist():
    """Link existing DICOM studies to worklist entries"""
    
    print("\nLinking DICOM studies to worklist entries...")
    
    studies = DicomStudy.objects.all()
    worklist_entries = WorklistEntry.objects.all()
    
    for i, study in enumerate(studies):
        if i < len(worklist_entries):
            entry = worklist_entries[i]
            
            # Update study with worklist info
            study.patient_name = entry.patient_name
            study.patient_id = entry.patient_id
            study.accession_number = entry.accession_number
            study.modality = entry.modality
            study.study_description = entry.study_description
            study.save()
            
            print(f"🔗 Linked study {study.id} to patient {entry.patient_name}")
    
    print(f"✅ Linked {min(len(studies), len(worklist_entries))} studies to worklist entries")


def verify_patient_data():
    """Verify that patient data is properly set up"""
    
    print("\n🔍 Verifying patient data setup...")
    
    # Check worklist entries
    entries = WorklistEntry.objects.all()
    print(f"📋 Worklist entries: {entries.count()}")
    
    for entry in entries:
        print(f"  - {entry.patient_name} ({entry.patient_id}) - {entry.modality} - {entry.status}")
    
    # Check studies
    studies = DicomStudy.objects.all()
    print(f"\n🏥 DICOM studies: {studies.count()}")
    
    for study in studies:
        print(f"  - Study {study.id}: {study.patient_name} - {study.modality}")
    
    # Check images
    images = DicomImage.objects.all()
    print(f"\n📸 DICOM images: {images.count()}")
    
    print("\n✅ Patient data verification complete!")


if __name__ == "__main__":
    print("🚀 Starting patient data fix...")
    
    create_realistic_patient_data()
    link_studies_to_worklist()
    verify_patient_data()
    
    print("\n🎉 Patient data fix completed!")