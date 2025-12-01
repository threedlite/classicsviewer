#!/usr/bin/env python3
"""
Latin Dictionary Lookup Module

Provides dictionary lookup functionality for Latin words using:
1. Whitaker's Words dictionary entries
2. Latin lemma_map for morphological analysis

Similar to Greek ui_dictionary_lookup.py but adapted for Latin orthography.
"""

import sqlite3
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Set
from functools import lru_cache


@dataclass
class DictionaryEntry:
    """Represents a dictionary entry for Latin."""
    lemma: str
    definition: str
    morph_info: Optional[str] = None
    is_direct_match: bool = False
    confidence: Optional[float] = None
    source: Optional[str] = None


class LatinRepository:
    """Repository for Latin dictionary and morphology lookups."""

    def __init__(self, db_path: str, debug: bool = False):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.debug = debug

    def normalize_latin(self, word: str) -> str:
        """
        Normalize Latin word for lookup.

        - Removes macrons (ā→a, ē→e, etc.)
        - Converts to lowercase
        - Handles u/v and i/j variants
        """
        # First normalize to NFD (decomposed form)
        decomposed = unicodedata.normalize('NFD', word)

        # Remove combining characters (macrons, etc.)
        without_diacritics = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')

        # Convert to lowercase
        lowercased = without_diacritics.lower()

        return lowercased

    def normalize_latin_uv(self, word: str) -> str:
        """Additional normalization for u/v variants."""
        normalized = self.normalize_latin(word)
        # Classical Latin: v→u (e.g., "uirum" for "virum")
        # We try both forms
        return normalized

    def get_all_dictionary_entries(self, word: str, language: str = "latin") -> List[DictionaryEntry]:
        """
        Get all dictionary entries for a Latin word.

        Lookup strategy:
        1. Try exact match on headword
        2. Try normalized form (no macrons, lowercase)
        3. Try lemma_map for inflected forms
        4. Try u/v and i/j variants
        5. Try stripping enclitics

        Note: Dictionary entries are sorted by Whitaker's frequency codes during import,
        so the first result for any lemma is the most common meaning.
        """
        entries = []
        cursor = self.conn.cursor()

        # Normalize the input word
        word_normalized = self.normalize_latin(word)

        # 1. Try exact match on headword
        cursor.execute("""
            SELECT headword, entry_plain, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
        """, (word, language))

        for row in cursor.fetchall():
            if row['entry_plain']:
                entries.append(DictionaryEntry(
                    lemma=row['headword'],
                    definition=row['entry_plain'],
                    source=row['source'],
                    is_direct_match=True
                ))

        # 2. Try normalized (lowercase) form on headword if different
        if not entries and word_normalized != word:
            cursor.execute("""
                SELECT headword, entry_plain, source
                FROM dictionary_entries
                WHERE headword = ? AND language = ?
            """, (word_normalized, language))

            for row in cursor.fetchall():
                if row['entry_plain']:
                    entries.append(DictionaryEntry(
                        lemma=row['headword'],
                        definition=row['entry_plain'],
                        source=row['source'],
                        is_direct_match=True
                    ))

        # 3. Try lemma_map for inflected forms - use indexed lookup only
        if not entries:
            # First try exact match on indexed word_form column
            cursor.execute("""
                SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                       de.entry_plain, de.source as dict_source
                FROM lemma_map lm
                LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?
                WHERE lm.word_form = ?
                ORDER BY lm.confidence DESC
                LIMIT 5
            """, (language, word))

            for row in cursor.fetchall():
                definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                entries.append(DictionaryEntry(
                    lemma=row['lemma'],
                    definition=definition,
                    morph_info=row['morph_info'],
                    confidence=row['confidence'],
                    source=row['dict_source'] or row['source'],
                    is_direct_match=False
                ))

        # 3b. Try normalized form in lemma_map (lowercase) if different from original
        if not entries and word_normalized != word:
            cursor.execute("""
                SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                       de.entry_plain, de.source as dict_source
                FROM lemma_map lm
                LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?
                WHERE lm.word_form = ?
                ORDER BY lm.confidence DESC
                LIMIT 5
            """, (language, word_normalized))

            for row in cursor.fetchall():
                definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                entries.append(DictionaryEntry(
                    lemma=row['lemma'],
                    definition=definition,
                    morph_info=row['morph_info'],
                    confidence=row['confidence'],
                    source=row['dict_source'] or row['source'],
                    is_direct_match=False
                ))

        # 4. Try u/v variants in lemma_map (classical Latin often uses 'u' where medieval uses 'v')
        if not entries:
            # Try replacing v with u
            word_u = word_normalized.replace('v', 'u')
            if word_u != word_normalized:
                cursor.execute("""
                    SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                           de.entry_plain, de.source as dict_source
                    FROM lemma_map lm
                    LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?
                    WHERE lm.word_form = ?
                    ORDER BY lm.confidence DESC
                    LIMIT 5
                """, (language, word_u))

                for row in cursor.fetchall():
                    definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                    entries.append(DictionaryEntry(
                        lemma=row['lemma'],
                        definition=definition,
                        morph_info=row['morph_info'],
                        confidence=row['confidence'],
                        source=row['dict_source'] or row['source'],
                        is_direct_match=False
                    ))

            # Try replacing u with v
            if not entries:
                word_v = word_normalized.replace('u', 'v')
                if word_v != word_normalized:
                    cursor.execute("""
                        SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                               de.entry_plain, de.source as dict_source
                        FROM lemma_map lm
                        LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?
                        WHERE lm.word_form = ?
                        ORDER BY lm.confidence DESC
                        LIMIT 5
                    """, (language, word_v))

                    for row in cursor.fetchall():
                        definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                        entries.append(DictionaryEntry(
                            lemma=row['lemma'],
                            definition=definition,
                            morph_info=row['morph_info'],
                            confidence=row['confidence'],
                            source=row['dict_source'] or row['source'],
                            is_direct_match=False
                        ))

        # 5. Try i/j variants in lemma_map (j is sometimes used for consonantal i)
        if not entries:
            word_i = word_normalized.replace('j', 'i')
            if word_i != word_normalized:
                cursor.execute("""
                    SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                           de.entry_plain, de.source as dict_source
                    FROM lemma_map lm
                    LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?
                    WHERE lm.word_form = ?
                    ORDER BY lm.confidence DESC
                    LIMIT 5
                """, (language, word_i))

                for row in cursor.fetchall():
                    definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                    entries.append(DictionaryEntry(
                        lemma=row['lemma'],
                        definition=definition,
                        morph_info=row['morph_info'],
                        confidence=row['confidence'],
                        source=row['dict_source'] or row['source'],
                        is_direct_match=False
                    ))

        # 6. Try stripping Latin enclitics (-que, -ve, -ne)
        if not entries:
            enclitic_info = self._strip_enclitic(word_normalized)
            if enclitic_info:
                base_word, enclitic_meaning = enclitic_info
                # Recursively look up the base word
                base_entries = self.get_all_dictionary_entries(base_word, language)
                if base_entries:
                    # Found the base word - modify the first entry to include enclitic
                    for entry in base_entries:
                        # Prepend the enclitic meaning to the definition
                        modified_def = f"{entry.definition} + {enclitic_meaning}"
                        entries.append(DictionaryEntry(
                            lemma=entry.lemma,
                            definition=modified_def,
                            morph_info=entry.morph_info,
                            confidence=entry.confidence,
                            source=entry.source,
                            is_direct_match=False
                        ))

        return entries

    def _strip_enclitic(self, word: str) -> Optional[tuple]:
        """
        Check if word has a Latin enclitic suffix and return (base_word, enclitic_meaning).

        Common Latin enclitics:
        - -que = "and" (most common)
        - -ve = "or"
        - -ne = interrogative particle (makes a yes/no question)

        Returns None if no enclitic found.
        """
        word_lower = word.lower()

        # Check for -que (and) - most common
        if len(word_lower) > 3 and word_lower.endswith('que'):
            base = word_lower[:-3]
            # Avoid false positives: some words naturally end in -que
            # like 'aeque', 'usque', 'neque', 'atque', 'itaque', 'quoque'
            false_positives = {'aeq', 'usq', 'neq', 'atq', 'itaq', 'quoq', 'ubiq', 'undiq', 'utiq', 'pleriq', 'deniq'}
            if base not in false_positives and len(base) >= 2:
                return (base, '-que (and)')

        # Check for -ve (or)
        if len(word_lower) > 2 and word_lower.endswith('ve'):
            base = word_lower[:-2]
            # Avoid words that naturally end in -ve
            false_positives = {'si', 'ni', 'seu', 'iu'}  # sive, nive, seuve not common
            if base not in false_positives and len(base) >= 2:
                return (base, '-ve (or)')

        # Check for -ne (question marker)
        if len(word_lower) > 2 and word_lower.endswith('ne'):
            base = word_lower[:-2]
            # Many words naturally end in -ne: omne, bene, sine, etc.
            # Only strip if base is substantial and makes sense
            # This is trickier, so we'll be conservative
            false_positives = {'om', 'be', 'si', 'u', 'pla', 'ple'}
            if base not in false_positives and len(base) >= 3:
                return (base, '-ne (?)')

        return None

    def get_morph_info(self, word: str) -> Optional[str]:
        """Get morphological information for a word from lemma_map."""
        cursor = self.conn.cursor()
        word_normalized = self.normalize_latin(word)

        # Try exact match first (uses index)
        cursor.execute("""
            SELECT morph_info FROM lemma_map
            WHERE word_form = ?
            AND morph_info IS NOT NULL AND morph_info != ''
            ORDER BY confidence DESC
            LIMIT 1
        """, (word,))

        row = cursor.fetchone()
        if row:
            return row[0]

        # Try normalized form if different
        if word_normalized != word:
            cursor.execute("""
                SELECT morph_info FROM lemma_map
                WHERE word_form = ?
                AND morph_info IS NOT NULL AND morph_info != ''
                ORDER BY confidence DESC
                LIMIT 1
            """, (word_normalized,))

            row = cursor.fetchone()
            return row[0] if row else None

        return None


def extract_gloss(entry: DictionaryEntry) -> str:
    """
    Extract a simple English gloss from a Latin dictionary entry.

    Whitaker's format is cleaner than LSJ - definitions are already English
    with part of speech markers like "(n.)", "(v.)", "(adj.)", etc.

    Preserves enclitic suffixes like "+ -que (and)" at the end.
    """
    if not entry or not entry.definition:
        return "???"

    text = entry.definition.strip()

    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)

    # Remove part of speech markers at start
    text = re.sub(r'^\([^)]+\)\s*', '', text)

    # Check for enclitic suffix (e.g., "+ -que (and)", "+ -ve (or)", "+ -ne (?)")
    # These appear at the end of definitions for words with enclitics stripped
    enclitic_suffix = ""
    enclitic_match = re.search(r'\s*\+\s*-(\w+)\s*\(([^)]+)\)\s*$', text)
    if enclitic_match:
        # Extract the enclitic meaning (e.g., "and", "or", "?")
        enclitic_meaning = enclitic_match.group(2)
        enclitic_suffix = f" + {enclitic_meaning}"
        # Remove the enclitic from text for processing
        text = text[:enclitic_match.start()].strip()

    # Split on semicolons and take first meaning
    parts = text.split(';')
    if parts:
        text = parts[0].strip()

    # Split on commas if still too long
    if len(text) > 50:
        comma_parts = text.split(',')
        if comma_parts:
            text = comma_parts[0].strip()

    # Remove trailing punctuation
    text = text.rstrip('.,;:')

    # Re-append enclitic suffix
    text = text + enclitic_suffix

    # Truncate if still too long
    if len(text) > 50:
        text = text[:47] + '...'

    # Return "???" if empty
    if not text or len(text) < 2:
        return "???"

    return text


if __name__ == "__main__":
    # Test the module standalone
    import sys

    if len(sys.argv) < 2:
        print("Usage: python latin_dictionary_lookup.py <database_path> [word]")
        sys.exit(1)

    db_path = sys.argv[1]
    repo = LatinRepository(db_path)

    if len(sys.argv) >= 3:
        word = sys.argv[2]
        entries = repo.get_all_dictionary_entries(word, "latin")
        print(f"\nLookup results for '{word}':")
        for entry in entries:
            gloss = extract_gloss(entry)
            print(f"  Lemma: {entry.lemma}")
            print(f"  Definition: {entry.definition[:100]}...")
            print(f"  Gloss: {gloss}")
            print(f"  Source: {entry.source}")
            print()
    else:
        # Test some common words
        test_words = ['arma', 'virum', 'cano', 'Troiae', 'qui', 'primus', 'ab', 'oris']
        for word in test_words:
            entries = repo.get_all_dictionary_entries(word, "latin")
            if entries:
                gloss = extract_gloss(entries[0])
                print(f"{word}: {gloss} ({entries[0].source})")
            else:
                print(f"{word}: ???")
