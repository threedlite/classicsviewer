#!/usr/bin/env python3
"""
Create Sanskrit Lexicon ZIP from DCS extracted data.
"""

import zipfile
import shutil
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent

# Source files
DCS_DICT_CSV = SCRIPT_DIR / "dcs_sanskrit_dictionary.csv"
DCS_MORPH_CSV = SCRIPT_DIR / "dcs_sanskrit_morphology.csv"
NORM_RULES_SOURCE = SCRIPT_DIR / "normalization_rules_sanskrit.csv"

# Output file
DCS_LEXICON_ZIP = SCRIPT_DIR / "dcs_sanskrit_lexicon.zip"


def create_lexicon_zip():
    """Create lexicon ZIP file for ClassicsViewer import."""
    print("=" * 60)
    print("Creating DCS Sanskrit Lexicon ZIP")
    print("=" * 60)

    if not DCS_DICT_CSV.exists():
        print(f"ERROR: Dictionary file not found: {DCS_DICT_CSV}")
        print("Run: python3 extract_dcs_lexicon.py")
        return False

    if not DCS_MORPH_CSV.exists():
        print(f"ERROR: Morphology file not found: {DCS_MORPH_CSV}")
        print("Run: python3 extract_dcs_lexicon.py")
        return False

    # Temporary file names (will be renamed inside ZIP)
    dict_temp = SCRIPT_DIR / "dictionary.csv"
    morph_temp = SCRIPT_DIR / "morphology.csv"
    norm_temp = SCRIPT_DIR / "normalization_rules.csv"

    # Copy files with correct names
    print(f"  Copying {DCS_DICT_CSV.name} -> dictionary.csv")
    shutil.copy(DCS_DICT_CSV, dict_temp)

    print(f"  Copying {DCS_MORPH_CSV.name} -> morphology.csv")
    shutil.copy(DCS_MORPH_CSV, morph_temp)

    # Check for normalization rules
    has_norm_rules = NORM_RULES_SOURCE.exists()
    if has_norm_rules:
        print(f"  Copying {NORM_RULES_SOURCE.name} -> normalization_rules.csv")
        shutil.copy(NORM_RULES_SOURCE, norm_temp)
    else:
        print(f"  Note: Normalization rules not found at {NORM_RULES_SOURCE}")

    # Create ZIP file
    print(f"  Creating ZIP archive...")
    with zipfile.ZipFile(DCS_LEXICON_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(dict_temp, 'dictionary.csv')
        zipf.write(morph_temp, 'morphology.csv')
        if has_norm_rules:
            zipf.write(norm_temp, 'normalization_rules.csv')

    # Clean up temporary files
    dict_temp.unlink()
    morph_temp.unlink()
    if has_norm_rules:
        norm_temp.unlink()

    # Verify ZIP
    with zipfile.ZipFile(DCS_LEXICON_ZIP, 'r') as zipf:
        file_list = zipf.namelist()
        print(f"  ZIP contains: {file_list}")

        if 'dictionary.csv' not in file_list:
            raise ValueError("ZIP file missing dictionary.csv")

    # Get file size
    zip_size_mb = DCS_LEXICON_ZIP.stat().st_size / (1024 * 1024)
    print(f"\n✅ Created {DCS_LEXICON_ZIP.name} ({zip_size_mb:.2f} MB)")

    # Print statistics
    print(f"\n" + "=" * 60)
    print("Lexicon Statistics")
    print("=" * 60)

    # Count dictionary entries
    with open(DCS_DICT_CSV, 'r', encoding='utf-8') as f:
        dict_count = sum(1 for line in f) - 1  # Subtract header

    # Count morphology entries
    with open(DCS_MORPH_CSV, 'r', encoding='utf-8') as f:
        morph_count = sum(1 for line in f) - 1  # Subtract header

    print(f"Dictionary entries:   {dict_count:,}")
    print(f"Morphology forms:     {morph_count:,}")
    print(f"Total forms:          {dict_count + morph_count:,}")
    print(f"File size:            {zip_size_mb:.2f} MB")

    print(f"\n" + "=" * 60)
    print("SUCCESS: DCS Lexicon package created")
    print("=" * 60)
    print(f"\nTo use in ClassicsViewer:")
    print(f"1. Copy {DCS_LEXICON_ZIP.name} to app assets folder")
    print(f"2. App will extract on first launch")
    print(f"3. Users can look up Sanskrit words → definitions")

    print(f"\nNext step:")
    print(f"  python3 test_dcs_coverage.py")

    return True


def main():
    """Main entry point."""
    success = create_lexicon_zip()
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
