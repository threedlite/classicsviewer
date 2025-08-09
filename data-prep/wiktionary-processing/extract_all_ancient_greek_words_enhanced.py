#!/usr/bin/env python3
"""
Enhanced extraction of ALL Ancient Greek words from cached Wiktionary data.
This includes:
- Inflected forms (existing functionality)
- Standalone lemmas (adverbs, particles, conjunctions, etc.)
- All parts of speech
"""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from datetime import datetime

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
    """Extract lemma from various inflection templates"""
    lemmas = []
    
    # Common patterns for lemma extraction from inflection templates
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

def extract_pos_and_definition(content):
    """Extract part of speech and definition from entry content"""
    pos_patterns = {
        'noun': r'===Noun===',
        'verb': r'===Verb===',
        'adjective': r'===Adjective===',
        'adverb': r'===Adverb===',
        'particle': r'===Particle===',
        'conjunction': r'===Conjunction===',
        'preposition': r'===Preposition===',
        'pronoun': r'===Pronoun===',
        'numeral': r'===Numeral===',
        'interjection': r'===Interjection===',
        'article': r'===Article===',
        'determiner': r'===Determiner===',
    }
    
    pos_found = []
    for pos, pattern in pos_patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            pos_found.append(pos)
    
    # Extract first definition line
    definition = None
    def_match = re.search(r'#\s*([^\n]+)', content)
    if def_match:
        definition = def_match.group(1).strip()
        # Clean up wiki markup
        definition = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', definition)  # [[link|text]] -> text
        definition = re.sub(r'\[\[([^\]]+)\]\]', r'\1', definition)  # [[link]] -> link
        definition = re.sub(r'\{\{[^}]+\}\}', '', definition)  # Remove templates
        definition = definition.strip()
    
    return pos_found, definition

def is_ancient_greek_entry(content):
    """Check if the entry contains Ancient Greek content"""
    return '==Ancient Greek==' in content

def extract_all_greek_words(cache_path, output_path):
    """Extract all Ancient Greek words including standalone lemmas"""
    print(f"=== ENHANCED ANCIENT GREEK WORD EXTRACTION ===")
    print(f"Source: {cache_path}")
    print(f"Output: {output_path}")
    print()
    
    # Load cached data
    print("Loading cached Wiktionary data...")
    with open(cache_path, 'r', encoding='utf-8') as f:
        all_pages = json.load(f)
    print(f"Loaded {len(all_pages):,} pages")
    
    # Results storage
    all_mappings = {}  # word -> lemma info
    standalone_lemmas = {}  # lemmas that are not inflections
    stats = defaultdict(int)
    
    # Process each page
    for word, content in all_pages.items():
        if not is_ancient_greek_entry(content):
            continue
            
        stats['ancient_greek_entries'] += 1
        normalized_word = normalize_greek(word)
        
        # Extract part of speech and definition
        pos_list, definition = extract_pos_and_definition(content)
        
        # Check if this is an inflection of another word
        lemmas = extract_lemma_from_template(content)
        
        if lemmas:
            # This is an inflected form
            stats['inflected_forms'] += 1
            for lemma in lemmas:
                normalized_lemma = normalize_greek(lemma)
                if normalized_word and normalized_lemma:
                    if normalized_word not in all_mappings:
                        all_mappings[normalized_word] = {
                            'lemmas': [],
                            'type': 'inflection',
                            'pos': pos_list,
                            'definition': definition
                        }
                    all_mappings[normalized_word]['lemmas'].append(normalized_lemma)
        else:
            # This is a standalone lemma (adverb, particle, etc.)
            if pos_list:  # Only if we found a part of speech
                stats['standalone_lemmas'] += 1
                stats[f'standalone_{pos_list[0]}'] += 1
                
                if normalized_word:
                    # Add to mappings with itself as lemma
                    all_mappings[normalized_word] = {
                        'lemmas': [normalized_word],  # Maps to itself
                        'type': 'lemma',
                        'pos': pos_list,
                        'definition': definition
                    }
                    
                    # Also track standalone lemmas separately
                    standalone_lemmas[normalized_word] = {
                        'pos': pos_list,
                        'definition': definition,
                        'original_form': word
                    }
    
    # Print statistics
    print("\n=== EXTRACTION STATISTICS ===")
    print(f"Ancient Greek entries processed: {stats['ancient_greek_entries']:,}")
    print(f"Inflected forms found: {stats['inflected_forms']:,}")
    print(f"Standalone lemmas found: {stats['standalone_lemmas']:,}")
    print(f"\nStandalone lemmas by part of speech:")
    for pos in ['noun', 'verb', 'adjective', 'adverb', 'particle', 'conjunction', 'preposition', 'pronoun']:
        count = stats.get(f'standalone_{pos}', 0)
        if count > 0:
            print(f"  {pos}: {count:,}")
    
    # Check for our target missing words
    print("\n=== TARGET WORDS CHECK ===")
    target_words = ['μαλιστα', 'πρωτον', 'μεντοι', 'ορθωσ', 'καθαπερ', 'ουχ', 'ημιν', 'ημασ']
    for target in target_words:
        if target in all_mappings:
            info = all_mappings[target]
            print(f"✓ {target}: {info['type']}, POS: {info['pos']}, lemmas: {info['lemmas'][:3]}")
        else:
            print(f"✗ {target}: NOT FOUND")
    
    # Convert to standard format expected by database
    print("\nConverting to standard format...")
    mappings_list = []
    
    for word_form, info in all_mappings.items():
        if 'lemmas' in info:
            for lemma in info['lemmas']:
                mappings_list.append({
                    'word_form': word_form,
                    'lemma': lemma,
                    'confidence': 0.95 if info.get('type') == 'lemma' else 0.9,
                    'source': 'Enhanced Wiktionary',
                    'morph_type': f"{info.get('type', 'unknown')}:{','.join(info.get('pos', ['unknown']))}"
                })
    
    # Create output in standard format
    output_data = {
        'metadata': {
            'source': 'Enhanced Ancient Greek Wiktionary Extraction',
            'extraction_date': datetime.now().isoformat(),
            'total_entries': len(all_mappings),
            'standalone_lemmas': len(standalone_lemmas),
            'inflected_forms': stats['inflected_forms']
        },
        'mappings': mappings_list
    }
    
    # Save results in standard format
    print(f"\nSaving {len(mappings_list):,} mappings in standard format...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Also save standalone lemmas separately for reference
    standalone_output = str(output_path).replace('.json', '_standalone_lemmas.json')
    print(f"Saving {len(standalone_lemmas):,} standalone lemmas to {standalone_output}...")
    with open(standalone_output, 'w', encoding='utf-8') as f:
        json.dump(standalone_lemmas, f, ensure_ascii=False, indent=2)
    
    print("\nExtraction complete!")
    return output_data, standalone_lemmas

if __name__ == "__main__":
    cache_path = Path("all_greek_wiktionary_pages.json")
    output_path = Path("ancient_greek_complete_morphology.json")
    
    if not cache_path.exists():
        print(f"Error: Cache file {cache_path} not found!")
        print("Please run extract_all_greek_pages.py first.")
        exit(1)
    
    all_mappings, standalone_lemmas = extract_all_greek_words(cache_path, output_path)