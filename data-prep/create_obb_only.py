#!/usr/bin/env python3
"""Create OBB file from existing database"""

import shutil
from pathlib import Path

def main():
    # Database path
    db_path = Path("perseus_texts.db")
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create OBB file (just copy the database)
    obb_name = 'main.1.com.classicsviewer.app.debug.obb'
    shutil.copy(db_path, output_dir / obb_name)
    print(f"✓ Created: output/{obb_name}")
    
    # Also copy to data-prep root
    shutil.copy(db_path, Path(__file__).parent / obb_name)
    
    # Show file size
    size_mb = (output_dir / obb_name).stat().st_size / (1024 * 1024)
    print(f"✓ OBB file size: {size_mb:.1f} MB")
    
    print("\nTo deploy to device:")
    print(f"  adb push output/{obb_name} /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/")

if __name__ == "__main__":
    main()