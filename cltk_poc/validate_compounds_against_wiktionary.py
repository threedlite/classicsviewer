#!/usr/bin/env python3
"""
Validate CLTK Compound Decompositions Against Wiktionary Ground Truth
=====================================================================

Compares CLTK-generated compound decompositions with documented Wiktionary
compound structure to assess accuracy.

Usage:
    python3 validate_compounds_against_wiktionary.py <dictionary_zip>

Output:
    Analysis written to COMPOUND_VALIDATION_REPORT.md
"""

import csv
import sys
import json
import zipfile
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

def normalize_greek(text: str) -> str:
    """Remove diacritics from Greek text for comparison"""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

class CompoundValidator:
    """Validates CLTK compound decompositions against Wiktionary ground truth"""

    def __init__(self, zip_path: Path, ground_truth_path: Path):
        self.zip_path = zip_path
        self.ground_truth_path = ground_truth_path
        self.cltk_compounds = {}
        self.wiktionary_compounds = {}
        self.load_data()

    def load_data(self):
        """Load CLTK output and Wiktionary ground truth"""
        print(f"Loading CLTK output from {self.zip_path.name}...")

        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            with zf.open('dictionary.csv') as f:
                reader = csv.DictReader(f.read().decode('utf-8').splitlines())
                for entry in reader:
                    word = entry['word_form']
                    definition = entry['definition']

                    # Extract top-ranked decomposition
                    if '1. ' in definition:
                        first_decomp = definition.split('1. ')[1].split('\n')[0].split(' 2.')[0]
                        # Parse decomposition: "ἀνά + τίθημι [score: 33.8]"
                        if ' + ' in first_decomp:
                            parts = first_decomp.split('[score:')[0].strip()
                            components = [c.strip() for c in parts.split(' + ')]
                            score = None
                            if '[score:' in first_decomp:
                                score_str = first_decomp.split('[score:')[1].split(']')[0].strip()
                                try:
                                    score = float(score_str)
                                except:
                                    pass

                            self.cltk_compounds[word] = {
                                'components': components,
                                'score': score,
                                'raw': first_decomp
                            }

        print(f"  ✓ Loaded {len(self.cltk_compounds)} CLTK compound decompositions")

        print(f"\nLoading Wiktionary ground truth from {self.ground_truth_path.name}...")
        with open(self.ground_truth_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.wiktionary_compounds = data['compounds']

        print(f"  ✓ Loaded {len(self.wiktionary_compounds)} Wiktionary compound entries")

    def compare_components(self, cltk_parts: List[str], wiki_parts: List[str]) -> Tuple[bool, str]:
        """Compare CLTK and Wiktionary component lists"""
        # Normalize all parts
        cltk_norm = [normalize_greek(p.lower()) for p in cltk_parts]
        wiki_norm = [normalize_greek(p.lower()) for p in wiki_parts]

        # Exact match
        if cltk_norm == wiki_norm:
            return True, "Exact match"

        # Same components, different order
        if set(cltk_norm) == set(wiki_norm):
            return True, "Same components (different order)"

        # Subset match (CLTK found some but not all)
        if set(cltk_norm).issubset(set(wiki_norm)):
            return True, "Partial match (subset)"

        # Overlap (some components match)
        overlap = set(cltk_norm) & set(wiki_norm)
        if overlap:
            return False, f"Partial overlap: {len(overlap)}/{len(wiki_norm)} components"

        return False, "No match"

    def validate(self):
        """Perform validation and generate report"""
        print(f"\n{'='*70}")
        print("COMPOUND DECOMPOSITION VALIDATION")
        print(f"{'='*70}")

        # Find overlapping words
        cltk_words = set(self.cltk_compounds.keys())
        wiki_words = set(self.wiktionary_compounds.keys())
        overlap_words = cltk_words & wiki_words

        print(f"\nCoverage:")
        print(f"  CLTK compounds: {len(cltk_words):,}")
        print(f"  Wiktionary ground truth: {len(wiki_words):,}")
        print(f"  Overlap (testable): {len(overlap_words):,}")
        print(f"  Coverage: {len(overlap_words)/len(wiki_words)*100:.1f}% of Wiktionary compounds")

        if not overlap_words:
            print("\n  WARNING: No overlapping words found!")
            return

        # Validate each overlapping word
        results = {
            'exact_match': [],
            'partial_match': [],
            'no_match': [],
            'scores': []
        }

        for word in sorted(overlap_words):
            cltk_data = self.cltk_compounds[word]
            wiki_entries = self.wiktionary_compounds[word]

            # Compare against all Wiktionary entries for this word
            best_match = None
            best_status = "No match"

            for wiki_entry in wiki_entries:
                wiki_parts = wiki_entry['components']
                is_match, status = self.compare_components(cltk_data['components'], wiki_parts)

                if is_match and best_match is None:
                    best_match = wiki_entry
                    best_status = status
                    break

            result = {
                'word': word,
                'cltk_components': cltk_data['components'],
                'cltk_score': cltk_data['score'],
                'wiki_components': wiki_parts,
                'status': best_status,
                'match': best_match is not None
            }

            if best_match:
                if "Exact match" in best_status:
                    results['exact_match'].append(result)
                else:
                    results['partial_match'].append(result)
            else:
                results['no_match'].append(result)

            if cltk_data['score'] is not None:
                results['scores'].append(cltk_data['score'])

        # Summary statistics
        total = len(overlap_words)
        exact = len(results['exact_match'])
        partial = len(results['partial_match'])
        no_match = len(results['no_match'])

        print(f"\nValidation Results:")
        print(f"  Exact matches: {exact}/{total} ({exact/total*100:.1f}%)")
        print(f"  Partial matches: {partial}/{total} ({partial/total*100:.1f}%)")
        print(f"  No matches: {no_match}/{total} ({no_match/total*100:.1f}%)")
        print(f"  Overall accuracy: {(exact+partial)/total*100:.1f}%")

        if results['scores']:
            avg_score = sum(results['scores']) / len(results['scores'])
            print(f"\nScore Statistics (for testable compounds):")
            print(f"  Average score: {avg_score:.1f}")
            print(f"  Min score: {min(results['scores']):.1f}")
            print(f"  Max score: {max(results['scores']):.1f}")

        # Write detailed report
        report_path = Path('COMPOUND_VALIDATION_REPORT.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Compound Decomposition Validation Report\n\n")
            f.write(f"**Dictionary**: {self.zip_path.name}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"- CLTK compounds: {len(cltk_words):,}\n")
            f.write(f"- Wiktionary ground truth: {len(wiki_words):,}\n")
            f.write(f"- Testable overlap: {total:,} ({total/len(wiki_words)*100:.1f}% of ground truth)\n\n")
            f.write(f"## Validation Results\n\n")
            f.write(f"- **Exact matches**: {exact}/{total} ({exact/total*100:.1f}%)\n")
            f.write(f"- **Partial matches**: {partial}/{total} ({partial/total*100:.1f}%)\n")
            f.write(f"- **No matches**: {no_match}/{total} ({no_match/total*100:.1f}%)\n")
            f.write(f"- **Overall accuracy**: {(exact+partial)/total*100:.1f}%\n\n")

            if results['scores']:
                f.write(f"## Score Distribution\n\n")
                f.write(f"- Average: {avg_score:.1f}\n")
                f.write(f"- Range: {min(results['scores']):.1f} - {max(results['scores']):.1f}\n\n")

            # Exact matches section
            f.write(f"## Exact Matches ({len(results['exact_match'])})\n\n")
            for r in results['exact_match'][:20]:
                f.write(f"- **{r['word']}**: ")
                f.write(f"{' + '.join(r['cltk_components'])}")
                if r['cltk_score']:
                    f.write(f" [score: {r['cltk_score']:.1f}]")
                f.write(f"\n")
            if len(results['exact_match']) > 20:
                f.write(f"\n*... and {len(results['exact_match']) - 20} more*\n")
            f.write(f"\n")

            # Partial matches section
            f.write(f"## Partial Matches ({len(results['partial_match'])})\n\n")
            for r in results['partial_match'][:20]:
                f.write(f"- **{r['word']}**\n")
                f.write(f"  - CLTK: {' + '.join(r['cltk_components'])}")
                if r['cltk_score']:
                    f.write(f" [score: {r['cltk_score']:.1f}]")
                f.write(f"\n")
                f.write(f"  - Wiktionary: {' + '.join(r['wiki_components'])}\n")
                f.write(f"  - Status: {r['status']}\n")
            if len(results['partial_match']) > 20:
                f.write(f"\n*... and {len(results['partial_match']) - 20} more*\n")
            f.write(f"\n")

            # No matches section
            f.write(f"## No Matches ({len(results['no_match'])})\n\n")
            for r in results['no_match'][:20]:
                f.write(f"- **{r['word']}**\n")
                f.write(f"  - CLTK: {' + '.join(r['cltk_components'])}")
                if r['cltk_score']:
                    f.write(f" [score: {r['cltk_score']:.1f}]")
                f.write(f"\n")
                f.write(f"  - Wiktionary: {' + '.join(r['wiki_components'])}\n")
            if len(results['no_match']) > 20:
                f.write(f"\n*... and {len(results['no_match']) - 20} more*\n")

        print(f"\n✓ Detailed report saved to: {report_path}")

        return results

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    if not zip_path.exists():
        print(f"ERROR: File not found: {zip_path}")
        sys.exit(1)

    ground_truth_path = Path('wiktionary_compound_ground_truth.json')
    if not ground_truth_path.exists():
        print(f"ERROR: Ground truth not found: {ground_truth_path}")
        print(f"Run extract_wiktionary_compounds.py first to generate ground truth data")
        sys.exit(1)

    validator = CompoundValidator(zip_path, ground_truth_path)
    validator.validate()

if __name__ == '__main__':
    main()
