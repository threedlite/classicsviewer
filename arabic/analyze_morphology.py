#!/usr/bin/env python3
"""
Analyze Mu'allaqa words with CAMeL Tools to extract lemmas and roots

This script:
1. Extracts unique words from arabic_texts.db
2. Analyzes each word using CAMeL Tools Gulf + Levantine analyzers (CC BY 4.0)
3. Generates morphology.csv with word_form → lemma/root mappings
4. Provides coverage statistics

Note: Using Gulf and Levantine dialect databases (CC BY 4.0 compatible)
      MSA database is GPL v2 licensed and cannot be used.
      Expected coverage: 20-40% (dialect databases on Classical Arabic)
"""

import sqlite3
import csv
from pathlib import Path
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
import re

# Paths
SCRIPT_DIR = Path(__file__).parent
DB_FILE = SCRIPT_DIR / "arabic_texts.db"
OUTPUT_CSV = SCRIPT_DIR / "arabic_morphology.csv"
NORM_RULES_FILE = SCRIPT_DIR.parent / "custom_dictionary" / "normalization_rules_arabic.csv"

def load_normalization_rules():
    """Load normalization rules from CSV file"""
    rules = []
    with open(NORM_RULES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['language'] == 'arabic':
                rules.append({
                    'pattern': row['pattern'],
                    'replacement': row['replacement'],
                    'priority': int(row['priority'])
                })
    # Sort by priority
    rules.sort(key=lambda x: x['priority'])
    return rules

# Load normalization rules once
NORMALIZATION_RULES = load_normalization_rules()

def normalize_arabic(text):
    """
    Apply normalization rules from normalization_rules_arabic.csv
    This ensures the script uses the EXACT same normalization as the app
    """
    if not text:
        return ""

    # Apply each rule in priority order
    for rule in NORMALIZATION_RULES:
        text = re.sub(rule['pattern'], rule['replacement'], text)

    return text

def extract_words_from_db():
    """Extract unique words from database"""
    print("Extracting words from database...")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT word
        FROM words
        ORDER BY word
    """)

    words = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"  Found {len(words)} unique words")
    return words

def analyze_words(words):
    """Analyze words using CAMeL Tools Gulf and Levantine analyzers (CC BY 4.0)"""
    print("\nLoading CAMeL Tools databases (Gulf + Levantine, CC BY 4.0)...")

    # Load Gulf Arabic database (CC BY 4.0)
    db_glf = MorphologyDB.builtin_db('calima-glf-01')
    analyzer_glf = Analyzer(db_glf)

    # Load Levantine Arabic database (CC BY 4.0)
    db_lev = MorphologyDB.builtin_db('calima-lev-01')
    analyzer_lev = Analyzer(db_lev)

    print("  Databases loaded successfully")
    print(f"\nAnalyzing {len(words)} words (trying Gulf then Levantine)...")

    morphology_entries = []
    analyzed_count = 0
    failed_words = []

    for idx, word in enumerate(words, 1):
        # Try Gulf Arabic analyzer first
        analyses = analyzer_glf.analyze(word)
        source = 'Gulf'

        if not analyses:
            # Try Levantine analyzer
            analyses = analyzer_lev.analyze(word)
            source = 'Levantine'

        if analyses:
            # Take first (most likely) analysis
            top_analysis = analyses[0]

            # Extract morphological features
            lemma_arabic = top_analysis.get('lex', word)
            root = top_analysis.get('root', '')
            pos = top_analysis.get('pos', '')

            # Normalize both lemma and word form (remove diacritics)
            lemma = normalize_arabic(lemma_arabic)
            word_form = normalize_arabic(word)

            # Confidence: 1.0 if single analysis, 0.8 if multiple
            confidence = 1.0 if len(analyses) == 1 else 0.8

            entry = {
                'word_form': word_form,
                'lemma': lemma,
                'root': root,
                'pos': pos,
                'language': 'arabic',
                'confidence': confidence,
                'source_name': f'CAMeL Tools {source} (CC BY 4.0)'
            }
            morphology_entries.append(entry)
            analyzed_count += 1
        else:
            # No analysis found - use normalized word as lemma
            word_form = normalize_arabic(word)
            entry = {
                'word_form': word_form,
                'lemma': word_form,  # Use same normalized form as lemma
                'root': '',
                'pos': '',
                'language': 'arabic',
                'confidence': 0.0,
                'source_name': 'Unanalyzed'
            }
            morphology_entries.append(entry)
            failed_words.append(word_form)

        # Progress indicator
        if idx % 50 == 0:
            print(f"  Processed {idx}/{len(words)} words...")

    print(f"\n✅ Analysis complete:")
    print(f"   Analyzed: {analyzed_count}/{len(words)} ({analyzed_count/len(words)*100:.1f}%)")
    print(f"   Unanalyzed: {len(failed_words)} ({len(failed_words)/len(words)*100:.1f}%)")

    if failed_words:
        print(f"\n  Sample unanalyzed words (showing first 20):")
        for word in failed_words[:20]:
            print(f"    - {word}")

    return morphology_entries, analyzed_count, len(failed_words)

def write_morphology_csv(entries):
    """Write morphology entries to CSV"""
    print(f"\nWriting morphology to {OUTPUT_CSV}...")

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['word_form', 'lemma', 'root', 'pos', 'language', 'confidence', 'source_name']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(entries)

    # Get file size
    size_kb = OUTPUT_CSV.stat().st_size / 1024

    print(f"✅ Morphology file created:")
    print(f"   File: {OUTPUT_CSV.name}")
    print(f"   Size: {size_kb:.1f} KB")
    print(f"   Entries: {len(entries)}")

def main():
    """Main execution"""
    print("="*60)
    print("Arabic Morphology Analysis using CAMeL Tools")
    print("="*60)
    print()

    # Extract words
    words = extract_words_from_db()

    # Analyze with CAMeL Tools
    morphology_entries, analyzed, failed = analyze_words(words)

    # Write to CSV
    write_morphology_csv(morphology_entries)

    print(f"\n{'='*60}")
    print("✅ Morphology analysis complete!")
    print(f"{'='*60}")
    print()
    print("Next steps:")
    print("1. Review arabic_morphology.csv")
    print("2. Consider manually adding lemmas for high-frequency unanalyzed words")
    print("3. Run create_arabic_lexicon.py to update arabic_lexicon.zip")

if __name__ == "__main__":
    main()
