#!/usr/bin/env python3
"""
Parse Bhagavad Gita Besant translation (verse-by-verse)
Extracts English verse translations from each discourse
"""

import re
import json
import os

def parse_discourse(html_content, discourse_num):
    """Parse a single discourse HTML file and extract verse translations"""
    verses = []

    # Pattern to match English verse translations
    # The verse number appears in <span class="wst-floatright">...(X)</span>
    # Strategy: Find all verse numbers first, then extract the text before each

    # Find all verse numbers
    verse_nums = re.findall(r'class="wst-floatright"[^>]*>.*?\((\d+)\)', html_content)

    # For each verse number, find the corresponding text
    matches = []
    for i, verse_num_str in enumerate(verse_nums):
        # Find the position of this verse number marker
        pattern = rf'class="wst-floatright"[^>]*>.*?\({verse_num_str}\)'
        match = re.search(pattern, html_content)
        if not match:
            continue

        end_pos = match.start()

        # Find the start position - look backwards for <p> tag
        # Look back up to 5000 characters
        start_search = max(0, end_pos - 5000)
        preceding_text = html_content[start_search:end_pos]

        # Find the last <p> before the verse number
        p_matches = list(re.finditer(r'<p[^>]*>', preceding_text))
        if not p_matches:
            continue

        last_p = p_matches[-1]
        verse_text = preceding_text[last_p.end():]

        matches.append((verse_text, verse_num_str))

    for verse_text, verse_num_str in matches:
        verse_num = int(verse_num_str)

        # Clean up the verse text
        # Remove footnote references like <sup>...<a href="#cite_note-1">...</a></sup>
        verse_text = re.sub(r'<sup[^>]*>.*?</sup>', '', verse_text)
        # Remove other HTML tags
        verse_text = re.sub(r'<[^>]+>', '', verse_text)
        # Decode HTML entities
        verse_text = verse_text.replace('&quot;', '"')
        verse_text = verse_text.replace('&#91;', '[')
        verse_text = verse_text.replace('&#93;', ']')
        verse_text = verse_text.replace('&amp;', '&')
        # Normalize whitespace
        verse_text = re.sub(r'\s+', ' ', verse_text)
        verse_text = verse_text.strip()

        # Skip if empty or too short
        if not verse_text or len(verse_text) < 5:
            continue

        verses.append({
            'number': verse_num,
            'text': verse_text
        })

    return verses

def main():
    print("Parsing Bhagavad Gita Besant translation...")
    print("=" * 60)

    discourses = []

    # Process all 18 discourses
    for discourse_num in range(1, 19):
        filename = f'bhagavad_gita_besant_{discourse_num}.html'

        if not os.path.exists(filename):
            print(f"Error: File not found: {filename}")
            continue

        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()

        verses = parse_discourse(html_content, discourse_num)

        if verses:
            discourses.append({
                'chapter': discourse_num,
                'verses': verses
            })
            print(f"Discourse {discourse_num}: {len(verses)} verses")
        else:
            print(f"Discourse {discourse_num}: No verses found")

    # Save to JSON
    output = {
        'source': 'English Wikisource',
        'translator': 'Annie Besant',
        'year': '1922',
        'edition': '4th',
        'url': 'https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)',
        'license': 'Public Domain',
        'chapters': discourses
    }

    with open('bhagavad_gita_besant.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_verses = sum(len(d['verses']) for d in discourses)

    print("=" * 60)
    print(f"Total: {len(discourses)} discourses, {total_verses} verses")
    print(f"Output: bhagavad_gita_besant.json")

if __name__ == '__main__':
    main()
