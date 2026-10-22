#!/usr/bin/env bash
# Fetch the build binaries from the GitHub release and put them where BUILD.md
# expects them (none of these files are in git; see GITHUB_RELEASE.md):
#
#   sample      perseus_texts_sample.db.zip -> app/src/{debug,main}/assets/ and perseus_database/src/main/assets/ as perseus_texts.db.zip
#   ios         perseus_texts_ios.db.zip    -> ios/ClassicsViewer/Resources/perseus_texts.db.zip
#   full        perseus_texts_full.db.zip + full.manifest.json -> full_database_pack/src/main/assets/; zip also to ios OnDemand/;
#               perseus_texts_extended.lexicon_ranges.json -> data-prep/ (assemble_database.py full needs it)
#   extended    perseus_texts_extended.db.zip (published in pieces, joined here) -> ios/ClassicsViewer/Resources/OnDemand/
#   parts       db_extended_part{1,2}_pack.db.zip + .manifest.json -> db_extended_part{1,2}_pack/src/main/assets/
#   topical     topical_{greek,latin}.db.zip -> topical_pack/src/main/assets/, app/src/debug/assets/topical/, ios OnDemand/
#   audio       homer_iliad_chamberlain_audio.zip -> audio/ and audio_pack/src/main/assets/
#   references  the three grammar PDFs -> references/ and ios/ClassicsViewer/Resources/OnDemand/References/
#   interlinear {greek,latin,sanskrit}_interlinear_output.tar.gz -> greek/, latin/ and sanskrit/interlinear_output/
#   glosses     lewis-short-glosses.zip -> lsgloss/
#   modules     the module DB zips the module builds write (latin extended, sanskrit, coptic, pali, norse,
#               old_english, dante, syriac) -> <module>/<name>.db.zip, unzipped there to the .db assembly reads
#   caches      all_greek_wiktionary_pages.json -> greek/wiktionary-processing/; all_syriac_enwiktionary_pages.json -> syriac/
#
#   bash fetch_release.sh sample topical        # named groups
#   bash fetch_release.sh android               # sample full parts topical audio references: what bundleRelease needs
#   bash fetch_release.sh all                   # everything, about 9.5 GB
#   bash fetch_release.sh --list
#
# Every file is checked against the release's SHA256SUMS before it is put in place. Idempotent:
# anything already in place is skipped (pass --verify to re-check files in place against the
# checksums; tarballs are re-fetched, since the checksum is of the archive).
# CV_RELEASE (default data-2026-10-17) and CV_RELEASE_REPO (default threedlite/classicsviewer)
# select the release; CV_RELEASE_DEST (default: this repository) the root the paths above are
# relative to; CV_RELEASE_BASE overrides the download URL (a file:// URL works, for testing).
#
# The script never deletes recursively: downloads are removed one file at a time by name, and the
# temporary directory is removed with rmdir once it is empty.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CV_RELEASE_DEST:-$ROOT}"
REPO="${CV_RELEASE_REPO:-threedlite/classicsviewer}"
TAG="${CV_RELEASE:-data-2026-10-17}"
BASE="${CV_RELEASE_BASE:-https://github.com/$REPO/releases/download/$TAG}"

GROUPS_ALL="sample ios full extended parts topical audio references interlinear glosses modules caches"

assets_of_group() {
  case "$1" in
    sample)      echo "perseus_texts_sample.db.zip" ;;
    ios)         echo "perseus_texts_ios.db.zip" ;;
    full)        echo "perseus_texts_full.db.zip full.manifest.json perseus_texts_extended.lexicon_ranges.json" ;;
    extended)    echo "perseus_texts_extended.db.zip" ;;
    parts)       echo "db_extended_part1_pack.db.zip db_extended_part1_pack.manifest.json db_extended_part2_pack.db.zip db_extended_part2_pack.manifest.json" ;;
    topical)     echo "topical_greek.db.zip topical_latin.db.zip" ;;
    audio)       echo "homer_iliad_chamberlain_audio.zip" ;;
    references)  echo "greekgrammarforc0000herb.pdf allengreenoughsn00alleiala.pdf whitneysanskritgrammar.pdf" ;;
    interlinear) echo "greek_interlinear_output.tar.gz latin_interlinear_output.tar.gz sanskrit_interlinear_output.tar.gz" ;;
    glosses)     echo "lewis-short-glosses.zip" ;;
    modules)     echo "latin_texts_extended.db.zip sanskrit_texts.db.zip coptic_texts.db.zip pali_texts.db.zip norse_texts.db.zip old_english_texts.db.zip dante_texts.db.zip syriac_texts.db.zip" ;;
    caches)      echo "all_greek_wiktionary_pages.json all_syriac_enwiktionary_pages.json" ;;
    *) return 1 ;;
  esac
}

usage() {
  echo "usage: bash fetch_release.sh <group>... | android | all | --list [--verify]"
  echo
  echo "groups: $GROUPS_ALL"
  echo "android = sample full parts topical audio references"
  local g
  for g in $GROUPS_ALL; do printf "  %-12s %s\n" "$g" "$(assets_of_group "$g")"; done
}

# asset name -> destination paths relative to DEST, one per line, the first being the primary
# copy. The two tarballs print the module directory they unpack into.
targets_of() {
  local a="$1"
  case "$a" in
    perseus_texts_sample.db.zip)
      printf '%s\n' app/src/debug/assets/perseus_texts.db.zip app/src/main/assets/perseus_texts.db.zip perseus_database/src/main/assets/perseus_texts.db.zip ;;
    perseus_texts_ios.db.zip)      echo ios/ClassicsViewer/Resources/perseus_texts.db.zip ;;
    perseus_texts_full.db.zip)     printf '%s\n' "full_database_pack/src/main/assets/$a" "ios/ClassicsViewer/Resources/OnDemand/$a" ;;
    full.manifest.json)            echo "full_database_pack/src/main/assets/$a" ;;
    perseus_texts_extended.db.zip) echo "ios/ClassicsViewer/Resources/OnDemand/$a" ;;
    db_extended_part?_pack.*)      echo "${a%%.*}/src/main/assets/$a" ;;
    topical_*.db.zip)              printf '%s\n' "topical_pack/src/main/assets/$a" "app/src/debug/assets/topical/$a" "ios/ClassicsViewer/Resources/OnDemand/$a" ;;
    homer_iliad_chamberlain_audio.zip) printf '%s\n' "audio/$a" "audio_pack/src/main/assets/$a" ;;
    *.pdf)                         printf '%s\n' "references/$a" "ios/ClassicsViewer/Resources/OnDemand/References/$a" ;;
    greek_interlinear_output.tar.gz) echo greek ;;
    latin_interlinear_output.tar.gz) echo latin ;;
    sanskrit_interlinear_output.tar.gz) echo sanskrit ;;
    lewis-short-glosses.zip)       echo "lsgloss/$a" ;;
    perseus_texts_extended.lexicon_ranges.json) echo "data-prep/$a" ;;
    latin_texts_extended.db.zip)   echo "latin/$a" ;;
    sanskrit_texts.db.zip)         echo "sanskrit/$a" ;;
    coptic_texts.db.zip)           echo "coptic/$a" ;;
    pali_texts.db.zip)             echo "pali/$a" ;;
    norse_texts.db.zip)            echo "norse/$a" ;;
    old_english_texts.db.zip)      echo "old_english/$a" ;;
    dante_texts.db.zip)            echo "dante/$a" ;;
    syriac_texts.db.zip)           echo "syriac/$a" ;;
    all_greek_wiktionary_pages.json) echo "greek/wiktionary-processing/$a" ;;
    all_syriac_enwiktionary_pages.json) echo "syriac/$a" ;;
    *) echo "internal error: no destination for $a" >&2; return 1 ;;
  esac
}

is_tarball() { case "$1" in *.tar.gz) return 0 ;; *) return 1 ;; esac; }

# Module DB zips are placed and then unzipped beside themselves, because assembly reads the .db.
is_module_zip() {
  case "$1" in
    latin_texts_extended.db.zip|sanskrit_texts.db.zip|coptic_texts.db.zip|pali_texts.db.zip|norse_texts.db.zip|old_english_texts.db.zip|dante_texts.db.zip|syriac_texts.db.zip) return 0 ;;
    *) return 1 ;;
  esac
}

# bsdtar on macOS writes file names in decomposed Unicode (NFD) into the archive, so the Sanskrit
# work names (e.g. Abhidharmakośa) come out of the tarball with combining marks while the build
# wrote them precomposed (NFC). Rename every extracted file back to NFC so the tree matches the
# original byte for byte; ASCII names (Greek, Latin) are untouched.
nfc_names() {
  command -v python3 >/dev/null 2>&1 || { echo "  ERROR python3 is required to normalise file names in $1" >&2; return 1; }
  python3 -I - "$1" <<'PY'
import os, sys, unicodedata
d = sys.argv[1]; n = 0
for f in os.listdir(d):
    c = unicodedata.normalize("NFC", f)
    if c != f:
        os.rename(os.path.join(d, f), os.path.join(d, c)); n += 1
if n: print(f"  note  {n} file names normalised to NFC in {d}")
PY
}

# A tarball counts as in place when its interlinear_output/ holds at least as many XMLs as the
# module build's own guard requires (greek 100, latin 50; BUILD.md Step 5). A clean clone has 2.
# Sanskrit has no guard (its build regenerates the XML); 100 is used, against 272 in the release.
xml_count() { find "$DEST/$1/interlinear_output" -maxdepth 1 -name '*.xml' 2>/dev/null | wc -l | tr -d ' '; }

in_place() {   # 0 if the asset is already where it belongs (every copy)
  local a="$1" t
  if is_tarball "$a"; then
    t="$(targets_of "$a")"
    case "$t" in latin) [ "$(xml_count "$t")" -ge 50 ] ;; *) [ "$(xml_count "$t")" -ge 100 ] ;; esac
    return
  fi
  while IFS= read -r t; do [ -f "$DEST/$t" ] || return 1; done <<< "$(targets_of "$a")"
  if is_module_zip "$a"; then t="$(targets_of "$a")"; [ -f "$DEST/${t%.zip}" ] || return 1; fi
  return 0
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

expected_sum() { awk -v f="$1" '$2 == f { print $1 }' "$TMP/SHA256SUMS"; }

download() {   # asset -> $TMP/asset, checksum verified
  local a="$1" expected actual
  expected="$(expected_sum "$a")"
  if [ -z "$expected" ]; then echo "  ERROR $a is not in the release's SHA256SUMS" >&2; return 1; fi
  echo "  fetch $a"
  if ! curl -fL --retry 3 --progress-bar -o "$TMP/$a" "$BASE/$a"; then
    echo "  ERROR download failed: $BASE/$a" >&2; rm -f "$TMP/$a"; return 1
  fi
  actual="$(sha256_of "$TMP/$a")"
  if [ "$actual" != "$expected" ]; then
    echo "  ERROR checksum mismatch for $a (expected $expected, got $actual)" >&2; rm -f "$TMP/$a"; return 1
  fi
}

# The extended zip is above GitHub's 2 GiB asset limit and is published as <name>.part-aa,
# .part-ab, ...; each piece and the joined file are listed in SHA256SUMS.
download_joined() {
  local a="$1" p pieces expected actual
  pieces="$(awk -v f="$a.part-" 'index($2, f) == 1 { print $2 }' "$TMP/SHA256SUMS" | sort)"
  if [ -z "$pieces" ]; then echo "  ERROR no $a.part-* pieces in the release's SHA256SUMS" >&2; return 1; fi
  for p in $pieces; do download "$p" || return 1; done
  : > "$TMP/$a"
  for p in $pieces; do cat "$TMP/$p" >> "$TMP/$a"; rm -f "$TMP/$p"; done
  expected="$(expected_sum "$a")"
  if [ -z "$expected" ]; then echo "  ERROR joined $a is not in the release's SHA256SUMS" >&2; rm -f "$TMP/$a"; return 1; fi
  actual="$(sha256_of "$TMP/$a")"
  if [ "$actual" != "$expected" ]; then
    echo "  ERROR checksum mismatch for joined $a (expected $expected, got $actual)" >&2; rm -f "$TMP/$a"; return 1
  fi
}

place() {   # $TMP/asset -> every destination; the temp copy is consumed
  local a="$1" first="" t
  if is_tarball "$a"; then
    t="$DEST/$(targets_of "$a")"
    mkdir -p "$t" && tar -xzf "$TMP/$a" -C "$t" || return 1
    rm -f "$TMP/$a"
    nfc_names "$t/interlinear_output" || return 1
    echo "  ok    $a -> $t/interlinear_output/ ($(xml_count "$(targets_of "$a")") XML files; checksum verified)"
    return 0
  fi
  while IFS= read -r t; do
    mkdir -p "$(dirname "$DEST/$t")" || return 1
    if [ -z "$first" ]; then mv "$TMP/$a" "$DEST/$t" || return 1; first="$DEST/$t"
    else cp "$first" "$DEST/$t" || return 1; fi
    echo "  ok    $a -> $t (checksum verified)"
  done <<< "$(targets_of "$a")"
  if is_module_zip "$a"; then
    unzip -o -q "$first" -d "$(dirname "$first")" || return 1
    echo "  ok    $a unzipped -> ${first%.zip}"
  fi
}

fetch_one() {
  local a="$1" expected actual primary t same
  if in_place "$a" && [ "$VERIFY" -eq 0 ]; then echo "  skip  $a (in place)"; return 0; fi
  if in_place "$a" && ! is_tarball "$a"; then
    expected="$(expected_sum "$a")"
    if [ -z "$expected" ]; then echo "  ERROR $a is not in the release's SHA256SUMS" >&2; return 1; fi
    primary="$DEST/$(targets_of "$a" | head -n 1)"
    actual="$(sha256_of "$primary")"
    if [ "$actual" = "$expected" ]; then
      same=1
      while IFS= read -r t; do cmp -s "$primary" "$DEST/$t" || same=0; done <<< "$(targets_of "$a")"
      if [ "$same" -eq 1 ]; then echo "  ok    $a (in place, checksum verified)"; return 0; fi
      echo "  WARN  $a copies differ from each other; re-fetching" >&2
    else
      echo "  WARN  $a in place but checksum differs; re-fetching" >&2
    fi
  fi
  if [ "$a" = perseus_texts_extended.db.zip ]; then download_joined "$a" || return 1; else download "$a" || return 1; fi
  place "$a"
}

[ "$#" -eq 0 ] && { usage; exit 1; }
ASSETS=""; VERIFY=0
for arg in "$@"; do
  case "$arg" in
    -h|--help|--list) usage; exit 0 ;;
    --verify) VERIFY=1 ;;
    all)     for g in $GROUPS_ALL; do ASSETS="$ASSETS $(assets_of_group "$g")"; done ;;
    android) for g in sample full parts topical audio references; do ASSETS="$ASSETS $(assets_of_group "$g")"; done ;;
    *) if a="$(assets_of_group "$arg")"; then ASSETS="$ASSETS $a"
       else echo "unknown group: $arg" >&2; echo >&2; usage >&2; exit 1; fi ;;
  esac
done
[ -z "$ASSETS" ] && { usage; exit 1; }
for tool in curl tar unzip; do command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: $tool is required" >&2; exit 1; }; done

# Temporary directory, flat: SHA256SUMS plus at most one download in flight. Each download is
# removed by name once placed or on failure; cleanup removes the checksum file and then the
# directory itself, which only succeeds if nothing was left behind (no recursive delete).
TMP="$(mktemp -d)"
cleanup() { rm -f "$TMP/SHA256SUMS"; rmdir "$TMP" 2>/dev/null || echo "note: $TMP left in place (not empty)" >&2; }
trap cleanup EXIT
echo "==> $REPO release $TAG -> $DEST"
curl -fsSL --retry 3 -o "$TMP/SHA256SUMS" "$BASE/SHA256SUMS" || { echo "ERROR: could not fetch $BASE/SHA256SUMS" >&2; exit 1; }
failed=0
for a in $ASSETS; do fetch_one "$a" || failed=1; done
echo
if [ "$failed" -ne 0 ]; then echo "some files failed; fix the errors above and re-run (finished ones are skipped)." >&2; exit 1; fi
echo "done. The files are where BUILD.md Steps 5, 7 and 8 expect them; git status will list them as untracked or modified, which is correct."
