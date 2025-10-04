#!/usr/bin/env python3
"""
Create Persian texts database from Perseus canonical-farsiLit repository.
This script processes Hafez's Divan with parallel Persian-English texts.

Database structure matches ClassicsViewer schema exactly.
"""

import sqlite3
import xml.etree.ElementTree as ET
import re
import os
from pathlib import Path

# TEI namespace
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

class PersianDatabaseCreator:
    def __init__(self, db_path='persian_texts.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def create_schema(self):
        """Create database schema matching ClassicsViewer structure exactly."""
        print("Creating database schema...")

        schema = """
        -- Authors
        CREATE TABLE IF NOT EXISTS authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        );

        -- Works
        CREATE TABLE IF NOT EXISTS works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        );

        -- Books
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        );

        -- Text lines (Persian original)
        CREATE TABLE IF NOT EXISTS text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        -- Translation segments (English)
        CREATE TABLE IF NOT EXISTS translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        -- Translation lookup for alignment
        CREATE TABLE IF NOT EXISTS translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id)
        );

        -- Individual words for search
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_authors_language ON authors(language);
        CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id);
        CREATE INDEX IF NOT EXISTS idx_books_work ON books(work_id);
        CREATE INDEX IF NOT EXISTS idx_text_lines_book ON text_lines(book_id);
        CREATE INDEX IF NOT EXISTS idx_text_lines_sequence ON text_lines(book_id, sequence_number);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_book ON translation_segments(book_id);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_lines ON translation_segments(book_id, start_line);
        CREATE INDEX IF NOT EXISTS idx_translation_lookup ON translation_lookup(book_id, line_number);
        CREATE INDEX IF NOT EXISTS idx_words_word ON words(word);
        CREATE INDEX IF NOT EXISTS idx_words_book_line_seq ON words(book_id, line_number, sequence_number);
        """

        self.cursor.executescript(schema)
        self.conn.commit()
        print("✓ Schema created")

    def split_into_words(self, text):
        """Split Persian text into words."""
        # Split on whitespace and common punctuation
        words = re.split(r'[\s\u200C،؛؟]+', text)
        return [w.strip() for w in words if w.strip()]

    def parse_hafez_divan(self):
        """Parse Hafez Divan Persian and English XML files."""
        persian_file = '../data-sources/canonical-farsiLit/data/hafez/divan/hafez.divan.perseus-far1.xml'
        english_file = '../data-sources/canonical-farsiLit/data/hafez/divan/hafez.divan.perseus-eng1.xml'

        print(f"\nParsing Hafez Divan...")
        print(f"  Persian: {persian_file}")
        print(f"  English: {english_file}")

        # Parse Persian text
        tree_persian = ET.parse(persian_file)
        root_persian = tree_persian.getroot()

        # Parse English translation
        tree_english = ET.parse(english_file)
        root_english = tree_english.getroot()

        # Get metadata
        author_name = root_persian.find('.//tei:author', NS).text
        work_title = root_persian.find('.//tei:title[@type="work"]', NS).text

        # Create IDs
        author_id = 'hafez'
        work_id = 'hafez.divan'
        book_id = 'hafez.divan.1'

        # Insert author
        self.cursor.execute("""
            INSERT OR REPLACE INTO authors (id, name, language, has_translations)
            VALUES (?, ?, ?, ?)
        """, (author_id, author_name, 'persian', 1))

        # Insert work
        self.cursor.execute("""
            INSERT OR REPLACE INTO works (id, author_id, title, title_english, type, urn)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (work_id, author_id, work_title, 'Divan', 'poetry', 'urn:cts:farsiLit:hafez.divan'))

        print(f"  Author: {author_name}")
        print(f"  Work: {work_title}")

        # Process Persian text and English translation
        line_count = self._process_parallel_texts(root_persian, root_english, book_id, work_id)

        # Insert book with line count
        self.cursor.execute("""
            INSERT OR REPLACE INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_id, work_id, 1, 'Complete Divan', 1, line_count, line_count))

        self.conn.commit()

    def _process_parallel_texts(self, persian_root, english_root, book_id, work_id):
        """Process Persian text and English translation with alignment."""

        # Find all divisions (letters/poems)
        persian_body = persian_root.find('.//tei:body/tei:div', NS)
        english_body = english_root.find('.//tei:body/tei:div', NS)

        line_counter = 1  # Global line counter across all poems (this is sequence_number)
        global_line_number = 1  # This is the line_number for the entire book

        # Process each letter (Alif, Ba, etc.)
        for letter_div in persian_body.findall('./tei:div[@subtype="letter"]', NS):
            letter_n = letter_div.get('n')

            # Find corresponding English letter
            english_letter = english_body.find(f'./tei:div[@subtype="letter"][@n="{letter_n}"]', NS)

            # Process each poem in this letter
            for poem_div in letter_div.findall('./tei:div[@subtype="poem"]', NS):
                poem_n = poem_div.get('n')

                # Find corresponding English poem
                english_poem = None
                if english_letter is not None:
                    english_poem = english_letter.find(f'./tei:div[@subtype="poem"][@n="{poem_n}"]', NS)

                # Process each line in the poem
                for line_elem in poem_div.findall('./tei:l', NS):
                    line_n = line_elem.get('n')

                    # Combine both segments (couplet halves) into one line
                    segments = line_elem.findall('./tei:seg', NS)
                    persian_text_parts = []
                    english_text_parts = []

                    for seg in segments:
                        seg_n = seg.get('n')
                        persian_text = seg.text or ''
                        persian_text_parts.append(persian_text.strip())

                        # Get corresponding English segment
                        if english_poem is not None:
                            english_line = english_poem.find(f'./tei:l[@n="{line_n}"]', NS)
                            if english_line is not None:
                                english_seg = english_line.find(f'./tei:seg[@n="{seg_n}"]', NS)
                                if english_seg is not None and english_seg.text:
                                    # Remove markers (###, ***)
                                    eng_text = english_seg.text.replace('###', '').replace('***', '').strip()
                                    english_text_parts.append(eng_text)

                    # Combine both halves of the couplet
                    persian_line = ' '.join(persian_text_parts)
                    english_line = ' '.join(english_text_parts)

                    if not persian_line.strip():
                        continue

                    # Insert Persian text line
                    self.cursor.execute("""
                        INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                        VALUES (?, ?, ?, ?)
                    """, (book_id, global_line_number, line_counter, persian_line))

                    # Insert English translation segment if available
                    if english_line.strip():
                        self.cursor.execute("""
                            INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (book_id, global_line_number, global_line_number, line_counter, english_line, 'H. Wilberforce Clarke'))

                        segment_id = self.cursor.lastrowid

                        # Insert translation lookup
                        self.cursor.execute("""
                            INSERT INTO translation_lookup (book_id, line_number, segment_id)
                            VALUES (?, ?, ?)
                        """, (book_id, global_line_number, segment_id))

                    # Process words
                    words = self.split_into_words(persian_line)
                    for word_pos, word in enumerate(words, 1):
                        if word.strip():
                            self.cursor.execute("""
                                INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                                VALUES (?, ?, ?, ?, ?)
                            """, (word, book_id, global_line_number, line_counter, word_pos))

                    line_counter += 1
                    global_line_number += 1

        print(f"  Processed {line_counter - 1} lines")
        return line_counter - 1

    def create_database(self):
        """Main method to create the Persian database."""
        print(f"Creating Persian database: {self.db_path}")

        # Remove existing database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"  Removed existing database")

        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        try:
            # Create schema
            self.create_schema()

            # Parse and import Hafez Divan
            self.parse_hafez_divan()

            # Get statistics
            self._print_statistics()

            print(f"\n✓ Database created successfully: {self.db_path}")

        finally:
            if self.conn:
                self.conn.close()

    def _print_statistics(self):
        """Print database statistics."""
        print("\n=== Database Statistics ===")

        # Count authors
        self.cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = self.cursor.fetchone()[0]
        print(f"  Authors: {author_count}")

        # Count works
        self.cursor.execute("SELECT COUNT(*) FROM works")
        work_count = self.cursor.fetchone()[0]
        print(f"  Works: {work_count}")

        # Count books
        self.cursor.execute("SELECT COUNT(*) FROM books")
        book_count = self.cursor.fetchone()[0]
        print(f"  Books: {book_count}")

        # Count lines
        self.cursor.execute("SELECT COUNT(*) FROM text_lines")
        line_count = self.cursor.fetchone()[0]
        print(f"  Total lines: {line_count}")

        # Count translation segments
        self.cursor.execute("SELECT COUNT(*) FROM translation_segments")
        translation_count = self.cursor.fetchone()[0]
        print(f"  Translation segments: {translation_count}")

        # Count words
        self.cursor.execute("SELECT COUNT(*) FROM words")
        word_count = self.cursor.fetchone()[0]
        print(f"  Total words: {word_count}")


if __name__ == '__main__':
    creator = PersianDatabaseCreator()
    creator.create_database()
