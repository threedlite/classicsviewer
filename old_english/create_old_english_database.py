#!/usr/bin/env python3
"""
Create Old English database for ClassicsViewer

Sources:
- Texts: Project Gutenberg Beowulf (Public Domain)
- Dictionary: Bosworth-Toller Anglo-Saxon Dictionary (Public Domain, 1898/1921)

License: Public Domain (commercial use allowed)

Usage:
  python3 create_old_english_database.py
"""

import sqlite3
import os
import re
import zipfile
import urllib.request
import bz2
from pathlib import Path

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data-sources")
DB_PATH = os.path.join(SCRIPT_DIR, "old_english_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "old_english_texts.db.zip")

# Source URLs
# Note: #16328 is English translation, #9700 is Old English original
BEOWULF_URL = "https://www.gutenberg.org/cache/epub/9700/pg9700.txt"
BEOWULF_TRANS_URL = "https://www.gutenberg.org/cache/epub/16328/pg16328.txt"
DICT_URL = "https://raw.githubusercontent.com/madeleineth/btc_anglo_saxon/master/db/oe_bosworthtoller.txt.bz2"

# File paths
BEOWULF_PATH = os.path.join(DATA_DIR, "beowulf.txt")
BEOWULF_TRANS_PATH = os.path.join(DATA_DIR, "beowulf_translation.txt")
DICT_PATH = os.path.join(DATA_DIR, "oe_bosworthtoller.txt")


def create_database(db_path):
    """Create the database schema (matches Greek/Latin/Norse schema)"""
    print(f"Creating database: {db_path}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    # Create indexes
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


def download_sources():
    """Download source files if not present"""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Download Beowulf (Old English)
    if not os.path.exists(BEOWULF_PATH):
        print(f"Downloading Beowulf (Old English) from Project Gutenberg...")
        urllib.request.urlretrieve(BEOWULF_URL, BEOWULF_PATH)
        print(f"  Saved to: {BEOWULF_PATH}")
    else:
        print(f"Beowulf (Old English) already downloaded: {BEOWULF_PATH}")

    # Download Beowulf English translation
    if not os.path.exists(BEOWULF_TRANS_PATH):
        print(f"Downloading Beowulf English translation from Project Gutenberg...")
        urllib.request.urlretrieve(BEOWULF_TRANS_URL, BEOWULF_TRANS_PATH)
        print(f"  Saved to: {BEOWULF_TRANS_PATH}")
    else:
        print(f"Beowulf translation already downloaded: {BEOWULF_TRANS_PATH}")

    # Download dictionary
    if not os.path.exists(DICT_PATH):
        print(f"Downloading Bosworth-Toller dictionary...")
        bz2_path = DICT_PATH + ".bz2"
        urllib.request.urlretrieve(DICT_URL, bz2_path)
        print(f"  Decompressing...")
        with bz2.open(bz2_path, 'rt', encoding='utf-8', errors='replace') as f_in:
            with open(DICT_PATH, 'w', encoding='utf-8') as f_out:
                f_out.write(f_in.read())
        os.remove(bz2_path)
        print(f"  Saved to: {DICT_PATH}")
    else:
        print(f"Dictionary already downloaded: {DICT_PATH}")


def normalize_old_english(word):
    """Normalize Old English word for lookup"""
    word = word.lower()
    # Normalize special characters
    word = word.replace('ƿ', 'w')  # wynn to w
    # Keep þ, ð, æ as-is (important for Old English)
    return word


def tokenize_old_english(text):
    """Tokenize Old English text into words"""
    # Remove punctuation except for special OE characters
    text = re.sub(r'[^\w\sþðæÞÐÆƿ]', ' ', text, flags=re.UNICODE)
    words = text.split()
    return [w.strip().lower() for w in words if w.strip()]


def parse_beowulf(filepath):
    """Parse Beowulf text from Project Gutenberg #9700 format.

    The file contains:
    - Gutenberg header/preface
    - The poem itself (starting with "Hwät! we Gâr-Dena")
    - The Fight at Finnsburh fragment
    - Glossary and index

    Returns list of (section_name, lines) tuples.
    """
    print(f"Parsing Beowulf from: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    sections = []
    current_section = None
    current_lines = []

    in_poem = False
    in_glossary = False

    # Section pattern: "I. TITLE" or "XLIII. TITLE"
    section_pattern = re.compile(r'^([IVX]+)\.\s+(.+)$')

    for line in lines:
        line_stripped = line.strip()

        # Detect end markers - stop at glossary, notes, or list of names
        # Only match if it's a section header (all caps, short line)
        if (re.match(r'^(GLOSSARY|LIST OF NAMES|NOTES)[\.\s;]*$', line_stripped, re.IGNORECASE) or
            re.match(r'^LIST OF NAMES; NOTES; AND GLOSSARY\.?$', line_stripped, re.IGNORECASE)):
            in_glossary = True
            in_poem = False
            if current_section and current_lines:
                sections.append((current_section, current_lines))
                current_lines = []
            continue

        if in_glossary:
            continue

        # Detect the famous opening line - this starts the poem
        if 'Hwät! we Gâr-Dena' in line or 'Hwæt! we Gar-Dena' in line:
            in_poem = True
            current_section = "I. The Life and Death of Scyld"
            # Include this line
            cleaned = re.sub(r'^\d+\s+', '', line_stripped).strip()
            if cleaned:
                current_lines.append(cleaned)
            continue

        # Detect section headers (Roman numeral + title)
        section_match = section_pattern.match(line_stripped)
        if section_match and in_poem:
            numeral = section_match.group(1)
            title = section_match.group(2).strip()
            # Skip the "I. BEÓWULF:" header line
            if 'BEÓWULF' in title.upper() or 'BEOWULF' in title.upper():
                if ':' in title:  # It's the header, not a section
                    continue
            # Save previous section
            if current_section and current_lines:
                sections.append((current_section, current_lines))
                current_lines = []
            current_section = f"{numeral}. {title}"
            continue

        # Collect poem lines
        if in_poem and line_stripped:
            # Skip subtitle lines (italicized)
            if line_stripped.startswith('_') and line_stripped.endswith('_'):
                continue
            # Skip "AN ANGLO-SAXON POEM" etc
            if 'ANGLO-SAXON' in line_stripped:
                continue

            # Clean the line - remove leading line numbers
            cleaned = re.sub(r'^\d+\s+', '', line_stripped).strip()

            if cleaned and len(cleaned) > 2:
                current_lines.append(cleaned)

    # Add final section
    if current_section and current_lines:
        sections.append((current_section, current_lines))

    print(f"  Found {len(sections)} sections")
    return sections


def parse_beowulf_translation(filepath):
    """Parse Beowulf English translation from Project Gutenberg #16328 format.

    J. Lesslie Hall's 1892 translation. Section titles are in ALL CAPS like:
    "THE LIFE AND DEATH OF SCYLD."
    "SCYLD'S SUCCESSORS.--HROTHGAR'S GREAT MEAD-HALL."

    Returns list of (section_name, lines) tuples matching Old English structure.
    """
    print(f"Parsing Beowulf translation from: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    sections = []
    current_section = None
    current_lines = []

    in_poem = False
    in_appendix = False

    # Section title pattern: ALL CAPS ending with period, allowing hyphens and apostrophes
    # Examples: "THE LIFE AND DEATH OF SCYLD." or "SCYLD'S SUCCESSORS.--HROTHGAR'S GREAT MEAD-HALL."
    section_pattern = re.compile(r"^[A-Z][A-Z\s'\-\.]+\.$")

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Detect end of poem - ADDENDA section
        if line_stripped == 'ADDENDA' or line_stripped.startswith('ADDENDA.'):
            in_appendix = True
            in_poem = False
            if current_section and current_lines:
                sections.append((current_section, current_lines))
                current_lines = []
            continue

        if in_appendix:
            continue

        # Detect start of poem - first section title
        if line_stripped == 'THE LIFE AND DEATH OF SCYLD.' and not in_poem:
            in_poem = True
            current_section = "I. The Life and Death of Scyld"
            continue

        # Detect section headers (ALL CAPS titles)
        if in_poem and section_pattern.match(line_stripped):
            # Make sure it's not a subtitle or annotation
            if len(line_stripped) > 10:  # Real section titles are longer
                # Save previous section
                if current_section and current_lines:
                    sections.append((current_section, current_lines))
                    current_lines = []
                # Convert to title case for section name
                section_num = len(sections) + 1
                # Convert Roman numeral
                roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                                  'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
                                  'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII', 'XXIX', 'XXX',
                                  'XXXI', 'XXXII', 'XXXIII', 'XXXIV', 'XXXV', 'XXXVI', 'XXXVII', 'XXXVIII', 'XXXIX',
                                  'XL', 'XLI', 'XLII', 'XLIII']
                numeral = roman_numerals[section_num] if section_num <= len(roman_numerals) else str(section_num)
                # Clean and title-case the section name
                title = line_stripped.rstrip('.').replace('--', ' - ').title()
                current_section = f"{numeral}. {title}"
                continue

        # Collect poem lines
        if in_poem and line_stripped:
            # Skip page markers like [1], [2], etc.
            if re.match(r'^\[\d+\]', line_stripped):
                continue
            # Skip line numbers at start
            cleaned = re.sub(r'^\d+\s+', '', line_stripped).strip()
            # Skip footnote references like [1], [2]
            cleaned = re.sub(r'\[\d+\]', '', cleaned).strip()

            if cleaned and len(cleaned) > 2:
                current_lines.append(cleaned)

    # Add final section
    if current_section and current_lines:
        sections.append((current_section, current_lines))

    print(f"  Found {len(sections)} translation sections")
    return sections


def populate_texts(conn):
    """Parse Beowulf and populate the database"""
    cursor = conn.cursor()

    # Insert author (Anonymous)
    print("Inserting author...")
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('old_english_anonymous', 'Anonymous', 'Beowulf Poet', 'old_english', 1))

    # Parse Beowulf
    sections = parse_beowulf(BEOWULF_PATH)

    if not sections:
        print("  ERROR: No text sections found in Beowulf!")
        return {'works': 0, 'chapters': 0, 'lines': 0, 'words': 0}

    # Insert work
    work_id = "old_english_beowulf"
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        work_id,
        'old_english_anonymous',
        'Beowulf',
        'Béowulf',
        'Beowulf',
        'poetry',
        'Old English epic poem, c. 700-1000 CE'
    ))

    total_lines = 0
    total_words = 0
    total_chapters = 0

    # Process each section/fitt
    for chapter_num, (section_name, lines) in enumerate(sections, 1):
        if not lines:
            continue

        book_id = f"{work_id}.{chapter_num}"

        # Insert book (section/fitt)
        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            book_id,
            work_id,
            chapter_num,
            section_name,
            1,
            len(lines),
            len(lines)
        ))

        # Insert lines
        section_words = 0
        for line_num, line_text in enumerate(lines, 1):
            cursor.execute('''
                INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                VALUES (?, ?, ?, ?)
            ''', (book_id, line_num, line_num, line_text))

            # Insert words
            words = tokenize_old_english(line_text)
            for word_pos, word in enumerate(words, 1):
                cursor.execute('''
                    INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                    VALUES (?, ?, ?, ?, ?)
                ''', (word, book_id, line_num, line_num, word_pos))
                section_words += 1

        total_lines += len(lines)
        total_words += section_words
        total_chapters += 1

        print(f"  {section_name}: {len(lines)} lines, {section_words} words")

    conn.commit()

    return {
        'works': 1,
        'chapters': total_chapters,
        'lines': total_lines,
        'words': total_words
    }


def populate_translations(conn):
    """Parse and populate English translations for Beowulf.

    Aligns J. Lesslie Hall's 1892 translation with the Old English sections.
    Uses proportional line mapping within each section.
    """
    cursor = conn.cursor()

    print("Populating translations...")

    # Parse translation
    trans_sections = parse_beowulf_translation(BEOWULF_TRANS_PATH)

    if not trans_sections:
        print("  WARNING: No translation sections found!")
        return 0

    # Get Old English sections for alignment
    cursor.execute('''
        SELECT id, book_number, label, line_count
        FROM books
        WHERE work_id = 'old_english_beowulf'
        ORDER BY book_number
    ''')
    oe_books = cursor.fetchall()

    if len(oe_books) != len(trans_sections):
        print(f"  WARNING: Section count mismatch: {len(oe_books)} OE vs {len(trans_sections)} translation")
        # Use minimum to avoid index errors
        num_sections = min(len(oe_books), len(trans_sections))
    else:
        num_sections = len(oe_books)

    total_segments = 0
    total_lookups = 0

    for i in range(num_sections):
        book_id, book_num, label, oe_line_count = oe_books[i]
        trans_section_name, trans_lines = trans_sections[i]

        if not trans_lines or not oe_line_count:
            continue

        # Combine all translation lines into one segment per section
        # This is simpler and matches how prose translations work
        trans_text = '\n'.join(trans_lines)

        cursor.execute('''
            INSERT INTO translation_segments
            (book_id, start_line, end_line, sequence_number, translation_text, translator)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (book_id, 1, oe_line_count, 1, trans_text, 'J. Lesslie Hall (1892)'))

        segment_id = cursor.lastrowid
        total_segments += 1

        # Create translation_lookup entries for every line in the section
        for line_num in range(1, oe_line_count + 1):
            cursor.execute('''
                INSERT INTO translation_lookup (book_id, line_number, segment_id)
                VALUES (?, ?, ?)
            ''', (book_id, line_num, segment_id))
            total_lookups += 1

        print(f"  Section {book_num} ({label}): {len(trans_lines)} trans lines -> {oe_line_count} OE lines")

    conn.commit()
    print(f"  Created {total_segments} translation segments")
    print(f"  Created {total_lookups} translation lookup entries")

    return total_segments


def parse_dictionary_entry(entry_text):
    """Parse a Bosworth-Toller dictionary entry.

    Returns (headword, definition) or None if invalid.
    """
    # Entry format: <B>headword</B> ... definition text ...

    # Extract headword from <B> tags
    headword_match = re.search(r'<B>([^<]+)</B>', entry_text)
    if not headword_match:
        return None

    headword = headword_match.group(1).strip()

    # Strip trailing punctuation (commas, semicolons, colons, periods)
    headword = headword.rstrip(',;:.')

    # Skip entries that are just references or too short
    if len(headword) < 1:
        return None
    if headword.startswith('-') and len(headword) < 3:
        return None

    # Clean up definition - remove HTML-like tags but keep content
    definition = entry_text
    definition = re.sub(r'<B>[^<]*</B>\s*', '', definition, count=1)  # Remove headword
    definition = re.sub(r'<[^>]+>', '', definition)  # Remove all tags
    definition = re.sub(r'&[a-z]+;', '', definition)  # Remove HTML entities
    definition = re.sub(r'\s+', ' ', definition).strip()

    # Skip if definition is too short or empty
    if len(definition) < 5:
        return None

    return (headword, definition)


def populate_dictionary(conn):
    """Load Bosworth-Toller dictionary into database"""
    cursor = conn.cursor()

    print(f"Loading dictionary from: {DICT_PATH}")

    with open(DICT_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Skip introduction section
    intro_end = content.find('</INTRODUCTION>')
    if intro_end > 0:
        content = content[intro_end + len('</INTRODUCTION>'):]

    # Split into entries - entries start with <B> tag for headword
    # Each entry typically spans from one <B> to the next
    entries_raw = re.split(r'(?=<B>[^<]+</B>)', content)

    count = 0
    lemma_count = 0

    print("Inserting dictionary entries...")

    for entry_text in entries_raw:
        entry_text = entry_text.strip()
        if not entry_text:
            continue

        parsed = parse_dictionary_entry(entry_text)
        if not parsed:
            continue

        headword, definition = parsed

        # Normalize headword
        headword_normalized = normalize_old_english(headword)

        # Truncate very long definitions
        if len(definition) > 5000:
            definition = definition[:5000] + "..."

        cursor.execute('''
            INSERT INTO dictionary_entries (headword, headword_normalized_ultra, language, entry_plain, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (headword, headword_normalized, 'old_english', definition, 'Bosworth-Toller'))

        # Also add to lemma_map for basic lookup
        cursor.execute('''
            INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (headword, headword_normalized, headword, 1.0, 'Bosworth-Toller'))
        lemma_count += 1

        # Add lowercase variant if different
        headword_lower = headword.lower()
        if headword_lower != headword:
            cursor.execute('''
                INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (headword_lower, headword_normalized, headword, 1.0, 'Bosworth-Toller'))
            lemma_count += 1

        count += 1

        if count % 5000 == 0:
            print(f"    Processed {count} entries...")

    conn.commit()
    print(f"  Inserted {count} dictionary entries")
    print(f"  Created {lemma_count} lemma mappings")

    return count


def populate_normalization_patterns(conn):
    """Add normalization patterns for Old English."""
    cursor = conn.cursor()

    print("Adding normalization patterns...")

    patterns = [
        # (pattern, replacement, description, priority)
        ('ƿ', 'w', 'Wynn to modern w', 10),
        ('þ', 'th', 'Thorn to th (for search)', 20),
        ('ð', 'th', 'Eth to th (for search)', 21),
        ('æ', 'ae', 'Ash to ae (for search)', 30),
    ]

    count = 0
    for pattern, replacement, desc, priority in patterns:
        cursor.execute('''
            INSERT INTO normalization_patterns (language, pattern, replacement, description, priority)
            VALUES (?, ?, ?, ?, ?)
        ''', ('old_english', pattern, replacement, desc, priority))
        count += 1

    conn.commit()
    print(f"  Added {count} normalization patterns")

    return count


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


def main():
    print("=" * 60)
    print("Creating Old English Database")
    print("=" * 60)

    # Download sources
    print("\n--- Downloading Source Data ---")
    download_sources()

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate texts
    print("\n--- Populating Texts ---")
    text_stats = populate_texts(conn)

    # Populate translations
    print("\n--- Populating Translations ---")
    trans_count = populate_translations(conn)

    # Populate dictionary
    print("\n--- Populating Dictionary ---")
    dict_count = populate_dictionary(conn)

    # Populate normalization patterns
    print("\n--- Adding Normalization Patterns ---")
    pattern_count = populate_normalization_patterns(conn)

    conn.close()

    # Compress
    print("\n--- Compressing ---")
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE CREATION COMPLETE")
    print("=" * 60)
    print(f"Works: {text_stats['works']}")
    print(f"Sections: {text_stats['chapters']}")
    print(f"Lines: {text_stats['lines']}")
    print(f"Words: {text_stats['words']}")
    print(f"Translation segments: {trans_count}")
    print(f"Dictionary entries: {dict_count}")
    print(f"Normalization patterns: {pattern_count}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
