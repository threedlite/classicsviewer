#!/usr/bin/env python3
"""Remove every http:// and https:// reference from the mirror.

Makes the mirror fully self-contained (no network loads at all):
  - <script> blocks containing a URL              -> removed entirely
  - <a href="http(s)://...">text</a>              -> unwrapped (text kept)
  - <img>/<link>/<iframe>/<object>/<embed> w/ URL -> removed
  - any remaining literal http:// or https://     -> scheme stripped

Relative links (already local) are left untouched.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rhetoric.byu.edu")
if not os.path.isdir(ROOT):
    sys.exit(f"mirror dir not found: {ROOT}")

URL = re.compile(r'https?://', re.I)

SCRIPT_RE = re.compile(r'<script\b[^>]*>.*?</script>', re.I | re.S)
A_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.I | re.S)
RES_RE = re.compile(r'<(?:img|link|iframe|object|embed)\b[^>]*?/?>', re.I)

stats = {"script": 0, "a": 0, "resource": 0, "scheme": 0}


def has_url(s):
    return bool(URL.search(s))


def transform(text):
    # 1. drop <script> blocks that pull in or reference a URL
    def script_sub(m):
        if has_url(m.group(0)):
            stats["script"] += 1
            return ""
        return m.group(0)

    text = SCRIPT_RE.sub(script_sub, text)

    # 2. unwrap <a> whose href is an absolute URL — keep the visible text
    def a_sub(m):
        if has_url(m.group(1)):
            stats["a"] += 1
            return m.group(2)
        return m.group(0)

    text = A_RE.sub(a_sub, text)

    # 3. remove resource tags pointing at an absolute URL
    def res_sub(m):
        if has_url(m.group(0)):
            stats["resource"] += 1
            return ""
        return m.group(0)

    text = RES_RE.sub(res_sub, text)

    # 4. sweep: strip the scheme from anything still left (text, attrs, etc.)
    text, n = URL.subn("", text)
    stats["scheme"] += n

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
    print(f"  <script> blocks removed       : {stats['script']}")
    print(f"  <a> external links unwrapped  : {stats['a']}")
    print(f"  resource tags removed         : {stats['resource']}")
    print(f"  bare http(s):// schemes swept : {stats['scheme']}")


if __name__ == "__main__":
    main()
