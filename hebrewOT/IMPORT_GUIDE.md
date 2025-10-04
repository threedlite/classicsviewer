# Hebrew Lexicon Import Guide

## Quick Start

The `hebrew_lexicon.zip` file is ready to import into the ClassicsViewer app.

### What's Included

✅ **20,518 dictionary entries** from:
- Brown-Driver-Briggs Hebrew Lexicon (11,845 entries)
- Strong's Hebrew Dictionary (8,673 entries)

✅ **111,948 morphology mappings** from:
- Open Scriptures Hebrew Bible (morphhb)
- Complete word form → lemma mappings for entire Hebrew Bible

✅ **Normalization rules** for:
- Removing nikud (vocalization marks)
- Normalizing final letter forms (ך→כ, ם→מ, etc.)
- Enabling lookups on vocalized Hebrew text

✅ **File size**: 1.93 MB compressed (8.6 MB uncompressed)

## Import Process

### Step 1: Transfer to Android Device
```bash
# Using adb
adb push hebrew_lexicon.zip /sdcard/Download/

# Or copy manually via USB/cloud storage
```

### Step 2: Import via App
1. Open **ClassicsViewer** app
2. Navigate to **Settings** or **Dictionary** menu
3. Select **Import Custom Dictionary**
4. Choose `hebrew_lexicon.zip`
5. Wait for import to complete (~30 seconds)

### Step 3: Verify Import
After import, the app should show:
- Dictionary entries populated in search
- Hebrew word lookups return definitions
- Morphology links to lemma entries

## Database Tables Populated

The import populates three existing tables:

### `dictionary_entries` table
- Stores BDB and Strong's definitions
- Searchable by Hebrew lemma
- Links to morphology via lemma field

### `lemma_map` table
- Maps Hebrew word forms to lemmas
- Enables morphology-based lookups
- Includes grammatical information

### `normalization_patterns` table
- Stores text normalization rules for Hebrew
- Removes vocalization marks (nikud)
- Normalizes final letter forms
- Applied automatically during word lookups

## Example Lookups

After import, you can look up:

**Hebrew Word**: בְּרֵאשִׁית (b'reshit)
- **Lemma**: 7225
- **Morphology**: HR/Ncfsa (Hebrew, Preposition/Noun common feminine singular absolute)
- **Definition**: "beginning, first"

**Hebrew Word**: בָּרָא (bara)
- **Lemma**: 1254 a
- **Morphology**: HVqp3ms (Hebrew Verb Qal perfect 3rd person masculine singular)
- **Definition**: "to create, form, fashion"

## Verification

To verify the lexicon package before import:

```bash
cd hebrewOT
./verify_lexicon.sh
```

This checks:
- ✓ ZIP file integrity
- ✓ Required CSV files present
- ✓ Correct file format
- ✓ Sample data preview

## File Format

The ZIP contains three CSV files following the app's standard format:

### dictionary.csv
```csv
lemma,language,definition,html_definition,source_name
אָב,hebrew,"father, in a literal...",,"Strong's H1"
```

### morphology.csv
```csv
word_form,lemma,morph_info,language,confidence,source_name
בְּרֵאשִׁית,7225,HR/Ncfsa,hebrew,1.0,OSHB morphhb
```

### normalization_rules.csv
```csv
language,pattern,replacement,description,priority
hebrew,[\u0591-\u05C7],,Remove all nikud (vocalization marks),1
hebrew,ם,מ,Normalize final mem to regular mem,3
```

## Troubleshooting

### Import Fails
- Check file is not corrupted: `unzip -t hebrew_lexicon.zip`
- Verify file size is ~1.9 MB
- Ensure app has storage permissions

### No Dictionary Results
- Verify import completed successfully
- Check app database for entries
- Restart app to reload dictionary

### Hebrew Text Not Displaying
- Ensure device supports Hebrew fonts
- Check app settings for RTL text support
- Verify vocalization marks render correctly

## Attribution

This lexicon is compiled from:

**Open Scriptures Hebrew Bible** (CC BY 4.0)
- https://github.com/openscriptures/morphhb

**OSHB Hebrew Lexicon** (CC BY 4.0)
- https://github.com/openscriptures/HebrewLexicon

Both projects are licensed under Creative Commons Attribution 4.0 International License.

## Regenerating the Lexicon

To regenerate from source data:

```bash
cd hebrewOT
python3 create_hebrew_lexicon.py
```

This will:
1. Parse HebrewLexicon XML files
2. Extract morphology from morphhb OSIS files
3. Generate fresh CSV files
4. Package into `hebrew_lexicon.zip`

Total processing time: ~10-15 seconds

## Technical Details

**CSV Encoding**: UTF-8
**Compression**: ZIP (DEFLATE)
**Hebrew Text**: Fully vocalized (nikud)
**Normalization**: None (preserves original forms)
**Deduplication**: Word forms deduplicated across entire Bible

## Next Steps

After importing the lexicon:

1. **Test lookups**: Search for common words (אָב, בָּרָא, etc.)
2. **Browse entries**: View all BDB and Strong's definitions
3. **Check morphology**: Verify word forms link to correct lemmas
4. **Import texts**: Use with Hebrew Bible texts when available

---

For questions or issues, see:
- `README.md` - Complete documentation
- `HEBREW_DATASOURCE_PLAN.md` - Implementation details
- Source repositories for data format specifications
