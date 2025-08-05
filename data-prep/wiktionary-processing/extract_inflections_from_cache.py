#!/usr/bin/env python3
"""
Extract inflection mappings from pre-extracted Greek pages cache.
This is MUCH faster than scanning the entire dump repeatedly.
"""

import json
import re
import unicodedata
import time
from datetime import datetime
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def extract_inflection_info(title, text):
    """Extract lemma and morphology info from page"""
    
    # Look for Ancient Greek section first, then Greek
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
    if not ag_match:
        ag_match = re.search(r'==Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
        if not ag_match:
            return None
    
    ag_section = ag_match.group(0)
    
    # Look for inflection_of templates
    inflection_patterns = [
        # Standard inflection_of template
        r'\{\{inflection of\|grc\|([^|]+)\|([^}]+)\}\}',
        r'\{\{inflection of\|el\|([^|]+)\|([^}]+)\}\}',
        r'\{\{infl of\|grc\|([^|]+)\|([^}]+)\}\}',
        
        # Form of templates
        r'\{\{form of\|([^|]+)\|([^|]+)\|lang=grc[^}]*\}\}',
        r'\{\{inflected form of\|grc\|([^|]+)[^}]*\}\}',
        
        # Specific form templates
        r'\{\{(nominative|genitive|dative|accusative|vocative) (?:singular|plural) of\|grc\|([^}]+)\}\}',
    ]
    
    lemma = None
    morphology = []
    
    for pattern in inflection_patterns:
        match = re.search(pattern, ag_section, re.IGNORECASE)
        if match:
            if 'inflection of' in pattern or 'infl of' in pattern:
                lemma = match.group(1)
                # Extract morphology from the tags section
                tags = match.group(2)
                morphology = [tag.strip() for tag in tags.split('|') if tag.strip() and tag.strip() != '']
            elif 'form of' in pattern:
                if match.lastindex >= 2:
                    lemma = match.group(2)
                else:
                    lemma = match.group(1)
            else:
                # Specific form templates
                case_info = match.group(1)
                lemma = match.group(2)
                morphology = [case_info]
            break
    
    if not lemma:
        return None
    
    # Clean lemma
    lemma = re.sub(r'[#|].*', '', lemma).strip()
    
    # Get part of speech if available
    pos_match = re.search(r'===(Noun|Verb|Adjective|Pronoun|Particle|Adverb|Preposition|Conjunction|Numeral|Interjection|Proper noun)===', ag_section)
    pos = pos_match.group(1).lower() if pos_match else None
    
    # Look for any definition
    definition = None
    if pos_match:
        definition_section = ag_section[pos_match.end():]
        for line in definition_section.split('\n'):
            if line.startswith('# ') and not line.startswith('##'):
                definition = line[2:].strip()
                # Clean wiki markup
                definition = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', definition)
                definition = re.sub(r'\[\[([^\]]+)\]\]', r'\1', definition)
                definition = re.sub(r"'''?", '', definition)
                definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
                break
    
    normalized_title = normalize_greek(title)
    
    return {
        'word_form': title,
        'word_form_normalized': normalized_title,
        'lemma': lemma,
        'lemma_normalized': normalize_greek(lemma),
        'pos': pos,
        'morphology': morphology,
        'definition': definition,
        'source': 'wiktionary'
    }

def process_greek_pages_for_corpus(greek_pages_file, corpus_words_file, output_dir):
    """Process pre-extracted Greek pages to find inflection mappings"""
    
    # Load corpus words
    print("Loading corpus words...")
    with open(corpus_words_file, 'r', encoding='utf-8') as f:
        corpus_words = json.load(f)
    
    target_set = set(corpus_words.keys())
    print(f"Looking for {len(target_set):,} unique Greek words")
    
    # Load Greek pages
    print("\nLoading pre-extracted Greek pages...")
    with open(greek_pages_file, 'r', encoding='utf-8') as f:
        greek_pages = json.load(f)
    
    print(f"Loaded {len(greek_pages):,} Greek pages")
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Process pages
    found_mappings = {}
    not_found = set(target_set)
    processed = 0
    start_time = time.time()
    
    print("\nProcessing pages...")
    for title, text in greek_pages.items():
        processed += 1
        normalized_title = normalize_greek(title)
        
        if normalized_title in target_set:
            inflection_info = extract_inflection_info(title, text)
            if inflection_info:
                found_mappings[normalized_title] = inflection_info
                not_found.discard(normalized_title)
                
                # Progress update
                if len(found_mappings) % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = len(found_mappings) / elapsed
                    
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress:")
                    print(f"  Found: {len(found_mappings):,} mappings")
                    print(f"  Remaining: {len(not_found):,} words")
                    print(f"  Rate: {rate:.1f} mappings/second")
                    
                    # Show example
                    if inflection_info['morphology']:
                        print(f"  Example: {title} → {inflection_info['lemma']} ({', '.join(inflection_info['morphology'][:3])})")
                
                # Save checkpoint every 1000 entries
                if len(found_mappings) % 1000 == 0:
                    checkpoint_file = f"{output_dir}/inflection_checkpoint_{len(found_mappings)}.json"
                    with open(checkpoint_file, 'w', encoding='utf-8') as out:
                        json.dump(found_mappings, out, ensure_ascii=False, indent=2)
                    print(f"  Saved checkpoint: {checkpoint_file}")
        
        if processed % 10000 == 0:
            print(f"  Processed {processed:,}/{len(greek_pages):,} Greek pages...")
    
    # Save final results
    final_file = f"{output_dir}/inflection_mappings_final.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(found_mappings, f, ensure_ascii=False, indent=2)
    
    # Summary
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Pages processed: {len(greek_pages):,}")
    print(f"Mappings found: {len(found_mappings):,}")
    print(f"Success rate: {len(found_mappings)/len(corpus_words)*100:.1f}%")
    print(f"Final output: {final_file}")
    
    # Save words not found
    not_found_list = sorted(not_found)
    with open(f"{output_dir}/words_without_inflection_info.json", 'w', encoding='utf-8') as f:
        json.dump(not_found_list, f, ensure_ascii=False, indent=2)
    print(f"Words without inflection info: {len(not_found_list):,}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_inflections_from_cache.py <command>")
        print("Commands:")
        print("  cache   - Extract all Greek pages to cache (run once)")
        print("  extract - Extract inflection mappings from cache")
        return
    
    command = sys.argv[1]
    
    if command == 'cache':
        import extract_all_greek_pages
        extract_all_greek_pages.main()
    
    elif command == 'extract':
        greek_pages_file = 'all_greek_wiktionary_pages.json'
        if not Path(greek_pages_file).exists():
            print(f"Error: Greek pages cache not found at {greek_pages_file}")
            print("Run 'python extract_inflections_from_cache.py cache' first")
            return
        
        corpus_words_file = 'all_greek_words_in_corpus.json'
        output_dir = 'inflection_extraction_results'
        
        process_greek_pages_for_corpus(greek_pages_file, corpus_words_file, output_dir)

if __name__ == '__main__':
    main()