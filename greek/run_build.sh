#!/bin/bash
# Greek module build wrapper. Mirrors latin/run_build.sh and sanskrit/run_build.sh.
#
# Usage: ./run_build.sh [sample|full|extended|ios]
#
# Greek processing code is vendored under greek/build_modules/; no dependency
# on data-prep/ beyond shared/database_schema.py and the top-level
# merge_database.py.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
MODE="${1:-sample}"

PYTHON="$REPO_ROOT/venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
    echo "ERROR: venv Python not found at $PYTHON"
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON" create_greek_database.py "$MODE"
