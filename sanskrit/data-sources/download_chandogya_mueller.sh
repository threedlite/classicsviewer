#!/bin/bash
# Download F. Max Müller's translation of the Chāndogya Upaniṣad (Sacred
# Books of the East, vol. 1, 1879; public domain) from English Wikisource,
# one rendered page per prapāṭhaka, via the MediaWiki API.
#   https://en.wikisource.org/wiki/Sacred_Books_of_the_East/Volume_1/Khândogya-upanishad
# Wikisource text: public-domain translation; contributions CC BY-SA.
#
# The build runs this script itself when the files are missing (see
# create_sanskrit_database_interlinear.py), so there is no manual step.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/mueller"
mkdir -p "$OUT_DIR"
UA="classicsviewer-build/1.0 (https://github.com/threedlite/classicsviewer)"

ordinals=(First Second Third Fourth Fifth Sixth Seventh Eighth)
for i in 1 2 3 4 5 6 7 8; do
    out="$OUT_DIR/chandogya_$i.html"
    if [ -s "$out" ]; then
        echo "exists: $out"
        continue
    fi
    page="Sacred Books of the East/Volume 1/Khândogya-upanishad/${ordinals[$((i-1))]} Prapâthaka"
    echo "downloading prapathaka $i: $page"
    curl -fsSL -A "$UA" -G "https://en.wikisource.org/w/api.php" \
        --data-urlencode "action=parse" --data-urlencode "page=$page" \
        --data-urlencode "prop=text" --data-urlencode "format=json" \
        --data-urlencode "disabletoc=1" -o "$out.json"
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); open(sys.argv[2],'w').write(d['parse']['text']['*'])" "$out.json" "$out"
    rm -f "$out.json"
    echo "saved: $out ($(wc -c < "$out") bytes)"
done
