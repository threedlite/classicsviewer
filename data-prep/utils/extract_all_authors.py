#!/usr/bin/env python3
"""Extract all Greek author information from canonical-greekLit for reference"""

import xml.etree.ElementTree as ET
from pathlib import Path
import json

def extract_all_authors():
    """Extract all Greek authors with their names and work counts"""
    
    data_dir = Path("/home/user/git2/classicsviewer/data-sources/canonical-greekLit/data")
    authors = {}
    
    for author_dir in sorted(data_dir.iterdir()):
        if author_dir.is_dir() and author_dir.name.startswith("tlg"):
            cts_file = author_dir / "__cts__.xml"
            
            author_info = {
                "name": "Unknown",
                "works": 0,
                "has_translations": False
            }
            
            if cts_file.exists():
                try:
                    tree = ET.parse(cts_file)
                    root = tree.getroot()
                    
                    # Find groupname element
                    ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
                    groupname_elem = root.find('.//ti:groupname', ns)
                    
                    if groupname_elem is not None and groupname_elem.text:
                        author_info["name"] = groupname_elem.text.strip()
                except Exception as e:
                    print(f"Error parsing {cts_file}: {e}")
            
            # Count works
            for work_dir in author_dir.iterdir():
                if work_dir.is_dir() and work_dir.name.startswith("tlg"):
                    author_info["works"] += 1
                    
                    # Check for translations
                    for file in work_dir.iterdir():
                        if file.name.endswith("-eng") or "perseus-eng" in file.name:
                            author_info["has_translations"] = True
                            break
            
            authors[author_dir.name] = author_info
    
    # Save to JSON
    output_file = Path(__file__).parent.parent / "greek_authors_catalog.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(authors, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print(f"Found {len(authors)} Greek authors")
    print(f"\nAuthors with translations:")
    
    with_trans = [(k, v) for k, v in authors.items() if v["has_translations"]]
    for tlg_id, info in sorted(with_trans):
        print(f"  {tlg_id}: {info['name']} ({info['works']} works)")
    
    print(f"\nTotal with translations: {len(with_trans)}")
    
    # Generate Python dict for easy copy-paste
    print("\n\nPython dictionary format:")
    print("greek_authors = {")
    for tlg_id, info in sorted(authors.items()):
        print(f'    "{tlg_id}": "{info["name"]}",')
    print("}")

if __name__ == "__main__":
    extract_all_authors()