#!/usr/bin/env python3
"""Scan for Greek pages to understand structure"""

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

def is_greek_word(title):
    """Check if title contains Greek characters"""
    return any('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff' for c in title)

dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
greek_pages = []
processed = 0

print("Scanning for Greek pages...")
with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
    for event, elem in ET.iterparse(f, events=('start', 'end')):
        if event == 'end' and elem.tag.endswith('page'):
            processed += 1
            
            title_elem = elem.find('.//ns:title', namespace)
            text_elem = elem.find('.//ns:text', namespace)
            
            if title_elem is not None and text_elem is not None:
                title = title_elem.text
                
                if is_greek_word(title) and ':' not in title:
                    text = text_elem.text or ''
                    
                    # Check what sections it has
                    has_ancient_greek = '==Ancient Greek==' in text
                    has_greek = '==Greek==' in text
                    has_inflection_of = 'inflection of' in text.lower()
                    has_form_of = 'form of' in text.lower()
                    
                    greek_pages.append({
                        'title': title,
                        'normalized': normalize_greek(title),
                        'has_ancient_greek': has_ancient_greek,
                        'has_greek': has_greek,
                        'has_inflection_of': has_inflection_of,
                        'has_form_of': has_form_of
                    })
                    
                    if len(greek_pages) >= 50:  # Get 50 examples
                        break
            
            elem.clear()
            
            if processed % 10000 == 0:
                print(f"  Processed {processed:,} pages...")

print(f"\n\nFound {len(greek_pages)} Greek pages")
print("\nExamples:")
for page in greek_pages[:20]:
    flags = []
    if page['has_ancient_greek']: flags.append('AG')
    if page['has_greek']: flags.append('G')
    if page['has_inflection_of']: flags.append('INFL')
    if page['has_form_of']: flags.append('FORM')
    
    print(f"{page['title']:20} [{', '.join(flags)}]")

# Statistics
ag_count = sum(1 for p in greek_pages if p['has_ancient_greek'])
g_count = sum(1 for p in greek_pages if p['has_greek'])
infl_count = sum(1 for p in greek_pages if p['has_inflection_of'])
form_count = sum(1 for p in greek_pages if p['has_form_of'])

print(f"\nStatistics:")
print(f"  With Ancient Greek section: {ag_count}/{len(greek_pages)}")
print(f"  With Greek section: {g_count}/{len(greek_pages)}")
print(f"  With 'inflection of': {infl_count}/{len(greek_pages)}")
print(f"  With 'form of': {form_count}/{len(greek_pages)}")