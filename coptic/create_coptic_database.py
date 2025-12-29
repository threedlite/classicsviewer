#!/usr/bin/env python3
"""
Create Coptic Scriptorium database for ClassicsViewer

Sources:
  - Coptic SCRIPTORIUM corpus: https://github.com/CopticScriptorium/corpora.git
  - Comprehensive Coptic Lexicon: https://github.com/KELLIA/dictionary (CC-BY-SA 4.0)

License: Most documents are CC-BY 3.0/4.0 unless otherwise indicated.
Excluded corpora:
  - sahidica.mark, sahidica.1corinthians, sahidica.nt, coptic-treebank:
    J Warren Wells restricted license ("for academic use only")
  - life-aphou, life-longinus-lucius, life-paul-tamma, life-phib:
    CC-BY-NC (non-commercial) licenses

Usage:
  python3 create_coptic_database.py
"""

import sqlite3
import re
import os
import zipfile
from collections import defaultdict
import html
from xml.etree import ElementTree as ET

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data-sources", "corpora")
LEXICON_PATH = os.path.join(SCRIPT_DIR, "data-sources", "Comprehensive_Coptic_Lexicon-v1.2-2020.xml")
DB_PATH = os.path.join(SCRIPT_DIR, "coptic_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "coptic_texts.db.zip")

# TEI namespace
TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

# Corpora to exclude (restricted licenses)
EXCLUDED_CORPORA = {
    # J Warren Wells restricted license ("for academic use only")
    'sahidica.mark',
    'sahidica.1corinthians',
    'sahidica.nt',
    'coptic-treebank',
    # CC-BY-NC (non-commercial) licenses
    'life-aphou',
    'life-longinus-lucius',
    'life-paul-tamma',
    'life-phib',
}


def create_database(db_path):
    """Create the database schema (matches Greek/Latin/Sanskrit/Dante schema exactly)"""
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


def normalize_corpus_name(name):
    """Convert folder name to corpus ID"""
    # Remove hyphens and convert to lowercase
    return name.lower().replace('-', '.')


def find_tt_files(data_dir):
    """Find all TT files in the corpora directory, excluding restricted ones"""
    tt_files = []

    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    for corpus_folder in sorted(os.listdir(data_dir)):
        corpus_path = os.path.join(data_dir, corpus_folder)
        if not os.path.isdir(corpus_path):
            continue

        # Check exclusion list (handle both hyphenated folder names and dot-separated corpus names)
        normalized_name = normalize_corpus_name(corpus_folder)
        if corpus_folder in EXCLUDED_CORPORA or normalized_name in EXCLUDED_CORPORA:
            print(f"  SKIPPING {corpus_folder} (restricted license)")
            continue

        # Look for _TT subdirectory
        tt_dir = None
        for subdir in os.listdir(corpus_path):
            if subdir.endswith('_TT'):
                tt_dir = os.path.join(corpus_path, subdir)
                break

        if tt_dir and os.path.isdir(tt_dir):
            for filename in sorted(os.listdir(tt_dir)):
                if filename.endswith('.tt'):
                    tt_files.append(os.path.join(tt_dir, filename))

    return tt_files


def parse_meta_tag(content):
    """Parse the <meta> tag to extract metadata"""
    meta = {}

    # Find meta tag
    meta_match = re.search(r'<meta\s+([^>]+)>', content)
    if not meta_match:
        return meta

    meta_attrs = meta_match.group(1)

    # Extract attributes
    for attr in ['author', 'corpus', 'title', 'language', 'license', 'translation',
                 'document_cts_urn', 'book', 'chapter', 'msItem_title']:
        match = re.search(rf'{attr}="([^"]*)"', meta_attrs)
        if match:
            meta[attr] = html.unescape(match.group(1))

    return meta


def extract_norm_words(content):
    """Extract normalized words and their lemmas from the TT content"""
    words = []

    # Pattern to match <norm> tags with their attributes and content
    norm_pattern = re.compile(
        r'<norm[^>]*\slemma="([^"]*)"[^>]*\snorm="([^"]*)"[^>]*>(.*?)</norm>',
        re.DOTALL
    )

    for match in norm_pattern.finditer(content):
        lemma = match.group(1)
        norm = match.group(2)
        # Get the actual text content (strip inner tags)
        text_content = re.sub(r'<[^>]+>', '', match.group(3)).strip()

        if text_content and norm:
            words.append({
                'text': text_content,
                'norm': norm,
                'lemma': lemma
            })

    return words


def extract_translations(content):
    """Extract translation segments from <translation> tags"""
    translations = []

    # Pattern for verse translations
    verse_pattern = re.compile(
        r'<verse_n\s+verse_n="([^"]+)"[^>]*>.*?<translation\s+translation="([^"]+)"',
        re.DOTALL
    )

    for match in verse_pattern.finditer(content):
        verse_num = match.group(1)
        translation = html.unescape(match.group(2))
        translations.append({
            'verse': verse_num,
            'text': translation
        })

    return translations


def extract_lines_from_tt(content):
    """Extract text organized by lines (lb_n tags)"""
    lines = []
    current_line_words = []
    current_line_num = 1

    # Split by line breaks
    parts = re.split(r'(<lb_n\s+lb_n="[^"]+">|</lb_n>)', content)

    in_line = False
    line_num = None

    for part in parts:
        lb_match = re.match(r'<lb_n\s+lb_n="([^"]+)">', part)
        if lb_match:
            # Save previous line if exists
            if current_line_words:
                lines.append({
                    'line_num': current_line_num,
                    'words': current_line_words
                })
            current_line_words = []
            current_line_num = lb_match.group(1)
            in_line = True
        elif part == '</lb_n>':
            in_line = False
        elif in_line:
            # Extract words from this part
            words = extract_norm_words(part)
            current_line_words.extend(words)

    # Don't forget last line
    if current_line_words:
        lines.append({
            'line_num': current_line_num,
            'words': current_line_words
        })

    return lines


def parse_tt_file(filepath):
    """Parse a TT file and extract structured data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse metadata
    meta = parse_meta_tag(content)

    # Extract words with lemmas
    words = extract_norm_words(content)

    # Extract translations
    translations = extract_translations(content)

    # Try to extract line-organized data
    lines = extract_lines_from_tt(content)

    return {
        'meta': meta,
        'words': words,
        'translations': translations,
        'lines': lines,
        'filepath': filepath
    }


def group_files_by_work(tt_files):
    """Group TT files by corpus/work"""
    works = defaultdict(list)

    for filepath in tt_files:
        # Parse to get metadata
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        meta = parse_meta_tag(content)

        corpus = meta.get('corpus', os.path.basename(os.path.dirname(os.path.dirname(filepath))))
        works[corpus].append(filepath)

    return works


def get_author_from_corpus(corpus_name, meta):
    """Determine author from corpus name and metadata"""
    # Use meta author if available
    if meta.get('author'):
        return meta['author']

    # Infer from corpus name
    corpus_lower = corpus_name.lower()

    if 'shenoute' in corpus_lower:
        return 'Shenoute'
    elif 'besa' in corpus_lower:
        return 'Besa'
    elif 'pachomius' in corpus_lower:
        return 'Pachomius'
    elif 'pseudo-athanasius' in corpus_lower:
        return 'Pseudo-Athanasius'
    elif 'pseudo-basil' in corpus_lower:
        return 'Pseudo-Basil'
    elif 'pseudo-chrysostom' in corpus_lower:
        return 'Pseudo-Chrysostom'
    elif 'pseudo-ephrem' in corpus_lower:
        return 'Pseudo-Ephrem'
    elif 'pseudo-flavianus' in corpus_lower:
        return 'Pseudo-Flavianus'
    elif 'pseudo-theophilus' in corpus_lower:
        return 'Pseudo-Theophilus'
    elif 'pseudo-timothy' in corpus_lower:
        return 'Pseudo-Timothy'
    elif 'pseudo-celestinus' in corpus_lower:
        return 'Pseudo-Celestinus'
    elif 'proclus' in corpus_lower:
        return 'Proclus'
    elif 'theodosius' in corpus_lower:
        return 'Theodosius of Alexandria'
    elif 'john' in corpus_lower and 'constantinople' in corpus_lower:
        return 'John of Constantinople'
    elif 'johannes' in corpus_lower:
        return 'Apa Johannes'
    elif corpus_lower.startswith('sahidic') or corpus_lower.startswith('bohairic'):
        return 'Biblical'
    elif 'abraham' in corpus_lower:
        return 'Abraham (Patriarch)'
    elif 'ap' == corpus_lower or 'apophthegmata' in corpus_lower:
        return 'Apophthegmata Patrum'
    elif 'pistis' in corpus_lower:
        return 'Gnostic'
    elif 'thomas' in corpus_lower:
        return 'Gospel of Thomas'
    elif 'acts-pilate' in corpus_lower:
        return 'Acts of Pilate'
    elif 'mercurius' in corpus_lower:
        return 'Mercurius'
    elif 'martyrdom' in corpus_lower:
        return 'Martyrdom'
    elif 'magical' in corpus_lower:
        return 'Magical Papyri'
    elif 'doc-papyri' in corpus_lower:
        return 'Documentary Papyri'
    else:
        return 'Anonymous'


def make_safe_id(text):
    """Convert text to safe ID (alphanumeric and underscore only)"""
    # Replace non-alphanumeric with underscore
    safe = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
    # Remove consecutive underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    return safe or 'unknown'


def populate_database(conn, tt_files):
    """Populate database with parsed TT files"""
    cursor = conn.cursor()

    # Group files by corpus/work
    works_by_corpus = group_files_by_work(tt_files)

    # Track authors we've inserted
    authors_inserted = set()

    # Statistics
    stats = {
        'authors': 0,
        'works': 0,
        'books': 0,
        'lines': 0,
        'words': 0,
        'translations': 0,
        'lemma_mappings': 0
    }

    # Track lemma mappings to avoid duplicates
    lemma_mappings_seen = set()

    print(f"\nProcessing {len(works_by_corpus)} corpora...")

    for corpus_name, files in sorted(works_by_corpus.items()):
        print(f"\n  Processing corpus: {corpus_name} ({len(files)} files)")

        # Parse first file to get metadata
        first_file_data = parse_tt_file(files[0])
        meta = first_file_data['meta']

        # Determine author
        author_name = get_author_from_corpus(corpus_name, meta)
        author_id = make_safe_id(author_name)

        # Insert author if not already
        if author_id not in authors_inserted:
            cursor.execute('''
                INSERT OR IGNORE INTO authors (id, name, name_alt, language, has_translations)
                VALUES (?, ?, ?, ?, ?)
            ''', (author_id, author_name, None, 'coptic', 1))
            authors_inserted.add(author_id)
            stats['authors'] += 1

        # Create work
        work_id = make_safe_id(corpus_name)
        work_title = meta.get('msItem_title') or meta.get('title') or corpus_name

        cursor.execute('''
            INSERT OR IGNORE INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            work_id,
            author_id,
            work_title,
            corpus_name,
            work_title,  # Most titles are already in English
            'prose',
            meta.get('document_cts_urn'),
            meta.get('language', '')
        ))
        stats['works'] += 1

        # Process each file as a "book" (chapter/section)
        for file_idx, filepath in enumerate(sorted(files), 1):
            file_data = parse_tt_file(filepath)
            file_meta = file_data['meta']

            # Create book ID
            filename = os.path.basename(filepath).replace('.tt', '')
            book_id = f"{work_id}.{file_idx}"

            # Get chapter label
            chapter = file_meta.get('chapter') or file_meta.get('book') or filename
            label = f"Chapter {chapter}" if chapter.isdigit() else chapter

            # If we have line-organized data, use it
            if file_data['lines']:
                lines_data = file_data['lines']
            else:
                # Create pseudo-lines from words (group every 10-15 words)
                all_words = file_data['words']
                lines_data = []
                words_per_line = 12
                for i in range(0, len(all_words), words_per_line):
                    lines_data.append({
                        'line_num': len(lines_data) + 1,
                        'words': all_words[i:i+words_per_line]
                    })

            line_count = len(lines_data)

            # Insert book
            cursor.execute('''
                INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (book_id, work_id, file_idx, label, 1, line_count, line_count))
            stats['books'] += 1

            # Insert lines and words
            sequence_num = 0
            for line_data in lines_data:
                sequence_num += 1
                line_num = sequence_num  # Use sequential numbers

                # Construct line text from words
                line_text = ' '.join(w['text'] for w in line_data['words'])

                if not line_text.strip():
                    continue

                cursor.execute('''
                    INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, line_num, sequence_num, line_text))
                stats['lines'] += 1

                # Insert words
                for word_pos, word_info in enumerate(line_data['words'], 1):
                    word_text = word_info['text']
                    lemma = word_info.get('lemma', '')

                    if not word_text.strip():
                        continue

                    cursor.execute('''
                        INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word_text.lower(), book_id, line_num, sequence_num, word_pos))
                    stats['words'] += 1

                    # Add lemma mapping if we have a lemma
                    if lemma:
                        mapping_key = (word_text.lower(), lemma.lower())
                        if mapping_key not in lemma_mappings_seen:
                            cursor.execute('''
                                INSERT INTO lemma_map (word_form, lemma, confidence, source)
                                VALUES (?, ?, ?, ?)
                            ''', (word_text.lower(), lemma.lower(), 1.0, 'coptic_scriptorium'))
                            lemma_mappings_seen.add(mapping_key)
                            stats['lemma_mappings'] += 1

            # Insert translations
            translations = file_data['translations']
            translator = file_meta.get('translation', 'Unknown')

            # Map verse numbers to line numbers (approximate)
            lines_per_verse = max(1, line_count // max(1, len(translations))) if translations else 1

            for trans_idx, trans in enumerate(translations):
                start_line = trans_idx * lines_per_verse + 1
                end_line = min((trans_idx + 1) * lines_per_verse, line_count)

                cursor.execute('''
                    INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, start_line, end_line, trans_idx + 1, trans['text'], translator))

                segment_id = cursor.lastrowid

                # Add to translation_lookup
                for ln in range(start_line, end_line + 1):
                    cursor.execute('''
                        INSERT OR IGNORE INTO translation_lookup (book_id, line_number, segment_id)
                        VALUES (?, ?, ?)
                    ''', (book_id, ln, segment_id))

                stats['translations'] += 1

        print(f"    {len(files)} files processed")

    conn.commit()
    return stats


def parse_coptic_lexicon(conn, lexicon_path):
    """Parse the Comprehensive Coptic Lexicon TEI XML and populate dictionary_entries and lemma_map"""
    if not os.path.exists(lexicon_path):
        print(f"  WARNING: Lexicon not found at {lexicon_path}")
        print("  Skipping lexicon integration.")
        return {'entries': 0, 'forms': 0}

    print(f"  Parsing lexicon: {lexicon_path}")

    cursor = conn.cursor()
    stats = {'entries': 0, 'forms': 0}

    # Track forms we've already added to lemma_map to avoid duplicates
    forms_seen = set()

    # Parse XML
    tree = ET.parse(lexicon_path)
    root = tree.getroot()

    # TEI namespace
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # Find all entries
    entries = root.findall('.//tei:entry', ns)
    print(f"  Found {len(entries)} lexicon entries")

    for entry in entries:
        entry_id = entry.get('{http://www.w3.org/XML/1998/namespace}id', '')

        # Find the lemma form (headword)
        lemma_form = entry.find('.//tei:form[@type="lemma"]', ns)
        if lemma_form is None:
            # Some entries don't have type="lemma", use first form
            lemma_form = entry.find('.//tei:form', ns)

        if lemma_form is None:
            continue

        # Get orthography (headword)
        orth_elem = lemma_form.find('tei:orth', ns)
        if orth_elem is None or orth_elem.text is None:
            continue

        headword = orth_elem.text.strip()
        if not headword:
            continue

        # Get dialect/usage
        usg_elem = lemma_form.find('tei:usg[@type="geo"]', ns)
        dialect = usg_elem.text if usg_elem is not None and usg_elem.text else ''

        # Get part of speech from entry-level gramGrp or form-level
        pos = ''
        gram_grp = entry.find('tei:gramGrp', ns) or lemma_form.find('tei:gramGrp', ns)
        if gram_grp is not None:
            pos_elem = gram_grp.find('tei:pos', ns)
            if pos_elem is not None and pos_elem.text:
                pos = pos_elem.text

        # Get translations from sense elements
        translations = {'de': '', 'en': '', 'fr': ''}
        for sense in entry.findall('.//tei:sense', ns):
            for cit in sense.findall('tei:cit[@type="translation"]', ns):
                # Check for <quote> elements
                for quote in cit.findall('tei:quote', ns):
                    lang = quote.get('{http://www.w3.org/XML/1998/namespace}lang', '')
                    if lang in translations and quote.text:
                        if translations[lang]:
                            translations[lang] += '; ' + quote.text.strip()
                        else:
                            translations[lang] = quote.text.strip()
                # Check for <def> elements (some entries use this instead)
                for defn in cit.findall('tei:def', ns):
                    lang = defn.get('{http://www.w3.org/XML/1998/namespace}lang', '')
                    if lang in translations and defn.text:
                        if translations[lang]:
                            translations[lang] += '; ' + defn.text.strip()
                        else:
                            translations[lang] = defn.text.strip()

        # Build plain text entry (prefer English, fall back to German/French)
        entry_plain = translations['en'] or translations['de'] or translations['fr'] or ''
        if pos:
            entry_plain = f"({pos}) {entry_plain}" if entry_plain else f"({pos})"
        if dialect:
            entry_plain = f"[{dialect}] {entry_plain}"

        # Build HTML entry for display
        entry_html_parts = []
        if dialect:
            entry_html_parts.append(f'<span class="dialect">[{dialect}]</span>')
        if pos:
            entry_html_parts.append(f'<span class="pos">{pos}</span>')
        if translations['en']:
            entry_html_parts.append(f'<span class="def">{translations["en"]}</span>')
        elif translations['de']:
            entry_html_parts.append(f'<span class="def">{translations["de"]}</span>')
        elif translations['fr']:
            entry_html_parts.append(f'<span class="def">{translations["fr"]}</span>')
        entry_html = ' '.join(entry_html_parts)

        # Insert dictionary entry
        cursor.execute('''
            INSERT INTO dictionary_entries
            (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            headword,
            headword.lower(),  # Simple normalization for Coptic
            'coptic',
            entry_id,  # Store XML ID for reference
            entry_html,
            entry_plain,
            'comprehensive_coptic_lexicon'
        ))
        stats['entries'] += 1

        # Collect all word forms for lemma_map
        all_forms = []
        for form in entry.findall('.//tei:form', ns):
            form_orth = form.find('tei:orth', ns)
            if form_orth is not None and form_orth.text:
                form_text = form_orth.text.strip()
                if form_text:
                    all_forms.append(form_text)

        # Add forms to lemma_map (map inflected forms to headword)
        for form_text in all_forms:
            form_key = (form_text.lower(), headword.lower())
            if form_key not in forms_seen:
                cursor.execute('''
                    INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    form_text.lower(),
                    form_text.lower(),  # Simple normalization for Coptic
                    headword.lower(),
                    0.9,  # High confidence from lexicon
                    'comprehensive_coptic_lexicon'
                ))
                forms_seen.add(form_key)
                stats['forms'] += 1

    conn.commit()
    print(f"  Added {stats['entries']} dictionary entries")
    print(f"  Added {stats['forms']} lemma mappings from lexicon")

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
    print("Creating Coptic Scriptorium Database")
    print("=" * 60)

    # Check data directory
    if not os.path.exists(DATA_DIR):
        print(f"\nERROR: Data directory not found: {DATA_DIR}")
        print("Please clone the Coptic Scriptorium corpus:")
        print("  cd data-sources")
        print("  git clone https://github.com/CopticScriptorium/corpora.git")
        return 1

    # Find TT files
    print(f"\n--- Finding TT Files ---")
    print(f"Data directory: {DATA_DIR}")
    tt_files = find_tt_files(DATA_DIR)
    print(f"Found {len(tt_files)} TT files (excluding restricted corpora)")

    if not tt_files:
        print("ERROR: No TT files found!")
        return 1

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate database
    print("\n--- Populating Database ---")
    stats = populate_database(conn, tt_files)

    # Parse lexicon
    print("\n--- Parsing Coptic Lexicon ---")
    lexicon_stats = parse_coptic_lexicon(conn, LEXICON_PATH)
    stats['dictionary_entries'] = lexicon_stats['entries']
    stats['lemma_mappings'] += lexicon_stats['forms']  # Add lexicon forms to text-derived mappings

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
    print(f"Translations: {stats['translations']}")
    print(f"Dictionary entries: {stats['dictionary_entries']}")
    print(f"Lemma mappings: {stats['lemma_mappings']}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
