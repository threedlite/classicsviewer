#!/usr/bin/env python3
"""
Generate line-by-line interlinear translation for Greek works

Uses the proper dictionary lookup implementation from ui_dictionary_lookup.py
to match the Android app's behavior exactly.
"""

import sqlite3
import re
from pathlib import Path
from typing import List, Dict
import html

# Import the proper dictionary lookup from ui_dictionary_lookup (same directory)
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

    def extract_gloss_from_entry(self, entry: DictionaryEntry) -> str:
        """
        Extract a simple English gloss from a DictionaryEntry.
        Returns the first reasonable definition text, truncated to 50 chars.
        """
        if not entry or not entry.definition:
            return "???"

        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', entry.definition)

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

                return gloss

        # Fallback: just take first 50 chars of cleaned text
        text = ' '.join(text.split())[:50]
        return text if text else "???"

    def lookup_word(self, word: str, book_id: str, line_number: int, position: int) -> Dict:
        """
        Lookup word using the proper dictionary lookup from ui_dictionary_lookup.py
        Returns a dict with greek, position, gloss, lemma, morph
        """
        # Use the proper PerseusRepository implementation to get all dictionary entries
        entries = self.repo.get_all_dictionary_entries(word, "greek")

        # Build result dict
        result = {
            'greek': word,
            'position': position,
            'gloss': None,
            'lemma': None,
            'morph': None
        }

        # Try each entry until we get a good gloss
        # Prioritize Wiktionary entries as they tend to have cleaner definitions
        if entries and len(entries) > 0:
            # First, try Wiktionary entries (skip cross-references)
            for entry in entries:
                if entry.source == 'wiktionary':
                    # Skip Wiktionary entries that are just cross-references
                    # Example: "Epic inflection of διίστημι ( 3:d aor actv indc)"
                    if entry.definition and 'inflection of' in entry.definition.lower():
                        continue  # Skip these, look for actual definitions

                    gloss = self.extract_gloss_from_entry(entry)
                    if gloss and gloss != "???" and len(gloss) > 2:
                        result['lemma'] = entry.lemma
                        result['morph'] = entry.morph_info
                        result['gloss'] = gloss
                        break

            # If no good Wiktionary entry, try other sources
            if not result['gloss']:
                for entry in entries[:5]:  # Try up to first 5 entries
                    gloss = self.extract_gloss_from_entry(entry)
                    # Check if gloss is valid (not just citations/references)
                    # Citations typically have patterns like "Α76, 83" or "α220, 301"
                    is_citation_only = bool(re.search(r'[Α-Ω][α-ω]?\d+', gloss))

                    if gloss and gloss != "???" and not is_citation_only and len(gloss) > 2:
                        result['lemma'] = entry.lemma
                        result['morph'] = entry.morph_info
                        result['gloss'] = gloss
                        break

            # If still no good gloss, use first entry's lemma at least
            if not result['gloss']:
                first_entry = entries[0]
                result['lemma'] = first_entry.lemma
                result['morph'] = first_entry.morph_info
                result['gloss'] = self.extract_gloss_from_entry(first_entry)

        # Fallback if no gloss found
        if not result['gloss'] or result['gloss'] == "???":
            result['gloss'] = "???"

        return result

    def generate_interlinear(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Main function to generate interlinear translation"""

        # Step 1: Get Greek text
        print(f"Extracting Greek lines {start_line}-{end_line}...")
        greek_lines = self.get_greek_lines(book_id, start_line, end_line)

        if not greek_lines:
            raise ValueError(f"No Greek text found for {book_id} lines {start_line}-{end_line}")

        print(f"Found {len(greek_lines)} Greek lines")

        # Step 2: Process each line
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
                word_data = self.lookup_word(token, book_id, line_num, pos)
                words.append(word_data)
                print(f"  [{pos}] {token} → {word_data['gloss']}")

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


def _generate_work(work_id: str, output_dir: Path):
    """Generate interlinear translation for a single work using TLG ID"""

    print("=" * 80)
    print(f"INTERLINEAR TRANSLATION GENERATOR")
    print("=" * 80)
    print(f"Work ID: {work_id}")
    print(f"Database: {DB_PATH}")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}")
        return

    # Get all books for this work
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    book_pattern = f"{work_id}.%"
    cursor.execute("SELECT DISTINCT book_id FROM text_lines WHERE book_id LIKE ? ORDER BY book_id", (book_pattern,))
    book_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not book_ids:
        print(f"\nERROR: No books found for work ID {work_id}")
        return

    print(f"\nFound {len(book_ids)} books to process")
    print("=" * 80)

    try:
        # Dictionary to store results by book
        all_results = {}

        with InterlinearGenerator(str(DB_PATH)) as generator:
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

                results = generator.generate_interlinear(book_id, start_line, end_line)
                all_results[book_num] = results

                percent_complete = idx / len(book_ids) * 100
                print(f"  ✓ Book {book_num} complete ({percent_complete:.1f}% total)")

        print("\n" + "=" * 80)
        print("WRITING OUTPUT FILES")
        print("=" * 80)

        # Generate output filenames from work_id
        txt_filename = f"{work_id}.interlinear.txt"
        xml_filename = f"{work_id}.perseus-eng99.xml"

        # Save to text file in pipe-delimited format
        output_file = output_dir / txt_filename
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

        # Get work metadata from database for XML
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT w.title_english, a.name
            FROM works w
            JOIN authors a ON w.author_id = a.id
            WHERE w.id = ?
        """, (work_id,))
        work_metadata = cursor.fetchone()
        conn.close()

        if work_metadata:
            work_title, author_name = work_metadata
        else:
            # Fallback to work_id if metadata not found
            work_title = work_id
            author_name = "Unknown"

        # Escape values for XML to prevent injection
        work_title_escaped = html.escape(work_title)
        author_name_escaped = html.escape(author_name)
        work_id_escaped = html.escape(work_id)

        # Save to XML file in Perseus format
        xml_output_file = output_dir / xml_filename
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

            # Write all books
            for book_num in sorted(all_results.keys()):
                f.write(f'                <div type="textpart" subtype="Book" n="{book_num}">\n')

                # Write each line in this book
                for line_data in all_results[book_num]:
                    line_num = line_data['line_number']

                    # Format each word as a Markdown table
                    word_tables = []
                    for w in line_data['words']:
                        greek = w['greek'] if w['greek'] else '???'
                        gloss = w['gloss'] if w['gloss'] else '???'
                        lemma = w['lemma'] if w['lemma'] else '?'
                        morph = w['morph'] if w['morph'] else ''

                        # Build lemma + morph line
                        if morph:
                            lemma_morph = f'{lemma} {morph}'
                        else:
                            lemma_morph = lemma

                        # Create Markdown table for this word
                        # Format: | greek | \n | **gloss** | \n | lemma morph |
                        table = f'| {greek} |\n| **{gloss}** |\n| {lemma_morph} |'
                        word_tables.append(table)

                    # Separate word tables with double space for visual separation
                    interlinear_text = '  '.join(word_tables)

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
