#!/usr/bin/env python3
"""
Minimal combine script with O(1) duplicate checking using a set
"""

import json
from pathlib import Path

def main():
    # Load already extracted files
    cunliffe_data = {}
    lsj_data = {}
    wiktionary_data = {}
    
    cunliffe_file = Path("extract_cunliffe_new.json")
    if cunliffe_file.exists():
        with open(cunliffe_file, 'r', encoding='utf-8') as f:
            cunliffe_data = json.load(f)
        print(f"Loaded {len(cunliffe_data)} Cunliffe entries")
    
    lsj_file = Path("extract_lsj_fixed.json")
    if lsj_file.exists():
        with open(lsj_file, 'r', encoding='utf-8') as f:
            lsj_data = json.load(f)
        print(f"Loaded {len(lsj_data)} LSJ entries")
    
    wiktionary_file = Path("extract_wiktionary_final.json")
    if wiktionary_file.exists():
        with open(wiktionary_file, 'r', encoding='utf-8') as f:
            wiktionary_data = json.load(f)
        print(f"Loaded {len(wiktionary_data)} Wiktionary entries")
    
    # Combine dictionary entries
    dictionary_entries = {}
    lemma_mappings = []
    
    # PERFORMANCE FIX: Use a set for O(1) duplicate checking
    seen_mappings = set()
    
    # Process Cunliffe (highest priority)
    print("\nProcessing Cunliffe...")
    for headword, data in cunliffe_data.items():
        dictionary_entries[headword] = {
            "headword": headword,
            "language": "greek",
            "entry_plain": data["definition"],
            "entry_html": f"<div class='definition'>{data['definition']}</div>",
            "source": "cunliffe"
        }
        
        # Self-mapping
        mapping_key = (headword, headword)
        if mapping_key not in seen_mappings:
            seen_mappings.add(mapping_key)
            lemma_mappings.append({
                "word_form": headword,
                "lemma": headword,
                "confidence": 1.0,
                "source": "cunliffe",
                "morph_info": None
            })
        
        for form in data.get("inflected_forms", []):
            if form != headword:
                mapping_key = (form, headword)
                if mapping_key not in seen_mappings:
                    seen_mappings.add(mapping_key)
                    lemma_mappings.append({
                        "word_form": form,
                        "lemma": headword,
                        "confidence": 0.95,
                        "source": "cunliffe",
                        "morph_info": None
                    })
    
    # Process LSJ
    print("Processing LSJ...")
    for headword, data in lsj_data.items():
        if headword not in dictionary_entries:
            dictionary_entries[headword] = {
                "headword": headword,
                "language": "greek",
                "entry_plain": data["definition"],
                "entry_html": f"<div class='definition'>{data['definition']}</div>",
                "source": "lsj"
            }
            
            mapping_key = (headword, headword)
            if mapping_key not in seen_mappings:
                seen_mappings.add(mapping_key)
                lemma_mappings.append({
                    "word_form": headword,
                    "lemma": headword,
                    "confidence": 1.0,
                    "source": "lsj",
                    "morph_info": None
                })
        
        for form in data.get("inflected_forms", []):
            if form != headword:
                mapping_key = (form, headword)
                if mapping_key not in seen_mappings:
                    seen_mappings.add(mapping_key)
                    lemma_mappings.append({
                        "word_form": form,
                        "lemma": headword,
                        "confidence": 0.90,
                        "source": "lsj",
                        "morph_info": None
                    })
    
    # Process Wiktionary
    print("Processing Wiktionary...")
    for headword, data in wiktionary_data.items():
        if headword not in dictionary_entries:
            definition = data["definition"]
            # Skip morphological placeholders for inflected forms
            if "orphological entry" in definition and len(data.get("inflected_forms", [])) == 0:
                continue
            
            dictionary_entries[headword] = {
                "headword": headword,
                "language": "greek",
                "entry_plain": definition,
                "entry_html": f"<div class='definition'>{definition}</div>" if not definition.startswith("Etymology:") else definition,
                "source": "wiktionary"
            }
            
            mapping_key = (headword, headword)
            if mapping_key not in seen_mappings:
                seen_mappings.add(mapping_key)
                lemma_mappings.append({
                    "word_form": headword,
                    "lemma": headword,
                    "confidence": 1.0,
                    "source": "wiktionary",
                    "morph_info": None
                })
        
        for form in data.get("inflected_forms", []):
            if form != headword:
                mapping_key = (form, headword)
                if mapping_key not in seen_mappings:
                    seen_mappings.add(mapping_key)
                    lemma_mappings.append({
                        "word_form": form,
                        "lemma": headword,
                        "confidence": 0.85,
                        "source": "wiktionary",
                        "morph_info": None
                    })
    
    print(f"\nTotal dictionary entries: {len(dictionary_entries)}")
    print(f"Total lemma mappings: {len(lemma_mappings)}")
    
    # Save combined dictionary entries
    print("\nSaving combined_dictionary_entries.json...")
    with open("combine_dictionaries_to_lemma_map_1.json", 'w', encoding='utf-8') as f:
        json.dump(dictionary_entries, f, ensure_ascii=False, indent=2)
    
    # Save lemma mappings
    print("Saving combined_lemma_mappings.json...")
    with open("combine_dictionaries_to_lemma_map_2.json", 'w', encoding='utf-8') as f:
        json.dump(lemma_mappings, f, ensure_ascii=False, indent=2)
    
    print("\nDone!")

if __name__ == "__main__":
    main()