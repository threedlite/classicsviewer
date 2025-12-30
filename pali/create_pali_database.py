#!/usr/bin/env python3
"""
Create Pali Canon database for ClassicsViewer

Sources:
- Pali text: SuttaCentral bilara-data (CC0 - Public Domain)
- English translation: Bhikkhu Sujato (CC0 - Public Domain)

License: CC0 (Public Domain - commercial use allowed)

Usage:
  python3 create_pali_database.py
"""

import sqlite3
import json
import os
import zipfile
import subprocess
from pathlib import Path
from collections import defaultdict

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data-sources")
BILARA_DIR = os.path.join(DATA_DIR, "bilara-data")
DB_PATH = os.path.join(SCRIPT_DIR, "pali_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "pali_texts.db.zip")

# GitHub repository
BILARA_REPO = "https://github.com/suttacentral/bilara-data.git"
BILARA_BRANCH = "published"

# Nikaya definitions (collection, name, abbreviation)
NIKAYAS = [
    ("dn", "Dīgha Nikāya", "Long Discourses"),
    ("mn", "Majjhima Nikāya", "Middle-Length Discourses"),
    ("sn", "Saṁyutta Nikāya", "Connected Discourses"),
    ("an", "Aṅguttara Nikāya", "Numerical Discourses"),
    ("kn", "Khuddaka Nikāya", "Minor Collection"),
]

# Khuddaka Nikaya texts to include
KHUDDAKA_TEXTS = [
    "dhp",   # Dhammapada
    "ud",    # Udāna
    "iti",   # Itivuttaka
    "snp",   # Sutta Nipāta
    "thag",  # Theragāthā
    "thig",  # Therīgāthā
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


def clone_bilara_data():
    """Clone or update the bilara-data repository"""
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(BILARA_DIR):
        print(f"Updating bilara-data repository...")
        subprocess.run(
            ["git", "-C", BILARA_DIR, "fetch", "origin", BILARA_BRANCH],
            check=True
        )
        subprocess.run(
            ["git", "-C", BILARA_DIR, "checkout", BILARA_BRANCH],
            check=True
        )
        subprocess.run(
            ["git", "-C", BILARA_DIR, "pull", "origin", BILARA_BRANCH],
            check=True
        )
    else:
        print(f"Cloning bilara-data repository (branch: {BILARA_BRANCH})...")
        subprocess.run(
            ["git", "clone", "--branch", BILARA_BRANCH, "--single-branch",
             "--depth", "1", BILARA_REPO, BILARA_DIR],
            check=True
        )

    print(f"  Repository ready at: {BILARA_DIR}")


def find_sutta_files(nikaya_id):
    """Find all sutta files for a nikaya"""
    root_dir = os.path.join(BILARA_DIR, "root", "pli", "ms", "sutta", nikaya_id)
    trans_dir = os.path.join(BILARA_DIR, "translation", "en", "sujato", "sutta", nikaya_id)

    if not os.path.exists(root_dir):
        print(f"  Warning: Root directory not found: {root_dir}")
        return []

    suttas = []

    # Walk through root directory to find all JSON files
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith("_root-pli-ms.json"):
                root_file = os.path.join(dirpath, filename)

                # Construct corresponding translation file path
                rel_path = os.path.relpath(dirpath, root_dir)
                trans_filename = filename.replace("_root-pli-ms.json", "_translation-en-sujato.json")
                trans_file = os.path.join(trans_dir, rel_path, trans_filename)

                # Extract sutta ID from filename (e.g., "mn1" from "mn1_root-pli-ms.json")
                sutta_id = filename.replace("_root-pli-ms.json", "")

                suttas.append({
                    'id': sutta_id,
                    'root_file': root_file,
                    'trans_file': trans_file if os.path.exists(trans_file) else None
                })

    # Sort by sutta ID
    suttas.sort(key=lambda x: natural_sort_key(x['id']))
    return suttas


def natural_sort_key(s):
    """Natural sorting key for sutta IDs like mn1, mn2, mn10, mn100"""
    import re
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def parse_sutta(root_file, trans_file):
    """Parse a sutta from its JSON files"""
    with open(root_file, 'r', encoding='utf-8') as f:
        root_data = json.load(f)

    trans_data = {}
    if trans_file and os.path.exists(trans_file):
        with open(trans_file, 'r', encoding='utf-8') as f:
            trans_data = json.load(f)

    # Convert to aligned segments
    segments = []
    for segment_id, pali_text in root_data.items():
        english_text = trans_data.get(segment_id, "")
        segments.append({
            'id': segment_id,
            'pali': pali_text,
            'english': english_text
        })

    return segments


def get_sutta_title(segments, sutta_id):
    """Extract sutta title from first segment"""
    if segments:
        # First segment usually contains the title
        first_pali = segments[0]['pali'] if segments else sutta_id
        first_english = segments[0]['english'] if segments else ""
        return first_pali, first_english
    return sutta_id, ""


def tokenize_pali(text):
    """Tokenize Pali text into words"""
    import re
    # Remove punctuation except for Pali-specific characters
    text = re.sub(r'[^\w\sāīūṃṁṅñṭḍṇḷĀĪŪṂṀṄÑṬḌṆḶ]', ' ', text, flags=re.UNICODE)
    words = text.split()
    return [w.strip().lower() for w in words if w.strip()]


def populate_database(conn):
    """Parse suttas and populate the database"""
    cursor = conn.cursor()

    # Insert author (Buddha / Early Buddhist Texts)
    print("Inserting author...")
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('buddha', 'Early Buddhist Texts', 'Pāli Canon', 'pali', 1))

    # Statistics
    total_lines = 0
    total_words = 0
    total_translations = 0
    total_suttas = 0

    # Process each nikaya
    for nikaya_id, nikaya_name, nikaya_english in NIKAYAS:
        print(f"\n--- Processing {nikaya_name} ({nikaya_english}) ---")

        # For Khuddaka, only process specific texts
        if nikaya_id == "kn":
            suttas = []
            for kn_text in KHUDDAKA_TEXTS:
                kn_suttas = find_sutta_files(os.path.join(nikaya_id, kn_text))
                if not kn_suttas:
                    # Try without subdirectory
                    kn_root = os.path.join(BILARA_DIR, "root", "pli", "ms", "sutta", nikaya_id)
                    if os.path.exists(kn_root):
                        for item in os.listdir(kn_root):
                            if item.startswith(kn_text):
                                kn_suttas.extend(find_sutta_files(os.path.join(nikaya_id, item)))
                suttas.extend(kn_suttas)
        else:
            suttas = find_sutta_files(nikaya_id)

        if not suttas:
            print(f"  No suttas found for {nikaya_id}")
            continue

        # Insert work for this nikaya
        work_id = f"pali_{nikaya_id}"
        cursor.execute('''
            INSERT INTO works (id, author_id, title, title_alt, title_english, type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            work_id,
            'buddha',
            nikaya_name,
            nikaya_id.upper(),
            nikaya_english,
            'sutta',
            f'{nikaya_english} of the Pāli Canon'
        ))

        # Process each sutta
        for sutta_num, sutta in enumerate(suttas, 1):
            sutta_id = sutta['id']

            try:
                segments = parse_sutta(sutta['root_file'], sutta['trans_file'])
            except Exception as e:
                print(f"  Error parsing {sutta_id}: {e}")
                continue

            if not segments:
                continue

            pali_title, english_title = get_sutta_title(segments, sutta_id)
            book_id = f"{work_id}.{sutta_id}"

            # Insert book (sutta)
            line_count = len(segments)
            cursor.execute('''
                INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                book_id,
                work_id,
                sutta_num,
                sutta_id.upper(),
                1,
                line_count,
                line_count
            ))

            # Insert segments as lines
            for line_num, segment in enumerate(segments, 1):
                pali_text = segment['pali']
                english_text = segment['english']

                # Insert Pali text line
                cursor.execute('''
                    INSERT INTO text_lines (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, line_num, line_num, pali_text))

                # Insert words
                words = tokenize_pali(pali_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word, book_id, line_num, line_num, word_pos))
                    total_words += 1

                # Insert English translation if available
                if english_text:
                    cursor.execute('''
                        INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (book_id, line_num, line_num, line_num, english_text, 'Sujato'))
                    total_translations += 1

            total_lines += line_count
            total_suttas += 1

            if total_suttas % 100 == 0:
                print(f"  Processed {total_suttas} suttas...")

        print(f"  {nikaya_id}: {len(suttas)} suttas")
        conn.commit()

    return {
        'suttas': total_suttas,
        'lines': total_lines,
        'words': total_words,
        'translations': total_translations
    }


def generate_statistical_dictionary(conn):
    """Generate dictionary entries from parallel text alignment using TF-IDF.

    This creates a 'Statistical Dictionary' by analyzing which English words
    appear disproportionately often in translations of lines containing each
    Pali word, using TF-IDF weighting to filter out common words.
    """
    import re
    from collections import Counter
    import math

    cursor = conn.cursor()

    print("Generating Statistical Dictionary from parallel texts...")

    # Get total document count for IDF
    cursor.execute('SELECT COUNT(*) FROM translation_segments')
    total_docs = cursor.fetchone()[0]

    if total_docs == 0:
        print("  No translations found, skipping statistical dictionary")
        return 0

    # Build document frequency for all English words (for IDF calculation)
    print("  Building IDF from all translations...")
    cursor.execute('SELECT translation_text FROM translation_segments')
    doc_freq = Counter()

    for (text,) in cursor.fetchall():
        if text:
            for w in set(re.findall(r'[a-zA-Z]+', text.lower())):
                doc_freq[w] += 1

    # Build word → translation mapping in memory (single query)
    print("  Building word-to-translation mapping...")
    cursor.execute('''
        SELECT w.word, ts.translation_text
        FROM words w
        JOIN translation_segments ts ON ts.book_id = w.book_id
            AND w.line_number >= ts.start_line
            AND w.line_number <= COALESCE(ts.end_line, ts.start_line)
        WHERE ts.translation_text IS NOT NULL
    ''')

    word_translations = defaultdict(list)
    row_count = 0
    for word, trans_text in cursor.fetchall():
        word_translations[word].append(trans_text)
        row_count += 1
        if row_count % 500000 == 0:
            print(f"    Processed {row_count} word-translation pairs...")

    print(f"  Loaded {row_count} word-translation pairs for {len(word_translations)} unique words")

    # Compute stems and group words by stem
    print("  Grouping words by stem...")
    stem_to_words = defaultdict(set)
    for word in word_translations.keys():
        if len(word) >= 3:
            # Compute stem
            if len(word) <= 4:
                stem = word
            elif len(word) <= 6:
                stem = word[:-1]
            else:
                stem = word[:-2]
            stem_to_words[stem].add(word)

    # Filter to stems with 20+ total occurrences
    stem_counts = {}
    for stem, words in stem_to_words.items():
        total = sum(len(word_translations[w]) for w in words)
        if total >= 20:
            stem_counts[stem] = total

    print(f"  Found {len(stem_counts)} stems with 20+ occurrences")

    # Process each stem and compute TF-IDF glosses
    print("  Computing TF-IDF glosses for each stem...")
    dict_count = 0
    lemma_count = 0

    for stem in sorted(stem_counts.keys(), key=lambda s: -stem_counts[s]):
        if len(stem) < 3:
            continue

        # Aggregate translations for all words with this stem
        translations = []
        for word in stem_to_words[stem]:
            translations.extend(word_translations[word])

        if len(translations) < 10:
            continue

        # Count term frequency in these translations
        tf = Counter()
        for text in translations:
            if text:
                for w in re.findall(r'[a-zA-Z]+', text.lower()):
                    tf[w] += 1

        if not tf:
            continue

        # Compute TF-IDF scores
        tfidf = {}
        num_docs = len(translations)
        for word, freq in tf.items():
            tf_score = freq / num_docs
            idf_score = math.log(total_docs / (1 + doc_freq.get(word, 0)))
            tfidf[word] = tf_score * idf_score

        # Get top 3 words
        top_words = sorted(tfidf.items(), key=lambda x: -x[1])[:3]

        if not top_words:
            continue

        # Format as dictionary entry
        glosses = [w for w, score in top_words]
        entry_plain = ', '.join(glosses)

        # Insert dictionary entry
        cursor.execute('''
            INSERT INTO dictionary_entries
            (headword, headword_normalized_ultra, language, entry_plain, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (stem, stem.lower(), 'pali', entry_plain, 'Statistical Dictionary'))
        dict_count += 1

        # Add lemma_map entries for all word forms with this stem
        for word_form in stem_to_words[stem]:
            cursor.execute('''
                INSERT OR IGNORE INTO lemma_map
                (word_form, word_form_normalized_ultra, lemma, confidence, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (word_form, word_form.lower(), stem, 0.8, 'Statistical Dictionary'))
            lemma_count += 1

    conn.commit()
    print(f"  Created {dict_count} dictionary entries")
    print(f"  Created {lemma_count} lemma mappings")

    return dict_count


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
    print("Creating Pali Canon Database")
    print("=" * 60)

    # Clone/update bilara-data
    print("\n--- Fetching Source Data ---")
    clone_bilara_data()

    # Create database
    print("\n--- Creating Database ---")
    conn = create_database(DB_PATH)

    # Populate database
    print("\n--- Populating Database ---")
    stats = populate_database(conn)

    # Generate statistical dictionary from parallel texts
    print("\n--- Generating Statistical Dictionary ---")
    dict_count = generate_statistical_dictionary(conn)
    stats['dictionary_entries'] = dict_count

    conn.close()

    # Compress
    print("\n--- Compressing ---")
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE CREATION COMPLETE")
    print("=" * 60)
    print(f"Suttas: {stats['suttas']}")
    print(f"Pali segments: {stats['lines']}")
    print(f"Words: {stats['words']}")
    print(f"English translations: {stats['translations']}")
    print(f"Statistical Dictionary entries: {stats['dictionary_entries']}")
    print(f"\nOutput: {ZIP_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
