#!/usr/bin/env python3
"""
Extract ALL Greek pages from Wiktionary dump into a smaller JSON file.
This will be much faster to search through multiple times.
"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import time
from datetime import datetime
from pathlib import Path

def is_greek_word(title):
    """Check if title contains Greek characters"""
    return any('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff' for c in title)

def extract_all_greek_pages(dump_file, output_file):
    """Extract all Greek pages from Wiktionary dump"""
    
    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    greek_pages = {}
    processed_pages = 0
    start_time = time.time()
    
    print(f"Extracting all Greek pages from Wiktionary dump...")
    print(f"Source: {dump_file}")
    print(f"Output: {output_file}")
    print()
    
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
        for event, elem in ET.iterparse(f, events=('start', 'end')):
            if event == 'end' and elem.tag.endswith('page'):
                processed_pages += 1
                
                title_elem = elem.find('.//ns:title', namespace)
                text_elem = elem.find('.//ns:text', namespace)
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    
                    # Skip non-main namespace
                    if ':' in title and not title.startswith('Reconstruction:'):
                        elem.clear()
                        continue
                    
                    # Check if Greek word
                    if is_greek_word(title):
                        text = text_elem.text or ''
                        
                        # Only include pages with Ancient Greek or Greek sections
                        if '==Ancient Greek==' in text or '==Greek==' in text:
                            greek_pages[title] = text
                            
                            if len(greek_pages) % 1000 == 0:
                                elapsed = time.time() - start_time
                                rate = processed_pages / elapsed
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress:")
                                print(f"  Pages processed: {processed_pages:,}")
                                print(f"  Greek pages found: {len(greek_pages):,}")
                                print(f"  Rate: {rate:.0f} pages/second")
                                print(f"  Latest: {title}")
                
                elem.clear()
                
                # Status update every 100,000 pages
                if processed_pages % 100000 == 0:
                    print(f"  Processed {processed_pages:,} Wiktionary pages...")
    
    # Save results
    print(f"\nSaving {len(greek_pages):,} Greek pages to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(greek_pages, f, ensure_ascii=False, indent=2)
    
    # Summary
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Pages processed: {processed_pages:,}")
    print(f"Greek pages extracted: {len(greek_pages):,}")
    print(f"Processing rate: {processed_pages/elapsed_total:.0f} pages/second")
    print(f"Output file: {output_file} ({Path(output_file).stat().st_size / 1024 / 1024:.1f} MB)")

def main():
    dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
    output_file = 'all_greek_wiktionary_pages.json'
    
    extract_all_greek_pages(dump_file, output_file)

if __name__ == '__main__':
    main()