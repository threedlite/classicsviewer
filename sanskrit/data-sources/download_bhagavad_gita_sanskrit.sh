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

# Download each chapter
for i in {1..18}; do
    chapter="${chapters[$i-1]}"
    output="bhagavad_gita_sa_${i}.html"
    url="${base_url}/${chapter}"

    echo "Downloading Chapter ${i}: ${chapter}..."
    curl -s "$url" -o "$output"

    # Small delay to be respectful to server
    sleep 0.5
done

echo ""
echo "Download complete! Downloaded 18 chapters."
echo "Files: bhagavad_gita_sa_*.html"
