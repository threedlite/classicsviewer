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
MAX_LINE_SIZE = 2000  # Display limit - lines longer than this won't render in the app

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
    # Prose Edda - separate works with different translation sources
    'Snorra-Edda/Gylfaginning': {
        'url': 'https://www.gutenberg.org/cache/epub/14726/pg14726.txt',  # Same as Poetic Edda (contains "Younger Eddas")
        'path': os.path.join(DATA_DIR, 'poetic_edda_translation.txt'),
        'translator': 'Benjamin Thorpe (1866)',
        'type': 'section',  # Section-aligned
    },
    'Snorra-Edda/Prologus': {
        'url': 'https://www.gutenberg.org/cache/epub/14726/pg14726.txt',
        'path': os.path.join(DATA_DIR, 'poetic_edda_translation.txt'),
        'translator': 'Benjamin Thorpe (1866)',
        'type': 'section',
    },
    # Skáldskaparmál: No public domain translation available in chapter-aligned format
    # Háttatal: No translation available (highly technical verse forms)
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
    # Prose Edda - split into separate works for proper citation and translation alignment
    ("Snorra-Edda/Gylfaginning", "Gylfaginning", "Gylfaginning (Prose Edda)", "prose"),
    ("Snorra-Edda/Prologus", "Prologus", "Prologue (Prose Edda)", "prose"),
    ("Snorra-Edda/skaaldskaparmaal.txt", "Skáldskaparmál", "Skáldskaparmál (Prose Edda)", "poetry"),
    ("Snorra-Edda/haattatal.txtl", "Háttatal", "Háttatal (Prose Edda)", "poetry"),
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
        trans_url = trans_info.get('url')

        if trans_url is None:
            continue

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
    by splitting long prose into sentences. Ensures no line exceeds MAX_LINE_SIZE.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into lines, filter empty lines
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # Split long lines to ensure none exceed MAX_LINE_SIZE
            chunks = split_long_text(line)
            lines.extend(chunks)

    return lines


def parse_poetic_edda_stanzas(filepath):
    """Parse a Poetic Edda poem into numbered stanzas.

    The source files have the structure:
    - Speaker tags like "Alvíss kvað:" (Alvis said:)
    - Numbered stanzas: "1.", "2.", "3.", etc.
    - Multiple verse lines per stanza

    Returns list of (stanza_number, speaker, stanza_text) tuples.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    stanzas = []
    current_stanza_num = None
    current_stanza_speaker = None  # Speaker for the current stanza being built
    pending_speaker = None  # Speaker for the NEXT stanza
    current_lines = []

    # Pattern to match stanza numbers like "1.", "2.", "35."
    stanza_pattern = re.compile(r'^(\d+)\.$')
    # Pattern to match speaker tags like "Alvíss kvað:" or "Þórr kvað:"
    # Speaker names are short (1-3 words), no periods/commas (which indicate prose)
    speaker_pattern = re.compile(r'^([A-ZÞÐÁÉÍÓÚÝÆÖa-zþðáéíóúýæö][A-ZÞÐÁÉÍÓÚÝÆÖa-zþðáéíóúýæö\s]{0,40})\s+kvað:$')

    for line in content.split('\n'):
        line = line.strip()

        # Skip empty lines, title line, and separator lines
        if not line or line.startswith('#') or line.startswith('-'):
            continue

        # Check for speaker tag - this sets the speaker for the NEXT stanza
        speaker_match = speaker_pattern.match(line)
        if speaker_match:
            pending_speaker = speaker_match.group(1)
            continue

        # Check for stanza number
        stanza_match = stanza_pattern.match(line)
        if stanza_match:
            # Save previous stanza if exists (with its own speaker)
            if current_stanza_num is not None and current_lines:
                stanza_text = ' '.join(current_lines)
                stanzas.append((current_stanza_num, current_stanza_speaker, stanza_text))
                current_lines = []

            # Start new stanza - use pending speaker
            current_stanza_num = int(stanza_match.group(1))
            current_stanza_speaker = pending_speaker
            pending_speaker = None  # Reset pending speaker
            continue

        # Regular verse line - add to current stanza
        if current_stanza_num is not None:
            # Remove surrounding quotes if present
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            elif line.startswith('"'):
                line = line[1:]
            elif line.endswith('"'):
                line = line[:-1]
            current_lines.append(line)

    # Add final stanza
    if current_stanza_num is not None and current_lines:
        stanza_text = ' '.join(current_lines)
        stanzas.append((current_stanza_num, current_stanza_speaker, stanza_text))

    return stanzas


def parse_prose_edda_sections(filepath):
    """Parse a Prose Edda source file into numbered sections.

    The source files (gylfaginning.txt, etc.) have the structure:
    - Section headers like "1. Frá Gylfa konungi ok Gefjuni."
    - Prose content between sections
    - Embedded verse stanzas (standalone "1.", "2.", etc.) which are PART of the prose

    Returns list of (section_number, section_title, section_text) tuples.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = []
    current_section_num = None
    current_section_title = None
    current_lines = []

    # Pattern to match section headers: "1. Title starting with capital"
    # Must start with number, dot, space, then capitalized word with non-ASCII chars
    section_pattern = re.compile(r'^(\d+)\.\s+([A-ZÞÁÉÍÓÚÝÆÖ].*)$')

    for line in content.split('\n'):
        line = line.strip()

        # Skip empty lines at the beginning
        if not line and current_section_num is None:
            continue

        # Check for section header
        section_match = section_pattern.match(line)
        if section_match:
            # Save previous section if exists
            if current_section_num is not None and current_lines:
                section_text = ' '.join(current_lines)
                sections.append((current_section_num, current_section_title, section_text))
                current_lines = []

            # Start new section
            current_section_num = int(section_match.group(1))
            current_section_title = section_match.group(2)
            continue

        # Add content to current section (including embedded verses)
        if current_section_num is not None and line:
            current_lines.append(line)

    # Add final section
    if current_section_num is not None and current_lines:
        section_text = ' '.join(current_lines)
        sections.append((current_section_num, current_section_title, section_text))

    return sections


def parse_skaaldskaparmaal_chapters(filepath):
    """Parse Skáldskaparmál into numbered chapters.

    Skáldskaparmál has numbered chapters (sections) like:
      "1. Ægir sækir heim æsi."
      "27. Friggjarkenningar."

    Each chapter contains prose and/or embedded verses.
    Returns list of (chapter_num, chapter_title, content_lines) tuples.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    current_chapter_num = None
    current_chapter_title = None
    current_lines = []

    # Pattern to match chapter headers: "27. Friggjarkenningar." (number, period, title)
    chapter_pattern = re.compile(r'^(\d+)\.\s+([A-ZÞÁÉÍÓÚÝÆÖ].+)$')

    for line in content.split('\n'):
        line_stripped = line.strip()

        # Check for chapter header
        chapter_match = chapter_pattern.match(line_stripped)
        if chapter_match:
            # Save previous chapter if exists
            if current_chapter_num is not None and current_lines:
                chapters.append((current_chapter_num, current_chapter_title, current_lines))

            # Start new chapter
            current_chapter_num = int(chapter_match.group(1))
            current_chapter_title = chapter_match.group(2).rstrip('.')
            current_lines = []
            continue

        # Skip empty lines before first chapter
        if current_chapter_num is None:
            continue

        # Add line to current chapter (preserve structure)
        if line_stripped:
            current_lines.append(line_stripped)
        elif current_lines:
            # Keep paragraph breaks as empty strings for formatting
            current_lines.append('')

    # Add final chapter
    if current_chapter_num is not None and current_lines:
        # Remove trailing empty lines
        while current_lines and current_lines[-1] == '':
            current_lines.pop()
        chapters.append((current_chapter_num, current_chapter_title, current_lines))

    return chapters


def parse_haattatal_chapters(filepath):
    """Parse Háttatal into numbered verse chapters.

    Háttatal has numbered verses with prose commentary.
    Each verse becomes a chapter, containing the verse and surrounding prose.

    Returns list of (verse_num, content_lines) tuples.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    current_verse_num = None
    current_lines = []
    pending_prose = []  # Prose before current verse

    # Pattern to match verse numbers: "27." on its own line
    verse_pattern = re.compile(r'^(\d+)\.$')
    # Pattern to match Roman numeral section markers (skip these)
    roman_pattern = re.compile(r'^[IVXLCDM]+\.$')

    for line in content.split('\n'):
        line_stripped = line.strip()

        # Skip Roman numeral section markers
        if roman_pattern.match(line_stripped):
            continue

        # Check for verse number
        verse_match = verse_pattern.match(line_stripped)
        if verse_match:
            # Save previous chapter if exists
            if current_verse_num is not None:
                # Remove trailing empty lines
                while current_lines and current_lines[-1] == '':
                    current_lines.pop()
                if current_lines:
                    chapters.append((current_verse_num, current_lines))

            # Start new chapter with any pending prose
            current_verse_num = int(verse_match.group(1))
            current_lines = list(pending_prose)  # Copy pending prose
            pending_prose = []
            continue

        # Skip empty lines before first verse
        if current_verse_num is None:
            # Accumulate prose before first verse for context
            if line_stripped:
                pending_prose.append(line_stripped)
            continue

        # Add line to current chapter
        if line_stripped:
            current_lines.append(line_stripped)
        elif current_lines:
            # Keep paragraph breaks
            current_lines.append('')

    # Add final chapter
    if current_verse_num is not None and current_lines:
        while current_lines and current_lines[-1] == '':
            current_lines.pop()
        if current_lines:
            chapters.append((current_verse_num, current_lines))

    return chapters


def parse_younger_eddas_translation(filepath):
    """Parse the Younger Eddas section of poetic_edda_translation.txt.

    The Younger Eddas section starts after "THE YOUNGER EDDAS OF STURLESON."
    It contains numbered sections like "1. King Gylfi ruled...", "2. King Gylfi was renowned..."

    Returns dict of {section_num: translation_text}.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {}
    current_section_num = None
    current_lines = []

    in_younger_eddas = False
    past_deluding_of_gylfi = False

    # Pattern to match numbered sections starting a paragraph
    section_pattern = re.compile(r'^(\d+)\.\s+(.+)')

    for line in content.split('\n'):
        line_stripped = line.strip()

        # Detect actual start of Younger Eddas content (not table of contents)
        # Must see "THE DELUDING OF GYLFI" which is the first actual section header
        if not in_younger_eddas:
            if line_stripped == 'THE YOUNGER EDDAS OF STURLESON.':
                in_younger_eddas = True
            continue

        # Need to see "THE DELUDING OF GYLFI." (exact section header) to start collecting
        # This avoids matching the TOC entry "The Deluding of Gylfi          256"
        if not past_deluding_of_gylfi:
            if line_stripped.upper() == 'THE DELUDING OF GYLFI.':
                past_deluding_of_gylfi = True
            continue

        # Detect end of text (stop at footnotes, glossary, or project gutenberg footer)
        if re.match(r'^(FOOTNOTES:|GLOSSARY\.|SIEGFRIED AWAKENS|\*\*\*\s*END OF|END OF THE PROJECT)', line_stripped, re.IGNORECASE):
            if current_section_num is not None and current_lines:
                sections[current_section_num] = ' '.join(current_lines)
            break

        # Check for numbered section start (must be at start of line and look like prose)
        section_match = section_pattern.match(line_stripped)
        if section_match:
            # The content after the number should look like prose (not verse numbers like "1." on its own)
            rest = section_match.group(2)
            # Skip leading quote if present
            rest_check = rest.lstrip('"\'')
            # Verify it's prose (starts with capital, has multiple words)
            if rest_check and rest_check[0].isupper() and len(rest.split()) > 2:
                # Save previous section
                if current_section_num is not None and current_lines:
                    sections[current_section_num] = ' '.join(current_lines)
                    current_lines = []

                current_section_num = int(section_match.group(1))
                # Include the rest of the first line as content
                current_lines.append(rest)
                continue

        # Regular content line
        if current_section_num is not None and line_stripped:
            # Skip obvious non-translation content
            if line_stripped.startswith('[Footnote'):
                continue
            # Skip ALL CAPS section headers (like "IDUNA AND HER APPLES.")
            if re.match(r'^[A-Z\s\'\-\.]+$', line_stripped) and len(line_stripped) > 5:
                continue
            # Remove footnote markers like [125], [126]
            clean_line = re.sub(r'\[\d+\]', '', line_stripped)
            if clean_line.strip():
                current_lines.append(clean_line.strip())

    # Add final section
    if current_section_num is not None and current_lines:
        sections[current_section_num] = ' '.join(current_lines)

    print(f"    Found {len(sections)} sections in Younger Eddas translation")
    return sections


def parse_thorpe_glossary(filepath):
    """Parse the glossary from the end of poetic_edda_translation.txt.

    The glossary contains etymological entries for Norse names and terms.
    Format: HEADWORD, definition text (may span multiple lines)

    Returns list of (headword, definition) tuples with headwords converted
    to mixed case (first letter uppercase).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    current_headword = None
    current_definition_lines = []

    in_glossary = False

    # Pattern to match glossary headwords (uppercase word(s) followed by comma)
    # Examples: "ÆGIR or OEGIR, horror..." or "BALDUR, prop. BALDR..."
    headword_pattern = re.compile(r'^([A-ZÆØÅÞÐ][A-ZÆØÅÞÐ\s,]+),\s*(.+)$')

    for line in content.split('\n'):
        line_stripped = line.strip()

        # Detect start of glossary
        if line_stripped == 'GLOSSARY.':
            in_glossary = True
            continue

        # Detect end of glossary (appendix content starts)
        if in_glossary and line_stripped.startswith('SIEGFRIED AWAKENS'):
            # Save last entry
            if current_headword and current_definition_lines:
                definition = ' '.join(current_definition_lines)
                entries.append((current_headword, definition))
            break

        if not in_glossary:
            continue

        # Skip empty lines but finalize current entry
        if not line_stripped:
            continue

        # Check for new headword entry
        match = headword_pattern.match(line_stripped)
        if match:
            # Save previous entry
            if current_headword and current_definition_lines:
                definition = ' '.join(current_definition_lines)
                entries.append((current_headword, definition))
                current_definition_lines = []

            # Parse new headword - convert to mixed case
            raw_headword = match.group(1).strip()
            # Handle variants like "ALFADIR, or ALFODUR" -> take first one
            if ',' in raw_headword:
                raw_headword = raw_headword.split(',')[0].strip()
            # Also handle "or" variants like "ÆGIR or OEGIR"
            if ' or ' in raw_headword.lower():
                raw_headword = raw_headword.split(' or ')[0].strip()
                raw_headword = raw_headword.split(' OR ')[0].strip()

            # Convert to mixed case (capitalize first letter, rest lowercase)
            current_headword = raw_headword.capitalize()

            # Start definition with rest of first line
            current_definition_lines = [match.group(2)]
        elif current_headword:
            # Continuation of current definition
            current_definition_lines.append(line_stripped)

    return entries


def split_long_text(text, max_size=None):
    """Split text into chunks that don't exceed MAX_LINE_SIZE.

    Tries to split at sentence boundaries first, then at word boundaries.
    Returns a list of text chunks, each under max_size characters.
    """
    if max_size is None:
        max_size = MAX_LINE_SIZE

    if len(text) <= max_size:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_size:
            chunks.append(remaining)
            break

        # Try to find a sentence boundary within the limit
        # Look for period/!/? followed by space
        best_split = -1
        for match in re.finditer(r'[.!?]\s+', remaining[:max_size]):
            best_split = match.end()

        if best_split > 0:
            chunks.append(remaining[:best_split].strip())
            remaining = remaining[best_split:].strip()
        else:
            # No sentence boundary - split at last space before limit
            space_pos = remaining[:max_size].rfind(' ')
            if space_pos > 0:
                chunks.append(remaining[:space_pos].strip())
                remaining = remaining[space_pos:].strip()
            else:
                # No space - hard cut (shouldn't happen with normal text)
                chunks.append(remaining[:max_size])
                remaining = remaining[max_size:]

    return [c for c in chunks if c]


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
        work_path = os.path.join(TEXTS_DIR, dir_name)

        if not os.path.exists(work_path):
            print(f"  Warning: Work path not found: {dir_name}")
            continue

        # Generate clean work_id from the final path component
        # Note: .txtl must be replaced before .txt to avoid leaving trailing 'l'
        path_parts = dir_name.replace('/', '_').replace('.txtl', '').replace('.txt', '')
        work_id = f"norse_{path_parts.lower().replace(' ', '_')}"

        # Check if this is a single file (Skáldskaparmál, Háttatal) vs directory
        is_single_file = os.path.isfile(work_path)

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

        # Get text files - handle single file vs directory
        if is_single_file:
            text_files = [(work_path, title)]
        else:
            text_files = get_text_files(work_path)

        if not text_files:
            print(f"  Warning: No text files found for {dir_name}")
            continue

        work_lines = 0
        work_words = 0
        work_chapters = 0

        # Process each chapter/section
        for chapter_num, (filepath, label) in enumerate(text_files, 1):
            book_id = f"{work_id}.{chapter_num}"

            # Use stanza-based parsing for Poetic Edda poems
            if dir_name == "Sæmundar-Edda":
                stanzas = parse_poetic_edda_stanzas(filepath)

                if not stanzas:
                    continue

                # Get max stanza number for line_count
                max_stanza = max(s[0] for s in stanzas)

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
                    max_stanza,
                    len(stanzas)
                ))

                # Insert stanzas as lines
                for stanza_num, speaker, stanza_text in stanzas:
                    cursor.execute('''
                        INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, speaker)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (book_id, stanza_num, stanza_num, stanza_text, speaker))

                    # Insert words
                    words = tokenize_norse(stanza_text)
                    for word_pos, word in enumerate(words, 1):
                        cursor.execute('''
                            INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (word, book_id, stanza_num, stanza_num, word_pos))
                        work_words += 1

                work_lines += len(stanzas)
                total_chapters += 1
                work_chapters += 1
            elif 'skaaldskaparmaal' in dir_name.lower():
                # Skáldskaparmál - parse into numbered chapters
                # This is a single-file work that produces multiple chapters
                chapters = parse_skaaldskaparmaal_chapters(filepath)

                if not chapters:
                    continue

                # Process each chapter as a separate book
                for ch_num, ch_title, ch_lines in chapters:
                    ch_book_id = f"{work_id}.{ch_num}"

                    # Join lines into paragraphs (empty strings mark paragraph breaks)
                    formatted_lines = []
                    current_para = []
                    for line in ch_lines:
                        if line == '':
                            if current_para:
                                formatted_lines.append(' '.join(current_para))
                                current_para = []
                        else:
                            current_para.append(line)
                    if current_para:
                        formatted_lines.append(' '.join(current_para))

                    if not formatted_lines:
                        continue

                    # Split any long lines to ensure none exceed MAX_LINE_SIZE
                    final_lines = []
                    for text in formatted_lines:
                        final_lines.extend(split_long_text(text))

                    line_count = len(final_lines)

                    # Insert book (chapter)
                    cursor.execute('''
                        INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ch_book_id,
                        work_id,
                        ch_num,
                        f"Chapter {ch_num}: {ch_title}",
                        1,
                        line_count,
                        line_count
                    ))

                    # Insert lines
                    for line_num, line_text in enumerate(final_lines, 1):
                        cursor.execute('''
                            INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, speaker)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (ch_book_id, line_num, line_num, line_text, None))

                        # Insert words
                        words = tokenize_norse(line_text)
                        for word_pos, word in enumerate(words, 1):
                            cursor.execute('''
                                INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (word, ch_book_id, line_num, line_num, word_pos))
                            work_words += 1

                    work_lines += line_count
                    total_chapters += 1
                    work_chapters += 1

                # Skip the outer loop's chapter counting since we handled all chapters
                continue
            elif 'haattatal' in dir_name.lower():
                # Háttatal - parse into numbered verse chapters
                # This is a single-file work that produces multiple chapters
                chapters = parse_haattatal_chapters(filepath)

                if not chapters:
                    continue

                # Process each verse as a separate chapter (book)
                for verse_num, verse_lines in chapters:
                    verse_book_id = f"{work_id}.{verse_num}"

                    # Join lines into paragraphs
                    formatted_lines = []
                    current_para = []
                    for line in verse_lines:
                        if line == '':
                            if current_para:
                                formatted_lines.append(' '.join(current_para))
                                current_para = []
                        else:
                            current_para.append(line)
                    if current_para:
                        formatted_lines.append(' '.join(current_para))

                    if not formatted_lines:
                        continue

                    # Split any long lines to ensure none exceed MAX_LINE_SIZE
                    final_lines = []
                    for text in formatted_lines:
                        final_lines.extend(split_long_text(text))

                    line_count = len(final_lines)

                    # Insert book (chapter = verse number)
                    cursor.execute('''
                        INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        verse_book_id,
                        work_id,
                        verse_num,
                        f"Verse {verse_num}",
                        1,
                        line_count,
                        line_count
                    ))

                    # Insert lines
                    for line_num, line_text in enumerate(final_lines, 1):
                        cursor.execute('''
                            INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, speaker)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (verse_book_id, line_num, line_num, line_text, None))

                        # Insert words
                        words = tokenize_norse(line_text)
                        for word_pos, word in enumerate(words, 1):
                            cursor.execute('''
                                INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (word, verse_book_id, line_num, line_num, word_pos))
                            work_words += 1

                    work_lines += line_count
                    total_chapters += 1
                    work_chapters += 1

                # Skip the outer loop since we handled all chapters
                continue
            elif 'gylfaginning' in dir_name.lower() or 'prologus' in dir_name.lower():
                # Chapter-based parsing for Gylfaginning and Prologus (each file = one chapter)
                # These have prose paragraphs leading to numbered verses
                # Use verse numbers as line numbers for proper citation
                with open(filepath, 'r', encoding='utf-8') as f:
                    chapter_text = f.read().strip()

                if not chapter_text:
                    continue

                # Extract chapter number from filename (chapter_1.txt -> 1)
                match = re.search(r'chapter_(\d+)', filepath)
                if match:
                    chapter_section_num = int(match.group(1))
                else:
                    chapter_section_num = chapter_num

                # Split chapter into paragraphs (blank lines separate them)
                paragraphs = re.split(r'\n\s*\n', chapter_text)

                # Check if this chapter has numbered verses
                has_verses = False
                for para in paragraphs:
                    first_line = para.strip().split('\n')[0].strip() if para.strip() else ''
                    if re.match(r'^(\d+)\.\s*$', first_line):
                        has_verses = True
                        break

                lines_dict = {}  # line_num -> full text

                if has_verses:
                    # Build lines: verse number -> (prose_before, verse_text)
                    current_prose = []
                    first_verse_num = None

                    for para in paragraphs:
                        para = para.strip()
                        if not para:
                            continue

                        # Check if this paragraph is a numbered verse (starts with "N." on its own line)
                        first_line = para.split('\n')[0].strip()
                        verse_match = re.match(r'^(\d+)\.\s*$', first_line)

                        if verse_match:
                            # This is a verse
                            verse_num = int(verse_match.group(1))
                            if first_verse_num is None:
                                first_verse_num = verse_num

                            verse_lines = para.split('\n')[1:]  # Skip the number line
                            verse_text = ' / '.join(line.strip() for line in verse_lines if line.strip())

                            # Combine prose before this verse with the verse
                            if current_prose:
                                prose_text = ' '.join(current_prose)
                                full_text = f"{prose_text} {verse_num}. {verse_text}"
                            else:
                                full_text = f"{verse_num}. {verse_text}"

                            lines_dict[verse_num] = full_text
                            current_prose = []
                        else:
                            # Prose paragraph - accumulate for next verse
                            para_text = ' '.join(line.strip() for line in para.split('\n') if line.strip())
                            current_prose.append(para_text)

                    # Handle any trailing prose (after last verse)
                    if current_prose:
                        if lines_dict:
                            # Append to last verse
                            last_num = max(lines_dict.keys())
                            lines_dict[last_num] += ' ' + ' '.join(current_prose)
                        else:
                            lines_dict[1] = ' '.join(current_prose)
                else:
                    # Pure prose chapter (no verses) - break into sentences
                    # Combine all paragraphs into one text block first
                    full_text = ' '.join(
                        ' '.join(line.strip() for line in para.split('\n') if line.strip())
                        for para in paragraphs if para.strip()
                    )
                    # Split by sentence (period followed by space and capital letter)
                    # Handle Old Norse capitals: A-Z plus Þ, Ð, Á, É, Í, Ó, Ú, Ý, Æ, Ö
                    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÞÐÁÉÍÓÚÝÆÖ])', full_text)
                    for i, sentence in enumerate(sentences, 1):
                        sentence = sentence.strip()
                        if sentence:
                            lines_dict[i] = sentence

                if not lines_dict:
                    continue

                # Convert to sorted list and split any long lines
                sorted_lines = [text for _, text in sorted(lines_dict.items())]
                final_lines = []
                for text in sorted_lines:
                    # Split long lines to ensure none exceed MAX_LINE_SIZE
                    final_lines.extend(split_long_text(text))

                # Use sequential 1-based line numbers
                line_count = len(final_lines)

                # Insert book (chapter)
                cursor.execute('''
                    INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    book_id,
                    work_id,
                    chapter_num,
                    label,
                    1,  # Always start at 1
                    line_count,
                    line_count
                ))

                # Insert each line with sequential line numbers
                for line_num, line_text in enumerate(final_lines, 1):
                    cursor.execute('''
                        INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, speaker)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (book_id, line_num, line_num, line_text, None))

                    # Insert words
                    words = tokenize_norse(line_text)
                    for word_pos, word in enumerate(words, 1):
                        cursor.execute('''
                            INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (word, book_id, line_num, line_num, word_pos))
                        work_words += 1

                work_lines += line_count
                total_chapters += 1
                work_chapters += 1
            else:
                # Standard line-based parsing for sagas
                lines = parse_text_file(filepath)

                if not lines:
                    continue

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
                work_chapters += 1

        total_lines += work_lines
        total_words += work_words
        total_works += 1

        print(f"  {title}: {work_chapters} chapters, {work_lines} lines, {work_words} words")

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


def populate_glossary_entries(conn):
    """Add glossary entries from Thorpe's Poetic Edda translation.

    Only adds entries if a headword doesn't already exist in the dictionary.
    These are etymological notes for Norse names and mythological terms.
    """
    cursor = conn.cursor()

    # Parse glossary from the translation file
    glossary_path = TRANSLATIONS['Sæmundar-Edda']['path']
    if not os.path.exists(glossary_path):
        print("  Warning: Glossary source not found")
        return 0

    print("Adding glossary entries from Thorpe's translation...")
    entries = parse_thorpe_glossary(glossary_path)
    print(f"  Parsed {len(entries)} glossary entries")

    # Get existing headwords (case-insensitive)
    cursor.execute("SELECT LOWER(headword) FROM dictionary_entries")
    existing = {row[0] for row in cursor.fetchall()}

    added = 0
    skipped = 0

    for headword, definition in entries:
        # Check if entry already exists (case-insensitive)
        if headword.lower() in existing:
            skipped += 1
            continue

        # Normalize headword
        headword_normalized = normalize_norse(headword)

        # Insert new dictionary entry
        cursor.execute('''
            INSERT INTO dictionary_entries (headword, headword_normalized_ultra, language, entry_plain, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (headword, headword_normalized, 'norse', definition, 'Thorpe Glossary'))

        # Add to lemma_map for lookup
        cursor.execute('''
            INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (headword, headword_normalized, headword, 1.0, 'Thorpe Glossary'))

        # Add lowercase variant
        headword_lower = headword.lower()
        if headword_lower != headword:
            cursor.execute('''
                INSERT INTO lemma_map (word_form, word_form_normalized_ultra, lemma, confidence, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (headword_lower, headword_normalized, headword, 1.0, 'Thorpe Glossary'))

        existing.add(headword.lower())  # Track for duplicates within glossary
        added += 1

    conn.commit()
    print(f"  Added {added} new glossary entries, skipped {skipped} existing")

    return added


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


def parse_saga_chapters(filepath, work_name):
    """Parse saga translation into chapters with Roman numeral headings.

    Works for Gutenberg translations that use "CHAPTER I", "CHAPTER II", etc.
    Returns list of (chapter_num, chapter_text) tuples.
    """
    print(f"  Parsing {work_name} translation...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapters = []
    current_chapter = None
    current_lines = []
    in_text = False
    in_title = False

    # Chapter pattern: "CHAPTER I" or "CHAPTER XLII." with optional period/title
    chapter_pattern = re.compile(r'^CHAPTER\s+([IVXLC]+)\b', re.IGNORECASE)

    for line in content.split('\n'):
        line_stripped = line.strip()

        # Detect end of text - appendix or project gutenberg footer
        if in_text and re.match(r'^(APPENDIX|END OF THE PROJECT|\*\*\*\s*END OF)', line_stripped, re.IGNORECASE):
            if current_chapter is not None and current_lines:
                chapters.append((current_chapter, '\n'.join(current_lines)))
            break

        # Check for chapter heading
        chapter_match = chapter_pattern.match(line_stripped)
        if chapter_match:
            # Save previous chapter
            if current_chapter is not None and current_lines:
                chapters.append((current_chapter, '\n'.join(current_lines)))
                current_lines = []

            in_text = True
            in_title = True
            roman = chapter_match.group(1).upper()
            current_chapter = roman_to_int(roman)
            continue

        # Skip chapter title lines (until blank line or content starts)
        if in_title:
            if not line_stripped:
                in_title = False
            continue

        if not in_text:
            continue

        # Collect text (skip ALL CAPS title lines)
        if current_chapter is not None and line_stripped:
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
    """Parse Poetic Edda translation into stanza-aligned translations.

    Scans for poem title patterns and extracts stanza-numbered translations.
    Returns dict of {old_norse_name: {stanza_number: translation_text}}.

    Excludes:
    - FOOTNOTES sections
    - Everything after "THE YOUNGER EDDAS"
    - Preface, introduction, and table of contents
    """
    print(f"  Parsing Poetic Edda translation (stanza-aligned)...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    poems = {}  # {poem_name: {stanza_num: text}}
    current_poem = None
    current_stanza_num = None
    current_stanza_lines = []
    current_speaker = None  # Track speaker for dialogues
    in_text = False
    in_footnotes = False
    past_preamble = False  # Skip table of contents

    # Pattern to match stanza numbers like "1.", "2.", "35." at start of line
    stanza_pattern = re.compile(r'^(\d+)\.\s+(.*)$')
    # Pattern for speaker tags like "_Alvis_." or "_Vingthor_."
    speaker_pattern = re.compile(r'^_([^_]+)_\.$')

    lines = content.split('\n')

    for line in lines:
        line_stripped = line.strip()
        line_upper = line_stripped.upper()

        # Skip preamble/table of contents by detecting first "VÖLUSPÂ" title
        # The actual poem section starts with "VÖLUSPÂ. THE VALA'S PROPHECY."
        if not past_preamble:
            if 'VÖLUSPÂ' in line_upper and 'VALA' in line_upper:
                past_preamble = True
                # Continue to process this line as a poem title
            else:
                continue

        # Stop at THE YOUNGER EDDAS
        if 'THE YOUNGER EDDAS OF STURLESON' in line_upper:
            # Save current stanza before stopping
            if current_poem and current_stanza_num is not None and current_stanza_lines:
                if current_poem not in poems:
                    poems[current_poem] = {}
                poems[current_poem][current_stanza_num] = ' '.join(current_stanza_lines)
            break

        # Detect FOOTNOTES section - skip until next poem title
        if line_upper.startswith('FOOTNOTE'):
            in_footnotes = True
            # Save current stanza before footnotes
            if current_poem and current_stanza_num is not None and current_stanza_lines:
                if current_poem not in poems:
                    poems[current_poem] = {}
                poems[current_poem][current_stanza_num] = ' '.join(current_stanza_lines)
                current_stanza_num = None
                current_stanza_lines = []
            continue

        # Check if line contains a poem title pattern
        # Only match title lines (start with "THE" or "VÖLUSPÂ", are mostly uppercase)
        # Skip lines that start with a number (stanza lines like "3. Alvis...")
        matched_poem = None
        if line_stripped and not line_stripped[0].isdigit():
            # Title lines typically start with "THE LAY OF..." or poem name
            is_title_line = (line_upper.startswith('THE ') or
                             line_upper.startswith('VÖLUSPÂ') or
                             line_upper.startswith("ODIN'S") or
                             (len(line_stripped) < 80 and line_stripped.isupper()))
            if is_title_line:
                for norse_name, pattern in POETIC_EDDA_MAP.items():
                    if pattern in line_upper:
                        matched_poem = norse_name
                        in_text = True
                        in_footnotes = False  # Exit footnotes section
                        break

        if matched_poem:
            # Save previous stanza
            if current_poem and current_stanza_num is not None and current_stanza_lines:
                if current_poem not in poems:
                    poems[current_poem] = {}
                poems[current_poem][current_stanza_num] = ' '.join(current_stanza_lines)
                current_stanza_lines = []
                current_stanza_num = None

            current_poem = matched_poem
            continue

        # Skip footnotes section
        if in_footnotes:
            continue

        # Capture speaker tags for dialogues (e.g., "_Alvis_.", "_Vingthor_.")
        speaker_match = speaker_pattern.match(line_stripped)
        if speaker_match:
            current_speaker = speaker_match.group(1)
            continue

        # Skip empty lines
        if not line_stripped:
            continue

        # Not in any poem yet
        if not in_text or not current_poem:
            continue

        # Check for stanza number at start of line
        stanza_match = stanza_pattern.match(line_stripped)
        if stanza_match:
            # Save previous stanza
            if current_stanza_num is not None and current_stanza_lines:
                if current_poem not in poems:
                    poems[current_poem] = {}
                poems[current_poem][current_stanza_num] = ' '.join(current_stanza_lines)
                current_stanza_lines = []

            current_stanza_num = int(stanza_match.group(1))

            # Include speaker tag if present (appears before stanza number in dialogues)
            if current_speaker:
                current_stanza_lines.append(f"[{current_speaker}]")
                current_speaker = None  # Reset after using

            # Rest of line is part of this stanza
            rest_of_line = stanza_match.group(2).strip()
            if rest_of_line:
                # Remove footnote markers like [33]
                rest_of_line = re.sub(r'\[\d+\]', '', rest_of_line).strip()
                if rest_of_line:
                    current_stanza_lines.append(rest_of_line)
            continue

        # Regular text line - add to current stanza
        if current_stanza_num is not None:
            # Remove footnote markers like [33]
            clean_line = re.sub(r'\[\d+\]', '', line_stripped).strip()
            if clean_line:
                current_stanza_lines.append(clean_line)

    # Save final stanza
    if current_poem and current_stanza_num is not None and current_stanza_lines:
        if current_poem not in poems:
            poems[current_poem] = {}
        poems[current_poem][current_stanza_num] = ' '.join(current_stanza_lines)

    # Count total stanzas
    total_stanzas = sum(len(stanzas) for stanzas in poems.values())
    print(f"    Found {len(poems)} poems with {total_stanzas} total stanzas")
    return poems


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

        # Get the work_id from the database - match the generation in populate_texts
        path_parts = work_dir_name.replace('/', '_').replace('.txt', '').replace('.txtl', '')
        work_id = f"norse_{path_parts.lower().replace(' ', '_')}"

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
        trans_type = trans_info.get('type', 'chapter')
        section_aligned = False
        stanza_aligned = False

        if work_dir_name in ('Völsunga_saga', 'Grettis_Saga'):
            # Sagas with Roman numeral chapter headings
            trans_chapters = parse_saga_chapters(trans_path, work_dir_name)
            trans_map = {ch_num: text for ch_num, text in trans_chapters}
            match_by = 'number'
        elif work_dir_name == 'Sæmundar-Edda':
            trans_map = parse_poetic_edda_translation(trans_path)
            match_by = 'stanza'
            stanza_aligned = True
        elif 'Gylfaginning' in work_dir_name or 'Prologus' in work_dir_name:
            # Use Younger Eddas section from Thorpe translation
            trans_map = parse_younger_eddas_translation(trans_path)
            match_by = 'section'
            section_aligned = True
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

        # Handle Poetic Edda stanza-aligned translations
        if stanza_aligned:
            for book_id, book_num, line_count, label in books_with_label:
                # Find matching poem translations
                poem_stanzas = None
                if label in trans_map:
                    poem_stanzas = trans_map[label]
                else:
                    # Try case-insensitive match
                    label_lower = label.lower()
                    for key, stanzas in trans_map.items():
                        if key.lower() == label_lower:
                            poem_stanzas = stanzas
                            break

                if poem_stanzas:
                    # Insert one segment per stanza, aligned by stanza number
                    for stanza_num, trans_text in poem_stanzas.items():
                        cursor.execute('''
                            INSERT INTO translation_segments
                            (book_id, start_line, end_line, sequence_number, translation_text, translator)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (book_id, stanza_num, stanza_num, stanza_num, trans_text, translator))

                        segment_id = cursor.lastrowid
                        work_segments += 1

                        # Create translation_lookup entry for this stanza
                        cursor.execute('''
                            INSERT INTO translation_lookup (book_id, line_number, segment_id)
                            VALUES (?, ?, ?)
                        ''', (book_id, stanza_num, segment_id))
                        work_lookups += 1
        elif section_aligned:
            # Handle chapter-aligned translations (Gylfaginning/Prologus/Skáldskaparmál)
            # Each chapter (book) gets one translation that covers all its lines
            matched_chapters = 0
            missing_chapters = 0

            for book_id, book_num, line_count, label in books_with_label:
                # Look up translation by chapter number (book_num)
                if book_num in trans_map:
                    trans_text = trans_map[book_num]
                    matched_chapters += 1
                else:
                    trans_text = "[Translation not available for this chapter]"
                    missing_chapters += 1

                # Get actual line count from text_lines
                cursor.execute("SELECT MAX(line_number) FROM text_lines WHERE book_id = ?", (book_id,))
                max_line = cursor.fetchone()[0] or 1

                # Insert one translation segment covering all lines in this chapter
                cursor.execute('''
                    INSERT INTO translation_segments
                    (book_id, start_line, end_line, sequence_number, translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, 1, max_line, book_num, trans_text, translator))

                segment_id = cursor.lastrowid
                work_segments += 1

                # Create translation_lookup entries for all lines in this chapter
                for line_num in range(1, max_line + 1):
                    cursor.execute('''
                        INSERT INTO translation_lookup (book_id, line_number, segment_id)
                        VALUES (?, ?, ?)
                    ''', (book_id, line_num, segment_id))
                    work_lookups += 1

            total_chapters = matched_chapters + missing_chapters
            if missing_chapters > 0:
                print(f"    {matched_chapters}/{total_chapters} chapters with translations ({missing_chapters} missing)")
        else:
            # Match translation chapters to book chapters (non-stanza-aligned)
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

    # Add glossary entries from Thorpe translation
    print("\n--- Adding Glossary Entries ---")
    glossary_count = populate_glossary_entries(conn)

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
    print(f"Glossary entries added: {glossary_count}")
    print(f"Morphology mappings: {morph_count}")
    print(f"Normalization patterns: {pattern_count}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
