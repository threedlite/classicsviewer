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

    # Check for chapter_*.txt files
    chapter_files = sorted(
        [f for f in os.listdir(work_dir) if f.startswith('chapter_') and f.endswith('.txt')],
        key=lambda x: int(re.search(r'chapter_(\d+)', x).group(1)) if re.search(r'chapter_(\d+)', x) else 0
    )

    if chapter_files:
        for f in chapter_files:
            text_files.append((os.path.join(work_dir, f), f.replace('.txt', '').replace('_', ' ').title()))
        return text_files

    # Check for subdirectories with txt_files/complete.txt (like Edda poems)
    for item in sorted(os.listdir(work_dir)):
        item_path = os.path.join(work_dir, item)
        if os.path.isdir(item_path):
            # Check for txt_files/complete.txt
            complete_path = os.path.join(item_path, 'txt_files', 'complete.txt')
            if os.path.exists(complete_path):
                text_files.append((complete_path, item))
            else:
                # Check for any .txt file in subdirectory
                for f in os.listdir(item_path):
                    if f.endswith('.txt'):
                        text_files.append((os.path.join(item_path, f), item))
                        break

    # Check for direct .txt files
    if not text_files:
        for f in sorted(os.listdir(work_dir)):
            if f.endswith('.txt'):
                text_files.append((os.path.join(work_dir, f), f.replace('.txt', '')))

    return text_files


def parse_text_file(filepath):
    """Parse a text file into lines"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into lines, filter empty lines
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
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

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate texts
    print("\n--- Populating Texts ---")
    text_stats = populate_texts(conn)

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
    print(f"Dictionary entries: {dict_count}")
    print(f"Morphology mappings: {morph_count}")
    print(f"Normalization patterns: {pattern_count}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
