#!/usr/bin/env python3
import os
import sys
import django
from datetime import datetime, timedelta
import random

# Setup Django
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import WorklistEntry, DicomStudy, Facility

# Use existing facility
facility = Facility.objects.first()
if not facility:
    print("No facility found!")
    sys.exit(1)

print(f"Using facility: {facility.name}")

# Sample patient data
patients = [
    {
        'patient_name': 'Smith, John',
        'patient_id': 'PAT001',
        'accession_number': 'ACC001',
        'modality': 'CT',
        'study_description': 'CT HEAD WITHOUT CONTRAST'
    },
    {
        'patient_name': 'Johnson, Sarah',
        'patient_id': 'PAT002',
        'accession_number': 'ACC002',
        'modality': 'MR',
        'study_description': 'MRI BRAIN WITH CONTRAST'
    },
    {
        'patient_name': 'Williams, Robert',
        'patient_id': 'PAT003',
        'accession_number': 'ACC003',
        'modality': 'CR',
        'study_description': 'CHEST X-RAY 2 VIEWS'
    }
]

# Create/update worklist entries
for patient_data in patients:
    entry, created = WorklistEntry.objects.update_or_create(
        accession_number=patient_data['accession_number'],
        defaults={
            'patient_name': patient_data['patient_name'],
            'patient_id': patient_data['patient_id'],
            'modality': patient_data['modality'],
            'procedure_description': patient_data['study_description'],
            'facility': facility,
            'status': random.choice(['scheduled', 'in_progress', 'completed']),
            'scheduled_procedure_step_start_date': datetime.now().date(),
            'scheduled_procedure_step_start_time': datetime.now().time(),
            'scheduled_performing_physician': 'Dr. Smith'
        }
    )
    
    action = "Created" if created else "Updated"
    print(f"✅ {action} worklist entry: {patient_data['patient_name']}")

# Update existing studies with patient info
studies = DicomStudy.objects.all()
entries = WorklistEntry.objects.all()

for i, study in enumerate(studies):
    if i < len(entries):
        entry = list(entries)[i]
        study.patient_name = entry.patient_name
        study.patient_id = entry.patient_id
        study.accession_number = entry.accession_number
        study.modality = entry.modality
        study.study_description = entry.procedure_description
        study.save()
        print(f"🔗 Updated study {study.id} with patient {entry.patient_name}")

print(f"\n📊 Final counts:")
print(f"- Worklist entries: {WorklistEntry.objects.count()}")
print(f"- DICOM studies: {DicomStudy.objects.count()}")
print(f"✅ Patient data fix completed!")