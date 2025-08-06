#!/usr/bin/env python3
"""
Create SQLite database from Perseus Digital Library texts.
This single script handles the entire database creation process.
"""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json
from datetime import datetime
import unicodedata
from typing import Dict, List, Tuple, Optional, Set
import subprocess
import sys

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
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

def normalize_line_for_search(text, language='greek'):
    """Normalize a line of text for searching, preserving word boundaries"""
    if not text:
        return ""
    
    if language == 'greek':
        # First normalize to NFD (decomposed form)
        text = unicodedata.normalize('NFD', text)
        
        # Remove diacritical marks
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace final sigma
        text = text.replace('ς', 'σ')
        
        # Replace all non-letter characters with spaces to preserve word boundaries
        normalized = []
        for c in text:
            if c.isalpha():
                normalized.append(c)
            else:
                normalized.append(' ')
        
        # Join and clean up multiple spaces
        result = ''.join(normalized)
        result = ' '.join(result.split())  # Normalize whitespace
        
        return result
    else:
        # For non-Greek text, just lowercase and normalize spaces
        return ' '.join(text.lower().split())

class LSJParser:
    """Parser for LSJ XML dictionary entries"""
    
    def __init__(self):
        self.namespaces = {
            'tei': 'http://www.tei-c.org/ns/1.0'
        }
    
    def normalize_greek(self, text: str) -> str:
        """Use the global normalize_greek function"""
        return normalize_greek(text)
    
    def extract_text_content(self, element) -> str:
        """Extract all text content from an XML element, including nested elements"""
        if element is None:
            return ""
        
        text_parts = []
        
        # Add element's direct text
        if element.text:
            text_parts.append(element.text)
        
        # Process child elements
        for child in element:
            # Add child's text content
            child_text = self.extract_text_content(child)
            if child_text:
                text_parts.append(child_text)
            
            # Add tail text after child element
            if child.tail:
                text_parts.append(child.tail)
        
        return ''.join(text_parts).strip()
    
    def parse_entry_key(self, key: str) -> str:
        """Parse the entry key to extract the base lemma"""
        if not key:
            return ""
        
        # Basic conversion of Perseus key notation to Greek
        key = key.replace(')', '῾')  # rough breathing
        key = key.replace('(', '᾿')  # smooth breathing  
        key = key.replace('/', '́')   # acute accent
        key = key.replace('\\', '̀')  # grave accent
        key = key.replace('=', '͂')   # circumflex
        key = key.replace('|', 'ι')  # iota subscript (simplified)
        
        return key
    
    def parse_sense(self, sense_elem) -> Dict[str, str]:
        """Parse a single sense element and extract translation and usage info"""
        sense_data = {
            'level': sense_elem.get('level', '0'),
            'n': sense_elem.get('n', ''),
            'translation': '',
            'usage': '',
            'examples': ''
        }
        
        # Extract translations from <trans><tr> elements
        translations = []
        for trans_elem in sense_elem.findall('.//trans/tr'):
            trans_text = self.extract_text_content(trans_elem)
            if trans_text:
                translations.append(trans_text)
        
        sense_data['translation'] = '; '.join(translations)
        
        # Extract usage information from <usg> elements
        usages = []
        for usg_elem in sense_elem.findall('.//usg'):
            usg_text = self.extract_text_content(usg_elem)
            if usg_text:
                usages.append(usg_text)
        
        sense_data['usage'] = ', '.join(usages)
        
        # Extract Greek examples from <foreign lang="greek"> elements
        examples = []
        for foreign_elem in sense_elem.findall('.//foreign[@lang="greek"]'):
            example_text = self.extract_text_content(foreign_elem)
            if example_text:
                examples.append(example_text)
        
        sense_data['examples'] = ' | '.join(examples)
        
        return sense_data
    
    def format_entry_html(self, headword: str, senses: List[Dict[str, str]], 
                         etymology: str = "") -> str:
        """Format dictionary entry as HTML for display in the app"""
        html_parts = []
        
        # Headword
        html_parts.append(f'<div class="headword"><strong>{headword}</strong></div>')
        
        # Etymology if present
        if etymology:
            html_parts.append(f'<div class="etymology"><em>{etymology}</em></div>')
        
        # Senses
        for i, sense in enumerate(senses):
            sense_html = '<div class="sense">'
            
            # Sense number if multiple senses
            if len(senses) > 1 and sense['n']:
                sense_html += f'<span class="sense-number">{sense["n"]}.</span> '
            
            # Translation
            if sense['translation']:
                sense_html += f'<span class="translation">{sense["translation"]}</span>'
            
            # Usage information
            if sense['usage']:
                sense_html += f' <span class="usage">({sense["usage"]})</span>'
            
            # Greek examples
            if sense['examples']:
                sense_html += f'<div class="examples">{sense["examples"]}</div>'
            
            sense_html += '</div>'
            html_parts.append(sense_html)
        
        return '\n'.join(html_parts)
    
    def format_entry_plain(self, headword: str, senses: List[Dict[str, str]], 
                          etymology: str = "") -> str:
        """Format dictionary entry as plain text for searching"""
        text_parts = [headword]
        
        if etymology:
            text_parts.append(etymology)
        
        for sense in senses:
            if sense['translation']:
                text_parts.append(sense['translation'])
            if sense['usage']:
                text_parts.append(sense['usage'])
            if sense['examples']:
                text_parts.append(sense['examples'])
        
        return ' '.join(text_parts)
    
    def parse_lsj_xml(self, xml_path: str) -> List[Dict[str, str]]:
        """Parse the complete LSJ XML file and extract all dictionary entries"""
        print(f"Parsing LSJ XML from {xml_path}")
        
        # Read and preprocess XML to handle entities
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Replace common entities that aren't defined in the DTD
            entity_replacements = {
                '&lpar;': '(',
                '&rpar;': ')',
                '&mdash;': '—',
                '&equals;': '=',
                '&ast;': '*',
                '&dagger;': '†',
                '&colon;': ':',
                '&agrave;': 'à',
                '&eacute;': 'é',
                '&breve;': '˘',
                '&macr;': '¯',
                '&quest;': '?',
                '&plus;': '+'
            }
            
            for entity, replacement in entity_replacements.items():
                xml_content = xml_content.replace(entity, replacement)
            
            # Parse the preprocessed XML
            root = ET.fromstring(xml_content)
        except (ET.ParseError, FileNotFoundError, UnicodeDecodeError) as e:
            print(f"Error parsing XML: {e}")
            return []
        
        entries = []
        entry_count = 0
        
        # Find all dictionary entries
        for entry_elem in root.findall('.//entry[@type="main"]'):
            entry_count += 1
            
            # Extract key and headword
            key = entry_elem.get('key', '')
            
            # Get the Greek headword from <form><orth>
            headword = ""
            form_elem = entry_elem.find('.//form/orth[@lang="greek"]')
            if form_elem is not None:
                headword = self.extract_text_content(form_elem)
            
            # If no headword found, try to parse from key
            if not headword and key:
                headword = self.parse_entry_key(key)
            
            if not headword:
                continue  # Skip entries without headwords
            
            # Extract etymology
            etymology = ""
            etym_elem = entry_elem.find('.//etym')
            if etym_elem is not None:
                etymology = self.extract_text_content(etym_elem)
            
            # Extract all senses
            senses = []
            for sense_elem in entry_elem.findall('.//sense'):
                sense_data = self.parse_sense(sense_elem)
                if sense_data['translation']:  # Only include senses with translations
                    senses.append(sense_data)
            
            # Skip entries without any meaningful senses
            if not senses:
                continue
            
            # Create entry record
            entry = {
                'headword': headword,
                'headword_normalized': self.normalize_greek(headword),
                'language': 'greek',
                'entry_xml': ET.tostring(entry_elem, encoding='unicode'),
                'entry_html': self.format_entry_html(headword, senses, etymology),
                'entry_plain': self.format_entry_plain(headword, senses, etymology),
                'source': 'LSJ'
            }
            
            entries.append(entry)
            
            # Progress indicator
            if entry_count % 1000 == 0:
                print(f"  Processed {entry_count} entries, extracted {len(entries)} valid entries")
        
        print(f"✓ LSJ parsing complete: {len(entries)} dictionary entries extracted from {entry_count} total entries")
        return entries

class GreekLemmatizer:
    """Enhanced Greek lemmatizer for comprehensive morphological analysis"""
    
    def __init__(self):
        # First declension endings (mostly feminine)
        self.first_decl_endings = {
            # -α stems
            'α_long': ['α', 'ας', 'ᾳ', 'αν', 'α', 'αι', 'ων', 'αις', 'ας'],
            'α_short': ['α', 'ης', 'ῃ', 'αν', 'α', 'αι', 'ων', 'αις', 'ας'],
            # -η stems  
            'η': ['η', 'ης', 'ῃ', 'ην', 'η', 'αι', 'ων', 'αις', 'ας']
        }
        
        # Second declension endings
        self.second_decl_endings = {
            # Masculine -ος
            'ος': ['ος', 'ου', 'ῳ', 'ον', 'ε', 'οι', 'ων', 'οις', 'ους'],
            # Neuter -ον
            'ον': ['ον', 'ου', 'ῳ', 'ον', 'ον', 'α', 'ων', 'οις', 'α']
        }
        
        # Third declension endings (consonant stems)
        self.third_decl_endings = {
            # Various patterns - simplified
            'consonant': ['', 'ος', 'ι', 'α', '', 'ες', 'ων', 'σι', 'ας'],
            'sigma': ['ς', 'ους', 'ει', 'η', 'ες', 'η', 'ων', 'εσι', 'ας'],
            'neuter_τ': ['', 'τος', 'τι', '', '', 'τα', 'των', 'σι', 'τα']
        }
        
        # Present tense verb endings
        self.present_endings = {
            'ω_active': ['ω', 'εις', 'ει', 'ομεν', 'ετε', 'ουσι'],
            'ω_middle': ['ομαι', 'ῃ', 'εται', 'ομεθα', 'εσθε', 'ονται'],
            'μι_active': ['μι', 'ς', 'σι', 'μεν', 'τε', 'ασι'],
            'contract_α': ['ῶ', 'ᾷς', 'ᾷ', 'ῶμεν', 'ᾶτε', 'ῶσι'],
            'contract_ε': ['ῶ', 'εῖς', 'εῖ', 'οῦμεν', 'εῖτε', 'οῦσι'],
            'contract_ο': ['ῶ', 'οῖς', 'οῖ', 'οῦμεν', 'οῦτε', 'οῦσι']
        }
        
        # Imperfect endings
        self.imperfect_endings = {
            'active': ['ον', 'ες', 'ε', 'ομεν', 'ετε', 'ον'],
            'middle': ['ομην', 'ου', 'ετο', 'ομεθα', 'εσθε', 'οντο']
        }
        
        # Aorist endings
        self.aorist_endings = {
            'weak_active': ['α', 'ας', 'ε', 'αμεν', 'ατε', 'αν'],
            'weak_middle': ['αμην', 'ω', 'ατο', 'αμεθα', 'ασθε', 'αντο'],
            'strong_active': ['ον', 'ες', 'ε', 'ομεν', 'ετε', 'ον']
        }
        
        # Common irregular verbs and their forms
        self.irregular_verbs = {
            'εἰμι': ['εἰμι', 'εἶ', 'ἐστι', 'ἐσμεν', 'ἐστε', 'εἰσι', 'ἦν', 'ἦς', 'ἦν', 'ἦμεν', 'ἦτε', 'ἦσαν'],
            'φημι': ['φημι', 'φῃς', 'φησι', 'φαμεν', 'φατε', 'φασι'],
            'οἶδα': ['οἶδα', 'οἶσθα', 'οἶδε', 'ἴσμεν', 'ἴστε', 'ἴσασι'],
            'εἶμι': ['εἶμι', 'εἶ', 'εἶσι', 'ἴμεν', 'ἴτε', 'ἴασι']
        }
        
        # Common contractions
        self.contractions = {
            'ου': ['εου', 'οου'],
            'ω': ['εω', 'αω', 'οω'],
            'ᾳ': ['αει', 'αῃ'],
            'ει': ['εει'],
            'οι': ['εοι', 'οοι'],
            'ῃ': ['εῃ'],
            'ου': ['εου']
        }
    
    def normalize_greek(self, text: str) -> str:
        """
        Normalize Greek text by removing diacritics and converting to lowercase
        """
        if not text:
            return ""
        
        # First normalize to NFD (decomposed form)
        text = unicodedata.normalize('NFD', text)
        
        # Remove diacritical marks
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace final sigma with regular sigma
        text = text.replace('ς', 'σ')
        
        return text
    
    def generate_noun_forms(self, lemma: str) -> Set[str]:
        """Generate all possible inflected forms for a noun lemma"""
        forms = set()
        normalized_lemma = self.normalize_greek(lemma)
        
        # Try different declension patterns
        for decl_name, endings in {**self.first_decl_endings, **self.second_decl_endings, **self.third_decl_endings}.items():
            # Guess stem by trying to remove common nominative endings
            possible_stems = [normalized_lemma]
            
            if normalized_lemma.endswith('ος'):
                possible_stems.append(normalized_lemma[:-2])
            elif normalized_lemma.endswith('η'):
                possible_stems.append(normalized_lemma[:-1])
            elif normalized_lemma.endswith('α'):
                possible_stems.append(normalized_lemma[:-1])
            elif normalized_lemma.endswith('ον'):
                possible_stems.append(normalized_lemma[:-2])
            
            for stem in possible_stems:
                if len(stem) >= 2:  # Avoid too-short stems
                    for ending in endings:
                        if ending:  # Skip empty endings for some cases
                            forms.add(stem + ending)
                        else:
                            forms.add(stem)
        
        return forms
    
    def generate_verb_forms(self, lemma: str) -> Set[str]:
        """Generate all possible inflected forms for a verb lemma"""
        forms = set()
        normalized_lemma = self.normalize_greek(lemma)
        
        # Handle irregular verbs first
        if normalized_lemma in self.irregular_verbs:
            for form in self.irregular_verbs[normalized_lemma]:
                forms.add(self.normalize_greek(form))
            return forms
        
        # Get verb stem by removing -ω or -μι
        stem = normalized_lemma
        verb_type = None
        
        if normalized_lemma.endswith('ω'):
            stem = normalized_lemma[:-1]
            verb_type = 'ω'
        elif normalized_lemma.endswith('μι'):
            stem = normalized_lemma[:-2]
            verb_type = 'μι'
        elif normalized_lemma.endswith('ειν'):  # Infinitive form
            stem = normalized_lemma[:-3]
            verb_type = 'ω'
        
        if not verb_type or len(stem) < 2:
            return forms
        
        # Generate present forms
        if verb_type == 'ω':
            for ending in self.present_endings['ω_active']:
                forms.add(stem + ending)
            for ending in self.present_endings['ω_middle']:
                forms.add(stem + ending)
            
            # Check for contract verbs
            if stem.endswith('α'):
                contract_stem = stem[:-1]
                for ending in self.present_endings['contract_α']:
                    forms.add(contract_stem + ending)
            elif stem.endswith('ε'):
                contract_stem = stem[:-1]
                for ending in self.present_endings['contract_ε']:
                    forms.add(contract_stem + ending)
            elif stem.endswith('ο'):
                contract_stem = stem[:-1]
                for ending in self.present_endings['contract_ο']:
                    forms.add(contract_stem + ending)
        
        elif verb_type == 'μι':
            for ending in self.present_endings['μι_active']:
                forms.add(stem + ending)
        
        # Generate imperfect forms (with augment)
        augmented_stem = stem
        if not stem.startswith(('α', 'ε', 'η', 'ι', 'ο', 'υ', 'ω')):
            augmented_stem = 'ε' + stem  # Add temporal augment
        
        for ending in self.imperfect_endings['active']:
            forms.add(augmented_stem + ending)
        for ending in self.imperfect_endings['middle']:
            forms.add(augmented_stem + ending)
        
        # Generate aorist forms
        for ending in self.aorist_endings['weak_active']:
            forms.add(augmented_stem + 'σ' + ending)  # Sigmatic aorist
        for ending in self.aorist_endings['strong_active']:
            forms.add(augmented_stem + ending)  # Strong aorist
        
        return forms
    
    def generate_all_forms(self, lemma: str, pos_hint: str = None) -> Set[str]:
        """
        Generate all possible inflected forms for a lemma
        pos_hint can be 'noun', 'verb', 'adjective' or None
        """
        forms = set()
        forms.add(self.normalize_greek(lemma))  # Always include the lemma itself
        
        if pos_hint == 'verb' or pos_hint is None:
            forms.update(self.generate_verb_forms(lemma))
        
        if pos_hint == 'noun' or pos_hint == 'adjective' or pos_hint is None:
            forms.update(self.generate_noun_forms(lemma))
        
        # Remove forms that are too short or obviously wrong
        valid_forms = set()
        for form in forms:
            if len(form) >= 2 and re.match(r'^[α-ωάέήίόύώ]+$', form):
                valid_forms.add(form)
        
        return valid_forms
    
    def reverse_lemmatize(self, word: str) -> List[str]:
        """
        Given an inflected word, generate possible lemmas
        This is the inverse operation - used for dictionary lookup
        """
        candidates = []
        normalized = self.normalize_greek(word)
        
        # Always try the word itself
        candidates.append(normalized)
        
        # Try removing common endings and adding common lemma endings
        
        # Noun patterns
        if normalized.endswith('ου'):  # Genitive singular
            candidates.extend([normalized[:-2] + 'ος', normalized[:-2] + 'η', normalized[:-2] + 'ον'])
        elif normalized.endswith('ων'):  # Genitive plural  
            candidates.extend([normalized[:-2] + 'ος', normalized[:-2] + 'η', normalized[:-2] + 'ον'])
        elif normalized.endswith('ας'):  # Various cases
            candidates.extend([normalized[:-2] + 'α', normalized[:-2] + 'ης'])
        elif normalized.endswith('αι'):  # Nominative plural
            candidates.extend([normalized[:-2] + 'α', normalized[:-2] + 'η', normalized[:-2] + 'ος'])
        
        # Verb patterns
        if normalized.endswith('ει'):  # 3rd person singular
            candidates.append(normalized[:-2] + 'ω')
        elif normalized.endswith('ουσι'):  # 3rd person plural
            candidates.append(normalized[:-4] + 'ω')
        elif normalized.endswith('ομεν'):  # 1st person plural
            candidates.append(normalized[:-4] + 'ω')
        elif normalized.endswith('ετε'):  # 2nd person plural
            candidates.append(normalized[:-3] + 'ω')
        elif normalized.endswith('εις'):  # 2nd person singular
            candidates.append(normalized[:-3] + 'ω')
        elif normalized.endswith('ον'):  # Imperfect/aorist
            candidates.append(normalized[:-2] + 'ω')
            # Remove augment if present
            if normalized.startswith('ε') and len(normalized) > 3:
                candidates.append(normalized[1:-2] + 'ω')
        
        # Handle contractions
        for contracted, expansions in self.contractions.items():
            if contracted in normalized:
                for expansion in expansions:
                    candidates.append(normalized.replace(contracted, expansion))
        
        return list(set(candidates))  # Remove duplicates

def create_lemma_mappings(lsj_entries: List[Dict]) -> List[Dict]:
    """
    Create lemma mappings from LSJ entries
    Returns list of mapping dictionaries for database insertion
    """
    lemmatizer = GreekLemmatizer()
    mappings = []
    
    print("Generating lemma mappings from LSJ entries...")
    
    for i, entry in enumerate(lsj_entries):
        headword = entry['headword']
        normalized_headword = entry['headword_normalized']
        
        # Generate all possible inflected forms for this headword
        all_forms = lemmatizer.generate_all_forms(headword)
        
        # Create mapping for each form
        for form in all_forms:
            if form != normalized_headword:  # Don't map lemma to itself
                mapping = {
                    'word_form': form,
                    'word_normalized': form,
                    'lemma': normalized_headword,
                    'confidence': 0.8,  # Generated mappings have lower confidence
                    'source': 'generated'
                }
                mappings.append(mapping)
        
        # Progress indicator
        if (i + 1) % 1000 == 0:
            print(f"  Processed {i + 1}/{len(lsj_entries)} entries, generated {len(mappings)} mappings")
    
    print(f"✓ Generated {len(mappings)} lemma mappings from {len(lsj_entries)} LSJ entries")
    return mappings

def parse_cts_metadata(cts_path):
    """Parse CTS metadata file to get work information"""
    try:
        tree = ET.parse(cts_path)
        root = tree.getroot()
        
        # Handle different namespace possibilities
        work_info = {}
        
        # Extract title from title elements
        for title_elem in root.iter():
            if 'title' in title_elem.tag.lower():
                lang = title_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 
                                    title_elem.get('lang', 'unk'))
                if lang == 'eng':
                    work_info['title_english'] = title_elem.text
                elif lang == 'lat':
                    work_info['title_latin'] = title_elem.text
                elif lang in ['grc', 'greek']:
                    work_info['title_greek'] = title_elem.text
        
        # Also check for English title in translation/label elements
        for elem in root.iter():
            if 'translation' in elem.tag.lower():
                # Look for English label within translation
                for label in elem.iter():
                    if 'label' in label.tag.lower():
                        lang = label.get('{http://www.w3.org/XML/1998/namespace}lang', 
                                       label.get('lang', 'unk'))
                        if lang == 'eng' and label.text:
                            work_info['title_english'] = label.text
                            break
        
        # Extract URN
        urn = root.get('urn', '')
        if not urn:
            # Try to find it in work element
            for elem in root.iter():
                if 'work' in elem.tag.lower():
                    urn = elem.get('urn', '')
                    break
        work_info['urn'] = urn
        
        # Extract work type (if available)
        work_info['type'] = 'text'  # default
        
        return work_info
    except Exception as e:
        print(f"Error parsing CTS metadata {cts_path}: {e}")
        return None

def get_text_content(elem):
    """Get all text content from element and its children, excluding editorial elements"""
    text_parts = []
    
    # Skip editorial elements entirely
    excluded_tags = {'note', 'foreign', 'ref', 'bibl' }
    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    
    if tag_name in excluded_tags:
        return ''
    
    # Add element's text
    if elem.text:
        text_parts.append(elem.text)
    
    # Process children
    for child in elem:
        # Skip editorial elements
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if child_tag not in excluded_tags:
            text_parts.append(get_text_content(child))
        
        # Always add tail text after child (this is text that comes after the child element)
        if child.tail:
            text_parts.append(child.tail)
    
    return ''.join(text_parts).strip()


def get_section_line_mapping(cursor, book_id, max_section, segment_count=None):
    """Create a mapping from section numbers to line ranges with improved detection"""
    
    # Get total lines for this book
    cursor.execute("""
        SELECT COUNT(*), MAX(CAST(line_number as INTEGER))
        FROM text_lines 
        WHERE book_id = ?
    """, (book_id,))
    
    line_count, max_line = cursor.fetchone()
    
    if not line_count or not max_line or not max_section:
        return {}
    
    # Improved detection: if max_section equals segment count, it's likely section numbering
    # This handles cases like Aeschines where 196 sections map to 866 lines
    if segment_count and max_section == segment_count and max_section < max_line / 2:
        section_map = {}
        lines_per_section = max_line / max_section
        
        for section_num in range(1, max_section + 1):
            start_line = int((section_num - 1) * lines_per_section) + 1
            end_line = int(section_num * lines_per_section)
            if end_line > max_line:
                end_line = max_line
            section_map[section_num] = (start_line, end_line)
        return section_map
    
    # Enhanced threshold detection - avoid mapping large section numbers
    # Only map if sections are numbered significantly lower than lines
    if max_section < max_line / 3 and max_section < 200:
        section_map = {}
        lines_per_section = max_line / max_section
        
        for section_num in range(1, max_section + 1):
            start_line = int((section_num - 1) * lines_per_section) + 1
            end_line = int(section_num * lines_per_section)
            if end_line > max_line:
                end_line = max_line
            section_map[section_num] = (start_line, end_line)
        return section_map
    
    return {}

def extract_translation_segments(book_elem, book_id, cursor, translator):
    """Extract translation segments based on milestone markers"""
    segments = []
    
    # Debug: print what we're processing
    elem_tag = book_elem.tag.split('}')[-1] if '}' in book_elem.tag else book_elem.tag
    print(f"        → Extracting from {elem_tag} for {book_id} (translator: {translator})")
    
    # First check if this is a dramatic text with speaker tags
    has_speakers = False
    for elem in book_elem.iter():
        if elem.tag.endswith('speaker'):
            has_speakers = True
            break
    
    if has_speakers:
        # Process dramatic text with speakers
        print(f"          Processing dramatic text with speakers")
        current_speaker = None
        current_lines = []
        
        for elem in book_elem.iter():
            # Track current speaker
            if elem.tag.endswith('speaker'):
                # Save previous speaker's lines if any
                if current_speaker and current_lines:
                    # Consolidate lines for this speaker
                    start_line = current_lines[0]['line']
                    end_line = current_lines[-1]['line']
                    text = ' '.join(line['text'] for line in current_lines)
                    segments.append({
                        'start_line': start_line,
                        'end_line': end_line,
                        'text': text,
                        'translator': translator,
                        'speaker': current_speaker
                    })
                    current_lines = []
                
                current_speaker = elem.text.strip() if elem.text else None
            
            # Collect lines for current speaker
            elif elem.tag.endswith('l') and current_speaker:
                line_n = elem.get('n', '')
                if line_n and line_n.isdigit():
                    line_text = get_text_content(elem).strip()
                    if line_text:
                        current_lines.append({
                            'line': int(line_n),
                            'text': line_text
                        })
        
        # Don't forget the last speaker's lines
        if current_speaker and current_lines:
            start_line = current_lines[0]['line']
            end_line = current_lines[-1]['line']
            text = ' '.join(line['text'] for line in current_lines)
            segments.append({
                'start_line': start_line,
                'end_line': end_line,
                'text': text,
                'translator': translator,
                'speaker': current_speaker
            })
        
        print(f"          Extracted {len(segments)} segments with speakers")
        
    # Check if there are any milestones at all
    milestones_found = False
    milestone_count = 0
    for elem in book_elem.iter():
        if elem.tag.endswith('milestone') and elem.get('unit') in ['line', 'card', 'section', 'chapter']:
            milestones_found = True
            milestone_count += 1
            if milestone_count <= 3:
                print(f"          Found milestone: unit={elem.get('unit')}, n={elem.get('n')}")
            break
    
    print(f"          Milestones found: {milestones_found} (total: {milestone_count})")
    
    # If we already have segments from speaker processing, skip other methods
    if segments:
        pass  # Already have segments from speaker processing
    elif milestones_found:
        # Handle milestones inside paragraphs (common in Perseus translations)
        para_count = 0
        for para in book_elem.iter():
            if para.tag.endswith('p'):
                para_count += 1
                # Check for milestones in this paragraph
                milestones_in_para = []
                for child in para.iter():
                    if child.tag.endswith('milestone') and child.get('unit') in ['line', 'card', 'section', 'chapter']:
                        n = child.get('n', '')
                        if n:
                            # Try to extract numeric part for sorting
                            try:
                                # For pure numbers
                                line_num = int(n)
                                milestones_in_para.append(line_num)
                            except ValueError:
                                # For Stephanus pagination like "327a", use the number part
                                num_match = re.match(r'(\d+)', n)
                                if num_match:
                                    line_num = int(num_match.group(1))
                                    milestones_in_para.append(line_num)
                                else:
                                    # For non-numeric references, use hash of string for ordering
                                    milestones_in_para.append(hash(n) % 10000)
                
                # Get paragraph text
                para_text = get_text_content(para).strip()
                
                if milestones_in_para and para_text:
                    # Associate paragraph with first milestone
                    segments.append({
                        'start_line': milestones_in_para[0],
                        'end_line': milestones_in_para[-1] if len(milestones_in_para) > 1 else milestones_in_para[0],
                        'text': para_text,
                        'translator': translator
                    })
        
        print(f"          Processed {para_count} paragraphs, extracted {len(segments)} segments")
    else:
        # No milestones - look for sections/chapters
        sections_found = False
        for elem in book_elem.iter():
            if (elem.tag.endswith('div') and 
                elem.get('type') == 'textpart' and 
                elem.get('subtype') in ['section', 'chapter']):
                sections_found = True
                section_n = elem.get('n', '')
                if section_n.isdigit():
                    section_num = int(section_n)
                    section_text = get_text_content(elem).strip()
                    if section_text:
                        segments.append({
                            'start_line': section_num,
                            'end_line': section_num,
                            'text': section_text,
                            'translator': translator
                        })
        
        # If no sections, just extract paragraphs
        if not sections_found:
            para_num = 1
            for para in book_elem.iter():
                if para.tag.endswith('p'):
                    para_text = get_text_content(para).strip()
                    if para_text and len(para_text) > 20:
                        segments.append({
                            'start_line': para_num,
                            'end_line': para_num,
                            'text': para_text,
                            'translator': translator
                        })
                        para_num += 1
    
    # Also check for line elements (even if we found some paragraphs)
    # This handles cases like Horace Book 3 which has both paragraphs and lines
    if len(segments) < 50:  # If we have very few segments, also look for lines
        # First check if there are poem subdivisions (like in Horace)
        poem_divs = []
        for div in book_elem.iter():
            if (div.tag.endswith('div') and 
                div.get('type') == 'textpart' and 
                div.get('subtype') == 'poem'):
                poem_divs.append(div)
        
        if poem_divs:
            # Process poems individually
            line_num = 1
            for poem_div in poem_divs:
                for elem in poem_div.iter():
                    if elem.tag.endswith('l'):
                        line_text = get_text_content(elem).strip()
                        if line_text:
                            segments.append({
                                'start_line': line_num,
                                'end_line': line_num,
                                'text': line_text,
                                'translator': translator
                            })
                            line_num += 1
        else:
            # No poem subdivisions, extract lines directly
            for elem in book_elem.iter():
                if elem.tag.endswith('l'):
                    n = elem.get('n', '')
                    if n and n.isdigit():
                        line_text = get_text_content(elem).strip()
                        if line_text:
                            segments.append({
                                'start_line': int(n),
                                'end_line': int(n),
                                'text': line_text,
                                'translator': translator
                            })
    
    # Insert segments into database
    inserted_count = 0
    
    # Check if we need section-to-line mapping
    max_section = max((s['start_line'] for s in segments if isinstance(s['start_line'], int)), default=0)
    # Pass segment count to improve section detection
    section_map = get_section_line_mapping(cursor, book_id, max_section, len(segments))
    
    for segment in segments:
        start_line = segment['start_line']
        end_line = segment['end_line']
        
        # Apply section-to-line mapping if needed
        if section_map and start_line in section_map:
            start_line, end_line = section_map[start_line]
            
        cursor.execute("""
            INSERT OR IGNORE INTO translation_segments
            (book_id, start_line, end_line, translation_text, translator, speaker)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (book_id, start_line, end_line, 
              segment['text'], segment['translator'], segment.get('speaker')))
        if cursor.rowcount > 0:
            inserted_count += 1
    
    if section_map:
        print(f"        → Applied section-to-line mapping: {max_section} sections to lines")
    
    if inserted_count > 0:
        print(f"        → {inserted_count} translation segments added for {book_id}")
    else:
        print(f"        ⚠️  No segments extracted for {book_id} (found {len(segments)} segments)")
    
    return inserted_count

def process_prose_translation(root, book_id, cursor, translator):
    """Process prose translation by sections"""
    sections = []
    
    # Find all sections
    for elem in root.iter():
        if (elem.tag.endswith('div') and 
            elem.get('type') == 'textpart' and 
            elem.get('subtype') == 'section'):
            
            section_n = elem.get('n', '')
            try:
                section_num = int(section_n)
            except ValueError:
                continue
            
            # Extract all text from this section
            section_text = ""
            for p in elem.iter():
                if p.tag.endswith('p'):
                    text = ''.join(p.itertext()).strip()
                    if text:
                        section_text += text + " "
            
            if section_text.strip():
                sections.append({
                    'number': section_num,
                    'text': section_text.strip()
                })
    
    # Insert translation segments
    for section in sections:
        cursor.execute("""
            INSERT OR IGNORE INTO translation_segments
            (book_id, start_line, end_line, translation_text, translator, speaker)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (book_id, section['number'], section['number'], 
              section['text'], translator, None))

def process_translations(work_dir, work_id, cursor):
    """Process English translations for a work"""
    # Find English translation files
    translation_files = list(work_dir.glob("*eng*.xml"))
    if not translation_files:
        return
        
    # Process ALL translation files, not just the first one
    for trans_file in translation_files:
        print(f"      Processing translation: {trans_file.name}")
        
        try:
            tree = ET.parse(trans_file)
            root = tree.getroot()
            
            # Extract translator name from header
            translator = None
            
            # Try multiple locations for translator info
            # 1. Editor with role="translator"
            for elem in root.iter():
                if 'editor' in elem.tag.lower() and elem.get('role') == 'translator':
                    translator = elem.text
                    if translator:
                        translator = translator.strip()
                        break
            
            # 2. If not found, check respStmt
            if not translator:
                for resp in root.iter():
                    if resp.tag.endswith('respStmt'):
                        # Look for resp with "translator" or "trans" in it
                        resp_text = ''.join(resp.itertext()).lower()
                        if 'translat' in resp_text:
                            # Find the name element
                            for name in resp.iter():
                                if name.tag.endswith('name') and name.text:
                                    translator = name.text.strip()
                                    # Filter out non-translator names
                                    if not any(skip in translator.lower() for skip in ['lisa cerrato', 'william merrill', 'elli mylonas', 'david smith']):
                                        break
                        if translator:
                            break
            
            # 3. Check author elements with translator role
            if not translator:
                for elem in root.iter():
                    if elem.tag.endswith('author'):
                        role = elem.get('role', '')
                        if 'trans' in role.lower():
                            translator = elem.text
                            if translator:
                                translator = translator.strip()
                                break
            
            # 4. Extract from filename pattern (e.g., perseus-eng3.xml might be Butler)
            if not translator and 'eng' in trans_file.name:
                # Common translator mappings based on filenames
                filename = trans_file.name
                filename_mappings = {
                    # Homer
                    'tlg0012.tlg001.perseus-eng3.xml': 'Samuel Butler',
                    'tlg0012.tlg001.perseus-eng4.xml': 'A. T. Murray',
                    'tlg0012.tlg002.perseus-eng3.xml': 'Samuel Butler',
                    'tlg0012.tlg002.perseus-eng4.xml': 'A. T. Murray',
                    # Herodotus
                    'tlg0016.tlg001.perseus-eng2.xml': 'A. D. Godley',
                    # Xenophon
                    'tlg0032.tlg001.perseus-eng2.xml': 'H. G. Dakyns',
                    'tlg0032.tlg002.perseus-eng2.xml': 'H. G. Dakyns',
                    'tlg0032.tlg006.perseus-eng2.xml': 'H. G. Dakyns',
                    'tlg0032.tlg007.perseus-eng2.xml': 'H. G. Dakyns',
                    # Aristotle
                    'tlg0086.tlg003.perseus-eng2.xml': 'Frederic G. Kenyon',
                    'tlg0086.tlg025.perseus-eng2.xml': 'Hugh Tredennick',
                    'tlg0086.tlg010.perseus-eng2.xml': 'Harris Rackham',
                    'tlg0086.tlg038.perseus-eng2.xml': 'John Henry Freese',
                    'tlg0086.tlg034.perseus-eng2.xml': 'William Hamilton Fyfe',
                    'tlg0086.tlg035.perseus-eng2.xml': 'Harris Rackham',
                    'tlg0086.tlg009.perseus-eng2.xml': 'Harris Rackham',
                    'tlg0086.tlg029.perseus-eng2.xml': 'George Cyril Armstrong',
                    'tlg0086.tlg045.perseus-eng2.xml': 'H. Rackham',
                    # Plutarch
                    'tlg0007.tlg051.perseus-eng1.xml': 'Bernadotte Perrin',
                    'tlg0007.tlg052.perseus-eng1.xml': 'Bernadotte Perrin',
                    # Horace
                    'phi0893.phi004.perseus-eng2.xml': 'Christopher Smart'
                }
                
                if filename in filename_mappings:
                    translator = filename_mappings[filename]
                elif 'butler' in filename.lower():
                    translator = 'Samuel Butler'
                elif 'murray' in filename.lower():
                    translator = 'A. T. Murray'
                elif 'jowett' in filename.lower():
                    translator = 'Benjamin Jowett'
            
            # Default translator if none found
            if not translator:
                translator = "Unknown"
                print(f"      ⚠️  Translator not found, using 'Unknown'")
            else:
                print(f"      Translator: {translator}")
            
            # Check if this is prose or drama
            # First check if there are book divisions (epic poetry)
            has_books = False
            for div in root.iter():
                if (div.tag.endswith('div') and 
                    div.get('type') == 'textpart' and 
                    div.get('subtype', '').lower() == 'book'):
                    has_books = True
                    break
            
            # If it has books, it's epic poetry (Homer, Virgil, etc) - use regular processing
            if has_books:
                is_prose = False
                is_drama = False
                print(f"      → Has book divisions, treating as epic poetry")
            else:
                # Count actual elements to determine if it's primarily prose or poetry
                p_count = sum(1 for elem in root.iter() if elem.tag.endswith('p'))
                l_count = sum(1 for elem in root.iter() if elem.tag.endswith('l'))
                # If there are many more paragraphs than lines, it's prose (even if it has some verse quotations)
                is_prose = p_count > 0 and p_count > (l_count * 2)
                
                author_id = work_id.split('.')[0]
                # Drama authors: Aeschylus, Sophocles, Euripides, Aristophanes
                is_drama = author_id in ['tlg0085', 'tlg0011', 'tlg0006', 'tlg0019']
            
            if is_prose:
                # For prose, use extract_translation_segments which handles both milestones and sections
                book_id = f"{work_id}.001"
                
                # Find the main translation div
                trans_div = None
                for div in root.iter():
                    if div.tag.endswith('div') and div.get('type') == 'translation':
                        trans_div = div
                        break
                
                if trans_div is not None:
                    extract_translation_segments(trans_div, book_id, cursor, translator)
                else:
                    # If no translation div, process the whole body
                    for body in root.iter():
                        if body.tag.endswith('body'):
                            extract_translation_segments(body, book_id, cursor, translator)
                            break
            elif is_drama:
                # For dramas, process the entire translation as one book
                book_id = f"{work_id}.001"
                
                # Find the main translation div
                trans_div = None
                for div in root.iter():
                    if div.tag.endswith('div') and div.get('type') == 'translation':
                        trans_div = div
                        break
                
                if trans_div is not None:
                    extract_translation_segments(trans_div, book_id, cursor, translator)
                else:
                    # If no translation div, process the whole body
                    for body in root.iter():
                        if body.tag.endswith('body'):
                            extract_translation_segments(body, book_id, cursor, translator)
                            break
            else:
                # Regular processing for texts with book divisions
                books_found = False
                
                # First check if there's a translation wrapper div
                translation_div = None
                for div in root.iter():
                    if div.tag.endswith('div') and div.get('type') == 'translation':
                        translation_div = div
                        break
                
                # Search for books in the appropriate container
                search_root = translation_div if translation_div is not None else root
                
                book_counter = 0
                for book_div in search_root.iter():
                    if (book_div.tag.endswith('div') and 
                        book_div.get('type') == 'textpart' and 
                        book_div.get('subtype', '').lower() == 'book'):
                        
                        books_found = True
                        book_counter += 1
                        book_num = book_div.get('n', '1')
                        try:
                            book_id = f"{work_id}.{int(book_num):03d}"
                        except ValueError:
                            # If book number is not numeric, use sequential numbering
                            book_id = f"{work_id}.{book_counter:03d}"
                            print(f"        → Non-numeric book '{book_num}', using book {book_counter}")
                        
                        # Extract translation segments with milestones
                        count = extract_translation_segments(book_div, book_id, cursor, translator)
                        if count == 0 and translation_div is None:
                            print(f"        Warning: No segments extracted for {book_id}")
                
                # If no books found, treat as single book
                if not books_found:
                    book_id = f"{work_id}.001"
                    if translation_div is not None:
                        extract_translation_segments(translation_div, book_id, cursor, translator)
                    else:
                        for body in root.iter():
                            if body.tag.endswith('body'):
                                extract_translation_segments(body, book_id, cursor, translator)
                                break
                    
        except Exception as e:
            print(f"      Error processing translation {trans_file}: {e}")

def process_prose_with_books(root, work_id, cursor, language):
    """Process prose texts that have book divisions (like Herodotus)"""
    import re
    
    books_processed = 0
    
    # Process each book
    for book_div in root.iter():
        if not (book_div.tag.endswith('div') and 
                book_div.get('type') == 'textpart' and 
                book_div.get('subtype', '').lower() == 'book'):
            continue
            
        book_n = book_div.get('n', str(books_processed + 1))
        # Try to parse as integer, otherwise use sequential numbering
        try:
            book_num = int(book_n)
        except ValueError:
            book_num = books_processed + 1
        book_id = f"{work_id}.{book_num:03d}"
        books_processed += 1
        
        all_lines = []
        line_num = 0
        
        # Process sections within this book
        for elem in book_div.iter():
            if (elem.tag.endswith('div') and 
                elem.get('type') == 'textpart' and 
                elem.get('subtype') in ['section', 'chapter']):
                
                section_n = elem.get('n', str(line_num + 1))
                
                # Extract paragraphs from this section
                for p in elem.iter():
                    if p.tag.endswith('p'):
                        text = ''.join(p.itertext()).strip()
                        if text and len(text) > 5:  # Skip very short text
                            # Split long paragraphs into sentences
                            if language == 'greek':
                                sentences = re.split(r'[.!?·;]\s+', text)
                            else:
                                sentences = re.split(r'[.!?]\s+', text)
                            
                            # Process each sentence as a line
                            for sentence in sentences:
                                sentence = sentence.strip()
                                # Filter out editorial notes
                                if (sentence and len(sentence) > 10 and 
                                    not re.match(r'^[A-Z]:', sentence) and
                                    not sentence.startswith('em.') and
                                    not sentence.startswith('add.') and
                                    'Nauck' not in sentence and
                                    'Mullach' not in sentence and
                                    not sentence.startswith('id.')):
                                    line_num += 1
                                    all_lines.append({
                                        'number': line_num,
                                        'text': sentence,
                                        'section': section_n,
                                        'xml': ''
                                    })
        
        if all_lines:
            # Insert book with actual line count
            cursor.execute("""
                INSERT OR REPLACE INTO books 
                (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (book_id, work_id, book_num, f"Book {book_num}", 1, len(all_lines), len(all_lines)))
            
            # Clear existing text lines for this book
            cursor.execute("DELETE FROM text_lines WHERE book_id = ?", (book_id,))
            
            # Insert all lines
            for line in all_lines:
                cursor.execute("""
                    INSERT INTO text_lines 
                    (book_id, line_number, line_text, line_xml, speaker)
                    VALUES (?, ?, ?, ?, ?)
                """, (book_id, line['number'], line['text'], line['xml'], None))
            
            print(f"      Book {book_num}: {len(all_lines)} lines")
    
    if books_processed == 0:
        print(f"      Warning: No books found for {work_id}")

def process_prose_text(root, work_id, cursor, language):
    """Process prose texts which have sections instead of lines"""
    import re
    
    # First check if this prose work has book divisions (like Herodotus)
    has_books = False
    for div in root.iter():
        if (div.tag.endswith('div') and 
            div.get('type') == 'textpart' and 
            div.get('subtype', '').lower() == 'book'):
            has_books = True
            break
    
    # If it has books, process it with book divisions
    if has_books:
        process_prose_with_books(root, work_id, cursor, language)
        return
    
    # Otherwise treat the entire work as one book
    book_id = f"{work_id}.001"
    all_lines = []
    line_num = 0
    
    # Find all sections (divs with type="textpart" and subtype="section" or "chapter")
    for elem in root.iter():
        if (elem.tag.endswith('div') and 
            elem.get('type') == 'textpart' and 
            elem.get('subtype') in ['section', 'chapter']):
            
            section_n = elem.get('n', str(line_num + 1))
            
            # First try to extract paragraphs from this section
            paragraphs_found = False
            for p in elem.iter():
                if p.tag.endswith('p'):
                    paragraphs_found = True
                    text = ''.join(p.itertext()).strip()
                    if text and len(text) > 5:  # Skip very short text
                        # Split long paragraphs into sentences for better readability
                        # Greek uses · or ; as sentence separators, plus standard . ! ?
                        if language == 'greek':
                            # Split on Greek punctuation
                            sentences = re.split(r'[.!?·;]\s+', text)
                        else:
                            # Split on Latin punctuation
                            sentences = re.split(r'[.!?]\s+', text)
                        
                        # Process each sentence as a line
                        for sentence in sentences:
                            sentence = sentence.strip()
                            # Filter out editorial notes and very short sentences
                            if (sentence and len(sentence) > 10 and 
                                not re.match(r'^[A-Z]:', sentence) and  # Skip "W:" style notes
                                not sentence.startswith('em.') and      # Skip "em." notes
                                not sentence.startswith('add.') and     # Skip "add." notes
                                'Nauck' not in sentence and             # Skip Nauck references
                                'Mullach' not in sentence and           # Skip Mullach references
                                not sentence.startswith('id.')):        # Skip "id." references
                                line_num += 1
                                all_lines.append({
                                    'number': line_num,
                                    'text': sentence,
                                    'section': section_n,
                                    'xml': ''
                                })
            
            # If no paragraphs found, treat the entire section text as prose
            if not paragraphs_found:
                # Extract text but exclude notes and milestones
                text_parts = []
                for text_elem in elem.iter():
                    if (text_elem.tag.endswith('p') or  # Include paragraph text
                        (text_elem.tag.endswith('div') and text_elem == elem)):  # Include direct div text
                        if not (text_elem.tag.endswith('note') or 
                                text_elem.tag.endswith('milestone')):
                            elem_text = text_elem.text or ''
                            if elem_text.strip():
                                text_parts.append(elem_text.strip())
                
                text = ' '.join(text_parts)
                text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                
                # Also try getting just direct text content, filtering notes
                if not text or len(text) < 20:
                    all_text = []
                    for child in elem:
                        if not (child.tag.endswith('note') or 
                                child.tag.endswith('milestone') or
                                'anchored' in child.attrib):
                            child_text = ''.join(child.itertext())
                            if child_text.strip():
                                all_text.append(child_text.strip())
                    text = ' '.join(all_text)
                    text = re.sub(r'\s+', ' ', text)
                
                if text and len(text) > 20:  # Skip very short sections
                    if language == 'greek':
                        sentences = re.split(r'[.!?·;]\s+', text)
                    else:
                        sentences = re.split(r'[.!?]\s+', text)
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        # Filter out editorial notes and very short sentences
                        if (sentence and len(sentence) > 20 and 
                            not re.match(r'^[A-Z]:', sentence) and  # Skip "W:" style notes
                            not sentence.startswith('em.') and      # Skip "em." notes
                            not sentence.startswith('add.') and     # Skip "add." notes
                            'Nauck' not in sentence and             # Skip Nauck references
                            'Mullach' not in sentence):             # Skip Mullach references
                            line_num += 1
                            all_lines.append({
                                'number': line_num,
                                'text': sentence,
                                'section': section_n,
                                'xml': ''
                            })
    
    if all_lines:
        # Insert book with actual line count
        cursor.execute("""
            INSERT OR IGNORE INTO books 
            (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_id, work_id, 1, "Complete Text", 1, len(all_lines), len(all_lines)))
        
        # Insert lines
        for line in all_lines:
            cursor.execute("""
                INSERT OR IGNORE INTO text_lines 
                (book_id, line_number, line_text, line_xml, speaker)
                VALUES (?, ?, ?, ?, ?)
            """, (book_id, line['number'], line['text'], line['xml'], None))
            
            # Insert words into words table
            words = line['text'].split()
            for word_pos, word in enumerate(words, 1):
                if language == 'greek':
                    word_normalized = normalize_greek(word)
                else:
                    word_normalized = word.lower()
                
                if word_normalized:  # Only insert if normalized form is not empty
                    cursor.execute("""
                        INSERT INTO words 
                        (word, word_normalized, book_id, line_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    """, (word, word_normalized, book_id, line['number'], word_pos))
        
        print(f"      Complete Text: {len(all_lines)} lines")

def process_text_file(xml_path, work_id, cursor, language):
    """Process a single text file and extract books/lines"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Check if this is a dramatic text with different structure
        author_id = work_id.split('.')[0]
        # Drama authors: Aeschylus, Sophocles, Euripides, Aristophanes (ONLY these are true dramas)
        is_drama = author_id in ['tlg0085', 'tlg0011', 'tlg0006', 'tlg0019']
        # Prose authors: Plutarch, Herodotus, Thucydides, Xenophon, Plato, Aristotle
        # Plato's dialogues have speakers but should be treated as prose, not drama
        is_prose_author = author_id in ['tlg0007', 'tlg0016', 'tlg0003', 'tlg0032', 'tlg0059', 'tlg0086']
        
        # Special handling for Aristotle's Politics (which has books)
        if work_id == 'tlg0086.tlg035':
            print(f"      Special handling for Aristotle's Politics...")
            process_prose_with_books(root, work_id, cursor, language)
            return
        
        # Check if this is prose by looking for paragraphs
        # Count actual elements to determine if it's primarily prose or poetry
        p_count = sum(1 for elem in root.iter() if elem.tag.endswith('p'))
        l_count = sum(1 for elem in root.iter() if elem.tag.endswith('l'))
        section_count = sum(1 for elem in root.iter() if elem.tag.endswith('div') and 
                           elem.get('type') == 'textpart' and 
                           elem.get('subtype') in ['section', 'chapter'])
        
        # Prose detection logic:
        # 1. Known prose authors should always be treated as prose
        # 2. Works with many paragraphs relative to lines are prose
        # 3. Works with sections/chapters and paragraphs are likely prose
        is_prose = (is_prose_author or 
                   (p_count > 0 and p_count > (l_count * 2)) or
                   (section_count > 0 and p_count > 0 and p_count >= section_count))
        
        if is_prose:
            # For prose texts, process sections as the main unit
            process_prose_text(root, work_id, cursor, language)
            return
        elif is_drama:
            # For dramatic texts, treat the entire play as one book
            book_id = f"{work_id}.001"
            lines = []
            current_speaker = None
            
            # Extract ALL lines with their original line numbers and speakers
            for elem in root.iter():
                # Track current speaker
                if elem.tag.endswith('speaker'):
                    current_speaker = elem.text
                    
                if elem.tag.endswith('l'):
                    line_n = elem.get('n')
                    if line_n and line_n.isdigit():
                        text = ''.join(elem.itertext()).strip()
                        
                        if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern', 'This pointer']):
                            lines.append({
                                'number': int(line_n),
                                'text': text,
                                'xml': ET.tostring(elem, encoding='unicode'),
                                'speaker': current_speaker
                            })
            
            # Sort by line number to ensure correct order
            lines.sort(key=lambda x: x['number'])
            
            if lines:
                # Insert single book for the entire play
                cursor.execute("""
                    INSERT OR IGNORE INTO books 
                    (id, work_id, book_number, label, start_line, end_line, line_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (book_id, work_id, 1, "Complete Text", 1, len(lines), len(lines)))
                
                # Insert lines
                for line in lines:
                    cursor.execute("""
                        INSERT OR IGNORE INTO text_lines 
                        (book_id, line_number, line_text, line_xml, speaker)
                        VALUES (?, ?, ?, ?, ?)
                    """, (book_id, line['number'], line['text'], line['xml'], line.get('speaker')))
                    
                    # Insert words into words table
                    words = line['text'].split()
                    for word_pos, word in enumerate(words, 1):
                        if language == 'greek':
                            word_normalized = normalize_greek(word)
                        else:
                            word_normalized = word.lower()
                        
                        if word_normalized:  # Only insert if normalized form is not empty
                            cursor.execute("""
                                INSERT INTO words 
                                (word, word_normalized, book_id, line_number, word_position)
                                VALUES (?, ?, ?, ?, ?)
                            """, (word, word_normalized, book_id, line['number'], word_pos))
                
                print(f"      Complete Text: {len(lines)} lines")
            return
        
        # For non-dramatic texts, use the original book-based logic
        books_processed = 0
        
        # Look for divs with type="textpart" and subtype="book"
        for div in root.iter():
            if not div.tag.endswith('div'):
                continue
            
            div_type = div.get('type', '')
            div_subtype = div.get('subtype', '')
            div_n = div.get('n', '')
            
            # Check if this is a book div - must have type="textpart" and subtype="book" (case-insensitive)
            if div_type == 'textpart' and div_subtype.lower() == 'book':
                book_num = int(div_n) if div_n.isdigit() else books_processed + 1
                book_id = f"{work_id}.{book_num:03d}"
                
                # Extract lines from this book
                lines = []
                line_num = 0
                
                for elem in div.iter():
                    if elem.tag.endswith('l') or elem.tag.endswith('line'):
                        line_num += 1
                        text = ''.join(elem.itertext()).strip()
                        
                        if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                            lines.append({
                                'number': line_num,
                                'text': text,
                                'xml': ET.tostring(elem, encoding='unicode')
                            })
                
                if lines:
                    # Insert book
                    cursor.execute("""
                        INSERT OR IGNORE INTO books 
                        (id, work_id, book_number, label, start_line, end_line, line_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (book_id, work_id, book_num, f"Book {book_num}", 
                          1, len(lines), len(lines)))
                    
                    # Insert lines
                    for line in lines:
                        cursor.execute("""
                            INSERT OR IGNORE INTO text_lines 
                            (book_id, line_number, line_text, line_xml, speaker)
                            VALUES (?, ?, ?, ?, ?)
                        """, (book_id, line['number'], line['text'], line['xml'], None))
                        
                        # Insert words into words table
                        words = line['text'].split()
                        for word_pos, word in enumerate(words, 1):
                            if language == 'greek':
                                word_normalized = normalize_greek(word)
                            else:
                                word_normalized = word.lower()
                            
                            if word_normalized:  # Only insert if normalized form is not empty
                                cursor.execute("""
                                    INSERT INTO words 
                                    (word, word_normalized, book_id, line_number, word_position)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (word, word_normalized, book_id, line['number'], word_pos))
                    
                    books_processed += 1
                    print(f"      Book {book_num}: {len(lines)} lines")
        
        # If no books found, treat the whole text as one book
        if books_processed == 0:
            book_id = f"{work_id}.001"
            lines = []
            line_num = 0
            
            for elem in root.iter():
                if elem.tag.endswith('l') or elem.tag.endswith('line'):
                    line_num += 1
                    text = ''.join(elem.itertext()).strip()
                    
                    if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                        lines.append({
                            'number': line_num,
                            'text': text,
                            'xml': ET.tostring(elem, encoding='unicode')
                        })
            
            if lines:
                cursor.execute("""
                    INSERT OR IGNORE INTO books 
                    (id, work_id, book_number, label, start_line, end_line, line_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (book_id, work_id, 1, "Book 1", 1, len(lines), len(lines)))
                
                for line in lines:
                    cursor.execute("""
                        INSERT OR IGNORE INTO text_lines 
                        (book_id, line_number, line_text, line_xml, speaker)
                        VALUES (?, ?, ?, ?, ?)
                    """, (book_id, line['number'], line['text'], line['xml'], None))
                    
                    # Insert words into words table
                    words = line['text'].split()
                    for word_pos, word in enumerate(words, 1):
                        if language == 'greek':
                            word_normalized = normalize_greek(word)
                        else:
                            word_normalized = word.lower()
                        
                        if word_normalized:  # Only insert if normalized form is not empty
                            cursor.execute("""
                                INSERT INTO words 
                                (word, word_normalized, book_id, line_number, word_position)
                                VALUES (?, ?, ?, ?, ?)
                            """, (word, word_normalized, book_id, line['number'], word_pos))
                
                print(f"      Single book: {len(lines)} lines")
                
    except Exception as e:
        print(f"    Error processing {xml_path}: {e}")
        import traceback
        traceback.print_exc()

def process_perseus_author(author_dir, language, cursor):
    """Process all works for a single author"""
    author_id = author_dir.name
    
    # Read author metadata
    author_cts = author_dir / "__cts__.xml"
    author_name = author_id  # default
    
    if author_cts.exists():
        try:
            tree = ET.parse(author_cts)
            root = tree.getroot()
            
            # Find groupname
            for elem in root.iter():
                if 'groupname' in elem.tag.lower():
                    author_name = elem.text or author_id
                    break
        except:
            pass
    
    
    print(f"\nProcessing author: {author_name} ({author_id})")
    
    # Insert author
    cursor.execute("INSERT OR IGNORE INTO authors VALUES (?, ?, ?, ?, ?)",
                   (author_id, author_name, None, language, 0))
    
    works_processed = 0
    
    # Process each work
    for work_dir in author_dir.iterdir():
        if not work_dir.is_dir() or work_dir.name.startswith('__'):
            continue
        
        work_num = work_dir.name
        work_id = f"{author_id}.{work_num}"
        
        # Read work metadata
        work_cts = work_dir / "__cts__.xml"
        if not work_cts.exists():
            print(f"  Warning: No metadata for work {work_id}")
            continue
        
        work_info = parse_cts_metadata(work_cts)
        if not work_info:
            continue
        
        # For title_english, prefer English, then Latin, then work_num
        title_english = work_info.get('title_english') or work_info.get('title_latin') or work_num
        
        # Common Latin to English title mappings
        latin_to_english = {
            'Carmina': 'Odes',
            'Epistulae': 'Epistles',
            'Sermones': 'Satires',
            'Epodi': 'Epodes',
            'De Bello Gallico': 'The Gallic War',
            'De Bello Civili': 'The Civil War',
            'Metamorphoses': 'Metamorphoses',
            'Fasti': 'Fasti',
            'Tristia': 'Tristia',
            'Ex Ponto': 'Letters from Pontus',
            'Heroides': 'Heroides',
            'Amores': 'The Loves',
            'Remedia Amoris': 'The Cure for Love',
            'Medicamina Faciei Femineae': 'Cosmetics for Ladies'
        }
        
        # If we only have a Latin title, try to map it to English
        if not work_info.get('title_english') and title_english in latin_to_english:
            title_english = latin_to_english[title_english]
        
        # Find text files first - before processing anything
        text_files = list(work_dir.glob("*.xml"))
        text_files = [f for f in text_files if not f.name.startswith('__')]
        
        if not text_files:
            print(f"  Skipping work: {title_english} ({work_id}) - no text files found")
            continue
        
        # Check if we have a suitable text file for this language
        text_file = None
        for f in text_files:
            if 'perseus' in f.name and (
                ('grc' in f.name and language == 'greek') or 
                ('lat' in f.name and language == 'latin')
            ):
                text_file = f
                break
        
        if not text_file:
            print(f"  Skipping work: {title_english} ({work_id}) - no suitable {language} text file found")
            continue
        
        print(f"  Processing work: {title_english} ({work_id})")
        
        # Insert work (only if we have suitable text files)
        cursor.execute("""
            INSERT OR IGNORE INTO works 
            (id, author_id, title, title_alt, title_english, type, urn, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            work_id,
            author_id,
            work_info.get('title_greek') or work_info.get('title_latin') or title_english,
            work_info.get('title_latin'),
            title_english,
            work_info.get('type', 'text'),
            work_info.get('urn', f"urn:cts:{language}Lit:{work_id}"),
            f"{title_english} by {author_name}"
        ))
        
        works_processed += 1
        print(f"    Reading {text_file.name}...")
        
        # Parse the text
        process_text_file(text_file, work_id, cursor, language)
        
        # Process translations for this work
        process_translations(work_dir, work_id, cursor)
    
    # If no works were processed, remove the author
    if works_processed == 0:
        print(f"    No suitable works found, removing author: {author_name} ({author_id})")
        cursor.execute("DELETE FROM authors WHERE id = ?", (author_id,))

def generate_manifest(cursor):
    """Generate a manifest file with database contents"""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "database_version": "2.0",
        "statistics": {},
        "authors": []
    }
    
    # Get overall statistics
    cursor.execute("SELECT COUNT(*) FROM authors")
    manifest["statistics"]["total_authors"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM works")
    manifest["statistics"]["total_works"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM books")
    manifest["statistics"]["total_books"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    manifest["statistics"]["total_lines"] = cursor.fetchone()[0]
    
    # word_forms statistics removed - not needed
    
    cursor.execute("SELECT COUNT(*) FROM translation_segments")
    manifest["statistics"]["total_translation_segments"] = cursor.fetchone()[0]
    
    # Dictionary and lemma statistics
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
    manifest["statistics"]["total_dictionary_entries"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    manifest["statistics"]["total_lemma_mappings"] = cursor.fetchone()[0]
    
    # Dictionary coverage by language
    cursor.execute("SELECT language, COUNT(*) FROM dictionary_entries GROUP BY language")
    dict_by_lang = cursor.fetchall()
    manifest["statistics"]["dictionary_by_language"] = {lang: count for lang, count in dict_by_lang}
    
    # Calculate translation coverage
    cursor.execute("""
        SELECT COUNT(DISTINCT w.id) as total_works,
               COUNT(DISTINCT CASE WHEN ts.id IS NOT NULL THEN w.id END) as works_with_trans
        FROM works w
        LEFT JOIN books b ON w.id = b.work_id
        LEFT JOIN translation_segments ts ON b.id = ts.book_id
    """)
    total_works, works_with_trans = cursor.fetchone()
    manifest["statistics"]["works_with_translations"] = works_with_trans
    manifest["statistics"]["translation_coverage_percent"] = round((works_with_trans / total_works * 100) if total_works > 0 else 0, 1)
    
    # Get author details with line counts
    cursor.execute("""
        SELECT a.id, a.name, a.language, 
               COUNT(DISTINCT w.id) as work_count,
               COUNT(DISTINCT b.id) as total_books,
               SUM(b.line_count) as total_lines
        FROM authors a
        LEFT JOIN works w ON a.id = w.author_id
        LEFT JOIN books b ON w.id = b.work_id
        GROUP BY a.id
        ORDER BY a.language, a.name
    """)
    
    for author_row in cursor.fetchall():
        author = {
            "id": author_row[0],
            "name": author_row[1],
            "language": author_row[2],
            "work_count": author_row[3],
            "total_books": author_row[4] or 0,
            "total_lines": author_row[5] or 0,
            "works": []
        }
        
        # Get works for this author
        cursor.execute("""
            SELECT w.id, w.title, w.title_english, 
                   COUNT(DISTINCT b.id) as book_count,
                   SUM(b.line_count) as total_lines,
                   COUNT(DISTINCT ts.translator) as translator_count
            FROM works w
            LEFT JOIN books b ON w.id = b.work_id
            LEFT JOIN translation_segments ts ON b.id = ts.book_id
            WHERE w.author_id = ?
            GROUP BY w.id
            ORDER BY w.id
        """, (author_row[0],))
        
        for work_row in cursor.fetchall():
            work = {
                "id": work_row[0],
                "title": work_row[1],
                "title_english": work_row[2],
                "book_count": work_row[3],
                "total_lines": work_row[4] or 0,
                "translator_count": work_row[5]
            }
            
            # Get book details
            cursor.execute("""
                SELECT book_number, label, line_count
                FROM books
                WHERE work_id = ?
                ORDER BY book_number
            """, (work_row[0],))
            
            work["books"] = []
            for book_row in cursor.fetchall():
                work["books"].append({
                    "number": book_row[0],
                    "label": book_row[1],
                    "line_count": book_row[2]
                })
            
            author["works"].append(work)
        
        manifest["authors"].append(author)
    
    # Save manifest
    manifest_path = Path(__file__).parent / "database_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Manifest saved to {manifest_path}")

def generate_quality_report(cursor):
    """Generate detailed quality report"""
    from collections import defaultdict
    
    # Create detailed line-by-line report
    report_lines = []
    report_lines.append("=== PERSEUS TEXTS DATABASE QUALITY REPORT ===")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append("")
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM authors")
    total_authors = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM works")
    total_works = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    total_lines = cursor.fetchone()[0]
    
    report_lines.append(f"Total Authors: {total_authors}")
    report_lines.append(f"Total Works: {total_works}")
    report_lines.append(f"Total Books: {total_books}")
    report_lines.append(f"Total Lines: {total_lines:,}")
    
    # Dictionary statistics
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
    total_dict = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    total_lemma = cursor.fetchone()[0]
    
    if total_dict > 0:
        report_lines.append(f"Dictionary Entries: {total_dict:,}")
        report_lines.append(f"Lemma Mappings: {total_lemma:,}")
    
    report_lines.append("")
    report_lines.append("=== DETAILED BREAKDOWN ===")
    report_lines.append("")
    
    # Get all data with translations
    cursor.execute("""
        SELECT 
            a.name as author_name,
            w.title_english as work_title,
            b.book_number,
            b.label as book_label,
            b.line_count,
            b.id as book_id,
            w.id as work_id
        FROM authors a
        JOIN works w ON a.id = w.author_id
        JOIN books b ON w.id = b.work_id
        ORDER BY a.name, w.title_english, b.book_number
    """)
    
    all_books = cursor.fetchall()
    
    # Get translation data
    cursor.execute("""
        SELECT 
            ts.book_id,
            ts.translator,
            COUNT(*) as segment_count,
            MIN(ts.start_line) as first_line,
            MAX(COALESCE(ts.end_line, ts.start_line)) as last_line
        FROM translation_segments ts
        WHERE ts.translator IS NOT NULL
        GROUP BY ts.book_id, ts.translator
        ORDER BY ts.book_id, ts.translator
    """)
    
    translations = defaultdict(list)
    for row in cursor.fetchall():
        book_id, translator, segments, first_line, last_line = row
        translations[book_id].append({
            "translator": translator,
            "segments": segments,
            "line_range": f"{first_line}-{last_line}"
        })
    
    # Format the report
    current_author = None
    current_work = None
    
    for row in all_books:
        author_name, work_title, book_num, book_label, line_count, book_id, work_id = row
        
        # Author header
        if author_name != current_author:
            if current_author is not None:
                report_lines.append("")  # Space between authors
            report_lines.append(f"[{author_name}]")
            current_author = author_name
            current_work = None
        
        # Work and book line
        if work_id != current_work:
            current_work = work_id
            # For single-book works
            cursor.execute("SELECT COUNT(*) FROM books WHERE work_id = ?", (work_id,))
            book_count = cursor.fetchone()[0]
            
            if book_count == 1:
                report_lines.append(f"{author_name} / {work_title} - {line_count or 0:,} lines")
            else:
                # Multi-book work - show the work title first
                cursor.execute("SELECT SUM(line_count) FROM books WHERE work_id = ?", (work_id,))
                total_work_lines = cursor.fetchone()[0] or 0
                report_lines.append(f"{author_name} / {work_title} - {total_work_lines:,} lines total")
        
        # For multi-book works, show individual books
        if book_count > 1:
            report_lines.append(f"{author_name} / {work_title} / {book_label} - {line_count or 0:,} lines")
        
        # Show translations for this book
        if book_id in translations:
            trans_list = []
            for trans in translations[book_id]:
                trans_list.append(f"{trans['translator']} {trans['segments']} segments")
            report_lines.append(f"{author_name} / {work_title} translations: {', '.join(trans_list)}")
    
    # Save as text file
    with open('database_quality_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print("✓ Quality report saved to database_quality_report.txt")

def extract_wiktionary_mappings():
    """Run Wiktionary extraction scripts if intermediate files don't exist"""
    print("\n=== CHECKING WIKTIONARY EXTRACTION FILES ===")
    
    script_dir = Path(__file__).parent
    wikt_dir = script_dir / "wiktionary-processing"
    
    # Check if intermediate files exist
    required_files = [
        (wikt_dir / "greek_inflection_of_mappings.json", 
         "wiktionary-processing/extract_inflection_of_template.py",
         "English Wiktionary inflections"),
        (wikt_dir / "ancient_greek_all_forms.json",
         "wiktionary-processing/extract_all_ancient_greek_forms.py", 
         "English Wiktionary all non-lemma forms"),
        (wikt_dir / "ancient_greek_all_morphology_correct.json",
         "wiktionary-processing/extract_greek_wiktionary_fixed.py",
         "Greek Wiktionary morphological forms"),
        (wikt_dir / "ancient_greek_declension_mappings.json",
         "wiktionary-processing/extract_declension_mappings.py",
         "Greek declension mappings")
    ]
    
    for json_file, script_path, desc in required_files:
        if not json_file.exists():
            print(f"\n{desc} file not found, extracting from Wiktionary dumps...")
            try:
                result = subprocess.run(
                    [sys.executable, script_path],
                    cwd=script_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                if result.stdout:
                    print(result.stdout)
                print(f"✓ {desc} extracted successfully")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to extract {desc}: {e.stderr}")
                # Continue anyway - the extraction might be optional
        else:
            print(f"✓ {desc} file already exists")
    
    print("\n✓ Wiktionary extraction files ready")

def load_wiktionary_mappings(cursor):
    """Load Ancient Greek morphological mappings from Wiktionary intermediate files"""
    
    # Look for all Wiktionary mapping files
    mapping_files = [
        ("wiktionary-processing/greek_inflection_of_mappings.json", "English Wiktionary (inflection_of)"),
        ("wiktionary-processing/ancient_greek_all_forms.json", "English Wiktionary (all non-lemma forms)"),
        ("wiktionary-processing/ancient_greek_all_morphology_correct.json", "Greek Wiktionary (All Forms)"),
        ("wiktionary-processing/ancient_greek_declension_mappings.json", "Greek Wiktionary (Declensions)")
    ]
    
    total_loaded = 0
    valid_lemmas = set()
    
    for relative_path, source_name in mapping_files:
        wiktionary_file = Path(__file__).parent / relative_path
        
        if not wiktionary_file.exists():
            print(f"Warning: {source_name} mappings file not found at {wiktionary_file}")
            continue
        
        print(f"\n=== LOADING {source_name.upper()} MORPHOLOGICAL MAPPINGS ===")
        print(f"Loading from: {wiktionary_file}")
        
        try:
            with open(wiktionary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            mappings = data.get('mappings', [])
            
            print(f"Source: {metadata.get('source', 'Unknown')}")
            print(f"Extraction date: {metadata.get('extraction_date', 'Unknown')}")
            print(f"Total mappings in file: {len(mappings):,}")
            
            if not mappings:
                print("Warning: No mappings found in file")
                continue
            
            # Get existing dictionary entries for validation (only once)
            if total_loaded == 0:
                cursor.execute("SELECT DISTINCT headword_normalized FROM dictionary_entries WHERE language = 'greek'")
                valid_lemmas = set(row[0] for row in cursor.fetchall())
                print(f"Found {len(valid_lemmas):,} Greek dictionary entries to match against")
            
            # Insert mappings
            inserted = 0
            skipped_duplicate = 0
            skipped_no_lemma = 0
            
            print("Inserting mappings...")
            for i, mapping in enumerate(mappings):
                # Only insert if the lemma exists in our dictionary
                if mapping['lemma'] not in valid_lemmas:
                    skipped_no_lemma += 1
                    continue
                
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO lemma_map 
                        (word_form, word_normalized, lemma, confidence, source, morph_info)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        mapping['word_form'],
                        mapping['word_form'],  # word_normalized same as word_form since already normalized
                        mapping['lemma'],
                        mapping['confidence'],
                        mapping['source'],
                        mapping.get('morph_info') or mapping.get('morph_type')
                    ))
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped_duplicate += 1
                    
                    # Progress indicator
                    if (i + 1) % 1000 == 0:
                        print(f"  Progress: {inserted:,} inserted, {skipped_duplicate:,} duplicates, {skipped_no_lemma:,} no matching lemma")
                
                except Exception as e:
                    print(f"  Warning: Failed to insert mapping: {e}")
            
            print(f"\n✓ {source_name} mappings loaded successfully!")
            print(f"  Mappings inserted: {inserted:,}")
            print(f"  Mappings skipped (duplicates): {skipped_duplicate:,}")
            print(f"  Mappings skipped (no dictionary entry): {skipped_no_lemma:,}")
            
            total_loaded += inserted
            
        except Exception as e:
            print(f"Error loading {source_name} mappings: {e}")
            import traceback
            traceback.print_exc()
    
    # Test coverage for known problematic words after loading all sources
    if total_loaded > 0:
        test_words = ['μηνιν', 'αειδε', 'πολλασ', 'ψυχασ', 'εθηκε', 'ουλομενην']
        print(f"\n  Testing coverage for known problematic words:")
        found_count = 0
        for word in test_words:
            cursor.execute("""
                SELECT COUNT(*) FROM lemma_map lm
                JOIN dictionary_entries de ON lm.lemma = de.headword_normalized
                WHERE lm.word_form = ?
            """, (word,))
            if cursor.fetchone()[0] > 0:
                found_count += 1
                print(f"    ✓ {word}")
            else:
                print(f"    ✗ {word}")
        
        print(f"  Coverage: {found_count}/{len(test_words)} test words found ({found_count/len(test_words)*100:.1f}%)")
    
    print(f"\n  Total mappings loaded from all sources: {total_loaded:,}")

def generate_comprehensive_lemmatization(cursor):
    """Generate lemma mappings for ALL unique words in texts using algorithmic approach"""
    
    # Since we don't have word_forms, we'll work with dictionary headwords instead
    # This will generate reverse mappings from inflected forms to lemmas
    print("Generating lemmatization mappings based on dictionary entries...")
    
    # Get all dictionary headwords
    cursor.execute("""
        SELECT DISTINCT headword_normalized 
        FROM dictionary_entries 
        WHERE language = 'greek'
        ORDER BY headword_normalized
    """)
    all_words = [row[0] for row in cursor.fetchall()]
    print(f"Total dictionary headwords: {len(all_words):,}")
    
    # Get all dictionary headwords for validation
    cursor.execute("""
        SELECT DISTINCT headword_normalized 
        FROM dictionary_entries 
        WHERE language = 'greek'
    """)
    valid_lemmas = set(row[0] for row in cursor.fetchall())
    print(f"Dictionary headwords available: {len(valid_lemmas):,}")
    
    # Common endings to try removing
    endings_to_remove = [
        # Noun endings
        'ων', 'ου', 'ω', 'ον', 'ε', 'α', 'ασ', 'ησ', 'η', 'αν', 'ην', 
        'οι', 'ων', 'οισ', 'ουσ', 'αι', 'ων', 'αισ', 'ασ',
        'οσ', 'εσ', 'ι', 'σι', 'των', 'τοσ', 'τησ', 'τον', 'την', 'τα', 'ται',
        # Verb endings
        'ει', 'εισ', 'ομεν', 'ετε', 'ουσι', 'ουσιν',
        'ομαι', 'εται', 'ομεθα', 'εσθε', 'ονται',
        'σω', 'σεισ', 'σει', 'σομεν', 'σετε', 'σουσι',
        'σα', 'σασ', 'σε', 'σαμεν', 'σατε', 'σαν',
        'κα', 'κασ', 'κε', 'καμεν', 'κατε', 'κασι',
        # Participles
        'μενοσ', 'μενη', 'μενον', 'μενου', 'μενησ', 'μενω',
        'ντοσ', 'ντι', 'ντα', 'ντεσ', 'ντων',
        # Aorist passive participles
        'θεισ', 'θεντοσ', 'θεντι', 'θεντα', 'θεντεσ', 'θεντων',
        'θεισα', 'θεισαν', 'θεν', 'θεντα'
    ]
    
    # Dictionary form endings to try adding
    dict_endings = ['οσ', 'η', 'ον', 'α', 'ω', 'ημι', 'μι']
    
    generated = 0
    print("\nGenerating algorithmic mappings for ALL words...")
    
    for i, word in enumerate(all_words):
        if (i + 1) % 10000 == 0:
            print(f"  Progress: {i+1:,}/{len(all_words):,} words...")
        
        found_lemmas = set()
        
        # Try the word itself
        if word in valid_lemmas:
            found_lemmas.add(word)
        
        # Try adding dictionary endings to the word as-is (for elided forms)
        for dict_ending in dict_endings:
            candidate = word + dict_ending
            if candidate in valid_lemmas:
                found_lemmas.add(candidate)
        
        # Try removing common endings
        for ending in endings_to_remove:
            if word.endswith(ending) and len(word) > len(ending) + 2:
                stem = word[:-len(ending)]
                
                # Try stem itself
                if stem in valid_lemmas:
                    found_lemmas.add(stem)
                
                # Try stem + dictionary endings
                for dict_ending in dict_endings:
                    candidate = stem + dict_ending
                    if candidate in valid_lemmas:
                        found_lemmas.add(candidate)
        
        # Try removing augment for verbs
        if word.startswith('ε') and len(word) > 3:
            unaugmented = word[1:]
            if unaugmented in valid_lemmas:
                found_lemmas.add(unaugmented)
            
            # Special case for εθηκε -> τιθημι
            if word.startswith('εθ'):
                if 'τιθημι' in valid_lemmas:
                    found_lemmas.add('τιθημι')
        
        # Special handling for aorist passive participles in -θεις
        if word.endswith('θεισ') and len(word) > 4:
            stem = word[:-4]
            # For -οω verbs, the ω before θ comes from ο+ω contraction
            if stem.endswith('ω'):
                # χολω-θεις -> χολ-οω
                stem_base = stem[:-1]  # Remove the ω
                candidate = stem_base + 'οω'  # Add back οω
                if candidate in valid_lemmas:
                    found_lemmas.add(candidate)
            # Try adding various verb endings
            for verb_ending in ['ω', 'εω', 'αω', 'οω', 'υω']:
                candidate = stem + verb_ending
                if candidate in valid_lemmas:
                    found_lemmas.add(candidate)
        
        # Try patronymic patterns (son of X)
        # Pattern 1: -ιδησ/-ιαδησ/-ιδου/-ιαδεω endings
        patronymic_endings = [
            ('ιδησ', 'ευσ'),    # e.g., ατρειδησ → ατρευσ
            ('ιαδησ', 'ευσ'),   # e.g., πηληιαδησ → πηλευσ
            ('ιδου', 'ευσ'),    # genitive
            ('ιαδεω', 'ευσ'),   # genitive
            ('ιδη', 'ευσ'),     # other cases
            ('ιαδη', 'ευσ'),
            ('ιδα', 'ευσ'),
            ('ιαδα', 'ευσ'),
            # Also try other name endings
            ('ιδησ', 'οσ'),     # some names end in -os
            ('ιαδησ', 'οσ'),
            ('ιδησ', 'ησ'),     # some names end in -es
            ('ιαδησ', 'ησ'),
        ]
        
        for pat_ending, name_ending in patronymic_endings:
            if word.endswith(pat_ending) and len(word) > len(pat_ending) + 2:
                # Extract base
                base = word[:-len(pat_ending)]
                
                # Handle vowel changes in patronymics
                # η → ε is common (e.g., Πηλη-ιάδης → Πηλεύς)
                if base.endswith('η') and name_ending == 'ευσ':
                    # η + ευσ → ευς (not εευς)
                    base_alt = base[:-1]
                    candidate = base_alt + name_ending
                    if candidate in valid_lemmas:
                        found_lemmas.add(candidate)
                elif base.endswith('ε') and name_ending == 'ευσ':
                    # If base already ends in ε, just add υσ
                    candidate = base + 'υσ'
                    if candidate in valid_lemmas:
                        found_lemmas.add(candidate)
                elif base.endswith('η'):
                    # For other endings, do normal vowel change
                    base_alt = base[:-1] + 'ε'
                    candidate = base_alt + name_ending
                    if candidate in valid_lemmas:
                        found_lemmas.add(candidate)
                
                # Try without vowel change too
                candidate = base + name_ending
                if candidate in valid_lemmas:
                    found_lemmas.add(candidate)
                
                # Also try the patronymic form itself as a lemma
                # (in case it's listed as a headword)
                patronymic_nom = word[:-1] + 'σ' if word.endswith('ου') or word.endswith('εω') else word
                if patronymic_nom.endswith('ησ'):
                    patronymic_nom = patronymic_nom[:-1] + 'σ'
                if patronymic_nom in valid_lemmas:
                    found_lemmas.add(patronymic_nom)
        
        # Pattern 2: For names ending in -ηοσ (genitive of -ευς names)
        # e.g., Ἀχιλλῆος (αχιληοσ) → Ἀχιλλεύς (αχιλλευσ)
        if word.endswith('ηοσ'):
            base = word[:-3]
            # Sometimes need to add λλ (e.g., αχιλ → αχιλλ)
            candidate = base + 'ευσ'
            if candidate in valid_lemmas:
                found_lemmas.add(candidate)
            # Try with doubled consonant
            if base and base[-1] in 'λμνρ':
                candidate = base + base[-1] + 'ευσ'
                if candidate in valid_lemmas:
                    found_lemmas.add(candidate)
        
        # Insert found lemmas with different confidence based on match type
        for lemma in found_lemmas:
            # Assign confidence based on how the lemma was found
            if lemma == word:
                confidence = 0.9  # Exact match
            elif word + 'οσ' == lemma or word + 'η' == lemma or word + 'ον' == lemma:
                confidence = 0.7  # Direct suffix addition (likely good for elided forms)
            elif lemma.endswith('ευσ') and any(word.endswith(pat[0]) for pat in patronymic_endings):
                confidence = 0.75  # Patronymic pattern match
            elif len(lemma) < len(word):
                confidence = 0.6  # Removed suffix (stem)
            else:
                confidence = 0.5  # Other transformations
            
            cursor.execute("""
                INSERT OR IGNORE INTO lemma_map 
                (word_form, word_normalized, lemma, confidence, source)
                VALUES (?, ?, ?, ?, ?)
            """, (word, word, lemma, confidence, 'algorithmic'))
            generated += 1
    
    print(f"\n✓ Generated {generated:,} algorithmic mappings")
    
    # Check final lemma map size
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    final_count = cursor.fetchone()[0]
    print(f"Total lemma mappings generated: {final_count:,}")

def optimize_lemma_map(cursor):
    """Optimize lemma_map by removing invalid entries"""
    print("\n=== OPTIMIZING LEMMA MAP ===")
    
    # Since we don't have word_forms, we'll just clean up invalid entries
    # Remove any lemma_map entries where the lemma doesn't exist in dictionary
    print("Removing invalid lemma mappings...")
    cursor.execute("""
        DELETE FROM lemma_map
        WHERE NOT EXISTS (
            SELECT 1 FROM dictionary_entries de
            WHERE de.headword_normalized = lemma_map.lemma
            AND de.language = 'greek'
        )
    """)
    deleted_count = cursor.rowcount
    print(f"Removed {deleted_count:,} invalid mappings")
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM lemma_map")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE morph_info IS NOT NULL")
    with_morph = cursor.fetchone()[0]
    
    print(f"\nTotal mappings: {final_count:,}")
    print(f"With morphology: {with_morph:,} ({with_morph/final_count*100:.1f}%)") if final_count > 0 else None
    
    # Ensure indexes exist
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lemma_map_word ON lemma_map(word_form)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lemma_map_lemma ON lemma_map(lemma)")
    # idx_lemma_map_normalized removed - Room doesn't expect it
    
    print("✓ Optimization complete!")

def create_database():
    """Create database from Perseus data"""
    
    # Paths
    script_dir = Path(__file__).parent
    db_path = script_dir / "perseus_texts.db"
    data_sources = script_dir.parent / "data-sources"
    
    # Check paths
    print("Checking data sources...")
    greek_dir = data_sources / "canonical-greekLit" / "data"
    latin_dir = data_sources / "canonical-latinLit" / "data"
    
    if not greek_dir.exists():
        print(f"Error: Greek texts directory not found at {greek_dir}")
        return
    
    if not latin_dir.exists():
        print(f"Error: Latin texts directory not found at {latin_dir}")
        return
    
    # Create new database
    print(f"\nCreating new database at {db_path}...")
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables with Room-compatible schema
    print("Creating tables...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_authors_language 
        ON authors(language)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_works_author 
        ON works(author_id)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_books_work 
        ON books(work_id)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_text_lines_book 
        ON text_lines(book_id)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            word_normalized TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_words_normalized 
        ON words(word_normalized)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_words_book_line 
        ON words(book_id, line_number)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_segments_book 
        ON translation_segments(book_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_segments_lines 
        ON translation_segments(book_id, start_line)
    """)
    
    # word_forms table removed - not needed for app functionality
    
    # word_forms indexes removed - not needed
    
    # Process specific authors we want
    print("\n=== PROCESSING GREEK AUTHORS ===")
    
    # Discover all Greek authors dynamically
    greek_authors = {}
    print("Discovering Greek authors...")
    
    for author_dir in sorted(greek_dir.iterdir()):
        if author_dir.is_dir() and author_dir.name.startswith("tlg"):
            cts_file = author_dir / "__cts__.xml"
            author_name = f"Author {author_dir.name}"
            
            if cts_file.exists():
                try:
                    tree = ET.parse(cts_file)
                    root = tree.getroot()
                    
                    # Find groupname element
                    ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
                    groupname_elem = root.find('.//ti:groupname', ns)
                    
                    if groupname_elem is not None and groupname_elem.text:
                        author_name = groupname_elem.text.strip()
                except Exception as e:
                    print(f"  Warning: Failed to parse {cts_file}: {e}")
            
            greek_authors[author_dir.name] = author_name
    
    print(f"\nDiscovered {len(greek_authors)} Greek authors")
    
    # Add phase control for testing
    import sys
    phase = sys.argv[1] if len(sys.argv) > 1 else "full"
    phase_limits = {"test": 30, "medium": 60, "full": None}
    
    if phase in phase_limits and phase_limits[phase]:
        # Get priority authors for testing
        priority_authors = ["tlg0012", "tlg0085", "tlg0011", "tlg0006", "tlg0019",
                           "tlg0007", "tlg0016", "tlg0003", "tlg0032", "tlg0059",
                           "tlg0086", "tlg0020", "tlg0033", "tlg0026"]
        
        selected = {}
        for auth_id in priority_authors:
            if auth_id in greek_authors and len(selected) < phase_limits[phase]:
                selected[auth_id] = greek_authors[auth_id]
        
        for auth_id, name in sorted(greek_authors.items()):
            if auth_id not in selected and len(selected) < phase_limits[phase]:
                selected[auth_id] = name
        
        greek_authors = selected
        print(f"\nPhase '{phase}': Limited to {len(greek_authors)} authors")
    
    # Process each Greek author with progress tracking
    total_authors = len(greek_authors)
    processed = 0
    failed_authors = []
    
    for author_id, author_name in sorted(greek_authors.items()):
        processed += 1
        author_path = greek_dir / author_id
        if author_path.exists():
            print(f"\n[{processed}/{total_authors}] Processing {author_name} ({author_id})")
            try:
                process_perseus_author(author_path, "greek", cursor)
                # Commit periodically
                if processed % 5 == 0:
                    conn.commit()
                    print(f"  Progress saved ({processed}/{total_authors} authors)")
            except Exception as e:
                print(f"  ERROR: {e}")
                failed_authors.append((author_id, author_name, str(e)))
        else:
            print(f"\n[{processed}/{total_authors}] Warning: {author_name} ({author_id}) not found")
            failed_authors.append((author_id, author_name, "Directory not found"))
    
    # Report failures
    if failed_authors:
        print(f"\n=== FAILED AUTHORS ({len(failed_authors)}) ===")
        for auth_id, name, error in failed_authors:
            print(f"  {name} ({auth_id}): {error}")
    
    print("\n=== PROCESSING LATIN AUTHORS ===")
    
    # Define Latin authors
    latin_authors = {
        "phi0959": "Ovid",
        "phi0690": "Virgil",
        "phi0893": "Horace"
    }
    
    # Process each Latin author
    for author_id, author_name in latin_authors.items():
        author_path = latin_dir / author_id
        if author_path.exists():
            print(f"\nProcessing {author_name} ({author_id})")
            process_perseus_author(author_path, "latin", cursor)
        else:
            print(f"\nWarning: {author_name} ({author_id}) not found")
    
    # Import LSJ dictionary
    print("\n=== PROCESSING LSJ DICTIONARY ===")
    lsj_path = data_sources / "canonical-pdlrefwk" / "data" / "viaf66541464" / "001" / "viaf66541464.001.perseus-eng1.xml"
    
    if lsj_path.exists():
        
        # Create dictionary tables
        print("Creating dictionary tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dictionary_entries (
                id INTEGER PRIMARY KEY NOT NULL,
                headword TEXT NOT NULL,
                headword_normalized TEXT NOT NULL,
                language TEXT NOT NULL,
                entry_xml TEXT,
                entry_html TEXT,
                entry_plain TEXT,
                source TEXT,
                CHECK (language IN ('greek', 'latin'))
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dictionary_headword_normalized 
            ON dictionary_entries(headword_normalized, language)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lemma_map (
                word_form TEXT NOT NULL,
                word_normalized TEXT NOT NULL,
                lemma TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                morph_info TEXT,
                PRIMARY KEY (word_form, lemma)
            )
        """)
        
        # idx_lemma_map_normalized removed - Room doesn't expect it
        
        # Parse and import LSJ
        parser = LSJParser()
        lsj_entries = parser.parse_lsj_xml(str(lsj_path))
        
        if lsj_entries:
            print(f"Importing {len(lsj_entries)} LSJ entries...")
            
            # Import dictionary entries
            for entry in lsj_entries:
                cursor.execute("""
                    INSERT INTO dictionary_entries 
                    (headword, headword_normalized, language, entry_xml, entry_html, entry_plain, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry['headword'],
                    entry['headword_normalized'], 
                    entry['language'],
                    entry['entry_xml'],
                    entry['entry_html'],
                    entry['entry_plain'],
                    entry['source']
                ))
            
            print("✓ LSJ dictionary entries imported successfully")
            
            # Generate and import lemma mappings
            print("Generating lemma mappings...")
            lemma_mappings = create_lemma_mappings(lsj_entries)
            
            if lemma_mappings:
                print(f"Importing {len(lemma_mappings)} lemma mappings...")
                
                for mapping in lemma_mappings:
                    cursor.execute("""
                        INSERT OR IGNORE INTO lemma_map
                        (word_form, word_normalized, lemma, confidence, source)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        mapping['word_form'],
                        mapping['word_normalized'],
                        mapping['lemma'],
                        mapping['confidence'],
                        mapping['source']
                    ))
                
                print("✓ Lemma mappings imported successfully")
            else:
                print("Warning: No lemma mappings generated")
        else:
            print("Warning: No LSJ entries found")
    else:
        print(f"Warning: LSJ file not found at {lsj_path}")
    
    # Extract Wiktionary mappings if needed
    extract_wiktionary_mappings()
    
    # Load Wiktionary morphological mappings
    load_wiktionary_mappings(cursor)
    
    # Generate comprehensive mappings for all words in texts
    print("\n=== GENERATING COMPREHENSIVE LEMMATIZATION ===")
    generate_comprehensive_lemmatization(cursor)
    
    # Optimize lemma map to only include words in texts
    optimize_lemma_map(cursor)
    
    # Commit
    conn.commit()
    
    # Show statistics
    print("\n=== DATABASE STATISTICS ===")
    
    cursor.execute("SELECT COUNT(*) FROM authors")
    print(f"Authors: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM works")
    print(f"Works: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM books")
    print(f"Books: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    print(f"Text lines: {cursor.fetchone()[0]}")
    
    # word_forms statistics removed - not needed
    
    cursor.execute("SELECT COUNT(*) FROM translation_segments")
    print(f"Translation segments: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
    dict_count = cursor.fetchone()[0]
    if dict_count > 0:
        print(f"Dictionary entries: {dict_count}")
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")  
    lemma_count = cursor.fetchone()[0]
    if lemma_count > 0:
        print(f"Lemma mappings: {lemma_count}")
    
    # Show author summary with line counts
    print("\n=== AUTHOR SUMMARY ===")
    cursor.execute("""
        SELECT a.name, 
               COUNT(DISTINCT w.id) as work_count,
               COUNT(DISTINCT b.id) as book_count,
               SUM(b.line_count) as total_lines
        FROM authors a
        LEFT JOIN works w ON a.id = w.author_id
        LEFT JOIN books b ON w.id = b.work_id
        GROUP BY a.id
        ORDER BY total_lines DESC
        LIMIT 20
    """)
    
    print(f"{'Author':<20} {'Works':>8} {'Books':>8} {'Lines':>10}")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"{row[0]:<20} {row[1]:>8} {row[2]:>8} {row[3] or 0:>10,}")
    
    # Show largest works
    print("\n=== LARGEST WORKS ===")
    cursor.execute("""
        SELECT a.name, w.title_english, 
               COUNT(b.id) as book_count,
               SUM(b.line_count) as total_lines
        FROM authors a
        JOIN works w ON a.id = w.author_id
        JOIN books b ON w.id = b.work_id
        GROUP BY w.id
        ORDER BY total_lines DESC
        LIMIT 15
    """)
    
    print(f"{'Author':<20} {'Work':<30} {'Books':>8} {'Lines':>10}")
    print("-" * 70)
    for row in cursor.fetchall():
        work_title = row[1][:28] + '..' if len(row[1]) > 30 else row[1]
        print(f"{row[0]:<20} {work_title:<30} {row[2]:>8} {row[3]:>10,}")
    
    # Generate manifest file
    generate_manifest(cursor)
    
    # Generate quality report
    generate_quality_report(cursor)
    
    # Print translation coverage
    cursor.execute("""
        SELECT COUNT(DISTINCT w.id) as total_works,
               COUNT(DISTINCT CASE WHEN ts.id IS NOT NULL THEN w.id END) as works_with_trans
        FROM works w
        LEFT JOIN books b ON w.id = b.work_id
        LEFT JOIN translation_segments ts ON b.id = ts.book_id
    """)
    total_works, works_with_trans = cursor.fetchone()
    coverage = (works_with_trans / total_works * 100) if total_works > 0 else 0
    print(f"\n=== TRANSLATION COVERAGE ===")
    print(f"Works with translations: {works_with_trans}/{total_works} ({coverage:.1f}%)")
    
    # Update has_translations flag for authors
    print("\nUpdating has_translations flag for authors...")
    cursor.execute("""
        UPDATE authors
        SET has_translations = 1
        WHERE id IN (
            SELECT DISTINCT a.id
            FROM authors a
            JOIN works w ON a.id = w.author_id
            JOIN books b ON w.id = b.work_id
            JOIN translation_segments ts ON b.id = ts.book_id
            WHERE ts.translation_text IS NOT NULL 
            AND LENGTH(TRIM(ts.translation_text)) > 10
        )
    """)
    conn.commit()
    
    # Print authors with translations
    cursor.execute("""
        SELECT COUNT(*) as total_authors,
               SUM(has_translations) as authors_with_trans
        FROM authors
        WHERE language = 'greek'
    """)
    total_authors, authors_with_trans = cursor.fetchone()
    print(f"Greek authors with translations: {authors_with_trans}/{total_authors}")
    
    # Create translation lookup table for better alignment
    print("\n=== CREATING TRANSLATION LOOKUP TABLE ===")
    try:
        create_translation_lookup_table(conn)
    except Exception as e:
        print(f"Warning during translation lookup table creation: {e}")
        print("Continuing...")
    
    conn.close()
    print("\n✓ Database created successfully!")


def create_translation_lookup_table(conn):
    """Create a normalized lookup table for translation alignment"""
    cursor = conn.cursor()
    
    # Drop and recreate the lookup table
    cursor.execute("DROP TABLE IF EXISTS translation_lookup")
    cursor.execute("""
        CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes to match Room entity definition exactly
    cursor.execute("CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)")
    cursor.execute("CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)")
    
    # Get all books with translations
    cursor.execute("""
        SELECT DISTINCT b.id, COUNT(DISTINCT tl.line_number), 
               MIN(tl.line_number), MAX(tl.line_number)
        FROM books b
        JOIN text_lines tl ON b.id = tl.book_id
        WHERE EXISTS (SELECT 1 FROM translation_segments ts WHERE ts.book_id = b.id)
        GROUP BY b.id
    """)
    
    books = cursor.fetchall()
    total_mappings = 0
    
    for book_id, line_count, min_line, max_line in books:
        # Get translation segments
        cursor.execute("""
            SELECT id, start_line, end_line
            FROM translation_segments
            WHERE book_id = ?
            ORDER BY start_line
        """, (book_id,))
        
        segments = cursor.fetchall()
        if not segments:
            continue
            
        # Get actual line numbers from text_lines
        cursor.execute("""
            SELECT DISTINCT line_number 
            FROM text_lines 
            WHERE book_id = ?
        """, (book_id,))
        valid_lines = set(row[0] for row in cursor.fetchall())
        
        # Detect if translation uses different numbering
        max_trans_line = max(seg[2] for seg in segments) if segments else 0
        needs_mapping = max_trans_line < max_line / 2 or max_trans_line > max_line * 2
        
        book_mappings = 0
        
        for seg_id, start, end in segments:
            if needs_mapping and max_trans_line < 500 and max_trans_line > 0:
                # Section-based translation - distribute across actual lines
                proportion_start = (start - 1) / max_trans_line
                proportion_end = end / max_trans_line
                
                mapped_start = int(min_line + proportion_start * (max_line - min_line))
                mapped_end = int(min_line + proportion_end * (max_line - min_line))
                
                for line_num in range(mapped_start, mapped_end + 1):
                    if line_num in valid_lines:
                        cursor.execute("""
                            INSERT OR IGNORE INTO translation_lookup 
                            VALUES (?, ?, ?)
                        """, (book_id, line_num, seg_id))
                        book_mappings += 1
            else:
                # Direct line mapping or close enough
                for line_num in range(start, end + 1):
                    if line_num in valid_lines:
                        cursor.execute("""
                            INSERT OR IGNORE INTO translation_lookup 
                            VALUES (?, ?, ?)
                        """, (book_id, line_num, seg_id))
                        book_mappings += 1
        
        # For lines without direct mappings, find nearest segment
        unmapped_lines = valid_lines - set(
            row[0] for row in cursor.execute(
                "SELECT DISTINCT line_number FROM translation_lookup WHERE book_id = ?", 
                (book_id,)
            )
        )
        
        if unmapped_lines and segments:
            for line_num in unmapped_lines:
                # Find nearest segment
                best_seg = None
                min_dist = float('inf')
                
                for seg_id, start, end in segments:
                    dist = min(abs(line_num - start), abs(line_num - end))
                    if dist < min_dist and dist < 100:  # Within 100 lines
                        min_dist = dist
                        best_seg = seg_id
                
                if best_seg:
                    cursor.execute("""
                        INSERT OR IGNORE INTO translation_lookup 
                        VALUES (?, ?, ?)
                    """, (book_id, line_num, best_seg))
                    book_mappings += 1
        
        total_mappings += book_mappings
        if book_mappings > 0:
            coverage = len(set(row[0] for row in cursor.execute(
                "SELECT line_number FROM translation_lookup WHERE book_id = ?", (book_id,)
            ))) / line_count * 100
            print(f"  {book_id}: {book_mappings} mappings ({coverage:.1f}% coverage)")
    
    conn.commit()
    print(f"\nTotal translation mappings: {total_mappings}")


def compress_and_copy_database():
    """Compress database and copy to asset pack location"""
    import shutil
    import os
    import zipfile
    
    asset_pack_dir = "../perseus_database/src/main/assets"
    os.makedirs(asset_pack_dir, exist_ok=True)
    
    if os.path.exists("perseus_texts.db"):
        # Remove old uncompressed file if exists
        uncompressed_path = os.path.join(asset_pack_dir, "perseus_texts.db")
        if os.path.exists(uncompressed_path):
            os.remove(uncompressed_path)
        
        # Create compressed version
        zip_path = os.path.join(asset_pack_dir, "perseus_texts.db.zip")
        print(f"\nCompressing database to {zip_path}...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write("perseus_texts.db", "perseus_texts.db")
        
        # Get file sizes
        original_size = os.path.getsize("perseus_texts.db") / (1024 * 1024)
        compressed_size = os.path.getsize(zip_path) / (1024 * 1024)
        
        print(f"Database compressed to asset pack location: {asset_pack_dir}")
        print(f"Original size: {original_size:.1f}MB")
        print(f"Compressed size: {compressed_size:.1f}MB ({compressed_size/original_size*100:.1f}%)")
        return True
    else:
        print("\nWarning: Database file not found for asset pack copy")
        return False


if __name__ == "__main__":
    import time
    start_time = time.time()
    
    # Create database
    create_database()
    print(f"\nTotal build time: {(time.time() - start_time)/60:.1f} minutes")
    
    # Compress and copy database
    compress_and_copy_database()
