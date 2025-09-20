#!/usr/bin/env python3
"""Apply alignment model to First1K texts with detailed reporting"""

import sys
import json
import pickle
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from src.xml_parser import TEIReader
from src.alignment import AlignmentPredictor
from src.xml_writer import XMLEnhancer
from src.validation import TranslationValidator
from generate_author_work_mapping import generate_mappings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class First1KAligner:
    """Apply alignment to First1K texts with detailed reporting"""

    def __init__(self, model_path: Path = None, first1k_dir: Path = None):
        self.tei_reader = TEIReader()
        self.xml_enhancer = XMLEnhancer()
        self.validator = TranslationValidator()

        # Generate or load author/work mappings
        self.mappings = self._load_or_generate_mappings(first1k_dir)

        # Load trained model if provided
        self.model_data = None
        if model_path and model_path.exists():
            logger.info(f"Using trained model: {model_path}")
            with open(model_path, 'rb') as f:
                self.model_data = pickle.load(f)
                self.predictor = AlignmentPredictor()
                self.predictor.model = self.model_data['model']
        else:
            logger.info("Using rule-based alignment only")
            self.predictor = AlignmentPredictor()

        # Initialize report structure
        self.report = {
            'summary': {
                'total_texts': 0,
                'successful': 0,
                'failed': 0,
                'total_runtime': 0,
                'start_time': None,
                'end_time': None
            },
            'model_metrics': {
                'total_alignments_attempted': 0,
                'total_alignments_accepted': 0,
                'total_alignments_rejected': 0,
                'confidence_distribution': []
            },
            'by_author': defaultdict(lambda: {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'works': []
            }),
            'successful_alignments': [],
            'failed_alignments': [],
            'timing': []
        }

    def _load_or_generate_mappings(self, first1k_dir: Path = None) -> Dict:
        """Load existing mappings or generate from First1K metadata"""

        mapping_file = Path(__file__).parent.parent / 'author_work_mapping.json'

        # If First1K dir provided, regenerate mappings
        if first1k_dir and first1k_dir.exists():
            logger.info("Generating author/work mappings from First1K metadata...")
            try:
                mappings = generate_mappings(first1k_dir)

                # Save the generated mappings
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(mappings, f, indent=2, ensure_ascii=False)
                logger.info(f"Generated mappings for {len(mappings['authors'])} authors")
                return mappings
            except Exception as e:
                logger.warning(f"Failed to generate mappings: {e}")

        # Try to load existing
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Fallback to empty
        return {'authors': {}, 'works': {}}

    def align_text_pair(self, greek_file: Path, english_file: Path,
                       output_dir: Path, min_confidence: float = 0.6) -> Tuple[bool, Dict]:
        """Align a Greek-English text pair and generate report entry"""

        start_time = time.time()
        result = {
            'greek_file': str(greek_file.name),
            'english_file': str(english_file.name),
            'author': greek_file.parent.parent.name,  # tlgXXXX
            'work': greek_file.parent.name,  # tlgYYY
            'start_time': datetime.now().isoformat(),
            'runtime': 0,
            'status': 'failed',
            'reason': None,
            'stats': {}
        }

        try:
            logger.info(f"Aligning {greek_file.name} with {english_file.name}")

            # Validate that the English file is actually a translation
            logger.info(f"Validating translation pair...")
            validation_result = self.validator.validate_translation_pair(greek_file, english_file)

            if not validation_result['is_valid']:
                logger.warning(f"English file does not appear to be a translation: {validation_result['reason']}")
                result['reason'] = f'Not a valid translation: {validation_result["reason"]}'
                result['validation_details'] = validation_result
                result['runtime'] = time.time() - start_time
                return False, result

            logger.info(f"Validation passed with overall score: {validation_result.get('overall_score', 0):.3f}")

            # Parse XML files
            parse_start = time.time()
            greek_root = self.tei_reader.parse_file(greek_file)
            english_root = self.tei_reader.parse_file(english_file)
            parse_time = time.time() - parse_start
            result['stats']['parse_time'] = round(parse_time, 3)

            if greek_root is None or english_root is None:
                result['reason'] = 'Failed to parse XML files'
                result['runtime'] = time.time() - start_time
                return False, result

            # Extract segments
            extract_start = time.time()
            greek_segments = self.tei_reader.extract_segments(greek_root)
            english_segments = self.tei_reader.extract_segments(english_root)
            extract_time = time.time() - extract_start
            result['stats']['extract_time'] = round(extract_time, 3)
            result['stats']['greek_segments'] = len(greek_segments)
            result['stats']['english_segments'] = len(english_segments)

            if not greek_segments:
                result['reason'] = f'No Greek segments extracted'
                result['runtime'] = time.time() - start_time
                return False, result

            if not english_segments:
                result['reason'] = f'No English segments extracted'
                result['runtime'] = time.time() - start_time
                return False, result

            # Perform alignment
            align_start = time.time()
            result_dict = self.predictor.align_texts(greek_file, english_file)
            alignments = result_dict.get('alignments', [])
            align_time = time.time() - align_start
            result['stats']['align_time'] = round(align_time, 3)
            result['stats']['total_alignments'] = len(alignments)

            # Filter by confidence and collect metrics
            filtered = [a for a in alignments if a.get('confidence', 0) >= min_confidence]
            result['stats']['filtered_alignments'] = len(filtered)
            result['stats']['avg_confidence'] = round(
                sum(a.get('confidence', 0) for a in filtered) / max(len(filtered), 1), 3
            )

            # Collect confidence scores for model metrics
            for a in alignments:
                confidence = a.get('confidence', 0)
                self.report['model_metrics']['confidence_distribution'].append(confidence)
                self.report['model_metrics']['total_alignments_attempted'] += 1
                if confidence >= min_confidence:
                    self.report['model_metrics']['total_alignments_accepted'] += 1
                else:
                    self.report['model_metrics']['total_alignments_rejected'] += 1

            if not filtered:
                result['reason'] = f'No alignments above confidence threshold {min_confidence}'
                result['runtime'] = time.time() - start_time
                return False, result

            logger.info(f"Found {len(filtered)} alignments (filtered from {len(alignments)} total)")

            # Save alignment JSON
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{greek_file.stem}_alignment.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'greek_file': str(greek_file),
                    'english_file': str(english_file),
                    'alignments': filtered,
                    'metadata': {
                        'total_greek_segments': len(greek_segments),
                        'total_english_segments': len(english_segments),
                        'aligned_segments': len(filtered),
                        'confidence_threshold': min_confidence
                    }
                }, f, ensure_ascii=False, indent=2)

            result['status'] = 'success'
            result['output_file'] = str(output_file)
            result['runtime'] = round(time.time() - start_time, 3)

            # Try to enhance XML (optional, don't fail if this errors)
            try:
                logger.info(f"Enhancing XML files with alignments")
                greek_output, english_output = self.xml_enhancer.enhance_xml_files(
                    greek_file, english_file, filtered, output_dir
                )
                result['xml_enhanced'] = True
                result['enhanced_files'] = {
                    'greek': str(greek_output),
                    'english': str(english_output)
                }
            except Exception as e:
                logger.error(f"Error enhancing XML: {e}")
                result['xml_enhanced'] = False
                result['xml_error'] = str(e)
                # Still consider it successful if we got alignments

            return True, result

        except Exception as e:
            logger.error(f"Error aligning {greek_file.name}: {e}")
            result['reason'] = f'Exception: {str(e)}'
            result['runtime'] = round(time.time() - start_time, 3)
            return False, result

    def process_first1k_texts(self, analysis: Dict, first1k_dir: Path,
                            output_dir: Path, min_confidence: float = 0.6):
        """Process all First1K texts needing alignment"""

        # Get texts needing alignment
        texts_to_align = analysis['by_status']['needs_alignment']

        if not texts_to_align:
            logger.info("No First1K texts need alignment")
            return

        self.report['summary']['total_texts'] = len(texts_to_align)
        self.report['summary']['start_time'] = datetime.now().isoformat()

        logger.info(f"\nProcessing {len(texts_to_align)} First1K texts needing alignment")
        logger.info(f"Skipping {analysis['stats']['has_alignment']} texts with existing alignment")
        logger.info(f"Ignoring {analysis['stats']['greek_only']} Greek-only texts")

        # Process each text
        with tqdm(texts_to_align, desc="Aligning texts") as pbar:
            for text_info in pbar:
                # Get file paths - add 'data/' if path doesn't start with it
                greek_path = text_info['greek_file']
                english_path = text_info['english_file']

                # Add 'data/' prefix if not present
                if not greek_path.startswith('data/'):
                    greek_path = f"data/{greek_path}"
                if not english_path.startswith('data/'):
                    english_path = f"data/{english_path}"

                greek_file = first1k_dir / greek_path
                english_file = first1k_dir / english_path

                # Update progress bar
                pbar.set_description(f"Aligning {text_info['id']}")

                # Check files exist
                if not greek_file.exists():
                    logger.warning(f"Greek file not found: {greek_file}")
                    result = {
                        'greek_file': str(greek_file.name),
                        'english_file': str(english_file.name),
                        'author': greek_file.parent.parent.name,
                        'work': greek_file.parent.name,
                        'status': 'failed',
                        'reason': 'Greek file not found',
                        'runtime': 0
                    }
                    self.report['failed_alignments'].append(result)
                    self.report['summary']['failed'] += 1
                    self.report['by_author'][result['author']]['failed'] += 1
                    self.report['by_author'][result['author']]['total'] += 1
                    self.report['by_author'][result['author']]['works'].append(result)
                    continue

                if not english_file.exists():
                    logger.warning(f"English file not found: {english_file}")
                    result = {
                        'greek_file': str(greek_file.name),
                        'english_file': str(english_file.name),
                        'author': greek_file.parent.parent.name,
                        'work': greek_file.parent.name,
                        'status': 'failed',
                        'reason': 'English file not found',
                        'runtime': 0
                    }
                    self.report['failed_alignments'].append(result)
                    self.report['summary']['failed'] += 1
                    self.report['by_author'][result['author']]['failed'] += 1
                    self.report['by_author'][result['author']]['total'] += 1
                    self.report['by_author'][result['author']]['works'].append(result)
                    continue

                # Align
                success, result = self.align_text_pair(
                    greek_file, english_file, output_dir, min_confidence
                )

                # Update report
                if success:
                    self.report['successful_alignments'].append(result)
                    self.report['summary']['successful'] += 1
                    self.report['by_author'][result['author']]['successful'] += 1
                    pbar.set_postfix(failed=self.report['summary']['failed'],
                                    success=self.report['summary']['successful'])
                else:
                    self.report['failed_alignments'].append(result)
                    self.report['summary']['failed'] += 1
                    self.report['by_author'][result['author']]['failed'] += 1
                    pbar.set_postfix(failed=self.report['summary']['failed'],
                                    success=self.report['summary']['successful'])

                self.report['by_author'][result['author']]['total'] += 1
                self.report['by_author'][result['author']]['works'].append(result)
                self.report['timing'].append({
                    'work': f"{result['author']}.{result['work']}",
                    'runtime': result['runtime']
                })

        self.report['summary']['end_time'] = datetime.now().isoformat()
        start = datetime.fromisoformat(self.report['summary']['start_time'])
        end = datetime.fromisoformat(self.report['summary']['end_time'])
        self.report['summary']['total_runtime'] = round((end - start).total_seconds(), 3)

    def _calculate_model_metrics(self):
        """Use actual model training metrics if available"""
        metrics = self.report['model_metrics']

        # If we have actual training metrics from the model, use those
        if self.model_data and 'training_metrics' in self.model_data:
            tm = self.model_data['training_metrics']
            metrics['model_accuracy'] = round(tm.get('accuracy', 0), 3)
            metrics['aligned_precision'] = round(tm.get('aligned_precision', 0), 3)
            metrics['aligned_recall'] = round(tm.get('aligned_recall', 0), 3)
            metrics['aligned_f1'] = round(tm.get('aligned_f1', 0), 3)
            metrics['non_aligned_precision'] = round(tm.get('non_aligned_precision', 0), 3)
            metrics['non_aligned_recall'] = round(tm.get('non_aligned_recall', 0), 3)
            metrics['non_aligned_f1'] = round(tm.get('non_aligned_f1', 0), 3)
        else:
            # No model used - indicate rule-based only
            metrics['model_accuracy'] = None
            metrics['aligned_precision'] = None
            metrics['aligned_recall'] = None
            metrics['aligned_f1'] = None
            metrics['non_aligned_precision'] = None
            metrics['non_aligned_recall'] = None
            metrics['non_aligned_f1'] = None

        # Also load feature importance if available
        importance_file = Path('output/models/alignment_model.importance.json')
        if importance_file.exists():
            with open(importance_file, 'r') as f:
                metrics['feature_importance'] = json.load(f)

        # Calculate confidence statistics
        if metrics['confidence_distribution']:
            confidences = metrics['confidence_distribution']
            metrics['avg_confidence'] = round(sum(confidences) / len(confidences), 3)
            metrics['min_confidence'] = round(min(confidences), 3)
            metrics['max_confidence'] = round(max(confidences), 3)

            # Confidence buckets
            buckets = {
                'very_low': len([c for c in confidences if c < 0.3]),
                'low': len([c for c in confidences if 0.3 <= c < 0.5]),
                'medium': len([c for c in confidences if 0.5 <= c < 0.7]),
                'high': len([c for c in confidences if 0.7 <= c < 0.9]),
                'very_high': len([c for c in confidences if c >= 0.9])
            }
            metrics['confidence_buckets'] = buckets

    def save_report(self, output_path: Path):
        """Save detailed report to file"""

        # Calculate model metrics before generating report
        self._calculate_model_metrics()

        # Create markdown report
        md_report = []
        md_report.append("# First1K Translation Alignment Report")
        md_report.append(f"\nGenerated: {datetime.now().isoformat()}")
        md_report.append(f"\n## Summary")
        md_report.append(f"- Total texts processed: {self.report['summary']['total_texts']}")
        md_report.append(f"- Successfully aligned: {self.report['summary']['successful']} ({self.report['summary']['successful']/max(self.report['summary']['total_texts'],1)*100:.1f}%)")
        md_report.append(f"- Failed: {self.report['summary']['failed']} ({self.report['summary']['failed']/max(self.report['summary']['total_texts'],1)*100:.1f}%)")
        md_report.append(f"- Total runtime: {self.report['summary']['total_runtime']} seconds")

        # Model Performance Metrics
        metrics = self.report['model_metrics']
        md_report.append(f"\n## Model Training Performance")

        if metrics.get('model_accuracy') is not None:
            md_report.append(f"*Using trained RandomForest model*")
            md_report.append(f"\n### Model Test Set Performance:")
            md_report.append(f"- **Overall Accuracy**: {metrics['model_accuracy']:.1%}")
            md_report.append(f"\n#### Aligned Pairs:")
            md_report.append(f"- **Precision**: {metrics['aligned_precision']:.2f}")
            md_report.append(f"- **Recall**: {metrics['aligned_recall']:.2f}")
            md_report.append(f"- **F1-Score**: {metrics['aligned_f1']:.2f}")
            md_report.append(f"\n#### Non-Aligned Pairs:")
            md_report.append(f"- **Precision**: {metrics['non_aligned_precision']:.2f}")
            md_report.append(f"- **Recall**: {metrics['non_aligned_recall']:.2f}")
            md_report.append(f"- **F1-Score**: {metrics['non_aligned_f1']:.2f}")

            # Feature importance if available
            if metrics.get('feature_importance'):
                md_report.append(f"\n### Feature Importance:")
                sorted_features = sorted(metrics['feature_importance'].items(),
                                       key=lambda x: x[1], reverse=True)
                for feature, importance in sorted_features[:5]:
                    md_report.append(f"- **{feature}**: {importance:.1%}")
                if len(sorted_features) > 5:
                    md_report.append(f"- *Other features*: < {sorted_features[5][1]:.1%} each")
        else:
            md_report.append(f"*Using rule-based alignment only (no trained model)*")

        if metrics.get('total_alignments_attempted', 0) > 0:
            md_report.append(f"\n### Alignment Statistics")
            md_report.append(f"- Total alignments attempted: {metrics['total_alignments_attempted']}")
            md_report.append(f"- Alignments accepted: {metrics['total_alignments_accepted']}")
            md_report.append(f"- Alignments rejected: {metrics['total_alignments_rejected']}")

            if metrics.get('avg_confidence'):
                md_report.append(f"- Average confidence: {metrics['avg_confidence']:.3f}")
                md_report.append(f"- Min confidence: {metrics['min_confidence']:.3f}")
                md_report.append(f"- Max confidence: {metrics['max_confidence']:.3f}")

            if metrics.get('confidence_buckets'):
                buckets = metrics['confidence_buckets']
                md_report.append(f"\n### Confidence Distribution")
                md_report.append(f"- Very Low (< 0.3): {buckets['very_low']}")
                md_report.append(f"- Low (0.3-0.5): {buckets['low']}")
                md_report.append(f"- Medium (0.5-0.7): {buckets['medium']}")
                md_report.append(f"- High (0.7-0.9): {buckets['high']}")
                md_report.append(f"- Very High (≥ 0.9): {buckets['very_high']}")

        # Author breakdown
        md_report.append(f"\n## By Author")
        for author_id, stats in sorted(self.report['by_author'].items()):
            author_name = self.mappings['authors'].get(author_id, author_id)
            md_report.append(f"\n### {author_id} - {author_name}")
            md_report.append(f"- Total works: {stats['total']}")
            md_report.append(f"- Successful: {stats['successful']}")
            md_report.append(f"- Failed: {stats['failed']}")

            # List works
            for work in stats['works']:
                status_icon = "✅" if work['status'] == 'success' else "❌"
                work_title = self.mappings['works'].get(work['author'], {}).get(work['work'], work['work'])
                # Extract version from greek_file (e.g., "grc1" or "grc2")
                version = ""
                if 'greek_file' in work:
                    if 'grc1' in work['greek_file']:
                        version = " (grc1)"
                    elif 'grc2' in work['greek_file']:
                        version = " (grc2)"
                md_report.append(f"  - {status_icon} **{work['work']}{version}** - {work_title}: {work['status']}")
                if work['status'] == 'failed':
                    md_report.append(f"    - Reason: {work['reason']}")
                else:
                    md_report.append(f"    - Alignments: {work['stats'].get('filtered_alignments', 0)}")
                    md_report.append(f"    - Runtime: {work['runtime']}s")

        # Failed alignments details
        if self.report['failed_alignments']:
            md_report.append(f"\n## Failed Alignments Details")
            for fail in self.report['failed_alignments']:
                author_name = self.mappings['authors'].get(fail['author'], fail['author'])
                work_title = self.mappings['works'].get(fail['author'], {}).get(fail['work'], fail['work'])
                md_report.append(f"\n### {fail['author']}.{fail['work']} - {author_name}: {work_title}")
                md_report.append(f"- Greek file: {fail['greek_file']}")
                md_report.append(f"- English file: {fail['english_file']}")
                md_report.append(f"- Reason: {fail['reason']}")
                if fail.get('stats'):
                    md_report.append(f"- Greek segments: {fail['stats'].get('greek_segments', 0)}")
                    md_report.append(f"- English segments: {fail['stats'].get('english_segments', 0)}")

        # Performance statistics
        md_report.append(f"\n## Performance Statistics")
        if self.report['timing']:
            runtimes = [t['runtime'] for t in self.report['timing']]
            md_report.append(f"- Average runtime per text: {sum(runtimes)/len(runtimes):.3f}s")
            md_report.append(f"- Fastest: {min(runtimes):.3f}s")
            md_report.append(f"- Slowest: {max(runtimes):.3f}s")

        # Write markdown report
        md_path = output_path.with_suffix('.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_report))

        # Also save JSON report for programmatic access
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Report saved to {md_path} and {json_path}")

        # Print summary to console
        print("\n" + "=" * 60)
        print("First1K Alignment Complete")
        print("=" * 60)
        print(f"Successfully aligned: {self.report['summary']['successful']}")
        print(f"Failed: {self.report['summary']['failed']}")
        print(f"Total processed: {self.report['summary']['total_texts']}")
        print(f"Total runtime: {self.report['summary']['total_runtime']}s")
        print(f"Report saved to: {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Apply alignment to First1K texts with detailed reporting'
    )
    parser.add_argument('--first1k-dir', type=Path, required=True,
                       help='Directory containing First1K texts')
    parser.add_argument('--model', type=Path,
                       help='Path to trained alignment model')
    parser.add_argument('--analysis', type=Path, required=True,
                       help='First1K analysis JSON file')
    parser.add_argument('--output-dir', type=Path,
                       default=Path('output/alignments'),
                       help='Output directory for alignments')
    parser.add_argument('--report', type=Path,
                       default=Path('alignment_report'),
                       help='Output path for report (without extension)')
    parser.add_argument('--min-confidence', type=float, default=0.6,
                       help='Minimum confidence threshold')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Load analysis
    with open(args.analysis, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    # Create aligner (pass first1k_dir to generate mappings)
    aligner = First1KAligner(model_path=args.model, first1k_dir=args.first1k_dir)

    # Process texts
    aligner.process_first1k_texts(
        analysis, args.first1k_dir, args.output_dir, args.min_confidence
    )

    # Save report
    aligner.save_report(args.report)

    return 0


if __name__ == '__main__':
    sys.exit(main())