#!/usr/bin/env python3
"""
Load Whitaker's Words Latin dictionary and morphology into the Perseus database.
This integrates Latin definitions and inflections directly into the main dictionary.
"""

import os
import re
from functools import cmp_to_key
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class LatinInflectionEngine:
    """Latin inflection engine based on Whitaker's Words INFLECTS.LAT"""
    
    def __init__(self):
        self.inflection_patterns = []
    
    def parse_inflects(self, file_path: str):
        """Parse INFLECTS.LAT for inflection patterns"""
        if not os.path.exists(file_path):
            print(f"Warning: INFLECTS.LAT not found at {file_path}")
            return
        
        print("Loading Latin inflection patterns...")
        pattern_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                if not line or line.startswith('--'):
                    continue
                
                parts = line.split()
                
                if parts[0] == 'V' and len(parts) >= 11:
                    # Parse verb inflections
                    pattern = {
                        'pos': 'V',
                        'conjugation': int(parts[1]),
                        'variant': int(parts[2]),
                        'tense': parts[3],
                        'voice': parts[4],
                        'mood': parts[5],
                        'person': parts[6],
                        'number': parts[7],
                        'stem_pos': int(parts[8]),
                        'ending_len': int(parts[9]),
                        'ending': parts[10] if len(parts) > 10 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'VPAR' and len(parts) >= 11:
                    # Parse verb participle inflections
                    pattern = {
                        'pos': 'VPAR',
                        'conjugation': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'tense': parts[6],
                        'voice': parts[7],
                        'mood': parts[8],
                        'stem_pos': int(parts[9]),
                        'ending_len': int(parts[10]),
                        'ending': parts[11] if len(parts) > 11 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'N' and len(parts) >= 9:
                    # Parse noun inflections
                    pattern = {
                        'pos': parts[0],
                        'declension': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'stem_pos': int(parts[6]),
                        'ending_len': int(parts[7]),
                        'ending': parts[8] if len(parts) > 8 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'ADJ' and len(parts) >= 10:
                    # Parse adjective inflections
                    pattern = {
                        'pos': parts[0],
                        'declension': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'degree': parts[6],  # POS/COMP/SUPER
                        'stem_pos': int(parts[7]),
                        'ending_len': int(parts[8]),
                        'ending': parts[9] if len(parts) > 9 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'PRON' and len(parts) >= 8:
                    # Parse pronoun inflections
                    # Format: PRON decl variant case number gender stem_pos ending_len [ending] age freq
                    # Note: if ending_len is 0, there's no ending token - parts[8] is age instead
                    ending_len = int(parts[7])
                    if ending_len > 0 and len(parts) > 8:
                        ending = parts[8]
                    else:
                        ending = ''
                    pattern = {
                        'pos': 'PRON',
                        'declension': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'stem_pos': int(parts[6]),
                        'ending_len': ending_len,
                        'ending': ending
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1

        print(f"Loaded {pattern_count} inflection patterns")
    
    def generate_morphology_for_dictionary(self, dictionary_line: str) -> List[Dict]:
        """Generate morphology entries from a DICTLINE.GEN entry"""
        if len(dictionary_line) < 100:
            return []

        stems_part = dictionary_line[0:76].strip()
        pos_part = dictionary_line[76:88].strip() if len(dictionary_line) > 76 else None

        if not pos_part:
            return []

        # Extract frequency code from flags section (position 83-110)
        # Format: "2 1 M P          X X X A O" - frequency is second from end
        # Whitaker's codes: A=very frequent, B=frequent, C=common, D=lesser, E=uncommon, F=very rare, X=unknown
        # Map to confidence: higher frequency = higher confidence for better sorting
        freq_confidence_map = {'A': 0.95, 'B': 0.90, 'C': 0.85, 'D': 0.80, 'E': 0.75, 'F': 0.70, 'X': 0.65}
        flags_part = dictionary_line[83:110] if len(dictionary_line) > 110 else ""
        flags_tokens = flags_part.split()
        freq_code = flags_tokens[-2] if len(flags_tokens) >= 2 else 'X'
        confidence = freq_confidence_map.get(freq_code, 0.65)

        morphology_entries = []
        pos_info = pos_part.split()
        
        if pos_info[0] == 'V':
            # Verb: V conj variant
            conjugation = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            
            # Extract stems
            stems = [s for s in stems_part.split() if s]
            if len(stems) >= 1:
                # Generate verb forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'V':
                        continue
                    if pattern['conjugation'] != conjugation and pattern['conjugation'] != 0:
                        continue
                    
                    # Apply the ending to the appropriate stem
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern['stem_pos'] - 1 < len(stems) else None
                    
                    if not stem_to_use:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string
                    morph_info = []
                    if pattern['person'] != 'X':
                        morph_info.append(pattern['person'])
                    if pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern['tense']:
                        morph_info.append(pattern['tense'].lower())
                    if pattern['voice']:
                        morph_info.append(pattern['voice'].lower())
                    if pattern['mood']:
                        morph_info.append(pattern['mood'].lower())
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': stems[0],
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })
                
                # Also generate participle forms (VPAR) for verbs
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'VPAR':
                        continue
                    if pattern['conjugation'] != conjugation and pattern['conjugation'] != 0:
                        continue
                    
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern['stem_pos'] - 1 < len(stems) else None
                    
                    if not stem_to_use:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string for participles
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    if pattern.get('tense'):
                        morph_info.append(pattern['tense'].lower())
                    if pattern.get('voice'):
                        morph_info.append(pattern['voice'].lower())
                    morph_info.append("part")  # Mark as participle
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': stems[0],
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })
        
        elif pos_info[0] == 'N':
            # Noun: N decl variant gender
            declension = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            
            stems = [s for s in stems_part.split() if s]
            if len(stems) >= 1:
                # Generate noun forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'N':
                        continue
                    if pattern['declension'] != declension and pattern['declension'] != 0:
                        continue
                    
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern.get('stem_pos') and pattern['stem_pos'] - 1 < len(stems) else stems[0]
                    
                    if not stem_to_use:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': stems[0],
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })
        
        elif pos_info[0] == 'ADJ':
            # Adjective: ADJ decl variant
            declension = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            variant = int(pos_info[2]) if len(pos_info) > 2 and pos_info[2].isdigit() else 0
            
            stems = [s for s in stems_part.split() if s]
            if len(stems) >= 1:
                # For ADJ 1 1 (first/second declension), expand stems if needed
                if declension == 1 and variant == 1 and len(stems) == 1:
                    masc_stem = stems[0]
                    fem_stem = masc_stem
                    neut_stem = masc_stem
                    stems = [masc_stem, fem_stem, neut_stem, masc_stem]
                
                # Generate adjective forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'ADJ':
                        continue
                    if pattern['declension'] != declension and pattern['declension'] != 0:
                        continue
                    
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern['stem_pos'] - 1 < len(stems) and pattern.get('stem_pos') else stems[0]
                    
                    if not stem_to_use:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': stems[0],
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })

        elif pos_info[0] == 'PRON':
            # Pronoun: PRON decl variant type
            # Examples from DICTLINE.GEN:
            # - ill ill PRON 6 1 ADJECT (ille - that)
            # - h hu PRON 3 1 ADJECT (hic - this)
            # - i e PRON 4 1 PERS (is - he/she/it)
            # - ego m PRON 5 1 PERS (ego - I)
            # - tu t PRON 5 2 PERS (tu - you)
            # - qu cu PRON 1 0 REL (qui - who)
            declension = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            variant = int(pos_info[2]) if len(pos_info) > 2 and pos_info[2].isdigit() else 0

            stems = [s for s in stems_part.split() if s and s != 'zzz']

            if len(stems) >= 1:
                # Generate pronoun forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'PRON':
                        continue

                    # Match declension (0 in pattern means any)
                    if pattern['declension'] != declension and pattern['declension'] != 0:
                        continue

                    # Match variant:
                    # - Pattern variant 0 matches any dictionary entry variant
                    # - Dictionary entry variant 0 matches any pattern variant
                    # - Otherwise, variants must match exactly
                    if pattern['variant'] != 0 and variant != 0 and pattern['variant'] != variant:
                        continue

                    # Get the appropriate stem
                    stem_idx = pattern['stem_pos'] - 1
                    if stem_idx < 0 or stem_idx >= len(stems):
                        stem_to_use = stems[0] if stems else None
                    else:
                        stem_to_use = stems[stem_idx]

                    if not stem_to_use:
                        continue

                    # Apply ending to stem
                    form = stem_to_use + pattern['ending']

                    # Create morphology info string
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    morph_info.append('pron')  # Mark as pronoun

                    morphology_entries.append({
                        'word_form': form,
                        'lemma': stems[0],
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })

        return morphology_entries


def load_whitakers_latin(cursor, include_full_morphology=True):
    """Load Whitaker's Words Latin dictionary and morphology into the database
    
    Args:
        cursor: Database cursor
        include_full_morphology: If True, include concatenated morph_info strings (for full DB).
                                If False, just store word-to-lemma mappings (for sample DB).
    """
    
    print("\n=== LOADING WHITAKER'S LATIN DICTIONARY ===")
    
    # Find the Whitaker's Words directory in data-sources
    base_dir = Path(__file__).parent.parent.parent / "data-sources" / "whitakers-words"
    if not base_dir.exists():
        print(f"Warning: Whitaker's Words directory not found at {base_dir}")
        return
    
    dictline_path = base_dir / "DICTLINE.GEN"
    inflects_path = base_dir / "INFLECTS.LAT"
    uniques_path = base_dir / "UNIQUES.LAT"
    
    if not dictline_path.exists():
        print(f"Warning: DICTLINE.GEN not found at {dictline_path}")
        return
    
    # Initialize inflection engine
    inflection_engine = LatinInflectionEngine()
    if inflects_path.exists():
        inflection_engine.parse_inflects(str(inflects_path))
    
    # Process DICTLINE.GEN
    print("\nParsing Whitaker's DICTLINE.GEN...")
    definitions_count = 0
    morphology_entries = []
    dictionary_entries = []

    # Whitaker's frequency codes: A=very frequent, B=frequent, C=common, D=lesser, E=uncommon, F=very rare, X=unknown
    # Lower number = more frequent (for sorting)
    freq_priority = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'X': 7}

    with open(dictline_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            if len(line) > 90:
                lemma_part = line[0:76].strip()
                lemma = lemma_part.split()[0] if lemma_part else None

                # Extract part of speech (position 76-82 in Whitaker's format)
                pos_part = line[76:83].strip() if len(line) > 82 else None
                pos = pos_part.split()[0] if pos_part else None

                # Extract frequency code and noun type from flags section (position 83-110)
                # Format: "2 1 M P          X X X A O" - tokens are:
                # [0-1]=decl, [2]=gender, [3]=type, [4-6]=Age/Area/Geo, [7]=Frequency, [8]=Source
                # For nouns: [2]=gender (M/F/N/C), [3]=type (P=personal, T=thing, etc.)
                flags_part = line[83:110] if len(line) > 110 else ""
                flags_tokens = flags_part.split()
                freq_code = 'X'  # default to unknown
                # noun_priority: secondary sort for entries with same headword and frequency
                # Only affects noun-to-noun comparisons: 0 = personal nouns, 1 = thing nouns and all non-nouns
                noun_priority = 1  # default: same as thing nouns (no preference vs nouns)

                if len(flags_tokens) >= 2:
                    # Frequency is always second-to-last, source is last
                    freq_code = flags_tokens[-2]  # second from end is frequency
                    # For nouns, check if it's a personal noun (M P, F P, C P)
                    # Personal nouns refer to people and should be preferred over "thing" variants
                    if pos == 'N' and len(flags_tokens) >= 4:
                        noun_type = flags_tokens[3]  # P=personal, T=thing, L=locale, etc.
                        noun_priority = 0 if noun_type == 'P' else 1

                freq_sort = freq_priority.get(freq_code, 7)

                # Get definition from position 110
                definition_part = line[110:] if len(line) > 110 else None
                if definition_part and lemma:
                    definition = definition_part.strip()
                    # Clean up the definition
                    definition = re.sub(r'\s+', ' ', definition)
                    definition = definition.replace('|', '; ')
                    definition = definition.replace('=>', ':')

                    if not definition or re.match(r'^[;:\s]+$', definition):
                        continue

                    # Add part of speech label if available
                    if pos:
                        pos_label = {
                            'N': '(n.) ',
                            'V': '(v.) ',
                            'ADJ': '(adj.) ',
                            'ADV': '(adv.) ',
                            'PREP': '(prep.) ',
                            'CONJ': '(conj.) ',
                            'PRON': '(pron.) ',
                            'INTERJ': '(interj.) ',
                            'NUM': '(num.) '
                        }.get(pos, '')
                        definition = pos_label + definition

                    # Limit definition length
                    if len(definition) > 400:
                        definition = definition[:400] + "..."

                    if lemma and len(lemma) > 0 and not re.match(r'^[0-9]+$', lemma):
                        # Add dictionary entry with frequency and noun_priority for sorting
                        dictionary_entries.append({
                            'headword': lemma,
                            'language': 'latin',
                            'definition': definition,
                            'source': 'Whitaker',
                            'freq_sort': freq_sort,  # for sorting only, not stored in DB
                            'noun_priority': noun_priority,  # 0=personal noun, 1=thing noun
                            'is_noun': (pos == 'N')  # for custom sort comparator
                        })
                        definitions_count += 1

                        # Generate morphology entries for this dictionary entry
                        morph_entries = inflection_engine.generate_morphology_for_dictionary(line)
                        morphology_entries.extend(morph_entries)

    # Custom comparator: freq is primary, noun_priority only used when comparing two nouns
    def compare_entries(a, b):
        # First compare by headword
        if a['headword'] < b['headword']:
            return -1
        if a['headword'] > b['headword']:
            return 1
        # Then by frequency
        if a['freq_sort'] < b['freq_sort']:
            return -1
        if a['freq_sort'] > b['freq_sort']:
            return 1
        # Only use noun_priority if BOTH are nouns
        if a.get('is_noun') and b.get('is_noun'):
            if a['noun_priority'] < b['noun_priority']:
                return -1
            if a['noun_priority'] > b['noun_priority']:
                return 1
        return 0

    # Initial sort (will be re-done after UNIQUES.LAT entries are added)
    dictionary_entries.sort(key=cmp_to_key(compare_entries))

    print(f"Extracted {definitions_count} Latin definitions from Whitaker's")
    print(f"Generated {len(morphology_entries)} morphology entries")
    
    # Process UNIQUES.LAT for special forms
    if uniques_path.exists():
        print("\nParsing UNIQUES.LAT...")
        uniques_count = 0
        
        with open(uniques_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('--'):
                i += 1
                continue
            
            if re.match(r'^[a-z]+$', line):
                word_form = line
                
                i += 1
                if i < len(lines) and re.match(r'^[A-Z]', lines[i].strip()):
                    i += 1
                    
                    if i < len(lines) and lines[i].strip():
                        definition = lines[i].strip()
                        
                        # Add as both dictionary entry and special form
                        dictionary_entries.append({
                            'headword': word_form,
                            'language': 'latin',
                            'definition': definition,
                            'source': 'Whitaker UNIQUES',
                            'freq_sort': 4,  # D = lesser frequency for special forms
                            'noun_priority': 1,  # same as thing nouns
                            'is_noun': False  # UNIQUES are typically not nouns
                        })
                        uniques_count += 1
            
            i += 1
        
        print(f"Extracted {uniques_count} special forms from UNIQUES.LAT")

    # Re-sort after adding UNIQUES entries using same custom comparator
    dictionary_entries.sort(key=cmp_to_key(compare_entries))

    # Remove sort keys before inserting (not DB columns)
    for entry in dictionary_entries:
        if 'freq_sort' in entry:
            del entry['freq_sort']
        if 'noun_priority' in entry:
            del entry['noun_priority']
        if 'is_noun' in entry:
            del entry['is_noun']

    # Insert dictionary entries into database
    print("\nInserting Whitaker's dictionary entries into database...")
    for entry in dictionary_entries:
        # Create HTML version of definition
        entry_html = f"<div class='definition'>{entry['definition']}</div>"
        
        cursor.execute("""
            INSERT INTO dictionary_entries 
            (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
            VALUES (?, NULL, ?, '', ?, ?, ?)
        """, (
            entry['headword'],
            entry['language'],
            entry_html,
            entry['definition'],
            entry['source']
        ))
    
    print(f"Inserted {len(dictionary_entries)} dictionary entries")
    
    # Insert morphology entries into lemma_map
    print("\nInserting Whitaker's morphology into lemma_map...")
    
    if include_full_morphology:
        # For full database: include concatenated morph_info strings
        print("  Including full morphological analysis (full database mode)")
        
        # First deduplicate exact entries
        seen = set()
        unique_morphology = []
        for m in morphology_entries:
            key = f"{m['word_form']}_{m['lemma']}_{m['morph_info']}_{m.get('confidence', 0.8)}_{m.get('source', 'Whitaker')}"
            if key not in seen:
                seen.add(key)
                unique_morphology.append(m)
        
        print(f"  After deduplication: {len(unique_morphology)} entries (from {len(morphology_entries)})")
        
        # Now coalesce entries that differ only in morph_info
        grouped = {}
        for entry in unique_morphology:
            key = (entry['word_form'], entry['lemma'], entry.get('confidence', 0.8), entry.get('source', 'Whitaker'))
            if key not in grouped:
                grouped[key] = []
            if entry.get('morph_info'):
                grouped[key].append(entry['morph_info'])
        
        # Insert coalesced entries
        for (word_form, lemma, confidence, source), morph_infos in grouped.items():
            # Combine multiple morph_infos with pipe separator
            if morph_infos:
                coalesced_morph = '|'.join(sorted(set(morph_infos)))
            else:
                coalesced_morph = ''
            
            cursor.execute("""
                INSERT INTO lemma_map 
                (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                VALUES (?, NULL, ?, ?, ?, ?)
            """, (
                word_form,
                lemma,
                confidence,
                source,
                coalesced_morph
            ))
        
        print(f"  Inserted {len(grouped)} morphology entries with full analysis")
    else:
        # For sample database: just word-to-lemma mappings, no morph_info
        print("  Storing word-to-lemma mappings only (sample database mode)")
        
        seen = set()
        for m in morphology_entries:
            key = (m['word_form'], m['lemma'])
            if key not in seen:
                seen.add(key)
                cursor.execute("""
                    INSERT INTO lemma_map 
                    (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                    VALUES (?, NULL, ?, ?, ?, NULL)
                """, (
                    m['word_form'],
                    m['lemma'],
                    m.get('confidence', 0.8),
                    'Whitaker'
                ))
        
        print(f"  Inserted {len(seen)} unique word-to-lemma mappings (from {len(morphology_entries)} total)")
    
    print("\n=== WHITAKER'S LATIN DICTIONARY LOADED SUCCESSFULLY ===")


if __name__ == "__main__":
    # Test the module standalone
    import sqlite3
    
    # Create test database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create necessary tables
    cursor.execute("""
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    """)
    
    # Load Whitaker's data
    load_whitakers_latin(cursor)
    
    # Check results
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE language = 'latin'")
    dict_count = cursor.fetchone()[0]
    print(f"\nTotal Latin dictionary entries: {dict_count}")
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE source = 'Whitaker'")
    morph_count = cursor.fetchone()[0]
    print(f"Total Latin morphology entries: {morph_count}")
    
    conn.close()