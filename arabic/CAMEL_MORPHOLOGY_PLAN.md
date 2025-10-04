# CAMeL Tools Morphology Integration Plan

## ⚠️ LICENSE BLOCKER - PLAN CANCELLED

**CRITICAL ISSUE:** CAMeL Tools morphology databases are GPL v2 licensed

## License Analysis

**CAMeL Tools Components:**
- **Code:** MIT ✅ Compatible
- **MSA Morphology Database (calima-msa-r13):** GPL v2 ❌ **INCOMPATIBLE**
- **Gulf Arabic Database:** CC BY 4.0 ✅ Compatible (but wrong dialect)
- **Levantine Arabic Database:** CC BY 4.0 ✅ Compatible (but wrong dialect)

**Verdict:** Cannot use MSA morphology database due to GPL copyleft requirements

## Original Goal (Now Cancelled)
Use CAMeL Tools to generate word → root mappings for the Mu'allaqa text, creating a morphology.csv file for word lookup in ClassicsViewer.

## Why This Won't Work

**CAMeL Tools** (Columbia Arabic Language and dIalect Toolkit)
- **License:** MIT (code) + **GPL v2 (MSA data)** ❌ Incompatible with MIT app
- **Coverage:** Modern Standard Arabic (MSA)
- **Limitation:** Pre-Islamic poetry has archaic vocabulary - would expect ~60-80% coverage IF we could use it

## Current Status

**Existing Data:**
- ✅ Arabic text database: 78 verses, 770 total words, 606 unique normalized words
- ✅ Lane's Lexicon dictionary: 43,940 entries
- ❌ No morphology file (word form → lemma mappings)

**Without morphology:** Users must manually determine root from inflected forms
**With morphology:** Automatic word → root lookup (where CAMeL can analyze)

---

## Implementation Plan

### Phase 1: Setup & Research

#### 1.1 Install CAMeL Tools
```bash
# Python 3.8-3.12 required
pip install camel-tools

# Download morphology databases
camel_data -i morphology-msa-r13
```

**Requirements:**
- Python 3.8-3.12
- Rust compiler (for installation)
- ~500 MB for MSA morphology database

#### 1.2 Test CAMeL on Sample Words
```python
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

# Load MSA database
db = MorphologyDB.builtin_db('calima-msa-r13')
analyzer = Analyzer(db)

# Test analysis
word = "كتب"  # kataba (he wrote)
analyses = analyzer.analyze(word)
for analysis in analyses:
    print(f"Lemma: {analysis['lex']}")
    print(f"Root: {analysis.get('root', 'N/A')}")
```

---

### Phase 2: Extract Words from Database

#### 2.1 Query Unique Words
```python
import sqlite3

conn = sqlite3.connect('arabic/arabic_texts.db')
cursor = conn.cursor()

# Get unique words with diacritics (for better analysis)
cursor.execute("""
    SELECT DISTINCT word, word_normalized
    FROM words
    ORDER BY word
""")

words = cursor.fetchall()
print(f"Total unique words: {len(words)}")
```

**Expected:** ~606 unique normalized words

#### 2.2 Handle Diacritics
- **With diacritics:** Better CAMeL analysis (قِفَا vs قفا)
- **Without diacritics:** Fallback for normalized lookup

**Strategy:** Analyze both versions, prefer diacriticized result

---

### Phase 3: Morphological Analysis

#### 3.1 Create Analysis Script
**Script:** `arabic/analyze_morphology.py`

```python
#!/usr/bin/env python3
"""
Analyze Mu'allaqa words with CAMeL Tools to extract lemmas and roots
"""

from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
import sqlite3
import csv
from pathlib import Path

# Load database
print("Loading CAMeL Tools MSA database...")
db = MorphologyDB.builtin_db('calima-msa-r13')
analyzer = Analyzer(db)

# Extract words
conn = sqlite3.connect('arabic/arabic_texts.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT word, word_normalized FROM words")
words = cursor.fetchall()

# Analyze each word
morphology_entries = []
for word, word_normalized in words:
    # Try with diacritics first
    analyses = analyzer.analyze(word)

    if not analyses:
        # Fallback: try normalized (no diacritics)
        analyses = analyzer.analyze(word_normalized)

    if analyses:
        # Take first (most likely) analysis
        top_analysis = analyses[0]

        entry = {
            'word_form': word_normalized,  # Store normalized for lookup
            'lemma': top_analysis.get('lex', word_normalized),
            'root': top_analysis.get('root', ''),
            'pos': top_analysis.get('pos', ''),
            'language': 'arabic',
            'confidence': 1.0 if len(analyses) == 1 else 0.8,
            'source_name': 'CAMeL Tools MSA'
        }
        morphology_entries.append(entry)
    else:
        # No analysis found - store as-is
        entry = {
            'word_form': word_normalized,
            'lemma': word_normalized,
            'root': '',
            'pos': '',
            'language': 'arabic',
            'confidence': 0.0,  # Unknown
            'source_name': 'Unanalyzed'
        }
        morphology_entries.append(entry)

# Write to CSV
with open('arabic/arabic_morphology.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['word_form', 'lemma', 'root', 'pos', 'language', 'confidence', 'source_name'])
    writer.writeheader()
    writer.writerows(morphology_entries)

# Statistics
analyzed = sum(1 for e in morphology_entries if e['confidence'] > 0)
print(f"Analyzed: {analyzed}/{len(morphology_entries)} ({analyzed/len(morphology_entries)*100:.1f}%)")
```

#### 3.2 Expected Results
- **MSA-compatible words:** ~60-80% coverage (modern/classical overlap)
- **Archaic words:** Will fail (مَنْزِلِ, حَبِيبٍ might work, but obscure terms won't)
- **Common words:** Should work well (من، في، على، etc.)

---

### Phase 4: Output Format

#### 4.1 Morphology CSV Structure
**File:** `arabic_morphology.csv`

```csv
word_form,lemma,root,pos,language,confidence,source_name
كتب,كَتَبَ,ك-ت-ب,verb,arabic,1.0,CAMeL Tools MSA
من,مِن,,prep,arabic,1.0,CAMeL Tools MSA
قفا,قَفَا,ق-ف-و,verb,arabic,0.8,CAMeL Tools MSA
منزل,مَنزِل,ن-ز-ل,noun,arabic,1.0,CAMeL Tools MSA
```

**Fields:**
- `word_form`: Normalized word (no diacritics)
- `lemma`: Dictionary form (with diacritics)
- `root`: Trilateral/quadrilateral root (ك-ت-ب format)
- `pos`: Part of speech (verb, noun, prep, etc.)
- `language`: "arabic"
- `confidence`: 0.0-1.0 (1.0 = single analysis, 0.8 = multiple, 0.0 = failed)
- `source_name`: "CAMeL Tools MSA" or "Unanalyzed"

#### 4.2 Integration with Lexicon ZIP
Update `create_arabic_lexicon.py` to include morphology:

```python
# In create_lexicon_zip():
morph_source = SCRIPT_DIR / "arabic_morphology.csv"
morph_temp = SCRIPT_DIR / "morphology.csv"

if morph_source.exists():
    shutil.copy(morph_source, morph_temp)
    print(f"  Including morphology.csv")

with zipfile.ZipFile(ARABIC_LEXICON_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(dict_temp, 'dictionary.csv')
    zipf.write(norm_temp, 'normalization_rules.csv')
    if morph_source.exists():
        zipf.write(morph_temp, 'morphology.csv')
```

**Result:** `arabic_lexicon.zip` contains:
- `dictionary.csv` (Lane's Lexicon)
- `normalization_rules.csv` (Arabic normalization)
- `morphology.csv` (CAMeL analysis)

---

### Phase 5: Database Integration

#### 5.1 App Import Process
The Android app already supports importing morphology from custom dictionary ZIPs (see Hebrew implementation).

**Import flow:**
1. User selects `arabic_lexicon.zip` in app
2. App extracts to internal storage
3. Reads `morphology.csv` into database
4. Creates lookup table: word_form → lemma

#### 5.2 Word Lookup Flow
```kotlin
// User taps word "كتب" in text
val word = "كتب"
val normalized = normalize(word)  // Apply normalization rules

// Check morphology table
val lemma = morphologyDao.getLemma(normalized)  // Returns "كَتَبَ"

// Look up in dictionary
val definition = dictionaryDao.getDefinition(lemma)  // Lane's entry
```

---

## Expected Coverage Analysis

### Words Likely to Succeed (MSA Compatible)
- **Prepositions:** من، في، على، إلى (100% coverage expected)
- **Common verbs:** كان، قال، جاء (90% coverage)
- **Common nouns:** بيت، يوم، ليل (80% coverage)

### Words Likely to Fail (Pre-Islamic/Archaic)
- **Archaic vocabulary:** Poetic terms unique to Jahiliyya period
- **Rare verb forms:** Unusual conjugations not in MSA
- **Proper nouns:** Place names, tribal names

### Estimated Overall Coverage: 65-75%

---

## Fallback Strategy

For unanalyzed words (25-35%):

### Option A: Manual Annotation
Create `arabic_morphology_manual.csv` for high-frequency archaic words:
```csv
word_form,lemma,root,pos,language,confidence,source_name
حبيب,حَبيب,ح-ب-ب,noun,arabic,1.0,Manual annotation
منزل,مَنزِل,ن-ز-ل,noun,arabic,1.0,Manual annotation
```

Merge with CAMeL results.

### Option B: Lane's Lexicon Mapping
Some Lane's entries include roots - could extract and match.

### Option C: Accept Partial Coverage
Start with CAMeL-only, document limitations, add manual entries over time.

**Recommendation:** Start with Option C, add Option A for top 50 unanalyzed words

---

## Alternative: Qalsadi (GPL - Not Compatible)

**Qalsadi** is GPL-licensed (incompatible with MIT):
- Better classical Arabic support
- More comprehensive root extraction
- Cannot be used due to GPL copyleft requirements

---

## Implementation Timeline

1. **Install & Test** (30 min)
   - Install CAMeL Tools
   - Test on sample words
   - Verify database installation

2. **Extract & Analyze** (1 hour)
   - Create analysis script
   - Run on all 606 unique words
   - Generate morphology.csv

3. **Review & Enhance** (1 hour)
   - Analyze coverage statistics
   - Identify failed words
   - Manually add top 20-50 archaic words

4. **Integration** (30 min)
   - Update lexicon creation script
   - Regenerate arabic_lexicon.zip
   - Test import in app

**Total estimated time:** 3 hours

---

## Success Criteria

✅ **Minimum:**
- 60%+ word coverage from CAMeL Tools
- Morphology integrated into arabic_lexicon.zip
- App successfully imports and uses morphology

✅ **Target:**
- 75%+ coverage (CAMeL + manual top words)
- All common words (من، في، على) have lemmas
- User can tap most words and get dictionary lookup

✅ **Stretch:**
- 85%+ coverage with extensive manual annotation
- Alternative analyzer for remaining archaic words
- Root-based search functionality

---

## License Compliance

**CAMeL Tools:**
- Code: MIT License ✅
- Data: CC BY 4.0 ✅

**Required Attribution (already added to LicenseActivity.kt):**
```
CAMeL Tools: An Open Source Python Toolkit for Arabic Natural Language Processing
Copyright (c) 2018-2024 New York University Abu Dhabi
Licensed under MIT License

CAMeL Morph Morphological Databases
Licensed under Creative Commons Attribution 4.0 International License
New York University Abu Dhabi
```

---

## Next Steps

1. ✅ Plan created (this document)
2. ⏳ Install CAMeL Tools
3. ⏳ Create analysis script
4. ⏳ Generate morphology.csv
5. ⏳ Update lexicon ZIP
6. ⏳ Test in app
7. ⏳ Document coverage and limitations

**Ready to proceed with implementation!**
