# Hindi Normalization Rules

## Overview

These normalization rules handle Hindi text written in Devanagari script, removing diacritical marks, vowel signs, and phonetic annotations to enable consistent dictionary lookups. Hindi is the most widely spoken language in India and uses the same Devanagari script as Sanskrit, with some modifications for modern sounds.

## Background

**Hindi** (हिन्दी) is an Indo-Aryan language:
- **Native speakers**: ~600 million (including L2 speakers)
- **Official status**: Official language of India, official in several states
- **Script**: Devanagari (shared with Sanskrit, Marathi, Nepali)
- **History**: Derived from Khariboli dialect of Delhi region
- **Literary traditions**: Medieval bhakti poetry, modern novels, poetry, journalism

### Relationship to Other Languages

#### Same Script (Devanagari)
- **Sanskrit**: Classical language, uses same base script
- **Marathi**: Uses Devanagari with some modifications
- **Nepali**: Official language of Nepal, uses Devanagari
- **Konkani**: Can be written in Devanagari

#### Linguistically Related
- **Urdu**: Same spoken language, different script (Perso-Arabic)
- **Hindustani**: Umbrella term for Hindi-Urdu continuum
- **Punjabi**: Related Indo-Aryan language
- **Bengali**: Related, different script

## Normalization Rules

### Nasalization and Aspiration Marks (Priorities 1-4)

#### 1. Devanagari Signs (Priority 1)
- **Pattern**: `[\u0900-\u0903]`
- **Replacement**: (empty)
- **Purpose**: Remove inverted candrabindu, candrabindu, anusvara, visarga
- **Unicode Range**: U+0900 to U+0903
- **Usage**: Comprehensive removal of Sanskrit-derived diacritics

#### 2. Anusvara (Priority 2)
- **Pattern**: `ं` (U+0902)
- **Replacement**: (empty)
- **Purpose**: Remove anusvara (nasalization marker)
- **Example**: `हिंदी` → `हिदी` (Hindi)
- **Phonetic**: Represents nasal sound /m/ or /n/ before consonants
- **Note**: Very common in Hindi, marks nasalization

#### 3. Visarga (Priority 3)
- **Pattern**: `ः` (U+0903)
- **Replacement**: (empty)
- **Purpose**: Remove visarga (aspiration marker)
- **Example**: `नमः` → `नम` (namah → nama)
- **Phonetic**: Represents /h/ sound, mostly in Sanskrit loanwords
- **Usage**: Less common in modern Hindi than Sanskrit

#### 4. Candrabindu (Priority 4)
- **Pattern**: `ँ` (U+0901)
- **Replacement**: (empty)
- **Purpose**: Remove candrabindu (nasalization marker)
- **Example**: `हँसना` → `हसना` (hansna, "to laugh")
- **Phonetic**: Indicates nasalized vowels
- **Note**: Alternative to anusvara in some contexts

### Nukta and Modification Marks (Priorities 5-6)

#### 5. Nukta (Priority 5)
- **Pattern**: `़` (U+093C)
- **Replacement**: (empty)
- **Purpose**: Remove nukta (dot below for Perso-Arabic sounds)
- **Example**: `ज़रूर` → `जरूर` (zaroor, "necessary")
- **Phonetic**: Modifies consonants for sounds borrowed from Urdu/Persian/Arabic
- **Note**: Creates sounds like /z/, /f/, /q/ not native to Sanskrit

#### 6. Virama/Halant (Priority 6)
- **Pattern**: `्` (U+094D)
- **Replacement**: (empty)
- **Purpose**: Remove virama/halant (vowel killer)
- **Example**: `क्त` → `कत` (removes consonant cluster marker)
- **Phonetic**: Indicates consonant without following vowel
- **Usage**: Creates consonant clusters (conjuncts)

### Vowel Signs and Diacritics (Priorities 7-11)

#### 7. Vowel Signs and Nukta (Priority 7)
- **Pattern**: `[\u093A-\u093C]`
- **Replacement**: (empty)
- **Purpose**: Remove dependent vowel signs and nukta
- **Unicode Range**: U+093A to U+093C

#### 8. Dependent Vowel Signs (Priority 8)
- **Pattern**: `[\u0941-\u0948]`
- **Replacement**: (empty)
- **Purpose**: Remove dependent vowel signs (matras)
- **Unicode Range**: U+0941 to U+0948
- **Includes**: ु ू ृ ॄ ॅ ॆ े ै
- **Example**: `किताब` → `कतब` (kitaab, "book")

#### 9. Virama (Priority 9)
- **Pattern**: `[\u094D]`
- **Replacement**: (empty)
- **Purpose**: Remove virama (redundant with priority 6)
- **Unicode**: U+094D

#### 10. Vedic Tone Marks (Priority 10)
- **Pattern**: `[\u0951-\u0954]`
- **Replacement**: (empty)
- **Purpose**: Remove Vedic tone marks (udatta, anudatta, svarita)
- **Unicode Range**: U+0951 to U+0954
- **Usage**: Rare in Hindi, mainly in Sanskrit portions

#### 11. Vocalic L Signs (Priority 11)
- **Pattern**: `[\u0962-\u0963]`
- **Replacement**: (empty)
- **Purpose**: Remove vocalic L dependent vowel signs
- **Unicode Range**: U+0962 to U+0963
- **Usage**: Rare, mainly Sanskrit loanwords

### Nukta-Modified Consonants (Priorities 12-19)

Hindi uses nukta to create sounds borrowed from Persian/Arabic/Urdu:

#### 12. Qa (Priority 12)
- **Pattern**: `क़` → `क`
- **Purpose**: Normalize qa (uvular stop) to ka
- **Example**: `क़िला` → `किला` (qila → kila, "fort")
- **Phonetic**: /q/ → /k/

#### 13. Kha (Priority 13)
- **Pattern**: `ख़` → `ख`
- **Purpose**: Normalize voiced fricative kha to aspirated kha
- **Example**: `ख़त` → `खत` (khat, "letter")
- **Phonetic**: /x/ → /kʰ/

#### 14. Gha (Priority 14)
- **Pattern**: `ग़` → `ग`
- **Purpose**: Normalize voiced fricative gha to ga
- **Example**: `ग़रीब` → `गरीब` (gharib, "poor")
- **Phonetic**: /ɣ/ → /g/

#### 15. Za (Priority 15)
- **Pattern**: `ज़` → `ज`
- **Purpose**: Normalize za to ja
- **Example**: `ज़रूर` → `जरूर` (zaroor, "necessary")
- **Phonetic**: /z/ → /dʒ/
- **Note**: Very common in Hindi

#### 16. Ra (Priority 16)
- **Pattern**: `ड़` → `ड`
- **Purpose**: Normalize retroflex flap to retroflex stop
- **Example**: `पड़ना` → `पडना` (parna, "to fall")
- **Phonetic**: /ɽ/ → /ɖ/
- **Note**: This is actually a native Hindi sound, not borrowed

#### 17. Rha (Priority 17)
- **Pattern**: `ढ़` → `ढ`
- **Purpose**: Normalize aspirated retroflex flap
- **Example**: `ढ़ाई` → `ढाई` (dhai, "two and a half")
- **Phonetic**: /ɽʱ/ → /ɖʱ/

#### 18. Fa (Priority 18)
- **Pattern**: `फ़` → `फ`
- **Purpose**: Normalize fa to pha
- **Example**: `फ़िल्म` → `फिल्म` (film)
- **Phonetic**: /f/ → /pʰ/

#### 19. Ya with Nukta (Priority 19)
- **Pattern**: `य़` → `य`
- **Purpose**: Normalize ya with nukta to ya
- **Example**: Rare usage
- **Phonetic**: Variant pronunciation

### Vowel Variants (Priorities 20-25)

#### 20. Short O (Priority 20)
- **Pattern**: `ऑ` → `ओ`
- **Purpose**: Normalize short o (candra o) to o
- **Example**: `ऑफिस` → `ओफिस` (office)
- **Phonetic**: /ɔ/ → /o/
- **Usage**: Used for English loanwords

#### 21. Short O Variant (Priority 21)
- **Pattern**: `ऒ` → `ओ`
- **Purpose**: Normalize short o variant to o
- **Unicode**: U+0912 → U+0913

#### 22. Candra O Matra (Priority 22)
- **Pattern**: `ॉ` → `ो`
- **Purpose**: Normalize candra o matra to o matra
- **Example**: In dependent vowel form
- **Unicode**: U+0949 → U+094B

#### 23. Short O Matra (Priority 23)
- **Pattern**: `ॊ` → `ो`
- **Purpose**: Normalize short o matra to o matra
- **Unicode**: U+094A → U+094B

#### 24. Vocalic L Sign (Priority 24)
- **Pattern**: `ॢ` (U+0962)
- **Replacement**: (empty)
- **Purpose**: Remove vocalic l dependent vowel sign
- **Usage**: Sanskrit only, extremely rare in Hindi

#### 25. Vocalic LL Sign (Priority 25)
- **Pattern**: `ॣ` (U+0963)
- **Replacement**: (empty)
- **Purpose**: Remove vocalic ll dependent vowel sign
- **Usage**: Sanskrit only, not used in Hindi

### Special Characters (Priorities 26-30)

#### 26. Zero-Width Characters (Priority 26)
- **Pattern**: `[\u200C\u200D]`
- **Replacement**: (empty)
- **Purpose**: Remove zero-width non-joiner (ZWNJ) and zero-width joiner (ZWJ)
- **Unicode**: U+200C, U+200D
- **Usage**: Control conjunct formation, invisible formatting

#### 27. Devanagari Danda (Priority 27)
- **Pattern**: `।` (U+0964)
- **Replacement**: (empty)
- **Purpose**: Remove devanagari danda (phrase/sentence separator)
- **Usage**: Hindi punctuation mark (like comma/period)

#### 28. Double Danda (Priority 28)
- **Pattern**: `॥` (U+0965)
- **Replacement**: (empty)
- **Purpose**: Remove devanagari double danda (verse separator)
- **Usage**: Marks end of verse/paragraph

#### 29. Abbreviation Sign (Priority 29)
- **Pattern**: `॰` (U+0970)
- **Replacement**: (empty)
- **Purpose**: Remove devanagari abbreviation sign
- **Usage**: Marks abbreviated text

#### 30. Avagraha (Priority 30)
- **Pattern**: `ॱ` (U+0971)
- **Replacement**: (empty)
- **Purpose**: Remove avagraha (elision marker)
- **Usage**: Indicates missing vowel in sandhi

## Usage in Dictionary Files

Include this file as `normalization_rules.csv` in your Hindi dictionary ZIP file:

```
my-hindi-dictionary.zip
├── dictionary.csv          (Hindi entries)
├── morphology.csv          (Optional: lemma mappings)
└── normalization_rules.csv (This file, renamed)
```

Or use the language-specific filename:
```
└── normalization_rules_hindi.csv
```

## Example Transformations

### Common Hindi Phrases
**Input (with diacritics):**
```
हिंदी भाषा बहुत सुंदर है।
```

**After normalization:**
```
हिदी भाषा बहत सदर है
```
(Hindi language is very beautiful)

### Hindi Literature (Premchand)
**Input:**
```
गोदान उनकी सबसे प्रसिद्ध रचना है।
```

**After normalization:**
```
गोदान उनकी सबसे परसिद रचना है
```
(Godaan is his most famous work)

### Modern Hindi with English Loanwords
**Input:**
```
मैं कॉलेज में फ़िल्म देखने जा रहा हूँ।
```

**After normalization:**
```
मै कोलेज मे फिलम देखने जा रहा हू
```
(I am going to watch a film in college)

### Hindi Poetry (Kabir)
**Input:**
```
माला फेरत जुग गया, मिटा न मन का फेर।
```

**After normalization:**
```
माला फेरत जग गया मिटा न मन का फेर
```
(You turned the rosary for ages, but the mind's delusion didn't end)

### Urdu-influenced Hindi
**Input:**
```
ज़िन्दगी एक सफ़र है ख़ूबसूरत।
```

**After normalization:**
```
जिनदगी एक सफर है खूबसूरत
```
(Life is a beautiful journey)

## Technical Details

### Script Characteristics
- **Direction**: Left-to-right
- **Unicode Range**: U+0900 to U+097F (Devanagari)
- **Alphabet**: 11 vowels (स्वर), 33 consonants (व्यंजन)
- **Syllabic**: Each consonant has inherent /a/ vowel

### Devanagari Alphabet

#### Independent Vowels (स्वर)
अ आ इ ई उ ऊ ऋ ए ऐ ओ औ

**With nukta/variants:**
ऑ (short o, for English loanwords)

#### Dependent Vowel Signs (मात्राएँ)
(none) ा ि ी ु ू ृ े ै ो ौ

#### Consonants (व्यंजन)

**Stops:**
- क ख ग घ ङ (velar)
- च छ ज झ ञ (palatal)
- ट ठ ड ढ ण (retroflex)
- त थ द ध न (dental)
- प फ ब भ म (labial)

**Approximants/Fricatives:**
- य र ल व (semivowels)
- श ष स ह (sibilants)

**With nukta (Perso-Arabic sounds):**
- क़ (qa), ख़ (kha), ग़ (gha)
- ज़ (za), फ़ (fa)
- ड़ (flap ra), ढ़ (aspirated flap)

### Conjuncts (संयुक्ताक्षर)

Hindi uses virama (्) to form consonant clusters:
- क् + त = क्त (kta)
- स् + व = स्व (swa)
- द् + ध = द्ध (ddha)

Normalization removes virama, simplifying clusters.

### Hindi vs. Sanskrit

While both use Devanagari:
- **Hindi**: Modern spoken language, Urdu loanwords, simplified grammar
- **Sanskrit**: Classical language, more complex phonology and grammar

Hindi normalization is simpler than Sanskrit because:
- Fewer Vedic marks
- More nukta usage (borrowed sounds)
- Modern orthographic conventions

### Unicode NFD Normalization
All patterns are applied **after** Unicode NFD (Canonical Decomposition) normalization.

### Pattern Order
Patterns are applied in priority order (1-30). Lower numbers are applied first.

## Common Use Cases

### Literary Texts
- **Modern Hindi novels** (Premchand, Nirmal Verma, etc.)
- **Poetry** (Kabir, Tulsidas, Mahadevi Verma)
- **Short stories**
- **Essays and criticism**

### Religious Texts
- **Ramcharitmanas** (Tulsidas, Awadhi in Devanagari)
- **Hindu devotional literature**
- **Translations of Sanskrit texts**
- **Sikh scriptures** (when written in Devanagari)

### Modern Media
- **Newspapers** (Dainik Jagran, Amar Ujala, etc.)
- **Magazines**
- **Websites and blogs**
- **Social media** (increasing Devanagari usage)

### Educational Materials
- **Textbooks**
- **Grammar books**
- **Dictionaries** (Hindi-Hindi, Hindi-English)
- **Language learning materials**

### Cinema and Entertainment
- **Bollywood film scripts**
- **Song lyrics**
- **Subtitles**
- **TV show scripts**

## Dialectal and Register Variations

### Registers
- **Shuddh Hindi** (Pure Hindi): Sanskritized vocabulary, formal
- **Hindustani**: Hindi-Urdu mix, colloquial
- **Urdu-influenced Hindi**: More Perso-Arabic loanwords

### Major Dialects
- **Khariboli**: Standard Hindi, Delhi region
- **Braj**: Literary dialect, Krishna bhakti poetry
- **Awadhi**: Eastern UP, Ramcharitmanas
- **Bhojpuri**: Eastern UP/Bihar (sometimes written in Devanagari)
- **Rajasthani**: Western dialects

These rules work for all varieties written in Devanagari.

## Relationship to Urdu

Hindi and Urdu are essentially the **same spoken language** (Hindustani) with different:
- **Scripts**: Devanagari (Hindi) vs. Perso-Arabic (Urdu)
- **Vocabulary**: Sanskrit-derived (Hindi) vs. Persian/Arabic-derived (Urdu)
- **Orthography**: Different writing conventions

These Hindi rules handle:
- ✅ Pure Hindi (Sanskritized)
- ✅ Hindustani (mixed)
- ✅ Urdu words written in Devanagari (using nukta)

For Urdu in Arabic script, use Arabic normalization rules.

## Notes

### Why Remove Nukta?
Nukta creates sounds borrowed from Urdu/Persian/Arabic:
- क़ /q/, ख़ /x/, ग़ /ɣ/, ज़ /z/, फ़ /f/

Many Hindi speakers don't distinguish these from:
- क /k/, ख /kʰ/, ग /g/, ज /dʒ/, फ /pʰ/

Removing nukta creates more flexible matching for:
- Regional pronunciation variations
- Spelling variations (with/without nukta)
- Historical texts (pre-nukta orthography)

### Why Remove Vowel Signs?
Dependent vowel signs (matras) create the full syllable:
- क + ा = का (ka + aa = kaa)
- क + ि = कि (ka + i = ki)

Removing them leaves base consonants for root matching.

### Schwa Deletion
Hindi has a phenomenon called "schwa deletion" where inherent /a/ vowels are often not pronounced:
- कमल (kamal) pronounced as "kaml" (lotus)
- सदन (sadan) pronounced as "sadn" (house)

Normalization doesn't handle this phonological process, only orthographic normalization.

## Implementation Notes

When using these rules in the Classics Viewer app:
1. Rules are loaded from the CSV file during dictionary import
2. Greek and Latin patterns are automatically filtered out
3. Normalization happens at **lookup time**, not import time
4. Patterns are cached for performance
5. Text undergoes NFD normalization before pattern application
6. Works for all Hindi registers (Shuddh, Hindustani, Urdu-influenced)

## References

- Unicode Standard for Devanagari: U+0900 to U+097F
- McGregor's Hindi Grammar (R.S. McGregor)
- Oxford Hindi-English Dictionary
- Platt's Dictionary of Urdu, Classical Hindi and English
- CFILT (IIT Bombay) Hindi resources
- Hindi WordNet
- Central Hindi Directorate publications

## Modern Usage

Hindi is one of the world's most widely spoken languages:
- **Official language** of India (with English)
- **Native speakers**: ~350 million
- **Total speakers**: ~600 million (including L2)
- **Geographic spread**: India, Nepal, Fiji, Mauritius, diaspora worldwide

These normalization rules serve:
- **Academic research** (linguistics, literature, history)
- **Digital humanities** (corpus analysis, text mining)
- **Language learning** (dictionary apps, translation tools)
- **Media and publishing** (digital texts, e-books)
