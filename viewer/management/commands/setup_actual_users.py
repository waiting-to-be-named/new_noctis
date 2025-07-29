#!/usr/bin/env python3
"""
Django management command to replace test users with actual users
and clean up test data.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.contrib.auth.management.commands import createsuperuser
from viewer.models import DicomStudy, Facility, WorklistEntry
import getpass


class Command(BaseCommand):
    help = 'Replace test users with actual users and clean up test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean-test-data',
            action='store_true',
            help='Remove all test data (studies, facilities, etc.)',
        )
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='Create a new admin user',
        )
        parser.add_argument(
            '--create-radiologists',
            action='store_true',
            help='Create radiologist users',
        )
        parser.add_argument(
            '--create-technicians',
            action='store_true',
            help='Create technician users',
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Interactive mode for user creation',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting user setup...'))
        
        # Clean test data if requested
        if options['clean_test_data']:
            self.clean_test_data()
        
        # Create admin user
        if options['create_admin'] or options['interactive']:
            self.create_admin_user()
        
        # Create radiologists
        if options['create_radiologists'] or options['interactive']:
            self.create_radiologist_users()
        
        # Create technicians
        if options['create_technicians'] or options['interactive']:
            self.create_technician_users()
        
        self.stdout.write(self.style.SUCCESS('User setup completed!'))

    def clean_test_data(self):
        """Remove test data from the database"""
        self.stdout.write('Cleaning test data...')
        
        # Remove test studies
        test_studies = DicomStudy.objects.filter(
            patient_name__icontains='test',
            study_instance_uid__icontains='1.2.3'
        )
        count = test_studies.count()
        test_studies.delete()
        self.stdout.write(f'Removed {count} test studies')
        
        # Remove test facilities
        test_facilities = Facility.objects.filter(name__icontains='test')
        count = test_facilities.count()
        test_facilities.delete()
        self.stdout.write(f'Removed {count} test facilities')
        
        # Remove test worklist entries
        test_entries = WorklistEntry.objects.filter(patient_name__icontains='test')
        count = test_entries.count()
        test_entries.delete()
        self.stdout.write(f'Removed {count} test worklist entries')

    def create_admin_user(self):
        """Create an admin user"""
        self.stdout.write('Creating admin user...')
        
        try:
            username = input('Enter admin username (default: admin): ').strip() or 'admin'
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'User {username} already exists')
                return
            
            email = input('Enter admin email: ').strip()
            first_name = input('Enter admin first name: ').strip()
            last_name = input('Enter admin last name: ').strip()
            
            # Get password securely
            while True:
                password = getpass.getpass('Enter admin password: ')
                password_confirm = getpass.getpass('Confirm admin password: ')
                if password == password_confirm:
                    break
                else:
                    self.stdout.write(self.style.ERROR('Passwords do not match'))
            
            # Create admin user
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            user.is_superuser = True
            user.is_staff = True
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'Admin user {username} created successfully'))
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Admin user creation cancelled'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {e}'))

    def create_radiologist_users(self):
        """Create radiologist users"""
        self.stdout.write('Creating radiologist users...')
        
        # Get or create Radiologists group
        radiologist_group, created = Group.objects.get_or_create(name='Radiologists')
        if created:
            self.stdout.write('Created Radiologists group')
        
        radiologists = [
            {
                'username': 'dr.smith',
                'email': 'dr.smith@hospital.com',
                'first_name': 'John',
                'last_name': 'Smith',
                'password': 'radiologist123'
            },
            {
                'username': 'dr.johnson',
                'email': 'dr.johnson@hospital.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'password': 'radiologist123'
            },
            {
                'username': 'dr.williams',
                'email': 'dr.williams@hospital.com',
                'first_name': 'Michael',
                'last_name': 'Williams',
                'password': 'radiologist123'
            }
        ]
        
        for radiologist_data in radiologists:
            try:
                # Check if user already exists
                if User.objects.filter(username=radiologist_data['username']).exists():
                    self.stdout.write(f'Radiologist {radiologist_data["username"]} already exists')
                    continue
                
                # Create radiologist user
                user = User.objects.create_user(
                    username=radiologist_data['username'],
                    email=radiologist_data['email'],
                    first_name=radiologist_data['first_name'],
                    last_name=radiologist_data['last_name'],
                    password=radiologist_data['password']
                )
                
                # Add to radiologists group
                user.groups.add(radiologist_group)
                
                self.stdout.write(f'Created radiologist: {user.get_full_name()} ({user.username})')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating radiologist {radiologist_data["username"]}: {e}'))

    def create_technician_users(self):
        """Create technician users"""
        self.stdout.write('Creating technician users...')
        
        # Get or create Technicians group
        technician_group, created = Group.objects.get_or_create(name='Technicians')
        if created:
            self.stdout.write('Created Technicians group')
        
        technicians = [
            {
                'username': 'tech.davis',
                'email': 'tech.davis@hospital.com',
                'first_name': 'Emily',
                'last_name': 'Davis',
                'password': 'technician123'
            },
            {
                'username': 'tech.miller',
                'email': 'tech.miller@hospital.com',
                'first_name': 'David',
                'last_name': 'Miller',
                'password': 'technician123'
            },
            {
                'username': 'tech.garcia',
                'email': 'tech.garcia@hospital.com',
                'first_name': 'Maria',
                'last_name': 'Garcia',
                'password': 'technician123'
            }
        ]
        
        for technician_data in technicians:
            try:
                # Check if user already exists
                if User.objects.filter(username=technician_data['username']).exists():
                    self.stdout.write(f'Technician {technician_data["username"]} already exists')
                    continue
                
                # Create technician user
                user = User.objects.create_user(
                    username=technician_data['username'],
                    email=technician_data['email'],
                    first_name=technician_data['first_name'],
                    last_name=technician_data['last_name'],
                    password=technician_data['password']
                )
                
                # Add to technicians group
                user.groups.add(technician_group)
                
                self.stdout.write(f'Created technician: {user.get_full_name()} ({user.username})')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating technician {technician_data["username"]}: {e}'))

    def create_facility_staff(self):
        """Create facility staff users"""
        self.stdout.write('Creating facility staff users...')
        
        # Get or create Facility Staff group
        facility_staff_group, created = Group.objects.get_or_create(name='Facility Staff')
        if created:
            self.stdout.write('Created Facility Staff group')
        
        facility_staff = [
            {
                'username': 'staff.rodriguez',
                'email': 'staff.rodriguez@hospital.com',
                'first_name': 'Carlos',
                'last_name': 'Rodriguez',
                'password': 'staff123'
            },
            {
                'username': 'staff.martinez',
                'email': 'staff.martinez@hospital.com',
                'first_name': 'Ana',
                'last_name': 'Martinez',
                'password': 'staff123'
            }
        ]
        
        for staff_data in facility_staff:
            try:
                # Check if user already exists
                if User.objects.filter(username=staff_data['username']).exists():
                    self.stdout.write(f'Facility staff {staff_data["username"]} already exists')
                    continue
                
                # Create facility staff user
                user = User.objects.create_user(
                    username=staff_data['username'],
                    email=staff_data['email'],
                    first_name=staff_data['first_name'],
                    last_name=staff_data['last_name'],
                    password=staff_data['password']
                )
                
                # Add to facility staff group
                user.groups.add(facility_staff_group)
                
                self.stdout.write(f'Created facility staff: {user.get_full_name()} ({user.username})')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating facility staff {staff_data["username"]}: {e}'))