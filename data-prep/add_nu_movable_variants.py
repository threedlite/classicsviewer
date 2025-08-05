#!/usr/bin/env python3
"""
Add nu-movable variants to lemma_map.
Many Greek verb forms can optionally end in -ν (nu-movable), especially:
- 3rd person singular forms ending in -ε can become -εν
- 3rd person plural forms
"""

import sqlite3
from pathlib import Path

def main():
    db_path = Path("perseus_texts.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find verb forms that could have nu-movable variants
    cursor.execute("""
        SELECT DISTINCT word_form, lemma, morph_info, source
        FROM lemma_map
        WHERE source IN ('algorithmic', 'enwiktionary:ancient-greek', 'wiktionary:inflection_of')
        AND (morph_info LIKE '%3%s%' OR morph_info LIKE '%3%p%' OR morph_info LIKE 'third%')
    """)
    
    verb_forms = cursor.fetchall()
    print(f"Found {len(verb_forms)} verb forms to check for nu-movable variants")
    
    added = 0
    
    for word_form, lemma, morph_info, source in verb_forms:
        # Check if form ends in ε (without ν)
        if word_form.endswith('ε') and not word_form.endswith('εν'):
            # Create variant with ν
            variant = word_form + 'ν'
            
            # Check if variant already exists
            cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE word_form = ?", (variant,))
            if cursor.fetchone()[0] == 0:
                # Add the variant
                cursor.execute("""
                    INSERT INTO lemma_map (word_form, word_normalized, lemma, confidence, source, morph_info)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (variant, variant, lemma, 0.9, 'generated:nu-movable', morph_info))
                added += 1
        
        # Also check reverse: if form ends in εν, add variant without ν
        elif word_form.endswith('εν'):
            variant = word_form[:-1]  # Remove the ν
            
            cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE word_form = ?", (variant,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO lemma_map (word_form, word_normalized, lemma, confidence, source, morph_info)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (variant, variant, lemma, 0.9, 'generated:nu-movable', morph_info))
                added += 1
    
    # Also add common 3rd person forms
    # Many imperfect and aorist forms can have nu-movable
    cursor.execute("""
        SELECT DISTINCT word_form, lemma, morph_info, source
        FROM lemma_map
        WHERE word_form LIKE '%ε'
        AND length(word_form) > 3
        AND source IN ('algorithmic', 'enwiktionary:ancient-greek')
    """)
    
    epsilon_forms = cursor.fetchall()
    
    for word_form, lemma, morph_info, source in epsilon_forms:
        variant = word_form + 'ν'
        
        cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE word_form = ?", (variant,))
        if cursor.fetchone()[0] == 0:
            # Infer it's likely a 3rd person form
            new_morph = morph_info if morph_info else "3 s (nu-movable)"
            cursor.execute("""
                INSERT INTO lemma_map (word_form, word_normalized, lemma, confidence, source, morph_info)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (variant, variant, lemma, 0.8, 'generated:nu-movable', new_morph))
            added += 1
    
    conn.commit()
    
    print(f"\nAdded {added} nu-movable variants")
    
    # Test specific words
    print("\nChecking specific forms:")
    test_words = ['επερσεν', 'ελεγεν', 'ειπεν']
    for word in test_words:
        cursor.execute("SELECT lemma, morph_info FROM lemma_map WHERE word_form = ?", (word,))
        result = cursor.fetchone()
        if result:
            print(f"  {word} → {result[0]} ({result[1]})")
        else:
            print(f"  {word} → NOT FOUND")
    
    conn.close()

if __name__ == "__main__":
    main()