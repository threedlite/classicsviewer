#!/usr/bin/env bash
#
# mirror.sh — download a local copy of https://rhetoric.byu.edu
#
# Produces a browsable offline copy under ./rhetoric.byu.edu/
# Re-running resumes/refreshes (timestamping), so it's safe to stop and restart.

set -euo pipefail

SITE="https://rhetoric.byu.edu"
HOST="rhetoric.byu.edu"
DEST="$(cd "$(dirname "$0")" && pwd)"
LOG="$DEST/mirror.log"

cd "$DEST"

echo "Mirroring $SITE into $DEST/$HOST"
echo "Logging to $LOG"

# caffeinate keeps the Mac awake for the whole crawl — otherwise idle sleep
# freezes wget mid-download and the mirror never finishes.
caffeinate -ims wget \
  --mirror \
  --page-requisites \
  --convert-links \
  --adjust-extension \
  --no-parent \
  --domains="$HOST" \
  --exclude-domains=humanities.byu.edu,scout.cs.wisc.edu \
  --restrict-file-names=windows \
  --tries=2 \
  --timeout=20 \
  --retry-connrefused \
  --execute robots=off \
  --user-agent="Mozilla/5.0 (offline-archive mirror.sh)" \
  --append-output="$LOG" \
  "$SITE/" || rc=$?

# wget exit 8 = some URLs returned HTTP errors (broken links on the site).
# That is expected for a mirror and not a failure of the script.
rc=${rc:-0}
if [ "$rc" -ne 0 ] && [ "$rc" -ne 8 ]; then
  echo "wget failed with exit code $rc" >&2
  exit "$rc"
fi

# CC BY 3.0 requires attribution to travel with the copy.
cat > "$DEST/$HOST/ATTRIBUTION.txt" <<EOF
This is an offline copy of Silva Rhetoricae ($SITE),
by Dr. Gideon Burton, Brigham Young University.

Licensed under Creative Commons Attribution 3.0 (CC BY 3.0):
https://creativecommons.org/licenses/by/3.0/

Mirrored on $(date +%Y-%m-%d) with mirror.sh for offline/archival use.
Attribution must be preserved if this copy is redistributed or reused.
EOF

echo "Done. Open $DEST/$HOST/index.html in a browser."
echo "Wrote $DEST/$HOST/ATTRIBUTION.txt"
echo "Total size:"
du -sh "$DEST/$HOST"
