#!/usr/bin/env python3
"""Main alignment runner script - trains on Perseus and applies to First1K texts"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.train_aligner import AlignmentTrainer
from scripts.analyze_first1k import First1KAnalyzer
from scripts.apply_to_first1k_with_report import First1KAligner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_complete_alignment(perseus_dir: Path, first1k_dir: Path, 
                          output_dir: Path, min_confidence: float = 0.6,
                          skip_training: bool = False):
    """Run the complete alignment pipeline"""
    
    start_time = datetime.now()
    logger.info("Starting complete alignment pipeline")
    logger.info(f"Perseus dir: {perseus_dir}")
    logger.info(f"First1K dir: {first1k_dir}")
    logger.info(f"Output dir: {output_dir}")
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    models_dir = output_dir / 'models'
    models_dir.mkdir(exist_ok=True)
    alignments_dir = output_dir / 'alignments'
    alignments_dir.mkdir(exist_ok=True)
    
    # Step 1: Train alignment model on Perseus texts (unless skipped)
    model_path = models_dir / 'alignment_model.pkl'
    
    if not skip_training:
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Training alignment model on Perseus texts")
        logger.info("="*60)

        trainer = AlignmentTrainer()

        # Collect training data
        X, y = trainer.collect_training_data(perseus_dir)

        # Train the model
        trainer.train(X, y)

        # Save the model
        trainer.save_model(model_path)
        
        logger.info(f"Model saved to: {model_path}")
    else:
        if not model_path.exists():
            logger.error(f"Model not found at {model_path}")
            logger.error("Cannot skip training without an existing model!")
            logger.error("Either:")
            logger.error("  1. Remove --skip-training flag to train a new model")
            logger.error("  2. Run without --skip-training first to create the model")
            raise FileNotFoundError(f"Model file not found: {model_path}")
        else:
            logger.info(f"Using existing model: {model_path}")
    
    # Step 2: Analyze First1K texts
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Analyzing First1K texts")
    logger.info("="*60)

    analyzer = First1KAnalyzer()
    analysis = analyzer.analyze_directory(first1k_dir)
    
    # Save analysis
    analysis_file = output_dir / 'first1k_analysis.json'
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Analysis saved to: {analysis_file}")
    logger.info(f"Found {analysis['stats']['needs_alignment']} texts needing alignment")
    
    # Step 3: Apply alignment to First1K texts
    logger.info("\n" + "="*60)
    logger.info("STEP 3: Applying alignment to First1K texts")
    logger.info("="*60)
    
    aligner = First1KAligner(model_path=model_path, first1k_dir=first1k_dir)
    aligner.process_first1k_texts(
        analysis, first1k_dir, alignments_dir, min_confidence
    )
    
    # Step 4: Generate report
    logger.info("\n" + "="*60)
    logger.info("STEP 4: Generating alignment report")
    logger.info("="*60)
    
    report_path = output_dir / 'alignment_report'
    aligner.save_report(report_path)
    
    # Final summary
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "="*60)
    logger.info("ALIGNMENT PIPELINE COMPLETE")
    logger.info("="*60)
    logger.info(f"Total runtime: {total_time:.1f} seconds")
    logger.info(f"Successfully aligned: {aligner.report['summary']['successful']}")
    logger.info(f"Failed: {aligner.report['summary']['failed']}")
    logger.info(f"Success rate: {aligner.report['summary']['successful'] / max(aligner.report['summary']['total_texts'], 1) * 100:.1f}%")
    logger.info(f"\nOutputs:")
    logger.info(f"  - Model: {model_path}")
    logger.info(f"  - Alignments: {alignments_dir}/")
    logger.info(f"  - Report: {report_path}.md")
    logger.info(f"  - Analysis: {analysis_file}")
    
    return aligner.report


def main():
    parser = argparse.ArgumentParser(
        description='Complete Greek-English text alignment pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Run complete pipeline
  python run_alignment.py --perseus-dir ../data-sources/canonical-greekLit --first1k-dir ../data-sources/First1KGreek
  
  # Skip training and use existing model
  python run_alignment.py --perseus-dir ../data-sources/canonical-greekLit --first1k-dir ../data-sources/First1KGreek --skip-training
  
  # Use higher confidence threshold
  python run_alignment.py --perseus-dir ../data-sources/canonical-greekLit --first1k-dir ../data-sources/First1KGreek --min-confidence 0.7
        """
    )
    
    parser.add_argument('--perseus-dir', type=Path, required=True,
                       help='Directory containing Perseus Greek texts')
    parser.add_argument('--first1k-dir', type=Path, required=True,
                       help='Directory containing First1K Greek texts')
    parser.add_argument('--output-dir', type=Path, default=Path('output'),
                       help='Output directory for all results (default: output)')
    parser.add_argument('--min-confidence', type=float, default=0.6,
                       help='Minimum confidence threshold for alignments (default: 0.6)')
    parser.add_argument('--skip-training', action='store_true',
                       help='Skip training and use existing model')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Validate directories
    if not args.perseus_dir.exists():
        logger.error(f"Perseus directory not found: {args.perseus_dir}")
        return 1
    
    if not args.first1k_dir.exists():
        logger.error(f"First1K directory not found: {args.first1k_dir}")
        return 1
    
    # Run pipeline
    try:
        report = run_complete_alignment(
            args.perseus_dir, args.first1k_dir, args.output_dir,
            args.min_confidence, args.skip_training
        )
        
        return 0 if report['summary']['successful'] > 0 else 1
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())