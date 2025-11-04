#!/usr/bin/env python3
"""
Extract LSJ dictionary entries into the same format as Cunliffe:
{
  "headword": {
    "inflected_forms": [...],
    "definition": "..."
  }
}

No normalization - keeps all diacritics and apostrophes.
Only removes punctuation (period, comma, semi-colon, raised dot).
More careful extraction of inflected forms - only from grammatical contexts.
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set
from html import unescape

def clean_punctuation(text):
    """Remove only punctuation (period, comma, semi-colon, raised dot), keep diacritics"""
    return re.sub(r'[.,;·]', '', text)

def is_greek_word(word):
    """Check if a word contains Greek characters"""
    return any('\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF' for char in word)

def extract_text_content(element) -> str:
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
        child_text = extract_text_content(child)
        if child_text:
            text_parts.append(child_text)
        
        # Add tail text after child element
        if child.tail:
            text_parts.append(child.tail)
    
    return ''.join(text_parts).strip()

def extract_inflected_forms(entry_elem, headword) -> List[str]:
    """Extract inflected forms from the entry - only from grammatical contexts"""
    inflected_forms = set()

    # Articles and common particles that should never be extracted as inflected forms
    # These often appear in declension tables (e.g., "τὸ λέχος") and get incorrectly extracted
    ARTICLE_PARTICLES = {
        'ὁ', 'ἡ', 'τό', 'τὸ', 'οἱ', 'αἱ', 'τά', 'τὰ', 'τα',  # articles
        'τοῦ', 'τῆς', 'τῶν',  # genitive articles
        'τῷ', 'τῇ', 'τοῖς', 'ταῖς',  # dative articles
        'τόν', 'τὸν', 'τήν', 'τὴν', 'τούς', 'τοὺς', 'τάς', 'τὰς',  # accusative articles
        'ἐν', 'εἰς', 'ἐκ', 'ἐξ', 'ἔς', 'ἀπό', 'ἀπ', 'κατά', 'κατ', 'μετά', 'μετ',  # common prepositions
        'καί', 'καὶ', 'δέ', 'δὲ', 'τε', 'γάρ', 'γὰρ', 'ἀλλά', 'ἀλλὰ',  # common particles
        'ὡς', 'ὥς', 'ὅτι', 'εἰ', 'ἐάν', 'ἐὰν', 'ἄν', 'ἂν',  # common conjunctions
        'τι', 'τί', 'τις', 'τίς',  # indefinite/interrogative pronouns (too common)
        'εὐ', 'εὖ', 'κα', 'ος',  # common prefixes/particles that get extracted incorrectly
    }

    # 1. Extract forms from orth elements within form groups
    for form_elem in entry_elem.findall('.//form'):
        for orth_elem in form_elem.findall('.//orth'):
            form = extract_text_content(orth_elem)
            if form and is_greek_word(form):
                form = clean_punctuation(form)
                # Filter out: same as headword, too short, or common articles/particles
                if form and form != headword and len(form) > 2 and form not in ARTICLE_PARTICLES:
                    inflected_forms.add(form)
    
    # 2. Look for verb forms in grammatical patterns with explicit markers
    grammatical_patterns = [
        # Verb tenses with explicit markers
        r'(?:aor|aorist)[1-2]?\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:pf|perf|perfect)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:fut|future)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:pres|present)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:impf|imperf|imperfect)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:plpf|pluperf|pluperfect)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Verb moods
        r'(?:imper|imperative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:subj|subjunctive)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:opt|optative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Verb forms
        r'(?:inf|infinitive)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:part|participle)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Voice
        r'(?:act|active)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:mid|middle)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:pass|passive)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:med|medio-pass|medio-passive)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Noun cases with explicit markers
        r'(?:nom|nominative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:gen|genitive)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:dat|dative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:acc|accusative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:voc|vocative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Number
        r'(?:pl|plur|plural)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:du|dual)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Dialectal forms
        r'(?:Ion|Ionic)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:Att|Attic)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:Dor|Doric)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:Aeol|Aeolic)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:Ep|Epic)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        # Other forms
        r'(?:fem|feminine)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:masc|masculine)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:neut|neuter)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:comp|comparative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'(?:sup|superl|superlative)\.\s*([\u0370-\u03FF\u1F00-\u1FFF]+)',
    ]
    
    # Only look in specific sections likely to contain grammatical forms
    for gram_elem in entry_elem.findall('.//gram'):
        gram_text = extract_text_content(gram_elem)
        for pattern in grammatical_patterns:
            for match in re.finditer(pattern, gram_text, re.IGNORECASE):
                form = match.group(1)
                form = clean_punctuation(form)
                # Use same filters as orth extraction
                if form and form != headword and len(form) > 2 and form not in ARTICLE_PARTICLES:
                    inflected_forms.add(form)

    # Also check in the main entry text but only with grammatical markers
    full_text = extract_text_content(entry_elem)

    # Skip if this entry contains crasis explanation to avoid false positives
    if 'crasis for' in full_text.lower():
        # For crasis entries, don't extract from general patterns
        return sorted(list(inflected_forms))

    for pattern in grammatical_patterns:
        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            form = match.group(1)
            form = clean_punctuation(form)
            # Use same filters as orth extraction
            if form and form != headword and len(form) > 2 and form not in ARTICLE_PARTICLES:
                inflected_forms.add(form)
    
    # 3. Extract alternate forms from specific patterns
    alternate_patterns = [
        r'also\s+([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'later\s+([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'poet\.\s+([\u0370-\u03FF\u1F00-\u1FFF]+)',
        r'v\.l\.\s+([\u0370-\u03FF\u1F00-\u1FFF]+)',  # varia lectio
        # Removed equals pattern - it was capturing glosses/synonyms not inflected forms
        # e.g., "ψυχαί = ἄνθρωποι" means souls = people (synonym), not an inflection
    ]
    
    for pattern in alternate_patterns:
        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            form = match.group(1)
            form = clean_punctuation(form)
            # Use same filters as other extractions
            if form and form != headword and len(form) > 2 and len(form) < 20 and form not in ARTICLE_PARTICLES:
                inflected_forms.add(form)
    
    return sorted(list(inflected_forms))

def format_entry_text(entry_elem) -> str:
    """Format the complete dictionary entry as text"""
    parts = []
    
    # Extract etymology if present
    etym_elem = entry_elem.find('.//etym')
    if etym_elem is not None:
        etym_text = extract_text_content(etym_elem)
        if etym_text:
            parts.append(f"Etymology: {etym_text}")
    
    # Extract senses
    for sense_elem in entry_elem.findall('.//sense'):
        sense_parts = []
        
        # Get sense number
        sense_n = sense_elem.get('n', '')
        if sense_n:
            sense_parts.append(f"{sense_n}.")
        
        # Extract translations
        translations = []
        for trans_elem in sense_elem.findall('.//trans/tr'):
            trans_text = extract_text_content(trans_elem)
            if trans_text:
                translations.append(trans_text)
        
        if translations:
            sense_parts.append('; '.join(translations))
        
        # Extract usage information
        usages = []
        for usg_elem in sense_elem.findall('.//usg'):
            usg_text = extract_text_content(usg_elem)
            if usg_text:
                usages.append(usg_text)
        
        if usages:
            sense_parts.append(f"({', '.join(usages)})")
        
        if sense_parts:
            parts.append(' '.join(sense_parts))
    
    # If no structured senses, just get all text content
    if not parts:
        full_text = extract_text_content(entry_elem)
        if full_text:
            parts.append(full_text)
    
    return '\n'.join(parts)

def parse_lsj_xml(filepath: Path) -> Dict[str, Dict]:
    """Parse LSJ XML file and extract entries in standard format"""
    print(f"Parsing LSJ XML file: {filepath}")
    
    # Read and preprocess XML to handle entities
    with open(filepath, 'r', encoding='utf-8') as f:
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
    
    entries = {}
    entry_count = 0
    skipped_count = 0
    
    # Find all entry elements
    for entry_elem in root.findall('.//entry[@type="main"]'):
        entry_count += 1
        
        # Get the Greek headword from <form><orth lang="greek">
        headword = ""
        form_elem = entry_elem.find('.//form/orth[@lang="greek"]')
        if form_elem is not None:
            headword = extract_text_content(form_elem)
            headword = clean_punctuation(headword)
        
        # Skip if no Greek headword found
        if not headword or not is_greek_word(headword):
            skipped_count += 1
            continue
        
        # Extract inflected forms
        inflected_forms = extract_inflected_forms(entry_elem, headword)
        
        # Format complete definition
        definition = format_entry_text(entry_elem)
        
        # Store entry
        entries[headword] = {
            "inflected_forms": inflected_forms,
            "definition": definition
        }
        
        if entry_count % 5000 == 0:
            print(f"  Processed {entry_count} entries, extracted {len(entries)} valid entries, skipped {skipped_count}")
    
    print(f"\nExtracted {len(entries)} LSJ dictionary entries from {entry_count} total entries")
    print(f"Skipped {skipped_count} entries without Greek headwords")
    
    # Count entries with inflected forms
    entries_with_forms = sum(1 for e in entries.values() if e['inflected_forms'])
    total_forms = sum(len(e['inflected_forms']) for e in entries.values())
    print(f"Entries with inflected forms: {entries_with_forms} ({entries_with_forms/len(entries)*100:.1f}%)")
    print(f"Total inflected forms extracted: {total_forms}")
    
    return entries

def verify_extraction(dictionary_data):
    """Verify extraction quality by checking known entries"""
    print("\nVerifying extraction quality...")
    
    # Check for μῆνιν issue
    print("\nChecking μῆνιν mappings:")
    menin_found_in = []
    for headword, data in dictionary_data.items():
        if 'μῆνιν' in data['inflected_forms']:
            menin_found_in.append(headword)
    
    if menin_found_in:
        print(f"  μῆνιν found as inflected form of: {', '.join(menin_found_in[:5])}")
        if len(menin_found_in) > 5:
            print(f"  ... and {len(menin_found_in) - 5} more")
    else:
        print("  μῆνιν not found as inflected form")
    
    # Check some common words
    test_words = ['ἀγαθός', 'καί', 'λέγω', 'εἰμί', 'ἔχω', 'ποιέω', 'λαμβάνω', 'μῆνις']
    print("\nCommon words:")
    for word in test_words:
        if word in dictionary_data:
            forms = dictionary_data[word]['inflected_forms']
            print(f"  {word}: {len(forms)} inflected forms")
            if forms:
                print(f"    Example forms: {forms[:5]}...")
        else:
            print(f"  {word}: NOT FOUND")

def main():
    # Path to LSJ XML file
    lsj_path = Path(__file__).parent.parent.parent / "data-sources" / "canonical-pdlrefwk" / "data" / "viaf66541464" / "001" / "viaf66541464.001.perseus-eng1.xml"
    
    if not lsj_path.exists():
        print(f"Error: LSJ XML file not found at {lsj_path}")
        print("Please ensure the canonical-pdlrefwk repository is cloned in data-sources")
        raise FileNotFoundError(f"Required LSJ XML file missing: {lsj_path}")
    
    # Parse and extract
    dictionary_data = parse_lsj_xml(lsj_path)
    
    # Verify extraction
    verify_extraction(dictionary_data)
    
    # Save to JSON
    output_path = Path(__file__).parent / "extract_lsj_fixed.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dictionary_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved extracted data to {output_path}")
    
    # Show sample entries
    print("\nSample entries:")
    for i, (headword, data) in enumerate(list(dictionary_data.items())[:5]):
        print(f"\n{headword}:")
        print(f"  Inflected forms: {data['inflected_forms'][:5]}")
        print(f"  Definition: {data['definition'][:100]}...")

if __name__ == "__main__":
    main()