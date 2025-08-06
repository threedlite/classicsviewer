#!/usr/bin/env python3
"""
Split compressed database into multiple parts for Play Asset Delivery.
Each part must be under 512MB for fast-follow delivery.
"""

import os
import sys
from pathlib import Path

def split_file(input_file, chunk_size_mb=450, output_dir=None):
    """
    Split a file into chunks of specified size.
    Using 450MB to leave margin under 512MB limit.
    """
    chunk_size = chunk_size_mb * 1024 * 1024  # Convert to bytes
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file {input_file} not found")
        return False
    
    # Use output_dir if specified, otherwise use input file's directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path.parent
    
    file_size = input_path.stat().st_size
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    
    print(f"Splitting {input_path.name}:")
    print(f"  File size: {file_size / (1024*1024):.1f} MB")
    print(f"  Chunk size: {chunk_size_mb} MB")
    print(f"  Total chunks: {total_chunks}")
    
    # Create manifest file with split info
    manifest = {
        'original_file': input_path.name,
        'total_size': file_size,
        'chunk_size': chunk_size,
        'total_chunks': total_chunks,
        'chunks': []
    }
    
    with open(input_path, 'rb') as infile:
        for i in range(total_chunks):
            chunk_name = f"{input_path.stem}.part{i+1:03d}"
            chunk_path = output_path / chunk_name
            
            # Read and write chunk
            chunk_data = infile.read(chunk_size)
            actual_size = len(chunk_data)
            
            with open(chunk_path, 'wb') as outfile:
                outfile.write(chunk_data)
            
            manifest['chunks'].append({
                'name': chunk_name,
                'index': i,
                'size': actual_size
            })
            
            print(f"  Created {chunk_name} ({actual_size / (1024*1024):.1f} MB)")
    
    # Write manifest
    import json
    manifest_path = output_path / f"{input_path.stem}.manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nSplit complete! Manifest written to {manifest_path}")
    return True

def verify_split(manifest_file):
    """Verify that split files can be reassembled correctly."""
    import json
    import hashlib
    
    manifest_path = Path(manifest_file)
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"Verifying split files from {manifest_file}")
    
    # Calculate hash of original file if it exists
    original_path = manifest_path.parent / manifest['original_file']
    original_hash = None
    if original_path.exists():
        print(f"Calculating hash of original file...")
        hasher = hashlib.sha256()
        with open(original_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        original_hash = hasher.hexdigest()
        print(f"Original hash: {original_hash}")
    
    # Calculate hash of reassembled chunks
    print(f"Calculating hash of {manifest['total_chunks']} chunks...")
    hasher = hashlib.sha256()
    total_size = 0
    
    for chunk_info in manifest['chunks']:
        chunk_path = manifest_path.parent / chunk_info['name']
        if not chunk_path.exists():
            print(f"Error: Missing chunk {chunk_info['name']}")
            return False
        
        with open(chunk_path, 'rb') as f:
            data = f.read()
            hasher.update(data)
            total_size += len(data)
    
    reassembled_hash = hasher.hexdigest()
    print(f"Reassembled hash: {reassembled_hash}")
    print(f"Total size: {total_size} bytes (expected: {manifest['total_size']})")
    
    if original_hash and original_hash == reassembled_hash:
        print("✓ Verification passed: hashes match!")
        return True
    elif total_size == manifest['total_size']:
        print("✓ Verification passed: sizes match!")
        return True
    else:
        print("✗ Verification failed!")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Split:  python3 split_database_for_assets.py split <input_file> [chunk_size_mb] [output_dir]")
        print("  Verify: python3 split_database_for_assets.py verify <manifest_file>")
        print("\nExample:")
        print("  python3 split_database_for_assets.py split perseus_texts.db.zip 450")
        print("  python3 split_database_for_assets.py verify perseus_texts.db.manifest.json")
        return
    
    command = sys.argv[1]
    
    if command == "split":
        if len(sys.argv) < 3:
            print("Error: Please specify input file")
            return
        
        input_file = sys.argv[2]
        chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 450
        output_dir = sys.argv[4] if len(sys.argv) > 4 else None
        
        split_file(input_file, chunk_size, output_dir)
    
    elif command == "verify":
        if len(sys.argv) < 3:
            print("Error: Please specify manifest file")
            return
        
        manifest_file = sys.argv[2]
        verify_split(manifest_file)
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()