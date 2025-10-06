#!/usr/bin/env python3
"""
Test morphology coverage with normalized matching (preserving vowels)
"""

import csv
import sqlite3
from pathlib import Path
from normalize_arabic import normalize_arabic_for_matching

SCRIPT_DIR = Path(__file__).parent
MORPHOLOGY_FILE = SCRIPT_DIR / "arabic_morphology.csv"
TEXT_DB = SCRIPT_DIR / "arabic_texts.db"

def main():
    print("="*60)
    print("Normalized Match Coverage Test (Vowels Preserved)")
    print("="*60)
    print()

    # Load morphology mappings with normalized index
    print(f"Loading morphology from {MORPHOLOGY_FILE}...")
    morphology_index = {}  # normalized_word -> (original_word, lemma)
    with open(MORPHOLOGY_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word_norm = row['word_normalized']
            word = row['word']
            lemma = row['lemma']
            if word_norm not in morphology_index:
                morphology_index[word_norm] = []
            morphology_index[word_norm].append((word, lemma))

    print(f"Loaded {len(morphology_index):,} normalized forms")
    print()

    # Load text corpus words
    print(f"Loading text words from {TEXT_DB}...")
    conn = sqlite3.connect(TEXT_DB)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT word FROM words")
    text_words = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"Loaded {len(text_words):,} unique text words")
    print()

    # Test coverage with normalized matching
    print("Testing coverage with normalized matching...")
    print("(Removes shadda, sukun, tanween but KEEPS vowels)")
    print()
    matched = 0
    unmatched = []
    matches = []

    for word in text_words:
        # Normalize corpus word for matching
        word_norm = normalize_arabic_for_matching(word)

        if word_norm in morphology_index:
            matched += 1
            wikt_word, lemma = morphology_index[word_norm][0]
            matches.append((word, lemma, wikt_word))
        else:
            unmatched.append(word)

    coverage_pct = (matched / len(text_words) * 100) if text_words else 0

    print(f"{'='*60}")
    print(f"RESULTS (NORMALIZED MATCHING)")
    print(f"{'='*60}")
    print(f"Total text words: {len(text_words):,}")
    print(f"Words with matches: {matched:,}")
    print(f"Words without matches: {len(unmatched):,}")
    print(f"Coverage: {coverage_pct:.1f}%")

    # Show sample matches
    print(f"\n{'='*60}")
    print(f"SAMPLE MATCHES ({min(15, len(matches))} of {len(matches)})")
    print(f"{'='*60}")
    for word, lemma, wikt_word in matches[:15]:
        print(f"{word:20} → {lemma:20} (via {wikt_word})")

    # Show sample unmatched
    print(f"\n{'='*60}")
    print(f"SAMPLE UNMATCHED ({min(10, len(unmatched))} of {len(unmatched)})")
    print(f"{'='*60}")
    for word in unmatched[:10]:
        print(f"  {word}")

    print(f"\n{'='*60}")
    print(f"NORMALIZATION STRATEGY")
    print(f"{'='*60}")
    print("REMOVES (for matching):")
    print("  ّ (shadda), ْ (sukun), ً ٌ ٍ (tanween)")
    print()
    print("PRESERVES (semantically meaningful):")
    print("  َ (fatha), ُ (damma), ِ (kasra) - vowels")
    print()
    print("Example: أسْوَدَ → أسوَدَ (sukun removed, vowels kept)")
    print()
    print("This allows flexible matching while preserving word meaning.")

if __name__ == "__main__":
    main()
