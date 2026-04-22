#!/bin/bash
# Download Bhagavad Gita English translation by Annie Besant (1922, 4th edition)
# From English Wikisource
# License: Public Domain

base_url="https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)"

echo "Downloading Bhagavad Gita - Besant translation (18 discourses)..."

# Minimum plausible discourse size; Wikimedia error pages are ~2 KB.
min_size=30000
max_attempts=3
failed=()

for i in {1..18}; do
    url="${base_url}/Discourse_${i}"
    output="bhagavad_gita_besant_${i}.html"

    echo "Downloading Discourse ${i}..."

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

    # Brief delay to be respectful
    sleep 1
done

echo ""
if [ ${#failed[@]} -ne 0 ]; then
    echo "ERROR: download failed for discourse(s): ${failed[*]}" >&2
    exit 1
fi
echo "Download complete!"
echo "Downloaded 18 discourses"
