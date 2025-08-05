# Wiktionary Integration for Classics Viewer

## Overview
This document describes the integration of Wiktionary data to supplement the LSJ dictionary for Ancient Greek words that appear in classical texts but are missing from LSJ.

## Motivation
The Liddell-Scott-Jones (LSJ) dictionary, while comprehensive, has some gaps:
- Dual forms (e.g., σφωέ "they two")
- Some proper names (e.g., Ἀτρεύς)
- Ionic/Epic variant forms (e.g., νοῦσος for νόσος)
- Rare or specialized vocabulary

These gaps prevented dictionary lookups for legitimate Greek words in the texts.

## Implementation Approach

### Single Unified Dictionary
Rather than maintaining separate dictionaries, we chose to integrate Wiktionary entries directly into the existing `dictionary_entries` table:

```sql
CREATE TABLE dictionary_entries (
    id INTEGER PRIMARY KEY,
    headword TEXT NOT NULL,
    headword_normalized TEXT NOT NULL,
    language TEXT NOT NULL,
    entry_xml TEXT,
    entry_html TEXT,
    entry_plain TEXT,
    source TEXT  -- 'LSJ' or 'wiktionary'
);
```

**Benefits**:
- No changes needed to Android app UI
- Single lookup for all dictionary entries
- Consistent user experience
- Easy to identify source if needed

### Current Wiktionary Supplements

Five carefully selected entries have been added to fill critical gaps:

1. **σφωέ** - Epic dual pronoun "they two"
   - Essential for understanding dual forms
   - Common in epic poetry

2. **Ἀτρεύς** - Atreus, father of Agamemnon
   - Enables patronymic mappings (Ἀτρεΐδης → Ἀτρεύς)
   - Important mythological figure

3. **πρῶτα** - Adverbial use of πρῶτος "first, at first"
   - Common in epic narrative
   - Distinct from simple neuter plural

4. **νοῦσος** - Ionic form of νόσος "disease"
   - Important dialectal variant
   - Common in epic texts

5. **ἑλώριον** - "prey, spoil" 
   - Poetic/epic vocabulary
   - Important thematic word

### Build Process Integration

The Wiktionary supplements are added automatically during the build:

```python
# In build_database.py
1. Run main database creation (LSJ entries)
2. Add Wiktionary supplements
3. Result: unified dictionary with 28,652 entries
```

### Format and Styling

Wiktionary entries are formatted to match LSJ style:
- Clear, concise definitions
- Part of speech indicated
- Example citations where relevant
- Source attribution: "[From Wiktionary]"

## Results

### Coverage Improvement
- Sample epic text (Odyssey 100 lines): 77.1% coverage
- Key missing words now have definitions
- Patronymic patterns now work (e.g., Ἀτρεΐδης finds Ἀτρεύς)
- Dual forms and dialectal variants supported

### Database Impact
- Added only 5 entries (minimal size increase)
- No performance impact
- Maintains mobile-friendly database size

## Future Expansion

### Automated Extraction
The infrastructure supports larger-scale Wiktionary extraction:
- `extract_ancient_greek_definitions.py` - framework for parsing Wiktionary XML
- Could extract hundreds more entries for words in texts
- Would require curation to ensure quality

### Potential Additions
Priority candidates for future Wiktionary additions:
1. More proper names appearing in texts
2. Additional dual and rare forms
3. Dialectal variants (Ionic, Aeolic, Doric)
4. Technical/specialized vocabulary

### Quality Considerations
When expanding, maintain quality by:
- Focusing on words that actually appear in the corpus
- Preferring concise, clear definitions
- Verifying accuracy against scholarly sources
- Keeping entries appropriately sized for mobile

## Technical Details

### Files
- `wiktionary-processing/add_wiktionary_supplements.py` - Adds curated entries
- `wiktionary-processing/extract_ancient_greek_definitions.py` - Framework for automated extraction
- Entries stored in same `dictionary_entries` table with `source='wiktionary'`

### Android App Compatibility
No changes needed to the app:
- `DictionaryActivity` queries `dictionary_entries` as before
- Source field available if UI wants to indicate origin
- Seamless user experience maintained