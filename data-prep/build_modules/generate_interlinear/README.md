# Interlinear Translation Generator

This module generates word-by-word interlinear translations for Homer's Iliad and Odyssey.

## Integration into Build Pipeline

The interlinear generator is now integrated into the main database build process (`create_perseus_database.py`). After each database is built and compressed, the interlinear translations are automatically generated.

### Build Process Flow

1. Database creation (sample/full/extended)
2. Dictionary and morphology merging
3. OGA lemma extraction (if not skipped)
4. WAL checkpoint
5. Database compression
6. **→ Interlinear translation generation** (NEW)

### Usage from Build Pipeline

The module is imported and called automatically:

```python
from build_modules.generate_interlinear.generate_interlinear import generate_interlinear_translations

# After database build completes:
interlinear_output_dir = Path(__file__).parent / "build_modules" / "generate_interlinear"
generate_interlinear_translations(
    db_path=Path("perseus_texts_sample.db"),
    output_dir=interlinear_output_dir,
    works=['iliad', 'odyssey']
)
```

### Output Files

Generated files are placed in `data-prep/build_modules/generate_interlinear/`:

- `tlg0012.tlg001.perseus-eng99.xml` - Iliad TEI XML
- `iliad_full_interlinear.txt` - Iliad plain text (pipe-delimited)
- `tlg0012.tlg002.perseus-eng99.xml` - Odyssey TEI XML
- `odyssey_full_interlinear.txt` - Odyssey plain text (pipe-delimited)

### Migration from seg_trans

Previously, interlinear generation was in `seg_trans/prototype_interlinear.py` and run manually. Now it's:

1. **Integrated**: Part of the regular build process
2. **Modular**: Clean API for programmatic usage
3. **Organized**: Lives in `build_modules/` with other build components

The `seg_trans/` directory will be removed in a future update.

## API

### generate_interlinear_translations()

```python
def generate_interlinear_translations(db_path: Path, output_dir: Path, works=None):
    """
    Generate interlinear translations for Homer's works

    Args:
        db_path: Path to the Perseus database
        output_dir: Directory where XML files will be written
        works: List of works to process (e.g., ['iliad', 'odyssey']).
               If None, processes both.
    """
```

### Features

- **Exact Android UI dictionary logic**: Uses `ui_dictionary_lookup.py` for consistency
- **HTML table formatting**: Each word formatted as a table for proper display
- **TEI XML output**: Perseus-compatible XML format
- **Plain text output**: Pipe-delimited format for easy analysis

## Output Format

### XML Format (used in app)

Each word is formatted as an HTML table:

```xml
<table><tr><td>μῆνιν</td></tr><tr><td><b>wrath, anger</b></td></tr><tr><td>μῆνις acc s</td></tr></table>
<table><tr><td>ἄειδε</td></tr><tr><td><b>to sing</b></td></tr><tr><td>ἀείδω 2 s pres actv impr</td></tr></table>
```

This renders as:

| μῆνιν |
|-------|
| **wrath, anger** |
| μῆνις acc s |

| ἄειδε |
|-------|
| **to sing** |
| ἀείδω 2 s pres actv impr |

### Text Format (for debugging)

```
1. μῆνιν | ἄειδε | θεὰ
wrath, anger | to sing | a goddess

```

## Dictionary Lookup

Uses `ui_dictionary_lookup.py` which implements the exact same logic as the Android app:

1. Normalizes apostrophes and grave accents
2. Checks `lemma_map` table with confidence scoring
3. Follows lemma chains to find canonical forms
4. Applies source priority: User > LSJ > Cunliffe > Wiktionary
5. Returns top 5 sorted entries

## Next Steps

The interlinear translations can now be:
- Imported into the Android app database
- Used for study tools and language learning features
- Exported to other formats as needed
