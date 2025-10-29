# EXTENDED_AUTHORS.csv - Complete Author and Work List

This file contains all authors and works from the **extended database**, which includes:
- All Perseus Digital Library works (Greek and Latin)
- All non-duplicate First1KGreek works

## Statistics
- **Total Works**: 2,145
- **Total Authors**: 457
- **Perseus Works**: 1,062
- **First1KGreek Works**: 1,083

## Purpose

This file serves as a **starting point** for creating custom sample databases. You can:
1. Copy this file to create your own selection (e.g., `MY_CUSTOM_AUTHORS.csv`)
2. Edit it to include only the works you want
3. Build a sample database with your custom selection

## Usage

### Creating a Custom Sample Database

```bash
# 1. Copy and edit the file
cp EXTENDED_AUTHORS.csv MY_CUSTOM_AUTHORS.csv
# Edit MY_CUSTOM_AUTHORS.csv to include only desired works

# 2. Build database with your custom list
python3 create_perseus_database.py sample MY_CUSTOM_AUTHORS.csv
```

### Default Behavior

If you don't specify a CSV file, the script uses `SAMPLE_AUTHORS.csv`:
```bash
python3 create_perseus_database.py sample
```

## Format

The CSV has two columns:
- **Author**: The author's name (exactly as stored in database)
- **Work**: The work's English title (exactly as stored in database)

Example:
```csv
Author,Work
Homer,Iliad
Homer,Odyssey
Plato,Republic
```

## Notes About Duplicates

You may notice some works appear multiple times (14 exact duplicates). This happens when:
- A work exists in both Perseus and First1KGreek collections
- Different editions or translations of the same work

**This is intentional** - you can choose which version to include or include both.

## Languages Included

The extended database includes works in:
- **Ancient Greek** (majority)
- **Latin** (Virgil, Horace, etc.)
- **Biblical Hebrew** (Old Testament)
- **Koine Greek** (New Testament)
- **Sanskrit** (Vedic texts)
- **Arabic** (classical poetry)

## Regenerating This File

To regenerate after rebuilding the extended database:

```bash
cd data-prep
python3 create_extended_authors_csv.py
```

This will extract the latest author/work list from `perseus_texts_extended.db`.
