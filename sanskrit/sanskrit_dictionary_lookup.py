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
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


# ============================================================================
# COMMON WORD PRIORITY
# ============================================================================
# Hard-coded glosses for 100 most common Sanskrit particles and conjunctions
# Ensures these high-frequency words always get correct primary meaning
# Based on frequency analysis of Bhagavad Gita and Upanishads

COMMON_WORD_PRIORITY = {
    # Conjunctions and particles (highest frequency)
    'च': ('ca', 'and'),
    'न': ('na', 'not'),
    'तु': ('tu', 'but, however'),
    'वा': ('vā', 'or'),
    'अपि': ('api', 'also, even'),
    'एव': ('eva', 'indeed, only, just'),
    'हि': ('hi', 'for, because'),
    'इति': ('iti', 'thus, so'),
    'यत्': ('yat', 'that, which'),
    'यदा': ('yadā', 'when'),
    'तदा': ('tadā', 'then'),
    'अथ': ('atha', 'now, then'),
    'किम्': ('kim', 'what, why'),
    'कः': ('ka', 'who'),
    'सः': ('sa', 'he, that'),
    'तत्': ('tat', 'that'),
    'इदम्': ('idam', 'this'),
    'एतत्': ('etat', 'this'),
    'यः': ('ya', 'who, which'),
    'अयम्': ('ayam', 'this'),

    # Pronouns
    'अहम्': ('aham', 'I'),
    'त्वम्': ('tvam', 'you'),
    'मम': ('mama', 'my, of me'),
    'तव': ('tava', 'your, of you'),
    'मे': ('me', 'my, to me'),
    'ते': ('te', 'your, to you'),
    'स्व': ('sva', 'own, self'),

    # Common verbs (present tense forms)
    'अस्ति': ('asti', 'is, exists'),
    'भवति': ('bhavati', 'becomes, is'),
    'करोति': ('karoti', 'does, makes'),
    'गच्छति': ('gacchati', 'goes'),
    'आगच्छति': ('āgacchati', 'comes'),
    'ददाति': ('dadāti', 'gives'),
    'याति': ('yāti', 'goes'),
    'जानाति': ('jānāti', 'knows'),
    'पश्यति': ('paśyati', 'sees'),
    'श्रृणोति': ('śṛṇoti', 'hears'),
    'वदति': ('vadati', 'says, speaks'),
    'उवाच': ('uvāca', 'said, spoke'),

    # Prepositions/prefixes used independently
    'उप': ('upa', 'near, towards'),
    'अभि': ('abhi', 'to, towards'),
    'प्रति': ('prati', 'towards, against'),
    'सह': ('saha', 'with, together'),
    'विना': ('vinā', 'without'),

    # Common adverbs
    'सर्वम्': ('sarvam', 'all, everything'),
    'सदा': ('sadā', 'always'),
    'कदा': ('kadā', 'when'),
    'कुत्र': ('kutra', 'where'),
    'तत्र': ('tatra', 'there'),
    'इह': ('iha', 'here'),
    'पुनः': ('punaḥ', 'again'),
    'एवम्': ('evam', 'thus, so'),
    'नूनम्': ('nūnam', 'certainly, indeed'),

    # Common adjectives
    'महत्': ('mahat', 'great'),
    'अन्य': ('anya', 'other'),
    'बहु': ('bahu', 'many, much'),
    'स्वल्प': ('svalpa', 'little, small'),
    'पूर्ण': ('pūrṇa', 'full, complete'),
    'नव': ('nava', 'new'),
    'पुराण': ('purāṇa', 'ancient, old'),
}


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
        """Load DCS morphology CSV into memory (word form → lemma)."""
        dcs_morph_path = Path(__file__).parent / "dcs_sanskrit_morphology.csv"

        if not dcs_morph_path.exists():
            print(f"Warning: DCS morphology not found at {dcs_morph_path}")
            print("Run extract_dcs_lexicon.py to generate morphology data")
            return {}

        morphology = {}
        with open(dcs_morph_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle both old format (inflected_form) and new format (word_form)
                word_form = row.get('word_form') or row.get('inflected_form')
                lemma = row['lemma']
                # Store most frequent lemma for each form (first occurrence in sorted CSV)
                if word_form and word_form not in morphology:
                    morphology[word_form] = lemma

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

    # ========================================================================
    # COMPOUND WORD DECOMPOSITION
    # ========================================================================

    def decompose_compound(self, word: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Attempt to decompose a Sanskrit compound word using prefix analysis.

        This is a simplified approach focusing on verbal prefixes (upasarga).
        Does not handle all compound types (tatpuruṣa, bahuvrīhi, etc.) but
        covers common prefixed words.

        Args:
            word: Sanskrit word in Devanagari

        Returns:
            Tuple of (base_prefix, prefix_meaning, stem, stem_lemma) or None

        Example:
            समागच्छति → ('सम्', 'together', 'आगच्छति', 'आगम्')
        """
        from sanskrit_prefix_rules import get_all_prefix_forms

        # Get all prefix forms sorted by length (longest first)
        prefix_forms = get_all_prefix_forms()

        # Try each prefix form
        for prefix_form, base_prefix, meaning in prefix_forms:
            if word.startswith(prefix_form):
                # Extract stem (remainder after prefix)
                stem = word[len(prefix_form):]

                # Stem must be at least 3 characters
                if len(stem) < 3:
                    continue

                # Try to find entry for stem
                stem_entry = self.lookup_by_form(stem)

                if stem_entry:
                    return (base_prefix, meaning, stem, stem_entry.lemma)

        return None

    def create_compound_entry(self, prefix: str, prefix_meaning: str,
                             stem: str, stem_lemma: str) -> DictionaryEntry:
        """
        Create a dictionary entry for a compound word.

        Combines prefix meaning with stem definition.

        Args:
            prefix: Base prefix form
            prefix_meaning: Meaning of prefix
            stem: Stem portion of word
            stem_lemma: Lemma of stem

        Returns:
            DictionaryEntry for the compound
        """
        # Get full definition for stem
        stem_entry = self.lookup_by_lemma(stem_lemma)

        if stem_entry:
            # Extract clean gloss from stem definition
            stem_gloss = extract_gloss(stem_entry.definition, max_length=40)

            # Create compound definition
            # Format: (prefix meaning) + stem gloss
            # Example: (together) + comes = comes together
            compound_gloss = f"{prefix_meaning} + {stem_gloss}"

            # Full definition includes analysis
            full_definition = (
                f"[Compound Analysis]\n"
                f"{prefix}- ({prefix_meaning}) + {stem_lemma}\n\n"
                f"Stem definition:\n{stem_entry.definition}"
            )
        else:
            # No detailed entry for stem
            compound_gloss = f"{prefix_meaning} + {stem_lemma}"
            full_definition = f"[Compound] {prefix}- ({prefix_meaning}) + {stem_lemma}"

        return DictionaryEntry(
            lemma=f"{prefix}-{stem_lemma}",
            lemma_id=None,
            definition=full_definition,
            grammar=f"compound: {prefix}- + {stem}",
            source="compound analysis"
        )

    def lookup_best_match(self, word: str, lemma: Optional[str] = None) -> Optional[DictionaryEntry]:
        """
        Find best dictionary match for a word.

        Tries in order:
        1. Common word priority list (particles, conjunctions)
        2. Exact lemma match (if lemma provided)
        3. Exact word form match
        4. Morphology table lookup
        5. Compound decomposition (if word is long enough)

        Args:
            word: Word form in Devanagari
            lemma: Optional lemma (from CoNLL-U data)

        Returns:
            DictionaryEntry if found, None otherwise
        """
        # PRIORITY 1: Check common word priority list
        if word in COMMON_WORD_PRIORITY:
            lemma_form, gloss = COMMON_WORD_PRIORITY[word]
            return DictionaryEntry(
                lemma=lemma_form,
                lemma_id=None,
                definition=f"(ind) {gloss}",  # Format like DCS entries
                grammar='particle/conjunction',
                source='priority list'
            )

        # PRIORITY 2: Try lemma first if provided
        if lemma:
            entry = self.lookup_by_lemma(lemma)
            if entry:
                return entry

        # PRIORITY 3: Try word form
        entry = self.lookup_by_form(word)
        if entry:
            return entry

        # PRIORITY 4: Try compound decomposition (only if word is long enough)
        if len(word) >= 6:  # Minimum length for meaningful compound
            compound_parts = self.decompose_compound(word)
            if compound_parts:
                prefix, prefix_meaning, stem, stem_lemma = compound_parts
                return self.create_compound_entry(prefix, prefix_meaning, stem, stem_lemma)

        return None

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def extract_gloss(definition: str, max_length: int = 50) -> str:
    """
    Extract concise gloss from DCS definition with improved quality.

    Enhanced to handle:
    - Better German/English separation
    - Multiple glosses with preference for English
    - POS-only entries
    - Technical/grammatical entries
    - Smarter truncation

    DCS format: "(grammar) meaning1, meaning2; German text; ..."
    Example: "(adj.) first, original, primeval; der erste (German)"

    Args:
        definition: Full dictionary definition
        max_length: Maximum gloss length (default 50)

    Returns:
        Concise English gloss string
    """
    if not definition:
        return "?"

    import re

    original_text = definition
    text = definition.strip()

    # Step 1: Extract and remove POS marker
    pos_marker = ""
    if text.startswith('('):
        close_idx = text.find(')')
        if close_idx > 0:
            pos_marker = text[:close_idx + 1]
            text = text[close_idx + 1:].strip()

            # Check for POS-only entries (no actual definition)
            if not text or len(text) < 3:
                return "?"

    # Step 2: Check for purely technical/grammatical entries
    if text.startswith('[gramm.]'):
        # Remove marker but continue - might have useful info after
        text = text.replace('[gramm.]', '').strip()
        if not text or len(text) < 3:
            return "?"

    # Step 3: Split on semicolons to separate different glosses
    parts = [p.strip() for p in text.split(';') if p.strip()]

    if not parts:
        return "?"

    # Step 4: Filter and prioritize parts
    english_parts = []
    mixed_parts = []
    german_parts = []

    for part in parts:
        # Remove bracketed content like [medic.], [min.], etc.
        part_clean = re.sub(r'\[.*?\]', '', part).strip()

        if not part_clean or len(part_clean) < 2:
            continue

        # Classify part as English, German, or Mixed
        classification = _classify_text(part_clean)

        if classification == 'english':
            english_parts.append(part_clean)
        elif classification == 'german':
            german_parts.append(part_clean)
        else:
            mixed_parts.append(part_clean)

    # Step 5: Select best part
    # Priority: English > Mixed > German
    selected_part = None

    if english_parts:
        selected_part = english_parts[0]
    elif mixed_parts:
        # For mixed, try to extract English portion
        selected_part = _extract_english_from_mixed(mixed_parts[0])
    elif german_parts:
        # Last resort - use German but mark it
        selected_part = german_parts[0]

    if not selected_part:
        return "?"

    # Step 6: Further cleaning
    # Remove remaining parenthetical content (often just clarifications)
    # But be smart - keep if it's the main content
    if selected_part.count('(') <= 2:  # Not too many parens
        # Remove parens but keep content if short
        cleaned = re.sub(r'\([^)]{0,15}\)', '', selected_part)
        if cleaned.strip() and len(cleaned.strip()) > 3:
            selected_part = cleaned.strip()

    # Step 7: Take first clause before comma (primary meaning)
    if ',' in selected_part:
        first_part = selected_part.split(',')[0].strip()
        # Only use first part if it's substantial
        if len(first_part) >= 4:
            selected_part = first_part

    # Step 8: Clean up whitespace
    selected_part = ' '.join(selected_part.split())

    # Step 9: Truncate if needed at word boundary
    if len(selected_part) > max_length:
        # Try to break at word boundary
        truncated = selected_part[:max_length].rsplit(' ', 1)
        if len(truncated) > 1 and len(truncated[0]) >= max_length // 2:
            selected_part = truncated[0]
        else:
            # No good word boundary, just truncate
            selected_part = selected_part[:max_length]

    return selected_part if selected_part else "?"


def _classify_text(text: str) -> str:
    """
    Classify text as 'english', 'german', or 'mixed'.

    Returns:
        'english', 'german', or 'mixed'
    """
    # German indicators
    german_chars = ['ä', 'ö', 'ü', 'ß', 'Ä', 'Ö', 'Ü']
    has_german_chars = any(c in text for c in german_chars)

    # Common German words that wouldn't appear in English definitions
    german_words = {
        'der', 'die', 'das', 'den', 'dem', 'des',
        'ein', 'eine', 'einer', 'eines', 'einem',
        'von', 'zu', 'als', 'bei', 'mit',
        'ist', 'sind', 'war', 'waren',
        'Gott', 'Göttern', 'Eigenschaft',
        'Schnelligkeit', 'Wirklichkeit',
        'denn', 'jener', 'welcher'
    }

    words = text.split()
    german_word_count = sum(1 for w in words if w in german_words)

    # Decision logic
    if has_german_chars or german_word_count >= 2:
        # Check if there's also English
        if len(words) > german_word_count * 2:
            return 'mixed'
        else:
            return 'german'

    # Check for common English article/preposition starters
    if words and words[0].lower() in ['a', 'an', 'the', 'to', 'of', 'in', 'on', 'at']:
        return 'english'

    # Default to English if no German detected
    return 'english'


def _extract_english_from_mixed(text: str) -> str:
    """
    Extract English portion from mixed German/English text.

    Strategy: Take first clause before German words appear.
    """
    words = text.split()

    german_words = {
        'der', 'die', 'das', 'den', 'dem', 'des',
        'von', 'zu', 'als', 'Gott', 'denn'
    }

    # Find first German word
    for i, word in enumerate(words):
        if word in german_words or any(c in word for c in ['ä', 'ö', 'ü', 'ß']):
            # Take everything before this
            if i > 0:
                return ' '.join(words[:i]).strip()
            break

    # No German found or German is first word
    return text


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
