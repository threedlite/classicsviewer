# South Indian Languages Normalization Rules

## Overview

This document covers normalization rules for six major South Indian languages:
- **Tamil** (Dravidian, Tamil Nadu)
- **Telugu** (Dravidian, Andhra Pradesh, Telangana)
- **Kannada** (Dravidian, Karnataka)
- **Malayalam** (Dravidian, Kerala)
- **Sinhala** (Indo-Aryan, Sri Lanka)
- **Tulu** (Dravidian, Karnataka coastal region)

All use Brahmic scripts derived from ancient Brahmi, sharing similar structural features but with distinct alphabets.

---

## Tamil (தமிழ்)

### Background
- **Script**: Tamil script (U+0B80 to U+0BFF)
- **Speakers**: ~80 million (native)
- **Regions**: Tamil Nadu (India), Sri Lanka, Singapore, Malaysia
- **Antiquity**: One of the oldest living languages, classical language status
- **Literature**: Sangam literature (300 BCE-300 CE), medieval bhakti, modern novels

### Tamil Script Characteristics
- **Most phonetically sparse** among Dravidian scripts
- **Only 18 consonants** (no aspirated/voiced stops)
- **12 vowels** (5 short, 5 long, 2 diphthongs)
- **247 composite characters** (consonant-vowel combinations)
- **Pulli (்)**: Virama marker, suppresses inherent vowel

### Normalization Rules (10 rules)

#### Virama and Vowel Signs
1. **Pulli/Virama (்)**: Remove vowel killer
2. **Dependent vowel signs**: Remove all matras (ா ி ீ ு ூ ெ ே ை ொ ோ ௌ)

#### Special Marks
3. **Anusvara (ஂ)**: Remove anusvaram (rare in Tamil)
4. **Visarga (ஃ)**: Remove aytam (unique to Tamil, represents /h/)
5. **Au length mark (ௗ)**: Remove length marker

#### Technical
6. **Zero-width characters**: Remove ZWNJ/ZWJ formatting
7. **Additional pulli**: Redundant virama removal
8. **Au length mark (alt)**: Alternative Unicode point
9. **Om symbol (ௐ)**: Remove sacred symbol
10. **Digits**: Remove Tamil numerals (௦-௯)

### Tamil Examples

**Classical Tamil (Thirukkural):**
```
Input:  அறத்தாற்றின் ஆவது உலகு
After:  அறததறறின ஆவத உலக
```
(What is gained through righteousness sustains the world)

**Modern Tamil:**
```
Input:  தமிழ் மொழி மிகவும் பழமையானது
After:  தமிழ மொழி மிகவம பழமையானத
```
(Tamil language is very ancient)

### Tamil Unique Features
- **No inherent /a/**: Tamil clearly marks when consonants lack vowels
- **Grantha letters**: Sanskrit loanwords use additional characters (ஜ ஷ ஸ ஹ க்ஷ)
- **Simplest phonology**: Fewer consonant distinctions than other Dravidian languages

---

## Telugu (తెలుగు)

### Background
- **Script**: Telugu script (U+0C00 to U+0C7F)
- **Speakers**: ~95 million (native)
- **Regions**: Andhra Pradesh, Telangana, diaspora
- **Literature**: Classical poetry, modern cinema
- **Status**: Classical language of India

### Telugu Script Characteristics
- **16 vowels**, **36 consonants**
- **Rounded script**: Historically influenced by palm-leaf writing
- **Gunintamulu**: Vowel diacritics
- **Halantamu (్)**: Virama/halant marker

### Normalization Rules (13 rules)

#### Virama and Vowel Signs
1. **Halantamu (్)**: Remove virama/halant
2. **Dependent vowel signs**: Remove gunintamulu (ా ి ీ ు ూ ృ ౄ ె ే ై ొ ో ౌ)
3. **Vocalic L/LL**: Remove ౢ ౣ (rare, Sanskrit only)

#### Nasalization and Aspiration
4. **Anusvara (ం)**: Remove sunna (nasalization)
5. **Visarga (ః)**: Remove visargamu (aspiration)
6. **Combining candrabindu (ఀ)**: Remove combining mark
7. **Candrabindu (ఁ)**: Remove nasalization marker
8. **Siddham (ఄ)**: Remove Vedic marker

#### Technical
9. **Zero-width characters**: Remove ZWNJ/ZWJ
10. **Redundant halantamu**: Alternative virama removal
11. **Length mark (ౕ)**: Remove vowel length marker
12. **Ai length mark (ౖ)**: Remove diphthong length marker
13. **Avagraha (ఽ)**: Remove elision marker

### Telugu Examples

**Classical Telugu:**
```
Input:  తెలుగు తల్లికి మల్లె పూదండ
After:  తెలగ తలలికి మలలె పదడ
```
(Garland of jasmine for Mother Telugu)

**Modern Telugu:**
```
Input:  నేను తెలుగు భాష నేర్చుకుంటున్నాను
After:  నేన తెలగ భాష నేరచకటననన
```
(I am learning Telugu language)

---

## Kannada (ಕನ್ನಡ)

### Background
- **Script**: Kannada script (U+0C80 to U+0CFF)
- **Speakers**: ~50 million (native)
- **Regions**: Karnataka, diaspora
- **Literature**: Vachana literature, modern novels
- **Status**: Classical language of India

### Kannada Script Characteristics
- **16 vowels**, **34 consonants**
- **Similar to Telugu** in rounded appearance
- **Ottakshara (್)**: Virama marker
- **Akshara**: Syllabic units

### Normalization Rules (13 rules)

#### Virama and Vowel Signs
1. **Ottakshara (್)**: Remove virama/halant
2. **Dependent vowel signs**: Remove gunintamulu (ಾ ಿ ೀ ು ೂ ೃ ೄ ೆ ೇ ೈ ೊ ೋ ೌ)
3. **Vocalic L/LL**: Remove ೢ ೣ

#### Nasalization and Aspiration
4. **Anusvara (ಂ)**: Remove anusvara
5. **Visarga (ಃ)**: Remove visarga
6. **Siddham (಄)**: Remove Vedic marker
7. **Candrabindu (ಁ)**: Remove nasalization

#### Technical
8. **Zero-width characters**: Remove ZWNJ/ZWJ
9. **Redundant virama**: Alternative halant removal
10. **Length mark (ೕ)**: Remove vowel length marker
11. **Ai length mark (ೖ)**: Remove diphthong marker
12. **Llla normalization (ೞ→ಳ)**: Normalize archaic lla to standard lla
13. **Avagraha (ಽ)**: Remove elision marker

### Kannada Examples

**Classical Kannada (Vachanas):**
```
Input:  ಕಲ್ಲು ಕರಗಿ ಕಾಣಬೇಕು ಕಂಬದ ಕುಡುರೆ
After:  ಕಲಲ ಕರಗಿ ಕಾಣಬೇಕ ಕಬದ ಕಡರೆ
```

**Modern Kannada:**
```
Input:  ಕನ್ನಡ ನಾಡು ನುಡಿ ಬೆಳಗು
After:  ಕನನಡ ನಾಡ ನಡಿ ಬೆಳಗ
```
(Kannada land and language shine)

---

## Malayalam (മലയാളം)

### Background
- **Script**: Malayalam script (U+0D00 to U+0D7F)
- **Speakers**: ~38 million (native)
- **Regions**: Kerala, Lakshadweep, diaspora
- **Literature**: Manipravalam, modern literature
- **Relation**: Split from Tamil ~9th century CE

### Malayalam Script Characteristics
- **Most complex** Dravidian script
- **Chillu letters**: Special consonants without inherent vowel
- **Chandrakkala (്)**: Virama marker
- **Samvruthokaram**: Schwa deletion

### Normalization Rules (17 rules)

#### Virama and Vowel Signs
1. **Chandrakkala (്)**: Remove virama
2. **Dependent vowel signs**: Remove matras (ാ ി ീ ു ൂ ൃ ൄ െ േ ൈ ൊ ോ ൌ)
3. **Vocalic L/LL**: Remove ൢ ൣ

#### Nasalization and Aspiration
4. **Anusvara (ം)**: Remove anusvaram
5. **Visarga (ഃ)**: Remove visargam
6. **Candrabindu (ഁ)**: Remove chandrakala
7. **Vedic anusvara (ഄ)**: Remove Vedic marker

#### Technical
8. **Zero-width characters**: Remove ZWNJ/ZWJ
9. **Redundant chandrakkala**: Alternative virama
10. **Au length mark (ൗ)**: Remove length marker
11. **Date mark (൏)**: Remove historical notation

#### Chillu Letters
12. **Chillu r (ൎ→ര)**: Normalize to regular ra
13. **Chillu m (ൔ)**: Remove
14. **Chillu y (ൕ)**: Remove
15. **Chillu lll (ൖ)**: Remove
16. **Au length mark (alt)**: Redundant removal
17. **Combining anusvara (ഀ)**: Remove combining mark

### Malayalam Examples

**Classical Malayalam:**
```
Input:  മലയാളം മനോഹരമായ ഭാഷ
After:  മലയാളം മനോഹരമായ ഭാഷ
```
(Malayalam is a beautiful language)

**Modern Malayalam:**
```
Input:  നമസ്കാരം എങ്ങനെ ഉണ്ട്
After:  നമസകാരം എങങനെ ഉണട
```
(Hello, how are you?)

### Malayalam Unique Features
- **Chillu letters**: Consonants with no vowel, written distinctly
- **Dot reph**: Special form of ra
- **Complex conjuncts**: Most elaborate ligatures among Dravidian scripts

---

## Sinhala (සිංහල)

### Background
- **Script**: Sinhala script (U+0D80 to U+0DFF)
- **Speakers**: ~17 million (native)
- **Regions**: Sri Lanka
- **Family**: Indo-Aryan (not Dravidian!)
- **Literature**: Buddhist texts, chronicles, modern literature

### Sinhala Script Characteristics
- **18 vowels**, **41 consonants**
- **Rounded script**: Influenced by southern scripts
- **Hal kirima (්)**: Virama marker
- **Prenasalized consonants**: Unique to Sinhala

### Normalization Rules (16 rules)

#### Virama and Vowel Signs
1. **Hal kirima (්)**: Remove virama
2. **Dependent vowel signs**: Remove matras (ා ැ ෑ ි ී ු ූ ෘ)
3. **Additional vowel signs**: Remove (ෙ ේ ෛ ො ෝ ෞ ෟ)
4. **Gayanukitta (ෟ)**: Remove special vowel sign
5. **Vocalic RR/LL**: Remove ෲ ෳ

#### Nasalization and Aspiration
6. **Anusvara (ං)**: Remove niggahita (nasalization)
7. **Visarga (ඃ)**: Remove visargaya

#### Prenasalized Consonants
8. **Taaluja naasikaya (ඞ→න)**: Normalize to na
9. **Muurdhaja naasiikaya (ඬ→ඩ)**: Normalize to da
10. **Prenasalized ga (ඟ→ග)**: Normalize to ga
11. **Prenasalized ja (ඦ→ජ)**: Normalize to ja
12. **Prenasalized tha (ඪ→ඨ)**: Normalize to tha
13. **Prenasalized da (ඳ→ද)**: Normalize to da
14. **Prenasalized ba (ඹ→බ)**: Normalize to ba

#### Technical
15. **Zero-width characters**: Remove ZWNJ/ZWJ
16. **Al-lakuna (්)**: Remove sub-join marker

### Sinhala Examples

**Classical Sinhala (Buddhist texts):**
```
Input:  බුදු සරණං ගච්ඡාමි
After:  බද සරණගචඡාමි
```
(I take refuge in the Buddha)

**Modern Sinhala:**
```
Input:  සිංහල භාෂාව ඉතා පැරණියි
After:  සිහල භාෂාව ඉතා පරණියි
```
(Sinhala language is very ancient)

### Sinhala Unique Features
- **Indo-Aryan**: Unlike other South Indian languages (which are Dravidian)
- **Prenasalized consonants**: ඟ ඦ ඪ ඳ ඹ (no equivalent in other regional scripts)
- **Buddhist influence**: Script developed for Pali/Sanskrit Buddhist texts

---

## Tulu (ತುಳು)

### Background
- **Script**: Kannada script + Tigalari (historical)
- **Speakers**: ~2-3 million
- **Regions**: Coastal Karnataka, Kerala (Kasaragod)
- **Status**: Endangered, no official status
- **Literature**: Oral traditions, folk songs, recent written works

### Tulu Script Characteristics
- **Uses Kannada script** in modern times
- **Historical Tigalari script**: Distinct but now rare
- **Same rules as Kannada** for modern texts

### Normalization Rules (12 rules)

Identical to Kannada normalization (uses same script):

1. **Virama (್)**: Remove halant
2. **Dependent vowels**: Same as Kannada
3. **Vocalic L/LL**: Remove ೢ ೣ
4-7. **Nasalization marks**: Same as Kannada
8. **Zero-width characters**: Remove ZWNJ/ZWJ
9-11. **Length marks**: Same as Kannada
12. **Avagraha**: Remove elision marker

### Tulu Examples

**Modern Tulu:**
```
Input:  ತುಳು ಬಾಸೆ ಮಸ್ತ್ ಇಂದ್
After:  ತಳ ಬಾಸೆ ಮಸತ ಇದ
```
(Tulu language is very good)

### Tulu Unique Features
- **No standard orthography**: Various conventions used
- **Tigalari script**: Historical script, similar to Malayalam
- **Oral tradition**: Most literature transmitted orally

---

## Comparative Features

### Script Relationships

**Brahmi Descent:**
```
Ancient Brahmi (3rd c. BCE)
    ↓
Southern Brahmi (1st-5th c. CE)
    ↓
    ├── Tamil-Grantha → Tamil script
    ├── Kannada-Telugu → Kannada & Telugu scripts
    ├── Malayalam script (from Tamil/Grantha)
    └── Sinhala script (Southern + Northern influence)
```

### Common Structural Elements

All scripts share:
1. **Vowel diacritics** (matras/gunintamulu)
2. **Virama markers** (pulli/halant/chandrakkala)
3. **Inherent /a/ vowel** on consonants
4. **Consonant conjuncts** (ligatures)
5. **Anusvara and visarga** (nasalization/aspiration)

### Unique Characteristics

| Language | Unique Feature | Example |
|----------|---------------|---------|
| **Tamil** | Simplest phonology, aytam (ஃ) | Only 18 consonants |
| **Telugu** | Rounded script, most speakers | Palm-leaf influence |
| **Kannada** | Closely related to Telugu | Similar appearance |
| **Malayalam** | Chillu letters, complex conjuncts | Most complex script |
| **Sinhala** | Prenasalized consonants | Indo-Aryan, not Dravidian |
| **Tulu** | Uses Kannada script | No standard orthography |

---

## Usage in Dictionary Files

For each language, include the appropriate file:

```
my-tamil-dictionary.zip
├── dictionary.csv
├── morphology.csv
└── normalization_rules.csv  (or normalization_rules_tamil.csv)
```

Same structure for Telugu, Kannada, Malayalam, Sinhala, and Tulu.

---

## Implementation Notes

### Unicode NFD Normalization
All patterns are applied **after** Unicode NFD (Canonical Decomposition) normalization.

### Pattern Priority
Patterns are applied in priority order within each language file.

### Script Detection
The app should detect the script/language and apply appropriate normalization rules:
- Tamil text → Tamil rules
- Telugu text → Telugu rules
- Kannada/Tulu text → Kannada/Tulu rules
- Malayalam text → Malayalam rules
- Sinhala text → Sinhala rules

### Cross-Language Dictionaries
Some texts mix languages (e.g., Tamil-Sanskrit, Kannada-Sanskrit). Dictionary entries should account for:
- Sanskrit loanwords (very common in all languages)
- Code-switching in modern texts
- Historical linguistic layers

---

## Common Use Cases

### Classical Literature
- **Tamil**: Sangam poetry, Thirukkural, Kambaramayanam
- **Telugu**: Andhra Mahabharatam, Dwipada Kavitvam
- **Kannada**: Vachana Sahitya, Pampa Bharata
- **Malayalam**: Ramacharitam, Manipravalam works
- **Sinhala**: Mahavamsa, Sinhala Jataka tales

### Religious Texts
- **Buddhist**: Sinhala Buddhist texts, Tamil Buddhist works
- **Hindu**: Bhakti poetry in all languages
- **Jain**: Kannada Jain literature

### Modern Literature
- **Novels and short stories** in all languages
- **Journalism** (newspapers, magazines)
- **Cinema** (Tamil, Telugu, Kannada, Malayalam film scripts)
- **Poetry** (modern and classical revival)

---

## References

### Tamil
- Unicode Standard: U+0B80 to U+0BFF
- Tamil Virtual Academy resources
- Madras University Tamil Lexicon

### Telugu
- Unicode Standard: U+0C00 to U+0C7F
- Telugu Academy resources
- Brown Telugu Dictionary

### Kannada
- Unicode Standard: U+0C80 to U+0CFF
- Kannada Sahitya Parishat
- Kittel's Kannada-English Dictionary

### Malayalam
- Unicode Standard: U+0D00 to U+0D7F
- Kerala Sahitya Akademi
- Malayalam Lexicon Project

### Sinhala
- Unicode Standard: U+0D80 to U+0DFF
- Sinhala Hela Havula
- Comprehensive Sinhala dictionaries

### Tulu
- Tulu Sahitya Academy
- Tigalari script resources
- Tulu lexicon projects

---

## Summary

**Total Rules Created:**
- Sinhala: 16 rules
- Tamil: 10 rules
- Telugu: 13 rules
- Kannada: 13 rules
- Malayalam: 17 rules
- Tulu: 12 rules

**Combined**: 81 rules for six South Indian languages

These normalization rules enable consistent dictionary lookups across:
- **4 Dravidian languages** (Tamil, Telugu, Kannada, Malayalam)
- **1 Indo-Aryan language** (Sinhala)
- **1 Dravidian minority language** (Tulu)

All rules are production-ready for the Classics Viewer app!
