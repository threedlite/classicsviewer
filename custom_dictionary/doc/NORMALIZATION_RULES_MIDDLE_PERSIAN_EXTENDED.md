# Middle Persian (Pahlavi) Extended Normalization Rules
## Supporting Inscriptional, Psalter, and Ligatures

## Overview

This extended normalization ruleset provides **comprehensive cross-script support** for Middle Persian texts, enabling dictionary lookups across:
- **Inscriptional Pahlavi** (U+10B60–U+10B7F) - Standard form
- **Psalter Pahlavi** (U+10B80–U+10BAF) - Christian texts
- **Ligatures** - Connected letter forms
- **Variant glyphs** - Multiple representations of same letter

All variants normalize to **Inscriptional Pahlavi** as the canonical form.

## Rule Categories

### Priority 1: Diacritics (1 rule)
Remove modern scholarly additions

### Priority 2-24: Cross-Script Mapping (23 rules)
**Psalter Pahlavi → Inscriptional Pahlavi**

Map all 22 Psalter letters + 1 reversed aleph to Inscriptional equivalents.

### Priority 25-29: Inscriptional Variants (5 rules)
**Inscriptional variants → Standard Inscriptional**

Handle alternate glyph forms within Inscriptional Pahlavi block.

### Priority 30-32: Ligature Decomposition (3 rules)
**Ligatures → Separate letters**

Break apart connected letter forms.

---

## Detailed Rule Breakdown

### Priority 1: Remove Scholarly Diacritics

**Pattern**: `[\u0300-\u036F]`
**Replacement**: *(empty)*
**Description**: Remove combining diacritical marks

**What it does**:
- Removes modern scholarly marks added to critical editions
- Accent marks, dots, lines for disambiguation
- Historical Pahlavi had NO diacritics

**Example**:
```
Before: 𐭬𐭫́𐭣 (with accent on resh)
After:  𐭬𐭫𐭣 (plain)
```

---

## Cross-Script Mapping: Psalter → Inscriptional

### Background: Why Two Scripts?

**Inscriptional Pahlavi**:
- Used for Zoroastrian texts, royal inscriptions
- Official administrative documents
- Most common in digital corpora
- Unicode: U+10B60–U+10B7F

**Psalter Pahlavi**:
- Used for Christian texts (Psalms, liturgy)
- Developed by Syriac Christian communities in Persia
- Different letter shapes but same alphabet
- Unicode: U+10B80–U+10BAF

### The Problem

A scholar might have:
- **Dictionary**: Inscriptional Pahlavi entries
- **Text**: Psalter Pahlavi manuscript

Without normalization, lookups fail despite same underlying language.

### The Solution

Normalize **all Psalter forms** to **Inscriptional equivalents**:

```csv
middle_persian,𐮀,𐭠,Psalter aleph to Inscriptional aleph,2
middle_persian,𐮁,𐭡,Psalter beth to Inscriptional beth,3
...
middle_persian,𐮕,𐭵,Psalter taw to Inscriptional taw,23
```

### Complete Mapping Table

| Psalter | Unicode | → | Inscriptional | Unicode | Name |
|---------|---------|---|---------------|---------|------|
| 𐮀 | U+10B80 | → | 𐭠 | U+10B60 | aleph |
| 𐮁 | U+10B81 | → | 𐭡 | U+10B61 | beth |
| 𐮂 | U+10B82 | → | 𐭢 | U+10B62 | gimel |
| 𐮃 | U+10B83 | → | 𐭣 | U+10B63 | daleth |
| 𐮄 | U+10B84 | → | 𐭤 | U+10B64 | he |
| 𐮅 | U+10B85 | → | 𐭥 | U+10B65 | waw |
| 𐮆 | U+10B86 | → | 𐭦 | U+10B66 | zayin |
| 𐮇 | U+10B87 | → | 𐭧 | U+10B67 | heth |
| 𐮈 | U+10B88 | → | 𐭨 | U+10B68 | teth |
| 𐮉 | U+10B89 | → | 𐭩 | U+10B69 | yodh |
| 𐮊 | U+10B8A | → | 𐭪 | U+10B6A | kaph |
| 𐮋 | U+10B8B | → | 𐭫 | U+10B6B | lamedh |
| 𐮌 | U+10B8C | → | 𐭬 | U+10B6C | mem |
| 𐮍 | U+10B8D | → | 𐭭 | U+10B6D | nun |
| 𐮎 | U+10B8E | → | 𐭮 | U+10B6E | samekh |
| 𐮏 | U+10B8F | → | 𐭯 | U+10B6F | ayin |
| 𐮐 | U+10B90 | → | 𐭰 | U+10B70 | pe |
| 𐮑 | U+10B91 | → | 𐭱 | U+10B71 | sadhe |
| 𐮒 | U+10B92 | → | 𐭲 | U+10B72 | qoph |
| 𐮓 | U+10B93 | → | 𐭳 | U+10B73 | resh |
| 𐮔 | U+10B94 | → | 𐭴 | U+10B74 | shin |
| 𐮕 | U+10B95 | → | 𐭵 | U+10B75 | taw |

### Special Case: Reversed Aleph

**Priority 24**:
```csv
middle_persian,𐮖,𐭠,Psalter reversed aleph to Inscriptional aleph,24
```

- **𐮖** (U+10B96) = Reversed aleph in Psalter
- Used in certain contexts (word-final?)
- Normalizes to standard aleph

### Example: Psalter Text Normalization

**Original** (Psalter Pahlavi):
```
𐮀𐮅𐮇𐮅𐮅𐮌𐮆𐮃
```

**Normalized** (Inscriptional):
```
𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣
```

**Reading**: Ohrmazd (Ahura Mazda)

**Dictionary match**: ✅ Now matches Inscriptional dictionary entry

---

## Inscriptional Pahlavi Variants

### Priority 25-29: Variant Glyphs

Unicode includes **alternate glyph forms** for some Inscriptional letters:

```csv
middle_persian,𐭻,𐭠,Inscriptional Pahlavi aleph variant to standard aleph,25
middle_persian,𐭼,𐭡,Inscriptional Pahlavi beth variant to standard beth,26
middle_persian,𐭽,𐭤,Inscriptional Pahlavi he variant to standard he,27
middle_persian,𐭾,𐭥,Inscriptional Pahlavi waw variant to standard waw,28
middle_persian,𐭿,𐭩,Inscriptional Pahlavi yodh variant to standard yodh,29
```

### Variant Mapping Table

| Variant | Unicode | → | Standard | Unicode | Name |
|---------|---------|---|----------|---------|------|
| 𐭻 | U+10B7B | → | 𐭠 | U+10B60 | aleph variant |
| 𐭼 | U+10B7C | → | 𐭡 | U+10B61 | beth variant |
| 𐭽 | U+10B7D | → | 𐭤 | U+10B64 | he variant |
| 𐭾 | U+10B7E | → | 𐭥 | U+10B65 | waw variant |
| 𐭿 | U+10B7F | → | 𐭩 | U+10B69 | yodh variant |

### Why Variants Exist

**Contextual forms**:
- Different shapes based on position (initial, medial, final)
- Font rendering preferences
- Scholarly conventions for distinguishing homographs

**Example**:
```
Standard: 𐭥 (waw)
Variant:  𐭾 (waw variant - different glyph shape)
→ Both normalize to 𐭥
```

**Benefit**: Dictionary lookups work regardless of which glyph form was used in encoding.

---

## Ligature Decomposition

### Priority 30-32: Break Apart Connected Letters

Pahlavi script is cursive, and letters connect. Unicode includes some common ligatures as separate codepoints.

```csv
middle_persian,𐮗,𐭥𐭥,Psalter doubled waw ligature to two waws,30
middle_persian,𐮘,𐭩𐭥,Psalter yodh-waw ligature to yodh+waw,31
middle_persian,𐮙,𐭭𐭥,Psalter nun-waw ligature to nun+waw,32
```

### Ligature Details

#### Priority 30: Doubled Waw (𐮗)

**Ligature**: 𐮗 (U+10B97)
**Decomposes to**: 𐭥𐭥 (two separate waws)

**Use case**: Representing long *ū* vowel in Psalter texts

**Example**:
```
Before: 𐮗 (ligature)
After:  𐭥𐭥 (two letters)
Match:  Dictionary entry for words with double waw ✅
```

#### Priority 31: Yodh-Waw (𐮘)

**Ligature**: 𐮘 (U+10B98)
**Decomposes to**: 𐭩𐭥 (yodh + waw)

**Use case**: Common letter combination in Psalter

**Example**:
```
Before: 𐮘 (ligature)
After:  𐭩𐭥 (two letters)
```

#### Priority 32: Nun-Waw (𐮙)

**Ligature**: 𐮙 (U+10B99)
**Decomposes to**: 𐭭𐭥 (nun + waw)

**Use case**: Another common combination

**Example**:
```
Before: 𐮙 (ligature)
After:  𐭭𐭥 (two letters)
```

### Why Decompose Ligatures?

**Problem**: Dictionary entries use separate letters, but texts may use ligatures

**Example**:
- **Dictionary entry**: 𐭭𐭥𐭧 (n-w-h pattern)
- **Text**: 𐮙𐭧 (ligature + letter)
- **Without normalization**: No match ❌
- **After normalization**: 𐭭𐭥𐭧 = 𐭭𐭥𐭧 ✅

### Note on Other Ligatures

Unicode Psalter Pahlavi includes additional ligature codepoints not covered here:
- **𐮚** (U+10B9A) - ayb-waw ligature
- **𐮛** (U+10B9B) - bet-yodh ligature
- And others...

**To add more**:
```csv
middle_persian,𐮚,𐭠𐭥,Psalter ayb-waw ligature to aleph+waw,33
middle_persian,𐮛,𐭡𐭩,Psalter bet-yodh ligature to beth+yodh,34
```

Consult Unicode Standard Annex #31 for complete Psalter ligature list.

---

## Complete Normalization Flow

### Example 1: Psalter Christian Text

**Input**: 𐮀𐮌𐮉𐮕 (Psalter "amit" - truth)

**Step-by-step**:
1. Priority 2: 𐮀 → 𐭠 (aleph)
2. Priority 14: 𐮌 → 𐭬 (mem)
3. Priority 11: 𐮉 → 𐭩 (yodh)
4. Priority 23: 𐮕 → 𐭵 (taw)

**Output**: 𐭠𐭬𐭩𐭵 (Inscriptional)

**Dictionary match**: ✅

### Example 2: Text with Ligatures

**Input**: 𐮙𐮓 (Psalter with nun-waw ligature)

**Step-by-step**:
1. Priority 32: 𐮙 → 𐭭𐭥 (decompose ligature)
2. Priority 21: 𐮓 → 𐭳 (resh)

**Output**: 𐭭𐭥𐭳 (Inscriptional, fully decomposed)

**Dictionary match**: ✅

### Example 3: Mixed Script Text

**Input**: 𐮀𐭥𐭧𐭥𐭥𐭬𐭦𐭣 (mixed Psalter + Inscriptional)

**Step-by-step**:
1. Priority 2: 𐮀 → 𐭠 (Psalter aleph to Inscriptional)
2. Priorities 7-14: Already Inscriptional, no change

**Output**: 𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣 (all Inscriptional)

**Reading**: Ohrmazd

**Dictionary match**: ✅

### Example 4: Inscriptional Variants

**Input**: 𐭬𐭫𐭻 (with aleph variant at end)

**Step-by-step**:
1. Priority 25: 𐭻 → 𐭠 (variant to standard)

**Output**: 𐭬𐭫𐭠

**Dictionary match**: ✅

---

## Use Cases

### 1. Psalter Pahlavi Christian Manuscripts

**Sources**:
- Psalms translations
- Christian liturgy
- Biblical texts in Middle Persian

**Challenge**: Most dictionaries use Inscriptional forms

**Solution**: Cross-script normalization (Priorities 2-24)

**Example**:
```
Psalter manuscript: 𐮌𐮓𐮉𐮌 (Maryam - Mary)
Normalized:        𐭬𐭳𐭩𐭬
Dictionary entry:   𐭬𐭳𐭩𐭬 ✅
```

### 2. Mixed-Script Editions

**Sources**:
- Comparative editions showing both scripts
- Digital texts from multiple sources
- Transcriptions with inconsistent encoding

**Challenge**: Same text, different Unicode blocks

**Solution**: All normalize to Inscriptional

### 3. Ligature-Heavy Manuscripts

**Sources**:
- Cursive Book Pahlavi manuscripts
- Psalter texts with joined letters
- Calligraphic inscriptions

**Challenge**: Dictionary entries use separate letters

**Solution**: Ligature decomposition (Priorities 30-32)

### 4. Glyph Variant Tolerance

**Sources**:
- Different font renderings
- Multiple encoding conventions
- Historical digitization projects

**Challenge**: Same letter, different codepoint

**Solution**: Variant normalization (Priorities 25-29)

---

## Dictionary Entry Best Practices

### Use Inscriptional Pahlavi Standard Forms

✅ **Correct**:
```csv
lemma,transliteration,language,definition
𐭬𐭫𐭣,MRD/mard,middle_persian,man; person
𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣,ʾwhwwmzd/Ohrmazd,middle_persian,Ahura Mazda
```

❌ **Avoid**:
- Psalter forms in dictionary (use Inscriptional)
- Ligatures in lemmas (use decomposed)
- Variant glyphs (use standard forms)

### Handle Heterograms Separately

✅ **Recommended**:
```csv
lemma,transliteration,reading,language,definition
𐭌𐭋𐭊𐭀,MLKʾ,šāh,middle_persian,"king (Aramaic heterogram, read as šāh)"
𐭱𐭧𐭫,ŠHR,šahr,middle_persian,"city (phonetic spelling)"
```

### Provide Both Script Forms (Optional)

For reference, you can include Psalter forms in notes:

```csv
lemma,psalter_form,transliteration,language,definition
𐭠𐭬𐭩𐭵,𐮀𐮌𐮉𐮕,ʾmyt/amit,middle_persian,truth
```

But normalization will handle Psalter automatically.

---

## Testing Examples

### Test 1: Basic Psalter Mapping

**Input**: 𐮀 (Psalter aleph)
**Expected**: 𐭠 (Inscriptional aleph)
**Result**: ✅

### Test 2: Complete Psalter Word

**Input**: 𐮀𐮅𐮇𐮅𐮅𐮌𐮆𐮃 (Ohrmazd in Psalter)
**Expected**: 𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣 (Inscriptional)
**Result**: ✅

### Test 3: Ligature Decomposition

**Input**: 𐮗 (doubled waw ligature)
**Expected**: 𐭥𐭥 (two waws)
**Result**: ✅

### Test 4: Variant Normalization

**Input**: 𐭻 (aleph variant)
**Expected**: 𐭠 (standard aleph)
**Result**: ✅

### Test 5: Mixed Everything

**Input**: 𐮀𐭼𐮘𐭻 (Psalter aleph + beth variant + yodh-waw ligature + aleph variant)
**Expected**: 𐭠𐭡𐭩𐭥𐭠 (all normalized and decomposed)
**Result**: ✅

---

## Comparison: Basic vs Extended Rules

### Basic Rules (1 active rule)
```csv
middle_persian,[\u0300-\u036F],,Remove diacritics,1
```

**Handles**:
- ✅ Scholarly diacritics
- ❌ Psalter script
- ❌ Ligatures
- ❌ Variants

**Use when**: Only Inscriptional texts, no cross-script needs

### Extended Rules (32 active rules)
```csv
# All the rules in the current file
```

**Handles**:
- ✅ Scholarly diacritics
- ✅ Psalter → Inscriptional mapping
- ✅ Ligature decomposition
- ✅ Glyph variant normalization

**Use when**: Working with diverse Middle Persian corpus

---

## Technical Notes

### Unicode Blocks

**Inscriptional Pahlavi**: U+10B60–U+10B7F
- 22 base letters (U+10B60–U+10B75)
- 5 variant forms (U+10B7B–U+10B7F)
- Numbers and punctuation

**Psalter Pahlavi**: U+10B80–U+10BAF
- 22 base letters (U+10B80–U+10B95)
- 1 reversed aleph (U+10B96)
- Ligatures (U+10B97–U+10B9C)
- Additional marks

### NFD Normalization Interaction

The app applies NFD before custom rules:
1. **NFD**: Separates combining marks
2. **Priority 1**: Removes combining marks
3. **Priorities 2-32**: Script and ligature normalization

This ensures diacritics are removed even if they were composed with base characters.

### Regular Expression Considerations

- **Single character patterns**: Fast matching
- **Replacement is literal**: Not regex
- **Order matters**: Diacritics removed first, then cross-script, then ligatures

### Performance

With 32 rules:
- **Per-character check**: O(32) = constant time
- **Whole text**: O(n) where n = text length
- **Impact**: Minimal (milliseconds for typical texts)

---

## Limitations

### What This Does NOT Handle

1. **Homograph Disambiguation**
   - 𐭣𐭥𐭫𐭭 still look similar
   - Context needed, not normalization

2. **Heterogram Expansion**
   - 𐭌𐭋𐭊𐭀 (MLKʾ) not auto-expanded to šāh
   - Keep as separate dictionary entries

3. **Book Pahlavi Manuscripts**
   - Extremely cursive, many more ligatures
   - Would need hundreds of additional rules
   - Current scope: Inscriptional + Psalter

4. **Vowel Insertion**
   - Pahlavi is consonantal
   - Can't automatically add vowels

### Future Enhancements

1. **More Ligatures**:
   Add all Psalter ligatures (U+10B9A–U+10B9C, etc.)

2. **Manichaean Middle Persian**:
   Different script (U+10AC0–U+10AFF), needs separate rules

3. **Inscriptional Parthian**:
   Related script (U+10B40–U+10B5F), similar approach

---

## Summary

✅ **32 comprehensive normalization rules**
✅ **Cross-script support** (Inscriptional ↔ Psalter)
✅ **Ligature decomposition** (3 common forms)
✅ **Variant normalization** (5 glyph alternates)
✅ **Production-ready** for diverse Middle Persian corpus

Use `normalization_rules_middle_persian.csv` in your dictionary ZIP for maximum Middle Persian text coverage across scripts, ligatures, and variants.

---

## References

### Unicode Standards
- **Inscriptional Pahlavi**: https://unicode.org/charts/PDF/U10B60.pdf
- **Psalter Pahlavi**: https://unicode.org/charts/PDF/U10B80.pdf
- **Proposal L2/07-234**: Pahlavi script encoding

### Academic Resources
- Skjærvø, P.O. (2009). "Middle West Iranian"
- Henning, W.B. (1958). "Mitteliranisch"
- MacKenzie, D.N. (1971). "A Concise Pahlavi Dictionary"

### Digital Projects
- **eScripta**: Digital Pahlavi corpus
- **TITUS**: Multi-script text database
