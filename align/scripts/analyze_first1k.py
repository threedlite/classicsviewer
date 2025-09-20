#!/usr/bin/env python3
"""Analyze First1K texts to identify which need alignment"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from lxml import etree

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.xml_parser import TEIReader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class First1KAnalyzer:
    """Analyze First1K corpus for alignment needs"""

    def __init__(self):
        self.tei_reader = TEIReader()

    def find_english_translation(self, greek_file: Path) -> Optional[Path]:
        """Find corresponding English translation file"""

        # Get base name without language code
        stem = greek_file.stem
        base_name = stem.replace('-grc1', '').replace('-grc2', '').replace('-grc', '')

        # Look for English file in same directory
        search_dir = greek_file.parent

        # Try various patterns
        patterns = [
            f"{base_name}-eng*.xml",
            f"{base_name}.first1k-eng*.xml",
            f"*{base_name}*-eng*.xml"
        ]

        for pattern in patterns:
            english_files = list(search_dir.glob(pattern))
            if english_files:
                return english_files[0]

        return None

    def has_alignment_milestones(self, greek_file: Path, english_file: Path) -> bool:
        """Check if files already have alignment milestones"""

        try:
            # Parse files
            greek_doc = etree.parse(str(greek_file))
            english_doc = etree.parse(str(english_file))

            # Check for alignment milestones
            greek_milestones = greek_doc.xpath('//milestone[@unit="alignment"]')
            english_milestones = english_doc.xpath('//milestone[@unit="alignment"]')

            # Also check for align namespace
            greek_has_align = 'align' in greek_doc.getroot().nsmap
            english_has_align = 'align' in english_doc.getroot().nsmap

            return (len(greek_milestones) > 0 or len(english_milestones) > 0 or
                   greek_has_align or english_has_align)

        except Exception as e:
            logger.debug(f"Error checking milestones: {e}")
            return False

    def check_translation_lookup_exists(self, text_id: str) -> bool:
        """Check if translation_lookup entries exist in database"""
        # This would query the database, but for now we assume
        # First1K texts don't have existing alignments unless
        # they have alignment milestones in XML
        return False

    def analyze_text(self, greek_file: Path) -> Dict:
        """Analyze a single Greek text"""

        text_id = greek_file.stem

        # Find the First1K root directory (parent of 'data' folder)
        first1k_root = greek_file
        while first1k_root.name != 'data' and first1k_root.parent != first1k_root:
            first1k_root = first1k_root.parent
        if first1k_root.name == 'data':
            first1k_root = first1k_root.parent

        result = {
            'id': text_id,
            'greek_file': str(greek_file.relative_to(first1k_root)),
            'status': 'greek_only',
            'english_file': None,
            'has_alignment': False
        }

        # Check for English translation
        english_file = self.find_english_translation(greek_file)

        if english_file:
            result['english_file'] = str(english_file.relative_to(first1k_root))

            # Check if alignment exists
            if self.has_alignment_milestones(greek_file, english_file):
                result['status'] = 'has_alignment'
                result['has_alignment'] = True
            else:
                result['status'] = 'needs_alignment'
        else:
            # Try to parse Greek file to get metadata
            try:
                greek_doc = self.tei_reader.parse_file(greek_file)
                if greek_doc:
                    # Could extract author, title, etc.
                    pass
            except:
                pass

        return result

    def analyze_directory(self, first1k_dir: Path) -> Dict:
        """Analyze entire First1K directory"""

        results = {
            'texts': [],
            'by_status': {
                'greek_only': [],
                'has_alignment': [],
                'needs_alignment': []
            },
            'stats': {}
        }

        # First1K structure has XML files in 'data' subdirectory
        data_dir = first1k_dir / 'data'
        if not data_dir.exists():
            data_dir = first1k_dir  # Fallback to root if no data dir

        # Find all Greek files
        greek_files = list(data_dir.glob('**/*-grc*.xml'))
        logger.info(f"Found {len(greek_files)} Greek texts in First1K")

        # Analyze each text
        for greek_file in greek_files:
            logger.debug(f"Analyzing {greek_file.name}")
            text_info = self.analyze_text(greek_file)

            results['texts'].append(text_info)
            results['by_status'][text_info['status']].append(text_info)

        # Calculate statistics
        total = len(results['texts'])
        results['stats'] = {
            'total': total,
            'greek_only': len(results['by_status']['greek_only']),
            'has_alignment': len(results['by_status']['has_alignment']),
            'needs_alignment': len(results['by_status']['needs_alignment']),
            'with_translation': len(results['by_status']['has_alignment']) +
                              len(results['by_status']['needs_alignment']),
            'percentage_with_translation': 0
        }

        if total > 0:
            results['stats']['percentage_with_translation'] = (
                results['stats']['with_translation'] / total * 100
            )

        return results

    def print_summary(self, results: Dict):
        """Print analysis summary"""

        stats = results['stats']

        print("\n" + "=" * 60)
        print("First1K Corpus Analysis Summary")
        print("=" * 60)
        print(f"\nTotal Greek texts: {stats['total']}")
        print(f"├── Greek only (no translation): {stats['greek_only']} "
              f"({stats['greek_only']/stats['total']*100:.1f}%)")
        print(f"├── Has translation + alignment: {stats['has_alignment']} "
              f"({stats['has_alignment']/stats['total']*100:.1f}%)")
        print(f"└── Has translation, needs alignment: {stats['needs_alignment']} "
              f"({stats['needs_alignment']/stats['total']*100:.1f}%)")

        print(f"\nTexts with translations: {stats['with_translation']} "
              f"({stats['percentage_with_translation']:.1f}%)")

        if results['by_status']['needs_alignment']:
            print(f"\nTexts needing alignment ({len(results['by_status']['needs_alignment'])}):")
            for text in results['by_status']['needs_alignment'][:10]:
                print(f"  - {text['id']}")
            if len(results['by_status']['needs_alignment']) > 10:
                print(f"  ... and {len(results['by_status']['needs_alignment']) - 10} more")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze First1K texts to identify alignment needs'
    )
    parser.add_argument(
        '--first1k-dir',
        type=Path,
        required=True,
        help='Directory containing First1K texts'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('first1k_analysis.json'),
        help='Output JSON file for analysis results'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Check input directory
    if not args.first1k_dir.exists():
        logger.error(f"First1K directory not found: {args.first1k_dir}")
        return 1

    # Analyze
    analyzer = First1KAnalyzer()
    logger.info(f"Analyzing First1K corpus in {args.first1k_dir}")

    results = analyzer.analyze_directory(args.first1k_dir)

    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Analysis saved to {args.output}")

    # Print summary
    analyzer.print_summary(results)

    return 0


if __name__ == '__main__':
    sys.exit(main())