#!/usr/bin/env python3
"""
Master build script for Perseus database with all morphological enhancements.

This single script orchestrates the complete database build:
1. Creates base database with Perseus texts and LSJ dictionary (via create_perseus_database.py)
2. Adds Wiktionary inflection mappings (15,592 entries)
3. Adds Greek Wiktionary declension mappings (37,119 entries)  
4. Adds nu-movable verb variants
5. Adds supplemental Wiktionary definitions for missing lemmas
6. Optimizes and packages the database as OBB

Usage: python3 build_database.py
"""

import subprocess
import sys
import sqlite3
import json
from pathlib import Path
import unicodedata
import shutil

def normalize_greek(text):
    """Normalize Greek text by removing diacritics and converting to lowercase"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, cwd=Path(__file__).parent)
    if result.returncode != 0:
        print(f"ERROR: {description} failed with code {result.returncode}")
        sys.exit(1)
    return result

def add_wiktionary_inflections(db_path):
    """Add Wiktionary inflection mappings from our extraction"""
    print("\nAdding Wiktionary inflection mappings...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load inflection mappings
    inflection_file = Path(__file__).parent / 'wiktionary-processing' / 'inflection_extraction_results' / 'inflection_mappings_final.json'
    if inflection_file.exists():
        with open(inflection_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        count = 0
        for word_form, lemma_data in mappings.items():
            if isinstance(lemma_data, dict) and 'lemma' in lemma_data:
                lemma = lemma_data['lemma']
                morph_info = lemma_data.get('morphology', '')
                
                # Convert list to string if needed
                if isinstance(morph_info, list):
                    morph_info = ', '.join(morph_info)
                
                # Normalize
                word_normalized = normalize_greek(word_form)
                lemma_normalized = normalize_greek(lemma)
                
                # Skip if mapping already exists
                cursor.execute("""
                    SELECT 1 FROM lemma_map 
                    WHERE word_normalized = ? AND lemma = ?
                """, (word_normalized, lemma_normalized))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)
                        VALUES (?, ?, ?, ?, 'wiktionary_inflection', 0.9)
                    """, (word_form, word_normalized, lemma_normalized, morph_info))
                    count += 1
        
        conn.commit()
        print(f"  Added {count} inflection mappings")
    else:
        print(f"  WARNING: Inflection mappings file not found at {inflection_file}")
    
    conn.close()

def add_greek_wiktionary_declensions(db_path):
    """Add Greek Wiktionary declension mappings from our extraction"""
    print("\nAdding Greek Wiktionary declension mappings...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load declension mappings
    declension_file = Path(__file__).parent / 'wiktionary-processing' / 'ancient_greek_declension_mappings.json'
    if declension_file.exists():
        with open(declension_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract mappings from the data structure
        mappings = data.get('mappings', []) if isinstance(data, dict) else data
        
        count = 0
        for mapping in mappings:
            word_form = mapping.get('word_form', '')
            lemma = mapping.get('lemma', '')
            case_info = mapping.get('case', '')
            number = mapping.get('number', '')
            gender = mapping.get('gender', '')
            
            if word_form and lemma:
                # Build morphology string
                morph_parts = []
                if case_info:
                    morph_parts.append(case_info)
                if number:
                    morph_parts.append(number)
                if gender:
                    morph_parts.append(gender)
                morph_info = '_'.join(morph_parts)
                
                # Normalize
                word_normalized = normalize_greek(word_form)
                lemma_normalized = normalize_greek(lemma)
                
                # Skip if mapping already exists
                cursor.execute("""
                    SELECT 1 FROM lemma_map 
                    WHERE word_normalized = ? AND lemma = ?
                """, (word_normalized, lemma_normalized))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)
                        VALUES (?, ?, ?, ?, 'greek_wiktionary_declension', 0.85)
                    """, (word_form, word_normalized, lemma_normalized, morph_info))
                    count += 1
        
        conn.commit()
        print(f"  Added {count} declension mappings")
    else:
        print(f"  WARNING: Declension mappings file not found at {declension_file}")
    
    conn.close()

def add_nu_movable_variants(db_path):
    """Add nu-movable variants for Greek verbs"""
    print("\nAdding nu-movable variants...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all verb forms ending in ε, ι, or σι that could take movable nu
    cursor.execute("""
        SELECT DISTINCT word_form, lemma, morph_info
        FROM lemma_map
        WHERE (word_form LIKE '%ε' OR word_form LIKE '%ι' OR word_form LIKE '%σι')
        AND source != 'nu_movable_variant'
    """)
    
    variants = []
    for word_form, lemma, morph_info in cursor.fetchall():
        # Create nu-movable variant
        variant = word_form + 'ν'
        variant_normalized = normalize_greek(variant)
        
        # Add morph info
        new_morph = morph_info + '_with_nu' if morph_info else 'with_nu'
        
        variants.append((variant, variant_normalized, lemma, new_morph))
    
    # Insert variants
    count = 0
    for variant, variant_normalized, lemma, morph_info in variants:
        cursor.execute("""
            SELECT 1 FROM lemma_map 
            WHERE word_normalized = ? AND lemma = ?
        """, (variant_normalized, lemma))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)
                VALUES (?, ?, ?, ?, 'nu_movable_variant', 0.95)
            """, (variant, variant_normalized, lemma, morph_info))
            count += 1
    
    conn.commit()
    print(f"  Added {count} nu-movable variants")
    conn.close()

def add_wiktionary_definitions(db_path):
    """Add Wiktionary definitions for lemmas missing from LSJ"""
    print("\nAdding Wiktionary definitions for missing lemmas...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if we have the Wiktionary pages file
    wiktionary_file = Path(__file__).parent / 'wiktionary-processing' / 'all_greek_wiktionary_pages.json'
    if not wiktionary_file.exists():
        print("  WARNING: Wiktionary pages file not found")
        conn.close()
        return
    
    with open(wiktionary_file, 'r', encoding='utf-8') as f:
        wiktionary_pages = json.load(f)
    
    # Get lemmas without dictionary entries (limit to prevent timeout)
    cursor.execute("""
        SELECT DISTINCT lm.lemma
        FROM lemma_map lm
        LEFT JOIN dictionary_entries de 
            ON lm.lemma = de.headword_normalized AND de.language = 'greek'
        WHERE de.id IS NULL
            AND lm.lemma != ''
            AND LENGTH(lm.lemma) > 1
        LIMIT 2000
    """)
    
    missing_lemmas = [row[0] for row in cursor.fetchall()]
    
    count = 0
    for lemma in missing_lemmas:
        # Look for the lemma in Wiktionary
        for title, content in wiktionary_pages.items():
            if normalize_greek(title) == lemma and '==Ancient Greek==' in content:
                # Extract basic definition
                import re
                def_match = re.search(r'==Ancient Greek==.*?#\s*([^#\n]+)', content, re.DOTALL)
                if def_match:
                    definition = def_match.group(1).strip()
                    # Clean up wiki markup
                    definition = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', definition)
                    definition = re.sub(r'\[\[([^\]]+)\]\]', r'\1', definition)
                    definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
                    
                    if definition and len(definition) > 5:
                        cursor.execute("""
                            INSERT OR IGNORE INTO dictionary_entries 
                            (headword, headword_normalized, language, entry_plain, source)
                            VALUES (?, ?, 'greek', ?, 'wiktionary_supplement')
                        """, (title, lemma, definition))
                        count += 1
                        break
    
    conn.commit()
    print(f"  Added {count} Wiktionary definitions")
    conn.close()

def main():
    """Build complete Perseus database with all enhancements"""
    
    print("=== COMPLETE PERSEUS DATABASE BUILD ===")
    print("This will create a database with:")
    print("- Perseus texts and metadata")
    print("- LSJ dictionary entries")
    print("- Wiktionary inflection mappings (~15k)")
    print("- Greek Wiktionary declension mappings (~37k)")
    print("- Nu-movable variants")
    print("- Supplemental Wiktionary definitions")
    print()
    
    # Step 1: Create base database with texts and LSJ
    run_command(
        "python3 create_perseus_database.py",
        "Creating base Perseus database with texts and LSJ"
    )
    
    db_path = Path(__file__).parent / 'perseus_texts.db'
    if not db_path.exists():
        print("ERROR: Database not created!")
        sys.exit(1)
    
    # Step 2-5: Add all Wiktionary enhancements
    add_wiktionary_inflections(db_path)
    add_greek_wiktionary_declensions(db_path)
    add_nu_movable_variants(db_path)
    add_wiktionary_definitions(db_path)
    
    # Step 6: Optimize database
    print("\n" + "="*60)
    print("Optimizing database...")
    print("="*60)
    
    conn = sqlite3.connect(db_path)
    conn.execute("VACUUM")
    conn.execute("ANALYZE")
    conn.close()
    
    # Step 7: Generate summary report
    print("\n" + "="*60)
    print("DATABASE BUILD COMPLETE")
    print("="*60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM authors WHERE language = 'greek'")
    greek_authors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM works w JOIN authors a ON w.author_id = a.id WHERE a.language = 'greek'")
    greek_works = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT word_normalized) FROM word_forms wf JOIN books b ON wf.book_id = b.id JOIN works w ON b.work_id = w.id JOIN authors a ON w.author_id = a.id WHERE a.language = 'greek'")
    unique_words = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    lemma_mappings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE language = 'greek'")
    dict_entries = cursor.fetchone()[0]
    
    print(f"\nDatabase Statistics:")
    print(f"  Greek authors: {greek_authors:,}")
    print(f"  Greek works: {greek_works:,}")
    print(f"  Unique Greek word forms: {unique_words:,}")
    print(f"  Lemma mappings: {lemma_mappings:,}")
    print(f"  Dictionary entries: {dict_entries:,}")
    
    # Show sources breakdown
    cursor.execute("""
        SELECT source, COUNT(*) as count 
        FROM lemma_map 
        GROUP BY source 
        ORDER BY count DESC
    """)
    
    print(f"\nLemma mappings by source:")
    for source, count in cursor.fetchall():
        print(f"  {source}: {count:,}")
    
    conn.close()
    
    # Step 8: Create OBB file
    print(f"\nCreating OBB file...")
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    obb_name = 'main.1.com.classicsviewer.app.debug.obb'
    shutil.copy(db_path, output_dir / obb_name)
    print(f"  Created: output/{obb_name}")
    
    # Also copy to root for convenience
    shutil.copy(db_path, Path(__file__).parent / obb_name)
    
    print("\n✓ Build complete!")
    print(f"\nTo deploy to Android device:")
    print(f"  adb push output/{obb_name} /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/")

if __name__ == "__main__":
    main()