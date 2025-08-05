#!/usr/bin/env python3
"""
Extract verb conjugations and noun declensions from lemma pages in Wiktionary.
This will help us map inflected forms like ἔπερσεν → πέρθω
"""

import json
import re
import unicodedata
from pathlib import Path
from collections import defaultdict

def normalize_greek(text):
    """Normalize Greek text - remove diacritics and lowercase"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    return text

def extract_conjugation_forms(lemma, content):
    """Extract all inflected forms from a verb's conjugation table"""
    forms = {}
    
    # Look for Ancient Greek section
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', content, re.DOTALL)
    if not ag_match:
        return forms
    
    ag_section = ag_match.group(0)
    
    # Look for conjugation templates - these generate inflected forms
    conj_patterns = [
        # Ancient Greek verb conjugation templates
        r'\{\{grc-conj[^}]*\}\}',
        r'\{\{grc-verb[^}]*\}\}',
        r'\{\{el-conj[^}]*\}\}',
        
        # Specific verb patterns that might have forms listed
        r'====Conjugation====.*?(?=\n====|\n===|\Z)',
        r'===Verb===.*?(?=\n===|\Z)',
    ]
    
    # Extract verb forms from tables
    # Look for Greek words that might be inflected forms
    greek_word_pattern = r'[ἀ-���Α-Ω]+'
    
    for pattern in conj_patterns:
        matches = re.findall(pattern, ag_section, re.DOTALL)
        for match in matches:
            # Find all Greek words in the conjugation section
            greek_words = re.findall(greek_word_pattern, match)
            for word in greek_words:
                if len(word) > 2 and word != lemma:  # Skip short particles and the lemma itself
                    normalized = normalize_greek(word)
                    if normalized and normalized != normalize_greek(lemma):
                        forms[normalized] = {
                            'lemma': lemma,
                            'lemma_normalized': normalize_greek(lemma),
                            'word_form': word,
                            'word_form_normalized': normalized,
                            'pos': 'verb',
                            'source': 'wiktionary:conjugation'
                        }
    
    return forms

def extract_declension_forms(lemma, content):
    """Extract all inflected forms from a noun's declension table"""
    forms = {}
    
    # Look for Ancient Greek section
    ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|\Z)', content, re.DOTALL)
    if not ag_match:
        return forms
    
    ag_section = ag_match.group(0)
    
    # Look for declension templates
    decl_patterns = [
        r'\{\{grc-decl[^}]*\}\}',
        r'\{\{grc-noun[^}]*\}\}',
        r'\{\{el-nN[^}]*\}\}',
        r'\{\{el-nF[^}]*\}\}',
        r'\{\{el-nM[^}]*\}\}',
        r'====Declension====.*?(?=\n====|\n===|\Z)',
    ]
    
    greek_word_pattern = r'[ἀ-ῷΑ-Ω]+'
    
    for pattern in decl_patterns:
        matches = re.findall(pattern, ag_section, re.DOTALL)
        for match in matches:
            greek_words = re.findall(greek_word_pattern, match)
            for word in greek_words:
                if len(word) > 2 and word != lemma:
                    normalized = normalize_greek(word)
                    if normalized and normalized != normalize_greek(lemma):
                        forms[normalized] = {
                            'lemma': lemma,
                            'lemma_normalized': normalize_greek(lemma),
                            'word_form': word,
                            'word_form_normalized': normalized,
                            'pos': 'noun',
                            'source': 'wiktionary:declension'
                        }
    
    return forms

def main():
    """Extract conjugations and declensions from cached Greek pages"""
    
    # Load Greek pages cache
    cache_file = Path("all_greek_wiktionary_pages.json")
    print(f"Loading Greek pages from {cache_file}...")
    
    with open(cache_file) as f:
        pages = json.load(f)
    
    print(f"Loaded {len(pages):,} pages")
    
    # Load corpus words to prioritize
    corpus_file = Path("all_greek_words_in_corpus.json")
    with open(corpus_file) as f:
        corpus_words = set(json.load(f))
    
    # Find lemma pages (pages that have Ancient Greek sections with conjugation/declension)
    all_forms = {}
    processed = 0
    
    print("\nExtracting inflected forms from lemma pages...")
    
    for lemma, content in pages.items():
        if '==Ancient Greek==' not in content:
            continue
        
        # Check if this is a verb or noun page
        if any(marker in content for marker in ['===Verb===', '====Conjugation====', '{{grc-conj']):
            forms = extract_conjugation_forms(lemma, content)
            all_forms.update(forms)
            if forms:
                processed += 1
        
        if any(marker in content for marker in ['===Noun===', '====Declension====', '{{grc-decl']):
            forms = extract_declension_forms(lemma, content)
            all_forms.update(forms)
            if forms:
                processed += 1
        
        if processed % 100 == 0 and processed > 0:
            print(f"  Processed {processed} lemma pages, found {len(all_forms):,} forms...")
    
    print(f"\nTotal forms extracted: {len(all_forms):,}")
    
    # Filter to corpus words
    corpus_forms = {k: v for k, v in all_forms.items() if k in corpus_words}
    print(f"Forms in corpus: {len(corpus_forms):,}")
    
    # Save results
    output_file = Path("lemma_conjugation_mappings.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_forms, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved all forms to {output_file}")
    
    # Show some examples
    print("\nExample mappings:")
    examples = list(all_forms.items())[:10]
    for form, info in examples:
        print(f"  {info['word_form']} → {info['lemma']} ({info['pos']})")

if __name__ == "__main__":
    main()