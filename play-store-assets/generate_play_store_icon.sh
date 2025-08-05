#!/bin/bash

# Generate 512x512 icon for Google Play Store from the vector drawable

# Create a simple icon based on the app theme
# Green background with a stylized book/scroll icon

convert -size 512x512 \
  -background '#2E7D32' \
  xc:'#2E7D32' \
  -fill white \
  -gravity center \
  -font DejaVu-Sans-Bold \
  -pointsize 240 \
  -annotate +0+0 "C" \
  -fill '#1B5E20' \
  -draw "rectangle 140,360 372,380" \
  -draw "rectangle 140,390 372,410" \
  play_store_icon.png

echo "Play Store icon created: play_store_icon.png (512x512)"
echo ""
echo "If you have a better icon design, you can replace this file."
echo "Requirements: 512x512 PNG, 32-bit color, no transparency"