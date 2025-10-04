# Persian (Farsi) Normalization Rules

## Overview

Persian uses a modified Arabic script with additional letters and different conventions. These normalization rules enable dictionary lookups for Persian text regardless of diacritical marks, script variants, or Arabic vs. Persian letter forms.

## Language Context

**Persian (فارسی / Fārsī)** is an Indo-European language written in a modified Arabic-based alphabet:
- **Script family**: Perso-Arabic
- **Direction**: Right-to-left (RTL)
- **Alphabet size**: 32 letters (Arabic 28 + 4 Persian: پ چ ژ گ)
- **Diacritics**: Uses Arabic diacritics (zabar, zēr, pēsh) but rarely in modern text
- **Historical texts**: Classical Persian poetry and prose often include full diacritics

## Rules Breakdown

### Priority 1: Remove Arabic Diacritics
**Pattern**: `[\u064B-\u065F\u0670]`
**Replacement**: *(empty string)*
**Description**: Remove Arabic diacritics (zabar zēr pēš tanwīn etc)

**What it does**:
- Removes all Arabic vocalization marks (ḥarakāt):
  - **َ** (zabar/fatḥa) - "a" sound
  - **ِ** (zēr/kasra) - "i" sound
  - **ُ** (pēsh/ḍamma) - "u" sound
  - **ً ٌ ٍ** (tanwīn) - "an/un/in" sounds
  - **ّ** (tashdīd/shadda) - gemination/doubling
  - **ْ** (jazm/sukūn) - absence of vowel
  - **ٓ** (maddah) - long ā
  - **ٰ** (alif khanjariyah) - superscript alif

**Example**:
```
Before: کِتَابٌ (kitābun - with full diacritics)
After:  کتاب (ktāb - plain text)
Match:  کتاب ✅ (dictionary entry)
```

**Use case**: Classical Persian texts (Hafez, Rumi, Ferdowsi) often include diacritics for proper pronunciation and meter (in poetry). Modern Persian rarely uses them except in educational contexts.

---

### Priority 2: Remove Tatweel/Kashida
**Pattern**: `\u0640`
**Replacement**: *(empty string)*
**Description**: Remove tatweel/kashida (elongation character)

**What it does**:
- Removes the kashida (ـ), a horizontal line used to stretch words for justification or aesthetic purposes

**Example**:
```
Before: کـــتـــاب (stretched for calligraphy)
After:  کتاب (normal form)
Match:  کتاب ✅
```

**Use case**: Common in Persian calligraphy, justified text, decorative headers, or Nastaliq script formatting.

---

### Priority 3: Normalize Alif Variants
**Pattern**: `[أإآٱ]`
**Replacement**: `ا`
**Description**: Normalize all alif variants to plain alif

**What it does**:
- **أ** (alif with hamza above) → **ا** (plain alif)
- **إ** (alif with hamza below) → **ا** (plain alif)
- **آ** (alif with maddah) → **ا** (plain alif)
- **ٱ** (alif wasla) → **ا** (plain alif)

**Example**:
```
Before: آب (āb - water, with maddah)
After:  اب (ab - normalized)
Match:  اب ✅

Before: إسلام (Islām - with hamza below)
After:  اسلام (slām - normalized)
Match:  اسلام ✅
```

**Use case**: Persian primarily uses plain alif (ا). Hamza variants appear in:
- Arabic loanwords (إسلام, أحمد)
- Quranic Persian texts
- Classical religious texts

---

### Priority 4: Normalize Hamza on Waw
**Pattern**: `ؤ`
**Replacement**: `و`
**Description**: Normalize hamza on waw to plain waw

**What it does**:
- **ؤ** (waw with hamza) → **و** (plain waw)

**Example**:
```
Before: مؤمن (mo'men - believer)
After:  مومن (momen)
Match:  مومن ✅
```

**Use case**: Hamza on waw is used in Arabic orthography but often simplified in Persian.

---

### Priority 5: Normalize Hamza on Ya
**Pattern**: `ئ`
**Replacement**: `ی`
**Description**: Normalize hamza on ya to plain ya

**What it does**:
- **ئ** (ya with hamza) → **ی** (plain Persian ya)

**Example**:
```
Before: شیئ (shey' - thing)
After:  شیی (shyy - normalized)
Match:  شیی ✅
```

**Use case**: Common in Arabic loanwords but often written without hamza in Persian.

---

### Priority 6-7: Normalize Arabic Ya to Persian Ya
**Pattern 6**: `ى` → `ی`
**Pattern 7**: `ي` → `ی`
**Description**: Normalize Arabic ya variants to Persian yeh

**What it does**:
- **ى** (Arabic alif maqsura / ya without dots) → **ی** (Persian yeh with dots)
- **ي** (Arabic yeh with dots below) → **ی** (Persian yeh with dots below)

**Example**:
```
Before: علي (Ali - Arabic form)
After:  علی (Ali - Persian form)
Match:  علی ✅

Before: موسى (Musa - Arabic form)
After:  موسی (Musa - Persian form)
Match:  موسی ✅
```

**Use case**:
- **Critical for Persian**: Persian uses ی (U+06CC) while Arabic uses ي (U+064A)
- Names and loanwords from Arabic often retain Arabic ya
- Modern Persian keyboards default to Persian yeh

**Unicode note**:
- **ى** = U+0649 (Arabic letter alif maksura - no dots)
- **ي** = U+064A (Arabic letter yeh - dots below)
- **ی** = U+06CC (Persian letter yeh - dots below, preferred)

---

### Priority 8: Normalize Arabic Kaf to Persian Kaf
**Pattern**: `ك`
**Replacement**: `ک`
**Description**: Normalize Arabic kaf to Persian kaf

**What it does**:
- **ك** (Arabic kaf) → **ک** (Persian kaf/keheh)

**Example**:
```
Before: كتاب (ketāb - book, Arabic kaf)
After:  کتاب (ketāb - book, Persian kaf)
Match:  کتاب ✅
```

**Use case**:
- **Visual difference**: Arabic ك has a shorter vertical stroke than Persian ک
- **Critical for Persian**: Most Persian texts use ک (U+06A9)
- Mixed texts (Arabic quotes in Persian) may use both forms

**Unicode note**:
- **ك** = U+0643 (Arabic letter kaf)
- **ک** = U+06A9 (Persian letter keheh)

---

### Priority 9: Normalize Taa Marbuta
**Pattern**: `ة`
**Replacement**: `ه`
**Description**: Normalize taa marbuta to haa

**What it does**:
- **ة** (taa marbuta - "tied taa") → **ه** (haa)

**Example**:
```
Before: مدرسة (madrese - school, Arabic ending)
After:  مدرسه (madrese - school, Persian ending)
Match:  مدرسه ✅
```

**Use case**:
- **Arabic feminine marker**: Taa marbuta (ة) marks feminine nouns in Arabic
- **Persian adaptation**: Persian often writes the same words with plain haa (ه)
- Common in Arabic loanwords: مکتبة/مکتبه (library), جمعة/جمعه (Friday)

---

### Priority 10: Remove Standalone Hamza
**Pattern**: `ء`
**Replacement**: *(empty string)*
**Description**: Remove standalone hamza

**What it does**:
- **ء** (standalone hamza) → removed

**Example**:
```
Before: جزء (joz' - part)
After:  جز (jz)
Match:  جز ✅
```

**Use case**:
- Hamza represents a glottal stop in Arabic
- Often omitted in simplified Persian orthography
- Common in Arabic loanwords

---

## Full Normalization Example

**Original text** (Classical Persian with full diacritics):
```
کِتَابِ شَاهْنَامَهٔ فِرْدَوْسِی
```

**After normalization**:
```
کتاب شاهنامه فردوسی
```

**Step-by-step**:
1. Remove diacritics: کتاب شاهنامه فردوسی
2. Remove kashida: *(none in this example)*
3. Normalize alif: *(none to change)*
4-5. Normalize hamza: *(none in this example)*
6-7. Normalize ya to Persian: *(already Persian)*
8. Normalize kaf: *(already Persian)*
9. Normalize taa marbuta: *(none in this example)*
10. Remove hamza: *(none in this example)*

**Result**: Clean, searchable form that matches dictionary entries.

---

## Persian-Specific Considerations

### Letters Unique to Persian
These four letters are **NOT** normalized (they are distinct from Arabic):
- **پ** (pe) - /p/ sound - not in Arabic
- **چ** (che) - /ch/ sound - not in Arabic
- **ژ** (zhe) - /zh/ sound - not in Arabic
- **گ** (gaf) - /g/ sound - not in Arabic (Arabic uses ج for /g/ in some dialects)

### Ezāfe (اضافه)
The **ezāfe** is a Persian grammatical construct:
- Written as **ـِ** (zēr) or **ی** (ya)
- Connects nouns in possessive/descriptive phrases
- Example: **کتابِ فارسی** (ketāb-e fārsi - Persian book)

**Normalization behavior**:
- Diacritic ezāfe (ـِ) is removed by Priority 1
- Ya ezāfe (ی) is preserved (it's a letter, not a diacritic)

### Modern vs. Classical Persian

**Modern Persian** (post-20th century):
- Rarely uses diacritics
- Consistent use of Persian letters (ی، ک)
- Minimal normalization needed

**Classical Persian** (pre-20th century, poetry):
- Full diacritics common (for meter and pronunciation)
- Mixed Arabic/Persian letter forms
- Heavy normalization beneficial

---

## Testing Examples

### Poetry (Classical Persian - Hafez)
**Original**:
```
شِنِیدَم کِه صُبحِ اَزَل نُورِ حُسنِ تُو
```

**Normalized**:
```
شنیدم که صبح ازل نور حسن تو
```

**Dictionary matches**: شنیدم، صبح، ازل، نور، حسن ✅

### Prose (Modern Persian)
**Original**:
```
کتابخانهٔ ملّی ایران
```

**Normalized** (minimal changes):
```
کتابخانه ملی ایران
```

### Mixed Arabic-Persian
**Original**:
```
الحمد لله رب العالمين
```

**Normalized**:
```
الحمد لله رب العالمین
```

**Changes**:
- ي → ی (Arabic ya to Persian ya)

---

## Use Cases

### 1. Classical Persian Literature
**Texts**: Shahnameh (Ferdowsi), Divan-e Hafez, Masnavi (Rumi)
- Full diacritics for poetic meter
- Archaic orthography
- Mixed Arabic/Persian conventions

**Benefit**: Normalize to match modern dictionary entries

### 2. Quranic Persian Translations
- Heavy use of Arabic diacritics
- Arabic letter forms in quotes
- Standardized Persian in commentary

**Benefit**: Consistent lookup across Arabic quotes and Persian text

### 3. Modern Persian Texts
- Minimal diacritics (educational texts only)
- Consistent Persian orthography
- Occasional kashida in justified text

**Benefit**: Handle justified text and rare diacritics

### 4. Historical Documents
- Ottoman Persian (mixed Turkish/Persian/Arabic)
- Colonial-era texts (mixed conventions)
- Religious manuscripts

**Benefit**: Harmonize variant orthographies

---

## Dictionary Entry Best Practices

When creating a Persian dictionary for use with these normalization rules:

1. **Use normalized forms** as lemmas:
   - ✅ `کتاب` (plain)
   - ❌ `کِتَاب` (with diacritics)

2. **Use Persian letters** (not Arabic):
   - ✅ `ی` (U+06CC Persian yeh)
   - ❌ `ي` (U+064A Arabic yeh)
   - ✅ `ک` (U+06A9 Persian kaf)
   - ❌ `ك` (U+0643 Arabic kaf)

3. **No diacritics** in dictionary lemmas:
   - ✅ `علی` (Ali)
   - ❌ `عَلِی` (Ali with diacritics)

4. **Plain letter forms**:
   - ✅ `ا` (plain alif)
   - ❌ `آ` (alif with maddah)

---

## Comparison with Arabic Normalization

### Similarities
- Remove diacritics (Priority 1)
- Remove kashida (Priority 2)
- Normalize alif variants (Priority 3)
- Normalize hamza on waw/ya (Priority 4-5)
- Remove standalone hamza (Priority 10)

### Persian-Specific
- **Priority 6-7**: Normalize Arabic ya (ي/ى) to Persian yeh (ی)
  - **Critical**: Different Unicode codepoints!
- **Priority 8**: Normalize Arabic kaf (ك) to Persian keheh (ک)
  - **Critical**: Visual difference matters for readability
- **Priority 9**: Normalize taa marbuta to haa (common in loanwords)

### Arabic-Specific (Not in Persian rules)
- Normalize alif maqsura: Persian uses this less frequently
- Some Arabic-specific diacritic combinations

---

## Technical Notes

### Character Encoding
- **Always use UTF-8**
- Persian requires Unicode range U+0600 to U+06FF (Arabic block)
- Persian-specific letters: U+067E (پ), U+0686 (چ), U+0698 (ژ), U+06AF (گ)

### NFD Normalization
The app applies **NFD** (Unicode Normalization Form D) before custom rules:
- Separates base characters from combining marks
- Makes diacritic removal patterns more reliable
- Example: `کِ` (U+06A9 + U+0650) splits for easier matching

### Regex Patterns
All patterns use Unicode escapes:
- `\u064B-\u065F` = diacritics range
- `\u0670` = alif khanjariyah
- `\u0640` = kashida

### Right-to-Left (RTL)
- Patterns match left-to-right (logical order)
- Display is RTL (visual order)
- Regex engines work on logical order

---

## FAQ

**Q: Why normalize both ي and ى to ی?**
A: Persian uses ی (U+06CC) as standard. Arabic uses ي (U+064A) and ى (U+0649). Texts may mix them, so we normalize to Persian standard.

**Q: Will this work for Dari (Afghan Persian)?**
A: Yes! Dari uses the same alphabet and script. These rules apply equally well.

**Q: What about Tajik Persian?**
A: Tajik uses Cyrillic script, not Arabic script. These rules don't apply.

**Q: Should I remove the ezāfe?**
A: No. The ezāfe is grammatically significant. Diacritic ezāfe (ـِ) is removed, but letter ezāfe (ی) is preserved.

**Q: What about numbers (۰-۹)?**
A: Persian uses Eastern Arabic numerals (۰۱۲۳۴۵۶۷۸۹). These rules don't affect them. Consider separate normalization if you want to match Western Arabic (0-9) or Latin (0-9) numerals.

**Q: Will this affect Arabic text in Persian documents?**
A: Yes, Arabic words will be normalized to Persian letter forms. This is usually desirable for consistent dictionary lookup. If you need to preserve Arabic orthography, consider creating separate rules or not normalizing mixed texts.

---

## Summary

✅ **10 normalization rules** for Persian text
✅ **Handles classical and modern** Persian orthography
✅ **Arabic-to-Persian letter conversion** (ي→ی, ك→ک)
✅ **Diacritic removal** for vocalized texts
✅ **Compatible** with Dari Persian
✅ **Production-ready** for dictionary import

Use `normalization_rules_persian.csv` in your custom dictionary ZIP for robust Persian text matching.

---

## References

- **Persian alphabet**: https://en.wikipedia.org/wiki/Persian_alphabet
- **Unicode Persian**: https://unicode.org/charts/PDF/U0600.pdf
- **Persian typography**: https://en.wikipedia.org/wiki/Persian_alphabet#Typography
- **Ezāfe**: https://en.wikipedia.org/wiki/Ezafe
