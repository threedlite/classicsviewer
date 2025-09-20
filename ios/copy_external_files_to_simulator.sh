#!/bin/bash

# Copy importable files to simulator to be able to access them for import:
# data-prep/perseus_texts_full.db.zip
# audio/homer_iliad_chamberlain_audio.zip
# custom_dictionary/test_dictionary.zip

# Get the booted simulator device ID
DEVICE_ID=$(xcrun simctl list devices | grep "Booted" | head -1 | grep -o '([A-F0-9-]*)' | tr -d '()')

if [ -z "$DEVICE_ID" ]; then
    echo "No booted simulator found. Please boot a simulator first."
    exit 1
fi

echo "Using simulator: $DEVICE_ID"

# Get the app container for our app (to access Documents directory)
APP_CONTAINER=$(xcrun simctl get_app_container $DEVICE_ID com.classicsviewer.app data 2>/dev/null)

if [ -z "$APP_CONTAINER" ]; then
    echo "App not installed on simulator. Please install the app first."
    exit 1
fi

DOCUMENTS_DIR="$APP_CONTAINER/Documents"
echo "App Documents directory: $DOCUMENTS_DIR"

# Create Documents directory if it doesn't exist
mkdir -p "$DOCUMENTS_DIR"

# Copy database files if they exist
if [ -f "../data-prep/perseus_texts_full.db.zip" ]; then
    echo "Copying perseus_texts_full.db.zip..."
    cp "../data-prep/perseus_texts_full.db.zip" "$DOCUMENTS_DIR/"
    echo "✓ Copied perseus_texts_full.db.zip"
else
    echo "⚠ perseus_texts_full.db.zip not found in ../data-prep/"
fi

# Copy audio files if they exist
if [ -f "../audio/homer_iliad_chamberlain_audio.zip" ]; then
    echo "Copying homer_iliad_chamberlain_audio.zip..."
    cp "../audio/homer_iliad_chamberlain_audio.zip" "$DOCUMENTS_DIR/"
    echo "✓ Copied homer_iliad_chamberlain_audio.zip"
else
    echo "⚠ homer_iliad_chamberlain_audio.zip not found in ../audio/"
fi

# Copy custom dictionary if it exists
if [ -f "../custom_dictionary/test_dictionary.zip" ]; then
    echo "Copying test_dictionary.zip..."
    cp "../custom_dictionary/test_dictionary.zip" "$DOCUMENTS_DIR/"
    echo "✓ Copied test_dictionary.zip"
else
    echo "⚠ test_dictionary.zip not found in ../custom_dictionary/"
fi

# List the files in Documents to confirm
echo ""
echo "Files in app's Documents directory:"
ls -lah "$DOCUMENTS_DIR"

echo ""
echo "Files are now available for import in the app via Settings > Database > Import from Path"
echo "Use these filenames:"
echo "  • perseus_texts_full.db.zip"
echo "  • homer_iliad_chamberlain_audio.zip"
echo "  • test_dictionary.zip"
