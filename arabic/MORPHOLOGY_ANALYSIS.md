# Arabic Morphology Options Analysis

## Overview

This document analyzes available Arabic morphological resources for word form → lemma mapping in ClassicsViewer, focusing on license compatibility and classical Arabic coverage.

## License Requirements

ClassicsViewer uses **MIT License**, which requires morphological data to be:
- ✅ MIT, Apache, BSD, CC-BY, CC-BY-SA
- ❌ GPL, LGPL (requires derivatives to be GPL)
- ❌ CC-BY-NC (NonCommercial restriction)

---

## Arabic Morphology Resources Evaluated

### 1. Quranic Arabic Corpus

**License:** GPL-3.0 ❌
**Source:** https://github.com/kaisdukes/quranic-corpus, https://github.com/mustafa0x/quran-morphology
**Coverage:** 77,430 words with complete morphological analysis

**Verdict:** ❌ **Not usable** - GPL license incompatible with MIT (requires derivatives to be GPL)

**Data Quality:**
- Complete word → root, lemma, POS, grammatical features
- Classical Arabic (6th-7th century CE)
- Similar register to Mu'allaqa

---

### 2. CAMeL Tools & CAMeL Morph

**License:**
- **Code:** MIT ✅
- **Data:** CC BY 4.0 ✅

**Source:**
- Tools: https://github.com/CAMeL-Lab/camel_tools
- Morphology: https://github.com/CAMeL-Lab/camel_morph

**Coverage:**
- Modern Standard Arabic (MSA)
- Egyptian Arabic dialect
- Verbs, nominals, morphological categories

**Verdict:** ✅ **License compatible**, ⚠️ **Coverage limited**

**Limitations:**
- Designed for Modern Standard Arabic, not Classical Arabic
- Pre-Islamic poetry (Mu'allaqa) uses archaic vocabulary not in MSA models
- Will work for some words, fail on archaic/poetic forms

**Credits Required:**
```
Morphological analysis uses CAMeL Tools
Copyright (c) 2018-2024 New York University Abu Dhabi
Licensed under MIT License

Morphological databases from CAMeL Morph
Licensed under CC BY 4.0 International License
https://github.com/CAMeL-Lab/camel_morph
```

---

### 3. Qalsadi Morphological Analyzer

**License:** GPL ❌
**Source:** https://github.com/linuxscout/qalsadi

**Verdict:** ❌ **Not usable** - GPL license incompatible with MIT

---

### 4. Arramooz Arabic Dictionary

**License:** GPL ❌
**Source:** https://github.com/linuxscout/arramooz

**Verdict:** ❌ **Not usable** - GPL license incompatible with MIT

---

### 5. Universal Dependencies Arabic Treebanks

**Licenses:**
- UD Arabic-PADT: CC BY-NC-SA 3.0 ❌
- UD Arabic-NYUAD: CC BY-SA 4.0 ✅

**Source:** https://universaldependencies.org/

**Limitations:**
- UD Arabic-NYUAD is compatible but...
- Text not included (must obtain separately from LDC Penn Arabic Treebank)
- Modern newswire genre, not classical poetry
- Would require significant preprocessing

**Verdict:** ⚠️ **Technically compatible but impractical**

---

### 6. Lane's Arabic-English Lexicon Inflections

**License:** CC BY-SA 3.0 ✅
**Source:** Perseus Digital Library (already integrated)

**Coverage:**
- ~6,669 inflection entries
- Verb conjugation paradigms (aorist forms)
- Arabic verb forms I-X

**Limitations:**
- **Transliterated**, not Arabic script (e.g., `maw^uja` not `مَوَجَ`)
- **Paradigmatic** (how verbs *can* inflect) not actual text words
- **Verb-focused**, minimal noun/adjective coverage
- Estimated <5% coverage of Mu'allaqa vocabulary

**Verdict:** ⚠️ **Available but insufficient**

---

## Current Reality

**No permissively-licensed classical Arabic morphology dataset exists** that:
1. Has MIT/Apache/BSD/CC-BY compatible license
2. Covers pre-Islamic/classical Arabic vocabulary
3. Provides word form → lemma mappings

---

## Recommended Approaches

### Option 1: Dictionary-Only Lookup (Immediate Implementation)

**Approach:**
- Use Lane's Lexicon for root/lemma definitions
- Users must know the root form to look up words
- No automatic word form → root resolution

**Pros:**
- ✅ Available now
- ✅ Fully compatible license (CC BY-SA 3.0)
- ✅ 43,940 dictionary entries

**Cons:**
- ❌ Users must manually determine root from inflected forms
- ❌ Less convenient than Greek/Latin/Hebrew word lookup

**Implementation Status:** ✅ Complete (`arabic_lexicon.zip`)

---

### Option 2: CAMeL Tools Enhancement (Future)

**Approach:**
- Use CAMeL Tools to analyze Mu'allaqa text
- Generate word → lemma mappings for MSA-compatible words
- Fail gracefully for archaic vocabulary

**Pros:**
- ✅ License compatible (MIT + CC BY 4.0)
- ✅ Automatic analysis for modern-compatible words
- ✅ Better than nothing

**Cons:**
- ⚠️ Partial coverage (many archaic words will fail)
- ⚠️ Requires Python runtime or pre-processing step

**Credits Required:**
```
CAMeL Tools: An Open Source Python Toolkit for Arabic Natural Language Processing
Ossama Obeid, Nasser Zalmout, Salam Khalifa, Dima Taji, Mai Oudah,
Bashar Alhafni, Go Inoue, Fadhl Eryani, Alexander Erdmann, and Nizar Habash.
In Proceedings of the 12th Language Resources and Evaluation Conference (LREC),
Marseille, France, 2020.

CAMeL Morph Morphological Databases
Licensed under Creative Commons Attribution 4.0 International License
New York University Abu Dhabi
```

---

### Option 3: Manual Morphology for Mu'allaqa (High Quality)

**Approach:**
- Extract ~500-1000 unique words from Mu'allaqa poem
- Manually create word → root mappings
- Build morphology.csv specific to this poem

**Pros:**
- ✅ Complete coverage for the demonstration text
- ✅ High accuracy
- ✅ No license issues (original work)

**Cons:**
- ❌ Labor intensive
- ❌ Only covers one poem
- ❌ Not scalable to other Arabic texts

**Potential Strategy:**
- Start with high-frequency words
- Add incrementally over time
- Could crowdsource from Arabic scholars

---

## Recommended Implementation Path

### Phase 1: Dictionary-Only (Current) ✅
- Deploy Lane's Lexicon as custom dictionary
- Users search by root form
- Similar to early Greek/Latin implementation

### Phase 2: CAMeL Tools Integration (Future)
- Add CAMeL Tools morphological analysis
- Pre-process Mu'allaqa text to generate word mappings
- Create `morphology.csv` with MSA-compatible words
- Document coverage limitations

### Phase 3: Manual Enhancement (Long-term)
- Identify high-frequency archaic words not covered by CAMeL
- Manually add morphology entries for these words
- Gradually improve coverage to 80%+ of Mu'allaqa vocabulary

---

## License Credits

### Lane's Arabic-English Lexicon
```
Text provided by Perseus Digital Library, with funding from
The U.S. Department of Education and The Max Planck Society.

License: Creative Commons Attribution-ShareAlike 3.0 United States
Source: https://www.perseus.tufts.edu/hopper/opensource/
```

### CAMeL Tools (if implemented)
```
CAMeL Tools: An Open Source Python Toolkit for Arabic Natural Language Processing
Copyright (c) 2018-2024 New York University Abu Dhabi

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

Source: https://github.com/CAMeL-Lab/camel_tools
```

### CAMeL Morph Databases (if implemented)
```
CAMeL Morph Morphological Databases
New York University Abu Dhabi

Creative Commons Attribution 4.0 International License

You are free to:
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material for any purpose,
  even commercially

Under the following terms:
- Attribution — You must give appropriate credit, provide a link to the
  license, and indicate if changes were made

Source: https://github.com/CAMeL-Lab/camel_morph
```

---

## Conclusion

For immediate deployment, **dictionary-only approach** using Lane's Lexicon is the pragmatic choice. Future enhancements can add morphological analysis using CAMeL Tools (MIT + CC BY 4.0 compatible) to provide partial automatic word → root resolution, with manual enhancement for high-frequency archaic vocabulary.

The lack of permissively-licensed classical Arabic morphology is a gap in the open-source NLP ecosystem that may improve over time as more academic projects adopt permissive licenses.
