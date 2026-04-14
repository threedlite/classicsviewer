#!/usr/bin/env python3
"""
Enhanced extraction of ALL Ancient Greek words from cached Wiktionary data.
This includes:
- Inflected forms (existing functionality)
- Standalone lemmas (adverbs, particles, conjunctions, etc.)
- All parts of speech
PRESERVES DIACRITICS - only removes punctuation (.,;·)
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime

def clean_punctuation(text):
    """Remove only punctuation (period, comma, semi-colon, raised dot), keep diacritics"""
    if not text:
        return ""
    # Only remove specific punctuation marks
    return re.sub(r'[.,;·]', '', text)

def parse_template(template_text):
    """Parse a Wiktionary template and extract meaningful content"""
    match = re.match(r'\{\{([^|{}]+)(?:\|(.+?))?\}\}', template_text, re.DOTALL)
    if not match:
        return None

    template_name = match.group(1).strip()
    params_text = match.group(2) if match.group(2) else ''

    # Split parameters carefully with nested templates
    params = []
    current_param = ''
    depth = 0
    for char in params_text:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        elif char == '|' and depth == 0:
            params.append(current_param.strip())
            current_param = ''
            continue
        current_param += char
    if current_param.strip():
        params.append(current_param.strip())

    return template_name, params

def extract_definition_from_template(template_text):
    """Extract human-readable definition from a template"""
    result = parse_template(template_text)
    if not result:
        return None

    template_name, params = result

    if template_name in ['inflection of', 'infl of']:
        # Cross-reference, not a definition — skip entirely
        return None
    elif template_name == 'place':
        place_type = params[1] if len(params) > 1 else ''
        location = params[2] if len(params) > 2 else ''
        for p in params:
            if p.startswith('t='):
                return p[2:]
        location = re.sub(r'\[\[([^\]]+)\]\]', r'\1', location)
        return f"{place_type} {location}".strip()
    elif template_name in ['lb', 'label']:
        # Dialect/register labels (Epic, Ionic, etc.) — not definitions
        return None

    return None

def clean_wiki_markup(text):
    """Clean wiki markup from text"""
    if not text:
        return ''

    # Remove templates recursively
    while '{{' in text:
        match = re.search(r'\{\{[^{}]+\}\}', text)
        if not match:
            break
        template = match.group(0)
        replacement = extract_definition_from_template(template) or ''
        text = text[:match.start()] + replacement + text[match.end():]

    # Clean wiki links
    text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)

    # Remove HTML and references
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)

    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Clean leading/trailing punctuation artifacts from template removal
    text = re.sub(r'^[,;:\s]+', '', text)
    text = re.sub(r'[,;:\s]+$', '', text)

    return text

def extract_lemma_from_template(template_text):
    """Extract lemma from various inflection templates"""
    lemmas = []
    
    # Common patterns for lemma extraction from inflection templates
    patterns = [
        # {{inflection of|grc|LEMMA|...}}
        r'\{\{inflection of\|grc\|([^|{}]+)\|',
        # {{infl of|grc|LEMMA|...}} - abbreviated form
        r'\{\{infl of\|grc\|([^|{}]+)\|',
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
    print(f"=== ENHANCED ANCIENT GREEK WORD EXTRACTION (WITH DIACRITICS) ===")
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
        cleaned_word = clean_punctuation(word)
        
        # Extract part of speech and definition
        pos_list, definition = extract_pos_and_definition(content)
        
        # Check if this is an inflection of another word
        lemmas = extract_lemma_from_template(content)
        
        if lemmas:
            # This is an inflected form
            stats['inflected_forms'] += 1
            for lemma in lemmas:
                cleaned_lemma = clean_punctuation(lemma)
                if cleaned_word and cleaned_lemma:
                    if cleaned_word not in all_mappings:
                        all_mappings[cleaned_word] = {
                            'lemmas': [],
                            'type': 'inflection',
                            'pos': pos_list,
                            'definition': definition
                        }
                    all_mappings[cleaned_word]['lemmas'].append(cleaned_lemma)
        else:
            # This is a standalone lemma (adverb, particle, etc.)
            if pos_list:  # Only if we found a part of speech
                stats['standalone_lemmas'] += 1
                stats[f'standalone_{pos_list[0]}'] += 1
                
                if cleaned_word:
                    # Add to mappings with itself as lemma
                    all_mappings[cleaned_word] = {
                        'lemmas': [cleaned_word],  # Maps to itself
                        'type': 'lemma',
                        'pos': pos_list,
                        'definition': definition
                    }
                    
                    # Also track standalone lemmas separately
                    standalone_lemmas[cleaned_word] = {
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
    
    # Check for μῆνιν
    print("\n=== μῆνιν CHECK ===")
    if 'μῆνιν' in all_mappings:
        info = all_mappings['μῆνιν']
        print(f"✓ μῆνιν found: {info['type']}, lemmas: {info['lemmas']}")
    else:
        print(f"✗ μῆνιν: NOT FOUND")
    
    if 'μῆνις' in all_mappings:
        info = all_mappings['μῆνις']
        print(f"✓ μῆνις found: {info['type']}, lemmas: {info['lemmas']}")
    else:
        print(f"✗ μῆνις: NOT FOUND")
    
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
            'source': 'Ancient Greek Wiktionary Extraction (with diacritics)',
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

    # Create comprehensive definitions file for extract_wiktionary_final.py
    # Extract definitions from ALL Ancient Greek pages using comprehensive parsing
    print("\nCreating comprehensive definitions file for dictionary build...")
    print("Using template parsing and comprehensive extraction...")

    definitions_dict = {}
    pages_processed = 0
    stats = {'with_definitions': 0, 'with_etymology': 0, 'with_pos_only': 0}

    for word, content in all_pages.items():
        if not is_ancient_greek_entry(content):
            continue

        pages_processed += 1
        cleaned_word = clean_punctuation(word)
        if not cleaned_word:
            continue

        # Extract Ancient Greek section
        ag_match = re.search(r'==Ancient Greek==(.*?)(?:\n==[^=]|\Z)', content, re.DOTALL)
        if not ag_match:
            continue

        ag_section = ag_match.group(1)

        # Determine part of speech
        pos = None
        for p, pattern in [('proper noun', r'===Proper noun==='), ('noun', r'===Noun==='),
                          ('verb', r'===Verb==='), ('adjective', r'===Adjective==='),
                          ('adverb', r'===Adverb==='), ('numeral', r'===Numeral==='),
                          ('particle', r'===Particle==='), ('conjunction', r'===Conjunction==='),
                          ('preposition', r'===Preposition==='), ('pronoun', r'===Pronoun===')]:
            if re.search(pattern, ag_section, re.IGNORECASE):
                pos = p
                break

        # Extract definition lines
        def_lines = re.findall(r'^#\s+(.+)$', ag_section, re.MULTILINE)

        if def_lines:
            # Clean and combine definitions
            cleaned_defs = []
            for def_line in def_lines[:5]:
                # Skip lines that are purely inflection-of references
                if re.match(r'^\s*\{\{(inflection of|infl of)\b', def_line):
                    continue
                cleaned = clean_wiki_markup(def_line)
                if cleaned and len(cleaned) > 2:
                    cleaned_defs.append(cleaned)

            if cleaned_defs:
                definitions_dict[cleaned_word] = {
                    'entry_plain': '; '.join(cleaned_defs),
                    'part_of_speech': pos or 'unknown',
                    'type': 'lemma'
                }
                stats['with_definitions'] += 1
                continue

        # Fallback: try etymology
        etym_match = re.search(r'===Etymology===\s*\n(.+?)(?:\n===|\Z)', ag_section, re.DOTALL)
        if etym_match:
            etymology = etym_match.group(1)
            meaning_match = re.search(r't=([^,}\]]+)', etymology)
            if meaning_match:
                definitions_dict[cleaned_word] = {
                    'entry_plain': meaning_match.group(1).strip(),
                    'part_of_speech': pos or 'unknown',
                    'type': 'lemma'
                }
                stats['with_etymology'] += 1
                continue

        # Last resort: skip — POS-only entries ("adjective", "noun") provide no
        # useful definition and pollute the dictionary with meaningless glosses
        if pos:
            stats['with_pos_only'] += 1

    print(f"  Processed {pages_processed:,} Ancient Greek pages")
    print(f"  Extracted {len(definitions_dict):,} definitions:")
    print(f"    - Full definitions: {stats['with_definitions']:,}")
    print(f"    - From etymology: {stats['with_etymology']:,}")
    print(f"    - POS only: {stats['with_pos_only']:,}")
    print(f"  Coverage: {len(definitions_dict) / pages_processed * 100:.1f}%")

    definitions_output = Path(__file__).parent / "wiktionary_definitions_complete.json"
    print(f"Saving {len(definitions_dict):,} definitions to {definitions_output}...")
    with open(definitions_output, 'w', encoding='utf-8') as f:
        json.dump(definitions_dict, f, ensure_ascii=False, indent=2)

    print("\nExtraction complete!")
    return output_data, standalone_lemmas

def main():
    """Main function for use by other scripts"""
    cache_path = Path(__file__).parent / "all_greek_wiktionary_pages.json"
    output_path = Path(__file__).parent / "extract_all_ancient_greek_words_with_diacritics.json"
    
    if not cache_path.exists():
        print(f"Error: Cache file {cache_path} not found!")
        raise FileNotFoundError(f"Required cache file missing: {cache_path}")
    
    return extract_all_greek_words(cache_path, output_path)

if __name__ == "__main__":
    main()