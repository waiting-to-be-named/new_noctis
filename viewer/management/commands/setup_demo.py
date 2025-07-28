from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from viewer.models import Facility, UserProfile, DicomStudy
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Sets up demo users, facilities, and sample data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up demo data...')
        
        # Create facilities
        facility1, _ = Facility.objects.get_or_create(
            code='HOSP001',
            defaults={
                'name': 'General Hospital',
                'address': '123 Medical Center Dr, City, State 12345',
                'phone': '(555) 123-4567',
                'email': 'info@generalhospital.com'
            }
        )
        
        facility2, _ = Facility.objects.get_or_create(
            code='CLINIC001',
            defaults={
                'name': 'City Medical Clinic',
                'address': '456 Health Ave, City, State 12345',
                'phone': '(555) 987-6543',
                'email': 'contact@citymedical.com'
            }
        )
        
        # Create demo users
        # Admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
                'last_name': 'User'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        
        UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': 'admin',
                'facility': facility1
            }
        )
        
        # Radiologist user
        radiologist_user, created = User.objects.get_or_create(
            username='radiologist',
            defaults={
                'email': 'radiologist@example.com',
                'first_name': 'Dr. John',
                'last_name': 'Smith'
            }
        )
        if created:
            radiologist_user.set_password('rad123')
            radiologist_user.save()
        
        UserProfile.objects.get_or_create(
            user=radiologist_user,
            defaults={
                'role': 'radiologist',
                'license_number': 'RAD12345'
            }
        )
        
        # Technician users
        tech1_user, created = User.objects.get_or_create(
            username='tech1',
            defaults={
                'email': 'tech1@example.com',
                'first_name': 'Mary',
                'last_name': 'Johnson'
            }
        )
        if created:
            tech1_user.set_password('tech123')
            tech1_user.save()
        
        UserProfile.objects.get_or_create(
            user=tech1_user,
            defaults={
                'role': 'technician',
                'facility': facility1
            }
        )
        
        tech2_user, created = User.objects.get_or_create(
            username='tech2',
            defaults={
                'email': 'tech2@example.com',
                'first_name': 'Bob',
                'last_name': 'Williams'
            }
        )
        if created:
            tech2_user.set_password('tech123')
            tech2_user.save()
        
        UserProfile.objects.get_or_create(
            user=tech2_user,
            defaults={
                'role': 'technician',
                'facility': facility2
            }
        )
        
        # Create sample studies
        modalities = ['CT', 'MR', 'CR', 'DX', 'US']
        urgencies = ['routine', 'urgent', 'stat']
        statuses = ['pending', 'in_progress', 'completed']
        
        patient_names = [
            'John Doe', 'Jane Smith', 'Robert Johnson', 'Maria Garcia',
            'Michael Brown', 'Sarah Davis', 'David Wilson', 'Lisa Anderson',
            'James Taylor', 'Jennifer Martinez'
        ]
        
        for i in range(20):
            study_date = date.today() - timedelta(days=random.randint(0, 30))
            
            DicomStudy.objects.get_or_create(
                study_instance_uid=f'1.2.3.4.5.{i}',
                defaults={
                    'patient_name': random.choice(patient_names),
                    'patient_id': f'PAT{1000 + i:04d}',
                    'study_date': study_date,
                    'study_description': f'Sample {random.choice(modalities)} Study',
                    'modality': random.choice(modalities),
                    'institution_name': random.choice([facility1.name, facility2.name]),
                    'facility': random.choice([facility1, facility2]),
                    'urgency': random.choice(urgencies),
                    'report_status': random.choice(statuses),
                    'clinical_history': 'Sample clinical history for testing purposes.',
                    'indication': 'Rule out pathology',
                    'referring_physician': 'Dr. Referring Physician',
                    'uploaded_by': random.choice([tech1_user, tech2_user])
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Demo data setup complete!'))
        self.stdout.write(self.style.SUCCESS('\nDemo Users:'))
        self.stdout.write(self.style.SUCCESS('  Admin: username=admin, password=admin123'))
        self.stdout.write(self.style.SUCCESS('  Radiologist: username=radiologist, password=rad123'))
        self.stdout.write(self.style.SUCCESS('  Technician 1: username=tech1, password=tech123'))
        self.stdout.write(self.style.SUCCESS('  Technician 2: username=tech2, password=tech123'))