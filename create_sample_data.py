#!/usr/bin/env python3
"""
Simple script to create sample DICOM worklist data for testing
"""
import sqlite3
import datetime

def create_sample_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('/workspace/db.sqlite3')
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    print("Available tables:", [table[0] for table in tables])
    
    # Check if we have any worklist entries
    try:
        cursor.execute("SELECT COUNT(*) FROM viewer_worklistentry;")
        count = cursor.fetchone()[0]
        print(f"Current worklist entries: {count}")
        
        if count == 0:
            print("Creating sample worklist entries...")
            
            # Get current date
            today = datetime.date.today()
            
            # Sample data
            sample_entries = [
                ('John Smith', 'JS001', 'ACC001', 'CT', 'scheduled', today.strftime('%Y-%m-%d'), '09:00:00'),
                ('Mary Johnson', 'MJ002', 'ACC002', 'MR', 'in-progress', today.strftime('%Y-%m-%d'), '10:30:00'),
                ('Robert Davis', 'RD003', 'ACC003', 'CR', 'completed', (today - datetime.timedelta(days=1)).strftime('%Y-%m-%d'), '14:15:00'),
                ('Sarah Wilson', 'SW004', 'ACC004', 'US', 'scheduled', today.strftime('%Y-%m-%d'), '11:45:00'),
                ('Michael Brown', 'MB005', 'ACC005', 'MG', 'scheduled', (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d'), '08:30:00'),
            ]
            
            # Insert sample entries
            for entry in sample_entries:
                cursor.execute("""
                    INSERT INTO viewer_worklistentry 
                    (patient_name, patient_id, accession_number, modality, status, 
                     scheduled_procedure_step_start_date, scheduled_procedure_step_start_time,
                     created_at, updated_at, facility_id, study_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), NULL, NULL)
                """, entry)
            
            print(f"Inserted {len(sample_entries)} sample entries")
            
        # Check for DICOM studies
        cursor.execute("SELECT COUNT(*) FROM viewer_dicomstudy;")
        study_count = cursor.fetchone()[0]
        print(f"Current DICOM studies: {study_count}")
        
        if study_count == 0:
            print("Creating sample DICOM studies...")
            
            # Create sample studies
            sample_studies = [
                ('Study 1', 'ST001', 'John Smith', 'JS001', 'CT Chest', today.strftime('%Y-%m-%d')),
                ('Study 2', 'ST002', 'Mary Johnson', 'MJ002', 'MR Brain', today.strftime('%Y-%m-%d')),
                ('Study 3', 'ST003', 'Robert Davis', 'RD003', 'CR Chest', (today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')),
            ]
            
            for study in sample_studies:
                cursor.execute("""
                    INSERT INTO viewer_dicomstudy 
                    (study_instance_uid, study_id, patient_name, patient_id, study_description,
                     study_date, created_at, updated_at, total_images)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 10)
                """, study)
            
            print(f"Inserted {len(sample_studies)} sample studies")
        
        # Commit changes
        conn.commit()
        print("Sample data creation completed!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    create_sample_data()