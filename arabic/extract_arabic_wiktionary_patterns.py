#!/usr/bin/env python3
"""
Extract morphology from Arabic Wiktionary using native Arabic text patterns.
Parses patterns like "جمع", "من الفعل", "مذكره" etc.
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / "all_arabic_wiktionary_pages.json"
OUTPUT_FILE = SCRIPT_DIR / "arabic_wiktionary_morphology.json"

def extract_lemma_from_link(link_text):
    """
    Extract lemma from wiki link format.
    [[lemma]] → lemma
    [[link|display]] → display (the actual word form)
    """
    # Pattern: [[link|display]] or [[lemma]]
    match = re.match(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', link_text)
    if match:
        # If there's a pipe, use the display text, otherwise use the link
        return match.group(2) if match.group(2) else match.group(1)
    return None

def extract_arabic_patterns(title, text):
    """
    Extract morphology from Arabic Wiktionary text patterns.

    Patterns:
    - جمع [[lemma]] - plural of lemma
    - يجمع...على [[plural]] - pluralizes to plural
    - مذكره [[masc]] - its masculine is masc
    - مؤنثه [[fem]] - its feminine is fem
    - من الفعل [[verb]] - from the verb
    - فاعل من [[verb]] - active participle from verb
    - مفعول من [[verb]] - passive participle from verb
    """
    if not text:
        return []

    inflections = []

    # Pattern 1: جمع [[lemma]] - "plural of lemma"
    # Example: جمع [[قَاعِدَة]]
    # Use negative lookbehind to avoid matching يُجمع or يجمع (verbs)
    pattern1 = r'(?<!ي)(?<!ُ)جمع\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern1, text):
        link = match.group(1)
        lemma = extract_lemma_from_link(link)
        if lemma:
            inflections.append({
                'lemma': lemma,
                'tags': 'plural',
                'type': 'plural_of',
                'source': 'ar_wikt_pattern'
            })

    # Pattern 2: يُجمع...على [[plural]] - "pluralizes to plural"
    # Example: يُجمع جمع قلة على [[أَشْخُص]]
    # The word "على" (to/on) precedes the actual plural form
    # This creates mapping: plural_word_form → singular_lemma
    pattern2 = r'على\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern2, text):
        # Only process if "يجمع" appears before this match
        match_pos = match.start()
        text_before = text[:match_pos]
        if 'يجمع' in text_before or 'يُجمع' in text_before:
            link = match.group(1)
            plural_form = extract_lemma_from_link(link)
            if plural_form and plural_form != title:  # Don't self-reference
                # Create entry: plural_form → singular_lemma (title)
                inflections.append({
                    'word_form': plural_form,  # The plural word
                    'lemma': title,             # The singular (current page)
                    'tags': 'plural',
                    'type': 'plural_of',
                    'source': 'ar_wikt_pattern'
                })

    # Pattern 3: مذكره [[masculine]] - "its masculine is"
    # Used on feminine pages to point to masculine
    pattern3 = r'مذكره?\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern3, text):
        link = match.group(1)
        lemma = extract_lemma_from_link(link)
        if lemma:
            inflections.append({
                'lemma': lemma,
                'tags': 'feminine',
                'type': 'feminine_of',
                'source': 'ar_wikt_pattern'
            })

    # Pattern 4: مؤنثه [[feminine]] - "its feminine is"
    # Used on masculine pages to point to feminine
    # Creates mapping: feminine_form → masculine_lemma
    pattern4 = r'مؤنثه?\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern4, text):
        link = match.group(1)
        fem_form = extract_lemma_from_link(link)
        if fem_form and fem_form != title:
            inflections.append({
                'word_form': fem_form,  # The feminine word
                'lemma': title,          # The masculine (current page)
                'tags': 'feminine',
                'type': 'feminine_of',
                'source': 'ar_wikt_pattern'
            })

    # Pattern 5: من الفعل [[verb]] - "from the verb"
    pattern5 = r'من الفعل\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern5, text):
        link = match.group(1)
        lemma = extract_lemma_from_link(link)
        if lemma:
            inflections.append({
                'lemma': lemma,
                'tags': 'verbal_derivative',
                'type': 'from_verb',
                'source': 'ar_wikt_pattern'
            })

    # Pattern 6: فاعل من [[verb]] - "active participle from"
    pattern6 = r'فاعل من\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern6, text):
        link = match.group(1)
        lemma = extract_lemma_from_link(link)
        if lemma:
            inflections.append({
                'lemma': lemma,
                'tags': 'active_participle',
                'type': 'from_verb',
                'source': 'ar_wikt_pattern'
            })

    # Pattern 7: مفعول من [[verb]] - "passive participle from"
    pattern7 = r'مفعول من\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern7, text):
        link = match.group(1)
        lemma = extract_lemma_from_link(link)
        if lemma:
            inflections.append({
                'lemma': lemma,
                'tags': 'passive_participle',
                'type': 'from_verb',
                'source': 'ar_wikt_pattern'
            })

    # Pattern 8: مثنى [[word]] - "dual of word"
    pattern8 = r'مثنى\s+(\[\[[^\]]+\]\])'
    for match in re.finditer(pattern8, text):
        link = match.group(1)
        lemma = extract_lemma_from_link(link)
        if lemma:
            inflections.append({
                'lemma': lemma,
                'tags': 'dual',
                'type': 'dual_of',
                'source': 'ar_wikt_pattern'
            })

    return inflections

def extract_from_arabic_wiktionary():
    """Extract morphology from Arabic Wiktionary cached pages"""

    if not CACHE_FILE.exists():
        print(f"ERROR: Cache file not found at {CACHE_FILE}")
        print(f"Run extract_all_arabic_pages.py first to create the cache.")
        raise FileNotFoundError(f"Required cache file: {CACHE_FILE}")

    print(f"Reading cached Arabic Wiktionary pages: {CACHE_FILE}")
    print(f"File size: {CACHE_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    print()

    # Load cached pages
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        pages = json.load(f)

    print(f"Loaded {len(pages):,} cached pages")
    print()
    print("Extracting Arabic text patterns...")

    mappings = {}  # word_form -> list of {lemma, tags, type}
    inflection_count = 0

    # Process each cached page
    for page in pages:
        title = page['title']
        text = page.get('text', '')

        # Extract inflection patterns
        inflections = extract_arabic_patterns(title, text)

        for infl in inflections:
            # Check if this pattern specifies a different word_form
            # (e.g., plural form found on singular page)
            word_form = infl.get('word_form', title)

            if word_form not in mappings:
                mappings[word_form] = []

            # Remove word_form field before storing (it's now the key)
            infl_copy = {k: v for k, v in infl.items() if k != 'word_form'}
            mappings[word_form].append(infl_copy)
            inflection_count += 1

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

    print(f"\nBreakdown by pattern type:")
    for type_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {type_name}: {count:,}")

    return mappings

def main():
    print("="*60)
    print("Arabic Wiktionary Native Pattern Extraction")
    print("="*60)
    print()

    # Extract mappings
    mappings = extract_from_arabic_wiktionary()

    # Save to JSON
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    file_size = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ Saved {len(mappings):,} word forms ({file_size:.1f} KB)")

    # Show samples
    print("\nSample mappings:")
    for i, (word, inflections) in enumerate(list(mappings.items())[:5], 1):
        print(f"{i}. {word} →")
        for infl in inflections[:2]:  # Show first 2 inflections
            print(f"     lemma: {infl['lemma']}, tags: {infl['tags']}, type: {infl['type']}")

if __name__ == "__main__":
    main()
