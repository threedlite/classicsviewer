#!/bin/bash
# Download Bhagavad Gita English translation by Annie Besant (1922, 4th edition)
# From English Wikisource
# License: Public Domain

base_url="https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)"

echo "Downloading Bhagavad Gita - Besant translation (18 discourses)..."

for i in {1..18}; do
    url="${base_url}/Discourse_${i}"
    output="bhagavad_gita_besant_${i}.html"

    echo "Downloading Discourse ${i}..."
    curl -s "$url" > "$output"

    # Brief delay to be respectful
    sleep 1
done

echo "Download complete!"
echo "Downloaded 18 discourses"
