# Unicode Filtering Analysis: Impact Assessment

## Overview
This document analyzes what would break if we suppressed display of characters in text views that are not part of the Unicode set for that language (e.g., Sanskrit, Hebrew, Arabic).

## Critical Breakages

### 1. Numbers & Punctuation (Severity: CRITICAL)
**Impact**: All Arabic numerals (0-9), spaces, commas, periods, etc. would disappear

**Affected Code**:
- `TextLineAdapter.kt:67` - Line numbers rendered as text
- `OccurrenceAdapter.kt:71` - Reference text like "Homer, Iliad 1.23"

**Result**: Reference text "Homer, Iliad 1.23" would become "Homer Iliad " with all numbers and punctuation stripped.

---

### 2. Word Parsing & Click Detection (Severity: CRITICAL)
**Impact**: Character-by-character word boundary detection would fail

**Affected Code**:
- `TextLineAdapter.kt:100-158` - Word tokenization for dictionary lookups
- Currently includes hyphens, slashes, apostrophes, combining marks

**Result**:
- Dictionary lookups would break
- Words with mixed scripts (e.g., transliterated names) would be partially invisible
- Click spans would target incorrect positions

---

### 3. Occurrence Highlighting (Severity: CRITICAL)
**Impact**: Word position-based highlighting would target wrong words

**Affected Code**:
- `OccurrenceAdapter.kt:75` - Uses word positions to apply background spans
- Database stores position numbers expecting full text, not filtered text

**Result**: Highlights would appear on wrong words due to position shift after filtering.

---

### 4. Translation Display (Severity: CRITICAL)
**Impact**: English translations would disappear when viewing non-Latin script texts

**Affected Components**:
- `TranslationAdapter.kt` and translation views
- `TranslationSegmentEntity` - Stores English translation text

**Result**: Translation feature would become completely unusable. When viewing Greek/Sanskrit/Arabic texts, the English translations (which use Latin script) would be filtered out.

---

### 5. Author/Work Metadata (Severity: MODERATE)
**Impact**: Mixed-script work titles and author names would be corrupted

**Affected Data**:
- `AuthorEntity` and `WorkEntity` - Store mixed-script content
- Example: "Ῥήτορες Ἀθηναῖοι (Greek Orators)" would lose parenthetical Latin

**Result**: Work titles and author names with clarifying notes in other scripts would be incomplete.

---

## Moderate Issues

### 6. Cross-Language Citations (Severity: MODERATE)
**Impact**: Quoted text in other languages would disappear

**Examples**:
- Persian texts quoting Arabic Quran verses
- Greek texts including Latin phrases
- Scholarly annotations mixing scripts

**Affected Data**:
- `TextLineEntity.lineXml` - Preserves original TEI markup with mixed scripts

---

### 7. Diacritical Mark Complexity (Severity: MODERATE)
**Impact**: Combining marks might be incorrectly filtered

**Affected Code**:
- `TextLineAdapter.kt:110-112` - Handles combining marks across Unicode blocks
- Hebrew nikud, Arabic harakat, Sanskrit matras span different Unicode ranges

**Result**: Text rendering would break if combining marks are filtered while base characters remain.

---

### 8. Search & Dictionary Lookups (Severity: MODERATE)
**Impact**: Database lookups would fail with filtered text

**Affected Flow**:
- `onWordClick` callback passes filtered text to dictionary
- Database expects unfiltered normalized forms
- Morphology matching relies on complete word forms

**Result**: Dictionary lookups and morphological analysis would fail for partially-filtered words.

---

## Minor Issues

### 9. Font Rendering (Severity: MINOR)
**Impact**: Font fallback chains might break

**Affected Code**:
- `TextLineAdapter.kt:54-59` - Sinaiticus font loading for Greek
- `OccurrenceAdapter.kt:54-59` - Same font loading logic

**Result**: Custom font rendering might break if expected characters are filtered out.

---

### 10. Bookmarks & Navigation (Severity: MINOR)
**Impact**: Line references with mixed numeric/text content would be corrupted

**Affected Data**:
- Bookmark references stored as "Book 1, Line 23"
- Navigation labels with mixed content

---

## Technical Dependencies

### Character Position Assumptions
The text display pipeline assumes **complete character fidelity** from database → screen:

1. **Database Storage**: `TextLineEntity.lineText` stores complete text
2. **Word Parsing**: Character-by-character scanning (lines 100-158)
3. **Clickable Spans**: Applied using absolute character positions
4. **Highlighting**: Uses word position numbers that assume complete text
5. **Search**: Expects full text for pattern matching

### Coordination Requirements
Multiple systems coordinate based on unfiltered text:

- **Word positions** (database) ↔ **highlighting** (display)
- **Line numbers** (database) ↔ **references** (display)
- **Click positions** (user input) ↔ **word boundaries** (parsing)

Filtering at display time would desynchronize all of these.

---

## Recommended Alternative Approaches

Instead of runtime character filtering, consider:

### 1. Validation Warnings (Proactive)
- Detect encoding errors during database import
- Flag suspicious character patterns
- Catch corruption early in the pipeline

### 2. Character Substitution (Corrective)
- Replace known mojibake patterns
- Fix common encoding mistakes
- Maintain position integrity

### 3. Font Selection (Rendering)
- Ensure proper Unicode font coverage
- Configure font fallback chains
- Handle missing glyphs gracefully

### 4. Normalization (Already Implemented)
- Handle diacritical variations
- Canonicalize combining marks
- Preserve semantic equivalence

---

## Conclusion

**Character filtering at display time would require:**
- Complete rewrite of word parsing logic
- Rebuilding all position-based highlighting
- New coordination system between database and display
- Alternative approach for translations (cannot filter target language)
- Extensive testing for edge cases

**Estimated Impact**: 5+ major systems requiring significant rewrites

**Recommendation**: Use validation/correction during import rather than filtering during display.
