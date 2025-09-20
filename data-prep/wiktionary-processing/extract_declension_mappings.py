#!/usr/bin/env python3
"""
Extract Ancient Greek mappings from declension templates in Greek Wiktionary
This implements the actual declension patterns to generate inflected forms
"""

import xml.etree.ElementTree as ET
import re
import bz2
import json
import unicodedata
from pathlib import Path

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
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
    # Remove punctuation (including Greek punctuation)
    # Keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

class GreekDeclensionGenerator:
    """Generate Ancient Greek declensions based on template patterns"""
    
    def __init__(self):
        # Define declension patterns for most common templates
        self.patterns = {
            # First declension (feminine -α/-η)
            'θάλασσα': {
                'type': '1st_decl_fem_a',
                'endings': {
                    'nom_sg': 'α', 'gen_sg': 'ης', 'dat_sg': 'ῃ', 'acc_sg': 'αν', 'voc_sg': 'α',
                    'nom_pl': 'αι', 'gen_pl': 'ων', 'dat_pl': 'αις', 'acc_pl': 'ας', 'voc_pl': 'αι'
                }
            },
            'γνώμη': {
                'type': '1st_decl_fem_h', 
                'endings': {
                    'nom_sg': 'η', 'gen_sg': 'ης', 'dat_sg': 'ῃ', 'acc_sg': 'ην', 'voc_sg': 'η',
                    'nom_pl': 'αι', 'gen_pl': 'ων', 'dat_pl': 'αις', 'acc_pl': 'ας', 'voc_pl': 'αι'
                }
            },
            'χώρα': {
                'type': '1st_decl_fem_a_pure',
                'endings': {
                    'nom_sg': 'α', 'gen_sg': 'ας', 'dat_sg': 'ᾳ', 'acc_sg': 'αν', 'voc_sg': 'α',
                    'nom_pl': 'αι', 'gen_pl': 'ων', 'dat_pl': 'αις', 'acc_pl': 'ας', 'voc_pl': 'αι'
                }
            },
            
            # Second declension
            'δρόμος': {
                'type': '2nd_decl_masc',
                'endings': {
                    'nom_sg': 'ος', 'gen_sg': 'ου', 'dat_sg': 'ῳ', 'acc_sg': 'ον', 'voc_sg': 'ε',
                    'nom_pl': 'οι', 'gen_pl': 'ων', 'dat_pl': 'οις', 'acc_pl': 'ους', 'voc_pl': 'οι'
                }
            },
            'πρόσωπον': {
                'type': '2nd_decl_neut',
                'endings': {
                    'nom_sg': 'ον', 'gen_sg': 'ου', 'dat_sg': 'ῳ', 'acc_sg': 'ον', 'voc_sg': 'ον',
                    'nom_pl': 'α', 'gen_pl': 'ων', 'dat_pl': 'οις', 'acc_pl': 'α', 'voc_pl': 'α'
                }
            },
            
            # Third declension
            'πόλις': {
                'type': '3rd_decl_i',
                'endings': {
                    'nom_sg': 'ις', 'gen_sg': 'εως', 'dat_sg': 'ει', 'acc_sg': 'ιν', 'voc_sg': 'ι',
                    'nom_pl': 'εις', 'gen_pl': 'εων', 'dat_pl': 'εσι(ν)', 'acc_pl': 'εις', 'voc_pl': 'εις'
                }
            },
            'φύλαξ': {
                'type': '3rd_decl_velar',
                'endings': {
                    'nom_sg': 'ξ', 'gen_sg': 'κος', 'dat_sg': 'κι', 'acc_sg': 'κα', 'voc_sg': 'ξ',
                    'nom_pl': 'κες', 'gen_pl': 'κων', 'dat_pl': 'ξι(ν)', 'acc_pl': 'κας', 'voc_pl': 'κες'
                }
            },
            'βέλος': {
                'type': '3rd_decl_s_neut',
                'endings': {
                    'nom_sg': 'ος', 'gen_sg': 'ους', 'dat_sg': 'ει', 'acc_sg': 'ος', 'voc_sg': 'ος',
                    'nom_pl': 'η', 'gen_pl': 'ων', 'dat_pl': 'εσι(ν)', 'acc_pl': 'η', 'voc_pl': 'η'
                }
            },
            'κτήμα': {
                'type': '3rd_decl_ma_neut',
                'endings': {
                    'nom_sg': 'μα', 'gen_sg': 'ματος', 'dat_sg': 'ματι', 'acc_sg': 'μα', 'voc_sg': 'μα',
                    'nom_pl': 'ματα', 'gen_pl': 'ματων', 'dat_pl': 'μασι(ν)', 'acc_pl': 'ματα', 'voc_pl': 'ματα'
                }
            },
            
            # Adjectives
            'καλός': {
                'type': '2-1-2_adj',
                'endings': {
                    # Masculine
                    'masc_nom_sg': 'ος', 'masc_gen_sg': 'ου', 'masc_dat_sg': 'ῳ', 'masc_acc_sg': 'ον', 'masc_voc_sg': 'ε',
                    'masc_nom_pl': 'οι', 'masc_gen_pl': 'ων', 'masc_dat_pl': 'οις', 'masc_acc_pl': 'ους', 'masc_voc_pl': 'οι',
                    # Feminine  
                    'fem_nom_sg': 'η', 'fem_gen_sg': 'ης', 'fem_dat_sg': 'ῃ', 'fem_acc_sg': 'ην', 'fem_voc_sg': 'η',
                    'fem_nom_pl': 'αι', 'fem_gen_pl': 'ων', 'fem_dat_pl': 'αις', 'fem_acc_pl': 'ας', 'fem_voc_pl': 'αι',
                    # Neuter
                    'neut_nom_sg': 'ον', 'neut_gen_sg': 'ου', 'neut_dat_sg': 'ῳ', 'neut_acc_sg': 'ον', 'neut_voc_sg': 'ον',
                    'neut_nom_pl': 'α', 'neut_gen_pl': 'ων', 'neut_dat_pl': 'οις', 'neut_acc_pl': 'α', 'neut_voc_pl': 'α'
                }
            },
            'δύσκολος': {
                'type': '2-1-2_adj_compound',
                'endings': {
                    # Same as καλός but vocative singular keeps -ος
                    'masc_nom_sg': 'ος', 'masc_gen_sg': 'ου', 'masc_dat_sg': 'ῳ', 'masc_acc_sg': 'ον', 'masc_voc_sg': 'ος',
                    'masc_nom_pl': 'οι', 'masc_gen_pl': 'ων', 'masc_dat_pl': 'οις', 'masc_acc_pl': 'ους', 'masc_voc_pl': 'οι',
                    'fem_nom_sg': 'ος', 'fem_gen_sg': 'ου', 'fem_dat_sg': 'ῳ', 'fem_acc_sg': 'ον', 'fem_voc_sg': 'ος',
                    'fem_nom_pl': 'οι', 'fem_gen_pl': 'ων', 'fem_dat_pl': 'οις', 'fem_acc_pl': 'ους', 'fem_voc_pl': 'οι',
                    'neut_nom_sg': 'ον', 'neut_gen_sg': 'ου', 'neut_dat_sg': 'ῳ', 'neut_acc_sg': 'ον', 'neut_voc_sg': 'ον',
                    'neut_nom_pl': 'α', 'neut_gen_pl': 'ων', 'neut_dat_pl': 'οις', 'neut_acc_pl': 'α', 'neut_voc_pl': 'α'
                }
            }
        }
    
    def get_stem(self, word, pattern_name):
        """Extract the stem from a word based on the pattern"""
        pattern = self.patterns.get(pattern_name)
        if not pattern:
            return None
            
        # Find the nominative singular ending
        nom_ending = None
        for key, ending in pattern['endings'].items():
            if key.endswith('nom_sg') and not key.startswith(('masc_', 'fem_', 'neut_')):
                nom_ending = ending
                break
            elif key == 'nom_sg':
                nom_ending = ending
                break
            elif key == 'masc_nom_sg':  # For adjectives, use masculine
                nom_ending = ending
                break
        
        if nom_ending and word.endswith(nom_ending):
            return word[:-len(nom_ending)] if nom_ending else word
        
        # For some patterns, the whole word is the stem
        return word
    
    def generate_forms(self, lemma, pattern_name):
        """Generate all inflected forms for a lemma based on pattern"""
        pattern = self.patterns.get(pattern_name)
        if not pattern:
            return []
        
        stem = self.get_stem(lemma, pattern_name)
        if stem is None or not stem:  # Reject empty stems
            return []
        
        forms = []
        for case_name, ending in pattern['endings'].items():
            # Remove (ν) optional endings
            clean_ending = ending.replace('(ν)', '').replace('(ι)', '').replace('(ε)', '')
            
            # Generate the form
            if clean_ending:
                form = stem + clean_ending
            else:
                form = stem
            
            # Only include forms that have Greek letters and aren't just endings
            # Check that the form contains the stem (prevents bare endings)
            if form != lemma and form and stem in form:
                forms.append({
                    'form': form,
                    'case': case_name,
                    'pattern': pattern_name
                })
            
            # Also generate forms with optional endings
            if '(ν)' in ending:
                form_with_n = stem + ending.replace('(ν)', 'ν')
                # Check that the form contains the stem
                if form_with_n != lemma and form_with_n and stem in form_with_n:
                    forms.append({
                        'form': form_with_n,
                        'case': case_name + '_with_nu',
                        'pattern': pattern_name
                    })
        
        return forms

def extract_declension_mappings(dump_path, output_path):
    """Extract mappings from Greek declension templates"""
    print(f"=== EXTRACTING DECLENSION MAPPINGS FROM GREEK WIKTIONARY ===")
    print(f"Source: {dump_path}")
    print(f"Output: {output_path}")
    
    generator = GreekDeclensionGenerator()
    
    with bz2.open(dump_path, 'rt', encoding='utf-8') as f:
        context = ET.iterparse(f, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        all_mappings = []
        pages_processed = 0
        declension_pages = 0
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('page'):
                pages_processed += 1
                
                # Extract title and text
                title_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}title')
                text_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
                
                if title_elem is not None and text_elem is not None:
                    title = title_elem.text or ''
                    text = text_elem.text or ''
                    
                    # Skip non-main namespace pages
                    if ':' in title:
                        elem.clear()
                        root.clear()
                        continue
                    
                    # Look for declension templates
                    for pattern_name in generator.patterns:
                        template_pattern = f"{{{{grc-κλίση-'{pattern_name}'"
                        if template_pattern in text:
                            declension_pages += 1
                            
                            # Generate forms for this word
                            forms = generator.generate_forms(title, pattern_name)
                            
                            if forms:
                                # Add mappings for each form
                                title_normalized = normalize_greek(title)
                                
                                for form_data in forms:
                                    form_normalized = normalize_greek(form_data['form'])
                                    
                                    if form_normalized != title_normalized:
                                        mapping = {
                                            'word_form': form_normalized,
                                            'lemma': title_normalized,
                                            'confidence': 0.9,  # Slightly lower confidence for generated forms
                                            'source': f'elwiktionary:declension:{pattern_name}',
                                            'morph_type': 'generated',
                                            'case': form_data['case'],
                                            'debug_title': title,
                                            'debug_form': form_data['form']
                                        }
                                        all_mappings.append(mapping)
                                
                                if declension_pages <= 5:
                                    print(f"Generated {len(forms)} forms for {title} using {pattern_name}")
                            
                            break  # Only use first matching template
                
                # Clear memory
                elem.clear()
                root.clear()
                
                # Progress
                if pages_processed % 50000 == 0:
                    print(f"  Processed {pages_processed:,} pages, found {declension_pages:,} declensions, generated {len(all_mappings):,} mappings")
    
    print(f"\n✓ Extraction complete!")
    print(f"  Total pages processed: {pages_processed:,}")
    print(f"  Declension pages found: {declension_pages:,}")
    print(f"  Total mappings generated: {len(all_mappings):,}")
    
    # Deduplicate mappings
    print(f"\nDeduplicating mappings...")
    unique_mappings = {}
    
    for mapping in all_mappings:
        key = (mapping['word_form'], mapping['lemma'])
        if key not in unique_mappings:
            unique_mappings[key] = mapping
    
    final_mappings = list(unique_mappings.values())
    print(f"  Unique mappings after deduplication: {len(final_mappings):,}")
    
    # Save to JSON file
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'source': 'Greek Wiktionary Declension Templates',
                'source_file': str(dump_path),
                'extraction_date': '2025-08-04',
                'license': 'Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)',
                'total_pages_processed': pages_processed,
                'declension_pages_found': declension_pages,
                'total_mappings': len(final_mappings),
                'description': 'Ancient Greek inflection mappings generated from declension templates'
            },
            'mappings': final_mappings
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(final_mappings):,} unique mappings to {output_path}")
    
    # Show sample mappings
    print(f"\nSample mappings:")
    for mapping in final_mappings[:20]:
        print(f"  {mapping['debug_form']} -> {mapping['debug_title']} ({mapping['case']})")
    
    return True

def main():
    """Main function for use by other scripts"""
    # Use dump file - this script requires the Greek Wiktionary dump
    dump_file = Path(__file__).parent.parent.parent / "data-sources" / "elwiktionary-latest-pages-articles.xml.bz2"
    output_file = Path(__file__).parent / "extract_declension_mappings.json"
    
    if not dump_file.exists():
        print(f"ERROR: Required Greek Wiktionary dump file {dump_file} not found!")
        raise FileNotFoundError(f"Greek Wiktionary dump file required: {dump_file}")
    
    # Extract from dump
    success = extract_declension_mappings(str(dump_file), str(output_file))
    if not success:
        raise RuntimeError("Failed to extract declension mappings")
    
    print(f"\n✓ Successfully extracted declension mappings!")
    return success

if __name__ == "__main__":
    main()