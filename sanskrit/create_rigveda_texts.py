#!/usr/bin/env python3
"""
Create Rig Veda texts database for ClassicsViewer
Uses complete Rig Veda from DCS (all 10 mandalas, 39,830 padas)

Sources:
- Sanskrit text: DCS rigveda/pada-and-analysis.dat (CC BY 4.0)
- English translation: Ralph T.H. Griffith (1896) (Public Domain)
- Morphology: DCS lexicon (already extracted)

License: CC BY 4.0 & Public Domain (commercial use allowed)
"""

import sqlite3
import json
import csv
import re
import os
import sys
from collections import defaultdict

# Try to import indic-transliteration
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    HAS_TRANSLITERATION = True
except ImportError:
    print("Warning: indic-transliteration not installed. Install with: pip install indic-transliteration")
    HAS_TRANSLITERATION = False

def iast_to_devanagari(text):
    """Convert IAST to Devanagari for display"""
    if not HAS_TRANSLITERATION:
        return text
    try:
        return transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except:
        return text

def tokenize_sanskrit(text):
    """Tokenize Sanskrit text into words"""
    # Remove punctuation
    text = re.sub(r'[।॥,;।\.\?\!]', ' ', text)
    # Split on whitespace
    words = text.split()
    # Filter out empty strings
    return [w.strip() for w in words if w.strip()]

def create_database(db_path):
    """Create Rig Veda texts database"""
    print(f"Creating database: {db_path}")

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same schema as other texts)
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
            FOREIGN KEY (author_id) REFERENCES authors(id)
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
            FOREIGN KEY (work_id) REFERENCES works(id)
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
            FOREIGN KEY (book_id) REFERENCES books(id)
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
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER NOT NULL,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # Create indexes
    print("Creating indexes...")
    cursor.execute('CREATE INDEX idx_books_work ON books(work_id)')
    cursor.execute('CREATE INDEX idx_text_lines_book ON text_lines(book_id)')
    cursor.execute('CREATE INDEX idx_words_book ON words(book_id)')
    cursor.execute('CREATE INDEX idx_translation_segments_book ON translation_segments(book_id)')

    conn.commit()
    return conn, cursor

def load_rigveda_text():
    """Load Rig Veda padas from DCS data"""
    pada_file = '../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat'

    if not os.path.exists(pada_file):
        print(f"Error: Rig Veda data file not found: {pada_file}")
        return None

    print(f"\nLoading Rig Veda text from {pada_file}...")

    # Structure: book → hymn → stanza → [padas]
    rigveda_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    with open(pada_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            book = int(row['book'])
            hymn = int(row['hymn'])
            stanza = int(row['stanza'])
            pada = row['pada']  # 'a', 'b', 'c', 'd'
            text = row['text']  # IAST format

            # Convert IAST to Devanagari
            text_devanagari = iast_to_devanagari(text)

            rigveda_data[book][hymn][stanza].append({
                'pada': pada,
                'text_iast': text,
                'text_devanagari': text_devanagari
            })

    print(f"Loaded {len(rigveda_data)} mandalas")

    # Count total hymns and stanzas
    total_hymns = sum(len(hymns) for hymns in rigveda_data.values())
    total_stanzas = sum(
        len(stanzas)
        for hymns in rigveda_data.values()
        for stanzas in hymns.values()
    )

    print(f"  Total hymns: {total_hymns}")
    print(f"  Total stanzas: {total_stanzas}")

    return rigveda_data

def load_griffith_translation():
    """Load Griffith's English translation"""
    translation_file = '../data-sources/sanskrit/translations/RV-Griffith.txt'

    if not os.path.exists(translation_file):
        print(f"Warning: Griffith translation not found: {translation_file}")
        return {}

    print(f"\nLoading Griffith translation from {translation_file}...")

    # Structure: book → hymn → stanza → translation
    translations = defaultdict(lambda: defaultdict(dict))
    current_hymn_title = None

    with open(translation_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for hymn title (;;; Title)
            if line.startswith(';;;'):
                current_hymn_title = line[3:].strip()
                continue

            # Parse citation line (e.g., "1.1.1 Translation text...")
            match = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
            if match:
                book = int(match.group(1))
                hymn = int(match.group(2))
                stanza = int(match.group(3))
                translation_text = match.group(4).strip()

                translations[book][hymn][stanza] = translation_text

    # Count translations
    total_translations = sum(
        len(stanzas)
        for hymns in translations.values()
        for stanzas in hymns.values()
    )

    print(f"Loaded {total_translations} translation stanzas")

    return translations

def insert_rigveda_data(cursor, rigveda_data, translations):
    """Insert Rig Veda text and translations into database"""

    # Insert author - using "Various Rishis" as the collective author
    author_id = 'rishis'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, 'ऋषयः', 'Various Rishis', 'sanskrit', 1))

    # Create single work for Rig Veda
    work_id = 'rigveda'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, 'ऋग्वेदः', 'Ṛgveda', 'Rig Veda', 'poetry', None,
          'The Rig Veda, oldest of the four Vedas, collection of 10 mandalas'))

    total_verses = 0
    total_words = 0
    total_translations = 0

    # Process each mandala (book)
    for book_num in sorted(rigveda_data.keys()):
        hymns = rigveda_data[book_num]

        # Create book for this mandala
        book_id = f'rigveda.{book_num}'
        book_label = f'Mandala {book_num}'

        # Calculate line count (stanzas in this mandala)
        line_count = sum(len(stanzas) for stanzas in hymns.values())

        # We'll use continuous line numbering across all hymns in the mandala
        start_line = 1
        end_line = line_count

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, book_num, book_label, start_line, end_line, line_count))

        print(f"\nProcessing Mandala {book_num} ({len(hymns)} hymns, {line_count} stanzas)")

        # Line numbering within the book (continuous across hymns)
        line_number = 1

        # Process each hymn in this mandala
        for hymn_num in sorted(hymns.keys()):
            stanzas = hymns[hymn_num]

            # Process each stanza in this hymn
            for stanza_num in sorted(stanzas.keys()):
                padas = stanzas[stanza_num]

                # Combine all padas into one verse text
                # Sort padas by their letter (a, b, c, d)
                padas_sorted = sorted(padas, key=lambda x: x['pada'])

                # Join padas with spaces
                verse_text = ' '.join(pada['text_devanagari'] for pada in padas_sorted)

                # Insert verse as a text line
                cursor.execute('''
                    INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (None, book_id, line_number, line_number, verse_text, None, None))

                # Tokenize and insert words
                words = tokenize_sanskrit(verse_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (id, word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (None, word, book_id, line_number, line_number, word_pos))
                    total_words += 1

                # Insert translation if available
                if book_num in translations and hymn_num in translations[book_num] and stanza_num in translations[book_num][hymn_num]:
                    translation_text = translations[book_num][hymn_num][stanza_num]

                    cursor.execute('''
                        INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, book_id, line_number, line_number, line_number, translation_text, 'Ralph T.H. Griffith', None))
                    total_translations += 1

                total_verses += 1
                line_number += 1

    print(f"\nLoaded {total_verses} verses with {total_words:,} words and {total_translations} translations")

    return total_verses, total_words, total_translations

def main():
    print("=" * 70)
    print("Rig Veda Database Creation")
    print("Complete Rig Veda: 10 Mandalas, ~10,600 verses")
    print("Sanskrit text (Devanagari) + English translation (Griffith)")
    print("=" * 70)

    if not HAS_TRANSLITERATION:
        print("\nNote: Running without indic-transliteration library")
        print("For full functionality, install it with:")
        print("  pip install indic-transliteration\n")

    # Load Rig Veda text
    rigveda_data = load_rigveda_text()
    if not rigveda_data:
        print("\nError: Could not load Rig Veda text. Exiting.")
        return 1

    # Load Griffith translation
    translations = load_griffith_translation()

    # Create database
    db_path = 'rigveda_texts.db'
    conn, cursor = create_database(db_path)

    # Insert data
    verse_count, word_count, translation_count = insert_rigveda_data(cursor, rigveda_data, translations)

    if verse_count == 0:
        print("\nError: No text loaded. Exiting.")
        conn.close()
        return 1

    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM authors')
    author_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM works')
    work_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM books')
    book_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT word) FROM words')
    unique_word_count = cursor.fetchone()[0]

    # Commit and close
    conn.commit()
    conn.close()

    # Create compressed version
    print("\nCompressing database...")
    import zipfile
    zip_path = 'rigveda_texts.db.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(db_path)

    # Get file sizes
    db_size = os.path.getsize(db_path) / 1024 / 1024  # MB
    zip_size = os.path.getsize(zip_path) / 1024 / 1024  # MB

    print("\n" + "=" * 70)
    print("Database Creation Complete!")
    print("=" * 70)
    print(f"Authors: {author_count}")
    print(f"Works: {work_count}")
    print(f"Books (Mandalas): {book_count}")
    print(f"Verses: {verse_count:,}")
    print(f"Translations: {translation_count:,}")
    print(f"Total words: {word_count:,}")
    print(f"Unique words: {unique_word_count:,}")
    print(f"\nDatabase size: {db_size:.2f} MB")
    print(f"Compressed size: {zip_size:.2f} MB")
    print(f"\nFiles created:")
    print(f"  - {db_path}")
    print(f"  - {zip_path}")
    print("\nThis is Vedic Sanskrit text with aligned translation:")
    print("  ✓ Sanskrit: DCS Rig Veda pada-and-analysis (CC BY 4.0)")
    print("  ✓ English: Ralph T.H. Griffith translation (1896, Public Domain)")
    print("  ✓ Text in Devanagari script (converted from IAST)")
    print("  ✓ 10 mandalas as books")
    print("  ✓ Same database schema as Greek/Latin/Arabic/Bhagavad Gita")
    print(f"  ✓ Translation coverage: {translation_count}/{verse_count} verses ({100*translation_count/verse_count:.1f}%)")
    print("\nLicense: CC BY 4.0 & Public Domain (commercial use allowed)")
    print("Sources:")
    print("  - Sanskrit: Digital Corpus of Sanskrit (Oliver Hellwig)")
    print("  - English: Griffith translation (sacred-texts.com)")
    print("\nAttribution required for DCS:")
    print("  Digital Corpus of Sanskrit (DCS)")
    print("  Author: Oliver Hellwig")
    print("  License: CC BY 4.0")
    print("  Source: http://www.sanskrit-linguistics.org/dcs/")

if __name__ == '__main__':
    sys.exit(main() or 0)
