#!/usr/bin/env python3
"""
Analyze dictionary coverage by author in the Perseus texts database.
Calculates the percentage of unique words per author that have dictionary entries.
"""

import sqlite3
from collections import defaultdict
import json

def analyze_author_coverage(db_path="perseus_texts_sample.db"):
    """Calculate dictionary coverage statistics for each author."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all authors
    cursor.execute("""
        SELECT DISTINCT id, name 
        FROM authors 
        ORDER BY name
    """)
    authors = cursor.fetchall()
    
    results = []
    
    for author_id, author_name in authors:
        # Get total unique words for this author
        cursor.execute("""
            SELECT COUNT(DISTINCT w.word_normalized)
            FROM words w
            JOIN books b ON w.book_id = b.id
            JOIN works wo ON b.work_id = wo.id
            WHERE wo.author_id = ?
        """, (author_id,))
        total_unique_words = cursor.fetchone()[0]
        
        # Get unique words with lemma mappings (dictionary entry OR standalone lemma)
        cursor.execute("""
            SELECT COUNT(DISTINCT w.word_normalized)
            FROM words w
            JOIN books b ON w.book_id = b.id
            JOIN works wo ON b.work_id = wo.id
            WHERE wo.author_id = ?
            AND EXISTS (
                SELECT 1 FROM lemma_map lm
                WHERE lm.word_form = w.word_normalized
            )
        """, (author_id,))
        words_with_dictionary = cursor.fetchone()[0]
        
        # Get unique words with direct dictionary match (in dictionary_entries)
        cursor.execute("""
            SELECT COUNT(DISTINCT w.word_normalized)
            FROM words w
            JOIN books b ON w.book_id = b.id
            JOIN works wo ON b.work_id = wo.id
            WHERE wo.author_id = ?
            AND EXISTS (
                SELECT 1 FROM dictionary_entries de
                WHERE de.headword_normalized = w.word_normalized
            )
        """, (author_id,))
        direct_dictionary_matches = cursor.fetchone()[0]
        
        # Get total word count (tokens) for this author
        cursor.execute("""
            SELECT COUNT(*)
            FROM words w
            JOIN books b ON w.book_id = b.id
            JOIN works wo ON b.work_id = wo.id
            WHERE wo.author_id = ?
        """, (author_id,))
        total_tokens = cursor.fetchone()[0]
        
        # Get tokens with dictionary coverage
        cursor.execute("""
            SELECT COUNT(*)
            FROM words w
            JOIN books b ON w.book_id = b.id
            JOIN works wo ON b.work_id = wo.id
            WHERE wo.author_id = ?
            AND EXISTS (
                SELECT 1 FROM lemma_map lm
                WHERE lm.word_form = w.word_normalized
            )
        """, (author_id,))
        tokens_with_dictionary = cursor.fetchone()[0]
        
        # Calculate coverage percentages
        unique_coverage = (words_with_dictionary / total_unique_words * 100) if total_unique_words > 0 else 0
        token_coverage = (tokens_with_dictionary / total_tokens * 100) if total_tokens > 0 else 0
        direct_match_percent = (direct_dictionary_matches / total_unique_words * 100) if total_unique_words > 0 else 0
        
        # Get top missing words for this author
        cursor.execute("""
            SELECT w.word_normalized, COUNT(*) as freq
            FROM words w
            JOIN books b ON w.book_id = b.id
            JOIN works wo ON b.work_id = wo.id
            WHERE wo.author_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM lemma_map lm
                WHERE lm.word_form = w.word_normalized
            )
            GROUP BY w.word_normalized
            ORDER BY freq DESC
            LIMIT 10
        """, (author_id,))
        top_missing = cursor.fetchall()
        
        results.append({
            'author': author_name,
            'total_unique_words': total_unique_words,
            'words_with_dictionary': words_with_dictionary,
            'unique_coverage_percent': round(unique_coverage, 2),
            'total_tokens': total_tokens,
            'tokens_with_dictionary': tokens_with_dictionary,
            'token_coverage_percent': round(token_coverage, 2),
            'direct_dictionary_matches': direct_dictionary_matches,
            'direct_match_percent': round(direct_match_percent, 2),
            'top_missing_words': [{'word': w, 'frequency': f} for w, f in top_missing]
        })
    
    conn.close()
    return results

def print_coverage_report(results):
    """Print a formatted coverage report."""
    
    print("=" * 80)
    print("DICTIONARY COVERAGE BY AUTHOR")
    print("=" * 80)
    print()
    
    # Sort by unique coverage percentage
    results.sort(key=lambda x: x['unique_coverage_percent'], reverse=True)
    
    # Print summary table
    print(f"{'Author':<25} {'Unique Words':>12} {'Coverage %':>10} {'Token Coverage %':>16}")
    print("-" * 65)
    
    for r in results:
        print(f"{r['author']:<25} {r['total_unique_words']:>12,} {r['unique_coverage_percent']:>9.1f}% {r['token_coverage_percent']:>15.1f}%")
    
    print()
    print("=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    
    for r in results:
        print(f"\n{r['author']}:")
        print(f"  Total unique words: {r['total_unique_words']:,}")
        print(f"  Words with dictionary entry: {r['words_with_dictionary']:,} ({r['unique_coverage_percent']:.1f}%)")
        print(f"  Direct dictionary matches: {r['direct_dictionary_matches']:,} ({r['direct_match_percent']:.1f}%)")
        print(f"  Total word occurrences (tokens): {r['total_tokens']:,}")
        print(f"  Token coverage: {r['tokens_with_dictionary']:,} ({r['token_coverage_percent']:.1f}%)")
        
        if r['top_missing_words']:
            print(f"  Top missing words:")
            for word_data in r['top_missing_words'][:5]:
                print(f"    - {word_data['word']} ({word_data['frequency']} occurrences)")

if __name__ == "__main__":
    import sys
    
    # Use command line argument for database path if provided
    db_path = sys.argv[1] if len(sys.argv) > 1 else "perseus_texts_sample.db"
    
    print(f"Analyzing dictionary coverage in: {db_path}")
    results = analyze_author_coverage(db_path)
    
    # Save results to JSON
    output_file = "author_dictionary_coverage.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Print report
    print_coverage_report(results)