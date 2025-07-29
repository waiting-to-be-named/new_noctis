#!/usr/bin/env python3
"""
Django management command to set up actual healthcare facilities
"""
from django.core.management.base import BaseCommand
from viewer.models import Facility


class Command(BaseCommand):
    help = 'Set up actual healthcare facilities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean-test',
            action='store_true',
            help='Remove test facilities',
        )
        parser.add_argument(
            '--create-sample',
            action='store_true',
            help='Create sample facilities',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up facilities...'))
        
        if options['clean_test']:
            self.clean_test_facilities()
        
        if options['create_sample']:
            self.create_sample_facilities()
        
        self.stdout.write(self.style.SUCCESS('Facility setup completed!'))

    def clean_test_facilities(self):
        """Remove test facilities"""
        self.stdout.write('Cleaning test facilities...')
        
        test_facilities = Facility.objects.filter(name__icontains='test')
        count = test_facilities.count()
        test_facilities.delete()
        self.stdout.write(f'Removed {count} test facilities')

    def create_sample_facilities(self):
        """Create sample healthcare facilities"""
        self.stdout.write('Creating sample facilities...')
        
        facilities = [
            {
                'name': 'General Hospital',
                'address': '123 Main Street, City, State 12345',
                'phone': '(555) 123-4567',
                'email': 'info@generalhospital.com'
            },
            {
                'name': 'Medical Center',
                'address': '456 Oak Avenue, City, State 12345',
                'phone': '(555) 234-5678',
                'email': 'contact@medicalcenter.com'
            },
            {
                'name': 'Community Clinic',
                'address': '789 Pine Street, City, State 12345',
                'phone': '(555) 345-6789',
                'email': 'info@communityclinic.com'
            },
            {
                'name': 'Specialty Hospital',
                'address': '321 Elm Road, City, State 12345',
                'phone': '(555) 456-7890',
                'email': 'contact@specialtyhospital.com'
            },
            {
                'name': 'Regional Medical Center',
                'address': '654 Maple Drive, City, State 12345',
                'phone': '(555) 567-8901',
                'email': 'info@regionalmedical.com'
            }
        ]
        
        for facility_data in facilities:
            try:
                # Check if facility already exists
                if Facility.objects.filter(name=facility_data['name']).exists():
                    self.stdout.write(f'Facility {facility_data["name"]} already exists')
                    continue
                
                # Create facility
                facility = Facility.objects.create(
                    name=facility_data['name'],
                    address=facility_data['address'],
                    phone=facility_data['phone'],
                    email=facility_data['email']
                )
                
                self.stdout.write(f'Created facility: {facility.name}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating facility {facility_data["name"]}: {e}'))