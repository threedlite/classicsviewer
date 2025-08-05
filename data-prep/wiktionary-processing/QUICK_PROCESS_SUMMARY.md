# Wiktionary Extraction - Quick Process Summary

## The Optimization in a Nutshell

**Problem**: Searching 10M+ Wiktionary pages for each of 179k Greek words = 1.79 trillion page checks  
**Solution**: Extract all Greek pages first (10M checks), then search only those (124k × 179k = 22B checks)  
**Result**: 50x faster (12 hours → 15 minutes)

## Complete Process Flow

```bash
# Step 1: Create Greek page cache (10 min) - RUN ONCE
python3 extract_all_greek_pages.py
# Output: all_greek_wiktionary_pages.json (46MB, 124k pages)

# Step 2: Extract inflection mappings (3 sec) - FAST!
python3 extract_inflections_from_cache.py extract
# Output: inflection_mappings_final.json (15k mappings)

# Step 3: Extract definitions (30 sec) - OPTIONAL
python3 extract_definitions_from_cache.py extract  
# Output: wiktionary_definitions_final.json (6.7k definitions)

# Step 4: Add to database
python3 extract_inflections_from_cache.py add
python3 extract_definitions_from_cache.py add

# Step 5: Rebuild main database
cd ..
python3 build_database.py
```

## Key Files Created

1. **all_greek_wiktionary_pages.json** (46MB)
   - Cache of all Greek pages from Wiktionary
   - 124,116 pages with Greek/Ancient Greek sections
   - KEY TO SPEED - create this once, use many times

2. **inflection_mappings_final.json** (2.6MB)
   - 15,592 inflected form → lemma mappings
   - Includes morphological tags (case, number, tense, etc.)
   - Example: "ἀνδρός" → "ἀνήρ" (genitive singular)

3. **wiktionary_definitions_final.json** (1.6MB)
   - 6,755 dictionary entries
   - Brief definitions for lemmas
   - Supplements LSJ dictionary

## What Made It Fast

1. **One-time cost**: Scan 10M pages → extract 124k Greek pages (10 min)
2. **Reuse cache**: All subsequent operations use the 46MB cache
3. **In-memory search**: JSON loads fully into RAM for instant access
4. **Set operations**: O(1) lookup for "is this word in our corpus?"

## Performance Stats

- Initial extraction: 16,000 pages/second
- Cache size: 46MB (0.003% of original 1.4GB)
- Inflection extraction: 6,200 mappings/second
- Memory usage: ~250MB peak
- Total time: 15 minutes vs 12+ hours

## To Run Again

If you need to process a new corpus or updated Wiktionary:

```bash
# Only if Wiktionary dump is updated:
rm all_greek_wiktionary_pages.json
python3 extract_all_greek_pages.py

# For new corpus words:
python3 extract_inflections_from_cache.py extract
python3 extract_inflections_from_cache.py add
```

The cache file can be reused indefinitely unless Wiktionary is updated!