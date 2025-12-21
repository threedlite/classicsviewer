#!/usr/bin/env python3
"""
Generate line-by-line interlinear translation for Latin works

Uses the Latin dictionary lookup implementation from latin_dictionary_lookup.py.
Modeled after generate_interlinear.py for Greek but adapted for Latin orthography.

Output formats:
1. Plain text format (.interlinear.txt)
2. TEI XML format (.perseus-eng99.xml)
"""

import sqlite3
import re
from pathlib import Path
from typing import List, Dict
import html
from functools import lru_cache
import time

# Import the Latin dictionary lookup
try:
    from .latin_dictionary_lookup import LatinRepository, DictionaryEntry, extract_gloss
except ImportError:
    # Fallback for direct execution (testing)
    from latin_dictionary_lookup import LatinRepository, DictionaryEntry, extract_gloss

# Database path - will be set when called from build script
DB_PATH = None


class LatinInterlinearGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.repo = LatinRepository(db_path)
        # Performance tracking
        self.lookup_count = 0
        self.total_db_time = 0.0

    def __enter__(self):
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        if self.repo and self.repo.conn:
            self.repo.conn.close()

    def get_latin_lines(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Extract Latin text lines from database"""
        start_time = time.time()
        cursor = self.conn.cursor()
        query = """
        SELECT line_number, line_text
        FROM text_lines
        WHERE book_id = ? AND line_number BETWEEN ? AND ?
        ORDER BY line_number
        """
        cursor.execute(query, (book_id, start_line, end_line))

        lines = []
        for row in cursor.fetchall():
            lines.append({
                'line_number': row['line_number'],
                'text_content': row['line_text']
            })

        query_time = time.time() - start_time
        if query_time > 0.1:  # Log queries slower than 100ms
            print(f"  [PERF] text_lines query for {book_id}: {query_time:.3f}s")

        return lines

    def tokenize_latin(self, text: str) -> List[str]:
        """
        Simple Latin tokenization - split on whitespace and remove punctuation.

        Latin is simpler than Greek - no breathing marks or complex diacritics.
        Just handle standard punctuation and enclitic markers.
        """
        # Remove common punctuation but keep Latin text
        text = re.sub(r'[,;.?!—\[\]():\'\"""«»]', ' ', text)
        tokens = text.split()
        return [t.strip() for t in tokens if t.strip()]

    def extract_gloss_from_entry(self, entry: DictionaryEntry) -> str:
        """Extract a simple English gloss from a DictionaryEntry."""
        return extract_gloss(entry)

    @lru_cache(maxsize=36000)
    def _cached_lookup_word(self, word: str) -> tuple:
        """
        Cache word lookups - returns (gloss, lemma, morph) tuple.

        LRU cache means common words like et, in, ad, etc.
        are only looked up once and then retrieved from cache instantly.

        Dictionary entries are sorted by frequency during database creation,
        so the first result is the most common meaning.
        """
        # Database lookup
        start_time = time.time()
        entries = self.repo.get_all_dictionary_entries(word, "latin")

        # If no results and word starts with uppercase, try lowercase
        if (not entries or len(entries) == 0) and word and word[0].isupper():
            entries = self.repo.get_all_dictionary_entries(word.lower(), "latin")

        db_time = time.time() - start_time

        self.lookup_count += 1
        self.total_db_time += db_time

        # Log cache stats every 1000 lookups
        if self.lookup_count % 1000 == 0:
            cache_info = self._cached_lookup_word.cache_info()
            hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses) * 100 if (cache_info.hits + cache_info.misses) > 0 else 0
            avg_db_time = (self.total_db_time / self.lookup_count) * 1000  # Convert to ms
            print(f"  [PERF] Cache: {hit_rate:.1f}% hit rate, {cache_info.currsize}/30000 entries, avg DB time: {avg_db_time:.2f}ms")

        # Process entries to extract gloss, lemma, morph
        gloss = None
        lemma = None
        morph = None

        if entries and len(entries) > 0:
            # Get morph info from database
            preferred_morph = self.repo.get_morph_info(word)

            # Find best entry with a good definition
            for entry in entries:
                extracted_gloss = self.extract_gloss_from_entry(entry)
                if extracted_gloss and extracted_gloss != "???" and len(extracted_gloss) > 2:
                    lemma = entry.lemma
                    morph = entry.morph_info
                    gloss = extracted_gloss
                    break

            # If still no good gloss, use first entry's lemma at least
            if not gloss and entries:
                first_entry = entries[0]
                lemma = first_entry.lemma
                morph = first_entry.morph_info
                gloss = self.extract_gloss_from_entry(first_entry)

            # Use preferred morphology if we didn't get it from entries
            if not morph:
                morph = preferred_morph

        # Fallback if no gloss found
        if not gloss or gloss == "???":
            gloss = "???"

        return (gloss, lemma, morph)

    def lookup_word(self, word: str, book_id: str, line_number: int, position: int) -> Dict:
        """
        Lookup word using cached dictionary lookup.
        Returns a dict with latin, position, gloss, lemma, morph
        """
        # Get cached result (gloss, lemma, morph) - instant for repeated words!
        gloss, lemma, morph = self._cached_lookup_word(word)

        return {
            'latin': word,
            'position': position,
            'gloss': gloss,
            'lemma': lemma,
            'morph': morph
        }

    def generate_interlinear(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Main function to generate interlinear translation"""

        # Step 1: Get Latin text
        t0 = time.time()
        latin_lines = self.get_latin_lines(book_id, start_line, end_line)
        text_fetch_time = time.time() - t0

        if not latin_lines:
            print(f"  WARNING: No Latin text found for {book_id} lines {start_line}-{end_line}")
            return []

        # Step 2: Process each line
        t1 = time.time()
        lines_data = []

        for line in latin_lines:
            line_num = line['line_number']
            text = line['text_content']

            # Tokenize
            tokens = self.tokenize_latin(text)

            # Lookup each word
            words = []
            for pos, token in enumerate(tokens, 1):
                word_data = self.lookup_word(token, book_id, line_num, pos)
                words.append(word_data)

            # Create word-by-word gloss
            word_gloss = ' '.join([w['gloss'] if w['gloss'] else '???' for w in words])

            lines_data.append({
                'line_number': line_num,
                'latin_text': text,
                'words': words,
                'word_gloss': word_gloss
            })

        processing_time = time.time() - t1
        total_time = time.time() - t0

        return lines_data


def generate_latin_interlinear_translations(db_path: Path, output_dir: Path, work_ids=None):
    """
    Generate interlinear translations for Latin works

    Args:
        db_path: Path to the Perseus database
        output_dir: Directory where XML files will be written
        work_ids: List of PHI work IDs to process (e.g., ['phi0690.phi003']).
                  If None, defaults to Virgil's Aeneid.
    """
    global DB_PATH
    DB_PATH = db_path

    if work_ids is None:
        # Default to Virgil's Aeneid
        work_ids = ['phi0690.phi003']
    elif isinstance(work_ids, str):
        work_ids = [work_ids]

    output_dir.mkdir(parents=True, exist_ok=True)

    total_works = len(work_ids)
    for work_idx, work_id in enumerate(work_ids, 1):
        work_percent = (work_idx - 1) / total_works * 100
        print(f"\n{'=' * 80}")
        print(f"LATIN WORK {work_idx}/{total_works} - {work_percent:.1f}% complete: {work_id}")
        print(f"{'=' * 80}")
        _generate_latin_work(work_id, output_dir)
        work_percent = work_idx / total_works * 100
        print(f"\nWork {work_id} done ({work_percent:.1f}% of all works)")


def _write_xml_header(f, work_id: str, work_title: str, author_name: str):
    """Write XML header and TEI metadata (streaming helper)"""
    work_title_escaped = html.escape(work_title)
    author_name_escaped = html.escape(author_name)
    work_id_escaped = html.escape(work_id)

    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<?xml-model href="http://www.stoa.org/epidoc/schema/8.19/tei-epidoc.rng"\n')
    f.write('  schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
    f.write('<TEI xmlns="http://www.tei-c.org/ns/1.0">\n')
    f.write('    <teiHeader>\n')
    f.write('        <fileDesc>\n')
    f.write('            <titleStmt>\n')
    f.write(f'                <title>{work_title_escaped} - Interlinear Translation</title>\n')
    f.write(f'                <author>{author_name_escaped}</author>\n')
    f.write('                <editor role="translator">Interlinear (Beta, AI-generated from app dictionary)</editor>\n')
    f.write('                <sponsor>Derived from Whitaker\'s Words, Perseus</sponsor>\n')
    f.write('                <principal></principal>\n')
    f.write('                <respStmt>\n')
    f.write('                    <resp>AI-generated interlinear translation</resp>\n')
    f.write('                    <name>Claude Code</name>\n')
    f.write('                </respStmt>\n')
    f.write('            </titleStmt>\n')
    f.write('            <extent>AI-generated interlinear</extent>\n')
    f.write('            <publicationStmt>\n')
    f.write('                <publisher></publisher>\n')
    f.write('                <pubPlace></pubPlace>\n')
    f.write('                <authority></authority>\n')
    f.write('            </publicationStmt>\n')
    f.write('            <notesStmt>\n')
    f.write('                <note anchored="true">AI-generated word-by-word interlinear translation derived from Whitaker\'s Words dictionary.</note>\n')
    f.write('            </notesStmt>\n')
    f.write('            <sourceDesc>\n')
    f.write('                <biblStruct>\n')
    f.write('                    <monogr>\n')
    f.write(f'                        <author>{author_name_escaped}</author>\n')
    f.write(f'                        <title>{work_title_escaped}</title>\n')
    f.write('                        <title type="sub">Interlinear Translation</title>\n')
    f.write('                        <editor role="translator">AI-generated</editor>\n')
    f.write('                        <imprint>\n')
    f.write('                            <date>2025</date>\n')
    f.write('                        </imprint>\n')
    f.write('                    </monogr>\n')
    f.write('                </biblStruct>\n')
    f.write('            </sourceDesc>\n')
    f.write('        </fileDesc>\n')
    f.write('        <encodingDesc>\n')
    f.write('            <refsDecl n="CTS">\n')
    f.write('                <cRefPattern n="line" matchPattern="(\\w+).(\\w+)"\n')
    f.write('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\']//tei:l[@n=\'$2\'])">\n')
    f.write('                    <p>This pointer pattern extracts book and line</p>\n')
    f.write('                </cRefPattern>\n')
    f.write('                <cRefPattern n="book" matchPattern="(\\w+)"\n')
    f.write('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\'])">\n')
    f.write('                    <p>This pointer pattern extracts book</p>\n')
    f.write('                </cRefPattern>\n')
    f.write('            </refsDecl>\n')
    f.write('            <refsDecl>\n')
    f.write('                <refState unit="book" delim="."/>\n')
    f.write('                <refState unit="line"/>\n')
    f.write('            </refsDecl>\n')
    f.write('        </encodingDesc>\n')
    f.write('        <profileDesc>\n')
    f.write('            <langUsage>\n')
    f.write('                <language ident="eng">English</language>\n')
    f.write('                <language ident="lat">Latin</language>\n')
    f.write('            </langUsage>\n')
    f.write('        </profileDesc>\n')
    f.write('        <revisionDesc>\n')
    f.write('            <change when="20251201" who="Claude Code">Generated Latin interlinear translation.</change>\n')
    f.write('        </revisionDesc>\n')
    f.write('    </teiHeader>\n')
    f.write('    <text xml:lang="eng">\n')
    f.write('        <body>\n')
    f.write(f'            <div type="translation" n="urn:cts:latinLit:{work_id_escaped}.perseus-eng99" xml:lang="eng">\n')


def _write_book_to_xml(f, book_num: int, book_results: List[Dict]):
    """Write a single book to XML file (streaming helper)"""
    f.write(f'                <div type="textpart" subtype="Book" n="{book_num}">\n')

    for line_data in book_results:
        line_num = line_data['line_number']

        # Build interlinear text efficiently using list comprehension
        word_tables = []
        for w in line_data['words']:
            latin = w['latin'] if w['latin'] else '???'
            gloss = w['gloss'] if w['gloss'] else '???'
            lemma = w['lemma'] if w['lemma'] else '?'
            morph = w['morph'] if w['morph'] else ''

            # CRITICAL: Escape XML special characters to prevent malformed XML
            # Latin texts may contain <word> for editorial additions which break XML parsing
            latin = html.escape(latin)
            gloss = html.escape(gloss)
            lemma = html.escape(lemma)
            morph = html.escape(morph)

            lemma_morph = f'{lemma} {morph}' if morph else lemma
            table = f'| {latin} |\n| **{gloss}** |\n| {lemma_morph} |'
            word_tables.append(table)

        interlinear_text = '  '.join(word_tables)
        f.write(f'                    <l n="{line_num}">{interlinear_text}</l>\n')

    f.write('                </div>\n')


def _write_xml_footer(f):
    """Write XML footer (streaming helper)"""
    f.write('            </div>\n')
    f.write('        </body>\n')
    f.write('    </text>\n')
    f.write('</TEI>\n')


def _write_book_to_txt(f, book_num: int, book_results: List[Dict]):
    """Write a single book to text file (streaming helper)"""
    f.write(f"\n{'=' * 80}\n")
    f.write(f"BOOK {book_num}\n")
    f.write(f"{'=' * 80}\n\n")

    for line_data in book_results:
        line_num = line_data['line_number']
        latin_words = [w['latin'] for w in line_data['words']]
        glosses = [w['gloss'] for w in line_data['words']]

        f.write(f"{line_num}. {' | '.join(latin_words)}\n")
        f.write(f"{' | '.join(glosses)}\n\n")


def _generate_latin_work(work_id: str, output_dir: Path):
    """
    Generate interlinear translation for a single Latin work using PHI ID.

    Uses STREAMING architecture: processes and writes one book at a time
    to minimize memory usage and ensure all files are written correctly.
    """

    print("=" * 80)
    print(f"LATIN INTERLINEAR TRANSLATION GENERATOR")
    print("=" * 80)
    print(f"Work ID: {work_id}")
    print(f"Database: {DB_PATH}")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"\n  FATAL ERROR: Database not found at {DB_PATH}")
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # Get all books for this work
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    book_pattern = f"{work_id}.%"
    cursor.execute("SELECT DISTINCT book_id FROM text_lines WHERE book_id LIKE ? ORDER BY book_id", (book_pattern,))
    book_ids = [row[0] for row in cursor.fetchall()]

    # Get work metadata for XML
    cursor.execute("""
        SELECT DISTINCT w.title_english, a.name
        FROM works w
        JOIN authors a ON w.author_id = a.id
        WHERE w.id = ?
    """, (work_id,))
    work_metadata = cursor.fetchone()
    conn.close()

    if not book_ids:
        print(f"\n  WARNING: No books found for work ID {work_id}")
        print(f"  Skipping this work.")
        return

    if work_metadata:
        work_title, author_name = work_metadata
    else:
        work_title = work_id
        author_name = "Unknown"

    print(f"\nFound {len(book_ids)} books to process")
    print(f"Work: {work_title} by {author_name}")
    print("=" * 80)

    # Generate output filenames
    txt_filename = f"{work_id}.interlinear.txt"
    xml_filename = f"{work_id}.perseus-eng99.xml"
    output_file = output_dir / txt_filename
    xml_output_file = output_dir / xml_filename

    total_lines = 0

    try:
        # Open BOTH output files at the start - streaming architecture
        with open(output_file, 'w', encoding='utf-8') as txt_file, \
             open(xml_output_file, 'w', encoding='utf-8') as xml_file, \
             LatinInterlinearGenerator(str(DB_PATH)) as generator:

            # Write XML header once at start
            _write_xml_header(xml_file, work_id, work_title, author_name)

            # Process each book ONE AT A TIME - memory efficient streaming
            for idx, book_id in enumerate(book_ids, 1):
                book_num = int(book_id.split('.')[-1])
                percent_complete = (idx - 1) / len(book_ids) * 100

                # Get line range for this book
                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT MIN(line_number), MAX(line_number) FROM text_lines WHERE book_id = ?", (book_id,))
                start_line, end_line = cursor.fetchone()
                conn.close()

                # Generate interlinear for THIS book only
                book_results = generator.generate_interlinear(book_id, start_line, end_line)

                # IMMEDIATELY write to both files - streaming!
                _write_book_to_txt(txt_file, book_num, book_results)
                _write_book_to_xml(xml_file, book_num, book_results)

                # Track progress
                total_lines += len(book_results)

            # Write XML footer once at end
            _write_xml_footer(xml_file)

        # Files are closed and flushed - guaranteed written to disk
        print(f"\n\n{'=' * 80}")
        print("COMPLETE!")
        print("=" * 80)
        print(f"Processed {len(book_ids)} books, {total_lines} lines")
        print(f"\nText output: {output_file}")
        print(f"XML output: {xml_output_file}")
        print("=" * 80)

    except Exception as e:
        # Clean up partial files on error
        if output_file.exists():
            output_file.unlink()
        if xml_output_file.exists():
            xml_output_file.unlink()
        print(f"\n{'=' * 80}")
        print(f"  FAILED: Work {work_id}")
        print(f"{'=' * 80}")
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 80}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python generate_latin_interlinear.py <database_path> <output_dir> [work_id]")
        print("Example: python generate_latin_interlinear.py ../../perseus_texts_sample.db ../../interlinear_output phi0690.phi003")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    work_ids = [sys.argv[3]] if len(sys.argv) > 3 else None

    generate_latin_interlinear_translations(db_path, output_dir, work_ids)
