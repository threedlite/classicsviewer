# Aramaic Normalization Rules

## Overview

These normalization rules handle Aramaic text written in both **Hebrew script** (Imperial/Biblical Aramaic) and **Syriac script** (Classical Syriac). They remove vocalization marks, cantillation, and normalize final letter forms to enable consistent dictionary lookups across different text traditions.

## Background

Aramaic was written in multiple scripts throughout history:
- **Imperial Aramaic** (5th-3rd century BCE): Early square script
- **Biblical Aramaic** (portions of Daniel, Ezra): Hebrew square script with Aramaic vocabulary
- **Jewish Aramaic** (Targums, Talmud): Hebrew script
- **Syriac** (Christian Aramaic): Distinct script derived from Aramaic
- **Mandaic, Nabatean, Palmyrene**: Other historical variants

These rules handle the two most common modern representations:
1. **Hebrew-script Aramaic** (Biblical, Targumic, Talmudic)
2. **Syriac-script Aramaic** (Peshitta, Syriac literature)

## Normalization Rules

### Hebrew-Script Aramaic (Priorities 1-2, 14-18)

#### 1. Hebrew Cantillation Marks (Priority 1)
- **Pattern**: `[\u0591-\u05AF]`
- **Replacement**: (empty)
- **Purpose**: Remove all Hebrew/Aramaic cantillation marks
- **Unicode Range**: U+0591 to U+05AF
- **Example**: Biblical Aramaic portions of Daniel with ta'amim
- **Note**: Same marks used in Hebrew Bible, applied to Aramaic sections

#### 2. Hebrew/Aramaic Vocalization Points (Priority 2)
- **Pattern**: `[\u05B0-\u05BD\u05BF\u05C1-\u05C2\u05C4-\u05C5\u05C7]`
- **Replacement**: (empty)
- **Purpose**: Remove all nikud (vocalization points)
- **Includes**:
  - Shva, Hataf vowels
  - Dagesh, Mappiq
  - Rafe
  - Shin/Sin dots
  - Vowel points (hiriq, segol, patah, qamats, etc.)
- **Unicode Range**: U+05B0 to U+05C7
- **Example**: `מַלְכָּא` → `מלכא` (malka, "king" in Aramaic)

#### 3. Final Letter Forms (Priorities 14-18)
These normalize final letter forms to their regular counterparts:

- **Final Kaf** (ך → כ): `מַלְכָּא` → `מלכא`
- **Final Mem** (ם → מ): `שָׁלוֹם` → `שלום`
- **Final Nun** (ן → נ): `מִן` → `מנ`
- **Final Pe** (ף → פ): `יוֹסֵף` → `יוסף`
- **Final Tsadi** (ץ → צ): `אֶרֶץ` → `ארצ`

**Note**: Same final letters as Hebrew, since Biblical Aramaic uses Hebrew script

### Syriac-Script Aramaic (Priorities 3-13)

#### 4. Syriac Vocalization Marks (Priority 3)
- **Pattern**: `[\u0730-\u074A]`
- **Replacement**: (empty)
- **Purpose**: Remove all Syriac vocalization marks
- **Unicode Range**: U+0730 to U+074A
- **Covers**: West Syriac and East Syriac vowel systems

#### 5. Syriac Rwaha (Priority 4)
- **Pattern**: `ܿ` (U+073F)
- **Replacement**: (empty)
- **Purpose**: Remove Rwaha (supralinear dot, West Syriac /o/)
- **Example**: `ܡܿܠܟܐ` → `ܡܠܟܐ` (malka)

#### 6. Syriac Dotted Zlama Angular (Priority 5)
- **Pattern**: `ܾ` (U+073E)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama angular (West Syriac vowel)

#### 7. Syriac Hbasa (Priority 6)
- **Pattern**: `ܼ` (U+073C)
- **Replacement**: (empty)
- **Purpose**: Remove Hbasa (sublinear dot, West Syriac /i/)
- **Example**: Vocalization in Peshitta manuscripts

#### 8. Syriac Dotted Zlama Horizontal (Priority 7)
- **Pattern**: `ܻ` (U+073B)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama horizontal (East Syriac vowel)

#### 9. Syriac Hbasa-Esasa (Priority 8)
- **Pattern**: `ܺ` (U+073A)
- **Replacement**: (empty)
- **Purpose**: Remove Hbasa-Esasa (two dots below, East Syriac /i/)

#### 10. Syriac Esasa (Priority 9)
- **Pattern**: `ܹ` (U+0739)
- **Replacement**: (empty)
- **Purpose**: Remove Esasa (dot below, East Syriac /e/)

#### 11. Syriac Dotted Zlama (Priority 10)
- **Pattern**: `ܸ` (U+0738)
- **Replacement**: (empty)
- **Purpose**: Remove dotted Zlama (East Syriac /a/)

#### 12. Syriac Rwaha Reversed (Priority 11)
- **Pattern**: `ܷ` (U+0737)
- **Replacement**: (empty)
- **Purpose**: Remove Rwaha reversed (East Syriac /u/)

#### 13. All Syriac Points Above (Priority 12)
- **Pattern**: `[\u0730-\u073F]`
- **Replacement**: (empty)
- **Purpose**: Catch-all for supralinear Syriac vowel points
- **Unicode Range**: U+0730 to U+073F

#### 14. All Syriac Points Below (Priority 13)
- **Pattern**: `[\u0740-\u074A]`
- **Replacement**: (empty)
- **Purpose**: Catch-all for sublinear Syriac vowel points
- **Unicode Range**: U+0740 to U+074A

## Usage in Dictionary Files

Include this file as `normalization_rules.csv` in your Aramaic dictionary ZIP file:

```
my-aramaic-dictionary.zip
├── dictionary.csv          (Aramaic entries)
├── morphology.csv          (Optional: lemma mappings)
└── normalization_rules.csv (This file, renamed)
```

Or use the language-specific filename:
```
└── normalization_rules_aramaic.csv
```

## Example Transformations

### Biblical Aramaic (Daniel 2:4)
**Input (with nikud):**
```
מַלְכָּא לְעָלְמִין חֱיִי
```

**After normalization:**
```
מלכא לעלמין חיי
```
(Removes vocalization: "O king, live forever!")

### Targum Onkelos (Genesis 1:1)
**Input (with vocalization):**
```
בְּקַדְמִיתָא בְּרָא יְיָ יָת שְׁמַיָּא וְיָת אַרְעָא
```

**After normalization:**
```
בקדמיתא ברא יי ית שמיא וית ארעא
```
(Removes nikud from Aramaic translation)

### Syriac Peshitta (John 1:1)
**Input (with West Syriac vowels):**
```
ܒ݁ܪܺܫܺܝܬ݂ ܐܺܝܬ݂ܰܘܗ݈ܝ ܗ݈ܘܳܐ ܡܶܠܬ݂ܳܐ
```

**After normalization:**
```
ܒܪܫܝܬ ܐܝܬܘܗܝ ܗܘܐ ܡܠܬܐ
```
(Removes Syriac vowel points: "In the beginning was the Word")

### Talmudic Aramaic
**Input:**
```
אָמַר רַב יְהוּדָה אָמַר רַב
```

**After normalization:**
```
אמר רב יהודה אמר רב
```
(Removes vocalization from Talmudic quotation)

## Technical Details

### Two Script Systems

#### Hebrew Script (U+0590-U+05FF)
Used for:
- Biblical Aramaic (Daniel, Ezra)
- Targumim (Onkelos, Jonathan, etc.)
- Talmudic Aramaic (Bavli, Yerushalmi)
- Jewish Aramaic texts

#### Syriac Script (U+0700-U+074F)
Used for:
- Peshitta (Old Testament and New Testament)
- Syriac Fathers (Ephrem, Aphrahat, etc.)
- Liturgical texts
- Eastern and Western Syriac traditions

### Vocalization Systems

#### Hebrew-Based System
- Same nikud as Hebrew
- Used in printed Targums and Biblical texts
- Tiberian, Babylonian, and Palestinian systems

#### Syriac Systems
- **West Syriac (Jacobite)**: Uses Greek-derived vowel system
- **East Syriac (Nestorian)**: Uses dots above and below
- **Both**: Supralinear and sublinear points

### Unicode NFD Normalization
All patterns are applied **after** Unicode NFD (Canonical Decomposition) normalization.

### Pattern Order
Patterns are applied in priority order (1-18). Lower numbers are applied first.

## Common Use Cases

### Biblical Aramaic
- Daniel 2-7 (Aramaic sections)
- Ezra 4-7 (Aramaic documents)
- Jeremiah 10:11 (one Aramaic verse)
- Genesis 31:47 (Laban's phrase)

### Targumim
- Targum Onkelos (Pentateuch)
- Targum Jonathan (Prophets)
- Targum Pseudo-Jonathan
- Fragment Targums

### Talmudic Literature
- Babylonian Talmud (mainly Aramaic)
- Jerusalem Talmud
- Midrash Rabbah (Aramaic portions)

### Syriac Literature
- Peshitta Bible
- Syriac Fathers
- Liturgical texts (East and West Syriac)
- Diatessaron

### Other Aramaic Texts
- Dead Sea Scrolls (Aramaic portions)
- Elephantine papyri
- Nabatean inscriptions
- Palmyrene inscriptions
- Magic bowls

## Dialects Covered

These rules work for Aramaic texts in:
- **Imperial/Official Aramaic** (Achaemenid period)
- **Biblical Aramaic** (Hebrew Bible portions)
- **Jewish Literary Aramaic** (Targums, Talmud)
- **Classical Syriac** (Peshitta, Syriac Fathers)
- **Christian Palestinian Aramaic**
- **Samaritan Aramaic**

## Not Covered

These rules do **not** handle:
- **Mandaic script** (requires separate rules)
- **Nabatean script** (proto-Arabic precursor)
- **Palmyrene script** (monumental inscriptions)
- **Arabic transcriptions** of Aramaic (use Arabic rules)
- **Latin transcriptions** (romanization)

## Notes

### Why Two Script Systems?
Aramaic had a long history (1000+ BCE to present) and was adopted by different communities who developed their own scripts. Jews used Hebrew script, Christians developed Syriac script, and Mandaeans created their own script.

### Dialect Differences
The rules normalize **orthographic** differences (spelling, vocalization), not **dialectal** differences (vocabulary, grammar). Dictionary entries should account for dialectal variations in their lemma mappings.

### East vs. West Syriac
The two main Syriac traditions use different vowel systems:
- **East Syriac** (Nestorian/Chaldean): Dots and diacritics
- **West Syriac** (Jacobite/Maronite): Different dot patterns

These rules remove both systems' vowel marks.

## Implementation Notes

When using these rules in the Classics Viewer app:
1. Rules are loaded from the CSV file during dictionary import
2. Greek and Latin patterns are automatically filtered out
3. Normalization happens at **lookup time**, not import time
4. Patterns are cached for performance
5. Text undergoes NFD normalization before pattern application
6. Both Hebrew-script and Syriac-script Aramaic are handled

## References

- Unicode Standard for Hebrew: U+0590 to U+05FF
- Unicode Standard for Syriac: U+0700 to U+074F
- Biblical Aramaic grammar (Rosenthal, Stevenson)
- Syriac grammar (Nöldeke, Muraoka)
- Targum texts and traditions
- Peshitta Bible editions
