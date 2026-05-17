#!/usr/bin/env python3
"""Phase 1 of the rhetoric reference feature: build rhetoric.db from the mirror.

Parses the Silva Rhetoricae mirror (figures/rhetoric.byu.edu/) into a small,
self-contained SQLite database -- separate from perseus_texts.db -- per the
schema in RHETORIC_REFERENCE_PROPOSAL.md sec. 4.

Pipeline position:
    mirror.sh -> relativize.py -> strip_external.py -> purge_urls.py
              -> ocr_greek_terms.py (-> greek_terms.csv) -> build_rhetoric_db.py

Outputs (all under figures/):
    rhetoric.db                  the database
    rhetoric.db.zip              compressed, for bundling in the app
    rhetoric_quality_report.txt  coverage + dropped-link report

Graceful degradation (proposal sec. 4): a page that does not parse is logged,
counted, and skipped -- never fatal. A cross-reference whose target resolves to
no known entry is dropped and counted, never written as a dangling row.
"""
import csv
import html as htmllib
import os
import re
import sqlite3
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, Comment

HERE = Path(__file__).resolve().parent
MIRROR = HERE / "rhetoric.byu.edu"
GREEK_CSV = HERE / "greek_terms.csv"
DB_OUT = HERE / "rhetoric.db"
ZIP_OUT = HERE / "rhetoric.db.zip"
REPORT_OUT = HERE / "rhetoric_quality_report.txt"

# Copied into the app asset dirs that exist, mirroring create_perseus_database.py.
ASSET_DIRS = [
    HERE.parent / "app" / "src" / "main" / "assets",          # Android release
    HERE.parent / "app" / "src" / "debug" / "assets",         # Android debug
    HERE.parent / "ios" / "ClassicsViewer" / "Resources",     # iOS bundle
]

# Top-level mirror dir -> (section id, display title, sort order).
SECTIONS = {
    "Figures": ("figures", "Figures", 1),
    "Canons": ("canons", "Canons", 2),
    "Branches of Oratory": ("branches", "Branches of Oratory", 3),
    "Persuasive Appeals": ("appeals", "Persuasive Appeals", 4),
    "Four Changes": ("changes", "Four Changes", 5),
    "Encompassing Terms": ("terms", "Encompassing Terms", 6),
    "General Rhetorical Strategies": ("strategies", "General Rhetorical Strategies", 7),
    "Pedagogy": ("pedagogy", "Pedagogy", 8),
    "Primary Texts": ("primary-texts", "Primary Texts", 9),
    "Rhetorical Ability": ("ability", "Rhetorical Ability", 10),
    "Sources": ("sources", "Sources", 12),
}

# Editable-region name (lowercased) -> logical field. Two Dreamweaver templates
# are in use (capitalised Def-Eg-Fig-Also-Src.dwt and lowercase figure3.dwt);
# matching case-insensitively folds both.
REGION_FIELD = {
    "term": "name",
    "greek in greek": "greek_img",
    "greek": "greek_img",
    "etymology": "etymology",
    "definition": "definition",
    "explanation": "explanation",
    "examples": "examples",
    "related figures": "related",
    "see also": "see_also",
}

EDITABLE_RE = re.compile(
    r'<!--\s*#BeginEditable\s*"([^"]*)"\s*-->(.*?)<!--\s*#EndEditable\s*-->',
    re.DOTALL | re.IGNORECASE,
)
KEEP_TAGS = {"i", "b"}
TAG_ALIAS = {"em": "i", "strong": "b"}


def slugify(stem):
    """Filename stem -> entry id. Drops a leading '~', lowercases, hyphenates."""
    s = unquote(stem).lstrip("~").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def read_html(path):
    """Decode a mirror page: UTF-8 if valid, else cp1252 (legacy Windows bytes)."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def clean_inline(fragment):
    """Fragment -> string keeping only <i>/<b>; other tags unwrapped to text.

    Whitespace is collapsed. Used for etymology / definition / examples so the
    Android renderer can apply simple emphasis spans (proposal sec. 5.2).
    """
    soup = BeautifulSoup(fragment, "html.parser")
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    for tag in soup.find_all(True):
        name = TAG_ALIAS.get(tag.name, tag.name)
        if name in KEEP_TAGS:
            tag.name = name
            tag.attrs = {}
        else:
            tag.unwrap()
    text = str(soup)
    # Drop U+FFFD: the mirror has baked-in replacement chars where the original
    # site lost a Windows-1252 byte. The character is unrecoverable; strip it
    # rather than show a diamond-question-mark.
    text = text.replace("�", "")
    text = re.sub(r"\s+", " ", text).strip()
    # Drop emphasis tags left wrapping only whitespace.
    text = re.sub(r"<([ib])>\s*</\1>", "", text).strip()
    return text


def extract_links(fragment):
    """List of (href, anchor_text, trailing_note) for each <li> in a fragment.

    Related Figures / See Also are <ul><li><a href>name</a> optional note. The
    legacy markup omits </li>, so split on <li> (or <br> as a fallback) rather
    than trusting the parser's nesting; the note runs to the next <a>.
    """
    if not fragment:
        return []
    chunks = re.split(r"<li\b[^>]*>", fragment, flags=re.IGNORECASE)
    if len(chunks) == 1:
        chunks = re.split(r"<br\s*/?>", fragment, flags=re.IGNORECASE)
    out = []
    for chunk in chunks:
        m = re.search(r'<a\b[^>]*href\s*=\s*["\']?([^"\'>\s]+)[^>]*>(.*?)</a>',
                      chunk, re.IGNORECASE | re.DOTALL)
        if not m:
            continue
        href = m.group(1)
        anchor = clean_inline(m.group(2))
        tail = re.split(r"<a\b", chunk[m.end():], flags=re.IGNORECASE)[0]
        note = clean_inline(chunk[:m.start()] + tail)
        out.append((href, anchor, note))
    return out


def parse_regions(html):
    """All editable regions of a page -> {field: raw_fragment} (last wins)."""
    fields = {}
    for raw_name, fragment in EDITABLE_RE.findall(html):
        field = REGION_FIELD.get(unquote(raw_name).strip().lower())
        if field:
            fields[field] = fragment
    return fields


def greek_img_name(fragment):
    """The Images/Greek/*.gif basename referenced in a 'Greek in Greek' region."""
    if not fragment:
        return None
    m = re.search(r'src\s*=\s*["\']?[^"\'> ]*Images/Greek/([^"\'>]+\.gif)',
                  fragment, re.IGNORECASE)
    return unquote(m.group(1)) if m else None


def extract_all_hrefs(fragment):
    """Every <a href> in a fragment -- used to catch links embedded in prose.

    Many pages are pure pointers ('Latin term for catachresis') whose only
    cross-reference is an inline link inside the definition text.
    """
    if not fragment:
        return []
    return re.findall(r'<a\b[^>]*href\s*=\s*["\']?([^"\'>\s]+)', fragment, re.IGNORECASE)


def parse_loose(html):
    """Parse a legacy '~' synonym page, which has no editable regions.

    These older pages carry real content (definition + Related Figures) and are
    frequent cross-reference targets, so they must become entries too.
    """
    fields = {}
    m = re.search(r'<font[^>]*size=["\']?\+3[^>]*>(.*?)</font>', html,
                  re.IGNORECASE | re.DOTALL)
    if m:
        fields["name"] = m.group(1)
    m = re.search(r'greendiamond\.gif[^>]*>(.*?)<p\b', html,
                  re.IGNORECASE | re.DOTALL)
    if m:
        fields["definition"] = m.group(1)
    m = re.search(r'(<img[^>]*Images/Greek/[^>]*>)', html, re.IGNORECASE)
    if m:
        fields["greek_img"] = m.group(1)
    m = re.search(r'Related Figures.*?#EndLibraryItem\s*-->(.*?)</ul>', html,
                  re.IGNORECASE | re.DOTALL)
    if m:
        fields["related"] = m.group(1)
    m = re.search(r'<blockquote>(.*?)</blockquote>', html,
                  re.IGNORECASE | re.DOTALL)
    if m:
        fields["examples"] = m.group(1)
    return fields


def parse_generic(html):
    """Best-effort parse of a section page with no editable regions.

    Used for Canons / Branches of Oratory / Persuasive Appeals / Four Changes /
    etc., whose legacy layout is: header table (name) -> LINE051S separator ->
    optional nav table -> prose content -> footer. The prose after the last
    separator, minus a leading nav table and the footer, becomes the definition.
    """
    fields = {}
    # Name / etymology / Greek image live in the header, above the LINE051S
    # separator -- scope the search there so footer logo fonts are not matched.
    sep0 = html.lower().find("line051s")
    header = html[:sep0] if sep0 != -1 else html
    m = re.search(r'<font[^>]*size=["\']?\+3[^>]*>(.*?)</font>', header,
                  re.IGNORECASE | re.DOTALL)
    if m:
        fields["name"] = m.group(1)
    m = re.search(r'<font[^>]*size=["\']?\+2[^>]*>(.*?)</font>', header,
                  re.IGNORECASE | re.DOTALL)
    if m:
        fields["etymology"] = m.group(1)
    m = re.search(r'(<img[^>]*Images/Greek/[^>]*>)', header, re.IGNORECASE)
    if m:
        fields["greek_img"] = m.group(1)

    # Cut the footer / bottom navigation: the licensed notice, the footer
    # library item, or the "Trees | SILVA RHETORICAE | ..." bottom nav.
    body = html
    cut = len(body)
    for pat in (r'#BeginLibraryItem\s*"/Library/footer',
                r'This work is licensed',
                r'<[^>]*\btrees\.htm'):
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            cut = min(cut, m.start())
    body = body[:cut]
    # Content starts after the last LINE051S separator rule.
    sep = body.lower().rfind("line051s")
    if sep != -1:
        body = body[body.find(">", sep) + 1:]
    # Drop short tables (navigation / spacer); keep tables holding real prose.
    def _keep_long_table(m):
        inner = re.sub(r"<[^>]+>", "", m.group(0))
        return m.group(0) if len(inner.strip()) >= 240 else ""
    body = re.sub(r"<table\b.*?</table>", _keep_long_table, body,
                  flags=re.IGNORECASE | re.DOTALL)
    # Split the Related Figures / See Also sub-sections out of the prose --
    # these pages carry the same logical sections as figure pages, marked with
    # <u> headers instead of editable-region comments.
    parts = re.split(r'<u>\s*Related\s+Figures\s*</u>', body, maxsplit=1,
                     flags=re.IGNORECASE | re.DOTALL)
    definition = parts[0]
    if len(parts) > 1:
        sa = re.split(r'<u>\s*See\s+Also\s*</u>', parts[1], maxsplit=1,
                      flags=re.IGNORECASE | re.DOTALL)
        fields["related"] = sa[0]
        if len(sa) > 1:
            fields["see_also"] = sa[1]
    # Definition prose ends at the first structural marker (a library item, an
    # <u> sub-heading, or an example blockquote).
    definition = re.split(r'#BeginLibraryItem|<u\b|<blockquote', definition,
                          maxsplit=1, flags=re.IGNORECASE)[0]
    fields["definition"] = definition
    return fields


def resolve_href(page_dir, href, path_to_id):
    """Resolve an href relative to its page to a known entry id, or None."""
    target = unquote(href).split("#")[0].strip()
    if not target or target.lower().endswith((".jpg", ".jpeg", ".gif", ".png")):
        return None
    resolved = os.path.normpath(os.path.join(page_dir, target))
    try:
        rel = Path(resolved).relative_to(MIRROR).as_posix().lower()
    except ValueError:
        return None
    return path_to_id.get(rel)


def main():
    if not MIRROR.is_dir():
        sys.exit(f"ERROR: mirror not found at {MIRROR} -- run mirror.sh first.")

    # --- Greek-term map: gif basename (lowercased) -> Unicode polytonic ----
    greek_terms = {}
    if GREEK_CSV.exists():
        with GREEK_CSV.open(encoding="utf-8") as f:
            for row in list(csv.reader(f))[1:]:
                if len(row) >= 2 and row[1].strip():
                    greek_terms[row[0].strip().lower()] = row[1].strip()
    else:
        print(f"WARNING: {GREEK_CSV.name} missing -- entries will lack Greek terms.")

    pages = sorted(p for p in MIRROR.rglob("*")
                   if p.suffix.lower() == ".htm" and p.is_file())

    entries = {}            # id -> entry dict
    path_to_id = {}         # normalized lowercase rel path -> id
    skipped = []            # (rel_path, reason)
    missing_greek = []      # (id, gif name with no greek_terms row)

    for path in pages:
        rel = path.relative_to(MIRROR)
        top = rel.parts[0]
        if top not in SECTIONS:
            continue                                   # not a content section
        section_id = SECTIONS[top][0]

        html = read_html(path)
        regions = parse_regions(html)
        used_generic = False
        if not regions.get("definition"):
            if path.name.startswith("~"):
                regions = parse_loose(html)            # legacy synonym page
            elif section_id != "figures":
                regions = parse_generic(html)          # non-Figures section page
                used_generic = True

        name = clean_inline(regions["name"]) if regions.get("name") else ""
        definition = clean_inline(regions["definition"]) if regions.get("definition") else ""
        if not definition:
            skipped.append((rel.as_posix(), "no definition region"))
            continue
        # Generic section pages with only nav/index content are not entries.
        if used_generic and len(definition) < 60:
            skipped.append((rel.as_posix(), "section page has no prose content"))
            continue
        if not name:
            tm = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
            name = clean_inline(tm.group(1)) if tm else slugify(path.stem)
        # Display names: capitalise the first word for the non-Figures
        # sections. Figure names keep their canonical lowercase form
        # (e.g. "alliteration"), as the source presents them.
        if section_id != "figures":
            name = name[:1].upper() + name[1:]

        entry_id = slugify(path.stem)
        if entry_id in entries:
            skipped.append((rel.as_posix(), f"duplicate id '{entry_id}'"))
            continue

        explanation = clean_inline(regions["explanation"]) if regions.get("explanation") else ""
        if explanation:
            definition = f"{definition}\n\n{explanation}"

        gif = greek_img_name(regions.get("greek_img", ""))
        etymology_greek = None
        if gif:
            etymology_greek = greek_terms.get(gif.lower())
            if etymology_greek is None:
                missing_greek.append((entry_id, gif))

        entries[entry_id] = {
            "id": entry_id,
            "section_id": section_id,
            "name": name,
            "etymology_greek": etymology_greek,
            "etymology": clean_inline(regions["etymology"]) if regions.get("etymology") else None,
            "definition": definition,
            "examples": clean_inline(regions["examples"]) if regions.get("examples") else None,
            "source_path": rel.as_posix(),
            "_related": regions.get("related", ""),
            "_see_also": regions.get("see_also", ""),
            "_inline": extract_all_hrefs(regions.get("definition", ""))
            + extract_all_hrefs(regions.get("explanation", "")),
        }
        path_to_id[rel.as_posix().lower()] = entry_id

    # --- resolve cross-references -----------------------------------------
    cross_refs = []         # (from_id, to_id, kind, note)
    dropped_refs = []       # (from_id, raw_href)
    seen_ref = set()
    for entry in entries.values():
        page_dir = (MIRROR / entry["source_path"]).parent
        # Curated Related Figures / See Also lists (carry a note).
        for kind, fragment in (("related", entry.pop("_related")),
                               ("see_also", entry.pop("_see_also"))):
            for href, _anchor, note in extract_links(fragment):
                to_id = resolve_href(page_dir, href, path_to_id)
                if not to_id or to_id == entry["id"]:
                    if to_id != entry["id"]:
                        dropped_refs.append((entry["id"], href))
                    continue
                key = (entry["id"], to_id, kind)
                if key in seen_ref:
                    continue
                seen_ref.add(key)
                cross_refs.append((entry["id"], to_id, kind, note or None))
        # Links embedded in the definition prose (pointer pages) -- added as
        # 'related' so they surface as tappable cross-references in the app.
        for href in entry.pop("_inline", []):
            to_id = resolve_href(page_dir, href, path_to_id)
            if not to_id or to_id == entry["id"]:
                if to_id != entry["id"]:
                    dropped_refs.append((entry["id"], href))
                continue
            key = (entry["id"], to_id, "related")
            if key in seen_ref:
                continue
            seen_ref.add(key)
            cross_refs.append((entry["id"], to_id, "related", None))

    # --- write the database -----------------------------------------------
    used_sections = {e["section_id"] for e in entries.values()}
    DB_OUT.unlink(missing_ok=True)
    db = sqlite3.connect(DB_OUT)
    db.executescript("""
        CREATE TABLE rhetoric_sections (
            id          TEXT PRIMARY KEY NOT NULL,
            title       TEXT NOT NULL,
            sort_order  INTEGER NOT NULL
        );
        CREATE TABLE rhetoric_entries (
            id              TEXT PRIMARY KEY NOT NULL,
            section_id      TEXT NOT NULL,
            name            TEXT NOT NULL,
            etymology_greek TEXT,
            etymology       TEXT,
            definition      TEXT NOT NULL,
            examples        TEXT,
            source_path     TEXT NOT NULL
        );
        CREATE TABLE rhetoric_cross_refs (
            from_id     TEXT NOT NULL,
            to_id       TEXT NOT NULL,
            kind        TEXT NOT NULL,
            note        TEXT,
            PRIMARY KEY (from_id, to_id, kind)
        );
        CREATE INDEX idx_entries_section ON rhetoric_entries(section_id);
        CREATE INDEX idx_entries_name    ON rhetoric_entries(name);
        CREATE INDEX idx_xref_from       ON rhetoric_cross_refs(from_id);
    """)
    db.executemany(
        "INSERT INTO rhetoric_sections VALUES (?,?,?)",
        [(sid, title, order) for d, (sid, title, order) in SECTIONS.items()
         if sid in used_sections],
    )
    db.executemany(
        "INSERT INTO rhetoric_entries VALUES (?,?,?,?,?,?,?,?)",
        [(e["id"], e["section_id"], e["name"], e["etymology_greek"],
          e["etymology"], e["definition"], e["examples"], e["source_path"])
         for e in sorted(entries.values(), key=lambda e: e["name"].lower())],
    )
    db.executemany("INSERT INTO rhetoric_cross_refs VALUES (?,?,?,?)", cross_refs)
    db.commit()
    db.close()

    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(DB_OUT, DB_OUT.name)

    copied = []
    for d in ASSET_DIRS:
        if d.is_dir():
            (d / ZIP_OUT.name).write_bytes(ZIP_OUT.read_bytes())
            copied.append(str(d / ZIP_OUT.name))

    # --- quality report ----------------------------------------------------
    by_section = {}
    for e in entries.values():
        by_section.setdefault(e["section_id"], 0)
        by_section[e["section_id"]] += 1
    with_examples = sum(1 for e in entries.values() if e["examples"])
    with_greek = sum(1 for e in entries.values() if e["etymology_greek"])
    with_etym = sum(1 for e in entries.values() if e["etymology"])

    lines = [
        "Silva Rhetoricae -> rhetoric.db -- quality report",
        "=" * 55,
        f"HTML pages scanned (content sections): {len(pages)}",
        f"Entries imported:                      {len(entries)}",
        f"  with examples:   {with_examples}",
        f"  with etymology:  {with_etym}",
        f"  with Greek term: {with_greek}",
        f"Cross-references kept:    {len(cross_refs)}",
        f"Cross-references dropped: {len(dropped_refs)} (target not an entry)",
        f"Pages skipped:            {len(skipped)}",
        "",
        "Entries by section:",
    ]
    for sid in sorted(by_section, key=lambda s: by_section[s], reverse=True):
        lines.append(f"  {sid:14} {by_section[sid]}")
    if missing_greek:
        lines += ["", f"Greek GIFs with no greek_terms.csv row ({len(missing_greek)}):"]
        lines += [f"  {eid}: {gif}" for eid, gif in missing_greek]
    lines += ["", f"Skipped pages ({len(skipped)}):"]
    lines += [f"  {p} -- {why}" for p, why in skipped]
    lines += ["", f"Dropped cross-references ({len(dropped_refs)}):"]
    lines += [f"  {fid} -> {href}" for fid, href in dropped_refs]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Entries: {len(entries)}  cross-refs: {len(cross_refs)}  "
          f"skipped: {len(skipped)}")
    print(f"Wrote {DB_OUT.name} ({DB_OUT.stat().st_size//1024} KB), "
          f"{ZIP_OUT.name} ({ZIP_OUT.stat().st_size//1024} KB)")
    for c in copied:
        print(f"Copied -> {c}")
    print(f"Quality report: {REPORT_OUT.name}")


if __name__ == "__main__":
    main()
