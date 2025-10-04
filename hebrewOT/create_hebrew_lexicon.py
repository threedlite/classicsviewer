#!/usr/bin/env python3
"""
Create Hebrew Lexicon ZIP for ClassicsViewer app import.

Generates:
- hebrew_dictionary.csv: BDB and Strong's dictionary entries
- hebrew_morphology.csv: Word form to lemma mappings
- hebrew_lexicon.zip: Package containing dictionary.csv and morphology.csv

CSV format matches custom_dictionary/ pattern for app import.
"""

import xml.etree.ElementTree as ET
import csv
import os
import zipfile
from collections import defaultdict
import re
import html

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_SOURCES = os.path.join(SCRIPT_DIR, '..', 'data-sources')
HEBREW_LEXICON_DIR = os.path.join(DATA_SOURCES, 'HebrewLexicon')
MORPHHB_DIR = os.path.join(DATA_SOURCES, 'morphhb', 'wlc')

# Output files
HEBREW_DICT_CSV = os.path.join(SCRIPT_DIR, 'hebrew_dictionary.csv')
HEBREW_MORPH_CSV = os.path.join(SCRIPT_DIR, 'hebrew_morphology.csv')
HEBREW_LEXICON_ZIP = os.path.join(SCRIPT_DIR, 'hebrew_lexicon.zip')

# XML namespaces
OSIS_NS = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
LEXICON_NS = {'': 'http://openscriptures.github.com/morphhb/namespace'}


def strip_html_tags(text):
    """Remove HTML tags from text, keeping content."""
    if not text:
        return ""
    # Replace <br/> with newline
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Remove other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = html.unescape(text)
    return text.strip()


def extract_text_recursive(element):
    """Extract all text content from an element and its children."""
    if element is None:
        return ""

    text_parts = []
    if element.text:
        text_parts.append(element.text)

    for child in element:
        text_parts.append(extract_text_recursive(child))
        if child.tail:
            text_parts.append(child.tail)

    return ' '.join(text_parts).strip()


def parse_strong_lexicon():
    """Parse HebrewStrong.xml to extract Strong's dictionary entries."""
    print("Parsing Strong's Hebrew Dictionary...")

    strong_file = os.path.join(HEBREW_LEXICON_DIR, 'HebrewStrong.xml')
    if not os.path.exists(strong_file):
        raise FileNotFoundError(f"HebrewStrong.xml not found at {strong_file}")

    tree = ET.parse(strong_file)
    root = tree.getroot()

    entries = []
    for entry in root.findall('.//entry', LEXICON_NS):
        entry_id = entry.get('id', '')

        # Extract Hebrew word
        w_elem = entry.find('.//w', LEXICON_NS)
        if w_elem is None:
            continue

        hebrew_word = w_elem.text or ''
        hebrew_word = hebrew_word.strip()

        # Extract definition
        meaning_elem = entry.find('.//meaning', LEXICON_NS)
        usage_elem = entry.find('.//usage', LEXICON_NS)

        definition_parts = []
        if meaning_elem is not None:
            meaning_text = extract_text_recursive(meaning_elem)
            if meaning_text:
                definition_parts.append(meaning_text)

        if usage_elem is not None:
            usage_text = extract_text_recursive(usage_elem)
            if usage_text:
                definition_parts.append(f"Usage: {usage_text}")

        definition = '; '.join(definition_parts) if definition_parts else ''

        if hebrew_word and definition:
            entries.append({
                'lemma': hebrew_word,
                'language': 'hebrew',
                'definition': definition,
                'html_definition': '',
                'source_name': f"Strong's {entry_id}"
            })

    print(f"  Extracted {len(entries)} Strong's entries")
    return entries


def parse_bdb_lexicon():
    """Parse BrownDriverBriggs.xml to extract BDB dictionary entries."""
    print("Parsing Brown-Driver-Briggs Lexicon...")

    bdb_file = os.path.join(HEBREW_LEXICON_DIR, 'BrownDriverBriggs.xml')
    if not os.path.exists(bdb_file):
        raise FileNotFoundError(f"BrownDriverBriggs.xml not found at {bdb_file}")

    tree = ET.parse(bdb_file)
    root = tree.getroot()

    entries = []
    for entry in root.findall('.//entry', LEXICON_NS):
        entry_id = entry.get('id', '')

        # Extract Hebrew word
        w_elem = entry.find('.//w', LEXICON_NS)
        if w_elem is None:
            continue

        hebrew_word = w_elem.text or ''
        hebrew_word = hebrew_word.strip()

        # Extract definition (concatenate all text)
        definition_text = extract_text_recursive(entry)

        # Clean up definition - remove the Hebrew word from the beginning
        if definition_text.startswith(hebrew_word):
            definition_text = definition_text[len(hebrew_word):].strip()

        # Limit definition length (BDB entries can be very long)
        if len(definition_text) > 500:
            definition_text = definition_text[:497] + '...'

        if hebrew_word and definition_text:
            entries.append({
                'lemma': hebrew_word,
                'language': 'hebrew',
                'definition': definition_text,
                'html_definition': '',
                'source_name': f"BDB ({entry_id})"
            })

    print(f"  Extracted {len(entries)} BDB entries")
    return entries


def parse_morphhb_morphology():
    """Parse morphhb OSIS XML files to extract word→lemma morphology mappings."""
    print("Parsing morphhb OSIS files for morphology...")

    if not os.path.exists(MORPHHB_DIR):
        raise FileNotFoundError(f"morphhb wlc directory not found at {MORPHHB_DIR}")

    # Use a dict to deduplicate word forms (many repetitions across Bible)
    morphology_map = {}

    # Get all XML files in the wlc directory
    xml_files = [f for f in os.listdir(MORPHHB_DIR) if f.endswith('.xml')]

    for xml_file in sorted(xml_files):
        file_path = os.path.join(MORPHHB_DIR, xml_file)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find all <w> elements (word elements)
            for w_elem in root.findall('.//osis:w', OSIS_NS):
                word_text = w_elem.text or ''
                word_text = word_text.strip()

                # Remove slashes from compound words (like "בְּ/רֵאשִׁ֖ית" → "בְּרֵאשִׁ֖ית")
                word_clean = word_text.replace('/', '')

                # Get lemma and morph attributes
                lemma = w_elem.get('lemma', '')
                morph = w_elem.get('morph', '')

                if not word_clean or not lemma:
                    continue

                # Parse lemma - format is like "b/7225" or "1254 a"
                # Extract the base lemma (ignore prefixes and suffixes)
                lemma_parts = lemma.split('/')
                base_lemma = lemma_parts[-1] if lemma_parts else lemma
                base_lemma = base_lemma.strip()

                # Parse morphology code
                morph_info = parse_morph_code(morph)

                # Store unique word form → lemma mapping
                # Use word_clean as key to deduplicate
                if word_clean not in morphology_map:
                    morphology_map[word_clean] = {
                        'word_form': word_clean,
                        'lemma': base_lemma,
                        'morph_info': morph_info,
                        'language': 'hebrew',
                        'confidence': 1.0,
                        'source_name': 'OSHB morphhb'
                    }

        except ET.ParseError as e:
            print(f"  Warning: Could not parse {xml_file}: {e}")
            continue

    print(f"  Extracted {len(morphology_map)} unique word forms")
    return list(morphology_map.values())


def parse_morph_code(morph):
    """Parse morphology code into human-readable description."""
    if not morph:
        return ""

    # morphhb uses codes like "HVqp3ms" where:
    # H = Hebrew
    # V = Verb, N = Noun, A = Adjective, etc.
    # Rest is grammatical info

    # Simple parsing - just return the code as-is for now
    # A complete parser would decode: stem, tense, person, number, gender, state, etc.
    return morph


def write_dictionary_csv(entries, output_file):
    """Write dictionary entries to CSV file."""
    print(f"Writing dictionary CSV to {output_file}...")

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['lemma', 'language', 'definition', 'html_definition', 'source_name'])
        writer.writeheader()
        writer.writerows(entries)

    print(f"  Wrote {len(entries)} entries")


def write_morphology_csv(entries, output_file):
    """Write morphology mappings to CSV file."""
    print(f"Writing morphology CSV to {output_file}...")

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['word_form', 'lemma', 'morph_info', 'language', 'confidence', 'source_name'])
        writer.writeheader()
        writer.writerows(entries)

    print(f"  Wrote {len(entries)} morphology entries")


def create_lexicon_zip():
    """Package dictionary.csv, morphology.csv, and normalization_rules.csv into hebrew_lexicon.zip."""
    print(f"\nPackaging into {HEBREW_LEXICON_ZIP}...")

    # Create temporary renamed copies
    dict_temp = os.path.join(SCRIPT_DIR, 'dictionary.csv')
    morph_temp = os.path.join(SCRIPT_DIR, 'morphology.csv')

    # Copy with correct names
    import shutil
    shutil.copy(HEBREW_DICT_CSV, dict_temp)
    shutil.copy(HEBREW_MORPH_CSV, morph_temp)

    # Check for normalization rules
    norm_rules = os.path.join(SCRIPT_DIR, 'normalization_rules_hebrew.csv')
    norm_temp = os.path.join(SCRIPT_DIR, 'normalization_rules.csv')
    has_norm_rules = os.path.exists(norm_rules)

    if has_norm_rules:
        shutil.copy(norm_rules, norm_temp)
        print(f"  Including normalization rules for Hebrew")

    # Create ZIP file
    with zipfile.ZipFile(HEBREW_LEXICON_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(dict_temp, 'dictionary.csv')
        zipf.write(morph_temp, 'morphology.csv')
        if has_norm_rules:
            zipf.write(norm_temp, 'normalization_rules.csv')

    # Clean up temporary files
    os.remove(dict_temp)
    os.remove(morph_temp)
    if has_norm_rules:
        os.remove(norm_temp)

    # Verify ZIP
    with zipfile.ZipFile(HEBREW_LEXICON_ZIP, 'r') as zipf:
        file_list = zipf.namelist()
        print(f"  ZIP contains: {file_list}")

        if 'dictionary.csv' not in file_list or 'morphology.csv' not in file_list:
            raise ValueError("ZIP file missing required CSVs")

    # Get file size
    zip_size_mb = os.path.getsize(HEBREW_LEXICON_ZIP) / (1024 * 1024)
    print(f"  Created hebrew_lexicon.zip ({zip_size_mb:.2f} MB)")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Hebrew Lexicon Generator for ClassicsViewer")
    print("=" * 60)

    # Step 1: Parse Strong's Dictionary
    strong_entries = parse_strong_lexicon()

    # Step 2: Parse BDB Lexicon
    bdb_entries = parse_bdb_lexicon()

    # Step 3: Combine dictionary entries
    all_dict_entries = strong_entries + bdb_entries
    print(f"\nTotal dictionary entries: {len(all_dict_entries)}")

    # Step 4: Parse morphhb for morphology
    morphology_entries = parse_morphhb_morphology()

    # Step 5: Write CSVs
    write_dictionary_csv(all_dict_entries, HEBREW_DICT_CSV)
    write_morphology_csv(morphology_entries, HEBREW_MORPH_CSV)

    # Step 6: Create ZIP package
    create_lexicon_zip()

    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"Created files:")
    print(f"  - {HEBREW_DICT_CSV}")
    print(f"  - {HEBREW_MORPH_CSV}")
    print(f"  - {HEBREW_LEXICON_ZIP}")
    print("\nPackage includes:")
    print("  ✓ dictionary.csv (BDB + Strong's)")
    print("  ✓ morphology.csv (word → lemma mappings)")
    print("  ✓ normalization_rules.csv (removes nikud, normalizes final forms)")
    print("\nTo use:")
    print("  1. Import hebrew_lexicon.zip via ClassicsViewer app")
    print("  2. Lexicon data will populate dictionary_entries and lemma_map tables")
    print("  3. Normalization rules enable matching vocalized Hebrew text")


if __name__ == '__main__':
    main()
