#!/usr/bin/env python3
"""
Sanskrit Prefix Rules for Compound Decomposition

Based on Pāṇini's grammar and common Sanskrit compound patterns (samāsa).
Provides prefix definitions and assimilation rules for analyzing compound words.

License: CC BY 4.0
"""

# ============================================================================
# SANSKRIT VERBAL PREFIXES (Upasarga)
# ============================================================================
# These 20 prefixes modify verb roots and form preverbs
# Format: prefix → (transliteration, primary_meaning, [assimilated_forms])

SANSKRIT_PREFIXES = {
    # Prefix: (transliteration, meaning, [forms sorted by length])

    # Negation and privation
    'अ': ('a', 'not, without', ['अन्', 'अ']),  # a-/an- before vowels
    'अन्': ('an', 'not, without', ['अन्']),

    # Motion and direction
    'प्र': ('pra', 'forward, forth, before', ['प्र', 'प्रा']),
    'परा': ('parā', 'away, back, reverse', ['परा', 'पर']),
    'अप': ('apa', 'away, off, down', ['अप', 'अपा']),
    'सम्': ('sam', 'together, complete', ['सम्', 'सं', 'स']),
    'अनु': ('anu', 'after, along', ['अनु']),
    'अव': ('ava', 'down, away, off', ['अव']),
    'निर्': ('nir', 'out, forth, away', ['निस्', 'निर्', 'नि']),
    'निस्': ('nis', 'out, forth, away', ['निस्', 'निर्', 'नि']),
    'नि': ('ni', 'down, in, into', ['नि', 'निर्']),
    'दुर्': ('dur', 'bad, difficult', ['दुर्', 'दुस्', 'दुः']),
    'दुस्': ('dus', 'bad, difficult', ['दुस्', 'दुर्', 'दुः']),
    'वि': ('vi', 'apart, asunder', ['वि']),
    'आ': ('ā', 'towards, near, unto', ['आ']),
    'प्रति': ('prati', 'towards, back, against', ['प्रति']),
    'उप': ('upa', 'near, towards, under', ['उप']),
    'अभि': ('abhi', 'to, towards, over', ['अभि']),
    'अधि': ('adhi', 'over, above, concerning', ['अधि']),
    'उत्': ('ut', 'up, out, upwards', ['उद्', 'उत्', 'उ']),
    'उद्': ('ud', 'up, out, upwards', ['उद्', 'उत्', 'उ']),

    # Quality and manner
    'सु': ('su', 'good, well, very', ['सु', 'स्व']),
    'स्व': ('sva', 'good, well, own', ['स्व', 'सु']),

    # Association
    'सह': ('saha', 'with, together', ['सह', 'स']),
}

# ============================================================================
# COMMON COMPOUND STEMS
# ============================================================================
# Common elements that appear in compounds but might not be in dictionary

COMMON_COMPOUND_STEMS = {
    # Body parts
    'हस्त': 'hand',
    'पाद': 'foot',
    'शिर': 'head',
    'मुख': 'face, mouth',
    'नेत्र': 'eye',
    'कर्ण': 'ear',

    # Elements and nature
    'अग्नि': 'fire',
    'वायु': 'wind, air',
    'जल': 'water',
    'पृथिवी': 'earth',
    'आकाश': 'sky, space',
    'सूर्य': 'sun',
    'चन्द्र': 'moon',

    # Abstract concepts
    'धर्म': 'duty, righteousness',
    'कर्म': 'action, deed',
    'ज्ञान': 'knowledge',
    'भक्ति': 'devotion',
    'योग': 'union, discipline',
    'शक्ति': 'power, energy',
    'सत्य': 'truth',

    # Common adjectives
    'महा': 'great',
    'उच्च': 'high',
    'नीच': 'low',
    'पूर्ण': 'full',
    'शून्य': 'empty, zero',
}

# ============================================================================
# COMPOUND TYPES (Samāsa)
# ============================================================================
# For reference - different types of Sanskrit compounds

COMPOUND_TYPES = {
    'avyayībhāva': {
        'description': 'Adverbial compound (indeclinable)',
        'example': 'यथाशक्ति (yathā-śakti) = according to power',
        'pattern': 'prefix + noun → adverb'
    },
    'tatpuruṣa': {
        'description': 'Dependent determinative',
        'example': 'राजपुरुष (rāja-puruṣa) = king\'s man',
        'pattern': 'A of/for/by B'
    },
    'karmadhāraya': {
        'description': 'Descriptive determinative',
        'example': 'नीलोत्पल (nīla-utpala) = blue lotus',
        'pattern': 'adjective + noun'
    },
    'dvigu': {
        'description': 'Numerical compound',
        'example': 'त्रिलोक (tri-loka) = three worlds',
        'pattern': 'number + noun'
    },
    'dvandva': {
        'description': 'Copulative compound',
        'example': 'रामकृष्ण (rāma-kṛṣṇa) = Rama and Krishna',
        'pattern': 'A and B'
    },
    'bahuvrīhi': {
        'description': 'Possessive compound',
        'example': 'चतुर्भुज (catur-bhuja) = four-armed (one who has)',
        'pattern': 'having/characterized by'
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_prefix_forms():
    """
    Get all prefix forms sorted by length (longest first).

    Returns:
        List of tuples: (prefix_form, base_prefix, meaning)
    """
    all_forms = []
    for base_prefix, (trans, meaning, forms) in SANSKRIT_PREFIXES.items():
        for form in forms:
            all_forms.append((form, base_prefix, meaning))

    # Sort by length (longest first) for greedy matching
    all_forms.sort(key=lambda x: len(x[0]), reverse=True)
    return all_forms


def is_likely_compound(word: str, word_length_threshold: int = 8) -> bool:
    """
    Heuristic to determine if a word is likely a compound.

    Args:
        word: Sanskrit word in Devanagari
        word_length_threshold: Minimum length to consider compound (default 8)

    Returns:
        True if word is likely a compound
    """
    # Compounds are typically longer
    if len(word) < word_length_threshold:
        return False

    # Check if starts with known prefix
    for prefix_form, _, _ in get_all_prefix_forms():
        if word.startswith(prefix_form) and len(word) > len(prefix_form) + 2:
            return True

    return False
