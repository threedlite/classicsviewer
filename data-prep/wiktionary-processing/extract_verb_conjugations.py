#!/usr/bin/env python3
"""
Extract Ancient Greek verb conjugations from Greek Wiktionary
Similar to extract_declension_mappings.py but for verbs
"""

import xml.etree.ElementTree as ET
import re
import bz2
import json
import unicodedata
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    if not text:
        return ""
    # First normalize to NFD (decomposed form)
    text = unicodedata.normalize('NFD', text)
    # Remove diacritical marks
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Convert to lowercase
    text = text.lower()
    # Replace final sigma
    text = text.replace('ς', 'σ')
    # Remove punctuation (including Greek punctuation)
    # Keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def extract_verb_forms(title, text):
    """Extract verb forms from a Greek Wiktionary page"""
    mappings = []
    
    # Look for verb conjugation templates
    # Common patterns in Greek Wiktionary for verbs
    verb_patterns = [
        r'\{\{el-conjug-1.*?\}\}',
        r'\{\{el-conjug-2.*?\}\}',
        r'\{\{κλ:ρήμα.*?\}\}',
        r'\{\{κλ:αγαπώ.*?\}\}',
        r'\{\{κλ:λύω.*?\}\}',
        r'\{\{κλ:τίθημι.*?\}\}',
        r'\{\{κλ:δίδωμι.*?\}\}',
        r'\{\{κλ:ἵστημι.*?\}\}',
    ]
    
    for pattern in verb_patterns:
        if re.search(pattern, text):
            # Found a verb conjugation template
            # Generate basic forms (simplified - in reality would need full conjugation logic)
            stem = normalize_greek(title)
            
            # For now, just mark that this is a verb
            # In a full implementation, we'd generate all conjugated forms
            return True, stem
    
    return False, None

def extract_greek_verb_conjugations(dump_path="../../data-sources/elwiktionary-latest-pages-articles.xml.bz2",
                                   output_path="ancient_greek_verb_conjugations.json"):
    """Extract verb conjugations from Greek Wiktionary"""
    
    print("=== EXTRACTING VERB CONJUGATIONS FROM GREEK WIKTIONARY ===")
    print(f"Source: {dump_path}")
    print(f"Output: {output_path}")
    
    # For now, let's look for pages that have verb conjugation patterns
    # and extract what we can
    
    verb_pages = []
    pages_processed = 0
    
    with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
        context = ET.iterparse(f, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('page'):
                pages_processed += 1
                
                # Extract title and text
                title_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}title')
                text_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    text = text_elem.text or ""
                    
                    # Check if this page has Ancient Greek content
                    if title and '==Αρχαία ελληνικά==' in text:
                        # Check if it's a verb
                        if '===Ρήμα===' in text or '{{κλ:' in text:
                            is_verb, lemma = extract_verb_forms(title, text)
                            if is_verb:
                                verb_pages.append({
                                    'title': title,
                                    'lemma': lemma,
                                    'has_ancient_greek': True
                                })
                
                # Clear the element to save memory
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
                
                if pages_processed % 50000 == 0:
                    print(f"  Processed {pages_processed:,} pages, found {len(verb_pages)} verb pages")
        
        # Clear the root element
        root.clear()
    
    print(f"\n✓ Extraction complete!")
    print(f"  Total pages processed: {pages_processed:,}")
    print(f"  Verb pages found: {len(verb_pages)}")
    
    # Save results
    results = {
        'metadata': {
            'source': 'Greek Wiktionary Verb Conjugations',
            'total_pages_processed': pages_processed,
            'verb_pages_found': len(verb_pages)
        },
        'verbs': verb_pages
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved to {output_path}")

if __name__ == "__main__":
    extract_greek_verb_conjugations()