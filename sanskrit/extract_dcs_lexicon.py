#!/usr/bin/env python3
"""
Extract Sanskrit lexicon from Oliver Hellwig's Digital Corpus of Sanskrit (DCS).

Data source: https://github.com/OliverHellwig/sanskrit
License: CC BY 4.0

Note: DCS data is in IAST transliteration. This script converts to Devanagari.
"""

import csv
import json
import os
import re
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from indic_transliteration import sanscript

# Suppress sanskrit_parser warnings
os.environ['SANSKRIT_PARSER_LOG_LEVEL'] = 'ERROR'
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.ERROR)

# Paths
SCRIPT_DIR = Path(__file__).parent
DCS_ROOT = SCRIPT_DIR.parent / "data-sources" / "sanskrit" / "dcs" / "data" / "conllu"
DICTIONARY_CSV = DCS_ROOT / "lookup" / "dictionary.csv"
CONLLU_DIR = DCS_ROOT / "files"

# Output files
DCS_DICT_OUTPUT = SCRIPT_DIR / "dcs_sanskrit_dictionary.csv"
DCS_MORPH_OUTPUT = SCRIPT_DIR / "dcs_sanskrit_morphology.csv"
DCS_STATS_OUTPUT = SCRIPT_DIR / "dcs_extraction_stats.json"


def iast_to_devanagari(text):
    """Convert IAST transliteration to Devanagari script."""
    if not text or text == '_':
        return text
    try:
        return sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except:
        return text  # Return original if conversion fails


def parse_misc_field(misc_str):
    """Parse the MISC field (column 10) from CoNLL-U format."""
    if not misc_str or misc_str == '_':
        return {}

    result = {}
    for pair in misc_str.split('|'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    return result


def extract_dictionary():
    """Extract dictionary from DCS lookup/dictionary.csv."""
    print("=" * 60)
    print("Extracting DCS Dictionary")
    print("=" * 60)

    lemmas = {}

    with open(DICTIONARY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            lemma_id = row['id']
            word_iast = row['word']
            word_deva = iast_to_devanagari(word_iast)
            grammar = row['grammar']
            meanings = row['meanings']
            preverbs = row['preverbs']

            # Store with lemma_id as key for lookup
            lemmas[lemma_id] = {
                'word': word_deva,
                'word_iast': word_iast,
                'grammar': grammar,
                'meanings': meanings,
                'preverbs': preverbs
            }

    print(f"Loaded {len(lemmas):,} lemmas from DCS dictionary")

    # Write dictionary CSV
    with open(DCS_DICT_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['lemma', 'language', 'transliteration', 'definition', 'html_definition', 'source_name'])

        for lemma_id, info in lemmas.items():
            lemma = info['word']
            lemma_iast = info['word_iast']
            grammar = info['grammar']
            meanings = info['meanings']

            # Create definition with grammar info
            if grammar and meanings:
                definition = f"({grammar}) {meanings}"
            elif meanings:
                definition = meanings
            elif grammar:
                definition = f"({grammar})"
            else:
                definition = ""

            # Remove control characters (0x00-0x1F except tab/newline/CR, and 0x7F DEL)
            definition = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', definition)

            html_definition = f"<div>{definition}</div>"

            writer.writerow([
                lemma,
                'sanskrit',
                lemma_iast,
                definition,
                html_definition,
                'DCS (Oliver Hellwig)'
            ])

    dict_size_mb = DCS_DICT_OUTPUT.stat().st_size / (1024 * 1024)
    print(f"✅ Dictionary CSV created: {DCS_DICT_OUTPUT.name} ({dict_size_mb:.2f} MB)")
    print(f"   Total lemmas: {len(lemmas):,}")

    return lemmas


def enhance_with_sandhi(morphology_list, word_to_lemma_map):
    """Enhance morphology with sandhi-split compound forms."""
    print("\n" + "=" * 60)
    print("Enhancing with Sandhi Splitting")
    print("=" * 60)

    try:
        # Suppress sanskrit_parser debug logging
        import logging
        logging.getLogger('sanskrit_parser').setLevel(logging.WARNING)

        from sanskrit_parser import Parser

        # Initialize parser
        print("Initializing sandhi parser...")
        parser = Parser(input_encoding='iast', output_encoding='iast', score=False)

        # Build test database to find missing words
        print("Loading Bhagavad Gita vocabulary for testing...")
        bg_db = SCRIPT_DIR / "sanskrit_texts.db"

        if not bg_db.exists():
            print("  Note: sanskrit_texts.db not found, skipping sandhi enhancement")
            return morphology_list, 0, 0

        import sqlite3
        conn = sqlite3.connect(bg_db)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT word FROM words")
        bg_words = set(row[0] for row in cursor.fetchall())
        conn.close()

        print(f"  Found {len(bg_words):,} unique BG words")

        # Find missing words
        morph_forms = set(word_to_lemma_map.keys())
        missing_words = [w for w in bg_words if w and w != '&#160' and w not in morph_forms]

        print(f"  Missing from DCS: {len(missing_words):,} words")

        if not missing_words:
            print("  No missing words to process")
            return morphology_list, 0, 0

        # Process missing words
        splits_found = 0
        mappings_added = 0

        for i, word_deva in enumerate(missing_words, 1):
            if i % 100 == 0:
                print(f"  Processed {i:,}/{len(missing_words):,}, found {splits_found} splits...")

            # Convert to IAST
            word_iast = sanscript.transliterate(word_deva, sanscript.DEVANAGARI, sanscript.IAST)

            try:
                splits = parser.split(word_iast, limit=1)
                if not splits:
                    continue

                # Extract words from Split object
                best_split = splits[0]
                words_str = str(best_split).strip("[]'")
                words_iast = [w.strip().strip("'") for w in words_str.split("', '")]

                # Convert to Devanagari
                split_deva = [sanscript.transliterate(s, sanscript.IAST, sanscript.DEVANAGARI)
                             for s in words_iast]

                # Validate components and add mappings
                valid_found = False
                for component in split_deva:
                    if component in word_to_lemma_map:
                        lemma = word_to_lemma_map[component]
                        morphology_list.append({
                            'word_form': word_deva,
                            'lemma': lemma,
                            'root': '',
                            'pos': 'compound',
                            'language': 'sanskrit',
                            'confidence': 0.9,
                            'source': 'DCS+Sandhi'
                        })
                        mappings_added += 1
                        valid_found = True

                if valid_found:
                    splits_found += 1

            except:
                pass  # Skip failed splits

        print(f"\n✅ Sandhi splits found: {splits_found:,}")
        print(f"✅ New mappings added: {mappings_added:,}")

        return morphology_list, splits_found, mappings_added

    except ImportError:
        print("  Note: sanskrit_parser not installed, skipping sandhi enhancement")
        print("  Install with: pip install sanskrit_parser")
        return morphology_list, 0, 0


def extract_morphology_from_conllu(lemma_dict):
    """Extract morphology mappings from all CoNLL-U files."""
    print("\n" + "=" * 60)
    print("Extracting Morphology from CoNLL-U Files")
    print("=" * 60)

    morphology = []
    stats = defaultdict(int)

    # Get all text directories
    text_dirs = sorted([d for d in CONLLU_DIR.iterdir() if d.is_dir()])
    print(f"Found {len(text_dirs)} text directories")

    for text_dir in text_dirs:
        # Get all .conllu files in this directory
        conllu_files = list(text_dir.glob("*.conllu"))

        for conllu_file in conllu_files:
            stats['files_processed'] += 1

            with open(conllu_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Skip comments and empty lines
                    if line.startswith('#') or line.strip() == '':
                        continue

                    # Skip multiword token lines (they have ranges like 1-2)
                    if '-' in line.split('\t')[0]:
                        continue

                    parts = line.strip().split('\t')
                    if len(parts) < 10:
                        continue

                    word_id = parts[0]
                    form_iast = parts[1]  # The actual form in text (IAST)
                    lemma_iast = parts[2]  # The lemma (IAST)
                    upos = parts[3]   # Universal POS
                    misc = parts[9]   # MISC field

                    if form_iast == '_' or lemma_iast == '_':
                        continue

                    stats['words_processed'] += 1

                    # Convert to Devanagari
                    form = iast_to_devanagari(form_iast)
                    lemma = iast_to_devanagari(lemma_iast)

                    # Parse MISC field
                    misc_dict = parse_misc_field(misc)
                    lemma_id = misc_dict.get('LemmaId', '')
                    unsandhied_iast = misc_dict.get('Unsandhied', form_iast)
                    unsandhied = iast_to_devanagari(unsandhied_iast)

                    # Get grammar info from dictionary
                    grammar = ''
                    if lemma_id and lemma_id in lemma_dict:
                        grammar = lemma_dict[lemma_id].get('grammar', '')

                    # Map POS
                    if upos == '_':
                        upos = 'unknown'

                    # Create morphology mapping
                    # Map both the sandhied form and unsandhied form to the lemma

                    # 1. Map unsandhied form to lemma
                    if unsandhied and unsandhied != lemma:
                        morphology.append({
                            'word_form': unsandhied,
                            'lemma': lemma,
                            'pos': upos.lower(),
                            'confidence': 1.0,
                            'source': 'DCS',
                            'grammar': grammar
                        })
                        stats['unsandhied_forms'] += 1

                    # 2. Map sandhied form to lemma (if different from unsandhied)
                    if form != unsandhied and form != lemma:
                        morphology.append({
                            'word_form': form,
                            'lemma': lemma,
                            'pos': upos.lower(),
                            'confidence': 0.95,
                            'source': 'DCS',
                            'grammar': grammar
                        })
                        stats['sandhied_forms'] += 1

            if stats['files_processed'] % 100 == 0:
                print(f"  Processed {stats['files_processed']:,} files, {stats['words_processed']:,} words...")

    print(f"\n✅ Processed {stats['files_processed']:,} files")
    print(f"   Total words processed: {stats['words_processed']:,}")
    print(f"   Unsandhied forms: {stats['unsandhied_forms']:,}")
    print(f"   Sandhied forms: {stats['sandhied_forms']:,}")
    print(f"   Total morphology mappings: {len(morphology):,}")

    # Build word-to-lemma map for sandhi enhancement
    word_to_lemma = {}
    for mapping in morphology:
        word_form = mapping['word_form']
        if word_form not in word_to_lemma:
            word_to_lemma[word_form] = mapping['lemma']

    # Enhance with sandhi splitting
    morphology, sandhi_splits, sandhi_mappings = enhance_with_sandhi(morphology, word_to_lemma)
    stats['sandhi_splits'] = sandhi_splits
    stats['sandhi_mappings'] = sandhi_mappings

    # Write morphology CSV in format compatible with create_perseus_database.py
    # Format: word_form,lemma,root,pos,language,confidence,source_name
    with open(DCS_MORPH_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['word_form', 'lemma', 'root', 'pos', 'language', 'confidence', 'source_name'])

        # Write all morphology entries (duplicates allowed for frequency tracking)
        for mapping in morphology:
            writer.writerow([
                mapping['word_form'],
                mapping['lemma'],
                '',  # root - leave empty
                mapping['pos'],
                'sanskrit',
                mapping['confidence'],
                mapping['source']
            ])

    morph_size_mb = DCS_MORPH_OUTPUT.stat().st_size / (1024 * 1024)
    print(f"\n✅ Morphology CSV created: {DCS_MORPH_OUTPUT.name} ({morph_size_mb:.2f} MB)")
    print(f"   Total entries: {len(morphology):,} (including {sandhi_mappings:,} sandhi-enhanced)")

    return morphology, stats


def main():
    print("Digital Corpus of Sanskrit (DCS) Lexicon Extraction")
    print("Data source: Oliver Hellwig")
    print("License: CC BY 4.0")
    print()

    # Extract dictionary
    lemma_dict = extract_dictionary()

    # Extract morphology
    morphology, stats = extract_morphology_from_conllu(lemma_dict)

    # Save statistics
    final_stats = {
        'extraction_date': datetime.now().isoformat(),
        'dictionary_entries': len(lemma_dict),
        'morphology_mappings': len(morphology),
        'files_processed': stats['files_processed'],
        'words_processed': stats['words_processed'],
        'unsandhied_forms': stats['unsandhied_forms'],
        'sandhied_forms': stats['sandhied_forms'],
        'sandhi_splits': stats.get('sandhi_splits', 0),
        'sandhi_mappings': stats.get('sandhi_mappings', 0)
    }

    with open(DCS_STATS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_stats, f, indent=2)

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Dictionary entries: {final_stats['dictionary_entries']:,}")
    print(f"Morphology forms:   {final_stats['morphology_mappings']:,}")
    print(f"\nNext step: python3 create_dcs_lexicon.py")


if __name__ == "__main__":
    main()
