#!/usr/bin/env python3
"""
Extract Greek word form to lemma mappings from Perseus Treebank XML files.
This provides morphological data from hand-annotated linguistic analysis.
Part of the Perseus database build process.
"""

import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text for consistency."""
    if not text:
        return text
    # Remove numbers often appended to lemmas in treebank (e.g., "εἰμί1" -> "εἰμί")
    return text.rstrip('0123456789')

def extract_form_lemma_pairs(xml_file):
    """Extract all form-lemma pairs from a treebank XML file."""
    pairs = []
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Find all word elements regardless of depth
        for word in root.iter('word'):
            form = word.get('form')
            lemma = word.get('lemma')
            postag = word.get('postag', '')
            
            # Skip punctuation (postag starting with 'u' is punctuation)
            if postag and postag.startswith('u'):
                continue
                
            # Skip if form is punctuation
            if form and form in ',.;:!?·—':
                continue
            
            if form and lemma:
                # Normalize the lemma (remove trailing numbers)
                lemma_clean = normalize_greek(lemma)
                
                # Skip non-Greek lemmas (Latin alphabet entries)
                if lemma_clean and not any(c in 'abcdefghijklmnopqrstuvwxyz?' for c in lemma_clean.lower()):
                    if form != lemma_clean:  # Only store if different
                        pairs.append((form, lemma_clean))
    
    except Exception as e:
        print(f"Error processing {xml_file}: {e}")
    
    return pairs

def extract_treebank_lemmas():
    """Process all Greek treebank XML files and extract lemma mappings.
    
    Returns:
        dict: Dictionary mapping forms to lists of possible lemmas
    """
    
    # Paths relative to data-prep directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_prep_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(data_prep_dir)
    treebank_dir = os.path.join(project_root, 'data-sources', 'treebank_data')

    base_path = Path(treebank_dir)
    if not base_path.exists():
        raise FileNotFoundError(f"CRITICAL: Perseus Treebank directory missing: {treebank_dir}\n"
                               "The Perseus Treebank provides high-quality lemma mappings and is required for the build.")
    
    # Dictionary to store form -> set of possible lemmas
    form_to_lemmas = defaultdict(set)
    
    # Statistics
    total_files = 0
    total_pairs = 0
    
    print("Extracting lemmas from Perseus Treebank...")
    
    # Process all Greek XML files
    greek_patterns = ['**/Greek/**/*.xml', '**/greek/**/*.xml', '**/AGDT2/**/*.xml']
    
    for pattern in greek_patterns:
        for xml_file in base_path.glob(pattern):
            # Skip non-text files (like TAGSETS.xml)
            if 'TAGSETS' in str(xml_file) or 'README' in str(xml_file):
                continue
            
            pairs = extract_form_lemma_pairs(xml_file)
            
            for form, lemma in pairs:
                form_to_lemmas[form].add(lemma)
            
            total_files += 1
            total_pairs += len(pairs)
    
    print(f"  Processed {total_files} treebank files")
    print(f"  Found {total_pairs} total form-lemma pairs")
    print(f"  Unique forms with lemmas: {len(form_to_lemmas)}")
    
    # Convert sets to lists for JSON serialization
    result = {form: list(lemmas) for form, lemmas in form_to_lemmas.items()}
    
    return result

def save_treebank_lemmas(output_file='perseus_treebank_lemmas.json'):
    """Extract and save treebank lemmas to a JSON file.
    
    Args:
        output_file: Name of output file (in data-prep directory)
    
    Returns:
        dict: The extracted lemma mappings
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)
    
    # Extract treebank data
    treebank_data = extract_treebank_lemmas()
    
    if treebank_data:
        # Save to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(treebank_data, f, ensure_ascii=False, indent=2)
        print(f"  Saved treebank lemmas to {output_file}")
    
    return treebank_data

def load_treebank_lemmas(input_file='perseus_treebank_lemmas.json'):
    """Load previously extracted treebank lemmas from JSON file.
    
    Args:
        input_file: Name of input file (in data-prep directory)
    
    Returns:
        dict: The lemma mappings, or empty dict if file doesn't exist
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, input_file)
    
    if os.path.exists(input_path):
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

if __name__ == '__main__':
    # When run directly, extract and save the lemmas
    treebank_data = save_treebank_lemmas()
    
    # Print some statistics and samples
    if treebank_data:
        print("\nSample mappings:")
        sample_items = list(treebank_data.items())[:10]
        for form, lemmas in sample_items:
            print(f"  {form} -> {', '.join(lemmas)}")