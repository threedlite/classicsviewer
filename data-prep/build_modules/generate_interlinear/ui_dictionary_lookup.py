#!/usr/bin/env python3
"""
Standalone Python script that replicates the Android Kotlin dictionary retrieval UI.
Follows the exact implementation in PerseusRepository.kt including all layers,
normalization, precedence, sorting, and display logic.
"""

import sqlite3
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
from pathlib import Path


@dataclass
class DictionaryEntry:
    """Matches the Kotlin DictionaryEntry data class"""
    lemma: str
    definition: str
    morph_info: Optional[str] = None
    is_direct_match: bool = False
    confidence: Optional[float] = None
    source: Optional[str] = None
    has_non_treebank_path: bool = True
    insertion_order: int = 0  # Track insertion order for stable sorting


class PerseusRepository:
    """Python replica of PerseusRepository.kt dictionary lookup logic"""

    def __init__(self, db_path: str, debug: bool = False):
        self.db_path = db_path
        self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        self.debug = debug
        self.prefix_cache = {}  # Cache for prefix assimilation rules

    def normalize_apostrophes(self, word: str) -> str:
        """Normalize all apostrophe variants to U+02BC (ʼ)"""
        # First normalize to NFC (precomposed) form
        nfc_normalized = unicodedata.normalize('NFC', word)

        # Normalize all apostrophe variants
        return (nfc_normalized
                .replace("'", "ʼ")   # U+0027 APOSTROPHE → U+02BC
                .replace("\u2019", "ʼ")   # U+2019 RIGHT SINGLE QUOTATION MARK → U+02BC
                .replace("᾿", "ʼ")   # U+1FBF GREEK PSILI → U+02BC
                .replace("᾽", "ʼ")   # U+1FBD GREEK KORONIS → U+02BC
                .replace("′", "ʼ")   # U+2032 PRIME → U+02BC
                .replace("´", "ʼ"))  # U+00B4 ACUTE ACCENT → U+02BC

    def normalize_lunate_sigma(self, word: str) -> str:
        """
        Convert lunate sigma (ϲ/Ϲ) to regular sigma (σ/ς/Σ).
        Some ancient Greek texts use lunate sigma but dictionaries use regular sigma.

        Lunate sigma: U+03F2 (ϲ lowercase), U+03F9 (Ϲ uppercase)
        Regular sigma: U+03C3 (σ medial), U+03C2 (ς final), U+03A3 (Σ uppercase)
        """
        # Replace lunate sigmas with regular sigmas
        result = word.replace('ϲ', 'σ').replace('Ϲ', 'Σ')

        # Convert final σ to ς (standard Greek orthography)
        if result.endswith('σ'):
            result = result[:-1] + 'ς'

        return result

    def has_lunate_sigma(self, word: str) -> bool:
        """Check if word contains lunate sigma characters"""
        return 'ϲ' in word or 'Ϲ' in word

    def normalize_greek(self, word: str) -> str:
        """Only remove punctuation, keep all diacritics"""
        return re.sub(r'[.,;·]', '', word)

    def has_grave_accent(self, word: str) -> bool:
        """Check if word contains any Greek grave accent characters"""
        grave_chars = {
            'ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ',  # Simple grave
            'ἂ', 'ἒ', 'ἢ', 'ἲ', 'ὂ', 'ὒ', 'ὢ',  # With smooth breathing
            'ἃ', 'ἓ', 'ἣ', 'ἳ', 'ὃ', 'ὓ', 'ὣ'   # With rough breathing
        }
        return any(c in grave_chars for c in word)

    def convert_grave_to_acute(self, word: str) -> str:
        """Convert grave accents to acute accents"""
        grave_to_acute_map = {
            # Simple vowels
            'ὰ': 'ά', 'ὲ': 'έ', 'ὴ': 'ή', 'ὶ': 'ί',
            'ὸ': 'ό', 'ὺ': 'ύ', 'ὼ': 'ώ',
            # With smooth breathing
            'ἂ': 'ἄ', 'ἒ': 'ἔ', 'ἢ': 'ἤ', 'ἲ': 'ἴ',
            'ὂ': 'ὄ', 'ὒ': 'ὔ', 'ὢ': 'ὤ',
            # With rough breathing
            'ἃ': 'ἅ', 'ἓ': 'ἕ', 'ἣ': 'ἥ', 'ἳ': 'ἵ',
            'ὃ': 'ὅ', 'ὓ': 'ὕ', 'ὣ': 'ὥ'
        }

        return ''.join(grave_to_acute_map.get(c, c) for c in word)

    def normalize_greek_ultra(self, word: str) -> str:
        """Ultra-aggressive Greek normalization - removes ALL diacritics"""
        # First normalize to NFD (decomposed form)
        decomposed = unicodedata.normalize('NFD', word)

        # Remove all combining characters (diacritics, breathings, etc.)
        # Use unicodedata.category to filter out combining marks
        without_combining = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')

        # Convert to lowercase
        lowercased = without_combining.lower()

        # Replace final sigma with regular sigma
        with_regular_sigma = lowercased.replace('ς', 'σ')

        # Map pre-composed characters to base forms
        diacritic_map = {
            # Vowels with diacritics to plain vowels
            'ά': 'α', 'ὰ': 'α', 'ᾶ': 'α', 'ἀ': 'α', 'ἁ': 'α', 'ἄ': 'α', 'ἅ': 'α', 'ἂ': 'α', 'ἃ': 'α', 'ἆ': 'α', 'ἇ': 'α',
            'ᾳ': 'α', 'ᾷ': 'α', 'ᾴ': 'α', 'ᾲ': 'α', 'ᾀ': 'α', 'ᾁ': 'α', 'ᾄ': 'α', 'ᾅ': 'α', 'ᾂ': 'α', 'ᾃ': 'α', 'ᾆ': 'α', 'ᾇ': 'α',
            'έ': 'ε', 'ὲ': 'ε', 'ἐ': 'ε', 'ἑ': 'ε', 'ἔ': 'ε', 'ἕ': 'ε', 'ἒ': 'ε', 'ἓ': 'ε',
            'ή': 'η', 'ὴ': 'η', 'ῆ': 'η', 'ἠ': 'η', 'ἡ': 'η', 'ἤ': 'η', 'ἥ': 'η', 'ἢ': 'η', 'ἣ': 'η', 'ἦ': 'η', 'ἧ': 'η',
            'ῃ': 'η', 'ῇ': 'η', 'ῄ': 'η', 'ῂ': 'η', 'ᾐ': 'η', 'ᾑ': 'η', 'ᾔ': 'η', 'ᾕ': 'η', 'ᾒ': 'η', 'ᾓ': 'η', 'ᾖ': 'η', 'ᾗ': 'η',
            'ί': 'ι', 'ὶ': 'ι', 'ῖ': 'ι', 'ἰ': 'ι', 'ἱ': 'ι', 'ἴ': 'ι', 'ἵ': 'ι', 'ἲ': 'ι', 'ἳ': 'ι', 'ἶ': 'ι', 'ἷ': 'ι',
            'ΐ': 'ι', 'ῒ': 'ι', 'ῗ': 'ι',
            'ό': 'ο', 'ὸ': 'ο', 'ὀ': 'ο', 'ὁ': 'ο', 'ὄ': 'ο', 'ὅ': 'ο', 'ὂ': 'ο', 'ὃ': 'ο',
            'ύ': 'υ', 'ὺ': 'υ', 'ῦ': 'υ', 'ὐ': 'υ', 'ὑ': 'υ', 'ὔ': 'υ', 'ὕ': 'υ', 'ὒ': 'υ', 'ὓ': 'υ', 'ὖ': 'υ', 'ὗ': 'υ',
            'ΰ': 'υ', 'ῢ': 'υ', 'ῧ': 'υ',
            'ώ': 'ω', 'ὼ': 'ω', 'ῶ': 'ω', 'ὠ': 'ω', 'ὡ': 'ω', 'ὤ': 'ω', 'ὥ': 'ω', 'ὢ': 'ω', 'ὣ': 'ω', 'ὦ': 'ω', 'ὧ': 'ω',
            'ῳ': 'ω', 'ῷ': 'ω', 'ῴ': 'ω', 'ῲ': 'ω', 'ᾠ': 'ω', 'ᾡ': 'ω', 'ᾤ': 'ω', 'ᾥ': 'ω', 'ᾢ': 'ω', 'ᾣ': 'ω', 'ᾦ': 'ω', 'ᾧ': 'ω',
            # Rho with breathing
            'ῤ': 'ρ', 'ῥ': 'ρ'
        }

        return ''.join(diacritic_map.get(c, c) for c in with_regular_sigma)

    def resolve_lemma_chain(self, lemma: str, language: str, visited: Optional[Set[str]] = None, max_depth: int = 3) -> str:
        """Follow lemma chains to find canonical form with dictionary entry"""
        if visited is None:
            visited = set()

        # Prevent infinite loops
        if lemma in visited or len(visited) >= max_depth:
            return lemma
        visited.add(lemma)

        # Check if this lemma has a meaningful dictionary entry
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT entry_plain, entry_html FROM dictionary_entries
            WHERE headword = ? AND language = ?
        """, (lemma, language))
        entries = cursor.fetchall()

        has_meaningful_entry = any(
            (row['entry_plain'] and row['entry_plain'].strip() and row['entry_plain'] != "Morphological entry") or
            (row['entry_html'] and row['entry_html'].strip() and "Morphological entry" not in row['entry_html'])
            for row in entries
        )

        if has_meaningful_entry:
            return lemma  # Found a real definition

        # Check if this lemma maps to another lemma
        cursor.execute("""
            SELECT lemma, confidence FROM lemma_map
            WHERE word_form = ? AND lemma != ?
            ORDER BY confidence DESC LIMIT 1
        """, (lemma, lemma))
        next_mapping = cursor.fetchone()

        if next_mapping:
            return self.resolve_lemma_chain(next_mapping['lemma'], language, visited, max_depth)

        return lemma

    def find_morphologically_related_forms(self, word: str, language: str) -> List[str]:
        """
        Find morphologically related forms for a word.
        Matches PerseusRepository.kt findMorphologicallyRelatedForms()
        """
        related_forms = []
        cursor = self.conn.cursor()

        if language == "greek":
            # λαων (gen pl) -> try λαοι (nom pl), λαος (nom sg), etc.
            if word.endswith("ων") and len(word) >= 4:
                stem = word[:-2]  # Remove ων
                candidates = [
                    stem + "οι",   # nom pl
                    stem + "ος",   # nom sg
                    stem + "ου",   # gen sg
                    stem + "ον",   # acc sg
                    stem + "οις",  # dat pl
                    stem + "ους"   # acc pl
                ]
                for candidate in candidates:
                    cursor.execute("SELECT 1 FROM lemma_map WHERE word_form = ? LIMIT 1", (candidate,))
                    if cursor.fetchone():
                        related_forms.append(candidate)

            # Similar patterns for -οι and -ος endings
            elif word.endswith("οι") and len(word) >= 4:
                stem = word[:-2]
                candidates = [stem + "ος", stem + "ων", stem + "ου"]
                for candidate in candidates:
                    cursor.execute("SELECT 1 FROM lemma_map WHERE word_form = ? LIMIT 1", (candidate,))
                    if cursor.fetchone():
                        related_forms.append(candidate)

            elif word.endswith("ος") and len(word) >= 4:
                stem = word[:-2]
                candidates = [stem + "οι", stem + "ων", stem + "ου"]
                for candidate in candidates:
                    cursor.execute("SELECT 1 FROM lemma_map WHERE word_form = ? LIMIT 1", (candidate,))
                    if cursor.fetchone():
                        related_forms.append(candidate)

        return related_forms

    def get_prefix_assimilation_rules(self, language: str) -> List[Tuple[str, str, List[str]]]:
        """
        Load prefix assimilation rules from database and group by base prefix.
        Returns: List of (base_prefix, meaning, [assimilated_forms]) tuples sorted by prefix length (longest first)
        Matches PerseusRepository.kt getPrefixAssimilationRules()
        """
        if language in self.prefix_cache:
            return self.prefix_cache[language]

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT base_prefix, assimilated_form, meaning
            FROM prefix_assimilation_rules
            WHERE language = ?
            ORDER BY base_prefix, priority ASC
        """, (language,))

        rules_by_prefix = {}
        for row in cursor.fetchall():
            base_prefix = row['base_prefix']
            assimilated_form = row['assimilated_form']
            meaning = row['meaning'] or ""

            if base_prefix not in rules_by_prefix:
                rules_by_prefix[base_prefix] = (meaning, [])
            rules_by_prefix[base_prefix][1].append(assimilated_form)

        # Convert to list of tuples and sort by prefix length (longest first)
        # CRITICAL: Kotlin sorts by basePrefix.length descending (line 82 in PerseusRepository.kt)
        # This ensures longer prefixes like "αν" match before shorter ones like "α"
        result = [(prefix, meaning, forms) for prefix, (meaning, forms) in rules_by_prefix.items()]
        result.sort(key=lambda x: len(x[0]), reverse=True)
        self.prefix_cache[language] = result
        return result

    def find_stem_lemma(self, stem: str, language: str) -> Optional[str]:
        """
        Find lemma for a stem by doing a full dictionary lookup (without compound decomposition).
        Matches PerseusRepository.kt findStemLemma()

        CRITICAL: Ultra-normalized search MUST be enabled in nested calls!
        - skipCompoundDecomposition prevents infinite recursion (no compound decomposition)
        - But ultra-normalized search still runs to find inflected forms via lemma_map
        - This is how Kotlin finds "ψάλλει" → "ψάλλω" and "αγνοεῖ" → "ἀγνοέω"
        """
        # First try direct lookup WITH ultra-normalized search (matches actual Kotlin behavior)
        results = self.get_all_dictionary_entries(stem, language, skip_compound_decomposition=True, allow_ultra_normalized=True)
        if results:
            return results[0].lemma

        # If no results and Greek, try vowel restoration for contracted forms
        # Matches Kotlin's findStemWithVowelRestoration() - lines 1871-1896
        # Try plain vowels first, then rough breathing vowels (NOT smooth breathing)
        if language == "greek" and len(stem) >= 3:
            # Try common initial vowels (plain - no breathing marks)
            for test_vowel in ['ο', 'α', 'ε', 'ι', 'η', 'ω', 'υ']:
                test_word = test_vowel + stem
                results = self.get_all_dictionary_entries(test_word, language, skip_compound_decomposition=True, allow_ultra_normalized=True)
                if results:
                    return results[0].lemma

            # Try rough breathing variants (NOT smooth breathing - Kotlin only tries rough)
            for test_vowel in ['ὁ', 'ἁ', 'ἑ', 'ἱ', 'ὑ']:
                test_word = test_vowel + stem
                results = self.get_all_dictionary_entries(test_word, language, skip_compound_decomposition=True, allow_ultra_normalized=True)
                if results:
                    return results[0].lemma

        return None

    def decompose_compound_word(self, word: str, language: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Decompose a compound word into prefix + stem.
        Returns: (base_prefix, prefix_meaning, stem, stem_lemma) or None
        Matches PerseusRepository.kt decomposeCompoundWord()
        """
        prefix_groups = self.get_prefix_assimilation_rules(language)
        if not prefix_groups:
            return None

        # Normalize word to match prefixes
        normalized_word = self.normalize_greek_ultra(word) if language == "greek" else word.lower()

        # Try each prefix group
        for base_prefix, meaning, assimilated_forms in prefix_groups:
            # Try each assimilated form (longest first for greedy matching)
            for assimilated_form in sorted(assimilated_forms, key=len, reverse=True):
                # Normalize the prefix form for comparison
                norm_prefix = self.normalize_greek_ultra(assimilated_form) if language == "greek" else assimilated_form.lower()

                if normalized_word.startswith(norm_prefix):
                    # Extract stem
                    stem_start_pos = len(assimilated_form)
                    stem = word[stem_start_pos:]

                    if len(stem) >= 3:  # Stem must be at least 3 characters
                        # Find lemma for stem
                        stem_lemma = self.find_stem_lemma(stem, language)
                        if stem_lemma:
                            return (base_prefix, meaning, stem, stem_lemma)

        return None

    def create_compound_entry(self, base_prefix: str, prefix_meaning: str, stem: str, stem_lemma: str, language: str) -> List[DictionaryEntry]:
        """
        Create dictionary entries for a compound word.
        Matches PerseusRepository.kt createCompoundEntry()
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT headword, entry_html, entry_plain, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
        """, (stem_lemma, language))

        stem_entries = cursor.fetchall()

        if not stem_entries:
            # No dictionary entry for stem
            return [DictionaryEntry(
                lemma=base_prefix + stem_lemma,
                definition=f"<p><i>Compound word analysis:</i></p><p><b>{base_prefix}-</b> ({prefix_meaning}) + <b>{stem_lemma}</b></p><p>(No dictionary entry found for stem)</p>",
                morph_info=f"compound: {base_prefix}- + {stem_lemma}",
                is_direct_match=False,
                confidence=0.7,
                source="compound analysis",
                has_non_treebank_path=True
            )]

        # Create entry for each stem dictionary entry
        entries = []
        for stem_entry in stem_entries:
            stem_def = stem_entry['entry_html'] or stem_entry['entry_plain'] or ""
            compound_def = f"<p><i>Compound word analysis:</i></p><p><b>{base_prefix}-</b> ({prefix_meaning}) + <b>{stem_lemma}</b></p><hr/>{stem_def}"

            entries.append(DictionaryEntry(
                lemma=base_prefix + stem_lemma,
                definition=compound_def,
                morph_info=f"compound: {base_prefix}- + {stem_lemma}",
                is_direct_match=False,
                confidence=0.7,
                source=f"{stem_entry['source']} (compound analysis)",
                has_non_treebank_path=True
            ))

        return entries

    def get_all_dictionary_entries(self, word: str, language: str = "greek", skip_compound_decomposition: bool = False, allow_ultra_normalized: bool = False) -> List[DictionaryEntry]:
        """
        Main dictionary lookup method - replicates getAllDictionaryEntries() from Kotlin.
        Returns 0-5 sorted dictionary entries following Android UI logic.
        """
        # Hard-coded priority lemmas for 20 most common 1-2 letter words in Iliad Book 1
        # This ensures these high-frequency particles/conjunctions always show the correct primary lemma first
        # Format: word_form -> (lemma, gloss, occurrence_count)
        COMMON_WORD_PRIORITY = {
            'δʼ': ('δέ', 'and, but', 152),           # elided form
            'δὲ': ('δέ', 'and, but', 58),
            'τε': ('τε', 'and, both', 54),
            'δέ': ('δέ', 'and, but', 29),
            'ἐν': ('ἐν', 'in, on, at', 26),
            'ὣς': ('ὡς', 'thus, so', 22),
            'τʼ': ('τε', 'and', 21),                 # elided form
            'οὔ': ('οὐ', 'not', 20),
            'ἦ': ('ἦ', 'truly, indeed', 19),
            'ἢ': ('ἤ', 'or, than', 19),
            'σὺ': ('σύ', 'you', 19),
            'ὅ': ('ὅς', 'who, which', 18),
            'ὃ': ('ὅς', 'who, which', 18),
            'τι': ('τις', 'something, anything', 17),
            'δὴ': ('δή', 'indeed, certainly', 17),
            'γε': ('γε', 'at least, indeed', 17),
            'οὐ': ('οὐ', 'not', 16),
            'εἰ': ('εἰ', 'if', 16),
            'γʼ': ('γε', 'at least', 14),            # elided form
            'ἐς': ('εἰς', 'into, to', 13),
        }

        # Clean punctuation first, but preserve apostrophes for elided forms
        cleaned_word = re.sub(r'[.,;:!?·]', '', word)

        # Normalize apostrophes for Greek words
        if language.lower() == "greek":
            cleaned_word = self.normalize_apostrophes(cleaned_word)

        # For Greek words, create lunate sigma variant if word has lunate sigma
        # Many ancient Greek texts use lunate sigma (ϲ) but dictionaries use regular sigma (σ/ς)
        lunate_sigma_variant = None
        if language.lower() == "greek" and self.has_lunate_sigma(cleaned_word):
            lunate_sigma_variant = self.normalize_lunate_sigma(cleaned_word)

        # For Greek words, also create acute accent variant if word has grave accents
        acute_variant = None
        if language.lower() == "greek" and self.has_grave_accent(cleaned_word):
            acute_variant = self.convert_grave_to_acute(cleaned_word)

        # Normalize language parameter
        normalized_language = language.lower().strip()

        entries = []
        added_lemmas = set()
        user_added_lemmas = set()  # Track lemmas with user morphology entries (matches Kotlin's userAddedLemmas)
        insertion_counter = [0]  # Track insertion order for stable sorting (matches Kotlin's behavior) - use list for mutability

        # Morph abbreviations used by Cunliffe cross-reference entries
        _morph_abbrevs = {'sing', 'pl', 'dual', 'aor', 'pres', 'impf', 'fut', 'pf', 'plupf',
                          'act', 'mid', 'pass', 'subj', 'opt', 'imp', 'imper', 'impve', 'pple',
                          'contr', 'neut', 'masc', 'fem', 'nom', 'acc', 'gen', 'dat', 'voc',
                          'inf', 'ind', 'iterative', 'infin', 'comp', 'super', 'pa', 'app',
                          'prec', 'cf', 'prob'}

        def add_entry(entry: DictionaryEntry):
            """Helper to add entry with insertion order tracking.
            Filters out entries that are morphological cross-references rather than
            definitions — these produce garbled glosses instead of actual meanings."""
            if entry.definition:
                plain = re.sub(r'<[^>]+>', '', entry.definition).strip()
                plain_lower = plain.lower()
                # Skip wiktionary "inflection of" entries (e.g., "epi inflection of δῐῐ̈́στημῐ (3:d aor act ind)")
                if entry.source == 'wiktionary' and ('inflection of' in plain_lower or '{{infl of' in plain_lower):
                    return
                # Skip cunliffe cross-reference entries (e.g., "διαστήτην, 3 dual aor. διίστημι.")
                # These contain only Greek text + morph abbreviations but no English definition words.
                if entry.source == 'cunliffe' and len(plain) < 80:
                    english_words = re.findall(r'[a-zA-Z]{3,}', plain_lower)
                    if not any(w not in _morph_abbrevs for w in english_words):
                        return
            entry.insertion_order = insertion_counter[0]
            insertion_counter[0] += 1
            entries.append(entry)

        # STEP 1: Check dictionary for direct match
        cursor = self.conn.cursor()

        # DEBUG: Log the SQL query matching Kotlin's DictionaryDao.getAllEntriesForHeadword
        if self.debug:
            print(f"DEBUG: Direct dictionary lookup for '{cleaned_word}' (language={normalized_language})")

        cursor.execute("""
            SELECT headword, entry_html, entry_plain, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
        """, (cleaned_word, normalized_language))

        direct_entries = cursor.fetchall()

        # DEBUG: Log direct match results
        if self.debug and direct_entries:
            print(f"DEBUG: Found {len(direct_entries)} direct dictionary entries")
            for entry in direct_entries:
                print(f"  - {entry['headword']} ({entry['source']})")
        for entry in direct_entries:
            definition = entry['entry_html'] or entry['entry_plain'] or ""
            add_entry(DictionaryEntry(
                lemma=entry['headword'],
                definition=definition,
                is_direct_match=True,
                source=entry['source'],
                confidence=1.0,  # High confidence for direct dictionary match
                has_non_treebank_path=True
            ))
            added_lemmas.add(entry['headword'])

        # STEP 1b: If no direct match, try acute variant (matches Kotlin lines 572-591)
        if not direct_entries and acute_variant and acute_variant != cleaned_word:
            cursor.execute("""
                SELECT headword, entry_html, entry_plain, source
                FROM dictionary_entries
                WHERE headword = ? AND language = ?
            """, (acute_variant, normalized_language))

            acute_entries = cursor.fetchall()
            for entry in acute_entries:
                definition = entry['entry_html'] or entry['entry_plain'] or ""
                add_entry(DictionaryEntry(
                    lemma=entry['headword'],
                    definition=definition,
                    is_direct_match=True,
                    source=entry['source'],
                    confidence=1.0,
                    has_non_treebank_path=True
                ))
                added_lemmas.add(entry['headword'])

        # STEP 1c: If no direct match and word has lunate sigma, try with regular sigma
        # Some ancient Greek texts use lunate sigma (ϲ) but dictionaries use regular sigma (σ/ς)
        if not entries and lunate_sigma_variant and lunate_sigma_variant != cleaned_word:
            cursor.execute("""
                SELECT headword, entry_html, entry_plain, source
                FROM dictionary_entries
                WHERE headword = ? AND language = ?
            """, (lunate_sigma_variant, normalized_language))

            lunate_entries = cursor.fetchall()
            for entry in lunate_entries:
                definition = entry['entry_html'] or entry['entry_plain'] or ""
                add_entry(DictionaryEntry(
                    lemma=entry['headword'],
                    definition=definition,
                    is_direct_match=True,
                    source=entry['source'],
                    confidence=0.95,  # Slightly lower confidence for sigma variant
                    has_non_treebank_path=True
                ))
                added_lemmas.add(entry['headword'])

            # Also update cleaned_word for subsequent lookups if lunate variant worked
            if lunate_entries:
                cleaned_word = lunate_sigma_variant

        # STEP 2: For Greek/Latin, ALWAYS check lemma_map (even if we found direct matches)
        # This matches Kotlin behavior at line 544
        if normalized_language in ("greek", "latin"):
            # DEBUG: Log lemma_map lookup matching Kotlin's LemmaMapDao.getAllLemmaMappingsForWord
            if self.debug:
                print(f"DEBUG: Lemma map lookup for '{cleaned_word}'")

            cursor.execute("""
                SELECT word_form, lemma, morph_info, confidence, source
                FROM lemma_map
                WHERE word_form = ?
                ORDER BY confidence DESC
            """, (cleaned_word,))

            lemma_mappings = cursor.fetchall()

            # DEBUG: Log lemma mappings found
            if self.debug and lemma_mappings:
                print(f"DEBUG: Found {len(lemma_mappings)} lemma mappings:")
                for mapping in lemma_mappings:
                    print(f"  - {mapping['word_form']} → {mapping['lemma']} (conf={mapping['confidence']}, source={mapping['source']})")

            # Also try acute variant if available
            if not lemma_mappings and acute_variant and acute_variant != cleaned_word:
                cursor.execute("""
                    SELECT word_form, lemma, morph_info, confidence, source
                    FROM lemma_map
                    WHERE word_form = ?
                """, (acute_variant,))
                lemma_mappings = cursor.fetchall()

            # For Greek: If no exact match and word ends with apostrophe, try prefix search
            if normalized_language == "greek" and not lemma_mappings:
                if any(cleaned_word.endswith(ap) for ap in ["'", "'", "ʼ"]):
                    prefix = cleaned_word.rstrip("'ʼ'")

                    # CRITICAL: Match Kotlin's exact filtering logic
                    # 1. Get ALL prefix matches (ordered by LENGTH ASC, confidence DESC)
                    # 2. Filter by maxLength
                    # 3. Take first 10
                    # This matches PerseusRepository.kt lines 698-706

                    # IMPORTANT: SQLite's LIKE with Greek characters needs explicit case handling.
                    # Kotlin's query matches both lowercase (δ) and uppercase (Δ) variants.
                    # For prefix 'δαιμόνι', it also matches 'Δαιμόνι᾽' and other uppercase variants.
                    # This is critical because uppercase variants can have higher confidence and
                    # push out lower-confidence entries from the top 10.

                    prefix_upper = prefix[0].upper() + prefix[1:] if len(prefix) > 0 else prefix

                    cursor.execute("""
                        SELECT word_form, lemma, morph_info, confidence, source
                        FROM lemma_map
                        WHERE (word_form LIKE ? OR word_form LIKE ?)
                        ORDER BY LENGTH(word_form) ASC, confidence DESC
                    """, (prefix + '%', prefix_upper + '%'))
                    all_prefix_mappings = list(cursor.fetchall())

                    # For single-letter prefix, also try uppercase variant
                    # This handles cases like κʼ → Κ (uppercase single letter)
                    if len(prefix) == 1:
                        cursor.execute("""
                            SELECT word_form, lemma, morph_info, confidence, source
                            FROM lemma_map
                            WHERE word_form = ? OR lemma = ?
                        """, (prefix.upper(), prefix.upper()))
                        uppercase_mappings = cursor.fetchall()
                        all_prefix_mappings.extend(uppercase_mappings)

                    # Filter by length FIRST (like Kotlin does)
                    max_length = len(prefix) + (2 if len(prefix) == 1 else 4)
                    filtered_mappings = [m for m in all_prefix_mappings if len(m['word_form']) <= max_length]

                    # THEN take first 10 (like Kotlin's .take(10))
                    lemma_mappings = filtered_mappings[:10]

            # Track which lemmas have non-treebank sources
            lemmas_with_non_treebank = set()
            for mapping in lemma_mappings:
                if mapping['source'] != 'perseus_treebank':
                    # Normalize to NFC form
                    normalized_lemma = unicodedata.normalize('NFC', mapping['lemma'])
                    lemmas_with_non_treebank.add(normalized_lemma)

            # Group by lemma and keep best mapping by highest confidence
            # Matches PerseusRepository.kt line 710-713: maxByOrNull { it.confidence }
            lemma_groups = {}
            for mapping in lemma_mappings:
                lemma = mapping['lemma']
                if lemma not in lemma_groups:
                    lemma_groups[lemma] = mapping
                else:
                    current = lemma_groups[lemma]
                    # Simply prefer higher confidence (matches Kotlin logic)
                    if (mapping['confidence'] or 0.0) > (current['confidence'] or 0.0):
                        lemma_groups[lemma] = mapping

            # Get dictionary entries for each unique lemma (sorted by confidence)
            sorted_lemmas = sorted(lemma_groups.values(), key=lambda x: x['confidence'] or 0.0, reverse=True)

            for lemma_mapping in sorted_lemmas:
                # Normalize lemma to NFC form
                lemma = unicodedata.normalize('NFC', lemma_mapping['lemma'])

                # Skip if already added
                if lemma in added_lemmas:
                    continue

                # Follow lemma chain to find canonical form
                resolved_lemma = self.resolve_lemma_chain(lemma, normalized_language)

                # CRITICAL: Track user morphology entries separately
                # This matches Kotlin's userAddedLemmas set at line 796
                # Only create morphology-only entry if resolved lemma not already in user_added_lemmas
                if resolved_lemma not in user_added_lemmas:
                    if lemma_mapping['morph_info']:
                        morph_info = lemma_mapping['morph_info']
                        if '|' in morph_info:
                            # Handle pipe-delimited morphology
                            morph_forms = [f.strip() for f in morph_info.split('|')]
                            definition = f"Forms: {', '.join(morph_forms)}"
                        else:
                            definition = f"Form: {morph_info}"

                        add_entry(DictionaryEntry(
                            lemma=resolved_lemma,
                            definition=definition,
                            morph_info=morph_info,
                            is_direct_match=False,
                            confidence=lemma_mapping['confidence'],
                            source="User morphology",
                            has_non_treebank_path=True
                        ))
                        user_added_lemmas.add(resolved_lemma)

                # Then get all dictionary entries for this resolved lemma
                # CRITICAL: Must ORDER BY id (primary key = rowid) to match Kotlin's getAllEntriesForHeadword behavior
                # which returns entries in database insertion order (rowid/id order)
                cursor.execute("""
                    SELECT headword, entry_html, entry_plain, source, id
                    FROM dictionary_entries
                    WHERE headword = ? AND language = ?
                    ORDER BY id
                """, (resolved_lemma, normalized_language))

                lemma_entries = cursor.fetchall()

                # Check if this lemma has non-treebank source in lemma_map
                has_non_treebank = lemma in lemmas_with_non_treebank

                # CRITICAL: If lemma has dictionary entries, it's ALWAYS non-treebank
                # Because dictionary_entries table contains actual definitions, not just treebank morphology
                # This matches Kotlin behavior at line 808
                if lemma_entries:
                    has_non_treebank = True

                for entry in lemma_entries:
                    definition = entry['entry_html'] or entry['entry_plain'] or ""
                    source = entry['source']
                    # Only mark as "via Treebank" if truly treebank-only (no dictionary entries)
                    # But we just set has_non_treebank=True above if entries exist, so this won't happen
                    if not has_non_treebank:
                        source = f"{source} (via Treebank)"

                    add_entry(DictionaryEntry(
                        lemma=resolved_lemma,
                        definition=definition,
                        morph_info=lemma_mapping['morph_info'],
                        is_direct_match=False,
                        confidence=lemma_mapping['confidence'],
                        source=source,
                        has_non_treebank_path=has_non_treebank
                    ))

                # CRITICAL: Add ORIGINAL lemma to added_lemmas, not resolved
                # This matches Kotlin at line 826 where it adds 'lemma' not 'resolvedLemma'
                # This prevents processing the same lemma mapping twice
                if lemma_entries:
                    added_lemmas.add(lemma)

        # STEP 2.5: For Greek/Latin, check morphologically related forms
        # Matches PerseusRepository.kt line 841-874
        if normalized_language in ("greek", "latin"):
            related_forms = self.find_morphologically_related_forms(cleaned_word, normalized_language)
            for related_form in related_forms:
                # CRITICAL: Must ORDER BY confidence DESC to match Kotlin's getAllLemmaMappingsForWord
                cursor.execute("""
                    SELECT word_form, lemma, morph_info, confidence, source
                    FROM lemma_map
                    WHERE word_form = ?
                    ORDER BY confidence DESC
                """, (related_form,))

                related_mappings = cursor.fetchall()
                for mapping in related_mappings:
                    lemma = unicodedata.normalize('NFC', mapping['lemma'])

                    # Skip if already processed or self-referential
                    if lemma in added_lemmas or lemma == related_form:
                        continue

                    # Get dictionary entries for this lemma
                    # CRITICAL: Must ORDER BY id (primary key = rowid) to match Kotlin's getAllEntriesForHeadword behavior
                    # which returns entries in database insertion order (rowid/id order)
                    cursor.execute("""
                        SELECT headword, entry_html, entry_plain, source, id
                        FROM dictionary_entries
                        WHERE headword = ? AND language = ?
                        ORDER BY id
                    """, (lemma, normalized_language))

                    related_entries = cursor.fetchall()
                    has_non_treebank = mapping['source'] != 'perseus_treebank'

                    # DEBUG: Log the entries we got from ORDER BY id
                    if self.debug and related_entries:
                        print(f"DEBUG: Related lemma '{lemma}' has {len(related_entries)} dictionary entries (ORDER BY id):")
                        for idx, entry in enumerate(related_entries):
                            print(f"  [{idx}] {entry['source']} (id={entry['id']})")

                    for entry in related_entries:
                        definition = entry['entry_html'] or entry['entry_plain'] or ""
                        # CRITICAL: Add " (via Treebank)" suffix if mapping source is treebank-only
                        # This matches Kotlin line 890: source = if (!hasNonTreebank) "${relatedEntry.source} (via Treebank)" else relatedEntry.source
                        source = entry['source'] if has_non_treebank else f"{entry['source']} (via Treebank)"
                        # DEBUG: Log when add_entry is called
                        if self.debug:
                            print(f"DEBUG: Calling add_entry for {lemma}({source}) - insertion_counter={insertion_counter[0]}, has_non_treebank={has_non_treebank}")
                        add_entry(DictionaryEntry(
                            lemma=lemma,
                            definition=definition,
                            morph_info=f"inferred from related form: {related_form} ({mapping['morph_info'] or ''})",
                            is_direct_match=False,
                            confidence=(mapping['confidence'] or 0.0) * 0.8,  # Lower confidence for inferred
                            source=source,
                            has_non_treebank_path=has_non_treebank
                        ))

                    if related_entries:
                        added_lemmas.add(lemma)

        # STEP 2.6: Compound word decomposition - DISABLED for interlinear generation
        # Compound analysis produces "Compound word analysis" glosses instead of real definitions.
        # Ultra-normalized search (STEP 2.7) handles these cases better by matching dictionary
        # headwords with diacritic differences (e.g., προιάπτω → προϊάπτω).
        if False and not skip_compound_decomposition and not entries and normalized_language in ("greek", "latin") and len(cleaned_word) >= 6:
            compound_parts = self.decompose_compound_word(cleaned_word, normalized_language)
            if compound_parts:
                base_prefix, prefix_meaning, stem, stem_lemma = compound_parts
                compound_entries = self.create_compound_entry(base_prefix, prefix_meaning, stem, stem_lemma, normalized_language)
                for entry in compound_entries:
                    add_entry(entry)
                added_lemmas.add(base_prefix + stem_lemma)

        # STEP 2.7: Ultra-normalized search (fallback when no entries found)
        # Matches PerseusRepository.kt lines 1009-1098
        # This runs unconditionally as a last resort when no other method found entries
        # Applies 0.6x confidence penalty to ultra-normalized matches
        if not entries and normalized_language == "greek":
            if self.debug:
                print(f"DEBUG: No entries found, trying ultra-normalized search for '{cleaned_word}'")

            ultra_normalized = self.normalize_greek_ultra(cleaned_word)

            # Try direct dictionary lookup with ultra-normalized form
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT headword, entry_html, entry_plain, source
                FROM dictionary_entries
                WHERE headword_normalized_ultra = ? AND language = ?
            """, (ultra_normalized, normalized_language))

            ultra_direct = cursor.fetchone()
            if ultra_direct:
                if self.debug:
                    print(f"DEBUG: Found entry via ultra-normalization: {ultra_direct['headword']}")
                add_entry(DictionaryEntry(
                    lemma=ultra_direct['headword'],
                    definition=ultra_direct['entry_html'] or ultra_direct['entry_plain'] or "",
                    morph_info="found via simplified form",
                    is_direct_match=True,
                    confidence=0.7,
                    source=ultra_direct['source'],
                    has_non_treebank_path=True
                ))

            # Also try lemma mappings with ultra-normalized form
            cursor.execute("""
                SELECT lemma, morph_info, confidence, source
                FROM lemma_map
                WHERE word_form_normalized_ultra = ?
                ORDER BY confidence DESC
                LIMIT 5
            """, (ultra_normalized,))

            ultra_mappings = cursor.fetchall()
            if self.debug and ultra_mappings:
                print(f"DEBUG: Found {len(ultra_mappings)} ultra-normalized lemma mappings")

            for mapping in ultra_mappings:
                lemma = mapping['lemma']

                # Skip if we already added this lemma
                if lemma in added_lemmas:
                    continue

                # Get dictionary entries for this lemma
                cursor.execute("""
                    SELECT headword, entry_html, entry_plain, source, id
                    FROM dictionary_entries
                    WHERE headword = ? AND language = ?
                    ORDER BY id
                """, (lemma, normalized_language))

                ultra_entries = cursor.fetchall()
                for ultra_entry in ultra_entries:
                    if self.debug:
                        print(f"DEBUG: Adding ultra-normalized lemma: {lemma} (source: {ultra_entry['source']})")

                    has_non_treebank = mapping['source'] != 'perseus_treebank'
                    source = ultra_entry['source'] if has_non_treebank else f"{ultra_entry['source']} (via Treebank)"

                    # Clean up morph_info to avoid trailing ": " when mapping has no morph_info
                    morph_suffix = mapping['morph_info'] or ''
                    morph_text = f"found via simplified form: {morph_suffix}" if morph_suffix else "found via simplified form"

                    add_entry(DictionaryEntry(
                        lemma=lemma,
                        definition=ultra_entry['entry_html'] or ultra_entry['entry_plain'] or "",
                        morph_info=morph_text,
                        is_direct_match=False,
                        confidence=(mapping['confidence'] or 0.0) * 0.6,
                        source=source,
                        has_non_treebank_path=has_non_treebank
                    ))

                if ultra_entries:
                    added_lemmas.add(lemma)

        # STEP 3: Deduplicate entries
        seen_keys = set()
        deduplicated = []
        for entry in entries:
            # Create unique key from lemma + source + definition prefix
            definition_key = (entry.definition or "")[:100]
            key = f"{entry.lemma}_{entry.source}_{definition_key}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduplicated.append(entry)

        # STEP 4: Sort entries - matches Kotlin sorting logic exactly
        # DISABLED: Get priority lemma for common words if applicable
        # priority_info = COMMON_WORD_PRIORITY.get(cleaned_word)
        # priority_lemma = priority_info[0] if priority_info else None
        priority_lemma = None

        def sort_key(entry):
            # DISABLED: PRIORITY 0: For common 1-2 letter words, priority lemma comes first
            # if priority_lemma and entry.lemma == priority_lemma:
            #     priority_0 = -1000
            # else:
            #     priority_0 = 0
            priority_0 = 0

            # FIRST: Non-treebank entries come before treebank-only
            priority_1 = 0 if entry.has_non_treebank_path else 1000

            # SECOND: Minimal entry penalty
            # Deprioritize entries without actual definition content
            # This ensures entries with real definitions appear before cross-reference stubs
            # Also specifically deprioritize etymology-only entries
            import re
            plain_def = re.sub(r'<[^>]+>', '', entry.definition) if entry.definition else ""
            plain_def = plain_def.strip()

            # Check if entry is ONLY etymology (no definition after etymology section)
            is_etymology_only = False
            if plain_def.startswith('Etymology:') or plain_def.startswith('†'):
                # Remove etymology prefix and check remaining content
                content_after_etymology = re.sub(r'^Etymology:.*?(?=\n[A-Z]\.|\n[IVX]+\.|\n\d+\.|\Z)', '', plain_def, flags=re.DOTALL)
                content_after_etymology = re.sub(r'^†[^\n]*?\n', '', content_after_etymology)
                content_after_etymology = content_after_etymology.strip()
                # If nothing meaningful left, it's etymology-only
                has_definition = bool(re.search(r'[A-Z]\.|[IVX]+\.|^\d+\.', content_after_etymology, re.MULTILINE))
                is_etymology_only = not has_definition and len(content_after_etymology) < 50

            # Also check for minimal cross-reference entries
            content_after_etymology = re.sub(r'^Etymology:.*?\n', '', plain_def, flags=re.DOTALL)
            content_after_etymology = content_after_etymology.strip()
            has_actual_content = bool(re.search(r'[a-zA-Z]{3,}', content_after_etymology))
            is_minimal = not has_actual_content

            # Heavy penalty for etymology-only, lighter for other minimal entries
            priority_2 = 2000 if is_etymology_only else (1000 if is_minimal else 0)

            # THIRD: Source ranking
            source_lower = (entry.source or "").lower()
            if "user:" in source_lower:
                priority_3 = -1
            elif source_lower == "lsj":
                priority_3 = 0
            elif source_lower == "cunliffe":
                priority_3 = 1
            elif source_lower == "wiktionary":
                priority_3 = 2
            else:
                priority_3 = 3

            # FOURTH: Confidence (higher confidence first - use negative so higher values sort first)
            # This ensures that within the same source, higher confidence lemmas appear first
            # e.g., for οὗ from LSJ: οὗ (conf=1.0) appears before ὅς (conf=0.9)
            priority_4 = -(entry.confidence if entry.confidence else 0.0)

            # FIFTH: Lemma length (shorter first)
            priority_5 = len(entry.lemma)

            # SIXTH: Alphabetical
            priority_6 = entry.lemma

            # SEVENTH: Insertion order (CRITICAL for stable sort matching Kotlin's behavior)
            # When all other priorities are equal, preserve the order entries were added
            # This ensures that database rowid order is preserved when confidence/source/etc are identical
            priority_7 = entry.insertion_order

            return (priority_0, priority_1, priority_2, priority_3, priority_4, priority_5, priority_6, priority_7)

        sorted_entries = sorted(deduplicated, key=sort_key)

        # DEBUG: Log final sorted results matching Kotlin's "After sorting" format
        if self.debug and sorted_entries:
            entries_str = ", ".join([f"{e.lemma}({e.source},conf={e.confidence})" for e in sorted_entries])
            print(f"DEBUG: After sorting: {entries_str}")

        return sorted_entries


def format_morph_info(morph_info: str) -> str:
    """
    Format morphological tags for display - matches formatMorphInfo() from DictionaryActivity.kt
    Converts abbreviated codes to readable format
    """
    if not morph_info:
        return ""

    # Mapping from Kotlin formatMorphInfo() function
    morph_map = {
        # Tense
        "pres": "present",
        "impf": "imperfect",
        "aor": "aorist",
        "fut": "future",
        "perf": "perfect",
        "plup": "pluperfect",

        # Voice
        "act": "active",
        "mid": "middle",
        "pass": "passive",
        "mp": "middle/passive",

        # Mood
        "ind": "indicative",
        "subj": "subjunctive",
        "opt": "optative",
        "impv": "imperative",
        "impr": "imperative",
        "inf": "infinitive",
        "part": "participle",

        # Person/Number
        "1": "1st person",
        "2": "2nd person",
        "3": "3rd person",
        "s": "singular",
        "sg": "singular",
        "p": "plural",
        "pl": "plural",
        "d": "dual",
        "du": "dual",

        # Case
        "nom": "nominative",
        "gen": "genitive",
        "dat": "dative",
        "acc": "accusative",
        "voc": "vocative",

        # Gender
        "m": "masculine",
        "masc": "masculine",
        "f": "feminine",
        "fem": "feminine",
        "n": "neuter",
        "neut": "neuter",

        # Other
        "with_nu": "(with nu-movable)"
    }

    # Split on underscores, spaces, and semicolons
    parts = re.split(r'[_\s;]', morph_info)

    # Map each part and filter out blanks
    formatted_parts = []
    for part in parts:
        part = part.strip()
        if part:
            mapped = morph_map.get(part, part)
            formatted_parts.append(mapped)

    return ' '.join(formatted_parts)


def format_definition(definition: str, max_length: int = 200) -> str:
    """Format definition for display - strip HTML and truncate"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', definition)
    # Collapse whitespace
    text = ' '.join(text.split())
    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + '...'
    return text


def display_results(word: str, entries: List[DictionaryEntry]):
    """Display results in UI-like format"""
    print(f"\n{'='*80}")
    print(f"WORD: {word}")

    # Get morphological tags from first entry with morph_info (like Android UI does)
    # The UI displays this prominently at the top in blue
    morph_tags = None
    for entry in entries:
        if entry.morph_info:
            morph_tags = format_morph_info(entry.morph_info)
            if morph_tags:
                break

    if morph_tags:
        print(f"MORPH: {morph_tags}")

    print(f"{'='*80}")

    if not entries:
        print("No definition found")
        return

    # Display up to 5 entries (like Android UI)
    for i, entry in enumerate(entries[:5], 1):
        print(f"\n[{i}] {entry.lemma}")
        if entry.source:
            print(f"    Source: {entry.source}")
        if entry.morph_info:
            raw_morph = entry.morph_info
            formatted_morph = format_morph_info(raw_morph)
            print(f"    Morphology: {formatted_morph} [{raw_morph}]")
        if entry.confidence is not None:
            print(f"    Confidence: {entry.confidence:.2f}")
        print(f"    {format_definition(entry.definition)}")


def test_iliad_lines(num_lines=7):
    """Test dictionary lookup on first N lines of the Iliad"""
    db_path = "data-prep/perseus_texts_sample.db"

    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        return

    repo = PerseusRepository(db_path)

    # Get first N lines
    cursor = repo.conn.cursor()
    cursor.execute("""
        SELECT line_number, line_text
        FROM text_lines
        WHERE book_id = 'tlg0012.tlg001.001'
        ORDER BY line_number
        LIMIT ?
    """, (num_lines,))
    lines = cursor.fetchall()

    print("="*80)
    print(f"TESTING DICTIONARY LOOKUP ON FIRST {num_lines} LINES OF HOMER'S ILIAD")
    print("="*80)

    for line_num, line_text in lines:
        print(f"\nLine {line_num}: {line_text}")

        # Split line into words (simple whitespace split)
        words = line_text.split()

        # Test all words on each line
        for word in words:
            entries = repo.get_all_dictionary_entries(word, "greek")
            display_results(word, entries)

    repo.conn.close()


if __name__ == "__main__":
    import sys
    num_lines = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    test_iliad_lines(num_lines)
