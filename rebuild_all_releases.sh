#!/bin/bash
# Full end-to-end rebuild of all 4 release targets (sample, full, extended, ios).
# Total wall time: ~10 hours (Greek extended interlinear regeneration dominates).
#
# The sequence matters because greek/greek_texts.db gets overwritten by each
# mode's build. We build + assemble in order from longest to shortest so
# each mode's assembly reads the right module DB before the next rebuild
# stomps on it.
#
# Order:
#   1. Extended (includes full interlinear regen — ~8 hrs)
#   2. Full
#   3. Sample
#   4. iOS (uses greek_texts_ios.db + latin_texts_ios.db, separate paths)

set -e

REPO=/home/user/git/classicsviewer
PY="$REPO/venv/bin/python3"
LOG="$REPO/rebuild_all.log"

banner() {
    echo ""
    echo "################################################################"
    echo "# $(date '+%H:%M:%S')  $*"
    echo "################################################################"
}

cd "$REPO"

banner "EXTENDED — greek rebuild_after_update.sh (full pipeline ~8 hrs)"
cd "$REPO/greek" && ./rebuild_after_update.sh
cd "$REPO"

banner "EXTENDED — latin extended build"
cd "$REPO/latin" && "$PY" create_latin_database.py extended
cd "$REPO"

banner "EXTENDED — assembly"
cd "$REPO/data-prep" && "$PY" assemble_database.py extended
cd "$REPO"

banner "FULL — greek full build (overwrites greek_texts.db)"
cd "$REPO/greek" && ./run_build.sh full
cd "$REPO"

banner "FULL — latin full build"
cd "$REPO/latin" && "$PY" create_latin_database.py full
cd "$REPO"

banner "FULL — assembly"
cd "$REPO/data-prep" && "$PY" assemble_database.py full
cd "$REPO"

banner "SAMPLE — greek sample build"
cd "$REPO/greek" && ./run_build.sh sample
cd "$REPO"

banner "SAMPLE — latin sample build"
cd "$REPO/latin" && "$PY" create_latin_database.py sample
cd "$REPO"

banner "SAMPLE — assembly"
cd "$REPO/data-prep" && "$PY" assemble_database.py sample
cd "$REPO"

banner "iOS — greek ios build (writes greek_texts_ios.db)"
cd "$REPO/greek" && ./run_build.sh ios
cd "$REPO"

banner "iOS — latin ios build (IOS_SAMPLE_AUTHORS.csv → latin_texts_ios.db)"
cd "$REPO/latin" && "$PY" create_latin_database.py sample \
    --csv ../greek/data/IOS_SAMPLE_AUTHORS.csv \
    --output latin_texts_ios.db
cd "$REPO"

banner "iOS — assembly"
cd "$REPO/data-prep" && "$PY" assemble_database.py ios
cd "$REPO"

banner "ALL RELEASES COMPLETE"
echo "Verify with:"
echo "  ./venv/bin/python3 verify_all_releases.py"
