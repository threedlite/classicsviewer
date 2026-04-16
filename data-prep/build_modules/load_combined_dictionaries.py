#!/usr/bin/env python3
"""
Functions to load the combined dictionary data into the database.
This replaces the old LSJ, Cunliffe, and Wiktionary loading functions.
"""

import json
import csv
import unicodedata
from pathlib import Path
from .normalization_utils import normalize_greek_ultra

def load_combined_dictionaries(cursor, build_mode='full', skip_latin=False):
    """Load combined dictionary entries and lemma mappings

    Args:
        cursor: Database cursor
        build_mode: 'full', 'sample', or 'extended'
        skip_latin: When True, do not load Whitaker's Latin dictionary or Latin
            prefix assimilation rules. Used when the Latin module
            (latin/create_latin_database.py) will merge those in separately.
    """

    print("\n=== LOADING COMBINED DICTIONARY DATA ===")

    print("\nRunning complete extraction pipeline...")
    print("NOTE: All files will be regenerated from scratch (except all_greek_wiktionary_pages.json)")

    # Run the complete pipeline inline
    import subprocess
    import sys

    build_modules_dir = Path(__file__).parent
    data_prep_dir = build_modules_dir.parent
    wiktionary_dir = data_prep_dir / "wiktionary-processing"

    print("COMPLETE DICTIONARY AND MORPHOLOGY PIPELINE")
    print("="*60)

    # Step 1: Ensure Greek pages are extracted (one-time only)
    greek_pages_file = wiktionary_dir / "all_greek_wiktionary_pages.json"
    if not greek_pages_file.exists():
        print(f"\nExtracting Greek pages from Wiktionary (one-time, ~10 minutes)...")
        subprocess.run([sys.executable, "extract_all_greek_pages.py"], cwd=wiktionary_dir, check=True, timeout=1200)
    else:
        print(f"\n✓ Greek pages already extracted: {greek_pages_file}")

    # Step 2: Extract all morphology data
    print("\n\nSTEP 2: EXTRACTING MORPHOLOGY DATA")

    morphology_scripts = [
        ("extract_ancient_greek_conjugations.py", "Ancient Greek verb conjugations", 300),
        ("extract_ancient_greek_declensions.py", "Ancient Greek noun declensions", 300),
        ("extract_all_ancient_greek_words_with_diacritics.py", "All Ancient Greek words with diacritics (includes 48k definitions)", 300),
        ("extract_inflection_of_template_fixed.py", "Inflection_of template mappings", 300),
        ("extract_declension_mappings_fixed.py", "Declension template mappings", 300)
    ]

    for script, desc, timeout in morphology_scripts:
        print(f"\nExtracting {desc}...")
        subprocess.run([sys.executable, script], cwd=wiktionary_dir, check=True, timeout=timeout)

    # Step 3: Combine morphology
    print("\nCombining all Ancient Greek morphology...")
    subprocess.run([sys.executable, "combine_all_ancient_greek_morphology.py"], cwd=wiktionary_dir, check=True, timeout=300)

    # Step 4: Extract dictionary data
    print("\n\nSTEP 3: EXTRACTING DICTIONARY DATA")

    dictionary_scripts = [
        ("extract_cunliffe_new.py", "Cunliffe dictionary", 300),
        ("extract_lsj_fixed.py", "LSJ dictionary", 300),
        ("extract_wiktionary_final.py", "Wiktionary dictionary entries", 600)
    ]

    for script, desc, timeout in dictionary_scripts:
        print(f"\nExtracting {desc}...")
        subprocess.run([sys.executable, script], cwd=build_modules_dir, check=True, timeout=timeout)

    # Step 5: Combine dictionaries and create lemma mappings
    print("\n\nSTEP 4: COMBINING DICTIONARIES")

    # First create the base combined files - use fixed version
    combine_script = build_modules_dir / "quick_combine_minimal_fixed.py"
    if combine_script.exists():
        print("\nCreating combined dictionary and base lemma mappings...")
        subprocess.run([sys.executable, "quick_combine_minimal_fixed.py"], cwd=build_modules_dir, check=True, timeout=300)
    else:
        # Fallback to original if fixed doesn't exist
        combine_script = build_modules_dir / "quick_combine_minimal.py"
        if combine_script.exists():
            print("\nCreating combined dictionary and base lemma mappings...")
            subprocess.run([sys.executable, "quick_combine_minimal.py"], cwd=build_modules_dir, check=True, timeout=300)
        else:
            raise FileNotFoundError("Missing combine script")

    # Step 6: Generate variants
    print("\n\nSTEP 5: GENERATING VARIANTS")

    variant_scripts = [
        ("normalize_unicode.py", "Normalizing Unicode", 60),
        ("add_grave_accent_variants.py", "Adding grave accent variants", 300),
        ("add_enclitic_variants.py", "Adding enclitic variants", 60)
    ]

    for script, desc, timeout in variant_scripts:
        print(f"\n{desc}...")
        subprocess.run([sys.executable, script], cwd=build_modules_dir, check=True, timeout=timeout)

    print("\n✓ Pipeline complete")

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

    # Create prefix_assimilation_rules table for compound word decomposition
    cursor.execute("DROP TABLE IF EXISTS prefix_assimilation_rules")
    cursor.execute("""
        CREATE TABLE prefix_assimilation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            base_prefix TEXT NOT NULL,
            assimilated_form TEXT NOT NULL,
            meaning TEXT,
            phonological_rule TEXT,
            priority INTEGER NOT NULL,
            examples TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prefix_assimilation_language
        ON prefix_assimilation_rules(language)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prefix_assimilation_base
        ON prefix_assimilation_rules(base_prefix)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prefix_assimilation_form
        ON prefix_assimilation_rules(assimilated_form)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prefix_assimilation_lang_priority
        ON prefix_assimilation_rules(language, priority)
    """)

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

        # CRITICAL: Normalize headword to NFC form for consistent storage
        headword_nfc = unicodedata.normalize('NFC', entry['headword'])

        # Compute ultra-normalized form for Greek words
        headword_ultra = normalize_greek_ultra(headword_nfc) if entry['language'] == 'greek' else None

        cursor.execute("""
            INSERT INTO dictionary_entries
            (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            headword_nfc,
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

    # Convert treebank format to our mapping format with frequency-based confidence
    lemmas_dict = treebank_data['lemmas']
    counts_dict = treebank_data['counts']

    # Calculate frequency-weighted confidence for each mapping
    for form, lemmas in lemmas_dict.items():
        # Get total count for this form across all lemmas
        total_count_for_form = sum(counts_dict.get(f"{form}|||{l}", 0) for l in lemmas)

        for lemma in lemmas:
            # Get count for this specific form->lemma mapping
            count = counts_dict.get(f"{form}|||{lemma}", 1)
            frequency_weight = count / total_count_for_form if total_count_for_form > 0 else 1.0

            # Base confidence 0.95 for treebank, weighted by frequency
            # Examples:
            # - καὶ → καί appears 50,000 times out of 50,008 total καὶ occurrences = 0.9998 * 0.95 = 0.9498
            # - καὶ → φαίνω appears 4 times out of 50,008 total καὶ occurrences = 0.00008 * 0.95 = 0.000076
            # - καὶ → υνκνοων appears 4 times out of 50,008 total καὶ occurrences = 0.00008 * 0.95 = 0.000076
            base_confidence = 0.95
            weighted_confidence = base_confidence * frequency_weight

            treebank_mappings.append({
                'word_form': form,
                'lemma': lemma,
                'confidence': weighted_confidence,
                'source': 'perseus_treebank',
                'morph_info': ''
            })

    print(f"  Loaded {len(treebank_mappings)} Perseus Treebank mappings with frequency-weighted confidence")
    
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
        # CRITICAL: Normalize to NFC form before storing
        # This ensures consistent storage format that matches user input (NFC)
        # Wiktionary data comes in partially decomposed form, but SQLite doesn't
        # consistently normalize, so we must do it explicitly
        word_form_nfc = unicodedata.normalize('NFC', mapping['word_form'])
        # Normalize apostrophe variants to U+02BC to match lookup normalization
        word_form_nfc = (word_form_nfc
            .replace("'", "ʼ")      # U+0027 APOSTROPHE → U+02BC
            .replace("\u2019", "ʼ")  # U+2019 RIGHT SINGLE QUOTATION MARK → U+02BC
            .replace("᾿", "ʼ")      # U+1FBF GREEK PSILI → U+02BC
            .replace("᾽", "ʼ")      # U+1FBD GREEK KORONIS → U+02BC
            .replace("′", "ʼ")      # U+2032 PRIME → U+02BC
            .replace("´", "ʼ"))     # U+00B4 ACUTE ACCENT → U+02BC
        lemma_nfc = unicodedata.normalize('NFC', mapping['lemma'])

        # Compute ultra-normalized form (removes all diacritics)
        word_form_ultra = normalize_greek_ultra(word_form_nfc)

        cursor.execute("""
            INSERT OR IGNORE INTO lemma_map
            (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            word_form_nfc,
            word_form_ultra,
            lemma_nfc,
            mapping.get('confidence', 1.0),
            mapping.get('source', ''),
            mapping.get('morph_info')
        ))
        mappings_imported += 1
        
        if mappings_imported % 10000 == 0:
            print(f"  Imported {mappings_imported} mappings...")
    
    print(f"✓ Imported {mappings_imported} lemma mappings")
    
    # Load Whitaker's Latin dictionary and morphology (full and extended databases only).
    # skip_latin=True is set by the monolith after the Latin-module extraction,
    # because Latin dict data will be merged in from latin/latin_texts.db later.
    if skip_latin:
        print(f"  Skipping Whitaker's Latin (Latin module will merge it in)")
    elif build_mode in ['full', 'extended']:
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

    # Load prefix assimilation rules for compound word decomposition
    print("\nLoading prefix assimilation rules...")
    import csv
    import os

    # Get the data-prep directory (parent of build_modules)
    data_prep_dir = Path(__file__).parent.parent
    assimilation_rules_dir = data_prep_dir / "prefix_assimilation_rules"

    rules_imported = 0

    # Import Greek prefix assimilation rules
    greek_rules_file = assimilation_rules_dir / "greek_prefix_assimilation_rules.csv"
    if greek_rules_file.exists():
        with open(greek_rules_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute('''
                    INSERT INTO prefix_assimilation_rules
                    (language, base_prefix, assimilated_form, meaning, phonological_rule, priority, examples)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['language'],
                    row['base_prefix'],
                    row['assimilated_form'],
                    row.get('meaning', ''),
                    row.get('phonological_rule', ''),
                    int(row['priority']),
                    row.get('examples', '')
                ))
                rules_imported += 1
        print(f"  ✓ Imported {rules_imported} Greek prefix assimilation rules")
    else:
        print(f"  ⚠ Greek prefix assimilation rules not found: {greek_rules_file}")

    # Import Latin prefix assimilation rules (skipped when the Latin module
    # will merge its own rules in from latin/latin_texts.db).
    if skip_latin:
        print(f"  Skipping Latin prefix assimilation rules (Latin module will merge them)")
    else:
        latin_rules_file = assimilation_rules_dir / "latin_prefix_assimilation_rules.csv"
        if latin_rules_file.exists():
            latin_rules_count = 0
            with open(latin_rules_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute('''
                        INSERT INTO prefix_assimilation_rules
                        (language, base_prefix, assimilated_form, meaning, phonological_rule, priority, examples)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['language'],
                        row['base_prefix'],
                        row['assimilated_form'],
                        row.get('meaning', ''),
                        row.get('phonological_rule', ''),
                        int(row['priority']),
                        row.get('examples', '')
                    ))
                    latin_rules_count += 1
            print(f"  ✓ Imported {latin_rules_count} Latin prefix assimilation rules")
            rules_imported += latin_rules_count
        else:
            print(f"  ⚠ Latin prefix assimilation rules not found: {latin_rules_file}")

    print(f"  Total prefix assimilation rules: {rules_imported}")

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