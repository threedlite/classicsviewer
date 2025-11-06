 Database Row Counts:

  Sample DB:
  - dictionary_entries: 61,069
  - words: 3,693,367
  - books: 667
  - works: 265
  - authors: 12

  Full DB:
  - dictionary_entries: 118,951 (1.9x larger)
  - words: 19,753,640 (5.3x larger)
  - books: 2,613 (3.9x larger)
  - works: 1,014 (3.8x larger)
  - authors: 133 (11x larger)

  Extended DB:
  - dictionary_entries: 319,275 (5.2x vs sample, 2.7x vs full)
  - words: 72,137,628 (19.5x vs sample, 3.7x vs full)
  - books: 213,206 (319x vs sample, 81x vs full)
  - works: 2,145 (8.1x vs sample, 2.1x vs full)
  - authors: 457 (38x vs sample, 3.4x vs full)


==================

Greek dictionary entries are identical across all 3 databases: 61,069

  Sample DB:
  - Greek authors: 10
  - Greek works: 259
  - Greek dictionary: 61,069

  Full DB:
  - Greek authors: 91 (9.1x sample)
  - Greek works: 772 (3x sample)
  - Greek dictionary: 61,069 (same)

  Extended DB:
  - Greek authors: 367 (36.7x sample, 4x full)
  - Greek works: 1,855 (7.2x sample, 2.4x full)
  - Greek dictionary: 61,069 (same)

===================================

 Runtime Comparison:

  - Sample DB: 74.8 seconds
  - Full DB: 245.8 seconds

  Full DB is 3.3x slower (245.8 / 74.8 = 3.28)

  This makes sense given the full DB has:
  - Same Greek dictionary (61,069 entries)
  - But also Latin dictionary (39,414 entries)
  - Total dictionary entries: 118,951 (1.9x larger)


  Full DB average lookup time: ~10-11ms per word
  Sample DB average lookup time: ~3ms per word (from earlier logs)

  The full database has 3.3x slower database queries because:
  1. Larger database file (1.4GB vs 650MB) means more disk I/O
  2. Dictionary table is 1.9x larger (118,951 vs 61,069 entries)
  3. SQLite has to scan through more rows to find matches
  4. Indexes are larger and slower to traverse

  The Greek dictionary entries are the same (61,069), but the full database also contains
  Latin/Akkadian/Sumerian dictionaries in the same table, making every query slower even when
  looking up Greek words.



===========================


 Database Performance for Iliad Interlinear Generation:

  | Database | Dictionary Entries     | Time   | Slowdown vs Sample | Avg DB Lookup Time |
  |----------|------------------------|--------|--------------------|--------------------|
  | Sample   | 61,069 (Greek only)    | 74.8s  | 1.0x baseline      | ~3ms               |
  | Full     | 118,951 (multilingual) | 245.8s | 3.3x slower        | ~10-11ms           |
  | Extended | 319,275 (multilingual) | 668.5s | 8.9x slower        | ~28-30ms           |

  Key Findings:

  1. Dictionary table size directly impacts query performance - Even though all databases have the
  same 61,069 Greek entries, lookup time increases with total table size
  2. Extended database is 2.7x slower than full - The jump from 118,951 to 319,275 entries caused
  another 2.7x performance hit
  3. Cache hit rate remains consistent - All three databases achieved ~80% cache hit rate, so
  caching isn't the bottleneck
  4. Average DB lookup time scales with table size:
    - Sample: 3ms per lookup
    - Full: 10-11ms per lookup (3.7x slower)
    - Extended: 28-30ms per lookup (9-10x slower)

  | Test | Database | Works           | Lines  | Time   | Avg/Work | DB Lookup Time |
  |------|----------|-----------------|--------|--------|----------|----------------|
  | 1    | Sample   | Iliad only      | 15,687 | 74.8s  | 74.8s    | ~3ms           |
  | 2    | Full     | Iliad only      | 15,687 | 245.8s | 245.8s   | ~10-11ms       |
  | 3    | Extended | Iliad only      | 15,687 | 668.5s | 668.5s   | ~28-30ms       |
  | 4    | Extended | Iliad + Odyssey | 27,794 | 730.8s | 365.4s   | ~32-34ms       |

  Key Finding: With parallel processing, both works completed in just 62 seconds more than the Iliad
   alone (730.8s vs 668.5s), demonstrating parallelization with the 8 workers.


