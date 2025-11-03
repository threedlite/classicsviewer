#!/usr/bin/env python3
"""
Generate line-by-line interlinear translation for Homer's Iliad (all 24 books)

Uses:
- Greek text from database
- Dictionary entries for word-by-word glosses
- Murray translation for literary context
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Database path
DB_PATH = Path(__file__).parent.parent / "data-prep" / "perseus_texts_sample.db"

TRANSLATION_LANG = "Augustus Taber Murray"  # Murray translation


class InterlinearGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

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

    def get_murray_translation(self, book_id: str, start_line: int, end_line: int) -> Optional[str]:
        """Extract Murray translation segment"""
        cursor = self.conn.cursor()

        # First check translation_lookup table
        query = """
        SELECT DISTINCT ts.translation_text
        FROM translation_segments ts
        JOIN translation_lookup tl ON tl.segment_id = ts.id
        WHERE tl.book_id = ?
        AND ts.translator = ?
        AND tl.line_number BETWEEN ? AND ?
        ORDER BY ts.start_line
        """
        cursor.execute(query, (book_id, TRANSLATION_LANG, start_line, end_line))
        results = cursor.fetchall()

        if results:
            # Combine all matching segments
            return ' '.join([row['translation_text'] for row in results])

        # Fallback to range-based lookup
        query = """
        SELECT translation_text
        FROM translation_segments
        WHERE book_id = ?
        AND translator = ?
        AND start_line <= ?
        AND (end_line >= ? OR end_line IS NULL)
        ORDER BY start_line
        """
        cursor.execute(query, (book_id, TRANSLATION_LANG, end_line, start_line))
        results = cursor.fetchall()

        if results:
            return ' '.join([row['translation_text'] for row in results])

        return None

    def tokenize_greek(self, text: str) -> List[str]:
        """Simple Greek tokenization - split on whitespace and remove punctuation"""
        # Remove common punctuation but keep Greek text
        text = re.sub(r'[,;·.?!—\[\]():]', ' ', text)
        tokens = text.split()
        return [t.strip() for t in tokens if t.strip()]

    def normalize_greek(self, word: str) -> str:
        """Normalize Greek word - remove diacritics for lookup"""
        # This is simplified - the database has more sophisticated normalization
        import unicodedata
        # Remove combining diacritics
        normalized = unicodedata.normalize('NFD', word)
        # Filter out combining characters
        without_diacritics = ''.join(c for c in normalized if not unicodedata.combining(c))
        return unicodedata.normalize('NFC', without_diacritics).lower()

    def has_greek_chars(self, text: str) -> bool:
        """Check if text contains Greek characters"""
        # Greek Unicode range: 0x0370-0x03FF (Greek and Coptic), 0x1F00-0x1FFF (Greek Extended)
        return any(('\u0370' <= c <= '\u03FF') or ('\u1F00' <= c <= '\u1FFF') for c in text)

    def extract_english_gloss(self, entry_text: str, original_word: str = "") -> tuple:
        """
        Extract clean English gloss from dictionary entry
        Returns (gloss, pattern_priority) where pattern_priority is 0-3 (lower is better)
        original_word: the Greek word being looked up (for particle detection)
        """
        if not entry_text:
            return None, None

        # Skip etymolog-only entries
        if entry_text.strip().startswith('Etymology:') and '\n' not in entry_text:
            return None, None

        # Look for numbered definitions: "0. word" "I. word" "1. word" "A. word" ": word"
        patterns = [
            r'^:\s+([^\n]+)',                # Priority 0 - simple colon (e.g., ": I, me, my")
            r'(?:^|\n)A\.\s+([^\n]+)',      # Priority 1 - LSJ primary definition
            r'(?:^|\n)0\.\s+([^\n]+)',      # Priority 2
            r'(?:^|\n)I\.\s+([^\n]+)',      # Priority 3
            r'(?:^|\n)1\.\s+([^\n]+)',      # Priority 4
            r'^([^:\n]+)$',                  # Priority 5 - plain text entry (e.g., "than, as")
        ]

        for pattern_priority, pattern in enumerate(patterns):
            match = re.search(pattern, entry_text)
            if match:
                gloss = match.group(1).strip()

                # Take before semicolon (but not colon, as ": word" is a valid pattern)
                gloss = gloss.split(';')[0].strip()

                # Check if gloss has context markers like "(Od.)" or "(Il.)" before removing parens
                # These indicate context-specific meanings, should be lower priority
                has_context_marker = bool(re.search(r'\([A-Z][a-z]+\.\)', gloss))

                # Remove parentheticals
                gloss = re.sub(r'\s*\([^)]+\)', '', gloss)

                # Remove prefixes: "a. ", "1. ", "I. ", "II. ", "III. ", "IV. ", etc.
                # Match: single letter, digits, or Roman numerals followed by period and space
                gloss = re.sub(r'^(?:[a-zA-Z]|\d+|[IVX]+)\.\s+', '', gloss)

                # Skip if the result is just a marker/abbreviation (like "Trans.", "II.", "III.")
                # These are section headers, not actual glosses
                if re.match(r'^(?:[IVX]+|Trans|Mid|Act|Pass|Intrans)\.?$', gloss):
                    continue

                # Skip if the result is just a grammatical category (e.g., "verb", "noun", "adjective")
                # These are Wiktionary form-of entries, not actual definitions
                if re.match(r'^(?:verb|noun|adjective|adverb|pronoun|particle|preposition|conjunction)s?$', gloss, re.IGNORECASE):
                    continue

                # Skip if the result is just a dialect/style marker (e.g., "Epic", "Ionic", "Doric")
                # These are Wiktionary alternative-form markers, not actual definitions
                if re.match(r'^(?:Epic|Ionic|Doric|Attic|Aeolic|Homeric)$', gloss):
                    continue

                # Skip if contains grammatical junk or abbreviations
                # Use word boundaries to avoid false matches like "Adversative" containing "Adv."
                junk_patterns = [r'\baor\.', r'\bmid\.', r'\bsing\.', r'\bpl\.', r'\bimpf\.', r'\bpres\.',
                               r'\bDat\.', r'\bNom\.', r'\bGen\.', r'\bAcc\.', r'\bVoc\.', r'\bdual\b', r'\bpple\b',
                               r'\bprae\.', r'\bAdv\.', r'\bPrep\.', r'With dat\.', r'With acc\.', r'\bAbsol\.']
                if any(re.search(pattern, gloss) for pattern in junk_patterns):
                    continue

                # Skip if starts with or equals common Latin words (dictionary has Latin glosses)
                latin_words = ['alius', 'alia', 'alium', 'alter', 'quis', 'qui', 'quae', 'nego', 'nolo']
                if any(gloss.lower().startswith(latin) for latin in latin_words):
                    continue

                # Skip standalone Latin words that are glosses
                if gloss.lower() in ['ego', 'mihi', 'tibi', 'nobis', 'vobis']:
                    continue

                # Skip overly abstract/meta glosses (these are usually bad dictionary entries)
                abstract_words = ['exactness', 'definiteness', 'precision', 'accuracy']
                if gloss.lower() in abstract_words:
                    continue

                # Skip verb forms when we need particles (δέ should be "but" not "to withhold")
                # Strip elision for length check
                word_stripped = original_word.replace('ʼ', '').replace("'", '') if original_word else ""
                if len(word_stripped) <= 3 and gloss.startswith('to '):
                    # Short words like δέ, τε are particles, not verbs
                    continue

                # Skip if has Greek characters
                if self.has_greek_chars(gloss):
                    continue

                # Handle comma-separated glosses
                # Skip grammatical descriptions like "Adversative particle, but" to get "but"
                # But keep standalone descriptions like "Temporal particle."
                if ',' in gloss and len(gloss) > 15:  # Only split if gloss is verbose
                    parts = [p.strip() for p in gloss.split(',')]
                    # Skip parts that are grammatical descriptions
                    gram_descriptions = ['particle', 'adverb', 'preposition', 'conjunction', 'pronoun', 'article']
                    found_non_gram = False
                    for part in parts:
                        # Skip if it's a grammatical description
                        if any(desc in part.lower() for desc in gram_descriptions):
                            continue
                        # Use this part if it's short and simple
                        if 2 < len(part) < 30:
                            gloss = part
                            found_non_gram = True
                            break
                    # If all parts were grammatical, keep original (e.g., "Temporal particle.")
                    # Otherwise we've updated gloss above

                # Skip if too long (probably not a good gloss)
                if len(gloss) > 30:
                    continue

                # Lowercase first letter if it starts with "A " or "An " (articles)
                if gloss.startswith('A ') or gloss.startswith('An '):
                    gloss = gloss[0].lower() + gloss[1:]

                # Check if reasonable length
                if 2 < len(gloss) < 60:
                    # Penalize context-specific glosses
                    effective_priority = pattern_priority + (50 if has_context_marker else 0)
                    return gloss, effective_priority

        return None, None

    def lookup_word(self, word: str, book_id: str, line_number: int, position: int, murray_text: str = "") -> Dict:
        """Lookup word in database - get lemma, definition, morphology"""
        cursor = self.conn.cursor()

        result = {
            'greek': word,
            'position': position,
            'gloss': None,
            'lemma': None,
            'morph': None
        }

        # Strip elision mark (ʼ) if present for lookup (like the app does)
        word_for_lookup = word.replace('ʼ', '').replace("'", '')

        # Look up ALL possible lemmas for this word form
        query = """
        SELECT DISTINCT lemma
        FROM lemma_map
        WHERE word_form = ?
        """
        cursor.execute(query, (word_for_lookup,))
        lemma_results = cursor.fetchall()

        if lemma_results:
            murray_lower = murray_text.lower() if murray_text else ""
            best_gloss = None
            best_lemma = None
            best_score = 999999

            # Try each possible lemma
            for lemma_row in lemma_results:
                lemma = lemma_row['lemma']

                # Get dictionary definition for this lemma (may have multiple entries)
                query = """
                SELECT entry_plain
                FROM dictionary_entries
                WHERE headword = ? AND language = 'greek'
                """
                cursor.execute(query, (lemma,))
                dict_results = cursor.fetchall()

                # Try each dictionary entry for this lemma
                for dict_row in dict_results:
                    if dict_row['entry_plain']:
                        gloss, pattern_priority = self.extract_english_gloss(dict_row['entry_plain'], word)
                        if gloss:
                            # Score by: pattern priority (0-3), length, Murray match
                            # Lower score is better
                            score = pattern_priority * 100 + len(gloss)

                            # Boost common particles when lemma matches word (normalize accents)
                            lemma_normalized = self.normalize_greek(lemma)
                            word_normalized = self.normalize_greek(word_for_lookup)
                            if lemma_normalized == word_normalized and len(word_for_lookup) <= 4:
                                score = score / 100  # Massive preference for exact particle match

                            # If gloss appears in Murray, heavily favor it
                            if murray_lower and gloss.lower() in murray_lower:
                                score = score / 10  # Massive preference for Murray words
                            if score < best_score:
                                best_gloss = gloss
                                best_lemma = lemma
                                best_score = score

            if best_gloss:
                # Limit to reasonable length for display
                if len(best_gloss) > 50:
                    best_gloss = best_gloss[:47] + '...'
                result['gloss'] = best_gloss
                result['lemma'] = best_lemma

                # Get morphology for this lemma+word combination
                query = """
                SELECT morph_info
                FROM lemma_map
                WHERE word_form = ? AND lemma = ? AND morph_info IS NOT NULL AND morph_info != ''
                LIMIT 1
                """
                cursor.execute(query, (word_for_lookup, best_lemma))
                morph_row = cursor.fetchone()
                if morph_row:
                    result['morph'] = morph_row['morph_info']

        # If no gloss found yet, try normalized lookup (with elision stripped)
        if not result['gloss']:
            normalized = self.normalize_greek(word_for_lookup)
            query = """
            SELECT DISTINCT lemma
            FROM lemma_map
            WHERE word_form_normalized_ultra = ?
            """
            cursor.execute(query, (normalized,))
            lemma_results = cursor.fetchall()

            if lemma_results:
                murray_lower = murray_text.lower() if murray_text else ""
                best_gloss = None
                best_score = 999999

                # Try each possible lemma
                for lemma_row in lemma_results:
                    lemma = lemma_row['lemma']

                    # Get dictionary definition (may have multiple entries)
                    query = """
                    SELECT entry_plain
                    FROM dictionary_entries
                    WHERE headword = ? AND language = 'greek'
                    """
                    cursor.execute(query, (lemma,))
                    dict_results = cursor.fetchall()

                    # Try each dictionary entry
                    for dict_row in dict_results:
                        if dict_row['entry_plain']:
                            gloss, pattern_priority = self.extract_english_gloss(dict_row['entry_plain'], word)
                            if gloss:
                                # Score by pattern priority, length, and Murray match
                                score = pattern_priority * 100 + len(gloss)
                                if murray_lower and gloss.lower() in murray_lower:
                                    score = score / 10
                                if score < best_score:
                                    best_gloss = gloss
                                    best_score = score

                if best_gloss:
                    if len(best_gloss) > 50:
                        best_gloss = best_gloss[:47] + '...'
                    result['gloss'] = best_gloss

        # Final fallback: use placeholder for missing gloss
        if not result['gloss']:
            result['gloss'] = "???"

        return result

    def split_sentences(self, text: str) -> List[str]:
        """Split English text into sentences"""
        # Simple sentence splitting - can be improved with NLTK
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def calculate_alignment_score(self, sentence: str, word_glosses: List[str], line_lemmas: List[str]) -> float:
        """
        Calculate how well a sentence aligns with a Greek line
        Based on vocabulary overlap
        """
        sentence_lower = sentence.lower()

        # Filter out None values before processing
        valid_glosses = [g for g in word_glosses if g]
        valid_lemmas = [l for l in line_lemmas if l]

        # Count how many glosses appear in sentence
        gloss_matches = sum(1 for gloss in valid_glosses if gloss.lower() in sentence_lower)

        # Count how many lemmas appear in sentence (transliterated)
        lemma_matches = sum(1 for lemma in valid_lemmas if self.normalize_greek(lemma) in sentence_lower)

        total_words = len(word_glosses)
        if total_words == 0:
            return 0.0

        # Weight gloss matches more heavily
        score = (gloss_matches * 2.0 + lemma_matches * 1.0) / (total_words * 3.0)
        return min(score, 1.0)

    def align_sentences_to_lines(self, sentences: List[str], lines_data: List[Dict]) -> Dict[int, str]:
        """
        Align Murray sentences to Greek lines based on vocabulary matching
        Returns dict mapping line_number -> sentence
        """
        alignment = {}
        used_sentences = set()

        for line_data in lines_data:
            line_num = line_data['line_number']
            word_glosses = [w['gloss'] for w in line_data['words']]
            line_lemmas = [w['lemma'] for w in line_data['words']]

            best_score = 0.0
            best_sentence = None
            best_idx = -1

            for idx, sentence in enumerate(sentences):
                if idx in used_sentences:
                    continue

                score = self.calculate_alignment_score(sentence, word_glosses, line_lemmas)
                if score > best_score:
                    best_score = score
                    best_sentence = sentence
                    best_idx = idx

            if best_sentence:
                alignment[line_num] = best_sentence
                used_sentences.add(best_idx)
            else:
                # Fallback: use first unused sentence
                for idx, sentence in enumerate(sentences):
                    if idx not in used_sentences:
                        alignment[line_num] = sentence
                        used_sentences.add(idx)
                        break

        return alignment

    def generate_interlinear(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Main function to generate interlinear translation"""

        # Step 1: Get Greek text
        print(f"Extracting Greek lines {start_line}-{end_line}...")
        greek_lines = self.get_greek_lines(book_id, start_line, end_line)

        if not greek_lines:
            raise ValueError(f"No Greek text found for {book_id} lines {start_line}-{end_line}")

        print(f"Found {len(greek_lines)} Greek lines")

        # Step 2: Get Murray translation
        print(f"Extracting Murray translation...")
        murray_text = self.get_murray_translation(book_id, start_line, end_line)

        if not murray_text:
            print("WARNING: No Murray translation found")
            murray_text = ""
        else:
            print(f"Murray text: {murray_text[:100]}...")

        # Step 3: Process each line
        print(f"\nProcessing lines and generating glosses...")
        lines_data = []

        for line in greek_lines:
            line_num = line['line_number']
            text = line['text_content']

            print(f"\nLine {line_num}: {text}")

            # Tokenize
            tokens = self.tokenize_greek(text)

            # Lookup each word
            words = []
            for pos, token in enumerate(tokens, 1):
                word_data = self.lookup_word(token, book_id, line_num, pos, murray_text)
                words.append(word_data)
                print(f"  [{pos}] {token} → {word_data['gloss']}")

            # Create word-by-word gloss (should never be None now due to fallbacks)
            word_gloss = ' '.join([w['gloss'] if w['gloss'] else '???' for w in words])

            lines_data.append({
                'line_number': line_num,
                'greek_text': text,
                'words': words,
                'word_gloss': word_gloss
            })

        # Note: Murray translation is range-based (lines 1-30 in one segment)
        # Cannot split reliably into individual line translations
        # So we omit the literary_translation field
        print(f"\n\nNote: Murray translation is range-based, not line-by-line")
        print(f"Translation segment covers lines 1-30 as a single paragraph")

        return lines_data


def main():
    """Generate interlinear translation for all 24 books of the Iliad"""

    print("=" * 80)
    print("ILIAD INTERLINEAR TRANSLATION GENERATOR")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Translation: {TRANSLATION_LANG} (Murray)")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}")
        print("Please ensure perseus_texts_sample.db exists")
        return

    # Get all Iliad books
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT book_id FROM text_lines WHERE book_id LIKE 'tlg0012.tlg001.%' ORDER BY book_id")
    book_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"\nFound {len(book_ids)} books to process")
    print("=" * 80)

    try:
        # Dictionary to store results by book
        all_results = {}

        with InterlinearGenerator(str(DB_PATH)) as generator:
            for idx, book_id in enumerate(book_ids, 1):
                book_num = int(book_id.split('.')[-1])
                print(f"\n[{idx}/{len(book_ids)}] Processing Book {book_num}...")

                # Get line range for this book
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                cursor.execute("SELECT MIN(line_number), MAX(line_number) FROM text_lines WHERE book_id = ?", (book_id,))
                start_line, end_line = cursor.fetchone()
                conn.close()

                print(f"  Lines {start_line}-{end_line} ({end_line - start_line + 1} lines)")

                results = generator.generate_interlinear(book_id, start_line, end_line)
                all_results[book_num] = results

                print(f"  ✓ Book {book_num} complete")

        print("\n" + "=" * 80)
        print("WRITING OUTPUT FILES")
        print("=" * 80)

        # Save to text file in pipe-delimited format
        output_file = Path(__file__).parent / "iliad_full_interlinear.txt"
        print(f"\nWriting text file: {output_file.name}")
        with open(output_file, 'w', encoding='utf-8') as f:
            for book_num in sorted(all_results.keys()):
                f.write(f"\n{'=' * 80}\n")
                f.write(f"BOOK {book_num}\n")
                f.write(f"{'=' * 80}\n\n")

                for line_data in all_results[book_num]:
                    line_num = line_data['line_number']

                    # Get Greek words
                    greek_words = [w['greek'] for w in line_data['words']]

                    # Get glosses
                    glosses = [w['gloss'] for w in line_data['words']]

                    # Write line number and Greek words separated by pipes
                    f.write(f"{line_num}. {' | '.join(greek_words)}\n")

                    # Write glosses separated by pipes
                    f.write(f"{' | '.join(glosses)}\n")

                    # Blank line between entries
                    f.write("\n")

        # Save to XML file in Perseus format (matching eng3 structure)
        xml_output_file = Path(__file__).parent / "tlg0012.tlg001.perseus-eng99.xml"
        print(f"Writing XML file: {xml_output_file.name}")
        with open(xml_output_file, 'w', encoding='utf-8') as f:
            # Write XML header
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<?xml-model href="http://www.stoa.org/epidoc/schema/8.19/tei-epidoc.rng"\n')
            f.write('  schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
            f.write('<TEI xmlns="http://www.tei-c.org/ns/1.0">\n')
            f.write('    <teiHeader>\n')
            f.write('        <fileDesc>\n')
            f.write('            <titleStmt>\n')
            f.write('                <title>Iliad</title>\n')
            f.write('                <author>Homer</author>\n')
            f.write('                <editor role="translator">Interlinear (AI-generated from app dictionary and translations)</editor>\n')
            f.write('                <sponsor>Derived from LSJ, Murray, Cunliffe, Wikitionary, Perseus</sponsor>\n')
            f.write('                <principal></principal>\n')
            f.write('                <respStmt>\n')
            f.write('                    <resp>AI-generated interlinear translation</resp>\n')
            f.write('                    <name>Claude Code</name>\n')
            f.write('                </respStmt>\n')
            f.write('            </titleStmt>\n')
            f.write('            <extent>about 1.8Mb</extent>\n')
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
            f.write('                        <author>Homer</author>\n')
            f.write('                        <title>The Iliad</title>\n')
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
            f.write('            <change when="20251103" who="Claude Code">Generated interlinear translation.</change>\n')
            f.write('        </revisionDesc>\n')
            f.write('    </teiHeader>\n')
            f.write('    <text xml:lang="eng">\n')
            f.write('        <body>\n')
            f.write('            <div type="translation" n="urn:cts:greekLit:tlg0012.tlg001.perseus-eng99" xml:lang="eng">\n')

            # Write all books
            for book_num in sorted(all_results.keys()):
                f.write(f'                <div type="textpart" subtype="Book" n="{book_num}">\n')

                # Write each line in this book
                for line_data in all_results[book_num]:
                    line_num = line_data['line_number']

                    # Format each word as: <hi rend="bold">gloss</hi> (lemma, morph)
                    word_parts = []
                    for w in line_data['words']:
                        gloss = w['gloss'] if w['gloss'] else '???'
                        lemma = w['lemma'] if w['lemma'] else '?'
                        morph = w['morph'] if w['morph'] else ''

                        if morph:
                            word_parts.append(f'<hi rend="bold">{gloss}</hi> ({lemma}, {morph})')
                        else:
                            word_parts.append(f'<hi rend="bold">{gloss}</hi> ({lemma})')

                    interlinear_text = ' | '.join(word_parts)

                    f.write(f'                    <l n="{line_num}">{interlinear_text}</l>\n')

                f.write('                </div>\n')

            f.write('            </div>\n')
            f.write('        </body>\n')
            f.write('    </text>\n')
            f.write('</TEI>\n')

        # Count total lines processed
        total_lines = sum(len(results) for results in all_results.values())

        print(f"\n\n{'=' * 80}")
        print("COMPLETE!")
        print("=" * 80)
        print(f"Processed {len(all_results)} books, {total_lines} lines")
        print(f"\nText output: {output_file}")
        print(f"XML output: {xml_output_file}")
        print("=" * 80)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
