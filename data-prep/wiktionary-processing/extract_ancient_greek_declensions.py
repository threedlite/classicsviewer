#!/usr/bin/env python3
"""
Extract all Ancient Greek noun/adjective declensions from Wiktionary
Parses {{grc-decl|...}} and {{grc-adecl|...}} templates
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Tuple

def normalize_greek(text):
    """Normalize Greek text by removing diacritics"""
    if not text:
        return ""
    # First normalize to NFD (decomposed form)
    text = unicodedata.normalize('NFD', text)
    # Remove diacritical marks
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Convert to lowercase
    text = text.lower()
    # Replace final sigma
    text = text.replace('ς', 'σ')
    # Remove punctuation and keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

class AncientGreekDecliner:
    """Parse and expand Ancient Greek declension templates"""
    
    def is_greek_word(self, word):
        """Check if a word contains Greek characters"""
        return any('\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF' for char in word)
    
    def __init__(self):
        # Define endings for major declension patterns
        self.endings = {
            # First declension
            'first_fem_alpha': {
                'singular': ['α', 'ας', 'ᾳ', 'αν', 'α'],
                'plural': ['αι', 'ων', 'αις', 'ας', 'αι']
            },
            'first_fem_eta': {
                'singular': ['η', 'ης', 'ῃ', 'ην', 'η'],
                'plural': ['αι', 'ων', 'αις', 'ας', 'αι']
            },
            'first_masc': {
                'singular': ['ης', 'ου', 'ῃ', 'ην', 'α'],
                'plural': ['αι', 'ων', 'αις', 'ας', 'αι']
            },
            # Second declension
            'second_masc': {
                'singular': ['ος', 'ου', 'ῳ', 'ον', 'ε'],
                'plural': ['οι', 'ων', 'οις', 'ους', 'οι']
            },
            'second_neut': {
                'singular': ['ον', 'ου', 'ῳ', 'ον', 'ον'],
                'plural': ['α', 'ων', 'οις', 'α', 'α']
            },
            # Third declension patterns
            'third_cons': {
                'singular': ['', 'ος', 'ι', 'α', ''],
                'plural': ['ες', 'ων', 'σι(ν)', 'ας', 'ες']
            },
            'third_neut': {
                'singular': ['', 'ος', 'ι', '', ''],
                'plural': ['α', 'ων', 'σι(ν)', 'α', 'α']
            }
        }
        
        self.cases = ['nominative', 'genitive', 'dative', 'accusative', 'vocative']
    
    def parse_template(self, template: str, pos: str = 'noun') -> List[Dict]:
        """Parse a {{grc-decl|...}} or {{grc-adecl|...}} template"""
        forms = []
        
        # Extract template parameters
        match = re.match(r'\{\{grc-(?:a?decl|decl-[^|]+)\|([^}]+)\}\}', template)
        if not match:
            return forms
            
        params = match.group(1).split('|')
        
        # Try to identify declension pattern from template name
        if 'grc-decl-1st' in template or params[0].endswith('α') or params[0].endswith('η'):
            forms.extend(self.generate_first_declension(params))
        elif 'grc-decl-2nd' in template or params[0].endswith('ος') or params[0].endswith('ον'):
            forms.extend(self.generate_second_declension(params))
        elif 'grc-decl-3rd' in template:
            forms.extend(self.generate_third_declension(params))
        elif 'grc-adecl' in template:
            forms.extend(self.generate_adjective_forms(params))
            
        return forms
    
    def generate_first_declension(self, params: List[str]) -> List[Dict]:
        """Generate first declension forms"""
        forms = []
        
        if not params or not params[0]:
            return forms
            
        # Get the stem
        nom_sing = params[0]
        if nom_sing.endswith('α'):
            stem = nom_sing[:-1]
            pattern = 'first_fem_alpha'
        elif nom_sing.endswith('η'):
            stem = nom_sing[:-1]
            pattern = 'first_fem_eta'
        elif nom_sing.endswith('ης') or nom_sing.endswith('ας'):
            stem = nom_sing[:-2]
            pattern = 'first_masc'
        else:
            return forms
        
        # Never output forms with empty stem
        if not stem:
            return forms
            
        endings = self.endings[pattern]
        
        # Generate forms
        for i, case in enumerate(self.cases):
            # Singular
            form = stem + endings['singular'][i]
            # Skip if the form is just an ending (no stem)
            if form and self.is_greek_word(form):
                forms.append({
                    'form': form,
                    'case': case,
                    'number': 'singular',
                    'gender': 'feminine' if 'fem' in pattern else 'masculine'
                })
            
            # Plural
            form = stem + endings['plural'][i]
            # Skip if the form is just an ending (no stem)
            if form and self.is_greek_word(form):
                forms.append({
                    'form': form,
                    'case': case,
                    'number': 'plural',
                    'gender': 'feminine' if 'fem' in pattern else 'masculine'
                })
            
        return forms
    
    def generate_second_declension(self, params: List[str]) -> List[Dict]:
        """Generate second declension forms"""
        forms = []
        
        if not params or not params[0]:
            return forms
            
        # Get the stem
        nom_sing = params[0]
        if nom_sing.endswith('ος'):
            stem = nom_sing[:-2]
            pattern = 'second_masc'
            gender = 'masculine'
        elif nom_sing.endswith('ον'):
            stem = nom_sing[:-2]
            pattern = 'second_neut'
            gender = 'neuter'
        else:
            return forms
        
        # Never output forms with empty stem
        if not stem:
            return forms
            
        endings = self.endings[pattern]
        
        # Generate forms
        for i, case in enumerate(self.cases):
            # Singular
            form = stem + endings['singular'][i]
            # Skip if the form is just an ending (no stem)
            if form and self.is_greek_word(form):
                forms.append({
                    'form': form,
                    'case': case,
                    'number': 'singular',
                    'gender': gender
                })
            
            # Plural
            form = stem + endings['plural'][i]
            # Skip if the form is just an ending (no stem)  
            if form and self.is_greek_word(form):
                forms.append({
                    'form': form,
                    'case': case,
                    'number': 'plural',
                    'gender': gender
                })
            
        return forms
    
    def generate_third_declension(self, params: List[str]) -> List[Dict]:
        """Generate third declension forms (simplified)"""
        forms = []
        
        if not params or len(params) < 2:
            return forms
            
        # Third declension is complex - use provided forms
        nom_sing = params[0]
        gen_sing = params[1] if len(params) > 1 else params[0] + 'ος'
        
        # Try to extract stem from genitive
        if gen_sing.endswith('ος'):
            stem = gen_sing[:-2]
        else:
            stem = gen_sing[:-1]
        
        # Never output forms with empty stem
        if not stem:
            return forms
            
        # Guess gender from nominative ending
        if nom_sing.endswith('ς') or nom_sing.endswith('ρ') or nom_sing.endswith('ν'):
            pattern = 'third_cons'
            gender = 'masculine' # Default, could also be feminine
        else:
            pattern = 'third_neut'
            gender = 'neuter'
            
        endings = self.endings[pattern]
        
        # Generate forms
        for i, case in enumerate(self.cases):
            # Singular
            if i == 0:  # Nominative
                form = nom_sing
            else:
                ending = endings['singular'][i]
                form = stem + ending
            
            # Skip if the form is just an ending (no stem)
            if form and self.is_greek_word(form):
                forms.append({
                    'form': form,
                    'case': case,
                    'number': 'singular',
                    'gender': gender
                })
            
            # Plural
            ending = endings['plural'][i]
            if ending.endswith('(ν)'):
                # Add both forms
                form1 = stem + ending.replace('(ν)', '')
                form2 = stem + ending.replace('(ν)', 'ν')
                if form1 and self.is_greek_word(form1):
                    forms.append({
                        'form': form1,
                        'case': case,
                        'number': 'plural',
                        'gender': gender
                    })
                if form2 and self.is_greek_word(form2):
                    forms.append({
                        'form': form2,
                        'case': case,
                        'number': 'plural',
                        'gender': gender
                    })
            else:
                form = stem + ending
                if form:
                    forms.append({
                        'form': form,
                        'case': case,
                        'number': 'plural',
                        'gender': gender
                    })
                
        return forms
    
    def generate_adjective_forms(self, params: List[str]) -> List[Dict]:
        """Generate adjective forms (all three genders)"""
        forms = []
        
        if not params or not params[0]:
            return forms
            
        # Adjectives typically have masculine, feminine, neuter forms
        # For now, generate basic 2-1-2 pattern (like καλός, καλή, καλόν)
        masc = params[0]
        fem = params[1] if len(params) > 1 else masc.replace('ος', 'η')
        neut = params[2] if len(params) > 2 else masc.replace('ος', 'ον')
        
        # Generate masculine forms (2nd declension)
        if masc.endswith('ος'):
            stem = masc[:-2]
            # Never output forms with empty stem
            if stem:
                for i, case in enumerate(self.cases):
                    form = stem + self.endings['second_masc']['singular'][i]
                    if form and self.is_greek_word(form):
                        forms.append({
                            'form': form,
                            'case': case,
                            'number': 'singular',
                            'gender': 'masculine'
                        })
                    form = stem + self.endings['second_masc']['plural'][i]
                    if form and self.is_greek_word(form):
                        forms.append({
                            'form': form,
                            'case': case,
                            'number': 'plural',
                            'gender': 'masculine'
                        })
                
        # Generate feminine forms (1st declension)
        if fem.endswith('η'):
            stem = fem[:-1]
            # Never output forms with empty stem
            if stem:
                for i, case in enumerate(self.cases):
                    form = stem + self.endings['first_fem_eta']['singular'][i]
                    if form and self.is_greek_word(form):
                        forms.append({
                            'form': form,
                            'case': case,
                            'number': 'singular',
                            'gender': 'feminine'
                        })
                    form = stem + self.endings['first_fem_eta']['plural'][i]
                    if form and self.is_greek_word(form):
                        forms.append({
                            'form': form,
                            'case': case,
                            'number': 'plural',
                            'gender': 'feminine'
                        })
                
        # Generate neuter forms (2nd declension)
        if neut.endswith('ον'):
            stem = neut[:-2]
            # Never output forms with empty stem
            if stem:
                for i, case in enumerate(self.cases):
                    form = stem + self.endings['second_neut']['singular'][i]
                    if form and self.is_greek_word(form):
                        forms.append({
                            'form': form,
                            'case': case,
                            'number': 'singular',
                            'gender': 'neuter'
                        })
                    form = stem + self.endings['second_neut']['plural'][i]
                    if form and self.is_greek_word(form):
                        forms.append({
                            'form': form,
                            'case': case,
                            'number': 'plural',
                            'gender': 'neuter'
                        })
                
        return forms

def extract_declensions_from_wiktionary(wiktionary_path: Path):
    """Extract all Ancient Greek declensions from Wiktionary data"""
    
    print("Loading Wiktionary data...")
    with open(wiktionary_path, 'r', encoding='utf-8') as f:
        wiktionary_data = json.load(f)
    
    decliner = AncientGreekDecliner()
    all_mappings = []
    nouns_processed = 0
    forms_generated = 0
    
    print(f"Processing {len(wiktionary_data)} Wiktionary entries...")
    
    for lemma, content in wiktionary_data.items():
        # Skip non-Ancient Greek entries
        if '==Ancient Greek==' not in content:
            continue
            
        # Extract Ancient Greek section
        ag_match = re.search(r'==Ancient Greek==.*?(?=\n==[^=]|$)', content, re.DOTALL)
        if not ag_match:
            continue
            
        ag_section = ag_match.group(0)
        
        # Look for noun/adjective declension templates
        templates = re.findall(r'\{\{grc-(?:a?decl|decl-[^}]+)\|[^}]+\}\}', ag_section)
        
        if templates:
            nouns_processed += 1
            lemma_normalized = normalize_greek(lemma)
            
            # Determine POS
            pos = 'adjective' if '===Adjective===' in ag_section else 'noun'
            
            for template in templates:
                forms = decliner.parse_template(template, pos)
                
                for form_data in forms:
                    word_form = form_data['form']
                    # Clean up the form
                    word_form = word_form.strip()
                    if not word_form:
                        continue
                        
                    mapping = {
                        'word_form': word_form,
                        'lemma': lemma,
                        'confidence': 1.0,
                        'source': 'wiktionary:grc-decl',
                        'morph_info': f"{form_data['case']} {form_data['number']} {form_data['gender']}",
                        'pos': pos,
                        'debug_template': template
                    }
                    
                    all_mappings.append(mapping)
                    forms_generated += 1
            
            if nouns_processed % 100 == 0:
                print(f"  Processed {nouns_processed} nouns/adjectives, generated {forms_generated} forms...")
    
    print(f"\nProcessed {nouns_processed} Ancient Greek nouns/adjectives")
    print(f"Generated {forms_generated} declined forms")
    
    return all_mappings

def main():
    # Paths
    script_dir = Path(__file__).parent
    wiktionary_path = script_dir / 'all_greek_wiktionary_pages.json'
    output_path = script_dir / 'extract_ancient_greek_declensions.json'
    
    # Extract declensions
    mappings = extract_declensions_from_wiktionary(wiktionary_path)
    
    # Keep all mappings without deduplication
    unique_mappings = mappings
    
    print(f"Total mappings: {len(unique_mappings)}")
    
    # Save results
    output_data = {
        'metadata': {
            'source': 'Greek Wiktionary declension templates',
            'extraction_date': '2025-08-15',
            'total_lemmas': len(set(m['lemma'] for m in unique_mappings)),
            'total_mappings': len(unique_mappings),
            'description': 'Ancient Greek noun/adjective declensions extracted from {{grc-decl}} templates'
        },
        'mappings': unique_mappings
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(unique_mappings)} declension mappings to {output_path}")
    
    # Show some examples
    print("\nExample mappings:")
    for mapping in unique_mappings[:10]:
        print(f"  {mapping['word_form']} → {mapping['lemma']} ({mapping['morph_info']})")

if __name__ == '__main__':
    main()