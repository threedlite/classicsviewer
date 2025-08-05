#!/usr/bin/env python3
"""
Test lemmatization coverage on Odyssey Book 1, lines 1-100
"""

import sqlite3
from pathlib import Path
import re

def normalize_word(word):
    """Normalize a word for lemma lookup"""
    import unicodedata
    
    # Remove punctuation
    word = re.sub(r'[^\u0370-\u03FF\u1F00-\u1FFF]+', '', word)
    
    # Convert to lowercase
    word = word.lower()
    
    # Remove all diacritics
    # NFD decomposition separates base characters from diacritics
    word = unicodedata.normalize('NFD', word)
    # Remove combining diacritical marks
    word = ''.join(char for char in word if unicodedata.category(char) != 'Mn')
    # NFC recomposition
    word = unicodedata.normalize('NFC', word)
    
    return word

def test_coverage():
    """Test lemmatization coverage on Odyssey sample"""
    db_path = Path(__file__).parent / "perseus_texts.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get Odyssey Book 1, lines 1-100
    cursor.execute("""
        SELECT line_number, line_text 
        FROM text_lines 
        WHERE book_id = 'tlg0012.tlg002.001' 
        AND line_number <= 100
        ORDER BY line_number
    """)
    
    lines = cursor.fetchall()
    
    # Analyze each line
    total_words = 0
    found_lemmas = 0
    not_found = []
    
    print("Testing lemmatization coverage on Odyssey Book 1, lines 1-100...\n")
    
    for line_num, line_text in lines:
        words = line_text.split()
        
        for word in words:
            normalized = normalize_word(word)
            if not normalized:  # Skip empty after normalization
                continue
                
            total_words += 1
            
            # Check if we can find a lemma for this word
            cursor.execute("""
                SELECT lemma, source 
                FROM lemma_map 
                WHERE word_form = ?
            """, (normalized,))
            
            result = cursor.fetchone()
            if result:
                found_lemmas += 1
            else:
                not_found.append((line_num, word, normalized))
    
    # Calculate coverage
    coverage = (found_lemmas / total_words * 100) if total_words > 0 else 0
    
    print(f"Total words analyzed: {total_words}")
    print(f"Words with lemmas found: {found_lemmas}")
    print(f"Words without lemmas: {total_words - found_lemmas}")
    print(f"Coverage: {coverage:.1f}%\n")
    
    # Show some examples of words not found
    if not_found:
        print("Sample of words without lemmas (first 20):")
        for i, (line_num, orig, norm) in enumerate(not_found[:20]):
            print(f"  Line {line_num}: '{orig}' (normalized: '{norm}')")
    
    # Check source distribution
    print("\nChecking lemma source distribution...")
    cursor.execute("""
        SELECT source, COUNT(DISTINCT word_form) as unique_forms, COUNT(*) as total_mappings
        FROM lemma_map
        GROUP BY source
        ORDER BY unique_forms DESC
        LIMIT 10
    """)
    
    print("\nTop lemma sources in database:")
    for source, unique_forms, total in cursor.fetchall():
        print(f"  {source}: {unique_forms:,} unique forms, {total:,} total mappings")
    
    conn.close()
    
    return coverage

if __name__ == "__main__":
    coverage = test_coverage()