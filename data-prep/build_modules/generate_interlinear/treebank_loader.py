#!/usr/bin/env python3
"""
Perseus Treebank Loader

Loads and indexes Perseus Ancient Greek Dependency Treebank (AGDT) data
for integration with interlinear generation.

Provides O(1) lookup by work_id, book, line, word_form.
Falls back gracefully when treebank data is not available.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple
from xml.etree import ElementTree as ET
from dataclasses import dataclass


@dataclass
class TreebankWord:
    """Data for a single word from the treebank."""
    form: str
    lemma: str
    postag: str  # 9-character morphological tag
    head: int  # Head word position (sentence-relative, 0=root)
    relation: str  # AGDT dependency relation
    sentence_id: int  # Sentence ID for cross-line reference
    sentence_position: int  # 1-based position within sentence
    line_position: int  # 1-based position within line (computed)


# POS mapping: Perseus 1-char code -> UD POS tag
POS_MAP = {
    'n': 'NOUN',
    'v': 'VERB',
    'a': 'ADJ',
    'd': 'ADV',
    'p': 'PRON',
    'l': 'DET',
    'c': 'CCONJ',
    'r': 'ADP',
    'i': 'INTJ',
    'g': 'PART',
    'u': 'PUNCT',
    'm': 'NUM',
    'x': 'X',
    '-': 'X',
}

# Relation mapping: AGDT -> UD-style
RELATION_MAP = {
    'PRED': 'root',
    'PRED_CO': 'root',
    'SBJ': 'nsubj',
    'SBJ_CO': 'nsubj',
    'OBJ': 'obj',
    'OBJ_CO': 'obj',
    'ATR': 'nmod',
    'ATR_CO': 'nmod',
    'ADV': 'advmod',
    'ADV_CO': 'advmod',
    'AuxP': 'case',
    'AuxC': 'mark',
    'AuxV': 'aux',
    'ExD': 'vocative',
    'ExD_CO': 'vocative',
    'COORD': 'cc',
    'OCOMP': 'xcomp',
    'PNOM': 'nmod',
    'AuxX': 'punct',
    'AuxK': 'punct',
    'AuxG': 'punct',
    'AuxY': 'discourse',
    'AuxZ': 'advmod',
    'AposAtr': 'appos',
}


def map_pos(postag: str) -> str:
    """Map Perseus 9-char postag to UD POS."""
    if not postag or len(postag) < 1:
        return 'X'
    return POS_MAP.get(postag[0], 'X')


def map_relation(relation: str) -> str:
    """Map AGDT relation to UD-style relation."""
    return RELATION_MAP.get(relation, 'dep')


def extract_morph(postag: str) -> str:
    """
    Extract morphology string from 9-char postag.

    Postag positions:
    0: POS (n, v, a, ...)
    1: Person (1, 2, 3)
    2: Number (s, p, d)
    3: Tense (p, i, f, a, r, l)
    4: Mood (i, s, o, m, n, p)
    5: Voice (a, p, m, e)
    6: Gender (m, f, n)
    7: Case (n, g, d, a, v)
    8: Degree (c, s)
    """
    if not postag or len(postag) < 9:
        return ""

    parts = []

    # Person (for verbs)
    person = postag[1]
    if person in '123':
        parts.append(person)

    # Number
    number = postag[2]
    if number == 's':
        parts.append('s')
    elif number == 'p':
        parts.append('p')
    elif number == 'd':
        parts.append('d')

    # Tense
    tense = postag[3]
    tense_map = {'p': 'pres', 'i': 'impf', 'f': 'fut', 'a': 'aor', 'r': 'perf', 'l': 'plup'}
    if tense in tense_map:
        parts.append(tense_map[tense])

    # Voice
    voice = postag[5]
    voice_map = {'a': 'actv', 'p': 'pass', 'm': 'mid', 'e': 'mp'}
    if voice in voice_map:
        parts.append(voice_map[voice])

    # Mood
    mood = postag[4]
    mood_map = {'i': 'indc', 's': 'subj', 'o': 'opt', 'm': 'impr', 'n': 'inf', 'p': 'ptcp'}
    if mood in mood_map:
        parts.append(mood_map[mood])

    # Gender (for nouns/adjectives)
    gender = postag[6]
    if gender in 'mfn':
        pass  # Often implicit, skip for brevity

    # Case
    case = postag[7]
    case_map = {'n': 'nom', 'g': 'gen', 'd': 'dat', 'a': 'acc', 'v': 'voc'}
    if case in case_map:
        parts.append(case_map[case])

    return ' '.join(parts)


class PerseusTreebankLoader:
    """
    Load and index Perseus treebank data for fast lookup.

    Index structure:
    {work_id: {(book, line): [(word_form, TreebankWord), ...]}}
    """

    def __init__(self, treebank_dir: str = None):
        """
        Initialize loader with optional treebank directory.

        Args:
            treebank_dir: Path to treebank data. If None, uses default location.
        """
        self.index: Dict[str, Dict[tuple, List[tuple]]] = {}
        self.available_works: set = set()

        if treebank_dir:
            self.load_all_treebanks(treebank_dir)

    def load_all_treebanks(self, treebank_dir: str):
        """Load all treebank files from directory."""
        treebank_path = Path(treebank_dir)

        # Use v2.1 only (most recent and complete) - don't load v1.6 to avoid duplicates
        search_paths = [
            treebank_path / "v2.1" / "Greek" / "texts",
        ]

        for search_path in search_paths:
            if search_path.exists():
                for xml_file in search_path.glob("*.tb.xml"):
                    try:
                        self._load_treebank_file(xml_file)
                    except Exception as e:
                        print(f"  Warning: Failed to load treebank {xml_file.name}: {e}")

        if self.available_works:
            print(f"  Loaded treebank data for {len(self.available_works)} works")

    def _load_treebank_file(self, xml_path: Path):
        """Parse a single treebank XML file and index its data."""
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Extract work_id from filename or document_id
        # Filename: tlg0012.tlg001.perseus-grc1.tb.xml
        work_id = None
        filename = xml_path.stem.replace('.tb', '')
        # Extract tlgXXXX.tlgYYY pattern
        match = re.match(r'(tlg\d+\.tlg\d+)', filename)
        if match:
            work_id = match.group(1)

        if not work_id:
            return

        if work_id not in self.index:
            self.index[work_id] = {}

        # Process each sentence
        for sentence in root.iter('sentence'):
            sentence_id = int(sentence.get('id', 0))
            subdoc = sentence.get('subdoc', '')  # e.g., "1.1-1.7"

            # Track words by line within this sentence
            line_words: Dict[tuple, List[tuple]] = {}  # {(book, line): [(form, TreebankWord), ...]}

            # Two-pass approach to handle head remapping:
            # Pass 1: Collect all words and build position mapping
            # Pass 2: Create TreebankWord objects with remapped heads

            # Pass 1: Build mapping from original position to non-punct position
            orig_to_nopunct = {}  # {original_pos: nopunct_pos}
            nopunct_pos = 0
            word_data_list = []

            for word_elem in sentence.findall('word'):
                orig_pos = int(word_elem.get('id', 0))

                form = word_elem.get('form', '')
                lemma = word_elem.get('lemma', '')
                postag = word_elem.get('postag', '---------')
                relation = word_elem.get('relation', '')
                cite = word_elem.get('cite', '')

                # Parse head, handling empty values
                head_str = word_elem.get('head', '0')
                try:
                    orig_head = int(head_str) if head_str else 0
                except ValueError:
                    orig_head = 0

                # Check if punctuation
                is_punct = postag.startswith('u') or not form or form in ',;.·'

                if not is_punct:
                    nopunct_pos += 1
                    orig_to_nopunct[orig_pos] = nopunct_pos

                    word_data_list.append({
                        'form': form,
                        'lemma': lemma,
                        'postag': postag,
                        'relation': relation,
                        'cite': cite,
                        'orig_head': orig_head,
                        'nopunct_pos': nopunct_pos
                    })

            # Pass 2: Create TreebankWord objects with remapped heads
            for wd in word_data_list:
                # Remap head from original position to non-punct position
                remapped_head = orig_to_nopunct.get(wd['orig_head'], 0)

                # Parse cite to get book.line
                book, line = self._parse_cite(wd['cite'])
                if book is None:
                    continue

                key = (book, line)
                if key not in line_words:
                    line_words[key] = []

                tb_word = TreebankWord(
                    form=wd['form'],
                    lemma=wd['lemma'],
                    postag=wd['postag'],
                    head=remapped_head,
                    relation=wd['relation'],
                    sentence_id=sentence_id,
                    sentence_position=wd['nopunct_pos'],
                    line_position=0  # Will be computed below
                )

                line_words[key].append((wd['form'], tb_word))

            # Compute line-relative positions and add to main index
            for key, words in line_words.items():
                # Assign line positions (1-based)
                for i, (form, tb_word) in enumerate(words, 1):
                    tb_word.line_position = i

                # Add to main index
                if key not in self.index[work_id]:
                    self.index[work_id][key] = []
                self.index[work_id][key].extend(words)

        self.available_works.add(work_id)

    def _parse_cite(self, cite: str) -> tuple:
        """
        Parse cite URN to extract book and line.

        Args:
            cite: URN like "urn:cts:greekLit:tlg0012.tlg001:1.1"

        Returns:
            (book, line) tuple or (None, None) if invalid
        """
        if not cite or not cite.strip():
            return (None, None)

        # Extract the reference part after the last colon
        parts = cite.split(':')
        if len(parts) < 5:
            return (None, None)

        ref = parts[-1]  # e.g., "1.1" or "1.1.5"
        if not ref or not ref.strip():
            return (None, None)

        ref_parts = ref.split('.')

        if len(ref_parts) >= 2:
            try:
                # Handle cases like "1.1" or "1.1-1.2" (take first)
                book_str = ref_parts[0].split('-')[0].strip()
                line_str = ref_parts[1].split('-')[0].strip()
                if not book_str or not line_str:
                    return (None, None)
                book = int(book_str)
                line = int(line_str)
                return (book, line)
            except ValueError:
                return (None, None)

        # Flat citation: just a line number with no book (e.g., "444")
        # Common in drama (Aeschylus, Sophocles) and speeches (Lysias)
        # Treat as book=1
        if len(ref_parts) == 1:
            try:
                line_str = ref_parts[0].split('-')[0].strip()
                if line_str:
                    return (1, int(line_str))
            except ValueError:
                pass

        return (None, None)

    def has_coverage(self, work_id: str) -> bool:
        """Check if treebank data exists for this work."""
        # Normalize work_id (remove edition suffix if present)
        normalized = self._normalize_work_id(work_id)
        return normalized in self.available_works

    def _normalize_work_id(self, work_id: str) -> str:
        """Normalize work_id to tlgXXXX.tlgYYY format."""
        # Handle formats like "tlg0012.tlg001.perseus-grc2"
        match = re.match(r'(tlg\d+\.tlg\d+)', work_id)
        if match:
            return match.group(1)
        return work_id

    def get_line_words(self, work_id: str, book: int, line: int) -> List[tuple]:
        """
        Get all treebank words for a specific line.

        Args:
            work_id: Work identifier (e.g., "tlg0012.tlg001")
            book: Book number
            line: Line number

        Returns:
            List of (form, TreebankWord) tuples in order
        """
        normalized = self._normalize_work_id(work_id)
        if normalized not in self.index:
            return []

        key = (book, line)
        return self.index[normalized].get(key, [])

    def get_word_by_form(self, work_id: str, book: int, line: int,
                         word_form: str) -> Optional[TreebankWord]:
        """
        Get treebank data for a specific word by form.

        Note: This may not be unique if the same word appears twice on a line.
        Use get_line_words() for full control.
        """
        words = self.get_line_words(work_id, book, line)
        for form, tb_word in words:
            if form == word_form:
                return tb_word
        return None

    def build_tree_data_for_line(self, work_id: str, book: int, line: int,
                                  tokens: List[str]) -> Dict[int, Dict]:
        """
        Build tree_data dict compatible with generate_interlinear format.

        Args:
            work_id: Work identifier
            book: Book number
            line: Line number
            tokens: List of tokens from our tokenizer

        Returns:
            Dict mapping position -> tree data, compatible with existing format
        """
        tb_words = self.get_line_words(work_id, book, line)
        if not tb_words:
            return {}

        tree_data = {}
        tb_used = [False] * len(tb_words)

        position = 0
        for token in tokens:
            # Skip punctuation and non-Greek reference markers
            if self._is_punctuation(token):
                continue

            position += 1

            # Find matching treebank word
            for i, (form, tb_word) in enumerate(tb_words):
                if tb_used[i]:
                    continue

                if self._tokens_match(token, form):
                    # Convert to output format
                    tree_data[position] = {
                        'form': form,
                        'pos': map_pos(tb_word.postag),
                        'deprel': map_relation(tb_word.relation),
                        'head': tb_word.head,  # Sentence-relative for now
                        'sentence_position': tb_word.sentence_position,
                        'local_position': position,
                        'treebank_lemma': tb_word.lemma,
                        'treebank_morph': extract_morph(tb_word.postag),
                        'treebank_postag': tb_word.postag,
                    }
                    tb_used[i] = True
                    break

        return tree_data

    def _is_punctuation(self, token: str) -> bool:
        """Check if token is punctuation or a non-Greek reference marker."""
        import string
        punct = set(string.punctuation + '·;')
        if token in punct or all(c in punct for c in token):
            return True
        # ASCII-only alphanumeric tokens are reference markers (Bekker 1214a1, Stephanus 2a, etc.)
        if token.isascii() and token.isalnum():
            return True
        # Speaker labels: all caps Greek (ΣΩ, ΕΥΘ, ΦΑΙΔ, etc.)
        stripped = token.rstrip('.')
        if stripped and all(c.isupper() or c == '.' for c in stripped):
            return True
        return False

    def _tokens_match(self, token1: str, token2: str) -> bool:
        """Check if two tokens match (handling elisions, accent variants)."""
        if token1 == token2:
            return True

        # Normalize: remove combining characters, elision marks, lowercase
        import unicodedata

        # Elision markers that should be stripped for matching
        ELISION_CHARS = {
            '\u02BC',  # MODIFIER LETTER APOSTROPHE (ʼ)
            '\u2019',  # RIGHT SINGLE QUOTATION MARK (')
            '\u0027',  # APOSTROPHE (')
            '\u1FBD',  # GREEK KORONIS (᾽)
            '\u0374',  # GREEK NUMERAL SIGN (ʹ)
            '\u02B9',  # MODIFIER LETTER PRIME (ʹ)
        }

        def normalize(s):
            # Remove combining diacriticals but keep base letters
            s = unicodedata.normalize('NFD', s)
            # Remove combining marks (Mn) and elision characters
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn' and c not in ELISION_CHARS)
            return s.lower()

        return normalize(token1) == normalize(token2)


# Module-level singleton for efficiency
_loader_instance: Optional[PerseusTreebankLoader] = None


def get_treebank_loader(treebank_dir: str = None) -> PerseusTreebankLoader:
    """Get or create the treebank loader singleton."""
    global _loader_instance

    if _loader_instance is None and treebank_dir:
        _loader_instance = PerseusTreebankLoader(treebank_dir)

    return _loader_instance


def init_treebank_loader(treebank_dir: str) -> PerseusTreebankLoader:
    """Initialize the treebank loader (call once at startup)."""
    global _loader_instance
    _loader_instance = PerseusTreebankLoader(treebank_dir)
    return _loader_instance
