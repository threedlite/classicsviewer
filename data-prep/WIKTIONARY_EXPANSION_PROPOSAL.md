# Wiktionary Expansion Proposal

## Current State
- Only 5 manually selected Wiktionary entries in database
- ~77% coverage on epic texts (Odyssey sample)
- Many Greek words have no dictionary entry at all

## Proposed Expansion

### Option 1: Targeted Extraction
Extract Wiktionary definitions for all unique Greek words in corpus that:
1. Appear in our texts (from word_forms table)
2. Have no lemma mapping
3. Have no LSJ dictionary entry
4. Exist in Wiktionary

**Estimated scope**: Thousands of entries
**Benefits**: Fill actual gaps in corpus coverage
**Approach**:
```python
1. Get list of missing words from database
2. Parse Wiktionary dump looking for these specific words
3. Extract and format definitions
4. Add to dictionary_entries with source='wiktionary'
```

### Option 2: Full Ancient Greek Extraction
Extract ALL Ancient Greek entries from Wiktionary:
- ~29,000 lemmas
- ~16,000 non-lemma forms

**Benefits**: Comprehensive coverage
**Drawbacks**: Large database increase, many unused entries

### Option 3: Lemma-Only Extraction
For words with lemma mappings but missing dictionary entries:
1. Identify lemmas that map to non-existent dictionary entries
2. Extract those specific lemmas from Wiktionary
3. Enables existing mappings to work

## Recommendation
**Option 1** - Targeted extraction for corpus words only
- Maximizes coverage improvement
- Minimizes database bloat
- Focuses on actual user needs
- Can be run incrementally

## Implementation Steps
1. Modify `extract_ancient_greek_definitions.py` to:
   - Query database for missing words
   - Extract only those from Wiktionary
   - Format consistently with LSJ style
   
2. Integration:
   - Run after main database build
   - Add to build_database.py workflow
   - Mark entries with source='wiktionary'

## Expected Results
- Coverage could improve from 77% to 85-90%
- Database size increase: ~10-20MB
- Better support for:
  - Proper names
  - Dialectal forms
  - Rare vocabulary
  - Technical terms