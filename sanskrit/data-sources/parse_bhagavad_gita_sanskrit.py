#!/usr/bin/env python3
"""
Parse Bhagavad Gita Sanskrit text from Sanskrit Wikisource HTML files
Extracts Devanagari verses from each chapter
"""

import re
import json
import glob
import os

def convert_devanagari_number(dev_num):
    """Convert Devanagari numerals to Arabic numerals"""
    dev_to_arabic = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
    }
    result = ''
    for char in dev_num:
        result += dev_to_arabic.get(char, char)
    return result

def parse_chapter(html_content, chapter_num):
    """Parse a single chapter HTML file and extract verses"""
    verses = []

    # Find all <div class="poem"> sections (these contain the actual verses)
    poem_divs = re.findall(r'<div class="poem">(.*?)</div>', html_content, re.DOTALL | re.IGNORECASE)

    # Extract verses from poem divs only (excludes commentary sections)
    # Pattern: ॥number-number॥ or ॥number- number॥ (NO space after opening ॥)
    # Some chapters have space after dash: ॥२- १॥
    verse_pattern = r'<p>(.*?)॥([०-९\d]+)[-\.]\s*([०-९\d]+)\s*॥'

    verse_matches = []
    for poem_div in poem_divs:
        matches = re.findall(verse_pattern, poem_div, re.DOTALL)
        verse_matches.extend(matches)

    for verse_text, chapter_marker, verse_num_str in verse_matches:
        # Convert chapter number to verify it matches
        chapter_from_marker = int(convert_devanagari_number(chapter_marker))

        # Skip verses from other chapters (shouldn't happen but be safe)
        if chapter_from_marker != chapter_num:
            continue

        # Convert verse number (may be Devanagari or Arabic)
        verse_num = int(convert_devanagari_number(verse_num_str))

        # Clean up the verse text
        # Remove bold tags but keep the speaker labels
        verse_text = re.sub(r'</?b>', '', verse_text)
        # Replace <br> with space to join padas
        verse_text = re.sub(r'<br\s*/?>', ' ', verse_text, flags=re.IGNORECASE)
        # Remove other HTML tags
        verse_text = re.sub(r'<[^>]+>', '', verse_text)
        # Normalize whitespace
        verse_text = re.sub(r'\s+', ' ', verse_text)
        verse_text = verse_text.strip()

        # Remove trailing punctuation marks (। or ॥) that might remain
        verse_text = re.sub(r'\s*[।॥]\s*$', '', verse_text)

        # Skip if text is empty or too short
        if not verse_text or len(verse_text) < 10:
            continue

        verses.append({
            'number': verse_num,
            'text': verse_text
        })

    return verses

def main():
    print("Parsing Bhagavad Gita Sanskrit text...")
    print("=" * 60)

    hymns = []

    # Process all 18 chapters
    for chapter_num in range(1, 19):
        filename = f'bhagavad_gita_sa_{chapter_num}.html'

        if not os.path.exists(filename):
            print(f"Error: File not found: {filename}")
            continue

        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()

        verses = parse_chapter(html_content, chapter_num)

        if verses:
            hymns.append({
                'chapter': chapter_num,
                'verses': verses
            })
            print(f"Chapter {chapter_num}: {len(verses)} verses")
        else:
            print(f"Chapter {chapter_num}: No verses found")

    # Save to JSON
    output = {
        'source': 'Sanskrit Wikisource',
        'url': 'https://sa.wikisource.org/wiki/भगवद्गीता',
        'license': 'CC BY-SA 4.0',
        'chapters': hymns
    }

    with open('bhagavad_gita_sanskrit.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_verses = sum(len(h['verses']) for h in hymns)

    print("=" * 60)
    print(f"Total: {len(hymns)} chapters, {total_verses} verses")
    print(f"Output: bhagavad_gita_sanskrit.json")

if __name__ == '__main__':
    main()
