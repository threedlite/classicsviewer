# Expanded Database Implementation Plan

## Overview
This document outlines the implementation for expanding the Perseus database from 14 to 100 Greek authors, maintaining proper translation alignment and rebuilding the dictionary with the expanded vocabulary.

## Implementation Status

### ✅ Completed
1. **Dynamic Author Discovery**: Created `create_perseus_database_expanded.py` that automatically discovers all 100 Greek authors from the canonical-greekLit directory
2. **Phased Testing**: Added support for test phases (30, 60, or all authors)
3. **Progress Tracking**: Added detailed progress reporting during build
4. **Memory Optimizations**: Added SQLite pragmas for better performance
5. **Author Catalog**: Created utility to extract all author information

### 📋 Key Features

#### Dynamic Author Discovery
- Parses `__cts__.xml` files to get author names
- Handles missing/malformed metadata gracefully
- Prioritizes well-known authors for test phases

#### Translation Alignment
- Existing alignment logic preserved (handles prose section → line mapping)
- Tested with authors like Aeschines where translations use section numbers
- Proportional mapping automatically applied when detected

#### Performance Optimizations
- WAL mode enabled for better concurrent writes
- Batch commits every 5 authors
- Memory-efficient cache settings
- Progress saved periodically to avoid data loss

## Usage Instructions

### Phase 1: Test with 30 Authors
```bash
cd /home/user/git2/classicsviewer/data-prep
python3 create_perseus_database_expanded.py test
```

### Phase 2: Test with 60 Authors  
```bash
python3 create_perseus_database_expanded.py medium
```

### Phase 3: Full Build (All 100 Authors)
```bash
python3 create_perseus_database_expanded.py full
# or just:
python3 create_perseus_database_expanded.py
```

## Expected Results

### Database Size Projections
- **14 authors**: 774MB uncompressed, 171MB compressed
- **30 authors**: ~1.7GB uncompressed, ~370MB compressed
- **60 authors**: ~3.3GB uncompressed, ~730MB compressed  
- **100 authors**: ~5.5GB uncompressed, ~1.2GB compressed

### Build Time Estimates
- **Test (30)**: 10-15 minutes
- **Medium (60)**: 20-30 minutes
- **Full (100)**: 40-60 minutes

### Vocabulary Growth
- **14 authors**: ~179k unique words
- **100 authors**: ~1M+ unique words expected

## Dictionary Rebuilding Process

The expanded script automatically:
1. Extracts all unique words from the expanded corpus
2. Reuses existing Wiktionary cache (46MB, already extracted)
3. Generates lemma mappings for new vocabulary
4. Applies algorithmic lemmatization for unmapped words
5. Optimizes the lemma_map table to only include words in texts

## Next Steps for Full Deployment

### 1. Run Test Build
```bash
python3 create_perseus_database_expanded.py test
```

### 2. Verify Results
- Check database statistics in output
- Verify translation alignment for test authors
- Monitor memory usage during build

### 3. Run Full Build
```bash
python3 create_perseus_database_expanded.py full
```

### 4. Update Multi-part Deployment
Once the full database is built:
```bash
# Split the compressed database for multi-part asset packs
python3 split_database_for_assets.py split perseus_texts.db.zip 450

# Update the app to use MultiPartDatabaseExtractionActivity
# (See docs/multipart-database-deployment.md)
```

## Monitoring and Troubleshooting

### Memory Issues
If you encounter memory errors:
- Process authors in smaller batches
- Increase system swap space
- Use the medium phase first

### Translation Alignment Issues
The script will report any authors with alignment problems. Check the quality report:
```bash
cat quality_report.txt | grep -A5 "alignment"
```

### Failed Authors
Failed authors are reported at the end of the build. Common issues:
- Malformed XML files
- Missing work files
- Encoding issues

## Author List Summary

The 100 Greek authors include major works from:
- Epic: Homer, Hesiod, Apollonius Rhodius
- Drama: Aeschylus, Sophocles, Euripides, Aristophanes
- History: Herodotus, Thucydides, Xenophon, Plutarch
- Philosophy: Plato, Aristotle, Diogenes Laertius
- Poetry: Pindar, Theocritus, Greek Anthology
- Medicine: Hippocrates, Galen, Aretaeus
- Mathematics: Euclid, Proclus
- Religion: New Testament, Clemens Romanus, Eusebius

Full author catalog available in: `greek_authors_catalog.json`