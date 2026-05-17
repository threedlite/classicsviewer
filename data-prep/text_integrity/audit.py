"""text_integrity.audit — on-demand text-integrity audit CLI.

Read-only: reads data-sources/ XML and the named DB; writes only its
own reports to data-prep/text_integrity/reports/ (or the path given by
--report-out).

Usage:
    python3 data-prep/text_integrity/audit.py extended
    python3 data-prep/text_integrity/audit.py extended --works tlg0012.tlg001
    python3 data-prep/text_integrity/audit.py extended --corpus perseus
    python3 data-prep/text_integrity/audit.py extended --report-out /tmp/r.md

Modes: sample | full | extended | ios
Corpora: perseus (default) | first1k | pta | all
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
import time
from pathlib import Path


# When run as a script (python3 audit.py ...) make sure relative imports work.
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "data-prep.text_integrity"  # type: ignore

# Venv enforcement — must use the project's venv per BUILD.md Step 4.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.venv_check import assert_libs  # noqa: E402
assert_libs("audit")


from . import extract  # noqa: E402
from . import reconstruct  # noqa: E402
from . import verify  # noqa: E402
from . import report as report_mod  # noqa: E402
from .policy import resolve_policy_for_work  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_SOURCES = REPO_ROOT / "data-sources"
TOOL_DIR = Path(__file__).resolve().parent
REPORTS_DIR = TOOL_DIR / "reports"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="On-demand text-integrity audit of a Classics Viewer DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mode", choices=["sample", "full", "extended", "ios"])
    parser.add_argument("--corpus", default="perseus",
                        choices=["perseus", "first1k", "pta", "all"],
                        help="Which corpus to audit (default: perseus)")
    parser.add_argument("--works", nargs="*",
                        help="Specific work_ids; default = all in corpus scope")
    parser.add_argument("--report-out", type=Path, default=None,
                        help="Write Markdown report to this path "
                             "(default: ./reports/<ts>_<mode>_<corpus>.md)")
    parser.add_argument("--no-html", action="store_true",
                        help="(Phase 0 has no HTML output; flag reserved.)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Audit at most N works (for quick testing).")
    args = parser.parse_args(argv)

    db_path = REPO_ROOT / "data-prep" / f"perseus_texts_{args.mode}.db"
    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    # Read-only DB connection (mode=ro URI flag is the hard safety constraint)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    works = _select_works(conn, args.corpus, args.works, args.limit)
    print(f"[text_integrity] Auditing {len(works)} works "
          f"(corpus={args.corpus}, mode={args.mode}) "
          f"against {db_path.name}", file=sys.stderr)

    reports: list[verify.WorkReport] = []
    t_start = time.time()
    for i, work_id in enumerate(works, 1):
        if i % 25 == 0 or i == len(works):
            print(f"[text_integrity]   {i}/{len(works)} — "
                  f"passing so far: {sum(1 for r in reports if r.passed)}",
                  file=sys.stderr)
        xml = _find_source_xml(work_id)
        if xml is None:
            reports.append(verify.WorkReport.unfindable(work_id))
            continue
        policy = resolve_policy_for_work(work_id)
        reports.append(verify.verify_work(conn, xml, work_id, policy))

    conn.close()

    elapsed = time.time() - t_start
    print(f"[text_integrity] Done in {elapsed:.1f}s", file=sys.stderr)

    # Write report
    REPORTS_DIR.mkdir(exist_ok=True)
    if args.report_out:
        out_md = args.report_out
        out_json = args.report_out.with_suffix(".json")
    else:
        stem = REPORTS_DIR / f"{_timestamp()}_{args.mode}_{args.corpus}"
        out_md = stem.with_suffix(".md")
        out_json = stem.with_suffix(".json")

    meta = {"db_path": str(db_path), "mode": args.mode, "corpus": args.corpus,
            "policy_version": "v0"}
    out_md.write_text(report_mod.render(reports, fmt="md", **meta))
    out_json.write_text(report_mod.render(reports, fmt="json", **meta))

    # Console summary
    total = len(reports)
    passing = sum(1 for r in reports if r.passed)
    failing = total - passing
    print(file=sys.stderr)
    print(f"[text_integrity] Total: {total}  Passing: {passing}  Failing: {failing}",
          file=sys.stderr)
    print(f"[text_integrity] Markdown report: {out_md}", file=sys.stderr)
    print(f"[text_integrity] JSON sidecar:    {out_json}", file=sys.stderr)

    return 0 if failing == 0 else 1


# --- helpers ------------------------------------------------------------

def _select_works(conn, corpus: str, explicit: list[str] | None,
                  limit: int | None) -> list[str]:
    if explicit:
        return list(explicit[:limit]) if limit else list(explicit)

    if corpus == "perseus":
        # Perseus = no _OGL or _PTA suffix
        sql = (
            "SELECT id FROM works "
            "WHERE id NOT LIKE '%\\_OGL' ESCAPE '\\' "
            "AND id NOT LIKE '%\\_PTA' ESCAPE '\\' "
            "ORDER BY id"
        )
    elif corpus == "first1k":
        sql = "SELECT id FROM works WHERE id LIKE '%\\_OGL' ESCAPE '\\' ORDER BY id"
    elif corpus == "pta":
        sql = "SELECT id FROM works WHERE id LIKE '%\\_PTA' ESCAPE '\\' ORDER BY id"
    else:  # all
        sql = "SELECT id FROM works ORDER BY id"

    rows = conn.execute(sql).fetchall()
    out = [r[0] for r in rows]
    if limit:
        out = out[:limit]
    return out


def _find_source_xml(work_id: str) -> Path | None:
    """Best-effort source-XML locator. Returns None if not found."""
    base = work_id.replace("_OGL", "").replace("_PTA", "")
    if "." not in base:
        return None
    author, num = base.split(".", 1)
    candidates = [
        DATA_SOURCES / "canonical-greekLit/data" / author / num,
        DATA_SOURCES / "canonical-latinLit/data" / author / num,
        DATA_SOURCES / "First1KGreek/data" / author / num,
        DATA_SOURCES / "pta_data/data" / author / num,
    ]
    for d in candidates:
        if not d.is_dir():
            continue
        # Prefer source-language files; skip English translations and CTS headers.
        files = [f for f in sorted(d.glob("*.xml"))
                 if not f.name.startswith("__") and "eng" not in f.name]
        # Try grc / lat / pta-grc in that order; fall back to any non-eng xml.
        for hint in ("grc", "lat", "pta-"):
            for f in files:
                if hint in f.name:
                    return f
        if files:
            return files[0]
    return None


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    sys.exit(main())
