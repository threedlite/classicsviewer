#!/usr/bin/env python3
"""
Create Arabic Lexicon ZIP for ClassicsViewer app import.

Generates:
- arabic_dictionary.csv: Lane's Lexicon dictionary entries
- arabic_lexicon.zip: Package containing dictionary.csv and normalization_rules.csv

CSV format matches custom_dictionary/ pattern for app import.
Based on Hebrew lexicon creation (hebrewOT/create_hebrew_lexicon.py)
"""

import xml.etree.ElementTree as ET
import csv
import os
import re
import zipfile
import shutil
from pathlib import Path
from html import escape
from camel_tools.utils.transliterate import Transliterator
from camel_tools.utils.charmap import CharMapper

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data-sources" / "arabic_text_perseus" / "Lane" / "opensource"

# Output files (all in arabic folder)
ARABIC_DICT_CSV = SCRIPT_DIR / "arabic_dictionary.csv"
ARABIC_LEXICON_ZIP = SCRIPT_DIR / "arabic_lexicon.zip"
NORM_RULES_SOURCE = SCRIPT_DIR.parent / "custom_dictionary" / "normalization_rules_arabic.csv"

# Initialize Buckwalter transliterator (Buckwalter → Arabic)
bw2ar_transliterator = Transliterator(CharMapper.builtin_mapper('bw2ar'))

def load_normalization_rules():
    """Load normalization rules from CSV file"""
    rules = []
    with open(NORM_RULES_SOURCE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['language'] == 'arabic':
                rules.append({
                    'pattern': row['pattern'],
                    'replacement': row['replacement'],
                    'priority': int(row['priority'])
                })
    # Sort by priority
    rules.sort(key=lambda x: x['priority'])
    return rules

# Load normalization rules once
NORMALIZATION_RULES = load_normalization_rules()

def normalize_arabic(text):
    """
    Apply normalization rules from normalization_rules_arabic.csv
    This ensures the script uses the EXACT same normalization as the app
    """
    if not text:
        return ""

    # Apply each rule in priority order
    for rule in NORMALIZATION_RULES:
        text = re.sub(rule['pattern'], rule['replacement'], text)

    return text

def clean_text(text):
    """Remove extra whitespace and clean text"""
    if not text:
        return ""
    # Replace multiple spaces/newlines with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def lane_transliteration_to_arabic(lane_text):
    """
    Convert Lane's custom transliteration to normalized Arabic
    Lane uses a variant of Buckwalter with special characters
    We'll try to convert it and then normalize
    """
    if not lane_text:
        return ""

    # Lane's transliteration has some special markers:
    # ~ = shadda (doubling)
    # ^ = superscript
    # _ = subscript
    # = = macron (long vowel)
    # ' = hamza

    # Try to convert common Lane patterns to Buckwalter
    text = lane_text

    # Convert Lane's special characters to closest Buckwalter equivalents
    text = text.replace('^a', 'َ')  # fatha
    text = text.replace('^u', 'ُ')  # damma
    text = text.replace('^i', 'ِ')  # kasra
    text = text.replace('~', 'ّ')   # shadda
    text = text.replace('=', 'ا')   # alif (long a)
    text = text.replace("'", 'ء')   # hamza
    text = text.replace('_', '')    # remove subscript markers

    # Try Buckwalter transliteration
    try:
        arabic = bw2ar_transliterator.transliterate(text)
        # Normalize the result
        return normalize_arabic(arabic)
    except:
        # If transliteration fails, return empty string
        return ""

def extract_arabic_text(element):
    """Extract Arabic text from foreign lang='ar' tags"""
    arabic_parts = []
    for foreign in element.findall(".//foreign[@lang='ar']"):
        if foreign.text:
            arabic_parts.append(foreign.text.strip())
    return ", ".join(arabic_parts) if arabic_parts else None

def extract_definition_text(entry):
    """Extract plain text definition from entry, removing XML tags"""
    # Get all text content from the entry
    def get_all_text(elem):
        text = elem.text or ""
        for child in elem:
            text += get_all_text(child)
            text += child.tail or ""
        return text

    text = get_all_text(entry)
    # Clean up the text
    text = clean_text(text)
    # Limit length to avoid extremely long entries
    if len(text) > 500:
        text = text[:497] + "..."
    return text

def extract_definition_html(entry):
    """
    Extract HTML formatted definition from entry
    Keep basic formatting like italics, but simplify structure
    """
    def elem_to_html(elem):
        """Convert XML element to HTML recursively"""
        html = ""

        # Add opening text
        if elem.text:
            html += escape(elem.text)

        # Process children
        for child in elem:
            tag_name = child.tag.lower()

            # Convert TEI tags to HTML
            if tag_name == 'hi' and child.get('rend') == 'ital':
                html += f"<i>{elem_to_html(child)}</i>"
            elif tag_name == 'foreign' and child.get('lang') == 'ar':
                # Keep Arabic in special span
                html += f"<span class='arabic'>{escape(child.text or '')}</span>"
            else:
                # Recursively process other elements
                html += elem_to_html(child)

            # Add tail text
            if child.tail:
                html += escape(child.tail)

        return html

    html_content = elem_to_html(entry)
    html_content = clean_text(html_content)

    # Limit length
    if len(html_content) > 500:
        html_content = html_content[:497] + "..."

    return f"<div>{html_content}</div>"

def parse_lane_xml_file(xml_file):
    """Parse a single Lane's Lexicon XML file and extract entries"""
    entries = []

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find all entryFree elements (dictionary entries)
        for entry in root.findall(".//entryFree[@type='main']"):
            # Extract headword from orth tag with lang='ar'
            headword_transliterated = None
            for orth in entry.findall(".//orth[@lang='ar']"):
                if orth.text and orth.text != '*':
                    headword_transliterated = orth.text.strip()
                    break

            # Skip if no valid headword
            if not headword_transliterated:
                continue

            # Convert Lane's transliteration to normalized Arabic
            headword = lane_transliteration_to_arabic(headword_transliterated)

            # Skip if conversion failed
            if not headword:
                continue

            # Extract definition (plain text)
            definition = extract_definition_text(entry)
            if not definition or len(definition) < 5:
                continue

            # Extract HTML formatted definition
            html_def = extract_definition_html(entry)

            entries.append({
                'lemma': headword,
                'language': 'arabic',
                'definition': definition,
                'html_definition': html_def,
                'source_name': "Lane's Lexicon"
            })

    except Exception as e:
        print(f"Error parsing {xml_file}: {e}")

    return entries

def create_lexicon_zip():
    """Create lexicon ZIP file for ClassicsViewer import."""
    print(f"\n{'='*60}")
    print("Creating arabic_lexicon.zip...")
    print(f"{'='*60}")

    # Temporary file names (will be renamed inside ZIP)
    dict_temp = SCRIPT_DIR / "dictionary.csv"
    norm_temp = SCRIPT_DIR / "normalization_rules.csv"
    morph_temp = SCRIPT_DIR / "morphology.csv"

    # Copy dictionary CSV with correct name
    print(f"  Copying {ARABIC_DICT_CSV.name} -> dictionary.csv")
    shutil.copy(ARABIC_DICT_CSV, dict_temp)

    # Check for normalization rules
    has_norm_rules = NORM_RULES_SOURCE.exists()

    if has_norm_rules:
        print(f"  Copying normalization_rules_arabic.csv -> normalization_rules.csv")
        shutil.copy(NORM_RULES_SOURCE, norm_temp)
    else:
        print(f"  Warning: Normalization rules not found at {NORM_RULES_SOURCE}")

    # Check for morphology
    morph_source = SCRIPT_DIR / "arabic_morphology.csv"
    has_morphology = morph_source.exists()

    if has_morphology:
        print(f"  Copying arabic_morphology.csv -> morphology.csv")
        shutil.copy(morph_source, morph_temp)
    else:
        print(f"  Warning: Morphology file not found at {morph_source}")
        print(f"           Run analyze_morphology.py to generate it")

    # Create ZIP file
    print(f"  Creating ZIP archive...")
    with zipfile.ZipFile(ARABIC_LEXICON_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(dict_temp, 'dictionary.csv')
        if has_norm_rules:
            zipf.write(norm_temp, 'normalization_rules.csv')
        if has_morphology:
            zipf.write(morph_temp, 'morphology.csv')

    # Clean up temporary files
    dict_temp.unlink()
    if has_norm_rules:
        norm_temp.unlink()
    if has_morphology:
        morph_temp.unlink()

    # Verify ZIP
    with zipfile.ZipFile(ARABIC_LEXICON_ZIP, 'r') as zipf:
        file_list = zipf.namelist()
        print(f"  ZIP contains: {file_list}")

        if 'dictionary.csv' not in file_list:
            raise ValueError("ZIP file missing dictionary.csv")

    # Get file size
    zip_size_mb = ARABIC_LEXICON_ZIP.stat().st_size / (1024 * 1024)
    print(f"\n✅ Created {ARABIC_LEXICON_ZIP.name} ({zip_size_mb:.2f} MB)")


def create_arabic_dictionary():
    """Process all Lane's Lexicon XML files and create CSV dictionary"""

    print(f"{'='*60}")
    print("Arabic Lexicon Generator for ClassicsViewer")
    print(f"{'='*60}")
    print(f"\nReading Lane's Lexicon XML files from: {DATA_DIR}")

    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        return

    all_entries = []
    xml_files = sorted(DATA_DIR.glob("*.xml"))

    print(f"Found {len(xml_files)} XML files\n")

    for xml_file in xml_files:
        print(f"Processing {xml_file.name}...")
        entries = parse_lane_xml_file(xml_file)
        all_entries.extend(entries)
        print(f"  Extracted {len(entries)} entries")

    print(f"\nTotal entries extracted: {len(all_entries)}")

    # Remove duplicates (keep first occurrence)
    seen_lemmas = set()
    unique_entries = []
    for entry in all_entries:
        if entry['lemma'] not in seen_lemmas:
            seen_lemmas.add(entry['lemma'])
            unique_entries.append(entry)

    print(f"Unique entries after deduplication: {len(unique_entries)}")

    # Write to CSV
    print(f"\nWriting dictionary to {ARABIC_DICT_CSV.name}...")
    with open(ARABIC_DICT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['lemma', 'language', 'definition', 'html_definition', 'source_name'])
        writer.writeheader()
        writer.writerows(unique_entries)

    print(f"✅ Dictionary CSV created: {ARABIC_DICT_CSV.name}")
    print(f"   Total entries: {len(unique_entries)}")

    # Show sample entries
    print("\nSample entries:")
    for i, entry in enumerate(unique_entries[:5], 1):
        print(f"{i}. {entry['lemma']}: {entry['definition'][:80]}...")

    # Create the ZIP package
    create_lexicon_zip()

if __name__ == "__main__":
    create_arabic_dictionary()
