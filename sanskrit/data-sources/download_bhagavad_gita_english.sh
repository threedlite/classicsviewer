#!/bin/bash
# Download Bhagavad Gita English translation from English Wikisource
# Source: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)
# Translator: Edwin Arnold
# License: Public Domain (1885 translation)
# 18 chapters

echo "Downloading Bhagavad Gita English translation from English Wikisource"
echo "====================================================================="

# Base URL for English Wikisource
base_url="https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)"

# Minimum plausible chapter size; Wikimedia error pages are ~2 KB.
min_size=20000
max_attempts=3
failed=()

# Download each chapter with size check + retry
for i in {1..18}; do
    output="bhagavad_gita_en_${i}.html"
    url="${base_url}/Chapter_${i}"

    echo "Downloading Chapter ${i}..."

    attempt=1
    size=0
    while [ $attempt -le $max_attempts ]; do
        curl -sS --fail -o "$output" "$url" && size=$(wc -c < "$output") || size=0
        if [ "$size" -ge "$min_size" ]; then
            break
        fi
        echo "  attempt ${attempt} returned ${size} bytes (< ${min_size}); retrying..."
        attempt=$((attempt + 1))
        sleep 2
    done

    if [ "$size" -lt "$min_size" ]; then
        failed+=("$i")
    fi

    # Small delay to be respectful to server
    sleep 0.5
done

echo ""
if [ ${#failed[@]} -ne 0 ]; then
    echo "ERROR: download failed for chapter(s): ${failed[*]}" >&2
    exit 1
fi
echo "Download complete! Downloaded 18 chapters."
echo "Files: bhagavad_gita_en_*.html"
