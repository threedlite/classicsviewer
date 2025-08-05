#!/usr/bin/env python3
"""
Add inflection mappings from Wiktionary to the lemma_map table
"""

import json
import sqlite3
from pathlib import Path

def main():
    # Load inflection mappings
    mappings_file = Path("wiktionary-processing/inflection_extraction_results/inflection_mappings_final.json")
    print(f"Loading inflection mappings from {mappings_file}...")
    
    with open(mappings_file) as f:
        mappings = json.load(f)
    
    print(f"Found {len(mappings):,} inflection mappings")
    
    # Connect to database
    db_path = Path("perseus_texts.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add mappings
    added = 0
    skipped = 0
    
    for word_form_norm, info in mappings.items():
        # Check if mapping already exists
        cursor.execute("""
            SELECT COUNT(*) FROM lemma_map 
            WHERE word_form = ? AND lemma = ?
        """, (word_form_norm, info['lemma_normalized']))
        
        if cursor.fetchone()[0] > 0:
            skipped += 1
            continue
        
        # Build morphology string
        morph_str = None
        if info.get('morphology'):
            morph_str = ';'.join(info['morphology'])
        
        # Insert new mapping
        cursor.execute("""
            INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source)
            VALUES (?, ?, ?, ?, ?)
        """, (
            word_form_norm,
            word_form_norm,  # Using normalized form for both
            info['lemma_normalized'],
            morph_str,
            'wiktionary:inflection_of'
        ))
        added += 1
        
        if added % 1000 == 0:
            print(f"Added {added:,} mappings...")
    
    # Commit changes
    conn.commit()
    
    print(f"\nSummary:")
    print(f"  Total mappings: {len(mappings):,}")
    print(f"  Added: {added:,}")
    print(f"  Skipped (already exists): {skipped:,}")
    
    # Show final counts
    cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE source = 'wiktionary:inflection_of'")
    total_wikt = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    total_all = cursor.fetchone()[0]
    
    print(f"\nDatabase now has:")
    print(f"  {total_wikt:,} Wiktionary inflection mappings")
    print(f"  {total_all:,} total lemma mappings")
    
    conn.close()

if __name__ == "__main__":
    main()