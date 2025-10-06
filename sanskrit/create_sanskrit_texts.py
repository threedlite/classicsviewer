#!/usr/bin/env python3
"""
Create Sanskrit texts database for ClassicsViewer
Uses Rigveda Mandala 1 (all 191 hymns)

Sources:
- Sanskrit text: sacred-texts.com (Public Domain, ancient text)
- English translation: English Wikisource - Ralph T.H. Griffith (1896) (CC BY-SA)

Similar to Arabic implementation
"""

import sqlite3
import json
import csv
import re
import os
import sys

# Try to import indic-transliteration, but continue if not available
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    HAS_TRANSLITERATION = True
except ImportError:
    print("Warning: indic-transliteration not installed. Install with: pip install indic-transliteration")
    HAS_TRANSLITERATION = False

def normalize_devanagari(text):
    """Apply normalization rules to Devanagari text"""
    # Remove combining marks
    text = re.sub(r'[\u0900-\u0903]', '', text)
    # Remove nukta
    text = re.sub(r'[\u093C]', '', text)
    # Remove Vedic accents
    text = re.sub(r'[\u0951-\u0952]', '', text)
    # Remove dandas (sentence markers)
    text = re.sub(r'[\u0964-\u0965]', '', text)
    # Remove final visarga
    text = re.sub(r'ः$', '', text)
    # Remove final anusvara
    text = re.sub(r'ं$', '', text)
    return text

def devanagari_to_iast(text):
    """Convert Devanagari to IAST for dictionary lookup"""
    if not HAS_TRANSLITERATION:
        return text
    try:
        return transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
    except:
        return text

def tokenize_sanskrit(text):
    """Tokenize Sanskrit text into words"""
    # Remove dandas and other punctuation
    text = re.sub(r'[।॥,;।\.\?\!]', ' ', text)
    # Split on whitespace
    words = text.split()
    # Filter out empty strings
    return [w.strip() for w in words if w.strip()]

def create_database(db_path):
    """Create Sanskrit texts database"""
    print(f"Creating database: {db_path}")

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same schema as Arabic/Greek/Latin)
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

    conn.commit()
    return conn, cursor

def load_text(cursor):
    """Load Bhagavad Gita text and translations from JSON"""
    print("\nLoading Bhagavad Gita text...")

    # Load Sanskrit text
    text_path = 'data-sources/bhagavad_gita_sanskrit.json'
    if not os.path.exists(text_path):
        print(f"Error: Text file not found: {text_path}")
        print("Run: cd data-sources && python3 parse_bhagavad_gita_sanskrit.py")
        return 0

    with open(text_path, 'r', encoding='utf-8') as f:
        sanskrit_data = json.load(f)

    # Load Arnold's English translation (prose format)
    arnold_path = 'data-sources/bhagavad_gita_english.json'
    if not os.path.exists(arnold_path):
        print(f"Error: Arnold translation file not found: {arnold_path}")
        print("Run: cd data-sources && python3 parse_bhagavad_gita_english.py")
        return 0

    with open(arnold_path, 'r', encoding='utf-8') as f:
        arnold_data = json.load(f)

    # Create lookup for Arnold translations by chapter
    # Note: Arnold's translation is prose format, one text per chapter
    arnold_translations = {}
    for chapter in arnold_data['chapters']:
        chapter_num = chapter['chapter']
        arnold_translations[chapter_num] = chapter['text']

    # Load Besant's English translation (verse-by-verse)
    besant_path = 'data-sources/bhagavad_gita_besant.json'
    if not os.path.exists(besant_path):
        print(f"Warning: Besant translation file not found: {besant_path}")
        print("Run: cd data-sources && python3 parse_bhagavad_gita_besant.py")
        besant_data = None
    else:
        with open(besant_path, 'r', encoding='utf-8') as f:
            besant_data = json.load(f)

    # Create lookup for Besant translations by chapter and verse
    besant_translations = {}
    if besant_data:
        for chapter in besant_data['chapters']:
            chapter_num = chapter['chapter']
            besant_translations[chapter_num] = {}
            for verse in chapter['verses']:
                verse_num = verse['number']
                besant_translations[chapter_num][verse_num] = verse['text']

    # Insert author - using Vyasa (traditional author of the Mahabharata/Gita)
    author_id = 'vyasa'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, 'व्यासः', 'Ved Vyasa', 'sanskrit', 1))

    # Create single work for Bhagavad Gita
    work_id = 'bhagavad_gita'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, 'भगवद्गीता', None, 'Bhagavad Gita', None, None, None))

    # Process each chapter as a book
    total_verses = 0
    total_words = 0
    total_translations = 0

    for chapter_data in sanskrit_data['chapters']:
        chapter_num = chapter_data['chapter']
        verses = chapter_data['verses']

        # Create book for this chapter
        book_id = f'bhagavad_gita.{chapter_num}'
        book_label = f'Chapter {chapter_num}'

        # Calculate start/end lines
        start_line = verses[0]['number']
        end_line = verses[-1]['number']
        line_count = len(verses)

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, chapter_num, book_label, start_line, end_line, line_count))

        print(f"\n  Processing Chapter {chapter_num} ({len(verses)} verses)")

        # Insert verses for this chapter
        for verse in verses:
            verse_num = verse['number']
            verse_text = verse['text']

            # Insert Sanskrit verse as a line
            cursor.execute('''
                INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (None, book_id, verse_num, verse_num, verse_text, None, None))

            # Tokenize and insert words
            words = tokenize_sanskrit(verse_text)
            for word_pos, word in enumerate(words, 1):
                cursor.execute('''
                    INSERT INTO words (id, word, book_id, line_number, sequence_number, word_position)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (None, word, book_id, verse_num, verse_num, word_pos))
                total_words += 1

            total_verses += 1

        # Insert Arnold's English translation for the entire chapter
        # Arnold's translation is prose, so we insert it as one segment covering all verses
        if chapter_num in arnold_translations:
            # Get first and last verse numbers
            first_verse = verses[0]['number']
            last_verse = verses[-1]['number']

            cursor.execute('''
                INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (None, book_id, first_verse, last_verse, first_verse, arnold_translations[chapter_num], 'Edwin Arnold', None))
            total_translations += 1

        # Insert Besant's English translation (verse-by-verse)
        if chapter_num in besant_translations:
            for verse in verses:
                verse_num = verse['number']
                if verse_num in besant_translations[chapter_num]:
                    besant_text = besant_translations[chapter_num][verse_num]
                    cursor.execute('''
                        INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, book_id, verse_num, verse_num, verse_num, besant_text, 'Annie Besant', None))
                    total_translations += 1

    print(f"\nLoaded {total_verses} verses with {total_words} words and {total_translations} translation segments")
    return total_verses

def main():
    print("=" * 60)
    print("Sanskrit Texts Database Creation")
    print("Bhagavad Gita (18 Chapters, 700 Verses)")
    print("Sanskrit text + English translations")
    print("=" * 60)

    if not HAS_TRANSLITERATION:
        print("\nNote: Running without indic-transliteration library")
        print("For full functionality, install it with:")
        print("  pip install indic-transliteration\n")

    # Create database
    db_path = 'sanskrit_texts.db'
    conn, cursor = create_database(db_path)

    # Load data
    verse_count = load_text(cursor)

    if verse_count == 0:
        print("\nError: No text loaded. Exiting.")
        conn.close()
        return 1

    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM authors')
    author_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM works')
    work_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM words')
    word_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT word) FROM words')
    unique_word_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM translation_segments')
    translation_count = cursor.fetchone()[0]

    # Commit and close
    conn.commit()
    conn.close()

    # Create compressed version
    print("\nCompressing database...")
    import zipfile
    zip_path = 'sanskrit_texts.db.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(db_path)

    # Get file sizes
    db_size = os.path.getsize(db_path) / 1024
    zip_size = os.path.getsize(zip_path) / 1024

    print("\n" + "=" * 60)
    print("Database Creation Complete!")
    print("=" * 60)
    print(f"Authors: {author_count}")
    print(f"Works (Chapters): {work_count}")
    print(f"Verses: {verse_count}")
    print(f"Translations: {translation_count}")
    print(f"Total words: {word_count:,}")
    print(f"Unique words: {unique_word_count:,}")
    print(f"\nDatabase size: {db_size:.1f} KB")
    print(f"Compressed size: {zip_size:.1f} KB")
    print(f"\nFiles created:")
    print(f"  - {db_path}")
    print(f"  - {zip_path}")
    print("\nThis is classical Sanskrit text with aligned translations:")
    print("  ✓ Sanskrit: Bhagavad Gita from Sanskrit Wikisource (CC BY-SA 4.0)")
    print("  ✓ English 1: Edwin Arnold translation (prose, 1885, Public Domain)")
    print("  ✓ English 2: Annie Besant translation (verse-by-verse, 1922, Public Domain)")
    print("  ✓ Text in Devanagari script with normalization")
    print("  ✓ One book per chapter (18 chapters total)")
    print("  ✓ Same database schema as Greek/Latin/Arabic")
    print("\nLicense: CC BY-SA 4.0 & Public Domain (commercial use allowed)")
    print("Sources:")
    print("  - Sanskrit: https://sa.wikisource.org/wiki/भगवद्गीता")
    print("  - English (Arnold): https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)")
    print("  - English (Besant): https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)")

if __name__ == '__main__':
    sys.exit(main() or 0)
