# Analysis: Splitting Greek and Latin into Separate Build Modules

## Current State

`create_perseus_database.py` is a 508 KB / 11,064-line monolithic script that handles **both** Greek and Latin text processing. By contrast, Sanskrit (2,608 lines) and Chinese (990 lines) each have their own self-contained build directory.

### Current directory layout
```
data-prep/
  create_perseus_database.py          # 11,064 lines - Greek + Latin + First1K + PTA
  build_modules/
    load_combined_dictionaries.py     # Greek + Latin dictionary loading
    load_whitakers_latin.py           # Latin-only: Whitaker's Words
    normalization_utils.py            # Greek + Latin normalization
    extract_lsj_fixed.py             # Greek-only: LSJ dictionary
    extract_cunliffe_new.py          # Greek-only: Cunliffe dictionary
    combine_dictionaries_to_lemma_map.py
    add_enclitic_variants.py         # Greek-only
    add_grave_accent_variants.py     # Greek-only
    extract_perseus_treebank_lemmas.py
    generate_interlinear/
      generate_interlinear.py         # Greek interlinear (2,042 lines)
      generate_latin_interlinear.py   # Latin interlinear (538 lines)
      ui_dictionary_lookup.py         # Greek dictionary lookup
      latin_dictionary_lookup.py      # Latin dictionary lookup
      glaux_loader.py                 # Greek treebank
      treebank_loader.py              # Greek treebank
      interlinear_list.py             # Greek work list
      latin_interlinear_list.py       # Latin work list
  wiktionary-processing/              # Greek-only morphology extraction
    extract_all_greek_pages.py
    extract_ancient_greek_declensions.py
    extract_ancient_greek_conjugations.py
    combine_all_ancient_greek_morphology.py
    ...

sanskrit/                              # Self-contained module
  create_sanskrit_database_interlinear.py
  run_build.sh
  batch_generate_interlinear.py
  generate_sanskrit_interlinear.py
  ...

chinese/                               # Self-contained module
  create_chinese_database.py
  run_build.sh
  ...
```

## Why Split?

### 1. Maintainability
The 11K-line monolith is difficult to navigate. Changes to Latin parsing risk breaking Greek processing and vice versa. The Bekker/Stephanus alignment fix required understanding the entire file, when it only affects Greek philosophical texts.

### 2. Independent Build Cycles
Greek interlinear takes ~6 hours. Latin interlinear takes ~17 seconds. Currently both depend on the same database build. With separate modules, Latin could be rebuilt in minutes without waiting for Greek.

### 3. Testability
Individual work testing (e.g., testing just Aristotle alignment) currently requires the full build infrastructure. Separate modules could have targeted test modes.

### 4. Consistency
Sanskrit and Chinese already follow a clean per-language pattern. Greek and Latin should too.

### 5. Cognitive Load
A developer working on Latin prose parsing shouldn't need to understand Greek Bekker numbering, and vice versa.

## Proposed Structure

```
greek/
  create_greek_database.py            # Greek text processing + Perseus + First1K
  run_build.sh                        # Build wrapper (like Sanskrit)
  GREEK_SAMPLE.csv                    # Sample author list
  GREEK_FULL.csv                      # Full author list  
  GREEK_EXTENDED.csv                  # Extended author list (includes First1K)
  build_modules/
    greek_lemmatizer.py               # GreekLemmatizer class
    greek_dictionary.py               # LSJ + Cunliffe + Wiktionary loading
    greek_morphology.py               # Declensions, conjugations, accents
    interlinear/
      generate_interlinear.py         # Greek interlinear generator
      ui_dictionary_lookup.py         # Dictionary lookup for interlinear
      glaux_loader.py                 # Glaux treebank data
      treebank_loader.py              # Perseus treebank data
      run_interlinear_no_sleep.sh
      INTERLINEAR_ALL_GREEK_WITH_IDS.csv
  wiktionary-processing/              # Move here from data-prep/
    extract_all_greek_pages.py
    extract_ancient_greek_declensions.py
    ...

latin/
  create_latin_database.py            # Latin text processing
  run_build.sh
  LATIN_SAMPLE.csv
  LATIN_FULL.csv
  build_modules/
    latin_lemmatizer.py               # Latin-specific lemmatization
    latin_dictionary.py               # Lewis & Short + Whitaker's Words
    interlinear/
      generate_latin_interlinear.py
      latin_dictionary_lookup.py
      run_latin_interlinear_no_sleep.sh
      INTERLINEAR_ALL_LATIN_WITH_IDS.csv

shared/                                # Minimal - only what MUST be identical
  database_schema.py                   # Room-compatible schema (must match exactly)
  merge_database.py                    # Merge language databases into final assembly
```

## What Goes Where

### Design Principle: Minimize Shared Code
Shared code between Greek and Latin is a testing liability. A change to shared translation alignment for Greek could silently break Latin. Each module should be as self-contained as possible, like Sanskrit and Chinese already are. 

**Only share what MUST be identical** - the database schema (Room compatibility) and the merge script. Everything else gets copied into each module and evolves independently. Some code duplication is acceptable and preferable to coupling.

### Code currently in create_perseus_database.py (11,064 lines)

| Function Group | Lines (approx) | Destination |
|---|---|---|
| XML tag helpers (`is_p_tag`, `is_div_tag`, etc.) | ~200 | Copy into both `greek/` and `latin/` |
| `parse_xml_with_entity_resolver()` | ~80 | Copy into both (same Perseus XML format) |
| `get_text_content()` | ~100 | Copy into both (diverge as needed) |
| `extract_translation_segments()` | ~700 | Copy into both (Greek version has Bekker/Stephanus, Latin version is simpler) |
| `process_translations()` | ~800 | Copy into both (Greek has aligned/ + First1K, Latin is simpler) |
| `create_translation_lookup_table()` | ~300 | Copy into both (Greek has `create_philosophical_reference_mappings`, Latin doesn't) |
| `create_philosophical_reference_mappings()` | ~200 | `greek/` only |
| `extract_milestone_line_ranges()` | ~100 | `greek/` only |
| `process_prose_with_books()` | ~500 | Copy into both (Greek has Bekker/Stephanus/chapter.section, Latin has abbreviation handling) |
| `process_prose_text()` | ~400 | Copy into both |
| `process_verse_text()` | ~200 | Copy into both |
| `process_drama_text()` | ~200 | Copy into both |
| `GreekLemmatizer` class | ~300 | `greek/` only |
| `combine_all_ancient_greek_morphology()` | ~100 | `greek/` only |
| `load_combined_dictionaries()` (Greek parts) | ~200 | `greek/` only |
| `load_combined_dictionaries()` (Latin parts) | ~100 | `latin/` only |
| `process_perseus_author()` | ~400 | Copy into both (same general structure, language-specific details diverge) |
| `process_first1k_work()` | ~600 | `greek/` only |
| Author/work CSV filtering | ~200 | Each module has own CSV lists |
| Database schema creation | ~300 | `shared/database_schema.py` (MUST be identical - Room compatibility) |
| Quality report generation | ~400 | Copy into both (lightweight, no coupling risk) |
| Interlinear import | ~200 | Each module imports its own interlinear |
| Main entry point / CLI | ~300 | Each module has own `if __name__` |
| XML pattern analysis | ~200 | Copy into both |
| Aligned translation processing | ~300 | Copy into both (Greek has more aligned works) |
| Bekker/Stephanus handling | ~400 | `greek/` only |
| Chapter.section handling | ~200 | Copy into both |

### Greek-Only Concerns
- Bekker numbering (Aristotle)
- Stephanus pagination (Plato)
- First1K corpus parsing (`process_first1k_work`)
- PTA corpus parsing
- **Wiktionary extraction pipeline** (entirely Greek-specific):
  - Source: English Wiktionary XML dump (1.4GB bz2) → one-time extraction to 46MB JSON cache
  - Per-build: extracts conjugations, declensions, inflection mappings, definitions (~55MB combined morphology)
  - Combines with LSJ + Cunliffe dictionaries
  - Generates accent/enclitic variants
  - ~3-4 minutes per build
- OGA (Open Greek Alphabet) lemma extraction
- Glaux + Perseus treebank integration
- Greek interlinear generation (~6 hours)

### Latin-Only Concerns
- **Whitaker's Words** - direct load from `DICTLINE.GEN` + `INFLECTS.LAT` data files (no Wiktionary, no extraction pipeline)
- Latin interlinear generation (~17 seconds)
- Latin-specific sentence splitting (abbreviation handling: M., L., Cn., etc.)
- No milestone-based numbering systems
- No First1K/PTA corpus

### Dictionary Pipeline is a Clean Split
The Greek and Latin dictionary pipelines share **zero code**. Greek uses a 7-step Wiktionary extraction + LSJ + Cunliffe pipeline. Latin uses a single-step Whitaker's Words load. This makes the module split straightforward for dictionaries.

### Truly Shared (must be identical)
- Database schema (must match Room entities exactly) → `shared/database_schema.py`
- Database merge logic → `shared/merge_database.py`

### Duplicated Between Modules (copied, then diverge independently)
- TEI-XML parsing (same format, but Greek has more edge cases)
- Entity resolver for malformed XML
- Translation segment extraction (Greek version much more complex)
- Prose/verse/drama text type detection
- Sentence splitting (different rules per language)
- Translation lookup table creation
- Quality report generation
- Database compression
- Aligned translation import

This duplication is intentional. When Greek needs a new alignment fix (like Bekker/Stephanus), it changes only in `greek/`. Latin is unaffected and untouched. The alternative - shared code with language callbacks - creates fragile coupling where every Greek fix needs Latin regression testing.

## Migration Strategy

### Phase 0: Build verification tooling (prerequisite)
Before any code moves, create a verification script that can diff the monolith output against module output table-by-table. "Byte-for-byte identical (modulo row ordering)" is not a testable claim — SQLite row ordering is non-deterministic.

1. Create `verify_module_output.py` that:
   - Dumps each table from two databases sorted by primary key
   - Compares row counts, content hashes per table, and foreign key integrity
   - Reports per-table pass/fail with diffs for failures
2. Run against the current monolith to establish a baseline
3. Every subsequent phase uses this script as its acceptance gate

This script is small (~200 lines) and pays for itself immediately — without it, "verify" steps in later phases are manual and error-prone.

### Phase 1: Create Latin module first (easiest, lowest risk)
Latin is the simpler language to extract - no Bekker/Stephanus, no First1K/PTA, fewer aligned translations, simpler dictionary (Lewis & Short + Whitaker's).
1. Create `latin/` directory structure
2. Copy the relevant code from `create_perseus_database.py` into `latin/create_latin_database.py`
3. Strip out all Greek-specific code (Bekker, Stephanus, First1K, PTA, Greek lemmatizer, Wiktionary)
4. Copy `shared/database_schema.py` for schema creation
5. Move Latin interlinear to `latin/build_modules/interlinear/`
6. Move Whitaker's Words, Lewis & Short loading into `latin/build_modules/`
7. Create `latin/run_build.sh` with sample/full modes
8. Split `aligned/` directory: move Latin aligned translations (`phi*`) to `latin/aligned/`
9. **Verify**: Run `verify_module_output.py` — Latin tables in `latin/latin_texts.db` (merged into empty schema) match current build exactly

### Phase 2: Create Greek module (larger, more complex)
1. Create `greek/` directory structure
2. Copy the relevant code into `greek/create_greek_database.py`
3. Strip out Latin-specific code
4. Keep all Greek-specific code: Bekker/Stephanus, First1K, PTA, GreekLemmatizer, Wiktionary pipeline
5. Move Wiktionary processing to `greek/wiktionary-processing/`
6. Move Greek interlinear to `greek/build_modules/interlinear/`
7. Move Greek aligned translations (`tlg*`) to `greek/aligned/`
8. Create `greek/run_build.sh` with sample/full/extended modes
9. **Verify**: Run `verify_module_output.py` — Greek tables in `greek/greek_texts.db` match current build exactly

### Phase 3: Assembly script replaces monolith
1. Create `assemble_database.py` (~500 lines) alongside the existing monolith
2. Creates empty schema, merges all language `.db` files, builds cross-language indexes
3. Build modes control which modules to include (see "Build Mode Mapping" below)
4. Handle iOS build mode: assembly accepts an `ios` flag that merges only the iOS-subset language DBs and copies output to `ios/ClassicsViewer/Resources/`
5. **Keep `create_perseus_database.py` fully functional** — it remains the fallback until Phase 4 is verified
6. **Verify**: Run `verify_module_output.py` against both monolith and assembled output — all tables match

### Phase 4: Retire the monolith (low risk)
1. `create_perseus_database.py` replaced by `assemble_database.py`
2. It does NOT build any language — it only:
   - Creates empty database with schema (`shared/database_schema.py`)
   - Merges `greek/greek_texts.db` using `merge_database.py`
   - Merges `latin/latin_texts.db` using `merge_database.py`
   - Merges `sanskrit/sanskrit_texts.db` using `merge_database.py`
   - Merges `chinese/chinese_texts.db`, `coptic/coptic_texts.db`, etc.
   - Builds translation_lookup table (across all languages)
   - Generates quality report
   - Compresses to ZIP
   - Copies to app assets
3. Build modes (`sample`, `full`, `extended`, `ios`) control which language DBs to merge
4. Each language module is built independently before assembly
5. Old monolith archived to `archive/create_perseus_database_monolith.py` for reference
6. **Verify**: Final assembled database matches monolith output via `verify_module_output.py`

### Rollback Plan
The monolith (`create_perseus_database.py`) stays fully functional and runnable through Phase 3. If Phase 2 (Greek extraction) goes badly mid-flight:
- Fall back to the monolith for production builds immediately
- Debug the Greek module at leisure without blocking releases
- The monolith is only retired in Phase 4, after the assembled output is verified identical

### Build Mode Mapping
Each assembly mode maps to specific module build modes:

| Assembly Mode | Greek Module | Latin Module | Sanskrit | Chinese | Others |
|---|---|---|---|---|---|
| `sample` | `greek/run_build.sh sample` | `latin/run_build.sh sample` | `sanskrit/run_build.sh sample` | skip | skip |
| `full` | `greek/run_build.sh full` | `latin/run_build.sh full` | `sanskrit/run_build.sh full` | `chinese/run_build.sh` | all |
| `extended` | `greek/run_build.sh extended` | `latin/run_build.sh full` | `sanskrit/run_build.sh full` | `chinese/run_build.sh` | all |
| `ios` | `greek/run_build.sh ios` | skip | skip | skip | skip |

The assembly script orchestrates these calls automatically — the user runs one command (`assemble_database.py extended`) and each module is built with the correct mode.

## Risks and Mitigations

### Risk: Schema drift between modules
**Mitigation**: `shared/database_schema.py` is the single source of truth for table creation. All language modules import it. This is the ONE piece of shared code that must stay shared.

### Risk: Code duplication leads to divergent bugs
**Mitigation**: This is actually the point. If Greek's `extract_translation_segments` has a bug, it only affects Greek. Latin's copy is independent. The current monolith has the opposite problem: fixing Bekker alignment for Aristotle required touching code that also handles Cicero. Duplication is cheaper than coupling for code this complex.

### Risk: Bug fix in one module not propagated to other
**Mitigation**: If a bug is found in shared logic (e.g., XML entity resolver), it needs manual propagation. This is the tradeoff - but it's the same tradeoff Sanskrit and Chinese already make. Their XML parsing doesn't share code with Greek/Latin either.

### Risk: Build time increase from separate assembly step
**Mitigation**: The merge step using `merge_database.py` takes <1 minute per language. Total assembly overhead: ~5 minutes for all 15 languages.

### Risk: Database merge complexity
**Mitigation**: `merge_database.py` already handles AUTOINCREMENT ID remapping, foreign key fixup, and all table types. It's battle-tested from merging Sanskrit, Chinese, Coptic, and 10 other languages today.

### Risk: Regressions during multi-phase migration
**Mitigation**: Each module's `run_build.sh` supports a `test` mode (like Sanskrit already does) that builds a minimal database in ~1-2 minutes. Smoke test checklist per module:
1. `run_build.sh test` completes without errors
2. Output `.db` passes `verify_module_output.py` against monolith baseline (for the subset of works built)
3. Assembled database loads in the app without schema crashes
4. Translation lookup works for at least one work per language

This is not full CI — it's a manual checklist run before merging each phase. Full CI can be added later if the project grows contributors.

## Critical Details Not Addressed Above

### 1. Single Database Architecture
The app loads ONE `perseus_texts.db`. ALL languages are merged into this single database. Currently Greek/Latin is the "base" database and other languages merge into it. In the new architecture:
- Greek and Latin become modules just like Sanskrit and Chinese
- The main build script becomes **assembly-only**: creates empty schema, then merges all language DBs via `merge_database.py`
- Each language module produces its own standalone `.db` (e.g., `greek_texts.db`, `latin_texts.db`)
- The assembly step merges them all, builds the cross-language translation_lookup table, generates quality reports, and compresses
- This is cleaner than the current approach where Greek/Latin is special-cased as the "base"

### 2. The `aligned/` Directory is Mixed Greek and Latin
Contains 41 Greek and 2 Latin aligned translation files. Split during migration: Greek aligned files (`tlg*`) move to `greek/aligned/`, Latin aligned files (`phi*`) move to `latin/aligned/`. This keeps each module fully self-contained with no shared data directories.

### 3. SAMPLE_AUTHORS.csv Mixes Greek and Latin
The sample CSV has both Greek (Aeschylus, Aristotle, Euripides...) and Latin (Horace, Virgil) authors. Need separate CSVs per module, or the assembly step filters them.

### 4. OGA Lemma Extraction is Greek-Only
`insert_oga_lemmas()` processes the Open Greek and Latin Alphabet corpus. Despite the name, it currently only extracts Greek lemmas. This goes in the Greek module.

### 5. Translation Lookup Table: Module-Level vs. Assembly-Level
The `translation_lookup` table maps every text line to its translation segments. This mapping is per-book and per-language — a Greek line never maps to a Latin translation segment. Therefore, each module builds its own `translation_lookup` entries during its database creation. The assembly step simply merges these entries (with ID remapping) like any other table. No cross-language logic is needed.

### 6. Dictionary Tables Span Both Languages
The `dictionary_entries` and `lemma_map` tables contain BOTH Greek (LSJ, Cunliffe, Wiktionary) and Latin (Lewis & Short, Whitaker's Words) data. If built separately, each module builds its own dictionary tables and the merge step combines them. **Not a problem**: `merge_database.py` already handles AUTOINCREMENT ID remapping and foreign key fixup (e.g., `translation_lookup.segment_id`). This is the same mechanism used for Sanskrit, Chinese, and all other language merges today.

### 7. The `words` and `text_lines` Tables Have No Language Column
Distinguishing Greek vs Latin rows in the merged database relies on joining through `books → works → authors` (which has a `language` column). The merge step must preserve referential integrity across all these tables.

### 8. iOS Build Mode
There's an `ios` build mode that creates a smaller database and copies it to `ios/ClassicsViewer/Resources/`. This is handled at the assembly level: `assemble_database.py ios` builds only the Greek module in `ios` mode (using `IOS_SAMPLE_AUTHORS.csv`), skips Latin and other languages, and copies the output to the iOS resources directory. The Greek module needs an `ios` build mode that uses the iOS-specific author list. See the Build Mode Mapping table in Phase 4.

### 9. First1K and PTA Are Greek-Only but Stored Globally
`data-sources/First1KGreek/` and `data-sources/PTA/` are in the shared data-sources directory. The Greek module needs to reference these paths. The Latin module ignores them entirely.

### 10. Interlinear Output is Shared
Both Greek and Latin interlinear files go to `data-sources/classicsviewer_interlinear/`. The Greek module generates ~2049 files there, Latin generates ~230. The import step reads from this shared location. Could split into `greek_interlinear/` and `latin_interlinear/`, or keep shared with each module importing its own files.

### 11. `process_prose_with_books()` Has Language-Specific Branches
This core function handles both Greek and Latin but has `if language == 'greek'` branches for:
- Sentence splitting (Greek uses `·` and `;`, Latin handles abbreviations)
- Milestone tracking (Bekker/Stephanus only for Greek)
- `[chapter.section]` embedding (both, but Greek has special Plato/Aristotle exclusions)

Putting this in `shared/` requires passing language-specific callbacks or keeping the language parameter.

### 12. Translation Alignment Code Has Greek-Specific Logic Embedded
`extract_translation_segments()` detects Bekker/Stephanus based on `author_id == 'tlg0086'` or `'tlg0059'`. This Greek-specific logic is deeply intertwined with the general alignment code. Options:
- Keep in `shared/` with the Greek-specific checks (pragmatic but messy)
- Pass a "milestone config" from the calling module (cleaner but more refactoring)

### 13. External Database Merge Uses `merge_database.py`
There's a separate `data-prep/merge_database.py` script (not inside `create_perseus_database.py`) that handles the actual SQLite merge mechanics. This would become part of the assembly step.

### 14. Build Modes Interact
Current modes: `sample`, `full`, `extended`, `ios`, plus custom CSV. Each mode controls:
- Which authors to include (CSV filtering)
- Which external databases to merge
- Where to copy the final ZIP
- Whether to include First1K/PTA (extended only)

Each module would need its own mode handling, and the assembly step combines them.

## Interlinear Generation in the New Setup

### Current Pipeline (requires 2 full builds)
```
1. Build extended DB (35 min) → perseus_texts_extended.db (Greek+Latin+all)
2. Run Greek interlinear (6 hrs) - reads text_lines + dictionary from assembled DB
3. Run Latin interlinear (17 sec) - reads from same assembled DB
4. Rebuild extended DB (35 min) → reimports interlinear XML files
```
The interlinear generators need both `text_lines` (the source text) and `dictionary_entries`/`lemma_map` (for glossing). Currently they read from the fully assembled database.

### New Pipeline (each module self-contained)
```
1. Greek module builds greek_texts.db (includes Greek text + Greek dictionary)
2. Greek interlinear runs against greek_texts.db (has everything it needs)
3. Greek module rebuilds with interlinear imported → final greek_texts.db

4. Latin module builds latin_texts.db (includes Latin text + Latin dictionary)
5. Latin interlinear runs against latin_texts.db
6. Latin module rebuilds with interlinear imported → final latin_texts.db

7. Assembly merges all final .db files → perseus_texts.db
```

### Why This Works
Each language module's database already contains:
- `text_lines` - the source text to generate interlinear for
- `dictionary_entries` - the dictionary for glossing (LSJ for Greek, Lewis & Short for Latin)
- `lemma_map` - word form → lemma mappings
- `morphology` - morphological data

The interlinear generator only needs text + dictionary from ONE language. It never needs to look up Greek words in the Latin dictionary or vice versa. So each module can run its own interlinear pipeline independently.

### Benefits
- **Greek interlinear (6 hrs) and Latin interlinear (17 sec) run independently** - no waiting
- **No double-build** - each module builds once, generates interlinear, rebuilds once, done
- **Interlinear scripts live inside the module** - `greek/build_modules/interlinear/`, `latin/build_modules/interlinear/`
- **Sanskrit already works this way** - interlinear is generated during `sanskrit/run_build.sh`

### Module Build Sequence
```bash
# Each module: build → interlinear → rebuild (self-contained)
cd greek && ./run_build.sh extended    # builds DB, generates interlinear, reimports
cd latin && ./run_build.sh full        # same pattern, but takes 2 minutes total
cd sanskrit && ./run_build.sh full     # already works this way

# Assembly: merge all modules
cd data-prep && python3 assemble_database.py extended
```

## Build Time Comparison

| Current | Proposed |
|---|---|
| Extended: 35 min (Greek+Latin+First1K) | Greek extended: ~30 min |
| Full: 7 min (Greek+Latin) | Latin full: ~2 min |
| Sample: 5 min (Greek+Latin) | Greek full: ~5 min |
| Greek interlinear: 6 hours | (unchanged) |
| Latin interlinear: 17 seconds | (unchanged) |
| **Total pipeline**: ~7 hours | **Total pipeline**: ~6.5 hours |

The main benefit isn't speed but **independence**: Latin can be rebuilt in 2 minutes without touching Greek.

## Line Count Estimates

| Module | Estimated Lines | Notes |
|---|---|---|
| `shared/database_schema.py` | ~300 | Schema creation only (Room compatibility) |
| `shared/merge_database.py` | ~200 | Already exists, minor updates |
| `greek/create_greek_database.py` | ~7,000 | Self-contained: XML parsing, text processing, translations, Bekker/Stephanus, First1K, PTA, lemmatizer, dictionary, interlinear import, quality report |
| `latin/create_latin_database.py` | ~4,000 | Self-contained: XML parsing, text processing, translations, dictionary, interlinear import, quality report |
| `assemble_database.py` | ~500 | Merge all language DBs, build indexes, compress |
| `verify_module_output.py` | ~200 | Table-by-table comparison tool (Phase 0) |
| **Total** | **~12,200** | Up from 11,064 due to intentional duplication + verification tooling |

The total line count goes up slightly because shared functions (XML parsing, text processing, translation alignment) are duplicated. This is the correct tradeoff: ~1,000 extra lines of duplicated code eliminates the coupling that caused the Bekker/Stephanus regression.
