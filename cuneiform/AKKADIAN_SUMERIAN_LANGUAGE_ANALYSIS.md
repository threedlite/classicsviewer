# Analysis: Adding Akkadian and Sumerian Language Support to Classics Viewer

## Executive Summary

This document analyzes the requirements and implications of adding Akkadian and/or Sumerian language buttons to the Classics Viewer Android app, which currently supports Greek and Latin classical texts.

## Current Implementation

### Language Selection Architecture
- **UI Layer**: MainActivity displays language buttons using a RecyclerView with LanguageAdapter
- **Data Model**: Simple `Language` data class with `name` and `code` fields
- **Database Schema**: Authors table includes a `language` column (TEXT) that stores "greek" or "latin"
- **Color Scheme**: Follows Loeb Classical Library convention (green for Greek, red for Latin)

### Database Structure
```sql
CREATE TABLE authors (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    language TEXT NOT NULL,  -- Currently "greek" or "latin"
    ...
)
```

## Technical Requirements for New Languages

### 1. Minimal UI Changes
**Effort: Low**

Add new language buttons in MainActivity:
```kotlin
val languages = listOf(
    Language("Greek", "greek"),
    Language("Latin", "latin"),
    Language("Akkadian", "akkadian"),  // New
    Language("Sumerian", "sumerian")    // New
)
```

Add color mappings in LanguageAdapter:
- Akkadian: Brown (#8B6F47) - representing clay tablets
- Sumerian: Blue (#2E5090) - representing lapis lazuli

### 2. Database Schema
**Effort: None to Minimal**

The current schema already supports additional languages via the TEXT `language` column. No schema changes required.

### 3. Data Preparation Pipeline
**Effort: Very High**

This is where the majority of work resides:

#### Text Source Requirements
- **Cuneiform texts**: Need transliterated versions (not cuneiform script)
- **Standard editions**: ETCSL for Sumerian, SEAL/SAA for Akkadian
- **XML/TEI format**: Ideally structured like Perseus texts
- **Translations**: English translations for user accessibility

#### New Components Needed

##### A. Text Parser (`create_akkadian_sumerian_database.py`)
- Parse cuneiform transliteration formats (ATF, TEI-XML)
- Handle special characters (š, ṣ, ṭ, ḫ, etc.)
- Process sign indices (e.g., du₃, ki₂)
- Line numbering conventions (obverse/reverse for tablets)

##### B. Normalization System
- Akkadian normalization (handling Akkadian-specific diacritics)
- Sumerian normalization (sign variants, determinatives)
- Search compatibility with multiple transliteration standards

##### C. Morphological Analysis
- **Akkadian**: Would need dictionary integration (see options below)
- **Sumerian**: Would need ePSD2 (Electronic Pennsylvania Sumerian Dictionary)
- Both are agglutinative languages requiring different lemmatization

##### D. Dictionary Integration

**Akkadian Dictionary Options:**
1. **CAD (Chicago Assyrian Dictionary)**
   - Status: Free PDFs available from Oriental Institute
   - License: Copyright status unclear, need verification
   - Content: Complete 26-volume dictionary (1956-2011)
   - Challenge: No explicit open license, may need permission

2. **ORACC Corpus-Based Dictionary (CBD)**
   - Status: Available under CC BY-SA 3.0
   - Content: Lemmatized glossaries from cuneiform corpus
   - Advantage: Already integrated with ORACC texts
   - Format: Structured glossary entries with citations

**Sumerian Dictionary:**
- **ePSD2**: CC BY-SA license, fully compatible
- Format conversion to match existing dictionary structure

### 4. Text Rendering Considerations
**Effort: Low to Medium**

#### Cuneiform Script Display
**Important**: Cuneiform Unicode (U+12000-U+12400) is NOT supported by stock Android fonts
- Would display as empty rectangles/placeholders
- Custom font installation difficult on Android
- **Solution**: Use transliterated text only, not cuneiform glyphs

#### Transliteration Display
**Good news**: Akkadian/Sumerian transliterations use Latin script with diacritics
- Basic characters: Standard ASCII/Latin alphabet
- Special characters: š, ṣ, ṭ, ḫ, ĝ, ñ (mostly supported by Android)
- Subscript numbers: x₂, x₃ (for sign indices)
- Conventions:
  - CAPITALS = Sumerian logograms
  - lowercase = syllabic/phonetic readings
  - Superscript = determinatives (ᵈ for deity, etc.)

#### Display Format
- Tablet/manuscript references (e.g., "Tablet I, Column ii, Line 45")
- Broken text indicators ([...], ⸢...⸣)
- Line preservation marks

**Recommendation**: Display transliterated text only, which works with standard Android fonts. Avoid attempting to display actual cuneiform Unicode characters.

### 5. Search and Navigation
**Effort: Medium**

- Adapt search for logograms vs. syllabic spellings
- Handle Sumerian-Akkadian bilingual texts
- Support period-specific searching (Old Babylonian, Neo-Assyrian, etc.)

## Data Availability Analysis

### Akkadian Sources
1. **SEAL (Sources of Early Akkadian Literature)**: ~150 literary texts
2. **SAA (State Archives of Assyria)**: Thousands of administrative texts
3. **CDLI (Cuneiform Digital Library)**: 350,000+ transliterated tablets
4. **ORACC Projects**: Multiple curated corpora with translations

### Sumerian Sources
1. ~~**ETCSL**: ~400 compositions~~ (CC BY-NC-SA - cannot use)
2. **ORACC Sumerian projects**: Various texts under CC BY-SA
3. **ePSD2**: Dictionary with linked corpus (CC BY-SA)
4. **CDLI**: Extensive holdings (license needs verification)

### Licensing Considerations - CC-BY-SA Compatible Sources

#### Available CC-BY-SA Sources

**For Akkadian:**
1. **ORACC (Open Richly Annotated Cuneiform Corpus)**
   - License: CC BY-SA 3.0 (default for most projects)
   - Content: Thousands of curated, transliterated Akkadian texts with translations
   - Includes major corpora like RINAP (Royal Inscriptions), SAAo (State Archives)
   - Fonts: SIL Open Font License

**For Sumerian:**
1. **ePSD2 (Electronic Pennsylvania Sumerian Dictionary)**
   - License: CC BY-SA ✅
   - Content: 12,000+ Sumerian words, 100,000 distinct forms
   - Comprehensive dictionary with 2.27 million occurrences indexed
   - Hosted on ORACC platform

2. **ORACC Sumerian Texts**
   - License: CC BY-SA 3.0 ✅
   - Various Sumerian text projects hosted on ORACC
   - Includes literary, administrative, and royal inscriptions

3. ~~**ETCSL (Electronic Text Corpus of Sumerian Literature)**~~
   - License: CC BY-NC-SA 3.0 ❌ **Cannot use due to NonCommercial restriction**
   - Would have provided ~400 literary texts but incompatible with app distribution

4. **CDLI (Cuneiform Digital Library Initiative)**
   - Open access commitment, specific license needs verification
   - 500,000+ tablet images and transliterations
   - Code: MIT license (open source)

#### Usable Sources Summary

**Texts & Dictionaries (Content):**
- **ORACC texts (Akkadian & Sumerian)**: ✅ CC BY-SA 3.0 - Fully usable
- **ePSD2 (Sumerian dictionary)**: ✅ CC BY-SA - Fully usable, standalone dictionary
- **ORACC CBD (Akkadian dictionary)**: ✅ CC BY-SA 3.0 - Embedded in project glossaries
  - **Important Note**: Not a standalone dictionary like ePSD2
  - Each ORACC project (RINAP, SAAo, RIAo, CMAwRo) contains its own glossary/lexicon
  - Glossaries are included in JSON downloads but are project-specific
  - Would need to aggregate multiple project glossaries for comprehensive Akkadian dictionary coverage

**Code/Tools:**
- **pyoracc**: ✅ Check specific license (may be usable)
- **ORACC main code**: ⚠️ GPL-2.0 - Incompatible with MIT license
- **nisaba**: ⚠️ GPL-3.0 - Incompatible with MIT license

**Cannot Use:**
- **ETCSL**: ❌ CC BY-NC-SA - NonCommercial restriction
- **ORACC code (GPL)**: ❌ GPL incompatible with MIT
- **CAD**: 🔍 Free PDFs but license unclear
- **CDLI**: 🔍 License verification needed

**Note:** While ORACC's *content* (texts/dictionaries) is CC BY-SA and usable, their *code* is GPL-licensed and cannot be incorporated into MIT-licensed projects. You'll need to write your own parsers.

## Implementation Roadmap

### Phase 1: Proof of Concept (2-3 weeks)
1. Select 5-10 well-known texts (Epic of Gilgamesh, Code of Hammurabi)
2. Manual data preparation for testing
3. Basic display without morphology
4. Validate rendering and search

### Phase 2: Parser Development (4-6 weeks)
1. Build ATF/XML parsers for cuneiform texts
2. Implement normalization rules
3. Create database import pipeline
4. Test with larger corpus (50-100 texts)

### Phase 3: Dictionary Integration (3-4 weeks)
1. Parse CAD/ePSD2 formats
2. Convert to app dictionary schema
3. Link lemmas to dictionary entries
4. Test lookup functionality

### Phase 4: Full Corpus Import (2-3 weeks)
1. Process complete ETCSL for Sumerian
2. Import selected Akkadian corpora
3. Quality assurance and testing
4. Performance optimization

### Phase 5: UI Polish (1 week)
1. Add language-specific colors
2. Refine special character display
3. Update help documentation
4. Release preparation

## Challenges and Risks

### Technical Challenges
1. **Complexity of scripts**: Cuneiform transliteration has many conventions
2. **Data quality**: Many texts are fragmentary or disputed
3. **Morphology**: Agglutinative languages are harder to lemmatize
4. **File size**: Adding two languages could double database size

### Scholarly Challenges
1. **Text authority**: Multiple editions of same text
2. **Translation quality**: Many texts lack modern translations
3. **Periodization**: Akkadian spans 3,000 years with major changes
4. **Writing systems**: Same signs read differently in Sumerian vs. Akkadian

### User Experience Challenges
1. **Learning curve**: Cuneiform conventions unfamiliar to classical users
2. **Search complexity**: Multiple valid spellings for same word
3. **Fragment navigation**: Broken texts harder to read continuously

## Recommendations

### Start with Akkadian
- More standardized transliteration
- Better dictionary resources (CAD)
- More familiar to classicists (Semitic language family)
- Epic of Gilgamesh provides compelling flagship text

### Minimum Viable Product
1. 20-30 major literary texts
2. Basic dictionary lookup
3. Simple normalization (no full morphology initially)
4. English translations where available

### Consider Partnership
- Collaborate with ORACC/CDLI for data
- Consult Assyriologists for text selection
- Possible academic grant funding

## Estimated Timeline

**Minimum implementation**: 3-4 months for one language with basic features
**Full implementation**: 6-8 months for both languages with morphology
**Maintenance**: Ongoing updates as new texts are published

## Conclusion

Adding Akkadian and Sumerian is technically feasible with the current architecture, requiring minimal app changes but substantial data preparation work. The main challenges are:

1. **Data acquisition and parsing** - Finding and converting appropriate text sources
2. **Linguistic processing** - Building normalization and morphology systems
3. **Dictionary integration** - Converting specialized dictionaries to app format
4. **Quality assurance** - Ensuring accurate display of complex transliteration

The project would significantly expand the app's scope from Classical to Ancient Near Eastern studies, potentially attracting new user communities and academic partnerships.

## Next Steps

If proceeding:
1. Survey available text corpora and verify licensing
2. Build proof-of-concept with 5 Akkadian texts
3. Engage Assyriologist consultant for validation
4. Estimate database size impact
5. Plan phased release strategy