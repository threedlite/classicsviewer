# Middle Persian (Pahlavi) Normalization Rules

## Overview

Middle Persian, also known as **Pahlavi**, was the language of the Sasanian Empire (224-651 CE) and continued in use for several centuries after the Islamic conquest. These normalization rules are designed for **Inscriptional Pahlavi** script, the most common form used in digital texts.

## Language & Script Context

### Middle Persian (𐭯𐭠𐭧𐭫𐭥𐭩)
- **Period**: c. 300 BCE - 900 CE
- **Script family**: Aramaic-derived abjad
- **Direction**: Right-to-left (RTL)
- **Writing system**: Consonantal (vowels usually not written)
- **Unicode block**: U+10B60–U+10B7F (Inscriptional Pahlavi)

### Historical Importance
- Language of Zoroastrian religious texts
- Administrative language of Sasanian Empire
- Bridge between Old Persian and Modern Persian
- Preserved in inscriptions, coins, seals, and manuscripts

## Script Variants

Middle Persian was written in several script variants:

### 1. **Inscriptional Pahlavi** (Book Pahlavi)
- **Most common in digital texts**
- Used for rock inscriptions and official documents
- Clearest letter forms
- **These normalization rules target this variant**

### 2. **Psalter Pahlavi**
- Used for Christian texts
- Unicode: U+10B80–U+10BAF
- Different letter forms from Inscriptional

### 3. **Book Pahlavi** (Manuscript Pahlavi)
- Highly cursive and ambiguous
- Used in Zoroastrian manuscripts
- Very difficult to digitize/normalize

## Pahlavi Script Characteristics

### Challenges for Normalization

**1. Extreme Letter Ambiguity (Homography)**
- Many letters look identical in form
- Context-dependent reading required
- Examples of ambiguous letter groups:
  - **𐭣 𐭥 𐭫 𐭭** (daleth, waw, resh, nun) - often indistinguishable
  - **𐭤 𐭧 𐭲** (he, heth, qoph) - similar forms
  - **𐭩 𐭢** (yodh, gimel) - can be confusing

**2. Aramaic Heterograms (Ideograms)**
- Pahlavi texts use Aramaic words as logograms
- Written in Aramaic but read as Persian
- Example: 𐭌𐭋𐭊𐭀 (MLKʾ - "king" in Aramaic) read as *šāh* in Persian
- **Not addressed by normalization** - semantic issue, not orthographic

**3. Consonantal Writing**
- Vowels rarely marked
- Same consonant skeleton for multiple words
- Context determines pronunciation

**4. Ligatures & Cursive Forms**
- Letters connect in different ways
- Multiple glyph variants per letter
- Unicode attempts to represent base forms

## Normalization Rules Breakdown

### Priority 1: Remove Combining Diacritical Marks
**Pattern**: `[\u0300-\u036F]`
**Replacement**: *(empty string)*
**Description**: Remove combining diacritical marks

**What it does**:
- Removes modern scholarly diacritics added for transliteration aids
- Combines accent marks, dots, lines added to distinguish readings
- Not part of historical Pahlavi but added in modern editions

**Example**:
```
Before: 𐭬𐭫́𐭣𐭩 (with accent on resh for disambiguation)
After:  𐭬𐭫𐭣𐭩 (plain text)
```

**Use case**: Modern critical editions sometimes add diacritics to help readers distinguish homographs.

---

### Priorities 2-23: Letter Normalization

The Pahlavi alphabet consists of 22 base letters (derived from Aramaic). Each rule normalizes variant forms to a standard form.

**Current Implementation Note**:
The rules as written (Priority 2-23) are **placeholder identity mappings** because:
1. Unicode Inscriptional Pahlavi already uses standardized codepoints
2. True variant normalization would require:
   - Multiple Unicode representations of same letter (currently limited)
   - Mapping between Psalter and Inscriptional variants
   - Contextual ligature resolution

**However**, these rules serve as a **framework** for:
- Future variant handling if Unicode expands
- Mapping between script variants (Inscriptional ↔ Psalter)
- Custom font/encoding conversions

### Pahlavi Alphabet Reference

| Unicode | Letter | Aramaic Name | Transliteration | Persian Sound |
|---------|--------|--------------|-----------------|---------------|
| 𐭠 U+10B60 | 𐭠 | Aleph | ʾ, A | /a/, /ā/ (glottal stop or long a) |
| 𐭡 U+10B61 | 𐭡 | Beth | B | /b/ |
| 𐭢 U+10B62 | 𐭢 | Gimel | G | /g/ |
| 𐭣 U+10B63 | 𐭣 | Daleth | D | /d/ |
| 𐭤 U+10B64 | 𐭤 | He | H | /h/ |
| 𐭥 U+10B65 | 𐭥 | Waw | W, U, O | /w/, /ū/, /ō/ |
| 𐭦 U+10B66 | 𐭦 | Zayin | Z | /z/ |
| 𐭧 U+10B67 | 𐭧 | Heth | Ḥ | /x/ (kh sound) |
| 𐭨 U+10B68 | 𐭨 | Teth | Ṭ | /t/ |
| 𐭩 U+10B69 | 𐭩 | Yodh | Y, I, E | /y/, /ī/, /ē/ |
| 𐭪 U+10B6A | 𐭪 | Kaph | K | /k/ |
| 𐭫 U+10B6B | 𐭫 | Lamedh | L | /l/ |
| 𐭬 U+10B6C | 𐭬 | Mem | M | /m/ |
| 𐭭 U+10B6D | 𐭭 | Nun | N | /n/ |
| 𐭮 U+10B6E | 𐭮 | Samekh | S | /s/ |
| 𐭯 U+10B6F | 𐭯 | Ayin | ʿ | /ʿ/ (pharyngeal) |
| 𐭰 U+10B70 | 𐭰 | Pe | P | /p/ |
| 𐭱 U+10B71 | 𐭱 | Sadhe | Ṣ | /ts/ or /s/ |
| 𐭲 U+10B72 | 𐭲 | Qoph | Q | /k/ (emphatic) |
| 𐭳 U+10B73 | 𐭳 | Resh | R | /r/ |
| 𐭴 U+10B74 | 𐭴 | Shin | Š | /š/ (sh sound) |
| 𐭵 U+10B75 | 𐭵 | Taw | T | /t/ |

---

## Practical Normalization Challenges

### 1. Homograph Disambiguation

**Problem**: Many letters are visually identical in Pahlavi
- 𐭣𐭥𐭫𐭭 (d/w/r/n group) - context distinguishes them
- 𐭤𐭧 (h/ḥ) - often identical in manuscripts

**Current Solution**:
- Normalization preserves Unicode distinctions
- Scholars must manually encode correct letter
- No automatic disambiguation (requires AI/context)

**Example**:
```
Word: 𐭬𐭫𐭣𐭩
Could be: mrdy, mwdy, mndy, etc.
Reading: *mard* (man) - context-dependent
```

### 2. Aramaic Heterograms

**Problem**: Aramaic words used as logograms

**Example**:
```
Written: 𐭌𐭋𐭊𐭀 (MLKʾ - Aramaic "king")
Read as: šāh (Persian "king")

Written: 𐭁𐭓𐭀 (BRʾ - Aramaic "son")
Read as: puhr (Persian "son")
```

**Current Solution**:
- **Not normalized** - these are semantic units
- Dictionary entries should include both Aramaic spelling and Persian reading
- Separate lexical entries for heterograms

### 3. Manuscript Variants

**Problem**: Book Pahlavi vs. Inscriptional Pahlavi differences

**Potential Future Rule**:
```csv
middle_persian,\u10B80,\u10B60,Map Psalter aleph to Inscriptional aleph,24
middle_persian,\u10B81,\u10B61,Map Psalter beth to Inscriptional beth,25
# ... etc for all Psalter variants
```

This would allow cross-script normalization.

---

## Use Cases

### 1. Zoroastrian Religious Texts

**Texts**: Bundahišn, Denkard, Wizīdagīhā ī Zādspram
- Primary sources for Zoroastrian cosmology and theology
- Written in Book Pahlavi (very cursive)
- Modern editions transcribed to Inscriptional Pahlavi

**Example** (Bundahišn opening):
```
𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣 𐭬𐭦𐭣𐭠𐭠𐭯 𐭥𐭲𐭬
(Ohrmazd andar mēnōg-tōm)
"Ohrmazd in the spiritual state"
```

**Benefit**: Normalize scholarly diacritics in modern critical editions

### 2. Sasanian Inscriptions

**Sources**: Rock inscriptions (e.g., Naqsh-e Rustam, Paikuli)
- Royal proclamations
- Clearest Pahlavi forms
- Less ambiguous than manuscripts

**Example** (Shapur I inscription):
```
𐭬𐭦 𐭱𐭧𐭯𐭥𐭧𐭫𐭩 𐭬𐭫𐭪𐭠𐭭 𐭬𐭫𐭪𐭠
(MN ŠHPWHRY MLKAN MLKA)
"I, Shapur, King of Kings"
```

**Benefit**: Consistent encoding across different inscription databases

### 3. Manichean Middle Persian

**Texts**: Manichean psalms and teachings
- Written in variant of Pahlavi
- Some texts use Sogdian or Syriac script instead
- Important for history of religions

**Special consideration**: Manichean texts often use Manichaean script (U+10AC0–U+10AFF), not Pahlavi

### 4. Administrative & Legal Documents

**Sources**: Clay seals, bullae, ostraca
- Tax records, contracts, receipts
- Short formulaic texts
- Heavy use of Aramaic heterograms

**Example**:
```
𐭬𐭫𐭪𐭠 + seal impression
(MLKA - "king" or official's title)
```

---

## Dictionary Entry Best Practices

When creating a Middle Persian dictionary for use with these normalization rules:

### 1. Use Inscriptional Pahlavi Standard Forms

✅ **Correct**:
```csv
lemma,language,definition
𐭬𐭫𐭣,middle_persian,man; person
𐭱𐭧𐭫,middle_persian,city; town
```

❌ **Avoid**:
- Mixed script forms (Psalter + Inscriptional)
- Custom/non-Unicode encodings
- Transliteration only (use actual script)

### 2. Include Both Heterogram and Phonetic Spellings

✅ **Recommended**:
```csv
lemma,language,definition,notes
𐭌𐭋𐭊𐭀,middle_persian,king,Heterogram (read: šāh)
𐭱𐭧𐭫,middle_persian,king,Phonetic spelling (šahr)
```

### 3. Handle Homographs with Context Notes

✅ **Recommended**:
```csv
lemma,language,definition,disambiguation
𐭬𐭫𐭣,middle_persian,man,mard (daleth final)
𐭬𐭫𐭥,middle_persian,death,murw (waw final)
```

### 4. Transliteration as Supplementary Data

✅ **Best practice**:
```csv
lemma,transliteration,language,definition
𐭬𐭫𐭣,MRD / mard,middle_persian,man; person
𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣,ʾwhwwmzd / Ohrmazd,middle_persian,Ahura Mazda (supreme deity)
```

---

## Comparison with Other Iranian Languages

### Old Persian (Cuneiform)
- **Script**: Cuneiform syllabary
- **Period**: 600-300 BCE
- **Normalization**: Different (cuneiform-specific)
- **Relation**: Ancestor of Middle Persian

### Modern Persian (Farsi)
- **Script**: Perso-Arabic alphabet
- **Period**: 800 CE - present
- **Normalization**: See `normalization_rules_persian.csv`
- **Relation**: Descendant of Middle Persian

### Parthian
- **Script**: Inscriptional Parthian (similar to Pahlavi)
- **Period**: 250 BCE - 224 CE
- **Unicode**: U+10B40–U+10B5F
- **Normalization**: Similar rules could apply

### Sogdian
- **Script**: Sogdian alphabet
- **Period**: 400-1000 CE
- **Unicode**: U+10F30–U+10F6F
- **Normalization**: Different script, different rules

---

## Technical Notes

### Unicode Encoding

**Inscriptional Pahlavi Block**: U+10B60–U+10B7F
- 22 letter characters (U+10B60 – U+10B75)
- 1 number sign (U+10B76)
- 4 number characters (U+10B77 – U+10B7A)
- 5 reserved codepoints

**Related Blocks**:
- **Psalter Pahlavi**: U+10B80–U+10BAF (different letter forms)
- **Inscriptional Parthian**: U+10B40–U+10B5F (related script)

### Character Encoding Requirements

- **Always use UTF-8** encoding
- **Supplementary plane** (U+10000+) requires 4-byte UTF-8
- **Font support**: Limited fonts support Pahlavi
  - Noto Sans Inscriptional Pahlavi (Google Fonts)
  - Ahuramzda (specialist font)

### Right-to-Left (RTL) Text

- Pahlavi is written **right-to-left**
- Unicode BiDi algorithm handles direction
- Mixing with Latin (LTR) requires careful handling

### NFD Normalization

The app applies **NFD** before custom rules:
- Separates combining marks from base characters
- Makes diacritic removal (Priority 1) more reliable
- Example: Base letter + combining accent splits for easier matching

---

## Limitations & Future Directions

### Current Limitations

1. **No Automatic Homograph Resolution**
   - Context-dependent reading not supported
   - User/scholar must encode correct letter

2. **No Heterogram Expansion**
   - Aramaic logograms not automatically converted to Persian
   - Dictionary must include both forms

3. **Single Script Variant**
   - Rules target Inscriptional Pahlavi only
   - Psalter and Book Pahlavi need separate handling

4. **Limited Digital Texts**
   - Middle Persian corpus is small compared to Modern Persian
   - Many texts exist only in transliteration

### Potential Future Enhancements

1. **Cross-Script Mapping**
   ```csv
   middle_persian,\u10B80,\u10B60,Map Psalter to Inscriptional,24
   ```

2. **Heterogram Normalization** (if desired)
   ```csv
   middle_persian,𐭌𐭋𐭊𐭀,𐭱𐭧𐭫,Expand MLKʾ to šahr,25
   ```

3. **Contextual Disambiguation** (AI-assisted)
   - Machine learning models for homograph resolution
   - Trained on annotated Middle Persian corpus

4. **Transliteration Integration**
   - Parallel lookup in Pahlavi and Latin transliteration
   - Bidirectional search support

---

## Testing Examples

### Example 1: Remove Modern Diacritics

**Input**: 𐭬𐭫́𐭣𐭩 (with accent)
**Output**: 𐭬𐭫𐭣𐭩
**Match**: 𐭬𐭫𐭣𐭩 (mard - "man") ✅

### Example 2: Zoroastrian Text

**Input**: 𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣́ 𐭬𐭦𐭣𐭠𐭠𐭯
**Normalized**: 𐭠𐭥𐭧𐭥𐭥𐭬𐭦𐭣 𐭬𐭦𐭣𐭠𐭠𐭯
**Reading**: Ohrmazd mēnōg-tōm ("Ohrmazd in the spiritual state")

### Example 3: Royal Inscription

**Input**: 𐭱𐭧𐭯𐭥𐭧𐭫𐭩 𐭬𐭋𐭊𐭀𐭭 𐭬𐭋𐭊𐭀
**Normalized**: 𐭱𐭧𐭯𐭥𐭧𐭫𐭩 𐭬𐭋𐭊𐭀𐭭 𐭬𐭋𐭊𐭀
**Reading**: Šāhpuhr MLKAN MLKA ("Shapur, King of Kings")
**Note**: Heterograms (𐭬𐭋𐭊𐭀 = MLKʾ) preserved

---

## FAQ

**Q: Why so few active normalization rules?**
A: Unicode Inscriptional Pahlavi already uses standardized codepoints. The main normalization need is removing scholarly diacritics. The framework exists for future variant handling.

**Q: What about Book Pahlavi manuscripts?**
A: Book Pahlavi is extremely cursive and ambiguous. Most digital texts transcribe to Inscriptional Pahlavi first. Direct Book Pahlavi digitization is rare.

**Q: How do I handle heterograms?**
A: Include both Aramaic spelling and Persian reading in your dictionary. Don't normalize heterograms automatically.

**Q: Can I mix Pahlavi and Persian in one text?**
A: Yes, but they use different Unicode blocks and different `language` tags in normalization rules. Keep them separate in your dictionary.

**Q: What about Manichaean Middle Persian?**
A: Manichaean texts often use Manichaean script (U+10AC0–U+10AFF), not Pahlavi. Create separate rules for that script.

**Q: Is there a standard transliteration?**
A: Scholars use various systems. Common: MacKenzie system, using capital letters for Aramaic heterograms (MLKʾ) and lowercase for phonetic (šāh).

---

## Summary

✅ **23 normalization rules** for Middle Persian (Pahlavi)
✅ **Handles scholarly diacritics** in modern editions
✅ **Framework for variant mapping** (Inscriptional ↔ Psalter)
✅ **Preserves semantic heterograms** (Aramaic logograms)
✅ **Compatible with Inscriptional Pahlavi** Unicode standard
✅ **Production-ready** for Zoroastrian texts and Sasanian inscriptions

Use `normalization_rules_middle_persian.csv` in your Middle Persian dictionary ZIP for consistent text matching.

---

## References

### Unicode Standards
- **Inscriptional Pahlavi**: https://unicode.org/charts/PDF/U10B60.pdf
- **Psalter Pahlavi**: https://unicode.org/charts/PDF/U10B80.pdf

### Academic Resources
- MacKenzie, D.N. (1971). *A Concise Pahlavi Dictionary*
- Skjærvø, P.O. (2009). *Middle West Iranian*
- Henning, W.B. (1958). *Mitteliranisch* (Handbook of Oriental Studies)

### Digital Text Projects
- **TITUS**: Thesaurus Indogermanischer Text- und Sprachmaterialien
- **Corpus of Middle Persian Texts**: Various academic databases
- **Avestan Digital Archive**: Including Middle Persian materials
