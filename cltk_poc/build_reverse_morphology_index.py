#!/usr/bin/env python3
"""
Build a reverse morphology index from Perseus data.
Maps: normalized_word_form → [(lemma, frequency), ...]

This is the CORRECT solution - use Perseus's actual morphology data
instead of relying on CLTK's incorrect fragment lemmatization.
"""
import sys
sys.path.insert(0, '.')
from generate_cltk_dictionary import normalize_greek
import sqlite3
import json
from collections import defaultdict

print("Building reverse morphology index from Perseus...")
print("="*70)

conn = sqlite3.connect('../data-prep/perseus_texts_extended.db')
cursor = conn.cursor()

# Get all word_form → lemma mappings with frequencies
print("Querying Perseus morphology data...")
cursor.execute("""
    SELECT word_form, lemma, COUNT(*) as freq
    FROM lemma_map
    WHERE lemma IS NOT NULL AND word_form IS NOT NULL
    GROUP BY word_form, lemma
    ORDER BY freq DESC
""")

# Build reverse index
reverse_index = defaultdict(list)
total_mappings = 0

print("Building reverse index...")
for row in cursor.fetchall():
    word_form, lemma, freq = row
    
    # Normalize the word form (remove diacritics)
    norm_form = normalize_greek(word_form.lower())
    
    # Skip very short forms (< 3 chars)
    if len(norm_form) < 3:
        continue
    
    reverse_index[norm_form].append((lemma, freq))
    total_mappings += 1
    
    if total_mappings % 100000 == 0:
        print(f"  Processed {total_mappings:,} mappings...")

conn.close()

# Sort each list by frequency
for norm_form in reverse_index:
    reverse_index[norm_form] = sorted(
        reverse_index[norm_form], 
        key=lambda x: x[1], 
        reverse=True
    )

print(f"\n✓ Built reverse index with {len(reverse_index):,} unique forms")
print(f"✓ Total mappings: {total_mappings:,}")

# Save to JSON
output = dict(reverse_index)
with open('perseus_reverse_morphology.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✓ Saved to perseus_reverse_morphology.json")

# Test on our problem fragments
print("\n" + "="*70)
print("TESTING ON PROBLEM FRAGMENTS")
print("="*70)

test_fragments = [
    ('ιππος', 'ἵππος', 'horse'),
    ('ανδρος', 'ἀνήρ', 'man'),
    ('δωρος', 'δῶρον', 'gift'),
    ('βους', 'βοῦς', 'ox'),
]

for fragment, expected, meaning in test_fragments:
    norm = normalize_greek(fragment)
    print(f"\n'{fragment}' → expecting '{expected}' ({meaning})")
    
    if norm in reverse_index:
        results = reverse_index[norm][:10]
        print(f"  Found {len(reverse_index[norm])} possible lemmas")
        print(f"  Top 10:")
        
        expected_norm = normalize_greek(expected.lower())
        found_expected = False
        
        for i, (lemma, freq) in enumerate(results, 1):
            marker = ""
            if normalize_greek(lemma.lower()) == expected_norm:
                marker = " ✓✓✓ EXPECTED!"
                found_expected = True
            print(f"    {i}. {lemma} ({freq} occurrences){marker}")
        
        if found_expected:
            print(f"  ✅ SUCCESS!")
        else:
            print(f"  ❌ Expected lemma not in top 10")
    else:
        print(f"  ❌ Fragment not found in reverse index")

print("\n" + "="*70)
