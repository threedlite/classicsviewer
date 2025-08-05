#!/usr/bin/env python3
"""
Add Greek Wiktionary declension mappings to the lemma_map table
"""

import json
import sqlite3
from pathlib import Path

def main():
    # Load declension mappings
    mappings_file = Path("wiktionary-processing/ancient_greek_declension_mappings.json")
    print(f"Loading declension mappings from {mappings_file}...")
    
    with open(mappings_file) as f:
        mappings = json.load(f)
    
    # Extract the mappings list
    if 'mappings' in mappings:
        mappings_list = mappings['mappings']
    else:
        # Assume it's already a list
        mappings_list = mappings
    
    print(f"Found {len(mappings_list):,} declension mappings")
    
    # Connect to database
    db_path = Path("perseus_texts.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add mappings
    added = 0
    skipped = 0
    
    for mapping in mappings_list:
        word_form = mapping['word_form']
        lemma = mapping['lemma']
        
        # Check if mapping already exists
        cursor.execute("""
            SELECT COUNT(*) FROM lemma_map 
            WHERE word_form = ? AND lemma = ?
        """, (word_form, lemma))
        
        if cursor.fetchone()[0] > 0:
            skipped += 1
            continue
        
        # Build morphology string from case info
        morph_str = mapping.get('case', '')
        
        # Get source
        source = mapping.get('source', 'elwiktionary:declension:unknown')
        
        # Insert new mapping
        cursor.execute("""
            INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            word_form,
            word_form,
            lemma,
            morph_str,
            source,
            mapping.get('confidence', 0.9)
        ))
        added += 1
        
        if added % 1000 == 0:
            print(f"Added {added:,} mappings...")
    
    # Commit changes
    conn.commit()
    
    print(f"\nSummary:")
    print(f"  Total mappings: {len(mappings_list):,}")
    print(f"  Added: {added:,}")
    print(f"  Skipped (already exists): {skipped:,}")
    
    # Show final counts
    cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE source LIKE 'elwiktionary:declension:%'")
    total_decl = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    total_all = cursor.fetchone()[0]
    
    print(f"\nDatabase now has:")
    print(f"  {total_decl:,} Greek Wiktionary declension mappings")
    print(f"  {total_all:,} total lemma mappings")
    
    conn.close()

if __name__ == "__main__":
    main()