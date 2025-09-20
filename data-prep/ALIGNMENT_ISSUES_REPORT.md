# Translation Alignment Issues Report

## Summary
While Bekker/Stephanus references now appear correctly in translations (e.g., [1447a] in Aristotle, [357a] in Plato), the translation_lookup table has significant alignment issues for philosophical texts.

## Current Status

### ✅ Fixed Issues
1. **Bekker/Stephanus References**: Now correctly preserved in translations as bracketed references
2. **Sample Database**: Rebuilt and deployed with fixes (154MB)
3. **Full Database**: Currently rebuilding (25% complete)

### ❌ Remaining Issues

#### 1. Translation Lookup Misalignment
The `translation_lookup` table incorrectly maps Greek lines to translation segments in philosophical texts:

**Example: Plato Republic Book 2**
- Greek text: 507 lines
- Problem: Line 1 maps to both:
  - Segment 35036: [357a] "When I had said this..." (CORRECT)
  - Segment 35039: [360e] "So as he sat there..." (WRONG - from different section)

#### 2. Validation Scores
Content validation shows poor alignment for philosophical texts:
- Homer (Iliad/Odyssey): 85-100% alignment ✅
- Plato (Phaedo/Republic): 0-27% alignment ❌
- Aristotle (Poetics/Ethics): 0-27% alignment ❌

## Root Cause Analysis

The issue appears to be in how the `translation_lookup` table is built during database creation:

1. **Proximity-based mapping**: The current algorithm maps Greek lines to "nearest" translation segments within 100 lines
2. **Multiple mappings**: A single Greek line can map to multiple translation segments
3. **Incorrect associations**: This creates false connections between unrelated Greek and English text

## Impact

Users viewing Plato or Aristotle texts may see:
- Wrong translations when swiping to English view
- Multiple unrelated translation segments for a single Greek line
- Confusing jumps between different parts of the dialogue

## Recommended Fix

The translation_lookup building logic in `create_perseus_database.py` needs revision:
1. Use Stephanus/Bekker references as primary alignment anchors
2. Avoid mapping lines to segments with incompatible reference numbers
3. Consider one-to-one mapping instead of one-to-many for philosophical texts

## Test Cases

Use `spot_check_alignment.py` to verify fixes:
```bash
python3 spot_check_alignment.py perseus_texts_sample.db tlg0059.tlg030.002 1 5
```

This will show the misalignment clearly where line 1 incorrectly maps to [360e] content.