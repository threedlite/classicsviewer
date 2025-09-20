#!/usr/bin/env python3
"""
Fixed version of inflection_of template extraction
Uses cached Greek pages for fast processing
"""

import json
from pathlib import Path
import re

def extract_inflection_of_mappings(input_path, output_path):
    """Extract mappings using inflection_of template pattern from cached pages"""
    print(f"=== EXTRACTING INFLECTION_OF MAPPINGS ===")
    print(f"Source: {input_path}")
    print(f"Output: {output_path}")
    
    # Load cached Greek pages
    with open(input_path, 'r', encoding='utf-8') as f:
        all_pages = json.load(f)
    
    print(f"Processing {len(all_pages):,} Greek pages...")
    
    all_mappings = []
    pages_with_inflections = 0
    
    # Patterns to match inflection_of templates for Greek
    inflection_patterns = [
        # {{inflection of|grc|LEMMA||TAGS}}
        r'\{\{inflection of\|grc\|([^|]+)\|\|([^}]+)\}\}',
        # {{inflection of|el|LEMMA||TAGS}}  
        r'\{\{inflection of\|el\|([^|]+)\|\|([^}]+)\}\}',
        # {{infl of|grc|LEMMA||TAGS}}
        r'\{\{infl of\|grc\|([^|]+)\|\|([^}]+)\}\}',
        # Older format: {{inflection of|LEMMA||TAGS|lang=grc}}
        r'\{\{inflection of\|([^|]+)\|\|([^}]+)\|lang=grc\}\}'
    ]
    
    # Process each page
    for page_num, (title, text) in enumerate(all_pages.items()):
        if page_num % 10000 == 0:
            print(f"  Processed {page_num:,} pages, found {pages_with_inflections:,} with inflections...")
        
        # Skip non-Ancient Greek pages (modern Greek has lowercase)
        if not any('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff' for c in title):
            continue
            
        found_inflection = False
        
        for pattern in inflection_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                lemma = match[0].strip()
                tags = match[1].strip()
                
                # Skip if lemma contains templates or links
                if '{{' in lemma or '[[' in lemma:
                    continue
                
                # Parse grammatical info from tags
                tag_parts = [t.strip() for t in tags.split('|')]
                morph_info = ' '.join(tag_parts)
                
                all_mappings.append({
                    'word_form': title,
                    'lemma': lemma,
                    'morph_type': 'inflection',
                    'morph_info': morph_info,
                    'source': 'inflection_of',
                    'debug_form': title,
                    'debug_title': title
                })
                found_inflection = True
        
        if found_inflection:
            pages_with_inflections += 1
    
    print(f"\n✓ Extraction complete!")
    print(f"  Total pages processed: {len(all_pages):,}")
    print(f"  Pages with inflection_of: {pages_with_inflections:,}")
    print(f"  Total mappings found: {len(all_mappings):,}")
    
    # Deduplicate
    unique_mappings = {}
    for mapping in all_mappings:
        key = (mapping['word_form'], mapping['lemma'])
        if key not in unique_mappings:
            unique_mappings[key] = mapping
    
    final_mappings = list(unique_mappings.values())
    
    # Save as expected format
    output_data = {
        'mappings': final_mappings,
        'metadata': {
            'source': 'Wiktionary inflection_of templates',
            'total_mappings': len(final_mappings)
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(final_mappings):,} unique mappings to {output_path}")
    return True

def main():
    """Main function for use by other scripts"""
    # Use cached Greek pages
    cache_file = Path(__file__).parent / "all_greek_wiktionary_pages.json"
    output_file = Path(__file__).parent / "extract_inflection_of_template.json"
    
    if not cache_file.exists():
        print(f"ERROR: Required cache file {cache_file} not found!")
        raise FileNotFoundError(f"Greek pages cache required: {cache_file}")
    
    # Extract from cache
    success = extract_inflection_of_mappings(str(cache_file), str(output_file))
    if not success:
        raise RuntimeError("Failed to extract inflection_of mappings")
    
    print(f"\n✓ Successfully extracted inflection_of mappings!")
    return success

if __name__ == "__main__":
    main()