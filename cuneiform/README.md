# ORACC Cuneiform Text Downloader

This directory contains scripts for downloading CC BY-SA licensed Akkadian and Sumerian texts from the ORACC (Open Richly Annotated Cuneiform Corpus) project.

## License Verification

All texts downloaded by these scripts are from ORACC projects documented as using **CC BY-SA 3.0** licensing, which is compatible with commercial use with attribution.

## Downloaded Projects

### Akkadian Texts (with English translations)
- **RINAP**: Royal Inscriptions of the Neo-Assyrian Period
- **SAAo**: State Archives of Assyria online
- **RIAo**: Royal Inscriptions of Assyria online
- **CMAwRo**: Corpus of Mesopotamian Anti-witchcraft Rituals

### Sumerian Texts
- **ETCSRI**: Electronic Text Corpus of Sumerian Royal Inscriptions (with English translations)
- **ePSD2 Literary**: Sumerian literary texts (mostly untranslated)

### Dictionaries
- **ePSD2**: electronic Pennsylvania Sumerian Dictionary (CC BY-SA)

## Usage

```bash
# Run the download script
python3 cuneiform/download_oracc_texts.py
```

Downloaded files will be placed in: `data-sources/oracc/`

## Data Format

The script downloads JSON exports which contain:
- Transliterated text (Latin script with diacritics)
- English translations (where available)
- Lemmatization data
- Morphological analysis
- Metadata and cataloging information

## Important Notes

1. **No Cuneiform Unicode**: Texts use transliteration (Latin script) not cuneiform glyphs
2. **CC BY-SA 3.0**: All content is under Creative Commons Attribution-ShareAlike license
3. **Attribution Required**: Must attribute ORACC and specific projects when using data
4. **JSON Format**: Data is in JSON format, parsers needed to extract TEI/XML

## Android Display

These texts will display correctly on Android because they use:
- Standard Latin alphabet
- Common diacritics (š, ṣ, ṭ, ḫ)
- No special cuneiform fonts required