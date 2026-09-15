"""Load a dictionary package in the app's import format into the Latin DB.

The package is the same three-CSV zip the app accepts from users
(DICTIONARY_IMPORT_FORMAT.md), consumed here at BUILD time so the interlinear
generator can gloss from it:

    dictionary.csv           lemma, language, definition, source_name
    morphology.csv           word_form, lemma, language, morph_info, confidence
    normalization_rules.csv  (not loaded here -- the build has its own
                              normaliser in latin_normalization.py, and two
                              divergent folding rules is how Latin lookup
                              silently half-works)

WHY THIS EXISTS
---------------
Whitaker's data files carry no paradigm for `sum` -- the Ada program handles
irregular verbs in code. So `est`, `esse`, `sit`, `sint` and the rest resolve
to a lemma with no dictionary entry, and the interlinear either blanks them or,
worse, falls through to an unrelated verb that happens to share the surface
form: `est` shipped as "eject/emit" (edo, "to eat") for 55,286 tokens, `sit` as
"be thirsty" (sitio), `sint` as "allow, permit" (sino).

Giving `sum` a real entry fixes that without any change to the selection logic:
the treebank already resolves the form to `sum` correctly, and
select_entry_for_pos() prefers a candidate whose lemma matches. It only failed
because no such candidate existed.

The format is deliberately NOT extended for build-time use. It has to stay
byte-identical to what the shipped app imports.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Dict, Optional

# Row counts measured on the package this was written against. They are floors,
# not equalities, so a larger revision passes and a truncated or wrong-language
# file fails loudly rather than silently shipping fewer glosses (CLAUDE.md: do
# not add logic that fails the build pipeline silently).
EXPECTED_MIN_DEFINITIONS = 45_000
EXPECTED_MIN_FORMS = 1_400_000

# Package members. Names are exact and case-sensitive, per the spec.
_DICTIONARY = "dictionary.csv"
_MORPHOLOGY = "morphology.csv"

DEFAULT_PACKAGE = (
    Path(__file__).resolve().parents[2] / "lsgloss" / "lewis-short-glosses.zip"
)

# csv.field_size_limit default is 128 KB; a long L&S definition can exceed it.
csv.field_size_limit(10 ** 7)


def _read_csv(zf: zipfile.ZipFile, name: str, required: set) -> list:
    if name not in zf.namelist():
        raise SystemExit(
            f"ERROR: {name} missing from the dictionary package.\n"
            f"  Members found: {zf.namelist()}\n"
            f"  Files must sit at the archive root, not inside a folder."
        )
    with zf.open(name) as fh:
        reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8"))
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"ERROR: {name} is missing required column(s): "
                f"{sorted(missing)}\n  Found: {reader.fieldnames}"
            )
        return list(reader)


def load_gloss_package(cursor, package_path: Optional[Path] = None,
                       language: str = "latin") -> Dict[str, int]:
    """Insert a package's definitions and form->lemma rows. Returns stats."""
    path = Path(package_path) if package_path else DEFAULT_PACKAGE
    if not path.exists():
        raise SystemExit(
            f"ERROR: dictionary package not found: {path}\n"
            f"  Expected the importable zip (dictionary.csv, morphology.csv, "
            f"normalization_rules.csv)."
        )

    with zipfile.ZipFile(path) as zf:
        defs = _read_csv(zf, _DICTIONARY, {"lemma", "language", "definition"})
        forms = _read_csv(zf, _MORPHOLOGY, {"word_form", "lemma", "language"})

    defs = [r for r in defs if (r.get("language") or "").lower() == language]
    forms = [r for r in forms if (r.get("language") or "").lower() == language]

    if len(defs) < EXPECTED_MIN_DEFINITIONS:
        raise SystemExit(
            f"ERROR: package supplied {len(defs):,} {language} definitions, "
            f"below the {EXPECTED_MIN_DEFINITIONS:,} floor. Truncated file or "
            f"wrong language."
        )
    if len(forms) < EXPECTED_MIN_FORMS:
        raise SystemExit(
            f"ERROR: package supplied {len(forms):,} {language} form->lemma "
            f"rows, below the {EXPECTED_MIN_FORMS:,} floor."
        )

    # source_name is what the reader is shown as attribution. The spec makes it
    # optional and defaults it, so honour that rather than assuming it is set.
    source = next((r.get("source_name") for r in defs if r.get("source_name")),
                  None) or "User Import"

    # entry_plain carries the definition; the interlinear's extract_gloss()
    # reads that column. No XML/HTML: the package is plain text by design.
    cursor.executemany(
        "INSERT INTO dictionary_entries "
        "(headword, headword_normalized_ultra, language, entry_xml, "
        " entry_html, entry_plain, source) "
        "VALUES (?, NULL, ?, NULL, NULL, ?, ?)",
        [(r["lemma"], language, r["definition"], source) for r in defs],
    )

    def _confidence(raw):
        try:
            return round(float(raw), 4)
        except (TypeError, ValueError):
            return 1.0

    cursor.executemany(
        "INSERT INTO lemma_map "
        "(word_form, lemma, confidence, source, morph_info) "
        "VALUES (?, ?, ?, ?, ?)",
        [(r["word_form"], r["lemma"], _confidence(r.get("confidence")),
          source, r.get("morph_info") or None) for r in forms],
    )

    print(f"  Package: {path.name}")
    print(f"  Inserted {len(defs):,} dictionary entries and "
          f"{len(forms):,} lemma_map rows (source '{source}')")
    return {"source": source, "definitions": len(defs), "forms": len(forms)}
