# Persian Texts Database

This directory contains the Persian language texts database for ClassicsViewer, created from the Perseus Digital Library's canonical-farsiLit collection.

## Database Contents

**Source:** Perseus Digital Library - canonical-farsiLit
- **License:** Creative Commons Attribution-ShareAlike 3.0 United States (CC BY-SA 3.0)
- **Repository:** https://github.com/PerseusDL/canonical-farsiLit
- **Format:** TEI XML with Persian script (not transliteration)

### Included Works

**Hafez - Divān (Divan)**
- **Author:** Khwāja Shams-ud-Dīn Muhammad Hāfez-e Shīrāzī (c. 1315-1390)
- **Persian Text:** 4,192 lines in Persian script
- **English Translation:** 4,179 parallel translation segments (H. Wilberforce Clarke, 1891)
- **Content:** Complete collection of Hafez's ghazals (lyric poems)
- **Total Words:** 64,324 words
- **Unique Words:** 7,834 unique word forms

## Database Statistics

```
Texts: 1 (Hafez Divan)
Total lines: 4,192
Translation segments: 4,179
Total words: 64,324
Unique words: 7,834
Database size: 7.8 MB (uncompressed)
Compressed size: 2.2 MB (ZIP)
```

## Database Schema

The database follows the ClassicsViewer schema:

### Tables

1. **texts** - Metadata for works
   - `id`, `book_id`, `author`, `title`, `language`, `has_translation`

2. **text_lines** - Persian text content
   - Each line contains one couplet (both hemistichs combined)
   - Persian script (e.g., "الا یا ایها الساقی ادر کاسا و ناولها")

3. **translation_segments** - English translations
   - Line-by-line parallel translations
   - Aligned with Persian text via translation_lookup table

4. **translation_lookup** - Translation alignment mapping
   - Maps Persian line numbers to translation segments
   - Enables accurate parallel text display

5. **words** - Individual words for search
   - Each word with position in line
   - Normalized form for search (diacritics removed)

## Text Normalization

Persian text normalization rules are defined in `normalization_rules_persian.csv`:

- Remove Arabic diacritics (fatha, damma, kasra, sukun, shadda, tanwin)
- Remove superscript marks (alef khanjariyah, maddah, hamza)
- Remove zero-width non-joiner (ZWNJ)
- Normalize Arabic letter variants to Persian equivalents:
  - Arabic yeh (ى, ي) → Farsi yeh (ی)
  - Arabic kaf (ك) → Farsi kaf (ک)
  - Hamza variants → plain letters

## Building the Database

To rebuild the database from source:

```bash
cd /Users/user1/git/classicsviewer/persian
python3 create_persian_database.py
```

This will:
1. Parse Persian TEI XML (`hafez.divan.perseus-far1.xml`)
2. Parse English translation TEI XML (`hafez.divan.perseus-eng1.xml`)
3. Create aligned database with translation lookup
4. Extract and normalize words for search
5. Generate `persian_texts.db`

To compress:
```bash
zip -9 persian_texts.db.zip persian_texts.db
unzip -t persian_texts.db.zip  # Verify integrity
```

## Translation Alignment

The database uses the **translation_lookup** system to ensure accurate alignment between Persian text and English translations:

- Each Persian line maps to its corresponding English translation segment
- Direct line-by-line correspondence (Line 1 → Translation 1, etc.)
- The couplet structure is preserved (both hemistichs combined per line)
- Translation queries use the lookup table for exact matching

## Dictionary Status

**Currently:** No Persian dictionary included
- **Reason:** No Persian-script dictionary available with clear compatible licensing
- **Impact:** Users can read texts and parallel translations, but no word-by-word lookup
- **Future:** Dictionary will be added when licensing is resolved

See `PERSIAN_RESOURCES_ANALYSIS.md` for detailed analysis of dictionary options.

## Files in this Directory

- `persian_texts.db` - Uncompressed SQLite database (7.8 MB)
- `persian_texts.db.zip` - Compressed database for deployment (2.2 MB)
- `create_persian_database.py` - Database creation script
- `normalization_rules_persian.csv` - Persian text normalization rules
- `canonical-farsiLit/` - Perseus repository (cloned from GitHub)
- `steingass_persian_english_dictionary.txt` - Downloaded but not usable (transliteration only)
- `PERSIAN_RESOURCES_ANALYSIS.md` - Comprehensive analysis of Persian resources
- `README.md` - This file

## Integration with ClassicsViewer

To integrate this database into the ClassicsViewer app:

1. Copy `persian_texts.db.zip` to the app's asset delivery module
2. Add Persian language support to the database extraction code
3. Implement Persian text normalization using the rules CSV
4. Add Persian to the language selection UI
5. Test parallel text display and word search functionality

## License and Attribution

**Perseus Digital Library - canonical-farsiLit**
- License: CC BY-SA 3.0
- Additional Restriction: Users must offer Perseus any modifications they make
- Source: https://github.com/PerseusDL/canonical-farsiLit

**Persian Text:**
- Based on: Mohammad Qazvini and Qāsem Ḡani edition (Tehran, 1941)
- Digital edition: ganjoor.net, supervised by Maryam Foradi and Saeed Majidi
- Sponsor: Open Philology Project, Tufts University
- Funder: Humboldt Foundation

**English Translation:**
- Translator: H. Wilberforce Clarke
- Publisher: Government of India Central Printing Office, Calcutta, 1891
- Public domain translation

## Classical Persian Poetry

Hafez (c. 1315-1390) is one of the most celebrated poets in Persian literature. His Divan consists primarily of ghazals - lyric poems exploring themes of love, spirituality, wine, and mystical union with the divine. The poems can be read on multiple levels:

1. **Literal:** Love poetry, wine songs, nature imagery
2. **Mystical:** Sufi spiritual symbolism (wine = divine love, beloved = God)
3. **Philosophical:** Meditations on fate, mortality, joy, and transcendence

This edition preserves the traditional organization by first letter of the rhyme (Alif, Ba, etc.) and maintains the couplet structure of Persian classical poetry.

---

**Last Updated:** October 4, 2025
**Database Version:** 1.0
**Total Lines:** 4,192
**Total Words:** 64,324
