#!/usr/bin/env python3
"""Remove third-party links from the local mirror.

  - <a> to external sites : unwrap  (keep the visible text, drop the link)
  - <script>/<img>/<link> to external sites : remove the element
  - creativecommons.org is kept as an exception (it is the CC BY 3.0 notice)

Same-site links were already made relative by relativize.py and are untouched.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rhetoric.byu.edu")
if not os.path.isdir(ROOT):
    sys.exit(f"mirror dir not found: {ROOT}")

KEEP_HOSTS = ("creativecommons.org",)


def host_of(url):
    m = re.match(r'(?:https?:)?//([^/?#]+)', url.strip(), re.I)
    return m.group(1).lower() if m else None


def is_external(url):
    """True if url points off-site and is not a kept exception."""
    h = host_of(url)
    if h is None:
        return False  # relative path, mailto:, #fragment, javascript:
    return not (h in KEEP_HOSTS or any(h.endswith("." + k) for k in KEEP_HOSTS))


def attr_val(attrs, name):
    m = re.search(name + r'\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', attrs, re.I)
    return m.group(1).strip('"\'') if m else None


A_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.I | re.S)
SCRIPT_RE = re.compile(r'<script\b([^>]*)>.*?</script>', re.I | re.S)
IMG_RE = re.compile(r'<img\b([^>]*?)/?>', re.I)
LINK_RE = re.compile(r'<link\b([^>]*?)/?>', re.I)

stats = {"a": 0, "script": 0, "img": 0, "link": 0}


def transform(text):
    # scripts first: their JS body may contain stray < > that confuse <a> matching
    def script_sub(m):
        src = attr_val(m.group(1), "src")
        if src and is_external(src):
            stats["script"] += 1
            return ""
        return m.group(0)

    text = SCRIPT_RE.sub(script_sub, text)

    def a_sub(m):
        href = attr_val(m.group(1), "href")
        if href and is_external(href):
            stats["a"] += 1
            return m.group(2)  # unwrap: keep inner text/markup
        return m.group(0)

    text = A_RE.sub(a_sub, text)

    def img_sub(m):
        src = attr_val(m.group(1), "src")
        if src and is_external(src):
            stats["img"] += 1
            return ""
        return m.group(0)

    text = IMG_RE.sub(img_sub, text)

    def link_sub(m):
        href = attr_val(m.group(1), "href")
        if href and is_external(href):
            stats["link"] += 1
            return ""
        return m.group(0)

    text = LINK_RE.sub(link_sub, text)
    return text


def main():
    changed = 0
    for dirpath, _, names in os.walk(ROOT):
        for name in names:
            if not name.lower().endswith((".htm", ".html")):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
                text = fh.read()
            new = transform(text)
            if new != text:
                changed += 1
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(new)

    print(f"Modified {changed} files.")
    print(f"  <a> external links unwrapped : {stats['a']}")
    print(f"  <script> external removed    : {stats['script']}")
    print(f"  <img> external removed       : {stats['img']}")
    print(f"  <link> external removed      : {stats['link']}")
    print("  creativecommons.org refs kept as the CC BY 3.0 license notice.")


if __name__ == "__main__":
    main()
