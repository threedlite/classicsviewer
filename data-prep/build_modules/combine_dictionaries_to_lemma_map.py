#!/usr/bin/env python3
"""
Combine dictionary data from Cunliffe, LSJ, and Wiktionary to create:
1. dictionary_entries table data
2. lemma_map table data

This creates the final JSON files that will be imported into the SQLite database.
"""

import json
from pathlib import Path
from typing import Dict, List, Set

def clean_punctuation(text):
    """Remove only punctuation (period, comma, semi-colon, raised dot), keep diacritics"""
    import re
    return re.sub(r'[.,;·]', '', text)

def load_json_file(filepath: Path) -> Dict:
    """Load a JSON file - raises exception if not found"""
    if not filepath.exists():
        raise FileNotFoundError(f"Required JSON file not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_extraction_scripts():
    """Run all extraction scripts to generate fresh JSON files"""
    # Import the extraction modules
    import extract_cunliffe_new
    import extract_lsj_fixed
    import extract_wiktionary_final
    
    extractions = [
        (extract_cunliffe_new.main, "Extracting Cunliffe dictionary"),
        (extract_lsj_fixed.main, "Extracting LSJ dictionary"),
        (extract_wiktionary_final.main, "Extracting Wiktionary data")
    ]
    
    for extract_func, description in extractions:
        print(f"\n{description}...")
        try:
            extract_func()
            print(f"✓ {description} completed successfully")
        except Exception as e:
            print(f"ERROR: {description} failed: {str(e)}")
            raise RuntimeError(f"Extraction failed: {description}") from e

def run_variant_generation_scripts():
    """Run scripts to generate variant mappings (grave accents, enclitics, etc.)"""
    # Import the variant generation modules
    import normalize_unicode
    import add_grave_accent_variants
    import add_enclitic_variants
    
    # Run normalize first
    print(f"\nNormalizing Unicode to NFC...")
    try:
        normalize_unicode.main()
        print(f"✓ Unicode normalization completed successfully")
    except Exception as e:
        print(f"ERROR: Unicode normalization failed: {str(e)}")
        raise RuntimeError(f"Unicode normalization failed") from e
    
    # Then add grave accents
    print(f"\nAdding grave accent variants...")
    try:
        # Use the normalized file as input
        add_grave_accent_variants.process_lemma_mappings(
            'combine_dictionaries_to_lemma_map_2.json',
            'add_grave_accent_variants.json'
        )
        print(f"✓ Grave accent variants added successfully")
    except Exception as e:
        print(f"ERROR: Grave accent generation failed: {str(e)}")
        raise RuntimeError(f"Grave accent generation failed") from e
    
    # Finally add enclitics
    print(f"\nAdding enclitic variants...")
    try:
        add_enclitic_variants.main()
        print(f"✓ Enclitic variants added successfully")
    except Exception as e:
        print(f"ERROR: Enclitic variant generation failed: {str(e)}")
        raise RuntimeError(f"Enclitic variant generation failed") from e

def combine_dictionaries():
    """Combine all three dictionary sources"""
    
    # Always run extraction scripts to generate fresh JSON files
    print("=== Running extraction scripts to generate fresh data ===")
    run_extraction_scripts()
    
    # Load all dictionary files
    cunliffe_data = load_json_file(Path(__file__).parent / "extract_cunliffe_new.json")
    lsj_data = load_json_file(Path(__file__).parent / "extract_lsj_fixed.json")
    wiktionary_data = load_json_file(Path(__file__).parent / "extract_wiktionary_final.json")
    
    print(f"Loaded data:")
    print(f"  Cunliffe: {len(cunliffe_data)} entries")
    print(f"  LSJ: {len(lsj_data)} entries")
    print(f"  Wiktionary: {len(wiktionary_data)} entries")
    
    # Combine dictionary entries
    # Priority: Cunliffe > LSJ > Wiktionary
    dictionary_entries = {}
    lemma_mappings = []
    
    # PERFORMANCE FIX: Use a set for O(1) duplicate checking
    seen_mappings = set()
    
    # Process Cunliffe (highest priority for Homeric texts)
    print("\nProcessing Cunliffe entries...")
    for headword, data in cunliffe_data.items():
        dictionary_entries[headword] = {
            "headword": headword,
            "language": "greek",
            "entry_plain": data["definition"],
            "entry_html": f"<div class='definition'>{data['definition']}</div>",
            "source": "cunliffe"
        }
        
        # Always create self-mapping for headwords
        lemma_mappings.append({
            "word_form": headword,
            "lemma": headword,
            "confidence": 1.0,
            "source": "cunliffe",
            "morph_info": None
        })
        
        # Create lemma mappings for inflected forms
        for form in data["inflected_forms"]:
            if form != headword:  # Avoid duplicate self-mapping
                lemma_mappings.append({
                    "word_form": form,
                    "lemma": headword,
                    "confidence": 0.95,
                    "source": "cunliffe",
                    "morph_info": None
                })
    
    # Process LSJ (general Greek dictionary)
    print("\nProcessing LSJ entries...")
    for headword, data in lsj_data.items():
        if headword not in dictionary_entries:  # Don't override Cunliffe
            dictionary_entries[headword] = {
                "headword": headword,
                "language": "greek",
                "entry_plain": data["definition"],
                "entry_html": f"<div class='definition'>{data['definition']}</div>",
                "source": "lsj"
            }
            
            # Create self-mapping for new headwords
            lemma_mappings.append({
                "word_form": headword,
                "lemma": headword,
                "confidence": 1.0,
                "source": "lsj",
                "morph_info": None
            })
        
        # Create lemma mappings for inflected forms
        for form in data["inflected_forms"]:
            if form != headword:  # Avoid duplicate self-mapping
                # Check if this mapping already exists from Cunliffe
                existing = any(m["word_form"] == form and m["lemma"] == headword 
                             for m in lemma_mappings)
                if not existing:
                    lemma_mappings.append({
                        "word_form": form,
                        "lemma": headword,
                        "confidence": 0.90,
                        "source": "lsj",
                        "morph_info": None
                    })
    
    # Process Wiktionary (fallback for missing entries)
    print("\nProcessing Wiktionary entries...")
    wiktionary_skipped = 0
    for headword, data in wiktionary_data.items():
        if headword not in dictionary_entries:  # Don't override Cunliffe or LSJ
            definition = data["definition"]
            
            # Skip creating dictionary entries for inflected forms that are just morphological placeholders
            # These should use their lemma's definition instead
            # If we have a morphological placeholder, we need to find the real definition
            if "Morphological entry" in definition:
                # Try multiple normalizations to find a real definition
                candidates = []
                
                # First try without breve/macron marks (simple replacement)
                normalized = headword.replace("ῠ", "υ").replace("ῡ", "υ").replace("ᾱ", "α").replace("ᾰ", "α").replace("ῐ", "ι").replace("ῑ", "ι")
                if normalized != headword:
                    candidates.append(normalized)
                
                # More comprehensive removal of macrons and breves using Unicode normalization
                import unicodedata
                nfd = unicodedata.normalize('NFD', headword)
                # Remove combining macrons (U+0304) and breves (U+0306)
                no_macron_breve = ''.join(c for c in nfd if not (unicodedata.combining(c) and ord(c) in [0x0304, 0x0306]))
                if no_macron_breve not in candidates and no_macron_breve != headword:
                    candidates.append(no_macron_breve)
                
                # Also try normalizing all combining accents
                nfd = unicodedata.normalize('NFD', normalized)
                # Remove combining accents but keep base characters
                no_accents = ''.join(c for c in nfd if not unicodedata.combining(c))
                candidates.append(no_accents)
                
                # Try with standard acute accent  
                if headword.endswith('ς'):
                    candidates.append(no_accents + 'ς')
                else:
                    candidates.append(no_accents)
                
                # Try variations with standard accent patterns
                # (removed hardcoded specific mappings)
                
                # Search for real definitions in priority order
                found_definition = False
                found_normalized_form = None
                for candidate in candidates:
                    if candidate == headword:
                        continue
                        
                    # Check existing dictionary entries first
                    if candidate in dictionary_entries:
                        existing_entry = dictionary_entries[candidate]
                        definition = existing_entry.get("entry_plain", definition)
                        print(f"  Found real definition for {headword} from {candidate} in dictionary_entries")
                        found_definition = True
                        found_normalized_form = candidate
                        break
                    
                    # Check LSJ
                    elif candidate in lsj_data:
                        definition = lsj_data[candidate].get("definition", "")
                        if definition:
                            print(f"  Found LSJ definition for {headword} via {candidate}")
                            found_definition = True
                            found_normalized_form = candidate
                            break
                    
                    # Check Cunliffe
                    elif candidate in cunliffe_data:
                        definition = cunliffe_data[candidate].get("definition", "")
                        if definition:
                            print(f"  Found Cunliffe definition for {headword} via {candidate}")
                            found_definition = True
                            found_normalized_form = candidate
                            break
                
                # If we found a normalized form with a real definition, use that definition
                if found_normalized_form and found_normalized_form != headword and found_definition:
                    print(f"  Fixed definition for {headword} using {found_normalized_form}")
                    # Use the real definition we found instead of the placeholder
                    # But keep the headword as-is for now (we'll fix this properly below)
            
            dictionary_entries[headword] = {
                "headword": headword,
                "language": "greek",
                "entry_plain": definition,
                "entry_html": f"<div class='definition'>{definition}</div>" if not definition.startswith("Etymology:") else definition,
                "source": "wiktionary"
            }
            
            # Create self-mapping for new headwords
            lemma_mappings.append({
                "word_form": headword,
                "lemma": headword,
                "confidence": 1.0,
                "source": "wiktionary",
                "morph_info": None
            })
        
        # Create lemma mappings for inflected forms
        for form in data["inflected_forms"]:
            if form != headword:  # Avoid duplicate self-mapping
                # Check if this mapping already exists
                existing = any(m["word_form"] == form and m["lemma"] == headword 
                             for m in lemma_mappings)
                if not existing:
                    lemma_mappings.append({
                        "word_form": form,
                        "lemma": headword,
                        "confidence": 0.85,
                        "source": "wiktionary",
                        "morph_info": None
                    })
    
    # Load and add Wiktionary morphology mappings from combined morphology
    morphology_file = Path(__file__).parent.parent / "wiktionary-processing" / "combine_all_ancient_greek_morphology.json"
    if not morphology_file.exists():
        raise FileNotFoundError(f"Required morphology file not found: {morphology_file}")
    
    print("\nAdding Wiktionary morphology mappings...")
    with open(morphology_file, 'r', encoding='utf-8') as f:
        morphology_data = json.load(f)
        
        # Handle the morphology data format
        if isinstance(morphology_data, dict) and 'mappings' in morphology_data:
            morphology_list = morphology_data['mappings']
        else:
            print("Warning: Unexpected morphology data format")
            morphology_list = []
        
        for entry in morphology_list:
            if not isinstance(entry, dict):
                continue
                
            word_form = entry.get('word_form', '')
            word_form_clean = clean_punctuation(word_form)
            lemma = entry.get('lemma', word_form)
            lemma_clean = clean_punctuation(lemma)
            
            if word_form_clean != lemma_clean:  # Don't create self-mapping
                # Check if this mapping already exists
                existing = any(m["word_form"] == word_form_clean and m["lemma"] == lemma_clean 
                             for m in lemma_mappings)
                if not existing:
                    # Create morph_info string from the morphological data
                    morph_parts = []
                    if 'morph_type' in entry:
                        morph_parts.append(entry['morph_type'])
                    if 'source' in entry:
                        morph_parts.append(f"from {entry['source']}")
                    
                    lemma_mappings.append({
                        "word_form": word_form_clean,
                        "lemma": lemma_clean,
                        "confidence": 0.80,
                        "source": "wiktionary_morph",
                        "morph_info": ', '.join(morph_parts) if morph_parts else None
                    })
    
    print(f"\nCombined results:")
    print(f"  Dictionary entries: {len(dictionary_entries)}")
    print(f"  Lemma mappings: {len(lemma_mappings)}")
    if wiktionary_skipped > 0:
        print(f"  Skipped {wiktionary_skipped} Wiktionary inflected forms (will resolve through lemma_map)")
    
    # Save dictionary entries
    dict_output = Path(__file__).parent / "combine_dictionaries_to_lemma_map_1.json"
    with open(dict_output, 'w', encoding='utf-8') as f:
        json.dump(dictionary_entries, f, ensure_ascii=False, indent=2)
    print(f"\nSaved dictionary entries to {dict_output}")
    
    # Save lemma mappings
    lemma_output = Path(__file__).parent / "combine_dictionaries_to_lemma_map_2.json"
    with open(lemma_output, 'w', encoding='utf-8') as f:
        json.dump(lemma_mappings, f, ensure_ascii=False, indent=2)
    print(f"Saved lemma mappings to {lemma_output}")
    
    # Always run variant generation scripts
    print("\n=== Running variant generation scripts ===")
    run_variant_generation_scripts()
    print("\n✓ All variant files generated successfully")
    
    # Show statistics
    print("\nSource distribution in dictionary entries:")
    source_counts = {}
    for entry in dictionary_entries.values():
        source = entry["source"]
        source_counts[source] = source_counts.get(source, 0) + 1
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")
    
    print("\nSource distribution in lemma mappings:")
    source_counts = {}
    for mapping in lemma_mappings:
        source = mapping["source"]
        source_counts[source] = source_counts.get(source, 0) + 1
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

if __name__ == "__main__":
    combine_dictionaries()