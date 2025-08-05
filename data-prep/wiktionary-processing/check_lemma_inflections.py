#!/usr/bin/env python3
"""Check if lemma pages contain inflected forms"""

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

# Look for specific lemmas we know have inflections
test_lemmas = ['ἀνήρ', 'θεός', 'λόγος', 'ἄνθρωπος']

dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
processed = 0

print(f"Looking for lemma pages: {test_lemmas}")
with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
    for event, elem in ET.iterparse(f, events=('start', 'end')):
        if event == 'end' and elem.tag.endswith('page'):
            processed += 1
            
            title_elem = elem.find('.//ns:title', namespace)
            text_elem = elem.find('.//ns:text', namespace)
            
            if title_elem is not None and text_elem is not None:
                title = title_elem.text
                
                if title in test_lemmas:
                    print(f"\n{'='*80}")
                    print(f"FOUND LEMMA: {title}")
                    print(f"{'='*80}")
                    
                    text = text_elem.text or ''
                    
                    # Look for Ancient Greek section
                    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
                    if ag_match:
                        ag_section = ag_match.group(0)
                        
                        # Look for inflection/declension tables
                        if '{{grc-decl' in ag_section or '{{Ancient Greek' in ag_section:
                            print("\nDeclension template found!")
                            
                            # Extract template
                            decl_matches = re.findall(r'\{\{[^}]*decl[^}]+\}\}', ag_section)
                            for match in decl_matches[:2]:
                                print(f"  Template: {match}")
                        
                        # Look for inflection section
                        if '===Inflection===' in ag_section or '===Declension===' in ag_section:
                            print("\nInflection/Declension section found!")
                            
                            # Get the section
                            infl_match = re.search(r'===(?:Inflection|Declension)===.*?(?=\n===|\Z)', ag_section, re.DOTALL)
                            if infl_match:
                                infl_section = infl_match.group(0)
                                lines = infl_section.split('\n')[:20]
                                print("Content preview:")
                                for line in lines:
                                    if line.strip():
                                        print(f"  {line[:100]}")
                        
                        # Look for our test inflected forms
                        test_forms = ['ἀνδρός', 'ἄνδρα', 'θεοῦ', 'θεούς', 'λόγον', 'λόγους']
                        found_forms = []
                        for form in test_forms:
                            if form in ag_section:
                                found_forms.append(form)
                        
                        if found_forms:
                            print(f"\nFound inflected forms in page: {found_forms}")
            
            elem.clear()
            
            if processed % 10000 == 0:
                print(f"  Processed {processed:,} pages...")
            
            if processed > 500000:
                break

print(f"\nTotal pages processed: {processed:,}")