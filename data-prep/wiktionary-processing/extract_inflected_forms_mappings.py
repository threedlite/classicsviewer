#!/usr/bin/env python3
"""
Extract lemma mappings and morphology for ALL Greek words in the corpus.
This script looks for inflected form entries in Wiktionary that contain:
1. The lemma (base form) via {{inflection of}} or similar templates
2. Morphological information (case, number, tense, etc.)
3. Any definitions if available
"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import sqlite3
import unicodedata
import time
from datetime import datetime
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text - same as in main database creation"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def extract_inflection_info(title, text, normalized_title):
    """Extract lemma and morphology info from inflected form page"""
    
    # Look for Ancient Greek section
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
    if not ag_match:
        # Also check Greek section as some entries might be there
        ag_match = re.search(r'==Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
        if not ag_match:
            return None
    
    ag_section = ag_match.group(0)
    
    # Look for inflection_of templates
    inflection_patterns = [
        # Standard inflection_of template
        r'\{\{inflection of\|grc\|([^|]+)\|[^}]+\}\}',
        r'\{\{inflection of\|el\|([^|]+)\|[^}]+\}\}',
        r'\{\{infl of\|grc\|([^|]+)\|[^}]+\}\}',
        
        # Form of templates
        r'\{\{form of\|([^|]+)\|([^|]+)\|lang=grc[^}]*\}\}',
        r'\{\{inflected form of\|grc\|([^|]+)[^}]*\}\}',
        
        # Specific form templates
        r'\{\{nominative plural of\|grc\|([^}]+)\}\}',
        r'\{\{genitive (?:singular|plural) of\|grc\|([^}]+)\}\}',
        r'\{\{accusative (?:singular|plural) of\|grc\|([^}]+)\}\}',
        r'\{\{dative (?:singular|plural) of\|grc\|([^}]+)\}\}',
        r'\{\{vocative (?:singular|plural) of\|grc\|([^}]+)\}\}',
    ]
    
    lemma = None
    morphology = []
    
    for pattern in inflection_patterns:
        matches = re.findall(pattern, ag_section, re.IGNORECASE)
        if matches:
            if isinstance(matches[0], tuple):
                lemma = matches[0][1] if len(matches[0]) > 1 else matches[0][0]
            else:
                lemma = matches[0]
            
            # Extract morphological information from the template
            template_match = re.search(pattern.replace('([^|]+)', '.*?').replace('([^}]+)', '.*?'), ag_section)
            if template_match:
                template_text = template_match.group(0)
                # Extract tags between || delimiters
                tags = re.findall(r'\|([^|{}]+)', template_text)
                morphology = [tag for tag in tags if tag not in ['grc', 'el', lemma, 'lang=grc']]
            break
    
    if not lemma:
        # Try to find "inflected form of" or similar in plain text
        form_match = re.search(r'inflected form of\s+\[\[([^\]]+)\]\]', ag_section, re.IGNORECASE)
        if form_match:
            lemma = form_match.group(1)
        else:
            # Look for "form of" patterns
            form_match = re.search(r'(\w+)\s+(?:form|case|tense)\s+of\s+\[\[([^\]]+)\]\]', ag_section, re.IGNORECASE)
            if form_match:
                morphology.append(form_match.group(1).lower())
                lemma = form_match.group(2)
    
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

def process_wiktionary_for_inflections(dump_file, words_file, output_dir):
    """Process Wiktionary dump to extract inflection mappings"""
    
    # Load target words
    with open(words_file, 'r', encoding='utf-8') as f:
        corpus_words = json.load(f)
    
    target_set = set(corpus_words.keys())
    print(f"Looking for inflection info for {len(target_set):,} unique Greek words")
    
    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    found_mappings = {}
    processed_pages = 0
    start_time = time.time()
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"\nProcessing Wiktionary dump: {dump_file}")
    print("Looking for inflected form entries...")
    
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
                    normalized_title = normalize_greek(title)
                    
                    if normalized_title in target_set:
                        text = text_elem.text or ''
                        
                        # Look for inflection information
                        inflection_info = extract_inflection_info(title, text, normalized_title)
                        if inflection_info:
                            found_mappings[normalized_title] = inflection_info
                            
                            # Remove from target set
                            target_set.remove(normalized_title)
                            
                            # Progress update
                            if len(found_mappings) % 100 == 0:
                                elapsed = time.time() - start_time
                                rate = len(found_mappings) / elapsed
                                remaining = len(target_set) / rate if rate > 0 else 0
                                
                                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress:")
                                print(f"  Found: {len(found_mappings):,} mappings")
                                print(f"  Remaining: {len(target_set):,} words")
                                print(f"  Rate: {rate:.1f} mappings/second")
                                print(f"  Est. remaining: {remaining/3600:.1f} hours")
                                
                                # Show example
                                if inflection_info['morphology']:
                                    print(f"  Example: {title} → {inflection_info['lemma']} ({', '.join(inflection_info['morphology'][:3])})")
                            
                            # Save checkpoint every 1000 entries
                            if len(found_mappings) % 1000 == 0:
                                checkpoint_file = f"{output_dir}/inflection_checkpoint_{len(found_mappings)}.json"
                                with open(checkpoint_file, 'w', encoding='utf-8') as out:
                                    json.dump(found_mappings, out, ensure_ascii=False, indent=2)
                                print(f"  Saved checkpoint: {checkpoint_file}")
                
                elem.clear()
                
                # Status update every 10,000 pages
                if processed_pages % 10000 == 0:
                    print(f"  Processed {processed_pages:,} Wiktionary pages...")
    
    # Save final results
    final_file = f"{output_dir}/inflection_mappings_final.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(found_mappings, f, ensure_ascii=False, indent=2)
    
    # Summary
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed_total/3600:.1f} hours")
    print(f"Pages processed: {processed_pages:,}")
    print(f"Mappings found: {len(found_mappings):,}")
    print(f"Success rate: {len(found_mappings)/len(corpus_words)*100:.1f}%")
    print(f"Final output: {final_file}")
    
    # Show some statistics
    lemmas = {}
    for mapping in found_mappings.values():
        lemma = mapping['lemma_normalized']
        if lemma not in lemmas:
            lemmas[lemma] = 0
        lemmas[lemma] += 1
    
    print(f"\nUnique lemmas found: {len(lemmas):,}")
    print(f"Average forms per lemma: {len(found_mappings)/len(lemmas):.1f}")
    
    # Save words not found
    not_found = sorted(target_set)
    with open(f"{output_dir}/words_without_inflection_info.json", 'w', encoding='utf-8') as f:
        json.dump(not_found, f, ensure_ascii=False, indent=2)
    print(f"Words without inflection info: {len(not_found):,}")

def add_to_database(mappings_file, db_path='../perseus_texts.db'):
    """Add inflection mappings to database"""
    
    with open(mappings_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Update lemma_map table with better mappings
    updated = 0
    added = 0
    
    for norm_form, mapping in mappings.items():
        # Check if we already have this mapping
        cursor.execute("""
            SELECT lemma, confidence FROM lemma_map 
            WHERE word_form = ?
        """, (norm_form,))
        
        existing = cursor.fetchone()
        
        if existing and existing[1] < 0.9:  # Update if confidence is low
            cursor.execute("""
                UPDATE lemma_map 
                SET lemma = ?, confidence = 0.95, source = 'wiktionary_inflection'
                WHERE word_form = ?
            """, (mapping['lemma_normalized'], norm_form))
            updated += 1
        elif not existing:
            cursor.execute("""
                INSERT INTO lemma_map (word_form, lemma, confidence, source)
                VALUES (?, ?, 0.95, 'wiktionary_inflection')
            """, (norm_form, mapping['lemma_normalized']))
            added += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nDatabase update complete:")
    print(f"  Updated: {updated:,} mappings")
    print(f"  Added: {added:,} new mappings")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_inflected_forms_mappings.py <command>")
        print("Commands:")
        print("  extract - Extract inflection mappings from Wiktionary")
        print("  add     - Add extracted mappings to database")
        return
    
    command = sys.argv[1]
    
    if command == 'extract':
        dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
        words_file = 'all_greek_words_in_corpus.json'
        output_dir = 'inflection_extraction_results'
        
        process_wiktionary_for_inflections(dump_file, words_file, output_dir)
    
    elif command == 'add':
        mappings_file = 'inflection_extraction_results/inflection_mappings_final.json'
        if not Path(mappings_file).exists():
            print(f"Error: Mappings file not found at {mappings_file}")
            return
        
        add_to_database(mappings_file)

if __name__ == '__main__':
    main()