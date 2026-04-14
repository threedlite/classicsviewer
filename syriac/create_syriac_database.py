#!/usr/bin/env python3
"""
Create Syriac database for ClassicsViewer

Source: Patristic Text Archive (PTA) - https://pta.bbaw.de
        Digital Syriac Corpus - https://syriaccorpus.org

License: Only CC-BY 4.0 and CC-BY-SA 4.0 licensed texts are included.
Excluded: ETCBC Peshitta texts (CC-BY-NC 4.0)

Included texts:
  - Syriac New Testament (Digital Syriac Corpus) - CC-BY 4.0
  - John of Ephesus, Ecclesiastical History - CC-BY-SA 4.0
  - Athanasius, Biblical Excerpts (Syriac) - CC-BY-SA 4.0

Usage:
  python3 create_syriac_database.py
"""

import sqlite3
import re
import os
import zipfile
from xml.etree import ElementTree as ET
import html

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PTA_DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data-sources", "pta_data", "data")
DB_PATH = os.path.join(SCRIPT_DIR, "syriac_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "syriac_texts.db.zip")

# TEI namespace
TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def create_database(db_path):
    """Create the database schema (matches Greek/Latin/Coptic schema exactly)"""
    print(f"Creating database: {db_path}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same schema as other language databases)
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


def find_syriac_files(pta_dir):
    """Find all compatible Syriac TEI files in PTA"""
    syriac_files = []

    if not os.path.exists(pta_dir):
        raise FileNotFoundError(f"PTA data directory not found: {pta_dir}")

    # Walk through PTA data directory
    for root, dirs, files in os.walk(pta_dir):
        for filename in files:
            if 'syc' in filename and filename.endswith('.xml'):
                filepath = os.path.join(root, filename)

                # Check license in file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read(5000)  # Read first 5KB for license check

                    # Only include CC-BY 4.0 or CC-BY-SA 4.0, exclude CC-BY-NC
                    if 'by-nc' in content.lower():
                        continue
                    if 'creativecommons.org/licenses/by/4.0' in content or \
                       'creativecommons.org/licenses/by-sa/4.0' in content:
                        syriac_files.append(filepath)
                except Exception as e:
                    print(f"  Error checking {filepath}: {e}")

    return sorted(syriac_files)


def get_text_content(element):
    """Get all text content from element, handling nested tags"""
    text_parts = []
    if element.text:
        text_parts.append(element.text)
    for child in element:
        text_parts.append(get_text_content(child))
        if child.tail:
            text_parts.append(child.tail)
    return ''.join(text_parts)


def parse_tei_file(filepath):
    """Parse a TEI XML file and extract structured data"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Extract metadata
    meta = {}

    # Get title
    title_elem = root.find('.//tei:title', TEI_NS)
    if title_elem is not None:
        meta['title'] = get_text_content(title_elem).strip()

    # Get author
    author_elem = root.find('.//tei:author', TEI_NS)
    if author_elem is not None:
        persname = author_elem.find('.//tei:persName', TEI_NS)
        if persname is not None:
            meta['author'] = get_text_content(persname).strip()
        else:
            meta['author'] = get_text_content(author_elem).strip()

    # Get URN
    idno_elem = root.find('.//tei:idno[@type="PTA"]', TEI_NS)
    if idno_elem is not None and idno_elem.text:
        meta['urn'] = idno_elem.text.strip()

    # Get license
    licence_elem = root.find('.//tei:licence', TEI_NS)
    if licence_elem is not None:
        meta['license'] = licence_elem.get('target', '')

    # Extract text content organized by chapters/verses
    chapters = []

    # Find the edition div
    edition_div = root.find('.//tei:div[@type="edition"]', TEI_NS)
    if edition_div is None:
        edition_div = root.find('.//tei:body', TEI_NS)

    if edition_div is not None:
        # Try NT-style: chapters with verses
        for chapter_div in edition_div.findall('.//tei:div[@subtype="chapter"]', TEI_NS):
            chapter_num = chapter_div.get('n', '1')
            verses = []

            # Find verses within chapter
            for verse_div in chapter_div.findall('.//tei:div[@subtype="verse"]', TEI_NS):
                verse_num = verse_div.get('n', '1')

                # Get verse text from <p> elements or direct content
                verse_text = ''
                for p in verse_div.findall('.//tei:p', TEI_NS):
                    verse_text += get_text_content(p).strip() + ' '

                if not verse_text.strip():
                    verse_text = get_text_content(verse_div).strip()

                if verse_text.strip():
                    verses.append({
                        'verse_num': verse_num,
                        'text': verse_text.strip()
                    })

            # If no verses, try to get <p> tags directly within chapter
            if not verses:
                line_num = 0
                for p in chapter_div.findall('.//tei:p', TEI_NS):
                    text = get_text_content(p).strip()
                    if text and len(text) > 10:  # Skip short metadata lines
                        line_num += 1
                        verses.append({
                            'verse_num': str(line_num),
                            'text': text
                        })

            if verses:
                chapters.append({
                    'chapter_num': chapter_num,
                    'verses': verses
                })

        # If no chapters found, try book-style (John of Ephesus)
        if not chapters:
            for book_div in edition_div.findall('.//tei:div[@subtype="book"]', TEI_NS):
                book_num = book_div.get('n', '1')
                verses = []
                line_num = 0

                # Get paragraphs within book
                for p in book_div.findall('.//tei:p', TEI_NS):
                    text = get_text_content(p).strip()
                    if text and len(text) > 10:  # Skip short metadata
                        line_num += 1
                        verses.append({
                            'verse_num': str(line_num),
                            'text': text
                        })

                if verses:
                    chapters.append({
                        'chapter_num': book_num,
                        'verses': verses
                    })

        # If still no content, try sections
        if not chapters:
            for section_div in edition_div.findall('.//tei:div[@subtype="section"]', TEI_NS):
                section_num = section_div.get('n', '1')
                text = get_text_content(section_div).strip()
                if text:
                    chapters.append({
                        'chapter_num': section_num,
                        'verses': [{'verse_num': '1', 'text': text}]
                    })

    return {
        'meta': meta,
        'chapters': chapters,
        'filepath': filepath
    }


def make_safe_id(text):
    """Convert text to safe ID"""
    if not text:
        return 'unknown'
    safe = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')
    return safe or 'unknown'


def tokenize_syriac(text):
    """Tokenize Syriac text into words"""
    # Remove punctuation but keep Syriac characters
    # Syriac Unicode range: U+0700-U+074F
    words = text.split()
    # Clean each word
    cleaned = []
    for word in words:
        # Keep only Syriac letters and common diacritics
        clean = re.sub(r'[^\u0700-\u074F\u0308\u0323]', '', word)
        if clean:
            cleaned.append(clean)
    return cleaned


# Book name mappings for Syriac NT - maps work folder codes to English names
# Path structure: pta9999/pta063/... where pta063 is the work code
SYRIAC_NT_BOOKS = {
    'pta063': ('matthew', 'Matthew', 'Gospel of Matthew'),
    'pta064': ('mark', 'Mark', 'Gospel of Mark'),
    'pta065': ('luke', 'Luke', 'Gospel of Luke'),
    'pta066': ('john', 'John', 'Gospel of John'),
    'pta067': ('acts', 'Acts', 'Acts of the Apostles'),
    'pta068': ('romans', 'Romans', 'Epistle to the Romans'),
    'pta069': ('1corinthians', '1 Corinthians', 'First Epistle to the Corinthians'),
    'pta070': ('2corinthians', '2 Corinthians', 'Second Epistle to the Corinthians'),
    'pta071': ('galatians', 'Galatians', 'Epistle to the Galatians'),
    'pta072': ('ephesians', 'Ephesians', 'Epistle to the Ephesians'),
    'pta073': ('philippians', 'Philippians', 'Epistle to the Philippians'),
    'pta074': ('colossians', 'Colossians', 'Epistle to the Colossians'),
    'pta075': ('1thessalonians', '1 Thessalonians', 'First Epistle to the Thessalonians'),
    'pta076': ('2thessalonians', '2 Thessalonians', 'Second Epistle to the Thessalonians'),
    'pta077': ('1timothy', '1 Timothy', 'First Epistle to Timothy'),
    'pta078': ('2timothy', '2 Timothy', 'Second Epistle to Timothy'),
    'pta079': ('titus', 'Titus', 'Epistle to Titus'),
    'pta080': ('philemon', 'Philemon', 'Epistle to Philemon'),
    'pta081': ('hebrews', 'Hebrews', 'Epistle to the Hebrews'),
    'pta082': ('james', 'James', 'Epistle of James'),
    'pta083': ('1peter', '1 Peter', 'First Epistle of Peter'),
    'pta084': ('2peter', '2 Peter', 'Second Epistle of Peter'),
    'pta085': ('1john', '1 John', 'First Epistle of John'),
    'pta086': ('2john', '2 John', 'Second Epistle of John'),
    'pta087': ('3john', '3 John', 'Third Epistle of John'),
    'pta088': ('jude', 'Jude', 'Epistle of Jude'),
    'pta089': ('revelation', 'Revelation', 'Revelation of John'),
}


def populate_database(conn, syriac_files):
    """Populate database with parsed Syriac files"""
    cursor = conn.cursor()

    # Statistics
    stats = {
        'authors': 0,
        'works': 0,
        'books': 0,
        'lines': 0,
        'words': 0
    }

    authors_inserted = set()
    works_processed = set()

    print(f"\nProcessing {len(syriac_files)} Syriac files...")

    # Group files by work
    for filepath in syriac_files:
        print(f"  Processing: {os.path.basename(filepath)}")

        try:
            data = parse_tei_file(filepath)
        except Exception as e:
            print(f"    Error parsing {filepath}: {e}")
            continue

        meta = data['meta']
        chapters = data['chapters']

        if not chapters:
            print(f"    No content found in {filepath}")
            continue

        # Determine author and work from filepath
        filename = os.path.basename(filepath)
        path_parts = filepath.split(os.sep)

        # Check if it's a NT book - look for work-level pta code under pta9999 (NT author)
        # Path structure: .../pta9999/pta063/... where pta9999 is the NT author and pta063 is the work code
        # CRITICAL: Must verify author-level code is pta9999 to avoid confusing
        # non-NT works that share the same work code (e.g., pta0001/pta073 is Severianus,
        # NOT the Epistle to the Philippians which is pta9999/pta073)
        pta_codes = []
        for part in path_parts:
            if part.startswith('pta') and len(part) > 3 and part[3:].isdigit():
                pta_codes.append(part)

        # NT books must be under pta9999 (author) / ptaXXX (work)
        pta_author_code = pta_codes[0] if len(pta_codes) >= 2 else None
        pta_work_code = pta_codes[-1] if pta_codes else None
        is_nt = pta_author_code == 'pta9999' and pta_work_code in SYRIAC_NT_BOOKS

        if is_nt:
            # Syriac New Testament book
            work_id_base, work_title, work_desc = SYRIAC_NT_BOOKS[pta_work_code]
            author_id = 'syriac_nt'
            author_name = 'Syriac New Testament'

            if author_id not in authors_inserted:
                cursor.execute('''
                    INSERT OR IGNORE INTO authors (id, name, name_alt, language, has_translations)
                    VALUES (?, ?, ?, ?, ?)
                ''', (author_id, author_name, 'Peshitta NT', 'syriac', 0))
                authors_inserted.add(author_id)
                stats['authors'] += 1

            work_id = f"syriac_nt_{work_id_base}"
        else:
            # Other Syriac work (John of Ephesus, Athanasius, etc.)
            author_name = meta.get('author', 'Unknown')
            author_id = make_safe_id(author_name)

            if author_id not in authors_inserted:
                cursor.execute('''
                    INSERT OR IGNORE INTO authors (id, name, name_alt, language, has_translations)
                    VALUES (?, ?, ?, ?, ?)
                ''', (author_id, author_name, None, 'syriac', 0))
                authors_inserted.add(author_id)
                stats['authors'] += 1

            work_title = meta.get('title', 'Unknown Work')
            work_desc = work_title
            work_id = make_safe_id(f"{author_id}_{meta.get('urn', work_title)}")

        # Create work if not exists
        if work_id not in works_processed:
            cursor.execute('''
                INSERT OR IGNORE INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                work_id,
                author_id,
                work_title,
                meta.get('title'),
                work_desc,
                'prose',
                meta.get('urn'),
                f"License: {meta.get('license', 'CC-BY 4.0')}"
            ))
            works_processed.add(work_id)
            stats['works'] += 1

        # Process chapters as books
        for chapter_data in chapters:
            chapter_num = chapter_data['chapter_num']

            try:
                chapter_int = int(chapter_num)
            except ValueError:
                chapter_int = 1

            book_id = f"{work_id}.{chapter_num}"

            verses = chapter_data['verses']
            line_count = len(verses)

            # Check if book already exists
            cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
            if cursor.fetchone():
                continue

            cursor.execute('''
                INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (book_id, work_id, chapter_int, f"Chapter {chapter_num}", 1, line_count, line_count))
            stats['books'] += 1

            # Insert verses as lines
            for seq_num, verse in enumerate(verses, 1):
                verse_text = verse['text']

                cursor.execute('''
                    INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, seq_num, seq_num, verse_text))
                stats['lines'] += 1

                # Insert words
                words = tokenize_syriac(verse_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word, book_id, seq_num, seq_num, word_pos))
                    stats['words'] += 1

        print(f"    Added {len(chapters)} chapters")

    conn.commit()
    return stats


def compress_database(db_path, zip_path):
    """Compress database to ZIP"""
    print(f"\nCompressing database to {zip_path}...")

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
    print("Creating Syriac Database")
    print("=" * 60)

    # Check data directory
    if not os.path.exists(PTA_DATA_DIR):
        print(f"\nERROR: PTA data directory not found: {PTA_DATA_DIR}")
        print("Please clone the PTA data repository:")
        print("  cd data-sources")
        print("  git clone https://github.com/PatristicTextArchive/pta_data.git")
        return 1

    # Find Syriac files
    print(f"\n--- Finding Syriac Files ---")
    print(f"Data directory: {PTA_DATA_DIR}")
    syriac_files = find_syriac_files(PTA_DATA_DIR)
    print(f"Found {len(syriac_files)} compatible Syriac files (CC-BY/CC-BY-SA)")

    if not syriac_files:
        print("ERROR: No compatible Syriac files found!")
        return 1

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate database
    print("\n--- Populating Database ---")
    stats = populate_database(conn, syriac_files)

    conn.close()

    # Compress
    print("\n--- Compressing ---")
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE CREATION COMPLETE")
    print("=" * 60)
    print(f"Authors: {stats['authors']}")
    print(f"Works: {stats['works']}")
    print(f"Books/Chapters: {stats['books']}")
    print(f"Text lines: {stats['lines']}")
    print(f"Words: {stats['words']}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
