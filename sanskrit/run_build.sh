#!/bin/bash
# Run Sanskrit database build with proper venv Python
# This script ensures multiprocessing workers use venv Python with all dependencies
#
# Usage:
#   ./run_build.sh          # Full build (all 268 works)
#   ./run_build.sh test     # Test build (BG + RV only)
#   ./run_build.sh sample   # Sample build (BG + RV + selected works)
#   ./run_build.sh full     # Full build (all 268 works)
#   ./run_build.sh full WORKS.csv name
#                           # Only the works in WORKS.csv, written to
#                           # sanskrit_texts_<name>.db (+ interlinear_output_<name>/,
#                           # build_sanskrit_<name>.log); the main DB is untouched

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get build mode from argument, default to full; optional works CSV and output name
BUILD_MODE="${1:-full}"
WORKS_CSV="${2:-}"
OUTPUT_NAME="${3:-}"
LOG_FILE="build_sanskrit${OUTPUT_NAME:+_$OUTPUT_NAME}.log"

# Locate project venv (sanskrit/ → project root)
PROJECT_VENV_PY="$(cd "$SCRIPT_DIR/.." && pwd)/venv/bin/python3"
if [ ! -x "$PROJECT_VENV_PY" ]; then
    echo "ERROR: project venv not found at $PROJECT_VENV_PY"
    echo "Create with: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Verify required packages
if ! "$PROJECT_VENV_PY" -c "import indic_transliteration" 2>/dev/null; then
    echo "ERROR: indic_transliteration not installed in venv!"
    echo "Install with: venv/bin/pip install indic-transliteration"
    exit 1
fi

# Run the build
echo "Starting Sanskrit database build (${BUILD_MODE} mode)..."
echo "Using Python: $($PROJECT_VENV_PY --version)"
echo "Log file: $LOG_FILE"
echo ""

nohup "$PROJECT_VENV_PY" create_sanskrit_database_interlinear.py "$BUILD_MODE" ${WORKS_CSV:+"$WORKS_CSV"} ${OUTPUT_NAME:+"$OUTPUT_NAME"} > "$LOG_FILE" 2>&1 &
BUILD_PID=$!
echo "Build started with PID: $BUILD_PID"
echo ""
echo "Monitor progress with: tail -f $LOG_FILE"
echo "Check if running: ps -p $BUILD_PID"
