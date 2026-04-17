#!/usr/bin/env python3
"""
Combine all Ancient Greek morphological data from Wiktionary
Merges verb conjugations, noun declensions, and existing morphology
"""

import json
from pathlib import Path
from typing import Dict, List, Set
import subprocess
import sys

def load_json_file(path: Path) -> Dict:
    """Load a JSON file - raises exception if not found"""
    if not path.exists():
        raise FileNotFoundError(f"Required JSON file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_extraction_scripts():
    """Run all extraction scripts to generate fresh morphology data"""
    # Import the extraction modules
    import extract_ancient_greek_conjugations
    import extract_ancient_greek_declensions
    import extract_all_ancient_greek_words_with_diacritics
    import extract_inflection_of_template_fixed as extract_inflection_of_template
    import extract_declension_mappings_fixed as extract_declension_mappings
    
    extractions = [
        (extract_ancient_greek_conjugations.main, "Extracting Ancient Greek verb conjugations"),
        (extract_ancient_greek_declensions.main, "Extracting Ancient Greek noun declensions"),
        (extract_all_ancient_greek_words_with_diacritics.main, "Extracting all Ancient Greek words with diacritics"),
        (extract_inflection_of_template.main, "Extracting inflection_of template mappings"),
        (extract_declension_mappings.main, "Extracting declension template mappings")
    ]
    
    for extract_func, description in extractions:
        print(f"\n{description}...")
        try:
            extract_func()
            print(f"✓ {description} completed successfully")
        except Exception as e:
            print(f"ERROR: {description} failed: {str(e)}")
            raise RuntimeError(f"Extraction failed: {description}") from e

def main():
    script_dir = Path(__file__).parent
    
    # Always run extraction scripts first to ensure fresh data
    print("=== Running extraction scripts to generate fresh morphology data ===")
    run_extraction_scripts()
    
    # Load all morphology sources
    print("\nLoading morphology data...")
    
    # 1. Verb conjugations
    verb_data = load_json_file(script_dir / 'extract_ancient_greek_conjugations.json')
    verb_mappings = verb_data.get('mappings', [])
    print(f"  Loaded {len(verb_mappings)} verb forms")
    
    # 2. Noun/adjective declensions
    noun_data = load_json_file(script_dir / 'extract_ancient_greek_declensions.json')
    noun_mappings = noun_data.get('mappings', [])
    print(f"  Loaded {len(noun_mappings)} noun/adjective forms")
    
    # 3. No additional morphology file needed - we have all morphology from other sources
    existing_mappings = []
    
    # 4. Declension mappings (from declension templates)
    decl_data = load_json_file(script_dir / 'extract_declension_mappings.json')
    decl_mappings = decl_data.get('mappings', [])
    print(f"  Loaded {len(decl_mappings)} declension template mappings")
    
    # 5. Inflection mappings
    infl_data = load_json_file(script_dir / 'extract_inflection_of_template.json')
    infl_mappings = infl_data.get('mappings', [])
    print(f"  Loaded {len(infl_mappings)} inflection_of mappings")
    
    # 6. All Ancient Greek words with diacritics (includes standalone lemmas)
    diacritics_data = load_json_file(script_dir / 'extract_all_ancient_greek_words_with_diacritics.json')
    diacritics_mappings = diacritics_data.get('mappings', [])
    print(f"  Loaded {len(diacritics_mappings)} words with diacritics")
    
    # Combine all mappings
    all_mappings = []
    
    # Add verb conjugations (highest priority)
    for mapping in verb_mappings:
        all_mappings.append({
            'word_form': mapping['word_form'],
            'lemma': mapping['lemma'],
            'confidence': mapping.get('confidence', 1.0),
            'source': mapping.get('source', 'wiktionary:grc-conj'),
            'morph_type': 'verb',
            'morph_info': mapping.get('morph_info', ''),
            'priority': 1  # Highest priority for parsed conjugations
        })
    
    # Add noun declensions (high priority)
    for mapping in noun_mappings:
        all_mappings.append({
            'word_form': mapping['word_form'],
            'lemma': mapping['lemma'],
            'confidence': mapping.get('confidence', 1.0),
            'source': mapping.get('source', 'wiktionary:grc-decl'),
            'morph_type': mapping.get('pos', 'noun'),
            'morph_info': mapping.get('morph_info', ''),
            'priority': 2
        })
    
    # Add other morphology data (lower priority)
    for mapping in existing_mappings + decl_mappings + infl_mappings + diacritics_mappings:
        # Skip modern Greek
        if mapping.get('lemma', '').strip() and not any(ord(c) > 0x1FFF for c in mapping['lemma']):
            all_mappings.append({
                'word_form': mapping.get('word_form', ''),
                'lemma': mapping.get('lemma', ''),
                'confidence': mapping.get('confidence', 0.8),
                'source': mapping.get('source', 'wiktionary'),
                'morph_type': mapping.get('morph_type', 'unknown'),
                'morph_info': mapping.get('morph_info', ''),
                'priority': 3
            })
    
    print(f"\nTotal combined mappings: {len(all_mappings)}")
    
    # Keep all mappings - don't deduplicate
    # A word form can map to the same lemma through different morphological analyses
    unique_mappings = all_mappings
    # Remove priority field from final output
    for m in unique_mappings:
        m.pop('priority', None)
    
    print(f"Total mappings: {len(unique_mappings)}")
    
    # Statistics
    lemmas = set(m['lemma'] for m in unique_mappings)
    word_forms = set(m['word_form'] for m in unique_mappings)
    print(f"\nStatistics:")
    print(f"  Unique lemmas: {len(lemmas)}")
    print(f"  Unique word forms: {len(word_forms)}")
    print(f"  Average forms per lemma: {len(unique_mappings) / len(lemmas):.1f}")
    
    # Save combined data
    output_data = {
        'metadata': {
            'source': 'Combined Greek Wiktionary morphological data',
            'extraction_date': '2025-08-15',
            'total_lemmas': len(lemmas),
            'total_word_forms': len(word_forms),
            'total_mappings': len(unique_mappings),
            'sources': [
                'grc-conj verb conjugations',
                'grc-decl noun/adjective declensions',
                'inflection_of templates',
                'declension template mappings'
            ],
            'description': 'Comprehensive Ancient Greek morphology from all Wiktionary sources'
        },
        'mappings': unique_mappings
    }
    
    output_path = script_dir / 'combine_all_ancient_greek_morphology.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved combined morphology to {output_path}")
    print(f"Note: This file is recreated from scratch each time (not loaded from cache)")
    
    # Show examples of different types
    print("\nExample mappings:")
    print("\nVerb forms:")
    verb_examples = [m for m in unique_mappings if m['morph_type'] == 'verb'][:5]
    for m in verb_examples:
        print(f"  {m['word_form']} → {m['lemma']} ({m['morph_info']})")
    
    print("\nNoun forms:")
    noun_examples = [m for m in unique_mappings if m['morph_type'] == 'noun'][:5]
    for m in noun_examples:
        print(f"  {m['word_form']} → {m['lemma']} ({m['morph_info']})")
    
    print("\nAdjective forms:")
    adj_examples = [m for m in unique_mappings if m['morph_type'] == 'adjective'][:5]
    for m in adj_examples:
        print(f"  {m['word_form']} → {m['lemma']} ({m['morph_info']})")

if __name__ == '__main__':
    main()