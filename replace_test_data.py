#!/usr/bin/env python3
"""
Comprehensive script to replace test data with actual data
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.append(str(project_dir))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.contrib.auth.models import User, Group
from viewer.models import DicomStudy, Facility, WorklistEntry
import getpass


def clean_test_data():
    """Remove all test data from the database"""
    print("🧹 Cleaning test data...")
    
    # Remove test studies
    test_studies = DicomStudy.objects.filter(
        patient_name__icontains='test',
        study_instance_uid__icontains='1.2.3'
    )
    count = test_studies.count()
    test_studies.delete()
    print(f"   Removed {count} test studies")
    
    # Remove test facilities
    test_facilities = Facility.objects.filter(name__icontains='test')
    count = test_facilities.count()
    test_facilities.delete()
    print(f"   Removed {count} test facilities")
    
    # Remove test worklist entries
    test_entries = WorklistEntry.objects.filter(patient_name__icontains='test')
    count = test_entries.count()
    test_entries.delete()
    print(f"   Removed {count} test worklist entries")
    
    print("✅ Test data cleaned")


def create_actual_facilities():
    """Create actual healthcare facilities"""
    print("🏥 Creating actual facilities...")
    
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
    
    created_count = 0
    for facility_data in facilities:
        try:
            # Check if facility already exists
            if Facility.objects.filter(name=facility_data['name']).exists():
                print(f"   Facility {facility_data['name']} already exists")
                continue
            
            # Create facility
            facility = Facility.objects.create(
                name=facility_data['name'],
                address=facility_data['address'],
                phone=facility_data['phone'],
                email=facility_data['email']
            )
            
            print(f"   Created facility: {facility.name}")
            created_count += 1
            
        except Exception as e:
            print(f"   Error creating facility {facility_data['name']}: {e}")
    
    print(f"✅ Created {created_count} facilities")


def create_actual_users():
    """Create actual users with proper roles"""
    print("👥 Creating actual users...")
    
    # Create groups
    radiologist_group, _ = Group.objects.get_or_create(name='Radiologists')
    technician_group, _ = Group.objects.get_or_create(name='Technicians')
    facility_staff_group, _ = Group.objects.get_or_create(name='Facility Staff')
    
    # Radiologists
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
        },
        {
            'username': 'dr.brown',
            'email': 'dr.brown@hospital.com',
            'first_name': 'Lisa',
            'last_name': 'Brown',
            'password': 'radiologist123'
        }
    ]
    
    # Technicians
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
    
    # Facility Staff
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
    
    created_users = []
    
    # Create radiologists
    for user_data in radiologists:
        try:
            if User.objects.filter(username=user_data['username']).exists():
                print(f"   Radiologist {user_data['username']} already exists")
                continue
            
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                password=user_data['password']
            )
            user.groups.add(radiologist_group)
            created_users.append(f"Radiologist: {user.get_full_name()} ({user.username})")
            
        except Exception as e:
            print(f"   Error creating radiologist {user_data['username']}: {e}")
    
    # Create technicians
    for user_data in technicians:
        try:
            if User.objects.filter(username=user_data['username']).exists():
                print(f"   Technician {user_data['username']} already exists")
                continue
            
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                password=user_data['password']
            )
            user.groups.add(technician_group)
            created_users.append(f"Technician: {user.get_full_name()} ({user.username})")
            
        except Exception as e:
            print(f"   Error creating technician {user_data['username']}: {e}")
    
    # Create facility staff
    for user_data in facility_staff:
        try:
            if User.objects.filter(username=user_data['username']).exists():
                print(f"   Facility staff {user_data['username']} already exists")
                continue
            
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                password=user_data['password']
            )
            user.groups.add(facility_staff_group)
            created_users.append(f"Facility Staff: {user.get_full_name()} ({user.username})")
            
        except Exception as e:
            print(f"   Error creating facility staff {user_data['username']}: {e}")
    
    print(f"✅ Created {len(created_users)} users:")
    for user_info in created_users:
        print(f"   - {user_info}")


def create_admin_user():
    """Create an admin user interactively"""
    print("👑 Creating admin user...")
    
    try:
        username = input('Enter admin username (default: admin): ').strip() or 'admin'
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"User {username} already exists")
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
                print('Passwords do not match')
        
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
        
        print(f"✅ Admin user {username} created successfully")
        
    except KeyboardInterrupt:
        print("❌ Admin user creation cancelled")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")


def show_current_status():
    """Show current database status"""
    print("\n📊 Current Database Status:")
    print(f"   Users: {User.objects.count()}")
    print(f"   Groups: {Group.objects.count()}")
    print(f"   Facilities: {Facility.objects.count()}")
    print(f"   Studies: {DicomStudy.objects.count()}")
    print(f"   Worklist Entries: {WorklistEntry.objects.count()}")
    
    print("\n👥 Users by group:")
    for group in Group.objects.all():
        users = group.user_set.all()
        print(f"   {group.name}: {[u.username for u in users]}")


def main():
    """Main function to replace test data with actual data"""
    print("🔄 Replacing test data with actual data...")
    print("=" * 50)
    
    # Show current status
    show_current_status()
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Clean all test data")
    print("2. Create actual facilities")
    print("3. Create actual users")
    print("4. Create admin user")
    print("5. Do everything (recommended)")
    print("6. Show current status only")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        clean_test_data()
    elif choice == '2':
        create_actual_facilities()
    elif choice == '3':
        create_actual_users()
    elif choice == '4':
        create_admin_user()
    elif choice == '5':
        print("\n🚀 Setting up everything...")
        clean_test_data()
        create_actual_facilities()
        create_actual_users()
        create_admin_user()
    elif choice == '6':
        pass  # Status already shown
    else:
        print("Invalid choice")
        return
    
    # Show final status
    print("\n" + "=" * 50)
    show_current_status()
    print("\n✅ Setup completed!")


if __name__ == '__main__':
    main()