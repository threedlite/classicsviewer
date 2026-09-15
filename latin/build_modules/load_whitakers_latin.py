#!/usr/bin/env python3
"""
Load Whitaker's Words Latin dictionary and morphology into the Perseus database.
This integrates Latin definitions and inflections directly into the main dictionary.
"""

import os
import re
import itertools
from functools import cmp_to_key
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Whitaker's DICTLINE.GEN gives four principal-part stem columns per entry and
# writes "zzz" where a principal part DOES NOT EXIST. It is a null marker, not
# a stem: 2,170 of the 39,338 entries carry it.
#
# Treating it as real did two things, both visible to readers:
#
#  1. Forms were generated as "zzz" + ending, minting nonsense word_forms.
#  2. In 23 entries "zzz" occupies the FIRST column, and the loader took
#     lemma = stems[0] - so 23 unrelated defective words all collapsed onto the
#     single junk lemma "zzz", which ended up with 1,349 lemma_map rows and 23
#     dictionary entries. Those 23 are exactly the words whose first principal
#     part is suppletive:
#
#         zzz  Ad        N   -> Adam
#         zzz  mult      N   -> multa, "a fine"
#         zzz  deterius  ADV -> deterius, comparative with no positive
#
#     The interlinear then resolved that pile arbitrarily, so Aeneid 1.3's
#     "multum" was glossed "much, fine, Adam". 1,575 segments carried an
#     ", Adam" tail this way.
#
# Positions must be PRESERVED, not compacted: inflection patterns index stems by
# stem_pos, so dropping an element would silently shift every later stem. NULL
# them in place instead - the existing `if not stem_to_use: continue` then skips
# exactly the principal parts that do not exist.
_WHITAKER_NULL_STEM = "zzz"


_STEM_COLUMNS = ((0, 19), (19, 38), (38, 57), (57, 76))


def _parse_stem_columns(stem_block):
    """Stems by COLUMN, so an empty one keeps its position.

    `_parse_stems` splits on whitespace, which drops an empty column and
    shifts every later stem one place left. That is correct for all 39,338
    DICTLINE rows -- none has an interior blank, they use "zzz" -- but wrong
    for Whitaker's ESSE entry, whose SECOND principal part is deliberately
    blank. A zero-length stem is what generates es, est, eram, erat, ero,
    esse. Shifted, its `fu` and `fut` landed in positions 2 and 3 and
    generated fuest, fuesse, futisse, futeram.

    An interior blank is therefore a real zero-length stem; a trailing blank
    is an unused column, as in every two-stem noun. Verified against
    DICTLINE.GEN: 0 rows of 39,338 have an interior blank, so this changes
    nothing that the file already contains.
    """
    raw = [stem_block[a:b].strip() if len(stem_block) > a else ""
           for a, b in _STEM_COLUMNS]
    last_real = max((i for i, x in enumerate(raw) if x), default=-1)
    stems = []
    for i, x in enumerate(raw):
        if i > last_real:
            continue                     # trailing, unused
        stems.append(None if x == _WHITAKER_NULL_STEM else x)
    lemma = next((x for x in stems if x), None)
    return stems, lemma


def _parse_stems(stems_part):
    """Stem columns with Whitaker's "zzz" null marker replaced by None.

    Returns (stems, lemma). `lemma` is the first REAL stem, so a defective word
    whose first principal part is absent is keyed on its own next stem rather
    than on the shared "zzz" bucket. Returns (stems, None) if no stem is real.
    """
    stems = [None if s == _WHITAKER_NULL_STEM else s
             for s in stems_part.split() if s]
    lemma = next((s for s in stems if s), None)
    return stems, lemma


# ---------------------------------------------------------------------------
# Citation-form keying
# ---------------------------------------------------------------------------
# Whitaker keys its data on STEMS ("mult", "ed", "qu", "sit"), not on the
# dictionary form a reader would look up. Storing stems in
# dictionary_entries.headword makes the Latin lookup structurally wrong in three
# ways, all measured:
#
#  * A surface that coincides with a stem gets a step-1 exact match and
#    short-circuits lemma resolution. 30.1% of Latin corpus tokens have a
#    surface equal to some stem. "tibi" hits the stem of tibia -> "flute, pipe".
#  * One stem serves unrelated words. "mult" covers multus / multa / multo, so
#    the dual-gloss printed "much, fine, punish"; "ed" covers both edo verbs.
#  * Treebank lemmas and Lewis & Short headwords are dictionary FORMS, so they
#    cannot join to stems. "est" has the correct lemma "sum" recorded in the
#    interlinear yet glosses as "eject/emit", because the gloss is resolved from
#    the surface and "sum" as a Whitaker headword is the stem of sumo.
#
# The citation form is recoverable from the paradigm we already generate:
# a verb's is its 1st person singular present active indicative, a nominal's is
# its nominative singular. Measured over the built DB, 29,371 of 29,562 stems
# (99.4%) yield one; the 191 that do not are indeclinables and abbreviations
# (A, Abba, Adonai, Baal) which already ARE their own citation form.
#
# Keying on it aligns Whitaker with the treebank and with L&S:
#     sum(stem) -> sumo      frees the string "sum" for L&S's "to be"
#     mult      -> multus / multa / multo   as separate entries
#     ed        -> edo
# It must be computed PER ENTRY, not per stem: a stem serves several entries
# with different parts of speech, and a per-stem map picks the wrong one
# (mult -> multo rather than multus, tu -> tuo rather than tu).
_CIT_VERB = "1 s pres active ind"


# Whitaker's noun genders, as written in the DICTLINE POS columns.
_NOUN_GENDERS = ("m", "f", "n", "c")


def _citation_form(morph_entries, fallback, gender=None):
    """Dictionary form for an entry, from the paradigm it just generated.

    `gender` is the entry's DECLARED gender, and it matters. The noun block
    filters inflection patterns by declension but not by gender, so a
    2nd-declension NEUTER noun generates both the masculine "-us" and the
    neuter "-um" nominative. Taking whichever came first filed *bellum* "war"
    under the headword "bellus" (which is the adjective "pretty"), *aurum*
    under "aurus", *vitium* under "vitius", *praesidium* under "praesidius".

    Two things went wrong downstream. The headword the reader would look up did
    not exist, so `bellum` fell back to a placeholder; and
    select_entry_for_pos() separates same-POS candidates by testing whether the
    lemma starts with a candidate's stem, which "bellum" vs "bellus" fails, so
    it declined and the wrong gloss stood. `bello` glossed as "fight, wage war"
    for 1,815 tokens because of this.

    Preferring the nominative singular that MATCHES the declared gender fixes
    the key at source. Verbs are unaffected: they have no gender and still take
    the first-person present indicative.
    """
    verb = nominal = gendered = None
    g = (gender or "").strip().lower()
    want = f"nom s {g}" if g in _NOUN_GENDERS else None
    for m in morph_entries:
        mi = (m.get('morph_info') or '')
        if verb is None and mi == _CIT_VERB:
            verb = m['word_form']
        if want and gendered is None and mi.startswith(want):
            gendered = m['word_form']
        if nominal is None and 'nom s' in mi:
            nominal = m['word_form']
    return verb or gendered or nominal or fallback


class LatinInflectionEngine:
    """Latin inflection engine based on Whitaker's Words INFLECTS.LAT"""
    
    def __init__(self):
        self.inflection_patterns = []
    
    def parse_inflects(self, file_path: str):
        """Parse INFLECTS.LAT for inflection patterns"""
        if not os.path.exists(file_path):
            # HARD FAIL. Without INFLECTS.LAT there are no inflection patterns,
            # so lemma_map is built from headwords alone and every inflected
            # surface form in the corpus stops resolving. The build would still
            # exit 0 with a plausible-looking DB. CLAUDE.md: fail the build for
            # anything missing, never warn and continue.
            raise FileNotFoundError(
                f"Whitaker's INFLECTS.LAT not found at {file_path}. "
                f"Latin inflection patterns cannot be built without it. "
                f"Clone the source: cd data-sources && "
                f"git clone https://github.com/mk270/whitakers-words.git"
            )
        
        print("Loading Latin inflection patterns...")
        pattern_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                if not line or line.startswith('--'):
                    continue
                
                parts = line.split()
                
                if parts[0] == 'V' and len(parts) >= 11:
                    # Parse verb inflections
                    pattern = {
                        'pos': 'V',
                        'conjugation': int(parts[1]),
                        'variant': int(parts[2]),
                        'tense': parts[3],
                        'voice': parts[4],
                        'mood': parts[5],
                        'person': parts[6],
                        'number': parts[7],
                        'stem_pos': int(parts[8]),
                        'ending_len': int(parts[9]),
                        'ending': parts[10] if len(parts) > 10 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'VPAR' and len(parts) >= 11:
                    # Parse verb participle inflections
                    pattern = {
                        'pos': 'VPAR',
                        'conjugation': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'tense': parts[6],
                        'voice': parts[7],
                        'mood': parts[8],
                        'stem_pos': int(parts[9]),
                        'ending_len': int(parts[10]),
                        'ending': parts[11] if len(parts) > 11 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'N' and len(parts) >= 9:
                    # Parse noun inflections
                    pattern = {
                        'pos': parts[0],
                        'declension': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'stem_pos': int(parts[6]),
                        'ending_len': int(parts[7]),
                        'ending': parts[8] if len(parts) > 8 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'ADJ' and len(parts) >= 10:
                    # Parse adjective inflections
                    pattern = {
                        'pos': parts[0],
                        'declension': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'degree': parts[6],  # POS/COMP/SUPER
                        'stem_pos': int(parts[7]),
                        'ending_len': int(parts[8]),
                        'ending': parts[9] if len(parts) > 9 else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1
                elif parts[0] == 'ADV' and len(parts) >= 4:
                    # Format: ADV degree stem_pos ending_len [ending] age freq
                    #
                    # Whitaker stores an adverb's three degrees as three STEMS,
                    # not as endings:
                    #
                    #     bene       melius       optime          ADV X
                    #     generose   generosius   generosissime   ADV X
                    #
                    # and the patterns emit each stem with a zero-length ending
                    # (ADV X 1 0 / 2 0 / 3 0). An entry declared with a single
                    # degree (ADV POS, as `stulte` is) has only stem 1.
                    #
                    # The parser handled V, VPAR, N, ADJ and PRON but never ADV,
                    # so adverbs generated NO morphology at all and every
                    # comparative and superlative stem was dropped. 387 of the
                    # 2,204 ADV entries carry one.
                    pattern = {
                        'pos': 'ADV',
                        'declension': 0,
                        'variant': 0,
                        'degree': parts[1],
                        'stem_pos': int(parts[2]),
                        'ending_len': int(parts[3]),
                        'ending': parts[4] if len(parts) > 4 and parts[4].isalpha() else ''
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1

                elif parts[0] == 'PRON' and len(parts) >= 8:
                    # Parse pronoun inflections
                    # Format: PRON decl variant case number gender stem_pos ending_len [ending] age freq
                    # Note: if ending_len is 0, there's no ending token - parts[8] is age instead
                    ending_len = int(parts[7])
                    if ending_len > 0 and len(parts) > 8:
                        ending = parts[8]
                    else:
                        ending = ''
                    pattern = {
                        'pos': 'PRON',
                        'declension': int(parts[1]),
                        'variant': int(parts[2]),
                        'case': parts[3],
                        'number': parts[4],
                        'gender': parts[5],
                        'stem_pos': int(parts[6]),
                        'ending_len': ending_len,
                        'ending': ending
                    }
                    self.inflection_patterns.append(pattern)
                    pattern_count += 1

        # Whitaker writes "X" in the ending column to mean ZERO ENDING - the
        # form is the bare stem. The loader concatenated it literally, so every
        # such pattern minted a word_form like "visX" / "osX" / "abacX";
        # 26,048 of them are sitting in the shipped lemma_map. Harmless while
        # lemmas were stems, but citation-form keying surfaces them as lemmas.
        #
        # Normalised once here rather than at each of the five append sites.
        # NOT done by stripping a trailing "X" from finished forms: 33,701 real
        # Latin corpus tokens end in capital X (Roman numerals).
        zeroed = 0
        for pattern in self.inflection_patterns:
            if pattern.get('ending') == 'X':
                pattern['ending'] = ''
                zeroed += 1
        if zeroed:
            print(f"  Normalised {zeroed} zero-ending ('X') inflection patterns")

        print(f"Loaded {pattern_count} inflection patterns")
    
    def generate_morphology_for_dictionary(self, dictionary_line: str) -> List[Dict]:
        """Generate morphology entries from a DICTLINE.GEN entry"""
        if len(dictionary_line) < 100:
            return []

        stems_part = dictionary_line[0:76].strip()
        pos_part = dictionary_line[76:88].strip() if len(dictionary_line) > 76 else None

        if not pos_part:
            return []

        # Extract frequency code from flags section (position 83-110)
        # Format: "2 1 M P          X X X A O" - frequency is second from end
        # Whitaker's codes: A=very frequent, B=frequent, C=common, D=lesser, E=uncommon, F=very rare, X=unknown
        # Map to confidence: higher frequency = higher confidence for better sorting
        freq_confidence_map = {'A': 0.95, 'B': 0.90, 'C': 0.85, 'D': 0.80, 'E': 0.75, 'F': 0.70, 'X': 0.65}
        flags_part = dictionary_line[83:110] if len(dictionary_line) > 110 else ""
        flags_tokens = flags_part.split()
        freq_code = flags_tokens[-2] if len(flags_tokens) >= 2 else 'X'
        confidence = freq_confidence_map.get(freq_code, 0.65)

        morphology_entries = []
        # Bound before the POS dispatch: a part of speech with no block below
        # still reaches the citation-form rewrite at the end.
        entry_lemma = None
        pos_info = pos_part.split()
        
        if pos_info[0] == 'V':
            # Verb: V conj variant
            conjugation = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            variant = int(pos_info[2]) if len(pos_info) > 2 and pos_info[2].isdigit() else 0
            
            # Extract stems. By COLUMN, not by split: the ESSE entry's second
            # principal part is an intentional zero-length stem.
            stems, entry_lemma = _parse_stem_columns(dictionary_line[0:76])
            if entry_lemma:
                # Generate verb forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'V':
                        continue
                    if pattern['conjugation'] != conjugation and pattern['conjugation'] != 0:
                        continue
                    # Same keying, on (conjugation, variant).
                    if (pattern['variant'] != 0 and variant != 0
                            and pattern['variant'] != variant):
                        continue
                    
                    # Apply the ending to the appropriate stem
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern['stem_pos'] - 1 < len(stems) else None
                    
                    # `is None`, not falsy: an empty string is a real
                    # ZERO-LENGTH stem (Whitaker's ESSE second principal
                    # part), and it is what generates es, est, eram, ero,
                    # esse. `None` is a suppressed principal part ("zzz")
                    # and still skips.
                    if stem_to_use is None:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string
                    morph_info = []
                    if pattern['person'] != 'X':
                        morph_info.append(pattern['person'])
                    if pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern['tense']:
                        morph_info.append(pattern['tense'].lower())
                    if pattern['voice']:
                        morph_info.append(pattern['voice'].lower())
                    if pattern['mood']:
                        morph_info.append(pattern['mood'].lower())
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': entry_lemma,
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })
                
                # Also generate participle forms (VPAR) for verbs
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'VPAR':
                        continue
                    if pattern['conjugation'] != conjugation and pattern['conjugation'] != 0:
                        continue
                    # Same keying, on (conjugation, variant).
                    if (pattern['variant'] != 0 and variant != 0
                            and pattern['variant'] != variant):
                        continue
                    
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern['stem_pos'] - 1 < len(stems) else None
                    
                    # `is None`, not falsy: an empty string is a real
                    # ZERO-LENGTH stem (Whitaker's ESSE second principal
                    # part), and it is what generates es, est, eram, ero,
                    # esse. `None` is a suppressed principal part ("zzz")
                    # and still skips.
                    if stem_to_use is None:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string for participles
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    if pattern.get('tense'):
                        morph_info.append(pattern['tense'].lower())
                    if pattern.get('voice'):
                        morph_info.append(pattern['voice'].lower())
                    morph_info.append("part")  # Mark as participle
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': entry_lemma,
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })
        
        elif pos_info[0] == 'N':
            # Noun: N decl variant gender
            declension = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            variant = int(pos_info[2]) if len(pos_info) > 2 and pos_info[2].isdigit() else 0
            
            stems, entry_lemma = _parse_stems(stems_part)
            if entry_lemma:
                # Generate noun forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'N':
                        continue
                    if pattern['declension'] != declension and pattern['declension'] != 0:
                        continue
                    # Whitaker keys inflection patterns on (declension,
                    # VARIANT), and the variant is what distinguishes words
                    # with identical stems. Declension 2 has ten variants with
                    # ten different nominative endings:
                    #
                    #   N 2 1 NOM S      us     dominus
                    #   N 2 2 NOM S N    um     bellum
                    #   N 2 3 NOM S      <none> vir, puer  (nominative = stem)
                    #
                    # Filtering on declension alone generated every variant's
                    # endings for every entry, so DICTLINE's three "vir vir"
                    # nouns -- N 2 1 N "venom", N 2 2 N "virus", N 2 3 M "man"
                    # -- each produced the whole set and the citation-form
                    # picker had to guess between them. It guessed backwards:
                    # "man" was filed under the headword `virus` and "venom"
                    # under `virum`, so *viri* glossed as "venom" for ~2,000
                    # tokens. The same gap filed *bellum* under `bellus`.
                    #
                    # It also polluted lemma_map with forms that do not exist,
                    # since a variant-3 noun was given variant-1 endings.
                    #
                    # Variant 0 means "applies to every variant", so it is
                    # always kept. Idiom copied from the PRON block below,
                    # which has always filtered this way. Verified against the
                    # source files: no DICTLINE entry loses all its patterns.
                    if (pattern['variant'] != 0 and variant != 0
                            and pattern['variant'] != variant):
                        continue
                    
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern.get('stem_pos') and pattern['stem_pos'] - 1 < len(stems) else entry_lemma
                    
                    if not stem_to_use:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': entry_lemma,
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })
        
        elif pos_info[0] == 'ADJ':
            # Adjective: ADJ decl variant
            declension = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            variant = int(pos_info[2]) if len(pos_info) > 2 and pos_info[2].isdigit() else 0
            
            stems, entry_lemma = _parse_stems(stems_part)
            if entry_lemma:
                # For ADJ 1 1 (first/second declension), expand stems if needed
                if declension == 1 and variant == 1 and len(stems) == 1:
                    masc_stem = entry_lemma
                    fem_stem = masc_stem
                    neut_stem = masc_stem
                    stems = [masc_stem, fem_stem, neut_stem, masc_stem]
                
                # Generate adjective forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'ADJ':
                        continue
                    if pattern['declension'] != declension and pattern['declension'] != 0:
                        continue
                    # Same (declension, variant) keying as the noun block above.
                    if (pattern['variant'] != 0 and variant != 0
                            and pattern['variant'] != variant):
                        continue
                    
                    stem_to_use = stems[pattern['stem_pos'] - 1] if pattern['stem_pos'] - 1 < len(stems) and pattern.get('stem_pos') else entry_lemma
                    
                    if not stem_to_use:
                        continue
                    
                    form = stem_to_use + pattern['ending']
                    
                    # Create morphology info string
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': entry_lemma,
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })

        elif pos_info[0] == 'ADV':
            # Degree as DICTLINE declares it: X (all three stems present),
            # or POS / COMP / SUPER for a single-degree entry.
            degree = pos_info[1] if len(pos_info) > 1 else 'X'
            stems, entry_lemma = _parse_stem_columns(dictionary_line[0:76])
            if entry_lemma:
                _DEG = {1: 'positive', 2: 'comparative', 3: 'superlative'}
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'ADV':
                        continue
                    if pattern.get('degree') != degree:
                        continue
                    idx = pattern['stem_pos'] - 1
                    if idx >= len(stems):
                        continue
                    stem_to_use = stems[idx]
                    if stem_to_use is None or not stem_to_use:
                        continue
                    form = stem_to_use + pattern['ending']
                    morph = 'adv'
                    if degree == 'X':
                        morph = f"adv {_DEG.get(pattern['stem_pos'], '')}".strip()
                    elif degree in ('COMP', 'SUPER'):
                        morph = f"adv {degree.lower()}"
                    morphology_entries.append({
                        'word_form': form,
                        'lemma': entry_lemma,
                        'morph_info': morph,
                        'confidence': confidence,
                        'source': "Whitaker"
                    })

        elif pos_info[0] == 'PRON':
            # Pronoun: PRON decl variant type
            # Examples from DICTLINE.GEN:
            # - ill ill PRON 6 1 ADJECT (ille - that)
            # - h hu PRON 3 1 ADJECT (hic - this)
            # - i e PRON 4 1 PERS (is - he/she/it)
            # - ego m PRON 5 1 PERS (ego - I)
            # - tu t PRON 5 2 PERS (tu - you)
            # - qu cu PRON 1 0 REL (qui - who)
            declension = int(pos_info[1]) if len(pos_info) > 1 and pos_info[1].isdigit() else 0
            variant = int(pos_info[2]) if len(pos_info) > 2 and pos_info[2].isdigit() else 0

            # Was `[s for s in stems_part.split() if s and s != 'zzz']`, which
            # dropped null stems and COMPACTED the list - silently shifting every
            # stem_pos after the removed one onto the wrong column. _parse_stems
            # nulls them in place instead, preserving positions.
            stems, entry_lemma = _parse_stems(stems_part)

            if entry_lemma:
                # Generate pronoun forms using inflection patterns
                for pattern in self.inflection_patterns:
                    if pattern['pos'] != 'PRON':
                        continue

                    # Match declension (0 in pattern means any)
                    if pattern['declension'] != declension and pattern['declension'] != 0:
                        continue

                    # Match variant:
                    # - Pattern variant 0 matches any dictionary entry variant
                    # - Dictionary entry variant 0 matches any pattern variant
                    # - Otherwise, variants must match exactly
                    if pattern['variant'] != 0 and variant != 0 and pattern['variant'] != variant:
                        continue

                    # Get the appropriate stem
                    stem_idx = pattern['stem_pos'] - 1
                    if stem_idx < 0 or stem_idx >= len(stems):
                        stem_to_use = entry_lemma
                    else:
                        stem_to_use = stems[stem_idx]

                    if not stem_to_use:
                        continue

                    # Apply ending to stem
                    form = stem_to_use + pattern['ending']

                    # Create morphology info string
                    morph_info = []
                    if pattern.get('case') and pattern['case'] != 'X':
                        morph_info.append(pattern['case'].lower())
                    if pattern.get('number') and pattern['number'] != 'X':
                        morph_info.append(pattern['number'].lower())
                    if pattern.get('gender') and pattern['gender'] != 'X':
                        morph_info.append(pattern['gender'].lower())
                    morph_info.append('pron')  # Mark as pronoun

                    morphology_entries.append({
                        'word_form': form,
                        'lemma': entry_lemma,
                        'morph_info': ' '.join(morph_info),
                        'confidence': confidence,
                        'source': "Whitaker"
                    })

        # Re-key onto the citation form. Every POS block funnels through here,
        # so one rewrite covers verbs, nouns, adjectives, pronouns and numerals.
        # Gender is only meaningful for nouns; for other parts of speech the
        # DICTLINE column at this position means something else entirely.
        declared_gender = (pos_info[3] if pos_info and pos_info[0] == 'N'
                           and len(pos_info) > 3 else None)
        cit = _citation_form(morphology_entries, entry_lemma, declared_gender)
        if cit:
            for m in morphology_entries:
                m['lemma'] = cit
        return morphology_entries


def _esse_dictline_from_ada(base_dir):
    """The ESSE row Whitaker's own build appends to the general dictionary.

    `sum` is not in DICTLINE.GEN. It is not missing from Whitaker's dictionary
    either -- `src/commands/makedict_main.adb` prints "This version inserts
    ESSE when D_K = GEN" and constructs the entry in code before writing
    DICTFILE:

        Be_Ve      : constant Verb_Entry := (Con => (5, 1), Kind => To_Be);
        Mean_To_Be : constant Meaning_Type := Head ("be; exist; ...");
        De.Stems (1) := "s";  De.Stems (2) := "";
        De.Stems (3) := "fu"; De.Stems (4) := "fut";
        De.Tran := (X, X, X, A, X);

    Reading DICTLINE.GEN and stopping there reproduces his data files but not
    his build, so the commonest verb in Latin arrives with no entry. Every
    downstream symptom follows from that one hole: `est` resolved to *edo*
    ("eject/emit", 55,286 tokens), `sit` to *sitio*, `sint` to *sino*, `esto`
    to *sumo* ("take up"), because the selector falls through to whatever else
    shares the surface.

    The values are PARSED from the Ada, not transcribed here, so they stay
    Whitaker's. Nothing about this is specific to `sum` beyond the fact that
    his build is where the entry lives.

    Returns one line in DICTLINE.GEN's own column layout, to be read by the
    same parser as every other entry. The inflection engine takes it from
    there: conjugation (5, 1) with those four stems generates sum/es/est/
    sumus/estis/sunt, eram/ero/eris, fui/fuisse, futurus -- exactly as it
    already does for the compounds absum, adsum, desum, insum, intersum,
    which ARE in DICTLINE and carry the same (5, 1).
    """
    ada = base_dir / "src" / "commands" / "makedict_main.adb"
    if not ada.exists():
        raise FileNotFoundError(
            f"Whitaker's makedict_main.adb not found at {ada}. It carries the "
            f"ESSE entry that DICTLINE.GEN does not: without it `sum` has no "
            f"dictionary entry and every form of the verb to be resolves to "
            f"another word. An incomplete checkout reaches here."
        )
    src = ada.read_text(encoding="utf-8", errors="replace")

    con = re.search(r"Be_Ve\s*:\s*constant\s+Verb_Entry\s*:=\s*\(Con\s*=>\s*"
                    r"\((\d+)\s*,\s*(\d+)\)\s*,\s*Kind\s*=>\s*(\w+)\s*\)", src)
    # Up to Max_Meaning_Size, NOT to the first ";" -- the gloss itself is
    # "be; exist; ...", so a semicolon terminator truncates it to "be".
    mean = re.search(r"Mean_To_Be\s*:\s*constant\s+Meaning_Type\s*:=\s*"
                     r"Head\s*\((.*?),\s*Max_Meaning_Size\s*\)", src, re.S)
    block = re.search(r"--\s*First construct ESSE(.*?)De\.Mean", src, re.S)
    if not (con and mean and block):
        raise ValueError(
            f"Could not read the ESSE entry from {ada}. Expected Be_Ve, "
            f"Mean_To_Be and the 'First construct ESSE' block. Whitaker's "
            f"source has changed shape; re-read it rather than hard-coding "
            f"the entry here."
        )
    stems = re.findall(r'De\.Stems\s*\((\d)\)\s*:=\s*"([^"]*)"', block.group(1))
    tran = re.search(r"De\.Tran\s*:=\s*\(([^)]*)\)", block.group(1))
    if len(stems) != 4 or not tran:
        raise ValueError(f"ESSE block in {ada} has {len(stems)} stems and "
                         f"tran={bool(tran)}; expected 4 stems and a Tran.")

    by_key = {int(k): v.strip() for k, v in stems}
    text = " ".join(re.findall(r'"([^"]*)"', mean.group(1)))
    text = re.sub(r"\s+", " ", text).strip()
    flags = " ".join(t.strip() for t in tran.group(1).split(","))
    decl, conj, kind = con.group(1), con.group(2), con.group(3).upper()

    line = ("".join(by_key.get(i, "").ljust(19) for i in (1, 2, 3, 4))
            + "V".ljust(7)
            + f"{decl} {conj} " + kind.ljust(13) + flags + " "
            + text)
    if len(line) < 110:
        raise ValueError(f"Synthesised ESSE line is {len(line)} chars, "
                         f"shorter than DICTLINE's 110-column definition "
                         f"offset: {line!r}")
    return line + "\n"


def load_whitakers_latin(cursor, include_full_morphology=True):
    """Load Whitaker's Words Latin dictionary and morphology into the database
    
    Args:
        cursor: Database cursor
        include_full_morphology: If True, include concatenated morph_info strings (for full DB).
                                If False, just store word-to-lemma mappings (for sample DB).
    """
    
    print("\n=== LOADING WHITAKER'S LATIN DICTIONARY ===")
    
    # Find the Whitaker's Words directory in data-sources
    base_dir = Path(__file__).parent.parent.parent / "data-sources" / "whitakers-words"
    if not base_dir.exists():
        raise FileNotFoundError(
            f"Whitaker's Words directory not found at {base_dir}. "
            f"Clone it: cd data-sources && "
            f"git clone https://github.com/mk270/whitakers-words.git"
        )
    
    dictline_path = base_dir / "DICTLINE.GEN"
    inflects_path = base_dir / "INFLECTS.LAT"
    uniques_path = base_dir / "UNIQUES.LAT"
    
    if not dictline_path.exists():
        raise FileNotFoundError(
            f"Whitaker's DICTLINE.GEN not found at {dictline_path}. "
            f"This is THE Latin dictionary: without it the build produces a "
            f"database with zero Latin dictionary entries and every "
            f"interlinear gloss becomes '???'. Note create_latin_database.py "
            f"only checks that the whitakers-words DIRECTORY exists, so an "
            f"incomplete checkout reaches here."
        )
    
    # Initialize inflection engine
    inflection_engine = LatinInflectionEngine()
    # Unconditional: parse_inflects raises if the file is absent. The previous
    # `if inflects_path.exists()` turned a missing required input into a no-op.
    inflection_engine.parse_inflects(str(inflects_path))
    
    # Process DICTLINE.GEN
    print("\nParsing Whitaker's DICTLINE.GEN...")
    definitions_count = 0
    morphology_entries = []
    dictionary_entries = []

    # Whitaker's frequency codes: A=very frequent, B=frequent, C=common, D=lesser, E=uncommon, F=very rare, X=unknown
    # Lower number = more frequent (for sorting)
    freq_priority = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'X': 7}

    # Whitaker's build appends ESSE to the general dictionary; his data files
    # do not carry it. Read through the SAME parser, so it gets the same stem
    # handling, citation form, frequency sort and morphology generation.
    esse_line = _esse_dictline_from_ada(base_dir)

    with open(dictline_path, 'r', encoding='utf-8') as f:
        for line in itertools.chain(f, [esse_line]):
            if not line.strip():
                continue

            if len(line) > 90:
                lemma_part = line[0:76].strip()
                # First REAL stem, not simply the first column: 23 entries carry
                # Whitaker's "zzz" null marker in column 1 (Adam, multa,
                # deterius - words whose first principal part is suppletive).
                # Taking column 1 blindly keyed all 23 on the junk headword
                # "zzz", which the interlinear then resolved arbitrarily.
                _, lemma = _parse_stems(lemma_part)

                # Extract part of speech (position 76-82 in Whitaker's format)
                pos_part = line[76:83].strip() if len(line) > 82 else None
                pos = pos_part.split()[0] if pos_part else None

                # Extract frequency code and noun type from flags section (position 83-110)
                # Format: "2 1 M P          X X X A O" - tokens are:
                # [0-1]=decl, [2]=gender, [3]=type, [4-6]=Age/Area/Geo, [7]=Frequency, [8]=Source
                # For nouns: [2]=gender (M/F/N/C), [3]=type (P=personal, T=thing, etc.)
                flags_part = line[83:110] if len(line) > 110 else ""
                flags_tokens = flags_part.split()
                freq_code = 'X'  # default to unknown
                # noun_priority: secondary sort for entries with same headword and frequency
                # Only affects noun-to-noun comparisons: 0 = personal nouns, 1 = thing nouns and all non-nouns
                noun_priority = 1  # default: same as thing nouns (no preference vs nouns)

                if len(flags_tokens) >= 2:
                    # Frequency is always second-to-last, source is last
                    freq_code = flags_tokens[-2]  # second from end is frequency
                    # For nouns, check if it's a personal noun (M P, F P, C P)
                    # Personal nouns refer to people and should be preferred over "thing" variants
                    if pos == 'N' and len(flags_tokens) >= 4:
                        noun_type = flags_tokens[3]  # P=personal, T=thing, L=locale, etc.
                        noun_priority = 0 if noun_type == 'P' else 1

                freq_sort = freq_priority.get(freq_code, 7)

                # Get definition from position 110
                definition_part = line[110:] if len(line) > 110 else None
                if definition_part and lemma:
                    definition = definition_part.strip()
                    # Clean up the definition
                    definition = re.sub(r'\s+', ' ', definition)
                    definition = definition.replace('|', '; ')
                    definition = definition.replace('=>', ':')

                    if not definition or re.match(r'^[;:\s]+$', definition):
                        continue

                    # Add part of speech label if available
                    if pos:
                        pos_label = {
                            'N': '(n.) ',
                            'V': '(v.) ',
                            'ADJ': '(adj.) ',
                            'ADV': '(adv.) ',
                            'PREP': '(prep.) ',
                            'CONJ': '(conj.) ',
                            'PRON': '(pron.) ',
                            'INTERJ': '(interj.) ',
                            'NUM': '(num.) '
                        }.get(pos, '')
                        definition = pos_label + definition

                    # Limit definition length
                    if len(definition) > 400:
                        definition = definition[:400] + "..."

                    # Generate the paradigm FIRST: the citation form is derived
                    # from it, and the dictionary entry must be keyed on the same
                    # string the morphology points at, or the join breaks.
                    morph_entries = inflection_engine.generate_morphology_for_dictionary(line)
                    if morph_entries:
                        lemma = morph_entries[0]['lemma']   # already the citation form

                    if lemma and len(lemma) > 0 and not re.match(r'^[0-9]+$', lemma):
                        # Add dictionary entry with frequency and noun_priority for sorting
                        dictionary_entries.append({
                            'headword': lemma,
                            'language': 'latin',
                            'definition': definition,
                            'source': 'Whitaker',
                            'freq_sort': freq_sort,  # for sorting only, not stored in DB
                            'noun_priority': noun_priority,  # 0=personal noun, 1=thing noun
                            'is_noun': (pos == 'N')  # for custom sort comparator
                        })
                        definitions_count += 1

                        # Already generated above, so the headword and the
                        # morphology lemma are the same citation form.
                        morphology_entries.extend(morph_entries)

    # Custom comparator: freq is primary, noun_priority only used when comparing two nouns
    def compare_entries(a, b):
        # First compare by headword
        if a['headword'] < b['headword']:
            return -1
        if a['headword'] > b['headword']:
            return 1
        # Then by frequency
        if a['freq_sort'] < b['freq_sort']:
            return -1
        if a['freq_sort'] > b['freq_sort']:
            return 1
        # Only use noun_priority if BOTH are nouns
        if a.get('is_noun') and b.get('is_noun'):
            if a['noun_priority'] < b['noun_priority']:
                return -1
            if a['noun_priority'] > b['noun_priority']:
                return 1
        return 0

    # Initial sort (will be re-done after UNIQUES.LAT entries are added)
    dictionary_entries.sort(key=cmp_to_key(compare_entries))

    print(f"Extracted {definitions_count} Latin definitions from Whitaker's")
    print(f"Generated {len(morphology_entries)} morphology entries")
    
    # Process UNIQUES.LAT for special forms
    if not uniques_path.exists():
        raise FileNotFoundError(
            f"Whitaker's UNIQUES.LAT not found at {uniques_path}. It supplies "
            f"the irregular forms (sum, eo, fero and their paradigms) that no "
            f"inflection pattern generates."
        )
    print("\nParsing UNIQUES.LAT...")
    uniques_count = 0
    
    with open(uniques_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line or line.startswith('--'):
            i += 1
            continue
        
        if re.match(r'^[a-z]+$', line):
            word_form = line
            
            i += 1
            if i < len(lines) and re.match(r'^[A-Z]', lines[i].strip()):
                i += 1
                
                if i < len(lines) and lines[i].strip():
                    definition = lines[i].strip()
                    
                    # Add as both dictionary entry and special form
                    dictionary_entries.append({
                        'headword': word_form,
                        'language': 'latin',
                        'definition': definition,
                        'source': 'Whitaker UNIQUES',
                        'freq_sort': 4,  # D = lesser frequency for special forms
                        'noun_priority': 1,  # same as thing nouns
                        'is_noun': False  # UNIQUES are typically not nouns
                    })
                    uniques_count += 1
        
        i += 1
    
    print(f"Extracted {uniques_count} special forms from UNIQUES.LAT")

    # Re-sort after adding UNIQUES entries using same custom comparator
    dictionary_entries.sort(key=cmp_to_key(compare_entries))

    # Remove sort keys before inserting (not DB columns)
    for entry in dictionary_entries:
        if 'freq_sort' in entry:
            del entry['freq_sort']
        if 'noun_priority' in entry:
            del entry['noun_priority']
        if 'is_noun' in entry:
            del entry['is_noun']

    # Insert dictionary entries into database
    print("\nInserting Whitaker's dictionary entries into database...")
    for entry in dictionary_entries:
        # Create HTML version of definition
        entry_html = f"<div class='definition'>{entry['definition']}</div>"
        
        cursor.execute("""
            INSERT INTO dictionary_entries 
            (headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
            VALUES (?, NULL, ?, '', ?, ?, ?)
        """, (
            entry['headword'],
            entry['language'],
            entry_html,
            entry['definition'],
            entry['source']
        ))
    
    print(f"Inserted {len(dictionary_entries)} dictionary entries")
    
    # Insert morphology entries into lemma_map
    print("\nInserting Whitaker's morphology into lemma_map...")
    
    if include_full_morphology:
        # For full database: include concatenated morph_info strings
        print("  Including full morphological analysis (full database mode)")
        
        # First deduplicate exact entries
        seen = set()
        unique_morphology = []
        for m in morphology_entries:
            key = f"{m['word_form']}_{m['lemma']}_{m['morph_info']}_{m.get('confidence', 0.8)}_{m.get('source', 'Whitaker')}"
            if key not in seen:
                seen.add(key)
                unique_morphology.append(m)
        
        print(f"  After deduplication: {len(unique_morphology)} entries (from {len(morphology_entries)})")
        
        # Now coalesce entries that differ only in morph_info
        grouped = {}
        for entry in unique_morphology:
            key = (entry['word_form'], entry['lemma'], entry.get('confidence', 0.8), entry.get('source', 'Whitaker'))
            if key not in grouped:
                grouped[key] = []
            if entry.get('morph_info'):
                grouped[key].append(entry['morph_info'])
        
        # Insert coalesced entries
        for (word_form, lemma, confidence, source), morph_infos in grouped.items():
            # Combine multiple morph_infos with pipe separator
            if morph_infos:
                coalesced_morph = '|'.join(sorted(set(morph_infos)))
            else:
                coalesced_morph = ''
            
            cursor.execute("""
                INSERT INTO lemma_map 
                (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                VALUES (?, NULL, ?, ?, ?, ?)
            """, (
                word_form,
                lemma,
                confidence,
                source,
                coalesced_morph
            ))
        
        print(f"  Inserted {len(grouped)} morphology entries with full analysis")
    else:
        # For sample database: just word-to-lemma mappings, no morph_info
        print("  Storing word-to-lemma mappings only (sample database mode)")
        
        seen = set()
        for m in morphology_entries:
            key = (m['word_form'], m['lemma'])
            if key not in seen:
                seen.add(key)
                cursor.execute("""
                    INSERT INTO lemma_map 
                    (word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
                    VALUES (?, NULL, ?, ?, ?, NULL)
                """, (
                    m['word_form'],
                    m['lemma'],
                    m.get('confidence', 0.8),
                    'Whitaker'
                ))
        
        print(f"  Inserted {len(seen)} unique word-to-lemma mappings (from {len(morphology_entries)} total)")
    
    print("\n=== WHITAKER'S LATIN DICTIONARY LOADED SUCCESSFULLY ===")


if __name__ == "__main__":
    # Test the module standalone
    import sqlite3
    
    # Create test database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create necessary tables
    cursor.execute("""
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    """)
    
    # Load Whitaker's data
    load_whitakers_latin(cursor)
    
    # Check results
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries WHERE language = 'latin'")
    dict_count = cursor.fetchone()[0]
    print(f"\nTotal Latin dictionary entries: {dict_count}")
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map WHERE source = 'Whitaker'")
    morph_count = cursor.fetchone()[0]
    print(f"Total Latin morphology entries: {morph_count}")
    
    conn.close()