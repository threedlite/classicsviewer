#!/usr/bin/env python3
"""
Create Old Norse database for ClassicsViewer

Sources:
- Texts: CLTK Old Norse texts (CC BY-SA 3.0 + Public Domain)
- Dictionary: Zoega's Old Icelandic Dictionary (Public Domain, 1910)
- Morphology: IcePaHC Treebank (CC BY-SA 4.0) - form→lemma mappings

License: CC BY-SA 3.0 / CC BY-SA 4.0 / Public Domain (commercial use allowed with attribution)

Usage:
  python3 create_norse_database.py
"""

import sqlite3
import json
import os
import re
import zipfile
import subprocess
import urllib.request
from pathlib import Path

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data-sources")
DB_PATH = os.path.join(SCRIPT_DIR, "norse_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "norse_texts.db.zip")

# Repository paths
TEXTS_DIR = os.path.join(DATA_DIR, "non_texts")
DICT_DIR = os.path.join(DATA_DIR, "zoega-dictionary")
DICT_JSON = os.path.join(DICT_DIR, "json", "zoega-no-markup.json")

# GitHub repositories
TEXTS_REPO = "https://github.com/cltk/non_texts.git"
DICT_REPO = "https://github.com/stscoundrel/old-icelandic-zoega.git"
TREEBANK_REPO = "https://github.com/UniversalDependencies/UD_Icelandic-IcePaHC.git"

# Treebank path
TREEBANK_DIR = os.path.join(DATA_DIR, "icepahc")

# Translation URLs (Project Gutenberg - Public Domain)
TRANSLATIONS = {
    'Völsunga_saga': {
        'url': 'https://www.gutenberg.org/cache/epub/1152/pg1152.txt',
        'path': os.path.join(DATA_DIR, 'volsunga_translation.txt'),
        'translator': 'William Morris & Eiríkr Magnússon (1888)',
    },
    'Grettis_Saga': {
        'url': 'https://www.gutenberg.org/cache/epub/347/pg347.txt',
        'path': os.path.join(DATA_DIR, 'grettis_translation.txt'),
        'translator': 'G.H. Hight (1914)',
    },
    'Snorra-Edda': {
        'url': 'https://www.gutenberg.org/cache/epub/18947/pg18947.txt',
        'path': os.path.join(DATA_DIR, 'prose_edda_translation.txt'),
        'translator': 'Rasmus B. Anderson (1879)',
    },
    # Poetic Edda uses a different structure - poems are separate
    'Sæmundar-Edda': {
        'url': 'https://www.gutenberg.org/cache/epub/14726/pg14726.txt',
        'path': os.path.join(DATA_DIR, 'poetic_edda_translation.txt'),
        'translator': 'Benjamin Thorpe (1866)',
    },
}

# Works to include (directory name, display title, English title, type)
WORKS = [
    # Poetic Edda (Sæmundar-Edda)
    ("Sæmundar-Edda", "Sæmundar-Edda", "Poetic Edda", "poetry"),
    # Prose Edda
    ("Snorra-Edda", "Snorra-Edda", "Prose Edda", "prose"),
    # Major Sagas
    ("Grettis_Saga", "Grettis saga", "Grettir's Saga", "saga"),
    ("Völsunga_saga", "Völsunga saga", "Saga of the Volsungs", "saga"),
    ("Hrólfs_saga_kraka_ok_kappa_hans", "Hrólfs saga kraka", "Saga of Hrolf Kraki", "saga"),
    ("Ragnars_saga_loðbrókar", "Ragnars saga loðbrókar", "Saga of Ragnar Lothbrok", "saga"),
    ("Örvar-Odds_saga", "Örvar-Odds saga", "Arrow-Odd's Saga", "saga"),
    ("Friðþjófs_saga_ins_frækna", "Friðþjófs saga", "Saga of Fridthjof the Bold", "saga"),
    ("Egils_saga_einhenda_ok_Ásmundar_berserkjabana", "Egils saga einhenda", "Saga of Egil One-Hand", "saga"),
    # Additional sagas
    ("Gautreks_saga", "Gautreks saga", "Gautrek's Saga", "saga"),
    ("Bósa_saga_ok_Herrauðs", "Bósa saga", "Saga of Bosi and Herraud", "saga"),
    ("Göngu-Hrólfs_saga", "Göngu-Hrólfs saga", "Saga of Gongu-Hrolf", "saga"),
    ("Áns_saga_bogsveigis", "Áns saga bogsveigis", "Saga of An Bow-Bender", "saga"),
    ("Ásmundar_saga_kappabana", "Ásmundar saga kappabana", "Saga of Asmund Champion-Killer", "saga"),
    # Þættir (short tales)
    ("Norna-Gests_þáttr", "Norna-Gests þáttr", "Tale of Norna-Gest", "þáttr"),
    ("Tóka_þáttr_Tókasonar", "Tóka þáttr", "Tale of Toki", "þáttr"),
    ("Helga_þáttr_Þórissonar", "Helga þáttr Þórissonar", "Tale of Helgi Thorisson", "þáttr"),
    ("Þorsteins_þáttr_bæjarmagns", "Þorsteins þáttr", "Tale of Thorstein Mansion-Might", "þáttr"),
    # Other works
    ("Hálfdanar_saga_Brönufóstra", "Hálfdanar saga Brönufóstra", "Saga of Halfdan Bronufostri", "saga"),
    ("Hálfdanar_saga_Eysteinssonar", "Hálfdanar saga Eysteinssonar", "Saga of Halfdan Eysteinsson", "saga"),
    ("Hálfs_saga_ok_Hálfsrekka", "Hálfs saga", "Saga of Half and His Heroes", "saga"),
    ("Sögubrot_af_nokkrum_fornkonungum", "Sögubrot", "Fragment of Ancient Kings", "saga"),
    ("Sturlaugs_saga_starfsama", "Sturlaugs saga starfsama", "Saga of Sturlaug the Industrious", "saga"),
    ("Þorsteins_saga_Víkingssonar", "Þorsteins saga Víkingssonar", "Saga of Thorstein Vikingsson", "saga"),
]


def create_database(db_path):
    """Create the database schema (matches Greek/Latin/Sanskrit schema)"""
    print(f"Creating database: {db_path}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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


def clone_repositories():
    """Clone or update source repositories"""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Clone texts
    if os.path.exists(TEXTS_DIR):
        print("Updating Old Norse texts repository...")
        subprocess.run(["git", "-C", TEXTS_DIR, "pull"], check=True, capture_output=True)
    else:
        print("Cloning Old Norse texts repository...")
        subprocess.run(
            ["git", "clone", "--depth", "1", TEXTS_REPO, TEXTS_DIR],
            check=True
        )

    # Clone dictionary
    if os.path.exists(DICT_DIR):
        print("Updating Zoega dictionary repository...")
        subprocess.run(["git", "-C", DICT_DIR, "pull"], check=True, capture_output=True)
    else:
        print("Cloning Zoega dictionary repository...")
        subprocess.run(
            ["git", "clone", "--depth", "1", DICT_REPO, DICT_DIR],
            check=True
        )

    # Clone treebank
    if os.path.exists(TREEBANK_DIR):
        print("Updating IcePaHC treebank repository...")
        subprocess.run(["git", "-C", TREEBANK_DIR, "pull"], check=True, capture_output=True)
    else:
        print("Cloning IcePaHC treebank repository...")
        subprocess.run(
            ["git", "clone", "--depth", "1", TREEBANK_REPO, TREEBANK_DIR],
            check=True
        )

    print(f"  Texts ready at: {TEXTS_DIR}")
    print(f"  Dictionary ready at: {DICT_DIR}")
    print(f"  Treebank ready at: {TREEBANK_DIR}")


def download_translations():
    """Download English translations from Project Gutenberg"""
    print("\nDownloading English translations...")

    for work_name, trans_info in TRANSLATIONS.items():
        trans_path = trans_info['path']
        trans_url = trans_info['url']

        if os.path.exists(trans_path):
            print(f"  {work_name} translation already downloaded")
        else:
            print(f"  Downloading {work_name} translation...")
            try:
                urllib.request.urlretrieve(trans_url, trans_path)
                print(f"    Saved to: {trans_path}")
            except Exception as e:
                print(f"    Error downloading {work_name}: {e}")


def normalize_norse(word):
    """Normalize Old Norse word for lookup"""
    word = word.lower()
    # Normalize some common variants
    word = word.replace('ö', 'ǫ')  # Sometimes used interchangeably
    return word


def normalize_modern_to_old_norse(lemma):
    """Convert Modern Icelandic lemma to Old Norse form for dictionary lookup.

    Uses only systematic pattern-based transformations, not word-specific mappings.
    The IcePaHC treebank uses Modern Icelandic lemmas, but Zoega uses Old Norse forms.
    """
    lemma = lemma.lower()

    # Systematic transformations based on regular sound/spelling changes:

    # 1. Vowel transformations: ö → ǫ (höfuð → hǫfuð)
    lemma = lemma.replace('ö', 'ǫ')

    # 2. Common ending transformations: -ur → -r (maður → maðr, konungur → konungr)
    if lemma.endswith('ur') and len(lemma) > 3:
        lemma = lemma[:-2] + 'r'
    # -ður → -ðr (specific pattern)
    elif lemma.endswith('ður') and len(lemma) > 4:
        lemma = lemma[:-3] + 'ðr'

    # 3. Past participle endings: -ið → -it (verið → verit)
    if lemma.endswith('ið') and len(lemma) > 3:
        lemma = lemma[:-2] + 'it'

    # 4. Consonant cluster: ft → pt (eftir → eptir) - systematic in Old Norse
    lemma = lemma.replace('ft', 'pt')

    # 5. Vowel: o → á in certain positions (svo → svá pattern)
    # This is less systematic, handled by normalization patterns table instead

    return lemma


def parse_conllu_file(filepath):
    """Parse a CoNLL-U file and extract form→lemma mappings with morphology"""
    mappings = {}  # form -> {lemma, morph_info, count}

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) < 6:
                continue

            # CoNLL-U format: ID FORM LEMMA UPOS XPOS FEATS ...
            word_id = parts[0]

            # Skip multi-word tokens (e.g., "1-2")
            if '-' in word_id or '.' in word_id:
                continue

            form = parts[1].lower()
            lemma = parts[2].lower()
            upos = parts[3]  # Universal POS tag
            feats = parts[5] if parts[5] != '_' else ''  # Morphological features

            # Skip punctuation and special tokens
            if upos == 'PUNCT' or form == '_':
                continue

            # Build morph info string
            morph_info = f"{upos}"
            if feats:
                morph_info += f"|{feats}"

            key = (form, lemma)
            if key not in mappings:
                mappings[key] = {'morph_info': morph_info, 'count': 0}
            mappings[key]['count'] += 1

    return mappings


def populate_treebank_morphology(conn):
    """Load form→lemma mappings from IcePaHC treebank"""
    cursor = conn.cursor()

    print("Loading morphology from IcePaHC treebank...")

    all_mappings = {}

    # Parse all CoNLL-U files
    for filename in ['is_icepahc-ud-train.conllu', 'is_icepahc-ud-dev.conllu', 'is_icepahc-ud-test.conllu']:
        filepath = os.path.join(TREEBANK_DIR, filename)
        if os.path.exists(filepath):
            print(f"  Parsing {filename}...")
            mappings = parse_conllu_file(filepath)
            for key, value in mappings.items():
                if key not in all_mappings:
                    all_mappings[key] = value
                else:
                    all_mappings[key]['count'] += value['count']

    print(f"  Found {len(all_mappings)} unique form→lemma mappings")

    # Insert into lemma_map (avoiding duplicates from dictionary)
    count = 0
    normalized_count = 0
    for (form, lemma), info in all_mappings.items():
        # Normalize Modern Icelandic lemma to Old Norse form
        lemma_old_norse = normalize_modern_to_old_norse(lemma)

        # Check if this form already exists from dictionary
        cursor.execute(
            'SELECT COUNT(*) FROM lemma_map WHERE word_form = ? AND lemma = ?',
            (form, lemma_old_norse)
        )
        if cursor.fetchone()[0] == 0:
            form_normalized = normalize_norse(form)
            # Confidence based on frequency (more occurrences = higher confidence)
            confidence = min(1.0, 0.5 + (info['count'] / 100))

            cursor.execute('''
                INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (form, form_normalized, lemma_old_norse, confidence, 'IcePaHC', info['morph_info']))
            count += 1

            if lemma_old_norse != lemma:
                normalized_count += 1

    conn.commit()
    print(f"  Inserted {count} new form→lemma mappings from treebank")
    print(f"  Normalized {normalized_count} Modern Icelandic lemmas to Old Norse")

    return count


def load_dictionary():
    """Load Zoega dictionary from JSON"""
    print(f"Loading dictionary from: {DICT_JSON}")

    with open(DICT_JSON, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"  Loaded {len(entries)} dictionary entries")
    return entries


def get_text_files(work_dir):
    """Get all text files for a work, handling different directory structures"""
    text_files = []

    # Check for chapter_*.txt files at root level
    chapter_files = sorted(
        [f for f in os.listdir(work_dir) if f.startswith('chapter_') and f.endswith('.txt')],
        key=lambda x: int(re.search(r'chapter_(\d+)', x).group(1)) if re.search(r'chapter_(\d+)', x) else 0
    )

    if chapter_files:
        for f in chapter_files:
            text_files.append((os.path.join(work_dir, f), f.replace('.txt', '').replace('_', ' ').title()))
        return text_files

    # Check for subdirectories with txt_files/complete.txt (like Poetic Edda poems)
    for item in sorted(os.listdir(work_dir)):
        item_path = os.path.join(work_dir, item)
        if os.path.isdir(item_path):
            complete_path = os.path.join(item_path, 'txt_files', 'complete.txt')
            if os.path.exists(complete_path):
                text_files.append((complete_path, item))

    if text_files:
        return text_files

    # Check for top-level .txt files (like Snorra-Edda's gylfaginning.txt, etc.)
    # These are comprehensive files that should be preferred over subdirectory chapter files
    # Also include .txtl files (typo in CLTK repo for haattatal.txtl)
    top_level_txt = sorted([f for f in os.listdir(work_dir) if f.endswith('.txt') or f.endswith('.txtl')])
    if top_level_txt:
        for f in top_level_txt:
            # Handle both .txt and .txtl extensions
            label = f.replace('.txtl', '').replace('.txt', '').replace('_', ' ').title()
            text_files.append((os.path.join(work_dir, f), label))
        return text_files

    # Fallback: check subdirectories for chapter_*.txt files
    for item in sorted(os.listdir(work_dir)):
        item_path = os.path.join(work_dir, item)
        if os.path.isdir(item_path):
            subdir_chapters = sorted(
                [f for f in os.listdir(item_path) if f.startswith('chapter_') and f.endswith('.txt')],
                key=lambda x: int(re.search(r'chapter_(\d+)', x).group(1)) if re.search(r'chapter_(\d+)', x) else 0
            )
            for f in subdir_chapters:
                text_files.append((os.path.join(item_path, f), f"{item} - {f.replace('.txt', '').replace('_', ' ').title()}"))

    return text_files


def parse_text_file(filepath):
    """Parse a text file into lines.

    Handles files with no line terminators (common in CLTK saga texts)
    by splitting long prose into sentences.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into lines, filter empty lines
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # If line is very long (no proper line breaks in source),
            # split into sentences for readability
            if len(line) > 500:
                # Split on sentence-ending punctuation followed by space
                # Preserves the punctuation with the sentence
                sentences = re.split(r'(?<=[.!?])\s+', line)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        lines.append(sentence)
            else:
                lines.append(line)

    return lines


def tokenize_norse(text):
    """Tokenize Old Norse text into words"""
    # Remove punctuation except for special Norse characters
    text = re.sub(r'[^\w\sáéíóúýæøöþðÁÉÍÓÚÝÆØÖÞÐǫǪ]', ' ', text, flags=re.UNICODE)
    words = text.split()
    return [w.strip().lower() for w in words if w.strip()]


def populate_texts(conn):
    """Parse texts and populate the database"""
    cursor = conn.cursor()

    # Insert author (Anonymous / Traditional)
    print("Inserting author...")
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('norse_traditional', 'Traditional', 'Anonymous', 'norse', 0))

    # Statistics
    total_lines = 0
    total_words = 0
    total_works = 0
    total_chapters = 0

    # Process each work
    for dir_name, title, title_english, work_type in WORKS:
        work_dir = os.path.join(TEXTS_DIR, dir_name)

        if not os.path.exists(work_dir):
            print(f"  Warning: Work directory not found: {dir_name}")
            continue

        work_id = f"norse_{dir_name.lower().replace(' ', '_')}"

        # Insert work
        cursor.execute('''
            INSERT INTO works (id, author_id, title, title_alt, title_english, type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            work_id,
            'norse_traditional',
            title,
            dir_name,
            title_english,
            work_type,
            f'{title_english} - Old Norse {work_type}'
        ))

        # Get text files
        text_files = get_text_files(work_dir)

        if not text_files:
            print(f"  Warning: No text files found for {dir_name}")
            continue

        work_lines = 0
        work_words = 0

        # Process each chapter/section
        for chapter_num, (filepath, label) in enumerate(text_files, 1):
            lines = parse_text_file(filepath)

            if not lines:
                continue

            book_id = f"{work_id}.{chapter_num}"

            # Insert book (chapter)
            cursor.execute('''
                INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                book_id,
                work_id,
                chapter_num,
                label,
                1,
                len(lines),
                len(lines)
            ))

            # Insert lines
            for line_num, line_text in enumerate(lines, 1):
                cursor.execute('''
                    INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, line_num, line_num, line_text))

                # Insert words
                words = tokenize_norse(line_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word, book_id, line_num, line_num, word_pos))
                    work_words += 1

            work_lines += len(lines)
            total_chapters += 1

        total_lines += work_lines
        total_words += work_words
        total_works += 1

        print(f"  {title}: {len(text_files)} chapters, {work_lines} lines, {work_words} words")

    conn.commit()

    return {
        'works': total_works,
        'chapters': total_chapters,
        'lines': total_lines,
        'words': total_words
    }


def populate_dictionary(conn):
    """Load Zoega dictionary into database"""
    cursor = conn.cursor()

    entries = load_dictionary()
    count = 0
    lowercase_variants = 0

    print("Inserting dictionary entries...")

    for entry in entries:
        headword = entry.get('word', '')
        definitions = entry.get('definitions', [])

        if not headword or not definitions:
            continue

        # Join definitions into single text
        entry_plain = ' '.join(definitions)

        # Normalize headword (lowercase + spelling normalization)
        headword_normalized = normalize_norse(headword)

        cursor.execute('''
            INSERT INTO dictionary_entries (headword, headword_normalized_ultra, language, entry_plain, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (headword, headword_normalized, 'norse', entry_plain, 'Zoega'))

        # Also add to lemma_map for basic lookup (with original case)
        cursor.execute('''
            INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (headword, headword_normalized, headword, 1.0, 'Zoega'))

        # Add lowercase variant if different (for case-insensitive matching)
        headword_lower = headword.lower()
        if headword_lower != headword:
            cursor.execute('''
                INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (headword_lower, headword_normalized, headword, 1.0, 'Zoega'))
            lowercase_variants += 1

        count += 1

    conn.commit()
    print(f"  Inserted {count} dictionary entries")
    print(f"  Added {lowercase_variants} lowercase lemma variants for case-insensitive matching")

    return count


def populate_normalization_patterns(conn):
    """Add systematic normalization patterns for Modern Icelandic → Old Norse.
    These are stored in the normalization_patterns table for app-side use."""
    cursor = conn.cursor()

    print("Adding normalization patterns...")

    # Systematic spelling patterns (regex-based, not word-specific)
    patterns = [
        # (pattern, replacement, description, priority)
        ('ö', 'ǫ', 'Modern ö to Old Norse ǫ', 10),
        ('ur$', 'r', 'Noun ending -ur to -r', 20),
        ('ður$', 'ðr', 'Noun ending -ður to -ðr', 21),
        ('ið$', 'it', 'Past participle -ið to -it', 30),
        ('ft', 'pt', 'Consonant cluster ft to pt', 40),
    ]

    count = 0
    for pattern, replacement, desc, priority in patterns:
        cursor.execute('''
            INSERT INTO normalization_patterns (language, pattern, replacement, description, priority)
            VALUES (?, ?, ?, ?, ?)
        ''', ('norse', pattern, replacement, desc, priority))
        count += 1

    conn.commit()
    print(f"  Added {count} normalization patterns")

    return count


def parse_volsunga_translation(filepath):
    """Parse Völsunga saga translation into chapters.

    The Morris/Magnusson translation has chapters with Roman numeral headings.
    Returns list of (chapter_num, chapter_text) tuples.
    """
    print(f"  Parsing Völsunga saga translation...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    current_chapter = None
    current_lines = []

    in_text = False

    # Chapter pattern: "CHAPTER I." or "CHAPTER XLII." with title following
    chapter_pattern = re.compile(r'^CHAPTER\s+([IVXLC]+)\.?\s', re.IGNORECASE)

    lines = content.split('\n')

    for line in lines:
        line_stripped = line.strip()

        # Detect end of text - appendix or project gutenberg footer
        # Note: ENDNOTES appears multiple times as footnote sections, so we don't use it
        if in_text and re.match(r'^(APPENDIX|END OF THE PROJECT|\*\*\*\s*END OF)', line_stripped, re.IGNORECASE):
            if current_chapter is not None and current_lines:
                chapters.append((current_chapter, '\n'.join(current_lines)))
            break

        # Check for chapter heading - this also starts the text
        chapter_match = chapter_pattern.match(line_stripped)
        if chapter_match:
            # Save previous chapter
            if current_chapter is not None and current_lines:
                chapters.append((current_chapter, '\n'.join(current_lines)))
                current_lines = []

            in_text = True
            # Convert Roman numeral to number
            roman = chapter_match.group(1).upper()
            current_chapter = roman_to_int(roman)
            continue

        # Collect text
        if in_text and current_chapter is not None and line_stripped:
            current_lines.append(line_stripped)

    # Add final chapter
    if current_chapter is not None and current_lines:
        chapters.append((current_chapter, '\n'.join(current_lines)))

    print(f"    Found {len(chapters)} chapters")
    return chapters


def parse_grettis_translation(filepath):
    """Parse Grettir's Saga translation into chapters.

    The Hight translation has "CHAPTER I" etc. format.
    Returns list of (chapter_num, chapter_text) tuples.
    """
    print(f"  Parsing Grettir's Saga translation...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    current_chapter = None
    current_lines = []

    in_text = False

    # Chapter pattern: "CHAPTER I" or "CHAPTER XCIII"
    chapter_pattern = re.compile(r'^CHAPTER\s+([IVXLC]+)\b', re.IGNORECASE)

    lines = content.split('\n')

    for line in lines:
        line_stripped = line.strip()

        # Detect start of main text
        if 'CHAPTER I' in line.upper() and not in_text:
            in_text = True

        # Detect end of text - Project Gutenberg footer
        # Note: ENDNOTES appears multiple times as footnote sections, so we don't use it
        if in_text and re.match(r'^(\*\*\*\s*END OF|END OF THE PROJECT)', line_stripped, re.IGNORECASE):
            if current_chapter is not None and current_lines:
                chapters.append((current_chapter, '\n'.join(current_lines)))
            break

        if not in_text:
            continue

        # Check for chapter heading
        chapter_match = chapter_pattern.match(line_stripped)
        if chapter_match:
            # Save previous chapter
            if current_chapter is not None and current_lines:
                chapters.append((current_chapter, '\n'.join(current_lines)))
                current_lines = []

            # Convert Roman numeral to number
            roman = chapter_match.group(1).upper()
            current_chapter = roman_to_int(roman)
            continue

        # Collect text (skip chapter titles in ALL CAPS)
        if current_chapter is not None and line_stripped:
            # Skip ALL CAPS title lines
            if not re.match(r'^[A-Z\s\-\.\']+$', line_stripped):
                current_lines.append(line_stripped)

    # Add final chapter
    if current_chapter is not None and current_lines:
        chapters.append((current_chapter, '\n'.join(current_lines)))

    print(f"    Found {len(chapters)} chapters")
    return chapters


def roman_to_int(roman):
    """Convert Roman numeral to integer"""
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    prev = 0
    for char in reversed(roman.upper()):
        curr = values.get(char, 0)
        if curr < prev:
            result -= curr
        else:
            result += curr
        prev = curr
    return result


# Map Old Norse poem name -> search pattern in English translation
# More specific patterns must come before less specific ones (e.g., "GROENLAND LAY OF ATLI" before "LAY OF ATLI")
POETIC_EDDA_MAP = {
    "Völuspá": "VÖLUSPÂ",
    "Hávamál": "HIGH ONE'S",
    "Vafþrúðnismál": "VAFTHRUDNIR",
    "Grímnismál": "GRIMNIR",
    "Baldrs draumar": "BALDR'S DREAMS",
    "Hymiskviða": "HYMIR",
    "Þrymskviða": "THRYM",
    "Alvíssmál": "ALVIS",
    "Hárbarðsljóð": "HARBARD",
    "Skírnismál": "SKIRNIR",
    "Rígsþula": "LAY OF RIG",
    "Lokasenna": "LOKI'S ALTERCATION",
    "Hyndluljóð": "HYNDLA",
    "Völundarkviða": "LAY OF VOLUND",
    "Fáfnismál": "LAY OF FAFNIR",
    "Sigrdrífumál": "SIGRDRIFA",
    "Guðrúnarkviða": "LAY OF GUDRUN",
    "Helreið Brynhildar": "BRYNHILD'S HEL",
    "Dráp Niflunga": "NIFLUNGS",
    "Oddrúnarkviða": "ODDRUN'S",
    "Atlamál in grænlenzku": "GROENLAND LAY OF ATLI",  # Must be before "LAY OF ATLI"
    "Atlakviða": "LAY OF ATLI",
    "Guðrúnarhvöt": "GUDRUN'S INCITEMENT",
    "Hamðismál": "LAY OF HAMDIR",
}


def parse_poetic_edda_translation(filepath):
    """Parse Poetic Edda translation into individual poems.

    Scans for poem title patterns and extracts text between them.
    Returns dict of {old_norse_name: translation_text}.
    """
    print(f"  Parsing Poetic Edda translation...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    poems = {}
    current_poem = None
    current_lines = []
    in_text = False

    lines = content.split('\n')

    for line in lines:
        line_stripped = line.strip()
        line_upper = line_stripped.upper()

        # Detect end of text
        if in_text and re.match(r'^(\*\*\*\s*END OF|END OF THE PROJECT)', line_stripped, re.IGNORECASE):
            if current_poem and current_lines:
                poems[current_poem] = '\n'.join(current_lines)
            break

        # Check if line contains a poem title pattern
        matched_poem = None
        for norse_name, pattern in POETIC_EDDA_MAP.items():
            if pattern in line_upper:
                matched_poem = norse_name
                in_text = True
                break

        if matched_poem:
            # Save previous poem
            if current_poem and current_lines:
                if current_poem not in poems:
                    poems[current_poem] = '\n'.join(current_lines)
                current_lines = []
            current_poem = matched_poem
            continue

        # Collect text
        if in_text and current_poem and line_stripped:
            current_lines.append(line_stripped)

    # Add final poem
    if current_poem and current_lines:
        if current_poem not in poems:
            poems[current_poem] = '\n'.join(current_lines)

    print(f"    Found {len(poems)} poems")
    return poems


def parse_prose_edda_translation(filepath):
    """Parse Prose Edda translation into sections.

    The Anderson translation has sections: Gylfaginning, Skaldskaparmal, etc.
    Returns dict of {section_name: translation_text}.
    """
    print(f"  Parsing Prose Edda translation...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {}
    current_section = None
    current_lines = []

    in_text = False

    lines = content.split('\n')

    for line in lines:
        line_stripped = line.strip()

        # Detect end of text
        if in_text and re.match(r'^(\*\*\*\s*END OF|END OF THE PROJECT)', line_stripped, re.IGNORECASE):
            if current_section and current_lines:
                sections[current_section] = '\n'.join(current_lines)
            break

        # Detect major section headings
        if 'GYLFAGINNING' in line_stripped.upper() and not in_text:
            in_text = True
            if current_section and current_lines:
                sections[current_section] = '\n'.join(current_lines)
                current_lines = []
            current_section = 'Gylfaginning'
            continue

        if in_text and 'SKALDSKAPARMAL' in line_stripped.upper():
            if current_section and current_lines:
                sections[current_section] = '\n'.join(current_lines)
                current_lines = []
            current_section = 'skaaldskaparmaal'  # Match the filename
            continue

        if in_text and 'HATTATAL' in line_stripped.upper():
            if current_section and current_lines:
                sections[current_section] = '\n'.join(current_lines)
                current_lines = []
            current_section = 'haattatal'  # Match the filename (with typo)
            continue

        # Collect text
        if in_text and current_section and line_stripped:
            current_lines.append(line_stripped)

    # Add final section
    if current_section and current_lines:
        sections[current_section] = '\n'.join(current_lines)

    print(f"    Found {len(sections)} sections")
    return sections


def populate_translations(conn):
    """Populate English translations for Norse texts that have them."""
    cursor = conn.cursor()

    print("Populating translations...")

    total_segments = 0
    total_lookups = 0
    works_with_trans = []

    # Process each work that has translations
    for work_dir_name, trans_info in TRANSLATIONS.items():
        trans_path = trans_info['path']
        translator = trans_info['translator']

        if not os.path.exists(trans_path):
            print(f"  Warning: Translation not found for {work_dir_name}")
            continue

        # Get the work_id from the database
        work_id = f"norse_{work_dir_name.lower().replace(' ', '_')}"

        # Check if work exists
        cursor.execute("SELECT id FROM works WHERE id = ?", (work_id,))
        if not cursor.fetchone():
            print(f"  Warning: Work not found in database: {work_id}")
            continue

        # Get books (chapters) for this work
        cursor.execute("""
            SELECT id, book_number, line_count
            FROM books
            WHERE work_id = ?
            ORDER BY book_number
        """, (work_id,))
        books = cursor.fetchall()

        if not books:
            print(f"  Warning: No chapters found for {work_id}")
            continue

        # Parse translation based on work type
        if work_dir_name == 'Völsunga_saga':
            trans_chapters = parse_volsunga_translation(trans_path)
            # Create a mapping of chapter number -> translation text
            trans_map = {ch_num: text for ch_num, text in trans_chapters}
            match_by = 'number'
        elif work_dir_name == 'Grettis_Saga':
            trans_chapters = parse_grettis_translation(trans_path)
            # Create a mapping of chapter number -> translation text
            trans_map = {ch_num: text for ch_num, text in trans_chapters}
            match_by = 'number'
        elif work_dir_name == 'Sæmundar-Edda':
            trans_map = parse_poetic_edda_translation(trans_path)
            match_by = 'label'  # Match by poem name (book label)
        elif work_dir_name == 'Snorra-Edda':
            trans_map = parse_prose_edda_translation(trans_path)
            match_by = 'label'  # Match by section name (book label)
        else:
            print(f"  Warning: Unknown work type: {work_dir_name}")
            continue

        if not trans_map:
            print(f"  Warning: No chapters/poems parsed from {work_dir_name} translation")
            continue

        work_segments = 0
        work_lookups = 0

        # Get books with label for matching
        cursor.execute("""
            SELECT id, book_number, line_count, label
            FROM books
            WHERE work_id = ?
            ORDER BY book_number
        """, (work_id,))
        books_with_label = cursor.fetchall()

        # Match translation chapters to book chapters
        for book_id, book_num, line_count, label in books_with_label:
            trans_text = None

            if match_by == 'number':
                if book_num in trans_map:
                    trans_text = trans_map[book_num]
            else:
                # Match by label (poem/section name)
                # Try exact match first
                if label in trans_map:
                    trans_text = trans_map[label]
                else:
                    # Try case-insensitive match and partial match
                    label_lower = label.lower()
                    for key, text in trans_map.items():
                        if key.lower() == label_lower:
                            trans_text = text
                            break
                        # For Prose Edda, label is like "Gylfaginning", key might be lowercase
                        if key.lower() in label_lower or label_lower in key.lower():
                            trans_text = text
                            break

            if trans_text and line_count:
                # Insert translation segment
                cursor.execute('''
                    INSERT INTO translation_segments
                    (book_id, start_line, end_line, sequence_number, translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, 1, line_count, 1, trans_text, translator))

                segment_id = cursor.lastrowid
                work_segments += 1

                # Create translation_lookup entries
                for line_num in range(1, line_count + 1):
                    cursor.execute('''
                        INSERT INTO translation_lookup (book_id, line_number, segment_id)
                        VALUES (?, ?, ?)
                    ''', (book_id, line_num, segment_id))
                    work_lookups += 1

        if work_segments > 0:
            works_with_trans.append(work_dir_name)
            total_segments += work_segments
            total_lookups += work_lookups
            print(f"  {work_dir_name}: {work_segments} chapters with translations")

    # Update has_translations for the author if any translations were added
    if works_with_trans:
        cursor.execute("UPDATE authors SET has_translations = 1 WHERE id = 'norse_traditional'")

    conn.commit()

    print(f"  Total: {total_segments} translation segments, {total_lookups} lookup entries")
    return total_segments


def compress_database(db_path, zip_path):
    """Compress database to ZIP"""
    print(f"Compressing database to {zip_path}...")

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
    print("Creating Old Norse Database")
    print("=" * 60)

    # Clone/update repositories
    print("\n--- Fetching Source Data ---")
    clone_repositories()

    # Download translations
    download_translations()

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate texts
    print("\n--- Populating Texts ---")
    text_stats = populate_texts(conn)

    # Populate translations
    print("\n--- Populating Translations ---")
    trans_count = populate_translations(conn)

    # Populate dictionary
    print("\n--- Populating Dictionary ---")
    dict_count = populate_dictionary(conn)

    # Populate treebank morphology
    print("\n--- Populating Morphology from Treebank ---")
    morph_count = populate_treebank_morphology(conn)

    # Populate normalization patterns
    print("\n--- Adding Normalization Patterns ---")
    pattern_count = populate_normalization_patterns(conn)

    conn.close()

    # Compress
    print("\n--- Compressing ---")
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE CREATION COMPLETE")
    print("=" * 60)
    print(f"Works: {text_stats['works']}")
    print(f"Chapters: {text_stats['chapters']}")
    print(f"Lines: {text_stats['lines']}")
    print(f"Words: {text_stats['words']}")
    print(f"Translation segments: {trans_count}")
    print(f"Dictionary entries: {dict_count}")
    print(f"Morphology mappings: {morph_count}")
    print(f"Normalization patterns: {pattern_count}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
