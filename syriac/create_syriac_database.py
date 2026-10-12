#!/usr/bin/env python3
"""
Create Syriac database for ClassicsViewer

Source: Patristic Text Archive (PTA) - https://pta.bbaw.de
        Digital Syriac Corpus - https://syriaccorpus.org

License: Only CC-BY 4.0 and CC-BY-SA 4.0 licensed texts are included.
Excluded: ETCBC Peshitta texts (CC-BY-NC 4.0)

Included texts:
  - Syriac New Testament (Digital Syriac Corpus) - CC-BY 4.0
  - John of Ephesus, Ecclesiastical History - CC-BY-SA 4.0
  - Athanasius, Biblical Excerpts (Syriac) - CC-BY-SA 4.0

Lexicon: the Classical Syriac entries of the English Wiktionary (CC BY-SA 3.0),
read from data-sources/enwiktionary-latest-pages-articles.xml.bz2 and cached
in all_syriac_enwiktionary_pages.json. See "Classical Syriac lexicon" below.

Usage:
  python3 create_syriac_database.py
"""

import sqlite3
import re
import os
import zipfile
from xml.etree import ElementTree as ET
import html
import json
import bz2
import time
import unicodedata
import urllib.parse
from collections import defaultdict

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PTA_DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data-sources", "pta_data", "data")
DB_PATH = os.path.join(SCRIPT_DIR, "syriac_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "syriac_texts.db.zip")

# TEI namespace
TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}


def create_database(db_path):
    """Create the database schema (matches Greek/Latin/Coptic schema exactly)"""
    print(f"Creating database: {db_path}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same schema as other language databases)
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
        CREATE TABLE milestone_line_ranges (
            work_id TEXT,
            milestone TEXT,
            start_line INTEGER,
            end_line INTEGER,
            PRIMARY KEY (work_id, milestone)
        )
    ''')

    cursor.execute('''
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE normalization_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            pattern TEXT NOT NULL,
            replacement TEXT NOT NULL,
            description TEXT,
            priority INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE prefix_assimilation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            base_prefix TEXT NOT NULL,
            assimilated_form TEXT NOT NULL,
            meaning TEXT,
            phonological_rule TEXT,
            priority INTEGER NOT NULL,
            examples TEXT
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
    print("Creating indexes...")
    cursor.execute('CREATE INDEX idx_authors_language ON authors(language)')
    cursor.execute('CREATE INDEX idx_works_author ON works(author_id)')
    cursor.execute('CREATE INDEX idx_books_work ON books(work_id)')
    cursor.execute('CREATE INDEX idx_text_lines_book ON text_lines(book_id)')
    cursor.execute('CREATE INDEX idx_text_lines_sequence ON text_lines(book_id, sequence_number)')
    cursor.execute('CREATE INDEX idx_words_word ON words(word)')
    cursor.execute('CREATE INDEX idx_words_book_line_seq ON words(book_id, line_number, sequence_number)')
    cursor.execute('CREATE INDEX idx_translation_segments_book ON translation_segments(book_id)')
    cursor.execute('CREATE INDEX idx_translation_segments_lines ON translation_segments(book_id, start_line)')
    cursor.execute('CREATE INDEX idx_dictionary_headword ON dictionary_entries(headword, language)')
    cursor.execute('CREATE INDEX idx_dictionary_headword_ultra ON dictionary_entries(headword_normalized_ultra, language)')
    cursor.execute('CREATE INDEX idx_lemma_map_word ON lemma_map(word_form)')
    cursor.execute('CREATE INDEX idx_lemma_map_word_ultra ON lemma_map(word_form_normalized_ultra)')
    cursor.execute('CREATE INDEX idx_lemma_map_lemma ON lemma_map(lemma)')
    cursor.execute('CREATE INDEX idx_normalization_language ON normalization_patterns(language, priority)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_language ON prefix_assimilation_rules(language)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_base ON prefix_assimilation_rules(base_prefix)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_form ON prefix_assimilation_rules(assimilated_form)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_lang_priority ON prefix_assimilation_rules(language, priority)')
    cursor.execute('CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)')
    cursor.execute('CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)')

    conn.commit()
    return conn


def find_syriac_files(pta_dir):
    """Find all compatible Syriac TEI files in PTA"""
    syriac_files = []

    if not os.path.exists(pta_dir):
        raise FileNotFoundError(f"PTA data directory not found: {pta_dir}")

    # Walk through PTA data directory
    for root, dirs, files in os.walk(pta_dir):
        for filename in files:
            if 'syc' in filename and filename.endswith('.xml'):
                filepath = os.path.join(root, filename)

                # Check license in file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read(5000)  # Read first 5KB for license check

                    # Only include CC-BY 4.0 or CC-BY-SA 4.0, exclude CC-BY-NC
                    if 'by-nc' in content.lower():
                        continue
                    if 'creativecommons.org/licenses/by/4.0' in content or \
                       'creativecommons.org/licenses/by-sa/4.0' in content:
                        syriac_files.append(filepath)
                except Exception as e:
                    print(f"  Error checking {filepath}: {e}")

    return sorted(syriac_files)


# Elements whose text is not part of the running text: editorial and marginal
# notes, rejected apparatus readings (<rdg>; the accepted <lem> is kept) and
# erased text. <ref> and <bibl> stay: in the PTA files they wrap quoted
# scripture and work titles inside the sentence (the Syriac editions' <ref>s
# are empty markers).
TEXT_EXCLUDED_TAGS = {'note', 'rdg', 'del'}


def _local(tag):
    return tag.split('}')[-1] if '}' in tag else tag


def get_text_content(element):
    """Running text of an element: text of every descendant except the
    TEXT_EXCLUDED_TAGS (whose tails are still kept)."""
    text_parts = []
    if element.text:
        text_parts.append(element.text)
    for child in element:
        if _local(child.tag) not in TEXT_EXCLUDED_TAGS:
            text_parts.append(get_text_content(child))
        if child.tail:
            text_parts.append(child.tail)
    return ''.join(text_parts)


# A sentence ends at a full stop or the Syriac end-of-paragraph mark (U+0700).
SENTENCE_END = re.compile(r'(?<=[.\u0700])\s+')


def split_sentences(text):
    """Split a paragraph into sentence lines; pieces without a word are dropped."""
    text = ' '.join(text.split())
    return [s for s in (piece.strip() for piece in SENTENCE_END.split(text)) if re.search(r'\w', s)]


def _textpart_leaves(container):
    """Leaf <div type="textpart"> elements under container, in document order,
    each with the (subtype, n) path of its textpart ancestors including itself."""
    leaves = []

    def walk(elem, path):
        for child in elem:
            if _local(child.tag) != 'div':
                continue
            if child.get('type') == 'textpart':
                child_path = path + [(child.get('subtype') or 'part', child.get('n') or '')]
                if any(d.get('type') == 'textpart' for d in child.iter('{%s}div' % TEI_NS['tei']) if d is not child):
                    walk(child, child_path)
                else:
                    leaves.append((child_path, child))
            else:
                walk(child, path)

    walk(container, [])
    return leaves


def _path_key(path):
    return '_'.join(n for _, n in path)


def _path_label(path):
    return ' '.join(f"{subtype.capitalize()} {n}" for subtype, n in path)


def _paragraph_texts(div):
    return [txt for txt in (get_text_content(p).strip() for p in div.iter('{%s}p' % TEI_NS['tei'])) if txt]


def parse_tei_file(filepath):
    """Parse a TEI XML file and extract structured data"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Extract metadata
    meta = {}

    # Get title
    title_elem = root.find('.//tei:title', TEI_NS)
    if title_elem is not None:
        meta['title'] = get_text_content(title_elem).strip()

    # Get author
    author_elem = root.find('.//tei:author', TEI_NS)
    if author_elem is not None:
        persname = author_elem.find('.//tei:persName', TEI_NS)
        if persname is not None:
            meta['author'] = get_text_content(persname).strip()
        else:
            meta['author'] = get_text_content(author_elem).strip()

    # Get URN
    idno_elem = root.find('.//tei:idno[@type="PTA"]', TEI_NS)
    if idno_elem is not None and idno_elem.text:
        meta['urn'] = idno_elem.text.strip()

    # Get license
    licence_elem = root.find('.//tei:licence', TEI_NS)
    if licence_elem is not None:
        meta['license'] = licence_elem.get('target', '')

    # Extract text content organized by chapters/verses
    chapters = []

    # Find the edition div
    edition_div = root.find('.//tei:div[@type="edition"]', TEI_NS)
    if edition_div is None:
        edition_div = root.find('.//tei:body', TEI_NS)

    if edition_div is not None and edition_div.find('.//tei:div[@subtype="verse"]', TEI_NS) is not None:
        # Biblical structure: chapters with verses, one verse per line.
        for chapter_div in edition_div.findall('.//tei:div[@subtype="chapter"]', TEI_NS):
            chapter_num = chapter_div.get('n', '1')
            verses = []

            # Find verses within chapter
            for verse_div in chapter_div.findall('.//tei:div[@subtype="verse"]', TEI_NS):
                verse_num = verse_div.get('n', '1')

                # Get verse text from <p> elements or direct content
                verse_text = ''
                for p in verse_div.findall('.//tei:p', TEI_NS):
                    verse_text += get_text_content(p).strip() + ' '
                if not verse_text.strip():
                    verse_text = get_text_content(verse_div).strip()

                if verse_text.strip():
                    verses.append({
                        'verse_num': verse_num,
                        'text': verse_text.strip()
                    })

            if verses:
                chapters.append({
                    'chapter_num': chapter_num,
                    'label': f"Chapter {chapter_num}",
                    'verses': verses
                })
    elif edition_div is not None:
        # Prose editions (PTA): every leaf textpart div (a chapter, a section,
        # a testimonium ...) becomes a book whose id and label carry the whole
        # path, e.g. "3_1_3" / "Part 3 Book 1 Chapter 3", so that the same
        # chapter number in different books cannot collide. Its paragraphs
        # are split into sentence lines, as the Greek loader does for PTA.
        for path, leaf in _textpart_leaves(edition_div):
            lines = [s for txt in _paragraph_texts(leaf) for s in split_sentences(txt)]
            if lines:
                chapters.append({
                    'chapter_num': _path_key(path),
                    'label': _path_label(path),
                    'verses': [{'verse_num': str(i), 'text': s} for i, s in enumerate(lines, 1)]
                })

    return {
        'meta': meta,
        'chapters': chapters,
        'filepath': filepath
    }


# ---------------------------------------------------------------------------
# PTA English translations. The work's __cts__.xml lists every translation
# with a dct:relation naming the edition it translates; an English (eng/en)
# translation of one of our Syriac editions, under CC BY / CC BY-SA, is
# imported as one translation segment per leaf textpart div, matched to the
# Syriac book with the same (subtype, n) path. A translated passage with no
# matching Syriac book fails the build: it means the two files are not
# structured alike and the matching needs attention, not silence.
# ---------------------------------------------------------------------------

CTS_NS = {
    'ti': 'http://chs.harvard.edu/xmlns/cts',
    'dct': 'http://purl.org/dc/terms/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'cpt': 'http://purl.org/capitains/ns/1.0#',
}
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
ALLOWED_LICENCES = ('creativecommons.org/licenses/by/4.0', 'creativecommons.org/licenses/by-sa/4.0')


def find_pta_translations(syc_filepath):
    """English translations of this edition: list of (path, translator)."""
    work_dir = os.path.dirname(syc_filepath)
    edition_id = os.path.basename(syc_filepath)[:-4]          # pta0200.pta001.pta-syc1
    cts_path = os.path.join(work_dir, '__cts__.xml')
    if not os.path.exists(cts_path):
        return []
    root = ET.parse(cts_path).getroot()
    found = []
    for trans in root.findall('ti:translation', CTS_NS):
        if trans.get(XML_LANG) not in ('eng', 'en'):
            continue
        relations = [r.text.strip() for r in trans.findall('.//dct:relation', CTS_NS) if r.text]
        if not any(rel.endswith(':' + edition_id) for rel in relations):
            continue
        urn = trans.get('urn', '')
        path = os.path.join(work_dir, urn.split(':')[-1] + '.xml')
        if not os.path.exists(path):
            raise FileNotFoundError(f"{cts_path} lists translation {urn} but {path} is missing")
        rights = trans.find('.//dc:rights', CTS_NS)
        rights_text = (rights.text or '') if rights is not None else ''
        if not any(lic in rights_text for lic in ALLOWED_LICENCES) or 'by-nc' in rights_text:
            print(f"    Translation {urn} skipped: licence {rights_text!r}")
            continue
        creator = trans.find('.//dc:creator', CTS_NS)
        translator = ' '.join((creator.text or '').split()) if creator is not None else 'Patristic Text Archive'
        found.append((path, translator))
    return found


def parse_pta_translation(filepath):
    """{path key: translated text} for every leaf textpart div with text."""
    root = ET.parse(filepath).getroot()
    container = root.find('.//tei:div[@type="translation"]', TEI_NS)
    if container is None:
        container = root.find('.//tei:body', TEI_NS)
    segments = {}
    for path, leaf in _textpart_leaves(container):
        paragraphs = [' '.join(txt.split()) for txt in _paragraph_texts(leaf)]
        if paragraphs:
            segments[_path_key(path)] = '\n\n'.join(paragraphs)
    return segments


def import_pta_translations(cursor, syc_filepath, books_by_key, stats):
    """Insert translation segments for the books of one Syriac edition.

    books_by_key: {path key: (book_id, line_count)} of the books just inserted.
    Returns the number of segments inserted."""
    inserted = 0
    for trans_path, translator in find_pta_translations(syc_filepath):
        segments = parse_pta_translation(trans_path)
        missing = sorted(k for k in segments if k not in books_by_key)
        if missing:
            raise RuntimeError(
                f"{os.path.basename(trans_path)}: {len(missing)} translated passages have no "
                f"matching Syriac book in {os.path.basename(syc_filepath)}: {missing[:10]}")
        for key, text in segments.items():
            book_id, line_count = books_by_key[key]
            cursor.execute('''
                INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
            ''', (book_id, 1, line_count, 1, text, translator))
            segment_id = cursor.lastrowid
            cursor.executemany(
                'INSERT INTO translation_lookup (book_id, line_number, segment_id) VALUES (?, ?, ?)',
                [(book_id, n, segment_id) for n in range(1, line_count + 1)])
            inserted += 1
        print(f"    Translation {os.path.basename(trans_path)}: {len(segments)} passages ({translator})")
    stats['translations'] += inserted
    return inserted


def make_safe_id(text):
    """Convert text to safe ID"""
    # An empty or "Unknown" name gets a language-specific id: the merge keys
    # authors, works and books by id across every module, and the bare
    # 'unknown' that both this script and the Coptic one produced for an
    # unnamed author collided (nine Coptic works were listed under a Syriac
    # author until 2026-10-12).
    if not text:
        return 'unknown_syriac'
    safe = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')
    if safe in ('', 'unknown'):
        return 'unknown_syriac'
    return safe


def tokenize_syriac(text):
    """Tokenize Syriac text into words"""
    # Remove punctuation but keep Syriac characters
    # Syriac Unicode range: U+0700-U+074F
    words = text.split()
    # Clean each word
    cleaned = []
    for word in words:
        # Keep only Syriac letters and common diacritics
        clean = re.sub(r'[^\u0700-\u074F\u0308\u0323]', '', word)
        if clean:
            cleaned.append(clean)
    return cleaned


# Book name mappings for Syriac NT - maps work folder codes to English names
# Path structure: pta9999/pta063/... where pta063 is the work code
SYRIAC_NT_BOOKS = {
    'pta063': ('matthew', 'Matthew', 'Gospel of Matthew'),
    'pta064': ('mark', 'Mark', 'Gospel of Mark'),
    'pta065': ('luke', 'Luke', 'Gospel of Luke'),
    'pta066': ('john', 'John', 'Gospel of John'),
    'pta067': ('acts', 'Acts', 'Acts of the Apostles'),
    'pta068': ('romans', 'Romans', 'Epistle to the Romans'),
    'pta069': ('1corinthians', '1 Corinthians', 'First Epistle to the Corinthians'),
    'pta070': ('2corinthians', '2 Corinthians', 'Second Epistle to the Corinthians'),
    'pta071': ('galatians', 'Galatians', 'Epistle to the Galatians'),
    'pta072': ('ephesians', 'Ephesians', 'Epistle to the Ephesians'),
    'pta073': ('philippians', 'Philippians', 'Epistle to the Philippians'),
    'pta074': ('colossians', 'Colossians', 'Epistle to the Colossians'),
    'pta075': ('1thessalonians', '1 Thessalonians', 'First Epistle to the Thessalonians'),
    'pta076': ('2thessalonians', '2 Thessalonians', 'Second Epistle to the Thessalonians'),
    'pta077': ('1timothy', '1 Timothy', 'First Epistle to Timothy'),
    'pta078': ('2timothy', '2 Timothy', 'Second Epistle to Timothy'),
    'pta079': ('titus', 'Titus', 'Epistle to Titus'),
    'pta080': ('philemon', 'Philemon', 'Epistle to Philemon'),
    'pta081': ('hebrews', 'Hebrews', 'Epistle to the Hebrews'),
    'pta082': ('james', 'James', 'Epistle of James'),
    'pta083': ('1peter', '1 Peter', 'First Epistle of Peter'),
    'pta084': ('2peter', '2 Peter', 'Second Epistle of Peter'),
    'pta085': ('1john', '1 John', 'First Epistle of John'),
    'pta086': ('2john', '2 John', 'Second Epistle of John'),
    'pta087': ('3john', '3 John', 'Third Epistle of John'),
    'pta088': ('jude', 'Jude', 'Epistle of Jude'),
    'pta089': ('revelation', 'Revelation', 'Revelation of John'),
}


def populate_database(conn, syriac_files):
    """Populate database with parsed Syriac files"""
    cursor = conn.cursor()

    # Statistics
    stats = {
        'authors': 0,
        'works': 0,
        'books': 0,
        'lines': 0,
        'words': 0,
        'translations': 0
    }

    authors_inserted = set()
    works_processed = set()

    print(f"\nProcessing {len(syriac_files)} Syriac files...")

    # Group files by work
    for filepath in syriac_files:
        print(f"  Processing: {os.path.basename(filepath)}")

        data = parse_tei_file(filepath)   # a parse error fails the build

        meta = data['meta']
        chapters = data['chapters']

        if not chapters:
            print(f"    No content found in {filepath}")
            continue

        # Determine author and work from filepath
        filename = os.path.basename(filepath)
        path_parts = filepath.split(os.sep)

        # Check if it's a NT book - look for work-level pta code under pta9999 (NT author)
        # Path structure: .../pta9999/pta063/... where pta9999 is the NT author and pta063 is the work code
        # CRITICAL: Must verify author-level code is pta9999 to avoid confusing
        # non-NT works that share the same work code (e.g., pta0001/pta073 is Severianus,
        # NOT the Epistle to the Philippians which is pta9999/pta073)
        pta_codes = []
        for part in path_parts:
            if part.startswith('pta') and len(part) > 3 and part[3:].isdigit():
                pta_codes.append(part)

        # NT books must be under pta9999 (author) / ptaXXX (work)
        pta_author_code = pta_codes[0] if len(pta_codes) >= 2 else None
        pta_work_code = pta_codes[-1] if pta_codes else None
        is_nt = pta_author_code == 'pta9999' and pta_work_code in SYRIAC_NT_BOOKS

        if is_nt:
            # Syriac New Testament book
            work_id_base, work_title, work_desc = SYRIAC_NT_BOOKS[pta_work_code]
            author_id = 'syriac_nt'
            author_name = 'Syriac New Testament'

            if author_id not in authors_inserted:
                cursor.execute('''
                    INSERT OR IGNORE INTO authors (id, name, name_alt, language, has_translations)
                    VALUES (?, ?, ?, ?, ?)
                ''', (author_id, author_name, 'Peshitta NT', 'syriac', 0))
                authors_inserted.add(author_id)
                stats['authors'] += 1

            work_id = f"syriac_nt_{work_id_base}"
        else:
            # Other Syriac work (John of Ephesus, Athanasius, etc.)
            author_name = meta.get('author', 'Unknown')
            author_id = make_safe_id(author_name)

            if author_id not in authors_inserted:
                cursor.execute('''
                    INSERT OR IGNORE INTO authors (id, name, name_alt, language, has_translations)
                    VALUES (?, ?, ?, ?, ?)
                ''', (author_id, author_name, None, 'syriac', 0))
                authors_inserted.add(author_id)
                stats['authors'] += 1

            work_title = meta.get('title', 'Unknown Work')
            work_desc = work_title
            work_id = make_safe_id(f"{author_id}_{meta.get('urn', work_title)}")

        # Create work if not exists
        if work_id not in works_processed:
            cursor.execute('''
                INSERT OR IGNORE INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                work_id,
                author_id,
                work_title,
                meta.get('title'),
                work_desc,
                'prose',
                meta.get('urn'),
                f"License: {meta.get('license', 'CC-BY 4.0')}"
            ))
            works_processed.add(work_id)
            stats['works'] += 1

        # Process chapters as books. NT chapters are numbered by their chapter
        # number; prose books (one per leaf textpart div) by document order.
        books_by_key = {}
        for book_index, chapter_data in enumerate(chapters, 1):
            chapter_num = chapter_data['chapter_num']
            book_number = int(chapter_num) if is_nt and chapter_num.isdigit() else book_index
            book_id = f"{work_id}.{chapter_num}"

            verses = chapter_data['verses']
            line_count = len(verses)

            cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
            if cursor.fetchone():
                raise RuntimeError(f"duplicate book id {book_id} in {filepath}")

            cursor.execute('''
                INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (book_id, work_id, book_number, chapter_data['label'], 1, line_count, line_count))
            stats['books'] += 1
            books_by_key[chapter_num] = (book_id, line_count)

            # Insert verses as lines
            for seq_num, verse in enumerate(verses, 1):
                verse_text = verse['text']

                cursor.execute('''
                    INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, seq_num, seq_num, verse_text))
                stats['lines'] += 1

                # Insert words
                words = tokenize_syriac(verse_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word, book_id, seq_num, seq_num, word_pos))
                    stats['words'] += 1

        print(f"    Added {len(chapters)} chapters")

        if not is_nt:
            import_pta_translations(cursor, filepath, books_by_key, stats)

    # Same rule as the other modules: a human translation marks the author.
    cursor.execute('''
        UPDATE authors SET has_translations = 1 WHERE id IN (
            SELECT DISTINCT w.author_id FROM works w
            JOIN books b ON b.work_id = w.id
            JOIN translation_segments ts ON ts.book_id = b.id
            WHERE LENGTH(TRIM(ts.translation_text)) > 10)
    ''')
    conn.commit()
    return stats


# ---------------------------------------------------------------------------
# Classical Syriac lexicon from the English Wiktionary (CC BY-SA 3.0).
#
# The dump is scanned once for every page with a "==Classical Syriac==" section
# and a Syriac-script title; the pages are cached in WIKTIONARY_CACHE (git-
# ignored) so later builds skip the scan (4.3 min measured 2026-10-11). Each page's Classical
# Syriac section is parsed into part-of-speech senses with numbered
# definitions, headword transliteration and gender, inflection-of
# cross-references and the printed-dictionary references Wiktionary cites.
# ---------------------------------------------------------------------------

DATA_SOURCES_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data-sources")
WIKTIONARY_DUMP = os.path.join(DATA_SOURCES_DIR, "enwiktionary-latest-pages-articles.xml.bz2")
WIKTIONARY_CACHE = os.path.join(SCRIPT_DIR, "all_syriac_enwiktionary_pages.json")
LEXICON_SOURCE = "Wiktionary (syc)"   # registered to 'syriac' in shared/pack_layout.py
LEXICON_LANGUAGE = "syriac"

SYRIAC_LETTER = re.compile(r'[ܐ-ܯ]')
# Vowel points (East and West Syriac), qushshaya / rukkakha and the other
# reading marks, seyame and dots written as combining diacritics, Syriac
# punctuation and the abbreviation mark. None of these distinguish dictionary
# words, so the lookup key is the bare consonantal skeleton.
SYRIAC_MARKS = re.compile(r'[ܰ-݊̀-ͯ܀-܏]')

# Proclitic particles written together with the following word: ܘ "and",
# ܕ "of / that", ܒ "in", ܠ "to". ܘ may precede the others and ܕ may precede
# ܒ or ܠ. Tried in this order when a corpus form is not itself a headword.
SYRIAC_PROCLITICS = ['ܘ', 'ܕ', 'ܒ', 'ܠ', 'ܘܕ', 'ܘܒ', 'ܘܠ', 'ܕܒ', 'ܕܠ', 'ܘܕܒ', 'ܘܕܠ']

POS_HEADERS = {
    'Noun', 'Proper noun', 'Verb', 'Adjective', 'Adverb', 'Preposition',
    'Conjunction', 'Pronoun', 'Numeral', 'Interjection', 'Particle', 'Letter',
    'Determiner', 'Prefix', 'Suffix', 'Participle', 'Phrase', 'Contraction',
    'Proverb', 'Idiom', 'Symbol', 'Root',
}
GENDER_TOKENS = {'m', 'f', 'c', 'n', 'p', 'm-p', 'f-p', 'c-p', 'mf', 'm-s', 'f-s', 'mf-p'}
# Grammatical tags used by {{inflection of}}; expanded for display.
INFLECTION_TAGS = {
    's': 'singular', 'sg': 'singular', 'p': 'plural', 'pl': 'plural', 'du': 'dual',
    'm': 'masculine', 'f': 'feminine', 'c': 'common gender',
    'emph': 'emphatic', 'abs': 'absolute', 'cons': 'construct', 'def': 'definite',
    'act': 'active', 'pass': 'passive', 'ptcp': 'participle', 'part': 'participle',
    'perf': 'perfect', 'impf': 'imperfect', 'imp': 'imperative', 'inf': 'infinitive',
    '1': 'first-person', '2': 'second-person', '3': 'third-person',
    'poss': 'possessive', 'suf': 'suffix', 'obj': 'object',
}
FORM_OF_TEMPLATES = {
    'alt form', 'alt form of', 'alternative form of', 'alt sp', 'alt sp of',
    'alternative spelling of', 'spelling of', 'synonym of', 'syn of',
    'diminutive of', 'augmentative of', 'plural of', 'feminine of',
    'contraction of', 'abbreviation of', 'obsolete form of', 'archaic form of',
    'dated form of', 'rare form of', 'misspelling of', 'nonstandard form of',
    'standard form of', 'emphatic form of', 'absolute form of', 'construct form of',
}
DROP_TEMPLATES = {
    'cog', 'der', 'inh', 'bor', 'inh+', 'der+', 'bor+', 'lbor', 'desc', 'desctree',
    'etymon', 'cln', 'c', 'C', 'topics', 'catlangname', 'IPA', 'head', 'reflist',
    'rfdef', 'rfe', 'rfp', 'quote', 'quote-book', 'quote-text', 'ux', 'uxi',
    'syc-rootbox', 'etymid', 'senseid', 'anchor', 'attention', 'lang', 'nowrap',
    'table:gregorian calendar/syc', 'table:chess pieces/syc', 'col', 'col2',
    'col3', 'col4', 'der2', 'der3', 'rel2', 'rel3', 'syn', 'ant', 'synonyms',
    'antonyms', 'hyper', 'hypo', 'coord', 'n', 'ng-lite', 'taxlink',
}


def normalize_syriac(word):
    """Consonantal skeleton used as the lookup key (NFC, marks removed)."""
    return SYRIAC_MARKS.sub('', unicodedata.normalize('NFC', word))


def extract_syriac_wiktionary_pages():
    """Return {title: wikitext} for every English Wiktionary page with a
    Classical Syriac section, from the cache or by scanning the dump."""
    if os.path.exists(WIKTIONARY_CACHE):
        with open(WIKTIONARY_CACHE, encoding='utf-8') as f:
            pages = json.load(f)
        if not pages:
            raise RuntimeError(f"Wiktionary cache {WIKTIONARY_CACHE} is empty; delete it and rebuild")
        print(f"  Wiktionary cache: {len(pages):,} Classical Syriac pages ({os.path.basename(WIKTIONARY_CACHE)})")
        return pages

    if not os.path.exists(WIKTIONARY_DUMP):
        raise FileNotFoundError(
            f"English Wiktionary dump not found: {WIKTIONARY_DUMP}\n"
            f"  Download with: wget https://dumps.wikimedia.org/enwiktionary/latest/"
            f"enwiktionary-latest-pages-articles.xml.bz2 -P {DATA_SOURCES_DIR}")

    print(f"  Scanning {os.path.basename(WIKTIONARY_DUMP)} for Classical Syriac pages (about 5 minutes)...")
    pages = {}
    processed = 0
    start = time.time()
    with bz2.open(WIKTIONARY_DUMP, 'rt', encoding='utf-8', errors='ignore') as f:
        for event, elem in ET.iterparse(f, events=('end',)):
            if not elem.tag.endswith('}page'):
                continue
            processed += 1
            title = text = None
            for child in elem.iter():
                if child.tag.endswith('}title'):
                    title = child.text
                elif child.tag.endswith('}text'):
                    text = child.text
            if (title and ':' not in title and SYRIAC_LETTER.search(title)
                    and text and '==Classical Syriac==' in text):
                pages[title] = text
            elem.clear()
            if processed % 500000 == 0:
                print(f"    {processed:,} pages scanned, {len(pages):,} Classical Syriac pages, "
                      f"{(time.time() - start) / 60:.1f} min")
    if not pages:
        raise RuntimeError("No Classical Syriac pages found in the Wiktionary dump")
    tmp = WIKTIONARY_CACHE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False, indent=1)
    os.replace(tmp, WIKTIONARY_CACHE)
    print(f"  Scanned {processed:,} pages in {(time.time() - start) / 60:.1f} min; "
          f"cached {len(pages):,} Classical Syriac pages")
    return pages


def _split_template(body):
    """'name|a|b=c' -> (name, [positional...], {named...}); wiki links inside
    parameters are reduced to their display text first so their pipes do not
    split parameters."""
    body = re.sub(r'\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]', r'\1', body)
    parts = body.split('|')
    name = parts[0].strip()
    positional, named = [], {}
    for p in parts[1:]:
        if '=' in p:
            k, _, v = p.partition('=')
            named[k.strip()] = v.strip()
        else:
            positional.append(p.strip())
    return name, positional, named


def _first_syriac(params):
    for p in params:
        if SYRIAC_LETTER.search(p):
            return p
    return None


def _expand_tags(tags):
    out = []
    for t in tags:
        if not t or t == ';':
            continue
        out.append(INFLECTION_TAGS.get(t, t))
    return ' '.join(out)


def _render_template(body, cross_refs):
    """Display text for one (innermost) template. Inflection-of and
    form-of cross-references are also recorded in cross_refs as
    (kind, lemma, tags)."""
    name, positional, named = _split_template(body)
    lname = name.lower()
    if lname in ('lb', 'label', 'tlb'):
        labels = [p for p in positional[1:] if p and p != '_']
        return f"({', '.join(labels)})" if labels else ''
    if lname in ('l', 'm', 'link', 'mention', 'l-self', 'm-self', 'll'):
        word = positional[2] if len(positional) > 2 and positional[2] else (positional[1] if len(positional) > 1 else '')
        gloss = named.get('t') or named.get('gloss')
        return f"{word} ({gloss})" if word and gloss else (word or gloss or '')
    if lname in ('q', 'qual', 'qualifier', 'i', 'gloss', 'gl', 'sense', 'qq'):
        return f"({positional[0]})" if positional else ''
    if lname in ('ng', 'n-g', 'non-gloss', 'non-gloss definition', 'non gloss definition'):
        return positional[0] if positional else ''
    if lname == 'given name':
        gender = positional[1] if len(positional) > 1 else ''
        text = f"a {gender} given name" if gender in ('male', 'female', 'unisex') else 'a given name'
        if named.get('eq'):
            text += f", equivalent to {re.sub(r',\s*', ', ', named['eq'])}"
        return text
    if lname in ('surname',):
        return 'a surname'
    if lname in ('inflection of', 'infl of'):
        lemma = positional[1] if len(positional) > 1 else ''
        tags = _expand_tags(positional[3:])
        if lemma:
            cross_refs.append(('inflection', lemma, tags))
        return f"inflection of {lemma}" + (f": {tags}" if tags else '')
    if lname in FORM_OF_TEMPLATES:
        lemma = _first_syriac(positional[1:]) or (positional[1] if len(positional) > 1 else '')
        kind = re.sub(r'\s+of$', '', lname).replace('alt sp', 'alternative spelling').replace('alt form', 'alternative form')
        if lemma:
            cross_refs.append((kind, lemma, ''))
        return f"{kind} of {lemma}" if lemma else ''
    if lname in ('syc-root', 'root'):
        root = _first_syriac(positional) or ''
        return f"root {root}" if root else ''
    if lname in ('w', 'pedia', 'wikipedia', 'taxfmt', 'taxlink', 'vern', 'swp'):
        return positional[0] if positional else ''
    if lname in DROP_TEMPLATES or lname.startswith('syc-') or lname.startswith('R:'):
        return ''
    return named.get('t', '')


def clean_syriac_wikitext(text, cross_refs=None):
    """Reduce one line of wikitext to display text."""
    if cross_refs is None:
        cross_refs = []
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\{\{([^{}]*)\}\}', lambda m: _render_template(m.group(1), cross_refs), text)
    text = re.sub(r'\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]', r'\1', text)
    text = re.sub(r'<ref[^>]*/>', '', text)
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("'''", '').replace("''", '')
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[,;:\s]+|[,;:\s]+$', '', text)
    return text


def _render_reference(body):
    """'R:Payne Smith 1902|page=277b' -> 'Payne Smith 1902, p. 277b'."""
    name, positional, named = _split_template(body)
    if not name.startswith('R:'):
        return ''
    text = name[2:]
    text = re.sub(r'^[a-z]{2,3}:', '', text)      # R:syc:Brockelmann 1995
    text = text.replace(':', ' ')                 # R:syc:Nestle:1902
    if named.get('page'):
        text += f", p. {named['page']}"
    elif named.get('pages'):
        text += f", pp. {named['pages']}"
    if positional and positional[0]:
        key = urllib.parse.unquote(positional[0])
        # The CAL key is the lexicon's own ASCII transliteration (")" = alaph).
        text += f" s.v. {key}" if text.startswith('CAL') else f" ({key})"
    return text


def parse_classical_syriac_page(title, wikitext):
    """Parse the Classical Syriac section of one page.

    Returns {'senses': [{'pos', 'gender', 'tr', 'forms', 'defs'}],
             'cross_refs': [(kind, lemma, tags)], 'refs': [str]} or None."""
    m = re.search(r'^==Classical Syriac==\s*\n(.*?)(?=^==[^=]|\Z)', wikitext, re.S | re.M)
    if not m:
        return None
    section = m.group(1)
    senses, cross_refs, refs = [], [], []
    sense = None
    mode = 'other'
    for line in section.split('\n'):
        header = re.match(r'^(={3,6})\s*(.+?)\s*\1\s*$', line)
        if header:
            name = header.group(2).strip()
            if name in POS_HEADERS:
                sense = {'pos': name.lower(), 'gender': '', 'tr': '', 'forms': [], 'defs': []}
                senses.append(sense)
                mode = 'pos'
            elif name in ('References', 'Further reading'):
                mode = 'refs'
            else:
                mode = 'other'
            continue
        line = line.strip()
        if not line:
            continue
        if mode == 'pos' and sense is not None:
            if line.startswith('{{') and not sense['defs'] and not sense['tr'] and not sense['gender']:
                body = re.match(r'\{\{(.*)\}\}\s*$', line)
                if body:
                    name, positional, named = _split_template(body.group(1))
                    if name.startswith('syc-') or name == 'head':
                        for p in positional:
                            if p in GENDER_TOKENS:
                                sense['gender'] = p
                        sense['tr'] = named.get('tr', '')
                        for key, label in (('pl', 'plural'), ('f', 'feminine'), ('m', 'masculine'),
                                           ('p', 'plural'), ('cons', 'construct'), ('abs', 'absolute')):
                            value = named.get(key, '')
                            for form in re.split(r'\s*,\s*', value):
                                if form and SYRIAC_LETTER.search(form):
                                    sense['forms'].append((form, label))
                        continue
            d = re.match(r'^#\s*([^#*:].*)$', line)
            if d:
                text = clean_syriac_wikitext(d.group(1), cross_refs)
                if text:
                    sense['defs'].append(text)
        elif mode == 'refs':
            for body in re.findall(r'\{\{(R:[^{}]*)\}\}', line):
                ref = _render_reference(body)
                if ref and ref not in refs:
                    refs.append(ref)
    senses = [s for s in senses if s['defs']]
    if not senses and not cross_refs:
        return None
    return {'senses': senses, 'cross_refs': cross_refs, 'refs': refs}


def _is_lemma_definition(text):
    return not re.match(r'^(inflection|alternative (form|spelling)|spelling|synonym|diminutive|'
                        r'augmentative|plural|feminine|contraction|abbreviation|obsolete form|'
                        r'archaic form|dated form|rare form|misspelling|nonstandard form|'
                        r'standard form|emphatic form|absolute form|construct form) of ', text)


def render_syriac_entry(title, parsed):
    """(entry_html, entry_plain) for a page with at least one definition."""
    html_parts, plain_parts = [f"<b>{html.escape(title)}</b>"], [title]
    trs = [s['tr'] for s in parsed['senses'] if s['tr']]
    if trs:
        html_parts[0] += f" <i>{html.escape(trs[0])}</i>"
        plain_parts[0] += f" ({trs[0]})"
    for s in parsed['senses']:
        head = s['pos']
        if s['gender']:
            head += f" ({s['gender']})"
        if s['tr'] and s['tr'] != trs[0]:
            head += f" {s['tr']}"
        html_parts.append(f"<br><b>{html.escape(head)}</b><ol>" +
                          ''.join(f"<li>{html.escape(d)}</li>" for d in s['defs']) + "</ol>")
        plain_parts.append(head)
        plain_parts.extend(f"{i}. {d}" for i, d in enumerate(s['defs'], 1))
    if parsed['refs']:
        html_parts.append(f"<small>{html.escape('; '.join(parsed['refs']))}</small>")
        plain_parts.append('References: ' + '; '.join(parsed['refs']))
    return ''.join(html_parts), '\n'.join(plain_parts)


def build_syriac_lexicon(conn, pages):
    """Insert dictionary_entries and lemma_map rows for the Wiktionary
    Classical Syriac entries, then map every corpus word form (vowel-pointed
    or not, with or without a proclitic) onto the headwords it matches."""
    cursor = conn.cursor()
    parsed_pages = {}
    for title, text in pages.items():
        parsed = parse_classical_syriac_page(title, text)
        if parsed:
            parsed_pages[title] = parsed
    if not parsed_pages:
        raise RuntimeError("No Classical Syriac entries could be parsed from the Wiktionary pages")

    headwords = {}                       # title -> parsed (pages with definitions)
    by_skeleton = defaultdict(set)       # skeleton -> {headword}
    lemma_rows = {}                      # (word_form, lemma) -> (skeleton, confidence, morph_info)

    def add_mapping(form, lemma, confidence, morph_info):
        key = (form, lemma)
        if key not in lemma_rows or lemma_rows[key][1] < confidence:
            lemma_rows[key] = (normalize_syriac(form), confidence, morph_info)

    for title, parsed in parsed_pages.items():
        if any(_is_lemma_definition(d) for s in parsed['senses'] for d in s['defs']):
            headwords[title] = parsed
            by_skeleton[normalize_syriac(title)].add(title)
            add_mapping(title, title, 1.0, None)
            for s in parsed['senses']:
                for form, label in s['forms']:
                    add_mapping(form, title, 0.95, label)
        for kind, lemma, tags in parsed['cross_refs']:
            add_mapping(title, lemma, 0.95, (f"{kind}: {tags}" if tags else kind))

    n_defs = 0
    for title, parsed in headwords.items():
        entry_html, entry_plain = render_syriac_entry(title, parsed)
        n_defs += sum(len(s['defs']) for s in parsed['senses'])
        cursor.execute('''
            INSERT INTO dictionary_entries (headword, headword_normalized_ultra, language,
                                            entry_xml, entry_html, entry_plain, source)
            VALUES (?, ?, ?, NULL, ?, ?, ?)
        ''', (title, normalize_syriac(title), LEXICON_LANGUAGE, entry_html, entry_plain, LEXICON_SOURCE))

    # Cross-referenced forms also resolve by skeleton (ܐܒܗܐ -> ܐܒܐ).
    form_lemmas = defaultdict(set)
    for (form, lemma), (skeleton, confidence, morph_info) in list(lemma_rows.items()):
        if lemma in headwords and form not in headwords:
            form_lemmas[skeleton].add((lemma, morph_info))

    def lemmas_for_skeleton(skeleton):
        found = [(h, 0.9, None) for h in sorted(by_skeleton.get(skeleton, ()))]
        found += [(lemma, 0.85, morph) for lemma, morph in sorted(form_lemmas.get(skeleton, ()), key=str)]
        return found

    corpus_forms = cursor.execute('SELECT word, COUNT(*) FROM words GROUP BY word').fetchall()
    covered_tokens = total_tokens = 0
    for form, count in corpus_forms:
        total_tokens += count
        skeleton = normalize_syriac(form)
        if not skeleton:
            continue
        matches = lemmas_for_skeleton(skeleton)
        if not matches:
            for proclitic in SYRIAC_PROCLITICS:
                if skeleton.startswith(proclitic) and len(skeleton) > len(proclitic) + 1:
                    rest = lemmas_for_skeleton(skeleton[len(proclitic):])
                    if rest:
                        matches = [(lemma, min(conf, 0.7), f"with proclitic {proclitic}-" + (f"; {morph}" if morph else ''))
                                   for lemma, conf, morph in rest]
                        break
        if matches:
            covered_tokens += count
            for lemma, confidence, morph_info in matches:
                add_mapping(form, lemma, confidence, morph_info)

    cursor.executemany('''
        INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [(form, skeleton, lemma, confidence, LEXICON_SOURCE, morph_info)
          for (form, lemma), (skeleton, confidence, morph_info) in lemma_rows.items()])
    conn.commit()

    stats = {
        'wiktionary_pages': len(pages),
        'dictionary_entries': len(headwords),
        'definitions': n_defs,
        'lemma_map_rows': len(lemma_rows),
        'corpus_tokens': total_tokens,
        'corpus_tokens_covered': covered_tokens,
    }
    print(f"  Dictionary entries: {stats['dictionary_entries']:,} ({n_defs:,} definitions) "
          f"from {len(pages):,} Wiktionary pages")
    print(f"  Lemma map rows: {stats['lemma_map_rows']:,}")
    print(f"  Corpus coverage: {covered_tokens:,} of {total_tokens:,} word tokens "
          f"({100.0 * covered_tokens / max(total_tokens, 1):.1f}%) resolve to an entry")
    return stats


def compress_database(db_path, zip_path):
    """Compress database to ZIP"""
    print(f"\nCompressing database to {zip_path}...")

    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(db_path, os.path.basename(db_path))

    db_size = os.path.getsize(db_path) / (1024 * 1024)
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"  Database: {db_size:.2f} MB")
    print(f"  Compressed: {zip_size:.2f} MB")


def main():
    print("=" * 60)
    print("Creating Syriac Database")
    print("=" * 60)

    # Check data directory
    if not os.path.exists(PTA_DATA_DIR):
        print(f"\nERROR: PTA data directory not found: {PTA_DATA_DIR}")
        print("Please clone the PTA data repository:")
        print("  cd data-sources")
        print("  git clone https://github.com/PatristicTextArchive/pta_data.git")
        return 1

    # Find Syriac files
    print(f"\n--- Finding Syriac Files ---")
    print(f"Data directory: {PTA_DATA_DIR}")
    syriac_files = find_syriac_files(PTA_DATA_DIR)
    print(f"Found {len(syriac_files)} compatible Syriac files (CC-BY/CC-BY-SA)")

    if not syriac_files:
        print("ERROR: No compatible Syriac files found!")
        return 1

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate database
    print("\n--- Populating Database ---")
    stats = populate_database(conn, syriac_files)

    # Lexicon (fails the build if the dump/cache is missing or yields nothing)
    print("\n--- Classical Syriac Lexicon (English Wiktionary) ---")
    pages = extract_syriac_wiktionary_pages()
    stats.update(build_syriac_lexicon(conn, pages))

    conn.close()

    # Compress
    print("\n--- Compressing ---")
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE CREATION COMPLETE")
    print("=" * 60)
    print(f"Authors: {stats['authors']}")
    print(f"Works: {stats['works']}")
    print(f"Books/Chapters: {stats['books']}")
    print(f"Text lines: {stats['lines']}")
    print(f"Words: {stats['words']}")
    print(f"Translation segments (PTA English): {stats['translations']}")
    print(f"Dictionary entries: {stats['dictionary_entries']} (Wiktionary, {stats['definitions']} definitions)")
    print(f"Lemma map rows: {stats['lemma_map_rows']}")
    print(f"Corpus tokens with an entry: {stats['corpus_tokens_covered']} of {stats['corpus_tokens']}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
