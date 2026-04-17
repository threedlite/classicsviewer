#!/usr/bin/env python3
"""
GLAUx Treebank Loader

Loads and indexes GLAUx Ancient Greek treebank data for integration
with interlinear generation.

GLAUx provides 20M tokens of Ancient Greek with 97.2% morphology accuracy,
98.8% lemma accuracy. It uses the same AGDT format as Perseus Treebank
(9-char postag, same relation labels).

On-demand loading: Only parses metadata at init (~1s). Each work's XML is
loaded lazily on first access, keeping memory usage proportional to the
number of works actually processed (typically 1 per worker).

Poetry works: Indexed by (book, line) for O(1) lookup.
Prose works: Indexed sequentially per (work, book), matched by text content
             using a cursor that advances through the GLAUx word list.
"""

import os
import re
import string
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from dataclasses import dataclass

# Reuse AGDT format functions from treebank_loader
try:
    from .treebank_loader import (
        TreebankWord, POS_MAP, RELATION_MAP,
        map_pos, map_relation, extract_morph
    )
except ImportError:
    from treebank_loader import (
        TreebankWord, POS_MAP, RELATION_MAP,
        map_pos, map_relation, extract_morph
    )

# Punctuation set (module-level for performance)
# Include Unicode quotes/dashes that appear in Perseus texts
_PUNCT = set(string.punctuation + '·;\u2018\u2019\u201C\u201D\u2014\u2013\u00AB\u00BB')

# Elision markers stripped for matching
_ELISION_CHARS = {
    '\u02BC', '\u2019', '\u0027', '\u1FBD', '\u0374', '\u02B9',
}


def _normalize_form(s: str) -> str:
    """Normalize a Greek word form for comparison: strip diacritics, lowercase, strip trailing punct."""
    # Strip leading/trailing punctuation (our tokens may have attached , . ; etc.)
    s = s.strip(''.join(_PUNCT))
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn' and c not in _ELISION_CHARS)
    return s.lower()


def _is_punctuation(token: str) -> bool:
    """Check if token is punctuation, a section marker, or a non-Greek token."""
    if token in _PUNCT or all(c in _PUNCT for c in token):
        return True
    # Section markers: [1.2], [57a], [320b], etc.
    if token.startswith('[') and token.endswith(']'):
        return True
    # ASCII-only tokens: digits, letters, or mixed (section number fragments,
    # Bekker refs like 980a21, Stephanus like 57a, etc.)
    if token.isascii() and token.isalnum():
        return True
    # Speaker labels: all caps + period (ΕΧ., ΦΑΙΔ., ΣΩ.)
    stripped = token.rstrip('.')
    if stripped and all(c.isupper() or c == '.' for c in stripped):
        return True
    return False


def _tokens_match(token1: str, token2: str) -> bool:
    """Check if two tokens match (handling elisions, accent variants)."""
    if token1 == token2:
        return True
    return _normalize_form(token1) == _normalize_form(token2)


class GlauxLoader:
    """
    Load and index GLAUx treebank data for fast lookup.

    On-demand loading: metadata is parsed at init to know which works are
    available. Each work's XML is loaded lazily on first access.

    Poetry index: {work_id: {(book, line): [(form, TreebankWord), ...]}}
    Prose index:  {work_id: {book: [(form, TreebankWord), ...]}}
    """

    def __init__(self, glaux_dir: str):
        self._xml_dir: Optional[Path] = None
        # Metadata: work_id -> list of XML filenames
        self._work_to_files: Dict[str, List[str]] = {}
        # Loaded data (populated on demand)
        self._poetry_index: Dict[str, Dict[tuple, List[tuple]]] = {}
        self._prose_index: Dict[str, Dict[int, List[tuple]]] = {}
        self._loaded_works: set = set()  # Works whose XML has been parsed
        self._prose_works: set = set()
        self._prose_cursors: Dict[Tuple[str, int], int] = {}

        self._init_metadata(glaux_dir)

    def _init_metadata(self, glaux_dir: str):
        """Parse metadata only — no XML loading."""
        glaux_path = Path(glaux_dir)
        metadata_file = glaux_path / "metadata.txt"
        xml_dir = glaux_path / "xml"

        if not metadata_file.exists():
            print(f"  GLAUx metadata not found: {metadata_file}")
            return

        if not xml_dir.exists():
            print(f"  GLAUx xml directory not found: {xml_dir}")
            return

        self._xml_dir = xml_dir
        self._work_to_files = self._parse_metadata(metadata_file)

        # Verify which XML files actually exist
        valid_works = {}
        for work_id, filenames in self._work_to_files.items():
            existing = [f for f in filenames if (xml_dir / f).exists()]
            if existing:
                valid_works[work_id] = existing
        self._work_to_files = valid_works

        print(f"  GLAUx metadata loaded: {len(self._work_to_files)} works available (on-demand loading)")

    def _parse_metadata(self, metadata_file: Path) -> Dict[str, List[str]]:
        """Parse metadata.txt to build TLG work_id -> XML filename mapping."""
        tlg_to_files: Dict[str, List[str]] = {}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            header = f.readline()
            for line in f:
                line = line.strip()
                if not line:
                    continue

                fields = line.split('\t')
                if len(fields) < 2:
                    continue

                glaux_text_id = fields[0].strip()
                tlg_raw = fields[1].strip()

                if not tlg_raw or not glaux_text_id:
                    continue

                tlg_match = re.match(r'(\d{4})-(\d{3})', tlg_raw)
                if not tlg_match:
                    continue

                work_id = f"tlg{tlg_match.group(1)}.tlg{tlg_match.group(2)}"
                xml_filename = f"{tlg_raw}.xml"

                if work_id not in tlg_to_files:
                    tlg_to_files[work_id] = []
                if xml_filename not in tlg_to_files[work_id]:
                    tlg_to_files[work_id].append(xml_filename)

        return tlg_to_files

    def _ensure_loaded(self, work_id: str):
        """Load a work's XML on demand if not already loaded."""
        if work_id in self._loaded_works:
            return
        if work_id not in self._work_to_files:
            return
        if self._xml_dir is None:
            return

        for xml_filename in self._work_to_files[work_id]:
            xml_path = self._xml_dir / xml_filename
            self._load_xml_file(xml_path, work_id)

        self._loaded_works.add(work_id)

    def _load_xml_file(self, xml_path: Path, work_id: str) -> str:
        """Parse a single GLAUx XML file and index its data."""
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            print(f"  Warning: Failed to parse GLAUx XML {xml_path.name}: {e}")
            return 'error'

        root = tree.getroot()

        first_sentence = root.find('sentence')
        if first_sentence is None:
            return 'error'

        first_word = first_sentence.find('word')
        if first_word is None:
            return 'error'

        has_line = first_word.get('line') is not None

        if has_line:
            if work_id not in self._poetry_index:
                self._poetry_index[work_id] = {}
            for sentence in root.iter('sentence'):
                self._process_poetry_sentence(sentence, work_id)
            # Reassign line_position after all sentences are loaded,
            # since antilabe sub-lines (49b, 49c) merge into the base line
            for key, words in self._poetry_index[work_id].items():
                for i, (form, tb_word) in enumerate(words, 1):
                    tb_word.line_position = i
            return 'poetry'
        else:
            if work_id not in self._prose_index:
                self._prose_index[work_id] = {}
            for sentence in root.iter('sentence'):
                self._process_prose_sentence(sentence, work_id)
            self._prose_works.add(work_id)
            return 'prose'

    def _process_poetry_sentence(self, sentence, work_id: str):
        """Process a sentence from a poetry work (has line attributes)."""
        sentence_id = self._get_sentence_id(sentence)
        word_elements = sentence.findall('word')

        global_to_sent_pos = {}
        nopunct_pos = 0
        word_data_list = []

        for word_elem in word_elements:
            form = word_elem.get('form', '')
            postag = word_elem.get('postag', '---------')

            if postag.startswith('u') or not form or form in ',;.·':
                continue
            # Skip artificial elliptic nodes (E placeholders for antilabe)
            if word_elem.get('artificial') == 'elliptic':
                continue

            global_id = self._get_int_attr(word_elem, 'id')
            nopunct_pos += 1
            global_to_sent_pos[global_id] = nopunct_pos

            line_attr = word_elem.get('line', '')
            div_book = word_elem.get('div_book', '')
            book, line = self._parse_line_attr(line_attr, div_book)
            if book is None:
                continue

            word_data_list.append({
                'form': form,
                'lemma': word_elem.get('lemma', ''),
                'postag': postag,
                'relation': word_elem.get('relation', ''),
                'orig_head': self._get_int_attr(word_elem, 'head'),
                'global_id': global_id,
                'nopunct_pos': nopunct_pos,
                'book': book,
                'line': line,
            })

        line_words: Dict[tuple, List[tuple]] = {}
        for wd in word_data_list:
            remapped_head = global_to_sent_pos.get(wd['orig_head'], 0)
            key = (wd['book'], wd['line'])
            if key not in line_words:
                line_words[key] = []
            line_words[key].append((wd['form'], self._make_treebank_word(wd, remapped_head, sentence_id)))

        for key, words in line_words.items():
            if key not in self._poetry_index[work_id]:
                self._poetry_index[work_id][key] = []
            self._poetry_index[work_id][key].extend(words)

    def _process_prose_sentence(self, sentence, work_id: str):
        """Process a sentence from a prose work (no line attributes, sequential indexing)."""
        sentence_id = self._get_sentence_id(sentence)
        word_elements = sentence.findall('word')

        global_to_sent_pos = {}
        nopunct_pos = 0
        word_data_list = []

        for word_elem in word_elements:
            form = word_elem.get('form', '')
            postag = word_elem.get('postag', '---------')

            if postag.startswith('u') or not form or form in ',;.·':
                continue
            if word_elem.get('artificial') == 'elliptic':
                continue

            global_id = self._get_int_attr(word_elem, 'id')
            nopunct_pos += 1
            global_to_sent_pos[global_id] = nopunct_pos

            div_book = word_elem.get('div_book', '1')
            try:
                book = int(div_book)
            except ValueError:
                book = 1

            word_data_list.append({
                'form': form,
                'lemma': word_elem.get('lemma', ''),
                'postag': postag,
                'relation': word_elem.get('relation', ''),
                'orig_head': self._get_int_attr(word_elem, 'head'),
                'global_id': global_id,
                'nopunct_pos': nopunct_pos,
                'book': book,
            })

        for wd in word_data_list:
            remapped_head = global_to_sent_pos.get(wd['orig_head'], 0)
            tb_word = self._make_treebank_word(wd, remapped_head, sentence_id)
            book = wd['book']
            if book not in self._prose_index[work_id]:
                self._prose_index[work_id][book] = []
            self._prose_index[work_id][book].append((wd['form'], tb_word))

    def _make_treebank_word(self, wd: dict, remapped_head: int, sentence_id: int) -> TreebankWord:
        return TreebankWord(
            form=wd['form'], lemma=wd['lemma'], postag=wd['postag'],
            head=remapped_head, relation=wd['relation'],
            sentence_id=sentence_id, sentence_position=wd['nopunct_pos'],
            line_position=0
        )

    def _get_sentence_id(self, sentence) -> int:
        try:
            return int(sentence.get('id', '0'))
        except ValueError:
            return 0

    def _get_int_attr(self, elem, attr: str, default: int = 0) -> int:
        val = elem.get(attr, '')
        try:
            return int(val) if val else default
        except ValueError:
            return default

    def _parse_line_attr(self, line_attr: str, div_book: str) -> tuple:
        """Parse GLAUx line attribute (poetry): "book.line" -> (book, line).

        Handles formats:
        - "1.5" -> (1, 5) — book.line
        - "5" with div_book="2" -> (2, 5) — line with separate book attr
        - "5" with no div_book -> (1, 5) — single-book works (drama etc.)
        """
        if not line_attr:
            return (None, None)
        # Strip trailing alphabetic suffixes used for antilabe sub-lines
        # e.g., "49b", "49c" -> "49" (multiple speakers sharing a verse line)
        line_attr = re.sub(r'[a-z]+$', '', line_attr)
        if not line_attr:
            return (None, None)
        parts = line_attr.split('.')
        if len(parts) >= 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except ValueError:
                pass
        # Single line number — use div_book if available, else default to book 1
        try:
            line = int(parts[0])
            if line <= 0:
                return (None, None)
        except ValueError:
            return (None, None)
        if div_book:
            try:
                return (int(div_book), line)
            except ValueError:
                pass
        # No div_book — single-book work (e.g., drama), default to book 1
        return (1, line)

    # --- Public API ---

    @property
    def available_works(self) -> set:
        """All works with GLAUx XML files available (from metadata)."""
        return set(self._work_to_files.keys())

    def has_coverage(self, work_id: str) -> bool:
        """Check if GLAUx data exists for this work."""
        return self._normalize_work_id(work_id) in self._work_to_files

    def is_prose(self, work_id: str) -> bool:
        """Check if work is prose (uses sequential text matching).
        Requires the work to be loaded first."""
        normalized = self._normalize_work_id(work_id)
        self._ensure_loaded(normalized)
        return normalized in self._prose_works

    def reset_prose_cursor(self, work_id: str, book: int):
        """Reset the prose cursor for a new book."""
        normalized = self._normalize_work_id(work_id)
        self._prose_cursors[(normalized, book)] = 0

    def _normalize_work_id(self, work_id: str) -> str:
        # Don't strip _OGL suffix — Glaux line numbers are aligned to the
        # Perseus edition, not the First1KGreek (OGL) edition. Applying
        # Glaux data to OGL texts would misalign glosses to wrong words.
        if '_OGL' in work_id:
            return work_id  # won't match any Glaux key, so coverage = False
        match = re.match(r'(tlg\d+\.tlg\d+)', work_id)
        return match.group(1) if match else work_id

    def build_tree_data_for_line(self, work_id: str, book, line: int,
                                 tokens: List[str]) -> Dict[int, Dict]:
        """Build tree_data dict compatible with generate_interlinear format."""
        normalized = self._normalize_work_id(work_id)
        self._ensure_loaded(normalized)

        # Convert book to int (callers may pass string)
        try:
            book_int = int(book)
        except (ValueError, TypeError):
            book_int = 0

        if normalized in self._prose_works:
            return self._build_prose_tree_data(normalized, book_int, tokens)
        else:
            return self._build_poetry_tree_data(normalized, book_int, line, tokens)

    def _build_poetry_tree_data(self, work_id: str, book: int, line: int,
                                 tokens: List[str]) -> Dict[int, Dict]:
        """Build tree data for a poetry line using (book, line) index."""
        glaux_words = self._poetry_index.get(work_id, {}).get((book, line), [])
        if not glaux_words:
            return {}

        tree_data = {}
        glaux_used = [False] * len(glaux_words)

        position = 0
        for token in tokens:
            if _is_punctuation(token):
                continue
            position += 1

            best_match = None
            for offset in [0, -1, 1, -2, 2]:
                target_idx = position - 1 + offset
                if 0 <= target_idx < len(glaux_words) and not glaux_used[target_idx]:
                    form, tb_word = glaux_words[target_idx]
                    if _tokens_match(token, form):
                        best_match = (target_idx, form, tb_word)
                        break

            if best_match is None:
                for i, (form, tb_word) in enumerate(glaux_words):
                    if not glaux_used[i] and _tokens_match(token, form):
                        best_match = (i, form, tb_word)
                        break

            if best_match is not None:
                idx, form, tb_word = best_match
                tree_data[position] = self._make_tree_entry(form, tb_word, position)
                glaux_used[idx] = True

        return tree_data

    def _build_prose_tree_data(self, work_id: str, book: int,
                                tokens: List[str]) -> Dict[int, Dict]:
        """Build tree data for a prose line using cursor-based text matching."""
        all_words = self._prose_index.get(work_id, {}).get(book, [])
        if not all_words:
            return {}

        cursor_key = (work_id, book)
        cursor = self._prose_cursors.get(cursor_key, 0)

        content_tokens = [(i, t) for i, t in enumerate(tokens) if not _is_punctuation(t)]
        if not content_tokens:
            return {}

        anchor_count = min(3, len(content_tokens))
        anchor_normalized = [_normalize_form(content_tokens[i][1]) for i in range(anchor_count)]

        match_start = self._find_anchor(all_words, anchor_normalized, cursor)

        if match_start is None and cursor > 0:
            # Try searching backward — cursor may have overshot
            # Search backward up to 500 positions, but cap forward to cursor position
            # to avoid false matches far ahead in the text
            back_cursor = max(0, cursor - 500)
            match_start = self._find_anchor(all_words, anchor_normalized, back_cursor,
                                             max_search_pos=cursor + 200)

        if match_start is None:
            return {}

        tree_data = {}
        glaux_pos = match_start
        position = 0

        for token in tokens:
            if _is_punctuation(token):
                continue
            position += 1

            if glaux_pos >= len(all_words):
                break

            # Skip hyphen-prefixed GLAUx tokens (split clitics like -τε)
            while glaux_pos < len(all_words) and all_words[glaux_pos][0].startswith('-'):
                glaux_pos += 1

            if glaux_pos >= len(all_words):
                break

            matched = False
            for offset in [0, 1, -1, 2]:
                check_pos = glaux_pos + offset
                if 0 <= check_pos < len(all_words):
                    form, tb_word = all_words[check_pos]
                    if form.startswith('-'):
                        continue
                    if _tokens_match(token, form):
                        tree_data[position] = self._make_tree_entry(form, tb_word, position)
                        glaux_pos = check_pos + 1
                        matched = True
                        break

                    # Check combined tokens (e.g., 'οὔτε' = 'οὔ' + '-τε')
                    combined_norm = _normalize_form(form)
                    peek = check_pos + 1
                    while peek < check_pos + 3 and peek < len(all_words):
                        if all_words[peek][0].startswith('-'):
                            combined_norm += _normalize_form(all_words[peek][0].lstrip('-'))
                            if combined_norm == _normalize_form(token):
                                tree_data[position] = self._make_tree_entry(form, tb_word, position)
                                glaux_pos = peek + 1
                                matched = True
                                break
                        else:
                            break
                        peek += 1
                    if matched:
                        break

        if tree_data:
            self._prose_cursors[cursor_key] = glaux_pos

        return tree_data

    def _find_anchor(self, all_words: List[tuple], anchor_normalized: List[str],
                     start: int, max_search_pos: Optional[int] = None) -> Optional[int]:
        """Find where the anchor sequence starts in the word list."""
        if not anchor_normalized:
            return None

        if max_search_pos is not None:
            max_search = min(len(all_words), max_search_pos)
        else:
            max_search = min(len(all_words), start + 500)

        for i in range(start, max_search):
            if i >= len(all_words):
                break

            match = True
            glaux_j = 0
            for anchor in anchor_normalized:
                while (i + glaux_j < len(all_words) and
                       all_words[i + glaux_j][0].startswith('-')):
                    glaux_j += 1

                if i + glaux_j >= len(all_words):
                    match = False
                    break

                glaux_form = _normalize_form(all_words[i + glaux_j][0])
                if glaux_form != anchor:
                    combined = glaux_form
                    peek = glaux_j + 1
                    while (peek < glaux_j + 3 and i + peek < len(all_words) and
                           all_words[i + peek][0].startswith('-')):
                        combined += _normalize_form(all_words[i + peek][0].lstrip('-'))
                        if combined == anchor:
                            glaux_j = peek
                            break
                        peek += 1
                    else:
                        match = False
                        break

                    if combined != anchor:
                        match = False
                        break

                glaux_j += 1

            if match:
                return i

        return None

    def _make_tree_entry(self, form: str, tb_word: TreebankWord, position: int) -> dict:
        return {
            'form': form,
            'pos': map_pos(tb_word.postag),
            'deprel': map_relation(tb_word.relation),
            'head': tb_word.head,
            'sentence_position': tb_word.sentence_position,
            'local_position': position,
            'treebank_lemma': tb_word.lemma,
            'treebank_morph': extract_morph(tb_word.postag),
            'treebank_postag': tb_word.postag,
        }
