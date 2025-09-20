#!/usr/bin/env python3
"""Train alignment model on Perseus Greek-English text pairs"""

import sys
import pickle
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.xml_parser import TEIReader, StructureAnalyzer
from src.alignment import FeatureExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlignmentTrainer:
    """Train a statistical alignment model on Perseus data"""

    def __init__(self, model_type='random_forest'):
        self.model_type = model_type
        self.feature_extractor = FeatureExtractor()
        self.tei_reader = TEIReader()
        self.structure_analyzer = StructureAnalyzer()
        self.model = None

    def extract_training_pairs(self, greek_file: Path, english_file: Path) -> List[Dict]:
        """Extract aligned pairs from Perseus texts"""

        logger.info(f"Processing {greek_file.name} and {english_file.name}")

        # Parse XML files
        greek_doc = self.tei_reader.parse_file(greek_file)
        english_doc = self.tei_reader.parse_file(english_file)

        if not greek_doc or not english_doc:
            logger.warning(f"Could not parse files: {greek_file.name}, {english_file.name}")
            return []

        # Extract segments
        greek_segments = self.tei_reader.extract_segments(greek_doc)
        english_segments = self.tei_reader.extract_segments(english_doc)

        if not greek_segments or not english_segments:
            logger.warning(f"No segments found in files")
            return []

        # Analyze structure to determine alignment strategy
        structure_analysis = self.structure_analyzer.analyze_structure(greek_doc, english_doc)
        alignment_strategy = structure_analysis.get('alignment_strategy', 'content-similarity'
        )

        training_pairs = []

        # Generate positive examples (actual alignments)
        if alignment_strategy == 'direct-line':
            # Line-by-line alignment (poetry)
            for i, (greek_seg, english_seg) in enumerate(zip(greek_segments, english_segments)):
                if greek_seg.get('ref') == english_seg.get('ref'):
                    features = self.feature_extractor.extract_features(
                        greek_seg, english_seg,
                        {'position': i, 'total': len(greek_segments)}
                    )
                    training_pairs.append({
                        'features': features,
                        'label': 1,
                        'confidence': 0.95
                    })

        elif alignment_strategy == 'direct-section':
            # Section-by-section alignment (prose)
            greek_by_ref = {seg['ref']: seg for seg in greek_segments if seg.get('ref')}
            english_by_ref = {seg['ref']: seg for seg in english_segments if seg.get('ref')}

            for ref in set(greek_by_ref.keys()) & set(english_by_ref.keys()):
                features = self.feature_extractor.extract_features(
                    greek_by_ref[ref], english_by_ref[ref],
                    {'strategy': 'section'}
                )
                training_pairs.append({
                    'features': features,
                    'label': 1,
                    'confidence': 0.9
                })

        elif alignment_strategy == 'proportional':
            # Proportional mapping (different granularities)
            ratio = len(greek_segments) / len(english_segments)

            for eng_idx, english_seg in enumerate(english_segments):
                greek_start = int(eng_idx * ratio)
                greek_end = min(int((eng_idx + 1) * ratio), len(greek_segments))

                for greek_idx in range(greek_start, greek_end):
                    if greek_idx < len(greek_segments):
                        features = self.feature_extractor.extract_features(
                            greek_segments[greek_idx], english_seg,
                            {'method': 'proportional', 'ratio': ratio}
                        )
                        training_pairs.append({
                            'features': features,
                            'label': 1,
                            'confidence': 0.7
                        })

        # Generate negative examples (non-alignments)
        # Sample random misaligned pairs
        num_negatives = min(len(training_pairs), 100)  # Limit negatives

        for _ in range(num_negatives):
            greek_idx = np.random.randint(0, len(greek_segments))
            english_idx = np.random.randint(0, len(english_segments))

            # Make sure this isn't actually aligned
            if alignment_strategy == 'proportional':
                ratio = len(greek_segments) / len(english_segments)
                expected_eng = int(greek_idx / ratio)
                if abs(english_idx - expected_eng) < 2:
                    continue  # Too close to actual alignment

            features = self.feature_extractor.extract_features(
                greek_segments[greek_idx],
                english_segments[english_idx],
                {'negative': True}
            )
            training_pairs.append({
                'features': features,
                'label': 0,
                'confidence': 0.0
            })

        logger.info(f"Extracted {len(training_pairs)} training pairs "
                   f"({sum(1 for p in training_pairs if p['label'] == 1)} positive, "
                   f"{sum(1 for p in training_pairs if p['label'] == 0)} negative)")

        return training_pairs

    def collect_training_data(self, perseus_dir: Path) -> Tuple[np.ndarray, np.ndarray]:
        """Collect training data from all Perseus texts"""

        all_pairs = []

        # Find Greek-English pairs
        for greek_file in perseus_dir.glob('**/*-grc*.xml'):
            # Find corresponding English file
            base_name = greek_file.stem.replace('-grc1', '').replace('-grc2', '').replace('-grc', '')
            english_patterns = [
                f"{base_name}-eng*.xml",
                f"{base_name}.perseus-eng*.xml"
            ]

            english_file = None
            for pattern in english_patterns:
                english_files = list(greek_file.parent.glob(pattern))
                if english_files:
                    english_file = english_files[0]
                    break

            if english_file:
                pairs = self.extract_training_pairs(greek_file, english_file)
                all_pairs.extend(pairs)

        if not all_pairs:
            raise ValueError("No training pairs found")

        # Convert to feature matrix
        X = np.array([p['features'] for p in all_pairs])
        y = np.array([p['label'] for p in all_pairs])

        logger.info(f"Collected {len(X)} total training examples")
        logger.info(f"Class distribution: {np.bincount(y)}")

        return X, y

    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the alignment model"""

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(f"Training on {len(X_train)} examples, testing on {len(X_test)}")

        # Create model
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
        elif self.model_type == 'logistic':
            self.model = LogisticRegression(max_iter=1000, random_state=42)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

        # Train
        logger.info(f"Training {self.model_type} model...")
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)

        logger.info("\nClassification Report:")
        report = classification_report(y_test, y_pred,
                                      target_names=['Non-aligned', 'Aligned'],
                                      output_dict=True)
        print(classification_report(y_test, y_pred,
                                   target_names=['Non-aligned', 'Aligned']))

        logger.info("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(cm)

        # Store metrics for later use
        self.training_metrics = {
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'accuracy': report['accuracy'],
            'non_aligned_precision': report['Non-aligned']['precision'],
            'non_aligned_recall': report['Non-aligned']['recall'],
            'non_aligned_f1': report['Non-aligned']['f1-score'],
            'aligned_precision': report['Aligned']['precision'],
            'aligned_recall': report['Aligned']['recall'],
            'aligned_f1': report['Aligned']['f1-score']
        }

        # Feature importance (for Random Forest)
        if self.model_type == 'random_forest':
            feature_names = self.feature_extractor.get_feature_names()
            importances = self.model.feature_importances_

            logger.info("\nTop 10 Most Important Features:")
            feature_importance = sorted(zip(feature_names, importances),
                                      key=lambda x: x[1], reverse=True)
            for name, importance in feature_importance[:10]:
                print(f"  {name}: {importance:.4f}")

    def save_model(self, output_path: Path):
        """Save the trained model"""

        if not self.model:
            raise ValueError("No model trained yet")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'feature_names': self.feature_extractor.get_feature_names(),
            'training_metrics': getattr(self, 'training_metrics', {}),
            'version': '1.0'
        }

        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {output_path}")

        # Also save feature importance as JSON for inspection
        if self.model_type == 'random_forest':
            importance_file = output_path.with_suffix('.importance.json')
            feature_names = self.feature_extractor.get_feature_names()
            importances = self.model.feature_importances_

            importance_data = {
                name: float(imp)
                for name, imp in zip(feature_names, importances)
            }

            with open(importance_file, 'w') as f:
                json.dump(importance_data, f, indent=2)

            logger.info(f"Feature importance saved to {importance_file}")


def main():
    parser = argparse.ArgumentParser(description='Train alignment model on Perseus texts')
    parser.add_argument('--perseus-dir', type=Path, required=True,
                       help='Directory containing Perseus Greek-English texts')
    # Default to output/models directory relative to project root
    default_output = Path(__file__).parent.parent / 'output' / 'models' / 'alignment_model.pkl'
    parser.add_argument('--output', type=Path, default=default_output,
                       help='Output path for trained model (default: output/models/alignment_model.pkl)')
    parser.add_argument('--model-type', choices=['random_forest', 'logistic'],
                       default='random_forest', help='Type of model to train')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Check input directory
    if not args.perseus_dir.exists():
        logger.error(f"Perseus directory not found: {args.perseus_dir}")
        return 1

    # Train model
    trainer = AlignmentTrainer(model_type=args.model_type)

    try:
        # Collect training data
        X, y = trainer.collect_training_data(args.perseus_dir)

        # Train
        trainer.train(X, y)

        # Save
        trainer.save_model(args.output)

        logger.info("\nTraining complete!")
        return 0

    except Exception as e:
        logger.error(f"Training failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())