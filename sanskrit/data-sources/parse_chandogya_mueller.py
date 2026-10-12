#!/usr/bin/env python3
"""
Parse Müller's Chāndogya Upaniṣad translation (Wikisource HTML fetched by
download_chandogya_mueller.sh) into the DCS translation-file format read by
create_sanskrit_database_interlinear.py:

    @text=Chāndogyopaniṣad
    @translator=F. Max Müller
    1.1.1 Let a man meditate on the syllable Om, ...

Numbering: prapāṭhaka (1-8) . khaṇḍa . verse, the same scheme the DCS uses
for this text, so the build attaches each khaṇḍa's verses to the DCS chapter
with the same label.

Structure in the Wikisource HTML: each khaṇḍa begins at an anchor
<span id="KhandaN">; verses are paragraphs beginning "N. ".  Footnote
markers (<sup class="reference">) and the footnote list are removed; the
notes remain readable on Wikisource.  Page-number markers are removed.

Checks (any failure stops the build): khaṇḍa anchors run 1..N without gaps
in every prapāṭhaka; verse numbers run 1..M without gaps in every khaṇḍa;
no verse text is empty.
"""

import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IN_DIR = os.path.join(HERE, 'mueller')
OUT_PATH = os.path.join(IN_DIR, 'chandogya_mueller.txt')


def clean_html(fragment):
    """Drop references, page markers and tags; unescape; collapse whitespace."""
    fragment = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', fragment, flags=re.S)
    fragment = re.sub(r'<span[^>]*class="pagenum[^"]*"[^>]*>.*?</span>\s*</span>', '', fragment, flags=re.S)
    fragment = re.sub(r'<[^>]+>', ' ', fragment)
    text = html.unescape(fragment).replace('​', '')
    return re.sub(r'\s+', ' ', text).strip()


def parse_prapathaka(path, book):
    h = open(path, encoding='utf-8').read()
    # Cut away the footnote list at the end of the page.
    cut = h.find('<ol class="references">')
    if cut > 0:
        h = h[:cut]
    # Cut at the start of the anchor's tag, not at the id attribute, so no
    # half tag is left at either end of a chunk.
    anchors = [(m.start(), int(m.group(1))) for m in re.finditer(r'<span[^>]*\bid="Khanda(\d+)"', h)]
    if not anchors or [n for _, n in anchors] != list(range(1, len(anchors) + 1)):
        raise SystemExit(f'{path}: khanda anchors {[n for _, n in anchors]} are not 1..N')
    verses = {}
    for (start, n), nxt in zip(anchors, anchors[1:] + [(len(h), None)]):
        chunk = h[start:nxt[0]]
        # Verse text is not always inside <p>: at scan-page boundaries it
        # continues as bare text between a </p> and a <div>.  Remove the
        # reference and page-number markup from the whole chunk first (tags
        # may span lines), turn every block boundary into a line break, drop
        # the remaining tags, and read the lines.
        chunk = re.sub(r'<style\b[^>]*>.*?</style>', '', chunk, flags=re.S)
        chunk = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', chunk, flags=re.S)
        chunk = re.sub(r'<span[^>]*class="pagenum[^"]*"[^>]*>.*?</span>\s*</span>', '', chunk, flags=re.S)
        chunk = re.sub(r'</?(?:p|div|br|h\d|ol|li)\b[^>]*>', '\n', chunk)
        chunk = re.sub(r'<[^>]+>', ' ', chunk, flags=re.S)
        paras = [clean_html(p) for p in chunk.split('\n')]
        paras = [p for p in paras if p]
        current = None
        expected = 1
        for p in paras[1:]:          # paras[0] is the khanda heading
            # "4. text", or a range Müller translates as one unit: "1, 2. text"
            m = re.match(r'^(\d+)(?:\s*[,–-]\s*(\d+))?\.\s+(.*)$', p)
            if m:
                first = int(m.group(1))
                last = int(m.group(2)) if m.group(2) else first
                if first != expected or last < first:
                    raise SystemExit(f'{path}: khanda {n}: verse {m.group(1)} follows {expected - 1}')
                current = f'{first}-{last}' if last > first else str(first)
                verses.setdefault(n, {})[current] = m.group(3).strip()
                expected = last + 1
            elif current is not None:
                # continuation of the same verse across a page break
                verses[n][current] += ' ' + p
        if n not in verses:
            raise SystemExit(f'{path}: khanda {n} has no numbered verses')
        for v, t in verses[n].items():
            if not t:
                raise SystemExit(f'{path}: {book}.{n}.{v} is empty')
    return verses


def main():
    lines = ['@text=Chāndogyopaniṣad', '@translator=F. Max Müller',
             '@source=Sacred Books of the East, vol. 1 (Oxford 1879), transcribed on English Wikisource',
             '@prepared-by=parse_chandogya_mueller.py']
    total = 0
    for book in range(1, 9):
        path = os.path.join(IN_DIR, f'chandogya_{book}.html')
        if not os.path.isfile(path):
            raise SystemExit(f'{path} missing; run download_chandogya_mueller.sh')
        verses = parse_prapathaka(path, book)
        for n in sorted(verses):
            for v in sorted(verses[n], key=lambda s: int(s.split('-')[0])):
                lines.append(f'{book}.{n}.{v} {verses[n][v]}')
                total += 1
        print(f'prapathaka {book}: {len(verses)} khandas, {sum(len(x) for x in verses.values())} verses')
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'wrote {OUT_PATH}: {total} verses')


if __name__ == '__main__':
    main()
