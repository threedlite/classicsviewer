#!/bin/bash
# Latin module build wrapper. Mirrors sanskrit/run_build.sh.
#
# Usage: ./run_build.sh [sample|full|extended]
#   sample    RELEASE content for the Play Store sample APK. Must match the
#             pre-cutover monolith sample byte-for-byte.
#   full      Scan every phi* author under canonical-latinLit/ — ~2min  [default]
#   extended  Currently identical to `full` (same scan). Kept distinct so
#             Latin extended can diverge later without a code change.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
MODE="${1:-full}"

# Always use the repo venv — multiprocessing workers spawn fresh Python which
# doesn't inherit an activated shell venv.
PYTHON="$REPO_ROOT/venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
    echo "ERROR: venv Python not found at $PYTHON"
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON" create_latin_database.py "$MODE"
