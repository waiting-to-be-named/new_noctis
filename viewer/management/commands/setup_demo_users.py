from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from viewer.models import Facility


class Command(BaseCommand):
    help = 'Set up demo users for the DICOM system'

    def handle(self, *args, **options):
        # Create demo facility
        facility, created = Facility.objects.get_or_create(
            name='Demo Medical Center',
            defaults={
                'address': '123 Medical Drive',
                'phone': '+1-555-0123',
                'email': 'info@demomedical.com'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created facility: {facility.name}')
            )
        
        # Create groups
        radiologists_group, created = Group.objects.get_or_create(name='Radiologists')
        technicians_group, created = Group.objects.get_or_create(name='Technicians')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@demomedical.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(
                self.style.SUCCESS('Created admin user: admin/admin123')
            )
        
        # Create radiologist user
        radiologist_user, created = User.objects.get_or_create(
            username='radiologist',
            defaults={
                'email': 'radiologist@demomedical.com',
                'first_name': 'Dr. Sarah',
                'last_name': 'Johnson',
                'is_staff': True
            }
        )
        if created:
            radiologist_user.set_password('rad123')
            radiologist_user.save()
            radiologist_user.groups.add(radiologists_group)
            self.stdout.write(
                self.style.SUCCESS('Created radiologist user: radiologist/rad123')
            )
        
        # Create technician user
        tech_user, created = User.objects.get_or_create(
            username='tech',
            defaults={
                'email': 'tech@demomedical.com',
                'first_name': 'Mike',
                'last_name': 'Technician',
                'is_staff': True
            }
        )
        if created:
            tech_user.set_password('tech123')
            tech_user.save()
            tech_user.groups.add(technicians_group)
            self.stdout.write(
                self.style.SUCCESS('Created technician user: tech/tech123')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Demo users setup completed successfully!')
        )