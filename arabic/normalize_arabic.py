#!/usr/bin/env python3
"""
Arabic normalization that preserves vowels but removes other diacritics.
"""

def normalize_arabic_for_matching(text):
    """
    Normalize Arabic for matching while PRESERVING vowels.

    REMOVES (safe for matching):
    - Shadda (ّ) U+0651 - gemination mark
    - Sukun (ْ) U+0652 - no vowel mark
    - Tanween: ً U+064B, ٌ U+064C, ٍ U+064D - case endings
    - Madda (ٓ) U+0653
    - Hamza above (ٔ) U+0654
    - Hamza below (ٕ) U+0655
    - Alif khanjariyah (ٰ) U+0670
    - Other marks

    PRESERVES (semantically meaningful):
    - Fatha (َ) U+064E - "a" vowel
    - Damma (ُ) U+064F - "u" vowel
    - Kasra (ِ) U+0650 - "i" vowel
    """
    if not text:
        return ""

    # Define marks to REMOVE (but keep vowels)
    marks_to_remove = [
        '\u0651',  # ّ Shadda (gemination)
        '\u0652',  # ْ Sukun (no vowel)
        '\u064B',  # ً Tanween fathatan
        '\u064C',  # ٌ Tanween dammatan
        '\u064D',  # ٍ Tanween kasratan
        '\u0653',  # ٓ Madda
        '\u0654',  # ٔ Hamza above
        '\u0655',  # ٕ Hamza below
        '\u0670',  # ٰ Alif khanjariyah
        '\u0640',  # ـ Tatweel/kashida (elongation)
    ]

    # Remove non-vowel marks
    normalized = text
    for mark in marks_to_remove:
        normalized = normalized.replace(mark, '')

    return normalized.strip()

def test_normalization():
    """Test cases showing what gets removed and what stays"""

    test_cases = [
        ("كَتَبَ", "Keeps vowels"),
        ("كُتُب", "Keeps vowels"),
        ("كَاتِب", "Keeps vowels"),
        ("كَلِمَةٌ", "Removes tanween, keeps vowels"),
        ("مُحَمَّد", "Removes shadda, keeps vowels"),
        ("مِنْ", "Removes sukun, keeps vowels"),
        ("أسْوَدَ", "Removes sukun, keeps vowels"),
    ]

    print("Normalization Test Cases")
    print("="*60)
    for original, description in test_cases:
        normalized = normalize_arabic_for_matching(original)
        print(f"{original:15} → {normalized:15} | {description}")

    print()
    print("Preserved characters:")
    print("  َ (fatha) - 'a' vowel")
    print("  ُ (damma) - 'u' vowel")
    print("  ِ (kasra) - 'i' vowel")

    print()
    print("Removed characters:")
    print("  ّ (shadda), ْ (sukun), ً ٌ ٍ (tanween), etc.")

if __name__ == "__main__":
    test_normalization()
