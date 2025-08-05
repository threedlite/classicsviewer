#!/usr/bin/env python3
"""
Efficiently analyze corpus-wide coverage and identify patterns in missing words
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
    
    # Get total unique Greek words with their frequencies
    print("Getting unique Greek words with frequencies...")
    cursor.execute("""
        SELECT word_normalized, COUNT(*) as freq
        FROM word_forms wf
        JOIN books b ON wf.book_id = b.id
        JOIN works w ON b.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        WHERE a.language = 'greek'
        GROUP BY word_normalized
        ORDER BY freq DESC
    """)
    
    word_frequencies = cursor.fetchall()
    total_unique = len(word_frequencies)
    total_tokens = sum(freq for _, freq in word_frequencies)
    
    print(f"Total unique Greek word forms: {total_unique:,}")
    print(f"Total Greek word tokens: {total_tokens:,}")
    
    # Create sets for fast lookup
    print("\nBuilding lookup sets...")
    
    # Get all dictionary headwords
    cursor.execute("""
        SELECT DISTINCT headword_normalized 
        FROM dictionary_entries 
        WHERE language = 'greek'
    """)
    dictionary_words = set(row[0] for row in cursor.fetchall())
    print(f"Dictionary entries: {len(dictionary_words):,}")
    
    # Get all lemma mappings
    cursor.execute("""
        SELECT DISTINCT word_normalized, lemma 
        FROM lemma_map
    """)
    lemma_mappings = {}
    for word, lemma in cursor.fetchall():
        if word not in lemma_mappings:
            lemma_mappings[word] = []
        lemma_mappings[word].append(lemma)
    print(f"Lemma mappings: {len(lemma_mappings):,}")
    
    # Analyze coverage
    print("\nAnalyzing coverage...")
    found_tokens = 0
    not_found_words = []
    not_found_tokens = 0
    
    for word, freq in word_frequencies[:10000]:  # Analyze top 10k for efficiency
        found = False
        
        # Check if word is directly in dictionary
        if word in dictionary_words:
            found = True
        elif word in lemma_mappings:
            # Check if any lemma is in dictionary
            for lemma in lemma_mappings[word]:
                if lemma in dictionary_words:
                    found = True
                    break
        
        if found:
            found_tokens += freq
        else:
            not_found_words.append((word, freq))
            not_found_tokens += freq
    
    # Calculate coverage
    unique_coverage = (total_unique - len(not_found_words)) / total_unique * 100
    token_coverage = found_tokens / sum(f for _, f in word_frequencies[:10000]) * 100
    
    print(f"\nCoverage (top 10k unique words):")
    print(f"  Unique word coverage: {unique_coverage:.1f}%")
    print(f"  Token coverage: {token_coverage:.1f}%")
    
    # Analyze patterns in missing words
    print("\n=== ANALYSIS OF MISSING WORDS ===\n")
    
    # Top missing words by frequency
    print("Top 50 most frequent missing words:")
    not_found_words.sort(key=lambda x: x[1], reverse=True)
    
    for i, (word, freq) in enumerate(not_found_words[:50]):
        # Get sample context
        cursor.execute("""
            SELECT tl.line_text
            FROM word_forms wf
            JOIN text_lines tl ON wf.book_id = tl.book_id AND wf.line_number = tl.line_number
            WHERE wf.word_normalized = ?
            LIMIT 1
        """, (word,))
        
        context = cursor.fetchone()
        context_text = context[0][:60] + "..." if context else "No context"
        print(f"{i+1:3}. {word:15} (freq: {freq:5}) - {context_text}")
    
    # Common endings
    ending_counts = Counter()
    for word, _ in not_found_words[:1000]:
        if len(word) >= 3:
            ending_counts[word[-3:]] += 1
        if len(word) >= 2:
            ending_counts[word[-2:]] += 1
    
    print("\nMost common endings in missing words:")
    for ending, count in ending_counts.most_common(15):
        print(f"  -{ending}: {count:,} words")
    
    # Check specific categories
    print("\n=== CATEGORY ANALYSIS ===\n")
    
    # Single letter words
    single_letters = [(w, f) for w, f in not_found_words if len(w) == 1]
    print(f"Single letter words: {len(single_letters)}")
    for word, freq in single_letters[:10]:
        print(f"  '{word}': {freq:,} occurrences")
    
    # Very long words
    long_words = [(w, f) for w, f in not_found_words if len(w) > 15]
    print(f"\nVery long words (>15 chars): {len(long_words)}")
    for word, freq in long_words[:10]:
        print(f"  {word} ({len(word)} chars): {freq:,} occurrences")
    
    # Words with specific patterns
    print("\n=== PATTERN ANALYSIS ===\n")
    
    # Words ending in specific verb endings
    verb_endings = ['ειν', 'ειτε', 'ουσι', 'ουσιν', 'ομεν', 'ετε', 'οντο', 'ομην']
    for ending in verb_endings:
        matching = [(w, f) for w, f in not_found_words[:500] if w.endswith(ending)]
        if matching:
            print(f"Words ending in -{ending}: {len(matching)}")
            for word, freq in matching[:3]:
                print(f"  {word}: {freq:,} occurrences")
    
    # Save analysis
    print(f"\nSaving analysis to 'missing_words_analysis.json'...")
    
    analysis_data = {
        'total_unique_words': total_unique,
        'total_tokens': total_tokens,
        'unique_coverage_percentage': unique_coverage,
        'token_coverage_percentage': token_coverage,
        'top_missing_words': [
            {'word': w, 'frequency': f} 
            for w, f in not_found_words[:200]
        ],
        'ending_distribution': dict(ending_counts.most_common(30))
    }
    
    with open('missing_words_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    
    conn.close()
    print("\nAnalysis complete!")

if __name__ == '__main__':
    analyze_coverage()