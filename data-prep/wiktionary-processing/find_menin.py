#!/usr/bin/env python3
"""Find specific inflected form pages"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import unicodedata

# Look for specific inflected forms we know exist
test_forms = ['μῆνιν', 'menin', 'Μῆνιν', 'ἄνδρα', 'ἀνδρός', 'θεοῦ', 'ἀνδρὸς']

dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
processed = 0
found_count = 0

print(f"Looking for inflected form pages: {test_forms}")
with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
    for event, elem in ET.iterparse(f, events=('start', 'end')):
        if event == 'end' and elem.tag.endswith('page'):
            processed += 1
            
            title_elem = elem.find('.//ns:title', namespace)
            text_elem = elem.find('.//ns:text', namespace)
            
            if title_elem is not None and text_elem is not None:
                title = title_elem.text
                
                # Check if it's one of our test forms (case-insensitive for Latin)
                if title in test_forms or title.lower() in [t.lower() for t in test_forms]:
                    print(f"\n{'='*80}")
                    print(f"FOUND PAGE: {title}")
                    print(f"{'='*80}")
                    
                    text = text_elem.text or ''
                    
                    # Show the first 100 lines or 5000 chars
                    lines = text.split('\n')
                    for i, line in enumerate(lines[:100]):
                        print(f"{i+1:3}: {line[:150]}")
                        if len('\n'.join(lines[:i+1])) > 5000:
                            break
                    
                    found_count += 1
                    if found_count >= 3:  # Stop after finding 3 examples
                        break
            
            elem.clear()
            
            if processed % 10000 == 0:
                print(f"  Processed {processed:,} pages...")

print(f"\nTotal pages processed: {processed:,}")