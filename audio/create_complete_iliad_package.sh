#!/bin/bash

# Script to create the complete Homer Iliad audio package (all 24 books)
# Expected structure in ZIP: Homer/Iliad/book_N/line_X.mp4

PACKAGE_NAME="homer_iliad_complete.zip"
SOURCE_DIR="homer_iliad_chamberlain_audio"

echo "========================================="
echo "Creating Complete Homer Iliad Audio Package"
echo "========================================="

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: $SOURCE_DIR directory not found!"
    exit 1
fi

# Check if Homer/Iliad structure exists
if [ ! -d "$SOURCE_DIR/Homer/Iliad" ]; then
    echo "Error: Expected structure $SOURCE_DIR/Homer/Iliad not found!"
    exit 1
fi

# Count books and files
cd "$SOURCE_DIR"
book_count=$(ls -d Homer/Iliad/book_* 2>/dev/null | wc -l)
echo "Found $book_count books"

# Expected line counts per book
declare -A expected_lines=(
    [1]=611 [2]=877 [3]=461 [4]=544 [5]=909 [6]=529
    [7]=482 [8]=565 [9]=713 [10]=579 [11]=848 [12]=471
    [13]=837 [14]=522 [15]=746 [16]=867 [17]=761 [18]=617
    [19]=424 [20]=503 [21]=611 [22]=515 [23]=897 [24]=804
)

# Verify each book
echo ""
echo "Verifying book contents:"
total_files=0
missing_books=""

for book_num in {1..24}; do
    book_dir="Homer/Iliad/book_${book_num}"
    if [ -d "$book_dir" ]; then
        file_count=$(ls "$book_dir"/*.mp4 2>/dev/null | wc -l)
        expected=${expected_lines[$book_num]}
        total_files=$((total_files + file_count))
        
        if [ $file_count -eq $expected ]; then
            echo "✓ Book $book_num: $file_count files (correct)"
        else
            echo "⚠ Book $book_num: $file_count files (expected $expected)"
        fi
    else
        echo "✗ Book $book_num: MISSING"
        missing_books="$missing_books $book_num"
    fi
done

echo ""
echo "Total files found: $total_files (expected: 15,693)"

if [ -n "$missing_books" ]; then
    echo "Warning: Missing books:$missing_books"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Remove old package if exists
cd ..
if [ -f "$PACKAGE_NAME" ]; then
    echo ""
    echo "Removing existing $PACKAGE_NAME..."
    rm "$PACKAGE_NAME"
fi

# Create the ZIP package
echo ""
echo "Creating ZIP package (this may take a few minutes)..."
cd "$SOURCE_DIR"

# Create ZIP with progress indicator
if command -v pv > /dev/null 2>&1; then
    # Use pv for progress if available
    find Homer -name "*.mp4" -print0 | pv -0 -s $(find Homer -name "*.mp4" | wc -l) | xargs -0 zip -r "../$PACKAGE_NAME"
else
    # Standard zip with verbose output
    zip -r "../$PACKAGE_NAME" Homer
fi

cd ..

# Verify the package
if [ -f "$PACKAGE_NAME" ]; then
    echo ""
    echo "========================================="
    echo "Package created successfully!"
    echo "========================================="
    
    # Show package info
    size=$(ls -lh "$PACKAGE_NAME" | awk '{print $5}')
    echo "File: $PACKAGE_NAME"
    echo "Size: $size"
    
    # Verify ZIP integrity
    echo ""
    echo "Verifying ZIP integrity..."
    if unzip -t "$PACKAGE_NAME" > /dev/null 2>&1; then
        echo "✓ ZIP integrity check passed"
    else
        echo "✗ ZIP integrity check failed!"
        exit 1
    fi
    
    # Count files in ZIP
    zip_count=$(unzip -l "$PACKAGE_NAME" | grep "\.mp4" | wc -l)
    echo "Files in package: $zip_count"
    
    # Show sample structure
    echo ""
    echo "Sample package structure:"
    unzip -l "$PACKAGE_NAME" | grep "book_1/" | head -5
    echo "..."
    unzip -l "$PACKAGE_NAME" | grep "book_24/" | head -5
    
    echo ""
    echo "========================================="
    echo "To deploy to phone:"
    echo "adb push $PACKAGE_NAME /sdcard/Download/"
    echo "========================================="
else
    echo "Error: Failed to create package!"
    exit 1
fi