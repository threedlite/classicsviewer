#!/usr/bin/env python3
"""
Test lemmatization coverage on the entire corpus
"""

import sqlite3
import json
from pathlib import Path
import time

def test_corpus_coverage():
    """Test lemmatization coverage on all unique words in the corpus"""
    
    # Load corpus words
    corpus_file = Path("wiktionary-processing/all_greek_words_in_corpus.json")
    print(f"Loading corpus words from {corpus_file}...")
    
    with open(corpus_file) as f:
        corpus_words = json.load(f)
    
    print(f"Total unique words in corpus: {len(corpus_words):,}")
    
    # Connect to database
    db_path = Path("perseus_texts.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test coverage
    print("\nTesting coverage...")
    start_time = time.time()
    
    found = 0
    not_found = []
    
    # Check each word
    for i, word in enumerate(corpus_words):
        cursor.execute("""
            SELECT COUNT(*) FROM lemma_map 
            WHERE word_form = ?
        """, (word,))
        
        if cursor.fetchone()[0] > 0:
            found += 1
        else:
            not_found.append(word)
        
        # Progress update
        if (i + 1) % 10000 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (len(corpus_words) - i - 1) / rate
            print(f"  Processed {i+1:,} words... {found/(i+1)*100:.1f}% coverage (ETA: {remaining:.0f}s)")
    
    # Calculate final coverage
    coverage = (found / len(corpus_words) * 100) if len(corpus_words) > 0 else 0
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total unique words in corpus: {len(corpus_words):,}")
    print(f"Words with lemmas found: {found:,}")
    print(f"Words without lemmas: {len(not_found):,}")
    print(f"COVERAGE: {coverage:.1f}%")
    
    # Show sample of missing words
    print(f"\nSample of unmapped words (first 50):")
    for word in not_found[:50]:
        print(f"  {word}")
    
    # Get source distribution
    print("\nLemma sources distribution:")
    cursor.execute("""
        SELECT source, COUNT(DISTINCT word_form) as unique_forms
        FROM lemma_map
        GROUP BY source
        ORDER BY unique_forms DESC
        LIMIT 15
    """)
    
    for source, count in cursor.fetchall():
        print(f"  {source}: {count:,} unique forms")
    
    # Total unique mapped words
    cursor.execute("SELECT COUNT(DISTINCT word_form) FROM lemma_map")
    total_mapped = cursor.fetchone()[0]
    print(f"\nTotal unique words mapped: {total_mapped:,}")
    
    conn.close()
    
    return coverage

if __name__ == "__main__":
    coverage = test_corpus_coverage()