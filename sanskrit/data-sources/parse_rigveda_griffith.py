#!/usr/bin/env python3
"""
Parse Griffith's Rig Veda translation (Wikisource HTML fetched by
download_rigveda_griffith.py) into the stanza-numbered text file read by
load_rigveda() in create_sanskrit_database_interlinear.py:

    ;;; Agni.
    1.1.1 I laud Agni, the chosen Priest, God, minister of sacrifice, The Hotar, lavishest of wealth.
    1.1.2 Worthy is Agni to be praised ...

Two page formats occur on Wikisource:
- plain transcriptions (1,024 pages): a <pre> block or <p> paragraphs with
  <br/> line breaks; a stanza begins with its number at the start of a line
  ("N. text", also "N.text", "N, text", "N text", and "I" for the first
  stanza where the digit was transcribed as a letter); continuation lines
  are indented;
- proofread transclusions (4 pages): <div class="ws-poem-stanza"> blocks
  with <span class="ws-poem-versenum">N</span>, the first stanza unnumbered.
Footnote markers (<sup class="reference">) and the footnote list are
removed; the notes remain readable on Wikisource.

Hymn numbering in Book 8: Griffith prints the eleven Vālakhilya hymns as an
appendix after 8.92 (Wikisource pages Hymn 93-103, after a "VALAKHILYA"
heading at the end of Hymn 92); the DCS, following Aufrecht, numbers them
8.49-8.59 and shifts the following hymns by eleven.  The output uses the
DCS numbering so that stanzas match the Sanskrit text.

Checks (any failure stops the build): the hymn numbers of each book run
1..M without gaps; stanza numbers never run backwards.  Stanzas Griffith
left untranslated (e.g. 10.61.5-9) are absent from the output and reported;
a misprinted stanza number is read as the expected one and reported; a page
with no stanzas (1.179 carries only an editorial note) is reported and the
hymn is left without translation.
"""

import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
IN_DIR = os.path.join(HERE, 'wikisource', 'rigveda')
OUT_PATH = os.path.join(HERE, 'wikisource', 'rigveda_griffith.txt')

# The DCS numbers the Vālakhilya hymns 8.49-8.59 (Aufrecht's numbering).
VALAKHILYA_FIRST = 49
VALAKHILYA_RE = re.compile(r'(?i)^v[aâ]lakhilya\b')


def clean(fragment):
    fragment = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', fragment, flags=re.S)
    fragment = re.sub(r'<[^>]+>', ' ', fragment, flags=re.S)
    text = html.unescape(fragment).replace('​', '')
    # a few pages carry HTML-escaped tags inside the text (an errata link in
    # 1.121); strip them after unescaping
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_plain(h, path):
    """Plain transcription pages. Returns (stanzas, has_valakhilya_heading)."""
    start = h.find('id="ws-data"')
    if start > 0:
        start = h.find('</div>', start) + 6
        h = h[start:]
    end = h.find('<!-- \nNewPP')
    if end > 0:
        h = h[:end]
    h = re.sub(r'<br\s*/?>|</?(?:p|pre|div)\b[^>]*>', '\n', h)
    lines = [clean(l) for l in h.split('\n')]
    stanzas = {}            # stanza number -> text (Griffith omits some stanzas)
    preface = []
    heading = False
    notes = []
    last = 0
    for l in lines:
        if not l:
            continue
        if VALAKHILYA_RE.match(l):
            heading = True          # appendix heading printed after the last regular hymn
            continue
        expected = last + 1
        # "N. text" / "N, text" / "N.text": a numbered stanza start.  N above
        # the expected number means Griffith omitted stanzas (he left some
        # untranslated, e.g. 10.61.5-9); N below it is a misprinted number
        # (1.91 prints "16." for 18) and is read as the expected one.  A bare
        # "N text" or an "I" counts only when it is exactly the next number,
        # so text lines beginning with a numeral or "I ..." stay with the
        # stanza they belong to.
        m = re.match(r'^(\d+)([.,])\s*(.*)$', l) or re.match(r'^(\d+)(\s)(.*)$', l)
        if m and (m.group(2) in '.,' or int(m.group(1)) == expected):
            num = int(m.group(1))
            if num > expected:
                notes.append(f'stanzas {expected}-{num - 1} absent (not translated)')
            elif num < expected:
                notes.append(f'stanza number {num} printed where {expected} is expected; read as {expected}')
                num = expected
            stanzas[num] = m.group(3).strip()
            last = num
            continue
        if expected == 1 and re.match(r'^I[.,]?\s+', l):
            stanzas[1] = re.sub(r'^I[.,]?\s+', '', l).strip()
            last = 1
            continue
        if stanzas:
            stanzas[last] = (stanzas[last] + ' ' + l).strip()
        else:
            preface.append(l)          # e.g. the editorial note before 1.179
    for n in notes:
        print(f'  {os.path.basename(path)}: {n}')
    if preface:
        print(f'  {os.path.basename(path)}: {len(preface)} line(s) before stanza 1 not loaded: {preface[0][:60]!r}')
    return stanzas, heading


def parse_hymn(path):
    """Returns (title, stanzas, has_valakhilya_heading)."""
    h = open(path, encoding='utf-8').read()
    h = re.sub(r'<style\b[^>]*>.*?</style>', '', h, flags=re.S)
    cut = h.find('<ol class="references">')
    if cut > 0:
        h = h[:cut]
    # deity / title line: "HYMN I. Agni." rendered in a centred block
    title = ''
    m = re.search(r'HYMN\s+[IVXLC]+\.?(.*?)</', h, flags=re.S)
    if m:
        title = clean(m.group(1))
    if 'ws-poem-stanza' not in h:
        stanzas, heading = parse_plain(h, path)
        if not stanzas:
            # A page holding only an editorial note (1.179: Griffith left the
            # hymn untranslated in the main text) yields no stanzas; the hymn
            # then has no translation, which the build reports.
            print(f'  {os.path.basename(path)}: no stanzas on the page; hymn left without translation')
        return title, stanzas, heading
    stanzas = {}
    for sm in re.finditer(r'<div class="ws-poem-stanza"[^>]*>(.*?)</div>', h, flags=re.S):
        body = sm.group(1)
        num = None
        nm = re.match(r'\s*<span class="ws-poem-versenum">\s*(\d+)\s*</span>', body)
        if nm:
            num = int(nm.group(1))
            body = body[nm.end():]
        # ws-poem-line spans contain nested spans (small caps), so they are
        # not matched to their closing tag; each line start becomes a line
        # break instead and the remaining tags are stripped.
        body = re.sub(r'<span class="ws-poem-break">.*?</span>', ' ', body, flags=re.S)
        body = body.replace('<span class="ws-poem-line">', '\n')
        lines = [clean(l) for l in body.split('\n')]
        text = ' '.join(l for l in lines if l)
        if not text:
            continue
        expected = len(stanzas) + 1
        if num is None:
            num = expected
        if num != expected:
            raise SystemExit(f'{path}: stanza {num} follows {expected - 1}')
        stanzas[num] = text
    if not stanzas:
        raise SystemExit(f'{path}: no stanzas found')
    return title, stanzas, False


def renumber(book, parsed):
    """
    Map Wikisource hymn numbers of one book to DCS numbers.

    parsed: {wikisource_hymn: (title, stanzas, heading)}.  When a page carries
    the Vālakhilya heading, the pages after it are the Vālakhilya hymns and
    become VALAKHILYA_FIRST..; the regular hymns from VALAKHILYA_FIRST on
    are shifted up by their count.
    """
    marker = [hn for hn, (_, _, heading) in parsed.items() if heading]
    if not marker:
        return {hn: hn for hn in parsed}
    if len(marker) != 1:
        raise SystemExit(f'book {book}: Vālakhilya heading found on {len(marker)} pages')
    last_regular = marker[0]
    appendix = sorted(hn for hn in parsed if hn > last_regular)
    k = len(appendix)
    mapping = {}
    for hn in parsed:
        if hn > last_regular:
            mapping[hn] = VALAKHILYA_FIRST + appendix.index(hn)
        elif hn >= VALAKHILYA_FIRST:
            mapping[hn] = hn + k
        else:
            mapping[hn] = hn
    print(f'  book {book}: {k} Vālakhilya hymns after Hymn {last_regular} renumbered '
          f'{VALAKHILYA_FIRST}-{VALAKHILYA_FIRST + k - 1}; Hymns {VALAKHILYA_FIRST}-{last_regular} shifted to '
          f'{VALAKHILYA_FIRST + k}-{last_regular + k}')
    if sorted(mapping.values()) != list(range(1, len(parsed) + 1)):
        raise SystemExit(f'book {book}: renumbering is not a permutation of 1..{len(parsed)}')
    return mapping


def main():
    files = {}
    for name in os.listdir(IN_DIR) if os.path.isdir(IN_DIR) else []:
        m = re.match(r'^book(\d+)_hymn(\d+)\.html$', name)
        if m:
            files[(int(m.group(1)), int(m.group(2)))] = os.path.join(IN_DIR, name)
    if not files:
        raise SystemExit(f'no hymn files in {IN_DIR}; run download_rigveda_griffith.py')
    books = sorted({b for b, _ in files})
    out = []
    total = 0
    for b in books:
        hymns = sorted(hn for bb, hn in files if bb == b)
        if hymns != list(range(1, len(hymns) + 1)):
            raise SystemExit(f'book {b}: hymn numbers {hymns[:5]}... are not 1..{len(hymns)}')
        parsed = {hn: parse_hymn(files[(b, hn)]) for hn in hymns}
        mapping = renumber(b, parsed)
        for hn in sorted(hymns, key=lambda x: mapping[x]):
            title, stanzas, _ = parsed[hn]
            if not stanzas:
                continue
            out.append(f';;; {title}' if title else ';;;')
            for i in sorted(stanzas):
                out.append(f'{b}.{mapping[hn]}.{i} {stanzas[i]}')
                total += 1
        print(f'book {b}: {len(hymns)} hymns')
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print(f'wrote {OUT_PATH}: {len(files)} hymns, {total} stanzas')


if __name__ == '__main__':
    main()
