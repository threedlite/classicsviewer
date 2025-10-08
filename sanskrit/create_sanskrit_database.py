#!/usr/bin/env python3
"""
Create complete Sanskrit texts database for ClassicsViewer
Includes: Bhagavad Gita + Rig Veda + 5 DCS texts with translations

Sources:
- Bhagavad Gita: Sanskrit Wikisource (CC BY-SA 4.0)
  - English translations: Edwin Arnold (Public Domain), Annie Besant (Public Domain)
- Rig Veda: DCS pada-and-analysis.dat (CC BY 4.0)
  - English translation: Ralph T.H. Griffith (1896) (Public Domain)
- Atharvaveda (Śaunaka): DCS CoNLL-U files (CC BY 4.0)
  - English translation: William Dwight Whitney (1905) (Public Domain)
- Vājasaneyisaṃhitā (Yajur Veda): DCS CoNLL-U files (CC BY 4.0)
  - English translation: Ralph T.H. Griffith (1899) (Public Domain)
- Chāndogyopaniṣad: DCS CoNLL-U files (CC BY 4.0)
  - English translation: Patrick Olivelle (modern, with permission)
- Aitareyopaniṣad: DCS CoNLL-U files (CC BY 4.0)
  - English translation: Patrick Olivelle (modern, with permission)
- Śvetāśvataropaniṣad: DCS CoNLL-U files (CC BY 4.0)
  - English translation: Patrick Olivelle (modern, with permission)

License: CC BY 4.0, CC BY-SA 4.0 & Public Domain (commercial use allowed)
"""

import sqlite3
import json
import csv
import re
import os
import sys
import zipfile
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

    # Create tables (same schema as Greek/Latin/Arabic)
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

def load_bhagavad_gita(cursor):
    """Load Bhagavad Gita text and translations"""
    print("\n" + "=" * 70)
    print("Loading Bhagavad Gita...")
    print("=" * 70)

    # Load Sanskrit text
    text_path = 'data-sources/bhagavad_gita_sanskrit.json'
    if not os.path.exists(text_path):
        print(f"Error: Text file not found: {text_path}")
        print("Run: cd data-sources && python3 parse_bhagavad_gita_sanskrit.py")
        return 0, 0, 0

    with open(text_path, 'r', encoding='utf-8') as f:
        sanskrit_data = json.load(f)

    # Load Arnold's English translation
    arnold_path = 'data-sources/bhagavad_gita_english.json'
    if not os.path.exists(arnold_path):
        print(f"Error: Arnold translation file not found: {arnold_path}")
        return 0, 0, 0

    with open(arnold_path, 'r', encoding='utf-8') as f:
        arnold_data = json.load(f)

    arnold_translations = {}
    for chapter in arnold_data['chapters']:
        chapter_num = chapter['chapter']
        arnold_translations[chapter_num] = chapter['text']

    # Load Besant's English translation
    besant_path = 'data-sources/bhagavad_gita_besant.json'
    besant_data = None
    if os.path.exists(besant_path):
        with open(besant_path, 'r', encoding='utf-8') as f:
            besant_data = json.load(f)

    besant_translations = {}
    if besant_data:
        for chapter in besant_data['chapters']:
            chapter_num = chapter['chapter']
            besant_translations[chapter_num] = {}
            for verse in chapter['verses']:
                verse_num = verse['number']
                besant_translations[chapter_num][verse_num] = verse['text']

    # Insert author
    author_id = 'vyasa'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, 'व्यासः', 'Ved Vyasa', 'sanskrit', 1))

    # Create work
    work_id = 'bhagavad_gita'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, 'भगवद्गीता', None, 'Bhagavad Gita', 'poetry', None,
          'The Bhagavad Gita, 700-verse Hindu scripture that is part of the Mahabharata'))

    total_verses = 0
    total_words = 0
    total_translations = 0

    # Process each chapter as a book
    for chapter_data in sanskrit_data['chapters']:
        chapter_num = chapter_data['chapter']
        verses = chapter_data['verses']

        book_id = f'bhagavad_gita.{chapter_num}'
        book_label = f'Chapter {chapter_num}'

        start_line = verses[0]['number']
        end_line = verses[-1]['number']
        line_count = len(verses)

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, chapter_num, book_label, start_line, end_line, line_count))

        print(f"  Chapter {chapter_num}: {len(verses)} verses")

        # Insert verses
        for verse in verses:
            verse_num = verse['number']
            verse_text = verse['text']

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

        # Insert Arnold's translation (entire chapter)
        if chapter_num in arnold_translations:
            first_verse = verses[0]['number']
            last_verse = verses[-1]['number']

            cursor.execute('''
                INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (None, book_id, first_verse, last_verse, first_verse, arnold_translations[chapter_num], 'Edwin Arnold', None))
            total_translations += 1

        # Insert Besant's translation (verse-by-verse)
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

    print(f"\n  ✓ Loaded {total_verses} verses, {total_words:,} words, {total_translations} translations")
    return total_verses, total_words, total_translations

def load_rigveda(cursor):
    """Load Rig Veda text and translations"""
    print("\n" + "=" * 70)
    print("Loading Rig Veda...")
    print("=" * 70)

    # Load Rig Veda padas from DCS
    pada_file = '../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat'
    if not os.path.exists(pada_file):
        print(f"Error: Rig Veda data file not found: {pada_file}")
        return 0, 0, 0

    print(f"  Reading {pada_file}...")

    # Structure: book → hymn → stanza → [padas]
    rigveda_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    with open(pada_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            book = int(row['book'])
            hymn = int(row['hymn'])
            stanza = int(row['stanza'])
            pada = row['pada']
            text = row['text']

            # Convert IAST to Devanagari
            text_devanagari = iast_to_devanagari(text)

            rigveda_data[book][hymn][stanza].append({
                'pada': pada,
                'text_iast': text,
                'text_devanagari': text_devanagari
            })

    total_hymns = sum(len(hymns) for hymns in rigveda_data.values())
    total_stanzas = sum(
        len(stanzas)
        for hymns in rigveda_data.values()
        for stanzas in hymns.values()
    )

    print(f"  Loaded {len(rigveda_data)} mandalas, {total_hymns} hymns, {total_stanzas} stanzas")

    # Load Griffith translation
    translation_file = '../data-sources/sanskrit/translations/RV-Griffith.txt'
    translations = defaultdict(lambda: defaultdict(dict))

    if os.path.exists(translation_file):
        print(f"  Reading {translation_file}...")
        with open(translation_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(';;;'):
                    continue

                match = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
                if match:
                    book = int(match.group(1))
                    hymn = int(match.group(2))
                    stanza = int(match.group(3))
                    translation_text = match.group(4).strip()
                    translations[book][hymn][stanza] = translation_text

        translation_count = sum(
            len(stanzas)
            for hymns in translations.values()
            for stanzas in hymns.values()
        )
        print(f"  Loaded {translation_count} translations")
    else:
        print(f"  Warning: Translation file not found: {translation_file}")

    # Insert author
    author_id = 'rishis'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, 'ऋषयः', 'Various Rishis', 'sanskrit', 1))

    # Create work
    work_id = 'rigveda'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, 'ऋग्वेदः', 'Ṛgveda', 'Rig Veda', 'poetry', None,
          'The Rig Veda, oldest of the four Vedas, collection of 10 mandalas'))

    total_verses = 0
    total_words = 0
    total_translations = 0

    # Process each mandala
    for book_num in sorted(rigveda_data.keys()):
        hymns = rigveda_data[book_num]

        book_id = f'rigveda.{book_num}'
        book_label = f'Mandala {book_num}'

        line_count = sum(len(stanzas) for stanzas in hymns.values())

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, book_num, book_label, 1, line_count, line_count))

        print(f"  Mandala {book_num}: {len(hymns)} hymns, {line_count} stanzas")

        line_number = 1

        for hymn_num in sorted(hymns.keys()):
            stanzas = hymns[hymn_num]

            for stanza_num in sorted(stanzas.keys()):
                padas = stanzas[stanza_num]

                # Combine padas into verse
                padas_sorted = sorted(padas, key=lambda x: x['pada'])
                verse_text = ' '.join(pada['text_devanagari'] for pada in padas_sorted)

                cursor.execute('''
                    INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (None, book_id, line_number, line_number, verse_text, None, None))

                # Insert words
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

    print(f"\n  ✓ Loaded {total_verses:,} verses, {total_words:,} words, {total_translations:,} translations")
    return total_verses, total_words, total_translations

def load_dcs_text(cursor, text_name, text_dir, translation_file, author_info, work_info, translator_name):
    """
    Generic loader for DCS texts with CoNLL-U files

    Args:
        cursor: Database cursor
        text_name: Display name for logging
        text_dir: Directory path containing CoNLL-U files
        translation_file: Path to translation file
        author_info: Dict with 'id', 'name', 'name_alt' for author
        work_info: Dict with 'id', 'title', 'title_alt', 'title_english', 'type', 'description' for work
        translator_name: Name of translator for attribution
    """
    print("\n" + "=" * 70)
    print(f"Loading {text_name}...")
    print("=" * 70)

    if not os.path.exists(text_dir):
        print(f"Error: Text directory not found: {text_dir}")
        return 0, 0, 0

    print(f"  Reading CoNLL-U files from {text_dir}...")

    # Structure: book → chapter → verse → [sentences]
    text_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    # Parse all CoNLL-U files
    conllu_files = [f for f in os.listdir(text_dir) if f.endswith('.conllu') and not f.endswith('_parsed')]
    conllu_files.sort()

    for conllu_file in conllu_files:
        file_path = os.path.join(text_dir, conllu_file)

        with open(file_path, 'r', encoding='utf-8') as f:
            current_chapter = None
            verse_counter = 0  # Track verses within current chapter

            for line in f:
                line = line.strip()

                # Extract chapter citation (e.g., "## chapter: AU, 1, 1" or "ŚvetU, 1")
                if line.startswith('## chapter:'):
                    chapter_str = line.replace('## chapter:', '').strip()
                    # Parse citation - can be 2, 3, or 4 parts
                    parts = [p.strip() for p in chapter_str.split(',')]

                    if len(parts) == 2:
                        # Format: "ŚvetU, 1" - Only chapter number
                        # Treat chapter as book, track verses sequentially
                        prefix = parts[0]
                        book_num = int(parts[1])
                        current_chapter = (book_num, None, None)
                        verse_counter = 0  # Reset verse counter for new chapter
                    elif len(parts) >= 3:
                        # Format: "AU, 1, 1" or "ChUp, 1, 1, 1"
                        prefix = parts[0]
                        book_num = int(parts[1])
                        chapter_num = int(parts[2])
                        verse_num = int(parts[3]) if len(parts) > 3 else chapter_num
                        current_chapter = (book_num, chapter_num, verse_num)
                        verse_counter = None  # Don't use counter for explicit citations

                # Extract sentence text (e.g., "# text = ...")
                elif line.startswith('# text =') and current_chapter:
                    text_iast = line.replace('# text =', '').strip()
                    text_devanagari = iast_to_devanagari(text_iast)

                    book_num, chapter_num, verse_num = current_chapter

                    # If using verse counter (2-part citations)
                    if verse_counter is not None:
                        verse_counter += 1
                        verse_num = verse_counter
                        chapter_num = 1  # Single "chapter" per book
                        text_data[book_num][chapter_num][verse_num].append(text_devanagari)
                    else:
                        # Use explicit verse number
                        text_data[book_num][chapter_num][verse_num].append(text_devanagari)

    total_books = len(text_data)
    total_chapters = sum(len(chapters) for chapters in text_data.values())
    total_verses = sum(
        len(verses)
        for chapters in text_data.values()
        for verses in chapters.values()
    )

    print(f"  Loaded {total_books} books, {total_chapters} chapters, {total_verses} verses")

    # Load translations
    # Group by (book, chapter) to combine multiple verses per section
    translations = defaultdict(lambda: defaultdict(list))

    if os.path.exists(translation_file):
        print(f"  Reading {translation_file}...")
        with open(translation_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('@') or line.startswith(';;;'):
                    continue

                # Try 3-part citation format: "1.1.1 Translation text..."
                match = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
                if match:
                    book = int(match.group(1))
                    chapter = int(match.group(2))
                    verse = int(match.group(3))
                    translation_text = match.group(4).strip()
                    # Append to list for this (book, chapter) combination
                    translations[book][chapter].append(translation_text)
                    continue

                # Try 2-part citation format: "1.1 Translation text..."
                match = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
                if match:
                    book = int(match.group(1))
                    chapter = 1  # Single chapter per book for 2-part format
                    verse = int(match.group(2))
                    translation_text = match.group(3).strip()
                    translations[book][chapter].append(translation_text)

        translation_count = sum(
            len(verses)
            for chapters in translations.values()
            for verses in chapters.values()
        )
        print(f"  Loaded {translation_count} translation segments")
    else:
        print(f"  Warning: Translation file not found: {translation_file}")

    # Insert author
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_info['id'], author_info['name'], author_info['name_alt'], 'sanskrit', 1))

    # Insert work
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_info['id'], author_info['id'], work_info['title'], work_info.get('title_alt'),
          work_info['title_english'], work_info['type'], None, work_info['description']))

    total_verse_count = 0
    total_word_count = 0
    total_translation_count = 0

    # Process each book
    for book_num in sorted(text_data.keys()):
        chapters = text_data[book_num]

        book_id = f"{work_info['id']}.{book_num}"
        book_label = f"{work_info.get('book_label_prefix', 'Book')} {book_num}"

        line_count = sum(len(verses) for verses in chapters.values())

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_info['id'], book_num, book_label, 1, line_count, line_count))

        print(f"  {book_label}: {len(chapters)} chapters, {line_count} verses")

        line_number = 1

        for chapter_num in sorted(chapters.keys()):
            verses = chapters[chapter_num]

            # Track start/end lines for this chapter
            chapter_start_line = line_number

            for verse_num in sorted(verses.keys()):
                sentences = verses[verse_num]

                # Combine sentences into verse
                verse_text = ' '.join(sentences)

                cursor.execute('''
                    INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (None, book_id, line_number, line_number, verse_text, None, None))

                # Insert words
                words = tokenize_sanskrit(verse_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (id, word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (None, word, book_id, line_number, line_number, word_pos))
                    total_word_count += 1

                total_verse_count += 1
                line_number += 1

            # Insert translation once per chapter (after all verses processed)
            # This covers all verses in this chapter with a single translation segment
            chapter_end_line = line_number - 1
            if book_num in translations and chapter_num in translations[book_num]:
                translation_list = translations[book_num][chapter_num]
                if translation_list:
                    # Combine all translation verses for this section into one text
                    # Number each verse for readability
                    numbered_translations = [f"[{i+1}] {text}" for i, text in enumerate(translation_list)]
                    translation_text = ' '.join(numbered_translations)

                    cursor.execute('''
                        INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, book_id, chapter_start_line, chapter_end_line, chapter_start_line, translation_text, translator_name, None))
                    total_translation_count += 1

    print(f"\n  ✓ Loaded {total_verse_count:,} verses, {total_word_count:,} words, {total_translation_count:,} translations")
    return total_verse_count, total_word_count, total_translation_count

def main():
    print("=" * 70)
    print("Sanskrit Texts Database Creation")
    print("7 texts: Bhagavad Gita + Rig Veda + 5 DCS texts with translations")
    print("=" * 70)

    if not HAS_TRANSLITERATION:
        print("\nWarning: indic-transliteration not installed")
        print("For full functionality: pip install indic-transliteration\n")

    # Create database
    db_path = 'sanskrit_texts.db'
    conn, cursor = create_database(db_path)

    # Track all statistics
    all_stats = []

    # Load Bhagavad Gita
    bg_verses, bg_words, bg_translations = load_bhagavad_gita(cursor)
    all_stats.append(('Bhagavad Gita', bg_verses, bg_words, bg_translations))

    # Load Rig Veda
    rv_verses, rv_words, rv_translations = load_rigveda(cursor)
    all_stats.append(('Rig Veda', rv_verses, rv_words, rv_translations))

    # Load Aitareyopaniṣad
    au_verses, au_words, au_translations = load_dcs_text(
        cursor,
        text_name='Aitareyopaniṣad',
        text_dir='../data-sources/sanskrit/dcs/data/conllu/files/Aitareyopaniṣad',
        translation_file='../data-sources/sanskrit/translations/AU-Olivelle.txt',
        author_info={
            'id': 'vedic_sages',
            'name': 'वैदिकऋषयः',
            'name_alt': 'Vedic Sages'
        },
        work_info={
            'id': 'aitareyopanishad',
            'title': 'ऐतरेयोपनिषद्',
            'title_alt': 'Aitareyopaniṣad',
            'title_english': 'Aitareya Upanishad',
            'type': 'philosophy',
            'description': 'Principal Upanishad from the Rig Veda, teaching about the self (ātman)',
            'book_label_prefix': 'Adhyāya'
        },
        translator_name='Patrick Olivelle'
    )
    all_stats.append(('Aitareyopaniṣad', au_verses, au_words, au_translations))

    # Load Chāndogyopaniṣad
    chup_verses, chup_words, chup_translations = load_dcs_text(
        cursor,
        text_name='Chāndogyopaniṣad',
        text_dir='../data-sources/sanskrit/dcs/data/conllu/files/Chāndogyopaniṣad',
        translation_file='../data-sources/sanskrit/translations/ChUp-Olivelle.txt',
        author_info={
            'id': 'sama_vedic_sages',
            'name': 'सामवेदिकऋषयः',
            'name_alt': 'Sama Vedic Sages'
        },
        work_info={
            'id': 'chandogyopanishad',
            'title': 'छान्दोग्योपनिषद्',
            'title_alt': 'Chāndogyopaniṣad',
            'title_english': 'Chandogya Upanishad',
            'type': 'philosophy',
            'description': 'One of the oldest and largest Upanishads, teaching Vedantic philosophy',
            'book_label_prefix': 'Prapāṭhaka'
        },
        translator_name='Patrick Olivelle'
    )
    all_stats.append(('Chāndogyopaniṣad', chup_verses, chup_words, chup_translations))

    # Load Śvetāśvataropaniṣad
    svet_verses, svet_words, svet_translations = load_dcs_text(
        cursor,
        text_name='Śvetāśvataropaniṣad',
        text_dir='../data-sources/sanskrit/dcs/data/conllu/files/Śvetāśvataropaniṣad',
        translation_file='../data-sources/sanskrit/translations/SvetUp-Olivelle.txt',
        author_info={
            'id': 'svetasvatara',
            'name': 'श्वेताश्वतरः',
            'name_alt': 'Śvetāśvatara'
        },
        work_info={
            'id': 'svetasvataropanishad',
            'title': 'श्वेताश्वतरोपनिषद्',
            'title_alt': 'Śvetāśvataropaniṣad',
            'title_english': 'Svetasvatara Upanishad',
            'type': 'philosophy',
            'description': 'Important theistic Upanishad teaching yoga and meditation',
            'book_label_prefix': 'Adhyāya'
        },
        translator_name='Patrick Olivelle'
    )
    all_stats.append(('Śvetāśvataropaniṣad', svet_verses, svet_words, svet_translations))

    # Load Atharvaveda (Śaunaka)
    av_verses, av_words, av_translations = load_dcs_text(
        cursor,
        text_name='Atharvaveda (Śaunaka)',
        text_dir='../data-sources/sanskrit/dcs/data/conllu/files/Atharvaveda (Śaunaka)',
        translation_file='../data-sources/sanskrit/dcs/data/atharvaveda-shaunaka/translations/whitney.txt',
        author_info={
            'id': 'atharvan_rishis',
            'name': 'अथर्वऋषयः',
            'name_alt': 'Atharvan Rishis'
        },
        work_info={
            'id': 'atharvaveda',
            'title': 'अथर्ववेदः',
            'title_alt': 'Atharvaveda (Śaunaka)',
            'title_english': 'Atharva Veda',
            'type': 'poetry',
            'description': 'The fourth Veda, collection of spells, charms, incantations, and hymns',
            'book_label_prefix': 'Kāṇḍa'
        },
        translator_name='William Dwight Whitney'
    )
    all_stats.append(('Atharvaveda', av_verses, av_words, av_translations))

    # Load Vājasaneyisaṃhitā (Yajur Veda)
    vs_verses, vs_words, vs_translations = load_dcs_text(
        cursor,
        text_name='Vājasaneyisaṃhitā (Yajur Veda)',
        text_dir='../data-sources/sanskrit/dcs/data/conllu/files/Vājasaneyisaṃhitā (Mādhyandina)',
        translation_file='../data-sources/sanskrit/translations/VS-Griffith.txt',
        author_info={
            'id': 'yajur_rishis',
            'name': 'यजुर्वैदिकऋषयः',
            'name_alt': 'Yajur Vedic Rishis'
        },
        work_info={
            'id': 'vajasaneyisamhita',
            'title': 'वाजसनेयिसंहिता',
            'title_alt': 'Vājasaneyisaṃhitā',
            'title_english': 'Vajasaneyi Samhita (White Yajur Veda)',
            'type': 'poetry',
            'description': 'The White Yajur Veda, sacrificial formulas and prose instructions',
            'book_label_prefix': 'Adhyāya'
        },
        translator_name='Ralph T.H. Griffith'
    )
    all_stats.append(('Vājasaneyisaṃhitā', vs_verses, vs_words, vs_translations))

    # Check if any texts loaded
    total_verses_loaded = sum(stat[1] for stat in all_stats)
    if total_verses_loaded == 0:
        print("\nError: No texts loaded. Exiting.")
        conn.close()
        return 1

    # Get final statistics
    cursor.execute('SELECT COUNT(*) FROM authors')
    author_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM works')
    work_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM books')
    book_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM text_lines')
    total_verses = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM words')
    total_words = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT word) FROM words')
    unique_words = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM translation_segments')
    total_translations = cursor.fetchone()[0]

    # Commit and close
    conn.commit()
    conn.close()

    # Compress database
    print("\nCompressing database...")
    zip_path = 'sanskrit_texts.db.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(db_path)

    # Get file sizes
    db_size = os.path.getsize(db_path) / 1024 / 1024  # MB
    zip_size = os.path.getsize(zip_path) / 1024 / 1024  # MB

    print("\n" + "=" * 70)
    print("Database Creation Complete!")
    print("=" * 70)
    print(f"\nContents:")
    print(f"  Authors: {author_count}")
    print(f"  Works: {work_count}")
    print(f"  Books: {book_count}")
    print(f"\nTexts loaded:")
    for text_name, verses, words, translations in all_stats:
        print(f"  - {text_name}: {verses:,} verses, {words:,} words, {translations:,} translations")
    print(f"\nStatistics:")
    print(f"  Total verses: {total_verses:,}")
    print(f"  Total words: {total_words:,}")
    print(f"  Unique words: {unique_words:,}")
    print(f"  Translations: {total_translations:,}")
    print(f"\nFiles:")
    print(f"  Database: {db_path} ({db_size:.2f} MB)")
    print(f"  Compressed: {zip_path} ({zip_size:.2f} MB)")
    print(f"\nLicenses:")
    print(f"  ✓ Bhagavad Gita Sanskrit: CC BY-SA 4.0 (Wikisource)")
    print(f"  ✓ BG English (Arnold, Besant): Public Domain")
    print(f"  ✓ DCS Sanskrit texts: CC BY 4.0 (Oliver Hellwig)")
    print(f"  ✓ RV, AV, VS English (Griffith, Whitney): Public Domain")
    print(f"  ✓ Upanishads English (Olivelle): Used with permission")
    print(f"\nReady for ClassicsViewer integration!")

    return 0

if __name__ == '__main__':
    sys.exit(main() or 0)
