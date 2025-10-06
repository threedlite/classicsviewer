#!/usr/bin/env python3
"""
Extract Arabic inflection mappings from English Wiktionary using {{inflection of|ar|...}} templates.
Similar to extract_inflection_of_template.py for Ancient Greek.

This extracts explicit word form → lemma mappings from English Wiktionary.
"""

import xml.etree.ElementTree as ET
import json
import bz2
import re
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / "all_arabic_enwiktionary_pages.json"
OUTPUT_FILE = SCRIPT_DIR / "arabic_inflection_of_mappings.json"

def extract_inflection_templates(text):
    """
    Extract inflection templates from Arabic entries.

    Example formats:
    {{inflection of|ar|كَتَبَ||past|3|m|s}}
    {{plural of|ar|قَاعِدَة}}
    {{feminine of|ar|صِينِيّ}}
    {{form of|ar|...}}
    """
    if not text:
        return []

    inflections = []

    # Pattern 1: {{inflection of|ar|lemma|...}}
    pattern1 = r'\{\{inflection of\|ar\|([^|}]+)\|([^}]*)\}\}'
    for match in re.finditer(pattern1, text, re.IGNORECASE):
        lemma = match.group(1).strip()
        tags = match.group(2).strip()
        inflections.append({
            'lemma': lemma,
            'tags': tags,
            'type': 'inflection_of'
        })

    # Pattern 2: {{plural of|ar|lemma}}
    pattern2 = r'\{\{plural of\|ar\|([^|}]+)(?:\|([^}]*))?\}\}'
    for match in re.finditer(pattern2, text, re.IGNORECASE):
        lemma = match.group(1).strip()
        tags = match.group(2).strip() if match.group(2) else ''
        inflections.append({
            'lemma': lemma,
            'tags': f'plural|{tags}' if tags else 'plural',
            'type': 'plural_of'
        })

    # Pattern 3: {{feminine of|ar|lemma}}
    pattern3 = r'\{\{feminine of\|ar\|([^|}]+)(?:\|([^}]*))?\}\}'
    for match in re.finditer(pattern3, text, re.IGNORECASE):
        lemma = match.group(1).strip()
        tags = match.group(2).strip() if match.group(2) else ''
        inflections.append({
            'lemma': lemma,
            'tags': f'feminine|{tags}' if tags else 'feminine',
            'type': 'feminine_of'
        })

    # Pattern 4: {{form of|ar|form_type|lemma}}
    # Note: form_of has 3 positional params: language, type, lemma
    pattern4 = r'\{\{form of\|ar\|([^|}]+)\|([^|}]+)(?:\|([^}]*))?\}\}'
    for match in re.finditer(pattern4, text, re.IGNORECASE):
        form_type = match.group(1).strip()  # e.g., "Form", "alternative"
        lemma = match.group(2).strip()       # actual lemma
        extra = match.group(3).strip() if match.group(3) else ''
        inflections.append({
            'lemma': lemma,
            'tags': f'{form_type}|{extra}' if extra else form_type,
            'type': 'form_of'
        })

    return inflections

def is_arabic_section(text):
    """Check if text contains Arabic language section"""
    if not text:
        return False

    # Look for ==Arabic== or similar headers
    arabic_headers = [
        '==Arabic==',
        '== Arabic ==',
        '===Arabic===',
    ]

    return any(header in text for header in arabic_headers)

def extract_from_cache():
    """Extract Arabic inflection mappings from cached English Wiktionary pages"""

    if not CACHE_FILE.exists():
        print(f"ERROR: Cache file not found at {CACHE_FILE}")
        print(f"Run extract_all_arabic_pages_from_enwiktionary.py first to create the cache.")
        raise FileNotFoundError(f"Required cache file: {CACHE_FILE}")

    print(f"Reading cached Arabic pages: {CACHE_FILE}")
    print(f"File size: {CACHE_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    print()
    print("Extracting Arabic inflection templates...")

    # Load cached pages
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        pages = json.load(f)

    print(f"Loaded {len(pages):,} cached Arabic pages")
    print()

    mappings = {}  # word_form -> list of {lemma, tags, type}
    inflection_count = 0

    # Process each cached page
    for word_form, text in pages.items():
        # Extract inflection templates
        inflections = extract_inflection_templates(text)

        if inflections:
            if word_form not in mappings:
                mappings[word_form] = []

            mappings[word_form].extend(inflections)
            inflection_count += len(inflections)

    print(f"✅ Extraction complete:")
    print(f"   Cached pages processed: {len(pages):,}")
    print(f"   Unique word forms with inflections: {len(mappings):,}")
    print(f"   Total inflection mappings: {inflection_count:,}")

    # Show breakdown by type
    type_counts = {}
    for inflections in mappings.values():
        for infl in inflections:
            type_name = infl.get('type', 'unknown')
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

    print(f"\nBreakdown by template type:")
    for type_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {type_name}: {count:,}")

    return mappings

def main():
    print("="*60)
    print("Arabic Inflection Template Extraction")
    print("From English Wiktionary (cached)")
    print("="*60)
    print()

    # Extract mappings from cache
    mappings = extract_from_cache()

    # Save to JSON
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    file_size = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ Saved {len(mappings)} word forms ({file_size:.1f} KB)")

    # Show sample
    print("\nSample mappings:")
    for i, (word, inflections) in enumerate(list(mappings.items())[:5], 1):
        print(f"{i}. {word} →")
        for infl in inflections[:2]:  # Show first 2 inflections
            print(f"     lemma: {infl['lemma']}, tags: {infl['tags']}")

if __name__ == "__main__":
    main()
