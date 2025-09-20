"""Rule-based alignment for Greek-English texts"""

from typing import Dict, List, Tuple, Optional
import logging
from ..alignment.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class RuleBasedAligner:
    """Rule-based alignment using heuristics and patterns"""

    def __init__(self):
        self.feature_extractor = FeatureExtractor()

    def align_segments(self, greek_segments: List[Dict], english_segments: List[Dict],
                      strategy: str = 'auto') -> List[Dict]:
        """Align Greek and English segments using rule-based approach"""

        if strategy == 'auto':
            strategy = self._determine_strategy(greek_segments, english_segments)

        logger.info(f"Using alignment strategy: {strategy}")

        if strategy == 'direct-line':
            return self._align_direct_lines(greek_segments, english_segments)
        elif strategy == 'direct-section':
            return self._align_direct_sections(greek_segments, english_segments)
        elif strategy == 'proportional-mapping':
            return self._align_proportional(greek_segments, english_segments)
        elif strategy == 'content-similarity':
            return self._align_by_content(greek_segments, english_segments)
        else:
            return self._align_by_content(greek_segments, english_segments)

    def _determine_strategy(self, greek_segments: List[Dict], english_segments: List[Dict]) -> str:
        """Determine best alignment strategy"""

        # Check segment types
        greek_types = {s['type'] for s in greek_segments}
        english_types = {s['type'] for s in english_segments}

        # Both have lines
        if 'line' in greek_types and 'line' in english_types:
            # Check if counts are similar
            greek_lines = [s for s in greek_segments if s['type'] == 'line']
            english_lines = [s for s in english_segments if s['type'] == 'line']
            ratio = len(greek_lines) / max(len(english_lines), 1)

            if 0.8 <= ratio <= 1.2:
                return 'direct-line'

        # Both have sections
        if 'section' in greek_types and 'section' in english_types:
            # Check if section numbers match
            greek_refs = {s['ref'] for s in greek_segments if s['type'] == 'section'}
            english_refs = {s['ref'] for s in english_segments if s['type'] == 'section'}

            if len(greek_refs & english_refs) > len(greek_refs) * 0.5:
                return 'direct-section'

        # Greek has many more segments than English
        if len(greek_segments) > len(english_segments) * 2:
            return 'proportional-mapping'

        # Default to content-based
        return 'content-similarity'

    def _align_direct_lines(self, greek_segments: List[Dict], english_segments: List[Dict]) -> List[Dict]:
        """Direct line-to-line alignment"""
        alignments = []

        # Get only line segments
        greek_lines = [s for s in greek_segments if s['type'] == 'line']
        english_lines = [s for s in english_segments if s['type'] == 'line']

        # Create lookup by reference
        greek_by_ref = {s['ref']: s for s in greek_lines if s['ref']}
        english_by_ref = {s['ref']: s for s in english_lines if s['ref']}

        # First pass: match by reference
        matched_refs = set()
        for ref in greek_by_ref:
            if ref in english_by_ref:
                alignments.append({
                    'greek_ref': ref,
                    'english_ref': ref,
                    'greek_text': greek_by_ref[ref]['text'],
                    'english_text': english_by_ref[ref]['text'],
                    'confidence': 0.9,
                    'method': 'direct-ref'
                })
                matched_refs.add(ref)

        # Second pass: positional matching for unmatched
        unmatched_greek = [s for s in greek_lines if s['ref'] not in matched_refs]
        unmatched_english = [s for s in english_lines if s['ref'] not in matched_refs]

        for i, greek in enumerate(unmatched_greek):
            if i < len(unmatched_english):
                english = unmatched_english[i]
                features = self.feature_extractor.extract_features(greek['text'], english['text'])
                score = self.feature_extractor.calculate_alignment_score(features)

                if score > 0.5:
                    alignments.append({
                        'greek_ref': greek['ref'],
                        'english_ref': english['ref'],
                        'greek_text': greek['text'],
                        'english_text': english['text'],
                        'confidence': score,
                        'method': 'positional'
                    })

        return alignments

    def _align_direct_sections(self, greek_segments: List[Dict], english_segments: List[Dict]) -> List[Dict]:
        """Direct section-to-section alignment"""
        alignments = []

        # Get section segments
        greek_sections = [s for s in greek_segments if s['type'] in ['section', 'paragraph']]
        english_sections = [s for s in english_segments if s['type'] in ['section', 'paragraph']]

        # Create lookup by reference
        greek_by_ref = {s['ref']: s for s in greek_sections}
        english_by_ref = {s['ref']: s for s in english_sections}

        # Match by reference
        for ref in greek_by_ref:
            if ref in english_by_ref:
                features = self.feature_extractor.extract_features(
                    greek_by_ref[ref]['text'],
                    english_by_ref[ref]['text']
                )
                score = self.feature_extractor.calculate_alignment_score(features)

                alignments.append({
                    'greek_ref': ref,
                    'english_ref': ref,
                    'greek_text': greek_by_ref[ref]['text'],
                    'english_text': english_by_ref[ref]['text'],
                    'confidence': min(0.95, score + 0.3),  # Boost score for matching refs
                    'method': 'section-ref'
                })

        return alignments

    def _align_proportional(self, greek_segments: List[Dict], english_segments: List[Dict]) -> List[Dict]:
        """Proportional alignment for different granularities"""
        alignments = []

        # Calculate segments per English segment
        ratio = len(greek_segments) / max(len(english_segments), 1)

        for i, english in enumerate(english_segments):
            # Calculate Greek segment range
            start_idx = int(i * ratio)
            end_idx = min(int((i + 1) * ratio), len(greek_segments))

            # Combine Greek segments in range
            greek_texts = []
            greek_refs = []

            for j in range(start_idx, end_idx):
                if j < len(greek_segments):
                    greek_texts.append(greek_segments[j]['text'])
                    greek_refs.append(greek_segments[j]['ref'])

            if greek_texts:
                combined_greek = ' '.join(greek_texts)
                features = self.feature_extractor.extract_features(combined_greek, english['text'])
                score = self.feature_extractor.calculate_alignment_score(features)

                if score > 0.4:  # Lower threshold for proportional
                    alignments.append({
                        'greek_ref': f"{greek_refs[0]}-{greek_refs[-1]}" if len(greek_refs) > 1 else greek_refs[0],
                        'english_ref': english['ref'],
                        'greek_text': combined_greek,
                        'english_text': english['text'],
                        'confidence': score,
                        'method': 'proportional',
                        'greek_range': (start_idx, end_idx)
                    })

        return alignments

    def _align_by_content(self, greek_segments: List[Dict], english_segments: List[Dict]) -> List[Dict]:
        """Content-based alignment using feature similarity"""
        alignments = []

        # For each English segment, find best Greek match within a window
        for eng_idx, english in enumerate(english_segments):
            best_match = None
            best_score = 0.0
            best_greek_idx = -1

            # Calculate expected position in Greek text
            if len(english_segments) > 0:
                position_ratio = eng_idx / len(english_segments)
                expected_greek_idx = int(position_ratio * len(greek_segments))
            else:
                expected_greek_idx = 0

            # Define search window (only look at nearby segments)
            window_size = max(20, int(len(greek_segments) * 0.1))  # 10% of text or 20 segments
            start_idx = max(0, expected_greek_idx - window_size)
            end_idx = min(len(greek_segments), expected_greek_idx + window_size)

            # Only compare with segments in the window
            for i in range(start_idx, end_idx):
                greek = greek_segments[i]
                features = self.feature_extractor.extract_features(greek['text'], english['text'])
                score = self.feature_extractor.calculate_alignment_score(features)

                # Add small position penalty (prefer nearby segments)
                position_diff = abs(i - expected_greek_idx) / max(len(greek_segments), 1)
                adjusted_score = score * (1 - 0.1 * position_diff)  # 10% penalty for position difference

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_match = greek
                    best_greek_idx = i

            if best_match and best_score > 0.5:
                alignments.append({
                    'greek_ref': best_match['ref'],
                    'english_ref': english['ref'],
                    'greek_text': best_match['text'],
                    'english_text': english['text'],
                    'confidence': best_score,
                    'method': 'content-similarity'
                })

                # Mark as used to avoid re-matching
                greek_segments[best_greek_idx]['used'] = True

        return alignments

    def post_process_alignments(self, alignments: List[Dict]) -> List[Dict]:
        """Post-process alignments to ensure quality"""

        # Sort by Greek reference
        alignments = sorted(alignments, key=lambda x: self._ref_to_number(x['greek_ref']))

        # Ensure monotonicity (no backwards jumps)
        cleaned = []
        last_english_idx = -1

        for alignment in alignments:
            try:
                english_idx = self._ref_to_number(alignment['english_ref'])
                if english_idx >= last_english_idx:
                    cleaned.append(alignment)
                    last_english_idx = english_idx
                else:
                    logger.debug(f"Removing non-monotonic alignment: {alignment['greek_ref']} -> {alignment['english_ref']}")
            except:
                # Keep alignments we can't parse
                cleaned.append(alignment)

        # Merge adjacent alignments with same mapping
        merged = []
        for alignment in cleaned:
            if merged and merged[-1]['english_ref'] == alignment['english_ref']:
                # Merge Greek texts
                merged[-1]['greek_text'] += ' ' + alignment['greek_text']
                if '-' not in merged[-1]['greek_ref']:
                    merged[-1]['greek_ref'] = f"{merged[-1]['greek_ref']}-{alignment['greek_ref']}"
            else:
                merged.append(alignment)

        return merged

    def _ref_to_number(self, ref: str) -> float:
        """Convert reference to sortable number"""
        if not ref:
            return 0.0

        # Handle range references
        if '-' in ref:
            parts = ref.split('-')
            return self._ref_to_number(parts[0])

        # Try to extract number
        import re
        numbers = re.findall(r'\d+', ref)
        if numbers:
            return float(numbers[0])

        # Fallback to string comparison
        return hash(ref) % 10000