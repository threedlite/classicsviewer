 Plan to Add Strong's Exhaustive Concordance (Greek Dictionary)

  Based on my analysis of the codebase and Strong's Concordance structure on Wikisource,
  here's a comprehensive implementation plan:

  ---
  Overview

  Goal: Integrate Strong's Greek dictionary (entries G1-G5624) from Wikisource into the
  Classics Viewer app's existing dictionary system.

  Data Source: https://en.wikisource.org/wiki/Strong%27s_Exhaustive_Concordance (Greek
  sections G0-G5)

  Integration Point: The existing dictionary_entries and lemma_map tables in the Perseus
  database.

  ---
  1. Data Structure Analysis

  Strong's Entry Format (from Wikisource):

  G[number] Greek_word (transliteration): etymology; definition

  Example:
  - G1000 βολή (bol-ay'): from βάλλω; a throw (as a measure of distance): cast.
  - G1080 γεννάω (ghen-nah'-o): from γένος; to procreate: bear, beget, be born, bring forth,
  conceive

  Entry Components:

  1. Strong's number (G1-G5624)
  2. Greek headword (Unicode Greek text)
  3. Transliteration (pronunciation guide)
  4. Etymology (derivation, cross-references)
  5. Definition (theological/semantic meanings)

  Current Database Schema (No Changes Needed):

  CREATE TABLE dictionary_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      headword TEXT NOT NULL,
      headword_normalized_ultra TEXT,
      language TEXT NOT NULL,            -- Will be 'greek'
      entry_xml TEXT,
      entry_html TEXT,
      entry_plain TEXT,
      source TEXT                         -- Will be 'strongs'
  );

  CREATE TABLE lemma_map (
      word_form TEXT NOT NULL,
      word_form_normalized_ultra TEXT,
      lemma TEXT NOT NULL,
      confidence REAL NOT NULL DEFAULT 1.0,
      source TEXT,                        -- Will be 'strongs'
      morph_info TEXT
  );

  No schema changes required - existing structure supports multiple sources per headword.

  ---
  2. Implementation Strategy

  Phase 1: Wikisource Scraper (New Script)

  File: data-prep/build_modules/extract_strongs_greek.py

  Functionality:
  1. Download and parse 6 Wikisource pages (G0 through G5)
    - G0: entries 1-999
    - G1: entries 1000-1999
    - G2: entries 2000-2999
    - G3: entries 3000-3999
    - G4: entries 4000-4999
    - G5: entries 5000-5624
  2. For each entry, extract:
    - Strong's number
    - Greek headword
    - Transliteration
    - Full entry text (etymology + definition)
  3. Parse HTML structure to extract entries (likely using BeautifulSoup or regex)
  4. Output to JSON format matching existing pattern:
  {
    "βολή": {
      "strongs_number": "G1000",
      "transliteration": "bol-ay'",
      "definition": "from βάλλω; a throw (as a measure of distance): cast",
      "inflected_forms": []
    }
  }

  Challenges:
  - HTML parsing consistency across pages
  - Handling cross-references (links to other entries)
  - Unicode Greek text extraction
  - Preserving diacritics and accents

  ---
  Phase 2: Integration into Build Pipeline

  File: data-prep/build_modules/quick_combine_minimal_fixed.py

  Modifications:
  1. Add Strong's loading section after Wiktionary:
  # Process Strong's Concordance
  print("Processing Strong's Concordance...")
  strongs_file = Path("extract_strongs_greek.json")
  if strongs_file.exists():
      with open(strongs_file, 'r', encoding='utf-8') as f:
          strongs_data = json.load(f)
      print(f"Loaded {len(strongs_data)} Strong's entries")

      for headword, data in strongs_data.items():
          # Create enhanced entry with Strong's number
          definition = data["definition"]
          strongs_num = data.get("strongs_number", "")
          transliteration = data.get("transliteration", "")

          # Format entry with Strong's metadata
          entry_plain = f"[{strongs_num}] {transliteration}: {definition}"
          entry_html = f"<div class='strongs'><strong>{strongs_num}</strong> 
  <em>{transliteration}</em>: {definition}</div>"

          entry_key = (headword, "strongs")
          if entry_key not in seen_entries:
              seen_entries.add(entry_key)
              dictionary_entries_list.append({
                  "headword": headword,
                  "language": "greek",
                  "entry_plain": entry_plain,
                  "entry_html": entry_html,
                  "source": "strongs"
              })

          # Add self-mapping
          mapping_key = (headword, headword)
          if mapping_key not in seen_mappings:
              seen_mappings.add(mapping_key)
              lemma_mappings.append({
                  "word_form": headword,
                  "lemma": headword,
                  "confidence": 1.0,
                  "source": "strongs",
                  "morph_info": f"Strong's {strongs_num}"
              })

  2. Add extraction call in pipeline:
  File: data-prep/build_modules/load_combined_dictionaries.py

  Add to dictionary extraction scripts list (~line 71):
  dictionary_scripts = [
      ("extract_cunliffe_new.py", "Cunliffe dictionary", 300),
      ("extract_lsj_fixed.py", "LSJ dictionary", 300),
      ("extract_wiktionary_final.py", "Wiktionary dictionary entries", 600),
      ("extract_strongs_greek.py", "Strong's Concordance Greek dictionary", 300)  # NEW
  ]

  ---
  Phase 3: Testing & Validation

  Create test script: data-prep/build_modules/test_strongs_extraction.py
  - Verify all 5,624 entries are extracted
  - Check for parsing errors
  - Validate Greek Unicode integrity
  - Test cross-reference handling

  Integration test:
  1. Run sample database build with Strong's included
  2. Deploy to test device
  3. Verify:
    - Strong's entries appear in dictionary lookups
    - Multiple sources shown per word (LSJ + Wiktionary + Strong's)
    - Greek text displays correctly
    - No schema validation errors

  ---
  3. Technical Specifications

  Dependencies (Already Available):

  - requests or urllib for HTTP fetching
  - BeautifulSoup4 for HTML parsing (may need to add to venv)
  - json for data serialization
  - Existing normalization utilities for Greek text

  Output Format:

  File: data-prep/build_modules/extract_strongs_greek.json
  {
    "ἀγαπάω": {
      "strongs_number": "G25",
      "transliteration": "ag-ap-ah'-o",
      "definition": "perhaps from agan (much); to love (in a social or moral sense)",
      "inflected_forms": []
    },
    "ἁγιός": {
      "strongs_number": "G40",
      "transliteration": "hag'-ee-os",
      "definition": "from hagos (an awful thing); sacred (physically, pure, morally 
  blameless)",
      "inflected_forms": []
    }
  }

  Entry Rendering in App:

  Dictionary entries will show:
  - [G25] ag-ap-ah'-o: perhaps from agan (much); to love (in a social or moral sense)
  - Source tag: "Strong's Concordance"

  ---
  4. Implementation Roadmap

  Milestone 1: Scraper Development (2-4 hours)

  - Create extract_strongs_greek.py
  - Implement Wikisource page fetching
  - Parse entry structure with regex/BeautifulSoup
  - Extract all 5,624 entries
  - Write to JSON output
  - Handle edge cases (cross-references, special formatting)

  Milestone 2: Pipeline Integration (1-2 hours)

  - Add extraction call to load_combined_dictionaries.py
  - Modify quick_combine_minimal_fixed.py to process Strong's data
  - Format entries with Strong's number and transliteration
  - Add lemma mappings with confidence scores

  Milestone 3: Testing (1-2 hours)

  - Create test script for extraction validation
  - Build sample database with Strong's included
  - Deploy to test device
  - Verify dictionary lookups show Strong's entries
  - Test with Biblical Greek vocabulary
  - Document any issues/limitations

  Milestone 4: Documentation (30 mins)

  - Update CLAUDE.md with Strong's Concordance information
  - Document data source and licensing
  - Add to BUILD_INSTRUCTIONS.md

  ---
  5. Considerations & Risks

  Data Quality:

  - Concern: Strong's is biblical/Koine Greek focused, may not cover classical authors well
  - Mitigation: It complements LSJ (classical) and Wiktionary (comprehensive) - users get all
   three

  Licensing:

  - Strong's Concordance is public domain (1890s publication)
  - Wikisource provides CC-licensed transcriptions
  - Result: Safe to include

  Maintenance:

  - Wikisource structure could change
  - Mitigation: Cache extracted data; scraper only runs during database builds
  - Add error handling for HTTP failures

  Performance:

  - Adds ~5,624 dictionary entries
  - Minimal impact (LSJ has ~110k entries, Wiktionary ~48k)
  - No performance concerns

  User Experience:

  - Benefit: Biblical Greek students get specialized definitions
  - Display: Show source tag so users know it's from Strong's
  - Priority: Lower confidence than LSJ/Cunliffe for classical texts

  ---
  6. Success Criteria

  ✅ All 5,624 Strong's Greek entries successfully extracted✅ Entries integrated into
  database with source='strongs'✅ Greek Unicode text preserved correctly✅ Dictionary
  lookups return Strong's definitions alongside LSJ/Wiktionary✅ No schema validation
  errors✅ Sample database build completes successfully✅ App displays Strong's entries with
  proper formatting

  ---
  Next Steps

  To implement this plan:

  1. Start with scraper: Create extract_strongs_greek.py to fetch and parse Wikisource data
  2. Test extraction: Verify all entries are captured correctly
  3. Integrate into pipeline: Add to build process
  4. Build & deploy: Test with sample database
  5. Document: Update project documentation

  Estimated Total Time: 4-8 hours of development + testing

