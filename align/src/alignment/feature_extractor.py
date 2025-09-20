"""Feature extraction for alignment prediction"""

import re
from typing import Dict, List, Optional
import logging
from .proper_name_matcher import ProperNameMatcher

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract features for alignment scoring"""

    def __init__(self):
        # Use dynamic proper name matcher instead of hard-coded mappings
        self.name_matcher = ProperNameMatcher()

    def extract_features(self, greek_segment, english_segment, context: Optional[Dict] = None):
        """Extract features for alignment scoring"""

        # Handle both string and dict inputs
        if isinstance(greek_segment, dict):
            greek_text = greek_segment.get('text', '')
        else:
            greek_text = str(greek_segment)

        if isinstance(english_segment, dict):
            english_text = english_segment.get('text', '')
        else:
            english_text = str(english_segment)

        # Convert to list for compatibility with training script
        features = [
            # Length features
            self._safe_ratio(len(english_text), len(greek_text)),
            self._word_ratio(greek_text, english_text),

            # Content features
            self._proper_noun_overlap(greek_text, english_text),
            self._number_overlap(greek_text, english_text),
            self._punctuation_similarity(greek_text, english_text),

            # Structure features
            self._sentence_ratio(greek_text, english_text),
            1.0 if (self._has_dialogue(greek_text) and self._has_dialogue(english_text)) else 0.0,
            1.0 if self._starts_similarly(greek_text, english_text) else 0.0,

            # Context features (if available)
            context.get('position_diff', 0) if context else 0.0,
            1.0 if context and context.get('is_sequential', False) else 0.0,
        ]

        return features

    def _safe_ratio(self, a: float, b: float) -> float:
        """Calculate safe ratio avoiding division by zero"""
        if b == 0:
            return 0.0
        ratio = a / b
        # Normalize extreme ratios
        if ratio > 10:
            return 10.0
        if ratio < 0.1:
            return 0.1
        return ratio

    def _word_ratio(self, greek_text: str, english_text: str) -> float:
        """Calculate word count ratio"""
        greek_words = len(greek_text.split())
        english_words = len(english_text.split())
        return self._safe_ratio(english_words, greek_words)

    def _proper_noun_overlap(self, greek_text: str, english_text: str) -> float:
        """Check for matching proper nouns using dynamic extraction"""
        # Use the dynamic name matcher to calculate alignment score
        return self.name_matcher.calculate_name_alignment_score(greek_text, english_text)

    def _simple_transliterate(self, greek: str) -> str:
        """Very basic Greek to Latin transliteration for name matching"""
        # Just the most common mappings for names
        mappings = {
            'Α': 'A', 'α': 'a',
            'Β': 'B', 'β': 'b',
            'Γ': 'G', 'γ': 'g',
            'Δ': 'D', 'δ': 'd',
            'Ε': 'E', 'ε': 'e',
            'Ζ': 'Z', 'ζ': 'z',
            'Η': 'E', 'η': 'e',
            'Θ': 'Th', 'θ': 'th',
            'Ι': 'I', 'ι': 'i',
            'Κ': 'K', 'κ': 'k',
            'Λ': 'L', 'λ': 'l',
            'Μ': 'M', 'μ': 'm',
            'Ν': 'N', 'ν': 'n',
            'Ο': 'O', 'ο': 'o',
            'Π': 'P', 'π': 'p',
            'Ρ': 'R', 'ρ': 'r',
            'Σ': 'S', 'σ': 's', 'ς': 's',
            'Τ': 'T', 'τ': 't',
            'Υ': 'U', 'υ': 'u',
            'Φ': 'Ph', 'φ': 'ph',
            'Χ': 'Ch', 'χ': 'ch',
            'Ω': 'O', 'ω': 'o',
        }

        result = []
        for char in greek:
            result.append(mappings.get(char, ''))

        return ''.join(result)

    def _number_overlap(self, greek_text: str, english_text: str) -> float:
        """Check for matching numbers"""
        # Find numbers in both texts
        greek_numbers = set(re.findall(r'\d+', greek_text))
        english_numbers = set(re.findall(r'\d+', english_text))

        if not greek_numbers and not english_numbers:
            return 0.5  # Neutral if no numbers

        if not greek_numbers or not english_numbers:
            return 0.0

        overlap = len(greek_numbers & english_numbers)
        total = len(greek_numbers | english_numbers)

        return overlap / total if total > 0 else 0.0

    def _punctuation_similarity(self, greek_text: str, english_text: str) -> float:
        """Compare punctuation patterns"""
        greek_punct = len(re.findall(r'[.;!?]', greek_text))
        english_punct = len(re.findall(r'[.;!?]', english_text))

        if greek_punct == 0 and english_punct == 0:
            return 1.0

        diff = abs(greek_punct - english_punct)
        max_punct = max(greek_punct, english_punct, 1)

        return 1.0 - (diff / max_punct)

    def _sentence_ratio(self, greek_text: str, english_text: str) -> float:
        """Compare sentence counts"""
        # Simple sentence splitting
        greek_sentences = len(re.split(r'[.;!?]+', greek_text))
        english_sentences = len(re.split(r'[.;!?]+', english_text))

        return self._safe_ratio(english_sentences, greek_sentences)

    def _has_dialogue(self, text: str) -> bool:
        """Check if text appears to be dialogue"""
        # Look for patterns suggesting dialogue
        dialogue_patterns = [
            r'".*"',  # Quoted speech
            r'--',     # Dash dialogue
            r':\s*[A-ZΑ-Ω]',  # Colon followed by capital (speaker label)
        ]

        for pattern in dialogue_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _starts_similarly(self, greek_text: str, english_text: str) -> bool:
        """Check if texts start with similar content (e.g., numbers, names)"""
        # Get first word/token
        greek_start = greek_text.split()[0] if greek_text.split() else ''
        english_start = english_text.split()[0] if english_text.split() else ''

        # Check if both start with numbers
        if re.match(r'\d+', greek_start) and re.match(r'\d+', english_start):
            return greek_start == english_start

        # Use dynamic name matching instead of hard-coded mappings
        # Extract potential names from the references
        greek_names = self.name_matcher.extract_greek_proper_names(greek_start)
        english_names = self.name_matcher.extract_english_proper_names(english_start)

        if greek_names and english_names:
            matches = self.name_matcher.match_names(greek_names, english_names)
            if matches:
                return True

        return False

    def calculate_alignment_score(self, features) -> float:
        """Calculate overall alignment score from features"""

        # Handle both list and dict formats
        if isinstance(features, list):
            # Convert list to dict using feature names
            feature_names = self.get_feature_names()
            features = {name: features[i] if i < len(features) else 0.0
                       for i, name in enumerate(feature_names)}

        # Weight different features
        weights = {
            'char_ratio': 0.15,
            'word_ratio': 0.15,
            'proper_noun_overlap': 0.25,
            'number_overlap': 0.10,
            'punctuation_similarity': 0.10,
            'sentence_ratio': 0.10,
            'has_dialogue': 0.05,
            'starts_similarly': 0.10,
        }

        score = 0.0

        # Normalize ratios to 0-1 scale
        if 'char_ratio' in features:
            # Ideal ratio is around 1.5-2.0 (English usually longer)
            ratio_score = 1.0 - abs(features['char_ratio'] - 1.75) / 3.0
            score += weights['char_ratio'] * max(0, min(1, ratio_score))

        if 'word_ratio' in features:
            ratio_score = 1.0 - abs(features['word_ratio'] - 1.5) / 2.0
            score += weights['word_ratio'] * max(0, min(1, ratio_score))

        # Direct features
        for feature in ['proper_noun_overlap', 'number_overlap', 'punctuation_similarity']:
            if feature in features:
                score += weights[feature] * features[feature]

        if 'sentence_ratio' in features:
            ratio_score = 1.0 - abs(features['sentence_ratio'] - 1.0) / 2.0
            score += weights['sentence_ratio'] * max(0, min(1, ratio_score))

        # Boolean features
        if features.get('has_dialogue'):
            score += weights['has_dialogue']

        if features.get('starts_similarly'):
            score += weights['starts_similarly']

        return min(1.0, score)

    def get_feature_names(self) -> List[str]:
        """Get names of features for interpretability"""
        return [
            'char_ratio',
            'word_ratio',
            'proper_noun_overlap',
            'number_overlap',
            'punctuation_similarity',
            'sentence_ratio',
            'has_dialogue',
            'starts_similarly',
            'position_difference',
            'is_sequential'
        ]