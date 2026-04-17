#!/bin/bash
# Greek extended rebuild after a Perseus / First1K / PTA / Wiktionary update.
#
# The interlinear generator needs the DB's dictionary + treebank data to
# produce glosses. After any upstream corpus change, the pipeline must run
# in a specific 3-pass order or the released DB ships stale glosses.
#
#   Pass 1: Build greek_texts.db (extended mode) with whatever XMLs exist.
#           Old XMLs may be stale but won't crash the build; they get
#           overwritten in Pass 3. Produces the fresh dictionary + treebank
#           the generator needs.
#
#   Pass 1.5: Regenerate INTERLINEAR_ALL_GREEK_WITH_IDS.csv from the fresh
#            DB so the generator sees every new work and drops any that
#            were removed from Perseus. Without this, new works ship
#            without interlinear.
#
#   Pass 2: Regenerate all ~2,049 Greek interlinear XMLs against the fresh
#           DB. ~5-7 hours with 8 workers. Atomic write protects against
#           kill-midstream corruption.
#
#   Pass 3: Rebuild greek_texts.db to import the fresh XMLs. This is the
#           DB that goes into assembly.
#
# Usage:
#   ./rebuild_after_update.sh [--workers N]
#
# Options:
#   --workers N   Number of interlinear worker processes (default: 8).
#
# After this finishes, run Latin + assembly separately:
#   cd latin && ./run_build.sh extended && cd ..
#   cd data-prep && python3 assemble_database.py extended && cd ..

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
PYTHON="$REPO_ROOT/venv/bin/python3"
WORKERS=8

while [ $# -gt 0 ]; do
    case "$1" in
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: venv Python not found at $PYTHON" >&2
    exit 1
fi

log_step() {
    echo ""
    echo "================================================================"
    echo "$1"
    echo "================================================================"
}

log_step "[1/3] Pass 1: build greek_texts.db (extended, stale XMLs OK)"
cd "$SCRIPT_DIR"
./run_build.sh extended

log_step "[1.5/3] Regenerate INTERLINEAR_ALL_GREEK_WITH_IDS.csv from fresh DB"
cd "$SCRIPT_DIR/build_modules/generate_interlinear"
"$PYTHON" regenerate_works_csv.py "$SCRIPT_DIR/greek_texts.db"

log_step "[2/3] Pass 2: regenerate all Greek interlinear XMLs (~5-7 hours)"
# run_interlinear_no_sleep.sh blocks until the worker finishes (it calls
# `wait "$PID"`), so we see the real exit status instead of fire-and-forget.
./run_interlinear_no_sleep.sh \
    INTERLINEAR_ALL_GREEK_WITH_IDS.csv \
    "$SCRIPT_DIR/greek_texts.db" \
    "$WORKERS"

log_step "[3/3] Pass 3: rebuild greek_texts.db importing fresh XMLs"
cd "$SCRIPT_DIR"
./run_build.sh extended

log_step "Greek extended rebuild complete"
echo "Next steps:"
echo "  cd latin && ./run_build.sh extended && cd .."
echo "  cd data-prep && python3 assemble_database.py extended && cd .."
