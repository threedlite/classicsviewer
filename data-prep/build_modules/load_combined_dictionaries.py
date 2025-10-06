#!/usr/bin/env python3
"""
Functions to load the combined dictionary data into the database.
This replaces the old LSJ, Cunliffe, and Wiktionary loading functions.
"""

import json
from pathlib import Path
from .normalization_utils import normalize_greek_ultra

def load_combined_dictionaries(cursor, build_mode='full'):
    """Load combined dictionary entries and lemma mappings

    Args:
        cursor: Database cursor
        build_mode: 'full', 'sample', 'extended', or 'first1ktest'
                   - 'first1ktest' only creates empty tables
    """

    if build_mode == 'first1ktest':
        # For first1ktest, only create empty tables
        print("Creating empty dictionary tables for first1ktest mode...")
    else:
        print("\n=== LOADING COMBINED DICTIONARY DATA ===")

        print("\nRunning complete extraction pipeline...")
        print("NOTE: All files will be regenerated from scratch (except all_greek_wiktionary_pages.json)")

        # Always run the complete pipeline to ensure fresh data
        from . import run_complete_pipeline
        print("Running complete pipeline...")
        run_complete_pipeline.main()
    
    # The complete pipeline already handles morphology extraction
    wiktionary_dir = Path(__file__).parent.parent / "wiktionary-processing"
    
    # Create dictionary tables with new schema (no normalized columns)
    print("Creating dictionary tables...")
    cursor.execute("DROP TABLE IF EXISTS dictionary_entries")
    cursor.execute("""
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_dictionary_headword 
        ON dictionary_entries(headword, language)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_dictionary_headword_ultra 
        ON dictionary_entries(headword_normalized_ultra, language)
    """)
    
    cursor.execute("DROP TABLE IF EXISTS lemma_map")
    cursor.execute("""
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_lemma_map_word 
        ON lemma_map(word_form)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_lemma_map_word_ultra 
        ON lemma_map(word_form_normalized_ultra)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_lemma_map_lemma
        ON lemma_map(lemma)
    """)

    # Create normalization_patterns table for non-Greek/Latin languages
    cursor.execute("DROP TABLE IF EXISTS normalization_patterns")
    cursor.execute("""
        CREATE TABLE normalization_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            pattern TEXT NOT NULL,
            replacement TEXT NOT NULL,
            description TEXT,
            priority INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_normalization_language
        ON normalization_patterns(language, priority)
    """)

    # Skip data loading for first1ktest mode
    if build_mode == 'first1ktest':
        print("✓ Empty dictionary tables created for first1ktest mode")
        return

    # Load dictionary entries (should have been created by combine_dictionaries_to_lemma_map.py)
    dict_file = Path(__file__).parent / "combine_dictionaries_to_lemma_map_1.json"

    print("\nLoading dictionary entries...")
    with open(dict_file, 'r', encoding='utf-8') as f:
        dictionary_entries = json.load(f)
    
    # First pass: Fix morphological placeholders by looking up normalized forms
    print("\nFixing morphological placeholder entries...")
    fixed_count = 0
    for headword, entry in dictionary_entries.items():
        if entry.get('language') == 'greek' and 'orphological entry' in entry.get('entry_plain', ''):
            # Try to find a real definition from a normalized form
            candidates = []
            
            # Try without breve/macron marks
            normalized = headword.replace("ῠ", "υ").replace("ῡ", "υ").replace("ᾱ", "α").replace("ᾰ", "α").replace("ῐ", "ι").replace("ῑ", "ι")
            candidates.append(normalized)
            
            # Also try removing all diacritics
            import unicodedata
            nfd = unicodedata.normalize('NFD', normalized)
            no_accents = ''.join(c for c in nfd if not unicodedata.combining(c))
            candidates.append(no_accents)
            
            # Try variations with standard Greek accent patterns
            # (removed hardcoded specific mappings)
                
            for candidate in candidates:
                if candidate != headword and candidate in dictionary_entries:
                    other_entry = dictionary_entries[candidate]
                    if 'orphological entry' not in other_entry.get('entry_plain', ''):
                        # Use the real definition
                        entry['entry_plain'] = other_entry['entry_plain']
                        entry['entry_html'] = other_entry['entry_html']
                        entry['entry_xml'] = other_entry.get('entry_xml', '')
                        fixed_count += 1
                        print(f"  Fixed {headword} using definition from {candidate}")
                        break
    
    print(f"Fixed {fixed_count} morphological placeholder entries")
    
    entries_imported = 0
    for key, entry in dictionary_entries.items():
        # key might be "headword_source" format for multiple sources
        # entry contains the actual headword field
        
        # Compute ultra-normalized form for Greek words
        headword_ultra = normalize_greek_ultra(entry['headword']) if entry['language'] == 'greek' else None
        
        cursor.execute("""
            INSERT INTO dictionary_entries 
            (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry['headword'],
            headword_ultra,
            entry['language'],
            entry.get('entry_xml', ''),
            entry.get('entry_html', ''),
            entry.get('entry_plain', ''),
            entry.get('source', '')
        ))
        entries_imported += 1
        
        if entries_imported % 5000 == 0:
            print(f"  Imported {entries_imported} entries...")
    
    print(f"✓ Imported {entries_imported} dictionary entries")
    
    # Load both dictionary-based and Wiktionary morphology mappings
    print("\nLoading all lemma mappings...")
    
    # First load the comprehensive Wiktionary morphology
    combined_morph_file = wiktionary_dir / "combine_all_ancient_greek_morphology.json"
    wiktionary_mappings = []
    
    if not combined_morph_file.exists():
        raise FileNotFoundError(f"CRITICAL: Wiktionary morphology file missing: {combined_morph_file}\n"
                               "Run the morphology extraction pipeline first.")

    with open(combined_morph_file, 'r', encoding='utf-8') as f:
        wiktionary_morph_data = json.load(f)
    wiktionary_mappings = wiktionary_morph_data.get('mappings', [])

    if not wiktionary_mappings:
        raise RuntimeError("CRITICAL: Wiktionary morphology file contains no mappings. This is a required component.")

    print(f"  Loaded {len(wiktionary_mappings)} Wiktionary morphology mappings")
    
    # Load Perseus Treebank lemma mappings (high-quality hand-annotated data)
    treebank_mappings = []
    from .extract_perseus_treebank_lemmas import extract_treebank_lemmas
    print("  Extracting Perseus Treebank lemma mappings...")
    treebank_data = extract_treebank_lemmas()

    if not treebank_data:
        raise RuntimeError("CRITICAL: Perseus Treebank extraction returned no data. This is a required component.")

    # Convert treebank format to our mapping format
    for form, lemmas in treebank_data.items():
        for lemma in lemmas:
            treebank_mappings.append({
                'word_form': form,
                'lemma': lemma,
                'confidence': 0.95,  # High confidence for hand-annotated data
                'source': 'perseus_treebank',
                'morph_info': ''
            })
    print(f"  Loaded {len(treebank_mappings)} Perseus Treebank mappings")
    
    # Load dictionary-based mappings (always use final version with all variants)
    lemma_file = Path(__file__).parent / "add_enclitic_variants.json"
    print("  Loading dictionary-based lemma mappings with all variants...")
    with open(lemma_file, 'r', encoding='utf-8') as f:
        dict_lemma_mappings = json.load(f)
    
    # Combine all mappings - priority order: Treebank > Wiktionary > Dictionary
    all_lemma_mappings = []
    
    # Add Perseus Treebank mappings first (highest priority - hand-annotated)
    for mapping in treebank_mappings:
        all_lemma_mappings.append(mapping)
    
    # Add Wiktionary mappings second
    for mapping in wiktionary_mappings:
        all_lemma_mappings.append({
            'word_form': mapping['word_form'],
            'lemma': mapping['lemma'],
            'confidence': mapping.get('confidence', 1.0),
            'source': mapping.get('source', 'wiktionary'),
            'morph_info': mapping.get('morph_info', '')
        })
    
    # Then add dictionary-based mappings
    for mapping in dict_lemma_mappings:
        all_lemma_mappings.append({
            'word_form': mapping['word_form'],
            'lemma': mapping['lemma'],
            'confidence': mapping.get('confidence', 0.8),
            'source': mapping.get('source', 'dictionary'),
            'morph_info': mapping.get('morph_info', '')
        })
    
    print(f"  Total mappings to process: {len(all_lemma_mappings)}")
    
    # Import all mappings without deduplication
    # Multiple mappings for same word form are valid (homographs)
    mappings_imported = 0
    for mapping in all_lemma_mappings:
        # Compute ultra-normalized form
        word_form_ultra = normalize_greek_ultra(mapping['word_form'])
        
        cursor.execute("""
            INSERT OR IGNORE INTO lemma_map
            (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mapping['word_form'],
            word_form_ultra,
            mapping['lemma'],
            mapping.get('confidence', 1.0),
            mapping.get('source', ''),
            mapping.get('morph_info')
        ))
        mappings_imported += 1
        
        if mappings_imported % 10000 == 0:
            print(f"  Imported {mappings_imported} mappings...")
    
    print(f"✓ Imported {mappings_imported} lemma mappings")
    
    # Load Whitaker's Latin dictionary and morphology (full and extended databases)
    if build_mode in ['full', 'extended']:
        try:
            from .load_whitakers_latin import load_whitakers_latin
            print(f"  Loading Whitaker's Latin dictionary and morphology ({build_mode} database)")
            load_whitakers_latin(cursor, include_full_morphology=True)
        except ImportError as e:
            print(f"ERROR: Could not import Whitaker's Latin module: {e}")
            raise RuntimeError(f"Failed to load Whitaker's Latin for {build_mode} database build") from e
        except Exception as e:
            print(f"ERROR: Failed loading Whitaker's Latin: {e}")
            raise RuntimeError(f"Failed to load Whitaker's Latin for {build_mode} database build") from e
    else:
        print(f"  Skipping Whitaker's Latin dictionary ({build_mode} database)")
    
    # Print statistics
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE language = 'greek'")
    greek_dict_count = cursor.fetchone()[0]
    print(f"\nTotal Greek dictionary entries: {greek_dict_count:,}")
    
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE language = 'latin'")
    latin_dict_count = cursor.fetchone()[0]
    print(f"Total Latin dictionary entries: {latin_dict_count:,}")
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    lemma_count = cursor.fetchone()[0]
    print(f"Total lemma mappings: {lemma_count:,}")
    
    # Source breakdown for dictionary entries
    print("\nDictionary entries by source:")
    cursor.execute("""
        SELECT source, COUNT(*) as count 
        FROM dictionary_entries 
        WHERE language = 'greek'
        GROUP BY source 
        ORDER BY count DESC
    """)
    for source, count in cursor.fetchall():
        print(f"  {source}: {count:,} headwords")
    
    # Source breakdown for lemma mappings
    print("\nLemma mappings by source:")
    cursor.execute("""
        SELECT source, 
               COUNT(DISTINCT word_form) as word_forms,
               COUNT(DISTINCT lemma) as lemmas,
               COUNT(*) as total_mappings
        FROM lemma_map 
        GROUP BY source 
        ORDER BY total_mappings DESC
    """)
    for source, word_forms, lemmas, total in cursor.fetchall():
        print(f"  {source}: {word_forms:,} word forms → {lemmas:,} lemmas ({total:,} total mappings)")

if __name__ == "__main__":
    import sys
    
    print("=== Running complete dictionary pipeline ===\n")
    
    # Import and run combine_dictionaries_to_lemma_map directly
    print("Running combine_dictionaries_to_lemma_map.py (this will run all extraction scripts)...")
    try:
        import combine_dictionaries_to_lemma_map
        combine_dictionaries_to_lemma_map.combine_dictionaries()
    except Exception as e:
        print(f"ERROR: Dictionary pipeline failed: {str(e)}")
        sys.exit(1)
    
    print("\n=== All dictionary files created successfully ===")
    print("\nNow you can test loading them into a database")