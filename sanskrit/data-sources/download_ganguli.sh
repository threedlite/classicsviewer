#!/bin/bash
# Download Kisari Mohan Ganguli's English prose translation of the Mahabharata
# (1883-1896) from Project Gutenberg, four volumes:
#   15474  Volume 1, Books 1-3
#   15475  Volume 2, Books 4-7
#   15476  Volume 3, Books 8-12
#   15477  Volume 4, Books 13-18
# Licence: public domain (translator died 1908). Project Gutenberg's terms
# allow unrestricted use once its header, licence and name are removed; the
# build strips everything outside the "*** START OF" / "*** END OF" markers
# and verifies a SHA-256 of the text between them (see mahabharata_ganguli.py).
#
# The build calls this script itself when the files are missing, so there is
# no manual step; running it by hand only pre-fetches the files.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/ganguli"
mkdir -p "$OUT_DIR"

for n in 15474 15475 15476 15477; do
    out="$OUT_DIR/pg$n.txt"
    if [ -s "$out" ]; then
        echo "exists: $out"
        continue
    fi
    url="https://www.gutenberg.org/cache/epub/$n/pg$n.txt"
    echo "downloading $url"
    curl -fsSL -A "classicsviewer-build (https://github.com/) curl" -o "$out.part" "$url"
    mv "$out.part" "$out"
    echo "saved: $out ($(wc -c < "$out") bytes)"
done
