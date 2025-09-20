"""Main alignment prediction logic"""

from pathlib import Path
from typing import Dict, List, Optional
import logging
from ..xml_parser import TEIReader, StructureAnalyzer, MilestoneExtractor
from .rule_based_aligner import RuleBasedAligner
from .feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class AlignmentPredictor:
    """Predict alignments between Greek and English texts"""

    def __init__(self):
        self.tei_reader = TEIReader()
        self.structure_analyzer = StructureAnalyzer()
        self.milestone_extractor = MilestoneExtractor()
        self.aligner = RuleBasedAligner()
        self.feature_extractor = FeatureExtractor()

    def align_texts(self, greek_path: Path, english_path: Path) -> Dict:
        """Main alignment function"""

        logger.info(f"Aligning {greek_path.name} with {english_path.name}")

        # Read XML files
        greek_root = self.tei_reader.read_file(greek_path)
        english_root = self.tei_reader.read_file(english_path)

        # Extract metadata
        greek_metadata = self.tei_reader.get_metadata(greek_root)
        english_metadata = self.tei_reader.get_metadata(english_root)

        # Analyze structures
        structure_analysis = self.structure_analyzer.analyze_structure(greek_root, english_root)
        logger.info(f"Greek structure: {structure_analysis['greek']['primary_type']}")
        logger.info(f"English structure: {structure_analysis['english']['primary_type']}")
        logger.info(f"Alignment strategy: {structure_analysis['alignment_strategy']}")

        # Extract segments
        greek_segments = self.tei_reader.extract_text_segments(greek_root)
        english_segments = self.tei_reader.extract_text_segments(english_root)
        logger.info(f"Extracted {len(greek_segments)} Greek segments, {len(english_segments)} English segments")

        # Check for existing milestones
        greek_milestones = self.milestone_extractor.extract_milestones(greek_root)
        english_milestones = self.milestone_extractor.extract_milestones(english_root)

        alignments = []

        # If both have milestones, try milestone-based alignment first
        if greek_milestones and english_milestones:
            milestone_alignments = self._align_by_milestones(
                greek_milestones, english_milestones,
                greek_segments, english_segments
            )
            if milestone_alignments:
                alignments.extend(milestone_alignments)
                logger.info(f"Found {len(milestone_alignments)} milestone-based alignments")

        # Use rule-based alignment for remaining segments
        if not alignments or len(alignments) < min(len(greek_segments), len(english_segments)) * 0.5:
            rule_alignments = self.aligner.align_segments(
                greek_segments, english_segments,
                strategy=structure_analysis['alignment_strategy']
            )
            alignments.extend(rule_alignments)
            logger.info(f"Found {len(rule_alignments)} rule-based alignments")

        # Post-process alignments
        alignments = self.aligner.post_process_alignments(alignments)

        # Calculate statistics
        stats = self._calculate_statistics(alignments, greek_segments, english_segments)

        return {
            'greek_file': greek_path.name,
            'english_file': english_path.name,
            'greek_metadata': greek_metadata,
            'english_metadata': english_metadata,
            'structure_analysis': structure_analysis,
            'alignments': alignments,
            'statistics': stats
        }

    def _align_by_milestones(self, greek_milestones: List[Dict], english_milestones: List[Dict],
                            greek_segments: List[Dict], english_segments: List[Dict]) -> List[Dict]:
        """Align using milestone markers"""

        alignments = []
        aligned_milestones = self.milestone_extractor.align_milestones(greek_milestones, english_milestones)

        for greek_ms, english_ms in aligned_milestones:
            # Find text between milestones
            greek_text = self._get_text_for_milestone(greek_ms, greek_segments)
            english_text = self._get_text_for_milestone(english_ms, english_segments)

            if greek_text and english_text:
                features = self.feature_extractor.extract_features(greek_text, english_text)
                score = self.feature_extractor.calculate_alignment_score(features)

                alignments.append({
                    'greek_ref': greek_ms['n'],
                    'english_ref': english_ms['n'],
                    'greek_text': greek_text,
                    'english_text': english_text,
                    'confidence': min(0.95, score + 0.2),  # Boost for milestone match
                    'method': 'milestone',
                    'milestone_unit': greek_ms.get('unit', '')
                })

        return alignments

    def _get_text_for_milestone(self, milestone: Dict, segments: List[Dict]) -> str:
        """Get text associated with a milestone"""

        # Use following text from milestone
        if milestone.get('following_text'):
            return milestone['following_text']

        # Try to find segment at milestone position
        position = milestone.get('position', {})
        if position.get('section'):
            for segment in segments:
                if segment['ref'] == position['section']:
                    return segment['text']

        # Use surrounding text
        text = []
        if milestone.get('preceding_text'):
            text.append(milestone['preceding_text'])
        if milestone.get('following_text'):
            text.append(milestone['following_text'])

        return ' '.join(text)

    def _calculate_statistics(self, alignments: List[Dict],
                            greek_segments: List[Dict],
                            english_segments: List[Dict]) -> Dict:
        """Calculate alignment statistics"""

        if not alignments:
            return {
                'total_alignments': 0,
                'greek_coverage': 0.0,
                'english_coverage': 0.0,
                'average_confidence': 0.0
            }

        # Count aligned segments
        aligned_greek = set()
        aligned_english = set()

        for alignment in alignments:
            aligned_greek.add(alignment['greek_ref'])
            aligned_english.add(alignment['english_ref'])

        # Calculate coverage
        greek_coverage = len(aligned_greek) / max(len(greek_segments), 1)
        english_coverage = len(aligned_english) / max(len(english_segments), 1)

        # Calculate average confidence
        avg_confidence = sum(a['confidence'] for a in alignments) / len(alignments)

        # Method distribution
        method_counts = {}
        for alignment in alignments:
            method = alignment.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1

        return {
            'total_alignments': len(alignments),
            'greek_segments': len(greek_segments),
            'english_segments': len(english_segments),
            'aligned_greek': len(aligned_greek),
            'aligned_english': len(aligned_english),
            'greek_coverage': greek_coverage,
            'english_coverage': english_coverage,
            'average_confidence': avg_confidence,
            'method_distribution': method_counts
        }