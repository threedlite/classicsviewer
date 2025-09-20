# Build Modules Directory

This directory contains all the Python modules used by create_perseus_database.py
for building the Perseus texts database.

## Structure

- All dictionary extraction scripts (extract_*.py)
- All combination and normalization scripts (combine_*.py, add_*.py, normalize_*.py)
- The main pipeline coordinator (run_complete_pipeline.py)
- Supporting utilities (normalization_utils.py, load_combined_dictionaries.py)

## Generated Files

All JSON files generated during the build process are stored in this directory:
- combine_dictionaries_to_lemma_map_1.json (dictionary entries)
- combine_dictionaries_to_lemma_map_2.json (lemma mappings)
- add_grave_accent_variants.json (with grave accents)
- add_enclitic_variants.json (final mappings with all variants)
- extract_*.json (intermediate extraction results)

## Usage

These modules are imported and used by ../create_perseus_database.py
Do not run these scripts directly unless debugging.