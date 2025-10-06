#!/usr/bin/env python3
"""
Create Sumerian Lexicon Package for Classics Viewer

This script creates a Sumerian lexicon package containing:
- ePSD2 (electronic Pennsylvania Sumerian Dictionary) entries
- Morphological forms and normalizations
- Guide words (meanings) and part of speech

Usage:
    python3 create_sumerian_lexicon.py              # Use existing ePSD2 data
    python3 create_sumerian_lexicon.py --download   # Download fresh from ORACC
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
EPSD2_ZIP = DATA_SOURCES / 'epsd2.zip'
EPSD2_GLOSSARY = DATA_SOURCES / 'epsd2' / 'gloss-sux.json'

# Output files
DICTIONARY_CSV = SCRIPT_DIR / 'sumerian_dictionary.csv'
MORPHOLOGY_CSV = SCRIPT_DIR / 'sumerian_morphology.csv'
OUTPUT_ZIP = SCRIPT_DIR / 'sumerian_lexicon.zip'

def download_epsd2():
    """Download ePSD2 from ORACC"""
    import subprocess

    print("\n" + "="*60)
    print("DOWNLOADING ePSD2 FROM ORACC")
    print("="*60)
    print()

    url = "http://oracc.museum.upenn.edu/json/epsd2.zip"

    print(f"Downloading from: {url}")
    print(f"Destination: {EPSD2_ZIP}")
    print("This will download ~203 MB and may take several minutes...")
    print()

    try:
        result = subprocess.run(
            ['wget', '--no-check-certificate', '-c', url, '-O', str(EPSD2_ZIP)],
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
            ['unzip', '-q', '-o', str(EPSD2_ZIP), 'epsd2/gloss-sux.json', '-d', str(DATA_SOURCES)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"ERROR: Extraction failed")
            return False

        print(f"✓ Extracted to: {EPSD2_GLOSSARY}")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_source_files():
    """Check if source files exist"""
    if not EPSD2_GLOSSARY.exists():
        print(f"ERROR: ePSD2 glossary not found at {EPSD2_GLOSSARY}")
        print("Run with --download to fetch from ORACC")
        return False

    print(f"✓ ePSD2 glossary: {EPSD2_GLOSSARY} ({EPSD2_GLOSSARY.stat().st_size / 1024 / 1024:.1f} MB)")
    return True

def convert_epsd2_to_csv():
    """Convert ePSD2 JSON to CSV format"""
    print("\n" + "="*60)
    print("CONVERTING ePSD2 TO CSV")
    print("="*60)
    print()

    print(f"Loading glossary from: {EPSD2_GLOSSARY}")

    with open(EPSD2_GLOSSARY, 'r', encoding='utf-8') as f:
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
                'language': 'sumerian',
                'definition': definition,
                'transliteration': '',
                'html_definition': '',
                'source_name': 'ePSD2'
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
                    'source_name': 'ePSD2',
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
                    'source_name': 'ePSD2',
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
        description='Create Sumerian Lexicon Package from ePSD2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_sumerian_lexicon.py              # Use existing ePSD2 data
  python3 create_sumerian_lexicon.py --download   # Download fresh from ORACC

The package includes:
  - ePSD2 Dictionary (15,940+ entries)
  - Morphological forms and normalizations
  - Guide words (English meanings)

License: CC BY-SA (Creative Commons Attribution-ShareAlike)
Copyright: The Pennsylvania Sumerian Dictionary Project, 2017-
Source: http://oracc.museum.upenn.edu/epsd2/
        """
    )

    parser.add_argument(
        '--download',
        action='store_true',
        help='Download fresh ePSD2 data from ORACC (~203 MB)'
    )

    args = parser.parse_args()

    print("="*60)
    print("Sumerian Lexicon Package Creator")
    print("="*60)
    print()

    # Download if requested
    if args.download:
        if not download_epsd2():
            return 1

    # Check source files
    if not check_source_files():
        return 1

    # Convert to CSV
    if not convert_epsd2_to_csv():
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
    print("  1. Copy sumerian_lexicon.zip to app assets")
    print("  2. Import lexicon in app settings")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
