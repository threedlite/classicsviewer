#!/usr/bin/env python3
"""
Extract Wiktionary definitions for Greek words in the corpus that lack dictionary entries.
Focuses on frequently occurring words first for maximum impact.
"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import sqlite3
import unicodedata
import sys
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text - same as in main database creation"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def get_missing_words(db_path, min_frequency=10):
    """Get Greek words that appear in texts but have no dictionary entry"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Finding words with frequency >= {min_frequency} that need dictionary entries...")
    
    # Get missing words with their frequencies
    cursor.execute("""
        WITH word_counts AS (
            SELECT word_normalized, COUNT(*) as freq
            FROM word_forms 
            WHERE book_id LIKE 'tlg%'
            GROUP BY word_normalized
        )
        SELECT wc.word_normalized, wc.freq
        FROM word_counts wc
        WHERE wc.freq >= ?
        AND NOT EXISTS (
            SELECT 1 FROM lemma_map lm WHERE lm.word_normalized = wc.word_normalized
        )
        AND NOT EXISTS (
            SELECT 1 FROM dictionary_entries de 
            WHERE de.headword_normalized = wc.word_normalized AND de.language = 'greek'
        )
        ORDER BY wc.freq DESC
        LIMIT 5000
    """, (min_frequency,))
    
    missing_words = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    print(f"Found {len(missing_words)} high-frequency words needing definitions")
    return missing_words

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
            defn = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', defn)  # [[link|text]] -> text
            defn = re.sub(r'\[\[([^\]]+)\]\]', r'\1', defn)  # [[link]] -> link
            defn = re.sub(r"'''?", '', defn)  # Remove bold/italic
            defn = re.sub(r'\{\{[^}]+\}\}', '', defn)  # Remove templates
            defn = re.sub(r'\([^)]*\)', '', defn)  # Remove parenthetical references
            defn = defn.strip()
            
            if defn and len(defn) > 3:  # Skip very short definitions
                definitions.append(defn)
                
        if len(definitions) >= 3:  # Limit to 3 definitions
            break
    
    if not definitions:
        return None
    
    # Extract inflection information if present
    inflection_info = None
    inflection_match = re.search(r'{{grc-[^}]+}}', ag_section)
    if inflection_match:
        inflection_info = "inflects"  # Simplified - could parse more detail
    
    # Format as simple HTML entry similar to LSJ style
    html_entry = f'<div class="wiktionary-entry">'
    html_entry += f'<b>{title}</b>'
    
    if pos == 'proper noun':
        html_entry += ', proper name. '
    else:
        html_entry += f', {pos}. '
    
    if len(definitions) == 1:
        html_entry += definitions[0]
    else:
        html_entry += '<br/>'.join([f'{i+1}. {d}' for i, d in enumerate(definitions)])
    
    html_entry += '<br/><i style="font-size: 0.9em; color: #666;">[From Wiktionary]</i></div>'
    
    # Plain text version
    plain_entry = f'{title}, {pos}. ' + '; '.join(definitions) + ' (From Wiktionary)'
    
    return {
        'headword': title,
        'headword_normalized': normalized_title,
        'language': 'greek',
        'entry_html': html_entry,
        'entry_plain': plain_entry[:500],  # Limit length
        'entry_xml': None,
        'source': 'wiktionary'
    }

def process_wiktionary_dump(dump_file, target_words, output_file, max_entries=None):
    """Extract definitions for specific words from Wiktionary"""
    
    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    found_entries = {}
    processed = 0
    
    # Also look for non-normalized forms
    target_set = set(target_words.keys())
    print(f"\nSearching Wiktionary for {len(target_set)} words...")
    
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
        for event, elem in ET.iterparse(f, events=('start', 'end')):
            if event == 'end' and elem.tag.endswith('page'):
                title_elem = elem.find('.//ns:title', namespace)
                text_elem = elem.find('.//ns:text', namespace)
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    
                    # Skip non-main namespace pages
                    if ':' in title and not title.startswith('Reconstruction:'):
                        elem.clear()
                        continue
                    
                    # Check if this might be one of our target words
                    normalized_title = normalize_greek(title)
                    
                    if normalized_title in target_set:
                        text = text_elem.text or ''
                        
                        if '==Ancient Greek==' in text:
                            entry = extract_wiktionary_definition(title, text, normalized_title)
                            if entry:
                                found_entries[normalized_title] = entry
                                processed += 1
                                
                                if processed % 100 == 0:
                                    print(f"  Processed {processed} entries...")
                                
                                # Save periodically
                                if processed % 500 == 0:
                                    with open(output_file, 'w', encoding='utf-8') as out:
                                        json.dump(found_entries, out, ensure_ascii=False, indent=2)
                
                elem.clear()
                
            # Stop if we've found enough
            if max_entries and processed >= max_entries:
                break
    
    return found_entries

def add_to_database(entries_file, db_path='perseus_texts.db'):
    """Add extracted Wiktionary entries to the database"""
    
    with open(entries_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    added = 0
    skipped = 0
    
    for norm_form, entry in entries.items():
        # Check if already exists
        cursor.execute("""
            SELECT COUNT(*) FROM dictionary_entries 
            WHERE headword_normalized = ? AND language = ?
        """, (entry['headword_normalized'], entry['language']))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO dictionary_entries 
                (headword, headword_normalized, language, entry_xml, entry_html, entry_plain, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry['headword'],
                entry['headword_normalized'],
                entry['language'],
                entry['entry_xml'],
                entry['entry_html'],
                entry['entry_plain'],
                entry['source']
            ))
            added += 1
            
            # Also add self-mapping to lemma_map if it's a lemma form
            cursor.execute("""
                INSERT OR IGNORE INTO lemma_map 
                (word_form, word_normalized, lemma, confidence, source)
                VALUES (?, ?, ?, 1.0, 'wiktionary:lemma')
            """, (norm_form, norm_form, norm_form))
        else:
            skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nAdded {added} Wiktionary entries to database")
    print(f"Skipped {skipped} existing entries")

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_corpus_wiktionary_definitions.py <command>")
        print("Commands:")
        print("  extract - Extract definitions from Wiktionary dump")
        print("  add     - Add extracted definitions to database")
        return
    
    command = sys.argv[1]
    
    if command == 'extract':
        # Get missing words from database
        missing_words = get_missing_words('../perseus_texts.db', min_frequency=50)
        
        # Extract from Wiktionary
        dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
        output_file = 'corpus_wiktionary_definitions.json'
        
        if not Path(dump_file).exists():
            print(f"Error: Wiktionary dump not found at {dump_file}")
            return
        
        print(f"\nProcessing Wiktionary dump...")
        entries = process_wiktionary_dump(dump_file, missing_words, output_file, max_entries=1000)
        
        # Save final results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        
        print(f"\nExtracted {len(entries)} Wiktionary entries")
        print(f"Saved to {output_file}")
        
        # Show sample
        if entries:
            print("\nSample entries:")
            for word, entry in list(entries.items())[:5]:
                print(f"  {entry['headword']}: {entry['entry_plain'][:80]}...")
    
    elif command == 'add':
        add_to_database('corpus_wiktionary_definitions.json', '../perseus_texts.db')
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()