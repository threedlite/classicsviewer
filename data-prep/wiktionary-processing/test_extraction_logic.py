#!/usr/bin/env python3
"""Test extraction logic on known examples"""

import sys
sys.path.append('.')
from extract_inflected_forms_mappings import extract_inflection_info, normalize_greek

# Test with the pages we found
test_cases = [
    {
        'title': 'ἀνδρός',
        'text': '''{{also|Άνδρος|Ἄνδρος}}
==Ancient Greek==

===Pronunciation===
{{grc-IPA|ᾰνδρός}}

===Noun===
{{head|grc|noun form}}

# {{inflection of|grc|ἀνήρ||gen|s}}'''
    },
    {
        'title': 'θεοῦ',
        'text': '''{{also|θεού|Θεοῦ}}
==Ancient Greek==

===Pronunciation===
{{grc-IPA}}

===Noun===
{{head|grc|noun form|g=m}}

# {{inflection of|grc|θεός||gen|s}}'''
    }
]

for test in test_cases:
    print(f"\nTesting: {test['title']}")
    normalized = normalize_greek(test['title'])
    print(f"Normalized: {normalized}")
    
    result = extract_inflection_info(test['title'], test['text'], normalized)
    if result:
        print(f"✓ Extraction successful!")
        print(f"  Lemma: {result['lemma']}")
        print(f"  Lemma normalized: {result['lemma_normalized']}")
        print(f"  Morphology: {result['morphology']}")
        print(f"  POS: {result['pos']}")
    else:
        print("✗ Extraction failed!")