#!/usr/bin/env python3
"""
Dictionary Coverage Report Script

This script analyzes dictionary coverage for Greek/Latin texts in the Perseus database.
It replicates the "Check Definitions" functionality from the Android app to identify:
- Words with no dictionary entries
- Words with only morphological entries
- Words with full definitions

Usage:
    python3 check_dictionary_coverage.py --book-id tlg0012.tlg001.perseus-grc2 --start-line 1 --end-line 100
    python3 check_dictionary_coverage.py --work-id tlg0012.tlg001 --language greek
"""

import sqlite3
import re
import argparse
import sys
import csv
from collections import defaultdict
from typing import List, Set, Tuple, Dict

class DictionaryCoverageChecker:
    def __init__(self, db_path: str):
        """Initialize with path to Perseus database."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()

    def extract_words_from_text(self, text: str) -> List[str]:
        """
        Extract words from a text line using the same logic as the Android app.
        Handles multi-language support including Greek, Latin, and others.
        """
        words = []
        word_start = -1
        i = 0

        while i < len(text):
            char = text[i]

            # Check if character is a word character
            # Include hyphen for Akkadian/cuneiform transliteration (e.g., "it-bi-e-ma")
            # Include slash for Hebrew morpheme boundaries (e.g., "וַֽ/יְהִי֙")
            # Include apostrophe when between letters (e.g., "Ἀτρεΐδης")
            # Include all Unicode combining characters (diacritics, vowel marks, etc.)
            is_word_char = (
                char.isalpha() or
                char == '-' or
                char == '/' or
                # Unicode combining marks
                ord(char) in range(0x0300, 0x0370) or  # Combining Diacritical Marks
                ord(char) in range(0x1AB0, 0x1B00) or  # Combining Diacritical Marks Extended
                ord(char) in range(0x20D0, 0x2100) or  # Combining Diacritical Marks for Symbols
                ord(char) in range(0xFE20, 0xFE30) or  # Combining Half Marks
                # Apostrophe between letters
                (char == "'" and i > 0 and i < len(text) - 1 and
                 text[i-1].isalpha() and text[i+1].isalpha())
            )

            if is_word_char and word_start == -1:
                # Start of a new word
                word_start = i
            elif not is_word_char and word_start != -1:
                # End of current word
                word = text[word_start:i]
                if word:
                    words.append(word)
                word_start = -1

            i += 1

        # Handle last word if line ends with a word character
        if word_start != -1:
            word = text[word_start:]
            if word:
                words.append(word)

        return words

    def normalize_apostrophes(self, word: str) -> str:
        """Normalize all apostrophe variants to U+02BC (ʼ)."""
        import unicodedata
        # First normalize to NFC (precomposed) form
        word = unicodedata.normalize('NFC', word)
        # Then normalize apostrophes
        return (word
                .replace("'", "ʼ")  # U+0027 → U+02BC
                .replace("'", "ʼ")  # U+2019 → U+02BC
                .replace("᾿", "ʼ")  # U+1FBF → U+02BC
                .replace("′", "ʼ")  # U+2032 → U+02BC
                .replace("´", "ʼ"))  # U+00B4 → U+02BC

    def normalize_greek_ultra(self, word: str) -> str:
        """Ultra-aggressive Greek normalization - removes ALL diacritics."""
        import unicodedata
        # Decompose to NFD
        decomposed = unicodedata.normalize('NFD', word)
        # Remove combining characters
        without_combining = ''.join(c for c in decomposed
                                    if unicodedata.category(c) != 'Mn')
        # Lowercase and convert final sigma
        lowercased = without_combining.lower().replace('ς', 'σ')
        return lowercased

    def check_word_in_dictionary(self, word: str, language: str) -> Tuple[str, List[str]]:
        """
        Check if a word has dictionary entries using the FULL app logic.
        Returns (status, sources) where status is one of:
        - "no_entry": No dictionary entry at all
        - "morphology_only": Only morphological entries
        - "has_definition": Has actual dictionary definitions
        """
        # Clean punctuation but preserve apostrophes
        cleaned_word = re.sub(r'[.,;:!?·]', '', word)

        # Normalize apostrophes for Greek
        if language.lower() == 'greek':
            cleaned_word = self.normalize_apostrophes(cleaned_word)

        # Normalize language
        language = language.lower().strip()

        sources = []
        has_morphology = False
        has_definition = False

        # Step 1: Check direct dictionary entries
        cursor = self.conn.execute("""
            SELECT headword, source, entry_plain, entry_html
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
        """, (cleaned_word, language))

        for row in cursor:
            sources.append(row['source'])
            entry_text = row['entry_html'] or row['entry_plain'] or ""
            if "Morphological entry" in entry_text:
                has_morphology = True
            else:
                has_definition = True

        # Step 2: Check lemma mappings (exact match)
        cursor = self.conn.execute("""
            SELECT DISTINCT l.lemma, l.morph_info, d.source, d.entry_plain, d.entry_html
            FROM lemma_map l
            LEFT JOIN dictionary_entries d ON l.lemma = d.headword AND d.language = ?
            WHERE l.word_form = ?
        """, (language, cleaned_word))

        for row in cursor:
            if row['source']:
                sources.append(row['source'])
                entry_text = row['entry_html'] or row['entry_plain'] or ""
                if "Morphological entry" in entry_text:
                    has_morphology = True
                else:
                    has_definition = True
            elif row['morph_info']:
                has_morphology = True

        # Step 3: For Greek words ending with apostrophes, try prefix search
        if language == 'greek' and not has_definition and not has_morphology:
            apostrophe_chars = ["'", "'", "ʼ"]
            if any(cleaned_word.endswith(ch) for ch in apostrophe_chars):
                for ch in apostrophe_chars:
                    if cleaned_word.endswith(ch):
                        prefix = cleaned_word[:-1]
                        break

                # Prefix search with length limit
                max_length = len(prefix) + 2 if len(prefix) == 1 else len(prefix) + 4
                cursor = self.conn.execute("""
                    SELECT DISTINCT l.lemma, l.morph_info, d.source, d.entry_plain, d.entry_html
                    FROM lemma_map l
                    LEFT JOIN dictionary_entries d ON l.lemma = d.headword AND d.language = ?
                    WHERE l.word_form LIKE ? || '%'
                    AND LENGTH(l.word_form) <= ?
                    ORDER BY LENGTH(l.word_form) ASC, l.confidence DESC
                    LIMIT 10
                """, (language, prefix, max_length))

                for row in cursor:
                    if row['source']:
                        sources.append(row['source'])
                        entry_text = row['entry_html'] or row['entry_plain'] or ""
                        if "Morphological entry" in entry_text:
                            has_morphology = True
                        else:
                            has_definition = True
                    elif row['morph_info']:
                        has_morphology = True

        # Step 4: Ultra-normalized fallback for Greek
        if language == 'greek' and not has_definition and not has_morphology:
            ultra_normalized = self.normalize_greek_ultra(cleaned_word)

            # Try ultra-normalized dictionary lookup
            cursor = self.conn.execute("""
                SELECT headword, source, entry_plain, entry_html
                FROM dictionary_entries
                WHERE headword_normalized_ultra = ? AND language = ?
            """, (ultra_normalized, language))

            for row in cursor:
                sources.append(row['source'])
                entry_text = row['entry_html'] or row['entry_plain'] or ""
                if "Morphological entry" in entry_text:
                    has_morphology = True
                else:
                    has_definition = True

            # Try ultra-normalized lemma mappings
            if not has_definition and not has_morphology:
                cursor = self.conn.execute("""
                    SELECT DISTINCT l.lemma, l.morph_info, d.source, d.entry_plain, d.entry_html
                    FROM lemma_map l
                    LEFT JOIN dictionary_entries d ON l.lemma = d.headword AND d.language = ?
                    WHERE l.word_form_normalized_ultra = ?
                    ORDER BY l.confidence DESC
                    LIMIT 5
                """, (language, ultra_normalized))

                for row in cursor:
                    if row['source']:
                        sources.append(row['source'])
                        entry_text = row['entry_html'] or row['entry_plain'] or ""
                        if "Morphological entry" in entry_text:
                            has_morphology = True
                        else:
                            has_definition = True
                    elif row['morph_info']:
                        has_morphology = True

        # Determine status
        if has_definition:
            return ("has_definition", sources)
        elif has_morphology:
            return ("morphology_only", sources)
        else:
            return ("no_entry", sources)

    def get_text_lines(self, book_id: str, start_line: int, end_line: int) -> List[Tuple[int, int, str, str]]:
        """
        Get text lines from the database.
        Returns list of (line_number, sequence_number, line_text, speaker).
        """
        cursor = self.conn.execute("""
            SELECT line_number, sequence_number, line_text, speaker
            FROM text_lines
            WHERE book_id = ? AND line_number BETWEEN ? AND ?
            ORDER BY line_number, sequence_number
        """, (book_id, start_line, end_line))

        return [(row['line_number'], row['sequence_number'],
                row['line_text'], row['speaker'])
                for row in cursor]

    def get_books_for_work(self, work_id: str) -> List[str]:
        """Get all book IDs for a given work ID."""
        cursor = self.conn.execute("""
            SELECT id FROM books WHERE work_id = ?
        """, (work_id,))
        return [row['id'] for row in cursor]

    def get_book_info(self, book_id: str) -> Dict[str, str]:
        """Get book information including author and work titles."""
        cursor = self.conn.execute("""
            SELECT b.id as book_id, b.book_number, b.line_count,
                   w.id as work_id, w.title as work_title, w.title_english as work_title_english,
                   a.id as author_id, a.name as author_name, a.language
            FROM books b
            JOIN works w ON b.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE b.id = ?
        """, (book_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {}

    def analyze_book(self, book_id: str, start_line: int = None, end_line: int = None, csv_output: str = None) -> Dict:
        """
        Analyze dictionary coverage for a book.
        If start_line and end_line are None, analyze the entire book.
        """
        # Get book info
        book_info = self.get_book_info(book_id)
        if not book_info:
            print(f"Error: Book '{book_id}' not found in database")
            return None

        language = book_info['language']

        # Determine line range
        if start_line is None or end_line is None:
            start_line = 1
            end_line = book_info.get('line_count', 10000)

        print(f"\n{'='*80}")
        print(f"Dictionary Coverage Report")
        print(f"{'='*80}")
        print(f"Author: {book_info['author_name']}")
        print(f"Work: {book_info.get('work_title_english') or book_info['work_title']}")
        print(f"Book: {book_info['book_number']}")
        print(f"Language: {language}")
        print(f"Lines: {start_line}-{end_line}")
        print(f"{'='*80}\n")

        # Get text lines
        text_lines = self.get_text_lines(book_id, start_line, end_line)
        print(f"Loaded {len(text_lines)} text lines\n")

        # Extract all unique words
        all_words: Set[str] = set()
        for line_num, seq_num, text, speaker in text_lines:
            words = self.extract_words_from_text(text)
            all_words.update(words)

            # Also check speaker names
            if speaker and speaker.strip():
                all_words.add(speaker.strip())

        print(f"Found {len(all_words)} unique words\n")

        # Check each word
        words_no_entry = []
        words_morphology_only = []
        words_with_definition = []

        word_details = {}

        for word in sorted(all_words):
            status, sources = self.check_word_in_dictionary(word, language)
            word_details[word] = (status, sources)

            if status == "no_entry":
                words_no_entry.append(word)
            elif status == "morphology_only":
                words_morphology_only.append(word)
            else:
                words_with_definition.append(word)

        # Write CSV output if requested
        if csv_output:
            with open(csv_output, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow([
                    'word',
                    'status',
                    'sources',
                    'author',
                    'work',
                    'book',
                    'line_range',
                    'language'
                ])

                # Write all words with their status
                for word in sorted(all_words):
                    status, sources = word_details[word]
                    writer.writerow([
                        word,
                        status,
                        '; '.join(sources) if sources else '',
                        book_info['author_name'],
                        book_info.get('work_title_english') or book_info['work_title'],
                        book_info['book_number'],
                        f"{start_line}-{end_line}",
                        language
                    ])
            print(f"CSV output written to: {csv_output}")

        # Print summary
        print(f"{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total unique words: {len(all_words)}")
        print(f"Words with definitions: {len(words_with_definition)} ({len(words_with_definition)*100//len(all_words) if all_words else 0}%)")
        print(f"Words with morphology only: {len(words_morphology_only)} ({len(words_morphology_only)*100//len(all_words) if all_words else 0}%)")
        print(f"Words with NO entry: {len(words_no_entry)} ({len(words_no_entry)*100//len(all_words) if all_words else 0}%)")
        print(f"{'='*80}\n")

        # Print words with no entries
        if words_no_entry:
            print(f"\nWORDS WITH NO DICTIONARY ENTRY ({len(words_no_entry)}):")
            print(f"{'-'*80}")
            for word in words_no_entry[:50]:  # Limit to first 50
                print(f"  {word}")
            if len(words_no_entry) > 50:
                print(f"  ... and {len(words_no_entry) - 50} more")

        # Print words with morphology only
        if words_morphology_only:
            print(f"\nWORDS WITH MORPHOLOGY ONLY ({len(words_morphology_only)}):")
            print(f"{'-'*80}")
            for word in words_morphology_only[:50]:  # Limit to first 50
                print(f"  {word}")
            if len(words_morphology_only) > 50:
                print(f"  ... and {len(words_morphology_only) - 50} more")

        return {
            'book_info': book_info,
            'total_words': len(all_words),
            'words_with_definition': len(words_with_definition),
            'words_morphology_only': len(words_morphology_only),
            'words_no_entry': len(words_no_entry),
            'details': word_details
        }

    def analyze_work(self, work_id: str, csv_output: str = None) -> Dict:
        """Analyze dictionary coverage for an entire work (all books)."""
        books = self.get_books_for_work(work_id)
        if not books:
            print(f"Error: Work '{work_id}' not found or has no books")
            return None

        print(f"\nFound {len(books)} books for work {work_id}")

        # Aggregate results across all books
        total_results = {
            'total_words': 0,
            'words_with_definition': 0,
            'words_morphology_only': 0,
            'words_no_entry': 0,
            'all_words_no_entry': set(),
            'all_words_morphology_only': set()
        }

        # For work-level analysis, aggregate first then write CSV
        all_word_details = {}

        for book_id in books:
            result = self.analyze_book(book_id, csv_output=None)  # Don't write CSV per book
            if result:
                total_results['total_words'] += result['total_words']
                total_results['words_with_definition'] += result['words_with_definition']
                total_results['words_morphology_only'] += result['words_morphology_only']
                total_results['words_no_entry'] += result['words_no_entry']

                # Collect words for work-level reporting
                for word, (status, sources) in result['details'].items():
                    # Track unique words across all books
                    if word not in all_word_details:
                        all_word_details[word] = (status, sources)

                    if status == 'no_entry':
                        total_results['all_words_no_entry'].add(word)
                    elif status == 'morphology_only':
                        total_results['all_words_morphology_only'].add(word)

        # Write CSV output if requested
        if csv_output:
            # Get work info from first book
            first_book_info = self.get_book_info(books[0])

            with open(csv_output, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow([
                    'word',
                    'status',
                    'sources',
                    'author',
                    'work',
                    'language'
                ])

                # Write all unique words
                for word in sorted(all_word_details.keys()):
                    status, sources = all_word_details[word]
                    writer.writerow([
                        word,
                        status,
                        '; '.join(sources) if sources else '',
                        first_book_info['author_name'],
                        first_book_info.get('work_title_english') or first_book_info['work_title'],
                        first_book_info['language']
                    ])
            print(f"CSV output written to: {csv_output}")

        # Print work-level summary
        print(f"\n{'='*80}")
        print(f"WORK-LEVEL SUMMARY: {work_id}")
        print(f"{'='*80}")
        print(f"Total unique words across all books: {total_results['total_words']}")
        print(f"Unique words with NO entry: {len(total_results['all_words_no_entry'])}")
        print(f"Unique words with morphology only: {len(total_results['all_words_morphology_only'])}")
        print(f"{'='*80}\n")

        return total_results


def main():
    parser = argparse.ArgumentParser(
        description='Analyze dictionary coverage for Perseus texts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a specific book and line range
  python3 check_dictionary_coverage.py --book-id tlg0012.tlg001.perseus-grc2 --start-line 1 --end-line 100

  # Analyze an entire book
  python3 check_dictionary_coverage.py --book-id tlg0012.tlg001.perseus-grc2

  # Analyze an entire work (all books)
  python3 check_dictionary_coverage.py --work-id tlg0012.tlg001
        """
    )

    parser.add_argument('--db', default='perseus_texts.db',
                        help='Path to Perseus database (default: perseus_texts.db)')
    parser.add_argument('--book-id', help='Book ID to analyze (e.g., tlg0012.tlg001.perseus-grc2)')
    parser.add_argument('--work-id', help='Work ID to analyze all books (e.g., tlg0012.tlg001)')
    parser.add_argument('--start-line', type=int, help='Start line number (requires --book-id)')
    parser.add_argument('--end-line', type=int, help='End line number (requires --book-id)')
    parser.add_argument('--language', help='Language filter (default: auto-detect from book/work)')
    parser.add_argument('--csv', dest='csv_output', help='Output CSV file path (e.g., coverage_report.csv)')

    args = parser.parse_args()

    # Validate arguments
    if not args.book_id and not args.work_id:
        parser.error('Either --book-id or --work-id must be specified')

    if args.book_id and args.work_id:
        parser.error('Cannot specify both --book-id and --work-id')

    if (args.start_line or args.end_line) and not args.book_id:
        parser.error('--start-line and --end-line require --book-id')

    # Create checker
    checker = DictionaryCoverageChecker(args.db)

    # Run analysis
    try:
        if args.work_id:
            result = checker.analyze_work(args.work_id, csv_output=args.csv_output)
        else:
            result = checker.analyze_book(args.book_id, args.start_line, args.end_line, csv_output=args.csv_output)

        if result is None:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
