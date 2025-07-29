from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from viewer.models import Facility
from django.db import transaction


class Command(BaseCommand):
    help = 'Remove test users and data, setup for real users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to remove test data',
        )
        parser.add_argument(
            '--facility-name',
            type=str,
            help='Name of the real facility to create',
        )
        parser.add_argument(
            '--facility-address',
            type=str,
            help='Address of the real facility',
        )
        parser.add_argument(
            '--facility-phone',
            type=str,
            help='Phone number of the real facility',
        )
        parser.add_argument(
            '--facility-email',
            type=str,
            help='Email of the real facility',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will remove test users and data. '
                    'Run with --confirm to proceed.'
                )
            )
            self.stdout.write('\nCurrent test data:')
            
            # Show current test users
            test_users = User.objects.filter(username__in=['admin', 'radiologist'])
            for user in test_users:
                self.stdout.write(f'  - User: {user.username} ({user.email})')
            
            # Show test facilities
            test_facilities = Facility.objects.filter(name__icontains='test')
            for facility in test_facilities:
                self.stdout.write(f'  - Facility: {facility.name} ({facility.email})')
            
            self.stdout.write('\nTo remove test data, run:')
            self.stdout.write('python manage.py remove_test_data --confirm')
            
            if options['facility_name']:
                self.stdout.write('\nTo also create a real facility, add:')
                self.stdout.write(
                    f'--facility-name "{options["facility_name"]}" '
                    f'--facility-address "Your Address" '
                    f'--facility-phone "Your Phone" '
                    f'--facility-email "your@email.com"'
                )
            return

        try:
            with transaction.atomic():
                self.stdout.write('Removing test data...')
                
                # Remove test users
                test_users = User.objects.filter(username__in=['admin', 'radiologist'])
                user_count = test_users.count()
                test_users.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Removed {user_count} test users')
                )
                
                # Remove test facilities
                test_facilities = Facility.objects.filter(
                    name__icontains='test'
                ).exclude(
                    name__icontains='Test Hospital'  # Remove the exact test facility
                )
                # Also remove the exact test facility
                test_hospital = Facility.objects.filter(name='Test Hospital')
                facility_count = test_facilities.count() + test_hospital.count()
                test_facilities.delete()
                test_hospital.delete()
                
                if facility_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'Removed {facility_count} test facilities')
                    )
                
                # Create real facility if provided
                if options['facility_name']:
                    facility = Facility.objects.create(
                        name=options['facility_name'],
                        address=options['facility_address'] or 'Address not provided',
                        phone=options['facility_phone'] or 'Phone not provided',
                        email=options['facility_email'] or 'email@facility.com'
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Created real facility: {facility.name}')
                    )
                
                # Ensure Radiologists group still exists
                radiologists_group, created = Group.objects.get_or_create(name='Radiologists')
                if created:
                    self.stdout.write(
                        self.style.SUCCESS('Created Radiologists group')
                    )
                
                self.stdout.write(
                    self.style.SUCCESS('\nTest data removal completed!')
                )
                self.stdout.write(
                    '\nNext steps:'
                )
                self.stdout.write(
                    '1. Create a superuser: python manage.py createsuperuser'
                )
                self.stdout.write(
                    '2. Login as superuser and create radiologist users through the admin interface'
                )
                self.stdout.write(
                    '3. Or use the radiologist creation form at /admin/create-radiologist/'
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error removing test data: {e}')
            )
            raise