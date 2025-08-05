#!/bin/bash
# Run all Wiktionary integration steps

cd /home/user/classics-viewer/data-prep/wiktionary-processing

echo "=== Wiktionary Integration Process ==="
echo "Started at: $(date)"
echo

# Step 1: Wait for extraction to complete
echo "Step 1: Waiting for extraction to complete..."
while pgrep -f "extract_all_corpus_definitions.py extract" > /dev/null; do
    latest_checkpoint=$(ls -t wiktionary_extraction_results/wiktionary_checkpoint_*.json 2>/dev/null | head -1)
    if [ -n "$latest_checkpoint" ]; then
        count=$(basename "$latest_checkpoint" | grep -o '[0-9]*' | tail -1)
        echo "[$(date +%H:%M:%S)] Progress: $count entries extracted"
    fi
    sleep 600  # Check every 10 minutes
done

# Check if extraction completed successfully
if [ ! -f wiktionary_extraction_results/wiktionary_definitions_final.json ]; then
    echo "ERROR: Extraction did not complete successfully!"
    exit 1
fi

echo "Extraction completed!"
entries=$(jq 'length' wiktionary_extraction_results/wiktionary_definitions_final.json)
echo "Total entries extracted: $entries"

# Step 2: Add definitions to database
echo
echo "Step 2: Adding definitions to database..."
python3 extract_all_corpus_definitions.py add

# Step 3: Rebuild database with all improvements
echo
echo "Step 3: Rebuilding database..."
cd /home/user/classics-viewer/data-prep
python3 build_database.py

# Step 4: Create OBB file
echo
echo "Step 4: Creating OBB file..."
cd output
cp perseus_texts.db main.1.com.classicsviewer.app.debug.obb
echo "OBB file created: $(ls -lh main.1.com.classicsviewer.app.debug.obb | awk '{print $5}')"

echo
echo "=== All Steps Completed ==="
echo "Finished at: $(date)"
echo
echo "Next steps:"
echo "1. Deploy to Android device with:"
echo "   adb push output/main.1.com.classicsviewer.app.debug.obb /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/"
echo "2. Test coverage on Odyssey sample"