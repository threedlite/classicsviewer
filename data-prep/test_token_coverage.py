#!/usr/bin/env python3
"""
Test lemmatization coverage on actual text tokens (not just unique words)
This gives a better sense of real-world coverage since common words appear more often
"""

import sqlite3
import re
import unicodedata
from pathlib import Path
from collections import Counter

def normalize_word(word):
    """Normalize a word for lemma lookup"""
    # Remove punctuation
    word = re.sub(r'[^\u0370-\u03FF\u1F00-\u1FFF]+', '', word)
    
    # Convert to lowercase
    word = word.lower()
    
    # Remove all diacritics
    word = unicodedata.normalize('NFD', word)
    word = ''.join(char for char in word if unicodedata.category(char) != 'Mn')
    word = unicodedata.normalize('NFC', word)
    
    return word

def test_token_coverage():
    """Test coverage on actual text tokens from major works"""
    
    db_path = Path("perseus_texts.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Testing token coverage on major works...")
    
    # Test on Homer's works
    works = [
        ('tlg0012.tlg001', 'Iliad'),
        ('tlg0012.tlg002', 'Odyssey')
    ]
    
    for work_id, work_name in works:
        print(f"\n=== {work_name} ===")
        
        # Get all text lines
        cursor.execute("""
            SELECT line_text 
            FROM text_lines 
            WHERE book_id LIKE ?
        """, (f"{work_id}%",))
        
        lines = cursor.fetchall()
        
        # Count tokens
        token_counts = Counter()
        total_tokens = 0
        
        for line_text, in lines:
            words = line_text.split()
            for word in words:
                normalized = normalize_word(word)
                if normalized:
                    token_counts[normalized] += 1
                    total_tokens += 1
        
        # Check coverage
        tokens_found = 0
        unique_found = 0
        
        for word, count in token_counts.items():
            cursor.execute("""
                SELECT COUNT(*) FROM lemma_map 
                WHERE word_form = ?
            """, (word,))
            
            if cursor.fetchone()[0] > 0:
                tokens_found += count
                unique_found += 1
        
        # Calculate coverage
        token_coverage = (tokens_found / total_tokens * 100) if total_tokens > 0 else 0
        unique_coverage = (unique_found / len(token_counts) * 100) if len(token_counts) > 0 else 0
        
        print(f"  Total tokens: {total_tokens:,}")
        print(f"  Unique words: {len(token_counts):,}")
        print(f"  Token coverage: {token_coverage:.1f}% (of all word occurrences)")
        print(f"  Unique word coverage: {unique_coverage:.1f}% (of distinct words)")
        
        # Show most common unmapped words
        print(f"\n  Most common unmapped words:")
        unmapped = []
        for word, count in token_counts.most_common():
            cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE word_form = ?", (word,))
            if cursor.fetchone()[0] == 0:
                unmapped.append((word, count))
            if len(unmapped) >= 20:
                break
        
        for word, count in unmapped:
            print(f"    {word}: {count} occurrences")
    
    conn.close()

if __name__ == "__main__":
    test_token_coverage()