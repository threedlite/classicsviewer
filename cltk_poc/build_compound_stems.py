#!/usr/bin/env python3
"""
Build Greek compound stem mappings from Perseus morphological data.

This extracts genitive stems and other combining forms used in Greek compounds.
"""

import sqlite3
import json
import unicodedata
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List
import sys


def normalize_greek(text: str) -> str:
    """Remove diacritics for comparison."""
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    return text.lower().strip()


def extract_stem_from_inflection(inflected: str) -> str:
    """
    Extract stem by stripping Greek case/tense endings from inflected form.

    Strategy: Strip the longest matching ending to get the stem.
    Example:
    - γυναικός → γυναικ (remove -ός)
    - ἀνθρώπου → ἀνθρωπ (remove -ου)
    """
    inflected_norm = normalize_greek(inflected)

    # Common Greek noun/adjective case endings (sorted by length, longest first)
    case_endings = [
        # Three-letter endings
        'ουσ', 'οισ', 'αισ', 'εων', 'ηων', 'ιων', 'ωνα',
        # Two-letter endings
        'ου', 'ος', 'ον', 'οι', 'ων', 'ας', 'αι', 'ης', 'ει', 'εσ', 'εϲ',
        'ιν', 'ιδ', 'οσ', 'οϲ', 'ηϲ', 'εϲ', 'αϲ',
        # Single-letter endings
        'α', 'η', 'ε', 'ι', 'ο', 'ν', 'ς', 'ϲ'
    ]

    # Try to strip endings (must leave at least 3 chars)
    for ending in case_endings:
        if inflected_norm.endswith(ending) and len(inflected_norm) > len(ending) + 2:
            return inflected_norm[:-len(ending)]

    # Return as-is if no ending matched (might be stem already)
    return inflected_norm


def is_verb_lemma(lemma: str) -> bool:
    """
    Check if lemma is a verb (ends in -ω or -μι).

    Note: This is a heuristic. Some proper nouns end in -ω (e.g., Γοργώ, Σαπφώ)
    but Greek verbs consistently end in -ω (thematic) or -μι (athematic).
    The majority of -ω endings are verbs, so this is a reasonable heuristic.
    """
    lemma_norm = normalize_greek(lemma)

    # Basic verb endings
    if lemma_norm.endswith('μι'):
        return True

    # -ω ending could be verb or proper noun
    # Filter out obvious proper nouns (capitalized in original)
    if lemma_norm.endswith('ω'):
        # If original lemma starts with uppercase, likely proper noun
        if lemma and lemma[0].isupper():
            return False  # Proper noun like Γοργώ, Σαπφώ
        return True  # Likely verb

    return False


def extract_verbal_stems(lemma: str, inflections: List[str]) -> Set[str]:
    """
    Extract verbal stems used in Greek compounds.

    Key stems for compounds:
    - Present stem: πείθω → πειθ
    - Aorist stem: ἔπεισα → πεισ (after removing augment)
    - Perfect stem: πέποιθα → πεποιθ

    Args:
        lemma: Verb lemma (e.g., πείθω)
        inflections: List of inflected forms

    Returns:
        Set of verbal stems
    """
    stems = set()
    lemma_norm = normalize_greek(lemma)

    # Present stem: strip -ω or -μι
    if lemma_norm.endswith('ω'):
        present_stem = lemma_norm[:-1]  # πείθω → πειθ
        if len(present_stem) >= 3:
            stems.add(present_stem)
    elif lemma_norm.endswith('μι'):
        present_stem = lemma_norm[:-2]  # τίθημι → τιθη
        if len(present_stem) >= 3:
            stems.add(present_stem)

    # Extract aorist and perfect stems from inflections
    for infl in inflections:
        infl_norm = normalize_greek(infl)

        # Aorist forms typically have augment ἐ- or ἠ-
        # Example: ἔπεισα → πεισα → πεισ
        if infl_norm.startswith('ε') or infl_norm.startswith('η'):
            # Remove augment
            without_augment = infl_norm[1:]

            # Try to extract stem (remove common aorist endings)
            aorist_endings = ['σα', 'σας', 'σαν', 'σε', 'σεν']
            for ending in aorist_endings:
                if without_augment.endswith(ending) and len(without_augment) > len(ending) + 2:
                    aorist_stem = without_augment[:-len(ending)]
                    if len(aorist_stem) >= 3:
                        stems.add(aorist_stem)
                    break

        # Perfect forms often start with reduplication (πε-, λε-, etc.)
        # Example: πέποιθα → πεποιθ
        if infl_norm.startswith('πε') or infl_norm.startswith('λε') or infl_norm.startswith('κε'):
            # Extract stem after perfect endings
            perfect_endings = ['α', 'ας', 'ε', 'εν', 'ως', 'ωσ', 'οτοσ', 'οτα', 'εναι']
            for ending in perfect_endings:
                if infl_norm.endswith(ending) and len(infl_norm) > len(ending) + 3:
                    perfect_stem = infl_norm[:-len(ending)]
                    if len(perfect_stem) >= 4:  # Perfect stems usually longer
                        stems.add(perfect_stem)
                    break

    return stems


def build_compound_stems_from_perseus(db_path: Path) -> Dict:
    """
    Extract compound stems from Perseus lemma_map table.

    Returns dict mapping normalized lemma → stem info
    """
    print("Building compound stems from Perseus morphological data...")
    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all Greek lemmas with their inflections
    query = """
        SELECT DISTINCT lemma, word_form
        FROM lemma_map
        WHERE lemma IS NOT NULL
        AND word_form IS NOT NULL
        AND LENGTH(lemma) >= 3
        AND LENGTH(word_form) >= 3
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    print(f"Processing {len(rows):,} lemma-inflection pairs...")

    # Build stem mappings
    stem_map = defaultdict(lambda: {
        'lemma': '',
        'lemma_normalized': '',
        'stems': set(),
        'genitive_stems': set(),
        'compound_forms': set(),
        'verbal_stems': set(),
        'is_verb': False
    })

    # Group inflections by lemma for verbal stem extraction
    # Store both normalized and original lemma
    lemma_inflections = defaultdict(lambda: {'original': '', 'inflections': []})
    for lemma, inflected in rows:
        lemma_norm = normalize_greek(lemma)
        if len(lemma_norm) >= 3:
            if not lemma_inflections[lemma_norm]['original']:
                lemma_inflections[lemma_norm]['original'] = lemma
            lemma_inflections[lemma_norm]['inflections'].append(inflected)

    print(f"Grouped into {len(lemma_inflections):,} unique lemmas")

    processed = 0
    verb_count = 0

    for lemma_norm, data in lemma_inflections.items():
        processed += 1
        if processed % 10000 == 0:
            print(f"  Processed {processed:,} / {len(lemma_inflections):,} ({processed/len(lemma_inflections)*100:.1f}%)")

        # Get original lemma (with capitalization)
        lemma = data['original']
        inflections = data['inflections']

        # Check if this is a verb (using original lemma for capitalization check)
        is_verb = is_verb_lemma(lemma)

        stem_map[lemma_norm]['lemma'] = lemma
        stem_map[lemma_norm]['lemma_normalized'] = lemma_norm
        stem_map[lemma_norm]['is_verb'] = is_verb

        if is_verb:
            verb_count += 1
            # Extract verbal stems
            verbal_stems = extract_verbal_stems(lemma_norm, inflections)
            stem_map[lemma_norm]['verbal_stems'].update(verbal_stems)

        # Process all inflections for this lemma
        for inflected in inflections:
            # Extract stem
            stem = extract_stem_from_inflection(inflected)

            if len(stem) >= 3:
                stem_map[lemma_norm]['stems'].add(stem)

                # Identify genitive forms (most common in compounds)
                # Genitive markers: -ου, -ος, -ων, -ας
                inflected_norm = normalize_greek(inflected)
                if any(inflected_norm.endswith(end) for end in ['ου', 'ος', 'ων', 'ας']):
                    stem_map[lemma_norm]['genitive_stems'].add(stem)

                # Add thematic vowel variants (common in compounds)
                if stem[-1] not in ['ο', 'ι']:
                    stem_map[lemma_norm]['compound_forms'].add(stem + 'ο')
                    stem_map[lemma_norm]['compound_forms'].add(stem + 'ι')

    conn.close()

    # Convert sets to lists for JSON serialization
    result = {}
    for lemma_norm, data in stem_map.items():
        result[lemma_norm] = {
            'lemma': data['lemma'],
            'lemma_normalized': data['lemma_normalized'],
            'stems': sorted(list(data['stems'])),
            'genitive_stems': sorted(list(data['genitive_stems'])),
            'compound_forms': sorted(list(data['compound_forms'])),
            'verbal_stems': sorted(list(data['verbal_stems'])),
            'is_verb': data['is_verb']
        }

    print(f"\n✓ Extracted stems for {len(result):,} lemmas")

    # Statistics
    with_genitive = sum(1 for v in result.values() if v['genitive_stems'])
    with_compound = sum(1 for v in result.values() if v['compound_forms'])
    with_verbal = sum(1 for v in result.values() if v['verbal_stems'])

    print(f"  Lemmas with genitive stems: {with_genitive:,}")
    print(f"  Lemmas with compound forms: {with_compound:,}")
    print(f"  Verb lemmas with verbal stems: {with_verbal:,} (total verbs: {verb_count:,})")

    return result


def find_database() -> Path:
    """Find Perseus database with lemma_map table."""
    candidates = [
        Path('../data-prep/perseus_texts_extended.db'),
        Path('../data-prep/perseus_texts_full.db'),
        Path('perseus_texts_extended.db'),
        Path('perseus_texts_full.db'),
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError("Could not find Perseus database with lemma_map table")


def main():
    print("=" * 70)
    print("BUILDING GREEK COMPOUND STEMS DATABASE")
    print("=" * 70)

    # Find database
    try:
        db_path = find_database()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Build stem mappings
    stem_data = build_compound_stems_from_perseus(db_path)

    # Save to JSON
    output_file = Path('greek_compound_stems.json')
    print(f"\nSaving to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stem_data, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved {len(stem_data):,} lemma stem mappings")

    # Show examples
    print("\nExample stem mappings:")
    example_lemmas = ['γυνη', 'ανθρωπος', 'πελοψ', 'ναυς', 'πολις', 'πειθω', 'φιλεω', 'ιστημι']
    for lemma in example_lemmas:
        if lemma in stem_data:
            data = stem_data[lemma]
            print(f"\n  {data['lemma']} ({'VERB' if data['is_verb'] else 'NOUN'}):")
            if data['genitive_stems']:
                print(f"    Genitive stems: {', '.join(data['genitive_stems'][:3])}")
            if data['compound_forms']:
                print(f"    Compound forms: {', '.join(data['compound_forms'][:3])}")
            if data['verbal_stems']:
                print(f"    Verbal stems: {', '.join(data['verbal_stems'][:5])}")

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
