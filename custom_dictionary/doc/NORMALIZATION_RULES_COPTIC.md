# Coptic Normalization Rules

## Overview

These normalization rules handle Coptic text, the last stage of the ancient Egyptian language written in a modified Greek alphabet. The rules remove diacritical marks used in modern scholarly editions and normalize uppercase/lowercase variants to enable consistent dictionary lookups.

## Background

**Coptic** is the final stage of the Egyptian language, written using:
- **24 letters from Greek alphabet** (for Greek loanwords and Greek sounds)
- **6-8 letters from Demotic** (for native Egyptian sounds not in Greek)

The Coptic alphabet was developed around the 2nd-3rd century CE and became the liturgical language of Egyptian Christianity. It survives today in the Coptic Orthodox Church.

### Historical Context
- **Language**: Final stage of Ancient Egyptian (Pharaonic → Demotic → Coptic)
- **Script**: Greek alphabet + Demotic-derived letters
- **Period**: 2nd century CE to present (liturgical use)
- **Users**: Egyptian Christians (Copts)
- **Literature**: Biblical translations, patristic texts, liturgies, monastic literature

### Major Dialects
1. **Sahidic** (Upper Egypt) - classical literary dialect, most common
2. **Bohairic** (Lower Egypt/Delta) - modern liturgical standard
3. **Fayyumic** (Fayyum Oasis)
4. **Akhmimic** (Akhmim region)
5. **Lycopolitan/Subakhmimic** (Asyut region)
6. **Old Nubian** (Nubia, related but distinct)

## Normalization Rules

### Combining Diacritics (Priorities 1-10, 21-22)

#### 1. Grave and Acute Accents (Priority 1)
- **Pattern**: `[\u0300-\u0301]`
- **Replacement**: (empty)
- **Purpose**: Remove combining grave (`) and acute (´) accents
- **Unicode**: U+0300 (grave), U+0301 (acute)
- **Usage**: Modern scholarly editions use accents to mark stress
- **Example**: `ⲛⲟⲩⲧⲉ́` → `ⲛⲟⲩⲧⲉ` (noute, "god")

#### 2. Macron and Overline (Priority 2)
- **Pattern**: `[\u0304-\u0305]`
- **Replacement**: (empty)
- **Purpose**: Remove combining macron (¯) and overline
- **Unicode**: U+0304 (macron), U+0305 (overline)
- **Usage**: Marks long vowels or abbreviations (nomina sacra)
- **Example**: `ⲓ̄ⲥ̄` → `ⲓⲥ` (Iesous/Jesus - nomen sacrum)

#### 3. Diaeresis (Priority 3)
- **Pattern**: `[\u0308]`
- **Replacement**: (empty)
- **Purpose**: Remove combining diaeresis (¨)
- **Unicode**: U+0308
- **Usage**: Marks syllable separation in vowel sequences
- **Example**: `ⲁⲏ̈ⲣ` → `ⲁⲏⲣ` (air, "river")

#### 4. Breathing Marks (Priority 4)
- **Pattern**: `[\u0313-\u0314]`
- **Replacement**: (empty)
- **Purpose**: Remove combining comma above (smooth breathing) and reversed comma above (rough breathing)
- **Unicode**: U+0313 (psili), U+0314 (dasia)
- **Usage**: Borrowed from Greek orthography
- **Example**: Greek loanwords in Coptic texts

#### 5. Dot Below (Priority 5)
- **Pattern**: `[\u0323]`
- **Replacement**: (empty)
- **Purpose**: Remove combining dot below
- **Unicode**: U+0323
- **Usage**: Marks certain phonetic features in scholarly transcriptions

#### 6. Macron Below (Priority 6)
- **Pattern**: `[\u0331]`
- **Replacement**: (empty)
- **Purpose**: Remove combining macron below
- **Unicode**: U+0331
- **Usage**: Rare scholarly notation

#### 7-10. Individual Combining Marks (Priorities 7-10)
- **Grave accent**: ̀ (U+0300)
- **Acute accent**: ́ (U+0301)
- **Macron**: ̄ (U+0304)
- **Diaeresis**: ̈ (U+0308)
- **Purpose**: Redundant with ranges, ensures removal

#### 21. All Combining Diacritics Catch-All (Priority 21)
- **Pattern**: `[\u0300-\u036F]`
- **Replacement**: (empty)
- **Purpose**: Remove all combining diacritical marks
- **Unicode Range**: Complete combining diacritics block
- **Coverage**: Comprehensive catch-all for any missed marks

#### 22. Coptic-Specific Combining Marks (Priority 22)
- **Pattern**: `[\u2CBD-\u2CBE]`
- **Replacement**: (empty)
- **Purpose**: Remove Coptic combining diacritics
- **Unicode**: U+2CBD to U+2CBE

### Coptic-Specific Diacritics (Priorities 17-20)

#### 17. Old Nubian Combining Dot Below (Priority 17)
- **Pattern**: `⳨` (U+2CE8)
- **Replacement**: (empty)
- **Purpose**: Remove Old Nubian combining dot below
- **Usage**: Old Nubian texts (related to Coptic)

#### 18. Coptic Combining Ni Above (Priority 18)
- **Pattern**: `⳩` (U+2CE9)
- **Replacement**: (empty)
- **Purpose**: Remove Coptic combining ni above
- **Usage**: Marks nasalization or abbreviation

#### 19. Coptic Spiritus Asper (Priority 19)
- **Pattern**: `⳪` (U+2CEA)
- **Replacement**: (empty)
- **Purpose**: Remove Coptic combining spiritus asper
- **Usage**: Rough breathing mark (from Greek)

#### 20. Coptic Spiritus Lenis (Priority 20)
- **Pattern**: `Ⳬ` (U+2CEC)
- **Replacement**: (empty)
- **Purpose**: Remove Coptic combining spiritus lenis
- **Usage**: Smooth breathing mark (from Greek)

### Case Normalization (Priorities 23-61)

All uppercase Coptic letters are normalized to lowercase for consistent dictionary lookups.

#### Greek-Derived Letters (Priorities 23-47)

**24 Greek alphabet letters used in Coptic:**

- Ⲁ → ⲁ (alfa/alpha)
- Ⲃ → ⲃ (beta/vida)
- Ⲅ → ⲅ (gamma/gima)
- Ⲇ → ⲇ (dalda/delta)
- Ⲉ → ⲉ (ei/epsilon)
- Ⲋ → ⲋ (so/stigma - dialectal)
- Ⲍ → ⲍ (zata/zeta)
- Ⲏ → ⲏ (eta/ita)
- Ⲑ → ⲑ (theta/thita)
- Ⲓ → ⲓ (iota/yota)
- Ⲕ → ⲕ (kappa/kapa)
- Ⲗ → ⲗ (lambda/laula)
- Ⲙ → ⲙ (me/mi)
- Ⲛ → ⲛ (ne/ni)
- Ⲝ → ⲝ (ksi/xi)
- Ⲟ → ⲟ (o/omicron)
- Ⲡ → ⲡ (pi)
- Ⲣ → ⲣ (ro/rho)
- Ⲥ → ⲥ (sima/sigma)
- Ⲧ → ⲧ (tau/taw)
- Ⲩ → ⲩ (he/upsilon)
- Ⲫ → ⲫ (fi/phi)
- Ⲭ → ⲭ (khi/chi)
- Ⲯ → ⲯ (psi)
- Ⲱ → ⲱ (o/omega)

#### Coptic-Specific Letters (Priorities 48-61)

**Letters derived from Demotic Egyptian:**

- Ⲳ → ⲳ (shei/shai - /ʃ/)
- Ⲵ → ⲵ (fai - /f/)
- Ⲷ → ⲷ (khai - /x/)
- Ⲹ → ⲹ (hori - /h/)
- Ⲻ → ⲻ (janja - /ɟ/ or /dʒ/)
- Ⲽ → ⲽ (khima/kima)
- Ⲿ → ⲿ (ti - /t/ or /ti/)

**Additional forms:**
- Ϣ → ϣ (shai - /ʃ/, most common form)
- Ϥ → ϥ (fai - /f/, most common form)
- Ϧ → ϧ (hori variant)
- Ϩ → ϩ (hori - /h/, most common form)
- Ϫ → ϫ (janja - /ɟ/, most common form)
- Ϭ → ϭ (khei - /kʰ/ or /x/)
- Ϯ → ϯ (ti, most common form)

**Note**: Some Coptic letters have multiple Unicode representations. These rules normalize the major variants.

## Usage in Dictionary Files

Include this file as `normalization_rules.csv` in your Coptic dictionary ZIP file:

```
my-coptic-dictionary.zip
├── dictionary.csv          (Coptic entries)
├── morphology.csv          (Optional: lemma mappings)
└── normalization_rules.csv (This file, renamed)
```

Or use the language-specific filename:
```
└── normalization_rules_coptic.csv
```

## Example Transformations

### Coptic New Testament (John 1:1)
**Input (with diacritics and uppercase):**
```
Ϩⲛ̄ Ⲧⲁⲣⲭⲏ́ ⲛⲉⲣⲉ Ⲡϣⲁϫⲉ ϣⲟⲟⲡ
```

**After normalization:**
```
ϩⲛ ⲧⲁⲣⲭⲏ ⲛⲉⲣⲉ ⲡϣⲁϫⲉ ϣⲟⲟⲡ
```
(In the beginning was the Word)

### Sahidic Psalms (Psalm 1:1)
**Input:**
```
Ⲟⲩⲙⲁⲕⲁⲣⲓⲟⲥ ⲡⲉ Ⲡⲣⲱⲙⲉ ⲉⲧⲉ ⲙ̄ⲡⲉϥⲙⲟⲟϣⲉ
```

**After normalization:**
```
ⲟⲩⲙⲁⲕⲁⲣⲓⲟⲥ ⲡⲉ ⲡⲣⲱⲙⲉ ⲉⲧⲉ ⲙⲡⲉϥⲙⲟⲟϣⲉ
```
(Blessed is the man who has not walked...)

### Bohairic Liturgy
**Input:**
```
Ⲁⲅⲓⲟⲥ Ⲟ̀ Ⲑⲉⲟⲥ Ⲁⲅⲓⲟⲥ Ⲓⲥⲭⲩⲣⲟⲥ
```

**After normalization:**
```
ⲁⲅⲓⲟⲥ ⲟ ⲑⲉⲟⲥ ⲁⲅⲓⲟⲥ ⲓⲥⲭⲩⲣⲟⲥ
```
(Holy God, Holy Mighty - Trisagion in Coptic)

### Nomina Sacra
**Input (with abbreviation marks):**
```
Ⲓ̄Ⲥ̄ Ⲡⲉⲭ̄Ⲥ̄ Ⲡϣⲏⲣⲉ ⲙ̄Ⲡⲛⲟⲩⲧⲉ
```

**After normalization:**
```
ⲓⲥ ⲡⲉⲭⲥ ⲡϣⲏⲣⲉ ⲙⲡⲛⲟⲩⲧⲉ
```
(Jesus Christ, the Son of God - with nomina sacra normalized)

### Shenoute of Atripe
**Input (classical Sahidic):**
```
Ⲁⲛⲟⲕ ⲡⲉ Ⲡⲉⲭ̄ⲥ̄ Ⲡⲛⲟⲩⲧⲉ
```

**After normalization:**
```
ⲁⲛⲟⲕ ⲡⲉ ⲡⲉⲭⲥ ⲡⲛⲟⲩⲧⲉ
```
(I am Christ the God)

## Technical Details

### Script Characteristics
- **Direction**: Left-to-right (like Greek)
- **Unicode Ranges**:
  - U+03E2 to U+03EF (Coptic in Greek block)
  - U+2C80 to U+2CFF (Coptic block)
  - U+102E0 to U+102FF (Coptic Epact Numbers)
- **Case**: Has uppercase/lowercase distinction
- **Alphabet Size**: 30-32 letters (depending on dialect)

### Coptic Alphabet

#### Greek-Derived (24 letters)
Α Β Γ Δ Ε Ϛ Ζ Η Θ Ι Κ Λ Μ Ν Ξ Ο Π Ρ Σ Τ Υ Φ Χ Ψ Ω

#### Demotic-Derived (6-8 letters)
Ϣ (shai), Ϥ (fai), Ϧ/Ϩ (hori), Ϫ (janja), Ϭ (khei/khima), Ϯ (ti)

Some dialects add: Ⳁ (cryptogrammic ni), ⳉ (dialect-p), etc.

### Dialectal Differences

Different Coptic dialects use slightly different alphabets:
- **Sahidic**: Standard 31-letter alphabet
- **Bohairic**: Similar to Sahidic, modern liturgical standard
- **Fayyumic**: Some unique letter forms
- **Akhmimic**: Preserves some archaic features
- **Lycopolitan**: Transitional features

These rules handle all major dialects.

### Nomina Sacra

Like Greek manuscripts, Coptic texts abbreviate sacred names:
- ⲓ̄ⲥ̄ = ⲓⲏⲥⲟⲩⲥ (Jesus)
- ⲡⲭ̄ⲥ̄ = ⲡⲉⲭⲣⲓⲥⲧⲟⲥ (Christ)
- ⲡⲛ̄ⲁ̄ = ⲡⲛⲉⲩⲙⲁ (Spirit)
- ⲙ̄ⲡⲛ̄ⲁ̄ = ⲙⲡⲛⲉⲩⲙⲁ (of the Spirit)

Overlines (macrons) mark abbreviations; normalization removes them.

### Unicode NFD Normalization
All patterns are applied **after** Unicode NFD (Canonical Decomposition) normalization, which separates base characters from combining marks.

### Pattern Order
Patterns are applied in priority order (1-61). Lower numbers are applied first.

## Common Use Cases

### Biblical Texts
- **Sahidic New Testament** (3rd-4th century)
- **Bohairic New Testament** (modern liturgical version)
- **Sahidic Old Testament** (fragments and books)
- **Psalms** (complete in multiple dialects)
- **Coptic Apocrypha**

### Patristic Literature
- **Shenoute of Atripe** (4th-5th century, White Monastery)
- **Pachomius** (monastic rules)
- **Athanasius** (some works preserved in Coptic)
- **Homilies and Sermons**

### Monastic Literature
- **Lives of the Saints** (hagiography)
- **Apophthegmata Patrum** (Sayings of the Desert Fathers)
- **Monastic Rules**
- **Ascetic Treatises**

### Liturgical Texts
- **Coptic Liturgy of St. Basil**
- **Liturgy of St. Gregory**
- **Liturgy of St. Cyril**
- **Hymns** (Psalis, Tarh, etc.)
- **Prayer Books**

### Gnostic Texts
- **Nag Hammadi Library** (mostly Sahidic, 4th century)
  - Gospel of Thomas
  - Gospel of Philip
  - Apocryphon of John
  - Gospel of Truth
  - Many others

### Magical Texts
- **Coptic Magical Papyri**
- **Amulets and Spells**
- **Medical Texts**

### Documentary Texts
- **Letters**
- **Legal Documents**
- **Economic Records**
- **Ostraca** (pottery sherds with writing)

## Relationship to Other Languages

### Ancient Egyptian Stages
1. **Old Egyptian** (Pyramid Texts) - hieroglyphic
2. **Middle Egyptian** (Classical period) - hieroglyphic
3. **Late Egyptian** (New Kingdom) - hieroglyphic/hieratic
4. **Demotic** (Ptolemaic/Roman) - demotic script
5. **Coptic** (Roman/Byzantine) - Coptic alphabet

Coptic is the final stage, preserving the spoken language in alphabetic form.

### Greek Influence
- Alphabet borrowed from Greek
- Massive Greek loanwords (theological, philosophical terms)
- Bilingual texts (Greek-Coptic)
- Translation literature (Greek → Coptic)

### Arabic Influence
- After Arab conquest (7th century), Arabic gradually replaced Coptic
- Coptic-Arabic glossaries
- Arabic loanwords in later Coptic
- Modern Coptic liturgy often has Arabic translation

## Notes

### Why Normalize Case?
Coptic manuscripts typically use uppercase for:
- **Proper names** (especially nomina sacra)
- **Sentence beginnings**
- **Emphasis**

Normalizing to lowercase creates consistent dictionary matching, as most lexica use lowercase headwords.

### Why Remove Diacritics?
Modern scholarly editions add diacritics for:
- **Stress marking** (acute/grave accents)
- **Vowel length** (macrons)
- **Syllable separation** (diaeresis)
- **Greek orthography** (breathing marks)

Ancient manuscripts don't have these marks. Removing them matches the original orthography and enables consistent lookups.

### Dialect Variations
The same word may be spelled differently in different dialects:
- Sahidic: ⲛⲟⲩⲧⲉ (noute, "god")
- Bohairic: ⲛⲟⲩϯ (nouti, "god")

Dictionary entries should account for dialectal variations in their lemma mappings.

### Unicode Encoding Issues
Coptic has been encoded in Unicode in two locations:
1. **Coptic block** (U+2C80-U+2CFF) - preferred
2. **Greek and Coptic block** (U+03E2-U+03EF) - legacy

Modern texts use the Coptic block. These rules handle both encodings where relevant.

## Implementation Notes

When using these rules in the Classics Viewer app:
1. Rules are loaded from the CSV file during dictionary import
2. Greek and Latin patterns are automatically filtered out
3. Normalization happens at **lookup time**, not import time
4. Patterns are cached for performance
5. Text undergoes NFD normalization before pattern application
6. Both uppercase and lowercase Coptic letters are normalized to lowercase

## References

- Unicode Standard for Coptic: U+2C80 to U+2CFF
- Coptic Grammar (Bentley Layton)
- Crum's Coptic Dictionary (W.E. Crum, 1939)
- Coptic Encyclopedia
- SCRIPTORIUM project (Coptic NLP)
- Coptic SCRIPTORIUM corpora
- Marcion (online Coptic-English dictionary)

## Modern Usage

Coptic remains in use today:
- **Liturgical language** of the Coptic Orthodox Church
- **Academic study** of early Christianity, Gnosticism, Egyptian history
- **Cultural heritage** of Egyptian Christians
- **Revival efforts** for spoken Coptic

These normalization rules serve both:
- **Academic research** (ancient texts, manuscripts)
- **Liturgical use** (prayer books, hymnals)
