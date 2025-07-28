from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, time, datetime, timezone
from viewer.models import Facility, UserProfile
from worklist.models import WorklistEntry


class Command(BaseCommand):
    help = 'Set up demo data for NoctisView DICOM viewer'

    def handle(self, *args, **options):
        self.stdout.write('Setting up demo data...')

        # Create facilities
        facility1, created = Facility.objects.get_or_create(
            name='City General Hospital',
            defaults={
                'address': '123 Medical Center Drive, City, State 12345',
                'phone': '(555) 123-4567',
                'email': 'info@citygeneral.com'
            }
        )
        if created:
            self.stdout.write(f'Created facility: {facility1.name}')

        facility2, created = Facility.objects.get_or_create(
            name='Regional Medical Center',
            defaults={
                'address': '456 Healthcare Blvd, Town, State 67890',
                'phone': '(555) 987-6543',
                'email': 'admin@regionalmed.com'
            }
        )
        if created:
            self.stdout.write(f'Created facility: {facility2.name}')

        # Create users
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@noctisview.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'Created admin user: {admin_user.username}')

        radiologist_user, created = User.objects.get_or_create(
            username='radiologist',
            defaults={
                'email': 'radiologist@noctisview.com',
                'first_name': 'Dr. Sarah',
                'last_name': 'Johnson',
                'is_staff': True
            }
        )
        if created:
            radiologist_user.set_password('radio123')
            radiologist_user.save()
            self.stdout.write(f'Created radiologist user: {radiologist_user.username}')

        facility_user1, created = User.objects.get_or_create(
            username='facility1',
            defaults={
                'email': 'tech@citygeneral.com',
                'first_name': 'John',
                'last_name': 'Smith'
            }
        )
        if created:
            facility_user1.set_password('facility123')
            facility_user1.save()
            self.stdout.write(f'Created facility user: {facility_user1.username}')

        facility_user2, created = User.objects.get_or_create(
            username='facility2',
            defaults={
                'email': 'tech@regionalmed.com',
                'first_name': 'Jane',
                'last_name': 'Doe'
            }
        )
        if created:
            facility_user2.set_password('facility123')
            facility_user2.save()
            self.stdout.write(f'Created facility user: {facility_user2.username}')

        # Create user profiles
        admin_profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'admin'}
        )
        if created:
            self.stdout.write(f'Created admin profile')

        radiologist_profile, created = UserProfile.objects.get_or_create(
            user=radiologist_user,
            defaults={'role': 'radiologist'}
        )
        if created:
            self.stdout.write(f'Created radiologist profile')

        facility_profile1, created = UserProfile.objects.get_or_create(
            user=facility_user1,
            defaults={
                'role': 'facility',
                'facility': facility1
            }
        )
        if created:
            self.stdout.write(f'Created facility profile for {facility1.name}')

        facility_profile2, created = UserProfile.objects.get_or_create(
            user=facility_user2,
            defaults={
                'role': 'facility',
                'facility': facility2
            }
        )
        if created:
            self.stdout.write(f'Created facility profile for {facility2.name}')

        # Create sample worklist entries
        sample_entries = [
            {
                'patient_id': 'P001',
                'patient_name': 'John Doe',
                'patient_dob': date(1980, 5, 15),
                'patient_sex': 'M',
                'study_instance_uid': '1.2.826.0.1.3680043.8.498.1001',
                'accession_number': 'ACC001',
                'study_date': date.today(),
                'study_time': time(9, 30),
                'modality': 'CT',
                'study_description': 'CT Chest without contrast',
                'body_part': 'Chest',
                'referring_physician': 'Dr. Smith',
                'institution_name': facility1.name,
                'facility': facility1,
                'priority': 'normal',
                'status': 'scheduled',
                'created_by': facility_user1
            },
            {
                'patient_id': 'P002',
                'patient_name': 'Jane Smith',
                'patient_dob': date(1975, 8, 22),
                'patient_sex': 'F',
                'study_instance_uid': '1.2.826.0.1.3680043.8.498.1002',
                'accession_number': 'ACC002',
                'study_date': date.today(),
                'study_time': time(14, 15),
                'modality': 'MRI',
                'study_description': 'MRI Brain with and without contrast',
                'body_part': 'Brain',
                'referring_physician': 'Dr. Johnson',
                'institution_name': facility1.name,
                'facility': facility1,
                'priority': 'high',
                'status': 'scheduled',
                'created_by': facility_user1
            },
            {
                'patient_id': 'P003',
                'patient_name': 'Robert Wilson',
                'patient_dob': date(1965, 12, 3),
                'patient_sex': 'M',
                'study_instance_uid': '1.2.826.0.1.3680043.8.498.1003',
                'accession_number': 'ACC003',
                'study_date': date.today(),
                'study_time': time(16, 45),
                'modality': 'XR',
                'study_description': 'Chest X-Ray PA and Lateral',
                'body_part': 'Chest',
                'referring_physician': 'Dr. Brown',
                'institution_name': facility2.name,
                'facility': facility2,
                'priority': 'urgent',
                'status': 'in_progress',
                'created_by': facility_user2
            },
            {
                'patient_id': 'P004',
                'patient_name': 'Mary Davis',
                'patient_dob': date(1990, 3, 18),
                'patient_sex': 'F',
                'study_instance_uid': '1.2.826.0.1.3680043.8.498.1004',
                'accession_number': 'ACC004',
                'study_date': date.today(),
                'study_time': time(11, 20),
                'modality': 'US',
                'study_description': 'Abdominal Ultrasound',
                'body_part': 'Abdomen',
                'referring_physician': 'Dr. Davis',
                'institution_name': facility2.name,
                'facility': facility2,
                'priority': 'normal',
                'status': 'completed',
                'created_by': facility_user2
            }
        ]

        for entry_data in sample_entries:
            entry, created = WorklistEntry.objects.get_or_create(
                study_instance_uid=entry_data['study_instance_uid'],
                defaults=entry_data
            )
            if created:
                self.stdout.write(f'Created worklist entry: {entry.patient_name} - {entry.study_description}')

        self.stdout.write(
            self.style.SUCCESS('Demo data setup completed successfully!')
        )
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write('  Admin: admin / admin123')
        self.stdout.write('  Radiologist: radiologist / radio123')
        self.stdout.write('  Facility 1: facility1 / facility123')
        self.stdout.write('  Facility 2: facility2 / facility123')
        self.stdout.write('')
        self.stdout.write('Access the system at:')
        self.stdout.write('  DICOM Viewer: http://localhost:8000/')
        self.stdout.write('  Patient Worklist: http://localhost:8000/worklist/')