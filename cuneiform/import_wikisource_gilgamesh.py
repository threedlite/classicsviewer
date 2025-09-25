#!/usr/bin/env python3
"""
Import Epic of Gilgamesh from Wikisource (Langdon 1917) into Akkadian database.
This is public domain text with both transliteration and translation.
"""

import re
import sqlite3
import sys
from pathlib import Path

def load_wikisource_pages():
    """Load pages of Gilgamesh transliteration from local files."""
    from pathlib import Path

    texts = []
    data_dir = Path("data-sources/wikisource_gilgamesh")

    if not data_dir.exists():
        print(f"Error: Data directory {data_dir} does not exist.")
        print("Please run download_wikisource_gilgamesh.py first.")
        return []

    # Load pages from local files
    for page_file in sorted(data_dir.glob("page_*.txt")):
        page_num = int(page_file.stem.split('_')[1])

        with open(page_file, 'r', encoding='utf-8') as f:
            content = f.read()
            texts.append((page_num, content))
            print(f"Loaded page {page_num} from {page_file.name}")

    return texts

def parse_wikisource_content(content):
    """Parse Wikisource wiki markup to extract lines with transliteration and translation."""

    lines_data = []

    # Split content into lines
    lines = content.split('\n')

    for line in lines:
        # Look for table rows with transliteration
        if '|- valign="top"' in line:
            continue

        # Look for lines that contain table cells with both transliteration and translation
        # Format: | ... {{hi|1em|''transliteration''}} || ... {{hi|1em|translation}}
        if '||' in line and "''" in line and '{{hi|' in line:
            # Split by || to separate left (transliteration) and right (translation) cells
            parts = line.split('||')

            if len(parts) >= 2:
                left_cell = parts[0]  # Contains transliteration
                right_cell = parts[1]  # Contains translation

                # Extract line number from either cell
                line_num_match = re.search(r'\{\{pline\|(\d+)\|', line)
                line_number = int(line_num_match.group(1)) if line_num_match else len(lines_data) + 1

                # Extract transliteration from left cell
                translit_match = re.search(r"''([^']+)''", left_cell)
                transliteration = ""
                if translit_match:
                    transliteration = translit_match.group(1)
                    # Clean up HTML tags
                    transliteration = re.sub(r'<sup>[^<]+</sup>', '', transliteration)
                    transliteration = re.sub(r'<ref[^>]*>.*?</ref>', '', transliteration)
                    transliteration = transliteration.strip()

                # Extract translation from right cell
                trans_match = re.search(r'\{\{hi\|[^|]+\|([^}]+)\}\}', right_cell)
                translation = ""
                if trans_match:
                    translation = trans_match.group(1).strip()
                    # Remove any italic markers if present
                    translation = translation.replace("''", "")

                if transliteration:
                    lines_data.append({
                        'line_number': line_number,
                        'transliteration': transliteration,
                        'translation': translation
                    })

    return lines_data

def import_to_database(db_path, pages_content):
    """Import parsed Gilgamesh text into database."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Add Langdon as author
    cur.execute('''
        INSERT OR REPLACE INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('langdon_gilgamesh', 'Epic of Gilgamesh (Langdon 1917)',
          'Gilgamesh', 'akkadian', 1))

    # Create work entry
    work_id = 'gilgamesh_langdon_1917'
    cur.execute('''
        INSERT OR REPLACE INTO works
        (id, author_id, title, title_alt, title_english, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, 'langdon_gilgamesh', 'Epic of Gilgamesh',
          'Gilgamish', 'Epic of Gilgamesh',
          'epic', 'Stephen Langdon 1917 translation and transliteration from Wikisource'))

    # Process all pages
    all_lines = []
    current_tablet = 1

    for page_num, content in pages_content:
        # Check if this is a new tablet
        if 'SECOND TABLET' in content.upper():
            current_tablet = 2
        elif 'THIRD TABLET' in content.upper():
            current_tablet = 3

        # Parse lines from this page
        lines = parse_wikisource_content(content)

        for line in lines:
            line['tablet'] = current_tablet
            line['page'] = page_num
            all_lines.append(line)

    print(f"Found {len(all_lines)} lines with transliteration")

    # Group by tablet and create book entries
    tablets = {}
    for line in all_lines:
        tablet_num = line['tablet']
        if tablet_num not in tablets:
            tablets[tablet_num] = []
        tablets[tablet_num].append(line)

    # Insert each tablet as a book
    for tablet_num, tablet_lines in tablets.items():
        book_id = f"{work_id}_tablet_{tablet_num}"
        line_count = len(tablet_lines)

        cur.execute('''
            INSERT OR REPLACE INTO books
            (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, tablet_num, f'Tablet {tablet_num}',
              1, line_count, line_count))

        # Insert text lines and translations
        for i, line_data in enumerate(tablet_lines, 1):
            # Insert transliterated text
            cur.execute('''
                INSERT INTO text_lines
                (book_id, line_number, sequence_number, line_text)
                VALUES (?, ?, ?, ?)
            ''', (book_id, line_data['line_number'], i, line_data['transliteration']))

            # Insert translation if available
            if line_data.get('translation'):
                cur.execute('''
                    INSERT INTO translation_segments
                    (book_id, start_line, end_line, sequence_number,
                     translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, line_data['line_number'], line_data['line_number'], i,
                      line_data['translation'], 'Stephen Langdon (1917)'))

                # Add to translation lookup
                segment_id = cur.lastrowid
                cur.execute('''
                    INSERT INTO translation_lookup
                    (book_id, line_number, segment_id)
                    VALUES (?, ?, ?)
                ''', (book_id, line_data['line_number'], segment_id))

            # Insert words for indexing
            words = line_data['transliteration'].split()
            for j, word in enumerate(words, 1):
                # Clean word
                word_clean = re.sub(r'[,.\[\]()]', '', word)
                if word_clean:
                    cur.execute('''
                        INSERT INTO words
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word_clean, book_id, line_data['line_number'], i, j))

    conn.commit()
    conn.close()

    print(f"Successfully imported Epic of Gilgamesh with {len(all_lines)} lines")
    print(f"Tablets imported: {list(tablets.keys())}")

def main():
    if len(sys.argv) < 2:
        db_path = "akkadian_texts.db"
    else:
        db_path = sys.argv[1]

    print("Loading Wikisource pages from local files...")
    pages_content = load_wikisource_pages()

    if pages_content:
        print(f"Loaded {len(pages_content)} pages")
        import_to_database(db_path, pages_content)
    else:
        print("Failed to load content")
        sys.exit(1)

if __name__ == '__main__':
    main()