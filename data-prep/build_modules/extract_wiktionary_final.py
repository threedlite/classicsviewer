#!/usr/bin/env python3
"""
Extract Wiktionary morphological data and definitions into the same format as Cunliffe:
{
  "headword": {
    "inflected_forms": [...],
    "definition": "..."
  }
}

This uses the morphology file WITH diacritics preserved.
Structures data so headwords always have definitions with inflected forms listed under them.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

def clean_punctuation(text):
    """Remove only punctuation (period, comma, semi-colon, raised dot), keep diacritics"""
    return re.sub(r'[.,;·]', '', text)

def simplify_lemma(lemma):
    """Simplify lemma by removing macrons and breves while preserving other diacritics"""
    import unicodedata
    
    # First normalize to NFD (decomposed form) to handle all combinations
    result = unicodedata.normalize('NFD', lemma)
    
    # Remove combining macron (U+0304) and combining breve (U+0306)
    # while preserving all other combining marks (accents, breathings, etc.)
    result = ''.join(ch for ch in result if ord(ch) not in [0x0304, 0x0306])
    
    # Normalize back to NFC (composed form) for consistency
    result = unicodedata.normalize('NFC', result)
    
    # Also handle precomposed characters that include macrons/breves
    # These are separate Unicode characters that won't decompose
    replacements = [
        # Greek lowercase with macron
        ('ᾱ', 'α'),  # U+1FB1
        ('ῑ', 'ι'),  # U+1FD1
        ('ῡ', 'υ'),  # U+1FE1
        # Greek lowercase with breve
        ('ᾰ', 'α'),  # U+1FB0
        ('ῐ', 'ι'),  # U+1FD0
        ('ῠ', 'υ'),  # U+1FE0
        # Greek uppercase with macron
        ('Ᾱ', 'Α'),  # U+1FB9
        ('Ῑ', 'Ι'),  # U+1FD9
        ('Ῡ', 'Υ'),  # U+1FE9
        # Greek uppercase with breve
        ('Ᾰ', 'Α'),  # U+1FB8
        ('Ῐ', 'Ι'),  # U+1FD8
        ('Ῠ', 'Υ'),  # U+1FE8
    ]
    
    for old, new in replacements:
        result = result.replace(old, new)
    
    return result

def extract_wiktionary_data():
    """Extract all Wiktionary morphology data and available definitions"""
    
    # Paths to Wiktionary processed data
    morphology_file = Path(__file__).parent.parent / "wiktionary-processing" / "extract_all_ancient_greek_words_with_diacritics.json"
    definitions_file = Path(__file__).parent.parent / "wiktionary-processing" / "wiktionary_definitions_complete.json"
    
    # Also try loading LSJ and Cunliffe for better definitions
    lsj_file = Path(__file__).parent / "extract_lsj_fixed.json"
    cunliffe_file = Path(__file__).parent / "extract_cunliffe_new.json"
    
    if not morphology_file.exists():
        print(f"Error: Morphology file not found at {morphology_file}")
        raise FileNotFoundError(f"Required morphology file missing: {morphology_file}")
    
    print(f"Loading Wiktionary morphology from {morphology_file}")
    with open(morphology_file, 'r', encoding='utf-8') as f:
        morphology_data = json.load(f)
    
    mappings = morphology_data.get('mappings', [])
    print(f"Found {len(mappings)} morphology mappings")
    
    # Build lemma-to-forms mapping
    lemma_to_forms = defaultdict(set)
    lemma_info = {}  # Track additional info about lemmas
    
    for mapping in mappings:
        word_form = mapping.get('word_form', '')
        lemma = mapping.get('lemma', '')
        morph_type = mapping.get('morph_type', '')
        
        if not word_form or not lemma:
            continue
            
        # Clean punctuation
        word_form = clean_punctuation(word_form)
        lemma = clean_punctuation(lemma)
        
        if not word_form or not lemma:
            continue
        
        # Normalize lemma by removing macrons/breves
        normalized_lemma = simplify_lemma(lemma)
        
        # Store lemma info if this is a lemma entry
        if 'lemma:' in morph_type and word_form == lemma:
            # Extract part of speech from morph_type
            pos = morph_type.split(':')[1] if ':' in morph_type else 'unknown'
            lemma_info[normalized_lemma] = {
                'pos': pos,
                'source': mapping.get('source', 'Wiktionary')
            }
        
        # Add inflected form to normalized lemma
        if word_form != lemma:  # Keep original check to avoid self-mappings
            lemma_to_forms[normalized_lemma].add(word_form)
    
    print(f"Found {len(lemma_to_forms)} unique lemmas")

    # Load definitions - REQUIRED component
    if not definitions_file.exists():
        raise FileNotFoundError(
            f"CRITICAL: Wiktionary definitions file missing: {definitions_file}\n"
            f"This is a required component for the dictionary build.\n"
            f"You need to create a script to extract Ancient Greek definitions from:\n"
            f"  {morphology_file.parent / 'all_greek_wiktionary_pages.json'}\n"
            f"The file should contain definitions for ~48,486 Ancient Greek words."
        )

    print("Loading Wiktionary definitions...")
    with open(definitions_file, 'r', encoding='utf-8') as f:
        definitions_data = json.load(f)
    print(f"Found {len(definitions_data)} definition entries")
    
    # Load LSJ and Cunliffe as fallback sources for better definitions
    lsj_data = {}
    if lsj_file.exists():
        print("Loading LSJ dictionary...")
        with open(lsj_file, 'r', encoding='utf-8') as f:
            lsj_data = json.load(f)
        print(f"Found {len(lsj_data)} LSJ entries")
    
    cunliffe_data = {}
    if cunliffe_file.exists():
        print("Loading Cunliffe dictionary...")
        with open(cunliffe_file, 'r', encoding='utf-8') as f:
            cunliffe_data = json.load(f)
        print(f"Found {len(cunliffe_data)} Cunliffe entries")
    
    # Create dictionary entries for ALL lemmas
    dictionary_data = {}
    lemmas_with_defs = 0
    lemmas_without_defs = 0
    
    # First pass: create entries for all lemmas
    for lemma, forms in lemma_to_forms.items():
        inflected_forms = sorted(list(forms))
        
        # Look for definition
        definition = ""
        
        # Try to find definition for this lemma
        if lemma in definitions_data:
            entry = definitions_data[lemma]
            # Handle different possible formats
            if isinstance(entry, dict):
                if 'entry_plain' in entry:
                    definition = entry['entry_plain']
                elif 'definitions' in entry:
                    definition = format_definition(entry)
                else:
                    definition = format_definition(entry)
            else:
                definition = format_definition(entry)
            
            if definition and "orphological entry" not in definition:
                lemmas_with_defs += 1
            else:
                definition = ""  # Reset if it's a placeholder
        else:
            # Try without clean punctuation in case definitions use different conventions
            for headword, entry in definitions_data.items():
                if clean_punctuation(headword) == lemma:
                    if isinstance(entry, dict) and 'entry_plain' in entry:
                        definition = entry['entry_plain']
                    else:
                        definition = format_definition(entry)
                    
                    if definition and "orphological entry" not in definition:
                        lemmas_with_defs += 1
                    break
        
        if not definition:
            # Try with simplified lemma (removing macrons/breves)
            simplified = simplify_lemma(lemma)
            if simplified != lemma:
                # First check if simplified form exists in definitions
                if simplified in definitions_data:
                    entry = definitions_data[simplified]
                    definition = format_definition(entry)
                    lemmas_with_defs += 1
                # Then check LSJ with simplified form
                elif simplified in lsj_data:
                    definition = lsj_data[simplified].get("definition", "")
                    if definition:
                        lemmas_with_defs += 1
                        print(f"  Found LSJ definition for {lemma} via simplified {simplified}")
                # Then check Cunliffe
                elif simplified in cunliffe_data:
                    definition = cunliffe_data[simplified].get("definition", "")
                    if definition:
                        lemmas_with_defs += 1
                        print(f"  Found Cunliffe definition for {lemma} via simplified {simplified}")
            
        if not definition:
            # Try to find definition in Wiktionary's own definitions, LSJ or Cunliffe
            # Try multiple normalizations
            candidates = [lemma]
            
            # Add simplified form
            simplified = simplify_lemma(lemma)
            if simplified != lemma:
                candidates.append(simplified)
            
            # Try without accents  
            import unicodedata
            nfd = unicodedata.normalize('NFD', lemma)
            no_accents = ''.join(c for c in nfd if not unicodedata.combining(c))
            if no_accents not in candidates:
                candidates.append(no_accents)
            
            # Try variations with standard accent patterns
            # (removed hardcoded specific mappings)
            
            # Search in priority order: Wiktionary's own data, Cunliffe, LSJ, then placeholder
            for candidate in candidates:
                # First check Wiktionary's own definitions
                if candidate in definitions_data and candidate != lemma:
                    entry = definitions_data[candidate]
                    candidate_def = format_definition(entry)
                    if candidate_def and "orphological entry" not in candidate_def:
                        definition = candidate_def
                        lemmas_with_defs += 1
                        print(f"  Found Wiktionary definition for {lemma} via {candidate}")
                        break
                elif candidate in cunliffe_data:
                    definition = cunliffe_data[candidate].get("definition", "")
                    if definition:
                        lemmas_with_defs += 1
                        print(f"  Found Cunliffe definition for {lemma} via {candidate}")
                        break
                elif candidate in lsj_data:
                    definition = lsj_data[candidate].get("definition", "")
                    if definition:
                        lemmas_with_defs += 1
                        print(f"  Found LSJ definition for {lemma} via {candidate}")
                        break
            
        if not definition:
            # Only create placeholder if we really can't find anything
            info = lemma_info.get(lemma, {})
            pos = info.get('pos', 'unknown')
            
            # Check if this is a patronymic
            if lemma.endswith(('άδης', 'ίδης', 'ιάδης')):
                definition = f"Patronymic name (son of {lemma[:-4]})"
            # Check for other name patterns
            elif lemma[0].isupper() and pos == 'noun':
                definition = f"Proper name"
            # Check for specific parts of speech
            elif pos == 'verb':
                definition = f"Verb (morphological entry)"
            elif pos == 'noun':
                definition = f"Noun (morphological entry)"
            elif pos == 'adj':
                definition = f"Adjective (morphological entry)"
            elif pos == 'adv':
                definition = f"Adverb (morphological entry)"
            elif pos == 'prep':
                definition = f"Preposition (morphological entry)"
            elif pos == 'conj':
                definition = f"Conjunction (morphological entry)"
            elif pos == 'pron':
                definition = f"Pronoun (morphological entry)"
            elif pos == 'particle':
                definition = f"Particle (morphological entry)"
            else:
                definition = f"Morphological entry"
            
            lemmas_without_defs += 1
        
        # Create entry with normalized lemma (no macrons/breves)
        normalized_lemma = simplify_lemma(lemma)
        
        # If the normalized form already exists with a real definition, skip this entry
        if normalized_lemma in dictionary_data and dictionary_data[normalized_lemma]["definition"] != "Morphological entry":
            print(f"  Skipping {lemma} - normalized form {normalized_lemma} already exists")
            continue
            
        # Otherwise create/update the entry under the normalized form
        if normalized_lemma not in dictionary_data or dictionary_data[normalized_lemma]["definition"] == "Morphological entry":
            dictionary_data[normalized_lemma] = {
                "inflected_forms": inflected_forms,
                "definition": definition
            }
    
    # Second pass: add entries for ALL words in comprehensive definitions file
    # This captures the 48k definitions that don't have inflected forms
    comprehensive_added = 0
    for word, entry in definitions_data.items():
        cleaned_word = clean_punctuation(word)
        if cleaned_word and cleaned_word not in dictionary_data:
            # Extract definition
            if isinstance(entry, dict) and 'entry_plain' in entry:
                definition = entry['entry_plain']
            else:
                definition = format_definition(entry)

            if definition and len(definition) > 2:
                dictionary_data[cleaned_word] = {
                    "inflected_forms": [],
                    "definition": definition
                }
                comprehensive_added += 1

    print(f"Added {comprehensive_added} entries from comprehensive Wiktionary definitions")

    # Third pass: add entries for inflected forms that map to non-existent lemmas
    # This ensures every word can be looked up
    orphan_forms = set()
    for mapping in mappings:
        word_form = clean_punctuation(mapping.get('word_form', ''))
        lemma = clean_punctuation(mapping.get('lemma', ''))

        if word_form and lemma and lemma not in dictionary_data:
            orphan_forms.add(word_form)

    print(f"Found {len(orphan_forms)} orphan forms (forms whose lemmas aren't in dictionary)")

    # Add orphan forms as their own entries
    for form in orphan_forms:
        if form not in dictionary_data:  # Don't overwrite existing entries
            dictionary_data[form] = {
                "inflected_forms": [],
                "definition": "Inflected form (morphological entry)"
            }

    print(f"\nCreated {len(dictionary_data)} dictionary entries:")
    print(f"  - {lemmas_with_defs} with definitions from lemmas with inflected forms")
    print(f"  - {comprehensive_added} from comprehensive Wiktionary definitions")
    print(f"  - {lemmas_without_defs} morphology-only entries")
    print(f"  - {len(orphan_forms)} orphan form entries")
    
    # Count total inflected forms
    total_forms = sum(len(entry['inflected_forms']) for entry in dictionary_data.values())
    print(f"Total inflected forms: {total_forms}")
    
    return dictionary_data

def format_definition(entry):
    """Format Wiktionary definition entry"""
    definition_parts = []
    
    # Add part of speech if available
    if 'part_of_speech' in entry:
        definition_parts.append(f"[{entry['part_of_speech']}]")
    
    # Add etymology if available
    if 'etymology' in entry and entry['etymology']:
        etym_text = entry['etymology']
        if isinstance(etym_text, list):
            etym_text = ' '.join(etym_text)
        # Clean up HTML/wiki markup
        etym_text = re.sub(r'<[^>]+>', '', etym_text)
        etym_text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', etym_text)
        etym_text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', etym_text)
        if etym_text.strip():
            definition_parts.append(f"Etymology: {etym_text.strip()}")
    
    # Add definitions
    if 'definitions' in entry and entry['definitions']:
        for i, defn in enumerate(entry['definitions'], 1):
            if isinstance(defn, dict):
                defn_text = defn.get('definition', '')
            else:
                defn_text = str(defn)
            
            # Clean up markup
            defn_text = re.sub(r'<[^>]+>', '', defn_text)
            defn_text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', defn_text)
            defn_text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', defn_text)
            
            if defn_text.strip():
                definition_parts.append(f"{i}. {defn_text.strip()}")
    
    return '\n'.join(definition_parts) if definition_parts else ""

def verify_extraction(dictionary_data):
    """Verify extraction quality by checking known entries"""
    print("\nVerifying extraction quality...")
    
    # Check for μῆνιν specifically
    if 'μῆνιν' in dictionary_data:
        print("✓ Found μῆνιν as headword")
        entry = dictionary_data['μῆνιν']
        print(f"  Definition: {entry['definition'][:100]}...")
        print(f"  Inflected forms: {entry['inflected_forms'][:5]}...")
    else:
        print("✗ μῆνιν not found as headword")
    
    if 'μῆνις' in dictionary_data:
        print("✓ Found μῆνις as headword")
        forms = dictionary_data['μῆνις']['inflected_forms']
        if 'μῆνιν' in forms:
            print("  ✓ μῆνιν is an inflected form of μῆνις")
        else:
            print("  ✗ μῆνιν NOT in inflected forms of μῆνις")
        print(f"  Inflected forms ({len(forms)}): {forms[:5]}...")
    
    # Check other important words
    test_words = ['εἰμί', 'ἔχω', 'λέγω', 'λαμβάνω', 'ποιέω']
    print("\nCommon verbs:")
    for word in test_words:
        if word in dictionary_data:
            forms = dictionary_data[word]['inflected_forms']
            print(f"  {word}: {len(forms)} inflected forms")
        else:
            print(f"  {word}: NOT FOUND")

def main():
    # Extract all Wiktionary data
    dictionary_data = extract_wiktionary_data()
    
    if not dictionary_data:
        print("No data extracted!")
        return
    
    # Verify extraction
    verify_extraction(dictionary_data)
    
    # Save to JSON
    output_path = Path(__file__).parent / "extract_wiktionary_final.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dictionary_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved extracted data to {output_path}")
    
    # Show sample entries
    print("\nSample entries:")
    for i, (headword, data) in enumerate(list(dictionary_data.items())[:5]):
        print(f"\n{headword}:")
        print(f"  Inflected forms ({len(data['inflected_forms'])}): {data['inflected_forms'][:5]}...")
        print(f"  Definition: {data['definition'][:100]}...")

if __name__ == "__main__":
    main()