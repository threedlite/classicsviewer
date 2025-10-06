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

# Download each chapter
for i in {1..18}; do
    output="bhagavad_gita_en_${i}.html"
    url="${base_url}/Chapter_${i}"

    echo "Downloading Chapter ${i}..."
    curl -s "$url" -o "$output"

    # Small delay to be respectful to server
    sleep 0.5
done

echo ""
echo "Download complete! Downloaded 18 chapters."
echo "Files: bhagavad_gita_en_*.html"
