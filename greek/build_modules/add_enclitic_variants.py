#!/usr/bin/env python3
"""
Add unaccented variants for enclitic words.
Enclitics in Greek often appear without their accent when they "lean on" the previous word.
"""

import json
import re

def remove_all_accents(text):
    """Remove all accent marks from Greek text"""
    # Map of accented to unaccented characters
    accent_map = {
        # Acute accents
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'Ά': 'Α', 'Έ': 'Ε', 'Ή': 'Η', 'Ί': 'Ι', 'Ό': 'Ο', 'Ύ': 'Υ', 'Ώ': 'Ω',
        
        # Grave accents
        'ὰ': 'α', 'ὲ': 'ε', 'ὴ': 'η', 'ὶ': 'ι', 'ὸ': 'ο', 'ὺ': 'υ', 'ὼ': 'ω',
        'Ὰ': 'Α', 'Ὲ': 'Ε', 'Ὴ': 'Η', 'Ὶ': 'Ι', 'Ὸ': 'Ο', 'Ὺ': 'Υ', 'Ὼ': 'Ω',
        
        # Circumflex
        'ᾶ': 'α', 'ῆ': 'η', 'ῖ': 'ι', 'ῦ': 'υ', 'ῶ': 'ω',
        
        # With breathing marks
        'ἄ': 'ἀ', 'ἔ': 'ἐ', 'ἤ': 'ἠ', 'ἴ': 'ἰ', 'ὄ': 'ὀ', 'ὔ': 'ὐ', 'ὤ': 'ὠ',
        'ἅ': 'ἁ', 'ἕ': 'ἑ', 'ἥ': 'ἡ', 'ἵ': 'ἱ', 'ὅ': 'ὁ', 'ὕ': 'ὑ', 'ὥ': 'ὡ',
        'ἂ': 'ἀ', 'ἒ': 'ἐ', 'ἢ': 'ἠ', 'ἲ': 'ἰ', 'ὂ': 'ὀ', 'ὒ': 'ὐ', 'ὢ': 'ὠ',
        'ἃ': 'ἁ', 'ἓ': 'ἑ', 'ἣ': 'ἡ', 'ἳ': 'ἱ', 'ὃ': 'ὁ', 'ὓ': 'ὑ', 'ὣ': 'ὡ',
        'ἆ': 'ἀ', 'ἦ': 'ἠ', 'ἶ': 'ἰ', 'ὖ': 'ὐ', 'ὦ': 'ὠ',
        'ἇ': 'ἁ', 'ἧ': 'ἡ', 'ἷ': 'ἱ', 'ὗ': 'ὑ', 'ὧ': 'ὡ',
        
        # Capitals with breathing
        'Ἄ': 'Ἀ', 'Ἔ': 'Ἐ', 'Ἤ': 'Ἠ', 'Ἴ': 'Ἰ', 'Ὄ': 'Ὀ', 'Ὤ': 'Ὠ',
        'Ἅ': 'Ἁ', 'Ἕ': 'Ἑ', 'Ἥ': 'Ἡ', 'Ἵ': 'Ἱ', 'Ὅ': 'Ὁ', 'Ὕ': 'Ὑ', 'Ὥ': 'Ὡ',
        'Ἂ': 'Ἀ', 'Ἒ': 'Ἐ', 'Ἢ': 'Ἠ', 'Ἲ': 'Ἰ', 'Ὂ': 'Ὀ', 'Ὢ': 'Ὠ',
        'Ἃ': 'Ἁ', 'Ἓ': 'Ἑ', 'Ἣ': 'Ἡ', 'Ἳ': 'Ἱ', 'Ὃ': 'Ὁ', 'Ὓ': 'Ὑ', 'Ὣ': 'Ὡ',
        
        # With iota subscript
        'ᾴ': 'ᾳ', 'ῄ': 'ῃ', 'ῴ': 'ῳ',
        'ᾲ': 'ᾳ', 'ῂ': 'ῃ', 'ῲ': 'ῳ',
        'ᾷ': 'ᾳ', 'ῇ': 'ῃ', 'ῷ': 'ῳ',
        'ᾄ': 'ᾀ', 'ᾔ': 'ᾐ', 'ᾤ': 'ᾠ',
        'ᾅ': 'ᾁ', 'ᾕ': 'ᾑ', 'ᾥ': 'ᾡ',
        'ᾂ': 'ᾀ', 'ᾒ': 'ᾐ', 'ᾢ': 'ᾠ',
        'ᾃ': 'ᾁ', 'ᾓ': 'ᾑ', 'ᾣ': 'ᾡ',
        'ᾆ': 'ᾀ', 'ᾖ': 'ᾐ', 'ᾦ': 'ᾠ',
        'ᾇ': 'ᾁ', 'ᾗ': 'ᾑ', 'ᾧ': 'ᾡ',
    }
    
    result = text
    for accented, unaccented in accent_map.items():
        result = result.replace(accented, unaccented)
    
    return result

def is_likely_enclitic(word_form, lemma, source):
    """Identify likely enclitic words"""
    # Common enclitic particles, pronouns, and forms
    enclitic_lemmas = {
        # Pronouns
        'μέ', 'μοι', 'μου', 'με',
        'σέ', 'σοι', 'σου', 'σε', 
        'τις', 'τι', 'τινα', 'τινος', 'τινι', 'τινες', 'τινων', 'τισι', 'τινας',
        'σφωέ', 'σφέ', 'σφεῖς', 'σφῶν', 'σφίσι', 'σφέας', 'σφᾶς',
        
        # Particles
        'τε', 'γε', 'δέ', 'πέρ', 'πώ', 'πω', 'πού', 'που', 'πώς', 'πως',
        'νύ', 'νυ', 'τοί', 'τοι',
        
        # Verb forms (εἰμί, φημί)
        'εἰμί', 'ἐστί', 'ἐστέ', 'εἰσί', 'φημί', 'φησί',
        
        # Indefinite adverbs
        'ποτέ', 'ποτε', 'πῇ', 'πῃ', 'ποθέν', 'ποθεν'
    }
    
    # Check if it's an enclitic or could be one
    if lemma in enclitic_lemmas:
        return True
    
    # Check for specific patterns
    if source == 'wiktionary' and 'pronoun' in str(word_form):
        return True
        
    # Check for forms starting with τιν- (indefinite pronoun)
    if word_form.startswith('τιν') or word_form.startswith('τίν'):
        return True
    
    # Check for σφ- pronouns
    if word_form.startswith('σφ'):
        return True
        
    return False

def process_mappings_add_enclitics(input_file, output_file):
    """Add unaccented variants for enclitic words"""
    
    print(f"Loading mappings from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    print(f"Found {len(mappings)} original mappings")
    
    # Track statistics
    enclitic_forms = 0
    new_mappings = []
    existing_unaccented = set()
    
    # First pass: collect existing unaccented forms
    for mapping in mappings:
        word_form = mapping.get('word_form', '')
        if word_form:
            existing_unaccented.add(word_form)
    
    # Second pass: create unaccented variants for enclitics
    for mapping in mappings:
        word_form = mapping.get('word_form', '')
        lemma = mapping.get('lemma', '')
        source = mapping.get('source', '')
        
        if word_form and is_likely_enclitic(word_form, lemma, source):
            unaccented_form = remove_all_accents(word_form)
            
            # Only add if different and not already existing
            if unaccented_form != word_form and unaccented_form not in existing_unaccented:
                enclitic_forms += 1
                
                # Create new mapping
                new_mapping = mapping.copy()
                new_mapping['word_form'] = unaccented_form
                new_mapping['original_form'] = word_form
                new_mapping['enclitic_variant'] = True
                
                new_mappings.append(new_mapping)
                existing_unaccented.add(unaccented_form)
    
    print(f"\nFound {enclitic_forms} enclitic forms")
    print(f"Created {len(new_mappings)} new unaccented variants")
    
    # Combine original and new mappings
    all_mappings = mappings + new_mappings
    
    print(f"Total mappings: {len(all_mappings)}")
    
    # Test specific cases
    print("\nExample conversions:")
    test_words = ['σφωέ', 'τίς', 'ἐστί', 'μέ', 'τέ']
    for word in test_words:
        unaccented = remove_all_accents(word)
        if unaccented != word:
            print(f"  {word} → {unaccented}")
    
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
        output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_with_enclitics.json')
    else:
        # Use the file that already has grave variants
        input_file = 'add_grave_accent_variants.json'
        output_file = 'add_enclitic_variants.json'
    
    process_mappings_add_enclitics(input_file, output_file)

if __name__ == "__main__":
    main()