# Hebrew Dictionary Lookup Failure - Root Cause Analysis

## Problem Statement
When clicking on Hebrew words in the Jonah text, no dictionary definitions are found, even though the dictionary has been successfully imported.

## Data Flow Analysis

### 1. Text Display (What the user sees and clicks)
**Source**: `hebrew_texts.db` → `text_lines.line_text`
**Sample data**:
```
וַֽ/יְהִי֙ דְּבַר ־ יְהוָ֔ה אֶל ־ יוֹנָ֥ה בֶן ־ אֲמִתַּ֖י לֵ/אמֹֽר
```

**Key observation**: Text contains:
- Slashes (`/`) marking morphological boundaries
- Nikud (vocalization marks) like `ַֽ`, `ְ`, `ִ֙`, etc.
- Hyphens (`־`) as word separators

### 2. Word Parsing (What gets extracted when user clicks)
**Location**: `TextLineAdapter.kt` lines 106-112

**Parser logic**:
```kotlin
val isWordChar = char.isLetter() ||
                 char == '-' ||
                 Character.getType(char) == Character.NON_SPACING_MARK.toInt() ||
                 Character.getType(char) == Character.COMBINING_SPACING_MARK.toInt() ||
                 Character.getType(char) == Character.ENCLOSING_MARK.toInt() ||
                 (char == '\'' && ...)
```

**Critical**: Slashes (`/`) are NOT included in `isWordChar`, so they act as word separators.

**Example parsed word** when user clicks on `וַֽ/יְהִי֙`:
- Input text: `וַֽ/יְהִי֙`
- Parsed as TWO words: `וַֽ` and `יְהִי֙`
- User clicking on first part gets: `וַֽ`
- User clicking on second part gets: `יְהִי֙`

### 3. Morphology Mappings (What's in the dictionary)
**Source**: `hebrew_morphology.csv`
**Sample entries**:
```csv
word_form,lemma,morph_info,language,confidence,source_name
וַֽ/יְהִי֙,c/1961,conjunction,hebrew,1.0,OSHB morphhb
דְּבַר,1697,noun common,hebrew,1.0,OSHB morphhb
לֵ/אמֹֽר,l/559,preposition,hebrew,1.0,OSHB morphhb
```

**Key observation**: Word forms contain slashes, e.g., `וַֽ/יְהִי֙`

### 4. Dictionary Lookup Process

**Step 1**: User clicks word → `וַֽ` (without slash, because slash is a separator)

**Step 2**: Normalization applied (PerseusRepository.kt:54-73)
```kotlin
private suspend fun normalizeText(text: String, language: String): String? {
    return when (language) {
        "hebrew" -> {
            val patterns = normalizationPatternDao.getPatternsForLanguage("hebrew")
            if (patterns.isNotEmpty()) {
                PatternBasedNormalizer.normalize(text, language, patterns)
            } else null
        }
    }
}
```

**Current normalization patterns** (`normalization_rules_hebrew.csv`):
```csv
language,pattern,replacement,description,priority
hebrew,/,,Remove morphological boundary slashes,1
hebrew,[\u0591-\u05C7],,Remove all nikud (vocalization marks),2
hebrew,ך,כ,Normalize final kaf to regular kaf,3
hebrew,ם,מ,Normalize final mem to regular mem,4
hebrew,ן,נ,Normalize final nun to regular nun,5
hebrew,ף,פ,Normalize final pe to regular pe,6
hebrew,ץ,צ,Normalize final tsadi to regular tsadi,7
```

**Normalization on clicked word** `וַֽ`:
1. Input: `וַֽ`
2. NFD decomposition: `וַֽ` (separates combining marks)
3. Pattern 1 (remove `/`): No match (slash already removed by parser)
4. Pattern 2 (remove nikud `[\u0591-\u05C7]`): Matches `ַֽ` → Result: `ו`
5. Final normalized form: `ו`

**Step 3**: Database query (UserLemmaMappingDao.kt:9-22)
```sql
SELECT ulm.* FROM user_lemma_mappings ulm
WHERE (ulm.word_form = :word OR ulm.word_form_normalized_ultra = :normalizedWord)
AND ulm.language = :language
AND udp.is_active = 1
```

Query parameters:
- `:word` = `וַֽ` (original clicked word)
- `:normalizedWord` = `ו` (after normalization)
- `:language` = `hebrew`

**Step 4**: What's actually in the database?

**During import** (DictionaryZipParser.kt:340-395):
- Word form from CSV: `וַֽ/יְהִי֙`
- Normalization applied:
  1. NFD: `וַֽ/יְהִי֙`
  2. Pattern 1 (remove `/`): `וַֽיְהִי֙`
  3. Pattern 2 (remove nikud): `ויהי`
- Stored in database:
  - `word_form` = `וַֽ/יְהִי֙` (original)
  - `word_form_normalized_ultra` = `ויהי` (normalized)

## The Mismatch

### Lookup Query Looking For:
- `word_form` = `וַֽ` OR
- `word_form_normalized_ultra` = `ו`

### Database Contains:
- `word_form` = `וַֽ/יְהִי֙`
- `word_form_normalized_ultra` = `ויהי`

### Result: NO MATCH

## Root Causes

### Primary Issue: Multi-part Words
The morphhb data represents compound words as single entries with slashes:
- `וַֽ/יְהִי֙` is a single morphological unit (conjunction + verb)
- The slash separates the conjunction prefix `וַֽ` from the root verb `יְהִי֙`
- Strong's lemma is `c/1961` (conjunction c + verb 1961)

But the text display and word parser treat this as TWO separate words.

### Secondary Issue: Inconsistent Data Models
1. **Morphhb source data**: Uses slashes to mark morpheme boundaries within words
2. **Text display**: Shows slashes as-is (not removed in stored text)
3. **Word parser**: Treats slashes as word separators (like spaces)
4. **Dictionary**: Stores complete forms with slashes

## Why Normalization Won't Fix This

Adding slash removal to normalization helps during import:
- `וַֽ/יְהִי֙` → `ויהי` ✓

But the clicked word is already split by the parser:
- User clicks: `וַֽ` (only the prefix)
- Normalized to: `ו` (just the letter vav)
- Database has: `ויהי` (the full word without nikud/slash)

They don't match because `ו` ≠ `ויהי`.

## Potential Solutions

### Option 1: Store Each Morpheme Separately
**During import** (`process_hebrew_complete.py`):
- Split word forms on `/` before creating morphology entries
- `וַֽ/יְהִי֙` → Two entries:
  - `וַֽ` → lemma `c` (conjunction)
  - `יְהִי֙` → lemma `1961` (verb)
- Also split lemmas: `c/1961` → `c` and `1961`

**Pros**:
- Matches how users click words
- Each morpheme gets its own definition

**Cons**:
- Loses the compound word semantics
- Lemma IDs like `c/1961` need parsing
- May not have definitions for individual morphemes (like `c` = conjunction)

### Option 2: Remove Slashes from Displayed Text
**During database creation** (`process_hebrew_complete.py`):
- Strip slashes when storing `line_text`
- `וַֽ/יְהִי֙ דְּבַר` → `וַֽיְהִי֙ דְּבַר`

**Also keep original word forms without slashes in morphology**:
- Store: `וַֽיְהִי֙` (no slash)
- Lemma: `c/1961` (slash OK in lemma, just not in word_form)

**Pros**:
- Simple fix
- Maintains original morphology metadata
- Word clicks will match stored forms

**Cons**:
- Loses visual indication of morpheme boundaries
- May affect scholarly use

### Option 3: Make Word Parser Include Slashes
**In** `TextLineAdapter.kt`:
- Add `char == '/'` to `isWordChar`

**Result**:
- User clicks `וַֽ/יְהִי֙` as ONE word (with slash)
- Matches database entry `word_form = וַֽ/יְהִי֙`

**Pros**:
- No database changes needed
- Preserves all original data

**Cons**:
- We already tried this and user said "slashes should be word SEPARATORS"
- Not intuitive for Hebrew readers (slash isn't a letter)

### Option 4: Fuzzy Matching at Lookup Time
**During lookup**:
- When `וַֽ` doesn't match, try searching for word forms that START with `וַֽ/`
- Use partial matching or prefix search

**Pros**:
- No data changes
- Flexible

**Cons**:
- Complex query logic
- May return incorrect matches
- Performance overhead

## Recommended Solution

**Option 2: Remove slashes from displayed text and stored word forms**

### Implementation Steps:

1. **Update `process_hebrew_complete.py`**:
   - In `extract_text_from_word_elements()`: Strip `/` from extracted text
   - In word form extraction: Remove `/` before storing in morphology CSV

2. **Regenerate Hebrew data**:
   - Run `python3 process_hebrew_complete.py`
   - Creates new `hebrew_texts.db` and `hebrew_morphology.csv` without slashes

3. **Keep lemma IDs as-is**:
   - Lemma `c/1961` stays the same
   - Only affects `word_form` column, not `lemma` column

4. **No normalization changes needed**:
   - The slash normalization pattern becomes a no-op
   - Other patterns (nikud removal, final letters) still work

### Expected Result:

**Text displayed**: `וַֽיְהִי֙ דְּבַר יְהוָ֔ה`
**User clicks**: `וַֽיְהִי֙`
**Normalization**: `ויהי`
**Database query**: Finds `word_form_normalized_ultra = ויהי` ✓
**Definition returned**: Lemma `c/1961` → "and it came to pass"

## Testing Plan

1. Modify `process_hebrew_complete.py` to strip slashes
2. Regenerate database and morphology CSV
3. Recreate `hebrew_lexicon.zip`
4. Import on phone
5. Click on first word of Jonah 1:1
6. Verify definition appears

## Source Data Investigation

### Morphhb Source XML
**File**: `data-sources/morphhb/wlc/Jonah.xml`

The slashes ARE in the original morphhb source data:

```xml
<w lemma="c/1961" n="0.1.0" morph="HC/Vqw3ms">וַֽ/יְהִי֙</w>
<w lemma="l/559" morph="HR/Vqc">לֵ/אמֹֽר</w>
<w lemma="413" morph="HR/Sp3ms">אֵלָי/ו֙</w>
<w lemma="d/376" morph="HTd/Ncmpa">הָֽ/אֲנָשִׁים֙</w>
```

**Purpose of slashes**: They mark morpheme boundaries where:
- Prefixes attach to root words (prepositions, conjunctions, articles)
- Suffixes attach to root words (pronouns)

**Examples**:
- `וַֽ/יְהִי֙` = conjunction `ו` (and) + verb `היה` (to be) → "and it came to pass"
  - lemma: `c/1961` = conjunction + Strong's 1961
  - morph: `HC/Vqw3ms` = Hebrew Conjunction / Qal wayyiqtol 3rd masculine singular

- `לֵ/אמֹֽר` = preposition `ל` (to/for) + verb `אמר` (to say) → "saying"
  - lemma: `l/559` = preposition l + Strong's 559
  - morph: `HR/Vqc` = Hebrew pReposition / Qal construct

- `הָֽ/אֲנָשִׁים֙` = article `ה` (the) + noun `אנשים` (men) → "the men"
  - lemma: `d/376` = definite article + Strong's 376
  - morph: `HTd/Ncmpa` = Hebrew article The / Noun common masculine plural absolute

**This is linguistically accurate**: Hebrew is an agglutinative language where prefixes and suffixes attach to word roots. The slash notation preserves the morphological structure.

### Our Process Preserved This
`process_hebrew_complete.py` correctly extracts the `<w>` element text as-is:
```python
word_text = word_elem.text.strip()  # Gets "וַֽ/יְהִי֙" with slash
```

The slashes were never added by our code - they're from the scholarly morphhb data.

## Additional Observations

### Words Table
The `words` table in `hebrew_texts.db` contains individual words:
```
אֱ֠לֹהִים
אֱלֹהִ֖ים
אֱלֹהֵ֤י
אֱלֹהֶ֔י/ךָ  ← Still has slashes!
```

This confirms slashes appear in stored word data, not just in line_text.

### Dictionary Lemmas
Strong's dictionary uses plain Hebrew without nikud:
```
lemma,language,definition
אָב,hebrew,father
אַב,hebrew,father.
אָבַד,hebrew,wander; lose; perish; destroy
```

These are base lemma forms, not inflected forms with nikud.
