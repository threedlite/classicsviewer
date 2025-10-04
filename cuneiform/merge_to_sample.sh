#!/bin/bash
# Merge cuneiform database into sample database
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Merging Sumerian/Akkadian database into sample..."
python3 ../merge_database.py sumerian_texts.db ../data-prep/perseus_texts_sample.db
