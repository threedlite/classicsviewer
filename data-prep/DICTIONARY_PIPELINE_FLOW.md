# Dictionary Pipeline Flow Diagram

## Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCE DATA FILES                             │
├─────────────────────┬────────────────────┬─────────────────────────┤
│  Cunliffe XML       │    LSJ XML Files   │  Wiktionary Data        │
│  (Homeric lexicon)  │  (Comprehensive)   │  (Morphology)           │
└──────────┬──────────┴─────────┬──────────┴──────────┬──────────────┘
           │                    │                     │
           ▼                    ▼                     ▼
┌──────────────────┐  ┌─────────────────┐  ┌────────────────────────┐
│extract_cunliffe_ │  │extract_lsj_     │  │extract_wiktionary_     │
│fixed.py          │  │fixed.py         │  │final.py                │
├──────────────────┤  ├─────────────────┤  ├────────────────────────┤
│- Parse XML       │  │- Parse XML      │  │- Load morphology JSON  │
│- Convert beta-   │  │- Handle nested  │  │- Simplify lemmas       │
│  code headwords  │  │  entries        │  │  (remove macrons)      │
│- Extract entries │  │- Process cross- │  │- Generate meaningful   │
│                  │  │  references     │  │  placeholders          │
└──────────┬───────┘  └────────┬────────┘  └───────────┬────────────┘
           │                   │                        │
           ▼                   ▼                        ▼
    cunliffe_extracted.json  lsj_extracted_fixed.json  wiktionary_extracted_final.json
           │                   │                        │
           └───────────────────┴────────────────────────┘
                               │
                               ▼
                 ┌─────────────────────────────────┐
                 │combine_dictionaries_to_lemma_   │
                 │map.py                           │
                 ├─────────────────────────────────┤
                 │- Merge all sources              │
                 │- Apply priority (C>L>W)         │
                 │- Create unified entries         │
                 │- Generate base mappings         │
                 │- Call variant generators        │
                 └─────────────┬───────────────────┘
                               │
                ┌──────────────┴───────────────────┐
                ▼                                  ▼
    combined_dictionary_entries.json    combined_lemma_mappings.json
                │                                  │
                │                                  ▼
                │                      ┌──────────────────────┐
                │                      │normalize_unicode.py  │
                │                      ├──────────────────────┤
                │                      │- Convert to NFC      │
                │                      │- Fix Unicode issues  │
                │                      └──────────┬───────────┘
                │                                  │
                │                                  ▼
                │                      combined_lemma_mappings_normalized.json
                │                                  │
                │                                  ▼
                │                      ┌──────────────────────────┐
                │                      │add_grave_accent_         │
                │                      │variants.py               │
                │                      ├──────────────────────────┤
                │                      │- Generate grave variants │
                │                      │  (ά → ὰ)                 │
                │                      └──────────┬───────────────┘
                │                                  │
                │                                  ▼
                │                      combined_lemma_mappings_with_graves.json
                │                                  │
                │                                  ▼
                │                      ┌──────────────────────────┐
                │                      │add_enclitic_variants.py  │
                │                      ├──────────────────────────┤
                │                      │- Create unaccented forms │
                │                      │  for particles           │
                │                      └──────────┬───────────────┘
                │                                  │
                │                                  ▼
                │                      combined_lemma_mappings_final.json
                │                                  │
                └──────────────────────────────────┤
                                                   │
                               ┌───────────────────▼──────────────────┐
                               │load_combined_dictionaries.py         │
                               ├──────────────────────────────────────┤
                               │- Create database tables              │
                               │- Load dictionary_entries             │
                               │- Load lemma_map with all variants   │
                               └──────────────────────────────────────┘
                                                   │
                                                   ▼
                                          SQLite Database Tables
                                       (dictionary_entries, lemma_map)
```

## Key Points

1. **Three Independent Extractors**: Each source has its own specialized extraction logic
2. **Unified Combination**: All sources merge into a single dictionary system
3. **Sequential Variant Generation**: Each variant script builds on the previous
4. **Automatic Pipeline**: Running `combine_dictionaries_to_lemma_map.py` triggers variant generation
5. **Database Integration**: `load_combined_dictionaries.py` orchestrates the entire process

## File Dependencies

- **Input Files**:
  - `cunliffe_lexicon.xml`
  - `greek-lsj-xml/*.xml`
  - `wiktionary-processing/ancient_greek_morphology_with_diacritics.json`
  - `wiktionary-processing/wiktionary_extraction_results/wiktionary_definitions_complete.json`

- **Intermediate Files**:
  - `cunliffe_extracted.json`
  - `lsj_extracted_fixed.json`
  - `wiktionary_extracted_final.json`
  - `combined_dictionary_entries.json`
  - `combined_lemma_mappings.json`
  - `combined_lemma_mappings_normalized.json`
  - `combined_lemma_mappings_with_graves.json`

- **Final Output**:
  - `combined_lemma_mappings_final.json`
  - Database tables: `dictionary_entries`, `lemma_map`