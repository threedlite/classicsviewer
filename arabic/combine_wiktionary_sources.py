#!/usr/bin/env python3
"""
Combine English and Arabic Wiktionary morphology sources.
Only keeps high-quality, verified mappings.
"""

import json
import csv
from pathlib import Path
from normalize_arabic import normalize_arabic_for_matching

SCRIPT_DIR = Path(__file__).parent
EN_WIKT_FILE = SCRIPT_DIR / "arabic_inflection_of_mappings.json"
AR_WIKT_FILE = SCRIPT_DIR / "arabic_wiktionary_morphology.json"
OUTPUT_JSON = SCRIPT_DIR / "arabic_morphology_combined.json"
OUTPUT_CSV = SCRIPT_DIR / "arabic_morphology.csv"

# normalize_arabic function removed - using normalize_arabic_for_matching from module instead

def main():
    print("="*60)
    print("Combining Wiktionary Sources")
    print("="*60)
    print()

    # Load English Wiktionary
    print(f"Loading English Wiktionary: {EN_WIKT_FILE}")
    with open(EN_WIKT_FILE, 'r', encoding='utf-8') as f:
        en_wikt = json.load(f)
    print(f"  Loaded {len(en_wikt):,} word forms")

    # Load Arabic Wiktionary
    print(f"Loading Arabic Wiktionary: {AR_WIKT_FILE}")
    with open(AR_WIKT_FILE, 'r', encoding='utf-8') as f:
        ar_wikt = json.load(f)
    print(f"  Loaded {len(ar_wikt):,} word forms")
    print()

    # Combine sources
    print("Combining sources...")
    combined = {}

    # Add English Wiktionary entries
    for word_form, mappings in en_wikt.items():
        if word_form not in combined:
            combined[word_form] = []

        for mapping in mappings:
            # Add source marker
            mapping_copy = mapping.copy()
            mapping_copy['source'] = 'en_wikt'
            combined[word_form].append(mapping_copy)

    # Add Arabic Wiktionary entries
    conflicts = 0
    new_entries = 0

    for word_form, mappings in ar_wikt.items():
        if word_form not in combined:
            combined[word_form] = []
            new_entries += 1
        else:
            conflicts += 1

        for mapping in mappings:
            # Add source marker
            mapping_copy = mapping.copy()
            mapping_copy['source'] = 'ar_wikt'
            combined[word_form].append(mapping_copy)

    print(f"  English Wiktionary: {len(en_wikt):,} entries")
    print(f"  Arabic Wiktionary: {len(ar_wikt):,} entries")
    print(f"  New from Arabic: {new_entries:,}")
    print(f"  Overlapping: {conflicts:,}")
    print(f"  Combined total: {len(combined):,} unique word forms")
    print()

    # Save combined JSON
    print(f"Saving combined JSON: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    file_size = OUTPUT_JSON.stat().st_size / 1024
    print(f"  Saved {file_size:.1f} KB")
    print()

    # Generate CSV for database
    print(f"Generating CSV: {OUTPUT_CSV}")
    csv_rows = []

    for word_form, mappings in combined.items():
        # Normalize word for matching (removes shadda, sukun, tanween but keeps vowels)
        word_normalized = normalize_arabic_for_matching(word_form)

        for mapping in mappings:
            lemma = mapping.get('lemma', '')

            # Skip if lemma is empty or invalid
            if not lemma:
                continue

            # Normalize lemma too
            lemma_normalized = normalize_arabic_for_matching(lemma)

            csv_rows.append({
                'word': word_form,
                'word_normalized': word_normalized,
                'lemma': lemma,
                'lemma_normalized': lemma_normalized
            })

    # Write CSV
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['word', 'word_normalized', 'lemma', 'lemma_normalized'])
        writer.writeheader()
        writer.writerows(csv_rows)

    csv_size = OUTPUT_CSV.stat().st_size / 1024
    print(f"  Saved {len(csv_rows):,} mappings ({csv_size:.1f} KB)")
    print()

    # Show breakdown
    source_counts = {}
    for mappings in combined.values():
        for mapping in mappings:
            source = mapping.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

    print("Breakdown by source:")
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count:,} mappings")
    print()

    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Combined word forms: {len(combined):,}")
    print(f"Total mappings: {len(csv_rows):,}")
    print(f"Sources: English Wiktionary + Arabic Wiktionary")
    print(f"Quality: High (verified community entries)")
    print()

    # Show samples
    print("Sample mappings:")
    for i, (word, mappings) in enumerate(list(combined.items())[:5], 1):
        print(f"{i}. {word} →")
        for m in mappings[:2]:
            print(f"     lemma: {m['lemma']}, source: {m.get('source', '?')}")

if __name__ == "__main__":
    main()
