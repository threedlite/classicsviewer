#!/bin/bash

# Controlled sequential download for Homer's Iliad
# Downloads one file at a time with proper verification

BASE_DIR="/Users/user1/git/classicsviewer/audio/homer_iliad_chamberlain_audio/Homer/Iliad"
LOG_FILE="/Users/user1/git/classicsviewer/audio/controlled_download.log"

echo "Homer's Iliad Controlled Download" | tee "$LOG_FILE"
echo "Start: $(date)" | tee -a "$LOG_FILE"
echo "===================================" | tee -a "$LOG_FILE"

# Book line counts
declare -a BOOKS=(
    "1:611" "2:877" "3:461" "4:544" "5:909" "6:529"
    "7:482" "8:565" "9:713" "10:579" "11:848" "12:471"
    "13:837" "14:522" "15:746" "16:867" "17:761" "18:617"
    "19:424" "20:503" "21:611" "22:515" "23:897" "24:804"
)

total_downloaded=0
total_needed=15693

for book_info in "${BOOKS[@]}"; do
    IFS=':' read -r book lines <<< "$book_info"
    book_dir="$BASE_DIR/book_${book}"
    mkdir -p "$book_dir"
    
    echo "" | tee -a "$LOG_FILE"
    echo "Book $book: Processing $lines lines..." | tee -a "$LOG_FILE"
    
    book_count=0
    for line in $(seq 1 $lines); do
        file="$book_dir/line_${line}.mp4"
        
        # Skip if exists and valid
        if [ -f "$file" ] && [ $(stat -f%z "$file" 2>/dev/null || echo 0) -gt 1000 ]; then
            book_count=$((book_count + 1))
            continue
        fi
        
        # Download file
        url="https://hypotactic.com/homer/audio/${book}/line_${line}.mp4"
        if curl -s -L -o "$file" --connect-timeout 10 --max-time 30 "$url"; then
            if [ -f "$file" ] && [ $(stat -f%z "$file" 2>/dev/null || echo 0) -gt 1000 ]; then
                book_count=$((book_count + 1))
            else
                echo "  Failed: Book $book, Line $line (invalid file)" | tee -a "$LOG_FILE"
                rm -f "$file"
            fi
        else
            echo "  Failed: Book $book, Line $line (download error)" | tee -a "$LOG_FILE"
        fi
        
        # Progress update every 50 files
        if [ $((line % 50)) -eq 0 ]; then
            total_downloaded=$((total_downloaded + 50))
            echo "  Book $book: $line/$lines (Total: $total_downloaded/$total_needed)" | tee -a "$LOG_FILE"
        fi
        
        # Small delay to be respectful
        sleep 0.1
    done
    
    echo "Book $book complete: $book_count/$lines files" | tee -a "$LOG_FILE"
done

echo "" | tee -a "$LOG_FILE"
echo "===================================" | tee -a "$LOG_FILE"
echo "Complete: $(date)" | tee -a "$LOG_FILE"

# Final verification
python3 /Users/user1/git/classicsviewer/audio/verify_downloads.py | tee -a "$LOG_FILE"