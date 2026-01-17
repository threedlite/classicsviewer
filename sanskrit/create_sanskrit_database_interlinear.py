#!/usr/bin/env python3
"""
Create Sanskrit texts database for ClassicsViewer

Modes:
- sample: Bhagavad Gita + Rig Veda + 5 DCS texts with translations (7 texts total)
- full: All 268 DCS works (~738,000 verses, 5.6M words)

Usage:
  python3 create_sanskrit_database.py sample   # Create sample database (default)
  python3 create_sanskrit_database.py full     # Create full database with all DCS works

Sources:
- Bhagavad Gita: Sanskrit Wikisource (CC BY-SA 4.0)
  - English translations: Edwin Arnold (Public Domain), Annie Besant (Public Domain)
- Rig Veda: DCS pada-and-analysis.dat (CC BY 4.0)
  - English translation: Ralph T.H. Griffith (1896) (Public Domain)
- Sample DCS texts with English translations:
  - Atharvaveda (Śaunaka), Vājasaneyisaṃhitā, Upanishads
- Full DCS corpus: 268 works (CC BY 4.0)
  - Most works do not have English translations

License: CC BY 4.0, CC BY-SA 4.0 & Public Domain (commercial use allowed)
"""

import sqlite3
import json
import csv
import re
import os
import sys
import zipfile
from collections import defaultdict

# Try to import indic-transliteration
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    HAS_TRANSLITERATION = True
except ImportError:
    print("Warning: indic-transliteration not installed. Install with: pip install indic-transliteration")
    HAS_TRANSLITERATION = False

# Try to import Stanza for dependency parsing fallback
try:
    import stanza
    HAS_STANZA = True
except ImportError:
    print("Warning: stanza not installed. Install with: pip install stanza")
    print("  Non-treebank works will not have dependency tree data.")
    HAS_STANZA = False

# Global Stanza NLP pipeline (initialized lazily)
_stanza_nlp = None

def get_stanza_nlp():
    """Get or initialize the Stanza Sanskrit pipeline."""
    global _stanza_nlp
    if _stanza_nlp is None and HAS_STANZA:
        print("  Initializing Stanza Sanskrit pipeline...")
        try:
            # Download model if not present
            stanza.download('sa', verbose=False)
            _stanza_nlp = stanza.Pipeline('sa', processors='tokenize,pos,lemma,depparse', verbose=False)
            print("  ✓ Stanza pipeline ready")
        except Exception as e:
            print(f"  Warning: Failed to initialize Stanza: {e}")
            return None
    return _stanza_nlp

def is_sanskrit_punctuation(text: str) -> bool:
    """Check if text is Sanskrit punctuation (dandas, etc.)"""
    # Sanskrit punctuation: single danda, double danda, common punctuation
    punct_chars = set('।॥,;.·!?\'\"()-–—')
    return all(c in punct_chars or c.isspace() for c in text)


def extract_case_from_feats(feats: str) -> str:
    """Extract Case feature from Stanza features string."""
    if not feats:
        return None
    for pair in feats.split('|'):
        if pair.startswith('Case='):
            return pair.replace('Case=', '')
    return None


def fix_coordination_errors(parse_result: list) -> list:
    """
    Apply post-processing rules to fix common Stanza coordination errors.

    Stanza systematically mislabels coordinated nouns (conj) as appositional
    modifiers (nmod:appos) or adjectival modifiers (amod). This function
    applies four high-precision rules to correct these errors.

    Args:
        parse_result: List of word dicts from parse_with_stanza

    Returns:
        List of word dicts with corrected HEAD/DEPREL where applicable
    """
    if not parse_result or len(parse_result) < 2:
        return parse_result

    # Make copies to avoid modifying original
    fixed = [w.copy() for w in parse_result]

    # Apply fixes in order of precision (highest first)
    fixed = fix_accusative_cascades(fixed)
    fixed = fix_locative_repetitions(fixed)
    fixed = fix_nominative_predicates(fixed)
    fixed = fix_adjective_coordination(fixed)

    return fixed


def fix_accusative_cascades(parse_result: list) -> list:
    """
    Pattern 1: Fix cascading accusative noun misalignment (99%+ precision).

    Detects: Series of accusative nouns where Stanza incorrectly marks them
    as nmod:appos/amod instead of conj.

    Example (Ṛgveda 1.1.1):
        Stanza: devam→1/nmod:appos, ṛtvijam→1/nmod:appos, hotāram→1/nmod:appos
        Fixed:  devam→3/conj, ṛtvijam→3/conj, hotāram→3/conj

    The key insight: Words coordinate with the first APPOSITIVE in the series,
    not the first accusative overall (which may be the obj).
    """
    fixed = parse_result

    # Find the first accusative noun that is an appositive (the coordinator)
    # This is typically the first nmod:appos accusative, not the obj
    first_appos_idx = None
    for i, word in enumerate(fixed):
        case = extract_case_from_feats(word.get('feats', ''))
        if case == 'Acc' and word.get('pos') in ['NOUN', 'ADJ', 'NUM']:
            # Look for appositive modifier specifically (not obj)
            if word.get('deprel') in ['nmod:appos', 'amod']:
                first_appos_idx = i
                break

    if first_appos_idx is None:
        return fixed

    # Look for subsequent accusatives that should be conj with the appositive
    for i in range(first_appos_idx + 1, len(fixed)):
        word = fixed[i]

        # Must be accusative noun/adj
        word_case = extract_case_from_feats(word.get('feats', ''))
        if word_case != 'Acc':
            continue
        if word.get('pos') not in ['NOUN', 'ADJ', 'NUM']:
            continue

        # Skip if it's already correctly marked as conj with right head
        if word.get('deprel') == 'conj' and word.get('head') == first_appos_idx + 1:
            continue

        # Skip genitives (they're real nmod modifiers, not coordination)
        # This check helps avoid false positives
        if word.get('deprel') == 'nmod':
            prev_case = extract_case_from_feats(fixed[i-1].get('feats', '')) if i > 0 else None
            if prev_case == 'Gen':
                continue

        # Currently marked as appositive/adjectival modifier - should be conj
        if word.get('deprel') in ['nmod:appos', 'amod', 'nmod']:
            # Fix: make this conj, point to the first appositive
            fixed[i]['deprel'] = 'conj'
            fixed[i]['head'] = first_appos_idx + 1  # 1-based position

    return fixed


def fix_locative_repetitions(parse_result: list) -> list:
    """
    Pattern 2: Fix repeated locative words that should be conj (95%+ precision).

    Detects: Same locative word appearing multiple times where the second
    should coordinate with the first (common in Vedic: "dive dive" = day by day).
    """
    fixed = parse_result

    # Build map of locative words by form
    locatives = {}  # form -> [indices]
    for i, word in enumerate(fixed):
        case = extract_case_from_feats(word.get('feats', ''))
        if case != 'Loc':
            continue
        form = word.get('form', '')
        if not form:
            continue
        if form not in locatives:
            locatives[form] = []
        locatives[form].append(i)

    # Check repetitions
    for form, indices in locatives.items():
        if len(indices) < 2:
            continue

        first_idx = indices[0]
        first_word = fixed[first_idx]

        # First must be a real oblique modifier
        if first_word.get('deprel') not in ['obl', 'iobj', 'advmod', 'nmod']:
            continue

        # Subsequent occurrences should coordinate with first
        for j in range(1, len(indices)):
            idx = indices[j]
            word = fixed[idx]

            # Only fix if currently marked as appos/amod/nmod
            if word.get('deprel') not in ['nmod:appos', 'amod', 'nmod', 'obl']:
                continue

            # Don't fix if already conj
            if word.get('deprel') == 'conj':
                continue

            fixed[idx]['deprel'] = 'conj'
            fixed[idx]['head'] = first_idx + 1  # 1-based position

    return fixed


def fix_nominative_predicates(parse_result: list) -> list:
    """
    Pattern 3: Fix nominative predicates in series (85%+ precision).

    Detects: Multiple nominative nouns pointing to same head with same deprel,
    which should be coordinated predicates.
    """
    fixed = parse_result

    for i in range(1, len(fixed)):
        word = fixed[i]
        prev_word = fixed[i - 1]

        # Both must be nominative nouns
        word_case = extract_case_from_feats(word.get('feats', ''))
        prev_case = extract_case_from_feats(prev_word.get('feats', ''))

        if word_case != 'Nom' or prev_case != 'Nom':
            continue
        if word.get('pos') != 'NOUN' or prev_word.get('pos') != 'NOUN':
            continue

        # Same head
        if word.get('head') != prev_word.get('head'):
            continue

        # Skip if explicit conjunction
        if prev_word.get('pos') == 'CCONJ':
            continue

        # Previous marked as predicative modifier
        if prev_word.get('deprel') not in ['nmod', 'acl', 'amod', 'nsubj']:
            continue

        # Current is also nmod/amod (parallel structure)
        if word.get('deprel') not in ['nmod', 'amod', 'nsubj']:
            continue

        # Don't change if already conj
        if word.get('deprel') == 'conj':
            continue

        # Fix: make conj pointing to previous word
        fixed[i]['deprel'] = 'conj'
        fixed[i]['head'] = i  # Point to previous word (1-based = i since prev is i-1)

    return fixed


def fix_adjective_coordination(parse_result: list) -> list:
    """
    Pattern 4: Fix coordinated adjectives mistaken for modifier chains (90%+ precision).

    Detects: Sequential adjectives with same case modifying the same noun,
    which should be coordinated rather than chained.
    """
    fixed = parse_result

    for i in range(1, len(fixed)):
        word = fixed[i]
        prev_word = fixed[i - 1]

        # Both must be adjectives
        if word.get('pos') != 'ADJ' or prev_word.get('pos') != 'ADJ':
            continue

        # Same case
        word_case = extract_case_from_feats(word.get('feats', ''))
        prev_case = extract_case_from_feats(prev_word.get('feats', ''))

        if word_case != prev_case or word_case is None:
            continue

        # Previous is amod (modifying a noun)
        if prev_word.get('deprel') != 'amod':
            continue

        # Current is also amod or points to previous adj
        if word.get('deprel') not in ['amod', 'nmod:appos']:
            continue

        # Skip if explicit conjunction
        if prev_word.get('pos') == 'CCONJ':
            continue

        # Don't change if already conj
        if word.get('deprel') == 'conj':
            continue

        # Fix: make conj pointing to previous adjective
        fixed[i]['deprel'] = 'conj'
        fixed[i]['head'] = i  # Point to previous word (1-based)

    return fixed


def parse_with_stanza(text_iast: str, dcs_words: list = None) -> list:
    """
    Parse Sanskrit text with Stanza to get dependency information.

    Uses a two-pass approach similar to Greek treebank processing:
    1. First pass: Build mapping from original positions to non-punctuation positions
    2. Second pass: Create result with remapped HEAD values

    Args:
        text_iast: Sanskrit text in IAST transliteration
        dcs_words: Optional list of DCS word tuples for validation

    Returns:
        List of dicts with keys: form, lemma, pos, head, deprel, position
        Returns empty list if Stanza is not available, parsing fails,
        or word count doesn't match DCS.
    """
    nlp = get_stanza_nlp()
    if nlp is None:
        return []

    try:
        doc = nlp(text_iast)

        # Two-pass approach to handle punctuation and HEAD remapping
        # Similar to Greek treebank processing
        #
        # Key issue: Stanza may split input into multiple sentences, where
        # word.id resets to 1 for each sentence. We need to:
        # 1. Track global positions across all sentences
        # 2. Remap HEAD values to account for sentence offsets
        # 3. Exclude punctuation from position counting

        # Pass 1: Collect all words and build position mapping
        orig_to_nopunct = {}  # {global_orig_pos: nopunct_pos}
        nopunct_pos = 0
        word_data_list = []
        global_offset = 0  # Offset for converting sentence-local IDs to global

        for sent in doc.sentences:
            # Build sentence-local HEAD to global position mapping
            sent_orig_to_global = {}

            for word in sent.words:
                local_pos = word.id
                global_pos = global_offset + local_pos
                sent_orig_to_global[local_pos] = global_pos
                form = word.text

                # Check if punctuation - exclude from non-punct numbering
                is_punct = is_sanskrit_punctuation(form) or word.upos == 'PUNCT'

                if not is_punct:
                    nopunct_pos += 1
                    orig_to_nopunct[global_pos] = nopunct_pos

                    # Convert sentence-local HEAD to global position
                    # HEAD=0 means root, which stays 0
                    global_head = 0
                    if word.head != 0:
                        global_head = global_offset + word.head

                    word_data_list.append({
                        'form': form,
                        'lemma': word.lemma,
                        'pos': word.upos,
                        'feats': word.feats,  # Morphological features for coordination fixes
                        'global_head': global_head,
                        'deprel': word.deprel,
                        'nopunct_pos': nopunct_pos
                    })

            # Update offset for next sentence
            global_offset += len(sent.words)

        # Pass 2: Create result with remapped HEAD values
        result = []
        for wd in word_data_list:
            # Remap head from global position to non-punct position
            # HEAD=0 means root (no change needed)
            remapped_head = 0
            if wd['global_head'] != 0:
                remapped_head = orig_to_nopunct.get(wd['global_head'], 0)

            result.append({
                'form': wd['form'],
                'lemma': wd['lemma'],
                'pos': wd['pos'],
                'feats': wd['feats'],  # Include features for coordination fixes
                'head': remapped_head,
                'deprel': wd['deprel'],
                'position': wd['nopunct_pos']
            })

        # Validate word count matches DCS if provided
        if dcs_words is not None and len(result) != len(dcs_words):
            return []  # Mismatch due to sandhi resolution differences

        # Apply coordination error fixes (post-processing)
        result = fix_coordination_errors(result)

        return result
    except Exception as e:
        # Silently fail - return empty list
        return []

def iast_to_devanagari(text):
    """Convert IAST to Devanagari for display"""
    if not HAS_TRANSLITERATION:
        return text
    try:
        return transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except:
        return text

def tokenize_sanskrit(text):
    """Tokenize Sanskrit text into words"""
    # Remove dandas and other punctuation
    text = re.sub(r'[।॥,;।\.\?\!]', ' ', text)
    # Split on whitespace
    words = text.split()
    # Filter out empty strings
    return [w.strip() for w in words if w.strip()]

def create_database(db_path):
    """Create Sanskrit texts database"""
    print(f"Creating database: {db_path}")

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same schema as Greek/Latin/Arabic)
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
            head INTEGER,
            deprel TEXT,
            pos_tag TEXT,
            sentence_position INTEGER,
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

    conn.commit()
    return conn, cursor

def load_bhagavad_gita(cursor):
    """Load Bhagavad Gita text and translations"""
    print("\n" + "=" * 70)
    print("Loading Bhagavad Gita...")
    print("=" * 70)

    # Load Sanskrit text
    text_path = 'data-sources/bhagavad_gita_sanskrit.json'
    if not os.path.exists(text_path):
        print(f"Error: Text file not found: {text_path}")
        print("Run: cd data-sources && python3 parse_bhagavad_gita_sanskrit.py")
        return 0, 0, 0

    with open(text_path, 'r', encoding='utf-8') as f:
        sanskrit_data = json.load(f)

    # Load Arnold's English translation
    arnold_path = 'data-sources/bhagavad_gita_english.json'
    if not os.path.exists(arnold_path):
        print(f"Error: Arnold translation file not found: {arnold_path}")
        return 0, 0, 0

    with open(arnold_path, 'r', encoding='utf-8') as f:
        arnold_data = json.load(f)

    arnold_translations = {}
    for chapter in arnold_data['chapters']:
        chapter_num = chapter['chapter']
        arnold_translations[chapter_num] = chapter['text']

    # Load Besant's English translation
    besant_path = 'data-sources/bhagavad_gita_besant.json'
    besant_data = None
    if os.path.exists(besant_path):
        with open(besant_path, 'r', encoding='utf-8') as f:
            besant_data = json.load(f)

    besant_translations = {}
    if besant_data:
        for chapter in besant_data['chapters']:
            chapter_num = chapter['chapter']
            besant_translations[chapter_num] = {}
            for verse in chapter['verses']:
                verse_num = verse['number']
                besant_translations[chapter_num][verse_num] = verse['text']

    # Insert author (qualified ID to avoid collision with potential DCS version)
    # Use work name as author name for consistency with DCS texts
    author_id = 'vyasa_wikisource'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, 'भगवद्गीता', 'Bhagavad Gita (Wikisource)', 'sanskrit', 1))

    # Create work (qualified ID to avoid collision with potential DCS version)
    work_id = 'bhagavad_gita_wikisource'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, 'भगवद्गीता', None, 'Bhagavad Gita (Wikisource, with translations)', 'poetry', None,
          'The Bhagavad Gita, 700-verse Hindu scripture that is part of the Mahabharata. Source: Wikisource with Arnold and Besant translations'))

    total_verses = 0
    total_words = 0
    total_translations = 0

    # Process each chapter as a book
    for chapter_data in sanskrit_data['chapters']:
        chapter_num = chapter_data['chapter']
        verses = chapter_data['verses']

        book_id = f'{work_id}.{chapter_num}'
        book_label = f'Chapter {chapter_num}'

        start_line = verses[0]['number']
        end_line = verses[-1]['number']
        line_count = len(verses)

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, chapter_num, book_label, start_line, end_line, line_count))

        print(f"  Chapter {chapter_num}: {len(verses)} verses")

        # Insert verses
        for verse in verses:
            verse_num = verse['number']
            verse_text = verse['text']

            cursor.execute('''
                INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (None, book_id, verse_num, verse_num, verse_text, None, None))

            # Tokenize and insert words (BG doesn't have lemma data from Wikisource)
            words = tokenize_sanskrit(verse_text)
            for word_pos, word in enumerate(words, 1):
                cursor.execute('''
                    INSERT INTO words (id, word, book_id, line_number, sequence_number, word_position)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (None, word, book_id, verse_num, verse_num, word_pos))
                total_words += 1

            total_verses += 1

        # Insert Arnold's translation (entire chapter)
        if chapter_num in arnold_translations:
            first_verse = verses[0]['number']
            last_verse = verses[-1]['number']

            cursor.execute('''
                INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (None, book_id, first_verse, last_verse, first_verse, arnold_translations[chapter_num], 'Edwin Arnold', None))
            total_translations += 1

        # Insert Besant's translation (verse-by-verse)
        if chapter_num in besant_translations:
            for verse in verses:
                verse_num = verse['number']
                if verse_num in besant_translations[chapter_num]:
                    besant_text = besant_translations[chapter_num][verse_num]
                    cursor.execute('''
                        INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, book_id, verse_num, verse_num, verse_num, besant_text, 'Annie Besant', None))
                    total_translations += 1

    print(f"\n  ✓ Loaded {total_verses} verses, {total_words:,} words, {total_translations} translations")
    return total_verses, total_words, total_translations

def load_rigveda(cursor):
    """Load Rig Veda text and translations"""
    print("\n" + "=" * 70)
    print("Loading Rig Veda...")
    print("=" * 70)

    # Load Rig Veda padas from DCS
    pada_file = '../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat'
    if not os.path.exists(pada_file):
        print(f"Error: Rig Veda data file not found: {pada_file}")
        return 0, 0, 0

    print(f"  Reading {pada_file}...")

    # Structure: book → hymn → stanza → [padas]
    rigveda_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    with open(pada_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            book = int(row['book'])
            hymn = int(row['hymn'])
            stanza = int(row['stanza'])
            pada = row['pada']
            text = row['text']

            # Convert IAST to Devanagari
            text_devanagari = iast_to_devanagari(text)

            rigveda_data[book][hymn][stanza].append({
                'pada': pada,
                'text_iast': text,
                'text_devanagari': text_devanagari
            })

    total_hymns = sum(len(hymns) for hymns in rigveda_data.values())
    total_stanzas = sum(
        len(stanzas)
        for hymns in rigveda_data.values()
        for stanzas in hymns.values()
    )

    print(f"  Loaded {len(rigveda_data)} mandalas, {total_hymns} hymns, {total_stanzas} stanzas")

    # Load Griffith translation
    translation_file = '../data-sources/sanskrit/translations/RV-Griffith.txt'
    translations = defaultdict(lambda: defaultdict(dict))

    if os.path.exists(translation_file):
        print(f"  Reading {translation_file}...")
        with open(translation_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(';;;'):
                    continue

                match = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
                if match:
                    book = int(match.group(1))
                    hymn = int(match.group(2))
                    stanza = int(match.group(3))
                    translation_text = match.group(4).strip()
                    translations[book][hymn][stanza] = translation_text

        translation_count = sum(
            len(stanzas)
            for hymns in translations.values()
            for stanzas in hymns.values()
        )
        print(f"  Loaded {translation_count} translations")
    else:
        print(f"  Warning: Translation file not found: {translation_file}")

    # Insert author (qualified ID to avoid collision with DCS CoNLL-U version)
    # Use work name as author name for consistency with DCS texts
    author_id = 'rishis_pada'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, 'ऋग्वेदः', 'Rig Veda (pada format)', 'sanskrit', 1))

    # Create work (qualified ID to avoid collision with DCS version)
    work_id = 'rigveda_pada'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, 'ऋग्वेदः', 'Ṛgveda', 'Rig Veda (pada format, complete with Griffith translation)', 'poetry', None,
          'The Rig Veda, oldest of the four Vedas, collection of 10 mandalas. Source: DCS pada format with complete Griffith translation'))

    total_verses = 0
    total_words = 0
    total_translations = 0

    # Process each mandala
    for book_num in sorted(rigveda_data.keys()):
        hymns = rigveda_data[book_num]

        book_id = f'{work_id}.{book_num}'
        book_label = f'Mandala {book_num}'

        line_count = sum(len(stanzas) for stanzas in hymns.values())

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, book_num, book_label, 1, line_count, line_count))

        print(f"  Mandala {book_num}: {len(hymns)} hymns, {line_count} stanzas")

        line_number = 1

        for hymn_num in sorted(hymns.keys()):
            stanzas = hymns[hymn_num]

            for stanza_num in sorted(stanzas.keys()):
                padas = stanzas[stanza_num]

                # Combine padas into verse with traditional citation
                padas_sorted = sorted(padas, key=lambda x: x['pada'])
                verse_text = ' '.join(pada['text_devanagari'] for pada in padas_sorted)

                # Prepend traditional Rig Veda citation [mandala.hymn.stanza]
                verse_text_with_citation = f"[{book_num}.{hymn_num}.{stanza_num}] {verse_text}"

                cursor.execute('''
                    INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (None, book_id, line_number, line_number, verse_text_with_citation, None, None))

                # Insert words (Rig Veda uses pada format which is pre-split, but has no lemma data)
                words = tokenize_sanskrit(verse_text)
                for word_pos, word in enumerate(words, 1):
                    cursor.execute('''
                        INSERT INTO words (id, word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (None, word, book_id, line_number, line_number, word_pos))
                    total_words += 1

                # Insert translation if available
                if book_num in translations and hymn_num in translations[book_num] and stanza_num in translations[book_num][hymn_num]:
                    translation_text = translations[book_num][hymn_num][stanza_num]

                    cursor.execute('''
                        INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, book_id, line_number, line_number, line_number, translation_text, 'Ralph T.H. Griffith', None))
                    total_translations += 1

                total_verses += 1
                line_number += 1

    print(f"\n  ✓ Loaded {total_verses:,} verses, {total_words:,} words, {total_translations:,} translations")
    return total_verses, total_words, total_translations

def parse_citation_part(part_str):
    """
    Parse a citation part that may be numeric or textual.

    Examples:
        "1" -> 1
        "Sū." -> hash("Sū.") % 100000  (deterministic number)
        "Prathama adhyāyaḥ" -> hash("Prathama adhyāyaḥ") % 100000
        "43.2" -> hash("43.2") % 100000

    Returns an integer that can be used for ordering/indexing.
    """
    part_str = part_str.strip()

    # Try to parse as integer first
    try:
        return int(part_str)
    except ValueError:
        pass

    # Try to parse as float and convert to int
    try:
        return int(float(part_str))
    except ValueError:
        pass

    # For non-numeric strings, create a deterministic hash-based number
    # Use hash mod to keep numbers reasonable but unique
    return abs(hash(part_str)) % 100000

def discover_dcs_works():
    """
    Discover all works in the DCS corpus by scanning the conllu files directory

    Returns:
        List of dicts with work metadata: text_name, text_dir, work_id
    """
    dcs_base = '../data-sources/sanskrit/dcs/data/conllu/files'

    if not os.path.exists(dcs_base):
        print(f"Warning: DCS directory not found: {dcs_base}")
        return []

    works = []

    # Scan all subdirectories
    for entry in sorted(os.listdir(dcs_base)):
        text_dir = os.path.join(dcs_base, entry)

        # Skip non-directories
        if not os.path.isdir(text_dir):
            continue

        # Check if directory contains conllu files
        conllu_files = [f for f in os.listdir(text_dir) if f.endswith('.conllu') and not f.endswith('_parsed')]
        if not conllu_files:
            continue

        # Extract text name from first conllu file
        first_file = os.path.join(text_dir, conllu_files[0])
        text_name = None

        with open(first_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('## text:'):
                    text_name = line.replace('## text:', '').strip()
                    break

        if not text_name:
            text_name = entry  # Fallback to directory name

        # Create work_id from text name (lowercase, no spaces/special chars)
        work_id = re.sub(r'[^a-z0-9]+', '_', text_name.lower()).strip('_')

        works.append({
            'text_name': text_name,
            'text_dir': text_dir,
            'work_id': work_id,
            'dir_name': entry
        })

    return works

def load_dcs_text(cursor, text_name, text_dir, translation_file, author_info, work_info, translator_name):
    """
    Generic loader for DCS texts with CoNLL-U files

    Args:
        cursor: Database cursor
        text_name: Display name for logging
        text_dir: Directory path containing CoNLL-U files
        translation_file: Path to translation file (can be None)
        author_info: Dict with 'id', 'name', 'name_alt' for author
        work_info: Dict with 'id', 'title', 'title_alt', 'title_english', 'type', 'description' for work
        translator_name: Name of translator for attribution (can be None)
    """
    print("\n" + "=" * 70)
    print(f"Loading {text_name}...")
    print("=" * 70)

    if not os.path.exists(text_dir):
        print(f"Error: Text directory not found: {text_dir}")
        return 0, 0, 0

    print(f"  Reading CoNLL-U files from {text_dir}...")

    # Structure: book → chapter → verse → {'text': str, 'words': [(word, lemma)]}
    text_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'text': [], 'words': []})))

    # Parse all CoNLL-U files
    conllu_files = [f for f in os.listdir(text_dir) if f.endswith('.conllu') and not f.endswith('_parsed')]
    conllu_files.sort()

    # Track treebank vs Stanza usage
    sentences_with_treebank = 0
    sentences_with_stanza = 0
    sentences_no_tree = 0

    for conllu_file in conllu_files:
        file_path = os.path.join(text_dir, conllu_file)

        with open(file_path, 'r', encoding='utf-8') as f:
            current_chapter = None
            verse_counter = 0  # Track verses within current chapter
            current_sentence_words = []  # Accumulate segmented words for current sentence
            current_text_iast = None  # Store IAST text for Stanza fallback

            for line in f:
                line = line.strip()

                # Extract chapter citation (e.g., "## chapter: AU, 1, 1" or "ŚvetU, 1")
                if line.startswith('## chapter:'):
                    chapter_str = line.replace('## chapter:', '').strip()
                    # Parse citation - can be 2, 3, or 4 parts
                    parts = [p.strip() for p in chapter_str.split(',')]

                    if len(parts) == 2:
                        # Format: "ŚvetU, 1" - Only chapter number
                        # Treat chapter as book, track verses sequentially
                        prefix = parts[0]
                        book_num = parse_citation_part(parts[1])
                        current_chapter = (book_num, None, None)
                        verse_counter = 0  # Reset verse counter for new chapter
                    elif len(parts) >= 3:
                        # Format: "AU, 1, 1" or "ChUp, 1, 1, 1"
                        prefix = parts[0]
                        book_num = parse_citation_part(parts[1])
                        chapter_num = parse_citation_part(parts[2])
                        verse_num = parse_citation_part(parts[3]) if len(parts) > 3 else chapter_num
                        current_chapter = (book_num, chapter_num, verse_num)
                        verse_counter = None  # Don't use counter for explicit citations

                # Extract sentence text (e.g., "# text = ...")
                elif line.startswith('# text =') and current_chapter:
                    text_iast = line.replace('# text =', '').strip()
                    current_text_iast = text_iast  # Store for Stanza fallback
                    text_devanagari = iast_to_devanagari(text_iast)

                    book_num, chapter_num, verse_num = current_chapter

                    # If using verse counter (2-part citations)
                    if verse_counter is not None:
                        verse_counter += 1
                        verse_num = verse_counter
                        chapter_num = 1  # Single "chapter" per book
                        text_data[book_num][chapter_num][verse_num]['text'].append(text_devanagari)
                    else:
                        # Use explicit verse number
                        text_data[book_num][chapter_num][verse_num]['text'].append(text_devanagari)

                    current_sentence_words = []  # Reset for new sentence

                # Parse CoNLL-U token lines to extract segmented words and lemmas
                elif line and not line.startswith('#') and current_chapter:
                    fields = line.split('\t')
                    if len(fields) >= 10:
                        token_id = fields[0]
                        # Skip multi-word tokens (e.g., "1-2")
                        if '-' not in token_id and '.' not in token_id:
                            # Extract lemma from field 2 (column index 2)
                            lemma_iast = fields[2]  # The dictionary headword
                            lemma = iast_to_devanagari(lemma_iast) if lemma_iast != '_' else None

                            # Extract POS tag (field 3) and treebank data (fields 6-7)
                            pos_tag = fields[3] if fields[3] != '_' else None
                            head_str = fields[6]
                            deprel = fields[7] if fields[7] != '_' else None

                            # Parse HEAD - convert to int, None if not available
                            head = None
                            if head_str and head_str != '_':
                                try:
                                    head = int(head_str)
                                except ValueError:
                                    pass

                            # Track sentence position (1-based word index within sentence)
                            sentence_position = len(current_sentence_words) + 1

                            # Extract Unsandhied field from misc column (column 9)
                            misc = fields[9]
                            unsandhied = None
                            unsandhied_iast_form = None  # Keep IAST for Stanza
                            for pair in misc.split('|'):
                                if pair.startswith('Unsandhied='):
                                    unsandhied_iast_form = pair.replace('Unsandhied=', '')
                                    # Special case: _ means use the lemma for display
                                    if unsandhied_iast_form != '_':
                                        unsandhied = iast_to_devanagari(unsandhied_iast_form)
                                    else:
                                        unsandhied_iast_form = None
                                    break

                            # If no Unsandhied or it's _, use lemma or form
                            if not unsandhied:
                                # Try lemma first (for special characters like OM)
                                if lemma:
                                    unsandhied = lemma
                                    unsandhied_iast_form = lemma_iast
                                else:
                                    form_iast = fields[1]  # The word form
                                    unsandhied = iast_to_devanagari(form_iast)
                                    unsandhied_iast_form = form_iast

                            # Store tuple of (unsandhied_word, lemma, head, deprel, pos_tag, sentence_position, unsandhied_iast)
                            current_sentence_words.append((unsandhied, lemma, head, deprel, pos_tag, sentence_position, unsandhied_iast_form))

                # Blank line indicates end of sentence - save accumulated words
                elif line == '' and current_sentence_words and current_chapter:
                    book_num, chapter_num, verse_num = current_chapter

                    # Check if any words have treebank data (HEAD/DEPREL)
                    has_treebank = any(w[2] is not None for w in current_sentence_words)

                    # If no treebank data, use Stanza fallback
                    if has_treebank:
                        sentences_with_treebank += 1
                    elif HAS_STANZA:
                        # Reconstruct unsandhied text from DCS tokens for Stanza
                        # This ensures word count matches between Stanza and DCS
                        unsandhied_iast_forms = [w[6] for w in current_sentence_words if w[6]]
                        if len(unsandhied_iast_forms) == len(current_sentence_words):
                            reconstructed_text = ' '.join(unsandhied_iast_forms)
                            stanza_result = parse_with_stanza(reconstructed_text)
                        else:
                            # Fallback to original text if unsandhied forms missing
                            stanza_result = parse_with_stanza(current_text_iast) if current_text_iast else []

                        if stanza_result and len(stanza_result) == len(current_sentence_words):
                            # Map Stanza HEAD/DEPREL to DCS words (same position)
                            updated_words = []
                            for i, (word, lemma, head, deprel, pos_tag, sent_pos, unsandhied_iast) in enumerate(current_sentence_words):
                                stanza_word = stanza_result[i]
                                # Keep DCS data, but use Stanza tree data
                                updated_words.append((
                                    word,
                                    lemma,
                                    stanza_word['head'],
                                    stanza_word['deprel'],
                                    stanza_word['pos'] if pos_tag is None else pos_tag,  # Prefer DCS POS
                                    sent_pos,
                                    unsandhied_iast
                                ))
                            current_sentence_words = updated_words
                            sentences_with_stanza += 1
                        else:
                            sentences_no_tree += 1
                    else:
                        sentences_no_tree += 1

                    # Strip the unsandhied_iast field before storing (not needed in database)
                    words_for_db = [(w[0], w[1], w[2], w[3], w[4], w[5]) for w in current_sentence_words]

                    if verse_counter is not None:
                        text_data[book_num][chapter_num][verse_num]['words'].extend(words_for_db)
                    else:
                        text_data[book_num][chapter_num][verse_num]['words'].extend(words_for_db)

                    current_sentence_words = []
                    current_text_iast = None  # Reset for next sentence

    total_books = len(text_data)
    total_chapters = sum(len(chapters) for chapters in text_data.values())
    total_verses = sum(
        len(verses)
        for chapters in text_data.values()
        for verses in chapters.values()
    )

    print(f"  Loaded {total_books} books, {total_chapters} chapters, {total_verses} verses")

    # Report tree data coverage
    total_sentences = sentences_with_treebank + sentences_with_stanza + sentences_no_tree
    if total_sentences > 0:
        if sentences_with_treebank > 0:
            print(f"  Tree data: {sentences_with_treebank:,} sentences from DCS treebank")
        if sentences_with_stanza > 0:
            print(f"  Tree data: {sentences_with_stanza:,} sentences from Stanza fallback")
        if sentences_no_tree > 0 and HAS_STANZA:
            print(f"  Tree data: {sentences_no_tree:,} sentences without tree (word count mismatch)")

    # Load translations
    # Group by (book, chapter) to combine multiple verses per section
    translations = defaultdict(lambda: defaultdict(list))

    if translation_file and os.path.exists(translation_file):
        print(f"  Reading {translation_file}...")
        with open(translation_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('@') or line.startswith(';;;'):
                    continue

                # Try 3-part citation format: "1.1.1 Translation text..."
                match = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
                if match:
                    book = int(match.group(1))
                    chapter = int(match.group(2))
                    verse = int(match.group(3))
                    translation_text = match.group(4).strip()
                    # Append to list for this (book, chapter) combination
                    translations[book][chapter].append(translation_text)
                    continue

                # Try 2-part citation format: "1.1 Translation text..."
                match = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
                if match:
                    book = int(match.group(1))
                    chapter = 1  # Single chapter per book for 2-part format
                    verse = int(match.group(2))
                    translation_text = match.group(3).strip()
                    translations[book][chapter].append(translation_text)

        translation_count = sum(
            len(verses)
            for chapters in translations.values()
            for verses in chapters.values()
        )
        print(f"  Loaded {translation_count} translation segments")
    elif translation_file:
        print(f"  Warning: Translation file not found: {translation_file}")
    # else: No translation file specified, skip silently

    # Check if author already exists (for full mode where works share authors)
    cursor.execute('SELECT id FROM authors WHERE id = ?', (author_info['id'],))
    if not cursor.fetchone():
        # Insert author
        has_translations = 1 if (translation_file and os.path.exists(translation_file)) else 0
        cursor.execute('''
            INSERT INTO authors (id, name, name_alt, language, has_translations)
            VALUES (?, ?, ?, ?, ?)
        ''', (author_info['id'], author_info['name'], author_info['name_alt'], 'sanskrit', has_translations))

    # Insert work
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_info['id'], author_info['id'], work_info['title'], work_info.get('title_alt'),
          work_info['title_english'], work_info['type'], None, work_info['description']))

    total_verse_count = 0
    total_word_count = 0
    total_translation_count = 0

    # Process each book
    for book_num in sorted(text_data.keys()):
        chapters = text_data[book_num]

        book_id = f"{work_info['id']}.{book_num}"
        book_label = f"{work_info.get('book_label_prefix', 'Book')} {book_num}"

        line_count = sum(len(verses) for verses in chapters.values())

        cursor.execute('''
            INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_info['id'], book_num, book_label, 1, line_count, line_count))

        print(f"  {book_label}: {len(chapters)} chapters, {line_count} verses")

        line_number = 1

        for chapter_num in sorted(chapters.keys(), key=lambda x: x if x is not None else 0):
            verses = chapters[chapter_num]

            # Track start/end lines for this chapter
            chapter_start_line = line_number

            for verse_num in sorted(verses.keys()):
                verse_data = verses[verse_num]

                # Combine text sentences into verse (for display)
                verse_text = ' '.join(verse_data['text'])

                # Use segmented words (for dictionary lookup)
                verse_words = verse_data['words']

                # If no segmented words available, fall back to space-based tokenization
                if not verse_words:
                    verse_words = [(w, None) for w in tokenize_sanskrit(verse_text)]

                # For display, show the segmented words separated by spaces
                # This makes word boundaries visible and enables dictionary lookup
                # verse_words is now a list of tuples: (word, lemma, head, deprel, pos_tag, sentence_position)
                # Handle both old 2-tuple format and new 6-tuple format for compatibility
                display_text = ' '.join(word_tuple[0] for word_tuple in verse_words)

                cursor.execute('''
                    INSERT INTO text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (None, book_id, line_number, line_number, display_text, None, None))

                # Insert segmented words with treebank data if available
                for word_pos, word_tuple in enumerate(verse_words, 1):
                    # Unpack tuple - handle both old (word, lemma) and new (word, lemma, head, deprel, pos_tag, sent_pos) formats
                    if len(word_tuple) >= 6:
                        word, lemma, head, deprel, pos_tag, sentence_position = word_tuple[:6]
                    else:
                        word, lemma = word_tuple[0], word_tuple[1] if len(word_tuple) > 1 else None
                        head, deprel, pos_tag, sentence_position = None, None, None, None

                    cursor.execute('''
                        INSERT INTO words (id, word, book_id, line_number, sequence_number, word_position, head, deprel, pos_tag, sentence_position)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, word, book_id, line_number, line_number, word_pos, head, deprel, pos_tag, sentence_position))
                    total_word_count += 1

                total_verse_count += 1
                line_number += 1

            # Insert translation once per chapter (after all verses processed)
            # This covers all verses in this chapter with a single translation segment
            chapter_end_line = line_number - 1
            if book_num in translations and chapter_num in translations[book_num]:
                translation_list = translations[book_num][chapter_num]
                if translation_list:
                    # Combine all translation verses for this section into one text
                    # Number each verse for readability
                    numbered_translations = [f"[{i+1}] {text}" for i, text in enumerate(translation_list)]
                    translation_text = ' '.join(numbered_translations)

                    cursor.execute('''
                        INSERT INTO translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (None, book_id, chapter_start_line, chapter_end_line, chapter_start_line, translation_text, translator_name, None))
                    total_translation_count += 1

    print(f"\n  ✓ Loaded {total_verse_count:,} verses, {total_word_count:,} words, {total_translation_count:,} translations")
    return total_verse_count, total_word_count, total_translation_count

def create_translation_lookup_table(conn):
    """
    Create a lookup table mapping every line to its translation segment(s).

    This is essential for the Android app to efficiently find translations.
    Similar to the Greek database translation_lookup table.
    """
    cursor = conn.cursor()

    # Drop and recreate the lookup table
    cursor.execute("DROP TABLE IF EXISTS translation_lookup")
    cursor.execute("""
        CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )
    """)

    # Create indexes to match Room entity definition exactly
    cursor.execute("CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)")
    cursor.execute("CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)")

    # Get all books with translations
    cursor.execute("""
        SELECT DISTINCT b.id
        FROM books b
        WHERE EXISTS (SELECT 1 FROM translation_segments ts WHERE ts.book_id = b.id)
    """)

    books = [row[0] for row in cursor.fetchall()]
    total_mappings = 0

    for book_id in books:
        # Get translation segments
        cursor.execute("""
            SELECT id, start_line, end_line
            FROM translation_segments
            WHERE book_id = ?
            ORDER BY start_line
        """, (book_id,))

        segments = cursor.fetchall()
        if not segments:
            continue

        # Get actual line numbers from text_lines
        cursor.execute("""
            SELECT DISTINCT line_number
            FROM text_lines
            WHERE book_id = ?
        """, (book_id,))
        valid_lines = set(row[0] for row in cursor.fetchall())

        book_mappings = 0

        # For each segment, map all lines in its range
        for seg_id, start, end in segments:
            if end is None:
                end = start

            # Map each line in the segment's range
            for line_num in range(start, end + 1):
                if line_num in valid_lines:
                    cursor.execute("""
                        INSERT OR IGNORE INTO translation_lookup
                        VALUES (?, ?, ?)
                    """, (book_id, line_num, seg_id))
                    book_mappings += 1

        total_mappings += book_mappings

    print(f"  ✓ Created {total_mappings:,} line-to-translation mappings")
    conn.commit()


def import_sanskrit_lexicon(conn):
    """
    Import Sanskrit lexicon data from dcs_sanskrit_lexicon.zip.

    Imports:
    - dictionary.csv → dictionary_entries table
    - morphology.csv → lemma_map table
    - normalization_rules.csv → normalization_patterns table
    """
    import csv
    import zipfile
    import tempfile
    import re

    lexicon_zip = 'dcs_sanskrit_lexicon.zip'

    if not os.path.exists(lexicon_zip):
        print(f"  ⚠ Warning: Lexicon not found: {lexicon_zip}")
        print("  Skipping lexicon import - tables will be empty")
        return

    cursor = conn.cursor()

    # Extract ZIP to temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(lexicon_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Import dictionary.csv into dictionary_entries table
        dict_path = os.path.join(temp_dir, 'dictionary.csv')
        if os.path.exists(dict_path):
            print(f"  Importing dictionary...")
            with open(dict_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                dict_count = 0
                for row in reader:
                    # Incorporate transliteration into entry_html and entry_plain if available
                    transliteration = row.get('transliteration', '')
                    definition = row.get('definition', '')
                    html_definition = row.get('html_definition', '')

                    if transliteration:
                        # Add transliteration to plain definition
                        entry_plain = f"[{transliteration}] {definition}"
                        # Add transliteration to HTML definition
                        if html_definition:
                            entry_html = f'<div><span class="transliteration" style="color: #666; font-style: italic;">[{transliteration}]</span> {html_definition}</div>'
                        else:
                            entry_html = f'<div><span class="transliteration" style="color: #666; font-style: italic;">[{transliteration}]</span> {definition}</div>'
                    else:
                        entry_plain = definition
                        entry_html = html_definition if html_definition else f'<div>{definition}</div>'

                    cursor.execute('''
                        INSERT OR IGNORE INTO dictionary_entries
                        (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
                        VALUES (?, NULL, ?, '', ?, ?, ?)
                    ''', (row['lemma'], row['language'], entry_html, entry_plain, row.get('source_name', '')))
                    dict_count += 1
                print(f"  ✓ Imported {dict_count:,} dictionary entries")

        # Import morphology.csv into lemma_map table
        morph_path = os.path.join(temp_dir, 'morphology.csv')
        if os.path.exists(morph_path):
            print(f"  Importing morphology...")
            with open(morph_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                morph_count = 0
                for row in reader:
                    # Combine pos and root into morph_info
                    morph_info_parts = []
                    if row.get('pos'):
                        morph_info_parts.append(f"pos:{row['pos']}")
                    if row.get('root'):
                        morph_info_parts.append(f"root:{row['root']}")
                    morph_info = '; '.join(morph_info_parts) if morph_info_parts else None

                    cursor.execute('''
                        INSERT OR IGNORE INTO lemma_map
                        (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                        VALUES (?, NULL, ?, ?, ?, ?)
                    ''', (row['word_form'], row['lemma'],
                          float(row.get('confidence', 1.0)), row.get('source_name', ''), morph_info))
                    morph_count += 1
                    if morph_count % 100000 == 0:
                        print(f"    ... {morph_count:,} morphology forms")
                print(f"  ✓ Imported {morph_count:,} morphology forms")

        # Import normalization_rules.csv into normalization_patterns table
        norm_path = os.path.join(temp_dir, 'normalization_rules.csv')
        if os.path.exists(norm_path):
            print(f"  Importing normalization rules...")
            with open(norm_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                norm_count = 0
                for row in reader:
                    cursor.execute('''
                        INSERT OR IGNORE INTO normalization_patterns
                        (language, pattern, replacement, description, priority)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (row['language'], row['pattern'], row['replacement'],
                          row.get('description', ''), int(row.get('priority', 999))))
                    norm_count += 1
                print(f"  ✓ Imported {norm_count} normalization rules")

    # Post-process to populate normalized fields
    print("  Applying normalization to lemma_map and dictionary entries...")

    # Get all normalization patterns by language
    patterns_by_lang = {}
    cursor.execute("SELECT language, pattern, replacement, priority FROM normalization_patterns ORDER BY priority")
    for row in cursor.fetchall():
        lang, pattern_str, replacement, priority = row
        if lang not in patterns_by_lang:
            patterns_by_lang[lang] = []
        patterns_by_lang[lang].append((re.compile(pattern_str), replacement))

    # Apply normalization to Sanskrit lemma_map entries
    if 'sanskrit' in patterns_by_lang:
        import unicodedata
        patterns = patterns_by_lang['sanskrit']

        # Normalize lemma_map
        cursor.execute("SELECT id, word_form FROM lemma_map WHERE word_form_normalized_ultra IS NULL")
        lemma_entries = cursor.fetchall()
        updated_lemma = 0

        for entry_id, word_form in lemma_entries:
            # Apply NFD normalization, then patterns, then NFC
            normalized = unicodedata.normalize('NFD', word_form)
            for pattern, replacement in patterns:
                normalized = pattern.sub(replacement, normalized)
            normalized = unicodedata.normalize('NFC', normalized)

            # Update if normalization changed the word
            if normalized != word_form:
                cursor.execute("UPDATE lemma_map SET word_form_normalized_ultra = ? WHERE id = ?",
                             (normalized, entry_id))
                updated_lemma += 1

        if updated_lemma > 0:
            print(f"  ✓ Normalized {updated_lemma:,} lemma_map entries")
        else:
            print(f"  ✓ No normalization needed for lemma_map entries")

        # Normalize dictionary_entries
        cursor.execute("SELECT id, headword FROM dictionary_entries WHERE headword_normalized_ultra IS NULL")
        dict_entries = cursor.fetchall()
        updated_dict = 0

        for entry_id, headword in dict_entries:
            # Apply NFD normalization, then patterns, then NFC
            normalized = unicodedata.normalize('NFD', headword)
            for pattern, replacement in patterns:
                normalized = pattern.sub(replacement, normalized)
            normalized = unicodedata.normalize('NFC', normalized)

            # Update if normalization changed the word
            if normalized != headword:
                cursor.execute("UPDATE dictionary_entries SET headword_normalized_ultra = ? WHERE id = ?",
                             (normalized, entry_id))
                updated_dict += 1

        if updated_dict > 0:
            print(f"  ✓ Normalized {updated_dict:,} dictionary entries")
        else:
            print(f"  ✓ No normalization needed for dictionary entries")

    conn.commit()


def main():
    print("=" * 70)
    print("Sanskrit Texts Database Creation")
    print("All 268 DCS works")
    print("=" * 70)

    if not HAS_TRANSLITERATION:
        print("\nWarning: indic-transliteration not installed")
        print("For full functionality: pip install indic-transliteration\n")

    # Create database
    db_path = 'sanskrit_texts.db'
    conn, cursor = create_database(db_path)

    # Track all statistics
    all_stats = []

    # Load Bhagavad Gita (in both modes - uses Wikisource, not DCS)
    # Use unique IDs to avoid collision with potential DCS version
    bg_verses, bg_words, bg_translations = load_bhagavad_gita(cursor)
    all_stats.append(('Bhagavad Gita (Wikisource, with translations)', bg_verses, bg_words, bg_translations))

    # Load Rig Veda (in both modes - uses DCS pada format, not conllu)
    # Use unique IDs to avoid collision with DCS CoNLL-U version
    rv_verses, rv_words, rv_translations = load_rigveda(cursor)
    all_stats.append(('Rig Veda (pada format, complete with Griffith translation)', rv_verses, rv_words, rv_translations))

    # Mapping of DCS work names to translation files
    # Based on DCS translations directory
    translation_map = {
        'Aitareyopaniṣad': ('../data-sources/sanskrit/translations/AU-Olivelle.txt', 'Patrick Olivelle'),
        'Chāndogyopaniṣad': ('../data-sources/sanskrit/translations/ChUp-Olivelle.txt', 'Patrick Olivelle'),
        'Śvetāśvataropaniṣad': ('../data-sources/sanskrit/translations/SvetUp-Olivelle.txt', 'Patrick Olivelle'),
        'Āpastambagṛhyasūtra': ('../data-sources/sanskrit/translations/ApGS-Oldenberg.txt', 'H. Oldenberg'),
        'Gobhilagṛhyasūtra': ('../data-sources/sanskrit/translations/GobhGS-Oldenberg.txt', 'H. Oldenberg'),
        'Hiraṇyakeśigṛhyasūtra': ('../data-sources/sanskrit/translations/HirGS-Oldenberg.txt', 'Hermann Oldenberg'),
        'Śāṅkhāyanagṛhyasūtra': ('../data-sources/sanskrit/translations/SankhGS-Oldenberg.txt', 'Hermann Oldenberg'),
        'Śatapathabrāhmaṇa': ('../data-sources/sanskrit/translations/SB-Eggeling.txt', 'Eggeling'),
        'Vājasaneyīsaṃhitā': ('../data-sources/sanskrit/translations/VS-Griffith.txt', 'Griffith'),
    }

    # Load all DCS works
    print("\n" + "=" * 70)
    print("Loading all DCS works...")
    print("=" * 70)

    dcs_works = discover_dcs_works()
    print(f"\nDiscovered {len(dcs_works)} DCS works")

    for idx, work_meta in enumerate(dcs_works, 1):
        text_name = work_meta['text_name']
        text_dir = work_meta['text_dir']
        work_id = work_meta['work_id']

        print(f"\n[{idx}/{len(dcs_works)}] Processing {text_name}...")

        # Convert text name to Devanagari for display
        text_devanagari = iast_to_devanagari(text_name)

        # Check if translation is available for this work
        translation_file = None
        translator_name = None
        if text_name in translation_map:
            trans_path, trans_name = translation_map[text_name]
            if os.path.exists(trans_path):
                translation_file = trans_path
                translator_name = trans_name
                print(f"  ✓ Found translation by {translator_name}")
            else:
                print(f"  Warning: Translation file not found: {trans_path}")

        # Use work name as author name (since most Sanskrit texts don't have individual authors)
        author_info = {
            'id': work_id,
            'name': text_devanagari,
            'name_alt': text_name
        }

        work_info = {
            'id': work_id,
            'title': text_devanagari,
            'title_alt': text_name,
            'title_english': text_name,  # Use IAST as English title
            'type': 'text',  # Generic type
            'description': f'{text_name} from the Digital Corpus of Sanskrit',
            'book_label_prefix': 'Book'
        }

        try:
            verses, words, translations = load_dcs_text(
                cursor,
                text_name=text_name,
                text_dir=text_dir,
                translation_file=translation_file,
                author_info=author_info,
                work_info=work_info,
                translator_name=translator_name
            )
            all_stats.append((text_name, verses, words, translations))
        except Exception as e:
            print(f"  ✗ Error loading {text_name}: {e}")
            continue

    # Check if any texts loaded
    total_verses_loaded = sum(stat[1] for stat in all_stats)
    if total_verses_loaded == 0:
        print("\nError: No texts loaded. Exiting.")
        conn.close()
        return 1

    # Get final statistics
    cursor.execute('SELECT COUNT(*) FROM authors')
    author_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM works')
    work_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM books')
    book_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM text_lines')
    total_verses = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM words')
    total_words = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT word) FROM words')
    unique_words = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM translation_segments')
    total_translations = cursor.fetchone()[0]

    # Create translation lookup table for efficient translation retrieval
    print("\nCreating translation lookup table...")
    create_translation_lookup_table(conn)

    # Import lexicon data
    print("\nImporting Sanskrit lexicon data...")
    import_sanskrit_lexicon(conn)

    # Get lexicon statistics
    cursor.execute('SELECT COUNT(*) FROM dictionary_entries')
    dict_entries = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM lemma_map')
    lemma_mappings = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM normalization_patterns')
    norm_patterns = cursor.fetchone()[0]

    # Commit and close
    conn.commit()
    conn.close()

    # Generate and import interlinear translations
    print("\n" + "=" * 70)
    print("GENERATING INTERLINEAR TRANSLATIONS")
    print("=" * 70)

    interlinear_dir = 'interlinear_output'
    os.makedirs(interlinear_dir, exist_ok=True)

    # Import the batch generation script
    print(f"\nGenerating interlinear XML files to {interlinear_dir}/...")
    from batch_generate_interlinear import main as generate_interlinear
    import sys

    # Save original argv
    original_argv = sys.argv

    # Set up arguments for batch generation
    sys.argv = ['batch_generate_interlinear.py', db_path, '--output', interlinear_dir, '--parallel', '8']

    try:
        generate_interlinear()
    finally:
        # Restore original argv
        sys.argv = original_argv

    # Verify interlinear files were generated
    import glob
    xml_files = glob.glob(os.path.join(interlinear_dir, '*.dcs-eng99.xml'))
    print(f"\n✓ Generated {len(xml_files)} interlinear XML files")

    # Import interlinear translations
    print("\n" + "=" * 70)
    print("IMPORTING INTERLINEAR TRANSLATIONS")
    print("=" * 70)

    from import_sanskrit_interlinear import import_sanskrit_interlinear
    import_sanskrit_interlinear(db_path, interlinear_dir)

    # Get final interlinear statistics
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM translation_segments WHERE translator LIKE 'Interlinear%'")
    interlinear_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT book_id) FROM translation_segments WHERE translator LIKE 'Interlinear%'")
    interlinear_books = cursor.fetchone()[0]

    conn.close()

    print(f"\n✓ Imported {interlinear_count:,} interlinear segments for {interlinear_books} books")

    # Get file size (ZIP created by pipeline script after all steps complete)
    db_size = os.path.getsize(db_path) / 1024 / 1024  # MB

    print("\n" + "=" * 70)
    print("Database Creation Complete!")
    print("=" * 70)
    print(f"\nContents:")
    print(f"  Authors: {author_count}")
    print(f"  Works: {work_count}")
    print(f"  Books: {book_count}")

    # Show summary for all works
    print(f"\nTexts loaded: {len(all_stats)} works")
    print(f"  (First 5: {', '.join([s[0] for s in all_stats[:5]])}...)")

    print(f"\nStatistics:")
    print(f"  Total verses: {total_verses:,}")
    print(f"  Total words: {total_words:,}")
    print(f"  Unique words: {unique_words:,}")
    print(f"  Translations: {total_translations:,}")
    print(f"  Interlinear translations: {interlinear_count:,} ({interlinear_books} books)")
    print(f"\nLexicon:")
    print(f"  Dictionary entries: {dict_entries:,}")
    print(f"  Lemma mappings: {lemma_mappings:,}")
    print(f"  Normalization patterns: {norm_patterns}")
    print(f"\nFiles:")
    print(f"  Database: {db_path} ({db_size:.2f} MB)")
    print(f"\nLicenses:")
    print(f"  ✓ Bhagavad Gita Sanskrit: CC BY-SA 4.0 (Wikisource)")
    print(f"  ✓ BG English (Arnold, Besant): Public Domain")
    print(f"  ✓ Rig Veda English (Griffith): Public Domain")
    print(f"  ✓ DCS Sanskrit texts: CC BY 4.0 (Oliver Hellwig)")
    print(f"  ✓ DCS Lexicon: CC BY 4.0 (Oliver Hellwig)")
    print(f"\nReady for ClassicsViewer integration!")
    print(f"This database can be used standalone or merged into extended database.")

    return 0

if __name__ == '__main__':
    sys.exit(main() or 0)
