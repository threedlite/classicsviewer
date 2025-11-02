#!/usr/bin/env python3
"""
CLTK Dictionary Generator - Unified Script
==========================================

Generates both morphology mappings and compound word decompositions from CLTK analysis.

Usage:
    python3 generate_cltk_dictionary.py <input_csv> [options]

Options:
    --min-split N   Minimum characters per compound part (default: 3)
    --workers N     Number of parallel workers (default: 2, use 1 for serial)

Input CSV format (Author,Work pairs):
    Author,Work
    "Homer","Iliad"
    "Homer","Odyssey"

Outputs:
    <input_basename>_dictionary.zip containing:
        - morphology.csv: word_form → lemma mappings with morphological info
        - dictionary.csv: compound word decompositions (if --compounds enabled)
    <input_basename>_cltk_full_analysis.csv: detailed CLTK analysis for debugging

Examples:
    # Basic morphology with default 2 workers
    python3 generate_cltk_dictionary.py SAMPLE_AUTHORS.csv

    # Serial processing (1 worker)
    python3 generate_cltk_dictionary.py SAMPLE_AUTHORS.csv --workers 1

    # Parallel processing with 4 workers
    python3 generate_cltk_dictionary.py SAMPLE_AUTHORS.csv --workers 4
"""

import csv
import time
import sys
import zipfile
import re
import sqlite3
import unicodedata
import multiprocessing as mp
import logging
import json
from pathlib import Path
from typing import Set, List, Dict, Optional, Tuple
from dataclasses import dataclass

# Suppress INFO-level logging from CLTK/Stanza
logging.basicConfig(level=logging.WARNING)
logging.getLogger('stanza').setLevel(logging.WARNING)
logging.getLogger('cltk').setLevel(logging.WARNING)

# Add data-prep to path for potential future imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'data-prep'))


def normalize_greek(text: str) -> str:
    """Remove diacritics from Greek text for comparison"""
    # NFD = canonical decomposition (separates base + diacritics)
    nfd = unicodedata.normalize('NFD', text)
    # Filter out combining diacritical marks
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


def load_reverse_morphology() -> Dict[str, List[Tuple[str, int]]]:
    """
    Load Perseus reverse morphology index from perseus_reverse_morphology.json.
    If file doesn't exist, builds it automatically from Perseus database.

    Returns dict mapping normalized_word_form → [(lemma, frequency), ...]
    """
    morph_file = Path(__file__).parent / 'perseus_reverse_morphology.json'

    if not morph_file.exists():
        print("⚠ perseus_reverse_morphology.json not found")
        print("  Building from Perseus database...")

        try:
            # Find Perseus database
            db_path = find_database()
            if not db_path:
                print("  ✗ Could not find Perseus database")
                return {}

            # Build reverse morphology index inline
            import sqlite3
            from collections import defaultdict

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            print("  Querying Perseus morphology data...")
            cursor.execute("""
                SELECT word_form, lemma, COUNT(*) as freq
                FROM lemma_map
                WHERE lemma IS NOT NULL AND word_form IS NOT NULL
                GROUP BY word_form, lemma
                ORDER BY freq DESC
            """)

            reverse_index = defaultdict(list)
            total_mappings = 0

            print("  Building reverse index...")
            for row in cursor.fetchall():
                word_form, lemma, freq = row
                norm_form = normalize_greek(word_form.lower())

                # Skip very short forms (< 3 chars)
                if len(norm_form) < 3:
                    continue

                reverse_index[norm_form].append((lemma, freq))
                total_mappings += 1

                if total_mappings % 500000 == 0:
                    print(f"    Processed {total_mappings:,} mappings...")

            conn.close()

            # Sort each list by frequency
            for norm_form in reverse_index:
                reverse_index[norm_form] = sorted(
                    reverse_index[norm_form],
                    key=lambda x: x[1],
                    reverse=True
                )

            print(f"  ✓ Built reverse index with {len(reverse_index):,} unique forms")

            # Save to JSON
            output = dict(reverse_index)
            with open(morph_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            print(f"  ✓ Saved to {morph_file.name}")
            return output

        except Exception as e:
            print(f"  ✗ Could not build reverse morphology: {e}")
            import traceback
            traceback.print_exc()
            return {}

    # Load the file
    try:
        with open(morph_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data):,} word forms from reverse morphology")
        return data
    except Exception as e:
        print(f"  ✗ Error loading reverse morphology: {e}")
        return {}


def load_compound_stems() -> Dict[str, Dict]:
    """
    Load compound stem mappings from greek_compound_stems.json.
    If file doesn't exist, attempts to build it automatically from Perseus database.

    Returns dict mapping normalized lemma → stem info including:
    - genitive_stems: stems from genitive case (most common in compounds)
    - compound_forms: thematic vowel variants for compounds
    """
    stem_file = Path(__file__).parent / 'greek_compound_stems.json'

    # If stem file doesn't exist, try to build it
    if not stem_file.exists():
        print("⚠ greek_compound_stems.json not found")
        print("  Attempting to build stem database from Perseus...")

        try:
            # Import build script
            build_script = Path(__file__).parent / 'build_compound_stems.py'

            if not build_script.exists():
                print("  ✗ build_compound_stems.py not found")
                print("  → Stem matching disabled")
                return {}

            # Import and run the build function
            import importlib.util
            spec = importlib.util.spec_from_file_location("build_compound_stems", build_script)
            build_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(build_module)

            # Find Perseus database
            db_path = build_module.find_database()
            print(f"  ✓ Found Perseus database: {db_path}")

            # Build stem mappings
            print("  Building stem database (this may take 2-3 minutes)...")
            stem_data = build_module.build_compound_stems_from_perseus(db_path)

            # Save to JSON
            print(f"  Saving to {stem_file}...")
            with open(stem_file, 'w', encoding='utf-8') as f:
                json.dump(stem_data, f, ensure_ascii=False, indent=2)

            print(f"  ✓ Built and saved {len(stem_data):,} lemma stem mappings")
            return stem_data

        except FileNotFoundError as e:
            print(f"  ✗ Could not find Perseus database: {e}")
            print("  → Stem matching disabled")
            return {}
        except Exception as e:
            print(f"  ✗ Failed to build stem database: {e}")
            print("  → Stem matching disabled")
            return {}

    # Load existing stem file
    try:
        with open(stem_file, 'r', encoding='utf-8') as f:
            stems = json.load(f)
        print(f"✓ Loaded {len(stems):,} compound stem mappings")
        return stems
    except Exception as e:
        print(f"⚠ Warning: Failed to load compound stems: {e}")
        return {}


def build_prefix_index(perseus_lemmas: Set[str], prefix_len: int = 3) -> Dict[str, Set[str]]:
    """
    Build an in-memory prefix index for fast fuzzy matching.

    Maps normalized prefix -> set of lemmas with that prefix.
    This reduces O(n) scan to O(1) lookup.

    Args:
        perseus_lemmas: Set of all Perseus lemmas
        prefix_len: Length of prefix to index (default 3)

    Returns:
        Dict mapping prefix -> set of lemmas
    """
    index = {}
    for lemma in perseus_lemmas:
        normalized = normalize_greek(lemma.lower())
        if len(normalized) >= prefix_len:
            prefix = normalized[:prefix_len]
            if prefix not in index:
                index[prefix] = set()
            index[prefix].add(lemma)
    return index


def get_ensemble_lemma_candidates(
    fragment: str,
    reverse_morphology: Dict[str, List[Tuple[str, int]]],
    stem_database: Dict[str, Dict],
    lemma_freq: Dict[str, Tuple[str, int]],
    top_n: int = 10
) -> List[Tuple[str, float, str]]:
    """
    ENSEMBLE APPROACH: Get best lemma candidates for a fragment using ALL data sources.

    Combines three independent sources:
    1. Perseus reverse morphology (actual attested forms)
    2. Stem database (genitive/verbal stems)
    3. Prefix matching (fallback for rare forms)

    Args:
        fragment: The word fragment to match
        reverse_morphology: Dict of normalized_form → [(lemma, freq), ...]
        stem_database: Dict of normalized_lemma → {genitive_stems, verbal_stems, ...}
        lemma_freq: Dict of normalized_lemma → (lemma, frequency)
        top_n: Return top N candidates

    Returns:
        List of (lemma, score, source) tuples, sorted by score DESC
    """
    fragment_norm = normalize_greek(fragment.lower())
    candidates = {}  # lemma_norm -> (lemma_display, score, source)

    # SOURCE 1: Perseus reverse morphology (BEST - actual attested forms)
    if fragment_norm in reverse_morphology:
        for lemma, freq in reverse_morphology[fragment_norm][:20]:
            lemma_norm = normalize_greek(lemma.lower())
            # Score: frequency * 100 (prioritize high-frequency words) + bonus
            score = freq * 100 + 50  # +50 bonus for exact morphology match
            if lemma_norm not in candidates or score > candidates[lemma_norm][1]:
                candidates[lemma_norm] = (lemma, score, 'perseus_morphology')

    # SOURCE 2: Stem database (GOOD - handles genitive/verbal stems)
    for lemma_norm, stem_data in stem_database.items():
        # Check genitive stems
        for gen_stem in stem_data.get('genitive_stems', []):
            if len(gen_stem) >= 4 and fragment_norm.startswith(gen_stem):
                lemma = stem_data['lemma']
                # Get frequency if available
                freq = lemma_freq.get(lemma_norm, (lemma, 1))[1]
                # Score: frequency * 50 + stem_length (prefer longer stem matches)
                score = freq * 50 + len(gen_stem) * 5 + 30  # +30 bonus for genitive stem
                if lemma_norm not in candidates or score > candidates[lemma_norm][1]:
                    candidates[lemma_norm] = (lemma, score, 'genitive_stem')

        # Check verbal stems
        for verb_stem in stem_data.get('verbal_stems', [])[:3]:
            if len(verb_stem) >= 3 and fragment_norm.startswith(verb_stem):
                lemma = stem_data['lemma']
                freq = lemma_freq.get(lemma_norm, (lemma, 1))[1]
                score = freq * 40 + len(verb_stem) * 4 + 20  # +20 bonus for verbal stem
                if lemma_norm not in candidates or score > candidates[lemma_norm][1]:
                    candidates[lemma_norm] = (lemma, score, 'verbal_stem')

    # SOURCE 3: Direct prefix matching in lemma list (FALLBACK)
    # This catches cases where fragment is close to lemma
    for lemma_norm, (lemma, freq) in lemma_freq.items():
        if lemma_norm.startswith(fragment_norm) or fragment_norm.startswith(lemma_norm):
            # Calculate match quality
            match_len = len(set(fragment_norm) & set(lemma_norm))
            score = freq * 20 + match_len * 3  # Lower priority than morphology/stems
            if lemma_norm not in candidates or score > candidates[lemma_norm][1]:
                candidates[lemma_norm] = (lemma, score, 'prefix_match')

    # Sort by score and return top N
    sorted_candidates = sorted(
        [(lemma, score, source) for lemma, score, source in candidates.values()],
        key=lambda x: x[1],
        reverse=True
    )

    return sorted_candidates[:top_n]


def find_fuzzy_prefix_matches(
    cltk_lemma: str,
    perseus_lemmas: Set[str],
    min_prefix: int = 3,
    top_n: int = 10,
    prefix_index: Optional[Dict[str, Set[str]]] = None,
    stem_database: Optional[Dict[str, Dict]] = None
) -> List[tuple[str, int, int, bool]]:
    """
    Find Perseus lemmas that fuzzy match CLTK's lemma using prefix + length similarity.

    This handles CLTK's imperfect lemmatization (e.g., χρύω vs χρυσός).

    PHASE 1 ENHANCEMENT: Also matches against compound stems (genitive stems + thematic vowels).
    Example: Fragment "γυναικ" matches lemma "γυνή" via genitive stem "γυναικ".

    PHASE 3 ENHANCEMENT: Matches against verbal stems for verb compound elements.
    Example: Fragment "πειθ" matches verb "πείθω" via present stem "πειθ".
             Fragment "πεισ" matches verb "πείθω" via aorist stem "πεισ".

    OPTIMIZED: Uses prefix_index for O(1) candidate lookup instead of O(n) scan.

    Args:
        cltk_lemma: Lemma from CLTK (may not be in dictionary)
        perseus_lemmas: Set of valid Perseus lemmas (used if no index)
        min_prefix: Minimum prefix length to consider a match
        top_n: Return top N matches
        prefix_index: Optional pre-built prefix index for performance
        stem_database: Optional stem mappings (lemma → genitive/verbal/compound stems)

    Returns:
        List of (lemma, prefix_len, length_diff, is_verb) sorted by:
        1) prefix_len DESC (longer prefixes first)
        2) length_diff ASC (similar lengths preferred)
        is_verb: Boolean flag indicating if lemma is a verb (for POS-based scoring)
    """
    cltk_norm = normalize_greek(cltk_lemma.lower())
    cltk_len = len(cltk_norm)
    matches = []
    candidates = None  # Will be set if using prefix index
    stem_matched_lemmas = set()  # Track lemmas matched via stems

    # Get candidates first
    if prefix_index and len(cltk_norm) >= min_prefix:
        prefix = cltk_norm[:min_prefix]
        candidates = prefix_index.get(prefix, set())
    else:
        candidates = perseus_lemmas

    # PHASE 1: STEM-BASED MATCHING (CHECK FIRST for better ranking)
    # Check if cltk fragment matches compound stems (genitive stems + thematic vowels)
    # This handles cases like "γυναικ" → "γυνή" via genitive stem
    # CONSERVATIVE: Only boost if stem provides BETTER match than direct lemma match
    if stem_database and candidates:
        for perseus_lemma in candidates:
            perseus_norm = normalize_greek(perseus_lemma.lower())

            # Calculate direct lemma match score first
            direct_prefix_len = 0
            for i in range(min(len(cltk_norm), len(perseus_norm))):
                if cltk_norm[i] == perseus_norm[i]:
                    direct_prefix_len += 1
                else:
                    break

            # Check if this lemma has compound stems
            if perseus_norm in stem_database:
                stem_data = stem_database[perseus_norm]

                # Try genitive stems (most important for compounds) - BOOST +2 points
                # Filter: only use stems >= 4 chars to avoid spurious short matches
                # CONSERVATIVE: Only boost if stem match is BETTER than direct match
                for genitive_stem in stem_data.get('genitive_stems', []):
                    # Skip very short stems (likely spurious)
                    if len(genitive_stem) < 4:
                        continue

                    # Check if cltk fragment matches this genitive stem
                    prefix_len = 0
                    for i in range(min(len(cltk_norm), len(genitive_stem))):
                        if cltk_norm[i] == genitive_stem[i]:
                            prefix_len += 1
                        else:
                            break

                    # Only use stem if it provides BETTER match than direct lemma
                    if prefix_len >= min_prefix and prefix_len > direct_prefix_len:
                        # Genitive stem match - give moderate bonus (+2 to prefix_len for ranking)
                        length_diff = abs(len(genitive_stem) - cltk_len)
                        is_verb = stem_data.get('is_verb', False)
                        matches.append((perseus_lemma, prefix_len + 2, length_diff, is_verb))
                        stem_matched_lemmas.add(perseus_lemma)
                        break  # Only count best stem match per lemma

                # PHASE 3: Try verbal stems (for verb compound elements)
                # Example: πείθω → πειθ, πεισ (present/aorist stems)
                if perseus_lemma not in stem_matched_lemmas:
                    for verbal_stem in stem_data.get('verbal_stems', []):
                        # Skip very short stems
                        if len(verbal_stem) < 3:
                            continue

                        prefix_len = 0
                        for i in range(min(len(cltk_norm), len(verbal_stem))):
                            if cltk_norm[i] == verbal_stem[i]:
                                prefix_len += 1
                            else:
                                break

                        # Only use stem if it provides BETTER match than direct lemma
                        if prefix_len >= min_prefix and prefix_len > direct_prefix_len:
                            # Verbal stem match - good bonus (+2 to prefix_len, same as genitive)
                            length_diff = abs(len(verbal_stem) - cltk_len)
                            is_verb = stem_data.get('is_verb', False)
                            matches.append((perseus_lemma, prefix_len + 2, length_diff, is_verb))
                            stem_matched_lemmas.add(perseus_lemma)
                            break  # Only count best verbal stem match per lemma

                # If no genitive or verbal match, try all stems (lower priority)
                if perseus_lemma not in stem_matched_lemmas:
                    for stem in stem_data.get('stems', [])[:5]:  # Check top 5 stems only
                        # Skip very short stems
                        if len(stem) < 4:
                            continue

                        prefix_len = 0
                        for i in range(min(len(cltk_norm), len(stem))):
                            if cltk_norm[i] == stem[i]:
                                prefix_len += 1
                            else:
                                break

                        # Only use stem if it provides BETTER match than direct lemma
                        if prefix_len >= min_prefix and prefix_len > direct_prefix_len:
                            # Regular stem match - small bonus (+1 to prefix_len)
                            length_diff = abs(len(stem) - cltk_len)
                            is_verb = stem_data.get('is_verb', False)
                            matches.append((perseus_lemma, prefix_len + 1, length_diff, is_verb))
                            stem_matched_lemmas.add(perseus_lemma)
                            break

    # Regular prefix matching (for lemmas not matched via stems)
    for perseus_lemma in candidates:
        # Skip if already matched via stems (they have better scores)
        if perseus_lemma in stem_matched_lemmas:
            continue

        perseus_norm = normalize_greek(perseus_lemma.lower())

        # Calculate common prefix length
        prefix_len = 0
        for i in range(min(len(cltk_norm), len(perseus_norm))):
            if cltk_norm[i] == perseus_norm[i]:
                prefix_len += 1
            else:
                break

        if prefix_len >= min_prefix:
            length_diff = abs(len(perseus_norm) - cltk_len)
            # Check if this lemma is a verb (for non-stem matches)
            is_verb = False
            if stem_database and perseus_norm in stem_database:
                is_verb = stem_database[perseus_norm].get('is_verb', False)
            matches.append((perseus_lemma, prefix_len, length_diff, is_verb))

    # Sort by: 1) prefix length DESC, 2) length diff ASC
    matches.sort(key=lambda x: (-x[1], x[2]))
    return matches[:top_n]


def score_decomposition(
    original: str,
    split_point: int,
    left_pos: str,
    right_pos: str,
    left_matches: List[tuple[str, float, str]],
    right_matches: List[tuple[str, float, str]]
) -> float:
    """
    Score a compound decomposition for ranking quality.

    ENSEMBLE APPROACH: Uses ensemble match scores instead of fuzzy match metrics.

    Combines multiple factors:
    - Ensemble match quality (from Perseus morphology + stems + frequency)
    - Split point balance (prefer middle splits)
    - POS compatibility (prefer NOUN+NOUN or ADJ+NOUN)

    Args:
        original: Original word being decomposed
        split_point: Character position where word was split
        left_pos: POS tag of left part
        right_pos: POS tag of right part
        left_matches: Ensemble matches for left part [(lemma, score, source), ...]
        right_matches: Ensemble matches for right part

    Returns:
        Score (higher is better, typically 0-1000+ range with ensemble scores)
    """
    score = 0.0

    # 1. ENSEMBLE MATCH QUALITY - MOST IMPORTANT
    # Use the ensemble scores directly - they already incorporate:
    # - Frequency weighting (common words score higher)
    # - Source confidence (Perseus morphology > stems > prefix match)
    # - Match quality (stem length, exact form match bonuses)
    if left_matches and right_matches:
        # Get ensemble scores from top candidates
        left_ensemble_score = left_matches[0][1]   # score from ensemble
        right_ensemble_score = right_matches[0][1]

        # Average the ensemble scores and normalize to 0-30 range for compatibility
        # Ensemble scores can be 100-8000+, so normalize by dividing by 100
        ensemble_avg = (left_ensemble_score + right_ensemble_score) / 2
        normalized_score = min(ensemble_avg / 100, 30)  # Cap at 30
        score += normalized_score
    elif left_matches or right_matches:
        # One ensemble match - give partial credit (15 points)
        score += 15
    else:
        # No ensemble matches - give baseline (10 points)
        score += 10

    # 2. SPLIT BALANCE (0-5 points) - Less important than fuzzy match quality
    # Prefer splits near the middle of the word
    # Greek compounds often split around 40-60% through the word
    balance = 1 - abs(0.5 - split_point / len(original))
    balance_score = balance * 5  # Reduced from 10 to 5
    score += balance_score

    # 2A. PHASE 2A: UNBALANCED SPLIT PENALTY (0 to -5 points)
    # Heavily penalize very unbalanced splits (e.g., 2+10 chars)
    # These are rarely correct in Greek compound formation
    left_len = split_point
    right_len = len(original) - split_point

    if left_len == 0 or right_len == 0:
        # Degenerate split - heavily penalize
        score -= 10
    elif left_len > 0 and right_len > 0:
        # Calculate balance ratio (smaller / larger)
        balance_ratio = min(left_len, right_len) / max(left_len, right_len)

        if balance_ratio < 0.3:  # Very unbalanced (one part < 30% of other)
            # Example: 2+10 chars (ratio=0.17) or 3+10 chars (ratio=0.23)
            score -= 5
        elif balance_ratio < 0.4:  # Quite unbalanced (one part < 40% of other)
            # Example: 3+8 chars (ratio=0.375) or 4+11 chars (ratio=0.36)
            score -= 3
        elif balance_ratio < 0.5:  # Somewhat unbalanced (one part < 50% of other)
            # Example: 4+9 chars (ratio=0.44) or 5+11 chars (ratio=0.45)
            score -= 1

    # 3. POS COMPATIBILITY (-3 to +5 points)
    # Common compound patterns in Greek:
    # - NOUN + NOUN (e.g., χρυσός + θρόνος) - most common
    # - ADJ + NOUN (e.g., μέγας + ψυχή)
    # - NOUN + ADJ works too
    # PHASE 3 POS ENHANCEMENT: Use is_verb metadata to penalize unlikely patterns

    # ENSEMBLE APPROACH: Check if parts are verbal stems by source
    # The ensemble returns (lemma, score, source) where source can be 'verbal_stem'
    right_is_verb = False
    if right_matches and len(right_matches[0]) >= 3:
        right_is_verb = right_matches[0][2] == 'verbal_stem'  # 3rd element is source

    left_is_verb = False
    if left_matches and len(left_matches[0]) >= 3:
        left_is_verb = left_matches[0][2] == 'verbal_stem'

    # Reward good patterns
    if left_pos in ['NOUN', 'ADJ'] and right_pos in ['NOUN', 'ADJ']:
        # Best patterns - but penalize if right is actually a verb
        if right_is_verb:
            # NOUN + VERB(tagged as ADJ) - questionable pattern
            # Example: χαμαί + λεύσσω (ground + to see) vs χαμαί + Λευκή (ground + white)
            score -= 3  # Penalize NOUN+VERB combinations
        else:
            score += 5  # Reward genuine NOUN+NOUN or ADJ+NOUN
    elif left_pos == 'VERB' and right_pos in ['NOUN', 'ADJ']:
        # Verb stems can appear in compounds (φιλο-σοφος)
        score += 3
    elif left_is_verb and right_pos in ['NOUN', 'ADJ']:
        # Left is verb (by metadata) even if CLTK tagged it differently
        score += 3

    return score


@dataclass
class ProcessingOptions:
    """Configuration options for CLTK processing"""
    min_split_length: int = 4
    num_workers: int = 2  # Number of parallel workers for work-level processing


@dataclass
class MorphologyResult:
    """Result from morphological analysis"""
    word_form: str
    lemma: Optional[str]
    pos: Optional[str]
    features: Optional[str]
    success: bool
    error: Optional[str] = None


@dataclass
class CompoundDecomposition:
    """Result from compound word analysis"""
    original: str
    left_form: str
    left_lemma: str
    left_pos: str
    left_features: str
    right_form: str
    right_lemma: str
    right_pos: str
    right_features: str
    split_point: int
    score: float = 0.0  # Quality score for ranking (higher is better)
    left_matches: list = None  # Fuzzy matches for left part [(lemma, prefix_len, length_diff, is_verb), ...]
    right_matches: list = None  # Fuzzy matches for right part


def check_cltk_installation() -> bool:
    """Verify CLTK is installed"""
    try:
        import cltk
        print(f"✓ CLTK version {cltk.__version__} found")
        return True
    except ImportError:
        print("ERROR: CLTK not installed")
        print("Install with: pip install 'cltk[stanza]'")
        return False


def initialize_cltk():
    """Initialize CLTK with Ancient Greek support"""
    print("\nInitializing CLTK for Ancient Greek...")
    try:
        from cltk.nlp import NLP
        nlp = NLP(language_code="grc", backend="stanza", suppress_banner=True)
        print("✓ CLTK initialized successfully")
        return nlp
    except Exception as e:
        print(f"ERROR initializing CLTK: {e}")
        return None


def find_database() -> Optional[Path]:
    """Find the Perseus database file (priority: extended > full > sample)"""
    data_prep = Path(__file__).parent.parent / 'data-prep'

    db_candidates = [
        data_prep / 'perseus_texts_extended.db',
        data_prep / 'perseus_texts_full.db',
        data_prep / 'perseus_texts_sample.db',
        data_prep / 'perseus_texts.db',
    ]

    for db_path in db_candidates:
        if db_path.exists() and db_path.stat().st_size > 1000:
            return db_path

    return None


def load_author_works(csv_file: Path) -> Dict[str, Set[str]]:
    """Load author/work pairs from CSV"""
    works_by_author = {}

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            author = row['Author']
            work = row.get('Work', '')

            if author not in works_by_author:
                works_by_author[author] = set()
            if work:
                works_by_author[author].add(work)

    return works_by_author


def extract_words_from_database(
    db_conn: sqlite3.Connection,
    author: str,
    work_title: str
) -> Tuple[Set[str], Optional[str]]:
    """
    Extract Greek words from database for a specific author/work.
    Returns: (set of words, actual work title found in DB)
    """
    words = set()

    try:
        # Find work by author and title
        cursor = db_conn.execute("""
            SELECT DISTINCT w.id, w.title_english, w.title, w.title_alt
            FROM authors a
            JOIN works w ON a.id = w.author_id
            WHERE a.name = ?
            AND (w.title_english = ? OR w.title = ? OR w.title_alt = ?)
        """, (author, work_title, work_title, work_title))

        work_row = cursor.fetchone()
        if not work_row:
            return words, None

        work_id = work_row[0]
        found_title = work_row[1] or work_row[2]

        # Extract all Greek text for this work
        cursor = db_conn.execute("""
            SELECT DISTINCT tl.line_text
            FROM text_lines tl
            JOIN books b ON tl.book_id = b.id
            WHERE b.work_id = ?
        """, (work_id,))

        for row in cursor:
            line_text = row[0]
            if line_text:
                # Extract Greek words (Unicode ranges for Greek)
                greek_words = re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]+', line_text)
                words.update(greek_words)

        return words, found_title

    except Exception as e:
        print(f"  Warning: Database error for {author} - {work_title}: {e}")
        return words, None


# Global NLP instance per worker (initialized once per worker process)
_worker_nlp = None
_worker_id = None

def init_worker():
    """Initialize worker with a persistent NLP instance (called once per worker at startup)"""
    global _worker_nlp, _worker_id
    import os
    from cltk.nlp import NLP
    _worker_id = os.getpid()  # Store worker's process ID
    _worker_nlp = NLP(language_code="grc", backend="stanza", suppress_banner=True)


def process_work_worker(args: Tuple[Path, str, str, int, int, Set[str], Set[str]]) -> Tuple[int, str, str, List[MorphologyResult], List[Dict[str, str]]]:
    """
    Worker function to process an entire work: extract words + CLTK analysis + compound analysis.
    Uses shared NLP instance initialized once per worker (not once per work).

    Args:
        args: (db_path, author, work_title, work_index, min_split, valid_lemmas, lemmas_normalized)

    Returns:
        (work_index, author, work_title, morphology_results, compound_entries)
    """
    global _worker_nlp, _worker_id
    db_path, author, work_title, work_index, min_split, valid_lemmas, actual_words, lemmas_normalized = args

    # Extract words from database
    db_conn = sqlite3.connect(db_path)
    try:
        words, db_title = extract_words_from_database(db_conn, author, work_title)
    finally:
        db_conn.close()

    if not words or not db_title:
        return (work_index, author, work_title, [], [])

    # Sort words for deterministic processing
    sorted_words = sorted(words)

    # Use the worker's persistent NLP instance (initialized once at worker startup)
    nlp = _worker_nlp

    # Process words with CLTK (pass worker_id for labeling)
    results = process_words_batch(nlp, sorted_words, worker_id=_worker_id)

    # Generate compound decompositions for this work (pass worker_id for labeling)
    options = ProcessingOptions(min_split_length=min_split)
    compound_entries = generate_compounds(nlp, results, valid_lemmas, actual_words, lemmas_normalized, options, worker_id=_worker_id)

    return (work_index, author, db_title, results, compound_entries)


def process_all_works(
    db_path: Path,
    works_by_author: Dict[str, Set[str]],
    num_workers: int = 1,
    min_split: int = 4
) -> Tuple[List[MorphologyResult], List[Dict[str, str]], Dict[str, Set[str]]]:
    """
    Process all works: extract words + CLTK morphological analysis + compound analysis.

    Args:
        db_path: Path to database file
        works_by_author: Dict of author -> set of work titles
        num_workers: Number of parallel workers (1 = serial, 2+ = parallel)
        min_split: Minimum split length for compound words

    Returns: (morphology_results, compound_entries, found_works_by_author)
    """
    all_results = []
    all_compounds = []
    found_works = {}

    # Load valid lemmas once (shared across all workers)
    print("\nLoading Perseus lemma database...")
    db_conn = sqlite3.connect(db_path)
    valid_lemmas, actual_words, lemmas_normalized = load_valid_lemmas_and_words(db_conn)
    db_conn.close()

    # Prepare list of all works to process
    work_list = []
    work_index = 0
    for author, requested_works in works_by_author.items():
        for work_title in requested_works:
            work_list.append((db_path, author, work_title, work_index, min_split, valid_lemmas, actual_words, lemmas_normalized))
            work_index += 1

    if num_workers > 1:
        # Parallel processing: each worker does extract + CLTK + compounds
        import time
        print(f"\nProcessing {len(work_list)} works with {num_workers} workers (parallel CLTK + compounds)...")

        start_time = time.time()
        completed = 0
        total_words_processed = 0

        with mp.Pool(num_workers, initializer=init_worker) as pool:
            # Use imap_unordered for progress tracking
            for work_idx, author, db_title, results, compounds in pool.imap_unordered(process_work_worker, work_list):
                if results:
                    all_results.extend(results)
                    all_compounds.extend(compounds)
                    total_words_processed += len(results)

                    if author not in found_works:
                        found_works[author] = set()
                    found_works[author].add(db_title)

                    # Progress update with ETA to full completion
                    completed += 1
                    elapsed = time.time() - start_time

                    # Calculate processing rate and remaining time
                    words_per_sec = total_words_processed / elapsed if elapsed > 0 else 0
                    works_remaining = len(work_list) - completed

                    # Show progress
                    pct = (completed / len(work_list)) * 100
                    compound_info = f", {len(compounds)} compounds" if compounds else ""

                    # ETA based on average time per work (more stable for variable-sized works)
                    time_per_work = elapsed / completed if completed > 0 else 0
                    eta_seconds = time_per_work * works_remaining

                    # Format ETA as hours:minutes remaining + estimated completion time
                    if completed > 0:
                        from datetime import datetime, timedelta
                        current_time = datetime.now()
                        timestamp = current_time.strftime('%Y-%m-%d %I:%M:%S %p %Z')
                        eta_hours = int(eta_seconds // 3600)
                        eta_mins = int((eta_seconds % 3600) // 60)
                        eta_remaining = f"{eta_hours}h {eta_mins}m" if eta_hours > 0 else f"{eta_mins}m"
                        completion_time = current_time + timedelta(seconds=eta_seconds)
                        eta_str = f"ETA: {eta_remaining} (done ~{completion_time.strftime('%Y-%m-%d %I:%M %p %Z')})"
                    else:
                        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p %Z')
                        eta_str = "calculating..."

                    print(f"  [{timestamp}] [{completed}/{len(work_list)} ({pct:.0f}%)] ✓ {author} - {db_title}: {len(results)} words{compound_info} "
                          f"({words_per_sec:.0f} words/sec, {eta_str})")

        elapsed_total = time.time() - start_time
        print(f"\n✓ Completed {len(work_list)} works ({total_words_processed} words) in {elapsed_total/60:.1f} minutes")
    else:
        # Serial processing
        from cltk.nlp import NLP
        nlp = NLP(language_code="grc", backend="stanza", suppress_banner=True)

        db_conn = sqlite3.connect(db_path)
        options = ProcessingOptions(min_split_length=min_split)
        try:
            for author, requested_works in works_by_author.items():
                for work_title in requested_works:
                    words, db_title = extract_words_from_database(db_conn, author, work_title)
                    if words and db_title:
                        print(f"\nProcessing {author} - {db_title}...")
                        sorted_words = sorted(words)
                        results = process_words_batch(nlp, sorted_words)
                        all_results.extend(results)

                        # Generate compounds for this work
                        compounds = generate_compounds(nlp, results, valid_lemmas, actual_words, lemmas_normalized, options)
                        all_compounds.extend(compounds)

                        compound_info = f", {len(compounds)} compounds" if compounds else ""
                        print(f"  ✓ {db_title}: {len(results)} words{compound_info}")

                        if author not in found_works:
                            found_works[author] = set()
                        found_works[author].add(work_title)
        finally:
            db_conn.close()

    return all_results, all_compounds, found_works


def format_morphology(pos, features) -> str:
    """Format POS and features into a human-readable morphology string"""
    morph_parts = []

    # Extract POS tag
    if pos:
        pos_str = str(pos)
        if 'tag=' in pos_str:
            match = re.search(r'tag="([^"]+)"', pos_str)
            if match:
                morph_parts.append(match.group(1))
        else:
            morph_parts.append(pos_str)

    # Extract features
    if features:
        feature_str = str(features)
        if 'UDFeatureTag' in feature_str:
            tags = re.findall(r'UDFeatureTag\(([^)]+)\)', feature_str)
            for tag in tags:
                if '=' in tag:
                    # Extract value part: "Case=Dative" -> "Dative"
                    value = tag.split('=', 1)[1]
                    morph_parts.append(value)
                else:
                    morph_parts.append(tag)

    return ', '.join(morph_parts) if morph_parts else ''


def process_words_batch(nlp, words: List[str], worker_id: int = None) -> List[MorphologyResult]:
    """Process words in batches for optimal performance"""
    results = []
    total = len(words)

    # Auto-calculate optimal batch size based on dataset size
    if total < 10000:
        batch_size = 100
    elif total < 50000:
        batch_size = 150
    else:
        batch_size = 200

    import time
    start_time = time.time()
    last_report = start_time

    for i in range(0, total, batch_size):
        batch = words[i:i+batch_size]
        batch_text = " ".join(batch)

        try:
            doc = nlp.analyze(batch_text)

            # Match analyzed words to original batch
            for j, word_obj in enumerate(doc.words):
                if j < len(batch):
                    results.append(MorphologyResult(
                        word_form=batch[j],
                        lemma=word_obj.lemma if hasattr(word_obj, 'lemma') else None,
                        pos=word_obj.pos if hasattr(word_obj, 'pos') else None,
                        features=word_obj.features if hasattr(word_obj, 'features') else None,
                        success=True
                    ))
        except Exception as e:
            # Handle batch failure - mark all words as failed
            for word in batch:
                results.append(MorphologyResult(
                    word_form=word,
                    lemma=None,
                    pos=None,
                    features=None,
                    success=False,
                    error=str(e)
                ))

        # Progress update with rate calculation (no ETA - only show for full job completion)
        processed = min(i + batch_size, total)
        current_time = time.time()

        if processed % 500 == 0 or processed == total or (current_time - last_report) >= 30:
            elapsed = current_time - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            worker_label = f"[W{worker_id}] " if worker_id else ""
            print(f"  {worker_label}Processed {processed}/{total} ({processed/total*100:.1f}%) - "
                  f"{rate:.1f} words/sec")
            last_report = current_time

    return results


def score_individual_part(matches: List[tuple[str, float, str]], pos: str) -> float:
    """
    Score the quality of an individual part (left or right) of a decomposition.

    ENSEMBLE APPROACH: Uses ensemble scores instead of fuzzy match metrics.

    This is used for cross-decomposition to score parts independently.

    Args:
        matches: Ensemble matches [(lemma, score, source), ...]
        pos: POS tag of the part

    Returns:
        Score (typically 0-20 range)
    """
    if not matches:
        return 0.0

    score = 0.0

    # Ensemble match quality (0-15 points)
    # Normalize ensemble scores (100-8000+) to 0-15 range
    ensemble_score = matches[0][1]
    normalized = min(ensemble_score / 100, 15)
    score += normalized

    # POS bonus (0-5 points) - prefer NOUN and ADJ
    if pos in ['NOUN', 'ADJ']:
        score += 5
    elif pos == 'VERB':
        score += 3

    return score


def find_best_cross_decomposition(decompositions: List[CompoundDecomposition]) -> Optional[CompoundDecomposition]:
    """
    Find the best cross-decomposition: best left part + best right part from different splits.

    This handles cases where CLTK gets one part right in split A and the other part right in split B.

    FIXED STRATEGY:
    1. Score each LEFT part independently using its stored fuzzy match quality
    2. Score each RIGHT part independently using its stored fuzzy match quality
    3. Find combination with best combined PART scores (not full decomp scores)
    4. Return synthetic decomposition if it beats current best

    Args:
        decompositions: List of ranked decompositions (already sorted by score)

    Returns:
        A synthetic CompoundDecomposition with best left + best right, or None
    """
    if len(decompositions) < 2:
        return None  # Need at least 2 decomps to cross-match

    # Collect all unique left parts with their best individual scores
    best_left = {}  # lemma_norm -> (decomposition, individual_score)
    for decomp in decompositions:
        lemma_norm = normalize_greek(decomp.left_lemma.lower())

        # Score left part independently using stored fuzzy match data
        left_score = score_individual_part(decomp.left_matches, decomp.left_pos)

        if lemma_norm not in best_left or left_score > best_left[lemma_norm][1]:
            best_left[lemma_norm] = (decomp, left_score)

    # Collect all unique right parts with their best individual scores
    best_right = {}  # lemma_norm -> (decomposition, individual_score)
    for decomp in decompositions:
        lemma_norm = normalize_greek(decomp.right_lemma.lower())

        # Score right part independently using stored fuzzy match data
        right_score = score_individual_part(decomp.right_matches, decomp.right_pos)

        if lemma_norm not in best_right or right_score > best_right[lemma_norm][1]:
            best_right[lemma_norm] = (decomp, right_score)

    # Find the best left+right combination
    best_combined_score = decompositions[0].score  # Must beat or tie current best
    best_left_decomp = None
    best_right_decomp = None

    for left_lemma, (left_decomp, left_score) in best_left.items():
        for right_lemma, (right_decomp, right_score) in best_right.items():
            # Skip if it's the same decomposition
            if left_decomp == right_decomp:
                continue

            # Combined score from individual part scores
            combined_score = left_score + right_score

            # Allow ties (>=) because cross-match may have both correct parts
            # even if score is equal to current best
            if combined_score >= best_combined_score:
                best_combined_score = combined_score
                best_left_decomp = left_decomp
                best_right_decomp = right_decomp

    # Create synthetic decomposition if we found a better combination
    if best_left_decomp and best_right_decomp:
        return CompoundDecomposition(
            original=best_left_decomp.original,
            left_form=best_left_decomp.left_form,
            left_lemma=best_left_decomp.left_lemma,
            left_pos=best_left_decomp.left_pos,
            left_features=best_left_decomp.left_features,
            right_form=best_right_decomp.right_form,
            right_lemma=best_right_decomp.right_lemma,
            right_pos=best_right_decomp.right_pos,
            right_features=best_right_decomp.right_features,
            split_point=best_left_decomp.split_point,  # Use left's split point
            score=best_combined_score,
            left_matches=best_left_decomp.left_matches,
            right_matches=best_right_decomp.right_matches
        )

    return None


def load_valid_lemmas_and_words(db_conn: sqlite3.Connection) -> tuple[Set[str], Set[str], Set[str]]:
    """Load valid lemmas AND actual word forms from Perseus database, with normalized versions"""
    lemmas = set()
    actual_words = set()
    lemmas_normalized = set()  # NEW: normalized versions for matching

    try:
        # Get dictionary headwords (lemmas)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dictionary_entries'"
        )
        if cursor.fetchone():
            cursor = db_conn.execute(
                "SELECT DISTINCT headword FROM dictionary_entries "
                "WHERE headword IS NOT NULL AND headword != '' AND language = 'greek'"
            )
            for row in cursor:
                lemma = row[0].lower()
                lemmas.add(lemma)
                lemmas_normalized.add(normalize_greek(lemma))  # Add normalized version

        # Get actual corpus words
        cursor = db_conn.execute("SELECT DISTINCT word FROM words WHERE LENGTH(word) >= 3")
        for row in cursor:
            word = row[0].lower()
            actual_words.add(word)
            lemmas.add(word)  # Also add to lemmas
            lemmas_normalized.add(normalize_greek(word))  # Add normalized version

        print(f"  ✓ Loaded {len(lemmas)} valid lemmas ({len(lemmas_normalized)} normalized) and {len(actual_words)} corpus words for validation")
    except Exception as e:
        print(f"  Warning: Could not load data: {e}")

    return lemmas, actual_words, lemmas_normalized


def analyze_compounds_batch(
    words: List[str],
    nlp,
    valid_lemmas: Set[str],
    lemmas_normalized: Set[str],
    min_split: int,
    worker_id: int = None
) -> Dict[str, List[CompoundDecomposition]]:
    """
    Efficiently analyze multiple words for compound structure using batched CLTK calls.
    Returns dict mapping word -> list of decompositions.
    Uses normalized (no diacritics) matching to catch CLTK output like "τροπος" matching Perseus "τρόπος".

    OPTIMIZED: Builds prefix index once for all fuzzy matching operations.
    PHASE 1: Uses compound stem database for stem-aware matching.
    """
    worker_label = f"[W{worker_id}] " if worker_id else ""

    # ENSEMBLE APPROACH: Load all data sources (one-time cost)
    print(f"  {worker_label}Loading compound stem database...")
    stem_database = load_compound_stems()

    print(f"  {worker_label}Loading reverse morphology...")
    reverse_morphology = load_reverse_morphology()

    print(f"  {worker_label}Building lemma frequency database...")
    # Build from Perseus database
    import sqlite3
    db_paths = [
        Path(__file__).parent.parent / 'data-prep' / 'perseus_texts_extended.db',
        Path(__file__).parent.parent / 'data-prep' / 'perseus_texts_full.db',
        Path(__file__).parent.parent / 'data-prep' / 'perseus_texts_sample.db',
    ]
    lemma_freq = {}
    for db_path in db_paths:
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT lemma, COUNT(*) as freq
                FROM lemma_map
                WHERE lemma IS NOT NULL
                GROUP BY lemma
            """)
            for lemma, freq in cursor.fetchall():
                norm = normalize_greek(lemma.lower())
                if norm not in lemma_freq or freq > lemma_freq[norm][1]:
                    lemma_freq[norm] = (lemma, freq)
            conn.close()
            print(f"  {worker_label}✓ Loaded {len(lemma_freq):,} lemma frequencies")
            break

    # Build prefix index for fast fuzzy matching (one-time cost)
    print(f"  {worker_label}Building prefix index for fuzzy matching...")
    prefix_index = build_prefix_index(valid_lemmas, prefix_len=3)
    print(f"  {worker_label}✓ Indexed {len(prefix_index)} unique 3-char prefixes")

    # Collect all unique word parts that need analysis
    parts_to_analyze = set()
    word_splits = {}  # word -> list of (left, right) tuples

    for word in words:
        word_clean = word.strip()

        # Skip words with hyphens or too short
        if '-' in word_clean or len(word_clean) < min_split * 2:
            continue

        splits = []
        for i in range(min_split, len(word_clean) - min_split + 1):
            left = word_clean[:i]
            right = word_clean[i:]
            splits.append((left, right))
            parts_to_analyze.add(left)
            parts_to_analyze.add(right)

        if splits:
            word_splits[word_clean] = splits

    if not parts_to_analyze:
        return {}

    # Batch analyze all parts at once
    parts_list = sorted(parts_to_analyze)
    parts_analysis = {}
    total_parts = len(parts_list)

    batch_size = 100
    for i in range(0, len(parts_list), batch_size):
        batch = parts_list[i:i+batch_size]
        batch_text = " ".join(batch)

        try:
            doc = nlp.analyze(batch_text)
            for j, word_obj in enumerate(doc.words):
                if j < len(batch):
                    parts_analysis[batch[j]] = word_obj
        except Exception:
            pass

        # Progress update for compound part analysis
        processed = min(i + batch_size, total_parts)
        if processed % 500 == 0 or processed == total_parts:
            pct = (processed / total_parts) * 100
            print(f"  {worker_label}Analyzing parts: {processed}/{total_parts} ({pct:.0f}%)")

    # Now build compound decompositions using cached analyses
    results = {}
    total_candidates = len(word_splits)
    processed_candidates = 0

    print(f"\n  {worker_label}Validating {total_candidates} compound candidates...")

    for word, splits in word_splits.items():
        decompositions = []

        for left, right in splits:
            # Get cached analysis
            if left not in parts_analysis or right not in parts_analysis:
                continue

            left_word = parts_analysis[left]
            right_word = parts_analysis[right]

            left_lemma = left_word.lemma if hasattr(left_word, 'lemma') else None
            right_lemma = right_word.lemma if hasattr(right_word, 'lemma') else None

            # Must have both lemmas
            if not (left_lemma and right_lemma):
                continue

            # ENSEMBLE APPROACH: Get lemma candidates using ALL data sources
            # This bypasses CLTK's imperfect lemmatization by working with fragments directly
            # Combines: Perseus reverse morphology + stem database + frequency-weighted prefix matching
            left_matches = get_ensemble_lemma_candidates(
                left, reverse_morphology, stem_database, lemma_freq, top_n=10
            )
            right_matches = get_ensemble_lemma_candidates(
                right, reverse_morphology, stem_database, lemma_freq, top_n=10
            )

            # IMPROVED: Don't require Perseus matches - accept all CLTK lemmatizations
            # This allows compound decomposition for proper names and rare words
            # Use fuzzy match if available, otherwise use CLTK's lemma directly
            if left_matches:
                left_best_lemma = left_matches[0][0]
            else:
                left_best_lemma = left_lemma  # Use CLTK lemma directly

            if right_matches:
                right_best_lemma = right_matches[0][0]
            else:
                right_best_lemma = right_lemma  # Use CLTK lemma directly

            # Extract morphological features
            left_pos = str(left_word.upos.tag) if hasattr(left_word, 'upos') and left_word.upos else ''
            right_pos = str(right_word.upos.tag) if hasattr(right_word, 'upos') and right_word.upos else ''

            left_feats = format_morphology(
                left_word.upos if hasattr(left_word, 'upos') else None,
                left_word.features if hasattr(left_word, 'features') else None
            )
            right_feats = format_morphology(
                right_word.upos if hasattr(right_word, 'upos') else None,
                right_word.features if hasattr(right_word, 'features') else None
            )

            # Calculate quality score for ranking
            decomp_score = score_decomposition(
                original=word,
                split_point=len(left),
                left_pos=left_pos,
                right_pos=right_pos,
                left_matches=left_matches,
                right_matches=right_matches
            )

            decompositions.append(CompoundDecomposition(
                original=word,
                left_form=left,
                left_lemma=left_best_lemma,  # Use fuzzy-matched lemma
                left_pos=left_pos,
                left_features=left_feats,
                right_form=right,
                right_lemma=right_best_lemma,  # Use fuzzy-matched lemma
                right_pos=right_pos,
                right_features=right_feats,
                split_point=len(left),
                score=decomp_score,
                left_matches=left_matches,  # Store for cross-decomposition scoring
                right_matches=right_matches
            ))

        if decompositions:
            # Sort by score (highest first)
            decompositions.sort(key=lambda d: d.score, reverse=True)

            # CROSS-DECOMPOSITION: Find best left + best right across ALL splits
            # This handles cases where the correct parts are in different decompositions
            cross_match = find_best_cross_decomposition(decompositions)
            if cross_match:
                # Insert cross-match at the top if it's better than any single decomp
                if cross_match.score > decompositions[0].score:
                    decompositions.insert(0, cross_match)

            results[word] = decompositions

        # Progress update for candidate validation
        processed_candidates += 1
        if processed_candidates % 100 == 0 or processed_candidates == total_candidates:
            pct = (processed_candidates / total_candidates) * 100
            print(f"  {worker_label}Validated: {processed_candidates}/{total_candidates} ({pct:.0f}%)")

    return results


def format_compound_definition(decompositions: List[CompoundDecomposition], max_results: int = 5) -> str:
    """
    Format compound decompositions as a user-friendly definition string.

    Extracts unique left and right lemmas from all decompositions,
    preserving score-based ordering.

    Args:
        decompositions: List of ranked decompositions (sorted by score)
        max_results: Maximum number of unique lemmas per part to display

    Returns:
        Formatted string: "Compound parts possible lemma matches: (a,b,c,d,e) (f,g,h,i,j)"
    """
    if not decompositions:
        return ""

    # Collect unique left lemmas in score order (best first)
    left_lemmas_seen = set()
    left_lemmas = []
    for decomp in decompositions:
        # Skip blank or single-character lemmas
        if not decomp.left_lemma or len(decomp.left_lemma.strip()) <= 1:
            continue
        left_norm = normalize_greek(decomp.left_lemma.lower())
        if left_norm not in left_lemmas_seen:
            left_lemmas_seen.add(left_norm)
            left_lemmas.append(decomp.left_lemma)
            if len(left_lemmas) >= max_results:
                break

    # Collect unique right lemmas in score order (best first)
    right_lemmas_seen = set()
    right_lemmas = []
    for decomp in decompositions:
        # Skip blank or single-character lemmas
        if not decomp.right_lemma or len(decomp.right_lemma.strip()) <= 1:
            continue
        right_norm = normalize_greek(decomp.right_lemma.lower())
        if right_norm not in right_lemmas_seen:
            right_lemmas_seen.add(right_norm)
            right_lemmas.append(decomp.right_lemma)
            if len(right_lemmas) >= max_results:
                break

    # Format as: "Compound parts possible lemma matches: (a,b,c) (d,e,f)"
    left_part = "(" + ", ".join(left_lemmas) + ")"
    right_part = "(" + ", ".join(right_lemmas) + ")"

    return f"Compound parts possible matches: {left_part} - {right_part}"


def generate_compounds(
    nlp,
    morphology_results: List[MorphologyResult],
    valid_lemmas: Set[str],
    actual_words: Set[str],
    lemmas_normalized: Set[str],
    options: ProcessingOptions,
    worker_id: int = None
) -> List[Dict[str, str]]:
    """Generate compound decompositions for words that need them (batched for efficiency)"""

    # Find words that need compound analysis:
    # Only create compound entries if:
    # 1. The word form itself is NOT in our dictionary, AND
    # 2. CLTK failed to lemmatize it OR the lemma is also not in our dictionary
    compound_candidates = []

    for r in morphology_results:
        word_lower = r.word_form.lower()

        # Skip if word form is already in Perseus dictionary (as lemma or word)
        if word_lower in valid_lemmas:
            continue
        if word_lower in actual_words:
            continue

        # Skip if CLTK successfully lemmatized to something in Perseus
        if r.success and r.lemma:
            lemma_lower = r.lemma.lower()
            if lemma_lower in valid_lemmas or lemma_lower in actual_words:
                # Word has a known lemma in Perseus - no compound analysis needed
                continue

        # This word needs compound analysis (no known form or lemma in Perseus)
        compound_candidates.append(r.word_form)

    if not compound_candidates:
        worker_label = f"[W{worker_id}] " if worker_id else ""
        print(f"\n{worker_label}✓ No words need compound analysis")
        return []

    worker_label = f"[W{worker_id}] " if worker_id else ""
    print(f"\n{worker_label}Analyzing {len(compound_candidates)} words for compound structure...")
    print(f"  {worker_label}(Words not found in Perseus dictionary)")
    print(f"  {worker_label}Using batched analysis for maximum efficiency...")

    # Batch analyze ALL candidates at once
    word_decompositions = analyze_compounds_batch(compound_candidates, nlp, valid_lemmas, lemmas_normalized, options.min_split_length, worker_id=worker_id)

    # Convert to dictionary entries (with quality filtering)
    compound_entries = []
    filtered_count = 0
    filter_reasons = {}  # Track why things were filtered

    for word, decompositions in word_decompositions.items():
        # Quality filter: Only include decompositions with reasonable confidence
        # Skip if:
        # 1. Best decomposition score is too low (likely nonsense)
        # 2. Both parts are very short (likely wrong split)
        # 3. Neither part has Perseus matches (likely inflected forms misidentified as compounds)

        if not decompositions:
            filtered_count += 1
            filter_reasons['no_decompositions'] = filter_reasons.get('no_decompositions', 0) + 1
            continue

        best_decomp = decompositions[0]

        # Filter 1: Minimum score threshold (ensemble scores typically 100-1000+ for good matches)
        # BUT: Cross-decomposition scores can be lower, so use conservative threshold
        MIN_SCORE = 20  # Very conservative threshold - let other filters do the work
        if best_decomp.score < MIN_SCORE:
            filtered_count += 1
            filter_reasons['low_score'] = filter_reasons.get('low_score', 0) + 1
            continue

        # Filter 2: Both parts must have minimum length
        MIN_PART_LENGTH = 3
        if len(best_decomp.left_form) < MIN_PART_LENGTH or len(best_decomp.right_form) < MIN_PART_LENGTH:
            filtered_count += 1
            filter_reasons['short_parts'] = filter_reasons.get('short_parts', 0) + 1
            continue

        # Filter 3: BOTH parts should have Perseus matches for high-quality compounds
        # Exception: Allow if score is very high (>200), indicating strong evidence
        has_left_match = best_decomp.left_matches and len(best_decomp.left_matches) > 0
        has_right_match = best_decomp.right_matches and len(best_decomp.right_matches) > 0

        # Require both matches UNLESS we have very high confidence
        if not (has_left_match and has_right_match):
            # Allow through if score is exceptionally high (strong evidence from one side)
            if best_decomp.score < 200:
                filtered_count += 1
                filter_reasons['missing_matches'] = filter_reasons.get('missing_matches', 0) + 1
                continue

        # Filter 5: Reject if right part is just a particle/article
        # These are wrong splits (e.g., "στράτευμ" → στρατεύω + τε)
        PARTICLES = {'δέ', 'τε', 'κε', 'νυ', 'αὖ', 'γάρ', 'μέν', 'ἄν', 'περ', 'τοι', 'ῥα'}
        ARTICLES = {'ὁ', 'ἡ', 'τό', 'τόν', 'τήν', 'τούς', 'τάς', 'οἱ', 'αἱ', 'τά'}

        if has_right_match and best_decomp.right_matches:
            right_lemma = best_decomp.right_matches[0][0]  # Best match lemma
            if right_lemma in PARTICLES or right_lemma in ARTICLES:
                filtered_count += 1
                filter_reasons['particle_right'] = filter_reasons.get('particle_right', 0) + 1
                continue

        # Filter 6: Reject common inflected verb endings (ONLY if we have strong evidence)
        # These patterns indicate inflected forms misidentified as compounds
        # Only filter these if the left part matches a known verb lemma
        INFLECTED_VERB_ENDINGS = {
            # High confidence verb endings
            'οιντ', 'αιντ', 'ειντ',  # optative plural (e.g., γίγνοιντ)
            'ομεθ', 'ομεθα',  # 1st person plural middle (e.g., πεπλήγμεθ)
            'εται', 'νται',  # 3rd person middle/passive
            'ετο', 'ντο',  # imperfect middle/passive
            'ετ', 'ετε',  # 3rd person / 2nd plural present/imperfect
            'ομεν', 'ομαι',  # 1st person forms
        }

        word_lower = word.lower()
        has_verb_ending = any(word_lower.endswith(ending) for ending in INFLECTED_VERB_ENDINGS)

        if has_verb_ending and has_left_match and best_decomp.left_matches:
            # Check if left part is close to the full lemma (suggesting inflection, not compound)
            left_lemma = best_decomp.left_matches[0][0].lower()
            left_form = best_decomp.left_form.lower()

            # If left form IS the lemma (or very close), this is inflected not compound
            if left_form == left_lemma or normalize_greek(left_form) == normalize_greek(left_lemma):
                filtered_count += 1
                filter_reasons['inflected_verb_lemma_match'] = filter_reasons.get('inflected_verb_lemma_match', 0) + 1
                continue

            # Also filter if the left form is much longer than would be expected for a compound stem
            # Real compound stems are usually short (e.g., "ἱππο-", "χρυσ-")
            # Inflected forms have the full verb stem (e.g., "ἱκετεύ-" from ἱκετεύω)
            if len(left_form) > len(word_lower) * 0.75:  # Left part is >75% of word
                filtered_count += 1
                filter_reasons['inflected_verb_long_left'] = filter_reasons.get('inflected_verb_long_left', 0) + 1
                continue

        # Format definition for final checks
        definition = format_compound_definition(decompositions)

        # Filter 7: Final check - reject if formatted definition has empty parts
        # This catches edge cases where lemmas got filtered out during formatting
        if '()' in definition:
            filtered_count += 1
            filter_reasons['empty_parens'] = filter_reasons.get('empty_parens', 0) + 1
            continue

        compound_entries.append({
            'word_form': word.lower(),
            'lemma': word.lower(),
            'definition': definition,
            'language': 'greek'
        })

    compounds_found = len(compound_entries)
    worker_label = f"[W{worker_id}] " if worker_id else ""
    print(f"\n{worker_label}✓ Found {compounds_found} compound words ({compounds_found/len(compound_candidates)*100:.1f}% of candidates)")
    if filtered_count > 0:
        print(f"  {worker_label}Filtered out {filtered_count} low-quality decompositions")
        if filter_reasons:
            print(f"  {worker_label}Filter breakdown:")
            for reason, count in sorted(filter_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"    {worker_label}{reason}: {count}")
    return compound_entries


def save_full_analysis(results: List[MorphologyResult], output_file: Path):
    """Save detailed CLTK analysis for debugging"""
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['word_form', 'lemma', 'pos', 'features', 'success', 'error'])
        for r in results:
            writer.writerow([
                r.word_form,
                r.lemma or '',
                r.pos or '',
                str(r.features) if r.features else '',
                r.success,
                r.error or ''
            ])
    print(f"  ✓ Saved full analysis: {output_file.name}")


def save_morphology_csv(results: List[MorphologyResult], output_file: Path) -> int:
    """Save morphology mappings to CSV"""
    count = 0
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['word_form', 'lemma', 'morph_info', 'language', 'confidence', 'source_name'])

        for r in results:
            if r.success and r.lemma:
                morph_info = format_morphology(r.pos, r.features)
                writer.writerow([
                    r.word_form.lower(),
                    r.lemma.lower(),
                    morph_info,
                    'greek',
                    0.85,
                    'CLTK Stanza'
                ])
                count += 1

    return count


def save_dictionary_csv(compound_entries: List[Dict[str, str]], output_file: Path) -> int:
    """Save compound decompositions to dictionary CSV (always create file)"""
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['lemma', 'definition', 'language', 'source_name'])
        writer.writeheader()
        if compound_entries:
            # Convert entries to proper dictionary format
            for entry in compound_entries:
                writer.writerow({
                    'lemma': entry.get('lemma', entry.get('word_form', '')),
                    'definition': entry['definition'],
                    'language': entry['language'],
                    'source_name': 'CLTK ensemble'
                })

    return len(compound_entries)


def create_output_package(
    morphology_file: Path,
    dictionary_file: Path,
    output_zip: Path
):
    """Package output files into a ZIP (always includes both files)"""
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(morphology_file, 'morphology.csv')
        zipf.write(dictionary_file, 'dictionary.csv')

    # Cleanup temp files
    morphology_file.unlink()
    dictionary_file.unlink()


def parse_arguments():
    """Parse command line arguments"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_csv = Path(sys.argv[1])
    if not input_csv.exists():
        print(f"ERROR: Input file not found: {input_csv}")
        sys.exit(1)

    options = ProcessingOptions()

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--min-split' and i + 1 < len(sys.argv):
            options.min_split_length = int(sys.argv[i + 1])
            i += 2
        elif arg == '--workers' and i + 1 < len(sys.argv):
            options.num_workers = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    return input_csv, options


def main():
    input_csv, options = parse_arguments()

    # Setup output files
    output_base = input_csv.stem
    output_zip = Path(f"{output_base}_dictionary.zip")
    full_analysis_file = Path(f"{output_base}_cltk_full_analysis.csv")
    morphology_csv = Path('morphology.csv')
    dictionary_csv = Path('dictionary.csv')

    print("="*70)
    print(f"CLTK Dictionary Generator: {input_csv.name}")
    print("="*70)

    # Check CLTK installation
    if not check_cltk_installation():
        sys.exit(1)

    # Load author/work pairs
    print(f"\nReading works from {input_csv}...")
    works_by_author = load_author_works(input_csv)
    total_works = sum(len(works) for works in works_by_author.values())
    print(f"  ✓ Found {len(works_by_author)} authors with {total_works} total works")

    # Connect to database
    db_path = find_database()
    if not db_path:
        print("\nERROR: No database found")
        print("Looked for: perseus_texts_extended.db, perseus_texts_full.db, perseus_texts_sample.db")
        sys.exit(1)

    print(f"\nUsing database: {db_path.name}")
    if options.num_workers > 1:
        print(f"Parallel processing enabled: {options.num_workers} workers")

    # Process all works (extract + CLTK morphology + compounds)
    results, compound_entries, found_works = process_all_works(db_path, works_by_author, options.num_workers, options.min_split_length)

    # Verify all works were found
    missing_works = []
    for author, requested in works_by_author.items():
        found = found_works.get(author, set())
        for work in requested:
            if work not in found:
                missing_works.append(f"{author} - {work}")

    if missing_works:
        print("\nERROR: Could not find the following works in database:")
        for missing in missing_works:
            print(f"  - {missing}")
        sys.exit(1)

    total_found_works = sum(len(works) for works in found_works.values())

    if len(results) == 0:
        print("ERROR: No words processed")
        sys.exit(1)

    # Analyze results
    successful = sum(1 for r in results if r.success)
    has_lemma = sum(1 for r in results if r.success and r.lemma)
    unique_lemmas = set(r.lemma for r in results if r.success and r.lemma)

    print(f"\nMorphology Results:")
    print(f"  Successful: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"  With lemma: {has_lemma}/{len(results)} ({has_lemma/len(results)*100:.1f}%)")
    print(f"  Unique lemmas: {len(unique_lemmas)}")

    # Save full analysis
    save_full_analysis(results, full_analysis_file)

    # Compound analysis already done in parallel workers
    print(f"\n✓ Found {len(compound_entries)} compound word decompositions")

    # Create output package
    print("\n" + "="*70)
    print("Creating Output Package")
    print("="*70)

    # Save morphology CSV
    print(f"\nWriting morphology.csv...")
    morph_count = save_morphology_csv(results, morphology_csv)
    print(f"  ✓ Wrote {morph_count} morphology mappings")

    # Save dictionary CSV (always create, even if empty)
    print(f"\nWriting dictionary.csv...")
    dict_count = save_dictionary_csv(compound_entries, dictionary_csv)
    if dict_count > 0:
        print(f"  ✓ Wrote {dict_count} compound decompositions")
    else:
        print(f"  ✓ Created empty dictionary (no compounds found)")

    # Package into ZIP
    print(f"\nPackaging into {output_zip}...")
    create_output_package(morphology_csv, dictionary_csv, output_zip)

    # Summary
    print(f"\n" + "="*70)
    print(f"✓ SUCCESS! Created {output_zip}")
    print(f"="*70)
    print(f"\nOutput files:")
    print(f"  - {output_zip} ({output_zip.stat().st_size / 1024:.0f}KB)")
    print(f"      {morph_count} morphology mappings")
    print(f"      {len(unique_lemmas)} unique lemmas")
    if dict_count > 0:
        print(f"      {dict_count} compound decompositions")
    print(f"  - {full_analysis_file.name} (full CLTK analysis for debugging)")
    print(f"\nImport {output_zip} into the app via Custom Dictionary feature!")


if __name__ == '__main__':
    # Required for multiprocessing on macOS/Windows
    mp.set_start_method('spawn', force=True)
    main()
