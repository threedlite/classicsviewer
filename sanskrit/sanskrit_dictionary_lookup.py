#!/usr/bin/env python3
"""
Sanskrit Dictionary Lookup Module

Provides dictionary lookup functionality for Sanskrit words using:
1. DCS lemma IDs (for DCS texts with CoNLL-U data)
2. Word form lookup (for custom texts like Bhagavad Gita, Rig Veda)

Similar to Greek ui_dictionary_lookup.py but leverages DCS pre-identified lemmas.
"""

import sqlite3
import csv
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class DictionaryEntry:
    """Represents a dictionary entry."""
    lemma: str
    lemma_id: Optional[str]
    definition: str
    grammar: str
    source: str


class SanskritRepository:
    """
    Repository for Sanskrit dictionary and morphology lookups.

    Supports two lookup modes:
    1. By lemma_id (DCS texts) - most accurate
    2. By word form (custom texts) - uses morphology table
    """

    def __init__(self, db_path: str):
        """
        Initialize repository with database connection.

        Args:
            db_path: Path to Sanskrit database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

        # Load DCS dictionary and morphology into memory for fast lookups
        self.dcs_dictionary = self._load_dcs_dictionary()
        self.dcs_morphology = self._load_dcs_morphology()

    def _load_dcs_dictionary(self) -> Dict[str, Dict]:
        """Load DCS dictionary CSV into memory."""
        dcs_dict_path = Path(__file__).parent / "dcs_sanskrit_dictionary.csv"

        if not dcs_dict_path.exists():
            print(f"Warning: DCS dictionary not found at {dcs_dict_path}")
            print("Run extract_dcs_lexicon.py first to generate dictionary")
            return {}

        dictionary = {}
        with open(dcs_dict_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lemma = row['lemma']
                definition = row['definition']

                # Extract lemma_id from source_name (format: "DCS (ID: 12345)")
                lemma_id = None
                source = row['source_name']
                if 'ID:' in source:
                    lemma_id = source.split('ID:')[1].strip().rstrip(')')

                entry = {
                    'lemma_id': lemma_id,
                    'definition': definition,
                    'transliteration': row['transliteration'],
                    'source': source
                }

                # Priority system for selecting best definition
                if lemma in dictionary:
                    existing_def = dictionary[lemma]['definition']

                    # Check if new entry is pure German (heuristic)
                    is_german = self._is_german_definition(definition)

                    existing_priority = self._get_definition_priority(existing_def)
                    new_priority = self._get_definition_priority(definition)

                    # If new entry is German, heavily penalize it
                    if is_german:
                        new_priority += 10

                    if new_priority < existing_priority:
                        dictionary[lemma] = entry
                    # Keep existing if same priority
                else:
                    # Only add if not pure German
                    if not self._is_german_definition(definition):
                        dictionary[lemma] = entry

        print(f"Loaded {len(dictionary):,} entries from DCS dictionary")
        return dictionary

    def _is_german_definition(self, definition: str) -> bool:
        """
        Check if a definition is primarily in German.

        Returns True if the definition appears to be pure German with no English.
        """
        # Skip past the POS marker
        text = definition
        if text.startswith('('):
            close_idx = text.find(')')
            if close_idx > 0:
                text = text[close_idx + 1:].strip()

        # Check for German-only indicators
        german_chars = ['ä', 'ö', 'ü', 'ß', '￶', '￤']
        common_german_words = ['der', 'die', 'das', 'als', 'von', 'zu', 'den', 'Eigenschaft',
                              'Gott', 'G￶ttern', 'denn', 'jener', 'Schnelligkeit', 'Wirklichkeit']

        # If it has German chars, it's likely German
        if any(c in text for c in german_chars):
            return True

        # If it starts with common German words, likely German
        words = text.split()
        if words and words[0] in common_german_words:
            return True

        return False

    def _get_definition_priority(self, definition: str) -> int:
        """
        Get priority for definition selection (lower is better).

        Priority order:
        1. Pronouns and indeclinables: (pron), (ind) - most fundamental
        2. Common nouns: (m), (n) - core meanings
        3. Adjectives: (adj) - modifying meanings
        4. Feminine nouns: (f) - often derivative
        5. Verbs and roots - usually technical
        6. [gramm.] and [rel.] markers - grammatical terms, least useful
        """
        # Get the part-of-speech marker (first parenthesized element)
        if definition.startswith('('):
            close_idx = definition.find(')')
            if close_idx > 0:
                pos = definition[:close_idx + 1]

                # Check if it's a purely technical entry
                if '[gramm.]' in pos or '[rel.]' in pos:
                    return 6

                # Verb roots like (6. Ā.)
                if pos[1:].startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')):
                    return 5

                # Pronouns and particles are most fundamental in Sanskrit
                if pos in ['(pron)', '(ind)']:
                    return 1

                # Common masculine/neuter nouns
                if pos in ['(m)', '(n)']:
                    return 2

                # Adjectives
                if pos == '(adj)':
                    return 3

                # Feminine nouns (often derivatives or less common)
                if pos == '(f)':
                    return 4

        # Unknown format - medium priority
        return 3

    def _load_dcs_morphology(self) -> Dict[str, str]:
        """Load DCS morphology CSV into memory (inflected form → lemma)."""
        dcs_morph_path = Path(__file__).parent / "dcs_sanskrit_morphology.csv"

        if not dcs_morph_path.exists():
            print(f"Warning: DCS morphology not found at {dcs_morph_path}")
            print("Run extract_dcs_morphology.py to generate morphology data")
            return {}

        morphology = {}
        with open(dcs_morph_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                inflected = row['inflected_form']
                lemma = row['lemma']
                # Store most frequent lemma for each form
                if inflected not in morphology:
                    morphology[inflected] = lemma

        print(f"Loaded {len(morphology):,} morphology entries")
        return morphology

    def lookup_by_lemma(self, lemma: str) -> Optional[DictionaryEntry]:
        """
        Look up word by lemma (dictionary form).

        Args:
            lemma: Sanskrit word in Devanagari

        Returns:
            DictionaryEntry if found, None otherwise
        """
        if lemma in self.dcs_dictionary:
            entry = self.dcs_dictionary[lemma]
            return DictionaryEntry(
                lemma=lemma,
                lemma_id=entry['lemma_id'],
                definition=entry['definition'],
                grammar='',  # Grammar info included in definition
                source=entry['source']
            )

        return None

    def lookup_by_form(self, word_form: str) -> Optional[DictionaryEntry]:
        """
        Look up word by inflected form using morphology data.

        For custom texts (Bhagavad Gita, Rig Veda) without CoNLL-U data.

        Args:
            word_form: Inflected Sanskrit word in Devanagari

        Returns:
            DictionaryEntry if found, None otherwise
        """
        # Try morphology lookup FIRST (inflected form → lemma)
        # This is more accurate than direct dictionary lookup for inflected forms
        if word_form in self.dcs_morphology:
            lemma = self.dcs_morphology[word_form]
            entry = self.lookup_by_lemma(lemma)
            if entry:
                return entry

        # Fall back to direct lookup only if morphology doesn't have it
        if word_form in self.dcs_dictionary:
            return self.lookup_by_lemma(word_form)

        return None

    def lookup_best_match(self, word: str, lemma: Optional[str] = None) -> Optional[DictionaryEntry]:
        """
        Find best dictionary match for a word.

        Tries in order:
        1. Exact lemma match (if lemma provided)
        2. Exact word form match
        3. Morphology table lookup

        Args:
            word: Word form in Devanagari
            lemma: Optional lemma (from CoNLL-U data)

        Returns:
            DictionaryEntry if found, None otherwise
        """
        # Try lemma first if provided
        if lemma:
            entry = self.lookup_by_lemma(lemma)
            if entry:
                return entry

        # Try word form
        return self.lookup_by_form(word)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def extract_gloss(definition: str, max_length: int = 30) -> str:
    """
    Extract concise gloss from DCS definition.

    DCS format: "(grammar) meaning1, meaning2, ..."
    Example: "(adj.) first, original, primeval"

    Args:
        definition: Full dictionary definition
        max_length: Maximum gloss length (default 30 for conciseness)

    Returns:
        Concise gloss string
    """
    if not definition:
        return "?"

    import re

    text = definition

    # Remove grammar info in parentheses at start: "(m) ", "(adj) ", etc.
    if text.startswith('('):
        close_idx = text.find(')')
        if close_idx > 0:
            text = text[close_idx + 1:].strip()

    # Skip entries that are purely grammatical/technical
    if text.startswith('[gramm.]'):
        text = text.replace('[gramm.]', '').strip()

    # Remove all bracketed content like [min.], [medic.], etc.
    text = re.sub(r'\[.*?\]', '', text).strip()

    # Remove parenthetical content (often just clarifications or German)
    text = re.sub(r'\(.*?\)', '', text).strip()

    # Handle German/English mixed entries - prefer English
    # Split on semicolons and filter
    if ';' in text:
        parts = [p.strip() for p in text.split(';')]
        english_parts = []

        for part in parts:
            if not part:
                continue

            # Skip obvious German (contains umlauts or special chars)
            if any(c in part for c in ['ä', 'ö', 'ü', 'ß', '￼']):
                continue

            # Skip common German words
            german_words = ['denn', 'jener', 'Gang', 'als', 'von', 'der', 'die', 'das',
                          'Eigenschaft', 'Gott', 'G￶ttern', 'Nominalst￤mmen', 'zu',
                          'Auslaut', 'Schnelligkeit', 'in', 'Wirklichkeit']
            if any(gw in part for gw in german_words):
                continue

            # Skip botanical names (Genus species)
            if re.match(r'^[A-Z][a-z]+ [a-z]+$', part):
                continue

            english_parts.append(part)

        # Use first English part if found
        if english_parts:
            text = english_parts[0]
        elif parts:
            # If all were German, use first part anyway
            text = parts[0]

    # Take first meaning before comma
    if ',' in text:
        text = text.split(',')[0].strip()

    # Clean up extra whitespace
    text = ' '.join(text.split())

    # Truncate if still too long
    if len(text) > max_length:
        # Try to break at word boundary
        words = text[:max_length].rsplit(' ', 1)
        if len(words) > 1:
            text = words[0]
        else:
            # No space found, just truncate
            text = text[:max_length]

    return text if text else "?"


def test_lookups():
    """Test dictionary lookups with sample words."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 sanskrit_dictionary_lookup.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]

    print("=" * 70)
    print("Sanskrit Dictionary Lookup Test")
    print("=" * 70)

    test_words = [
        ('आत्मा', None, 'Direct word lookup'),
        ('आत्मन्', None, 'Lemma lookup'),
        ('भगवति', 'भगवन्त्', 'Word with lemma'),
    ]

    with SanskritRepository(db_path) as repo:
        for word, lemma, description in test_words:
            print(f"\n{description}:")
            print(f"  Word: {word}")
            if lemma:
                print(f"  Lemma: {lemma}")

            entry = repo.lookup_best_match(word, lemma)

            if entry:
                print(f"  ✓ Found: {entry.lemma}")
                print(f"    Definition: {entry.definition}")
                gloss = extract_gloss(entry.definition)
                print(f"    Gloss: {gloss}")
            else:
                print(f"  ✗ Not found")


if __name__ == '__main__':
    test_lookups()
