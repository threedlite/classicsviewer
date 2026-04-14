"""
Translation validation module to pre-check if English files are actual translations.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from lxml import etree
import statistics

class TranslationValidator:
    """Validates whether an English file is actually a translation of the Greek text."""

    def __init__(self):
        self.min_content_ratio = 0.3  # Minimum ratio of content similarity
        self.max_length_ratio = 10.0  # Maximum ratio between Greek and English lengths
        self.min_length_ratio = 0.1   # Minimum ratio between Greek and English lengths

    def validate_translation_pair(self, greek_file: Path, english_file: Path) -> Dict:
        """
        Validate if an English file is likely a translation of the Greek file.

        Returns:
            Dict with validation results including is_valid, reasons, and scores
        """
        try:
            # Extract segments from both files
            greek_segments = self._extract_segments(greek_file)
            english_segments = self._extract_segments(english_file)

            if not greek_segments or not english_segments:
                return {
                    'is_valid': False,
                    'reason': 'Empty segments',
                    'greek_segments': len(greek_segments),
                    'english_segments': len(english_segments)
                }

            # Basic length checks
            length_ratio = len(english_segments) / len(greek_segments)
            if length_ratio > self.max_length_ratio or length_ratio < self.min_length_ratio:
                return {
                    'is_valid': False,
                    'reason': f'Length ratio too extreme: {length_ratio:.2f}',
                    'greek_segments': len(greek_segments),
                    'english_segments': len(english_segments),
                    'length_ratio': length_ratio
                }

            # Language detection
            if not self._is_likely_english(english_segments):
                return {
                    'is_valid': False,
                    'reason': 'English file does not appear to be in English',
                    'greek_segments': len(greek_segments),
                    'english_segments': len(english_segments)
                }

            # Content structure analysis
            structure_score = self._analyze_structure_similarity(greek_segments, english_segments)

            # Check for proper nouns overlap
            proper_noun_score = self._analyze_proper_noun_overlap(greek_segments, english_segments)

            # Check for numeric references overlap
            numeric_score = self._analyze_numeric_overlap(greek_segments, english_segments)

            # Overall validation score
            overall_score = (structure_score + proper_noun_score + numeric_score) / 3

            is_valid = overall_score >= self.min_content_ratio

            return {
                'is_valid': is_valid,
                'reason': f'Overall score: {overall_score:.3f}' if is_valid else f'Overall score too low: {overall_score:.3f}',
                'greek_segments': len(greek_segments),
                'english_segments': len(english_segments),
                'length_ratio': length_ratio,
                'structure_score': structure_score,
                'proper_noun_score': proper_noun_score,
                'numeric_score': numeric_score,
                'overall_score': overall_score
            }

        except Exception as e:
            return {
                'is_valid': False,
                'reason': f'Error during validation: {str(e)}',
                'greek_segments': 0,
                'english_segments': 0
            }

    def _extract_segments(self, file_path: Path) -> List[str]:
        """Extract text segments from TEI XML file."""
        try:
            parser = etree.XMLParser(no_network=True)
            with open(file_path, 'rb') as f:
                tree = etree.parse(f, parser)

            # Look for various TEI elements that contain text
            segments = []

            # Common TEI text elements
            for xpath in [
                './/tei:l',      # lines
                './/tei:p',      # paragraphs
                './/tei:ab',     # anonymous blocks
                './/tei:div[@type="section"]',  # sections
                './/tei:s'       # sentences
            ]:
                elements = tree.xpath(xpath, namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})
                for elem in elements:
                    text = self._get_element_text(elem)
                    if text and len(text.strip()) > 10:  # Minimum text length
                        segments.append(text.strip())

            return segments

        except Exception:
            return []

    def _get_element_text(self, element) -> str:
        """Extract clean text from XML element."""
        text_parts = []
        if element.text:
            text_parts.append(element.text)

        for child in element:
            if child.tag.endswith('}milestone'):
                continue  # Skip milestone elements
            if child.text:
                text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)

        return ' '.join(text_parts).strip()

    def _is_likely_english(self, segments: List[str]) -> bool:
        """Check if text segments are likely in English."""
        # Sample first 10 segments for analysis
        sample_segments = segments[:10]
        english_indicators = 0
        total_words = 0

        # Common English words and patterns
        english_words = {
            'the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as',
            'with', 'his', 'they', 'i', 'at', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'word',
            'but', 'not', 'what', 'all', 'were', 'we', 'when', 'your', 'can', 'said', 'there', 'each', 'which',
            'she', 'do', 'how', 'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them'
        }

        for segment in sample_segments:
            words = re.findall(r'\b[a-zA-Z]+\b', segment.lower())
            total_words += len(words)

            for word in words:
                if word in english_words:
                    english_indicators += 1

        if total_words == 0:
            return False

        english_ratio = english_indicators / total_words
        return english_ratio > 0.1  # At least 10% common English words

    def _analyze_structure_similarity(self, greek_segments: List[str], english_segments: List[str]) -> float:
        """Analyze structural similarity between Greek and English texts."""
        if not greek_segments or not english_segments:
            return 0.0

        # Compare length distributions
        greek_lengths = [len(seg) for seg in greek_segments]
        english_lengths = [len(seg) for seg in english_segments]

        # Calculate similarity in length patterns
        greek_avg = statistics.mean(greek_lengths) if greek_lengths else 0
        english_avg = statistics.mean(english_lengths) if english_lengths else 0

        if greek_avg == 0 or english_avg == 0:
            return 0.0

        length_similarity = min(greek_avg, english_avg) / max(greek_avg, english_avg)

        # Compare segment count similarity
        count_ratio = min(len(greek_segments), len(english_segments)) / max(len(greek_segments), len(english_segments))

        return (length_similarity + count_ratio) / 2

    def _analyze_proper_noun_overlap(self, greek_segments: List[str], english_segments: List[str]) -> float:
        """Analyze overlap of proper nouns and names."""
        # Extract potential proper nouns (capitalized words)
        greek_proper_nouns = set()
        english_proper_nouns = set()

        # Greek proper nouns (look for capitalized Greek words)
        for segment in greek_segments:
            # Look for Greek words that start with capital letters
            greek_words = re.findall(r'\b[Α-Ωα-ω][α-ωάέήίόύώ]*\b', segment)
            for word in greek_words:
                if word[0].isupper() and len(word) > 2:
                    greek_proper_nouns.add(word)

        # English proper nouns
        for segment in english_segments:
            english_words = re.findall(r'\b[A-Z][a-z]+\b', segment)
            for word in english_words:
                if len(word) > 2:
                    english_proper_nouns.add(word)

        if not greek_proper_nouns or not english_proper_nouns:
            return 0.0

        # Look for transliterated matches (simple heuristic)
        matches = 0
        transliteration_map = {
            'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Θ': 'Th',
            'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'X', 'Ο': 'O', 'Π': 'P',
            'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'Ph', 'Χ': 'Ch', 'Ψ': 'Ps', 'Ω': 'O'
        }

        for greek_noun in greek_proper_nouns:
            # Simple transliteration check
            transliterated = ''
            for char in greek_noun:
                if char in transliteration_map:
                    transliterated += transliteration_map[char]
                else:
                    transliterated += char.lower()

            # Check if any English proper noun is similar
            for english_noun in english_proper_nouns:
                if (english_noun.lower().startswith(transliterated[:3]) or
                    transliterated.startswith(english_noun.lower()[:3])):
                    matches += 1
                    break

        total_nouns = min(len(greek_proper_nouns), len(english_proper_nouns))
        return matches / total_nouns if total_nouns > 0 else 0.0

    def _analyze_numeric_overlap(self, greek_segments: List[str], english_segments: List[str]) -> float:
        """Analyze overlap of numeric references and citations."""
        # Extract numbers from both texts
        greek_numbers = set()
        english_numbers = set()

        for segment in greek_segments:
            numbers = re.findall(r'\b\d+\b', segment)
            greek_numbers.update(numbers)

        for segment in english_segments:
            numbers = re.findall(r'\b\d+\b', segment)
            english_numbers.update(numbers)

        if not greek_numbers or not english_numbers:
            return 0.0

        overlap = len(greek_numbers & english_numbers)
        total_unique = len(greek_numbers | english_numbers)

        return overlap / total_unique if total_unique > 0 else 0.0