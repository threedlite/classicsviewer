#!/usr/bin/env python3
"""Generate references_manifest.json for the on-demand References asset pack.

Scans references/*.pdf, looks up each filename in REGISTRY for the canonical
display metadata, reads page count from the PDF itself, and writes the manifest
into references_pack/src/main/assets/references_manifest.json.

Add a new entry to REGISTRY when adding a new reference PDF to references/.
The build fails loudly if a PDF in references/ has no REGISTRY entry, so
new PDFs cannot ship with placeholder titles.
"""

import json
import os
import sys
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = REPO_ROOT / "references"
OUTPUT = REPO_ROOT / "references_pack" / "src" / "main" / "assets" / "references_manifest.json"

# Canonical display metadata. Keys are filenames in references/.
REGISTRY = {
    "greekgrammarforc0000herb.pdf": {
        "id": "smyth_greek_grammar",
        "title": "A Greek Grammar for Colleges",
        "author": "Herbert Weir Smyth",
        "language": "greek",
    },
    "allengreenoughsn00alleiala.pdf": {
        "id": "allen_greenough_latin",
        "title": "New Latin Grammar",
        "author": "Allen and Greenough",
        "language": "latin",
    },
}


def main() -> int:
    if not REFERENCES_DIR.is_dir():
        print(f"ERROR: {REFERENCES_DIR} not found", file=sys.stderr)
        return 1

    pdfs = sorted(REFERENCES_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"ERROR: no PDFs in {REFERENCES_DIR}", file=sys.stderr)
        return 1

    entries = []
    seen_ids = set()
    for pdf in pdfs:
        filename = pdf.name
        if filename not in REGISTRY:
            print(
                f"ERROR: {filename} has no REGISTRY entry in {Path(__file__).name}. "
                f"Add canonical id/title/author/language before shipping.",
                file=sys.stderr,
            )
            return 1
        reg = REGISTRY[filename]
        if reg["id"] in seen_ids:
            print(f"ERROR: duplicate id '{reg['id']}' in REGISTRY", file=sys.stderr)
            return 1
        seen_ids.add(reg["id"])

        reader = PdfReader(str(pdf))
        page_count = len(reader.pages)
        size_bytes = pdf.stat().st_size

        entries.append({
            "id": reg["id"],
            "filename": filename,
            "title": reg["title"],
            "author": reg["author"],
            "language": reg["language"],
            "pageCount": page_count,
            "sizeBytes": size_bytes,
        })

    manifest = {"version": 1, "entries": entries}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"✓ Wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(entries)} entries)")
    for e in entries:
        print(f"    {e['id']:30s} {e['pageCount']:4d}p  {e['sizeBytes']//1024//1024:4d} MB  {e['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
