#!/usr/bin/env python3
"""
Extract Ancient Greek inflection relationships using the correct template pattern
Based on {{inflection of|el|LEMMA|TAGS}} or {{inflection of|grc|LEMMA|TAGS}}
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

def extract_inflection_of_mappings(dump_path, output_path, max_pages=1000000):
    """Extract mappings using inflection_of template pattern"""
    print(f"=== EXTRACTING INFLECTION_OF MAPPINGS ===")
    print(f"Source: {dump_path}")
    print(f"Output: {output_path}")
    print(f"Max pages to process: {max_pages:,}")
    print()
    
    with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
        context = ET.iterparse(f, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        all_mappings = []
        pages_processed = 0
        pages_with_inflections = 0
        
        # Patterns to match inflection_of templates for Greek
        inflection_patterns = [
            # Modern Greek (el) and Ancient Greek (grc)
            r'\{\{inflection of\|el\|([^|]+)\|([^}]*)\}\}',
            r'\{\{inflection of\|grc\|([^|]+)\|([^}]*)\}\}',
            
            # Alternative formats
            r'\{\{inflection of\|lang=el\|([^|]+)\|([^}]*)\}\}',
            r'\{\{inflection of\|lang=grc\|([^|]+)\|([^}]*)\}\}',
        ]
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('page'):
                pages_processed += 1
                
                # Extract title and text
                title_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}title')
                text_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    text = text_elem.text or ''
                    
                    # Skip non-main namespace pages
                    if ':' in title:
                        elem.clear()
                        root.clear()
                        continue
                    
                    # Look for Greek content (either modern or ancient)
                    has_greek = ('==Greek==' in text or 
                               '==Ancient Greek==' in text or
                               any(pattern.split('|')[1] in ['el', 'grc'] for pattern in inflection_patterns 
                                   if re.search(pattern, text)))
                    
                    if not has_greek:
                        elem.clear()
                        root.clear()
                        continue
                    
                    title_normalized = normalize_greek(title)
                    
                    # Search for inflection_of patterns
                    for pattern in inflection_patterns:
                        matches = re.finditer(pattern, text)
                        for match in matches:
                            pages_with_inflections += 1
                            
                            # Extract lemma (first capture group)
                            lemma = match.group(1).strip()
                            tags = match.group(2).strip() if len(match.groups()) > 1 else ""
                            
                            # Clean up the lemma - remove any markup
                            lemma = re.sub(r'\[\[([^\]]+)\]\]', r'\1', lemma)  # Remove wiki links
                            lemma = re.sub(r'[{}]', '', lemma)  # Remove remaining template markup
                            lemma = lemma.strip()
                            
                            if lemma and title_normalized and lemma != title:
                                lemma_normalized = normalize_greek(lemma)
                                
                                # Skip if it's the same as the title (not an inflection)
                                if lemma_normalized != title_normalized:
                                    mapping = {
                                        'word_form': title_normalized,
                                        'lemma': lemma_normalized,
                                        'confidence': 1.0,
                                        'source': f'wiktionary:inflection_of',
                                        'tags': tags,
                                        'debug_pattern': match.group(0)[:100]  # For debugging
                                    }
                                    all_mappings.append(mapping)
                                    
                                    # Debug first few findings
                                    if len(all_mappings) <= 20:
                                        print(f"Found: {title} -> {lemma} (tags: {tags})")
                
                # Clear processed elements to save memory
                elem.clear()
                root.clear()
                
                # Progress indicator
                if pages_processed % 50000 == 0:
                    print(f"  Processed {pages_processed:,} pages, found {pages_with_inflections} with inflection_of, extracted {len(all_mappings):,} mappings")
                
                # Stop after max pages
                if pages_processed >= max_pages:
                    break
    
    print(f"\n✓ Extraction complete!")
    print(f"  Total pages processed: {pages_processed:,}")
    print(f"  Pages with inflection_of templates: {pages_with_inflections}")
    print(f"  Total mappings extracted: {len(all_mappings):,}")
    
    if len(all_mappings) == 0:
        print("\n❌ No mappings found - the template patterns may not exist in the dump")
        return False
    
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
        if mapping['word_form'] == 'μηνιν' or mapping['word_form'] == 'μῆνιν':
            menin_found = True
            print(f"  ✓ Found μῆνιν -> {mapping['lemma']}")
            break
    
    if not menin_found:
        print(f"  ⚠️  μῆνιν not found in extracted mappings")
    
    # Save to JSON file
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'source': 'English Wiktionary (Wikimedia Foundation)',
                'source_file': str(dump_path),
                'extraction_date': '2025-08-04',
                'license': 'Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)',
                'total_pages_processed': pages_processed,
                'pages_with_inflection_templates': pages_with_inflections,
                'total_mappings': len(final_mappings),
                'description': 'Greek inflection relationships extracted from {{inflection of}} templates'
            },
            'mappings': final_mappings
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(final_mappings):,} unique mappings to {output_path}")
    return True

if __name__ == "__main__":
    dump_file = "../../data-sources/enwiktionary-latest-pages-articles.xml.bz2"
    output_file = "greek_inflection_of_mappings.json"
    
    if Path(dump_file).exists():
        success = extract_inflection_of_mappings(dump_file, output_file)
        if success:
            print(f"\n🎉 Successfully extracted inflection_of mappings!")
        else:
            print(f"\n❌ No inflection_of mappings found")
    else:
        print("Dump file not found")