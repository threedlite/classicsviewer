#!/usr/bin/env python3
"""
Create Akkadian Lexicon Package for Classics Viewer

This script creates an Akkadian lexicon package containing:
- RINAP (Royal Inscriptions of the Neo-Assyrian Period) Akkadian glossary
- Morphological forms and normalizations
- Guide words (meanings) and part of speech

Usage:
    python3 create_akkadian_lexicon.py              # Use existing RINAP data
    python3 create_akkadian_lexicon.py --download   # Download fresh from ORACC
"""

import argparse
import json
import csv
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_SOURCES = SCRIPT_DIR.parent / 'data-sources'

# Source files
RINAP_ZIP = DATA_SOURCES / 'rinap.zip'
RINAP_GLOSSARY = DATA_SOURCES / 'rinap' / 'gloss-akk.json'

# Output files
DICTIONARY_CSV = SCRIPT_DIR / 'akkadian_dictionary.csv'
MORPHOLOGY_CSV = SCRIPT_DIR / 'akkadian_morphology.csv'
OUTPUT_ZIP = SCRIPT_DIR / 'akkadian_lexicon.zip'

def download_rinap():
    """Download RINAP from ORACC"""
    import subprocess

    print("\n" + "="*60)
    print("DOWNLOADING RINAP FROM ORACC")
    print("="*60)
    print()

    url = "http://oracc.museum.upenn.edu/json/rinap.zip"

    print(f"Downloading from: {url}")
    print(f"Destination: {RINAP_ZIP}")
    print("This will download ~24 MB...")
    print()

    try:
        result = subprocess.run(
            ['wget', '--no-check-certificate', '-c', url, '-O', str(RINAP_ZIP)],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            print(f"ERROR: Download failed")
            print(result.stderr)
            return False

        print(f"\n✓ Downloaded successfully")

        # Extract glossary
        print(f"\nExtracting glossary...")
        result = subprocess.run(
            ['unzip', '-q', '-o', str(RINAP_ZIP), 'rinap/gloss-akk.json', '-d', str(DATA_SOURCES)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"ERROR: Extraction failed")
            return False

        print(f"✓ Extracted to: {RINAP_GLOSSARY}")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_source_files():
    """Check if source files exist"""
    if not RINAP_GLOSSARY.exists():
        print(f"ERROR: RINAP glossary not found at {RINAP_GLOSSARY}")
        print("Run with --download to fetch from ORACC")
        return False

    print(f"✓ RINAP glossary: {RINAP_GLOSSARY} ({RINAP_GLOSSARY.stat().st_size / 1024 / 1024:.1f} MB)")
    return True

def convert_rinap_to_csv():
    """Convert RINAP JSON to CSV format"""
    print("\n" + "="*60)
    print("CONVERTING RINAP TO CSV")
    print("="*60)
    print()

    print(f"Loading glossary from: {RINAP_GLOSSARY}")

    with open(RINAP_GLOSSARY, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data.get('entries', [])
    print(f"Found {len(entries)} dictionary entries")

    # Create dictionary CSV
    print(f"\nCreating dictionary CSV...")
    dict_rows = []
    morph_rows = []

    for entry in entries:
        # Dictionary entry
        cf = entry.get('cf', '')  # Citation form
        gw = entry.get('gw', '')  # Guide word (meaning)
        pos = entry.get('pos', '')  # Part of speech
        headword = entry.get('headword', '')

        if cf and gw:
            # Format definition with POS and guide word
            definition = f"{gw} ({pos})" if pos else gw
            dict_rows.append({
                'lemma': cf,
                'language': 'akkadian',
                'definition': definition,
                'transliteration': '',
                'html_definition': '',
                'source_name': 'RINAP'
            })

        # Morphology - extract forms
        forms = entry.get('forms', [])
        for form in forms:
            form_text = form.get('n', '')  # Form text
            if form_text and cf:
                morph_rows.append({
                    'word_form': form_text,
                    'lemma': cf,
                    'confidence': '1.0',
                    'source_name': 'RINAP',
                    'pos': pos,
                    'root': ''
                })

        # Morphology - extract norms (normalizations)
        norms = entry.get('norms', [])
        for norm in norms:
            norm_text = norm.get('n', '')  # Normalized form
            if norm_text and cf:
                morph_rows.append({
                    'word_form': norm_text,
                    'lemma': cf,
                    'confidence': '1.0',
                    'source_name': 'RINAP',
                    'pos': pos,
                    'root': ''
                })

    # Write dictionary CSV
    with open(DICTIONARY_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['lemma', 'language', 'definition', 'transliteration', 'html_definition', 'source_name'])
        writer.writeheader()
        writer.writerows(dict_rows)

    print(f"✓ Dictionary CSV: {DICTIONARY_CSV} ({len(dict_rows)} entries)")

    # Write morphology CSV
    with open(MORPHOLOGY_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['word_form', 'lemma', 'confidence', 'source_name', 'pos', 'root'])
        writer.writeheader()
        writer.writerows(morph_rows)

    print(f"✓ Morphology CSV: {MORPHOLOGY_CSV} ({len(morph_rows)} forms)")

    return True

def create_lexicon_package():
    """Create the final lexicon ZIP package"""
    print("\n" + "="*60)
    print("CREATING LEXICON PACKAGE")
    print("="*60)
    print()

    files_to_package = [
        ('dictionary.csv', DICTIONARY_CSV),
        ('morphology.csv', MORPHOLOGY_CSV),
    ]

    # Verify all files exist
    for name, path in files_to_package:
        if not path.exists():
            print(f"ERROR: Required file not found: {path}")
            return False
        print(f"✓ {name:40} ({path.stat().st_size / 1024:.1f} KB)")

    print()

    # Create ZIP
    try:
        with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for name, path in files_to_package:
                print(f"  Adding {name}...")
                zf.write(path, name)

        zip_size = OUTPUT_ZIP.stat().st_size / 1024 / 1024

        print()
        print("="*60)
        print("✓ LEXICON PACKAGE CREATED SUCCESSFULLY")
        print("="*60)
        print(f"Output: {OUTPUT_ZIP}")
        print(f"Size: {zip_size:.2f} MB compressed")
        print()

        # Calculate compression ratio
        total_uncompressed = sum(p.stat().st_size for _, p in files_to_package)
        compression_ratio = (1 - (OUTPUT_ZIP.stat().st_size / total_uncompressed)) * 100
        print(f"Compression: {compression_ratio:.1f}% reduction")
        print()

        return True

    except Exception as e:
        print(f"ERROR: Failed to create ZIP: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Create Akkadian Lexicon Package from RINAP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_akkadian_lexicon.py              # Use existing RINAP data
  python3 create_akkadian_lexicon.py --download   # Download fresh from ORACC

The package includes:
  - RINAP Akkadian Dictionary (3,651+ entries)
  - Morphological forms and normalizations
  - Guide words (English meanings)

License: CC BY-SA (Creative Commons Attribution-ShareAlike)
Copyright: RINAP Project, 2011-2022
Source: http://oracc.museum.upenn.edu/rinap/
        """
    )

    parser.add_argument(
        '--download',
        action='store_true',
        help='Download fresh RINAP data from ORACC (~24 MB)'
    )

    args = parser.parse_args()

    print("="*60)
    print("Akkadian Lexicon Package Creator")
    print("="*60)
    print()

    # Download if requested
    if args.download:
        if not download_rinap():
            return 1

    # Check source files
    if not check_source_files():
        return 1

    # Convert to CSV
    if not convert_rinap_to_csv():
        return 1

    # Create package
    if not create_lexicon_package():
        return 1

    print()
    print("="*60)
    print("SUCCESS!")
    print("="*60)
    print(f"Package ready: {OUTPUT_ZIP}")
    print()
    print("Next steps:")
    print("  1. Copy akkadian_lexicon.zip to app assets")
    print("  2. Import lexicon in app settings")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
