"""
Dynamic proper name extraction and matching for Greek-English alignment.
No hard-coded names - extracts and matches names dynamically.
"""

import re
import unicodedata
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter


class ProperNameMatcher:
    """Extract and match proper names between Greek and English texts dynamically"""

    def __init__(self):
        # Enhanced transliteration map for Greek to Latin
        self.transliteration_map = {
            # Capitals
            'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z',
            'Η': 'E', 'Θ': 'Th', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M',
            'Ν': 'N', 'Ξ': 'X', 'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S',
            'Τ': 'T', 'Υ': 'Y', 'Φ': 'Ph', 'Χ': 'Ch', 'Ψ': 'Ps', 'Ω': 'O',
            # Lowercase
            'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z',
            'η': 'e', 'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm',
            'ν': 'n', 'ξ': 'x', 'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's',
            'ς': 's', 'τ': 't', 'υ': 'y', 'φ': 'ph', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
            # Common diphthongs
            'αι': 'ai', 'ει': 'ei', 'οι': 'oi', 'υι': 'yi', 'αυ': 'au',
            'ευ': 'eu', 'ου': 'ou'
        }

        # Common Latin endings that correspond to Greek endings
        self.ending_variants = {
            'us': ['os', 'ος'],
            'es': ['es', 'ης', 'ες'],
            'a': ['a', 'α', 'η'],
            'er': ['ηρ', 'ωρ'],
            'on': ['ων', 'on'],
            'is': ['ις', 'is'],
            'eus': ['ευς'],
            'ias': ['ιας'],
            'ides': ['ιδης'],
            'acles': ['ακλης'],
            'ocles': ['οκλης']
        }

    def extract_greek_proper_names(self, text: str) -> List[str]:
        """Extract likely proper names from Greek text"""
        names = []

        # Remove diacritics for easier processing
        text_no_diacritics = self._remove_diacritics(text)

        # Pattern 1: Words starting with capital Greek letters
        # Simplified pattern that captures Greek words starting with capitals
        capital_words = re.findall(r'\b[Α-Ω][\u0370-\u03ff\u1f00-\u1fff]+\b', text)
        names.extend(capital_words)

        # Pattern 2: Words that appear multiple times and might be names
        # (useful for texts where capitalization is inconsistent)
        words = re.findall(r'\b[Α-Ωα-ω]{3,}\b', text_no_diacritics)
        word_counts = Counter(words)

        # If a word appears multiple times and has certain characteristics, it might be a name
        for word, count in word_counts.items():
            if count >= 2 and len(word) >= 4:
                # Check if it has name-like endings
                if any(word.endswith(ending) for ending in ['ος', 'ης', 'ων', 'ας', 'ευς', 'ιος', 'ιδης']):
                    # Find original form with diacritics
                    pattern = self._create_diacritic_pattern(word)
                    original_forms = re.findall(pattern, text)
                    if original_forms:
                        names.extend(original_forms[:1])  # Add first occurrence

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in names:
            name_lower = self._remove_diacritics(name).lower()
            if name_lower not in seen and len(name) >= 3:
                seen.add(name_lower)
                unique_names.append(name)

        return unique_names

    def extract_english_proper_names(self, text: str) -> List[str]:
        """Extract likely proper names from English text"""
        names = []

        # Pattern 1: Capitalized words (not at sentence start)
        # Split into sentences first
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            words = sentence.split()
            # Skip first word (might be capitalized due to sentence start)
            for i, word in enumerate(words[1:], 1):
                # Remove punctuation
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word and clean_word[0].isupper() and len(clean_word) >= 3:
                    names.append(clean_word)

        # Pattern 2: Words that appear multiple times with capital letter
        capital_words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', text)
        word_counts = Counter(capital_words)

        for word, count in word_counts.items():
            if count >= 2 and word not in names:
                names.append(word)

        # Pattern 3: Words with classical name endings
        classical_patterns = re.findall(r'\b[A-Z][a-z]*(?:us|es|is|eus|ias|ides|acles|ocles)\b', text)
        for name in classical_patterns:
            if name not in names and len(name) >= 4:
                names.append(name)

        # Remove common English words that might be capitalized
        common_words = {'The', 'And', 'But', 'For', 'Nor', 'Yet', 'When', 'Where',
                       'What', 'Who', 'Which', 'That', 'This', 'These', 'Those',
                       'Then', 'Now', 'Here', 'There', 'Thus', 'Therefore'}

        return [name for name in names if name not in common_words]

    def transliterate_greek_name(self, greek_name: str) -> List[str]:
        """Transliterate Greek name to possible Latin forms"""
        # Remove diacritics for transliteration
        clean_name = self._remove_diacritics(greek_name)

        # Basic transliteration
        result = []
        current = []
        i = 0
        while i < len(clean_name):
            # Check for diphthongs first
            if i < len(clean_name) - 1:
                two_char = clean_name[i:i+2]
                if two_char in self.transliteration_map:
                    current.append(self.transliteration_map[two_char])
                    i += 2
                    continue

            # Single character
            char = clean_name[i]
            if char in self.transliteration_map:
                current.append(self.transliteration_map[char])
            else:
                current.append(char.lower())
            i += 1

        base_form = ''.join(current)
        result.append(base_form)

        # Generate variants with different endings
        for latin_ending, greek_endings in self.ending_variants.items():
            for greek_ending in greek_endings:
                if clean_name.lower().endswith(greek_ending):
                    # Find how many characters to remove from the base form
                    greek_ending_transliterated = ''
                    for char in greek_ending:
                        greek_ending_transliterated += self.transliteration_map.get(char, char)

                    if base_form.lower().endswith(greek_ending_transliterated):
                        variant = base_form[:-len(greek_ending_transliterated)] + latin_ending
                        result.append(variant)

        # Also create a capitalized version
        result.extend([r.capitalize() for r in result])

        return list(set(result))

    def match_names(self, greek_names: List[str], english_names: List[str]) -> Dict[str, List[str]]:
        """Find matches between Greek and English names"""
        matches = {}

        for greek_name in greek_names:
            possible_latin = self.transliterate_greek_name(greek_name)
            matched_english = []

            for english_name in english_names:
                english_lower = english_name.lower()

                # Check exact transliteration match
                for latin_form in possible_latin:
                    if latin_form.lower() == english_lower:
                        matched_english.append(english_name)
                        break
                    # Check partial match (for compound names or variants)
                    elif (len(latin_form) >= 4 and len(english_name) >= 4 and
                          (latin_form.lower() in english_lower or english_lower in latin_form.lower())):
                        matched_english.append(english_name)
                        break
                    # Check if they share a common root (first 3-4 characters)
                    elif (len(latin_form) >= 4 and len(english_name) >= 4 and
                          latin_form[:4].lower() == english_lower[:4]):
                        matched_english.append(english_name)
                        break

            if matched_english:
                matches[greek_name] = matched_english

        return matches

    def calculate_name_alignment_score(self, greek_text: str, english_text: str) -> float:
        """Calculate alignment score based on proper name matches"""
        greek_names = self.extract_greek_proper_names(greek_text)
        english_names = self.extract_english_proper_names(english_text)

        # Group Greek names by their stem (to handle declined forms)
        greek_stems = {}
        for name in greek_names:
            # Get stem by removing last 2-3 characters (rough approximation)
            stem = self._remove_diacritics(name)[:-2] if len(name) > 4 else self._remove_diacritics(name)
            if stem not in greek_stems:
                greek_stems[stem] = []
            greek_stems[stem].append(name)

        # Use stems for matching
        unique_greek = list(greek_stems.keys())
        greek_names = []
        for stem_names in greek_stems.values():
            greek_names.append(stem_names[0])  # Use first form of each stem

        if not greek_names and not english_names:
            # No names in either text - neutral score
            return 0.5

        if not greek_names or not english_names:
            # Names in one but not the other - low score
            return 0.1

        # Find matches
        matches = self.match_names(greek_names, english_names)

        # Calculate score based on match ratio
        total_unique_names = len(set(greek_names) | set(english_names))
        matched_names = len(matches)

        if total_unique_names == 0:
            return 0.5

        # Base score on percentage of names that have matches
        base_score = matched_names / min(len(greek_names), len(english_names))

        # Bonus for multiple occurrences of matched names
        # (indicates these are important to the text)
        bonus = 0.0
        for greek_name, english_matches in matches.items():
            greek_count = greek_text.count(greek_name)
            for english_name in english_matches:
                english_count = english_text.count(english_name)
                if greek_count >= 2 and english_count >= 2:
                    bonus += 0.1

        return min(base_score + bonus, 1.0)

    def _remove_diacritics(self, text: str) -> str:
        """Remove diacritics from Greek text"""
        # Normalize to decomposed form, then filter out diacritics
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    def _create_diacritic_pattern(self, word_no_diacritics: str) -> str:
        """Create regex pattern that matches word with any diacritics"""
        pattern = r'\b'
        for char in word_no_diacritics:
            if char in 'ΑΕΗΙΟΥΩαεηιουω':
                # These vowels can have diacritics
                pattern += f'[{char}][\\u0300-\\u036f]*'
            else:
                pattern += char
        pattern += r'\b'
        return pattern