#!/usr/bin/env python3
"""
Extract dictionary definitions for lemmas that are missing from LSJ but exist in Wiktionary
"""

import sqlite3
import json
import unicodedata
import re

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def extract_wiktionary_definition(title, content):
    """Extract a concise definition from Wiktionary content"""
    # Look for Ancient Greek section
    ancient_greek_match = re.search(r'==Ancient Greek==(.*?)(?===|$)', content, re.DOTALL)
    if not ancient_greek_match:
        return None
    
    ag_content = ancient_greek_match.group(1)
    
    # Extract first definition
    def_match = re.search(r'#\s*([^#\n]+)', ag_content)
    if def_match:
        definition = def_match.group(1).strip()
        # Clean up wiki markup
        definition = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', definition)
        definition = re.sub(r'\[\[([^\]]+)\]\]', r'\1', definition)
        definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
        definition = definition.strip()
        
        if definition and len(definition) > 5:
            return definition
    
    return None

def main():
    conn = sqlite3.connect('perseus_texts.db')
    cursor = conn.cursor()
    
    print("Loading Wiktionary data...")
    with open('wiktionary-processing/all_greek_wiktionary_pages.json', 'r', encoding='utf-8') as f:
        wiktionary_pages = json.load(f)
    
    print(f"Loaded {len(wiktionary_pages):,} Wiktionary pages")
    
    # Get all unique lemmas from lemma_map that don't have dictionary entries
    print("\nFinding lemmas without dictionary entries...")
    cursor.execute("""
        SELECT DISTINCT lm.lemma, COUNT(*) as usage_count
        FROM lemma_map lm
        LEFT JOIN dictionary_entries de 
            ON lm.lemma = de.headword_normalized AND de.language = 'greek'
        WHERE de.id IS NULL
            AND lm.lemma != ''
            AND LENGTH(lm.lemma) > 1
        GROUP BY lm.lemma
        ORDER BY usage_count DESC
    """)
    
    missing_lemmas = cursor.fetchall()
    print(f"Found {len(missing_lemmas):,} lemmas without dictionary entries")
    
    # Check which missing lemmas exist in Wiktionary
    definitions_to_add = []
    found_count = 0
    
    print("\nChecking Wiktionary for missing lemmas...")
    for lemma, usage_count in missing_lemmas:
        # Try to find the lemma in Wiktionary (with accents)
        found = False
        
        # Check all Wiktionary entries
        for title, content in wiktionary_pages.items():
            if normalize_greek(title) == lemma:
                definition = extract_wiktionary_definition(title, content)
                if definition:
                    definitions_to_add.append({
                        'headword': title,
                        'headword_normalized': lemma,
                        'definition': definition,
                        'usage_count': usage_count
                    })
                    found = True
                    found_count += 1
                    if found_count % 100 == 0:
                        print(f"  Found {found_count} definitions...")
                    break
    
    print(f"\nFound definitions for {len(definitions_to_add):,} missing lemmas")
    
    # Show top missing lemmas found
    print("\nTop 20 missing lemmas found in Wiktionary:")
    for item in sorted(definitions_to_add, key=lambda x: x['usage_count'], reverse=True)[:20]:
        print(f"  {item['headword']} ({item['headword_normalized']}) - usage: {item['usage_count']:,}")
        print(f"    Definition: {item['definition'][:80]}...")
    
    # Add to database
    if definitions_to_add:
        print(f"\nAdding {len(definitions_to_add)} definitions to dictionary_entries...")
        
        for item in definitions_to_add:
            cursor.execute("""
                INSERT OR IGNORE INTO dictionary_entries 
                (headword, headword_normalized, language, entry_plain, source)
                VALUES (?, ?, 'greek', ?, 'wiktionary_supplement')
            """, (item['headword'], item['headword_normalized'], item['definition']))
        
        conn.commit()
        print("Done!")
    
    # Also check for common particles and words that might be missing
    print("\nChecking for common particles and function words...")
    common_words = [
        'αὐτάρ', 'μέντοι', 'καθάπερ', 'ἐπειδή', 'πρῶτος', 'μάλιστα',
        'οὐχ', 'οὐχί', 'οὐκ', 'μήτε', 'οὔτε', 'κἄν', 'τοίνυν',
        'ἄρα', 'δήπου', 'που', 'πως', 'πῃ', 'ποθεν', 'ποι'
    ]
    
    particles_added = 0
    for word in common_words:
        normalized = normalize_greek(word)
        
        # Check if already in dictionary
        cursor.execute("""
            SELECT 1 FROM dictionary_entries 
            WHERE headword_normalized = ? AND language = 'greek'
        """, (normalized,))
        
        if not cursor.fetchone() and word in wiktionary_pages:
            definition = extract_wiktionary_definition(word, wiktionary_pages[word])
            if definition:
                cursor.execute("""
                    INSERT OR IGNORE INTO dictionary_entries 
                    (headword, headword_normalized, language, entry_plain, source)
                    VALUES (?, ?, 'greek', ?, 'wiktionary_particles')
                """, (word, normalized, definition))
                particles_added += 1
                print(f"  Added {word}: {definition[:60]}...")
    
    if particles_added > 0:
        conn.commit()
        print(f"Added {particles_added} common particles/function words")
    
    conn.close()

if __name__ == '__main__':
    main()