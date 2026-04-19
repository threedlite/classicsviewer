#!/usr/bin/env python3
"""
Process Hebrew Bible OSIS XML from morphhb into SQLite database.

This script follows the New Testament pattern from create_perseus_database.py
and the cuneiform pattern for CSV intermediate format.

Usage:
    python3 process_hebrew_complete.py [book_name]

    book_name: Optional. Process only this book (e.g., "Jonah").
               If omitted, processes all books.

Output:
    - hebrew_texts.csv - Intermediate CSV format for review
    - hebrew_texts.db - SQLite database with text data
    - hebrew_texts.db.zip - Compressed database for distribution
    - hebrew_dictionary.csv - Dictionary entries (BDB + Strong's)
    - hebrew_morphology.csv - Word form to lemma mappings
    - hebrew_lexicon.zip - Packaged dictionary CSVs for app import
"""

import os
import sys
import sqlite3
import xml.etree.ElementTree as ET
import csv
import re
from pathlib import Path
import zipfile

# Hebrew Bible book information
# Structure: canonical_name: (file_abbrev, hebrew_name, num_chapters)
HEBREW_BOOKS = {
    'Genesis': ('Gen', 'בְּרֵאשִׁית', 50),
    'Exodus': ('Exod', 'שְׁמוֹת', 40),
    'Leviticus': ('Lev', 'וַיִּקְרָא', 27),
    'Numbers': ('Num', 'בְּמִדְבַּר', 36),
    'Deuteronomy': ('Deut', 'דְּבָרִים', 34),
    'Joshua': ('Josh', 'יְהוֹשֻׁעַ', 24),
    'Judges': ('Judg', 'שֹׁפְטִים', 21),
    'Ruth': ('Ruth', 'רוּת', 4),
    '1Samuel': ('1Sam', 'שְׁמוּאֵל א', 31),
    '2Samuel': ('2Sam', 'שְׁמוּאֵל ב', 24),
    '1Kings': ('1Kgs', 'מְלָכִים א', 22),
    '2Kings': ('2Kgs', 'מְלָכִים ב', 25),
    '1Chronicles': ('1Chr', 'דִּבְרֵי הַיָּמִים א', 29),
    '2Chronicles': ('2Chr', 'דִּבְרֵי הַיָּמִים ב', 36),
    'Ezra': ('Ezra', 'עֶזְרָא', 10),
    'Nehemiah': ('Neh', 'נְחֶמְיָה', 13),
    'Esther': ('Esth', 'אֶסְתֵּר', 10),
    'Job': ('Job', 'אִיּוֹב', 42),
    'Psalms': ('Ps', 'תְּהִלִּים', 150),
    'Proverbs': ('Prov', 'מִשְׁלֵי', 31),
    'Ecclesiastes': ('Eccl', 'קֹהֶלֶת', 12),
    'Song of Solomon': ('Song', 'שִׁיר הַשִּׁירִים', 8),
    'Isaiah': ('Isa', 'יְשַׁעְיָהוּ', 66),
    'Jeremiah': ('Jer', 'יִרְמְיָהוּ', 52),
    'Lamentations': ('Lam', 'אֵיכָה', 5),
    'Ezekiel': ('Ezek', 'יְחֶזְקֵאל', 48),
    'Daniel': ('Dan', 'דָּנִיֵּאל', 12),
    'Hosea': ('Hos', 'הוֹשֵׁעַ', 14),
    'Joel': ('Joel', 'יוֹאֵל', 3 + 1),  # morphhb has 4 chapters
    'Amos': ('Amos', 'עָמוֹס', 9),
    'Obadiah': ('Obad', 'עֹבַדְיָה', 1),
    'Jonah': ('Jonah', 'יוֹנָה', 4),
    'Micah': ('Mic', 'מִיכָה', 7),
    'Nahum': ('Nah', 'נַחוּם', 3),
    'Habakkuk': ('Hab', 'חֲבַקּוּק', 3),
    'Zephaniah': ('Zeph', 'צְפַנְיָה', 3),
    'Haggai': ('Hag', 'חַגַּי', 2),
    'Zechariah': ('Zech', 'זְכַרְיָה', 14),
    'Malachi': ('Mal', 'מַלְאָכִי', 4),
}

# OSIS namespace
OSIS_NS = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}

class HebrewTextProcessor:
    def __init__(self, morphhb_dir, lexicon_dir, output_dir):
        self.morphhb_dir = Path(morphhb_dir)
        self.lexicon_dir = Path(lexicon_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Data structures
        self.text_data = []  # List of (book_code, chapter, verse, seq, hebrew_text, xml_content)
        self.word_data = []  # List of word entries for words table
        self.lemma_data = {}  # lemma -> (word_forms, morph_info)
        self.global_sequence = 0

    def parse_morph_code(self, morph):
        """Parse OSHB morphology code into readable form."""
        if not morph or len(morph) < 2:
            return morph

        # H prefix indicates Hebrew (vs Aramaic)
        if morph.startswith('H'):
            morph = morph[1:]

        # Parse first character (part of speech)
        pos_map = {
            'A': 'adjective',
            'C': 'conjunction',
            'D': 'adverb',
            'N': 'noun',
            'P': 'pronoun',
            'R': 'preposition',
            'S': 'suffix',
            'T': 'particle',
            'V': 'verb'
        }

        parts = []
        if morph and morph[0] in pos_map:
            parts.append(pos_map[morph[0]])

            # Verb parsing
            if morph[0] == 'V' and len(morph) >= 3:
                stem_map = {'q': 'qal', 'N': 'niphal', 'p': 'piel', 'P': 'pual',
                           'h': 'hiphil', 'H': 'hophal', 't': 'hithpael'}
                conj_map = {'p': 'perfect', 'i': 'imperfect', 'w': 'waw-consecutive',
                           'v': 'imperative', 'a': 'infinitive absolute', 'c': 'infinitive construct',
                           'r': 'participle'}
                if len(morph) > 1 and morph[1] in stem_map:
                    parts.append(stem_map[morph[1]])
                if len(morph) > 2 and morph[2] in conj_map:
                    parts.append(conj_map[morph[2]])

            # Noun parsing
            elif morph[0] == 'N' and len(morph) >= 2:
                type_map = {'c': 'common', 'p': 'proper'}
                if len(morph) > 1 and morph[1] in type_map:
                    parts.append(type_map[morph[1]])

        return ' '.join(parts) if parts else morph

    def extract_text_from_word_elements(self, parent):
        """Extract plain Hebrew text from word elements and segments."""
        text_parts = []
        for elem in parent:
            if elem.tag.endswith('}w'):
                # Word element - get text
                if elem.text:
                    text_parts.append(elem.text.strip())
            elif elem.tag.endswith('}seg'):
                # Segment (punctuation like maqqef) - skip or include as needed
                seg_type = elem.get('type', '')
                if seg_type == 'x-maqqef':
                    # Maqqef is a hyphen-like connector, keep it
                    text_parts.append('־')
                # Skip sof-pasuq (end of verse marker) and paseq
            # Recursively handle nested elements
            if elem.text and not elem.tag.endswith('}w') and not elem.tag.endswith('}seg'):
                text_parts.append(elem.text.strip())
        return ' '.join(text_parts).strip()

    def get_verse_xml(self, verse_elem):
        """Get the complete XML content of a verse for storage in line_xml."""
        return ET.tostring(verse_elem, encoding='unicode', method='xml')

    def process_book(self, book_name):
        """Process a single book from morphhb OSIS XML."""
        # Get file abbreviation and book metadata
        book_info = HEBREW_BOOKS.get(book_name)
        if not book_info:
            print(f"WARNING: Unknown book: {book_name}")
            return False

        file_abbrev, hebrew_name, expected_chapters = book_info
        xml_file = self.morphhb_dir / 'wlc' / f'{file_abbrev}.xml'

        if not xml_file.exists():
            print(f"WARNING: XML file not found: {xml_file}")
            return False

        print(f"Processing {book_name}...")

        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        book_id = f"oshb_{book_name.lower()}"

        # Find all chapters
        chapters = root.findall('.//osis:chapter', OSIS_NS)

        if not chapters:
            print(f"ERROR: No chapters found in {book_name}")
            return False

        print(f"  Found {len(chapters)} chapters")

        for chapter_elem in chapters:
            # Extract chapter number from osisID (e.g., "Jonah.1" -> 1)
            chapter_osis = chapter_elem.get('osisID', '')
            chapter_num = int(chapter_osis.split('.')[-1]) if '.' in chapter_osis else 0

            chapter_id = f"{book_id}_001_ch{chapter_num:02d}"

            # Find all verses in this chapter
            verses = chapter_elem.findall('.//osis:verse', OSIS_NS)

            for verse_elem in verses:
                # Extract verse number from osisID (e.g., "Jonah.1.3" -> 3)
                verse_osis = verse_elem.get('osisID', '')
                verse_parts = verse_osis.split('.')
                verse_num = int(verse_parts[-1]) if len(verse_parts) >= 3 else 0

                # Extract Hebrew text (plain text)
                hebrew_text = self.extract_text_from_word_elements(verse_elem)

                # Extract full XML for line_xml field
                verse_xml = self.get_verse_xml(verse_elem)

                # Increment global sequence
                self.global_sequence += 1

                # Add to text data
                self.text_data.append({
                    'book_code': book_name,
                    'chapter': chapter_num,
                    'verse': verse_num,
                    'sequence_number': self.global_sequence,
                    'hebrew_text': hebrew_text,
                    'xml_content': verse_xml,
                    'chapter_id': chapter_id
                })

                # Extract individual words for words table
                word_position = 0
                for word_elem in verse_elem.findall('.//osis:w', OSIS_NS):
                    word_position += 1
                    word_text = word_elem.text.strip() if word_elem.text else ''
                    lemma = word_elem.get('lemma', '')
                    morph = word_elem.get('morph', '')

                    if word_text:
                        self.word_data.append({
                            'word': word_text,
                            'chapter_id': chapter_id,
                            'verse_number': verse_num,
                            'sequence_number': self.global_sequence,
                            'word_position': word_position,
                            'lemma': lemma,
                            'morph': morph
                        })

                        # Track lemma for dictionary
                        if lemma:
                            if lemma not in self.lemma_data:
                                self.lemma_data[lemma] = {'forms': set(), 'morphs': set()}
                            self.lemma_data[lemma]['forms'].add(word_text)
                            if morph:
                                self.lemma_data[lemma]['morphs'].add(morph)

        print(f"  Processed {len(verses)} verses from {len(chapters)} chapters")
        return True

    def write_csv(self):
        """Write intermediate CSV for review."""
        csv_file = self.output_dir / 'hebrew_texts.csv'

        print(f"\nWriting CSV to {csv_file}...")

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['book_code', 'chapter', 'verse', 'sequence_number',
                           'hebrew_text', 'xml_content'])

            for entry in self.text_data:
                writer.writerow([
                    entry['book_code'],
                    entry['chapter'],
                    entry['verse'],
                    entry['sequence_number'],
                    entry['hebrew_text'],
                    entry['xml_content']
                ])

        print(f"  Wrote {len(self.text_data)} verses")

    def create_database(self):
        """Create SQLite database with existing schema."""
        db_file = self.output_dir / 'hebrew_texts.db'

        print(f"\nCreating database: {db_file}...")

        # Remove existing database
        if db_file.exists():
            db_file.unlink()

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Create schema (matching existing schema exactly)
        print("  Creating schema...")

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
        print("  Creating indexes...")
        cursor.execute('CREATE INDEX idx_authors_language ON authors(language)')
        cursor.execute('CREATE INDEX idx_works_author ON works(author_id)')
        cursor.execute('CREATE INDEX idx_books_work ON books(work_id)')
        cursor.execute('CREATE INDEX idx_text_lines_book ON text_lines(book_id)')
        cursor.execute('CREATE INDEX idx_text_lines_sequence ON text_lines(book_id, sequence_number)')
        cursor.execute('CREATE INDEX idx_translation_segments_book ON translation_segments(book_id)')
        cursor.execute('CREATE INDEX idx_translation_segments_lines ON translation_segments(book_id, start_line)')
        cursor.execute('CREATE INDEX idx_words_word ON words(word)')
        cursor.execute('CREATE INDEX idx_words_book_line_seq ON words(book_id, line_number, sequence_number)')
        cursor.execute('CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)')
        cursor.execute('CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)')

        # Group data by book for insertion
        print("  Populating database...")

        books_processed = {}
        for entry in self.text_data:
            book_code = entry['book_code']

            if book_code not in books_processed:
                # Create author entry (one per Bible book)
                book_info = HEBREW_BOOKS.get(book_code, (book_code, book_code, 0))
                _, hebrew_name, _ = book_info
                author_id = f"oshb_{book_code.lower()}"

                cursor.execute('''
                    INSERT INTO authors (id, name, name_alt, language, has_translations)
                    VALUES (?, ?, ?, ?, ?)
                ''', (author_id, f"{book_code} (OSHB)", hebrew_name, "hebrew", 0))

                # Create work entry (one per Bible book)
                work_id = f"{author_id}_001"
                cursor.execute('''
                    INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (work_id, author_id, book_code, hebrew_name, book_code,
                      "biblical_text", "https://github.com/openscriptures/morphhb",
                      f"Hebrew Bible - {book_code}"))

                books_processed[book_code] = {
                    'author_id': author_id,
                    'work_id': work_id,
                    'chapters': {}
                }

        # Group by chapter and insert books (chapters) and text_lines (verses)
        for entry in self.text_data:
            book_code = entry['book_code']
            chapter = entry['chapter']
            chapter_id = entry['chapter_id']

            book_info = books_processed[book_code]

            # Create book entry for this chapter if not exists
            if chapter not in book_info['chapters']:
                cursor.execute('''
                    INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (chapter_id, book_info['work_id'], chapter, f"Chapter {chapter}",
                      None, None, None))  # Will update counts later

                book_info['chapters'][chapter] = {
                    'chapter_id': chapter_id,
                    'verses': []
                }

            # Insert text_line (verse)
            cursor.execute('''
                INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, line_xml, speaker)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chapter_id, entry['verse'], entry['sequence_number'],
                  entry['hebrew_text'], entry['xml_content'], None))

            book_info['chapters'][chapter]['verses'].append(entry['verse'])

        # Update chapter statistics
        print("  Updating chapter statistics...")
        for book_code, book_info in books_processed.items():
            for chapter_num, chapter_info in book_info['chapters'].items():
                verses = chapter_info['verses']
                cursor.execute('''
                    UPDATE books SET start_line = ?, end_line = ?, line_count = ?
                    WHERE id = ?
                ''', (min(verses), max(verses), len(verses), chapter_info['chapter_id']))

        # Insert words
        print("  Inserting words...")
        for word_entry in self.word_data:
            cursor.execute('''
                INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                VALUES (?, ?, ?, ?, ?)
            ''', (word_entry['word'], word_entry['chapter_id'], word_entry['verse_number'],
                  word_entry['sequence_number'], word_entry['word_position']))

        conn.commit()

        # Get statistics
        author_count = cursor.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
        work_count = cursor.execute('SELECT COUNT(*) FROM works').fetchone()[0]
        book_count = cursor.execute('SELECT COUNT(*) FROM books').fetchone()[0]
        verse_count = cursor.execute('SELECT COUNT(*) FROM text_lines').fetchone()[0]
        word_count = cursor.execute('SELECT COUNT(*) FROM words').fetchone()[0]

        print(f"\n  Database Statistics:")
        print(f"    Authors (books): {author_count}")
        print(f"    Works: {work_count}")
        print(f"    Books (chapters): {book_count}")
        print(f"    Text lines (verses): {verse_count}")
        print(f"    Words: {word_count}")

        conn.close()

        return db_file

    def extract_lexicon_data(self):
        """Extract lexicon data from HebrewLexicon XML files to CSVs."""
        print("\nExtracting lexicon data...")

        # Parse AugIndex to map augmented Strong's numbers to lexical IDs
        aug_index_file = self.lexicon_dir / 'AugIndex.xml'
        aug_to_lex = {}

        if aug_index_file.exists():
            print("  Parsing AugIndex.xml...")
            tree = ET.parse(aug_index_file)
            root = tree.getroot()

            for w_elem in root.findall('.//{http://openscriptures.github.com/morphhb/namespace}w'):
                aug_num = w_elem.get('aug', '')
                lex_id = w_elem.text.strip() if w_elem.text else ''
                if aug_num and lex_id:
                    aug_to_lex[aug_num] = lex_id

        # Parse Strong's dictionary
        strong_file = self.lexicon_dir / 'HebrewStrong.xml'
        strong_entries = {}

        if strong_file.exists():
            print("  Parsing HebrewStrong.xml...")
            tree = ET.parse(strong_file)
            root = tree.getroot()

            ns = {'lex': 'http://openscriptures.github.com/morphhb/namespace'}

            for entry in root.findall('.//lex:entry', ns):
                strongs_num = entry.get('id', '')

                # Get lemma from <w> element
                w_elem = entry.find('./lex:w', ns)
                lemma = w_elem.text.strip() if w_elem is not None and w_elem.text else ''

                # Get definition - it's inside <meaning><def> or <usage>
                definition_parts = []

                # Try <meaning><def>
                meaning_elem = entry.find('./lex:meaning', ns)
                if meaning_elem is not None:
                    for def_elem in meaning_elem.findall('.//lex:def', ns):
                        if def_elem.text:
                            definition_parts.append(def_elem.text.strip())

                # Also get usage if no meaning found
                if not definition_parts:
                    usage_elem = entry.find('./lex:usage', ns)
                    if usage_elem is not None and usage_elem.text:
                        definition_parts.append(usage_elem.text.strip())

                definition = '; '.join(definition_parts) if definition_parts else ''

                if strongs_num and lemma:
                    strong_entries[strongs_num] = {
                        'lemma': lemma,
                        'definition': definition
                    }

        # Write morphology CSV
        morph_csv = self.output_dir / 'hebrew_morphology.csv'
        print(f"\n  Writing {morph_csv}...")

        with open(morph_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['word_form', 'lemma', 'morph_info', 'language', 'confidence', 'source_name'])

            # Use word data collected during text processing
            unique_forms = {}
            for word_entry in self.word_data:
                word = word_entry['word']
                lemma_code = word_entry['lemma']
                morph_code = word_entry['morph']

                # Parse lemma to get actual lemma text
                # Format: "c/1961" or "1961" or "c/b/7225"
                # The numbers correspond to Strong's, prefixes are grammatical particles
                lemma_text = ''
                if lemma_code:
                    # Extract the numeric part (last component)
                    parts = lemma_code.split('/')
                    for part in reversed(parts):
                        if part.isdigit() or (len(part) > 1 and part[-1].isalpha()):
                            # Look up in Strong's - prepend 'H' for Hebrew Strong's format
                            strong_key = f'H{part}'
                            if strong_key in strong_entries:
                                lemma_text = strong_entries[strong_key]['lemma']
                                break

                    if not lemma_text:
                        # Use the full code as fallback
                        lemma_text = lemma_code

                # Parse morph code
                morph_readable = self.parse_morph_code(morph_code)

                key = (word, lemma_text, morph_readable)
                if key not in unique_forms:
                    unique_forms[key] = True
                    writer.writerow([word, lemma_text, morph_readable, 'hebrew', 1.0, 'OSHB morphhb'])

        print(f"    Wrote {len(unique_forms)} unique word forms")

        # Write dictionary CSV
        dict_csv = self.output_dir / 'hebrew_dictionary.csv'
        print(f"\n  Writing {dict_csv}...")

        with open(dict_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['lemma', 'language', 'definition', 'html_definition', 'source_name'])

            # Add Strong's entries
            for strongs_num, entry in strong_entries.items():
                lemma = entry['lemma']
                definition = entry['definition']
                html_def = f"<div>{definition}</div>" if definition else "<div></div>"
                writer.writerow([lemma, 'hebrew', definition, html_def, f"Strong's H{strongs_num}"])

        print(f"    Wrote {len(strong_entries)} dictionary entries")

    def package_lexicon(self):
        """Package dictionary, morphology, and normalization CSVs into ZIP for app import."""
        print("\nPackaging lexicon files...")

        zip_file = self.output_dir / 'hebrew_lexicon.zip'

        # Copy CSVs with standard names
        import shutil
        dict_src = self.output_dir / 'hebrew_dictionary.csv'
        morph_src = self.output_dir / 'hebrew_morphology.csv'
        norm_src = self.output_dir / 'normalization_rules_hebrew.csv'

        # Create temporary copies with standard names
        dict_tmp = self.output_dir / 'dictionary.csv'
        morph_tmp = self.output_dir / 'morphology.csv'
        norm_tmp = self.output_dir / 'normalization_rules.csv'

        shutil.copy(dict_src, dict_tmp)
        shutil.copy(morph_src, morph_tmp)

        # Copy normalization rules if they exist
        if norm_src.exists():
            shutil.copy(norm_src, norm_tmp)

        # Create ZIP
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(dict_tmp, 'dictionary.csv')
            zf.write(morph_tmp, 'morphology.csv')
            if norm_tmp.exists():
                zf.write(norm_tmp, 'normalization_rules.csv')

        # Clean up temporary files
        dict_tmp.unlink()
        morph_tmp.unlink()
        if norm_tmp.exists():
            norm_tmp.unlink()

        print(f"  Created {zip_file}")

    def compress_database(self, db_file):
        """Compress database to .zip for distribution."""
        print("\nCompressing database...")

        zip_file = self.output_dir / 'hebrew_texts.db.zip'

        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write(db_file, 'hebrew_texts.db')

        # Get sizes
        db_size = db_file.stat().st_size / (1024 * 1024)
        zip_size = zip_file.stat().st_size / (1024 * 1024)

        print(f"  Database: {db_size:.2f} MB")
        print(f"  Compressed: {zip_size:.2f} MB")
        print(f"  Compression ratio: {(1 - zip_size/db_size)*100:.1f}%")

        return zip_file


def main():
    """Main entry point."""
    # Determine which books to process
    books_to_process = []

    if len(sys.argv) > 1:
        # Process specific book from command line
        book_name = sys.argv[1]
        if book_name in HEBREW_BOOKS:
            books_to_process = [book_name]
        else:
            print(f"ERROR: Unknown book '{book_name}'")
            print(f"Available books: {', '.join(HEBREW_BOOKS.keys())}")
            sys.exit(1)
    else:
        # Process all books
        books_to_process = list(HEBREW_BOOKS.keys())

    # Setup paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    morphhb_dir = project_root / 'data-sources' / 'morphhb'
    lexicon_dir = project_root / 'data-sources' / 'HebrewLexicon'
    output_dir = script_dir

    # Check prerequisites
    if not morphhb_dir.exists():
        print(f"ERROR: morphhb not found at {morphhb_dir}")
        print("Clone it first: cd data-sources && git clone https://github.com/openscriptures/morphhb.git")
        sys.exit(1)
    if not lexicon_dir.exists():
        print(f"ERROR: HebrewLexicon not found at {lexicon_dir}")
        print("Clone it first: cd data-sources && git clone https://github.com/openscriptures/HebrewLexicon.git")
        sys.exit(1)

    # Create processor
    processor = HebrewTextProcessor(morphhb_dir, lexicon_dir, output_dir)

    # Process books
    print(f"Processing {len(books_to_process)} book(s)...\n")

    for book_name in books_to_process:
        processor.process_book(book_name)

    # Write outputs
    processor.write_csv()
    db_file = processor.create_database()
    processor.extract_lexicon_data()
    processor.package_lexicon()
    processor.compress_database(db_file)

    print("\n" + "="*60)
    print("COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"\nOutput files in {output_dir}:")
    print("  - hebrew_texts.csv (intermediate format)")
    print("  - hebrew_texts.db (SQLite database)")
    print("  - hebrew_texts.db.zip (compressed for distribution)")
    print("  - hebrew_dictionary.csv (intermediate)")
    print("  - hebrew_morphology.csv (intermediate)")
    print("  - hebrew_lexicon.zip (for app import)")
    print("\nNext steps:")
    print("  1. Review hebrew_texts.csv for data accuracy")
    print("  2. Test hebrew_texts.db.zip in Android app")
    print("  3. Import hebrew_lexicon.zip via app UI")


if __name__ == '__main__':
    main()
