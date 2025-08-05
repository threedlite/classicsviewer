#!/usr/bin/env python3
"""
Extract Ancient Greek inflection mappings from Greek Wiktionary - Fixed version
"""

import xml.etree.ElementTree as ET
import re
import bz2
import json
import unicodedata
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    if not text:
        return ""
    # First normalize to NFD (decomposed form)
    text = unicodedata.normalize('NFD', text)
    # Remove diacritical marks
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Convert to lowercase
    text = text.lower()
    # Replace final sigma
    text = text.replace('ς', 'σ')
    # Remove punctuation (including Greek punctuation)
    # Keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def extract_greek_inflections_fixed(dump_path, output_path):
    """Extract Ancient Greek inflection mappings from Greek Wiktionary"""
    print(f"=== EXTRACTING ANCIENT GREEK INFLECTIONS FROM GREEK WIKTIONARY ===")
    print(f"Source: {dump_path}")
    print(f"Output: {output_path}")
    
    with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
        context = ET.iterparse(f, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        all_mappings = []
        pages_processed = 0
        inflection_pages = 0
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('page'):
                pages_processed += 1
                
                # Extract title and text
                title_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}title')
                text_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text or ''
                    text = text_elem.text or ''
                    
                    # Skip non-main namespace pages
                    if ':' in title:
                        elem.clear()
                        root.clear()
                        continue
                    
                    # Look for Ancient Greek section
                    if '=={{-grc-}}==' in text:
                        # Check if this is an inflection page
                        if '{{μορφή ουσιαστικού|grc}}' in text:
                            inflection_pages += 1
                            
                            # Pattern 1: {{κλ|grc|π=α|α=ε|μῆνις}} - last parameter is lemma
                            kl_match = re.search(r'{{\s*κλ\s*\|\s*grc\s*\|[^}]*\|([^}|]+)\s*}}', text)
                            if kl_match:
                                lemma = kl_match.group(1).strip()
                                word_form_normalized = normalize_greek(title)
                                lemma_normalized = normalize_greek(lemma)
                                
                                if word_form_normalized != lemma_normalized:
                                    mapping = {
                                        'word_form': word_form_normalized,
                                        'lemma': lemma_normalized,
                                        'confidence': 1.0,
                                        'source': 'elwiktionary:κλ',
                                        'debug_title': title,
                                        'debug_lemma': lemma
                                    }
                                    all_mappings.append(mapping)
                                    
                                    if len(all_mappings) <= 20:
                                        print(f"Found (κλ): {title} -> {lemma}")
                            else:
                                # Pattern 2: της λέξης [[μῆνις]]
                                lexis_match = re.search(r'της λέξης \[\[([^\]]+)\]\]', text)
                                if lexis_match:
                                    lemma = lexis_match.group(1).strip()
                                    word_form_normalized = normalize_greek(title)
                                    lemma_normalized = normalize_greek(lemma)
                                    
                                    if word_form_normalized != lemma_normalized:
                                        mapping = {
                                            'word_form': word_form_normalized,
                                            'lemma': lemma_normalized,
                                            'confidence': 1.0,
                                            'source': 'elwiktionary:λέξης',
                                            'debug_title': title,
                                            'debug_lemma': lemma
                                        }
                                        all_mappings.append(mapping)
                                        
                                        if len(all_mappings) <= 20:
                                            print(f"Found (λέξης): {title} -> {lemma}")
                
                # Clear processed elements to save memory
                elem.clear()
                root.clear()
                
                # Progress indicator
                if pages_processed % 50000 == 0:
                    print(f"  Processed {pages_processed:,} pages, found {inflection_pages} inflection pages, extracted {len(all_mappings):,} mappings")
    
    print(f"\n✓ Extraction complete!")
    print(f"  Total pages processed: {pages_processed:,}")
    print(f"  Inflection pages found: {inflection_pages}")
    print(f"  Total mappings extracted: {len(all_mappings):,}")
    
    # Deduplicate mappings
    print(f"\nDeduplicating mappings...")
    unique_mappings = {}
    
    for mapping in all_mappings:
        key = (mapping['word_form'], mapping['lemma'])
        if key not in unique_mappings:
            unique_mappings[key] = mapping
    
    final_mappings = list(unique_mappings.values())
    print(f"  Unique mappings after deduplication: {len(final_mappings):,}")
    
    # Check if we found μῆνιν specifically
    menin_found = False
    for mapping in final_mappings:
        if mapping['word_form'] == 'μηνιν':
            menin_found = True
            print(f"  ✓ Found μῆνιν -> {mapping['lemma']} ({mapping['debug_lemma']})")
            break
    
    if not menin_found:
        print(f"  ⚠️  μῆνιν not found in extracted mappings")
    
    # Save to JSON file
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'source': 'Greek Wiktionary (Wikimedia Foundation)',
                'source_file': str(dump_path),
                'extraction_date': '2025-08-04',
                'license': 'Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)',
                'total_pages_processed': pages_processed,
                'inflection_pages_found': inflection_pages,
                'total_mappings': len(final_mappings),
                'description': 'Ancient Greek inflection relationships extracted from Greek Wiktionary'
            },
            'mappings': final_mappings
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(final_mappings):,} unique mappings to {output_path}")
    
    # Show some sample mappings
    print(f"\nSample mappings:")
    for mapping in final_mappings[:20]:
        print(f"  {mapping['debug_title']} -> {mapping['debug_lemma']}")
    
    return True

if __name__ == "__main__":
    dump_file = "../../data-sources/elwiktionary-latest-pages-articles.xml.bz2"
    output_file = "ancient_greek_elwiktionary_mappings.json"
    
    if Path(dump_file).exists():
        success = extract_greek_inflections_fixed(dump_file, output_file)
        if success:
            print(f"\n🎉 Successfully extracted Ancient Greek inflection mappings from Greek Wiktionary!")
    else:
        print("Greek Wiktionary dump file not found")