#!/usr/bin/env python3
"""
Sanskrit Interlinear and TEI XML Generation

Generates word-by-word interlinear translations for Sanskrit texts in two formats:
1. Plain text format (.interlinear.txt) - matching Greek interlinear format
2. TEI XML format (.dcs-eng99.xml) - matching Greek TEI XML format

For DCS texts: Uses pre-identified lemmas from CoNLL-U data
For custom texts (BG, RV): Falls back to morphology lookup

Text format: Line N. word1 | word2 | word3
             gloss1 | gloss2 | gloss3

XML format:  <l n="N">| word1 |
             | **gloss1** |
             | lemma1 ~ POS deprel head sent_pos |  | word2 |
             | **gloss2** |
             | lemma2 ~ POS deprel head sent_pos | ...
             </l>

Treebank data (HEAD, DEPREL) is included for works in the Vedic Treebank subset.
"""

import sqlite3
import time
import re
import html
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache
from sanskrit_dictionary_lookup import SanskritRepository, extract_gloss

# Try to import treebank loader (optional dependency)
try:
    from sanskrit_treebank_loader import SanskritTreebankLoader, TREEBANK_WORKS
    TREEBANK_AVAILABLE = True
except ImportError:
    TREEBANK_AVAILABLE = False
    TREEBANK_WORKS = set()


@dataclass
class WordData:
    """Represents a word with its metadata."""
    word: str
    word_position: int
    lemma: Optional[str] = None
    pos_tag: Optional[str] = None
    # Treebank fields (Vedic Treebank subset only)
    head: Optional[int] = None          # Head word position (0=root)
    deprel: Optional[str] = None        # Dependency relation
    sentence_position: Optional[int] = None  # Position within sentence


def sanitize_xml_text(text: str) -> str:
    """
    Sanitize text for safe XML inclusion.

    Removes control characters (ASCII 0-31 except tab, newline, CR)
    and escapes XML special characters (&, <, >, ", ').

    Args:
        text: Raw text string

    Returns:
        XML-safe string
    """
    if not text:
        return ""

    # Remove control characters (0x00-0x1F except 0x09 tab, 0x0A newline, 0x0D CR)
    # Also remove 0x7F (DEL)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Escape XML special characters
    text = html.escape(text, quote=True)

    return text


class SanskritInterlinearGenerator:
    """
    Generates interlinear translations for Sanskrit texts.

    Uses database word segmentation and DCS dictionary lookups.
    Generates both plain text and TEI XML formats.
    Includes treebank data (HEAD, DEPREL) for Vedic Treebank works.
    """

    # Mapping from database work_id patterns to DCS work names
    # (database IDs use lowercase ASCII, DCS uses proper Sanskrit with diacritics)
    WORK_ID_TO_DCS = {
        'aitareyopanisad': 'Aitareyopaniṣad',
        'aitareyopanishad': 'Aitareyopaniṣad',
        'chandogyopanisad': 'Chāndogyopaniṣad',
        'chandogyopanishad': 'Chāndogyopaniṣad',
        'mundakopanisad': 'Muṇḍakopaniṣad',
        'mundakopanishad': 'Muṇḍakopaniṣad',
        'svetasvataropanisad': 'Śvetāśvataropaniṣad',
        'svetasvataropanishad': 'Śvetāśvataropaniṣad',
        'rgveda': 'Ṛgveda',
        'rigveda': 'Ṛgveda',
        'atharvaveda': 'Atharvaveda (Śaunaka)',
        'manusmrti': 'Manusmṛti',
        'manusmriti': 'Manusmṛti',
        'gautamadharmasutra': 'Gautamadharmasūtra',
        'hiranyakesigrhyasutra': 'Hiraṇyakeśigṛhyasūtra',
        'khadiragrhyasutra': 'Khādiragṛhyasūtra',
        'vaitanasutra': 'Vaitānasūtra',
        'varahagrhyasutra': 'Vārāhagṛhyasūtra',
        'apastambagrhyasutra': 'Āpastambagṛhyasūtra',
        'asvalayanasrautasutra': 'Āśvālāyanaśrautasūtra',
        'sankhayanaranyaka': 'Śāṅkhāyanāraṇyaka',
        'nyayabindu': 'Nyāyabindu',
    }

    def __init__(self, db_path: str, conllu_dir: str = None):
        """
        Initialize generator with database connection and optional treebank.

        Args:
            db_path: Path to Sanskrit texts database
            conllu_dir: Path to DCS CoNLL-U files directory (optional)
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.repo = SanskritRepository(db_path)

        # Initialize treebank loader if available and path provided
        self.treebank = None
        self.treebank_work_cache = {}  # Cache for work_id -> DCS work name mapping

        if TREEBANK_AVAILABLE and conllu_dir:
            try:
                self.treebank = SanskritTreebankLoader(conllu_dir)
                if self.treebank.available_works:
                    print(f"  Treebank loaded: {len(self.treebank.available_works)} works with tree data")
            except Exception as e:
                print(f"  Warning: Could not load treebank: {e}")
                self.treebank = None
        elif TREEBANK_AVAILABLE and not conllu_dir:
            # Try default path
            default_path = Path(__file__).parent.parent / "data-sources" / "sanskrit" / "dcs" / "data" / "conllu" / "files"
            if default_path.exists():
                try:
                    self.treebank = SanskritTreebankLoader(str(default_path))
                    if self.treebank.available_works:
                        print(f"  Treebank loaded: {len(self.treebank.available_works)} works with tree data")
                except Exception as e:
                    print(f"  Warning: Could not load treebank: {e}")

        # Statistics
        self.stats = {
            'lines_processed': 0,
            'words_total': 0,
            'words_found': 0,
            'words_missing': 0,
            'cache_hits': 0,
            'treebank_words': 0,
        }

    def _get_dcs_work_name(self, work_id: str) -> Optional[str]:
        """
        Map database work_id to DCS work name.

        Args:
            work_id: Database work identifier (e.g., "aitareyopanisad")

        Returns:
            DCS work name with proper diacritics, or None if not mapped
        """
        if work_id in self.treebank_work_cache:
            return self.treebank_work_cache[work_id]

        # Try direct mapping
        work_lower = work_id.lower().replace('-', '').replace('_', '')
        dcs_name = self.WORK_ID_TO_DCS.get(work_lower)

        if dcs_name and self.treebank and self.treebank.has_coverage(dcs_name):
            self.treebank_work_cache[work_id] = dcs_name
            return dcs_name

        self.treebank_work_cache[work_id] = None
        return None

    def get_work_info(self, work_id: str) -> Dict:
        """Get work metadata from database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT w.id, w.title, w.title_english, a.name as author_name
            FROM works w
            JOIN authors a ON w.author_id = a.id
            WHERE w.id = ?
        """, (work_id,))

        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Work not found: {work_id}")

        return {
            'work_id': row['id'],
            'title': row['title'],
            'title_english': row['title_english'],
            'author': row['author_name']
        }

    def get_books_for_work(self, work_id: str) -> List[str]:
        """Get all book IDs for a work."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM books
            WHERE work_id = ?
            ORDER BY id
        """, (work_id,))

        return [row['id'] for row in cursor.fetchall()]

    def get_line_words(self, book_id: str, line_number: int) -> List[WordData]:
        """
        Get segmented words for a specific line, including treebank data if stored in database.

        Args:
            book_id: Book identifier (e.g., "aitareyopanisad.1")
            line_number: Line number

        Returns:
            List of WordData objects with word forms and tree data
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT word, word_position, head, deprel, pos_tag, sentence_position
            FROM words
            WHERE book_id = ? AND line_number = ?
            ORDER BY word_position
        """, (book_id, line_number))

        words = []
        for row in cursor.fetchall():
            word = row['word']
            # Look up lemma via morphology (database or CSV, handled by SanskritRepository)
            lemma = self.repo.get_lemma_for_word(word)

            # Get treebank data from database (may be NULL for non-Vedic works)
            head = row['head']
            deprel = row['deprel']
            pos_tag = row['pos_tag']
            sentence_position = row['sentence_position']

            words.append(WordData(
                word=word,
                word_position=row['word_position'],
                lemma=lemma,
                pos_tag=pos_tag,
                head=head,
                deprel=deprel,
                sentence_position=sentence_position
            ))

            # Track treebank statistics
            if head is not None or deprel is not None:
                self.stats['treebank_words'] += 1

        return words

    def _enhance_with_treebank(self, words: List[WordData], dcs_work: str,
                                chapter_id: str, sentence_id: str):
        """
        Enhance word list with treebank data by matching words.

        Uses IAST transliteration matching between database words and treebank.
        Modifies words list in-place.

        Args:
            words: List of WordData to enhance
            dcs_work: DCS work name (e.g., "Ṛgveda")
            chapter_id: DCS chapter ID
            sentence_id: DCS sentence ID
        """
        try:
            from indic_transliteration import sanscript
        except ImportError:
            return  # Can't match without transliteration

        tb_words = self.treebank.get_sentence(dcs_work, chapter_id, sentence_id)
        if not tb_words:
            return

        # Build mapping of IAST forms to treebank data
        tb_by_form = {}
        for tb_word in tb_words:
            form_lower = tb_word.form.lower()
            if form_lower not in tb_by_form:
                tb_by_form[form_lower] = []
            tb_by_form[form_lower].append(tb_word)

        # Match database words to treebank words
        tb_used = set()
        for word_data in words:
            # Convert Devanagari to IAST for matching
            try:
                word_iast = sanscript.transliterate(
                    word_data.word, sanscript.DEVANAGARI, sanscript.IAST
                ).lower()
            except:
                continue

            # Find matching treebank word
            if word_iast in tb_by_form:
                for tb_word in tb_by_form[word_iast]:
                    tb_key = (tb_word.sentence_id, tb_word.sentence_position)
                    if tb_key not in tb_used:
                        word_data.pos_tag = tb_word.upos
                        word_data.head = tb_word.head
                        word_data.deprel = tb_word.deprel
                        word_data.sentence_position = tb_word.sentence_position
                        tb_used.add(tb_key)
                        self.stats['treebank_words'] += 1
                        break

    @lru_cache(maxsize=50000)
    def _cached_dictionary_lookup(self, word: str, lemma: str) -> tuple:
        """
        Cached dictionary lookup using LRU cache.

        Uses LRU cache to avoid repeated lookups of common words.
        Returns tuple of (gloss, found_flag) for statistics tracking.

        Args:
            word: Word form
            lemma: Lemma (or empty string if not available)

        Returns:
            Tuple of (gloss_string, was_found_boolean)
        """
        # Normalize lemma (None → empty string for cache key)
        lemma_normalized = lemma if lemma else None

        # Lookup in dictionary
        entry = self.repo.lookup_best_match(word, lemma_normalized)

        if entry:
            gloss = extract_gloss(entry.definition, max_length=40)
            return (gloss, True)
        else:
            return ("?", False)

    def lookup_word_gloss(self, word_data: WordData) -> str:
        """
        Look up gloss for a word using LRU cache.

        Args:
            word_data: Word to look up

        Returns:
            Concise gloss or "?" if not found
        """
        word = word_data.word
        lemma = word_data.lemma if word_data.lemma else ""

        # Use cached lookup
        gloss, was_found = self._cached_dictionary_lookup(word, lemma)

        # Update statistics
        self.stats['words_total'] += 1
        if was_found:
            self.stats['words_found'] += 1
            # Cache hits tracked by LRU mechanism
        else:
            self.stats['words_missing'] += 1

        return gloss

    def generate_line_interlinear(self, book_id: str, line_number: int) -> Tuple[str, str]:
        """
        Generate interlinear for a single line.

        Args:
            book_id: Work identifier
            line_number: Line number

        Returns:
            Tuple of (words_line, glosses_line) in Greek format:
            - words_line: "word1 | word2 | word3"
            - glosses_line: "gloss1 | gloss2 | gloss3"
        """
        words = self.get_line_words(book_id, line_number)

        if not words:
            return ("", "")

        word_parts = []
        gloss_parts = []
        for word_data in words:
            gloss = self.lookup_word_gloss(word_data)  # words_total tracked inside
            word_parts.append(word_data.word)
            gloss_parts.append(gloss)

        self.stats['lines_processed'] += 1
        words_line = " | ".join(word_parts)
        glosses_line = " | ".join(gloss_parts)
        return (words_line, glosses_line)

    def generate_work_interlinear(self, work_id: str) -> Dict[str, Dict[int, Tuple[str, str]]]:
        """
        Generate interlinear for all books in a work.

        Args:
            work_id: Work identifier

        Returns:
            Dictionary mapping book_id -> {line_number -> (words_line, glosses_line)}
        """
        cursor = self.conn.cursor()

        # Get all books for this work
        cursor.execute("""
            SELECT id FROM books WHERE work_id = ? ORDER BY id
        """, (work_id,))

        books = [row['id'] for row in cursor.fetchall()]

        if not books:
            raise ValueError(f"No books found for work: {work_id}")

        # Generate interlinear for each book
        result = {}
        for book_id in books:
            result[book_id] = self._generate_book_interlinear(book_id)

        return result

    def _generate_book_interlinear(self, book_id: str) -> Dict[int, Tuple[str, str]]:
        """Generate interlinear for a single book.

        Returns:
            Dictionary mapping line_number -> (words_line, glosses_line)
        """
        cursor = self.conn.cursor()

        # Get all line numbers for this book
        cursor.execute("""
            SELECT DISTINCT line_number
            FROM text_lines
            WHERE book_id = ?
            ORDER BY line_number
        """, (book_id,))

        line_numbers = [row['line_number'] for row in cursor.fetchall()]

        # Generate interlinear for each line
        interlinear_map = {}
        for line_num in line_numbers:
            words_line, glosses_line = self.generate_line_interlinear(book_id, line_num)
            if words_line:  # Only add if non-empty
                interlinear_map[line_num] = (words_line, glosses_line)

        return interlinear_map

    def write_interlinear_file(self, work_id: str, output_path: Path):
        """
        Generate interlinear for all books in a work and write to plain text file.

        Format matches Greek interlinear EXACTLY:
        ================================================================================
        BOOK 1
        ================================================================================

        1. word1 | word2 | word3
        gloss1 | gloss2 | gloss3

        2. word1 | word2 | word3
        gloss2 | gloss2 | gloss3

        NO English interpretive translations - only word-by-word glosses

        Args:
            work_id: Work identifier
            output_path: Path to output file
        """
        work_info = self.get_work_info(work_id)

        print(f"\nGenerating interlinear for: {work_info['title_english']}")
        print(f"  Work ID: {work_id}")

        start_time = time.time()
        books_interlinear = self.generate_work_interlinear(work_id)
        elapsed = time.time() - start_time

        # Write to file in Greek-style format
        total_lines = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            for book_idx, book_id in enumerate(sorted(books_interlinear.keys())):
                # Extract book number from book_id (e.g., "aitareyopanishad.1" -> "1")
                book_num = book_id.split('.')[-1]

                # Book header (skip initial newline for first book)
                if book_idx > 0:
                    f.write("\n")
                f.write("=" * 80 + "\n")
                f.write(f"BOOK {book_num}\n")
                f.write("=" * 80 + "\n\n")

                interlinear_map = books_interlinear[book_id]
                for line_num in sorted(interlinear_map.keys()):
                    words_line, glosses_line = interlinear_map[line_num]

                    # Line 1: Line number + Sanskrit words separated by " | "
                    f.write(f"{line_num}. {words_line}\n")

                    # Line 2: Glosses separated by " | "
                    f.write(f"{glosses_line}\n")

                    # Blank line between entries (NO translation text)
                    f.write("\n")
                    total_lines += 1

        print(f"  ✓ Generated {total_lines:,} lines in {elapsed:.2f}s")
        print(f"    Output: {output_path}")

    def generate_line_xml(self, book_id: str, line_number: int) -> str:
        """
        Generate XML for a complete line in Greek format:
        <l n="1">| word1 |
        | **gloss1** |
        | lemma1 ~ POS deprel head sent_pos |  | word2 |
        | **gloss2** |
        | lemma2 ~ POS deprel head sent_pos | ...
        </l>

        For works with treebank data, includes: ~ POS deprel head sent_pos
        For works without treebank, just: | lemma |

        Args:
            book_id: Book identifier
            line_number: Line number

        Returns:
            Complete XML string for the line
        """
        words = self.get_line_words(book_id, line_number)

        if not words:
            return ""

        # Build content parts (without tags)
        xml_parts = []

        for i, word_data in enumerate(words):
            # Lookup gloss and sanitize all text for XML
            gloss = self.lookup_word_gloss(word_data)
            word_clean = sanitize_xml_text(word_data.word)
            gloss_clean = sanitize_xml_text(gloss)
            lemma_clean = sanitize_xml_text(word_data.lemma) if word_data.lemma else "?"

            # Build lemma line with optional tree data
            # Format: | lemma ~ POS deprel head sent_pos |
            if word_data.deprel is not None and word_data.head is not None:
                pos = word_data.pos_tag or "X"
                deprel = word_data.deprel
                head = word_data.head
                sent_pos = word_data.sentence_position or 0
                lemma_line = f"| {lemma_clean} ~ {pos} {deprel} {head} {sent_pos} |"
            else:
                lemma_line = f"| {lemma_clean} |"

            # First word: no leading separator
            if i == 0:
                xml_parts.append(f"| {word_clean} |")
                xml_parts.append(f"| **{gloss_clean}** |")
                xml_parts.append(lemma_line)
            else:
                # Subsequent words: append separator to previous lemma line, then add word on same line
                xml_parts[-1] += f"  | {word_clean} |"
                xml_parts.append(f"| **{gloss_clean}** |")
                xml_parts.append(lemma_line)

        # Format matching Greek: <l n="X">first_part
        # middle_parts
        # last_part</l>
        if xml_parts:
            # Prepend opening tag to first line
            xml_parts[0] = f'<l n="{line_number}">{xml_parts[0]}'
            # Append closing tag to last line
            xml_parts[-1] = f'{xml_parts[-1]}</l>'

        return "\n".join(xml_parts)

    def generate_book_xml(self, book_id: str) -> str:
        """Generate XML for all lines in a book."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT line_number
            FROM text_lines
            WHERE book_id = ?
            ORDER BY line_number
        """, (book_id,))

        line_numbers = [row['line_number'] for row in cursor.fetchall()]

        # Extract book number from book_id
        book_num = book_id.split('.')[-1]

        xml_parts = []
        xml_parts.append(f'                <div type="textpart" subtype="Book" n="{book_num}">')

        for line_num in line_numbers:
            line_xml = self.generate_line_xml(book_id, line_num)
            if line_xml:
                # Add line XML without indentation (matches Greek format)
                xml_parts.append(f"                    {line_xml}")

        xml_parts.append("                </div>")

        return "\n".join(xml_parts)

    def write_tei_file(self, work_id: str, output_path: Path):
        """
        Generate TEI XML file for a work.

        Creates word-by-word interlinear XML in the exact format as Greek interlinear.
        Format matches tlg0093.tlg001_OGL.perseus-eng99.xml structure.

        Args:
            work_id: Work identifier
            output_path: Path to output TEI XML file
        """
        work_info = self.get_work_info(work_id)
        books = self.get_books_for_work(work_id)

        # Sanitize work metadata for XML
        title = sanitize_xml_text(work_info["title_english"] or work_info["title"])
        author = sanitize_xml_text(work_info["author"])

        xml_lines = []

        # XML declaration and TEI header
        xml_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        xml_lines.append('<?xml-model href="http://www.stoa.org/epidoc/schema/8.19/tei-epidoc.rng"')
        xml_lines.append('  schematypens="http://relaxng.org/ns/structure/1.0"?>')
        xml_lines.append('<TEI xmlns="http://www.tei-c.org/ns/1.0">')
        xml_lines.append('    <teiHeader>')
        xml_lines.append('        <fileDesc>')
        xml_lines.append('            <titleStmt>')
        xml_lines.append(f'                <title>{title} - Interlinear Translation</title>')
        xml_lines.append(f'                <author>{author}</author>')
        xml_lines.append('                <editor role="translator">Interlinear (Beta, AI-generated from app dictionary)</editor>')
        xml_lines.append('                <sponsor>Derived from DCS dictionary</sponsor>')
        xml_lines.append('                <principal></principal>')
        xml_lines.append('                <respStmt>')
        xml_lines.append('                    <resp>AI-generated interlinear translation</resp>')
        xml_lines.append('                    <name>Claude Code</name>')
        xml_lines.append('                </respStmt>')
        xml_lines.append('            </titleStmt>')
        xml_lines.append('            <extent>AI-generated interlinear</extent>')
        xml_lines.append('            <publicationStmt>')
        xml_lines.append('                <publisher></publisher>')
        xml_lines.append('                <pubPlace></pubPlace>')
        xml_lines.append('                <authority></authority>')
        xml_lines.append('            </publicationStmt>')
        xml_lines.append('            <notesStmt>')
        xml_lines.append('                <note anchored="true">AI-generated word-by-word interlinear translation derived from DCS dictionary.</note>')
        xml_lines.append('            </notesStmt>')
        xml_lines.append('            <sourceDesc>')
        xml_lines.append('                <biblStruct>')
        xml_lines.append('                    <monogr>')
        xml_lines.append(f'                        <author>{author}</author>')
        xml_lines.append(f'                        <title>{title}</title>')
        xml_lines.append('                        <title type="sub">Interlinear Translation</title>')
        xml_lines.append('                        <editor role="translator">AI-generated</editor>')
        xml_lines.append('                        <imprint>')
        xml_lines.append('                            <date>2025</date>')
        xml_lines.append('                        </imprint>')
        xml_lines.append('                    </monogr>')
        xml_lines.append('                </biblStruct>')
        xml_lines.append('            </sourceDesc>')
        xml_lines.append('        </fileDesc>')
        xml_lines.append('        <encodingDesc>')
        xml_lines.append('            <refsDecl n="CTS">')
        xml_lines.append(r'                <cRefPattern n="line" matchPattern="(\w+).(\w+)"')
        xml_lines.append('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\']//tei:l[@n=\'$2\'])">')
        xml_lines.append('                    <p>This pointer pattern extracts book and line</p>')
        xml_lines.append('                </cRefPattern>')
        xml_lines.append(r'                <cRefPattern n="book" matchPattern="(\w+)"')
        xml_lines.append('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\'])">')
        xml_lines.append('                    <p>This pointer pattern extracts book</p>')
        xml_lines.append('                </cRefPattern>')
        xml_lines.append('            </refsDecl>')
        xml_lines.append('            <refsDecl>')
        xml_lines.append('                <refState unit="book" delim="."/>')
        xml_lines.append('                <refState unit="line"/>')
        xml_lines.append('            </refsDecl>')
        xml_lines.append('        </encodingDesc>')
        xml_lines.append('        <profileDesc>')
        xml_lines.append('            <langUsage>')
        xml_lines.append('                <language ident="eng">English</language>')
        xml_lines.append('                <language ident="san">Sanskrit</language>')
        xml_lines.append('            </langUsage>')
        xml_lines.append('        </profileDesc>')
        xml_lines.append('        <revisionDesc>')
        xml_lines.append('            <change when="20251109" who="Claude Code">Generated interlinear translation.</change>')
        xml_lines.append('        </revisionDesc>')
        xml_lines.append('    </teiHeader>')
        xml_lines.append('    <text xml:lang="eng">')
        xml_lines.append('        <body>')
        xml_lines.append(f'            <div type="translation" n="urn:cts:sanskritLit:{work_id}.dcs-eng" xml:lang="eng">')

        # Add books
        for book_id in books:
            book_xml = self.generate_book_xml(book_id)
            xml_lines.append(book_xml)

        # Close tags
        xml_lines.append('            </div>')
        xml_lines.append('        </body>')
        xml_lines.append('    </text>')
        xml_lines.append('</TEI>')

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(xml_lines))

    def print_statistics(self):
        """Print generation statistics."""
        total_words = self.stats['words_total']
        found = self.stats['words_found']
        missing = self.stats['words_missing']
        treebank_words = self.stats['treebank_words']

        print("\n" + "=" * 70)
        print("Interlinear Generation Statistics")
        print("=" * 70)
        print(f"Lines processed: {self.stats['lines_processed']:,}")
        print(f"Total words: {total_words:,}")
        if total_words > 0:
            print(f"  Found in dictionary: {found:,} ({100*found/total_words:.1f}%)")
            print(f"  Missing: {missing:,} ({100*missing/total_words:.1f}%)")
            if treebank_words > 0:
                print(f"  With treebank data: {treebank_words:,} ({100*treebank_words/total_words:.1f}%)")

        # Treebank status
        if self.treebank:
            print(f"Treebank: {len(self.treebank.available_works)} works available")
        else:
            print("Treebank: Not loaded")

        # Get LRU cache info
        cache_info = self._cached_dictionary_lookup.cache_info()
        print(f"LRU Cache - Hits: {cache_info.hits:,}, Misses: {cache_info.misses:,}, Size: {cache_info.currsize:,}")

    def close(self):
        """Close database connections."""
        self.repo.close()
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def test_single_work(db_path: str, work_id: str, output_dir: Path):
    """Test interlinear generation on a single work (both .txt and .xml)."""
    print("=" * 70)
    print("Sanskrit Interlinear Generator - Single Work Test")
    print("=" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)
    txt_file = output_dir / f"{work_id}.interlinear.txt"
    xml_file = output_dir / f"{work_id}.dcs-eng99.xml"

    with SanskritInterlinearGenerator(db_path) as generator:
        # Generate text format
        generator.write_interlinear_file(work_id, txt_file)

        # Generate XML format
        print(f"\nGenerating TEI XML for: {work_id}")
        generator.write_tei_file(work_id, xml_file)
        print(f"  ✓ Created: {xml_file}")

        # Print statistics
        generator.print_statistics()


def main():
    """Main entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 generate_sanskrit_interlinear.py <database_path> [work_id]")
        print("\nExample:")
        print("  python3 generate_sanskrit_interlinear.py sanskrit_texts.db aitareyopanisad")
        sys.exit(1)

    db_path = sys.argv[1]
    work_id = sys.argv[2] if len(sys.argv) > 2 else "aitareyopanishad"

    output_dir = Path(__file__).parent / "interlinear"
    test_single_work(db_path, work_id, output_dir)


if __name__ == '__main__':
    main()
