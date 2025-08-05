#!/usr/bin/env python3
"""
Add Wiktionary definitions for specific Greek words that are missing from LSJ
but appear in our texts. This creates a supplemental dictionary.
"""

import sqlite3
import json

# Manually curated Wiktionary definitions for important missing words
# In production, these would be extracted from Wiktionary XML
WIKTIONARY_SUPPLEMENTS = [
    {
        'headword': 'σφωέ',
        'headword_normalized': 'σφωε',
        'language': 'greek',
        'entry_html': '''<div class="entry">
<b>σφωέ</b>, pronoun. Epic enclitic third person dual personal pronoun: 
they two, both of them, these two. 
<i>Example: τίς τ' ἄρ σφωε θεῶν ἔριδι ξυνέηκε μάχεσθαι; (Il. 1.8)</i>
<br/><span style="font-size: 0.9em; color: #666;">[From Wiktionary]</span>
</div>''',
        'entry_plain': 'σφωέ, pronoun. Epic enclitic third person dual personal pronoun: they two, both of them, these two.',
        'source': 'wiktionary'
    },
    {
        'headword': 'Ἀτρεύς',
        'headword_normalized': 'ατρευσ',
        'language': 'greek',
        'entry_html': '''<div class="entry">
<b>Ἀτρεύς</b>, -έως, ὁ, proper name. Atreus, king of Mycenae, 
father of Agamemnon and Menelaus. Hence Ἀτρεΐδης = son of Atreus.
<br/><span style="font-size: 0.9em; color: #666;">[From Wiktionary]</span>
</div>''',
        'entry_plain': 'Ἀτρεύς, -έως, ὁ, proper name. Atreus, king of Mycenae, father of Agamemnon and Menelaus.',
        'source': 'wiktionary'
    },
    {
        'headword': 'πρῶτα',
        'headword_normalized': 'πρωτα',
        'language': 'greek',
        'entry_html': '''<div class="entry">
<b>πρῶτα</b>, neuter plural of πρῶτος used adverbially: 
first, at first, firstly, in the first place.
<br/><span style="font-size: 0.9em; color: #666;">[From Wiktionary]</span>
</div>''',
        'entry_plain': 'πρῶτα, neuter plural of πρῶτος used adverbially: first, at first, firstly.',
        'source': 'wiktionary'
    },
    {
        'headword': 'νοῦσος',  
        'headword_normalized': 'νουσοσ',
        'language': 'greek',
        'entry_html': '''<div class="entry">
<b>νοῦσος</b>, ἡ, (Ionic and poetic for νόσος) disease, sickness, plague.
<i>Common in Homer: νοῦσον ἀνὰ στρατὸν ὄρσε κακήν (Il. 1.10)</i>
<br/><span style="font-size: 0.9em; color: #666;">[From Wiktionary]</span>
</div>''',
        'entry_plain': 'νοῦσος, ἡ, (Ionic for νόσος) disease, sickness, plague.',
        'source': 'wiktionary'
    },
    {
        'headword': 'ἑλώριον',
        'headword_normalized': 'ελωριον',  
        'language': 'greek',
        'entry_html': '''<div class="entry">
<b>ἑλώριον</b>, τό, (also ἑλώρια, τά) prey, spoil, booty; 
especially of bodies given as prey to dogs and birds.
<i>αὐτοὺς δὲ ἑλώρια τεῦχε κύνεσσιν (Il. 1.4)</i>
<br/><span style="font-size: 0.9em; color: #666;">[From Wiktionary]</span>
</div>''',
        'entry_plain': 'ἑλώριον, τό, prey, spoil, booty; especially of bodies given as prey.',
        'source': 'wiktionary'
    }
]

def add_to_database(db_path='perseus_texts.db'):
    """Add Wiktionary supplements to dictionary_entries table"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check how many we're adding
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE source = 'wiktionary'")
    before_count = cursor.fetchone()[0]
    
    added = 0
    for entry in WIKTIONARY_SUPPLEMENTS:
        # Check if already exists
        cursor.execute("""
            SELECT COUNT(*) FROM dictionary_entries 
            WHERE headword_normalized = ? AND language = ?
        """, (entry['headword_normalized'], entry['language']))
        
        if cursor.fetchone()[0] == 0:
            # Add the entry
            cursor.execute("""
                INSERT INTO dictionary_entries 
                (headword, headword_normalized, language, entry_xml, entry_html, entry_plain, source)
                VALUES (?, ?, ?, NULL, ?, ?, ?)
            """, (
                entry['headword'],
                entry['headword_normalized'],
                entry['language'],
                entry['entry_html'],
                entry['entry_plain'],
                entry['source']
            ))
            added += 1
            print(f"Added: {entry['headword']}")
        else:
            print(f"Skipped (already exists): {entry['headword']}")
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE source = 'wiktionary'")
    after_count = cursor.fetchone()[0]
    
    print(f"\nSummary:")
    print(f"  Before: {before_count} Wiktionary entries")
    print(f"  Added: {added} new entries")
    print(f"  After: {after_count} Wiktionary entries")
    
    # Also update lemma_map for words that are their own lemma
    print("\nUpdating lemma_map for self-lemmas...")
    for entry in WIKTIONARY_SUPPLEMENTS:
        headword_norm = entry['headword_normalized']
        cursor.execute("""
            INSERT OR IGNORE INTO lemma_map 
            (word_form, word_normalized, lemma, confidence, source)
            VALUES (?, ?, ?, 1.0, 'wiktionary:lemma')
        """, (headword_norm, headword_norm, headword_norm))
    
    conn.commit()
    conn.close()

def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        add_to_database()
    else:
        print("This will add Wiktionary definitions for the following words:")
        for entry in WIKTIONARY_SUPPLEMENTS:
            print(f"  - {entry['headword']} ({entry['headword_normalized']})")
        print(f"\nTotal: {len(WIKTIONARY_SUPPLEMENTS)} entries")
        print("\nRun with --execute to add to database")

if __name__ == '__main__':
    main()