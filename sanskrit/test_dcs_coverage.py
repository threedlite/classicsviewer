#!/usr/bin/env python3
"""
Test DCS lexicon coverage on Bhagavad Gita vocabulary.
"""

import csv
import sqlite3
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
BG_DB = SCRIPT_DIR / "sanskrit_texts.db"
DCS_DICT_CSV = SCRIPT_DIR / "dcs_sanskrit_dictionary.csv"
DCS_MORPH_CSV = SCRIPT_DIR / "dcs_sanskrit_morphology.csv"


def load_bg_vocabulary():
    """Load Bhagavad Gita vocabulary from database."""
    if not BG_DB.exists():
        print(f"ERROR: Database not found: {BG_DB}")
        print("Run: python3 create_sanskrit_texts.py")
        return set()

    conn = sqlite3.connect(BG_DB)
    cursor = conn.cursor()

    # Get unique normalized words
    cursor.execute("""
        SELECT DISTINCT word_normalized
        FROM words
        ORDER BY word_normalized
    """)

    words = set(row[0] for row in cursor.fetchall())
    conn.close()

    return words


def load_dcs_dictionary():
    """Load DCS dictionary lemmas."""
    lemmas = set()
    with open(DCS_DICT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemmas.add(row['lemma'])
    return lemmas


def load_dcs_morphology():
    """Load DCS morphology word forms."""
    word_forms = set()
    with open(DCS_MORPH_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word_forms.add(row['word_form'])
    return word_forms


def main():
    print("=" * 60)
    print("Bhagavad Gita Vocabulary Coverage Test (DCS Data)")
    print("=" * 60)
    print()

    # Load data
    print("Loading Bhagavad Gita vocabulary...")
    bg_vocab = load_bg_vocabulary()
    print(f"  Found {len(bg_vocab):,} unique words in Bhagavad Gita")

    print("Loading DCS dictionary...")
    dict_lemmas = load_dcs_dictionary()
    print(f"  Loaded {len(dict_lemmas):,} dictionary lemmas")

    print("Loading DCS morphology...")
    morph_forms = load_dcs_morphology()
    print(f"  Loaded {len(morph_forms):,} morphological forms")

    # Calculate coverage
    print()
    print("=" * 60)
    print("Coverage Analysis")
    print("=" * 60)
    print()

    found_in_dict = bg_vocab & dict_lemmas
    found_in_morph = bg_vocab & morph_forms
    found_total = found_in_dict | found_in_morph
    missing = bg_vocab - found_total

    total_count = len(bg_vocab)
    dict_count = len(found_in_dict)
    morph_count = len(found_in_morph)
    found_count = len(found_total)
    missing_count = len(missing)

    print(f"Total BG words:           {total_count:,}")
    print(f"Found in dictionary:      {dict_count:,} ({dict_count/total_count*100:.1f}%)")
    print(f"Found in morphology:      {morph_count:,} ({morph_count/total_count*100:.1f}%)")
    print(f"Found (total):            {found_count:,} ({found_count/total_count*100:.1f}%)")
    print(f"Missing:                  {missing_count:,} ({missing_count/total_count*100:.1f}%)")

    # Determine quality rating
    coverage_pct = found_count / total_count * 100
    print()
    print("=" * 60)
    if coverage_pct >= 90:
        print("✅ EXCELLENT: Coverage ≥90%")
    elif coverage_pct >= 70:
        print("✅ GOOD: Coverage ≥70%")
    elif coverage_pct >= 50:
        print("⚠️  FAIR: Coverage ≥50%")
    else:
        print("❌ POOR: Coverage <50% - insufficient")
    print("=" * 60)

    # Show sample missing words
    if missing:
        print()
        print(f"Sample missing words (first 20):")
        for i, word in enumerate(sorted(missing)[:20], 1):
            print(f"{i:4}. {word}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20:,} more")

    # Breakdown
    only_dict = found_in_dict - found_in_morph
    only_morph = found_in_morph - found_in_dict
    both = found_in_dict & found_in_morph

    print()
    print("=" * 60)
    print("Coverage Breakdown")
    print("=" * 60)
    print(f"Dictionary only:          {len(only_dict):,}")
    print(f"Morphology only:          {len(only_morph):,}")
    print(f"Both dict + morph:        {len(both):,}")
    print("=" * 60)

    # Save missing words
    if missing:
        missing_file = SCRIPT_DIR / "dcs_missing_words.txt"
        with open(missing_file, 'w', encoding='utf-8') as f:
            for word in sorted(missing):
                f.write(f"{word}\n")
        print()
        print(f"Missing words saved to: {missing_file.name}")


if __name__ == "__main__":
    main()
