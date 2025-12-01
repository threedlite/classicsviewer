#!/bin/bash
# Wrapper script to run Latin interlinear generation without idle sleep interruptions
# Usage: ./run_latin_interlinear_no_sleep.sh <works_csv> <database_path> <num_workers>
# Example: ./run_latin_interlinear_no_sleep.sh INTERLINEAR_ALL_LATIN_WITH_IDS.csv ../../perseus_texts_full.db 8

if [ $# -lt 3 ]; then
    echo "Usage: $0 <works_csv> <database_path> <num_workers>"
    echo "Example: $0 INTERLINEAR_ALL_LATIN_WITH_IDS.csv ../../perseus_texts_full.db 8"
    exit 1
fi

WORKS_CSV="$1"
DATABASE_PATH="$2"
NUM_WORKERS="$3"
BASENAME=$(basename "$WORKS_CSV" .csv)
LOGFILE="latin_generation.log"

echo "======================================================================="
echo "Latin Interlinear Generator (with caffeinate to prevent idle sleep)"
echo "======================================================================="
echo "Works CSV: $WORKS_CSV"
echo "Database: $DATABASE_PATH"
echo "Workers: $NUM_WORKERS"
echo "Log file: $LOGFILE"
echo ""
echo "Starting process with caffeinate to prevent system idle sleep..."
echo "Process will run continuously until completion."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run with caffeinate to prevent idle sleep
cd "$SCRIPT_DIR"
caffeinate -i python3 latin_interlinear_list.py "$WORKS_CSV" "$DATABASE_PATH" --workers "$NUM_WORKERS" > "$LOGFILE" 2>&1 &

PID=$!
echo "Background process started with PID: $PID"
echo "Caffeinate is preventing idle sleep for this process."
echo ""
echo "Monitor progress with:"
echo "  tail -f $SCRIPT_DIR/$LOGFILE"
echo ""
echo "Check process status with:"
echo "  ps -p $PID"
echo ""
echo "Check completed works count:"
echo "  grep '✓ Work.*complete' $SCRIPT_DIR/$LOGFILE | wc -l"
echo ""
echo "To kill the process:"
echo "  kill $PID"
echo "======================================================================="
