#!/usr/bin/env python3
"""
Extract Ancient Greek definitions from Wiktionary for words not in LSJ.
This provides fallback definitions for lemmas that exist in Wiktionary but not in LSJ.
"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
from collections import defaultdict

def parse_wiktionary_dump(dump_file):
    """Extract Ancient Greek definitions from Wiktionary dump"""
    
    definitions = {}
    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    
    print(f"Processing {dump_file}...")
    
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
        # Parse incrementally
        for event, elem in ET.iterparse(f, events=('start', 'end')):
            if event == 'end' and elem.tag.endswith('page'):
                title_elem = elem.find('.//ns:title', namespace)
                text_elem = elem.find('.//ns:text', namespace)
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    text = text_elem.text or ''
                    
                    # Skip non-main namespace pages
                    if ':' in title:
                        elem.clear()
                        continue
                    
                    # Look for Ancient Greek section
                    if '==Ancient Greek==' in text:
                        definition_data = extract_ancient_greek_definition(title, text)
                        if definition_data:
                            definitions[title] = definition_data
                
                elem.clear()
    
    return definitions

def extract_ancient_greek_definition(title, text):
    """Extract definition from Ancient Greek section"""
    
    # Extract Ancient Greek section
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
    if not ag_match:
        return None
    
    ag_section = ag_match.group(0)
    
    # Extract part of speech
    pos_match = re.search(r'===(Noun|Verb|Adjective|Pronoun|Particle|Adverb|Preposition|Conjunction)===', ag_section)
    if not pos_match:
        return None
    
    pos = pos_match.group(1).lower()
    
    # Extract definitions (look for # at start of line)
    definitions = []
    for line in ag_section.split('\n'):
        if line.startswith('# ') and not line.startswith('##'):
            # Clean definition
            defn = line[2:].strip()
            # Remove wiki markup
            defn = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', defn)  # [[link|text]] -> text
            defn = re.sub(r'\[\[([^\]]+)\]\]', r'\1', defn)  # [[link]] -> link
            defn = re.sub(r"'''?", '', defn)  # Remove bold/italic
            defn = re.sub(r'\{\{[^}]+\}\}', '', defn)  # Remove templates
            definitions.append(defn)
    
    if not definitions:
        return None
    
    # Extract etymology if present
    etymology = None
    etym_match = re.search(r'===Etymology===\n(.*?)(?=\n===|\Z)', ag_section, re.DOTALL)
    if etym_match:
        etymology = etym_match.group(1).strip()
        # Clean etymology text
        etymology = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', etymology)
        etymology = re.sub(r'\[\[([^\]]+)\]\]', r'\1', etymology)
        etymology = re.sub(r'\{\{[^}]+\}\}', '', etymology)
        etymology = etymology.split('\n')[0]  # Just first line
    
    return {
        'pos': pos,
        'definitions': definitions[:3],  # Limit to first 3 definitions
        'etymology': etymology
    }

def create_wiktionary_entries_schema():
    """SQL schema for Wiktionary entries table"""
    return """
    CREATE TABLE IF NOT EXISTS wiktionary_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        headword TEXT NOT NULL,
        headword_normalized TEXT NOT NULL,
        part_of_speech TEXT,
        definition_text TEXT NOT NULL,
        etymology TEXT,
        UNIQUE(headword_normalized)
    );
    
    CREATE INDEX idx_wiktionary_headword ON wiktionary_entries(headword_normalized);
    """

def main():
    # List of words we know are missing from LSJ
    target_words = [
        'σφωέ',      # dual pronoun
        'Ἀτρεύς',    # Atreus (proper name)
        'πρῶτα',     # neuter plural of πρῶτος
        'νοῦσος',    # disease (variant form)
    ]
    
    # In practice, we would:
    # 1. Parse the full Wiktionary dump
    # 2. Extract all Ancient Greek entries
    # 3. Filter to those not in LSJ
    # 4. Store in database
    
    print("Would extract definitions for words like:")
    for word in target_words:
        print(f"  - {word}")
    
    print("\nExample output structure:")
    example = {
        'σφωέ': {
            'pos': 'pronoun',
            'definitions': [
                'Epic enclitic third person dual personal pronoun',
                'they two, both of them',
                'these two'
            ],
            'etymology': 'From Proto-Indo-European *swé'
        }
    }
    print(json.dumps(example, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()