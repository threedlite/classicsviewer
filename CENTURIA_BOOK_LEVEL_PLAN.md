# Plan: Make centuriae the book level for proverb collections

## Context

5 First1KGreek proverb collections use a `centuria/section` XML hierarchy. Currently, each section (individual proverb) becomes its own "book" in the database. Since `centuria` is not in `structural_subtypes`, sections from different centuriae with the same number collide into one book_id (e.g., all 7 proverbs at section 80 from centuriae 1-7 share `tlg0097.tlg001_OGL.080` line 1).

**Goal**: Make each centuria a book, with sections (proverbs) as lines within that book.

## Affected works

| File | Author | Centuriae | Sections |
|------|--------|-----------|----------|
| tlg0097.tlg001 | Diogenianus | pref + 1-8 | 787 |
| tlg0098.tlg001 | Zenobius | 1-6 | 552 |
| tlg9007.tlg001 | Appendix Proverbiorum | 1-5 | 445 |
| tlg9006.tlg001 | Gregory II of Cyprus | 1-3, 3b | 305 |
| tlg0007.tlg146 | Plutarch | 1-2 | 131 |

## Changes

**File**: `data-prep/create_perseus_database.py`

### 1. Add `centuria` to `structural_subtypes` (2 locations)

- **Line 877** (analysis function): add `'centuria'` to the set
- **Line 1583** (parsing function): add `'centuria'` to the set

This ensures centuria divs are recognized as structural parents. (Doesn't change analysis results since sections are still leaf nodes.)

### 2. Handle centuria divs in div_sections loop (after line 1634)

In the `div_sections` method of `parse_first1k_with_selected_method()` (lines 1624-1690):

- Add a `processed_divs = set()` before the loop
- At top of loop, skip any div in `processed_divs`
- After the `is_leaf_div` check fails, check if div is a centuria with section children
- If so: iterate child section divs, extract each section's text as a line
- Add all child section divs to `processed_divs` to prevent them being processed as individual books
- Store as a single section entry with `type='centuria'` and `split_lines` containing one line per proverb
- Map `n="pref"` to section `"0"` to avoid collision with centuria `n="1"`
- Set `custom_label` field: "Preface" for pref, "Centuria N" for numbered

### 3. Add `'centuria'` to `has_chapter_structure` check (line 2377)

So centuria entries go through the multi-book path (lines 2381-2534) instead of the single-book path.

### 4. Use `custom_label` in book creation (around line 2468)

When a section dict has a `custom_label` field, use it for `section_label` instead of generating `"{type.title()} {sect_num}"`.

## Verification

1. Build a test database with just these 5 works:
   ```
   echo "Author,Work" > TEST_AUTHORS.csv
   echo 'Diogenianus of Heraclea,Paroemiae' >> TEST_AUTHORS.csv
   # ... add all 5
   ```
2. Check book structure: each centuria is one book, sections are lines
   ```sql
   SELECT id, label, line_count FROM books WHERE work_id LIKE 'tlg0097%';
   -- Should show ~9 books (pref + 8 centuriae), each with ~100 lines
   ```
3. Verify no duplicate line numbers within a book
4. Verify the bookmark proverb "Γηράσκω αἰεὶ πολλὰ διδασκόμενος" is at a unique location (Centuria 3, line 80)
