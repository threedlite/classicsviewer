#!/usr/bin/env python3
"""
Create ZIM file from optimized content directory.
"""

import os
import sys
from pathlib import Path
from libzim.writer import Creator, Item, StringProvider, Hint
from datetime import datetime
import argparse

class HTMLItem(Item):
    """Custom Item class for HTML content."""
    def __init__(self, path, title, content):
        super().__init__()
        self._path = path
        self._title = title if title else ""
        self._content = content
        self._mimetype = self._determine_mimetype()
    
    def _determine_mimetype(self):
        """Determine MIME type based on file extension."""
        if self._path.endswith('.html'):
            return 'text/html'
        elif self._path.endswith('.css'):
            return 'text/css'
        elif self._path.endswith('.js'):
            return 'application/javascript'
        elif self._path.endswith('.json'):
            return 'application/json'
        elif self._path.endswith('.png'):
            return 'image/png'
        elif self._path.endswith('.jpg') or self._path.endswith('.jpeg'):
            return 'image/jpeg'
        elif self._path.endswith('.svg'):
            return 'image/svg+xml'
        else:
            return 'application/octet-stream'
    
    def get_path(self):
        return self._path
    
    def get_title(self):
        return self._title
    
    def get_mimetype(self):
        return self._mimetype
    
    def get_contentprovider(self):
        return StringProvider(content=self._content)
    
    def get_hints(self):
        # Return hints about the item (e.g., should it be indexed)
        hints = {}
        if self._path.endswith('.html'):
            hints[Hint.FRONT_ARTICLE] = True
        return hints

def build_zim(content_dir="zim_content_optimized", output_file="perseus_sample.zim"):
    """Build ZIM file from HTML content."""
    content_path = Path(content_dir)
    
    if not content_path.exists():
        print(f"Error: Content directory '{content_path}' not found!")
        return 1
    
    print(f"Building ZIM file: {output_file}")
    print(f"Content directory: {content_path}")
    
    # Collect all files
    files = []
    for file_path in content_path.rglob('*'):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(content_path))
            # Convert backslashes to forward slashes for Windows compatibility
            rel_path = rel_path.replace('\\', '/')
            if not rel_path.startswith('.'):
                files.append((rel_path, file_path))
    
    files.sort()
    print(f"Found {len(files)} files to add")
    
    # Create and configure the creator before starting
    creator = Creator(filename=output_file)
    creator.config_verbose(True)
    creator.config_compression('zstd')
    creator.config_clustersize(2048)
    
    # Use creator within context manager
    with creator:
        
        # Determine if this is sample or full based on output filename
        is_sample = "sample" in output_file.lower()
        title_suffix = " (Sample)" if is_sample else " (Full)"
        desc_suffix = " - Sample with 12 authors" if is_sample else " - Full collection with 100+ authors"
        
        # Add metadata
        creator.add_metadata("Title", f"Classics Viewer{title_suffix}")
        creator.add_metadata("Description", f"Greek and Latin classical texts with dictionary{desc_suffix}")
        creator.add_metadata("Language", "mul")  # Multiple languages
        creator.add_metadata("Date", datetime.now().strftime("%Y-%m-%d"))
        creator.add_metadata("Creator", "Perseus Digital Library")
        creator.add_metadata("Publisher", "Perseus Digital Library")
        
        # Set main page
        creator.set_mainpath("index.html")
        
        # Add all content files
        added = 0
        for rel_path, file_path in files:
            try:
                # Read file content
                content = file_path.read_bytes()
                
                # Create and add item
                item = HTMLItem(path=rel_path, title="", content=content)
                creator.add_item(item)
                added += 1
                
                if added % 1000 == 0:
                    print(f"  Added {added}/{len(files)} files...")
                    
            except Exception as e:
                print(f"Error adding {rel_path}: {e}")
        
        print(f"Added {added} files total")
        print("Creating ZIM file...")
    
    # Check if file was created
    if Path(output_file).exists():
        size_mb = Path(output_file).stat().st_size / (1024 * 1024)
        print(f"Successfully created {output_file} ({size_mb:.1f} MB)")
        return 0
    else:
        print(f"Error: Failed to create {output_file}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='Create ZIM file from content directory')
    parser.add_argument('--input', default='zim_content_optimized', help='Input content directory')
    parser.add_argument('--output', default='perseus_sample.zim', help='Output ZIM file')
    args = parser.parse_args()
    
    return build_zim(args.input, args.output)

if __name__ == "__main__":
    sys.exit(main())