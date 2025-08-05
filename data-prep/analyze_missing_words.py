#!/usr/bin/env python3
"""
Analyze corpus-wide coverage and identify patterns in missing words
"""

import sqlite3
import json
from collections import Counter, defaultdict
import unicodedata

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text

def analyze_coverage():
    conn = sqlite3.connect('perseus_texts.db')
    cursor = conn.cursor()
    
    print("=== CORPUS-WIDE COVERAGE ANALYSIS ===\n")
    
    # Get all unique Greek words
    cursor.execute("""
        SELECT DISTINCT word_normalized
        FROM word_forms wf
        JOIN books b ON wf.book_id = b.id
        JOIN works w ON b.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        WHERE a.language = 'greek'
    """)
    
    unique_words = [row[0] for row in cursor.fetchall()]
    total_unique = len(unique_words)
    print(f"Total unique Greek word forms: {total_unique:,}")
    
    # Check which words have dictionary entries or lemma mappings
    found_words = set()
    not_found_words = []
    
    for word in unique_words:
        # Check dictionary
        cursor.execute("""
            SELECT 1 FROM dictionary_entries 
            WHERE headword_normalized = ? AND language = 'greek'
            LIMIT 1
        """, (word,))
        
        if cursor.fetchone():
            found_words.add(word)
        else:
            # Check lemma_map
            cursor.execute("""
                SELECT lemma FROM lemma_map 
                WHERE word_normalized = ?
                LIMIT 1
            """, (word,))
            
            lemma_result = cursor.fetchone()
            if lemma_result:
                lemma = lemma_result[0]
                # Check if lemma is in dictionary
                cursor.execute("""
                    SELECT 1 FROM dictionary_entries 
                    WHERE headword_normalized = ? AND language = 'greek'
                    LIMIT 1
                """, (lemma,))
                
                if cursor.fetchone():
                    found_words.add(word)
                else:
                    not_found_words.append(word)
            else:
                not_found_words.append(word)
    
    found_count = len(found_words)
    not_found_count = len(not_found_words)
    
    print(f"Found in dictionary/lemma map: {found_count:,} ({found_count/total_unique*100:.1f}%)")
    print(f"Not found: {not_found_count:,} ({not_found_count/total_unique*100:.1f}%)")
    
    # Analyze patterns in missing words
    print("\n=== ANALYSIS OF MISSING WORDS ===\n")
    
    # Length distribution
    length_dist = Counter(len(word) for word in not_found_words)
    print("Length distribution of missing words:")
    for length in sorted(length_dist.keys()):
        count = length_dist[length]
        print(f"  {length} chars: {count:,} words")
    
    # Common endings
    ending_counts = Counter()
    for word in not_found_words:
        if len(word) >= 3:
            ending_counts[word[-3:]] += 1
        if len(word) >= 2:
            ending_counts[word[-2:]] += 1
    
    print("\nMost common endings in missing words:")
    for ending, count in ending_counts.most_common(20):
        print(f"  -{ending}: {count:,} words")
    
    # Sample missing words by frequency
    print("\n=== SAMPLE OF MISSING WORDS (by corpus frequency) ===\n")
    
    # Get frequency of missing words
    missing_with_freq = []
    for word in not_found_words[:1000]:  # Sample first 1000
        cursor.execute("""
            SELECT COUNT(*) FROM word_forms 
            WHERE word_normalized = ?
        """, (word,))
        freq = cursor.fetchone()[0]
        missing_with_freq.append((word, freq))
    
    # Sort by frequency
    missing_with_freq.sort(key=lambda x: x[1], reverse=True)
    
    print("Top 50 most frequent missing words:")
    for i, (word, freq) in enumerate(missing_with_freq[:50]):
        print(f"{i+1:3}. {word:20} (occurs {freq:,} times)")
    
    # Check if these are proper nouns
    print("\n=== PROPER NOUN ANALYSIS ===\n")
    
    # Words starting with what would be capital in Greek
    likely_proper = [w for w in not_found_words if len(w) > 0 and w[0] in 'αβγδεζηθικλμνξοπρστυφχψω']
    
    # Get a sample with context
    print("Sample of missing words with context:")
    sample_missing = not_found_words[:20]
    
    for word in sample_missing:
        cursor.execute("""
            SELECT tl.line_text, b.id, w.title
            FROM word_forms wf
            JOIN text_lines tl ON wf.book_id = tl.book_id AND wf.line_number = tl.line_number
            JOIN books b ON wf.book_id = b.id
            JOIN works w ON b.work_id = w.id
            WHERE wf.word_normalized = ?
            LIMIT 1
        """, (word,))
        
        result = cursor.fetchone()
        if result:
            line_text, book_id, work_title = result
            print(f"\n{word}:")
            print(f"  Work: {work_title}")
            print(f"  Line: {line_text}")
    
    # Save missing words to file
    print(f"\nSaving missing words to 'missing_words_analysis.json'...")
    
    analysis_data = {
        'total_unique_words': total_unique,
        'found_count': found_count,
        'not_found_count': not_found_count,
        'coverage_percentage': found_count/total_unique*100,
        'missing_words_sample': not_found_words[:1000],
        'high_frequency_missing': [{'word': w, 'frequency': f} for w, f in missing_with_freq[:100]]
    }
    
    with open('missing_words_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    
    conn.close()

if __name__ == '__main__':
    analyze_coverage()