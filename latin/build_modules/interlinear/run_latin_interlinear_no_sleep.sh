#!/bin/bash
# Wrapper script to run Latin interlinear generation without idle sleep interruptions
# Usage: ./run_latin_interlinear_no_sleep.sh <works_csv> <database_path> <num_workers>
# Example: ./run_latin_interlinear_no_sleep.sh INTERLINEAR_ALL_LATIN_WITH_IDS.csv ../../perseus_texts_full.db 8

# Fail loudly. Without these a failing step scrolls past and the wrapper still
# exits 0, so the caller sees success while no XML was written. latin/run_build.sh
# has had `set -e` since it was written; this driver did not.
#   -e           stop on the first failing command
#   -o pipefail  a failure anywhere in a pipeline fails the pipeline
#
# `-u` is deliberately NOT set. macOS ships bash 3.2, where expanding an EMPTY
# array under `set -u` aborts with "unbound variable" -- and CAFFEINATE=() is
# exactly that whenever caffeinate is unavailable. Verified on
# GNU bash 3.2.57(1)-release: `set -u; A=(); echo "${A[@]}"` fails. Adding -u
# here would break the no-caffeinate path outright.
set -e
set -o pipefail

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

# Use caffeinate only on macOS (where it exists and is needed to prevent idle sleep)
if [[ "$(uname)" == "Darwin" ]] && command -v caffeinate >/dev/null 2>&1; then
    CAFFEINATE=(caffeinate -i)
else
    CAFFEINATE=()
fi

echo "======================================================================="
if [ ${#CAFFEINATE[@]} -gt 0 ]; then
    echo "Latin Interlinear Generator (with caffeinate to prevent idle sleep)"
else
    echo "Latin Interlinear Generator (caffeinate not available on this platform)"
fi
echo "======================================================================="
echo "Works CSV: $WORKS_CSV"
echo "Database: $DATABASE_PATH"
echo "Workers: $NUM_WORKERS"
echo "Log file: $LOGFILE"
echo ""
echo "Process will run continuously until completion."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$SCRIPT_DIR"

# Use the project venv explicitly. Bare `python3` is the system interpreter and
# has no stanza, so the generator silently degrades to POS-less output: it still
# reports "Successful", but every token loses its "~ POS DEPREL HEAD" block and
# the run finishes in seconds instead of an hour. Fail loudly instead.
PROJECT_VENV_PY="$(cd "$SCRIPT_DIR/../../.." && pwd)/venv/bin/python3"
if [ ! -x "$PROJECT_VENV_PY" ]; then
    echo "ERROR: project venv not found at $PROJECT_VENV_PY" >&2
    exit 1
fi
if ! "$PROJECT_VENV_PY" -c "import stanza" 2>/dev/null; then
    echo "ERROR: stanza not importable from $PROJECT_VENV_PY" >&2
    echo "Latin interlinear needs it for POS tags. Install it before running." >&2
    exit 1
fi
"${CAFFEINATE[@]}" "$PROJECT_VENV_PY" -u latin_interlinear_list.py "$WORKS_CSV" "$DATABASE_PATH" --workers "$NUM_WORKERS" > "$LOGFILE" 2>&1 &

PID=$!
echo "Background process started with PID: $PID"
if [ ${#CAFFEINATE[@]} -gt 0 ]; then
    echo "Caffeinate is preventing idle sleep for this process."
fi
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

# Forward common signals to the child so Ctrl-C / kill propagates correctly
trap 'kill -TERM "$PID" 2>/dev/null' INT TERM HUP

# Block until the worker finishes so callers (e.g. chain_builds.sh) see the real exit status.
# If you want fire-and-forget behaviour, invoke this script with a trailing & yourself.
wait "$PID"
RC=$?
echo "Latin interlinear generator exited with status $RC"
exit "$RC"
