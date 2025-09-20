#!/usr/bin/env python3
"""
Create SQLite database for Akkadian and Sumerian texts from ORACC JSON exports.
Uses the exact same schema as the Perseus database for compatibility with the Android app.
"""

import sqlite3
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import sys
import zipfile
from datetime import datetime

# Database file name
DB_NAME = "cuneiform_texts.db"
DB_ZIP_NAME = "cuneiform_texts.db.zip"

# Data source directory (where ORACC downloads are)
DATA_DIR = Path(__file__).parent.parent / "data-sources" / "oracc"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data-prep"

def normalize_akkadian_sumerian(text: str) -> str:
    """
    Normalize Akkadian/Sumerian transliteration for searching.
    Handles special characters: š, ṣ, ṭ, ḫ, ĝ, ñ
    """
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Normalize special characters for search
    replacements = {
        'š': 'sh',
        'ṣ': 's',
        'ṭ': 't',
        'ḫ': 'h',
        'ĝ': 'g',
        'ñ': 'n',
        # Remove subscript numbers
        '₀': '', '₁': '', '₂': '', '₃': '', '₄': '',
        '₅': '', '₆': '', '₇': '', '₈': '', '₉': '',
        # Remove other diacritics
        'ā': 'a', 'ē': 'e', 'ī': 'i', 'ū': 'u',
        'â': 'a', 'ê': 'e', 'î': 'i', 'û': 'u',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove remaining diacritics using Unicode normalization
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

    # Remove non-alphanumeric characters except spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)

    # Collapse multiple spaces
    text = ' '.join(text.split())

    return text

def create_database_schema(conn):
    """Create the database schema matching Perseus database structure."""
    cursor = conn.cursor()

    # Authors table
    cursor.execute("""
        CREATE TABLE authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        )
    """)

    # Works table
    cursor.execute("""
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
    """)

    # Books table
    cursor.execute("""
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
    """)

    # Text lines table
    cursor.execute("""
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
    """)

    # Translation segments table
    cursor.execute("""
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
    """)

    # Words table
    cursor.execute("""
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            word_normalized TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Milestone line ranges table
    cursor.execute("""
        CREATE TABLE milestone_line_ranges (
            work_id TEXT,
            milestone TEXT,
            start_line INTEGER,
            end_line INTEGER,
            PRIMARY KEY (work_id, milestone)
        )
    """)

    # Dictionary entries table - modified for Akkadian/Sumerian
    cursor.execute("""
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT,
            CHECK (language IN ('akkadian', 'sumerian'))
        )
    """)

    # Lemma map table
    cursor.execute("""
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    """)

    # Translation lookup table
    cursor.execute("""
        CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX idx_authors_language ON authors(language)")
    cursor.execute("CREATE INDEX idx_works_author_id ON works(author_id)")
    cursor.execute("CREATE INDEX idx_books_work_id ON books(work_id)")
    cursor.execute("CREATE INDEX idx_text_lines_book_id ON text_lines(book_id)")
    cursor.execute("CREATE INDEX idx_text_lines_line_number ON text_lines(book_id, line_number)")
    cursor.execute("CREATE INDEX idx_translation_segments_book_id ON translation_segments(book_id)")
    cursor.execute("CREATE INDEX idx_words_book_id ON words(book_id)")
    cursor.execute("CREATE INDEX idx_words_normalized ON words(word_normalized)")
    cursor.execute("CREATE INDEX idx_dictionary_language ON dictionary_entries(language)")
    cursor.execute("CREATE INDEX idx_dictionary_headword ON dictionary_entries(headword)")
    cursor.execute("CREATE INDEX idx_lemma_map_word_form ON lemma_map(word_form_normalized)")
    cursor.execute("CREATE INDEX idx_translation_lookup_book_line ON translation_lookup(book_id, line_number)")

    conn.commit()
    print("✓ Database schema created")

def parse_oracc_json_corpus(project_dir: Path, language: str) -> Dict:
    """
    Parse ORACC JSON corpus files to extract texts and translations.
    Returns a dictionary with texts organized by work.
    """
    corpus_data = {}

    # Look for corpus.json file
    corpus_file = project_dir / "corpus.json"
    if not corpus_file.exists():
        # Try to find it in subdirectories
        corpus_files = list(project_dir.glob("**/corpus.json"))
        if corpus_files:
            corpus_file = corpus_files[0]
        else:
            print(f"  Warning: No corpus.json found in {project_dir}")
            return corpus_data

    try:
        with open(corpus_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # ORACC JSON structure varies by project
        # Generally: data['type'] == 'corpus' and texts in data['members']
        if isinstance(data, dict):
            if 'members' in data:
                # Standard corpus format
                for text_id, text_data in data['members'].items():
                    corpus_data[text_id] = parse_oracc_text(text_data, language)
            elif 'texts' in data:
                # Alternative format
                for text_id, text_data in data['texts'].items():
                    corpus_data[text_id] = parse_oracc_text(text_data, language)

    except Exception as e:
        print(f"  Error parsing corpus.json: {e}")

    return corpus_data

def parse_oracc_text(text_data: Dict, language: str) -> Dict:
    """
    Parse individual ORACC text from JSON.
    Extracts transliteration and translation.
    """
    result = {
        'id': text_data.get('id', ''),
        'title': text_data.get('designation', 'Untitled'),
        'language': language,
        'lines': [],
        'translations': []
    }

    # Extract catalog metadata if available
    if 'catalog' in text_data:
        catalog = text_data['catalog']
        result['period'] = catalog.get('period', '')
        result['genre'] = catalog.get('genre', '')
        result['author'] = catalog.get('ancient_author', 'Anonymous')

    # Extract text content
    if 'cdl' in text_data:
        # CDL (Cuneiform Document Language) format
        for chunk in text_data['cdl']:
            if chunk.get('node') == 'c' and 'cdl' in chunk:
                # This is a text chunk
                for item in chunk['cdl']:
                    if item.get('node') == 'l':  # Line
                        line_data = parse_cdl_line(item)
                        if line_data:
                            result['lines'].append(line_data)

    return result

def parse_cdl_line(line_item: Dict) -> Optional[Dict]:
    """
    Parse a CDL line item to extract transliteration and translation.
    """
    line_data = {
        'number': line_item.get('label', ''),
        'transliteration': '',
        'translation': ''
    }

    # Build transliteration from words
    words = []
    if 'cdl' in line_item:
        for word in line_item['cdl']:
            if word.get('node') == 'w':  # Word
                # Get the transliterated form
                form = word.get('form', '')
                if not form and 'gdl' in word:
                    # Build from graphemes
                    form = build_word_from_gdl(word['gdl'])
                if form:
                    words.append(form)

    line_data['transliteration'] = ' '.join(words)

    # Look for translation in notes or elsewhere
    if 'notes' in line_item:
        for note in line_item['notes']:
            if note.get('type') == 'translation':
                line_data['translation'] = note.get('content', '')

    return line_data if line_data['transliteration'] else None

def build_word_from_gdl(gdl_list: List) -> str:
    """
    Build a word from GDL (Grapheme Description Language) components.
    """
    parts = []
    for gdl in gdl_list:
        if isinstance(gdl, dict):
            if 's' in gdl:  # Sign
                parts.append(gdl['s'])
            elif 'v' in gdl:  # Value
                parts.append(gdl['v'])
    return ''.join(parts)

def import_oracc_project(conn, project_dir: Path, project_name: str, language: str):
    """
    Import an ORACC project into the database.
    """
    cursor = conn.cursor()

    print(f"\n  Importing {project_name} ({language})...")

    # Parse the corpus
    corpus = parse_oracc_json_corpus(project_dir, language)

    if not corpus:
        print(f"    No texts found in {project_name}")
        return

    # Create author entry for the project (treating project as author)
    author_id = f"{language}_{project_name}"
    cursor.execute("""
        INSERT OR IGNORE INTO authors (id, name, language, has_translations)
        VALUES (?, ?, ?, ?)
    """, (author_id, project_name.upper(), language, 0))

    texts_imported = 0

    for text_id, text_data in corpus.items():
        if not text_data.get('lines'):
            continue

        # Create work entry
        work_id = f"{author_id}_{text_id}"
        title = text_data.get('title', text_id)

        cursor.execute("""
            INSERT OR IGNORE INTO works (id, author_id, title, type, urn)
            VALUES (?, ?, ?, ?, ?)
        """, (work_id, author_id, title, text_data.get('genre', 'text'), text_id))

        # Create book entry (one book per text for now)
        book_id = f"{work_id}_1"
        cursor.execute("""
            INSERT OR IGNORE INTO books (id, work_id, book_number, label)
            VALUES (?, ?, ?, ?)
        """, (book_id, work_id, 1, "Text"))

        # Import lines
        line_num = 1
        for line_data in text_data['lines']:
            # Insert text line
            cursor.execute("""
                INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                VALUES (?, ?, ?, ?)
            """, (book_id, line_num, line_num, line_data['transliteration']))

            # Insert words
            words = line_data['transliteration'].split()
            for word_pos, word in enumerate(words, 1):
                normalized = normalize_akkadian_sumerian(word)
                cursor.execute("""
                    INSERT INTO words (word, word_normalized, book_id, line_number,
                                     sequence_number, word_position)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (word, normalized, book_id, line_num, line_num, word_pos))

            # Insert translation if available
            if line_data.get('translation'):
                cursor.execute("""
                    INSERT INTO translation_segments (book_id, start_line, end_line,
                                                     sequence_number, translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (book_id, line_num, line_num, line_num,
                      line_data['translation'], project_name))

            line_num += 1

        texts_imported += 1

    conn.commit()
    print(f"    ✓ Imported {texts_imported} texts")

def import_epsd2_dictionary(conn, dict_dir: Path):
    """
    Import ePSD2 dictionary entries into the database.
    """
    cursor = conn.cursor()

    print("\n  Importing ePSD2 Sumerian dictionary...")

    # Look for glossary files
    glossary_files = list(dict_dir.glob("**/sux.json"))
    if not glossary_files:
        print("    Warning: No ePSD2 glossary files found")
        return

    entries_imported = 0

    for glossary_file in glossary_files:
        try:
            with open(glossary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # ePSD2 glossary format
            if 'entries' in data:
                for entry_id, entry_data in data['entries'].items():
                    headword = entry_data.get('cf', '')  # Citation form
                    if not headword:
                        continue

                    # Build dictionary entry
                    pos = entry_data.get('pos', '')  # Part of speech
                    gw = entry_data.get('gw', '')    # Guide word (meaning)

                    entry_plain = f"{headword}"
                    if pos:
                        entry_plain += f" [{pos}]"
                    if gw:
                        entry_plain += f": {gw}"

                    # Add forms and senses if available
                    if 'forms' in entry_data:
                        forms = ', '.join(f.get('form', '') for f in entry_data['forms'] if f.get('form'))
                        if forms:
                            entry_plain += f"\nForms: {forms}"

                    if 'senses' in entry_data:
                        senses = '\n'.join(f"  - {s.get('mng', '')}" for s in entry_data['senses'] if s.get('mng'))
                        if senses:
                            entry_plain += f"\nMeanings:\n{senses}"

                    normalized = normalize_akkadian_sumerian(headword)

                    cursor.execute("""
                        INSERT OR IGNORE INTO dictionary_entries
                        (headword, headword_normalized, language, entry_plain, source)
                        VALUES (?, ?, ?, ?, ?)
                    """, (headword, normalized, 'sumerian', entry_plain, 'ePSD2'))

                    entries_imported += 1

                    # Also add to lemma map
                    if 'forms' in entry_data:
                        for form_data in entry_data['forms']:
                            form = form_data.get('form', '')
                            if form:
                                form_normalized = normalize_akkadian_sumerian(form)
                                cursor.execute("""
                                    INSERT OR IGNORE INTO lemma_map
                                    (word_form, word_form_normalized, lemma, source, morph_info)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (form, form_normalized, headword, 'ePSD2', pos))

        except Exception as e:
            print(f"    Error parsing glossary: {e}")

    conn.commit()
    print(f"    ✓ Imported {entries_imported} dictionary entries")

def main():
    """Main function to create the cuneiform database."""

    print("=" * 70)
    print("Cuneiform Database Creator")
    print("=" * 70)
    print()
    print(f"Data source: {DATA_DIR}")
    print(f"Output: {OUTPUT_DIR / DB_NAME}")
    print()

    # Check if data directory exists
    if not DATA_DIR.exists():
        print("ERROR: Data directory not found!")
        print("Please run download_oracc_texts.py first to download the ORACC data.")
        sys.exit(1)

    # Create output directory if needed
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create database
    db_path = OUTPUT_DIR / DB_NAME

    # Remove existing database
    if db_path.exists():
        print(f"Removing existing database...")
        db_path.unlink()

    # Create new database
    conn = sqlite3.connect(db_path)

    # Create schema
    create_database_schema(conn)

    # Import Akkadian projects
    print("\n" + "=" * 70)
    print("IMPORTING AKKADIAN TEXTS")
    print("=" * 70)

    akkadian_dir = DATA_DIR / "akkadian"
    if akkadian_dir.exists():
        for project_dir in akkadian_dir.iterdir():
            if project_dir.is_dir():
                import_oracc_project(conn, project_dir, project_dir.name, "akkadian")
    else:
        print("  No Akkadian texts found")

    # Import Sumerian projects
    print("\n" + "=" * 70)
    print("IMPORTING SUMERIAN TEXTS")
    print("=" * 70)

    sumerian_dir = DATA_DIR / "sumerian"
    if sumerian_dir.exists():
        for project_dir in sumerian_dir.iterdir():
            if project_dir.is_dir():
                import_oracc_project(conn, project_dir, project_dir.name, "sumerian")
    else:
        print("  No Sumerian texts found")

    # Import dictionaries
    print("\n" + "=" * 70)
    print("IMPORTING DICTIONARIES")
    print("=" * 70)

    dict_dir = DATA_DIR / "dictionaries"
    if dict_dir.exists():
        # Import ePSD2
        epsd2_dir = dict_dir / "epsd2"
        if epsd2_dir.exists():
            import_epsd2_dictionary(conn, epsd2_dir)
    else:
        print("  No dictionaries found")

    # Get statistics
    cursor = conn.cursor()

    stats = {}
    for table in ['authors', 'works', 'books', 'text_lines', 'words',
                  'translation_segments', 'dictionary_entries', 'lemma_map']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cursor.fetchone()[0]

    # Close database
    conn.close()

    # Compress database
    print("\n" + "=" * 70)
    print("COMPRESSING DATABASE")
    print("=" * 70)

    zip_path = OUTPUT_DIR / DB_ZIP_NAME
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, DB_NAME)

    print(f"✓ Database compressed to {zip_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("DATABASE CREATION COMPLETE")
    print("=" * 70)
    print("\nStatistics:")
    print(f"  Authors:      {stats['authors']:,}")
    print(f"  Works:        {stats['works']:,}")
    print(f"  Books:        {stats['books']:,}")
    print(f"  Text lines:   {stats['text_lines']:,}")
    print(f"  Words:        {stats['words']:,}")
    print(f"  Translations: {stats['translation_segments']:,}")
    print(f"  Dictionary:   {stats['dictionary_entries']:,}")
    print(f"  Lemmas:       {stats['lemma_map']:,}")
    print()
    print(f"Database size: {db_path.stat().st_size / (1024*1024):.1f} MB")
    print(f"Compressed:    {zip_path.stat().st_size / (1024*1024):.1f} MB")
    print()
    print("NOTE: This is a basic import. The ORACC JSON format is complex")
    print("and varies by project. This script provides a starting point")
    print("but may need refinement for production use.")
    print()
    print(f"Database created: {db_path}")
    print(f"Compressed as:    {zip_path}")

if __name__ == "__main__":
    main()