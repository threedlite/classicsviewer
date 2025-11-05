#!/usr/bin/env python3
"""
Generate line-by-line interlinear translation for Greek works

Uses the proper dictionary lookup implementation from ui_dictionary_lookup.py
to match the Android app's behavior exactly.

⚠️  IMPORTANT: This module is loaded by multiprocessing workers
--------------------------------------------------------------
When interlinear_list.py runs with --workers > 1, this module is loaded
by spawned worker processes. Python bytecode cache (*.pyc, __pycache__) can
cause workers to load OLD versions of this code even after modifications.

**After ANY code changes to this file:**
1. Kill ALL Python processes: pkill -9 python
2. Clear cache: find . -name "*.pyc" -delete && find . -name "__pycache__" -exec rm -rf {} +
3. Restart generation from scratch

**Key fixes implemented here:**
- Lines 79-90: Wiktionary qualifier extraction (extracts "the" from "rarely in _ Epic... the")
- Lines 253-256: Sanity check to reject wrong data (prevents εἰ showing as "the")
"""

import sqlite3
import re
from pathlib import Path
from typing import List, Dict
import html
from functools import lru_cache

# Import the proper dictionary lookup from ui_dictionary_lookup (same directory)
# CRITICAL: Must be imported as relative import to maintain correct module state
# DO NOT add try/except fallback - if this fails, the build should fail
from .ui_dictionary_lookup import PerseusRepository, DictionaryEntry

# Database path - will be set when called from build script
DB_PATH = None


class InterlinearGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        # Use the proper dictionary lookup implementation
        self.repo = PerseusRepository(db_path)

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        if self.repo and self.repo.conn:
            self.repo.conn.close()

    def get_greek_lines(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Extract Greek text lines from database"""
        cursor = self.conn.cursor()
        query = """
        SELECT line_number, line_text
        FROM text_lines
        WHERE book_id = ? AND line_number BETWEEN ? AND ?
        ORDER BY line_number
        """
        cursor.execute(query, (book_id, start_line, end_line))

        lines = []
        for row in cursor.fetchall():
            lines.append({
                'line_number': row['line_number'],
                'text_content': row['line_text']
            })
        return lines

    def tokenize_greek(self, text: str) -> List[str]:
        """Simple Greek tokenization - split on whitespace and remove punctuation"""
        # Remove common punctuation but keep Greek text
        text = re.sub(r'[,;·.?!—\[\]():]', ' ', text)
        tokens = text.split()
        return [t.strip() for t in tokens if t.strip()]

    def _remove_greek_text(self, text: str) -> str:
        """
        Remove Greek characters from text to ensure English-only glosses.
        This is critical - Greek text in glosses causes major confusion.
        """
        # Remove Greek text in brackets and parentheses
        text = re.sub(r'[\[\(][^\]\)]*[\u0370-\u03FF\u1F00-\u1FFF][^\]\)]*[\]\)]', ' ', text)

        # Remove remaining Greek characters
        text = re.sub(r'[\u0370-\u03FF\u1F00-\u1FFF]+', ' ', text)

        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _remove_citations(self, text: str) -> str:
        """
        Remove ALL citation patterns from glosses.
        Citations appear in multiple formats and must be comprehensively removed.
        """
        # Remove Greek letter citations (e.g., "Α29", "Β113", "Ζ487")
        text = re.sub(r'\s+[Α-Ω][α-ω]?\d+(?:\s*,\s*[Α-Ω][α-ω]?\d+)*', '', text)

        # Remove Arabic numeral citations (e.g., "19, 164, 113 = 288 =")
        # Pattern: space + numbers with optional commas, equals, and trailing punctuation
        text = re.sub(r'\s+\d+(?:\s*[,=]\s*\d+)*\s*=?\s*', ' ', text)

        # Remove standalone equals signs
        text = re.sub(r'\s*=\s*', ' ', text)

        # Remove citation ranges (e.g., "19-24", "113-288")
        text = re.sub(r'\s+\d+\s*[-–]\s*\d+', ' ', text)

        # Remove numbers at end of definitions (Cunliffe references)
        # e.g., "To be asleep, sleep, slumber 313." -> "To be asleep, sleep, slumber"
        # e.g., "A shepherd (in 82 app." -> "A shepherd"
        # e.g., "Famous warrior 42, 357." -> "Famous warrior"
        # e.g., "To pass, make good one's passage 62, 357.--In" -> "To pass, make good one's passage"
        text = re.sub(r'\s+\d+(?:\s*,\s*\d+)*\s*\.?(?:\s*[-–]|$)', '', text)
        text = re.sub(r'\s+\(\s*in\s+\d+\s+[^)]*$', '', text)

        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def extract_gloss_from_entry(self, entry: DictionaryEntry) -> str:
        """
        Extract a simple English gloss from a DictionaryEntry using source-specific parsing.
        Returns the first reasonable definition text, truncated to 50 chars.
        """
        if not entry or not entry.definition:
            return "???"

        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', entry.definition)

        # SOURCE-SPECIFIC PARSING
        if entry.source == 'lsj':
            result = self._extract_lsj_gloss(text)
        elif entry.source == 'cunliffe':
            result = self._extract_cunliffe_gloss(text)
        elif entry.source == 'wiktionary':
            result = self._extract_wiktionary_gloss(text)
        else:
            # Generic fallback
            result = self._extract_generic_gloss(text)

        # FINAL VALIDATION: Reject obviously wrong definitions
        # These patterns indicate morphology returned wrong lemma
        if result and result != "???":
            result_lower = result.lower()
            # Reject verb definitions that are clearly wrong for particles
            # "to recall to memory" / "make famous" are from μνάομαι (wrong lemma for δέ)
            if "make famous" in result_lower or "recall to memory" in result_lower:
                return "???"

            # Strip ALL LSJ reference numbers and citations comprehensively:

            # 1. Remove numbers before double-dash separator (e.g., "437, 460.--So in mid.")
            result = re.sub(r'\s+\d+(?:,\s*\d+)*\.?--', ' ', result)

            # 2. Remove trailing citations (e.g., "62, 357.", "82 app.")
            result = re.sub(r'\s+\d+(?:,\s*\d+)*\.?(?:\s+app\.)?$', '', result)

            # 3. Remove cross-references (e.g., ", see (2).", ", cf. (1)")
            result = re.sub(r',?\s+(?:see|cf\.)\s+\(\d+\)\.?', '', result)

            # 4. Remove standalone parenthetical numbers (e.g., "(2)" as entire gloss)
            result = re.sub(r'^\s*\(\d+\)\s*$', '???', result)

            # 5. Remove trailing parenthetical numbers (e.g., "(1)" at end)
            result = re.sub(r'\s+\(\d+\)$', '', result)

            result = result.strip()

        return result

    def _extract_wiktionary_gloss(self, text: str) -> str:
        """
        Extract gloss from Wiktionary entry using structural analysis.

        Wiktionary entries follow: [qualifier metadata] [actual definition]
        This method uses structure (colons, semicolons, word patterns) rather than
        specific pattern matching to separate qualifiers from definitions.
        """
        text = text.strip()

        # Check for cross-references (e.g., "word = otherword" or "= otherword")
        # Pattern: Greek word followed by equals sign and another Greek word
        if re.match(r'^[\u0370-\u03FF\u1F00-\u1FFF]+\s*=\s*[\u0370-\u03FF\u1F00-\u1FFF]+', text):
            return "???"
        # Also check for starts with "= Greek"
        if re.match(r'^=\s*[\u0370-\u03FF\u1F00-\u1FFF]+', text):
            return "???"

        # Strip leading colon (indicates cross-reference or see-also)
        # Example: ": thou, you" -> "thou, you"
        text = re.sub(r'^\s*:\s*', '', text)

        # Step 1: Use colon as strong separator (qualifiers : definition)
        # Example: "chiefly Epic epithet of humans: strong" -> "strong"
        if ':' in text:
            parts = text.split(':', 1)
            before_colon = parts[0].lower().strip()
            after_colon = parts[1].strip()

            # Common qualifier indicators that appear before colon
            qualifier_indicators = [
                'epic', 'poetic', 'homeric', 'chiefly', 'rarely', 'vague', 'epithet',
                'transitive', 'intransitive', 'inflection', 'demonstrative'
            ]

            # If before colon has qualifiers and after has content, use after colon
            if any(q in before_colon for q in qualifier_indicators) and after_colon and after_colon[0].islower():
                text = after_colon

        # Step 2: Split by semicolon and process each part to find real definition
        parts = [p.strip() for p in text.split(';')]

        # Comprehensive qualifier word set
        qualifier_words = {
            # Dialectal/register
            'epic', 'poetic', 'homeric', 'ionic', 'attic', 'aeolic', 'doric',
            'archaic', 'classical', 'koine',
            # Frequency
            'chiefly', 'rarely', 'often', 'usually', 'sometimes', 'mainly',
            # Grammatical
            'transitive', 'intransitive', 'active', 'passive', 'middle',
            'ambitransitive',  # can be used transitively or intransitively
            'countable', 'uncountable', 'plurale', 'tantum',
            'inflection', 'demonstrative', 'personal', 'pronoun', 'adjective',
            'relative',  # relative pronoun qualifier
            'first', 'second', 'third',  # person qualifiers
            # Meta phrases (common in qualifier context)
            'of', 'in', '_', 'also', 'the', 'later', 'language',
            'singular', 'plural', 'dual', 'number',
            'one', 'or', 'whom', 'word', 'may', 'be', 'used',
            'person',  # as in "third person"
            'vague', 'humans', 'gods', 'animals', 'nature',
            'greek', 'and', 'for', 'from', 'with', 'than'
        }

        # Words that typically START definitions
        definition_starters = {'a', 'an', 'the', 'to'}

        # Helper function to strip qualifiers from a part
        def strip_qualifiers(part):
            """Strip leading qualifier words, return cleaned part or None if all qualifiers."""
            words = part.split()

            # Strip qualifier words from beginning, but stop at definition starters
            while words and words[0].lower() in qualifier_words and words[0].lower() not in definition_starters:
                words.pop(0)

            result = ' '.join(words) if words else ''
            return result if len(result) > 2 else None

        # Try each semicolon-separated part in order, return first valid one
        for part in parts:
            if not part:
                continue

            cleaned = strip_qualifiers(part)
            if cleaned:
                text = cleaned
                break
        else:
            # No part yielded a valid result, fall back to whole text
            text = strip_qualifiers(text) or text

        result = text

        # Check for "Famous" bug - reject ONLY if Famous/renowned at START
        # "Famous, renowned. Epithet of X" = bad (wrong lemma for particle)
        # "epic epithet: far-shooting" = OK (legitimate definition)
        if re.match(r'^\s*(?:Famous|renowned)\b', result, re.IGNORECASE):
            return "???"

        # Remove Greek characters (CRITICAL FIX)
        result = self._remove_greek_text(result)

        # Remove trailing prepositions/fragments (e.g., "To speak among, address. With" -> "To speak among, address")
        result = re.sub(r'\s+(with|to|in|of|for|by|at|on|from)\.?\s*$', '', result, flags=re.IGNORECASE)

        # Truncate if too long
        if len(result) > 50:
            result = result[:47] + '...'

        # FINAL SAFETY CHECK: If result still contains Greek, return "???"
        if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', result):
            return "???"

        # Final safety: if result is empty or very short, return original (but check for Greek first)
        if len(result) <= 2:
            fallback = text[:50]
            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', fallback):
                return "???"
            return fallback

        return result

    def _extract_lsj_gloss(self, text: str) -> str:
        """
        Extract gloss from LSJ entry using comprehensive structure parsing.

        LSJ entries have this structure:
        <div class='definition'>Etymology: ...
        I. main definition
        1. sub-definition; another meaning; yet another
        2. sub-definition
        II. secondary definition
        </div>

        Semicolons separate different meanings within the same numbered item.
        We want to extract the first real definition after Etymology, handling
        semicolon-separated meanings like we do for Wiktionary.
        """
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        text = text.strip()

        # Remove "Perseus." prefix
        text = re.sub(r'^Perseus\.\s*', '', text)

        # Remove Etymology section (everything up to and including "Etymology: ...")
        # Look for patterns like "Etymology: ... (citations)" followed by Roman numeral or number
        text = re.sub(r'^Etymology:.*?(?=\n[IVX0-9]+\.|\Z)', '', text, flags=re.DOTALL)
        text = text.strip()

        # LSJ structure: Look for first definition after section markers
        # CRITICAL PRIORITY ORDER:
        # 1. FIRST try simple text at beginning (before section markers) - e.g., "in, among. c. dat."
        # 2. THEN try ROMAN numerals (I., II., III.) - these are PRIMARY sections
        # 3. THEN try Arabic numbered sections (1., 2.) - these are SUB-sections
        patterns = [
            r'^([^0-9IVXABC\n][^\n]{3,}?)(?:\n|$)',  # Simple text at start (min 3 chars, not starting with UPPERCASE marker)
            r'(?:^|\n)I\.\s+([^\n]+)',       # "I. definition" - PRIMARY section
            r'(?:^|\n)II\.\s+([^\n]+)',      # "II. definition"
            r'(?:^|\n)A\.\s+([^\n]+)',       # "A. definition"
            r'(?:^|\n)B\.\s+([^\n]+)',       # "B. definition" (common in ὁ entry)
            r'(?:^|\n)0\.\s+([^\n]+)',       # "0. definition"
            r'(?:^|\n)1\.\s+([^\n]+)',       # "1. definition" - sub-section
            r'(?:^|\n)2\.\s+([^\n]+)',       # "2. definition" - sub-section
            r'^([^(\n]+?)(?:\(|$)',          # Text before parenthesis (fallback)
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                full_def = match.group(1).strip()

                # CRITICAL FIX: Remove leading number prefix (e.g., "1. all" -> "all")
                full_def = re.sub(r'^[0-9]+\.\s+', '', full_def)

                # Check if this is ONLY a source citation (e.g., "(Hom., Trag.)" or "(Hom.)")
                # These appear as section markers with no actual definition
                if re.match(r'^\([^)]*(?:Hom|Il|Od|Trag|Anth|Soph|Aesch|Eur|Ar|Plat)[^)]*\)\s*\.?\s*$', full_def):
                    return "???"

                # Also check for section number with citation only (e.g., "0. (Soph.)")
                if re.match(r'^\d+\.\s*\([^)]*\)\s*\.?\s*$', full_def):
                    return "???"

                # Check for grammatical term followed by numbers (e.g., "Locative 607")
                if re.match(r'^(?:Locative|Genitive|Dative|Accusative|Nominative|Vocative|Ablative)\s+\d+\s*$', full_def, re.IGNORECASE):
                    return "???"

                # Check if it's just a single word (likely case name like "Nom", "Dat")
                if re.match(r'^(?:Nom|Gen|Dat|Acc|Voc|Abl)\.?\s*$', full_def, re.IGNORECASE):
                    return "???"

                # Check for "Famous" bug - reject ONLY if Famous/renowned at START
                # "Famous, renowned. Epithet of X" = bad (wrong lemma for particle)
                # "The farshooter. Epithet of Apollo" = OK (legitimate definition)
                if re.match(r'^\s*(?:Famous|renowned)\b', full_def, re.IGNORECASE):
                    return "???"

                # Remove citations in parentheses
                full_def = re.sub(r'\([^)]+\)', '', full_def)

                # Split on semicolon - LSJ uses semicolons to separate meanings
                parts = [p.strip() for p in full_def.split(';')]

                # Qualifier words that can appear in LSJ definitions
                qualifier_words = {
                    'epic', 'poetic', 'homeric', 'ionic', 'attic', 'aeolic', 'doric',
                    'archaic', 'classical', 'koine', 'chiefly', 'rarely', 'often',
                    'usually', 'sometimes', 'mainly', 'all'  # "all" appears in δὴ
                }

                # Helper to strip leading qualifiers
                def strip_qualifiers(part):
                    words = part.split()
                    while words and words[0].lower() in qualifier_words:
                        words.pop(0)
                    result = ' '.join(words) if words else ''
                    return result if len(result) > 2 else None

                # Apply sequential stripping logic
                # PREFER FIRST PART if it's short and simple (like "this", "that", "who", "which")
                # These are often pronoun definitions that don't need "a/an/the" prefix
                first_stripped = None
                for i, part in enumerate(parts):
                    stripped = strip_qualifiers(part)
                    if stripped and len(stripped) > 2:
                        # Remove Greek characters (CRITICAL FIX)
                        stripped = self._remove_greek_text(stripped)
                        # Remove grammatical abbreviations (e.g., "c. dat.", "c. gen.", "w. acc.")
                        stripped = re.sub(r'\s+[cw]\.\s+\w+\.?\s*$', '', stripped, flags=re.IGNORECASE)
                        # Remove trailing prepositions
                        stripped = re.sub(r'\s+(with|to|in|of|for|by|at|on|from)\.?\s*$', '', stripped, flags=re.IGNORECASE)

                        # Save first valid part
                        if i == 0 and first_stripped is None:
                            first_stripped = stripped

                        # Check if it starts with a likely definition word
                        # Include demonstrative/interrogative pronouns and conjunctions that are themselves definitions
                        definition_starters = ['a ', 'an ', 'the ', 'to ', 'but', 'this', 'that', 'these',
                                             'those', 'who', 'whom', 'which', 'what', 'where', 'when']
                        # For single-word pronouns/conjunctions, do exact match; for others, check prefix
                        is_valid = False
                        stripped_lower = stripped.lower()
                        for starter in definition_starters:
                            if starter in ['but', 'this', 'that', 'these', 'those', 'who', 'whom', 'which', 'what', 'where', 'when']:
                                if stripped_lower == starter or stripped_lower.startswith(starter + ' ') or stripped_lower.startswith(starter + ';'):
                                    is_valid = True
                                    break
                            elif stripped_lower.startswith(starter):
                                is_valid = True
                                break

                        if is_valid:
                            if len(stripped) > 50:
                                stripped = stripped[:47] + '...'
                            # FINAL SAFETY CHECK: If result still contains Greek, return "???"
                            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', stripped):
                                return "???"
                            return stripped

                # If no "a/an/the/to" found, use FIRST part if it's a simple word
                # (like "this", "that", "who", "which" - common pronoun definitions)
                if first_stripped and len(first_stripped.split()) <= 2:
                    if len(first_stripped) > 50:
                        first_stripped = first_stripped[:47] + '...'
                    if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', first_stripped):
                        return "???"
                    return first_stripped

                # If no part with definition starter found, return first non-empty part
                for part in parts:
                    stripped = strip_qualifiers(part)
                    if stripped and len(stripped) > 2:
                        # Remove Greek characters (CRITICAL FIX)
                        stripped = self._remove_greek_text(stripped)
                        # Remove grammatical abbreviations (e.g., "c. dat.", "c. gen.", "w. acc.")
                        stripped = re.sub(r'\s+[cw]\.\s+\w+\.?\s*$', '', stripped, flags=re.IGNORECASE)
                        # Remove trailing prepositions
                        stripped = re.sub(r'\s+(with|to|in|of|for|by|at|on|from)\.?\s*$', '', stripped, flags=re.IGNORECASE)
                        # Remove leading section markers (I., II., A., B., etc.)
                        stripped = re.sub(r'^[IVXABC]+\.\s+', '', stripped)
                        # Remove trailing punctuation
                        stripped = re.sub(r'[.,;:]+$', '', stripped).strip()

                        if len(stripped) > 50:
                            stripped = stripped[:47] + '...'
                        # FINAL SAFETY CHECK: If result still contains Greek, return "???"
                        if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', stripped):
                            return "???"
                        return stripped

        # Fallback - check for Greek before returning
        if text:
            fallback = text[:50]
            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', fallback):
                return "???"
            return fallback
        return "???"

    def _extract_cunliffe_gloss(self, text: str) -> str:
        """
        Extract gloss from Cunliffe entry.

        Cunliffe structure:
        †word [etymology]. morphology forms. Definition: usage example cite.

        OR:

        word. Preamble text.
        1. Section header
                a. Definition: usage example cite.
        """
        # Strip HTML
        text = re.sub(r'<[^>]+>', '', text)
        text = text.strip()

        # ENHANCED CROSS-REFERENCE DETECTION
        # Pattern 1a: Standard cross-reference with tense before number/person
        # e.g., "word, aor. 3 dual otherword."
        if re.match(r'^[^\s,]+,\s+(?:aor|pres|fut|impf|perf|pluperf)\.?\s+\d+\s+(?:sing|pl|dual)\s+[^\s.]+\.\s*$', text):
            return "???"

        # Pattern 1b: Cross-reference with number/person before tense
        # e.g., "διαστήτην, 3 dual aor. διίστημι." or "ἐποίσει, 3 sing. fut. ἐπιφέρω."
        if re.match(r'^[^\s,]+,\s+\d+\s+(?:sing|pl|dual)\.?\s+(?:aor|pres|fut|impf|perf|pluperf)\.?\s+\S+\.\s*$', text):
            return "???"

        # Pattern 1c: Cross-reference with grammatical info and lemma
        # e.g., "σύνθεο, aor. imp. mid. συντίθημι."
        if re.match(r'^[^\s,]+,\s+(?:aor|pres|fut|impf|perf|pluperf)\.?\s+(?:imp|ind|subj|opt|inf|part)\.?\s+(?:act|mid|pass)\.?\s+\S+\.\s*$', text):
            return "???"

        # Pattern 1d: Cross-reference with participle
        # e.g., "ἐπάλμενος, aor. pple. ἐφάλλομαι."
        if re.match(r'^[^\s,]+,\s+(?:aor|pres|fut|impf|perf|pluperf)\.?\s+(?:pple|part)\.?\s+\S+\.\s*$', text):
            return "???"

        # Pattern 1e: Cross-reference with case info
        # e.g., "πολέες, nom. pl. πολύς."
        if re.match(r'^[^\s,]+,\s+(?:nom|acc|gen|dat|voc)\.?\s+(?:sing|pl|dual)\.?\s+\S+\.\s*$', text):
            return "???"

        # Pattern 1f: General cross-reference - comma, abbreviation(s), Greek word ending with period
        # This catches remaining patterns like "word, abbrev. abbrev. greekword."
        # Greek Unicode: U+0370-U+03FF, U+1F00-U+1FFF
        if re.match(r'^[^\s,]+,\s+(?:[a-z]+\.?\s+)+[\u0370-\u03FF\u1F00-\u1FFF]+\S*\.\s*$', text):
            return "???"

        # Pattern 2: Just grammatical info without definition (e.g., "In aor. and mid.")
        if re.match(r'^(?:In\s+)?(?:aor|mid|pass)\.(?:\s+and\s+(?:aor|mid|pass)\.)*\s*$', text):
            return "???"

        # Pattern 3: Section header without definition (e.g., "0. (Hom.)", "0. (Hom., Trag.)")
        if re.match(r'^\d+\.\s+\([^)]+\)\s*\.?\s*$', text):
            return "???"

        # Pattern 4: Very short entry that's just metadata
        if len(text.strip()) < 25 and re.search(r'\((?:Hom|Il|Od|Trag|Anth)\.\)', text):
            return "???"

        # Remove etymology in brackets at start
        text = re.sub(r'^\[[^\]]+\]\.\s*', '', text)

        # Remove morphology forms at start
        text = re.sub(r'^(?:\d+\s+)?(?:sing|pl|dual)\.?\s+(?:fut|aor|pres|impf|perf|pluperf)\.?\s+[^\n.]+?[Α-Ω][α-ω]?\d+.*?(?=\s+[A-Z]|$)', '', text, flags=re.DOTALL)
        text = re.sub(r'^\s*(?:Infin|Pple|Imp|Nom|Acc|Gen|Dat|Voc)\.\s+[^\n.]+?[Α-Ω][α-ω]?\d+.*?(?=\s+[A-Z]|$)', '', text, flags=re.DOTALL)

        # Look for numbered sections (e.g., "1. Expressing consequence")
        numbered_section = re.search(r'(?:^|\n)\s*1\.\s+([^\n:]+)', text)
        if numbered_section:
            gloss = numbered_section.group(1).strip()
            # Reject section headers that are just grammatical abbreviations
            # e.g., "In aor. and mid.", "In mid. or pass.", "In perf."
            if re.match(r'^(?:In\s+)?(?:aor|mid|pass|pres|fut|impf|perf|pluperf)\.(?:\s+(?:and|or)\s+(?:aor|mid|pass|pres|fut|impf|perf|pluperf)\.)*\s*$', gloss):
                return "???"
            # Check for "Famous" bug - reject ONLY if Famous/renowned at START
            if re.match(r'^\s*(?:Famous|renowned)\b', gloss, re.IGNORECASE):
                return "???"
            # Remove ALL citations (CRITICAL FIX)
            gloss = self._remove_citations(gloss)
            # Remove Greek characters (CRITICAL FIX)
            gloss = self._remove_greek_text(gloss)
            # Remove trailing prepositions
            gloss = re.sub(r'\s+(with|to|in|of|for|by|at|on|from)\.?\s*$', '', gloss, flags=re.IGNORECASE)
            if len(gloss) > 50:
                gloss = gloss[:50]
            # FINAL SAFETY CHECK: If result still contains Greek, return "???"
            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', gloss):
                return "???"
            return gloss

        # Look for definition pattern: "To verb: usage example"
        definition_with_example = re.search(r'\.?\s+(To\s+[^:]+?):\s+', text)
        if definition_with_example:
            gloss = definition_with_example.group(1).strip()
            # Check for "Famous" bug - reject ONLY if Famous/renowned at START
            if re.match(r'^\s*(?:Famous|renowned)\b', gloss, re.IGNORECASE):
                return "???"
            # Remove ALL citations (CRITICAL FIX)
            gloss = self._remove_citations(gloss)
            # Remove Greek characters (CRITICAL FIX)
            gloss = self._remove_greek_text(gloss)
            # Remove trailing prepositions - NO TRUNCATION for "To verb:" patterns
            gloss = re.sub(r'\s+(with|to|in|of|for|by|at|on|from)\.?\s*$', '', gloss, flags=re.IGNORECASE)
            # FINAL SAFETY CHECK: If result still contains Greek, return "???"
            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', gloss):
                return "???"
            return gloss  # Don't truncate complete phrases

        # Look for any capitalized definition after period
        cap_after_period = re.search(r'\.\s+([A-Z][^:.]+?)[,.]', text)
        if cap_after_period:
            gloss = cap_after_period.group(1).strip()
            # Check for case names only (e.g., "Nom", "Gen", "Dat")
            if re.match(r'^(?:Nom|Gen|Dat|Acc|Voc)(?:\.|$)', gloss):
                return "???"
            # Check for "Famous" bug - reject ONLY if Famous/renowned at START
            if re.match(r'^\s*(?:Famous|renowned)\b', gloss, re.IGNORECASE):
                return "???"
            # Remove ALL citations (CRITICAL FIX)
            gloss = self._remove_citations(gloss)
            # Remove Greek characters (CRITICAL FIX)
            gloss = self._remove_greek_text(gloss)
            # Remove trailing prepositions
            gloss = re.sub(r'\s+(with|to|in|of|for|by|at|on|from)\.?\s*$', '', gloss, flags=re.IGNORECASE)
            if len(gloss) > 2:
                if len(gloss) > 50:
                    gloss = gloss[:50]
                # FINAL SAFETY CHECK: If result still contains Greek, return "???"
                if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', gloss):
                    return "???"
                return gloss

        # Fallback - check for Greek before returning
        if text:
            fallback = text[:50]
            if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', fallback):
                return "???"
            return fallback
        return "???"

    def _extract_generic_gloss(self, text: str) -> str:
        """Generic gloss extraction for unknown sources."""

        # Remove "Perseus." prefix that appears in some LSJ entries
        text = re.sub(r'^Perseus\.\s*', '', text)

        # Remove etymology sections
        text = re.sub(r'^Etymology:.*?\n', '', text, flags=re.DOTALL)

        # Clean up the text first
        original_text = text

        # Remove Cunliffe-style etymology markers (dagger, cross, etc.)
        text = re.sub(r'^[†‡§]\s*', '', text)

        # Remove etymology in brackets at the start (e.g., "[προ- (1) + (Ϝ)ι-(Ϝ)άπτω, to throw. Cf. ἀπτοεπής, ἑάφθη]")
        text = re.sub(r'^\[[^\]]+\]\.\s*', '', text)

        # Remove lines that are just cross-references (e.g., "διαστήτην, 3 dual aor. διίστημι.")
        if re.match(r'^[^\s]+,\s+\d+\s+(?:sing|pl|dual)\s+(?:aor|pres|fut|impf|perf|pluperf)\.?\s+[^\s]+\.\s*$', text):
            return "???"  # This is just a cross-reference, not a definition

        # For Cunliffe entries, remove everything before the first numbered section or "To" phrase
        # Cunliffe format: "word [etymology]. 3 dual aor. form Α6. 1 pl. form Β7. \n1. To do something..."
        # We want to skip to the "1. To do something" part
        # Look for pattern like "\n1." or start with "1." indicating definition sections
        if re.search(r'[\n\s]+1\.\s+', text):
            # Extract from the first "1. " onwards
            match = re.search(r'[\n\s]+1\.\s+(.+)', text, re.DOTALL)
            if match:
                text = "1. " + match.group(1)

        # Remove Cunliffe-style morphology citations that remain
        # Pattern: "3 dual aor. διαστήτην Α6, Π470."
        text = re.sub(r'^\d+\s+(?:sing|pl|dual)\.?\s+(?:fut|aor|pres|impf|perf|pluperf)\.?\s+[^\n]+\n', '\n', text, flags=re.MULTILINE)
        # Remove lines like "Nom. pl. masc. pple. word Ref"
        text = re.sub(r'^\s*(?:Nom|Acc|Gen|Dat|Voc)\.\s+pl\.\s+(?:masc|fem|neut)\.\s+pple\.\s+[^\n]+\n', '\n', text, flags=re.MULTILINE)

        # Remove "Infin." and similar morphology markers with references
        text = re.sub(r'\b(?:Infin|Pple|Imp)\.\s+[^\s]+\s+[Α-Ω][α-ω]?\d+[.,]\s*', '', text)

        # Clean Greek text in brackets and parentheses
        text = re.sub(r'[\[\(][^\]\)]*[\u0370-\u03FF\u1F00-\u1FFF][^\]\)]*[\]\)]', ' ', text)

        # Remove remaining Greek characters
        text = re.sub(r'[\u0370-\u03FF\u1F00-\u1FFF]+', ' ', text)

        # Remove source abbreviations in parentheses (e.g., "(Hom., Od., Hdt., id=" or "(Il")
        # Common patterns: (Hom., (Od., (Il., (Hdt., etc.
        text = re.sub(r'\(\s*(?:Hom|Od|Il|Hdt|Aesch|Soph|Eur|Ar|Plat|Xen|Dem|Thuc|id)[.,\s)][^\)]*\)', '', text)
        # Also remove bare references like "(Hom" or "(Il" without closing paren
        text = re.sub(r'\(\s*(?:Hom|Od|Il|Hdt|Aesch|Soph|Eur|Ar|Plat|Xen|Dem|Thuc|id)[.,\s]*$', '', text)

        # Remove "Cf." references (e.g., "Cf. Ε190, Ζ487")
        text = re.sub(r'\bCf\.\s+[Α-Ω][α-ω]?\d+(?:\s*,\s*[Α-Ω][α-ω]?\d+)*\.?', '', text)

        # Remove standalone references like "Α3" or "ζ289"
        text = re.sub(r'\b[Α-Ω][α-ω]?\d+\b', '', text)

        # Clean multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # Try to extract first meaningful definition
        # Look for definitions in priority order:
        patterns = [
            r'^([^IA\d\n:]+?)(?:[;.\n]|$)',  # Simple text before semicolon/period/newline
            r'(?:^|\n)A\.\s+([^\n]+)',       # LSJ primary definition
            r'(?:^|\n)I\.\s+([^\n]+)',       # LSJ main section
            r'(?:^|\n)1\.\s+([^\n]+)',       # Numbered definition
            r'^([^:\n]+)',                    # Any text before colon/newline
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                gloss = match.group(1).strip()

                # Remove leading section markers
                gloss = re.sub(r'^[A-Z]\.\s+', '', gloss)
                gloss = re.sub(r'^[IVX]+\.\s+', '', gloss)
                gloss = re.sub(r'^\d+\.\s+', '', gloss)

                # Find first English phrase by splitting on punctuation
                parts = re.split(r'[;,.]', gloss)
                for part in parts:
                    part = part.strip()
                    # Check if this part has actual English words (not just numbers/symbols)
                    if re.search(r'[a-zA-Z]{2,}', part) and len(part) > 2:
                        # Skip meta-phrases from Wiktionary
                        skip_phrases = [
                            'one of or to whom the word may be used',
                            'that to which the word may be used',
                            'the place or time',
                        ]
                        if part.lower() in skip_phrases:
                            continue
                        gloss = part
                        break
                else:
                    gloss = parts[0].strip() if parts else ''

                # Final cleanup
                gloss = gloss.strip('.,;:').strip()

                # Remove trailing line/section references (e.g., "word 19", "word 22 = 376", "word II")
                gloss = re.sub(r'\s+\d+(?:\s*=\s*\d+)?$', '', gloss)  # Remove "19" or "22 = 376"
                gloss = re.sub(r'\s+[IVX]+$', '', gloss)  # Remove Roman numerals like "II", "III"
                gloss = re.sub(r'\s+[A-Z]$', '', gloss)  # Remove single letters like "A", "I"

                # If gloss is just numbers/periods (like "1. 2. 3. 4."), reject it
                if re.match(r'^[\d\.\s]+$', gloss):
                    continue

                # Remove "To" at the start if it's an infinitive form (we want simpler glosses)
                # Keep it if it's part of a phrase like "To give one's voice"
                if gloss.startswith('To ') and len(gloss.split()) <= 3:
                    gloss = gloss[3:].strip()

                # Reject if empty or too short
                if len(gloss) < 3:
                    continue

                # Reject if it's just grammatical metadata
                test_gloss = gloss.lower()
                test_gloss = re.sub(r'\d+', '', test_gloss)
                grammatical_terms = r'\b(sing|singular|plur|plural|dual|aor|aorist|pres|present|imperf|imperfect|perf|perfect|pluperf|pluperfect|fut|future|opt|optative|subj|subjunctive|indic|indicative|inf|infinitive|part|participle|act|active|mid|middle|pass|passive|nom|nominative|gen|genitive|dat|dative|acc|accusative|voc|vocative|masc|masculine|fem|feminine|neut|neuter)\b'
                test_gloss = re.sub(grammatical_terms, '', test_gloss)
                test_gloss = re.sub(r'[\s.,;:\-]+', '', test_gloss)

                if not test_gloss:
                    continue

                # Truncate if too long
                if len(gloss) > 50:
                    gloss = gloss[:47] + '...'

                # FINAL SAFETY CHECK: If result still contains Greek, return "???"
                if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', gloss):
                    return "???"

                return gloss

        # Fallback: just take first 50 chars of cleaned text
        text = ' '.join(text.split())[:50]
        # FINAL SAFETY CHECK for fallback
        if text and re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', text):
            return "???"
        return text if text else "???"

    @lru_cache(maxsize=10000)
    def _cached_lookup_word(self, word: str) -> tuple:
        """
        Cache word lookups - returns (gloss, lemma, morph) tuple.

        LRU cache with 10,000 entries means common words like καί, δέ, τε, ἐν, etc.
        are only looked up once and then retrieved from cache instantly.

        For the Iliad (~125,000 words), this reduces ~100,000+ database queries
        to just a few thousand unique word lookups.
        """
        entries = self.repo.get_all_dictionary_entries(word, "greek")

        # Process entries to extract gloss, lemma, morph
        gloss = None
        lemma = None
        morph = None

        if entries and len(entries) > 0:
            # PREFER LSJ/Cunliffe over Wiktionary for better quality
            # First, try LSJ and Cunliffe entries
            for entry in entries:
                if entry.source in ['lsj', 'cunliffe']:
                    extracted_gloss = self.extract_gloss_from_entry(entry)
                    is_citation_only = bool(re.search(r'[Α-Ω][α-ω]?\d+', extracted_gloss))

                    if extracted_gloss and extracted_gloss != "???" and not is_citation_only and len(extracted_gloss) > 2:
                        lemma = entry.lemma
                        morph = entry.morph_info
                        gloss = extracted_gloss
                        break

            # If no good LSJ/Cunliffe entry, try Wiktionary (skip low-quality ones)
            if not gloss:
                for entry in entries:
                    if entry.source == 'wiktionary':
                        # Skip Wiktionary entries that are just cross-references or templates
                        if entry.definition and ('inflection of' in entry.definition.lower() or
                                                '{{infl of' in entry.definition):
                            continue

                        # Skip Wiktionary entries that are just part-of-speech labels
                        pos_only = ['adjective', 'noun', 'verb', 'adverb', 'pronoun',
                                   'proper noun', 'substantive', 'preposition',
                                   'conjunction', 'particle']
                        def_stripped = entry.definition.strip().lower() if entry.definition else ''
                        # Remove HTML div tags for comparison
                        def_stripped = re.sub(r'<[^>]+>', '', def_stripped).strip()
                        if def_stripped in pos_only:
                            continue

                        extracted_gloss = self.extract_gloss_from_entry(entry)
                        if extracted_gloss and extracted_gloss != "???" and len(extracted_gloss) > 2:
                            # Sanity check: "the" should only be used for actual article lemmas
                            if extracted_gloss == "the" and entry.lemma not in ['ὁ', 'ἡ', 'τό']:
                                continue

                            # Reject glosses that are just qualifiers (Epic, poetic, etc.)
                            qualifier_only = ['epic', 'poetic', 'homeric', 'ionic', 'attic',
                                            'aeolic', 'doric']
                            if extracted_gloss.lower().strip() in qualifier_only:
                                continue

                            lemma = entry.lemma
                            morph = entry.morph_info
                            gloss = extracted_gloss
                            break

            # If still no good entry, try any other sources
            if not gloss:
                for entry in entries[:5]:
                    extracted_gloss = self.extract_gloss_from_entry(entry)
                    is_citation_only = bool(re.search(r'[Α-Ω][α-ω]?\d+', extracted_gloss))

                    if extracted_gloss and extracted_gloss != "???" and not is_citation_only and len(extracted_gloss) > 2:
                        lemma = entry.lemma
                        morph = entry.morph_info
                        gloss = extracted_gloss
                        break

            # If still no good gloss, use first entry's lemma at least
            if not gloss:
                first_entry = entries[0]
                lemma = first_entry.lemma
                morph = first_entry.morph_info
                gloss = self.extract_gloss_from_entry(first_entry)

        # Fallback if no gloss found
        if not gloss or gloss == "???":
            gloss = "???"

        return (gloss, lemma, morph)

    def lookup_word(self, word: str, book_id: str, line_number: int, position: int) -> Dict:
        """
        Lookup word using cached dictionary lookup.
        Returns a dict with greek, position, gloss, lemma, morph
        """
        # Get cached result (gloss, lemma, morph) - instant for repeated words!
        gloss, lemma, morph = self._cached_lookup_word(word)

        return {
            'greek': word,
            'position': position,
            'gloss': gloss,
            'lemma': lemma,
            'morph': morph
        }

    def generate_interlinear(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Main function to generate interlinear translation"""

        # Step 1: Get Greek text
        print(f"Extracting Greek lines {start_line}-{end_line}...")
        greek_lines = self.get_greek_lines(book_id, start_line, end_line)

        if not greek_lines:
            raise ValueError(f"No Greek text found for {book_id} lines {start_line}-{end_line}")

        print(f"Found {len(greek_lines)} Greek lines")

        # Step 2: Process each line
        print(f"Processing lines and generating glosses...")
        lines_data = []

        for line in greek_lines:
            line_num = line['line_number']
            text = line['text_content']

            # Tokenize
            tokens = self.tokenize_greek(text)

            # Lookup each word
            words = []
            for pos, token in enumerate(tokens, 1):
                word_data = self.lookup_word(token, book_id, line_num, pos)
                words.append(word_data)

            # Create word-by-word gloss
            word_gloss = ' '.join([w['gloss'] if w['gloss'] else '???' for w in words])

            lines_data.append({
                'line_number': line_num,
                'greek_text': text,
                'words': words,
                'word_gloss': word_gloss
            })

        return lines_data


def generate_interlinear_translations(db_path: Path, output_dir: Path, work_ids=None):
    """
    Generate interlinear translations for Greek works

    Args:
        db_path: Path to the Perseus database
        output_dir: Directory where XML files will be written
        work_ids: List of TLG work IDs to process (e.g., ['tlg0012.tlg001', 'tlg0012.tlg002']).
                  If None, defaults to Homer's Iliad and Odyssey.
    """
    global DB_PATH
    DB_PATH = db_path

    if work_ids is None:
        # Default to Homer's Iliad and Odyssey
        work_ids = ['tlg0012.tlg001', 'tlg0012.tlg002']
    elif isinstance(work_ids, str):
        work_ids = [work_ids]

    output_dir.mkdir(parents=True, exist_ok=True)

    total_works = len(work_ids)
    for work_idx, work_id in enumerate(work_ids, 1):
        work_percent = (work_idx - 1) / total_works * 100
        print(f"\n{'=' * 80}")
        print(f"WORK {work_idx}/{total_works} - {work_percent:.1f}% complete: {work_id}")
        print(f"{'=' * 80}")
        _generate_work(work_id, output_dir)
        work_percent = work_idx / total_works * 100
        print(f"\n✓ Work {work_id} complete ({work_percent:.1f}% of all works)")


def _write_xml_header(f, work_id: str, work_title: str, author_name: str):
    """Write XML header and TEI metadata (streaming helper)"""
    work_title_escaped = html.escape(work_title)
    author_name_escaped = html.escape(author_name)
    work_id_escaped = html.escape(work_id)

    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<?xml-model href="http://www.stoa.org/epidoc/schema/8.19/tei-epidoc.rng"\n')
    f.write('  schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
    f.write('<TEI xmlns="http://www.tei-c.org/ns/1.0">\n')
    f.write('    <teiHeader>\n')
    f.write('        <fileDesc>\n')
    f.write('            <titleStmt>\n')
    f.write(f'                <title>{work_title_escaped} - Interlinear Translation</title>\n')
    f.write(f'                <author>{author_name_escaped}</author>\n')
    f.write('                <editor role="translator">Interlinear (Beta, AI-generated from app dictionary)</editor>\n')
    f.write('                <sponsor>Derived from LSJ, Murray, Cunliffe, Wiktionary, Perseus</sponsor>\n')
    f.write('                <principal></principal>\n')
    f.write('                <respStmt>\n')
    f.write('                    <resp>AI-generated interlinear translation</resp>\n')
    f.write('                    <name>Claude Code</name>\n')
    f.write('                </respStmt>\n')
    f.write('            </titleStmt>\n')
    f.write('            <extent>AI-generated interlinear</extent>\n')
    f.write('            <publicationStmt>\n')
    f.write('                <publisher></publisher>\n')
    f.write('                <pubPlace></pubPlace>\n')
    f.write('                <authority></authority>\n')
    f.write('            </publicationStmt>\n')
    f.write('            <notesStmt>\n')
    f.write('                <note anchored="true">AI-generated word-by-word interlinear translation derived from LSJ, Cunliffe, and Wiktionary dictionaries.</note>\n')
    f.write('            </notesStmt>\n')
    f.write('            <sourceDesc>\n')
    f.write('                <biblStruct>\n')
    f.write('                    <monogr>\n')
    f.write(f'                        <author>{author_name_escaped}</author>\n')
    f.write(f'                        <title>{work_title_escaped}</title>\n')
    f.write('                        <title type="sub">Interlinear Translation</title>\n')
    f.write('                        <editor role="translator">AI-generated</editor>\n')
    f.write('                        <imprint>\n')
    f.write('                            <date>2025</date>\n')
    f.write('                        </imprint>\n')
    f.write('                    </monogr>\n')
    f.write('                </biblStruct>\n')
    f.write('            </sourceDesc>\n')
    f.write('        </fileDesc>\n')
    f.write('        <encodingDesc>\n')
    f.write('            <refsDecl n="CTS">\n')
    f.write('                <cRefPattern n="line" matchPattern="(\\w+).(\\w+)"\n')
    f.write('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\']//tei:l[@n=\'$2\'])">\n')
    f.write('                    <p>This pointer pattern extracts book and line</p>\n')
    f.write('                </cRefPattern>\n')
    f.write('                <cRefPattern n="book" matchPattern="(\\w+)"\n')
    f.write('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\'])">\n')
    f.write('                    <p>This pointer pattern extracts book</p>\n')
    f.write('                </cRefPattern>\n')
    f.write('            </refsDecl>\n')
    f.write('            <refsDecl>\n')
    f.write('                <refState unit="book" delim="."/>\n')
    f.write('                <refState unit="line"/>\n')
    f.write('            </refsDecl>\n')
    f.write('        </encodingDesc>\n')
    f.write('        <profileDesc>\n')
    f.write('            <langUsage>\n')
    f.write('                <language ident="eng">English</language>\n')
    f.write('                <language ident="grc">Greek</language>\n')
    f.write('            </langUsage>\n')
    f.write('        </profileDesc>\n')
    f.write('        <revisionDesc>\n')
    f.write('            <change when="20251104" who="Claude Code">Generated interlinear translation.</change>\n')
    f.write('        </revisionDesc>\n')
    f.write('    </teiHeader>\n')
    f.write('    <text xml:lang="eng">\n')
    f.write('        <body>\n')
    f.write(f'            <div type="translation" n="urn:cts:greekLit:{work_id_escaped}.perseus-eng99" xml:lang="eng">\n')


def _write_book_to_xml(f, book_num: int, book_results: List[Dict]):
    """Write a single book to XML file (streaming helper)"""
    f.write(f'                <div type="textpart" subtype="Book" n="{book_num}">\n')

    for line_data in book_results:
        line_num = line_data['line_number']

        # Build interlinear text efficiently using list comprehension
        word_tables = []
        for w in line_data['words']:
            greek = w['greek'] if w['greek'] else '???'
            gloss = w['gloss'] if w['gloss'] else '???'
            lemma = w['lemma'] if w['lemma'] else '?'
            morph = w['morph'] if w['morph'] else ''

            lemma_morph = f'{lemma} {morph}' if morph else lemma
            table = f'| {greek} |\n| **{gloss}** |\n| {lemma_morph} |'
            word_tables.append(table)

        interlinear_text = '  '.join(word_tables)
        f.write(f'                    <l n="{line_num}">{interlinear_text}</l>\n')

    f.write('                </div>\n')


def _write_xml_footer(f):
    """Write XML footer (streaming helper)"""
    f.write('            </div>\n')
    f.write('        </body>\n')
    f.write('    </text>\n')
    f.write('</TEI>\n')


def _write_book_to_txt(f, book_num: int, book_results: List[Dict]):
    """Write a single book to text file (streaming helper)"""
    f.write(f"\n{'=' * 80}\n")
    f.write(f"BOOK {book_num}\n")
    f.write(f"{'=' * 80}\n\n")

    for line_data in book_results:
        line_num = line_data['line_number']
        greek_words = [w['greek'] for w in line_data['words']]
        glosses = [w['gloss'] for w in line_data['words']]

        f.write(f"{line_num}. {' | '.join(greek_words)}\n")
        f.write(f"{' | '.join(glosses)}\n\n")


def _generate_work(work_id: str, output_dir: Path):
    """
    Generate interlinear translation for a single work using TLG ID.

    Uses STREAMING architecture: processes and writes one book at a time
    to minimize memory usage and ensure all files are written correctly.

    NO THREADS - completely single-threaded, simple, reliable.
    """

    print("=" * 80)
    print(f"INTERLINEAR TRANSLATION GENERATOR")
    print("=" * 80)
    print(f"Work ID: {work_id}")
    print(f"Database: {DB_PATH}")
    print("=" * 80)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # Get all books for this work
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    book_pattern = f"{work_id}.%"
    cursor.execute("SELECT DISTINCT book_id FROM text_lines WHERE book_id LIKE ? ORDER BY book_id", (book_pattern,))
    book_ids = [row[0] for row in cursor.fetchall()]

    # Get work metadata for XML
    cursor.execute("""
        SELECT DISTINCT w.title_english, a.name
        FROM works w
        JOIN authors a ON w.author_id = a.id
        WHERE w.id = ?
    """, (work_id,))
    work_metadata = cursor.fetchone()
    conn.close()

    if not book_ids:
        raise ValueError(f"No books found for work ID {work_id}")

    if work_metadata:
        work_title, author_name = work_metadata
    else:
        work_title = work_id
        author_name = "Unknown"

    print(f"\nFound {len(book_ids)} books to process")
    print(f"Work: {work_title} by {author_name}")
    print("=" * 80)

    # Generate output filenames
    txt_filename = f"{work_id}.interlinear.txt"
    xml_filename = f"{work_id}.perseus-eng99.xml"
    output_file = output_dir / txt_filename
    xml_output_file = output_dir / xml_filename

    total_lines = 0

    try:
        # Open BOTH output files at the start - streaming architecture
        with open(output_file, 'w', encoding='utf-8') as txt_file, \
             open(xml_output_file, 'w', encoding='utf-8') as xml_file, \
             InterlinearGenerator(str(DB_PATH)) as generator:

            # Write XML header once at start
            _write_xml_header(xml_file, work_id, work_title, author_name)

            # Process each book ONE AT A TIME - memory efficient streaming
            for idx, book_id in enumerate(book_ids, 1):
                book_num = int(book_id.split('.')[-1])
                percent_complete = (idx - 1) / len(book_ids) * 100
                print(f"\n[{idx}/{len(book_ids)} - {percent_complete:.1f}% complete] Processing Book {book_num}...")

                # Get line range for this book
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                cursor.execute("SELECT MIN(line_number), MAX(line_number) FROM text_lines WHERE book_id = ?", (book_id,))
                start_line, end_line = cursor.fetchone()
                conn.close()

                print(f"  Lines {start_line}-{end_line} ({end_line - start_line + 1} lines)")

                # Generate interlinear for THIS book only
                book_results = generator.generate_interlinear(book_id, start_line, end_line)

                # IMMEDIATELY write to both files - streaming!
                _write_book_to_txt(txt_file, book_num, book_results)
                _write_book_to_xml(xml_file, book_num, book_results)

                # Track progress
                total_lines += len(book_results)

                # book_results goes out of scope here - memory freed!
                percent_complete = idx / len(book_ids) * 100
                print(f"  ✓ Book {book_num} complete ({percent_complete:.1f}% total)")

            # Write XML footer once at end
            _write_xml_footer(xml_file)

        # Files are closed and flushed - guaranteed written to disk
        print(f"\n\n{'=' * 80}")
        print("COMPLETE!")
        print("=" * 80)
        print(f"Processed {len(book_ids)} books, {total_lines} lines")
        print(f"\nText output: {output_file}")
        print(f"XML output: {xml_output_file}")
        print("=" * 80)

    except Exception as e:
        # Clean up partial files on error
        if output_file.exists():
            output_file.unlink()
        if xml_output_file.exists():
            xml_output_file.unlink()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise so worker process reports failure
