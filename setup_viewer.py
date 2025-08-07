#!/usr/bin/env python3
"""
Setup script for DICOM Viewer system
This script helps initialize the system and creates test data if needed
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path
from datetime import date

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[96m",  # Cyan
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "RESET": "\033[0m"  # Reset
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['RESET']}")

def check_django_installation():
    """Check if Django is available"""
    try:
        import django
        print_status(f"Django {django.get_version()} is available", "SUCCESS")
        return True
    except ImportError:
        print_status("Django is not available", "ERROR")
        return False

def check_database():
    """Check database connectivity and content"""
    db_path = Path("db.sqlite3")
    if not db_path.exists():
        print_status("Database file does not exist", "ERROR")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'viewer_%';")
        tables = cursor.fetchall()
        
        if not tables:
            print_status("No viewer tables found in database", "ERROR")
            return False
        
        print_status(f"Found {len(tables)} viewer tables", "SUCCESS")
        
        # Check for studies
        try:
            cursor.execute("SELECT COUNT(*) FROM viewer_dicomstudy;")
            study_count = cursor.fetchone()[0]
            print_status(f"Found {study_count} studies in database", "SUCCESS" if study_count > 0 else "WARNING")
            
            cursor.execute("SELECT COUNT(*) FROM viewer_dicomimage;")
            image_count = cursor.fetchone()[0]
            print_status(f"Found {image_count} images in database", "SUCCESS" if image_count > 0 else "WARNING")
            
        except sqlite3.OperationalError as e:
            print_status(f"Error querying database: {e}", "ERROR")
            return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print_status(f"Database error: {e}", "ERROR")
        return False

def install_dependencies():
    """Install required dependencies"""
    print_status("Installing dependencies...", "INFO")
    
    try:
        # Try to install in a virtual environment
        subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", 
                       "django", "pydicom", "pillow", "djangorestframework"], 
                      check=True, capture_output=True)
        print_status("Dependencies installed successfully", "SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to install dependencies: {e}", "ERROR")
        return False

def create_test_data():
    """Create sample data if database is empty"""
    print_status("Creating sample medical data...", "INFO")
    
    try:
        from worklist.models import Study, Series, DICOMImage
        
        # Check if data already exists
        if Study.objects.exists():
            print_status("Sample data already exists", "INFO")
            return True
        
        # Create a sample study if none exists
        study = Study.objects.create(
            study_instance_uid="1.2.826.0.1.3680043.2.1125.1.12345678901234567890123456789012",
            patient_name="Smith, John M",
            patient_id="MRN789456",
            patient_birth_date=date(1975, 3, 15),
            accession_number="ACC2024001234",
            study_description="CT Chest with Contrast",
            study_date=date.today(),
            institution_name="General Medical Center"
        )
        
        # Create a sample series
        series = Series.objects.create(
            study=study,
            series_instance_uid="1.2.826.0.1.3680043.2.1125.2.12345678901234567890123456789012",
            series_number=1,
            series_description="Axial CT Chest",
            modality="CT"
        )
        
        # Create a sample image
        dicom_image = DICOMImage.objects.create(
            series=series,
            sop_instance_uid="1.2.826.0.1.3680043.2.1125.3.12345678901234567890123456789012",
            instance_number=1,
            slice_location=0.0,
            image_position_patient="0.0\\0.0\\0.0",
            image_orientation_patient="1.0\\0.0\\0.0\\0.0\\1.0\\0.0",
            pixel_spacing="0.976562\\0.976562",
            slice_thickness=5.0,
            rows=512,
            columns=512,
            bits_allocated=16,
            bits_stored=12,
            high_bit=11
        )
        
        print_status("Sample medical data created successfully", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"Failed to create sample data: {e}", "ERROR")
        return False

def start_server():
    """Start the Django development server"""
    print_status("Starting Django development server...", "INFO")
    
    try:
        # Run server in background
        process = subprocess.Popen([
            sys.executable, "manage.py", "runserver", "127.0.0.1:8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print_status("Server started on http://127.0.0.1:8000", "SUCCESS")
        print_status("Press Ctrl+C to stop the server", "INFO")
        
        return process
        
    except Exception as e:
        print_status(f"Failed to start server: {e}", "ERROR")
        return None

def main():
    """Main setup function"""
    print_status("=== DICOM Viewer Setup ===", "INFO")
    
    # Check Django installation
    if not check_django_installation():
        print_status("Attempting to install dependencies...", "INFO")
        if not install_dependencies():
            print_status("Setup failed: Could not install Django", "ERROR")
            return False
    
    # Check database
    db_ok = check_database()
    
    if check_django_installation():
        # Create test data if needed
        if not db_ok or True:  # Always try to ensure test data exists
            create_test_data()
    
    print_status("\n=== Setup Summary ===", "INFO")
    print_status("1. Open your web browser", "INFO")
    print_status("2. Navigate to: http://127.0.0.1:8000/viewer/", "INFO")
    print_status("3. Or use the diagnostic page: dicom_viewer_test.html", "INFO")
    print_status("4. Check the debug panel in the bottom left", "INFO")
    
    # Ask user if they want to start the server
    response = input("\nStart Django server now? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        server_process = start_server()
        if server_process:
            try:
                server_process.wait()
            except KeyboardInterrupt:
                print_status("\nShutting down server...", "INFO")
                server_process.terminate()
                server_process.wait()
    
    print_status("Setup complete!", "SUCCESS")
    return True

if __name__ == "__main__":
    main()