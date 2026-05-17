#!/usr/bin/env python3
"""Rewrite absolute rhetoric.byu.edu URLs in the local mirror to relative paths.

wget's --convert-links leaves same-site links that were written as absolute
http(s)://rhetoric.byu.edu/... URLs untouched. This makes the mirror fully
self-contained by turning each such href/src into a relative path to the
corresponding local file.

Genuinely third-party links (other hosts) are left alone — there is no local
file to point them at.
"""
import os
import re
import sys
from urllib.parse import unquote

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rhetoric.byu.edu")
if not os.path.isdir(ROOT):
    sys.exit(f"mirror dir not found: {ROOT}")

# href="..." or src="..." pointing at http(s)://rhetoric.byu.edu/...
PATTERN = re.compile(
    r"""(?P<pre>\b(?:href|src)\s*=\s*)(?P<q>["'])"""
    r"""https?://rhetoric\.byu\.edu(?P<path>[^"']*)"""
    r"""(?P=q)""",
    re.IGNORECASE,
)

dangling = set()  # relative links whose target file does not exist locally


def relative_for(src_file, url_path):
    """Return a relative URL from src_file to the local file for url_path."""
    suffix = ""
    # preserve a #fragment; drop any ?query (meaningless for static files)
    if "#" in url_path:
        url_path, frag = url_path.split("#", 1)
        suffix = "#" + frag
    if "?" in url_path:
        url_path = url_path.split("?", 1)[0]

    path = unquote(url_path).lstrip("/")
    if path in ("", "/"):
        path = "index.html"

    target = os.path.normpath(os.path.join(ROOT, path))

    # tolerate wget's --adjust-extension (.htm served as html saved as .html)
    if not os.path.exists(target):
        if target.lower().endswith(".htm") and os.path.exists(target + "l"):
            target += "l"
        elif target.lower().endswith(".html") and os.path.exists(target[:-1]):
            target = target[:-1]

    rel = os.path.relpath(target, os.path.dirname(src_file))
    if not os.path.exists(target):
        dangling.add(os.path.relpath(target, ROOT))
    # encode spaces only, matching wget's own converted-link style
    return rel.replace(os.sep, "/").replace(" ", "%20") + suffix


def process(src_file):
    with open(src_file, "r", encoding="utf-8", errors="surrogateescape") as fh:
        text = fh.read()

    count = 0

    def repl(m):
        nonlocal count
        count += 1
        rel = relative_for(src_file, m.group("path"))
        q = m.group("q")
        return f"{m.group('pre')}{q}{rel}{q}"

    new_text = PATTERN.sub(repl, text)
    if new_text != text:
        with open(src_file, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(new_text)
    return count


def main():
    total_refs = 0
    changed_files = 0
    for dirpath, _, names in os.walk(ROOT):
        for name in names:
            if name.lower().endswith((".htm", ".html")):
                n = process(os.path.join(dirpath, name))
                if n:
                    changed_files += 1
                    total_refs += n

    print(f"Rewrote {total_refs} absolute rhetoric.byu.edu refs "
          f"in {changed_files} files.")
    if dangling:
        print(f"\n{len(dangling)} of the rewritten links point to files not "
              f"present in the mirror (broken on the live site too):")
        for d in sorted(dangling):
            print(f"  {d}")


if __name__ == "__main__":
    main()
