# σώφρων Lemma Resolution Analysis — Aeschines, Against Timarchus

## Summary

Investigation of how all forms of σώφρων and its cognates are resolved in the Greek interlinear generation for Aeschines' *Against Timarchus* (`tlg0026.tlg001.001`) in the extended database.

**Result**: 15 of 16 forms resolve correctly. One form (`σωφρονίζει`) maps to the wrong lemma (`παιδεύω` instead of `σωφρονίζω`) due to a bad entry in the OGA (Opera Graeca Adnotata) corpus data.

---

## All σώφρων-Family Occurrences in Against Timarchus

27 total occurrences across 16 distinct inflected forms:

| Line | Form | Expected Lemma | Actual Lemma | Correct? |
|------|------|---------------|--------------|----------|
| 8 | ἐσωφρόνει | σωφρονέω | σωφρονέω | Yes |
| 18 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 19 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 26 | σωφρονεῖν | σωφρονέω | σωφρονέω | Yes |
| 29 | σωφρονεστάτῃ | σώφρων | σώφρων | Yes |
| 69 | σωφρόνων | σώφρων | σώφρων | Yes |
| 79 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 88 | σώφρονες | σώφρων | σώφρων | Yes |
| 178 | σώφρονος | σώφρων | σώφρων | Yes |
| 443 | σώφρονι | σώφρων | σώφρων | Yes |
| 447 | σώφρονος | σώφρων | σώφρων | Yes |
| 450 | σωφρονῇς | σωφρονέω | σωφρονέω | Yes |
| 489 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 496 | σωφρόνων | σώφρων | σώφρων | Yes |
| 506 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 507 | σωφρονίζει | σωφρονίζω | **παιδεύω** | **NO** |
| 508 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 509 | σώφρων | σώφρων | σώφρων | Yes |
| 511 | σώφρονας | σώφρων | σώφρων | Yes |
| 542 | σωφρόνως | σώφρων | σώφρων | Yes |
| 566 | σωφρονεστάτων | σώφρων | σώφρων | Yes |
| 574 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 579 | σωφροσύνης | σωφροσύνη | σωφροσύνη | Yes |
| 654 | σωφρόνων | σώφρων | σώφρων | Yes |
| 656 | σεσωφρονηκὼς | σωφρονέω | σωφρονέω | Yes |
| 659 | σωφροσύνην | σωφροσύνη | σωφροσύνη | Yes |
| 682 | σωφροσύνην | σωφροσύνη | σωφροσύνη | Yes |

---

## Correctly Resolved Forms — How They Resolve

### Direct lemma_map matches (high confidence)
- `σώφρων` → σώφρων (conf=1.0, LSJ direct dictionary match)
- `σωφροσύνης` → σωφροσύνη (conf=1.0, lemma_map)
- `σωφροσύνην` → σωφροσύνη (conf=1.0, lemma_map)
- `σωφρονεῖν` → σωφρονέω (conf=0.95, lemma_map)
- `σώφρονες` → σώφρων (conf=0.9, lemma_map)
- `σώφρονος` → σώφρων (conf=0.95, lemma_map)
- `σώφρονι` → σώφρων (conf=0.9, lemma_map)
- `σώφρονας` → σώφρων (conf=0.95, lemma_map)
- `σωφρόνων` → σώφρων (conf=0.95, lemma_map)
- `σωφρόνως` → σώφρων (conf=0.95, lemma_map)
- `σωφρονεστάτων` → σώφρων (conf=0.95, lemma_map)
- `σωφρονῇς` → σωφρονέω (conf=0.9, lemma_map)

### Ultra-normalized fallback matches (OGA, correct)
- `ἐσωφρόνει` → σωφρονέω (conf=0.42, via ultra-normalized OGA `εσωφρονει → σωφρονέω`)
- `σεσωφρονηκὼς` → σωφρονέω (conf=0.42, via ultra-normalized OGA `σεσωφρονηκωσ → σωφρονέω`)
- `σωφρονεστάτῃ` → σώφρων (conf=0.42, via ultra-normalized OGA `σωφρονεστατη → σώφρων`)

---

## The Incorrect Resolution: σωφρονίζει → παιδεύω

### Resolution path (step by step)

1. **Step 1 — Direct dictionary lookup**: `σωφρονίζει` is not a dictionary headword. No match.
2. **Step 1b — Acute variant**: No grave accents present. Skipped.
3. **Step 1c — Lunate sigma**: No lunate sigma. Skipped.
4. **Step 2 — Lemma map lookup**: `σωφρονίζει` (with diacritics) is not in `lemma_map`. No match.
5. **Step 2b — Acute variant in lemma_map**: N/A. Skipped.
6. **Step 2c — Elision**: Word doesn't end with apostrophe. Skipped.
7. **Step 2.5 — Morphologically related forms**: Word doesn't end in -ων/-οι/-ος. Skipped.
8. **Step 2.6 — Compound decomposition**: `decompose_compound_word()` returns None (no prefix match yields a valid stem).
9. **Step 2.7 — Ultra-normalized fallback**: Ultra-normalizes to `σωφρονιζει`. Finds OGA entry:
   - `σωφρονιζει → παιδεύω` (conf=0.7, source=oga)
   - **This is a data error in the OGA corpus.**

### Why the correct lemma is not found

- `σωφρονίζω` **does** exist as an LSJ dictionary headword.
- `σωφρονίζειν` → σωφρονίζω exists in lemma_map (perseus_treebank, conf=0.95).
- Many other OGA forms correctly map to σωφρονίζω:
  - `σωφρονιζων → σωφρονίζω`
  - `σωφρονιζομενων → σωφρονίζω`
  - `εσωφρονισε → σωφρονίζω`
  - etc.
- But `σωφρονιζει` specifically is incorrectly mapped to `παιδεύω` in the OGA data.

### Database evidence

```
lemma_map WHERE word_form = 'σωφρονίζει':
  (no results)

lemma_map WHERE word_form_normalized_ultra = 'σωφρονιζει':
  σωφρονιζει → παιδεύω (conf=0.7, source=oga)    ← WRONG

dictionary_entries WHERE headword = 'σωφρονίζω':
  σωφρονίζω (source=lsj)                          ← CORRECT entry exists

lemma_map WHERE lemma = 'σωφρονίζω' (sample):
  σωφρονίζω → σωφρονίζω (conf=1.0, source=lsj)
  σωφρονίζειν → σωφρονίζω (conf=0.95, source=perseus_treebank)
  σωφρονιζων → σωφρονίζω (conf=0.7, source=oga)   ← OGA correct for other forms
  ... (30+ forms, all correct except σωφρονιζει)
```

---

## Root Cause: OGA Data Quality

The OGA (Opera Graeca Adnotata) corpus is a large annotated Greek corpus (~40M tokens, 1,999 texts) used as a fallback lemmatization source. OGA entries:
- Are inserted with `INSERT OR IGNORE` (existing entries take precedence)
- Have confidence=0.7 (lower than Wiktionary=1.0 or treebank=0.95)
- Are filtered by minimum frequency (default: 3 occurrences)
- Have particle↔article cross-mapping validation

However, the OGA corpus contains **~50,000 entries that conflict with other sources** across the database. The `σωφρονιζει → παιδεύω` mapping is one such error.

The conflict arises specifically in the ultra-normalized fallback path (Step 2.7), where OGA entries stored without diacritics can be the only match found for a diacritized word form that has no exact lemma_map entry.

---

## Potential Fixes — Evaluation and Recommendation

### Recommended: Fix 3 — Filter conflicting OGA entries during import

**What**: In `insert_oga_lemmas()`, before inserting each OGA entry, check whether any non-OGA source already maps the same ultra-normalized form to a different lemma. If so, skip the OGA entry.

**Why this is the right fix**:

- It's a **data-quality fix at the source**. Bad data never enters the database, so no downstream code needs to compensate.
- It's **simple to implement** — a single EXISTS check before each INSERT in `create_perseus_database.py:9706-9892`.
- It **removes the 48,474 known-bad entries** while preserving the 287,656 non-conflicting OGA entries that provide valuable coverage for rare forms.
- It **respects the existing confidence hierarchy**. OGA (0.7) is the lowest-confidence source. When a higher-confidence source (treebank=0.95, LSJ=1.0, Wiktionary=0.95) disagrees, the higher source should win. The current INSERT OR IGNORE already enforces this for exact matches, but doesn't protect against ultra-normalized collisions — this fix closes that gap.
- It's **repeatable** — runs every build, consistent with the project's philosophy of no manual fixes.

### Viable secondary: Fix 2 — Expand Wiktionary morphology coverage

**What**: Generate more inflected forms (like `σωφρονίζει → σωφρονίζω`) from Wiktionary conjugation/declension tables so they're found at Step 2 before reaching the ultra-normalized fallback.

**Why it helps but isn't sufficient alone**:

- It addresses a real gap — `σωφρονίζει` *should* be in the lemma_map from Wiktionary conjugation data, but isn't. That's why the lookup falls through to Step 2.7 where the bad OGA entry is the only match.
- But there will always be gaps in Wiktionary coverage. Not every possible inflected form for every verb can be generated. So this fix reduces the *frequency* of the problem but doesn't *eliminate* it.
- It's a good complement to Fix 3 — fewer words reach Step 2.7, and the ones that do encounter cleaner OGA data.

### Not recommended: Fix 1 — Validate OGA entries against dictionary headwords

**What**: When an OGA word form shares a stem with a known dictionary headword, prefer that headword as the lemma over the OGA-supplied lemma.

**Why it's problematic**:

- **"Shares a stem" is hard to define algorithmically for Greek.** The stem of `σωφρονίζει` is `σωφρονιζ-`, which needs to match against the headword `σωφρονίζω`. But Greek morphology involves vowel contractions, consonant mutations, augments, and other changes that make stem matching unreliable without a full morphological analyzer — which is essentially the problem being solved.
- **False positives are likely.** Many Greek words share stems but have genuinely different lemmas (e.g., `λόγος` vs `λέγω` share the root `λεγ/λογ` but are distinct headwords). A naive stem matcher would suppress legitimate OGA entries.

### Not recommended: Fix 4 — Cross-check ultra-normalized results against dictionary headwords

**What**: In Step 2.7, when the ultra-normalized form finds an OGA mapping, also check if a dictionary headword shares the stem and prefer it.

**Why it's problematic**:

- Same stem-matching complexity as Fix 1.
- **Adds runtime complexity** to every lookup, slowing down interlinear generation for all 48.7M words in the extended database.

### Implemented: Fix 3A — OGA per-form majority vote

**What**: When the same word form maps to multiple lemmas in the OGA corpus, only keep the mapping with the highest frequency count. Simple majority wins — even 7 vs 6, the 6 is suppressed.

**Why this is needed in addition to Fix 3**: Fix 3 only catches OGA entries where a non-OGA source has an entry with the **exact same** ultra-normalized form mapping to a different lemma. Fix 3A addresses a different problem: internal inconsistency within the OGA corpus itself, where the same word form is annotated with different lemmas across different texts.

**Algorithm**:
1. Group all frequency-filtered OGA entries by word form
2. For each word form that maps to multiple lemmas, identify the lemma with the most occurrences
3. Suppress all entries whose lemma has fewer occurrences than the top lemma for that form

**Implementation**: `create_perseus_database.py`, `insert_oga_lemmas()` — majority vote runs after frequency filtering, before the insertion loop. Suppressed entries are collected in a set and skipped during insertion.

### Summary

| Fix | Effectiveness | Complexity | Risk | Status |
|-----|------|------|------|------|
| 3: Filter OGA at import | Eliminates entries conflicting with non-OGA sources | Low — one SQL check | Low — only removes entries contradicted by better sources | **Implemented** |
| 3A: Per-form majority vote | Eliminates internally inconsistent OGA mappings | Low — group by word form, keep top | Low — simple majority, ties preserved | **Implemented** |
| 2: Expand Wiktionary | Reduces fallback-to-OGA rate | Medium — morphology pipeline changes | Low | Not implemented |
| 1: Stem vs headword at import | Partial | High — Greek morphology is complex | Medium — false positives | Not recommended |
| 4: Stem vs headword at lookup | Partial | High — same complexity, plus runtime cost | Medium | Not recommended |

### Build Results (Extended Database)

OGA import statistics after both fixes:

| Metric | Count |
|---|---|
| Total OGA entries (pre-filter) | 336,132 |
| Word forms with multiple lemma candidates | 12,204 |
| Suppressed by per-form majority vote (Fix 3A) | 16,367 |
| Suppressed by ultra-normalized conflict (Fix 3) | 39,523 |
| Suppressed by particle/article filter | 2 |
| **OGA entries kept** | **280,240** |

Database sanity checks (no regressions):

| Metric | Expected | Actual |
|---|---|---|
| Authors | 778 | 778 |
| Books | ~172K | 172,794 |
| Text lines | ~3.1M | 3,131,731 |
| Words | ~48.7M | 49,189,935 |
| DB size | 13GB | 13GB |
| ZIP size | ~2.7GB | 2.8GB |
| ZIP integrity | OK | OK |

### OGA Conflict Statistics (Pre-Fix Baseline)

- **336,130** total OGA entries in the extended database (before fixes)
- **48,474** unique OGA entries (14.4%) conflict with non-OGA sources
- Full conflict listing: `OGA_CONFLICTS.csv` (21MB)

Conflicts by source (most common):

| Source | Conflicting OGA entries |
|---|---|
| Enhanced Wiktionary | 19,479 |
| Perseus Treebank | 18,384 |
| Wiktionary declensions | 17,250 |
| Wiktionary | 15,148 |
| inflection_of | 14,889 |
| Cunliffe | 5,937 |
| LSJ | 5,324 |
| Wiktionary conjugations | 3,493 |

---

## Source Files

- `data-prep/build_modules/generate_interlinear/ui_dictionary_lookup.py` — `PerseusRepository.get_all_dictionary_entries()` (lines 369-942)
- `data-prep/build_modules/generate_interlinear/generate_interlinear.py` — `InterlinearGenerator._cached_lookup_word()` (lines 1194-1364)
- `data-prep/create_perseus_database.py` — `insert_oga_lemmas()` (Fix 3, Fix 3A, particle/article filter)
