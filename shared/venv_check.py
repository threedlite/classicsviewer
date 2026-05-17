"""Required-library guard for build scripts.

Per BUILD.md Step 4 the build pipeline depends on NLP libraries (cltk,
stanza, indic-transliteration) plus general parsing utilities (lxml).
If the wrong Python is invoked — or `pip install -r requirements.txt`
hasn't been run — those imports fail mid-build, sometimes hours in
(e.g. an interlinear regen crashes 5 hours in because a worker can't
import stanza).

`assert_libs()` checks that the libraries needed for a given role are
importable at script startup. Fails loudly with a clear remedy.

Works on any platform — Linux, macOS, Docker, CI — because it checks
*importability* not the venv path. The venv may live anywhere as long
as the libs are reachable from sys.path.

Usage in a build entry point:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from shared.venv_check import assert_libs
    assert_libs("greek_build")    # or "latin_build", "interlinear", etc.
"""
from __future__ import annotations
import importlib
import os
import sys
from typing import Sequence


# Each role declares the libraries its scripts need. Keep the lists small —
# we want to fail fast on missing libs, not import the world.

ROLES: dict[str, list[tuple[str, str]]] = {
    # Generic Perseus/Latin build — XML parsing + CLTK NLP for Greek/Latin
    "greek_build":     [("cltk", "Classical Language Toolkit (Greek NLP)"),
                        ("lxml", "XML parsing")],
    "latin_build":     [("cltk", "Classical Language Toolkit"),
                        ("lxml", "XML parsing")],
    # Interlinear generator — uses both Greek and Sanskrit NLP pipelines
    "interlinear":     [("cltk", "Classical Language Toolkit"),
                        ("stanza", "Stanford NLP"),
                        ("lxml", "XML parsing")],
    # Sanskrit module — Stanza + Devanagari transliteration
    "sanskrit_build":  [("stanza", "Stanford NLP"),
                        ("indic_transliteration", "Sanskrit Devanagari conversion")],
    # Assembly / merge — stdlib-only currently, but we still check lxml since
    # downstream steps may shell out to scripts that need it.
    "assemble":        [("lxml", "XML parsing")],
    # Text-integrity audit tools — stdlib only.
    "audit":           [],
    # Merkle snapshotting — stdlib only.
    "merkle":          [],
}


def assert_libs(role: str = "assemble") -> None:
    """Abort with exit 2 if any library required by ``role`` is missing.

    ``role`` selects which library list to check (see ``ROLES``). Disable
    for tests via ``VENV_CHECK_DISABLE=1`` (do NOT use in production).
    """
    if os.environ.get("VENV_CHECK_DISABLE") == "1":
        return
    if role not in ROLES:
        sys.stderr.write(
            f"\nFATAL (lib_check): unknown role {role!r}. "
            f"Known roles: {sorted(ROLES)}\n\n"
        )
        sys.exit(2)

    missing: list[tuple[str, str, str]] = []
    for module, desc in ROLES[role]:
        try:
            importlib.import_module(module)
        except ImportError as e:
            missing.append((module, desc, str(e)))
    if not missing:
        return

    sys.stderr.write(
        f"\nFATAL (lib_check): {len(missing)} required librar"
        f"{'y' if len(missing) == 1 else 'ies'} missing for role {role!r}.\n\n"
    )
    for m, d, err in missing:
        sys.stderr.write(f"  - {m}  ({d})\n")
        sys.stderr.write(f"      ImportError: {err}\n")
    sys.stderr.write(
        "\n  Likely cause: this script is being invoked with a Python that's missing\n"
        "  the project's pinned dependencies. Per BUILD.md Step 4 the build requires\n"
        "  the project's venv:\n\n"
        "      python3 -m venv venv\n"
        "      venv/bin/pip install -r data-prep/requirements.txt\n"
        "      venv/bin/pip install -r sanskrit/requirements.txt   # if building Sanskrit\n\n"
        "  Re-invoke via the wrapper script (greek/run_build.sh, latin/run_build.sh,\n"
        "  sanskrit/run_build.sh) or with an explicit prefix:\n\n"
        "      <repo>/venv/bin/python3 <script.py> [args...]\n\n"
        f"  Current interpreter: {sys.executable}\n"
        f"  Current sys.prefix:  {sys.prefix}\n\n"
    )
    sys.exit(2)


# Backwards-compatible alias — old call sites used `assert_venv()`. Keep the
# name working but route to the new check. Default role is "assemble" since
# that was the dominant first caller.
def assert_venv() -> None:
    """Deprecated alias for ``assert_libs('assemble')``."""
    assert_libs("assemble")
