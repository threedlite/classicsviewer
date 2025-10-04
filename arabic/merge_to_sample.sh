#!/bin/bash
# Merge Arabic database into sample database
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Merging Arabic texts database into sample..."
python3 ../merge_database.py arabic_texts.db ../data-prep/perseus_texts_sample.db
