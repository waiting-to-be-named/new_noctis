#!/usr/bin/env python
"""
Script to create sample worklist entries and related data for testing
"""

import os
import sys
import django
from django.utils import timezone
from datetime import datetime, timedelta, time
import random

# Setup Django environment
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import Facility, WorklistEntry, DicomStudy
from django.contrib.auth.models import User

def create_sample_data():
    """Create sample worklist entries and facilities for testing"""
    
    print("Creating sample data for Noctis worklist...")
    
    # Create facilities if they don't exist
    facilities_data = [
        {
            'name': 'General Hospital',
            'address': '123 Medical Center Dr, Healthcare City, HC 12345',
            'phone': '555-0123',
            'email': 'admin@generalhospital.com'
        },
        {
            'name': 'Medical Center',
            'address': '456 Health Ave, Medical District, MD 67890',
            'phone': '555-0124',
            'email': 'info@medicalcenter.com'
        },
        {
            'name': 'Emergency Center',
            'address': '789 Emergency Blvd, Urgent Care Plaza, UC 54321',
            'phone': '555-0125',
            'email': 'emergency@emergencycenter.com'
        },
        {
            'name': "Women's Health",
            'address': '321 Women Dr, Family Care Center, FC 98765',
            'phone': '555-0126',
            'email': 'care@womenshealth.com'
        }
    ]
    
    facilities = []
    for facility_data in facilities_data:
        facility, created = Facility.objects.get_or_create(
            name=facility_data['name'],
            defaults=facility_data
        )
        facilities.append(facility)
        if created:
            print(f"Created facility: {facility.name}")
        else:
            print(f"Facility already exists: {facility.name}")
    
    # Create sample worklist entries
    sample_entries = [
        {
            'patient_name': 'Johnson, Sarah M.',
            'patient_id': 'PAT001234',
            'accession_number': 'ACC001234',
            'modality': 'CT',
            'procedure_description': 'Chest CT with contrast for lung nodule evaluation',
            'scheduled_performing_physician': 'Dr. Smith, John',
            'status': 'scheduled',
            'days_offset': 0,  # Today
            'time_offset': 2,  # 2 hours from now
        },
        {
            'patient_name': 'Smith, Michael R.',
            'patient_id': 'PAT001235',
            'accession_number': 'ACC001235',
            'modality': 'MR',
            'procedure_description': 'Brain MRI without contrast for headache evaluation',
            'scheduled_performing_physician': 'Dr. Davis, Emily',
            'status': 'in_progress',
            'days_offset': 0,  # Today
            'time_offset': -1,  # 1 hour ago
        },
        {
            'patient_name': 'Davis, Emily K.',
            'patient_id': 'PAT001236',
            'accession_number': 'ACC001236',
            'modality': 'CR',
            'procedure_description': 'Chest X-Ray PA and lateral for routine screening',
            'scheduled_performing_physician': 'Dr. Wilson, Robert',
            'status': 'completed',
            'days_offset': -1,  # Yesterday
            'time_offset': -3,  # 3 hours ago (from yesterday)
        },
        {
            'patient_name': 'Wilson, Robert J.',
            'patient_id': 'PAT001237',
            'accession_number': 'ACC001237',
            'modality': 'CT',
            'procedure_description': 'Urgent abdominal CT with contrast for acute abdominal pain',
            'scheduled_performing_physician': 'Dr. Brown, Lisa',
            'status': 'scheduled',
            'days_offset': 0,  # Today
            'time_offset': 1,  # 1 hour from now
        },
        {
            'patient_name': 'Brown, Lisa A.',
            'patient_id': 'PAT001238',
            'accession_number': 'ACC001238',
            'modality': 'US',
            'procedure_description': 'Obstetric ultrasound for 20-week anatomy scan',
            'scheduled_performing_physician': 'Dr. Johnson, Sarah',
            'status': 'in_progress',
            'days_offset': 0,  # Today
            'time_offset': 0,  # Now
        },
        {
            'patient_name': 'Anderson, Mark T.',
            'patient_id': 'PAT001239',
            'accession_number': 'ACC001239',
            'modality': 'MR',
            'procedure_description': 'Knee MRI without contrast for sports injury assessment',
            'scheduled_performing_physician': 'Dr. Taylor, James',
            'status': 'scheduled',
            'days_offset': 1,  # Tomorrow
            'time_offset': 3,  # 3 hours from now (tomorrow)
        },
        {
            'patient_name': 'Taylor, James P.',
            'patient_id': 'PAT001240',
            'accession_number': 'ACC001240',
            'modality': 'CT',
            'procedure_description': 'Head CT without contrast for trauma evaluation',
            'scheduled_performing_physician': 'Dr. Anderson, Mark',
            'status': 'scheduled',
            'days_offset': 0,  # Today
            'time_offset': 4,  # 4 hours from now
        },
        {
            'patient_name': 'Miller, Jennifer L.',
            'patient_id': 'PAT001241',
            'accession_number': 'ACC001241',
            'modality': 'MG',
            'procedure_description': 'Routine bilateral mammography screening',
            'scheduled_performing_physician': 'Dr. Miller, Jennifer',
            'status': 'completed',
            'days_offset': -2,  # 2 days ago
            'time_offset': -2,  # 2 hours ago (from 2 days ago)
        }
    ]
    
    # Clear existing sample entries to avoid duplicates
    print("Clearing existing sample data...")
    WorklistEntry.objects.filter(patient_id__startswith='PAT0012').delete()
    
    # Create worklist entries
    for i, entry_data in enumerate(sample_entries):
        # Calculate scheduled date and time
        base_date = timezone.now().date() + timedelta(days=entry_data['days_offset'])
        base_time = (timezone.now() + timedelta(hours=entry_data['time_offset'])).time()
        
        # Assign facility (rotate through available facilities)
        facility = facilities[i % len(facilities)]
        
        # Create the worklist entry
        entry = WorklistEntry.objects.create(
            patient_name=entry_data['patient_name'],
            patient_id=entry_data['patient_id'],
            accession_number=entry_data['accession_number'],
            scheduled_station_ae_title=facility.ae_title or 'NOCTIS_AE',
            scheduled_procedure_step_start_date=base_date,
            scheduled_procedure_step_start_time=base_time,
            modality=entry_data['modality'],
            scheduled_performing_physician=entry_data['scheduled_performing_physician'],
            procedure_description=entry_data['procedure_description'],
            facility=facility,
            status=entry_data['status']
        )
        
        print(f"Created worklist entry: {entry.patient_name} - {entry.accession_number}")
        
        # For some entries, create corresponding DICOM studies
        if entry_data['status'] in ['in_progress', 'completed'] and random.choice([True, False]):
            study = DicomStudy.objects.create(
                study_instance_uid=f"1.2.3.4.5.{entry.id}.{random.randint(1000, 9999)}",
                patient_name=entry.patient_name,
                patient_id=entry.patient_id,
                study_date=entry.scheduled_procedure_step_start_date,
                study_time=entry.scheduled_procedure_step_start_time,
                study_description=entry.procedure_description,
                modality=entry.modality,
                institution_name=facility.name,
                facility=facility,
                accession_number=entry.accession_number,
                referring_physician=entry.scheduled_performing_physician
            )
            
            # Link the study to the worklist entry
            entry.study = study
            entry.save()
            
            print(f"  -> Created associated DICOM study: {study.study_instance_uid}")
    
    print(f"\nSample data creation completed!")
    print(f"Created {len(facilities)} facilities")
    print(f"Created {len(sample_entries)} worklist entries")
    print(f"Created {WorklistEntry.objects.filter(study__isnull=False).count()} associated DICOM studies")
    
    print("\nWorklist entries by status:")
    for status_code, status_label in WorklistEntry.STATUS_CHOICES:
        count = WorklistEntry.objects.filter(status=status_code).count()
        print(f"  {status_label}: {count}")
    
    print("\nWorklist entries by facility:")
    for facility in facilities:
        count = WorklistEntry.objects.filter(facility=facility).count()
        print(f"  {facility.name}: {count}")

if __name__ == '__main__':
    create_sample_data()