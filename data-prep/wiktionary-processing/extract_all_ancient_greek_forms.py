#!/usr/bin/env python3
"""
Extract ALL Ancient Greek non-lemma forms from English Wiktionary
This includes all inflection templates, not just {{inflection of}}
"""

import xml.etree.ElementTree as ET
import re
import bz2
import json
import unicodedata
from pathlib import Path
from collections import defaultdict

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

def extract_lemma_from_template(template_text):
    """Extract lemma from various template formats"""
    lemmas = []
    
    # Common patterns for lemma extraction
    patterns = [
        # {{inflection of|grc|LEMMA|...}}
        r'\{\{inflection of\|grc\|([^|{}]+)\|',
        # {{form of|TYPE|grc|LEMMA}}
        r'\{\{form of\|[^|]+\|grc\|([^|{}]+)\}\}',
        # {{grc-form of|LEMMA|...}}
        r'\{\{grc-form of\|([^|{}]+)[|}]',
        # Specific form templates
        r'\{\{plural of\|grc\|([^|{}]+)\}\}',
        r'\{\{genitive of\|grc\|([^|{}]+)\}\}',
        r'\{\{dative of\|grc\|([^|{}]+)\}\}',
        r'\{\{accusative of\|grc\|([^|{}]+)\}\}',
        r'\{\{vocative of\|grc\|([^|{}]+)\}\}',
        r'\{\{nominative plural of\|grc\|([^|{}]+)\}\}',
        r'\{\{genitive plural of\|grc\|([^|{}]+)\}\}',
        # Verb forms
        r'\{\{aorist of\|grc\|([^|{}]+)\}\}',
        r'\{\{present of\|grc\|([^|{}]+)\}\}',
        r'\{\{imperfect of\|grc\|([^|{}]+)\}\}',
        r'\{\{future of\|grc\|([^|{}]+)\}\}',
        r'\{\{perfect of\|grc\|([^|{}]+)\}\}',
        # Epic/Ionic/Doric/etc forms
        r'\{\{epic form of\|grc\|([^|{}]+)\}\}',
        r'\{\{ionic form of\|grc\|([^|{}]+)\}\}',
        r'\{\{doric form of\|grc\|([^|{}]+)\}\}',
        r'\{\{aeolic form of\|grc\|([^|{}]+)\}\}',
        # Alternative spellings
        r'\{\{alternative form of\|grc\|([^|{}]+)\}\}',
        r'\{\{alternative spelling of\|grc\|([^|{}]+)\}\}',
        r'\{\{obsolete form of\|grc\|([^|{}]+)\}\}',
        r'\{\{archaic form of\|grc\|([^|{}]+)\}\}',
        # Participles
        r'\{\{present participle of\|grc\|([^|{}]+)\}\}',
        r'\{\{past participle of\|grc\|([^|{}]+)\}\}',
        r'\{\{participle of\|grc\|([^|{}]+)\}\}',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, template_text)
        lemmas.extend(matches)
    
    return lemmas

def extract_morph_info(template_text):
    """Extract morphological information from template"""
    # Try to extract the type of inflection
    if 'plural of' in template_text:
        return 'plural'
    elif 'genitive of' in template_text:
        return 'genitive'
    elif 'dative of' in template_text:
        return 'dative'
    elif 'accusative of' in template_text:
        return 'accusative'
    elif 'aorist of' in template_text:
        return 'aorist'
    elif 'perfect of' in template_text:
        return 'perfect'
    elif 'participle' in template_text:
        return 'participle'
    elif 'inflection of' in template_text:
        # Try to extract tags from inflection of template
        match = re.search(r'\{\{inflection of\|grc\|[^|]+\|([^}]+)\}\}', template_text)
        if match:
            tags = match.group(1).replace('|', ' ')
            return tags.strip()
    return None

def extract_all_ancient_greek_forms(dump_path, output_path):
    """Extract all Ancient Greek non-lemma forms from English Wiktionary"""
    print(f"=== EXTRACTING ALL ANCIENT GREEK FORMS FROM ENGLISH WIKTIONARY ===")
    print(f"Source: {dump_path}")
    print(f"Output: {output_path}")
    
    with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
        context = ET.iterparse(f, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        all_mappings = []
        pages_processed = 0
        ancient_greek_pages = 0
        forms_found = 0
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('page'):
                pages_processed += 1
                
                if pages_processed % 10000 == 0:
                    print(f"  Processed {pages_processed:,} pages, found {ancient_greek_pages:,} Ancient Greek pages, {forms_found:,} forms...")
                
                # Extract title and text
                title_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}title')
                text_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text or ''
                    text = text_elem.text or ''
                    
                    # Skip non-main namespace pages
                    if ':' in title and not title.startswith('Reconstruction:'):
                        elem.clear()
                        root.clear()
                        continue
                    
                    # Check if page has Ancient Greek section
                    if '==Ancient Greek==' not in text:
                        elem.clear()
                        root.clear()
                        continue
                    
                    ancient_greek_pages += 1
                    
                    # Extract the Ancient Greek section
                    grc_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|$)', text, re.DOTALL)
                    if not grc_match:
                        elem.clear()
                        root.clear()
                        continue
                    
                    grc_section = grc_match.group(0)
                    
                    # Look for ANY template that indicates this is a non-lemma form
                    lemmas = extract_lemma_from_template(grc_section)
                    
                    if lemmas:
                        forms_found += 1
                        word_form = normalize_greek(title)
                        morph_info = extract_morph_info(grc_section)
                        
                        # Get unique lemmas
                        seen_lemmas = set()
                        for lemma in lemmas:
                            lemma_norm = normalize_greek(lemma)
                            if lemma_norm and lemma_norm not in seen_lemmas:
                                seen_lemmas.add(lemma_norm)
                                
                                mapping = {
                                    'word_form': word_form,
                                    'lemma': lemma_norm,
                                    'confidence': 0.95,
                                    'source': 'enwiktionary:ancient-greek',
                                    'morph_info': morph_info
                                }
                                all_mappings.append(mapping)
                
                # Clear elements to save memory
                elem.clear()
                root.clear()
    
    print(f"\nExtraction complete!")
    print(f"  Total pages processed: {pages_processed:,}")
    print(f"  Ancient Greek pages: {ancient_greek_pages:,}")
    print(f"  Non-lemma forms found: {forms_found:,}")
    print(f"  Total mappings: {len(all_mappings):,}")
    
    # Count unique forms
    unique_forms = len(set(m['word_form'] for m in all_mappings))
    print(f"  Unique word forms: {unique_forms:,}")
    
    # Save results
    output_data = {
        'metadata': {
            'source': 'English Wiktionary (Wikimedia Foundation)',
            'extraction_type': 'All Ancient Greek non-lemma forms',
            'pages_processed': pages_processed,
            'ancient_greek_pages': ancient_greek_pages,
            'forms_found': forms_found,
            'total_mappings': len(all_mappings),
            'unique_forms': unique_forms
        },
        'mappings': all_mappings
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved {len(all_mappings):,} mappings to {output_path}")
    
    # Show sample mappings
    print("\nSample mappings:")
    for mapping in all_mappings[:10]:
        morph = f" ({mapping['morph_info']})" if mapping['morph_info'] else ""
        print(f"  {mapping['word_form']} → {mapping['lemma']}{morph}")

if __name__ == "__main__":
    dump_path = Path(__file__).parent.parent.parent / "data-sources" / "enwiktionary-latest-pages-articles.xml.bz2"
    output_path = Path(__file__).parent / "ancient_greek_all_forms.json"
    
    extract_all_ancient_greek_forms(dump_path, output_path)