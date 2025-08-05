#!/usr/bin/env python3
"""Test inflection extraction on a few known examples"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import unicodedata

def normalize_greek(text):
    """Normalize Greek text"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

# Test with a few words we know should have inflection info
test_words = ['ἀνδρός', 'ἄνδρα', 'θεοῦ', 'θεούς', 'λόγον', 'λόγους']
normalized_test = {normalize_greek(w): w for w in test_words}

print(f"Testing inflection extraction for: {test_words}")
print(f"Normalized forms: {list(normalized_test.keys())}")
print()

dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
found = 0
processed = 0

print("Starting scan...")
with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
    for event, elem in ET.iterparse(f, events=('start', 'end')):
        if event == 'end' and elem.tag.endswith('page'):
            processed += 1
            
            title_elem = elem.find('.//ns:title', namespace)
            text_elem = elem.find('.//ns:text', namespace)
            
            if title_elem is not None and text_elem is not None:
                title = title_elem.text
                normalized_title = normalize_greek(title)
                
                if normalized_title in normalized_test:
                    print(f"\n{'='*60}")
                    print(f"FOUND: {title} (normalized: {normalized_title})")
                    print(f"{'='*60}")
                    
                    text = text_elem.text or ''
                    
                    # Look for Ancient Greek section
                    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
                    if ag_match:
                        ag_section = ag_match.group(0)
                        print("\nAncient Greek section found!")
                        
                        # Look for inflection templates
                        inflection_matches = re.findall(r'\{\{inflection of[^}]+\}\}', ag_section)
                        if inflection_matches:
                            print(f"\nInflection templates found:")
                            for match in inflection_matches[:3]:
                                print(f"  {match}")
                        
                        # Look for form of templates
                        form_matches = re.findall(r'\{\{[^}]*form of[^}]+\}\}', ag_section)
                        if form_matches:
                            print(f"\nForm templates found:")
                            for match in form_matches[:3]:
                                print(f"  {match}")
                        
                        # Show first few lines of content
                        lines = ag_section.split('\n')[:20]
                        print(f"\nFirst lines of Ancient Greek section:")
                        for line in lines:
                            if line.strip():
                                print(f"  {line[:100]}")
                    
                    found += 1
                    if found >= 3:  # Stop after finding 3 examples
                        break
            
            elem.clear()
            
            if processed % 10000 == 0:
                print(f"  Processed {processed:,} pages...")
            
            if processed > 100000 and found == 0:
                print("\nNo test words found in first 100,000 pages. Stopping.")
                break

print(f"\n\nSummary: Found {found} out of {len(test_words)} test words")
print(f"Total pages processed: {processed:,}")