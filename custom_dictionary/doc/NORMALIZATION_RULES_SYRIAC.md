# Syriac Normalization Rules

## Overview

These normalization rules handle Classical Syriac text, removing vocalization marks, pronunciation indicators, and editorial annotations. Syriac is a dialect of Aramaic written in its own distinctive script, used extensively in Christian literature from the 1st century CE onwards.

## Background

**Syriac** is an Eastern Aramaic dialect that became the literary language of Aramaic-speaking Christians. It developed its own script (derived from Aramaic) and became a major vehicle for:
- Biblical translations (Peshitta)
- Theological writings (Syriac Fathers)
- Liturgical texts
- Scientific and philosophical translations
- Historical chronicles

### Two Main Traditions

#### West Syriac (Jacobite/Maronite)
- Greek-influenced vowel system
- Written in **Serto** script (cursive)
- Used by Syrian Orthodox, Maronites
- Vocalization: combination of dots and small Greek letters

#### East Syriac (Nestorian/Chaldean)
- Indigenous vowel system
- Written in **Estrangela** or **East Syriac** script
- Used by Church of the East, Chaldean Catholics, Assyrians
- Vocalization: system of dots above and below letters

## Normalization Rules

### Vowel Points (Priorities 1-17)

#### 1. All Syriac Vocalization Marks (Priority 1)
- **Pattern**: `[\u0730-\u074A]`
- **Replacement**: (empty)
- **Purpose**: Remove all Syriac vowel points in one sweep
- **Unicode Range**: U+0730 to U+074A
- **Note**: Comprehensive catch-all for all vowel systems

#### 2. Rwaha (Priority 2)
- **Pattern**: `ܿ` (U+073F)
- **Replacement**: (empty)
- **Purpose**: Remove Rwaha (supralinear dot, West Syriac /o/)
- **Example**: `ܡܿܠܟܐ` → `ܡܠܟܐ` (malka, "king")
- **Phonetic**: Represents /o/ in West Syriac

#### 3. Dotted Zlama Angular (Priority 3)
- **Pattern**: `ܾ` (U+073E)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama angular
- **Phonetic**: West Syriac vowel variant

#### 4. Rwaha (Priority 4)
- **Pattern**: `ܽ` (U+073D)
- **Replacement**: (empty)
- **Purpose**: Remove Rwaha (West Syriac /u/)
- **Phonetic**: Represents /u/ in West Syriac

#### 5. Hbasa (Priority 5)
- **Pattern**: `ܼ` (U+073C)
- **Replacement**: (empty)
- **Purpose**: Remove Hbasa (sublinear dot, West Syriac /i/)
- **Example**: Peshitta manuscripts with West Syriac pointing
- **Phonetic**: Represents /i/ in West Syriac

#### 6. Dotted Zlama Horizontal (Priority 6)
- **Pattern**: `ܻ` (U+073B)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama horizontal (East Syriac /i/)
- **Phonetic**: East Syriac /i/ vowel

#### 7. Hbasa-Esasa (Priority 7)
- **Pattern**: `ܺ` (U+073A)
- **Replacement**: (empty)
- **Purpose**: Remove Hbasa-Esasa (two dots below, East Syriac /i/)
- **Phonetic**: East Syriac /i/ vowel (variant)

#### 8. Esasa (Priority 8)
- **Pattern**: `ܹ` (U+0739)
- **Replacement**: (empty)
- **Purpose**: Remove Esasa (dot below, East Syriac /e/)
- **Phonetic**: East Syriac /e/ vowel

#### 9. Dotted Zlama (Priority 9)
- **Pattern**: `ܸ` (U+0738)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama (East Syriac /a/)
- **Phonetic**: East Syriac /a/ vowel

#### 10. Rwaha Reversed (Priority 10)
- **Pattern**: `ܷ` (U+0737)
- **Replacement**: (empty)
- **Purpose**: Remove Rwaha reversed (East Syriac /u/)
- **Phonetic**: East Syriac /u/ vowel

#### 11. Rbasa (Priority 11)
- **Pattern**: `ܶ` (U+0736)
- **Replacement**: (empty)
- **Purpose**: Remove Rbasa (two dots above, East Syriac /e/)
- **Phonetic**: East Syriac /e/ vowel

#### 12. Dotted Zlama (Priority 12)
- **Pattern**: `ܵ` (U+0735)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama (East Syriac /a/)
- **Phonetic**: East Syriac /a/ vowel (variant)

#### 13. Pthaha (Priority 13)
- **Pattern**: `ܴ` (U+0734)
- **Replacement**: (empty)
- **Purpose**: Remove Pthaha (West Syriac /a/)
- **Phonetic**: West Syriac /a/ vowel

#### 14. Zlama Horizontal (Priority 14)
- **Pattern**: `ܳ` (U+0733)
- **Replacement**: (empty)
- **Purpose**: Remove Zlama horizontal (West Syriac /o/)
- **Phonetic**: West Syriac /o/ vowel

#### 15. Pthaha Dotted (Priority 15)
- **Pattern**: `ܲ` (U+0732)
- **Replacement**: (empty)
- **Purpose**: Remove Pthaha dotted
- **Phonetic**: Vowel variant

#### 16. Zlama Angular (Priority 16)
- **Pattern**: `ܱ` (U+0731)
- **Replacement**: (empty)
- **Purpose**: Remove Zlama angular
- **Phonetic**: Vowel variant

#### 17. Pthaha (Priority 17)
- **Pattern**: `ܰ` (U+0730)
- **Replacement**: (empty)
- **Purpose**: Remove Pthaha (East Syriac /a/)
- **Phonetic**: East Syriac /a/ vowel

### Catch-All Ranges (Priorities 18-19)

#### 18. All Points Above (Priority 18)
- **Pattern**: `[\u0730-\u073F]`
- **Replacement**: (empty)
- **Purpose**: Catch-all for supralinear vowel points
- **Unicode Range**: U+0730 to U+073F

#### 19. All Points Below (Priority 19)
- **Pattern**: `[\u0740-\u074A]`
- **Replacement**: (empty)
- **Purpose**: Catch-all for sublinear vowel points
- **Unicode Range**: U+0740 to U+074A

### Combining Diacritics (Priorities 20-21)

#### 20. Combining Diacritics Above (Priority 20)
- **Pattern**: `[\u0308\u030A\u0304\u0307]`
- **Replacement**: (empty)
- **Purpose**: Remove combining diacritics (dots, macrons)
- **Includes**:
  - U+0308: Combining diaeresis
  - U+030A: Combining ring above
  - U+0304: Combining macron
  - U+0307: Combining dot above

#### 21. Combining Dots Below (Priority 21)
- **Pattern**: `[\u0323\u0324\u0325]`
- **Replacement**: (empty)
- **Purpose**: Remove combining dots below
- **Includes**:
  - U+0323: Combining dot below
  - U+0324: Combining diaeresis below
  - U+0325: Combining ring below

### Pronunciation Markers (Priorities 22-23)

#### 22. Qushshaya (Priority 22)
- **Pattern**: `݁` (U+0741)
- **Replacement**: (empty)
- **Purpose**: Remove Qushshaya (hard pronunciation marker)
- **Example**: Indicates hard pronunciation of ܒܓܕܟܦܬ letters
- **Linguistic**: Begadkepat letters pronounced as stops (not fricatives)

#### 23. Rukkakha (Priority 23)
- **Pattern**: `݂` (U+0742)
- **Replacement**: (empty)
- **Purpose**: Remove Rukkakha (soft pronunciation marker)
- **Example**: Indicates soft/spirantized pronunciation
- **Linguistic**: Begadkepat letters pronounced as fricatives

### Editorial and Special Marks (Priorities 24-29)

#### 24. Feminine Dot (Priority 24)
- **Pattern**: `݀` (U+0740)
- **Replacement**: (empty)
- **Purpose**: Remove Syriac feminine dot
- **Usage**: Marks feminine nouns (grammatical indicator)

#### 25. Harklean Obelus (Priority 25)
- **Pattern**: `܌` (U+070C)
- **Replacement**: (empty)
- **Purpose**: Remove Harklean Obelus (critical edition mark)
- **Usage**: Harklean version of New Testament (7th century)
- **Meaning**: Marks textual variants or asterisks

#### 26. Harklean Metobelus (Priority 26)
- **Pattern**: `܍` (U+070D)
- **Replacement**: (empty)
- **Purpose**: Remove Harklean Metobelus (critical edition mark)
- **Usage**: Harklean version closing mark
- **Meaning**: Closes passages marked with obelus

#### 27. Abbreviation Mark (Priority 27)
- **Pattern**: `܏` (U+070F)
- **Replacement**: (empty)
- **Purpose**: Remove Syriac abbreviation mark
- **Usage**: Marks abbreviated words (especially nomina sacra)

#### 28. Abbreviation Mark Alt (Priority 28)
- **Pattern**: `[\u070F]`
- **Replacement**: (empty)
- **Purpose**: Remove Syriac abbreviation mark (redundant catch)
- **Unicode**: U+070F

#### 29. Superscript Alaph (Priority 29)
- **Pattern**: `[\u0711]`
- **Replacement**: (empty)
- **Purpose**: Remove Syriac letter Superscript Alaph
- **Usage**: Marks vowel lengthening or silent alaph
- **Example**: Historical orthography

## Usage in Dictionary Files

Include this file as `normalization_rules.csv` in your Syriac dictionary ZIP file:

```
my-syriac-dictionary.zip
├── dictionary.csv          (Syriac entries)
├── morphology.csv          (Optional: lemma mappings)
└── normalization_rules.csv (This file, renamed)
```

Or use the language-specific filename:
```
└── normalization_rules_syriac.csv
```

## Example Transformations

### Peshitta Old Testament (Genesis 1:1)
**Input (with East Syriac vowels):**
```
ܒ݁ܪܺܫܺܝܬ݂ ܒ݁ܪܳܐ ܐܰܠܳܗܳܐ ܝܳܬ݂ ܫܡܰܝܳܐ ܘܝܳܬ݂ ܐܰܪܥܳܐ
```

**After normalization:**
```
ܒܪܫܝܬ ܒܪܐ ܐܠܗܐ ܝܬ ܫܡܝܐ ܘܝܬ ܐܪܥܐ
```
(Removes all vowels and pronunciation marks)

### Peshitta New Testament (John 1:1)
**Input (with West Syriac vowels):**
```
ܒ݁ܪܺܫܺܝܬ݂ ܐܺܝܬ݂ܰܘܗ݈ܝ ܗ݈ܘܳܐ ܡܶܠܬ݂ܳܐ ܘܗܽܘ ܡܶܠܬ݂ܳܐ ܐܺܝܬ݂ܰܘܗ݈ܝ ܗ݈ܘܳܐ ܠܘܳܬ݂ ܐܰܠܳܗܳܐ ܘܰܐܠܳܗܳܐ ܐܺܝܬ݂ܰܘܗ݈ܝ ܗ݈ܘܳܐ ܗܽܘ ܡܶܠܬ݂ܳܐ
```

**After normalization:**
```
ܒܪܫܝܬ ܐܝܬܘܗܝ ܗܘܐ ܡܠܬܐ ܘܗܘ ܡܠܬܐ ܐܝܬܘܗܝ ܗܘܐ ܠܘܬ ܐܠܗܐ ܘܐܠܗܐ ܐܝܬܘܗܝ ܗܘܐ ܗܘ ܡܠܬܐ
```
(In the beginning was the Word...)

### Syriac Liturgy
**Input (with vocalization):**
```
ܩܰܕܺܝܫܰܬ݂ ܐܰܠܳܗܳܐ ܩܰܕܺܝܫܰܬ݂ ܚܰܝܠܬ݂ܳܢܳܐ ܩܰܕܺܝܫܰܬ݂ ܠܳܐ ܡܳܝܽܘܬ݂ܳܐ
```

**After normalization:**
```
ܩܕܝܫܬ ܐܠܗܐ ܩܕܝܫܬ ܚܝܠܬܢܐ ܩܕܝܫܬ ܠܐ ܡܝܘܬܐ
```
(Trisagion: "Holy God, Holy Mighty, Holy Immortal...")

### Ephrem the Syrian
**Input (with diacritics):**
```
ܡܳܪܝܳܐ ܡܫܺܝܚܳܐ ܐܰܢ̱ܬ݁ ܗ̱ܘ ܢܽܘܗܪܳܐ
```

**After normalization:**
```
ܡܪܝܐ ܡܫܝܚܐ ܐܢܬ ܗܘ ܢܘܗܪܐ
```
("Lord Christ, you are the light")

## Technical Details

### Script Characteristics
- **Direction**: Right-to-left
- **Unicode Range**: U+0700 to U+074F
- **Vowel Points**: U+0730 to U+074A
- **Special Characters**: U+0700 to U+070F

### Three Script Styles

#### 1. Estrangela (Classical)
- Most ancient form
- Used for inscriptions and formal texts
- No inherent vowels (abjad)

#### 2. Serto (West Syriac)
- Cursive script
- Used by West Syriac churches
- Greek-influenced vowel system

#### 3. East Syriac (Nestorian)
- Angular script
- Used by East Syriac churches
- Indigenous vowel system

### Begadkepat Letters
Like Hebrew, Syriac has six letters (ܒܓܕܟܦܬ) that can be pronounced two ways:
- **Qushshaya** (݁): Hard/stop pronunciation (b, g, d, k, p, t)
- **Rukkakha** (݂): Soft/fricative pronunciation (v, ḡ, ḏ, ḵ, f, ṯ)

These markers are removed for normalization.

### Unicode NFD Normalization
All patterns are applied **after** Unicode NFD (Canonical Decomposition) normalization.

### Pattern Order
Patterns are applied in priority order (1-29). Lower numbers are applied first.

## Common Use Cases

### Biblical Texts
- **Peshitta Old Testament** (2nd-3rd century CE)
- **Peshitta New Testament** (2nd century CE)
- **Harklean Version** (7th century, with critical marks)
- **Philoxenian Version** (6th century)

### Patristic Literature
- **Ephrem the Syrian** (4th century)
- **Aphrahat** (4th century)
- **Jacob of Serugh** (5th-6th century)
- **Isaac of Nineveh** (7th century)
- **Bar Hebraeus** (13th century)

### Liturgical Texts
- **East Syriac Liturgy** (Chaldean, Assyrian)
- **West Syriac Liturgy** (Syrian Orthodox, Maronite)
- **Hymns** (Madrashe, Sogitha)
- **Prayer books**

### Historical and Scientific Texts
- **Syriac Chronicles**
- **Medical texts** (translations from Greek)
- **Philosophical works** (Aristotle, etc.)
- **Astronomical texts**

## Dialects and Periods

These rules work for all periods and dialects of Classical Syriac:
- **Early Syriac** (1st-3rd century)
- **Classical Syriac** (4th-7th century)
- **Middle Syriac** (8th-13th century)
- **Modern Literary Syriac** (continuing tradition)

## Regional Variants
- **Edessene** (Urfa/Edessa - standard literary dialect)
- **Mesopotamian**
- **Palestinian**
- **Eastern** (Persian-influenced)

## Notes

### Relationship to Aramaic
Syriac is an **Eastern Aramaic** dialect, closely related to:
- Jewish Babylonian Aramaic (Talmudic)
- Mandaic
- Other Eastern Aramaic dialects

However, Syriac developed its own:
- Unique script
- Literary tradition
- Vowel systems
- Pronunciation conventions

### Why Separate from Aramaic Rules?
While Aramaic and Syriac share the same linguistic roots, they are treated separately because:
1. **Different scripts**: Syriac script vs. Hebrew script (for Jewish Aramaic)
2. **Different vowel systems**: Syriac has unique vocalization not used in Hebrew-script Aramaic
3. **Different traditions**: Christian vs. Jewish literary traditions
4. **User clarity**: Scholars typically work with one or the other

### Modern Syriac
These rules are for **Classical/Literary Syriac**. Modern spoken Neo-Aramaic dialects (Assyrian Neo-Aramaic, Chaldean Neo-Aramaic, Turoyo) may have different orthographic conventions.

## Implementation Notes

When using these rules in the Classics Viewer app:
1. Rules are loaded from the CSV file during dictionary import
2. Greek and Latin patterns are automatically filtered out
3. Normalization happens at **lookup time**, not import time
4. Patterns are cached for performance
5. Text undergoes NFD normalization before pattern application
6. Both East and West Syriac vowel systems are handled

## References

- Unicode Standard for Syriac: U+0700 to U+074F
- Syriac grammar (Theodor Nöldeke, Takamitsu Muraoka)
- Peshitta Institute editions
- CAL (Comprehensive Aramaic Lexicon)
- Syriac Digital Library
- Beth Mardutho Syriac Institute resources
