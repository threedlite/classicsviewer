#!/bin/bash
# Run Chinese database build
#
# Usage:
#   ./run_build.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Chinese database build..."
echo "Log file: build.log"
echo ""

nohup python3 create_chinese_database.py > build.log 2>&1 &
BUILD_PID=$!
echo "Build started with PID: $BUILD_PID"
echo ""
echo "Monitor progress with: tail -f build.log"
echo "Check if running: ps -p $BUILD_PID"
