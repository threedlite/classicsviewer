#!/usr/bin/env python3
"""
Extract Wiktionary definitions for ALL Greek words in the corpus.
This is a comprehensive extraction that will take several hours.
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

def extract_wiktionary_definition(title, text, normalized_title):
    """Extract a concise definition from Wiktionary page text"""
    
    # Look for Ancient Greek section
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
    if not ag_match:
        return None
    
    ag_section = ag_match.group(0)
    
    # Find part of speech
    pos_match = re.search(r'===(Noun|Verb|Adjective|Pronoun|Particle|Adverb|Preposition|Conjunction|Numeral|Interjection|Proper noun)===', ag_section)
    if not pos_match:
        # Try alternative format
        pos_match = re.search(r'{{head\|grc\|(noun|verb|adjective|pronoun|particle|adverb|preposition|conjunction|numeral|interjection|proper noun)', ag_section)
        if not pos_match:
            return None
    
    pos = pos_match.group(1).lower()
    
    # Extract first few definitions
    definitions = []
    definition_section = ag_section[pos_match.end():]
    
    for line in definition_section.split('\n'):
        if line.startswith('# ') and not line.startswith('##'):
            # Clean the definition
            defn = line[2:].strip()
            
            # Remove wiki markup
            defn = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', defn)
            defn = re.sub(r'\[\[([^\]]+)\]\]', r'\1', defn)
            defn = re.sub(r"'''?", '', defn)
            defn = re.sub(r'\{\{[^}]+\}\}', '', defn)
            defn = re.sub(r'\([^)]*\)', '', defn).strip()
            
            if defn and len(defn) > 3:
                definitions.append(defn)
                
        if len(definitions) >= 2:  # Limit to 2 definitions for space
            break
    
    if not definitions:
        return None
    
    # Format as simple HTML entry
    html_entry = f'<div class="wiktionary-entry">'
    html_entry += f'<b>{title}</b>, {pos}. '
    
    if len(definitions) == 1:
        html_entry += definitions[0]
    else:
        html_entry += ' '.join([f'({i+1}) {d}' for i, d in enumerate(definitions)])
    
    html_entry += ' <i>[Wikt.]</i></div>'
    
    # Plain text version
    plain_entry = f'{title}, {pos}. ' + '; '.join(definitions) + ' [Wiktionary]'
    
    return {
        'headword': title,
        'headword_normalized': normalized_title,
        'language': 'greek',
        'entry_html': html_entry,
        'entry_plain': plain_entry[:400],  # Limit length
        'entry_xml': None,
        'source': 'wiktionary'
    }

def process_wiktionary_comprehensive(dump_file, words_file, output_dir):
    """Process entire Wiktionary dump for all corpus words"""
    
    # Load target words
    with open(words_file, 'r', encoding='utf-8') as f:
        corpus_words = json.load(f)
    
    target_set = set(corpus_words.keys())
    print(f"Looking for {len(target_set):,} unique Greek words in Wiktionary")
    
    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    found_entries = {}
    processed_pages = 0
    start_time = time.time()
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"\nProcessing Wiktionary dump: {dump_file}")
    print("This will take several hours...")
    
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
                        
                        if '==Ancient Greek==' in text or '== Ancient Greek ==' in text:
                            entry = extract_wiktionary_definition(title, text, normalized_title)
                            if entry:
                                found_entries[normalized_title] = entry
                                
                                # Remove from target set
                                target_set.remove(normalized_title)
                                
                                # Progress update
                                if len(found_entries) % 100 == 0:
                                    elapsed = time.time() - start_time
                                    rate = len(found_entries) / elapsed
                                    remaining = len(target_set) / rate if rate > 0 else 0
                                    
                                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress:")
                                    print(f"  Found: {len(found_entries):,} entries")
                                    print(f"  Remaining: {len(target_set):,} words")
                                    print(f"  Rate: {rate:.1f} entries/second")
                                    print(f"  Est. remaining: {remaining/3600:.1f} hours")
                                
                                # Save checkpoint every 1000 entries
                                if len(found_entries) % 1000 == 0:
                                    checkpoint_file = f"{output_dir}/wiktionary_checkpoint_{len(found_entries)}.json"
                                    with open(checkpoint_file, 'w', encoding='utf-8') as out:
                                        json.dump(found_entries, out, ensure_ascii=False, indent=2)
                                    print(f"  Saved checkpoint: {checkpoint_file}")
                
                elem.clear()
                
                # Status update every 10,000 pages
                if processed_pages % 10000 == 0:
                    print(f"  Processed {processed_pages:,} Wiktionary pages...")
    
    # Save final results
    final_file = f"{output_dir}/wiktionary_definitions_final.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(found_entries, f, ensure_ascii=False, indent=2)
    
    # Summary
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed_total/3600:.1f} hours")
    print(f"Pages processed: {processed_pages:,}")
    print(f"Entries found: {len(found_entries):,}")
    print(f"Success rate: {len(found_entries)/len(corpus_words)*100:.1f}%")
    print(f"Final output: {final_file}")
    
    # Save list of words not found
    not_found = sorted(target_set)
    with open(f"{output_dir}/words_not_found.json", 'w', encoding='utf-8') as f:
        json.dump(not_found, f, ensure_ascii=False, indent=2)
    print(f"Words not found: {len(not_found):,} (saved to words_not_found.json)")

def add_to_database(definitions_file, db_path='../perseus_texts.db'):
    """Add all extracted definitions to database"""
    
    with open(definitions_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, check how many we already have
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE source = 'wiktionary'")
    before_count = cursor.fetchone()[0]
    
    added = 0
    updated = 0
    batch = []
    
    for norm_form, entry in entries.items():
        # Check if exists
        cursor.execute("""
            SELECT id FROM dictionary_entries 
            WHERE headword_normalized = ? AND language = ?
        """, (entry['headword_normalized'], entry['language']))
        
        existing = cursor.fetchone()
        
        if not existing:
            batch.append((
                entry['headword'],
                entry['headword_normalized'], 
                entry['language'],
                entry['entry_xml'],
                entry['entry_html'],
                entry['entry_plain'],
                entry['source']
            ))
            added += 1
        elif entry['source'] == 'wiktionary':
            # Update if it's already a Wiktionary entry
            cursor.execute("""
                UPDATE dictionary_entries 
                SET entry_html = ?, entry_plain = ?
                WHERE id = ?
            """, (entry['entry_html'], entry['entry_plain'], existing[0]))
            updated += 1
        
        # Batch insert
        if len(batch) >= 100:
            cursor.executemany("""
                INSERT INTO dictionary_entries 
                (headword, headword_normalized, language, entry_xml, entry_html, entry_plain, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, batch)
            batch = []
    
    # Insert remaining
    if batch:
        cursor.executemany("""
            INSERT INTO dictionary_entries 
            (headword, headword_normalized, language, entry_xml, entry_html, entry_plain, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch)
    
    conn.commit()
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE source = 'wiktionary'")
    after_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\nDatabase update complete:")
    print(f"  Before: {before_count:,} Wiktionary entries")
    print(f"  Added: {added:,} new entries")
    print(f"  Updated: {updated:,} existing entries")
    print(f"  After: {after_count:,} Wiktionary entries")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_all_corpus_definitions.py <command>")
        print("Commands:")
        print("  extract - Extract all definitions from Wiktionary (takes hours)")
        print("  add     - Add extracted definitions to database")
        print("  stats   - Show statistics about corpus words")
        return
    
    command = sys.argv[1]
    
    if command == 'extract':
        dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
        words_file = 'all_greek_words_in_corpus.json'
        output_dir = 'wiktionary_extraction_results'
        
        if not Path(dump_file).exists():
            print(f"Error: Wiktionary dump not found at {dump_file}")
            return
        
        if not Path(words_file).exists():
            print(f"Error: Corpus words file not found at {words_file}")
            return
        
        process_wiktionary_comprehensive(dump_file, words_file, output_dir)
    
    elif command == 'add':
        definitions_file = 'wiktionary_extraction_results/wiktionary_definitions_final.json'
        if not Path(definitions_file).exists():
            print(f"Error: Definitions file not found at {definitions_file}")
            return
        
        add_to_database(definitions_file)
    
    elif command == 'stats':
        with open('all_greek_words_in_corpus.json', 'r', encoding='utf-8') as f:
            words = json.load(f)
        
        print(f"Total unique Greek words in corpus: {len(words):,}")
        
        # Frequency analysis
        freq_1 = sum(1 for freq in words.values() if freq == 1)
        freq_10plus = sum(1 for freq in words.values() if freq >= 10)
        freq_100plus = sum(1 for freq in words.values() if freq >= 100)
        
        print(f"\nFrequency analysis:")
        print(f"  Hapax legomena (freq=1): {freq_1:,} ({freq_1/len(words)*100:.1f}%)")
        print(f"  Common (freq≥10): {freq_10plus:,} ({freq_10plus/len(words)*100:.1f}%)")
        print(f"  Very common (freq≥100): {freq_100plus:,} ({freq_100plus/len(words)*100:.1f}%)")

if __name__ == '__main__':
    main()