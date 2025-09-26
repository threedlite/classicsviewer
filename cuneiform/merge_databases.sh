#!/bin/bash

# merge_databases.sh
# Merges data from one database into another, handling language constraints
# Usage: ./merge_databases.sh <source_db> <target_db>

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <source_db> <target_db>"
    echo "Example: $0 sumerian_texts.db ../data-prep/perseus_texts_sample.db"
    exit 1
fi

SOURCE_DB="$1"
TARGET_DB="$2"

if [ ! -f "$SOURCE_DB" ]; then
    echo "Error: Source database '$SOURCE_DB' not found"
    exit 1
fi

if [ ! -f "$TARGET_DB" ]; then
    echo "Error: Target database '$TARGET_DB' not found"
    exit 1
fi

echo "Merging data from '$SOURCE_DB' into '$TARGET_DB'"

# Create a backup of the target database
BACKUP_FILE="${TARGET_DB}.backup.$(date +%Y%m%d_%H%M%S)"
echo "Creating backup: $BACKUP_FILE"
cp "$TARGET_DB" "$BACKUP_FILE"

# Function to check if table exists
table_exists() {
    local db=$1
    local table=$2
    sqlite3 "$db" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"
}

# Function to get columns for a table
get_columns() {
    local db=$1
    local table=$2
    sqlite3 "$db" "PRAGMA table_info($table);" | cut -d'|' -f2 | tr '\n' ',' | sed 's/,$//'
}

# Step 1: Remove the CHECK constraint from dictionary_entries if it exists
echo "Checking for dictionary_entries CHECK constraint..."
if sqlite3 "$TARGET_DB" ".schema dictionary_entries" | grep -q "CHECK.*language.*IN.*'greek'.*'latin'"; then
    echo "Removing language CHECK constraint from dictionary_entries table..."

    # SQLite doesn't support dropping constraints directly, so we need to recreate the table
    sqlite3 "$TARGET_DB" <<EOF
BEGIN TRANSACTION;

-- Create temporary table without the CHECK constraint
CREATE TABLE dictionary_entries_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    headword TEXT NOT NULL,
    headword_normalized_ultra TEXT,
    language TEXT NOT NULL,
    entry_xml TEXT,
    entry_html TEXT,
    entry_plain TEXT,
    source TEXT
);

-- Copy existing data
INSERT INTO dictionary_entries_new
SELECT * FROM dictionary_entries;

-- Drop old table and rename new one
DROP TABLE dictionary_entries;
ALTER TABLE dictionary_entries_new RENAME TO dictionary_entries;

-- Recreate indexes
CREATE INDEX idx_dictionary_headword
ON dictionary_entries(headword, language);

CREATE INDEX idx_dictionary_headword_ultra
ON dictionary_entries(headword_normalized_ultra, language);

COMMIT;
EOF
    echo "CHECK constraint removed successfully"
else
    echo "No CHECK constraint found or already removed"
fi

# Step 2: Merge data from source to target for each table
echo ""
echo "Starting data merge..."

# Get list of tables from source database (excluding sqlite internal tables)
TABLES=$(sqlite3 "$SOURCE_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")

for TABLE in $TABLES; do
    # Check if table exists in target database
    if table_exists "$TARGET_DB" "$TABLE"; then
        echo "Merging table: $TABLE"

        # Get columns from both databases
        SOURCE_COLS=$(get_columns "$SOURCE_DB" "$TABLE")
        TARGET_COLS=$(get_columns "$TARGET_DB" "$TABLE")

        if [ "$SOURCE_COLS" != "$TARGET_COLS" ]; then
            echo "  Warning: Column mismatch for table $TABLE"
            echo "  Source columns: $SOURCE_COLS"
            echo "  Target columns: $TARGET_COLS"
            echo "  Attempting to merge matching columns..."

            # Use only common columns
            COMMON_COLS=$(sqlite3 "$TARGET_DB" <<EOF
ATTACH DATABASE '$SOURCE_DB' AS source;
SELECT GROUP_CONCAT(name)
FROM (
    SELECT name FROM pragma_table_info('$TABLE')
    INTERSECT
    SELECT name FROM pragma_table_info('source.$TABLE')
);
DETACH DATABASE source;
EOF
)
            if [ -z "$COMMON_COLS" ]; then
                echo "  Error: No common columns found for table $TABLE. Skipping."
                continue
            fi
            COLS_TO_USE="$COMMON_COLS"
        else
            COLS_TO_USE="$SOURCE_COLS"
        fi

        # Check if table has AUTOINCREMENT
        HAS_AUTOINCREMENT=$(sqlite3 "$TARGET_DB" ".schema $TABLE" | grep -c "AUTOINCREMENT" || true)

        # Merge the data
        COUNT=$(sqlite3 "$SOURCE_DB" "SELECT COUNT(*) FROM $TABLE;")
        echo "  Copying $COUNT rows..."

        if [ "$HAS_AUTOINCREMENT" -gt 0 ]; then
            # For AUTOINCREMENT tables, exclude the id column and let SQLite generate new ones
            COLS_WITHOUT_ID=$(echo "$COLS_TO_USE" | sed 's/^id,//; s/,id,/,/g; s/,id$//')

            sqlite3 "$TARGET_DB" <<EOF
ATTACH DATABASE '$SOURCE_DB' AS source;
INSERT OR IGNORE INTO main.$TABLE ($COLS_WITHOUT_ID)
SELECT $COLS_WITHOUT_ID FROM source.$TABLE;
DETACH DATABASE source;
EOF
        else
            sqlite3 "$TARGET_DB" <<EOF
ATTACH DATABASE '$SOURCE_DB' AS source;
INSERT OR IGNORE INTO main.$TABLE ($COLS_TO_USE)
SELECT $COLS_TO_USE FROM source.$TABLE;
DETACH DATABASE source;
EOF
        fi

        NEW_COUNT=$(sqlite3 "$TARGET_DB" "SELECT COUNT(*) FROM $TABLE;")
        echo "  Table $TABLE now has $NEW_COUNT total rows"
    else
        echo "Warning: Table $TABLE exists in source but not in target. Skipping."
    fi
done

echo ""
echo "Merge completed successfully!"
echo "Backup saved to: $BACKUP_FILE"

# Verify the merge
echo ""
echo "Verification:"
echo "-------------"
for TABLE in authors works books text_lines; do
    if table_exists "$TARGET_DB" "$TABLE"; then
        COUNT=$(sqlite3 "$TARGET_DB" "SELECT COUNT(*) FROM $TABLE;")
        echo "$TABLE: $COUNT rows"
    fi
done

# Check language diversity in dictionary_entries
if table_exists "$TARGET_DB" "dictionary_entries"; then
    echo ""
    echo "Dictionary entries by language:"
    sqlite3 "$TARGET_DB" "SELECT language, COUNT(*) as count FROM dictionary_entries GROUP BY language ORDER BY count DESC;"
fi

# Check language diversity in authors
if table_exists "$TARGET_DB" "authors"; then
    echo ""
    echo "Authors by language:"
    sqlite3 "$TARGET_DB" "SELECT language, COUNT(*) as count FROM authors GROUP BY language ORDER BY count DESC;"
fi