# Proposal: Integrating GLAUx Morphological Data into Classics Viewer

## Summary

We propose integrating the GLAUx corpus annotations (morphology, lemma, syntax) into the Classics Viewer interlinear generation pipeline. GLAUx provides 20M tokens of Ancient Greek text (8th c. BC to 4th c. AD) with high-accuracy automatic annotations — 97.2% morphology, 98.8% lemma, ~80% syntax — covering the same source texts we already use (Perseus, First1KGreek). Using GLAUx as a primary morphological data source would improve interlinear quality and reduce our dependence on runtime NLP processing with Stanza.

## Current Pipeline

Our interlinear generation currently uses a three-tier morphological priority:

1. **Perseus treebank data** — Gold-standard human annotations. Highest quality but limited coverage (~250K sentences across ~74 works).
2. **Wiktionary dictionary lookup** — 4.7M morphological forms extracted from Wiktionary. Good coverage but no contextual disambiguation.
3. **Stanza NLP** — Machine-generated sentence-level analysis. Provides full coverage as a fallback but lower accuracy than curated sources and slow to run (13+ hours for all Greek works).

## What GLAUx Offers

| Feature | GLAUx | Our Current Sources |
|---------|-------|-------------------|
| Morphology accuracy | 97.2% | Treebank: ~99%, Stanza: ~85-90% |
| Lemma accuracy | 98.8% | Treebank: ~99%, Dict: ~95%, Stanza: ~90% |
| Syntax accuracy | ~80% | Treebank: ~99%, Stanza: ~80% |
| Token coverage | 20M tokens | Treebank: ~1M, Dict: 4.7M forms, Stanza: unlimited |
| Text coverage | 8th c. BC - 4th c. AD | Same period |
| Source texts | Perseus, First1KGreek, Wikisource | Perseus, First1KGreek |
| Case annotation | Yes (morphology layer) | Yes (all three tiers) |
| Data format | XML | Treebank: CoNLL-U, Dict: JSON, Stanza: runtime |
| License | CC BY-SA 4.0 | Various open licenses |
| Animacy annotation | Yes (89.2%) | No |
| Word sense annotation | Yes (82.0%) | No |

## Proposed Integration

### Tier Placement

GLAUx would slot in as **Tier 2**, between treebank and dictionary:

1. **Perseus treebank** — Gold-standard (unchanged)
2. **GLAUx annotations** — High-accuracy automatic annotations (NEW)
3. **Wiktionary dictionary** — Form-level lookup without context (unchanged)
4. **Stanza NLP** — Runtime fallback (unchanged, but invoked far less often)

### Implementation Approach

#### Phase 1: Data Extraction
- Download GLAUx XML corpus from GitHub (`alekkeersmaekers/glaux`)
- Parse XML to extract per-token annotations: lemma, POS, morphological features (case, number, gender, tense, mood, voice), dependency relation, head
- Map GLAUx text references to our book/line/word_position identifiers
- Store as a lookup JSON or SQLite table indexed by work ID + line + word position

#### Phase 2: Pipeline Integration
- During interlinear generation (`generate_interlinear.py`), after checking treebank data, check GLAUx annotations before falling back to dictionary/Stanza
- GLAUx annotations would use the treebank delimiter (`~*`) since they follow the same AGDT guidelines, or a new delimiter (`~G`) to distinguish the source
- Mark GLAUx-sourced annotations in the UI (e.g., a distinct styling between treebank bold and Stanza italic)

#### Phase 3: Reduced Stanza Dependency
- With GLAUx covering 20M tokens, Stanza would only be needed for texts outside the GLAUx corpus
- This would significantly reduce interlinear generation time (currently 13+ hours for all Greek)
- Build pipeline becomes more deterministic — pre-computed annotations vs. runtime NLP

### Text Alignment Challenge

#### Work-Level Alignment (Solved)

GLAUx is already cloned at `data-sources/glaux/` (1,421 XML files). The `metadata.txt` file contains **TLG numbers** (e.g., `0012-001` = Homer Iliad) that map directly to our `tlg` identifiers. Work-level alignment is straightforward — no fuzzy matching needed.

#### GLAUx XML Data Format

Each word in the XML provides:
- `form` — the Greek word as it appears in text
- `postag` — 9-character morphological tag (AGDT format), where **position 8 is case**: `n`=nom, `g`=gen, `d`=dat, `a`=acc, `v`=voc
- `lemma` — dictionary headword
- `line` — line reference (e.g., `1.1`, `1.2`)
- `head` / `relation` — dependency tree structure
- `animacy` / `sense` — bonus annotations (not available from our other sources)

Example: `postag="n-s---na-"` = noun, singular, neuter, **accusative**. Case is directly extractable at character index 7.

#### Token-Level Alignment (Requires Validation)

While work-level and line-level alignment is straightforward via TLG IDs and the `line` attribute, token boundaries within a line may differ:
- Elisions: `τ'` vs `τε`, `δ'` vs `δέ`
- Crasis: `κἀγώ` = `καὶ ἐγώ`
- Punctuation tokens in GLAUx (commas, periods) that our pipeline skips
- Different editions or normalizations

See **Token Alignment Validation** section below for the sliding-window verification approach.

## Benefits

1. **Better case detection** — 97.2% morphology accuracy means more reliable case annotations for the new case color coding feature
2. **Faster builds** — Less reliance on Stanza (13+ hours) for Greek interlinear generation
3. **More consistent results** — Pre-computed annotations are deterministic, unlike Stanza which can vary between runs
4. **Additional features** — Animacy (89.2%) and word sense (82.0%) annotations could enable future UI features
5. **Broader coverage** — GLAUx includes Wikisource texts not in our current corpus

## Licensing Considerations

GLAUx uses **CC BY-SA 4.0**. This requires:
- **Attribution** — Credit GLAUx/Keersmaekers in the app (e.g., "Morphological data from GLAUx corpus" in About screen)
- **ShareAlike** — Derivative works of the data must use a compatible license. Since we're using the annotations as input data (not redistributing the corpus), and our app is a reader (not a corpus tool), this should be compatible with commercial use. However, this should be confirmed with the GLAUx team.

Note: Some texts in GLAUx use CC BY-NC. These would need to be identified and either excluded or handled separately.

## Token Alignment Validation

### The Problem

Token boundaries between GLAUx and our pipeline will not always match 1:1. Common mismatches include:

- **Elisions**: `τ'` vs `τε`, `δ'` vs `δέ`, `κ'` vs `κε` — GLAUx may treat elided forms as one token or two
- **Crasis**: `κἀγώ` (= καὶ ἐγώ) — one surface token, two logical words
- **Enclitics/proclitics**: `μέν`, `δέ`, `τε` may attach to adjacent words differently
- **Punctuation handling**: Some tokenizers split on punctuation, others don't
- **Movable nu**: `ἐστίν` vs `ἐστί` — same word, different surface forms
- **Breathing/accent normalization**: `ὁ` vs `ο` if diacritics differ

An off-by-one error at position 3 would cascade through the entire line, assigning every subsequent word the wrong morphology.

### Validation Strategy: Verify-Then-Apply

Never blindly assign GLAUx annotations by position index. Instead, for each word:

1. **Normalize both tokens** — strip diacritics (accents, breathing, iota subscript) from both the GLAUx token and our word to get a base form for comparison
2. **Exact match check** — if normalized forms match, accept the annotation
3. **Fuzzy match with window** — if no exact match at position N, look at positions N-1 and N+1 in GLAUx for a match (handles off-by-one from a split/merged token earlier in the line)
4. **Skip on mismatch** — if no match is found within the window, skip this word (fall through to dictionary/Stanza) rather than applying wrong morphology
5. **Log mismatches** — track alignment failures per work for quality reporting

### Implementation: Sliding Window Alignment

```python
def align_glaux_to_line(our_words, glaux_tokens):
    """
    Align GLAUx tokens to our word list using verified matching.
    Returns list of (word_index, glaux_annotation) pairs.
    Only returns matches where the Greek word actually matches.
    """
    alignments = []
    glaux_offset = 0  # tracks cumulative offset from splits/merges

    for i, our_word in enumerate(our_words):
        our_norm = normalize(our_word)
        best_match = None

        # Check positions within a window around expected position
        for delta in [0, -1, 1, -2, 2]:
            g_idx = i + glaux_offset + delta
            if 0 <= g_idx < len(glaux_tokens):
                glaux_norm = normalize(glaux_tokens[g_idx].form)
                if our_norm == glaux_norm:
                    best_match = (g_idx, delta)
                    break
                # Also check if GLAUx token is a substring (elision)
                if is_elision_match(our_norm, glaux_norm):
                    best_match = (g_idx, delta)
                    break

        if best_match:
            g_idx, delta = best_match
            glaux_offset += delta  # adjust running offset
            alignments.append((i, glaux_tokens[g_idx].annotation))
        # else: no match, word falls through to dictionary/Stanza

    return alignments
```

### Normalization Function

```python
import unicodedata

def normalize(word):
    """Strip all diacritics, lowercase, for comparison only."""
    # NFD decompose, then strip combining characters
    decomposed = unicodedata.normalize('NFD', word)
    stripped = ''.join(c for c in decomposed
                       if unicodedata.category(c) not in ('Mn',))  # Mn = combining marks
    return stripped.lower().replace("'", "").replace("ʼ", "")

def is_elision_match(our_norm, glaux_norm):
    """Check if one is an elided form of the other."""
    # e.g., our "τ" matches glaux "τε", or our "δ" matches glaux "δε"
    if len(our_norm) >= 1 and len(glaux_norm) >= 2:
        return glaux_norm.startswith(our_norm)
    if len(glaux_norm) >= 1 and len(our_norm) >= 2:
        return our_norm.startswith(glaux_norm)
    return False
```

### Quality Metrics

For each work, track and report:
- **Match rate**: % of words that found a GLAUx match (target: >90%)
- **Offset corrections**: how many times the sliding window had to adjust (indicates tokenization differences)
- **Consecutive mismatches**: flag lines where >3 consecutive words fail to match (likely a structural alignment issue, not just token differences)

### Rejection Criteria

Reject GLAUx data for an entire line/section if:
- Match rate drops below 70% for that line
- More than 5 consecutive words fail to match
- The GLAUx token count differs from ours by more than 30%

This ensures we never apply systematically wrong annotations — we'd rather fall through to Stanza than assign accusative morphology to a nominative word because of a shifted index.

## Effort Estimate

| Task | Effort |
|------|--------|
| GLAUx XML parser | 1-2 days |
| Text alignment / CTS mapping | 2-3 days |
| Token validation + sliding window aligner | 2-3 days |
| Pipeline integration in generate_interlinear.py | 1 day |
| Testing, quality metrics, edge case fixes | 2-3 days |
| **Total** | **8-12 days** |

## Next Steps

1. Download and explore GLAUx XML data structure in detail
2. Assess text overlap — how many of our 2,285 works have GLAUx coverage
3. Prototype the CTS URN alignment for a few works (e.g., Homer's Iliad)
4. Contact Alek Keersmaekers to discuss integration and confirm licensing compatibility
5. Build and validate with a test set before full integration

## References

- GLAUx corpus: https://github.com/alekkeersmaekers/glaux
- GLAUx NLP tools: https://github.com/alekkeersmaekers/glaux-nlp
- GLAUx web interface: https://glaux.be/
- Paper: Keersmaekers, A. (2021). "The GLAUx corpus: methodological issues in designing a long-term, diverse, multi-layered corpus of Ancient Greek"
