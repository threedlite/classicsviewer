#!/usr/bin/env python3
"""
Quality Spot-Check Tool for CLTK Dictionary Generation
=======================================================

Performs stratified random sampling and quality checks on generated dictionaries.

Usage:
    python3 quality_spot_check.py <dictionary_zip> [options]

Options:
    --sample-size N       Number of morphology entries to sample (default: 100)
    --compound-sample N   Number of compound entries to sample (default: 10)
    --check-perseus       Validate lemmas against Perseus database
    --output REPORT.md    Output quality report file

Checks performed:
    1. Morphology sampling: Random sample with lemma validation
    2. Compound decomposition quality: Score distribution and validation
    3. Coverage stats: Success rates, unique lemmas, POS distribution
    4. Known word validation: Test against known correct forms
"""

import csv
import sys
import zipfile
import random
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict

def normalize_greek(text: str) -> str:
    """Remove diacritics from Greek text for comparison"""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


class QualityChecker:
    """Quality checker for CLTK dictionary generation output"""

    def __init__(self, zip_path: Path, db_path: Path = None):
        self.zip_path = zip_path
        self.db_path = db_path or self.find_database()
        self.morphology_data = []
        self.compound_data = []
        self.perseus_lemmas = set()
        self.load_data()

    def find_database(self) -> Path:
        """Find Perseus database"""
        data_prep = Path(__file__).parent.parent / 'data-prep'
        candidates = [
            data_prep / 'perseus_texts_extended.db',
            data_prep / 'perseus_texts_full.db',
            data_prep / 'perseus_texts_sample.db',
        ]
        for db in candidates:
            if db.exists():
                return db
        return None

    def load_data(self):
        """Load morphology and compound data from ZIP"""
        print(f"Loading data from {self.zip_path.name}...")

        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            # Load morphology
            with zf.open('morphology.csv') as f:
                reader = csv.DictReader(f.read().decode('utf-8').splitlines())
                self.morphology_data = list(reader)

            # Load compounds
            with zf.open('dictionary.csv') as f:
                reader = csv.DictReader(f.read().decode('utf-8').splitlines())
                self.compound_data = list(reader)

        print(f"  ✓ Loaded {len(self.morphology_data)} morphology entries")
        print(f"  ✓ Loaded {len(self.compound_data)} compound entries")

    def load_perseus_lemmas(self):
        """Load valid lemmas from Perseus database"""
        if not self.db_path or self.perseus_lemmas:
            return

        print(f"\nLoading Perseus lemmas from {self.db_path.name}...")
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            "SELECT DISTINCT headword FROM dictionary_entries "
            "WHERE language = 'greek' AND headword IS NOT NULL"
        )
        for row in cursor:
            self.perseus_lemmas.add(row[0].lower())

        conn.close()
        print(f"  ✓ Loaded {len(self.perseus_lemmas)} Perseus lemmas")

    def sample_morphology(self, sample_size: int = 100) -> List[Dict]:
        """Stratified random sampling of morphology entries"""
        # Group by POS tag
        by_pos = defaultdict(list)
        for entry in self.morphology_data:
            pos = entry['morph_info'].split(',')[0] if entry['morph_info'] else 'Unknown'
            by_pos[pos].append(entry)

        # Sample proportionally from each POS category
        samples = []
        total = len(self.morphology_data)

        for pos, entries in by_pos.items():
            n_samples = max(1, int(len(entries) / total * sample_size))
            samples.extend(random.sample(entries, min(n_samples, len(entries))))

        return samples[:sample_size]

    def validate_lemma(self, lemma: str) -> Tuple[bool, str]:
        """Validate if lemma exists in Perseus dictionary"""
        if not self.perseus_lemmas:
            return None, "Perseus DB not loaded"

        lemma_lower = lemma.lower()
        lemma_norm = normalize_greek(lemma_lower)

        # Exact match
        if lemma_lower in self.perseus_lemmas:
            return True, "Exact match"

        # Normalized match (handles diacritics)
        for perseus_lemma in self.perseus_lemmas:
            if normalize_greek(perseus_lemma) == lemma_norm:
                return True, f"Fuzzy match: {perseus_lemma}"

        return False, "Not found in Perseus"

    def check_morphology_quality(self, sample_size: int = 100):
        """Perform quality checks on morphology"""
        print(f"\n{'='*70}")
        print("MORPHOLOGY QUALITY CHECK")
        print(f"{'='*70}")

        # Overall stats
        total = len(self.morphology_data)
        unique_lemmas = len(set(e['lemma'] for e in self.morphology_data))
        unique_words = len(set(e['word_form'] for e in self.morphology_data))

        print(f"\nOverall Statistics:")
        print(f"  Total entries: {total:,}")
        print(f"  Unique word forms: {unique_words:,}")
        print(f"  Unique lemmas: {unique_lemmas:,}")
        print(f"  Lemma reduction: {(1 - unique_lemmas/unique_words)*100:.1f}%")

        # POS distribution
        pos_counts = Counter()
        for entry in self.morphology_data:
            pos = entry['morph_info'].split(',')[0] if entry['morph_info'] else 'Unknown'
            pos_counts[pos] += 1

        print(f"\nPOS Distribution (top 10):")
        for pos, count in pos_counts.most_common(10):
            print(f"  {pos:20s}: {count:6,} ({count/total*100:5.1f}%)")

        # Sample validation
        print(f"\nRandom Sample Validation (n={sample_size}):")
        samples = self.sample_morphology(sample_size)

        if self.db_path:
            self.load_perseus_lemmas()

            valid_count = 0
            invalid_examples = []

            for entry in samples:
                is_valid, reason = self.validate_lemma(entry['lemma'])
                if is_valid:
                    valid_count += 1
                elif is_valid is False and len(invalid_examples) < 5:
                    invalid_examples.append((entry['word_form'], entry['lemma'], reason))

            print(f"  Valid lemmas: {valid_count}/{sample_size} ({valid_count/sample_size*100:.1f}%)")

            if invalid_examples:
                print(f"\n  Examples of invalid lemmas:")
                for word, lemma, reason in invalid_examples:
                    print(f"    {word} → {lemma} ({reason})")
        else:
            print("  [Skipped - Perseus database not available]")

        return {
            'total': total,
            'unique_lemmas': unique_lemmas,
            'unique_words': unique_words,
            'pos_distribution': dict(pos_counts.most_common(10)),
            'sample_size': sample_size,
            'valid_count': valid_count if self.db_path else None
        }

    def check_compound_quality(self, sample_size: int = 10):
        """Perform quality checks on compound decompositions"""
        print(f"\n{'='*70}")
        print("COMPOUND DECOMPOSITION QUALITY CHECK")
        print(f"{'='*70}")

        if not self.compound_data:
            print("\n  No compound entries found!")
            return

        total = len(self.compound_data)
        print(f"\nOverall Statistics:")
        print(f"  Total compounds: {total:,}")

        # Extract scores from definitions
        scores = []
        decomp_counts = []

        for entry in self.compound_data:
            definition = entry['definition']

            # Count decompositions
            count_match = definition.split('(')[1].split(' ')[0] if '(' in definition else '0'
            try:
                decomp_counts.append(int(count_match))
            except:
                pass

            # Extract top score
            if '[score:' in definition:
                score_str = definition.split('[score:')[1].split(']')[0].strip()
                try:
                    scores.append(float(score_str))
                except:
                    pass

        if scores:
            print(f"\nScore Distribution (top-ranked decompositions):")
            print(f"  Min:    {min(scores):.1f}")
            print(f"  Max:    {max(scores):.1f}")
            print(f"  Mean:   {sum(scores)/len(scores):.1f}")
            print(f"  Median: {sorted(scores)[len(scores)//2]:.1f}")

            # Score buckets
            buckets = Counter()
            for score in scores:
                bucket = int(score // 5) * 5
                buckets[bucket] += 1

            print(f"\n  Score ranges:")
            for bucket in sorted(buckets.keys(), reverse=True):
                count = buckets[bucket]
                print(f"    {bucket:2d}-{bucket+4}: {'█' * (count * 40 // total)} {count} ({count/total*100:.1f}%)")

        if decomp_counts:
            avg_decomps = sum(decomp_counts) / len(decomp_counts)
            print(f"\n  Average decompositions per word: {avg_decomps:.1f}")

        # Sample some compounds
        print(f"\nRandom Sample (n={min(sample_size, total)}):")
        samples = random.sample(self.compound_data, min(sample_size, total))

        for i, entry in enumerate(samples, 1):
            word = entry['word_form']
            definition = entry['definition']

            # Extract first decomposition
            if '1. ' in definition:
                first_decomp = definition.split('1. ')[1].split('\n')[0].split(' 2.')[0]
                print(f"\n  {i}. {word}")
                print(f"     {first_decomp[:100]}...")

        return {
            'total': total,
            'scores': scores,
            'avg_decomps': avg_decomps if decomp_counts else None
        }

    def test_known_words(self):
        """Test against known correct lemmatizations (only if words are present)"""
        print(f"\n{'='*70}")
        print("KNOWN WORD VALIDATION (Optional - Corpus Coverage Check)")
        print(f"{'='*70}")

        # Test cases: (word_form, expected_lemma, description)
        known_words = [
            ('ἀνδρός', 'ἀνήρ', 'man (genitive)'),
            ('λόγων', 'λόγος', 'word (genitive plural)'),
            ('πόλεως', 'πόλις', 'city (genitive)'),
            ('θεοῦ', 'θεός', 'god (genitive)'),
            ('ἐποίησε', 'ποιέω', 'he made (verb)'),
            ('μείζων', 'μέγας', 'greater (comparative)'),
            ('καλή', 'καλός', 'beautiful (feminine)'),
            ('ἀγαθόν', 'ἀγαθός', 'good (neuter)'),
        ]

        # Create lookup
        word_to_lemma = {e['word_form']: e['lemma'] for e in self.morphology_data}

        # Check how many test words are actually in corpus
        found_words = [w for w, _, _ in known_words if w in word_to_lemma]

        if len(found_words) < 3:
            print(f"\nNote: Only {len(found_words)}/{len(known_words)} test words found in corpus.")
            print(f"This is expected for specialized or limited corpora.")
            print(f"Skipping validation - insufficient coverage for meaningful results.\n")
            return {
                'tested': len(known_words),
                'found': len(found_words),
                'correct': 0,
                'accuracy': None,
                'skipped': True
            }

        print(f"\nTesting {len(known_words)} common Greek words ({len(found_words)} present in corpus):")
        correct = 0
        tested = 0

        for word, expected, desc in known_words:
            actual = word_to_lemma.get(word, None)

            if actual:
                tested += 1
                # Normalize for comparison
                expected_norm = normalize_greek(expected.lower())
                actual_norm = normalize_greek(actual.lower())

                is_correct = expected_norm == actual_norm
                status = "✓" if is_correct else "✗"

                print(f"  {status} {word:15s} → {actual:15s} (expected: {expected}, {desc})")

                if is_correct:
                    correct += 1
            else:
                print(f"  - {word:15s} → [NOT IN CORPUS] (would expect: {expected}, {desc})")

        if tested > 0:
            print(f"\nAccuracy: {correct}/{tested} ({correct/tested*100:.1f}%) of words present in corpus")

        print(f"Coverage: {tested}/{len(known_words)} test words found in corpus")

        return {
            'tested': len(known_words),
            'found': tested,
            'correct': correct,
            'accuracy': correct / tested if tested > 0 else None,
            'skipped': False
        }

    def generate_report(self, output_file: Path = None):
        """Generate comprehensive quality report"""
        print(f"\n{'='*70}")
        print("GENERATING COMPREHENSIVE QUALITY REPORT")
        print(f"{'='*70}")

        morph_stats = self.check_morphology_quality(sample_size=100)
        compound_stats = self.check_compound_quality(sample_size=20)
        known_stats = self.test_known_words()

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Quality Report: {self.zip_path.name}\n\n")
                f.write(f"Generated: {Path.ctime(self.zip_path)}\n\n")
                f.write(f"## Morphology\n\n")
                f.write(f"- Total entries: {morph_stats['total']:,}\n")
                f.write(f"- Unique lemmas: {morph_stats['unique_lemmas']:,}\n")
                f.write(f"- Unique words: {morph_stats['unique_words']:,}\n\n")
                f.write(f"## Compounds\n\n")
                f.write(f"- Total compounds: {compound_stats['total']:,}\n")
                if compound_stats['avg_decomps']:
                    f.write(f"- Avg decompositions: {compound_stats['avg_decomps']:.1f}\n")
                f.write(f"\n## Known Word Validation\n\n")
                f.write(f"- Accuracy: {known_stats['accuracy']*100:.1f}%\n")

            print(f"\n✓ Report saved to: {output_file}")

        print(f"\n{'='*70}")
        print("QUALITY CHECK COMPLETE")
        print(f"{'='*70}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    if not zip_path.exists():
        print(f"ERROR: File not found: {zip_path}")
        sys.exit(1)

    # Parse options
    sample_size = 100
    compound_sample = 10
    output_file = None

    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '--sample-size' and i + 1 < len(sys.argv):
            sample_size = int(sys.argv[i + 1])
        elif sys.argv[i] == '--compound-sample' and i + 1 < len(sys.argv):
            compound_sample = int(sys.argv[i + 1])
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_file = Path(sys.argv[i + 1])

    # Run quality checks
    checker = QualityChecker(zip_path)
    checker.generate_report(output_file)


if __name__ == '__main__':
    main()
