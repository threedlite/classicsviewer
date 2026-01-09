# Interlinear Build Status

**Last Build**: January 8, 2026
**Status**: Complete

## Build Results

| Language | Expected | Processed | Skipped | Files Generated |
|----------|----------|-----------|---------|-----------------|
| Greek    | 2,049    | 2,049     | 68      | 1,981           |
| Latin    | 230      | 230       | 2       | 228             |
| **Total**| 2,279    | 2,279     | 70      | 2,209           |

## Runtime (8 workers)

| Language | Words/Lines | Duration | Avg per Work |
|----------|-------------|----------|--------------|
| Greek    | 34.9M words | 11.1 hours (39,838s) | 19.4s |
| Latin    | 372K lines  | 14 seconds | 0.1s |

## Output Location

```
/Users/user1/git/classicsviewer/data-sources/classicsviewer_interlinear/
```

**Total size**: 4.1 GB
**File count**: 2,209 interlinear.txt files + 2,209 perseus-eng99.xml files

## Explanation of "Missing" Files

The 70 skipped works are **not failures** - they are works that exist in the database metadata (works table) but have **no actual text content** (no books/lines). The generation correctly skips these with a warning:

```
WARNING: No books found for work ID tlg0284.tlg001
This work exists in the database but has no text content.
Skipping this work.
```

### Works Without Text Content (70 total)

#### Aristides, Aelius - Orationes (54 works)
Only Orationes 55-56 have digitized text. Orationes 1-54 are catalogued but not available:
- tlg0284.tlg001 through tlg0284.tlg054 (excluding tlg055, tlg056)

#### Other Greek Works (14 works)
| Work ID | Author | Title |
|---------|--------|-------|
| tlg0545.tlg003 | Aelian | Epistulae Rusticae |
| tlg2040.tlg004 | Basil | Epistulae |
| tlg0555.tlg008 | Clement of Alexandria | Exhortation to Endurance (Fragment 44) |
| tlg0557.tlg004 | Epictetus | Gnomology (Books 1-2) |
| tlg0557.tlg005 | Epictetus | Gnomology (Books 3-4) |
| tlg1389.tlg001 | Harpocration | Lexicon in decem oratores Atticos |
| tlg0627.tlg013 | Hippocrates | Jusjurandum |
| tlg2003.tlg013 | Julian | Epistolae |
| tlg2003.tlg017 | Julian | Kata Galilaion |
| tlg0560.tlg001 | Longinus | On the Sublime |
| tlg0638.tlg004 | Philostratus | Heroicus |
| tlg0638.tlg005 | Philostratus | Nero |
| tlg4036.tlg023 | Proclus | Chrestomathy |
| tlg0099.tlg001 | Strabo | Geography |

#### Latin Works (2 works)
| Work ID | Author | Title |
|---------|--------|-------|
| phi0631.phi003 | Sallust | Historiae |
| phi1014.phi004 | Seneca the Elder | Fragmenta |

### Root Cause

These works are catalogued in Perseus/First1KGreek metadata but the actual text is:
- Not available in the source XML repositories
- Fragmentary/incomplete and excluded during XML processing
- Referenced only without digitized text

### File Prefix Distribution

| Prefix | Count | Source |
|--------|-------|--------|
| tlg    | 1,782 | Thesaurus Linguae Graecae |
| phi    | 228   | Packard Humanities Institute (Latin) |
| pta    | 194   | Patristic Text Archive |
| stoa   | 4     | Stoic texts |
| ogl    | 1     | Open Greek and Latin |

## Verification Commands

```bash
# Check for running processes
ps aux | grep -E "python|interlinear" | grep -v grep

# Count generated files
ls /Users/user1/git/classicsviewer/data-sources/classicsviewer_interlinear/*.interlinear.txt | wc -l

# Check works without text in database
sqlite3 /Users/user1/git/classicsviewer/data-prep/perseus_texts_extended.db \
  "SELECT COUNT(*) FROM works w WHERE NOT EXISTS (SELECT 1 FROM books b WHERE b.work_id = w.id);"

# View generation log summary
tail -20 generation.log
```
