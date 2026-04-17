#!/usr/bin/env python3
"""Greek text normalization utilities"""

import unicodedata
import re

def normalize_greek(text):
    """Normalize Greek text by removing all diacritics and converting to lowercase
    
    This is the standard normalization used for indexing and searching.
    """
    # First normalize apostrophe variants to a single form
    # There are multiple Unicode apostrophes: ' ' ʼ ᾿ ′ etc.
    text = text.replace('ʼ', "'")  # U+02BC MODIFIER LETTER APOSTROPHE
    text = text.replace('᾿', "'")  # U+1FBF GREEK PSILI
    text = text.replace('′', "'")  # U+2032 PRIME
    text = text.replace('\u2019', "'")  # U+2019 RIGHT SINGLE QUOTATION MARK
    text = text.replace('´', "'")  # U+00B4 ACUTE ACCENT
    
    # First normalize to NFD (decomposed form) to separate base characters from combining marks
    nfd_form = unicodedata.normalize('NFD', text)
    
    # Remove combining diacritical marks (accents, breathings, etc.)
    # These are in the Unicode blocks:
    # - Combining Diacritical Marks (U+0300–U+036F)
    # - Greek Extended (various combining marks)
    without_diacritics = ''.join(char for char in nfd_form 
                                if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase
    lowercased = without_diacritics.lower()
    
    # Normalize final sigma: ς → σ
    normalized = lowercased.replace('ς', 'σ')
    
    # Remove any punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized, flags=re.UNICODE)
    
    # Keep only Greek letters
    greek_only = ''.join(char for char in normalized 
                        if '\u0370' <= char <= '\u03ff' or 
                           '\u1f00' <= char <= '\u1fff' or
                           char.isspace())
    
    return greek_only.strip()

def normalize_greek_ultra(text):
    """Ultra-aggressive Greek normalization for fallback searches
    
    This handles pre-composed characters that don't decompose properly
    and provides a comprehensive mapping for all possible diacritics.
    """
    # First apply standard normalization
    text = normalize_greek(text)
    
    # Then apply hardcoded mappings for any remaining pre-composed characters
    # This catches cases where NFD decomposition doesn't fully work
    ultra_mappings = {
        # Alpha with iota subscript variants
        'ᾳ': 'α', 'ᾀ': 'α', 'ᾁ': 'α', 'ᾂ': 'α', 'ᾃ': 'α', 'ᾄ': 'α', 'ᾅ': 'α', 'ᾆ': 'α', 'ᾇ': 'α',
        'ᾲ': 'α', 'ᾴ': 'α', 'ᾶ': 'α', 'ᾷ': 'α',
        # Eta with iota subscript variants  
        'ῃ': 'η', 'ῂ': 'η', 'ῄ': 'η', 'ῆ': 'η', 'ῇ': 'η', 'ᾐ': 'η', 'ᾑ': 'η', 'ᾒ': 'η', 'ᾓ': 'η',
        'ᾔ': 'η', 'ᾕ': 'η', 'ᾖ': 'η', 'ᾗ': 'η',
        # Omega with iota subscript variants
        'ῳ': 'ω', 'ῲ': 'ω', 'ῴ': 'ω', 'ῶ': 'ω', 'ῷ': 'ω', 'ᾠ': 'ω', 'ᾡ': 'ω', 'ᾢ': 'ω', 'ᾣ': 'ω',
        'ᾤ': 'ω', 'ᾥ': 'ω', 'ᾦ': 'ω', 'ᾧ': 'ω',
        # Rho with breathing marks
        'ῤ': 'ρ', 'ῥ': 'ρ',
        # Other special characters
        'ΐ': 'ι', 'ΰ': 'υ', 'ϊ': 'ι', 'ϋ': 'υ',
        # Capital letters with diacritics (in case some slip through)
        'Ά': 'α', 'Έ': 'ε', 'Ή': 'η', 'Ί': 'ι', 'Ό': 'ο', 'Ύ': 'υ', 'Ώ': 'ω',
        'Ϊ': 'ι', 'Ϋ': 'υ',
        # Additional characters
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'ΐ': 'ι', 'ΰ': 'υ', 'ϊ': 'ι', 'ϋ': 'υ',
        # Any remaining composed characters
        'ἀ': 'α', 'ἁ': 'α', 'ἂ': 'α', 'ἃ': 'α', 'ἄ': 'α', 'ἅ': 'α', 'ἆ': 'α', 'ἇ': 'α',
        'Ἀ': 'α', 'Ἁ': 'α', 'Ἂ': 'α', 'Ἃ': 'α', 'Ἄ': 'α', 'Ἅ': 'α', 'Ἆ': 'α', 'Ἇ': 'α',
        'ἐ': 'ε', 'ἑ': 'ε', 'ἒ': 'ε', 'ἓ': 'ε', 'ἔ': 'ε', 'ἕ': 'ε',
        'Ἐ': 'ε', 'Ἑ': 'ε', 'Ἒ': 'ε', 'Ἓ': 'ε', 'Ἔ': 'ε', 'Ἕ': 'ε',
        'ἠ': 'η', 'ἡ': 'η', 'ἢ': 'η', 'ἣ': 'η', 'ἤ': 'η', 'ἥ': 'η', 'ἦ': 'η', 'ἧ': 'η',
        'Ἠ': 'η', 'Ἡ': 'η', 'Ἢ': 'η', 'Ἣ': 'η', 'Ἤ': 'η', 'Ἥ': 'η', 'Ἦ': 'η', 'Ἧ': 'η',
        'ἰ': 'ι', 'ἱ': 'ι', 'ἲ': 'ι', 'ἳ': 'ι', 'ἴ': 'ι', 'ἵ': 'ι', 'ἶ': 'ι', 'ἷ': 'ι',
        'Ἰ': 'ι', 'Ἱ': 'ι', 'Ἲ': 'ι', 'Ἳ': 'ι', 'Ἴ': 'ι', 'Ἵ': 'ι', 'Ἶ': 'ι', 'Ἷ': 'ι',
        'ὀ': 'ο', 'ὁ': 'ο', 'ὂ': 'ο', 'ὃ': 'ο', 'ὄ': 'ο', 'ὅ': 'ο',
        'Ὀ': 'ο', 'Ὁ': 'ο', 'Ὂ': 'ο', 'Ὃ': 'ο', 'Ὄ': 'ο', 'Ὅ': 'ο',
        'ὐ': 'υ', 'ὑ': 'υ', 'ὒ': 'υ', 'ὓ': 'υ', 'ὔ': 'υ', 'ὕ': 'υ', 'ὖ': 'υ', 'ὗ': 'υ',
        'Ὑ': 'υ', 'Ὓ': 'υ', 'Ὕ': 'υ', 'Ὗ': 'υ',
        'ὠ': 'ω', 'ὡ': 'ω', 'ὢ': 'ω', 'ὣ': 'ω', 'ὤ': 'ω', 'ὥ': 'ω', 'ὦ': 'ω', 'ὧ': 'ω',
        'Ὠ': 'ω', 'Ὡ': 'ω', 'Ὢ': 'ω', 'Ὣ': 'ω', 'Ὤ': 'ω', 'Ὥ': 'ω', 'Ὦ': 'ω', 'Ὧ': 'ω',
        'ὰ': 'α', 'ὲ': 'ε', 'ὴ': 'η', 'ὶ': 'ι', 'ὸ': 'ο', 'ὺ': 'υ', 'ὼ': 'ω',
        'Ὰ': 'α', 'Ὲ': 'ε', 'Ὴ': 'η', 'Ὶ': 'ι', 'Ὸ': 'ο', 'Ὺ': 'υ', 'Ὼ': 'ω',
    }
    
    # Apply the mappings
    result = text
    for old, new in ultra_mappings.items():
        result = result.replace(old, new)
    
    # Final cleanup - ensure only lowercase Greek letters remain
    result = ''.join(c for c in result.lower() if 'α' <= c <= 'ω' or c.isspace())
    
    return result.strip()