#!/usr/bin/env python3
"""
Parse Bhagavad Gita English translation (Arnold) from English Wikisource HTML files
Extracts prose translation from each chapter
Note: Arnold's translation is prose, not verse-by-verse
"""

import re
import json
import glob
import os

def clean_text(text):
    """Clean HTML tags and normalize whitespace"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove reference markers like [1], [2], etc.
    text = re.sub(r'\[\d+\]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_chapter(html_content, chapter_num):
    """Parse a single chapter HTML file and extract text"""
    # Find the poem div that contains the translation
    poem_match = re.search(r'<div class="poem">(.*?)</div>', html_content, re.DOTALL | re.IGNORECASE)
    if not poem_match:
        print(f"  Warning: No poem div found in chapter {chapter_num}")
        return None

    poem_content = poem_match.group(1)

    # Extract text from paragraphs, preserving structure
    paragraphs = []

    # Split by paragraph tags
    para_parts = re.split(r'</p>\s*<p>', poem_content)

    for para in para_parts:
        # Clean the paragraph
        para_text = clean_text(para)
        if para_text:
            paragraphs.append(para_text)

    if not paragraphs:
        return None

    # Join all paragraphs with newlines
    full_text = '\n'.join(paragraphs)

    return full_text

def main():
    print("Parsing Bhagavad Gita English translation (Arnold)...")
    print("=" * 60)

    chapters = []

    # Process all 18 chapters
    for chapter_num in range(1, 19):
        filename = f'bhagavad_gita_en_{chapter_num}.html'

        if not os.path.exists(filename):
            print(f"Error: File not found: {filename}")
            continue

        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()

        text = parse_chapter(html_content, chapter_num)

        if text:
            chapters.append({
                'chapter': chapter_num,
                'text': text
            })
            print(f"Chapter {chapter_num}: {len(text)} characters")
        else:
            print(f"Chapter {chapter_num}: No text found")

    # Save to JSON
    output = {
        'source': 'English Wikisource',
        'url': 'https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)',
        'translator': 'Edwin Arnold',
        'year': '1885',
        'license': 'Public Domain',
        'chapters': chapters
    }

    with open('bhagavad_gita_english.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_chars = sum(len(c['text']) for c in chapters)

    print("=" * 60)
    print(f"Total: {len(chapters)} chapters, {total_chars} characters")
    print(f"Output: bhagavad_gita_english.json")

if __name__ == '__main__':
    main()
