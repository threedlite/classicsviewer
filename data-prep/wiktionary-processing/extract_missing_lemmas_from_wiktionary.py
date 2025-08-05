#!/usr/bin/env python3
"""
Extract Wiktionary definitions for Ancient Greek lemmas that are missing from LSJ
but appear in our texts. This fills gaps in dictionary coverage.
"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import sqlite3
from collections import defaultdict
import unicodedata

def normalize_greek(text):
    """Normalize Greek text - same as in main database creation"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def get_missing_lemmas():
    """Get lemmas that appear in texts but are not in LSJ"""
    conn = sqlite3.connect('perseus_texts.db')
    cursor = conn.cursor()
    
    # Get all unique lemmas from lemma_map
    cursor.execute("""
        SELECT DISTINCT lemma 
        FROM lemma_map 
        WHERE lemma NOT IN (
            SELECT headword_normalized 
            FROM dictionary_entries 
            WHERE language = 'greek'
        )
        ORDER BY lemma
    """)
    
    missing_lemmas = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return missing_lemmas

def extract_wiktionary_definition(title, text):
    """Extract a concise definition from Wiktionary page text"""
    
    # Look for Ancient Greek section
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', text, re.DOTALL)
    if not ag_match:
        return None
    
    ag_section = ag_match.group(0)
    
    # Find part of speech
    pos_match = re.search(r'===(Noun|Verb|Adjective|Pronoun|Particle|Adverb|Preposition|Conjunction|Numeral|Interjection)===', ag_section)
    if not pos_match:
        return None
    
    pos = pos_match.group(1).lower()
    
    # Extract first few definitions
    definitions = []
    definition_section = ag_section[pos_match.end():]
    
    for line in definition_section.split('\n'):
        if line.startswith('# ') and not line.startswith('##'):
            # Clean the definition
            defn = line[2:].strip()
            
            # Remove wiki markup
            defn = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\\2', defn)  # [[link|text]] -> text
            defn = re.sub(r'\[\[([^\]]+)\]\]', r'\\1', defn)  # [[link]] -> link
            defn = re.sub(r"'''?", '', defn)  # Remove bold/italic
            defn = re.sub(r'\{\{[^}]+\}\}', '', defn)  # Remove templates
            defn = re.sub(r'\([^)]*\)', '', defn)  # Remove parenthetical references
            defn = defn.strip()
            
            if defn and len(defn) > 3:  # Skip very short definitions
                definitions.append(defn)
                
        if len(definitions) >= 3:  # Limit to 3 definitions
            break
    
    if not definitions:
        return None
    
    # Format as simple HTML entry similar to LSJ style
    html_entry = f'<div class="wiktionary-entry">'
    html_entry += f'<b>{title}</b>, {pos}. '
    
    if len(definitions) == 1:
        html_entry += definitions[0]
    else:
        html_entry += '<br/>'.join([f'{i+1}. {d}' for i, d in enumerate(definitions)])
    
    html_entry += '<br/><i>(From Wiktionary)</i></div>'
    
    # Plain text version
    plain_entry = f'{title}, {pos}. ' + '; '.join(definitions) + ' (From Wiktionary)'
    
    return {
        'headword': title,
        'headword_normalized': normalize_greek(title),
        'entry_html': html_entry,
        'entry_plain': plain_entry,
        'pos': pos
    }

def process_wiktionary_dump(dump_file, target_lemmas):
    """Extract definitions for specific lemmas from Wiktionary"""
    
    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    found_entries = {}
    target_set = set(target_lemmas)
    
    print(f"Looking for {len(target_lemmas)} missing lemmas in Wiktionary...")
    
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
        for event, elem in ET.iterparse(f, events=('start', 'end')):
            if event == 'end' and elem.tag.endswith('page'):
                title_elem = elem.find('.//ns:title', namespace)
                text_elem = elem.find('.//ns:text', namespace)
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    
                    # Check if this is one of our target lemmas
                    normalized_title = normalize_greek(title)
                    if normalized_title in target_set:
                        text = text_elem.text or ''
                        
                        if '==Ancient Greek==' in text:
                            entry = extract_wiktionary_definition(title, text)
                            if entry:
                                found_entries[normalized_title] = entry
                                print(f"  Found: {title}")
                
                elem.clear()
                
            # Stop if we found all targets
            if len(found_entries) == len(target_lemmas):
                break
    
    return found_entries

def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        # Get missing lemmas
        missing = get_missing_lemmas()
        print(f"Found {len(missing)} lemmas in texts but not in LSJ")
        
        # Filter to only those that might realistically be in Wiktionary
        # (skip algorithmic forms, very short words, etc.)
        candidates = [l for l in missing if len(l) > 2 and not l.endswith('ω')]
        print(f"Filtering to {len(candidates)} candidates for Wiktionary lookup")
        
        # Process Wiktionary
        dump_file = '/home/user/classics-viewer/data-sources/enwiktionary-latest-pages-articles.xml.bz2'
        entries = process_wiktionary_dump(dump_file, candidates[:100])  # Limit for testing
        
        # Save results
        with open('wiktionary_supplement.json', 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        
        print(f"\nExtracted {len(entries)} Wiktionary entries")
        
    else:
        # Demo mode - show what would be extracted
        print("DEMO: Would extract Wiktionary definitions for missing lemmas")
        print("\nExample missing lemmas that might have Wiktionary entries:")
        demo_lemmas = ['σφωε', 'ατρευσ', 'πρωτοσ', 'νουσοσ']
        
        for lemma in demo_lemmas:
            print(f"  - {lemma}")
        
        print("\nExample output format:")
        example = {
            'headword': 'σφωέ',
            'headword_normalized': 'σφωε',
            'entry_html': '<div class="wiktionary-entry"><b>σφωέ</b>, pronoun. Epic enclitic third person dual personal pronoun; they two, both of them<br/><i>(From Wiktionary)</i></div>',
            'entry_plain': 'σφωέ, pronoun. Epic enclitic third person dual personal pronoun; they two, both of them (From Wiktionary)',
            'pos': 'pronoun'
        }
        print(json.dumps(example, ensure_ascii=False, indent=2))
        
        print("\nRun with --execute to actually process Wiktionary dump")

if __name__ == '__main__':
    main()