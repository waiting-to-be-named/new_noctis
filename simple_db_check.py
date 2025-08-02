#!/usr/bin/env python3
import os
import sqlite3

def check_database():
    print("=" * 80)
    print("DATABASE IMAGE CHECK")
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
            SELECT id, file_path, instance_number, rows, columns, 
                   CASE WHEN processed_image_cache IS NOT NULL THEN 'Yes' ELSE 'No' END as has_cache,
                   CASE WHEN LENGTH(processed_image_cache) > 0 THEN LENGTH(processed_image_cache) ELSE 0 END as cache_size
            FROM viewer_dicomimage
            ORDER BY id DESC
            LIMIT 20
        """)
        images = cursor.fetchall()
        
        print(f"\nFound {len(images)} recent images in database")
        print("-" * 80)
        
        missing_files = 0
        found_files = 0
        
        for img in images:
            img_id, file_path, instance_num, rows, cols, has_cache, cache_size = img
            print(f"\nImage ID: {img_id}")
            print(f"  File path: {file_path}")
            print(f"  Dimensions: {rows}x{cols}")
            print(f"  Has cache: {has_cache} (size: {cache_size} bytes)")
            
            # Check if file exists
            if file_path:
                # Try different path combinations
                paths_to_try = [
                    os.path.join('media', file_path),
                    os.path.join('media', file_path.replace('\\', '/')),
                    file_path
                ]
                
                file_found = False
                for path in paths_to_try:
                    if os.path.exists(path):
                        print(f"  ✓ File EXISTS at: {path}")
                        file_found = True
                        found_files += 1
                        break
                
                if not file_found:
                    print(f"  ✗ File NOT FOUND")
                    missing_files += 1
                    
                    # Show what we tried
                    print(f"    Tried paths:")
                    for path in paths_to_try:
                        print(f"      - {path}")
        
        print("\n" + "=" * 80)
        print(f"SUMMARY:")
        print(f"  Total images checked: {len(images)}")
        print(f"  Files found: {found_files}")
        print(f"  Files missing: {missing_files}")
        
    except Exception as e:
        print(f"Error querying database: {e}")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%dicom%'")
        tables = cursor.fetchall()
        print(f"Available DICOM tables: {tables}")
    finally:
        conn.close()
    
    # List actual files in media/dicom_files
    print("\n" + "=" * 80)
    print("Actual files in media/dicom_files/:")
    dicom_dir = os.path.join('media', 'dicom_files')
    if os.path.exists(dicom_dir):
        files = os.listdir(dicom_dir)
        print(f"  Found {len(files)} files:")
        for file in files[:10]:  # Show first 10
            size = os.path.getsize(os.path.join(dicom_dir, file))
            print(f"    - {file} ({size/1024:.1f} KB)")
        if len(files) > 10:
            print(f"    ... and {len(files) - 10} more files")
    else:
        print("  Directory not found!")

if __name__ == "__main__":
    check_database()