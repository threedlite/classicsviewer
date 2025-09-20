# Latin Authors Line Numbering Issue - Proposed Fix

## Problem Description

Latin poetry collections (especially Horace's Odes) have duplicate line numbers in the database. Each poem within a book restarts its line numbering at 1, causing massive duplication.

**Example from Horace's Odes Book 1:**
- 38 poems, each starting at line 1
- Line number 1 appears 38 times (once per poem)
- Line number 2 appears 38 times (once per poem)
- Total: 876 lines but only 60 unique line numbers

## Root Cause

The `process_text_file` function in `create_perseus_database.py` extracts line numbers directly from Perseus XML files. For poetry collections, the XML structure has:

```xml
<div type="textpart" subtype="book" n="1">
  <div type="textpart" subtype="poem" n="1">
    <l n="1">Maecenas atavis edite regibus...</l>
    <l n="2">o et praesidium et dulce decus meum...</l>
    <!-- ... more lines -->
  </div>
  <div type="textpart" subtype="poem" n="2">
    <l n="1">Iam satis terris nivis atque dirae...</l>  <!-- Line 1 again! -->
    <l n="2">grandinis misit Pater et rubente...</l>     <!-- Line 2 again! -->
    <!-- ... more lines -->
  </div>
  <!-- ... more poems -->
</div>
```

Each poem's `<l n="1">`, `<l n="2">` etc. restarts the numbering.

## Proposed Solution

Modify the line extraction logic in `process_text_file` function (around lines 1640-1680) to implement **sequential line numbering** within books:

### Current Logic (Problematic)
```python
for elem in div.iter():
    if elem.tag.endswith('l') or elem.tag.endswith('line'):
        line_n = elem.get('n')  # Uses XML line number directly
        if line_n and line_n.isdigit():
            lines.append({'number': int(line_n), ...})  # Duplicates!
```

### Proposed Fix
```python
sequential_line_num = 1  # Counter for sequential numbering

for elem in div.iter():
    if elem.tag.endswith('l') or elem.tag.endswith('line'):
        line_n = elem.get('n')
        if line_n and line_n.isdigit():
            text = ''.join(elem.itertext()).strip()
            if text and not any(skip in text for skip in ['Gregory Crane', 'pointer pattern']):
                lines.append({
                    'number': sequential_line_num,  # Use sequential counter
                    'text': text,
                    'xml': ET.tostring(elem, encoding='unicode'),
                    'original_line_n': line_n  # Preserve original for debugging
                })
                sequential_line_num += 1
```

## Expected Result After Fix

**Horace's Odes Book 1:**
- Poem 1 lines: 1, 2, 3, 4, 5... (14 lines total)
- Poem 2 lines: 15, 16, 17, 18, 19... (16 lines total, starting from 15)
- Poem 3 lines: 31, 32, 33, 34, 35... (continuing sequentially)
- etc.
- Final result: 876 unique line numbers (1-876)

## Implementation Notes

### Detection Logic
The fix should only apply to books that contain multiple poems/odes. Detection criteria:
1. Book contains `<div type="textpart" subtype="poem">` elements
2. Line numbers restart at 1 multiple times within the same book
3. Primarily affects Latin poetry (Horace, Ovid, Virgil's shorter works)

### Affected Authors
- **Horace** (`phi0893`): Odes, Epodes, Satires
- **Ovid** (`phi0959`): Various poetry collections  
- **Catullus** (`phi0472`): Poems
- Other Latin poets with collections

### Database Schema Impact
No schema changes needed. The fix only affects the line numbering logic during database creation.

### Translation Alignment
The existing `translation_lookup` table creation process should automatically handle the new sequential line numbers through its proximity mapping algorithm.

## Testing Strategy

1. **Before Fix**: Query duplicate line numbers
   ```sql
   SELECT line_number, COUNT(*) FROM text_lines 
   WHERE book_id = 'phi0893.phi001.001' 
   GROUP BY line_number HAVING COUNT(*) > 1;
   ```

2. **After Fix**: Verify sequential numbering
   ```sql
   SELECT COUNT(*) as total, COUNT(DISTINCT line_number) as unique
   FROM text_lines WHERE book_id = 'phi0893.phi001.001';
   -- Should show: total = unique (e.g., 876 = 876)
   ```

3. **App Testing**: Verify that poem boundaries are still readable in the iOS app

## Files to Modify

- `data-prep/create_perseus_database.py` - Main fix in `process_text_file` function
- Consider adding debug logging to show when sequential renumbering is applied

## Deployment Notes

After implementing this fix:
1. Rebuild the database using `python3 create_perseus_database.py sample`
2. Redeploy using `./deploy_complete.sh` 
3. Clear app data to force schema refresh: `adb shell pm clear com.classicsviewer.app.debug`
4. Test Latin poetry navigation in the iOS app

---

**Status**: Documented for future implementation  
**Priority**: Medium (affects readability of Latin poetry collections)  
**Impact**: Improves line-by-line navigation and translation alignment for Latin authors