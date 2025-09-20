#!/usr/bin/env python3
"""
Extract Cunliffe dictionary entries into a clean intermediate format:
{
  "headword": {
    "inflected_forms": [...],
    "definition": "..."
  }
}

No normalization - keeps all diacritics and apostrophes.
Only removes punctuation (period, comma, semi-colon, raised dot).
Properly excludes words from quotations using sophisticated grammatical patterns.
"""

import re
import json
from pathlib import Path

def clean_punctuation(text):
    """Remove only punctuation (period, comma, semi-colon, raised dot), keep diacritics"""
    return re.sub(r'[.,;·]', '', text)

def is_greek_word(word):
    """Check if a word contains Greek characters"""
    return any('\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF' for char in word)

def extract_inflected_forms_proper(headword, entry_lines):
    """Extract only actual inflected forms, not words from quotations"""
    inflected_forms = []
    morphological_forms = []
    
    # Join lines for analysis
    full_text = '\n'.join(entry_lines)
    
    # Strategy: Only extract forms that appear in specific grammatical contexts
    # 1. Forms that appear immediately after grammatical abbreviations
    grammatical_patterns = [
        # After person/number/tense markers: "3 sing. aor. ἐτελέσθη"
        r'(?:\d+\s+)?(?:sing|pl|dual)\.?\s+(?:aor|pres|impf|fut|pf|plupf)\.?\s+(?:act|mid|pass|subj|opt|imper)?\s*\.?\s*([^\s,.:;]+)',
        # After mood markers: "Opt. τελέοι", "Subj. τελέῃ"
        r'(?:Opt\.|Optative|Subj\.|Subjunctive|Imper\.|Imperative)\.?\s+(?:\d+\s+)?(?:sing|pl|dual)?\s*\.?\s*([^\s,.:;]+)',
        # After participle markers: "Pple. τετελεσμένος"
        r'(?:Pple\.|Participle|Part\.)\.?\s+([^\s,.:;]+)',
        # After infinitive markers: "Infin. τελέεσθαι"
        r'(?:Infin\.|Infinitive|Inf\.)\.?\s+([^\s,.:;]+)',
        # After case markers for participles: "Nom. pl. masc. pple. τελέοντες"
        r'(?:Nom|Gen|Dat|Acc|Voc)\.?\s+(?:sing|pl|dual)\.?\s+(?:masc|fem|neut)\.?\s+(?:pple\.|part\.)?\s*([^\s,.:;]+)',
        # Future infinitive: "Fut. infin. τελέεσθαι"
        r'(?:Fut\.|Future)\.?\s+(?:infin\.|inf\.)\.?\s+([^\s,.:;]+)',
        # Forms in parentheses after grammatical info: "(ἐτελέσθη)"
        r'(?:sing|pl|dual)\.?\s+(?:aor|pres|impf|fut|pf|plupf)\.?\s*\(([^\s)]+)\)',
        # Iterative forms: "3 pl. pa. iterative ἐρίζεσκον"
        r'(?:\d+\s+)?(?:sing|pl|dual)\.?\s+(?:pa\.|pres\.|aor\.)?\s*iterative\s+([^\s,.:;]+)'
    ]
    
    for pattern in grammatical_patterns:
        for match in re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE):
            form = match.group(1).strip('.,;:()*†')
            if is_greek_word(form) and len(form) > 2:
                # Clean the form - only remove punctuation
                form = clean_punctuation(form)
                # Don't include the headword itself
                if form and form != headword and form not in inflected_forms:
                    inflected_forms.append(form)
    
    # 2. Also look for verb forms that are listed at the beginning of entries
    # These typically appear as: "Also τελείω (τελεσίω, fr. τελεσ-, τέλος)."
    also_pattern = r'Also\s+([^\s,()]+)'
    for match in re.finditer(also_pattern, full_text[:200]):  # Only check beginning
        form = match.group(1).strip('.,;:()*†')
        if is_greek_word(form) and len(form) > 2:
            form = clean_punctuation(form)
            if form and form != headword and form not in inflected_forms:
                inflected_forms.append(form)
    
    # 3. Extract morphological annotations with their forms
    annotation_patterns = [
        # "3 sing. aor. ἐτελέσθη"
        (r'((?:\d+\s+)?(?:sing|pl|dual)\.?\s+(?:aor|pres|impf|fut|pf|plupf)\.?\s+(?:act|mid|pass)?\.?)\s+([^\s,.:;]+)', 
         'verb_form'),
        # "Pple. τετελεσμένος"
        (r'((?:Pple\.|Participle|Part\.))\s+([^\s,.:;]+)', 
         'participle'),
        # "Infin. τελέεσθαι"
        (r'((?:Infin\.|Infinitive|Inf\.))\s+([^\s,.:;]+)', 
         'infinitive'),
        # "Opt. 3 sing. τελέοι"
        (r'((?:Opt\.|Optative)\s+(?:\d+\s+)?(?:sing|pl|dual)?\.?)\s+([^\s,.:;]+)', 
         'optative'),
        # "Subj. 3 sing. τελέῃ"
        (r'((?:Subj\.|Subjunctive)\s+(?:\d+\s+)?(?:sing|pl|dual)?\.?)\s+([^\s,.:;]+)', 
         'subjunctive'),
        # "Imper. τέλει"
        (r'((?:Imper\.|Imperative))\s+([^\s,.:;]+)', 
         'imperative'),
        # "Nom. pl. masc. pple. τελέοντες"
        (r'((?:Nom|Gen|Dat|Acc|Voc)\.?\s+(?:sing|pl|dual)\.?\s+(?:masc|fem|neut)\.?\s+(?:pple\.|part\.)?)\s+([^\s,.:;]+)', 
         'declined_form')
    ]
    
    for pattern, form_type in annotation_patterns:
        for match in re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE):
            morphology = match.group(1).strip()
            form = match.group(2).strip('.,;:()*†')
            
            if is_greek_word(form) and len(form) > 2:
                form = clean_punctuation(form)
                # Verify it's not the headword itself
                if form and form != headword:
                    morphological_forms.append({
                        'form': form,
                        'morphology': morphology,
                        'type': form_type
                    })
    
    return inflected_forms, morphological_forms

def parse_cunliffe_file(filepath):
    """Parse Cunliffe text file with proper inflected form extraction"""
    print(f"Parsing Cunliffe text file: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by separator
    entries = content.split('************************************************************')
    
    dictionary_data = {}
    entry_count = 0
    total_inflected = 0
    total_morphological = 0
    
    for entry_text in entries:
        lines = [line for line in entry_text.strip().split('\n') if line.strip()]
        if not lines:
            continue
            
        # First line should contain headword
        first_line = lines[0].strip()
        
        # Extract headword
        headword_match = re.match(r'^([^.,\[\s]+)', first_line)
        if not headword_match:
            continue
            
        headword = headword_match.group(1).strip('†*')
        
        # Skip if not Greek
        if not is_greek_word(headword):
            continue
        
        # Clean headword - only remove punctuation
        headword = clean_punctuation(headword)
        
        # Skip pure cross-reference entries
        if not headword or (len(lines) == 1 and '. See ' in first_line):
            continue
            
        entry_count += 1
        
        # Extract inflected forms properly
        inflected_forms, morphological_forms = extract_inflected_forms_proper(headword, lines)
        total_inflected += len(inflected_forms)
        total_morphological += len(morphological_forms)
        
        # Get definition (everything)
        definition = '\n'.join(lines)
        
        # Store the entry - we'll include the inflected forms in the simple format
        # but also keep track of morphological annotations internally
        dictionary_data[headword] = {
            'inflected_forms': inflected_forms,
            'definition': definition,
            # Keep morphological forms for potential future use
            '_morphological_forms': morphological_forms
        }
        
        if entry_count % 1000 == 0:
            print(f"  Processed {entry_count} entries...")
    
    print(f"✓ Extracted {len(dictionary_data)} dictionary entries")
    print(f"✓ Found {total_inflected} inflected forms")
    print(f"✓ Found {total_morphological} morphological annotations")
    
    return dictionary_data

def verify_extraction(dictionary_data):
    """Verify extraction quality by checking known entries"""
    print("\nVerifying extraction quality...")
    
    # Check if proper names have inflected forms (they shouldn't have many)
    proper_names = ['Ἀχιλλεύς', 'Ὀδυσσεύς', 'Ἕκτωρ', 'Ζεύς', 'Ἀπόλλων']
    print("Proper names (should have few inflected forms):")
    for name in proper_names:
        if name in dictionary_data:
            forms = dictionary_data[name]['inflected_forms']
            morph = dictionary_data[name].get('_morphological_forms', [])
            print(f"  {name}: {len(forms)} inflected forms, {len(morph)} morphological")
            if forms:
                print(f"    Forms: {forms[:3]}...")
    
    # Check regular verbs (should have many forms)
    verbs = ['τελέω', 'ἐρίζω', 'εἰμί', 'ἔρχομαι', 'δίδωμι', 'ποιέω']
    print("\nRegular verbs (should have many inflected forms):")
    for verb in verbs:
        if verb in dictionary_data:
            forms = dictionary_data[verb]['inflected_forms']
            morph = dictionary_data[verb].get('_morphological_forms', [])
            print(f"  {verb}: {len(forms)} inflected forms, {len(morph)} morphological")
            if forms:
                print(f"    Example forms: {forms[:3]}...")
            if morph and len(morph) > 0:
                m = morph[0]
                print(f"    Example morph: {m['form']} - {m['morphology']}")

def save_results(dictionary_data, output_file='extract_cunliffe_new.json'):
    """Save extracted data to JSON file"""
    output_path = Path(output_file)
    
    # Create clean version without internal fields
    clean_data = {}
    for headword, entry in dictionary_data.items():
        clean_data[headword] = {
            'inflected_forms': entry['inflected_forms'],
            'definition': entry['definition']
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved extracted data to {output_path}")

def main():
    # Parse Cunliffe text file
    cunliffe_path = Path(__file__).parent.parent.parent / "data-sources" / "cunliffe.txt"
    
    if not cunliffe_path.exists():
        print(f"Error: Cunliffe text file not found at {cunliffe_path}")
        print("Please ensure cunliffe.txt is in the data-sources directory")
        raise FileNotFoundError(f"Required Cunliffe text file missing: {cunliffe_path}")
    
    dictionary_data = parse_cunliffe_file(cunliffe_path)
    verify_extraction(dictionary_data)
    save_results(dictionary_data)
    
    # Show sample entries
    print("\nSample entries:")
    for i, (headword, data) in enumerate(list(dictionary_data.items())[:5]):
        print(f"\n{headword}:")
        print(f"  Inflected forms ({len(data['inflected_forms'])}): {data['inflected_forms'][:3]}...")
        print(f"  Definition: {data['definition'][:100]}...")
    
    print("\nExtraction complete!")

if __name__ == "__main__":
    main()