#!/bin/bash

# Create final Play Store icon with proper scaling
# Google Play Store requires 512x512 PNG

# Create SVG with better proportions - scale up the icon content
cat > temp_icon_final.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
    <rect width="512" height="512" fill="#2E7D32"/>
    <g transform="translate(256,256) scale(6,6) translate(-12,-12)">
        <path fill="white" d="M24,2C22.09,2 20.25,2.64 18.78,3.78L12,10.5L5.22,3.78C3.75,2.64 1.91,2 0,2H24M24,8C24,9.1 23.1,10 22,10C20.9,10 20,9.1 20,8C20,6.9 20.9,6 22,6C23.1,6 24,6.9 24,8M2,8C2,9.1 2.9,10 4,10C5.1,10 6,9.1 6,8C6,6.9 5.1,6 4,6C2.9,6 2,6.9 2,8M12,14L19,21H5L12,14Z" />
    </g>
</svg>
EOF

# Convert to PNG
convert -background none temp_icon_final.svg -resize 512x512 play_store_icon_final.png

# Clean up
rm temp_icon_final.svg

# Replace the old icon
mv play_store_icon_final.png play_store_icon.png

echo "Successfully created new play_store_icon.png (512x512)"
echo "The icon shows a classical Greek temple design matching the app's theme"