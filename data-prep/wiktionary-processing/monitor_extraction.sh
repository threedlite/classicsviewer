#!/bin/bash
# Monitor Wiktionary extraction progress

echo "=== Wiktionary Extraction Monitor ==="
echo "Started at: $(date)"
echo

while true; do
    # Check if process is still running
    if ! pgrep -f "extract_all_corpus_definitions.py extract" > /dev/null; then
        echo "Extraction process completed or stopped!"
        break
    fi
    
    # Check latest checkpoint
    latest_checkpoint=$(ls -t wiktionary_extraction_results/wiktionary_checkpoint_*.json 2>/dev/null | head -1)
    if [ -n "$latest_checkpoint" ]; then
        count=$(basename "$latest_checkpoint" | grep -o '[0-9]*' | tail -1)
        echo "[$(date +%H:%M:%S)] Progress: $count entries extracted"
    fi
    
    # Check log file
    if [ -f extraction_log.txt ]; then
        tail -5 extraction_log.txt | grep -E "(Progress:|Found:|Rate:)" || true
    fi
    
    sleep 300  # Check every 5 minutes
done

echo
echo "=== Final Results ==="
if [ -f wiktionary_extraction_results/wiktionary_definitions_final.json ]; then
    echo "Extraction completed successfully!"
    entries=$(jq 'length' wiktionary_extraction_results/wiktionary_definitions_final.json)
    echo "Total entries extracted: $entries"
else
    echo "Extraction did not complete normally."
fi