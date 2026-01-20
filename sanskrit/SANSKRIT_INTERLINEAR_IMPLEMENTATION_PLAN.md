# Sanskrit Interlinear Quality Improvement - Implementation Plan

## Current Implementation Status

### Two-Mode Morphological Analysis (Implemented)

The Sanskrit interlinear generation now works like Greek, with two modes for morphological and syntactic analysis:

#### Mode 1: DCS Treebank Data (16 works)
- **Source**: DCS CoNLL-U files with HEAD/DEPREL annotations
- **Works covered**: Ṛgveda, Atharvaveda, and 14 other Vedic texts
- **Data quality**: Full treebank with dependency parsing, morphological features
- **Coverage**: ~138K words across 16 works

#### Mode 2: Stanza NLP Fallback (254+ works)
- **Source**: Stanza NLP pipeline for Sanskrit (`stanza.Pipeline('sa')`)
- **Works covered**: All works without DCS treebank annotations (Bhagavad Gita, Mahabharata, etc.)
- **Processors**: tokenize, pos, lemma, depparse
- **Morphology coverage**: **90.1%** of words receive morphological features (Case, Gender, Number)

### Output Format
Both modes produce the same interlinear format matching Greek:
```
| lemma morph ~ POS deprel head sent_pos |
```

Example with morphology:
```
| agni acc s m ~ NOUN obj 2 1 |
```

Example without morphology (9.9% of Stanza words):
```
| word ~ VERB root 0 3 |
```

### Implementation Details

**File**: `sanskrit/generate_sanskrit_interlinear.py`

Key components:
1. **Stanza singleton initialization** (thread-safe with locks)
2. **`_enhance_line_with_stanza()`** method for NLP fallback
3. **`get_line_words()`** checks if words got tree data from DCS, falls back to Stanza if not

The fallback is triggered when:
- DCS CoNLL-U data exists for the work BUT
- No words in the line have HEAD/DEPREL values (only lexical data)

---



## Phase 2: Medium-term Improvements (1-2 days)

### 2.1 Add Basic Compound Decomposition

**Files impacted**: 3 files

#### File 1: `sanskrit/sanskrit_prefix_rules.py` (NEW FILE)

**Purpose**: Store Sanskrit prefix assimilation rules (like Greek's `prefix_assimilation_rules` table)

**Size**: ~200-300 lines

**Content**:
```python
"""
Sanskrit Prefix and Compound Analysis Rules

Based on Pāṇini's grammar and common Sanskrit word formation patterns.
"""

SANSKRIT_PREFIXES = {
    # Format: base_prefix: (transliteration, meaning, [assimilated_forms])

    # Negation prefixes
    'अ': ('a', 'not, without', ['अ', 'अन्']),  # a-/an- (before vowels)
    'नि': ('ni', 'down, in, into', ['नि', 'निर्']),

    # Directional prefixes
    'प्र': ('pra', 'forward, forth, before', ['प्र', 'प्रा']),
    'परा': ('parā', 'away, back, reverse', ['परा', 'पर']),
    'अप': ('apa', 'away, off', ['अप', 'अपा']),
    'सम्': ('sam', 'together, with, complete', ['सम्', 'सं', 'स']),
    'अनु': ('anu', 'after, along, following', ['अनु']),
    'अव': ('ava', 'down, away, off', ['अव']),
    'निस्': ('nis', 'out, forth', ['निस्', 'निर्', 'नि']),
    'दुर्': ('dur', 'bad, difficult, hard', ['दुर्', 'दुः']),
    'वि': ('vi', 'apart, asunder, away', ['वि']),
    'आ': ('ā', 'towards, near, until', ['आ']),
    'प्रति': ('prati', 'towards, against, back', ['प्रति']),
    'उप': ('upa', 'near, towards, under', ['उप']),
    'अभि': ('abhi', 'to, towards, over', ['अभि']),
    'अधि': ('adhi', 'over, above, on', ['अधि']),

    # Quality prefixes
    'सु': ('su', 'good, well, very', ['सु', 'स्व']),

    # Quantitative prefixes
    'सह': ('saha', 'with, together', ['सह']),
}

# Common compound patterns (samāsa types)
COMPOUND_PATTERNS = {
    'tatpuruṣa': 'Dependent determinative (A of B, A for B)',
    'karmadhāraya': 'Descriptive determinative (A which is B)',
    'dvandva': 'Copulative (A and B)',
    'bahuvrīhi': 'Possessive (having A)',
    'avyayībhāva': 'Adverbial (indeclinable)',
}

# Common suffixes that indicate compound boundaries
COMPOUND_SUFFIXES = [
    'त्व',  # -tva (abstract noun: "-ness")
    'ता',  # -tā (abstract noun: "-ness")
]
```

---

#### File 2: `sanskrit/sanskrit_dictionary_lookup.py`

**Lines to modify**: Add 3 new functions + modify lookup flow

**New functions** (add after `lookup_by_form`, around line 250):

```python
# NEW: Lines ~250-350 (100 lines)
def decompose_compound(self, word: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Attempt to decompose a Sanskrit compound word.

    Returns:
        Tuple of (prefix, prefix_meaning, stem, stem_lemma) or None
    """
    from sanskrit_prefix_rules import SANSKRIT_PREFIXES

    # Try each prefix (longest first for greedy matching)
    sorted_prefixes = sorted(SANSKRIT_PREFIXES.items(),
                            key=lambda x: len(x[0]),
                            reverse=True)

    for base_prefix, (trans, meaning, forms) in sorted_prefixes:
        for prefix_form in sorted(forms, key=len, reverse=True):
            if word.startswith(prefix_form):
                stem = word[len(prefix_form):]

                # Stem must be at least 3 characters
                if len(stem) >= 3:
                    # Try to find lemma for stem
                    stem_entry = self.lookup_by_form(stem)
                    if stem_entry:
                        return (base_prefix, meaning, stem, stem_entry.lemma)

    return None

def create_compound_entry(self, prefix: str, prefix_meaning: str,
                         stem: str, stem_lemma: str) -> DictionaryEntry:
    """Create a dictionary entry for a compound word."""
    # Get full definition for stem
    stem_entry = self.lookup_by_lemma(stem_lemma)

    if stem_entry:
        stem_def = stem_entry.definition
        compound_def = f"({prefix_meaning}) + {stem_lemma}\n\n{stem_def}"
    else:
        compound_def = f"({prefix_meaning}) + {stem_lemma}"

    return DictionaryEntry(
        lemma=f"{prefix}-{stem_lemma}",
        lemma_id=None,
        definition=compound_def,
        grammar=f"compound: {prefix}- + {stem_lemma}",
        source="compound analysis"
    )

# MODIFY: Lines 251-274 (lookup_best_match)
def lookup_best_match(self, word: str, lemma: Optional[str] = None) -> Optional[DictionaryEntry]:
    """Find best dictionary match, including compound decomposition."""

    # 1. Check common word priority (from Phase 1)
    if word in COMMON_WORD_PRIORITY:
        # ... priority logic

    # 2. Try lemma if provided
    if lemma:
        entry = self.lookup_by_lemma(lemma)
        if entry:
            return entry

    # 3. Try word form
    entry = self.lookup_by_form(word)
    if entry:
        return entry

    # NEW: 4. Try compound decomposition
    compound_parts = self.decompose_compound(word)
    if compound_parts:
        prefix, prefix_meaning, stem, stem_lemma = compound_parts
        return self.create_compound_entry(prefix, prefix_meaning, stem, stem_lemma)

    return None
```

**Expected additions**: ~150-200 lines

---

#### File 3: `sanskrit/generate_sanskrit_interlinear.py`

**Lines to modify**: None (benefits automatically from dictionary changes)

**Why**: The generator calls `repo.lookup_best_match()`, which now handles compounds

**Impact**: No changes needed, compound handling is transparent

---

### 2.2 Add Sandhi Resolution (Optional - More Complex)

**Files impacted**: 2 files

#### File 1: `sanskrit/sanskrit_sandhi_rules.py` (NEW FILE)

**Purpose**: Define sandhi combination and resolution rules

**Size**: ~400-500 lines (complex linguistic rules)

**Content**: Vowel sandhi, consonant sandhi, visarga sandhi rules

#### File 2: `sanskrit/sanskrit_dictionary_lookup.py`

**Modifications**: Add `resolve_sandhi()` function, integrate into lookup flow

**Expected additions**: ~100-150 lines

**Impact**: 20-30% additional improvement, but VERY complex to implement correctly

---


### Week 2: Compound Decomposition (Phase 2)
**Time**: 1-2 days
**Files**: 1 new, 1 modified
**Impact**: 30-40% improvement (cumulative: 45-65%)
**Risk**: Medium

1. Create `sanskrit_prefix_rules.py` (4 hours)
2. Add compound decomposition logic (4 hours)
3. Test with compound-heavy texts (2 hours)
4. Regenerate all interlinear (2 hours)


### Test Data:
- Rg Veda (DCS treebank)
- Bhagavad Gita (Stanza fallback, compound-heavy)
- Yoga Sutras (concise, technical)
- Mahabharata excerpt (narrative, varied)

---

