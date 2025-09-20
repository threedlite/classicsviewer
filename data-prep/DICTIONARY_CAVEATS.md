# Dictionary System Caveats and Edge Cases

## Unicode and Encoding Issues

### 1. NFD vs NFC Normalization
**Problem**: Greek text can be encoded in two ways:
- NFD (Decomposed): α + ́ = ά (base + combining accent)
- NFC (Composed): ά (single precomposed character)

**Why it matters**: String comparison fails when comparing NFD vs NFC
- "μῆνιν" (NFC) ≠ "μῆνιν" (NFD) at the byte level

**Solution**: Everything is normalized to NFC using `unicodedata.normalize('NFC', text)`

### 2. Combining Diacriticals Order
**Problem**: Multiple combining marks can appear in different orders:
- α + ̓ + ́ (smooth breathing + acute)
- α + ́ + ̓ (acute + smooth breathing)

**Solution**: NFC normalization standardizes the order

## Greek Language Specific Issues

### 1. Grave Accents at Clause Endings
**Problem**: Greek acute accents (ά) become grave (ὰ) at the end of clauses
- Text has: "θεὰ" (grave)
- Dictionary has: "θεά" (acute)

**Solution**: Generate grave variants for ALL words with acute accents

### 2. Enclitic Particles
**Problem**: Certain Greek particles lose their accent when enclitic:
- Dictionary: τέ, πού, γέ
- Text: τε, που, γε (unaccented)

**Affected words**:
- τέ/τε (and)
- πού/που (somewhere)
- γέ/γε (at least)
- μέ/με (me)
- σέ/σε (you)
- And others...

**Solution**: Generate unaccented variants for known enclitics

### 3. Macrons and Breves in Scholarly Texts
**Problem**: Wiktionary uses scholarly notation with vowel length marks:
- πολῠ́ς (with breve on υ = short u)
- ᾱ̓νήρ (with macron on α = long a)

**But dictionaries use**:
- πολύς (no length mark)
- ἀνήρ (no length mark)

**Solution**: Strip all macrons and breves during lemma processing

### 4. Patronymic Names
**Problem**: Many Greek names are patronymics without real definitions:
- Πηλείδης = son of Peleus
- Ἀτρείδης = son of Atreus

**Solution**: Detect -άδης/-ίδης/-ιάδης endings and generate meaningful descriptions

## Dictionary Source Conflicts

### 1. Multiple Dictionary Coverage
**Problem**: Same word appears in multiple sources with different definitions:
- Cunliffe: Specialized Homeric meanings
- LSJ: General/classical meanings
- Wiktionary: Modern linguistic analysis

**Solution**: Priority system: Cunliffe > LSJ > Wiktionary

### 2. Headword Normalization
**Problem**: Different dictionaries use different headword conventions:
- Some include punctuation: "ἄν,"
- Some don't: "ἄν"
- Some use different diacriticals

**Solution**: Strip punctuation and normalize during matching

### 3. Missing Definitions
**Problem**: Wiktionary morphology includes many forms without definitions
- Has: μῆνιν → μῆνις (accusative of μῆνις)
- Missing: What μῆνις actually means

**Solution**: 
1. Try to find definition from other sources
2. Generate meaningful placeholder based on part of speech
3. Never show "[unknown]" to users

## Technical Implementation Issues

### 1. Database Schema Constraints
**Problem**: Room (Android ORM) requires exact schema match:
- Original: Composite primary key (word_form, lemma)
- Room expects: Autoincrement integer ID

**Solution**: Changed to autoincrement ID with separate indexes

### 2. Large File Processing
**Problem**: Full LSJ has 116,000+ entries, creates memory issues

**Solution**: Process in chunks, use streaming where possible

### 3. Circular Dependencies
**Problem**: Some words reference themselves or create cycles:
- ὁράω → ὁρῶ → ὁράω

**Solution**: Track visited nodes during processing

### 4. Performance Optimization
**Problem**: 440,000+ lemma mappings slow down lookups

**Solution**: Create indexes on word_form and lemma columns

## Edge Cases in Word Forms

### 1. Crasis (Word Fusion)
**Examples**: 
- κἀγώ = καὶ ἐγώ (and I)
- τοὔνομα = τὸ ὄνομα (the name)

**Current Status**: Not fully handled, requires word splitting logic

### 2. Elision
**Examples**:
- δ' = δέ (but)
- ἀλλ' = ἀλλά (but)

**Current Status**: Common elisions handled in morphology data

### 3. Dialectical Variations
**Problem**: Different Greek dialects have different forms:
- Attic: πρᾶγμα
- Ionic: πρῆγμα
- Doric: πρᾶγμα

**Solution**: Wiktionary morphology includes major dialectical variants

### 4. Compound Words
**Problem**: Greek freely creates compounds not in dictionaries:
- πολυμῆτις (many-counseled) 
- May not have its own entry

**Current Status**: Relies on morphological analysis to identify components

## Data Quality Issues

### 1. OCR Errors in Source Data
**Problem**: Some dictionary sources have OCR artifacts:
- Confused letters: ο/ρ, ι/ί
- Missing diacriticals

**Solution**: Manual fixes in extraction scripts where detected

### 2. Incomplete Morphological Data
**Problem**: Not all inflected forms are in Wiktionary:
- Rare forms
- Poetic variants
- Dialectical forms

**Solution**: Multiple fallback strategies in lookup

### 3. Homonyms
**Problem**: Same spelling, different words:
- βίος (life) vs βιός (bow)
- Different accents = different words

**Solution**: Preserve all accent marks for disambiguation

## Future Considerations

### 1. Expanding Coverage
- Add more dialectical variants
- Include Byzantine Greek forms
- Add Latin morphology

### 2. Improving Placeholders
- Use AI to generate better definitions for undefined terms
- Link to related words when no definition exists

### 3. Handling Phrases
- Multi-word expressions
- Idiomatic phrases
- Proverbs and quotes

### 4. Cross-References
- Better handling of "see also" references
- Variant spelling connections
- Etymology chains