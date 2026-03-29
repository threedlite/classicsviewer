# Classical Chinese for ClassicsViewer

**Status**: Initial Release
**Language**: Classical Chinese (文言文)
**License**: CC BY-SA 4.0 + Public Domain (commercial use allowed with attribution)

## Quick Start

```bash
cd chinese
python3 create_chinese_database.py
```

The script automatically:
1. Downloads all 33 chapters of the Zhuangzi from Chinese Wikisource
2. Downloads Herbert Giles's English translation (1889) from English Wikisource
3. Downloads all 81 chapters of the Dao De Jing (Wang Bi edition) from Chinese Wikisource
4. Downloads James Legge's English translation (1891) from English Wikisource
5. Parses and tokenizes the Classical Chinese text (character-by-character)
6. Creates SQLite database with translations
7. Compresses to `chinese_texts.db.zip`

No external Python dependencies required (stdlib only).

## Contents

### Zhuangzi (莊子) — 33 chapters
- Inner Chapters (內篇): 1-7 — attributed to Zhuangzi himself
- Outer Chapters (外篇): 8-22
- Miscellaneous Chapters (雜篇): 23-33
- English translation: Herbert Giles (1889), all 33 chapters

### Dao De Jing (道德經) — 81 chapters
- Wang Bi (王弼) edition — the standard received text
- Part 1: Dao Jing (道經, chapters 1-37)
- Part 2: De Jing (德經, chapters 38-81)
- English translation: James Legge (1891), all 81 chapters
- Wang Bi commentary is stripped; only the source text is included

## Data Sources

| Content | Source | License |
|---------|--------|---------|
| Zhuangzi Chinese | [zh.wikisource.org/wiki/莊子](https://zh.wikisource.org/wiki/%E8%8E%8A%E5%AD%90) | CC BY-SA 4.0 |
| Zhuangzi English | [en.wikisource.org — Chuang Tzŭ (Giles)](https://en.wikisource.org/wiki/Chuang_Tz%C5%AD_(Giles)) | Public Domain (1889) |
| Dao De Jing Chinese | [zh.wikisource.org — 道德經 (王弼本)](https://zh.wikisource.org/wiki/%E9%81%93%E5%BE%B7%E7%B6%93_(%E7%8E%8B%E5%BC%BC%E6%9C%AC)) | CC BY-SA 4.0 |
| Dao De Jing English | [en.wikisource.org — Tâo Teh King](https://en.wikisource.org/wiki/T%C3%A2o_Teh_King) | Public Domain (1891) |

## File Structure

```
chinese/
├── create_chinese_database.py   # Main build script
├── run_build.sh                  # Background build wrapper
├── README.md                     # This file
├── .gitignore
├── data-sources/                 # Downloaded/cached Wikisource pages (gitignored)
├── chinese_texts.db              # Generated database (gitignored)
└── chinese_texts.db.zip          # Compressed database (gitignored)
```

## Technical Notes

### Character Tokenization
Classical Chinese does not use spaces between words. Each character is tokenized individually in the `words` table, which is the standard scholarly granularity for Classical Chinese — most words are single characters.

### Display
- Text uses Traditional Chinese characters (莊子 not 庄子) — the scholarly standard
- Modern punctuation (。，、) is preserved for readability
- Android has built-in CJK font support (Noto Sans CJK)

### MAX_LINE_SIZE
Lines are capped at 2000 characters. Long paragraphs are split at sentence boundaries (。) or clause boundaries (，).

### Caching
Downloaded Wikisource API responses are cached in `data-sources/`. Delete the cache to force re-download.

### Dao De Jing Parsing
The Wang Bi edition on zh.wikisource.org includes interleaved commentary in `<dl><dd><small>` blocks. These are automatically stripped during parsing, leaving only the source text. Colophon sections (跋) after chapter 81 are also excluded.

## License

- **Chinese text**: CC BY-SA 4.0 (Wikisource)
- **Zhuangzi English**: Public Domain (Herbert Giles, 1889)
- **Dao De Jing English**: Public Domain (James Legge, 1891)

Commercial use is permitted with attribution.

### Attribution
```
Zhuangzi Chinese text: Wikisource (zh.wikisource.org) - CC BY-SA 4.0
Zhuangzi English: "Chuang Tzŭ: Mystic, Moralist, and Social Reformer" by Herbert A. Giles (1889) - Public Domain
Dao De Jing Chinese text: Wikisource (zh.wikisource.org), Wang Bi edition - CC BY-SA 4.0
Dao De Jing English: "Tâo Teh King" by James Legge, Sacred Books of the East Vol. 39 (1891) - Public Domain
```
