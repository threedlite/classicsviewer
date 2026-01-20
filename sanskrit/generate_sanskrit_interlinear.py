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
             | lemma1 morph1 ~* POS deprel head sent_pos sent_id |  | word2 |
             | **gloss2** |
             | lemma2 morph2 ~* POS deprel head sent_pos sent_id | ...
             </l>

Treebank data (HEAD, DEPREL) and morphological features (case, number, gender, etc.)
are included for works in the Vedic Treebank subset. Morph format: "acc s m" for
"Case=Acc|Number=Sing|Gender=Masc".

The sent_id field disambiguates multiple sentences per verse line. Each verse may
contain multiple sentences (e.g., "Verse1.Sentence1", "Verse1.Sentence2"), and the
UI uses this to group words correctly when building dependency trees.
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
    from sanskrit_treebank_loader import SanskritTreebankLoader
    TREEBANK_AVAILABLE = True
except ImportError:
    TREEBANK_AVAILABLE = False

# Stanza for Sanskrit NLP fallback when no treebank data
# CRITICAL: Stanza is required for works without DCS treebank data
import threading
try:
    import stanza
    STANZA_AVAILABLE = True
except ImportError:
    print("WARNING: Stanza not installed. Works without treebank data will lack tree annotations.")
    STANZA_AVAILABLE = False

# Global Stanza NLP instance (lazy initialized, thread-safe singleton)
_stanza_nlp = None
_stanza_lock = threading.Lock()
_stanza_initialized = False


def get_stanza_nlp():
    """
    Get or create Stanza Sanskrit NLP instance (singleton pattern).
    Thread-safe for use with multiprocessing workers.
    Returns None if Stanza is not available.
    """
    global _stanza_nlp, _stanza_initialized

    if not STANZA_AVAILABLE:
        return None

    if _stanza_nlp is None and not _stanza_initialized:
        with _stanza_lock:
            if _stanza_nlp is None and not _stanza_initialized:
                print("Loading Stanza Sanskrit models...")
                try:
                    # Download model if needed
                    stanza.download('sa', verbose=False)
                    _stanza_nlp = stanza.Pipeline('sa', processors='tokenize,pos,lemma,depparse', verbose=False)
                    print("Stanza Sanskrit models loaded successfully")
                except Exception as e:
                    print(f"WARNING: Failed to load Stanza Sanskrit models: {e}")
                _stanza_initialized = True

    return _stanza_nlp


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
    sentence_id: Optional[str] = None   # Sentence identifier (for disambiguating multiple sentences per line)
    feats: Optional[str] = None         # Morphological features (e.g., "Case=Acc|Number=Sing")
    is_treebank: bool = False           # True if tree data from DCS treebank, False if from Stanza


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


def format_feats(feats_str: str) -> str:
    """
    Convert CoNLL-U morphological features to compact display format.

    Converts features like 'Case=Acc|Gender=Masc|Number=Sing' to 'acc sg m'.
    Similar to Greek interlinear format (e.g., "nom sg masc").

    Args:
        feats_str: CoNLL-U FEATS field (pipe-separated key=value pairs)

    Returns:
        Compact string for display, or empty string if no displayable features
    """
    if not feats_str or feats_str == '_':
        return ''

    # Abbreviation mappings for common morphological features
    abbrevs = {
        'Case': {
            'Nom': 'nom', 'Acc': 'acc', 'Gen': 'gen', 'Dat': 'dat',
            'Abl': 'abl', 'Loc': 'loc', 'Ins': 'ins', 'Voc': 'voc',
            'Cpd': 'cpd'  # Compound
        },
        'Number': {'Sing': 's', 'Plur': 'p', 'Dual': 'd'},
        'Gender': {'Masc': 'm', 'Fem': 'f', 'Neut': 'n'},
        'Person': {'1': '1', '2': '2', '3': '3'},
        'Tense': {
            'Pres': 'pres', 'Past': 'past', 'Fut': 'fut',
            'Aor': 'aor', 'Perf': 'perf', 'Pqp': 'pqp'
        },
        'Mood': {'Ind': 'ind', 'Sub': 'subj', 'Opt': 'opt', 'Imp': 'impr'},
        'Voice': {'Act': 'act', 'Pass': 'pass', 'Mid': 'mid'},
        'VerbForm': {'Gdv': 'gdv', 'Inf': 'inf', 'Part': 'part', 'Ger': 'ger', 'Conv': 'conv'},
    }

    # Order for display (case/number/gender first, then verb features)
    display_order = ['Case', 'Number', 'Gender', 'Person', 'Tense', 'Mood', 'Voice', 'VerbForm']

    # Parse features into dict
    feat_dict = {}
    for feat in feats_str.split('|'):
        if '=' in feat:
            key, val = feat.split('=', 1)
            feat_dict[key] = val

    # Build display string in order
    parts = []
    for key in display_order:
        if key in feat_dict:
            val = feat_dict[key]
            if key in abbrevs and val in abbrevs[key]:
                parts.append(abbrevs[key][val])

    return ' '.join(parts)


class SanskritInterlinearGenerator:
    """
    Generates interlinear translations for Sanskrit texts.

    Uses database word segmentation and DCS dictionary lookups.
    Generates both plain text and TEI XML formats.
    Includes treebank data (HEAD, DEPREL) for Vedic Treebank works.

    Design: Database work_id matches DCS treebank directory names exactly
    (e.g., "Ṛgveda", "Aitareyopaniṣad"), following the Greek pattern where
    database work_id = treebank ID. No mapping needed.
    """

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
            'stanza_words': 0,
            'feats_found': 0,
        }

        # Feats lookup cache: {dcs_work_name: {(pos, deprel, head, sent_pos): feats}}
        self._feats_cache: Dict[str, Dict[Tuple, str]] = {}

    def _build_feats_cache(self, dcs_work: str) -> Dict[Tuple, str]:
        """
        Build a lookup cache for morphological features from treebank data.

        Creates mapping: (pos, deprel, head, sentence_position) -> feats
        This allows efficient feats lookup without needing sentence_id.

        Args:
            dcs_work: DCS work name (e.g., "Aitareyopaniṣad")

        Returns:
            Dict mapping (pos, deprel, head, sent_pos) tuples to feats strings
        """
        if dcs_work in self._feats_cache:
            return self._feats_cache[dcs_work]

        if not self.treebank or dcs_work not in self.treebank.available_works:
            self._feats_cache[dcs_work] = {}
            return {}

        cache = {}
        chapters = self.treebank.get_chapters(dcs_work)

        for chapter_id in chapters:
            sentences = self.treebank.get_sentences_for_chapter(dcs_work, chapter_id)
            for sentence_id, words in sentences.items():
                for word in words:
                    # Key: (upos, deprel, head, sentence_position)
                    # This combination should be fairly unique within a work
                    key = (word.upos, word.deprel, word.head, word.sentence_position)
                    if key not in cache and word.feats and word.feats != '_':
                        cache[key] = word.feats

        self._feats_cache[dcs_work] = cache
        return cache

    def _lookup_feats(self, dcs_work: str, pos: str, deprel: str,
                      head: int, sent_pos: int) -> Optional[str]:
        """
        Look up morphological features for a word from treebank cache.

        Args:
            dcs_work: DCS work name
            pos: UPOS tag (e.g., "NOUN")
            deprel: Dependency relation (e.g., "nsubj")
            head: Head word position
            sent_pos: Sentence position

        Returns:
            Feats string (e.g., "Case=Acc|Gender=Masc|Number=Sing") or None
        """
        cache = self._build_feats_cache(dcs_work)
        if not cache:
            return None

        key = (pos, deprel, head, sent_pos)
        return cache.get(key)

    def _get_dcs_work_name(self, work_id: str) -> Optional[str]:
        """
        Get DCS work name from database work_id.

        Database work_id matches DCS treebank directory names exactly
        (following Greek pattern where database ID = treebank ID).

        Args:
            work_id: Database work identifier (e.g., "Ṛgveda")

        Returns:
            work_id if treebank has coverage, None otherwise
        """
        if work_id in self.treebank_work_cache:
            return self.treebank_work_cache[work_id]

        # Direct match - work_id IS the DCS work name
        if self.treebank and self.treebank.has_coverage(work_id):
            self.treebank_work_cache[work_id] = work_id
            return work_id

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
        Get segmented words for a specific line, including treebank data and feats.

        Tree data is read directly from DCS treebank files (not stored in database).
        This follows the Greek design pattern where the words table has only 6 columns.

        Args:
            book_id: Book identifier (e.g., "aitareyopanisad.1")
            line_number: Line number

        Returns:
            List of WordData objects with word forms, tree data, and morphological features
        """
        cursor = self.conn.cursor()
        # Query only the 6 columns that exist in the words table (matching Greek schema)
        cursor.execute("""
            SELECT word, word_position
            FROM words
            WHERE book_id = ? AND line_number = ?
            ORDER BY word_position
        """, (book_id, line_number))

        words = []
        for row in cursor.fetchall():
            word = row['word']
            # Look up lemma via morphology (database or CSV, handled by SanskritRepository)
            lemma = self.repo.get_lemma_for_word(word)

            words.append(WordData(
                word=word,
                word_position=row['word_position'],
                lemma=lemma,
                pos_tag=None,
                head=None,
                deprel=None,
                sentence_position=None,
                feats=None
            ))

        # Enhance with treebank data from DCS CoNLL-U files if available
        if words and self.treebank:
            # Extract work_id from book_id (e.g., "aitareyopanisad.1" -> "aitareyopanisad")
            work_id = book_id.rsplit('.', 1)[0] if '.' in book_id else book_id
            dcs_work = self._get_dcs_work_name(work_id)

            if dcs_work:
                self._enhance_line_with_treebank(words, dcs_work, book_id)

                # Fill in missing FEATS using cached Stanza data (much faster than per-line)
                words_missing_feats = sum(1 for w in words if w.head is not None and w.feats is None)
                if words_missing_feats > 0:
                    feats_cache = self._build_stanza_feats_cache_for_work(book_id)
                    self._fill_feats_gaps_from_cache(words, feats_cache)

        # Check if any words got tree data from treebank
        has_tree_data = any(w.head is not None for w in words)

        # Fallback: Use Stanza for lines without tree data (no treebank available)
        if words and not has_tree_data:
            # Get line text for Stanza analysis
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT line_text FROM text_lines
                WHERE book_id = ? AND line_number = ?
            """, (book_id, line_number))
            row = cursor.fetchone()
            if row:
                line_text = row['line_text']
                self._enhance_line_with_stanza(words, line_text)

        return words

    def _get_treebank_form_index(self, dcs_work: str) -> Dict[str, List]:
        """
        Build or retrieve cached index of treebank words by IAST form.

        Args:
            dcs_work: DCS work name (e.g., "Ṛgveda")

        Returns:
            Dict mapping lowercase IAST form to list of TreebankWord objects
        """
        # Check cache first
        cache_key = f"tb_form_idx_{dcs_work}"
        if cache_key in self._feats_cache:
            return self._feats_cache[cache_key]

        if not self.treebank or dcs_work not in self.treebank.available_works:
            self._feats_cache[cache_key] = {}
            return {}

        # Build index of all treebank words by IAST form
        tb_by_form: Dict[str, List] = {}
        chapters = self.treebank.get_chapters(dcs_work)

        for chapter_id in chapters:
            sentences = self.treebank.get_sentences_for_chapter(dcs_work, chapter_id)
            for sentence_id, tb_words in sentences.items():
                for tb_word in tb_words:
                    form_lower = tb_word.form.lower()
                    if form_lower not in tb_by_form:
                        tb_by_form[form_lower] = []
                    tb_by_form[form_lower].append(tb_word)

        self._feats_cache[cache_key] = tb_by_form
        return tb_by_form

    def _enhance_line_with_treebank(self, words: List[WordData], dcs_work: str, book_id: str):
        """
        Enhance word list with treebank data from DCS CoNLL-U files.

        Uses IAST transliteration matching between database words and treebank.
        Modifies words list in-place.

        Args:
            words: List of WordData to enhance
            dcs_work: DCS work name (e.g., "Ṛgveda")
            book_id: Book ID (e.g., "aitareyopanisad.1")
        """
        try:
            from indic_transliteration import sanscript
        except ImportError:
            return  # Can't match without transliteration

        # Get cached treebank index for this work
        tb_by_form = self._get_treebank_form_index(dcs_work)
        if not tb_by_form:
            return

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
                        word_data.sentence_id = tb_word.sentence_id  # Store sentence ID for tree disambiguation
                        word_data.feats = tb_word.feats if tb_word.feats and tb_word.feats != '_' else None
                        word_data.is_treebank = True  # Mark as treebank data
                        tb_used.add(tb_key)
                        self.stats['treebank_words'] += 1
                        if word_data.feats:
                            self.stats['feats_found'] += 1
                        break

    def _enhance_with_treebank(self, words: List[WordData], dcs_work: str,
                                chapter_id: str, sentence_id: str):
        """
        Enhance word list with treebank data by matching words.

        Uses IAST transliteration matching between database words and treebank.
        Modifies words list in-place.

        NOTE: This method is kept for backwards compatibility but _enhance_line_with_treebank
        is preferred as it doesn't require sentence_id.

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
                        word_data.sentence_id = tb_word.sentence_id  # Store sentence ID for tree disambiguation
                        tb_used.add(tb_key)
                        self.stats['treebank_words'] += 1
                        break

    def _enhance_line_with_stanza(self, words: List[WordData], line_text: str):
        """
        Enhance word list with Stanza NLP tree data (fallback when no treebank data).

        Uses Stanza Sanskrit dependency parser when DCS treebank data is not available.
        Morphological features are looked up from the morphology table first (more accurate),
        with Stanza feats as fallback.
        Modifies words list in-place.

        Args:
            words: List of WordData to enhance
            line_text: Original line text in Devanagari
        """
        nlp = get_stanza_nlp()
        if nlp is None:
            return

        try:
            # Analyze the line with Stanza
            doc = nlp(line_text)

            if not doc.sentences:
                return

            # For each sentence in the line
            for sent_idx, sent in enumerate(doc.sentences):
                stanza_words = sent.words
                if not stanza_words:
                    continue

                # Generate sentence ID for Stanza-derived sentences (S0, S1, S2, etc.)
                stanza_sent_id = f"S{sent_idx}"

                # Build mapping by text match
                stanza_by_text = {}
                for idx, sw in enumerate(stanza_words):
                    text_lower = sw.text.lower()
                    if text_lower not in stanza_by_text:
                        stanza_by_text[text_lower] = []
                    stanza_by_text[text_lower].append((idx, sw))

                # Match our words to Stanza words
                stanza_used = set()
                for word_data in words:
                    # Skip if already has tree data
                    if word_data.head is not None:
                        continue

                    word_lower = word_data.word.lower()
                    if word_lower in stanza_by_text:
                        for idx, sw in stanza_by_text[word_lower]:
                            if idx not in stanza_used:
                                word_data.pos_tag = sw.upos
                                word_data.head = sw.head
                                word_data.deprel = sw.deprel
                                word_data.sentence_position = sw.id
                                word_data.sentence_id = stanza_sent_id  # Store sentence ID for tree disambiguation
                                # Look up feats from morphology table first (takes precedence)
                                morph_feats = self._lookup_morph_feats(word_data.word)
                                if morph_feats:
                                    word_data.feats = morph_feats
                                    self.stats['morph_lookup_words'] = self.stats.get('morph_lookup_words', 0) + 1
                                # Fallback to Stanza feats if no dictionary entry
                                elif hasattr(sw, 'feats') and sw.feats:
                                    word_data.feats = sw.feats
                                stanza_used.add(idx)
                                self.stats['stanza_words'] += 1
                                break

                # Re-number positions to be consecutive (fix gaps from skipped tokens)
                # This ensures all head pointers are valid
                self._renumber_sentence_positions(words, stanza_sent_id, stanza_words)

        except Exception as e:
            # Don't crash on Stanza errors - just skip tree data for this line
            pass

    def _renumber_sentence_positions(self, words: List[WordData], sent_id: str, stanza_words):
        """
        Re-number sentence positions to be consecutive and fix head pointers.

        Stanza assigns IDs to ALL tokens including punctuation. When we skip
        some tokens, positions have gaps and head pointers may be invalid.
        This function re-numbers positions to be consecutive (1, 2, 3, ...)
        and adjusts head pointers by following the tree up to find valid ancestors.

        Args:
            words: List of WordData objects for this line
            sent_id: Sentence ID to filter by (only renumber words in this sentence)
            stanza_words: Original Stanza word list (to follow head chains)
        """
        # Collect words in this sentence that have positions
        sent_words = [(i, w) for i, w in enumerate(words)
                      if w.sentence_id == sent_id and w.sentence_position is not None]

        if not sent_words:
            return

        # Sort by original position
        sent_words.sort(key=lambda x: x[1].sentence_position)

        # Create mapping from old position to new position
        old_to_new = {}
        for new_pos, (word_idx, word_data) in enumerate(sent_words, start=1):
            old_pos = word_data.sentence_position
            old_to_new[old_pos] = new_pos

        # Build Stanza head map for traversing up the tree
        stanza_head_map = {}
        for sw in stanza_words:
            stanza_head_map[sw.id] = sw.head

        # Update positions and heads
        for word_idx, word_data in sent_words:
            old_pos = word_data.sentence_position
            old_head = word_data.head

            # Update position to new consecutive value
            word_data.sentence_position = old_to_new[old_pos]

            # Update head to new position (0 stays 0 for root)
            if old_head is not None and old_head != 0:
                if old_head in old_to_new:
                    word_data.head = old_to_new[old_head]
                else:
                    # Head pointed to a skipped token - follow tree up to find valid ancestor
                    new_head = self._find_valid_ancestor(old_head, old_to_new, stanza_head_map)
                    word_data.head = new_head

    def _find_valid_ancestor(self, start_head: int, old_to_new: dict, stanza_head_map: dict) -> int:
        """
        Follow the tree up from a skipped node to find a valid ancestor.

        Args:
            start_head: The original head position (which was skipped)
            old_to_new: Mapping from old positions to new positions
            stanza_head_map: Mapping from Stanza word id to its head

        Returns:
            New position of valid ancestor, or 0 if we reach root
        """
        current = start_head
        visited = set()

        while current != 0 and current not in visited:
            visited.add(current)

            # If this position exists in our output, use it
            if current in old_to_new:
                return old_to_new[current]

            # Otherwise, follow the tree up
            if current in stanza_head_map:
                current = stanza_head_map[current]
            else:
                # Can't find head, go to root
                return 0

        return 0  # Reached root

    def _lookup_morph_feats(self, word: str) -> Optional[str]:
        """
        Look up morphological features from the morphology table.

        Args:
            word: Word form in Devanagari

        Returns:
            CoNLL-U style feats string (e.g., "Case=Nom|Number=Sing|Gender=Masc") or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT grammatical_info FROM morphology
                WHERE word = ? LIMIT 1
            """, (word,))
            row = cursor.fetchone()
            if row and row['grammatical_info']:
                # Convert morphology table format to CoNLL-U feats format
                return self._convert_morph_to_feats(row['grammatical_info'])
        except Exception:
            pass
        return None

    def _convert_morph_to_feats(self, morph_info: str) -> Optional[str]:
        """
        Convert morphology table grammatical_info to CoNLL-U feats format.

        The morphology table stores info like "nom sg masc" or "3rd sg pres ind act"
        This converts to CoNLL-U format like "Case=Nom|Number=Sing|Gender=Masc"

        Args:
            morph_info: Grammatical info from morphology table

        Returns:
            CoNLL-U feats string or None if can't convert
        """
        if not morph_info:
            return None

        feats = []
        morph_lower = morph_info.lower()

        # Case mapping
        case_map = {
            'nom': 'Case=Nom', 'acc': 'Case=Acc', 'gen': 'Case=Gen',
            'dat': 'Case=Dat', 'abl': 'Case=Abl', 'loc': 'Case=Loc',
            'ins': 'Case=Ins', 'voc': 'Case=Voc'
        }
        for abbr, feat in case_map.items():
            if abbr in morph_lower.split():
                feats.append(feat)
                break

        # Number mapping
        if ' sg ' in f' {morph_lower} ' or 'sing' in morph_lower:
            feats.append('Number=Sing')
        elif ' pl ' in f' {morph_lower} ' or 'plur' in morph_lower:
            feats.append('Number=Plur')
        elif ' du ' in f' {morph_lower} ' or 'dual' in morph_lower:
            feats.append('Number=Dual')

        # Gender mapping
        if ' m ' in f' {morph_lower} ' or 'masc' in morph_lower:
            feats.append('Gender=Masc')
        elif ' f ' in f' {morph_lower} ' or 'fem' in morph_lower:
            feats.append('Gender=Fem')
        elif ' n ' in f' {morph_lower} ' or 'neut' in morph_lower:
            feats.append('Gender=Neut')

        # Person mapping (for verbs)
        if '1st' in morph_lower or ' 1 ' in f' {morph_lower} ':
            feats.append('Person=1')
        elif '2nd' in morph_lower or ' 2 ' in f' {morph_lower} ':
            feats.append('Person=2')
        elif '3rd' in morph_lower or ' 3 ' in f' {morph_lower} ':
            feats.append('Person=3')

        # Tense mapping
        if 'pres' in morph_lower:
            feats.append('Tense=Pres')
        elif 'past' in morph_lower or 'impf' in morph_lower:
            feats.append('Tense=Past')
        elif 'fut' in morph_lower:
            feats.append('Tense=Fut')
        elif 'perf' in morph_lower:
            feats.append('Tense=Perf')
        elif 'aor' in morph_lower:
            feats.append('Tense=Aor')

        # Mood mapping
        if 'ind' in morph_lower:
            feats.append('Mood=Ind')
        elif 'opt' in morph_lower:
            feats.append('Mood=Opt')
        elif 'imp' in morph_lower:
            feats.append('Mood=Imp')
        elif 'subj' in morph_lower:
            feats.append('Mood=Sub')

        # Voice mapping
        if ' act ' in f' {morph_lower} ' or 'active' in morph_lower:
            feats.append('Voice=Act')
        elif ' mid ' in f' {morph_lower} ' or 'middle' in morph_lower:
            feats.append('Voice=Mid')
        elif ' pass ' in f' {morph_lower} ' or 'passive' in morph_lower:
            feats.append('Voice=Pass')

        return '|'.join(feats) if feats else None

    def _build_stanza_feats_cache_for_work(self, book_id: str) -> Dict[str, str]:
        """
        Build a cache of word_form -> feats using Stanza for an entire work.

        Processes all lines in the work once and caches feats by word form.
        Much more efficient than calling Stanza per-line.

        Args:
            book_id: Book ID to process

        Returns:
            Dict mapping lowercase word forms to feats strings
        """
        # Check cache first
        work_id = book_id.rsplit('.', 1)[0] if '.' in book_id else book_id
        cache_key = f"stanza_feats_{work_id}"
        if cache_key in self._feats_cache:
            return self._feats_cache[cache_key]

        nlp = get_stanza_nlp()
        if nlp is None:
            self._feats_cache[cache_key] = {}
            return {}

        # Get all lines for this work
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT line_text FROM text_lines
            WHERE book_id LIKE ?
            ORDER BY line_number
        """, (f"{work_id}.%",))

        all_lines = [row['line_text'] for row in cursor.fetchall()]
        if not all_lines:
            self._feats_cache[cache_key] = {}
            return {}

        # Process in batches to avoid memory issues (join lines with newlines)
        feats_cache = {}
        batch_size = 50  # Process 50 lines at a time

        try:
            for i in range(0, len(all_lines), batch_size):
                batch = all_lines[i:i+batch_size]
                batch_text = '\n'.join(batch)

                doc = nlp(batch_text)

                for sent in doc.sentences:
                    for sw in sent.words:
                        if hasattr(sw, 'feats') and sw.feats:
                            word_lower = sw.text.lower()
                            # Only store first feats seen for each word form
                            if word_lower not in feats_cache:
                                feats_cache[word_lower] = sw.feats
        except Exception as e:
            pass  # Don't crash on Stanza errors

        self._feats_cache[cache_key] = feats_cache
        return feats_cache

    def _fill_feats_gaps_from_cache(self, words: List[WordData], feats_cache: Dict[str, str]):
        """
        Fill in missing FEATS using priority: Dictionary > Stanza cache.

        Only updates the feats field - preserves existing POS, head, deprel from treebank.
        Priority order for feats:
        1. Treebank (already set, not touched here)
        2. Dictionary (morphology table lookup)
        3. Stanza cache (fallback)

        Args:
            words: List of WordData (already enhanced with treebank)
            feats_cache: Dict mapping word forms to feats strings
        """
        for word_data in words:
            if word_data.head is not None and word_data.feats is None:
                # Priority 2: Try dictionary lookup first
                dict_feats = self._lookup_morph_feats(word_data.word)
                if dict_feats:
                    word_data.feats = dict_feats
                    self.stats['feats_from_dict'] = self.stats.get('feats_from_dict', 0) + 1
                # Priority 3: Fall back to Stanza cache
                elif feats_cache:
                    word_lower = word_data.word.lower()
                    if word_lower in feats_cache:
                        word_data.feats = feats_cache[word_lower]
                        self.stats['feats_found'] += 1

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

            # Build lemma line with optional morph and tree data
            # Format: | lemma morph ~* POS deprel head sent_pos sent_id | (treebank)
            #         | lemma morph ~ POS deprel head sent_pos sent_id |  (stanza)
            # Example: | agni acc s m ~* NOUN obj 2 1 Verse1.Sentence1 |
            if word_data.deprel is not None and word_data.head is not None:
                pos = sanitize_xml_text(word_data.pos_tag) if word_data.pos_tag else "X"
                deprel = sanitize_xml_text(word_data.deprel)
                head = word_data.head
                sent_pos = word_data.sentence_position or 0
                sent_id = word_data.sentence_id or "_"  # Use _ for missing sentence ID
                # Use ~* for treebank data, ~ for Stanza-generated data
                delimiter = "~*" if word_data.is_treebank else "~"

                # Include morphological features if available
                morph_display = format_feats(word_data.feats) if word_data.feats else ""
                if morph_display:
                    lemma_line = f"| {lemma_clean} {morph_display} {delimiter} {pos} {deprel} {head} {sent_pos} {sent_id} |"
                else:
                    lemma_line = f"| {lemma_clean} {delimiter} {pos} {deprel} {head} {sent_pos} {sent_id} |"
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
        xml_lines.append('                <editor role="translator">Interlinear (Beta, AI-generated from DCS dictionary and Stanza NLP)</editor>')
        xml_lines.append('                <sponsor>Derived from DCS dictionary, Stanza Sanskrit NLP models</sponsor>')
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
        xml_lines.append('                <note anchored="true">AI-generated word-by-word interlinear translation derived from DCS dictionary. Morphological analysis (case, number, gender, POS, dependencies) from Stanza Sanskrit NLP.</note>')
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
        feats_found = self.stats['feats_found']

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
            if feats_found > 0:
                print(f"  With morphological features: {feats_found:,} ({100*feats_found/total_words:.1f}%)")

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
