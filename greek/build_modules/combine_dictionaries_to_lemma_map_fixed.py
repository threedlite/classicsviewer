#!/usr/bin/env python3
"""
Fixed version of combine_dictionaries_to_lemma_map.py with O(1) performance
"""

import json
from pathlib import Path
from typing import Dict, List
import unicodedata

def clean_punctuation(text):
    """Remove punctuation from text, preserving other diacritics"""
    if not text:
        return text
    # Only remove specific punctuation
    return text.replace(".", "").replace(",", "").replace(";", "").replace("·", "")

def load_json_file(path: Path) -> Dict:
    """Load a JSON file - raises exception if not found"""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
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
    
    # Generate normalized versions
    print(f"\nGenerating normalized lemma mappings...")
    try:
        # Import the normalization script
        import normalize_unicode
        
        # First combine to create base files
        base_dict = load_json_file(Path(__file__).parent / "extract_cunliffe_new.json")
        base_dict.update(load_json_file(Path(__file__).parent / "extract_lsj_fixed.json"))
        base_dict.update(load_json_file(Path(__file__).parent / "extract_wiktionary_final.json"))
        
        # Create combined files for normalization
        with open("combine_dictionaries_to_lemma_map_1.json", 'w', encoding='utf-8') as f:
            json.dump(base_dict, f, ensure_ascii=False, indent=2)
        
        # Create empty lemma mappings for normalization
        with open("combine_dictionaries_to_lemma_map_2.json", 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        
        # Run normalization
        normalize_unicode.main()
        print(f"✓ Normalized mappings generated successfully")
    except Exception as e:
        print(f"ERROR: Normalization failed: {str(e)}")
        raise RuntimeError(f"Normalization failed") from e
    
    # Generate grave accent variants
    print(f"\nAdding grave accent variants...")
    try:
        import add_grave_accent_variants
        add_grave_accent_variants.add_grave_variants(
            'combined_lemma_mappings_normalized.json',
            'add_grave_accent_variants.json'
        )
        print(f"✓ Grave accent variants added successfully")
    except Exception as e:
        print(f"ERROR: Grave accent generation failed: {str(e)}")
        raise RuntimeError(f"Grave accent generation failed") from e
    
    # Finally add enclitics
    print(f"\nAdding enclitic variants...")
    try:
        import add_enclitic_variants
        add_enclitic_variants.main()
        print(f"✓ Enclitic variants added successfully")
    except Exception as e:
        print(f"ERROR: Enclitic variant generation failed: {str(e)}")
        raise RuntimeError(f"Enclitic variant generation failed") from e

def combine_dictionaries():
    """Combine all three dictionary sources with O(1) performance"""
    
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
        
        # Create lemma mappings for inflected forms
        for form in data["inflected_forms"]:
            if form != headword:  # Avoid duplicate self-mapping
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
        
        # Create lemma mappings for inflected forms
        for form in data["inflected_forms"]:
            if form != headword:  # Avoid duplicate self-mapping
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
    
    # Process Wiktionary (fallback for missing entries)
    print("\nProcessing Wiktionary entries...")
    wiktionary_skipped = 0
    for headword, data in wiktionary_data.items():
        if headword not in dictionary_entries:  # Don't override Cunliffe or LSJ
            definition = data["definition"]
            
            # Skip creating dictionary entries for inflected forms that are just morphological placeholders
            # These should use their lemma's definition instead
            if "orphological entry" in definition and "inflected_forms" in data and len(data["inflected_forms"]) == 0:
                # This is likely an inflected form, not a real headword
                # Don't create a dictionary entry for it - let it resolve through lemma_map
                wiktionary_skipped += 1
                continue
            
            # If we have a morphological placeholder, check if this is really a lemma or just an inflected form
            if "orphological entry" in definition:
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
                
                # If we found a normalized form with a real definition, don't create a dictionary entry
                # Instead, update lemma mappings to point inflected forms directly to the normalized form
                if found_normalized_form and found_normalized_form != headword:
                    print(f"  Skipping dictionary entry for {headword} - will map to {found_normalized_form} instead")
                    wiktionary_skipped += 1
                    
                    # Create mapping from the variant to the normalized form
                    mapping_key = (headword, found_normalized_form)
                    if mapping_key not in seen_mappings:
                        seen_mappings.add(mapping_key)
                        lemma_mappings.append({
                            "word_form": headword,
                            "lemma": found_normalized_form,  # πολῠ́ς -> πολύς
                            "confidence": 0.95,
                            "source": "wiktionary_normalized",
                            "morph_info": "variant with diacritical marks"
                        })
                    
                    # Update the inflected forms to map directly to the normalized form
                    for form in data["inflected_forms"]:
                        if form != headword:  # Avoid duplicate self-mapping
                            mapping_key = (form, found_normalized_form)
                            if mapping_key not in seen_mappings:
                                seen_mappings.add(mapping_key)
                                lemma_mappings.append({
                                    "word_form": form,
                                    "lemma": found_normalized_form,  # Map directly to the form with real definition
                                    "confidence": 0.85,
                                    "source": "wiktionary",
                                    "morph_info": None
                                })
                    continue  # Skip creating dictionary entry
            
            dictionary_entries[headword] = {
                "headword": headword,
                "language": "greek",
                "entry_plain": definition,
                "entry_html": f"<div class='definition'>{definition}</div>" if not definition.startswith("Etymology:") else definition,
                "source": "wiktionary"
            }
            
            # Create self-mapping for new headwords
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
        
        # Create lemma mappings for inflected forms
        for form in data["inflected_forms"]:
            if form != headword:  # Avoid duplicate self-mapping
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
                mapping_key = (word_form_clean, lemma_clean)
                if mapping_key not in seen_mappings:
                    seen_mappings.add(mapping_key)
                    
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
    
    # Load normalized mappings from previous steps
    normalized_file = Path(__file__).parent / "combined_lemma_mappings_normalized.json"
    if normalized_file.exists():
        print("\nAdding normalized mappings...")
        with open(normalized_file, 'r', encoding='utf-8') as f:
            normalized_mappings = json.load(f)
            for mapping in normalized_mappings:
                word_form = mapping.get('word_form', '')
                lemma = mapping.get('lemma', '')
                
                if word_form and lemma:
                    mapping_key = (word_form, lemma)
                    if mapping_key not in seen_mappings:
                        seen_mappings.add(mapping_key)
                        lemma_mappings.append(mapping)
    
    # Load grave accent variants
    graves_file = Path(__file__).parent / "add_grave_accent_variants.json"
    if graves_file.exists():
        print("\nAdding grave accent variants...")
        with open(graves_file, 'r', encoding='utf-8') as f:
            grave_mappings = json.load(f)
            for mapping in grave_mappings:
                word_form = mapping.get('word_form', '')
                lemma = mapping.get('lemma', '')
                
                if word_form and lemma:
                    mapping_key = (word_form, lemma)
                    if mapping_key not in seen_mappings:
                        seen_mappings.add(mapping_key)
                        lemma_mappings.append(mapping)
    
    # Load enclitic variants
    enclitics_file = Path(__file__).parent / "add_enclitic_variants.json"
    if enclitics_file.exists():
        print("\nAdding enclitic variants...")
        with open(enclitics_file, 'r', encoding='utf-8') as f:
            enclitic_mappings = json.load(f)
            for mapping in enclitic_mappings:
                word_form = mapping.get('word_form', '')
                lemma = mapping.get('lemma', '')
                
                if word_form and lemma:
                    mapping_key = (word_form, lemma)
                    if mapping_key not in seen_mappings:
                        seen_mappings.add(mapping_key)
                        lemma_mappings.append(mapping)
    
    print(f"\nWiktionary entries skipped: {wiktionary_skipped}")
    print(f"Total dictionary entries: {len(dictionary_entries)}")
    print(f"Total lemma mappings: {len(lemma_mappings)}")
    
    # Save combined dictionary entries
    with open("combine_dictionaries_to_lemma_map_1.json", 'w', encoding='utf-8') as f:
        json.dump(dictionary_entries, f, ensure_ascii=False, indent=2)
    
    # Save lemma mappings
    with open("combine_dictionaries_to_lemma_map_2.json", 'w', encoding='utf-8') as f:
        json.dump(lemma_mappings, f, ensure_ascii=False, indent=2)
    
    # Print some statistics
    print("\n=== STATISTICS ===")
    print(f"Dictionary entries by source:")
    source_counts = {}
    for entry in dictionary_entries.values():
        source = entry.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")
    
    print(f"\nLemma mappings by source:")
    mapping_counts = {}
    for mapping in lemma_mappings:
        source = mapping.get("source", "unknown")
        mapping_counts[source] = mapping_counts.get(source, 0) + 1
    for source, count in sorted(mapping_counts.items()):
        print(f"  {source}: {count}")

if __name__ == "__main__":
    combine_dictionaries()