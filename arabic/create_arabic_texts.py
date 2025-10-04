#!/usr/bin/env python3
"""
Create Arabic Texts Database for ClassicsViewer

Parses Mu'allaqa of Imru' al-Qays from Wikisource HTML and creates:
- arabic_texts.db: SQLite database with verses and words
- arabic_texts.db.zip: Compressed database for app deployment

Based on Hebrew texts creation (hebrewOT/process_hebrew_complete.py)
"""

import sqlite3
import re
import zipfile
from pathlib import Path
from html.parser import HTMLParser
from collections import defaultdict

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data-sources"
HTML_FILE = DATA_DIR / "muallaqat_imru_al_qays.html"
TRANSLATION_FILE = DATA_DIR / "muallaqat_translation_johnson.html"

# Output
OUTPUT_DB = SCRIPT_DIR / "arabic_texts.db"
OUTPUT_ZIP = SCRIPT_DIR / "arabic_texts.db.zip"

# Database schema
SCHEMA = """
-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    name_alt TEXT,
    language TEXT NOT NULL,
    has_translations INTEGER DEFAULT 0
);

-- Works table
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

-- Books table (for multi-book works)
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

-- Text lines table (matching sample DB schema)
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

-- Words table (matching sample DB schema)
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word TEXT NOT NULL,
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    word_position INTEGER NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Translation segments table
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

-- Indexes (matching sample DB)
CREATE INDEX IF NOT EXISTS idx_text_lines_book ON text_lines(book_id);
CREATE INDEX IF NOT EXISTS idx_text_lines_sequence ON text_lines(book_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_words_word ON words(word);
CREATE INDEX IF NOT EXISTS idx_words_book_line_seq ON words(book_id, line_number, sequence_number);
CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id);
CREATE INDEX IF NOT EXISTS idx_books_work ON books(work_id);
CREATE INDEX IF NOT EXISTS idx_translation_segments_book ON translation_segments(book_id);
CREATE INDEX IF NOT EXISTS idx_translation_segments_lines ON translation_segments(book_id, start_line);
"""


class MuallaqaHTMLParser(HTMLParser):
    """Parse Wikisource HTML to extract verses"""

    def __init__(self):
        super().__init__()
        self.verses = []
        self.in_abyat_wrapper = False
        self.in_sdr = False
        self.in_ajz = False
        self.current_sdr = ""
        self.current_ajz = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "div" and attrs_dict.get("class") == "abyat-wrapper":
            self.in_abyat_wrapper = True
        elif tag == "div" and self.in_abyat_wrapper:
            if attrs_dict.get("class") == "abyat-sdr":
                self.in_sdr = True
                self.current_sdr = ""
            elif attrs_dict.get("class") == "abyat-ajz":
                self.in_ajz = True
                self.current_ajz = ""

    def handle_endtag(self, tag):
        if tag == "div":
            if self.in_sdr:
                self.in_sdr = False
            elif self.in_ajz:
                self.in_ajz = False
                # Complete verse (sdr + ajz)
                full_verse = f"{self.current_sdr} {self.current_ajz}".strip()
                if full_verse:
                    self.verses.append(full_verse)
                self.current_sdr = ""
                self.current_ajz = ""
            elif self.in_abyat_wrapper and not self.in_sdr and not self.in_ajz:
                self.in_abyat_wrapper = False

    def handle_data(self, data):
        if self.in_sdr:
            self.current_sdr += data
        elif self.in_ajz:
            self.current_ajz += data


class TranslationHTMLParser(HTMLParser):
    """Parse Wikisource translation HTML to extract English lines"""

    def __init__(self):
        super().__init__()
        self.lines = []
        self.in_poem = False
        self.in_line = False
        self.current_line = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "div" and "ws-poem" in attrs_dict.get("class", ""):
            self.in_poem = True
        elif tag == "span" and self.in_poem and "ws-poem-line" in attrs_dict.get("class", ""):
            self.in_line = True
            self.current_line = ""

    def handle_endtag(self, tag):
        if tag == "span" and self.in_line:
            self.in_line = False
            if self.current_line.strip():
                self.lines.append(self.current_line.strip())
        elif tag == "div" and self.in_poem:
            self.in_poem = False

    def handle_data(self, data):
        if self.in_line:
            self.current_line += data


def normalize_arabic(text):
    """
    Apply normalization rules to Arabic text
    Based on custom_dictionary/normalization_rules_arabic.csv
    """
    if not text:
        return ""

    # Remove tashkeel (diacritics/vocalization)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)

    # Remove tatweel/kashida (elongation character)
    text = re.sub(r'\u0640', '', text)

    # Normalize alif variants to plain alif
    text = re.sub(r'[أإآ]', 'ا', text)

    # Normalize hamza on waw to plain waw
    text = text.replace('ؤ', 'و')

    # Normalize hamza on ya to plain ya
    text = text.replace('ئ', 'ي')

    # Normalize alif maqsura to ya
    text = text.replace('ى', 'ي')

    # Normalize taa marbuta to haa
    text = text.replace('ة', 'ه')

    return text


def tokenize_arabic(text):
    """
    Tokenize Arabic text into words
    Splits on whitespace and common punctuation
    """
    # Split on whitespace and punctuation
    words = re.findall(r'[\u0600-\u06FF]+', text)
    return words


def parse_muallaqat_html():
    """Parse HTML and extract verses"""
    print("Parsing Mu'allaqa HTML...")

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    parser = MuallaqaHTMLParser()
    parser.feed(html_content)

    print(f"  Extracted {len(parser.verses)} verses")

    # Show first verse as sample
    if parser.verses:
        print(f"  First verse: {parser.verses[0][:80]}...")

    return parser.verses


def parse_translation_html():
    """Parse translation HTML and extract English lines"""
    print("Parsing translation HTML...")

    with open(TRANSLATION_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    parser = TranslationHTMLParser()
    parser.feed(html_content)

    print(f"  Extracted {len(parser.lines)} translation lines")

    # Show first line as sample
    if parser.lines:
        print(f"  First line: {parser.lines[0][:80]}...")

    return parser.lines


def create_database(verses, translation_lines):
    """Create SQLite database from verses and translation"""
    print(f"\nCreating database: {OUTPUT_DB}")

    # Remove existing database
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    conn = sqlite3.connect(OUTPUT_DB)
    cursor = conn.cursor()

    # Create schema
    print("  Creating schema...")
    cursor.executescript(SCHEMA)

    # Insert author
    print("  Inserting author...")
    cursor.execute("""
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    """, ("imru_al_qays", "امرؤ القيس / Imru' al-Qays", "Imru' al-Qays", "arabic", 1))

    # Insert work
    print("  Inserting work...")
    cursor.execute("""
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "muallaqat",
        "imru_al_qays",
        "معلقة",
        "Mu'allaqa",
        "The Hanging Ode",
        "poetry",
        "One of the seven Mu'allaqat, pre-Islamic Arabic odes"
    ))

    # Insert book (single book for the poem)
    print("  Inserting book...")
    cursor.execute("""
        INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "muallaqat_1",
        "muallaqat",
        1,
        "Mu'allaqa",
        1,
        len(verses),
        len(verses)
    ))

    # Insert text lines and words
    print(f"  Inserting {len(verses)} verses with words...")

    for line_num, verse_text in enumerate(verses, 1):
        # Insert text line (matching sample DB schema)
        # sequence_number = line_number for simple linear text
        cursor.execute("""
            INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, line_xml, speaker)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("muallaqat_1", line_num, line_num, verse_text, None, None))

        # Tokenize and insert words
        words = tokenize_arabic(verse_text)
        for word_pos, word in enumerate(words, 1):
            cursor.execute("""
                INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                VALUES (?, ?, ?, ?, ?)
            """, (word, "muallaqat_1", line_num, line_num, word_pos))

        if line_num % 10 == 0:
            print(f"    Processed {line_num}/{len(verses)} verses...")

    # Insert translation segments
    print(f"  Inserting {len(translation_lines)} translation lines...")
    for line_num, trans_text in enumerate(translation_lines, 1):
        cursor.execute("""
            INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("muallaqat_1", line_num, line_num, line_num, trans_text, "F. E. Johnson", None))

    # Commit and close
    conn.commit()

    # Get stats
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    line_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM words")
    word_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT word) FROM words")
    unique_words = cursor.fetchone()[0]

    conn.close()

    print(f"\n✅ Database created:")
    print(f"   Lines: {line_count}")
    print(f"   Total words: {word_count}")
    print(f"   Unique words: {unique_words}")

    return line_count, word_count, unique_words


def create_zip():
    """Create compressed database for deployment"""
    print(f"\nCompressing database to {OUTPUT_ZIP}...")

    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(OUTPUT_DB, OUTPUT_DB.name)

    # Get file sizes
    db_size_mb = OUTPUT_DB.stat().st_size / (1024 * 1024)
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)

    print(f"✅ Compressed:")
    print(f"   Database: {db_size_mb:.2f} MB")
    print(f"   ZIP: {zip_size_mb:.2f} MB")
    print(f"   Compression: {(1 - zip_size_mb/db_size_mb)*100:.1f}%")


def main():
    """Main execution"""
    print("="*60)
    print("Arabic Texts Database Generator for ClassicsViewer")
    print("="*60)
    print()

    # Parse Arabic HTML
    verses = parse_muallaqat_html()

    if not verses:
        print("ERROR: No verses extracted from HTML")
        return

    # Parse translation HTML
    translation_lines = parse_translation_html()

    if not translation_lines:
        print("ERROR: No translation lines extracted from HTML")
        return

    # Create database
    create_database(verses, translation_lines)

    # Create ZIP
    create_zip()

    print(f"\n{'='*60}")
    print("✅ Arabic texts database created successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
