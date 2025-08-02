#!/usr/bin/env python3
import os
import sqlite3
import pydicom

def check_dicom_files():
    print("=" * 80)
    print("DICOM FILE CHECK (Without Django)")
    print("=" * 80)
    
    # Connect to SQLite database
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get DicomImage records
    try:
        cursor.execute("""
            SELECT id, file_path, instance_number, rows, columns, processed_image_cache
            FROM viewer_dicomimage
            ORDER BY id
            LIMIT 10
        """)
        images = cursor.fetchall()
        
        print(f"\nFound {len(images)} images in database")
        print("-" * 80)
        
        for img in images:
            img_id, file_path, instance_num, rows, cols, cache = img
            print(f"\nImage ID: {img_id}")
            print(f"File path: {file_path}")
            print(f"Instance: {instance_num}, Dimensions: {rows}x{cols}")
            print(f"Has cache: {'Yes' if cache else 'No'}")
            
            # Check if file exists
            if file_path:
                # Try different path combinations
                paths_to_try = [
                    file_path,
                    os.path.join('media', file_path),
                    os.path.join(os.getcwd(), 'media', file_path),
                    os.path.join(os.getcwd(), file_path)
                ]
                
                file_found = False
                for path in paths_to_try:
                    if os.path.exists(path):
                        print(f"✓ File found at: {path}")
                        file_found = True
                        
                        # Try to read it
                        try:
                            dcm = pydicom.dcmread(path)
                            print(f"  ✓ DICOM readable - Modality: {getattr(dcm, 'Modality', 'Unknown')}")
                            if hasattr(dcm, 'pixel_array'):
                                print(f"  ✓ Has pixel data")
                            else:
                                print(f"  ✗ No pixel data")
                        except Exception as e:
                            print(f"  ✗ Error reading DICOM: {e}")
                        break
                
                if not file_found:
                    print(f"✗ File not found in any location")
    
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()
    
    # List actual files in media/dicom_files
    print("\n" + "=" * 80)
    print("Files in media/dicom_files/:")
    dicom_dir = os.path.join('media', 'dicom_files')
    if os.path.exists(dicom_dir):
        for file in os.listdir(dicom_dir):
            print(f"  - {file}")
    else:
        print("  Directory not found!")

if __name__ == "__main__":
    check_dicom_files()