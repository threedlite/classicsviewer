#!/usr/bin/env python3
"""
Create Dante's Divine Comedy database for ClassicsViewer

Sources:
- Italian text: Project Gutenberg ebook #1000 (Public Domain)
- English translation: Henry Wadsworth Longfellow, Project Gutenberg ebook #1004 (Public Domain)

License: Public Domain (commercial use allowed)

Usage:
  python3 create_dante_database.py
"""

import sqlite3
import re
import os
import zipfile
import urllib.request

# URLs for source texts (Project Gutenberg)
ITALIAN_URL = "https://www.gutenberg.org/cache/epub/1000/pg1000.txt"
ENGLISH_URL = "https://www.gutenberg.org/cache/epub/1004/pg1004.txt"

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data-sources")
DB_PATH = os.path.join(SCRIPT_DIR, "dante_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "dante_texts.db.zip")

ITALIAN_FILE = os.path.join(DATA_DIR, "divina_commedia_italian.txt")
ENGLISH_FILE = os.path.join(DATA_DIR, "divine_comedy_longfellow.txt")

# Canticle definitions
CANTICLES = [
    ("inferno", "Inferno", 34),
    ("purgatorio", "Purgatorio", 33),
    ("paradiso", "Paradiso", 33),
]


def create_database(db_path):
    """Create the database schema (matches Sanskrit/Greek/Latin schema exactly)"""
    print(f"Creating database: {db_path}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same schema as Sanskrit/Greek/Latin)
    print("Creating tables...")

    cursor.execute('''
        CREATE TABLE authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE milestone_line_ranges (
            work_id TEXT,
            milestone TEXT,
            start_line INTEGER,
            end_line INTEGER,
            PRIMARY KEY (work_id, milestone)
        )
    ''')

    cursor.execute('''
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE normalization_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            pattern TEXT NOT NULL,
            replacement TEXT NOT NULL,
            description TEXT,
            priority INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE prefix_assimilation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            base_prefix TEXT NOT NULL,
            assimilated_form TEXT NOT NULL,
            meaning TEXT,
            phonological_rule TEXT,
            priority INTEGER NOT NULL,
            examples TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes (same as Sanskrit)
    print("Creating indexes...")
    cursor.execute('CREATE INDEX idx_authors_language ON authors(language)')
    cursor.execute('CREATE INDEX idx_works_author ON works(author_id)')
    cursor.execute('CREATE INDEX idx_books_work ON books(work_id)')
    cursor.execute('CREATE INDEX idx_text_lines_book ON text_lines(book_id)')
    cursor.execute('CREATE INDEX idx_text_lines_sequence ON text_lines(book_id, sequence_number)')
    cursor.execute('CREATE INDEX idx_words_word ON words(word)')
    cursor.execute('CREATE INDEX idx_words_book_line_seq ON words(book_id, line_number, sequence_number)')
    cursor.execute('CREATE INDEX idx_translation_segments_book ON translation_segments(book_id)')
    cursor.execute('CREATE INDEX idx_translation_segments_lines ON translation_segments(book_id, start_line)')
    cursor.execute('CREATE INDEX idx_dictionary_headword ON dictionary_entries(headword, language)')
    cursor.execute('CREATE INDEX idx_dictionary_headword_ultra ON dictionary_entries(headword_normalized_ultra, language)')
    cursor.execute('CREATE INDEX idx_lemma_map_word ON lemma_map(word_form)')
    cursor.execute('CREATE INDEX idx_lemma_map_word_ultra ON lemma_map(word_form_normalized_ultra)')
    cursor.execute('CREATE INDEX idx_lemma_map_lemma ON lemma_map(lemma)')
    cursor.execute('CREATE INDEX idx_normalization_language ON normalization_patterns(language, priority)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_language ON prefix_assimilation_rules(language)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_base ON prefix_assimilation_rules(base_prefix)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_form ON prefix_assimilation_rules(assimilated_form)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_lang_priority ON prefix_assimilation_rules(language, priority)')
    cursor.execute('CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)')
    cursor.execute('CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)')

    conn.commit()
    return conn


def parse_italian_text(filepath):
    """Parse Italian Divine Comedy text from Project Gutenberg"""
    print(f"Parsing Italian text: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find start and end markers
    start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK"
    end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Could not find Project Gutenberg markers")

    # Get content between markers
    text = content[start_idx:end_idx]

    # Parse cantos
    cantos = {}

    for canticle_id, canticle_name, num_cantos in CANTICLES:
        cantos[canticle_id] = {}

        for canto_num in range(1, num_cantos + 1):
            canto_roman = int_to_roman(canto_num)

            # Pattern to find canto header and content
            # Italian format: "Inferno\nCanto I\n\n\n" or "Canto I\n"
            pattern = rf'{canticle_name}\s*\n\s*Canto {canto_roman}\s*\n'

            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                # Try alternate pattern
                pattern = rf'Canto {canto_roman}\s*\n'
                matches = list(re.finditer(pattern, text, re.IGNORECASE))

                # Find the right match based on position
                if canticle_id == "inferno":
                    target_section = text[:len(text)//3]
                elif canticle_id == "purgatorio":
                    target_section = text[len(text)//3:2*len(text)//3]
                else:
                    target_section = text[2*len(text)//3:]

                for m in matches:
                    if m.start() >= text.find(target_section[:100]):
                        match = m
                        break

            if match:
                start_pos = match.end()

                # Find end of this canto (next canto header or next canticle)
                next_canto_pattern = rf'(?:{canticle_name}\s*\n\s*)?Canto {int_to_roman(canto_num + 1)}\s*\n'
                next_match = re.search(next_canto_pattern, text[start_pos:], re.IGNORECASE)

                # Also check for next canticle
                if canto_num == num_cantos:
                    next_canticle_idx = canticle_idx(canticle_id) + 1
                    if next_canticle_idx < len(CANTICLES):
                        next_canticle_name = CANTICLES[next_canticle_idx][1]
                        next_canticle_match = re.search(rf'\n{next_canticle_name}\s*\n', text[start_pos:], re.IGNORECASE)
                        if next_canticle_match:
                            if next_match is None or next_canticle_match.start() < next_match.start():
                                next_match = next_canticle_match

                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    end_pos = len(text)

                canto_text = text[start_pos:end_pos].strip()
                lines = extract_verse_lines(canto_text)
                cantos[canticle_id][canto_num] = lines
                print(f"  {canticle_name} Canto {canto_roman}: {len(lines)} lines")

    return cantos


def parse_english_text(filepath):
    """Parse English Divine Comedy translation from Project Gutenberg"""
    print(f"Parsing English text: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find start and end markers
    start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK"
    # Use rfind to find LAST occurrence of APPENDIX (not the one in TOC)
    end_marker = "\nAPPENDIX\n"

    start_idx = content.find(start_marker)
    end_idx = content.rfind(end_marker)  # rfind = last occurrence

    if start_idx == -1:
        raise ValueError("Could not find Project Gutenberg start marker")
    if end_idx == -1:
        end_idx = content.find("*** END OF THE PROJECT GUTENBERG EBOOK")

    text = content[start_idx:end_idx]

    # Parse cantos
    cantos = {}

    for canticle_id, canticle_name, num_cantos in CANTICLES:
        cantos[canticle_id] = {}

        for canto_num in range(1, num_cantos + 1):
            canto_roman = int_to_roman(canto_num)

            # English format: "Inferno: Canto I" or "Paradiso: Canto XXXIII"
            pattern = rf'{canticle_name}:\s*Canto {canto_roman}\s*\n'

            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                start_pos = match.end()

                # Find end of this canto
                next_canto_pattern = rf'{canticle_name}:\s*Canto {int_to_roman(canto_num + 1)}\s*\n'
                next_match = re.search(next_canto_pattern, text[start_pos:], re.IGNORECASE)

                # Check for next canticle
                if canto_num == num_cantos:
                    next_canticle_idx = canticle_idx(canticle_id) + 1
                    if next_canticle_idx < len(CANTICLES):
                        next_canticle_name = CANTICLES[next_canticle_idx][1]
                        next_canticle_match = re.search(rf'{next_canticle_name}:\s*Canto I\s*\n', text[start_pos:], re.IGNORECASE)
                        if next_canticle_match:
                            if next_match is None or next_canticle_match.start() < next_match.start():
                                next_match = next_canticle_match

                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    end_pos = len(text)

                canto_text = text[start_pos:end_pos].strip()
                lines = extract_verse_lines(canto_text)
                cantos[canticle_id][canto_num] = lines
                print(f"  {canticle_name} Canto {canto_roman}: {len(lines)} lines")

    return cantos


def extract_verse_lines(text):
    """Extract verse lines from canto text, removing blank lines and headers"""
    lines = []
    for line in text.split('\n'):
        # Strip whitespace
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip table of contents style lines (with periods between title and page)
        if re.match(r'^Canto [IVXLC]+\.?\s*$', line, re.IGNORECASE):
            continue

        # Skip lines that are just roman numerals (section headers in English)
        if re.match(r'^[IVXLC]+\.?\s*$', line):
            continue

        lines.append(line)

    return lines


def int_to_roman(num):
    """Convert integer to Roman numeral"""
    val = [
        1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1
    ]
    syms = [
        'M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I'
    ]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def canticle_idx(canticle_id):
    """Get index of canticle"""
    for i, (cid, _, _) in enumerate(CANTICLES):
        if cid == canticle_id:
            return i
    return -1


def tokenize_italian(text):
    """Tokenize Italian text into words"""
    # Remove punctuation except apostrophes within words
    text = re.sub(r"[^\w\s'']", ' ', text)
    words = text.split()
    return [w.strip() for w in words if w.strip()]


def populate_database(conn, italian_cantos, english_cantos):
    """Populate database with parsed texts"""
    cursor = conn.cursor()

    # Insert author
    print("Inserting author...")
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('dante', 'Dante Alighieri', 'Dante', 'italian', 1))

    # Insert work (Divine Comedy as single work)
    print("Inserting work...")
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'divina_commedia',
        'dante',
        'La Divina Commedia',
        'Divina Commedia',
        'The Divine Comedy',
        'poem',
        'Epic poem written 1308-1321, describing journey through Hell, Purgatory, and Paradise'
    ))

    # Statistics
    total_lines = 0
    total_words = 0
    total_translations = 0

    # Insert books (each canto is a "book")
    print("Inserting cantos...")
    book_number = 0

    for canticle_id, canticle_name, num_cantos in CANTICLES:
        for canto_num in range(1, num_cantos + 1):
            book_number += 1
            canto_roman = int_to_roman(canto_num)
            book_id = f"divina_commedia.{canticle_id}.{canto_num}"

            italian_lines = italian_cantos.get(canticle_id, {}).get(canto_num, [])
            english_lines = english_cantos.get(canticle_id, {}).get(canto_num, [])

            line_count = len(italian_lines)

            # Insert book
            cursor.execute('''
                INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                book_id,
                'divina_commedia',
                book_number,
                f"{canticle_name} Canto {canto_roman}",
                1,
                line_count,
                line_count
            ))

            # Insert Italian text lines
            sequence_num = 0
            for line_num, line_text in enumerate(italian_lines, 1):
                sequence_num += 1
                cursor.execute('''
                    INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, line_num, sequence_num, line_text))

                # Insert words
                words = tokenize_italian(line_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word.lower(), book_id, line_num, sequence_num, word_pos))
                    total_words += 1

            total_lines += line_count

            # Insert English translations (line by line)
            for line_num, english_line in enumerate(english_lines, 1):
                cursor.execute('''
                    INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, line_num, line_num, line_num, english_line, 'Longfellow'))
                total_translations += 1

            print(f"  {canticle_name} Canto {canto_roman}: {line_count} IT lines, {len(english_lines)} EN lines")

    conn.commit()

    return {
        'lines': total_lines,
        'words': total_words,
        'translations': total_translations,
        'cantos': book_number
    }


def compress_database(db_path, zip_path):
    """Compress database to ZIP"""
    print(f"Compressing database to {zip_path}...")

    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(db_path, os.path.basename(db_path))

    db_size = os.path.getsize(db_path) / (1024 * 1024)
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"  Database: {db_size:.2f} MB")
    print(f"  Compressed: {zip_size:.2f} MB")


def download_source_texts():
    """Download source texts from Project Gutenberg if not present"""
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(ITALIAN_FILE):
        print(f"Downloading Italian text from Project Gutenberg...")
        urllib.request.urlretrieve(ITALIAN_URL, ITALIAN_FILE)
        print(f"  Saved to: {ITALIAN_FILE}")

    if not os.path.exists(ENGLISH_FILE):
        print(f"Downloading English translation from Project Gutenberg...")
        urllib.request.urlretrieve(ENGLISH_URL, ENGLISH_FILE)
        print(f"  Saved to: {ENGLISH_FILE}")


def main():
    print("=" * 60)
    print("Creating Dante's Divine Comedy Database")
    print("=" * 60)

    # Download source texts if needed
    print("\n--- Checking Source Texts ---")
    download_source_texts()

    # Parse texts
    print("\n--- Parsing Italian Text ---")
    italian_cantos = parse_italian_text(ITALIAN_FILE)

    print("\n--- Parsing English Text ---")
    english_cantos = parse_english_text(ENGLISH_FILE)

    # Create and populate database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    print("\n--- Populating Database ---")
    stats = populate_database(conn, italian_cantos, english_cantos)

    conn.close()

    # Compress
    print("\n--- Compressing ---")
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE CREATION COMPLETE")
    print("=" * 60)
    print(f"Cantos: {stats['cantos']}")
    print(f"Italian lines: {stats['lines']}")
    print(f"Words: {stats['words']}")
    print(f"English translations: {stats['translations']}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
