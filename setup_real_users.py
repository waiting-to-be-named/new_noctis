#!/usr/bin/env python3
"""
Setup script to transition from test users to real users for DICOM Viewer
"""
import os
import sys
import django
from pathlib import Path

# Add the current directory to the Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.contrib.auth.models import User, Group
from viewer.models import Facility
from django.db import transaction


def main():
    print("=== DICOM Viewer - Real User Setup ===\n")
    
    # Check current state
    print("Checking current database state...")
    test_users = User.objects.filter(username__in=['admin', 'radiologist'])
    test_facilities = Facility.objects.filter(name__icontains='test')
    
    if test_users.exists() or test_facilities.exists():
        print(f"Found {test_users.count()} test users and {test_facilities.count()} test facilities.")
        
        # Ask for confirmation
        confirm = input("\nDo you want to remove test data and setup for real users? (y/N): ")
        if confirm.lower() != 'y':
            print("Setup cancelled.")
            return
        
        # Collect facility information
        print("\nPlease provide real facility information:")
        facility_name = input("Facility Name: ").strip()
        if not facility_name:
            facility_name = "Healthcare Facility"
        
        facility_address = input("Facility Address: ").strip()
        if not facility_address:
            facility_address = "Address not provided"
        
        facility_phone = input("Facility Phone: ").strip()
        if not facility_phone:
            facility_phone = "Phone not provided"
        
        facility_email = input("Facility Email: ").strip()
        if not facility_email:
            facility_email = "contact@facility.com"
        
        # Remove test data and create real facility
        with transaction.atomic():
            print("\nRemoving test data...")
            
            # Remove test users
            user_count = test_users.count()
            test_users.delete()
            print(f"✓ Removed {user_count} test users")
            
            # Remove test facilities
            facility_count = test_facilities.count()
            test_facilities.delete()
            # Also remove the exact "Test Hospital"
            test_hospital = Facility.objects.filter(name='Test Hospital')
            facility_count += test_hospital.count()
            test_hospital.delete()
            
            if facility_count > 0:
                print(f"✓ Removed {facility_count} test facilities")
            
            # Create real facility
            facility = Facility.objects.create(
                name=facility_name,
                address=facility_address,
                phone=facility_phone,
                email=facility_email
            )
            print(f"✓ Created real facility: {facility.name}")
            
            # Ensure Radiologists group exists
            radiologists_group, created = Group.objects.get_or_create(name='Radiologists')
            if created:
                print("✓ Created Radiologists group")
    
    else:
        print("✓ No test data found. System is ready for real users.")
    
    # Check if we need to create a superuser
    if not User.objects.filter(is_superuser=True).exists():
        print("\n=== Create Administrator Account ===")
        create_superuser = input("No administrator account found. Create one now? (Y/n): ")
        if create_superuser.lower() != 'n':
            print("\nCreating administrator account...")
            username = input("Administrator username: ").strip()
            if not username:
                username = "admin"
            
            email = input("Administrator email: ").strip()
            if not email:
                email = "admin@example.com"
            
            # Create superuser
            admin_user = User.objects.create_superuser(
                username=username,
                email=email,
                password='admin123'  # Default password - should be changed
            )
            print(f"✓ Created administrator: {admin_user.username}")
            print(f"  Default password: admin123")
            print(f"  ⚠️  Please change this password after first login!")
    
    print("\n=== Setup Complete ===")
    print("Next steps:")
    print("1. Start the server: python manage.py runserver")
    print("2. Access the admin interface at: http://localhost:8000/admin/")
    print("3. Login with your administrator account")
    print("4. Create radiologist users at: http://localhost:8000/admin/create-radiologist/")
    print("5. Change the default administrator password")
    print("\nThe system is now ready for production use with real users!")


if __name__ == "__main__":
    main()