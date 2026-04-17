#!/usr/bin/env python3
"""
Add grave accent variants for all lemma mappings with acute accents.
This handles the Greek orthographic rule where acute accents become grave
in certain positions, especially in poetry.
"""

import json
import unicodedata

def convert_acute_to_grave(text):
    """
    Convert all acute accents to grave accents in a Greek text.
    Handles all Unicode combinations including:
    - Simple acute (΄) to grave (`)
    - Combined characters (e.g., ά to ὰ)
    - Characters with breathing marks (e.g., ἄ to ἂ, ἅ to ἃ)
    - Characters with iota subscript (e.g., ᾴ to ᾲ)
    - All combinations (e.g., ᾅ to ᾃ)
    """
    # Unicode substitution mapping for all Greek characters with acute to grave
    acute_to_grave_map = {
        # Lowercase vowels with acute only
        'ά': 'ὰ',  # alpha
        'έ': 'ὲ',  # epsilon
        'ή': 'ὴ',  # eta
        'ί': 'ὶ',  # iota
        'ό': 'ὸ',  # omicron
        'ύ': 'ὺ',  # upsilon
        'ώ': 'ὼ',  # omega
        
        # Lowercase vowels with smooth breathing and acute
        'ἄ': 'ἂ',  # alpha
        'ἔ': 'ἒ',  # epsilon
        'ἤ': 'ἢ',  # eta
        'ἴ': 'ἲ',  # iota
        'ὄ': 'ὂ',  # omicron
        'ὔ': 'ὒ',  # upsilon
        'ὤ': 'ὢ',  # omega
        
        # Lowercase vowels with rough breathing and acute
        'ἅ': 'ἃ',  # alpha
        'ἕ': 'ἓ',  # epsilon
        'ἥ': 'ἣ',  # eta
        'ἵ': 'ἳ',  # iota
        'ὅ': 'ὃ',  # omicron
        'ὕ': 'ὓ',  # upsilon
        'ὥ': 'ὣ',  # omega
        
        # Lowercase vowels with iota subscript and acute
        'ᾴ': 'ᾲ',  # alpha
        'ῄ': 'ῂ',  # eta
        'ῴ': 'ῲ',  # omega
        
        # Lowercase vowels with smooth breathing, iota subscript and acute
        'ᾄ': 'ᾂ',  # alpha
        'ᾔ': 'ᾒ',  # eta
        'ᾤ': 'ᾢ',  # omega
        
        # Lowercase vowels with rough breathing, iota subscript and acute
        'ᾅ': 'ᾃ',  # alpha
        'ᾕ': 'ᾓ',  # eta
        'ᾥ': 'ᾣ',  # omega
        
        # Uppercase vowels with acute
        'Ά': 'Ὰ',  # Alpha
        'Έ': 'Ὲ',  # Epsilon
        'Ή': 'Ὴ',  # Eta
        'Ί': 'Ὶ',  # Iota
        'Ό': 'Ὸ',  # Omicron
        'Ύ': 'Ὺ',  # Upsilon
        'Ώ': 'Ὼ',  # Omega
        
        # Uppercase vowels with smooth breathing and acute
        'Ἄ': 'Ἂ',  # Alpha
        'Ἔ': 'Ἒ',  # Epsilon
        'Ἤ': 'Ἢ',  # Eta
        'Ἴ': 'Ἲ',  # Iota
        'Ὄ': 'Ὂ',  # Omicron
        'Ὤ': 'Ὢ',  # Omega
        
        # Uppercase vowels with rough breathing and acute
        'Ἅ': 'Ἃ',  # Alpha
        'Ἕ': 'Ἓ',  # Epsilon
        'Ἥ': 'Ἣ',  # Eta
        'Ἵ': 'Ἳ',  # Iota
        'Ὅ': 'Ὃ',  # Omicron
        'Ὕ': 'Ὓ',  # Upsilon
        'Ὥ': 'Ὣ',  # Omega
        
        # Uppercase vowels with iota subscript and acute
        'ᾼ': 'ᾊ',  # Alpha with prosgegrammeni (capital iota subscript shows as adscript)
        'ῌ': 'Ὴ',  # Eta with prosgegrammeni
        'ῼ': 'Ὼ',  # Omega with prosgegrammeni
        
        # Uppercase vowels with smooth breathing and iota subscript/adscript and acute
        'ᾌ': 'ᾊ',  # Alpha
        'ᾜ': 'ᾚ',  # Eta
        'ᾬ': 'ᾪ',  # Omega
        
        # Uppercase vowels with rough breathing and iota subscript/adscript and acute
        'ᾍ': 'ᾋ',  # Alpha
        'ᾝ': 'ᾛ',  # Eta
        'ᾭ': 'ᾫ',  # Omega
        
        # Rho with breathing marks
        'ῤ': 'ῤ',  # rho with smooth (no change needed)
        'ῥ': 'ῥ',  # rho with rough (no change needed)
        'Ῥ': 'Ῥ',  # Rho with rough (no change needed)
    }
    
    # Apply the mapping
    result = text
    for acute, grave in acute_to_grave_map.items():
        result = result.replace(acute, grave)
    
    return result

def has_acute_accent(text):
    """Check if text contains any acute accent"""
    acute_chars = set(['ά', 'έ', 'ή', 'ί', 'ό', 'ύ', 'ώ', 'Ά', 'Έ', 'Ή', 'Ί', 'Ό', 'Ύ', 'Ώ',
                      'ἄ', 'ἔ', 'ἤ', 'ἴ', 'ὄ', 'ὔ', 'ὤ', 'ἅ', 'ἕ', 'ἥ', 'ἵ', 'ὅ', 'ὕ', 'ὥ',
                      'Ἄ', 'Ἔ', 'Ἤ', 'Ἴ', 'Ὄ', 'Ὤ', 'Ἅ', 'Ἕ', 'Ἥ', 'Ἵ', 'Ὅ', 'Ὕ', 'Ὥ',
                      'ᾴ', 'ῄ', 'ῴ', 'ᾄ', 'ᾔ', 'ᾤ', 'ᾅ', 'ᾕ', 'ᾥ',
                      'ᾼ', 'ῌ', 'ῼ', 'ᾌ', 'ᾜ', 'ᾬ', 'ᾍ', 'ᾝ', 'ᾭ'])
    
    return any(char in acute_chars for char in text)

def process_lemma_mappings(input_file, output_file):
    """Add grave accent variants for all mappings with acute accents"""
    
    print(f"Loading lemma mappings from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    print(f"Found {len(mappings)} original mappings")
    
    # Track statistics
    acute_forms = 0
    new_mappings = []
    existing_graves = set()
    
    # First pass: collect existing grave forms to avoid duplicates
    for mapping in mappings:
        word_form = mapping.get('word_form', '')
        if word_form and not has_acute_accent(word_form):
            existing_graves.add(word_form)
    
    # Second pass: create grave variants
    for mapping in mappings:
        word_form = mapping.get('word_form', '')
        
        if word_form and has_acute_accent(word_form):
            grave_form = convert_acute_to_grave(word_form)
            
            # Only add if different and not already existing
            if grave_form != word_form and grave_form not in existing_graves:
                acute_forms += 1
                
                # Create new mapping with grave accent
                new_mapping = mapping.copy()
                new_mapping['word_form'] = grave_form
                new_mapping['original_form'] = word_form  # Track what it came from
                new_mapping['accent_variant'] = True      # Mark as accent variant
                
                new_mappings.append(new_mapping)
                existing_graves.add(grave_form)
    
    print(f"\nFound {acute_forms} word forms with acute accents")
    print(f"Created {len(new_mappings)} new grave accent variants")
    
    # Combine original and new mappings
    all_mappings = mappings + new_mappings
    
    print(f"Total mappings: {len(all_mappings)}")
    
    # Show some example conversions
    print("\nExample conversions:")
    examples_shown = 0
    for mapping in mappings[:100]:  # Check first 100 mappings for examples
        word = mapping.get('word_form', '')
        if word and has_acute_accent(word) and examples_shown < 5:
            grave = convert_acute_to_grave(word)
            print(f"  {word} → {grave}")
            examples_shown += 1
    
    # Save combined mappings
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_mappings, f, ensure_ascii=False, indent=2)
    
    print("Done!")
    
    return all_mappings

def main():
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_with_graves.json')
    else:
        input_file = 'combine_dictionaries_to_lemma_map_2.json'
        output_file = 'add_grave_accent_variants.json'
    
    process_lemma_mappings(input_file, output_file)

if __name__ == "__main__":
    main()