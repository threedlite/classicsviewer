#!/bin/bash

# Create a simple feature graphic for Google Play Store
# Size: 1024x500 pixels

# Create feature graphic with gradient background
convert -size 1024x500 \
  -define gradient:angle=135 \
  gradient:'#2E7D32'-'#1B5E20' \
  -gravity center \
  -font DejaVu-Sans-Bold \
  -pointsize 72 \
  -fill white \
  -annotate +0-50 "Classics Viewer" \
  -font DejaVu-Sans \
  -pointsize 36 \
  -annotate +0+50 "Read Ancient Greek & Latin Texts" \
  -pointsize 28 \
  -annotate +0+120 "With Dictionary & Morphology" \
  feature_graphic.png

echo "Feature graphic created: feature_graphic.png (1024x500)"