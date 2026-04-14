#!/bin/bash
# Build the all_greek_wiktionary_pages.json cache from a fresh Wiktionary dump.
#
# Reproducible end-to-end build of the Greek pages cache used by the morphology
# extraction pipeline (combine_all_ancient_greek_morphology.py).
#
# Steps:
#   1. Download enwiktionary-latest-pages-articles.xml.bz2 to data-sources/
#      (idempotent — resumes via curl -C - and skips if already complete)
#   2. Verify bz2 integrity (bzip2 -t)
#   3. Run extract_all_greek_pages.py to (re)build all_greek_wiktionary_pages.json
#
# Usage:
#   ./build_greek_pages_cache.sh           # download + extract
#   ./build_greek_pages_cache.sh --el      # also download elwiktionary dump
#                                          # (needed by extract_declension_mappings.py)
#
# Requires the project venv at <project>/venv with Python ≥3.13. Created via:
#   python3 -m venv venv && venv/bin/pip install -r data-prep/requirements.txt
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_SOURCES="$PROJECT_ROOT/data-sources"
VENV_PY="$PROJECT_ROOT/venv/bin/python3"

EN_DUMP_URL="https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2"
EL_DUMP_URL="https://dumps.wikimedia.org/elwiktionary/latest/elwiktionary-latest-pages-articles.xml.bz2"
EN_DUMP="$DATA_SOURCES/enwiktionary-latest-pages-articles.xml.bz2"
EL_DUMP="$DATA_SOURCES/elwiktionary-latest-pages-articles.xml.bz2"
CACHE_FILE="$SCRIPT_DIR/all_greek_wiktionary_pages.json"

DOWNLOAD_EL=0
for arg in "$@"; do
    case "$arg" in
        --el) DOWNLOAD_EL=1 ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

if [ ! -x "$VENV_PY" ]; then
    echo "ERROR: venv Python not found at $VENV_PY" >&2
    echo "Create the venv first: python3 -m venv venv && venv/bin/pip install -r data-prep/requirements.txt" >&2
    exit 1
fi

mkdir -p "$DATA_SOURCES"

download_dump() {
    local url="$1"
    local dest="$2"
    local label="$3"

    echo "=== $label ==="
    echo "URL:  $url"
    echo "Dest: $dest"

    # Resume-friendly download. curl -C - resumes partial transfers and is a no-op
    # if the local file already matches the remote size.
    curl -L -C - --fail --show-error -o "$dest" "$url"
    echo ""

    echo "Verifying bz2 integrity..."
    bzip2 -t "$dest"
    echo "OK ($(du -h "$dest" | cut -f1))"
    echo ""
}

download_dump "$EN_DUMP_URL" "$EN_DUMP" "Downloading English Wiktionary dump"

if [ "$DOWNLOAD_EL" -eq 1 ]; then
    download_dump "$EL_DUMP_URL" "$EL_DUMP" "Downloading Greek Wiktionary dump"
fi

echo "=== Extracting Greek pages cache ==="
echo "Input:  $EN_DUMP"
echo "Output: $CACHE_FILE"
echo ""
cd "$SCRIPT_DIR"
"$VENV_PY" -u extract_all_greek_pages.py --dump "$EN_DUMP" --output "$CACHE_FILE"

echo ""
echo "=== Done ==="
ls -lh "$CACHE_FILE"
