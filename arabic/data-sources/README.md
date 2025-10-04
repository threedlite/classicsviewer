# Arabic Data Sources

This folder contains source materials for Arabic text integration into ClassicsViewer.

## Downloaded Files

### 1. Mu'allaqa of Imru' al-Qays
**File:** `muallaqat_imru_al_qays.html`
**Source:** https://ar.wikisource.org/wiki/معلقة_امرئ_القيس
**License:** CC BY-SA 4.0
**Size:** 76 KB
**Description:** HTML page containing the complete text of the Mu'allaqa (hanging ode) by Imru' al-Qays, one of the seven famous pre-Islamic Arabic poems. The text is structured verse-by-verse.

### 2. Lane's Arabic-English Lexicon (Perseus)
**Directory:** `arabic_text_perseus/`
**Source:** https://github.com/cltk/arabic_text_perseus (mirror of Perseus Digital Library)
**License:** CC BY-SA 3.0
**Size:** 116 MB
**Description:** Complete Perseus Arabic collection including:

- **Lane's Lexicon** (`Lane/opensource/`): 36 XML files containing Lane's comprehensive classical Arabic dictionary (8 volumes, 1863-1893)
- **Quran** (`Quran/opensource/`):
  - `arabic-translit.xml` - Arabic text with transliteration (871 KB)
  - `pickthal.xml`, `shakir.xml`, `yusufali.xml` - English translations (not used per project decision)
- **Salmone** (`Salmone/opensource/`): Additional lexicon/reference work

## File Structure

```
arabic/data-sources/
├── README.md                           # This file
├── muallaqat_imru_al_qays.html        # Wikisource HTML of the poem
└── arabic_text_perseus/               # Perseus Arabic collection (git repo)
    ├── Lane/
    │   └── opensource/                # 36 XML files (dictionary entries)
    ├── Quran/
    │   └── opensource/                # 4 XML files (text + translations)
    └── Salmone/
        └── opensource/                # Additional reference
```

## Integration Status

- ✅ **Downloaded:** Both primary sources acquired
- ⏳ **Parsing:** Need to extract text from HTML and XML
- ⏳ **Database:** Need to integrate into `create_perseus_database.py`
- ⏳ **Normalization:** Use existing `custom_dictionary/normalization_rules_arabic.csv`

## Next Steps

1. Create parser for Wikisource HTML to extract verses and Arabic text
2. Create parser for Lane's Lexicon TEI XML to extract headwords and definitions
3. Add Arabic section to `data-prep/create_perseus_database.py`
4. Test with sample database build
5. Verify word lookup and navigation functionality

## License Compatibility

All sources use CC BY-SA licenses (3.0 or 4.0) which are compatible with:
- ClassicsViewer's MIT license
- Commercial distribution via app stores
- Existing Greek/Latin Perseus content (also CC BY-SA 3.0)

## Notes

- **No Quran integration planned** - Avoided due to translation sensitivities
- **Lane's Lexicon only** - Dictionary resource for word lookups, not reading text
- **Mu'allaqa text** - Single demonstration poem (~78-82 verses)
- **Git repo kept** - `arabic_text_perseus/` is a full git clone for version tracking


-rw-r--r--   1 user1  staff  77630 Oct  4 14:50 muallaqat_imru_al_qays.html
drwxr-xr-x   7 user1  staff    224 Oct  4 14:50 arabic_text_perseus
-rw-r--r--   1 user1  staff   2954 Oct  4 14:51 README.md
-rw-r--r--   1 user1  staff  91923 Oct  4 15:12 muallaqat_translation_johnson.html
