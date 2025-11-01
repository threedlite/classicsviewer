#!/bin/bash
# Wrapper script to run CLTK dictionary generation without idle sleep interruptions
# Usage: ./run_cltk_no_sleep.sh <authors_csv> <num_workers>
# Example: ./run_cltk_no_sleep.sh EXTENDED_AUTHORS_GREEK_ONLY.csv 4

if [ $# -lt 2 ]; then
    echo "Usage: $0 <authors_csv> <num_workers>"
    echo "Example: $0 EXTENDED_AUTHORS_GREEK_ONLY.csv 4"
    exit 1
fi

AUTHORS_CSV="$1"
NUM_WORKERS="$2"
BASENAME=$(basename "$AUTHORS_CSV" .csv)
LOGFILE="${BASENAME}_${NUM_WORKERS}workers.log"

echo "======================================================================="
echo "CLTK Dictionary Generator (with caffeinate to prevent idle sleep)"
echo "======================================================================="
echo "Authors CSV: $AUTHORS_CSV"
echo "Workers: $NUM_WORKERS"
echo "Log file: $LOGFILE"
echo ""
echo "Starting process with caffeinate to prevent system idle sleep..."
echo "Process will run continuously until completion."
echo ""

# Run with caffeinate to prevent idle sleep
caffeinate -i python3 generate_cltk_dictionary.py "$AUTHORS_CSV" "$NUM_WORKERS" > "$LOGFILE" 2>&1 &

PID=$!
echo "Background process started with PID: $PID"
echo "Caffeinate is preventing idle sleep for this process."
echo ""
echo "Monitor progress with:"
echo "  tail -f $LOGFILE"
echo ""
echo "Check process status with:"
echo "  ps -p $PID"
echo ""
echo "To kill the process:"
echo "  kill $PID"
echo "======================================================================="
