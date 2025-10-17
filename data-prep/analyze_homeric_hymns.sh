#!/bin/bash

DB="perseus_texts_full.db"
OUTPUT_DIR="homeric_hymns_coverage"
COMBINED_CSV="homeric_hymns_complete_coverage.csv"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get all Homeric Hymns work IDs
WORK_IDS=$(sqlite3 "$DB" "SELECT id FROM works WHERE author_id = 'tlg0013' ORDER BY id;")

echo "Analyzing 33 Homeric Hymns..."
echo "This may take a few minutes..."
echo ""

# Write CSV header
echo "word,status,sources,author,work,language" > "$COMBINED_CSV"

count=0
total=33

# Process each hymn
for work_id in $WORK_IDS; do
    count=$((count + 1))
    
    # Get work title
    title=$(sqlite3 "$DB" "SELECT title_english FROM works WHERE id = '$work_id';")
    
    echo "[$count/$total] Processing: $title ($work_id)"
    
    # Run analysis and append to combined CSV (skip header for all but first)
    temp_csv="${OUTPUT_DIR}/${work_id}_coverage.csv"
    
    python3 check_dictionary_coverage.py \
        --db "$DB" \
        --work-id "$work_id" \
        --csv "$temp_csv" > /dev/null 2>&1
    
    # Append to combined CSV (skip header line)
    if [ -f "$temp_csv" ]; then
        tail -n +2 "$temp_csv" >> "$COMBINED_CSV"
    fi
done

echo ""
echo "Complete! Results saved to:"
echo "  - Individual hymns: $OUTPUT_DIR/"
echo "  - Combined results: $COMBINED_CSV"
echo ""

# Generate summary statistics
echo "SUMMARY STATISTICS"
echo "=================="
total_words=$(tail -n +2 "$COMBINED_CSV" | wc -l | tr -d ' ')
has_def=$(grep ",has_definition," "$COMBINED_CSV" | wc -l | tr -d ' ')
morph_only=$(grep ",morphology_only," "$COMBINED_CSV" | wc -l | tr -d ' ')
no_entry=$(grep ",no_entry," "$COMBINED_CSV" | wc -l | tr -d ' ')

echo "Total unique words: $total_words"
echo "Words with definitions: $has_def ($(echo "scale=1; $has_def * 100 / $total_words" | bc)%)"
echo "Words with morphology only: $morph_only ($(echo "scale=1; $morph_only * 100 / $total_words" | bc)%)"
echo "Words with NO entry: $no_entry ($(echo "scale=1; $no_entry * 100 / $total_words" | bc)%)"
echo ""
echo "Words with NO entry:"
echo "-------------------"
grep ",no_entry," "$COMBINED_CSV" | cut -d',' -f1 | head -20
if [ $no_entry -gt 20 ]; then
    echo "... and $((no_entry - 20)) more"
fi
