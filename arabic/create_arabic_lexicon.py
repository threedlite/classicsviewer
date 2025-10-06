#!/usr/bin/env python3
"""
Create Arabic Lexicon Package for Classics Viewer

This script creates a complete Arabic lexicon package containing:
- Lane's Classical Arabic Lexicon dictionary
- Wiktionary morphology (English + Arabic sources)
- Normalization rules for vowel-preserving matching

Usage:
    python3 create_arabic_lexicon.py              # Use existing morphology
    python3 create_arabic_lexicon.py --rebuild    # Rebuild morphology from Wiktionary dumps
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import zipfile

SCRIPT_DIR = Path(__file__).parent

# Required source files
REQUIRED_FILES = {
    'dictionary': SCRIPT_DIR / 'arabic_dictionary.csv',
    'normalization': SCRIPT_DIR / 'normalization_rules_arabic.csv',
    'normalize_module': SCRIPT_DIR / 'normalize_arabic.py',
}

# Morphology pipeline scripts (in order)
MORPHOLOGY_SCRIPTS = [
    'extract_all_arabic_pages_from_enwiktionary.py',
    'extract_arabic_inflection_of.py',
    'extract_all_arabic_wiktionary_pages.py',
    'extract_arabic_wiktionary_patterns.py',
    'combine_wiktionary_sources.py',
]

# Output files
MORPHOLOGY_FILE = SCRIPT_DIR / 'arabic_morphology.csv'
OUTPUT_ZIP = SCRIPT_DIR / 'arabic_lexicon.zip'

def check_file_exists(filepath, description):
    """Check if required file exists"""
    if not filepath.exists():
        print(f"ERROR: {description} not found at {filepath}")
        return False
    return True

def run_script(script_name):
    """Run a Python script and handle errors"""
    script_path = SCRIPT_DIR / script_name

    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print(f"{'='*60}")

    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"ERROR: Script failed with exit code {result.returncode}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print(f"ERROR: Script timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Failed to run script: {e}")
        return False

def rebuild_morphology():
    """Rebuild morphology from Wiktionary dumps"""
    print("\n" + "="*60)
    print("REBUILDING MORPHOLOGY FROM WIKTIONARY")
    print("="*60)
    print("\nThis will take several minutes and requires:")
    print("  - English Wiktionary dump (enwiktionary-latest-pages-articles.xml.bz2)")
    print("  - Arabic Wiktionary dump (arwiktionary-latest-pages-articles.xml.bz2)")
    print("\nBoth should be in: ../data-sources/")
    print()

    # Check for dumps
    dumps_dir = SCRIPT_DIR.parent / 'data-sources'
    en_dump = dumps_dir / 'enwiktionary-latest-pages-articles.xml.bz2'
    ar_dump = dumps_dir / 'arwiktionary-latest-pages-articles.xml.bz2'

    if not en_dump.exists():
        print(f"ERROR: English Wiktionary dump not found at {en_dump}")
        print("Download from: https://dumps.wikimedia.org/enwiktionary/latest/")
        return False

    if not ar_dump.exists():
        print(f"ERROR: Arabic Wiktionary dump not found at {ar_dump}")
        print("Download from: https://dumps.wikimedia.org/arwiktionary/latest/")
        return False

    print(f"✓ English Wiktionary dump: {en_dump.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"✓ Arabic Wiktionary dump: {ar_dump.stat().st_size / 1024 / 1024:.1f} MB")
    print()

    # Run morphology extraction pipeline
    for script in MORPHOLOGY_SCRIPTS:
        if not run_script(script):
            print(f"\nERROR: Morphology pipeline failed at {script}")
            return False

    # Verify output
    if not MORPHOLOGY_FILE.exists():
        print(f"\nERROR: Morphology file not created: {MORPHOLOGY_FILE}")
        return False

    print("\n" + "="*60)
    print("✓ Morphology rebuilt successfully")
    print(f"  Output: {MORPHOLOGY_FILE} ({MORPHOLOGY_FILE.stat().st_size / 1024:.1f} KB)")
    print("="*60)

    return True

def verify_morphology():
    """Verify morphology file exists and has expected structure"""
    if not MORPHOLOGY_FILE.exists():
        print(f"ERROR: Morphology file not found: {MORPHOLOGY_FILE}")
        return False

    # Quick validation
    import csv
    try:
        with open(MORPHOLOGY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader)
            required_cols = {'word', 'word_normalized', 'lemma', 'lemma_normalized'}
            if not required_cols.issubset(first_row.keys()):
                print(f"ERROR: Morphology file missing columns: {required_cols - set(first_row.keys())}")
                return False

        print(f"✓ Morphology file: {MORPHOLOGY_FILE} ({MORPHOLOGY_FILE.stat().st_size / 1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"ERROR: Failed to validate morphology file: {e}")
        return False

def create_lexicon_package():
    """Create the final lexicon ZIP package"""
    print("\n" + "="*60)
    print("CREATING LEXICON PACKAGE")
    print("="*60)
    print()

    # Files to include in package
    files_to_package = [
        ('arabic_dictionary.csv', REQUIRED_FILES['dictionary']),
        ('arabic_morphology.csv', MORPHOLOGY_FILE),
        ('normalization_rules_arabic.csv', REQUIRED_FILES['normalization']),
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

        # Show contents summary
        print("Package contents:")
        for name, path in files_to_package:
            print(f"  - {name}")

        return True

    except Exception as e:
        print(f"ERROR: Failed to create ZIP: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Create Arabic Lexicon Package for Classics Viewer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_arabic_lexicon.py              # Use existing morphology
  python3 create_arabic_lexicon.py --rebuild    # Rebuild from Wiktionary dumps

The package includes:
  - Lane's Classical Arabic Lexicon (43,913 entries)
  - Wiktionary morphology (6,056 entries from English + Arabic Wiktionary)
  - Normalization rules for vowel-preserving matching

Expected coverage on Classical Arabic texts:
  - Direct dictionary matches: ~10%
  - Morphology matches: ~0.5%
  - Total coverage: ~10.1%
        """
    )

    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Rebuild morphology from Wiktionary dumps (takes several minutes)'
    )

    args = parser.parse_args()

    print("="*60)
    print("Arabic Lexicon Package Creator")
    print("="*60)
    print()

    # Check required files
    print("Checking required files...")
    for name, path in REQUIRED_FILES.items():
        if not check_file_exists(path, name):
            return 1

    print("✓ All required files found")
    print()

    # Handle morphology
    if args.rebuild:
        if not rebuild_morphology():
            print("\nERROR: Morphology rebuild failed")
            return 1
    else:
        print("Using existing morphology (use --rebuild to regenerate)")
        if not verify_morphology():
            print("\nERROR: Morphology file invalid or missing")
            print("Run with --rebuild to generate morphology from Wiktionary dumps")
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
    print("  1. Copy arabic_lexicon.zip to app assets")
    print("  2. Import lexicon in app settings")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
