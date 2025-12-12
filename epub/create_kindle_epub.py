#!/usr/bin/env python3
"""
Kindle ePub Generator for Classics Viewer

Creates ePub files optimized for Kindle with:
- Wrapping interlinear text (no horizontal scroll)
- Greek text with glosses
- TOC-based navigation
- No JavaScript dependencies
"""

import sqlite3
import os
import re
import zipfile
from pathlib import Path
from datetime import datetime
import html
import argparse

class KindleEpubGenerator:
    def __init__(self, db_path: str, output_dir: str):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Dictionary collector: word_id -> {'word': greek_word, 'lemma': lemma_form}
        self.dictionary = {}
        # Preload lemma mappings and dictionary entries
        self._preload_dictionary_data()

    def connect_db(self):
        return sqlite3.connect(self.db_path)

    def _preload_dictionary_data(self):
        """Preload lemma mappings and dictionary entries for fast lookup."""
        print("Loading dictionary data...")
        conn = self.connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Load lemma mappings: word_form -> lemma
        self.word_to_lemma = {}
        self.word_to_morph = {}
        cur.execute("""
            SELECT word_form, lemma, morph_info
            FROM lemma_map
            ORDER BY confidence DESC
        """)
        for row in cur.fetchall():
            word_form = row['word_form']
            if word_form not in self.word_to_lemma:  # Keep highest confidence lemma
                self.word_to_lemma[word_form] = row['lemma']
            # Collect morph_info from any entry that has it
            if row['morph_info'] and word_form not in self.word_to_morph:
                self.word_to_morph[word_form] = row['morph_info']

        print(f"  Loaded {len(self.word_to_lemma)} lemma mappings")

        # Load dictionary entries: headword -> list of entries
        self.dictionary_entries = {}
        cur.execute("""
            SELECT headword, source, entry_plain
            FROM dictionary_entries
            WHERE language = 'greek'
            ORDER BY headword,
                CASE LOWER(source)
                    WHEN 'lsj' THEN 1
                    WHEN 'cunliffe' THEN 2
                    WHEN 'wiktionary' THEN 3
                    ELSE 4
                END
        """)
        for row in cur.fetchall():
            headword = row['headword']
            if headword not in self.dictionary_entries:
                self.dictionary_entries[headword] = []
            self.dictionary_entries[headword].append({
                'source': row['source'],
                'text': row['entry_plain']
            })

        print(f"  Loaded dictionary entries for {len(self.dictionary_entries)} headwords")
        conn.close()

    def get_lemma_for_word(self, word: str) -> str:
        """Get lemma for a word, with fallback attempts."""
        # Try exact match first
        if word in self.word_to_lemma:
            return self.word_to_lemma[word]

        # Try lowercase
        word_lower = word.lower()
        if word_lower in self.word_to_lemma:
            return self.word_to_lemma[word_lower]

        # Return the word itself as fallback
        return word

    def get_dictionary_entries(self, lemma: str) -> list:
        """Get dictionary entries for a lemma."""
        # Try exact lemma first
        if lemma in self.dictionary_entries:
            return self.dictionary_entries[lemma]

        # Try lowercase
        lemma_lower = lemma.lower()
        if lemma_lower in self.dictionary_entries:
            return self.dictionary_entries[lemma_lower]

        return []

    def get_work(self, work_id: str) -> dict:
        """Get work metadata."""
        conn = self.connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT w.*, a.name as author_name
            FROM works w
            JOIN authors a ON w.author_id = a.id
            WHERE w.id = ?
        """, (work_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_books(self, work_id: str) -> list:
        """Get all books for a work."""
        conn = self.connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM books
            WHERE work_id = ?
            ORDER BY book_number
        """, (work_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_text_lines(self, book_id: str) -> list:
        """Get all text lines for a book."""
        conn = self.connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT line_number, line_text, speaker
            FROM text_lines
            WHERE book_id = ?
            ORDER BY line_number
        """, (book_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_interlinear(self, book_id: str) -> dict:
        """Get interlinear data for a book, keyed by line number."""
        conn = self.connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT start_line, translation_text
            FROM translation_segments
            WHERE book_id = ? AND translator LIKE 'Interlinear%'
            ORDER BY start_line
        """, (book_id,))
        rows = cur.fetchall()
        conn.close()

        interlinear = {}
        for row in rows:
            interlinear[row['start_line']] = row['translation_text']
        return interlinear

    def get_translation(self, book_id: str, translator: str = None) -> list:
        """Get translation segments for a book from a single translator."""
        conn = self.connect_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if not translator:
            # Find the translator with the most segments for this book
            cur.execute("""
                SELECT translator, COUNT(*) as cnt
                FROM translation_segments
                WHERE book_id = ? AND translator NOT LIKE 'Interlinear%'
                GROUP BY translator
                ORDER BY cnt DESC
                LIMIT 1
            """, (book_id,))
            row = cur.fetchone()
            if row:
                translator = row['translator']
            else:
                conn.close()
                return []

        cur.execute("""
            SELECT start_line, end_line, translation_text, translator
            FROM translation_segments
            WHERE book_id = ? AND translator = ?
            ORDER BY start_line
        """, (book_id, translator))

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def parse_interlinear(self, interlinear_text: str) -> list:
        """
        Parse pipe-delimited interlinear format into word groups.

        Format:
        | word |
        | **definition** |
        | morph |  | nextword |
        ...

        Word groups are separated by "|  |" (pipe-space-space-pipe)
        """
        if not interlinear_text:
            return []

        # Split by "|  |" pattern (word group boundary)
        parts = interlinear_text.split('|  |')

        word_groups = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Split by newline to get word, definition, morph lines
            lines = []
            for line in part.split('\n'):
                # Remove pipe delimiters and whitespace
                line = line.strip().strip('|').strip()
                if line:
                    lines.append(line)

            if not lines:
                continue

            # First line is the word
            word = lines[0] if lines else ''

            # Find definition (in **bold**) and morph
            definition = ''
            morph = ''

            for line in lines[1:]:
                if line.startswith('**') and line.endswith('**'):
                    definition = line[2:-2]  # Strip ** from both ends
                elif '**' in line:
                    # Extract bold part
                    match = re.search(r'\*\*(.+?)\*\*', line)
                    if match:
                        definition = match.group(1)
                else:
                    # This is morphology info
                    morph = line

            if word:
                word_groups.append({
                    'word': word,
                    'gloss': definition,
                    'morph': morph
                })

        return word_groups

    def get_dict_file_for_word(self, word: str) -> str:
        """Get the dictionary filename for a word based on its first letter."""
        if not word:
            return "dict_other.xhtml"
        first_char = word[0].lower()
        # Use the first character as filename (handles Greek letters)
        # Make it safe for filenames
        import base64
        safe_char = base64.urlsafe_b64encode(first_char.encode('utf-8')).decode('ascii').rstrip('=')
        return f"dict_{safe_char}.xhtml"

    def render_interlinear_line(self, line_num: int, word_groups: list, book_num: int = None, link_to_dict: bool = True) -> str:
        """Render a single interlinear line as HTML with linked words.

        Shows short glosses inline, but words link to full dictionary definitions.
        """
        # Add anchor ID for lines at multiples of 100
        line_id = f' id="line-{line_num}"' if line_num % 100 == 0 else ''
        html_parts = [f'<p class="interlinear-line"{line_id}>']
        # Display line number with book prefix (e.g., "3.114")
        line_display = f'{book_num}.{line_num}' if book_num else str(line_num)
        html_parts.append(f'<span class="line-num">{line_display}</span> ')

        for wg in word_groups:
            word = html.escape(wg['word'])
            gloss = html.escape(wg['gloss']) if wg['gloss'] else ''

            # Create anchor ID from word (normalized for URL)
            word_id = self.make_word_id(wg['word'])

            # Collect word for dictionary page generation (with lemma lookup)
            if word_id not in self.dictionary:
                lemma = self.get_lemma_for_word(wg['word'])
                self.dictionary[word_id] = {
                    'word': wg['word'],
                    'lemma': lemma,
                    'gloss': wg['gloss'] or ''  # Keep gloss as fallback
                }

            # Get the correct dictionary file for this word
            dict_file = self.get_dict_file_for_word(wg['word'])

            # Display: linked word with short gloss in parentheses
            if link_to_dict:
                if gloss:
                    html_parts.append(f'<a href="{dict_file}#{word_id}" class="word-link">{word}</a> <span class="gloss">({gloss})</span> ')
                else:
                    html_parts.append(f'<a href="{dict_file}#{word_id}" class="word-link">{word}</a> ')
            else:
                if gloss:
                    html_parts.append(f'<span class="greek">{word}</span> <span class="gloss">({gloss})</span> ')
                else:
                    html_parts.append(f'<span class="greek">{word}</span> ')

        html_parts.append('</p>')
        return ''.join(html_parts)

    def make_word_id(self, word: str) -> str:
        """Create a URL-safe ID from a Greek word."""
        import base64
        # Use base64 to handle Greek characters safely
        return base64.urlsafe_b64encode(word.encode('utf-8')).decode('ascii').rstrip('=')

    def render_plain_line(self, line_num: int, line_text: str, book_num: int = None, speaker: str = None) -> str:
        """Render a plain Greek line without interlinear."""
        text = html.escape(line_text)
        speaker_html = f'<span class="speaker">{html.escape(speaker)}</span> ' if speaker else ''
        # Add anchor ID for lines at multiples of 100
        line_id = f' id="line-{line_num}"' if line_num % 100 == 0 else ''
        # Display line number with book prefix (e.g., "3.114")
        line_display = f'{book_num}.{line_num}' if book_num else str(line_num)
        return f'''<p class="line"{line_id}>
<span class="line-num">{line_display}</span>
{speaker_html}<span class="greek">{text}</span>
</p>'''

    def generate_chapter_html(self, book: dict, lines: list, interlinear: dict) -> str:
        """Generate XHTML content for a chapter."""
        content_parts = []
        book_num = book['book_number']

        # Generate line navigation links (to lines 100, 200, 300, etc.)
        if lines:
            max_line = max(line['line_number'] for line in lines)
            line_nav_links = []
            for target_line in range(100, max_line + 1, 100):
                # Only add link if this line exists in the chapter
                if any(line['line_number'] == target_line for line in lines):
                    line_nav_links.append(f'<a href="#line-{target_line}">{book_num}.{target_line}</a>')

            if line_nav_links:
                content_parts.append(f'<p class="line-nav">Lines: {" · ".join(line_nav_links)}</p>')

        for line in lines:
            line_num = line['line_number']

            if line_num in interlinear:
                # Parse and render interlinear
                word_groups = self.parse_interlinear(interlinear[line_num])
                if word_groups:
                    content_parts.append(self.render_interlinear_line(line_num, word_groups, book_num))
                else:
                    # Fallback to plain if parsing fails
                    content_parts.append(self.render_plain_line(
                        line_num, line['line_text'], book_num, line.get('speaker')
                    ))
            else:
                # Plain Greek line
                content_parts.append(self.render_plain_line(
                    line_num, line['line_text'], book_num, line.get('speaker')
                ))

        return '\n'.join(content_parts)

    def generate_translation_html(self, book: dict, translations: list) -> str:
        """Generate HTML for a translation chapter."""
        if not translations:
            return '<p>No translation available for this book.</p>'

        content_parts = []
        book_num = book['book_number']

        for seg in translations:
            text = seg['translation_text'] or ''
            start = seg.get('start_line', '')
            end = seg.get('end_line', '')

            # Add line reference with book number prefix (e.g., [5.460-5.510])
            if start and end and start != end:
                line_ref = f'[{book_num}.{start}-{book_num}.{end}]'
            elif start:
                line_ref = f'[{book_num}.{start}]'
            else:
                line_ref = ''

            content_parts.append(
                f'<p class="translation-para">'
                f'<span class="line-ref">{line_ref}</span> '
                f'{html.escape(text)}'
                f'</p>'
            )

        return '\n'.join(content_parts)

    def get_css(self) -> str:
        """Return the CSS stylesheet."""
        return '''/* Kindle ePub Stylesheet - Optimized for e-ink */

body {
    font-family: "Gentium Plus", "Gentium", "Times New Roman", serif;
    margin: 5%;
    line-height: 1.4;
}

/* Page header showing work/book context */
.page-header {
    font-size: 0.85em;
    font-weight: bold;
    color: #333;
    text-align: center;
    margin: 0 0 0.5em 0;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #999;
}

/* Line navigation links */
.line-nav {
    font-size: 0.75em;
    color: #666;
    text-align: center;
    margin: 0.5em 0 1em 0;
}

.line-nav a {
    color: #0066cc;
    text-decoration: none;
    margin: 0 0.2em;
}

h1 {
    text-align: center;
    font-size: 1.5em;
    margin: 1em 0;
    page-break-after: avoid;
}

h2 {
    font-size: 1.2em;
    margin: 1em 0 0.5em 0;
}

/* Interlinear lines */
.interlinear-line {
    margin: 1em 0;
    padding-bottom: 0.8em;
    border-bottom: 1px dotted #aaa;
}

.line-num {
    font-weight: bold;
    color: #444;
    margin-right: 0.3em;
}

/* Word groups - simple inline with line breaks */
.word-group {
    display: inline;
    white-space: nowrap;
    margin-right: 0.4em;
}

.greek {
    font-size: 1.1em;
}

.gloss {
    font-size: 0.8em;
    color: #666;
}

/* Plain lines without interlinear */
.line {
    margin: 0.3em 0;
}

.speaker {
    font-weight: bold;
    color: #333;
}

/* Navigation */
.nav {
    margin: 2em 0;
    text-align: center;
}

.nav a {
    margin: 0 1em;
}

/* Translation section */
.translation {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 2px solid #999;
}

.translation p {
    text-indent: 1.5em;
    margin: 0.5em 0;
}

/* Title page */
.title-page {
    text-align: center;
    margin-top: 30%;
}

.title-page h1 {
    font-size: 2em;
    margin-bottom: 0.5em;
}

.title-page .author {
    font-size: 1.3em;
    margin-bottom: 2em;
}

.title-page .subtitle {
    font-size: 1em;
    color: #666;
}

/* Word links in interlinear text */
.word-link {
    color: #0066cc;
    text-decoration: none;
}

.word-link:visited {
    color: #551a8b;
}

/* Dictionary page styles */
.dict-note {
    font-style: italic;
    color: #666;
    margin-bottom: 2em;
    font-size: 0.9em;
}

.dict-entry {
    margin: 1.5em 0;
    padding-bottom: 1em;
    border-bottom: 1px solid #ddd;
}

.dict-word {
    font-size: 1.3em;
    color: #333;
    margin: 0 0 0.3em 0;
}

.dict-morph {
    font-size: 0.85em;
    color: #666;
    font-style: italic;
    margin: 0.2em 0;
}

.dict-lemma {
    font-size: 0.9em;
    color: #444;
    margin: 0.3em 0;
}

.dict-def {
    margin: 0.5em 0;
    padding-left: 1em;
}

.dict-source {
    font-weight: bold;
    color: #0066cc;
    font-size: 0.85em;
}

.dict-text {
    font-size: 0.95em;
    line-height: 1.5;
}

.dict-gloss-fallback {
    font-style: italic;
    color: #555;
}

.dict-no-entry {
    font-style: italic;
    color: #999;
}

/* Translation chapter styles */
.translator {
    font-style: italic;
    color: #666;
    text-align: center;
    margin-bottom: 1.5em;
}

.translation-para {
    margin: 0.8em 0;
    text-align: justify;
    line-height: 1.6;
}

.line-ref {
    font-size: 0.75em;
    color: #999;
}

/* License page styles */
.license-page {
    font-size: 0.85em;
}

.license-text {
    margin: 0.8em 0;
    line-height: 1.5;
    white-space: pre-wrap;
}

.license-source {
    font-size: 0.9em;
    color: #666;
    margin-bottom: 1.5em;
    border-bottom: 1px solid #ccc;
    padding-bottom: 1em;
}
'''

    def create_epub(self, work_id: str, book_numbers: list = None, output_name: str = None):
        """Create an ePub for specified books of a work."""

        # Reset dictionary for this ePub
        self.dictionary = {}

        work = self.get_work(work_id)
        if not work:
            raise ValueError(f"Work not found: {work_id}")

        all_books = self.get_books(work_id)
        if book_numbers:
            books = [b for b in all_books if b['book_number'] in book_numbers]
        else:
            books = all_books

        if not books:
            raise ValueError(f"No books found for work: {work_id}")

        # Determine output filename
        if not output_name:
            book_str = f"_book_{book_numbers[0]}" if book_numbers and len(book_numbers) == 1 else ""
            output_name = f"{work['author_name']}_{work['title']}{book_str}.epub".replace(' ', '_')

        output_path = self.output_dir / output_name

        # Create ePub structure in memory
        epub_files = {}

        # mimetype (must be first, uncompressed)
        epub_files['mimetype'] = 'application/epub+zip'

        # container.xml
        epub_files['META-INF/container.xml'] = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''

        # CSS
        epub_files['OEBPS/styles/main.css'] = self.get_css()

        # Generate chapters
        manifest_items = []
        spine_items = []
        nav_items = []

        # Title page
        title_page = self.generate_title_page(work, books)
        epub_files['OEBPS/title.xhtml'] = title_page
        manifest_items.append(('title', 'title.xhtml', 'application/xhtml+xml'))
        spine_items.append('title')
        nav_items.append(('title', 'title.xhtml', 'Title Page'))

        # License page
        license_page = self.generate_license_page(work)
        epub_files['OEBPS/license.xhtml'] = license_page
        manifest_items.append(('license', 'license.xhtml', 'application/xhtml+xml'))
        spine_items.append('license')
        nav_items.append(('license', 'license.xhtml', 'License'))

        # Generate each book chapter (this also collects dictionary words)
        for book in books:
            book_id = book['id']
            book_num = book['book_number']
            chapter_file = f'book{book_num:02d}.xhtml'

            lines = self.get_text_lines(book_id)
            interlinear = self.get_interlinear(book_id)

            chapter_content = self.generate_chapter_html(book, lines, interlinear)
            book_label = book['label'] if book['label'] != f"Book {book_num}" else f"Book {book_num}"
            chapter_xhtml = self.wrap_xhtml(
                book_label,
                chapter_content,
                work['title'],
                author_name=work['author_name'],
                book_label=book_label
            )

            epub_files[f'OEBPS/{chapter_file}'] = chapter_xhtml
            manifest_items.append((f'book{book_num}', chapter_file, 'application/xhtml+xml'))
            spine_items.append(f'book{book_num}')
            nav_items.append((f'book{book_num}', chapter_file, book['label'] or f"Book {book_num}"))

        # Generate dictionary pages (split by first letter for faster loading)
        if self.dictionary:
            dict_pages = self.generate_dictionary_pages()
            for dict_file, content in sorted(dict_pages.items()):
                epub_files[f'OEBPS/{dict_file}'] = content
                # Create ID from filename
                dict_id = dict_file.replace('.xhtml', '').replace('.', '_')
                manifest_items.append((dict_id, dict_file, 'application/xhtml+xml'))
            print(f"  - {len(self.dictionary)} dictionary entries in {len(dict_pages)} files")

        # Generate English translation chapters at the end, grouped by translator
        # First, find all translators for this work
        conn = self.connect_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ts.translator
            FROM translation_segments ts
            JOIN books b ON ts.book_id = b.id
            WHERE b.work_id = ? AND ts.translator NOT LIKE 'Interlinear%'
            ORDER BY ts.translator
        """, (work_id,))
        translators = [row[0] for row in cur.fetchall()]
        conn.close()

        translation_count = 0
        for translator in translators:
            for book in books:
                book_id = book['id']
                book_num = book['book_number']
                translations = self.get_translation(book_id, translator)

                if translations:
                    # Use translator initials for filename to keep it short
                    trans_initials = ''.join(w[0] for w in translator.split())
                    trans_file = f'trans_{trans_initials}_{book_num:02d}.xhtml'
                    book_label = book['label'] if book['label'] != f"Book {book_num}" else f"Book {book_num}"
                    trans_title = f"{book_label} ({translator})"

                    trans_content = self.generate_translation_html(book, translations)
                    trans_xhtml = self.wrap_xhtml(
                        trans_title,
                        trans_content,
                        work['title'],
                        author_name=work['author_name']
                    )

                    trans_id = f'trans_{trans_initials}_{book_num}'
                    epub_files[f'OEBPS/{trans_file}'] = trans_xhtml
                    manifest_items.append((trans_id, trans_file, 'application/xhtml+xml'))
                    spine_items.append(trans_id)
                    nav_items.append((trans_id, trans_file, trans_title))
                    translation_count += 1

        if translation_count:
            print(f"  - {translation_count} translation chapter(s) from {len(translators)} translator(s)")

        # nav.xhtml (ePub3) - must be created before content.opf
        epub_files['OEBPS/nav.xhtml'] = self.generate_nav(work, nav_items)

        # toc.ncx (legacy)
        epub_files['OEBPS/toc.ncx'] = self.generate_ncx(work, nav_items)

        # content.opf (nav is added automatically in generate_opf)
        epub_files['OEBPS/content.opf'] = self.generate_opf(work, manifest_items, spine_items)

        # Write ePub file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # mimetype must be first and uncompressed
            zf.writestr('mimetype', epub_files['mimetype'], compress_type=zipfile.ZIP_STORED)

            for path, content in epub_files.items():
                if path != 'mimetype':
                    zf.writestr(path, content)

        print(f"Created: {output_path}")
        print(f"  - {len(books)} chapter(s)")
        print(f"  - {sum(b['line_count'] for b in books)} lines")

        return output_path

    def generate_title_page(self, work: dict, books: list) -> str:
        """Generate title page XHTML."""
        book_range = ""
        if len(books) == 1:
            book_range = f"Book {books[0]['book_number']}"
        elif len(books) > 1:
            book_range = f"Books {books[0]['book_number']}-{books[-1]['book_number']}"

        content = f'''<div class="title-page">
<h1>{html.escape(work['title'])}</h1>
<p class="author">{html.escape(work['author_name'])}</p>
<p class="subtitle">Greek Text with Interlinear Glosses</p>
{f'<p class="subtitle">{book_range}</p>' if book_range else ''}
<p class="subtitle" style="margin-top: 3em; font-size: 0.8em;">Generated by Classics Viewer</p>
</div>'''

        return self.wrap_xhtml(work['title'], content, work['title'])

    def generate_license_page(self, work: dict) -> str:
        """Generate license page XHTML by reading LICENSE.txt dynamically."""
        # Read LICENSE.txt from the repo root (one level up from epub directory)
        license_path = Path(__file__).parent.parent / 'LICENSE.txt'
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_text = f.read()
            print(f"  Loaded license from: {license_path}")
        except FileNotFoundError:
            license_text = "License file not found. See https://github.com/threedlite/classicsviewer/blob/main/LICENSE.txt"
            print(f"  Warning: LICENSE.txt not found at {license_path}")

        # Add source attribution
        license_url = "https://github.com/threedlite/classicsviewer/blob/main/LICENSE.txt"
        build_date = datetime.now().strftime("%Y-%m-%d")

        # Convert to HTML paragraphs
        paragraphs = []
        for para in license_text.split('\n\n'):
            para = para.strip()
            if para:
                if para.startswith('==='):
                    paragraphs.append('<hr/>')
                else:
                    paragraphs.append(f'<p class="license-text">{html.escape(para)}</p>')

        content = f'''<div class="license-page">
<p class="license-source">Source: <a href="{license_url}">{license_url}</a><br/>Retrieved: {build_date}</p>
{''.join(paragraphs)}
</div>'''

        return self.wrap_xhtml('License', content, work['title'])

    def wrap_xhtml(self, title: str, content: str, work_title: str, author_name: str = None, book_label: str = None) -> str:
        """Wrap content in XHTML document structure.

        Args:
            title: Page title (for <title> and <h1>)
            content: HTML content
            work_title: Work title (e.g., "Iliad")
            author_name: Author name (e.g., "Homer")
            book_label: Book/chapter label (e.g., "Book 1")
        """
        # Build header showing author and work (not book - that goes in h1)
        header_html = ''
        if author_name:
            header_parts = [html.escape(author_name), html.escape(work_title)]
            header_html = f'<p class="page-header">{" — ".join(header_parts)}</p>'

        h1_html = f'<h1>{html.escape(title)}</h1>'

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="grc">
<head>
  <meta charset="UTF-8"/>
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
{header_html}
{h1_html}
{content}
</body>
</html>'''

    def generate_opf(self, work: dict, manifest_items: list, spine_items: list) -> str:
        """Generate content.opf package file."""
        from datetime import timezone
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        manifest_xml = '\n    '.join([
            f'<item id="{id}" href="{href}" media-type="{mt}"/>'
            for id, href, mt in manifest_items
        ])
        manifest_xml += '\n    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        manifest_xml += '\n    <item id="css" href="styles/main.css" media-type="text/css"/>'
        manifest_xml += '\n    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'

        # Build spine: title first, then nav (TOC), then content
        spine_parts = []
        # Title page first (if in spine_items)
        if 'title' in spine_items:
            spine_parts.append('<itemref idref="title"/>')
            spine_items = [s for s in spine_items if s != 'title']
        # Then nav/TOC
        spine_parts.append('<itemref idref="nav"/>')
        # Then remaining content (books, dictionary)
        for id in spine_items:
            spine_parts.append(f'<itemref idref="{id}"/>')
        spine_xml = '\n    '.join(spine_parts)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">classicsviewer-{work['id']}</dc:identifier>
    <dc:title>{html.escape(work['title'])}</dc:title>
    <dc:creator>{html.escape(work['author_name'])}</dc:creator>
    <dc:language>grc</dc:language>
    <dc:publisher>Classics Viewer</dc:publisher>
    <dc:date>{now}</dc:date>
    <meta property="dcterms:modified">{now}</meta>
  </metadata>
  <manifest>
    {manifest_xml}
  </manifest>
  <spine toc="ncx">
    {spine_xml}
  </spine>
  <guide>
    <reference type="toc" title="Table of Contents" href="nav.xhtml"/>
  </guide>
</package>'''

    def generate_ncx(self, work: dict, nav_items: list) -> str:
        """Generate toc.ncx for legacy readers."""
        nav_points = []
        for i, (id, href, label) in enumerate(nav_items, 1):
            nav_points.append(f'''    <navPoint id="{id}" playOrder="{i}">
      <navLabel><text>{html.escape(label)}</text></navLabel>
      <content src="{href}"/>
    </navPoint>''')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="classicsviewer-{work['id']}"/>
  </head>
  <docTitle><text>{html.escape(work['title'])}</text></docTitle>
  <navMap>
{chr(10).join(nav_points)}
  </navMap>
</ncx>'''

    def generate_nav(self, work: dict, nav_items: list) -> str:
        """Generate nav.xhtml for ePub3."""
        nav_list = '\n      '.join([
            f'<li><a href="{href}">{html.escape(label)}</a></li>'
            for id, href, label in nav_items
        ])

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <meta charset="UTF-8"/>
  <title>Table of Contents</title>
  <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
  <nav epub:type="toc">
    <h1>Table of Contents</h1>
    <ol>
      {nav_list}
    </ol>
  </nav>
</body>
</html>'''

    def generate_dictionary_pages(self) -> dict:
        """Generate multiple dictionary xhtml files, split by first letter.

        Returns dict of filename -> content for smaller, faster-loading pages.
        """
        # Group entries by first letter
        entries_by_file = {}
        for word_id, entry in self.dictionary.items():
            word = entry['word']
            dict_file = self.get_dict_file_for_word(word)
            if dict_file not in entries_by_file:
                entries_by_file[dict_file] = []
            entries_by_file[dict_file].append((word_id, entry))

        # Generate each dictionary file
        dict_files = {}
        for dict_file, entries in entries_by_file.items():
            # Sort entries by word
            sorted_entries = sorted(entries, key=lambda x: x[1]['word'])

            entries_html = []
            for word_id, entry in sorted_entries:
                word = entry['word']
                lemma = entry['lemma']
                gloss = entry.get('gloss', '')

                # Get morphological info if available
                morph = self.word_to_morph.get(word, '')

                # Get full dictionary entries for the lemma
                dict_entries = self.get_dictionary_entries(lemma)

                # Build the entry HTML
                entry_html = [f'<div class="dict-entry" id="{word_id}">']
                entry_html.append(f'<h2 class="dict-word">{html.escape(word)}</h2>')

                if morph:
                    entry_html.append(f'<p class="dict-morph">{html.escape(morph)}</p>')

                if lemma and lemma != word:
                    entry_html.append(f'<p class="dict-lemma">Lemma: <strong>{html.escape(lemma)}</strong></p>')

                if dict_entries:
                    for de in dict_entries:
                        source = de['source'].upper()
                        text = de['text'] or ''
                        entry_html.append(f'<div class="dict-def">')
                        entry_html.append(f'<span class="dict-source">[{html.escape(source)}]</span> ')
                        entry_html.append(f'<span class="dict-text">{html.escape(text)}</span>')
                        entry_html.append(f'</div>')
                elif gloss:
                    entry_html.append(f'<p class="dict-gloss-fallback">{html.escape(gloss)}</p>')
                else:
                    entry_html.append(f'<p class="dict-no-entry">No dictionary entry found.</p>')

                entry_html.append('</div>')
                entries_html.append('\n'.join(entry_html))

            # Get display letter for title
            if sorted_entries:
                first_word = sorted_entries[0][1]['word']
                display_letter = first_word[0].upper() if first_word else '?'
            else:
                display_letter = '?'

            dict_files[dict_file] = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="grc">
<head>
  <meta charset="UTF-8"/>
  <title>Dictionary - {display_letter}</title>
  <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
<h1>Dictionary - {display_letter}</h1>
<p class="dict-note">Use your device's back button to return to the text.</p>
{chr(10).join(entries_html)}
</body>
</html>'''

        return dict_files


def main():
    import csv

    parser = argparse.ArgumentParser(description='Generate Kindle-optimized ePub from Classics Viewer database')
    parser.add_argument('--db', required=True, help='Path to SQLite database')
    parser.add_argument('--work', help='Work ID (e.g., tlg0012.tlg001) for single work mode')
    parser.add_argument('--csv', help='CSV file with Author,Work columns (same format as SAMPLE_AUTHORS.csv)')
    parser.add_argument('--books', type=int, nargs='+', help='Book numbers to include (default: all)')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--output-name', help='Output filename (default: auto-generated)')

    args = parser.parse_args()

    if not args.work and not args.csv:
        parser.error('Either --work or --csv is required')

    generator = KindleEpubGenerator(args.db, args.output_dir)

    if args.csv:
        # Batch mode: read CSV and generate ePub for each entry
        conn = generator.connect_db()
        cur = conn.cursor()

        with open(args.csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            entries = list(reader)

        print(f"Processing {len(entries)} works from {args.csv}")
        successful = 0
        failed = []

        for i, row in enumerate(entries, 1):
            author_name = row['Author'].strip()
            work_title = row['Work'].strip()

            # Look up work_id from database
            cur.execute("""
                SELECT w.id, w.title, w.title_english, a.name
                FROM works w
                JOIN authors a ON w.author_id = a.id
                WHERE a.name = ? AND w.title = ?
            """, (author_name, work_title))
            result = cur.fetchone()

            if not result:
                # Try case-insensitive match
                cur.execute("""
                    SELECT w.id, w.title, w.title_english, a.name
                    FROM works w
                    JOIN authors a ON w.author_id = a.id
                    WHERE LOWER(a.name) = LOWER(?) AND LOWER(w.title) = LOWER(?)
                """, (author_name, work_title))
                result = cur.fetchone()

            if not result:
                # Try matching on title_english (for works with non-English titles)
                cur.execute("""
                    SELECT w.id, w.title, w.title_english, a.name
                    FROM works w
                    JOIN authors a ON w.author_id = a.id
                    WHERE a.name = ? AND w.title_english = ?
                """, (author_name, work_title))
                result = cur.fetchone()

            if not result:
                # Try case-insensitive match on title_english
                cur.execute("""
                    SELECT w.id, w.title, w.title_english, a.name
                    FROM works w
                    JOIN authors a ON w.author_id = a.id
                    WHERE LOWER(a.name) = LOWER(?) AND LOWER(w.title_english) = LOWER(?)
                """, (author_name, work_title))
                result = cur.fetchone()

            if not result:
                print(f"[{i}/{len(entries)}] SKIP: '{work_title}' by {author_name} not found in database")
                failed.append(f"{author_name} - {work_title}")
                continue

            work_id, db_title, db_title_english, db_author = result

            # Generate output filename: prefer English title, fall back to original
            display_title = db_title_english if db_title_english else db_title
            safe_title = re.sub(r'[^\w\s-]', '', display_title).strip().replace(' ', '_')
            output_name = f"{safe_title}_ClassicsViewer.epub"

            print(f"\n[{i}/{len(entries)}] Generating: {output_name}")
            print(f"  Work: {db_title} by {db_author}")
            print(f"  ID: {work_id}")

            try:
                # Reset dictionary for each work
                generator.dictionary = {}
                generator.create_epub(work_id, None, output_name)
                successful += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                failed.append(f"{author_name} - {work_title}: {e}")

        conn.close()

        print(f"\n{'='*50}")
        print(f"Completed: {successful}/{len(entries)} ePubs generated")
        if failed:
            print(f"Failed ({len(failed)}):")
            for f in failed:
                print(f"  - {f}")
    else:
        # Single work mode
        generator.create_epub(args.work, args.books, args.output_name)


if __name__ == '__main__':
    main()
