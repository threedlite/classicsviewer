#!/bin/bash
# Download Bhagavad Gita Sanskrit text from Sanskrit Wikisource
# Source: https://sa.wikisource.org/wiki/भगवद्गीता
# License: CC BY-SA 4.0
# 18 chapters (Adhyayas)

echo "Downloading Bhagavad Gita Sanskrit text from Sanskrit Wikisource"
echo "================================================================="

# Base URL for Sanskrit Wikisource
base_url="https://sa.wikisource.org/wiki/भगवद्गीता"

# Chapter names in Devanagari (1-18)
chapters=(
    "अर्जुनविषादयोगः"
    "साङ्ख्ययोगः"
    "कर्मयोगः"
    "ज्ञानकर्मसंन्यासयोगः"
    "कर्मसंन्यासयोगः"
    "आत्मसंयमयोगः"
    "ज्ञानविज्ञानयोगः"
    "अक्षरब्रह्मयोगः"
    "राजविद्याराजगुह्ययोगः"
    "विभूतियोगः"
    "विश्वरूपदर्शनयोगः"
    "भक्तियोगः"
    "क्षेत्रक्षेत्रज्ञविभागयोगः"
    "गुणत्रयविभागयोगः"
    "पुरुषोत्तमयोगः"
    "दैवासुरसम्पद्विभागयोगः"
    "श्रद्धात्रयविभागयोगः"
    "मोक्षसंन्यासयोगः"
)

# Minimum plausible size for a real chapter HTML; Wikimedia error pages are ~2 KB.
min_size=50000
max_attempts=3
failed=()

# Download each chapter with size check + retry
for i in {1..18}; do
    chapter="${chapters[$i-1]}"
    output="bhagavad_gita_sa_${i}.html"
    url="${base_url}/${chapter}"

    echo "Downloading Chapter ${i}: ${chapter}..."

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
        failed+=("$i:$chapter")
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
echo "Files: bhagavad_gita_sa_*.html"
