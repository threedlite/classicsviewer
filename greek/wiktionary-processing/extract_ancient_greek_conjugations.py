#!/usr/bin/env python3
"""
Extract all Ancient Greek verb conjugations from Wiktionary
Parses {{grc-conj|...}} templates to generate full conjugation tables
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

class AncientGreekConjugator:
    """Parse and expand Ancient Greek conjugation templates"""
    
    def __init__(self):
        # Define endings for each conjugation type
        self.endings = {
            # Present endings
            'pres-con-e': {
                'active': ['ω', 'εις', 'ει', 'ομεν', 'ετε', 'ουσι(ν)'],
                'middle': ['ομαι', 'ῃ/ει', 'εται', 'ομεθα', 'εσθε', 'ονται'],
                'imperative': ['ε', 'ετω', 'ετε', 'οντων'],
                'subjunctive': ['ω', 'ῃς', 'ῃ', 'ωμεν', 'ητε', 'ωσι(ν)'],
                'optative': ['οιμι', 'οις', 'οι', 'οιμεν', 'οιτε', 'οιεν'],
                'infinitive': 'ειν',
                'participle': 'ων/ουσα/ον'
            },
            'pres-con-a': {
                'active': ['ω', 'ᾷς', 'ᾷ', 'ῶμεν', 'ᾶτε', 'ῶσι(ν)'],
                'middle': ['ῶμαι', 'ᾷ', 'ᾶται', 'ώμεθα', 'ᾶσθε', 'ῶνται'],
            },
            'pres-con-o': {
                'active': ['ω', 'οῖς', 'οῖ', 'οῦμεν', 'οῦτε', 'οῦσι(ν)'],
                'middle': ['οῦμαι', 'οῖ', 'οῦται', 'ούμεθα', 'οῦσθε', 'οῦνται'],
            },
            # Imperfect
            'imperf-con-e': {
                'active': ['ον', 'ες', 'ε(ν)', 'ομεν', 'ετε', 'ον'],
                'middle': ['ομην', 'ου', 'ετο', 'ομεθα', 'εσθε', 'οντο']
            },
            # Future
            'fut': {
                'active': ['ω', 'εις', 'ει', 'ομεν', 'ετε', 'ουσι(ν)'],
                'middle': ['ομαι', 'ῃ/ει', 'εται', 'ομεθα', 'εσθε', 'ονται']
            },
            # Aorist type 1 (sigmatic)
            'aor-1': {
                'active': ['α', 'ας', 'ε(ν)', 'αμεν', 'ατε', 'αν'],
                'middle': ['αμην', 'ω', 'ατο', 'αμεθα', 'ασθε', 'αντο'],
                'imperative_act': ['ον', 'ατω', 'ατε', 'αντων'],
                'imperative_mid': ['αι', 'ασθω', 'ασθε', 'ασθων'],
                'subjunctive_act': ['ω', 'ῃς', 'ῃ', 'ωμεν', 'ητε', 'ωσι(ν)'],
                'subjunctive_mid': ['ωμαι', 'ῃ', 'ηται', 'ωμεθα', 'ησθε', 'ωνται'],
                'optative_act': ['αιμι', 'αις/ειας', 'αι/ειε(ν)', 'αιμεν', 'αιτε', 'αιεν/ειαν'],
                'optative_mid': ['αιμην', 'αιο', 'αιτο', 'αιμεθα', 'αισθε', 'αιντο'],
                'infinitive_act': 'αι',
                'infinitive_mid': 'ασθαι',
                'participle_act': 'ας/ασα/αν',
                'participle_mid': 'αμενος/η/ον'
            },
            # Aorist type 2 (thematic)
            'aor-2': {
                'active': ['ον', 'ες', 'ε(ν)', 'ομεν', 'ετε', 'ον'],
                'middle': ['ομην', 'ου', 'ετο', 'ομεθα', 'εσθε', 'οντο'],
                'imperative_act': ['ε', 'ετω', 'ετε', 'οντων'],
                'imperative_mid': ['ου', 'εσθω', 'εσθε', 'εσθων']
            },
            # Perfect
            'perf': {
                'active': ['α', 'ας', 'ε(ν)', 'αμεν', 'ατε', 'ασι(ν)'],
                'middle': ['μαι', 'σαι', 'ται', 'μεθα', 'σθε', 'νται']
            }
        }
    
    def parse_template(self, template: str) -> List[Dict]:
        """Parse a {{grc-conj|...}} template and return forms"""
        forms = []
        
        # Extract template parameters
        match = re.match(r'\{\{grc-conj\|([^}]+)\}\}', template)
        if not match:
            return forms
            
        params = match.group(1).split('|')
        if len(params) < 2:
            return forms
            
        conj_type = params[0]
        stems = params[1:]
        
        # Validate we have stems before processing
        if not stems or not any(stems):
            return forms
            
        # Generate forms based on conjugation type
        if conj_type == 'pres-con-e' and len(stems) > 0:
            forms.extend(self.generate_present_e(stems[0]))
        elif conj_type == 'imperf-con-e':
            forms.extend(self.generate_imperfect_e(stems[0]))
        elif conj_type == 'fut':
            forms.extend(self.generate_future(stems[0]))
        elif conj_type == 'aor-1':
            # Aorist can have both augmented and unaugmented stems
            if len(stems) >= 2:
                forms.extend(self.generate_aorist_1(stems[0], stems[1]))
            else:
                forms.extend(self.generate_aorist_1(stems[0], stems[0]))
        elif conj_type == 'perf':
            forms.extend(self.generate_perfect(stems[0]))
            
        return forms
    
    def generate_present_e(self, stem: str) -> List[Dict]:
        """Generate present tense forms for ε-contract verbs"""
        forms = []
        # Skip if stem is empty or None
        if not stem or stem.strip() == '':
            return forms
        endings = self.endings['pres-con-e']
        
        # Indicative active
        for i, ending in enumerate(endings['active']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': stem + ending_clean,
                'mood': 'indicative',
                'voice': 'active',
                'tense': 'present',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            # Also add form with movable nu
            if '(ν)' in ending:
                forms.append({
                    'form': stem + ending.replace('(ν)', 'ν'),
                    'mood': 'indicative',
                    'voice': 'active', 
                    'tense': 'present',
                    'person': (i % 3) + 1,
                    'number': 'singular' if i < 3 else 'plural'
                })
        
        # Indicative middle/passive
        for i, ending in enumerate(endings['middle']):
            for e in ending.split('/'):
                forms.append({
                    'form': stem + e,
                    'mood': 'indicative',
                    'voice': 'middle/passive',
                    'tense': 'present',
                    'person': (i % 3) + 1,
                    'number': 'singular' if i < 3 else 'plural'
                })
        
        # Imperatives
        for i, ending in enumerate(endings['imperative']):
            forms.append({
                'form': stem + ending,
                'mood': 'imperative',
                'voice': 'active',
                'tense': 'present',
                'person': 2 if i == 0 else 3 if i == 1 else 2 if i == 2 else 3,
                'number': 'singular' if i < 2 else 'plural'
            })
            
        # Subjunctive
        for i, ending in enumerate(endings['subjunctive']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': stem + ending_clean,
                'mood': 'subjunctive',
                'voice': 'active',
                'tense': 'present',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            
        # Infinitive
        forms.append({
            'form': stem + endings['infinitive'],
            'mood': 'infinitive',
            'voice': 'active',
            'tense': 'present'
        })
        
        return forms
    
    def generate_aorist_1(self, augmented_stem: str, unaugmented_stem: str) -> List[Dict]:
        """Generate aorist forms (sigmatic)"""
        forms = []
        # Skip if stems are empty or None
        if not augmented_stem or augmented_stem.strip() == '' or not unaugmented_stem or unaugmented_stem.strip() == '':
            return forms
        endings = self.endings['aor-1']
        
        # Indicative active (with augment)
        for i, ending in enumerate(endings['active']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': augmented_stem + ending_clean,
                'mood': 'indicative',
                'voice': 'active',
                'tense': 'aorist',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
        
        # Indicative middle (with augment)
        for i, ending in enumerate(endings['middle']):
            forms.append({
                'form': augmented_stem + ending,
                'mood': 'indicative',
                'voice': 'middle',
                'tense': 'aorist',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
        
        # Imperatives (without augment)
        for i, ending in enumerate(endings['imperative_act']):
            forms.append({
                'form': unaugmented_stem + ending,
                'mood': 'imperative',
                'voice': 'active',
                'tense': 'aorist',
                'person': 2 if i == 0 else 3 if i == 1 else 2 if i == 2 else 3,
                'number': 'singular' if i < 2 else 'plural'
            })
            
        # Subjunctive (without augment)
        for i, ending in enumerate(endings['subjunctive_act']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': unaugmented_stem + ending_clean,
                'mood': 'subjunctive',
                'voice': 'active',
                'tense': 'aorist',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            
        # Optative (without augment)
        for i, ending in enumerate(endings['optative_act']):
            # Handle alternative endings
            for e in ending.split('/'):
                ending_clean = e.replace('(ν)', '').replace('(ν)', 'ν')
                forms.append({
                    'form': unaugmented_stem + ending_clean,
                    'mood': 'optative',
                    'voice': 'active',
                    'tense': 'aorist',
                    'person': (i % 3) + 1,
                    'number': 'singular' if i < 3 else 'plural'
                })
        
        # Infinitive
        forms.append({
            'form': unaugmented_stem + endings['infinitive_act'],
            'mood': 'infinitive',
            'voice': 'active',
            'tense': 'aorist'
        })
        
        return forms
    
    def generate_imperfect_e(self, stem: str) -> List[Dict]:
        """Generate imperfect forms"""
        forms = []
        # Skip if stem is empty or None
        if not stem or stem.strip() == '':
            return forms
        endings = self.endings['imperf-con-e']
        
        # Active voice
        for i, ending in enumerate(endings['active']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': stem + ending_clean,
                'mood': 'indicative',
                'voice': 'active',
                'tense': 'imperfect',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            
        # Middle/passive voice
        for i, ending in enumerate(endings['middle']):
            forms.append({
                'form': stem + ending,
                'mood': 'indicative',
                'voice': 'middle/passive',
                'tense': 'imperfect',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            
        return forms
        
    def generate_future(self, stem: str) -> List[Dict]:
        """Generate future forms"""
        forms = []
        # Skip if stem is empty or None
        if not stem or stem.strip() == '':
            return forms
        endings = self.endings['fut']
        
        # Active voice
        for i, ending in enumerate(endings['active']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': stem + ending_clean,
                'mood': 'indicative',
                'voice': 'active',
                'tense': 'future',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            
        return forms
        
    def generate_perfect(self, stem: str) -> List[Dict]:
        """Generate perfect forms"""
        forms = []
        # Skip if stem is empty or None
        if not stem or stem.strip() == '':
            return forms
        endings = self.endings['perf']
        
        # Active voice
        for i, ending in enumerate(endings['active']):
            ending_clean = ending.replace('(ν)', '').replace('(ν)', 'ν')
            forms.append({
                'form': stem + ending_clean,
                'mood': 'indicative',
                'voice': 'active',
                'tense': 'perfect',
                'person': (i % 3) + 1,
                'number': 'singular' if i < 3 else 'plural'
            })
            
        return forms

def extract_conjugations_from_wiktionary(wiktionary_path: Path):
    """Extract all Ancient Greek conjugations from Wiktionary data"""
    
    print("Loading Wiktionary data...")
    with open(wiktionary_path, 'r', encoding='utf-8') as f:
        wiktionary_data = json.load(f)
    
    conjugator = AncientGreekConjugator()
    all_mappings = []
    verbs_processed = 0
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
        
        # Look for verb conjugation templates
        templates = re.findall(r'\{\{grc-conj\|[^}]+\}\}', ag_section)
        
        if templates:
            verbs_processed += 1
            lemma_normalized = normalize_greek(lemma)
            
            for template in templates:
                forms = conjugator.parse_template(template)
                
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
                        'source': 'wiktionary:grc-conj',
                        'morph_info': f"{form_data['tense']} {form_data['voice']} {form_data['mood']}",
                        'debug_template': template
                    }
                    
                    # Add person/number info if available
                    if 'person' in form_data and 'number' in form_data:
                        mapping['morph_info'] += f" {form_data['person']}p {form_data['number']}"
                    
                    all_mappings.append(mapping)
                    forms_generated += 1
            
            if verbs_processed % 100 == 0:
                print(f"  Processed {verbs_processed} verbs, generated {forms_generated} forms...")
    
    print(f"\nProcessed {verbs_processed} Ancient Greek verbs")
    print(f"Generated {forms_generated} verb forms")
    
    return all_mappings

def main():
    # Paths
    script_dir = Path(__file__).parent
    wiktionary_path = script_dir / 'all_greek_wiktionary_pages.json'
    output_path = script_dir / 'extract_ancient_greek_conjugations.json'
    
    # Extract conjugations
    mappings = extract_conjugations_from_wiktionary(wiktionary_path)
    
    # Keep all mappings without deduplication
    unique_mappings = mappings
    
    print(f"Total mappings: {len(unique_mappings)}")
    
    # Save results
    output_data = {
        'metadata': {
            'source': 'Greek Wiktionary conjugation templates',
            'extraction_date': '2025-08-15',
            'total_verbs': len(set(m['lemma'] for m in unique_mappings)),
            'total_mappings': len(unique_mappings),
            'description': 'Ancient Greek verb conjugations extracted from {{grc-conj}} templates'
        },
        'mappings': unique_mappings
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(unique_mappings)} conjugation mappings to {output_path}")
    
    # Show some examples
    print("\nExample mappings:")
    for mapping in unique_mappings[:10]:
        print(f"  {mapping['word_form']} → {mapping['lemma']} ({mapping['morph_info']})")

if __name__ == '__main__':
    main()