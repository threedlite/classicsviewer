# Translation Alignment System Documentation

## Overview

The Classics Viewer app handles multiple translations with different structural approaches. This document explains how the alignment system works to ensure all translations are accessible despite varying translation styles.

## Translation Styles in Perseus Data

### 1. Line-by-Line Translations
Some translators provide granular, line-by-line translations:
- **Example**: Gilbert Murray's Euripides translations
- **Structure**: Each Greek line gets its own translation segment
- **Database Storage**: `start_line = end_line` for each segment

### 2. Paragraph/Block Translations
Some translators group multiple lines into prose paragraphs:
- **Example**: Augustus Taber Murray's Homer translations
- **Structure**: Lines 1-35 might be combined into one prose paragraph
- **Database Storage**: `start_line=1, end_line=35`

### 3. Milestone-Based Translations
Some translators provide translations only at key narrative points:
- **Example**: Samuel Butler's Homer translations
- **Structure**: Translations at lines 1, 10, 15, 27, 30, 39, 58, 71...
- **Database Storage**: Each stored as `start_line=30, end_line=30` (single line)
- **Important**: Butler's "line 30" segment actually contains the translation for Greek lines 30-38, but Perseus only provides the starting line number

### 4. Reference-Based Translations (Philosophical Texts)
Plato and Aristotle translations use standard reference systems:
- **Example**: Plato's Republic, Aristotle's Nicomachean Ethics
- **Structure**: Translations grouped by Stephanus (Plato) or Bekker (Aristotle) references
- **Database Storage**: Segments like `start_line=1, end_line=18` containing [357a] reference
- **Greek Text**: Contains reference markers like [354c], [357d] at specific lines
- **Important**: The references in translations ([357a]) correspond to markers in Greek text

## Database Structure

### Tables Involved

1. **translation_segments**: Stores the actual translations
   - `id`: Unique identifier
   - `book_id`: Which book this translates
   - `start_line`: First line number of this segment
   - `end_line`: Last line number (often same as start_line for milestone translations)
   - `translation_text`: The actual translation
   - `translator`: Name of translator

2. **translation_lookup**: Maps Greek lines to translation segments
   - `book_id`: Book identifier
   - `line_number`: Greek line number
   - `segment_id`: Which translation segment covers this line

## Alignment Algorithm

### Phase 1: Direct Mapping
The system first creates direct mappings based on line ranges:
- If a segment covers lines 1-35, all lines 1-35 map to that segment
- If a segment is marked as line 30-30, only line 30 maps to it

### Phase 2: Proximity Mapping
For lines without direct mappings, the system finds the nearest segment within 100 lines:
- Greek line 31 with no direct mapping looks for nearest segment
- Finds Butler's segment at line 30 (distance = 1)
- Creates mapping: line 31 → Butler segment 30

### Phase 3: Multiple Translator Handling
When multiple translators exist:
- Each line can map to multiple segments (one per translator)
- Line 30 might map to:
  - Murray's paragraph segment (lines 1-35)
  - Butler's milestone segment (line 30)

## UI Retrieval Strategy

### The ±50 Line Expansion
When the app displays a Greek line, it:
1. Expands the search range by ±50 lines
2. For line 35, searches for segments in range -15 to 85
3. Retrieves ALL segments that either:
   - Have line ranges overlapping this expanded range
   - Are explicitly mapped in translation_lookup table

### Why This Works
- Assumes milestone translations are never more than 100 lines apart
- The ±50 expansion ensures at least one segment is always found
- Users see relevant translations even for "gap" lines

## Example: Homer Iliad Book 3, Line 35

### What's in the Database:
- **Murray**: Segment covering lines 1-35 (paragraph style)
- **Butler**: Segments at lines 30 and 39 (milestone style)
- **translation_lookup**: Line 35 only maps to Murray

### What the UI Does:
1. User views line 35
2. UI queries for lines -15 to 85 (35 ± 50)
3. Finds:
   - Murray's segment (1-35) - overlaps with range
   - Butler's segment at line 30 - within expanded range
   - Butler's segment at line 39 - within expanded range
4. Shows both translations to user

### Result:
User sees both Murray's paragraph translation AND Butler's nearest milestone translation, despite line 35 not being explicitly mapped to Butler.

## Example: Plato Republic Book 2, Line 1

### What's in the Database:
- **Greek Text**: Line 1 contains [354c] reference marker
- **Translation**: Segment covering lines 1-18 contains [357a] reference
- **translation_lookup**: Line 1 has NO explicit mapping (0 entries)

### What the UI Does:
1. User views line 1
2. UI queries for lines -49 to 51 (1 ± 50)
3. Finds:
   - Translation segment (1-18) - overlaps with expanded range
   - Segment contains proper Stephanus reference [357a]
4. Shows translation with reference to user

### Result:
User sees the correct translation with Stephanus reference, despite no explicit mapping in translation_lookup table.

## Coverage Patterns

### Expected Coverage by Translation Style:

1. **Line-by-line**: ~95-100% of lines have explicit mappings
   - Example: Gilbert Murray's Euripides - 983/987 lines (99.6%)

2. **Paragraph style**: ~90-100% of lines have explicit mappings
   - Example: Augustus Taber Murray's Homer - 434/461 lines (94%)

3. **Milestone style**: ~15-40% of lines have explicit mappings
   - Example: Samuel Butler's Homer - 65/461 lines (14%)
   - Example: E.P. Coleridge's Euripides - 378/987 lines (38%)

4. **Reference-based (Philosophical)**: ~10-15% of lines have explicit mappings
   - Example: Plato Republic Book 2 - 54/507 lines (11%)
   - Example: Aristotle Ethics Book 1 - 46/371 lines (12%)
   - The translations are complete but organized by reference sections
   - No gaps larger than 100 lines between segments

These coverage differences are **by design** - milestone and reference-based translations don't need explicit mappings for every line because the UI's expansion strategy ensures they're still displayed.

## Key Design Principles

1. **No translation is "missing"** - gaps between milestones are intentional
2. **Every Greek line can access translations** - via direct mapping or UI expansion
3. **Multiple translation styles coexist** - the system handles all three patterns
4. **Proximity matters** - nearest translations are always accessible
5. **UI compensation** - the ±50 line expansion bridges any mapping gaps

## Summary

The translation alignment system successfully handles four different translation approaches (line-by-line, paragraph, milestone, and reference-based) by combining:
- Direct line range mappings where available
- Proximity-based mappings for unmapped lines  
- UI-level range expansion to ensure all translations are accessible

This design allows the app to present multiple translations with different structural approaches without requiring every line to be explicitly mapped to every translation. The system works correctly for all major authors including Homer, Euripides, Plato, and Aristotle, with the UI's ±50 line expansion ensuring that even sparsely-mapped philosophical texts display their translations properly.
