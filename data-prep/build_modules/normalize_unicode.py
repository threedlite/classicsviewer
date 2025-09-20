#!/usr/bin/env python3
"""
Fix Unicode normalization mismatch between dictionary entries and lemma mappings.
The issue: Dictionary uses precomposed characters (NFC) while lemma mappings use 
combining diacritics (NFD).
"""

import json
import unicodedata
from pathlib import Path

def normalize_to_nfc(text):
    """Normalize text to NFC (precomposed) form"""
    return unicodedata.normalize('NFC', text)

def fix_lemma_mappings():
    """Normalize all lemma forms to NFC to match dictionary entries"""
    
    # Load combined lemma mappings
    mappings_file = Path("combine_dictionaries_to_lemma_map_2.json")
    print(f"Loading {mappings_file}...")
    
    with open(mappings_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    # Track changes
    changes = 0
    examples = []
    
    # Normalize each mapping
    for mapping in mappings:
        old_lemma = mapping['lemma']
        new_lemma = normalize_to_nfc(old_lemma)
        
        if old_lemma != new_lemma:
            mapping['lemma'] = new_lemma
            changes += 1
            if len(examples) < 10:
                examples.append((mapping['word_form'], old_lemma, new_lemma))
        
        # Also normalize word_form for consistency
        mapping['word_form'] = normalize_to_nfc(mapping['word_form'])
    
    print(f"\nNormalized {changes} lemma forms")
    
    if examples:
        print("\nExamples of normalized lemmas:")
        for word_form, old_lemma, new_lemma in examples:
            print(f"  {word_form}: {repr(old_lemma)} → {repr(new_lemma)}")
    
    # Save normalized mappings
    output_file = Path("combined_lemma_mappings_normalized.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved normalized mappings to {output_file}")
    
    # Show some example mappings to verify normalization
    print("\nExample mappings after normalization:")
    examples_shown = 0
    for mapping in mappings[:200]:  # Check first 200 for variety
        if mapping.get('lemma') != mapping.get('word_form') and examples_shown < 5:
            print(f"  {mapping['word_form']} → {mapping['lemma']}")
            examples_shown += 1

def fix_dictionary_entries():
    """Ensure dictionary entries are also normalized to NFC"""
    
    entries_file = Path("combine_dictionaries_to_lemma_map_1.json")
    print(f"\nChecking {entries_file}...")
    
    with open(entries_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    # Check and normalize headwords
    changes = 0
    for headword, entry in list(entries.items()):
        normalized_headword = normalize_to_nfc(headword)
        
        if headword != normalized_headword:
            # Move entry to normalized key
            entries[normalized_headword] = entry
            del entries[headword]
            changes += 1
            print(f"  Normalized: {repr(headword)} → {repr(normalized_headword)}")
    
    if changes > 0:
        print(f"\nNormalized {changes} dictionary headwords")
        
        with open(entries_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        
        print(f"Updated {entries_file}")
    else:
        print("All dictionary entries already use NFC normalization")
    
    # Show some dictionary entries to verify
    print("\nShowing a few dictionary entries after normalization:")
    example_count = 0
    for headword in sorted(entries.keys())[:100]:
        if example_count < 3:
            print(f"  {headword} ({entries[headword]['source']})")
            example_count += 1

if __name__ == "__main__":
    fix_lemma_mappings()
    fix_dictionary_entries()