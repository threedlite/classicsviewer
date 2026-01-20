#!/bin/bash
# Run Sanskrit database build with proper venv Python
# This script ensures multiprocessing workers use venv Python with all dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Verify venv exists
if [ ! -f "venv/bin/python3" ]; then
    echo "ERROR: venv/bin/python3 not found!"
    echo "Create venv with: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Verify required packages
if ! ./venv/bin/python3 -c "import indic_transliteration" 2>/dev/null; then
    echo "ERROR: indic_transliteration not installed in venv!"
    echo "Install with: venv/bin/pip install indic-transliteration"
    exit 1
fi

# Run the build
echo "Starting Sanskrit database build..."
echo "Using Python: $(./venv/bin/python3 --version)"
echo "Log file: build_sanskrit.log"
echo ""

nohup ./venv/bin/python3 create_sanskrit_database_interlinear.py > build_sanskrit.log 2>&1 &
BUILD_PID=$!
echo "Build started with PID: $BUILD_PID"
echo ""
echo "Monitor progress with: tail -f build_sanskrit.log"
echo "Check if running: ps -p $BUILD_PID"
