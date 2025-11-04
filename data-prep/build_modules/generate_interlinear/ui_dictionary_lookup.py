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


class PerseusRepository:
    """Python replica of PerseusRepository.kt dictionary lookup logic"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def normalize_apostrophes(self, word: str) -> str:
        """Normalize all apostrophe variants to U+02BC (ʼ)"""
        # First normalize to NFC (precomposed) form
        nfc_normalized = unicodedata.normalize('NFC', word)

        # Normalize all apostrophe variants
        return (nfc_normalized
                .replace("'", "ʼ")   # U+0027 APOSTROPHE → U+02BC
                .replace("'", "ʼ")   # U+2019 RIGHT SINGLE QUOTATION MARK → U+02BC
                .replace("᾿", "ʼ")   # U+1FBF GREEK PSILI → U+02BC
                .replace("′", "ʼ")   # U+2032 PRIME → U+02BC
                .replace("´", "ʼ"))  # U+00B4 ACUTE ACCENT → U+02BC

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

    def get_all_dictionary_entries(self, word: str, language: str = "greek") -> List[DictionaryEntry]:
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

        # For Greek words, also create acute accent variant if word has grave accents
        acute_variant = None
        if language.lower() == "greek" and self.has_grave_accent(cleaned_word):
            acute_variant = self.convert_grave_to_acute(cleaned_word)

        # Normalize language parameter
        normalized_language = language.lower().strip()

        entries = []
        added_lemmas = set()

        # STEP 1: Check dictionary for direct match
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT headword, entry_html, entry_plain, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
        """, (cleaned_word, normalized_language))

        direct_entries = cursor.fetchall()
        for entry in direct_entries:
            definition = entry['entry_html'] or entry['entry_plain'] or ""
            entries.append(DictionaryEntry(
                lemma=entry['headword'],
                definition=definition,
                is_direct_match=True,
                source=entry['source'],
                confidence=1.0,  # High confidence for direct dictionary match
                has_non_treebank_path=True
            ))
            added_lemmas.add(entry['headword'])

        # STEP 2: For Greek/Latin, ALWAYS check lemma_map (even if we found direct matches)
        # This matches Kotlin behavior at line 544
        if normalized_language in ("greek", "latin"):
            cursor.execute("""
                SELECT word_form, lemma, morph_info, confidence, source
                FROM lemma_map
                WHERE word_form = ?
            """, (cleaned_word,))

            lemma_mappings = cursor.fetchall()

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
                    cursor.execute("""
                        SELECT word_form, lemma, morph_info, confidence, source
                        FROM lemma_map
                        WHERE word_form LIKE ?
                        ORDER BY LENGTH(word_form) ASC
                        LIMIT 10
                    """, (prefix + '%',))

                    lemma_mappings = cursor.fetchall()
                    # Filter by length
                    max_length = len(prefix) + (2 if len(prefix) == 1 else 4)
                    lemma_mappings = [m for m in lemma_mappings if len(m['word_form']) <= max_length]

            # Track which lemmas have non-treebank sources
            lemmas_with_non_treebank = set()
            for mapping in lemma_mappings:
                if mapping['source'] != 'perseus_treebank':
                    # Normalize to NFC form
                    normalized_lemma = unicodedata.normalize('NFC', mapping['lemma'])
                    lemmas_with_non_treebank.add(normalized_lemma)

            # Group by lemma and keep best mapping (prefer one with morph_info, then highest confidence)
            # Matches DictionaryActivity.kt line 214: prefer the one with morph_info
            lemma_groups = {}
            for mapping in lemma_mappings:
                lemma = mapping['lemma']
                if lemma not in lemma_groups:
                    lemma_groups[lemma] = mapping
                else:
                    current = lemma_groups[lemma]
                    # Prefer mapping with morph_info (non-empty string)
                    current_morph = current['morph_info'] and current['morph_info'].strip()
                    mapping_morph = mapping['morph_info'] and mapping['morph_info'].strip()

                    if mapping_morph and not current_morph:
                        # New mapping has morph_info, current doesn't - use new
                        lemma_groups[lemma] = mapping
                    elif not mapping_morph and current_morph:
                        # Current has morph_info, new doesn't - keep current
                        pass
                    # If both have or both don't have morph_info, prefer higher confidence
                    elif (mapping['confidence'] or 0.0) > (current['confidence'] or 0.0):
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

                # Get all dictionary entries for this resolved lemma
                cursor.execute("""
                    SELECT headword, entry_html, entry_plain, source
                    FROM dictionary_entries
                    WHERE headword = ? AND language = ?
                """, (resolved_lemma, normalized_language))

                lemma_entries = cursor.fetchall()

                # Check if this lemma has non-treebank source in lemma_map
                has_non_treebank = lemma in lemmas_with_non_treebank

                # CRITICAL: If lemma has dictionary entries, it's ALWAYS non-treebank
                # Because dictionary_entries table contains actual definitions, not just treebank morphology
                # This matches Kotlin behavior at line 773
                if lemma_entries:
                    has_non_treebank = True

                for entry in lemma_entries:
                    definition = entry['entry_html'] or entry['entry_plain'] or ""
                    source = entry['source']
                    # Only mark as "via Treebank" if truly treebank-only (no dictionary entries)
                    # But we just set has_non_treebank=True above if entries exist, so this won't happen
                    if not has_non_treebank:
                        source = f"{source} (via Treebank)"

                    entries.append(DictionaryEntry(
                        lemma=resolved_lemma,
                        definition=definition,
                        morph_info=lemma_mapping['morph_info'],
                        is_direct_match=False,
                        confidence=lemma_mapping['confidence'],
                        source=source,
                        has_non_treebank_path=has_non_treebank
                    ))

                if lemma_entries:
                    added_lemmas.add(lemma)

        # STEP 3: If still no entries and Greek, try ultra-normalized search
        if not entries and normalized_language == "greek":
            ultra_normalized = self.normalize_greek_ultra(cleaned_word)

            cursor.execute("""
                SELECT headword, entry_html, entry_plain, source
                FROM dictionary_entries
                WHERE headword_normalized_ultra = ? AND language = ?
            """, (ultra_normalized, normalized_language))

            ultra_entries = cursor.fetchall()
            for entry in ultra_entries:
                if entry['headword'] not in added_lemmas:
                    definition = entry['entry_html'] or entry['entry_plain'] or ""
                    entries.append(DictionaryEntry(
                        lemma=entry['headword'],
                        definition=definition,
                        morph_info="found via simplified form",
                        is_direct_match=True,
                        confidence=0.7,
                        source=entry['source'],
                        has_non_treebank_path=True
                    ))
                    added_lemmas.add(entry['headword'])

        # STEP 4: Deduplicate entries
        seen_keys = set()
        deduplicated = []
        for entry in entries:
            # Create unique key from lemma + source + definition prefix
            definition_key = (entry.definition or "")[:100]
            key = f"{entry.lemma}_{entry.source}_{definition_key}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduplicated.append(entry)

        # STEP 5: Sort entries - matches Kotlin sorting logic exactly
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

            return (priority_0, priority_1, priority_2, priority_3, priority_4, priority_5, priority_6)

        sorted_entries = sorted(deduplicated, key=sort_key)

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
