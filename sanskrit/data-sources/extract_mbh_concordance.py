#!/usr/bin/env python3
"""
Extract the critical-edition -> Ganguli/Roy concordance of the Mahabharata
into mbh_ce_ganguli_concordance.csv.

Source: "Appendix: Concordance of Critical Edition and Ganguli/Roy
translation", in S. Brodbeck and B. Black (eds), Gender and Narrative in the
Mahabharata, Routledge 2007, pp. 279-284. The PDF of the appendix was posted
to the INDOLOGY list on 2019-07-02:
  https://list.indology.info/pipermail/indology/attachments/20190702/f7d5e428/attachment.pdf

The table is printed in two columns per page. Each row pairs a critical-
edition (CE) chapter, chapter range, or chapter.verse range on the left with
a Ganguli section or section range on the right ("?" where the authors found
no section). Text is extracted with its page coordinates, assigned to the
left or right column by x position, and read column by column. Where the
extraction loses the space between the two numbers (e.g. "1-51-5" for
"1-5 1-5") the split is recovered from the one reading that keeps the CE
chapters contiguous and the Ganguli sections non-decreasing; a row with no
such reading, or more than one, stops the extraction with an error.

The output is checked, per book, for contiguous CE coverage from chapter 1
to the last chapter of that book in the critical edition. Verse gaps inside a
chapter (e.g. 1.119.35-38 missing from the printed table) are allowed and
listed, because the build only uses the table at chapter granularity.

Usage:
  python3 extract_mbh_concordance.py            # downloads the PDF to a temp dir
  python3 extract_mbh_concordance.py local.pdf  # uses a local copy

The CSV is checked in; rerun this script only to regenerate it. The PDF is
not stored in the repository.
"""

import csv
import os
import re
import sys
import tempfile
import urllib.request
from collections import defaultdict

PDF_URL = ('https://list.indology.info/pipermail/indology/attachments/'
           '20190702/f7d5e428/attachment.pdf')
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'mbh_ce_ganguli_concordance.csv')

# Chapters per book in the critical edition (John Smith's electronic text).
CE_CHAPTERS = {1: 225, 2: 72, 3: 299, 4: 67, 5: 197, 6: 117, 7: 173, 8: 69,
               9: 64, 10: 18, 11: 27, 12: 353, 13: 154, 14: 96, 15: 47,
               16: 9, 17: 3, 18: 5}

DASH = '–'
FIRST_PRINTED_PAGE = 279   # the appendix's first page carries this page number
LEFT_MAX_X = 190      # fragments left of this are the left column (its numbers end near x=156)
RIGHT_MIN_X = 215     # fragments right of this are the right column
                      # (page numbers sit at x ~208 and are ignored)


def page_rows(page):
    """Return [(column, y, text)] for one page, left column first, top down."""
    frags = []

    def visit(text, cm, tm, font_dict, font_size):
        t = text.strip()
        if t:
            frags.append((round(tm[5], 1), round(tm[4], 1), t))

    page.extract_text(visitor_text=visit)
    cols = {0: defaultdict(list), 1: defaultdict(list)}
    for y, x, t in frags:
        if x < LEFT_MAX_X:
            cols[0][y].append((x, t))
        elif x >= RIGHT_MIN_X:
            cols[1][y].append((x, t))
    rows = []
    for col in (0, 1):
        for y in sorted(cols[col], reverse=True):
            rows.append((col, y, ''.join(t for _, t in sorted(cols[col][y]))))
    return rows


CE_RE = re.compile(r'^(\d+)(?:\.(\d+)[a-d]?(?:' + DASH + r'(\d+)[a-d]?)?)?(?:' + DASH + r'(\d+))?$')
ROY_RE = re.compile(r'^(\d+)(?:[' + DASH + r'/](\d+))?$')


def parse_ce(s):
    """'c' | 'c–d' | 'c.a' | 'c.a–b' (verse numbers may carry a pada letter)."""
    m = CE_RE.match(s)
    if not m:
        return None
    c = int(m.group(1))
    if m.group(2) is not None:
        a = int(m.group(2))
        b = int(m.group(3)) if m.group(3) is not None else a
        if m.group(4) is not None or b < a:
            return None
        return {'c1': c, 'c2': c, 'v1': a, 'v2': b}
    d = int(m.group(4)) if m.group(4) is not None else c
    if d < c:
        return None
    return {'c1': c, 'c2': d, 'v1': None, 'v2': None}


def parse_roy(s):
    if s == '?':
        return {'r1': None, 'r2': None}
    m = ROY_RE.match(s)
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    if b < a:
        return None
    return {'r1': a, 'r2': b}


def contiguous(prev, ce):
    """CE coverage must continue where the previous row ended."""
    if prev is None:
        return ce['c1'] == 1 and ce['v1'] in (None, 1)
    pc, pv = prev
    if ce['v1'] is not None:
        if pv is None:
            return ce['c1'] == pc + 1 and ce['v1'] == 1
        return (ce['c1'] == pc and ce['v1'] >= pv) or (ce['c1'] == pc + 1 and ce['v1'] == 1)
    return ce['c1'] == pc + 1


def candidates(s, prev_end, prev_roy):
    """All (ce, roy, normalised text) readings of a row consistent with the previous row."""
    def ok(ce, roy, check_order=True):
        return (ce is not None and roy is not None and contiguous(prev_end, ce)
                and (not check_order or roy['r1'] is None or roy['r1'] >= prev_roy))
    out = []
    printed = None
    if ' ' in s:
        a, b = s.split(' ', 1)
        printed = (parse_ce(a), parse_roy(b.replace(' ', '')))
        if ok(*printed):
            out.append((printed[0], printed[1], s))
    if not out:
        compact = s.replace(' ', '')
        for i in range(1, len(compact)):
            ce, roy = parse_ce(compact[:i]), parse_roy(compact[i:])
            if ok(ce, roy):
                out.append((ce, roy, compact[:i] + ' ' + compact[i:]))
    if not out and printed is not None and ok(*printed, check_order=False):
        # Printed with its space and continuous in CE, but its Ganguli number
        # runs backwards (13.99 -> 58).  Kept as printed; verify() reports it
        # and the build does not use such a row.
        out.append((printed[0], printed[1], s))
    return out


def extract(pdf_path):
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    rows = []
    book = None
    prev_end = None
    prev_roy = 0
    respaced = []
    skipped = []
    done = False
    for page_no, page in enumerate(reader.pages, 1):
        if done:
            break
        for col, y, s in page_rows(page):
            m = re.match(r'^Book (\d+),', s)
            if m:
                if book is not None and prev_end != (CE_CHAPTERS[book], None):
                    raise SystemExit(f'Book {book} ended at CE {prev_end}, expected chapter {CE_CHAPTERS[book]}')
                book = int(m.group(1))
                prev_end, prev_roy = None, 0
                continue
            if book is None or not re.match(r'^[\d' + DASH + r'./?a-d ]+$', s):
                continue
            if s == str(FIRST_PRINTED_PAGE + page_no - 1):
                skipped.append((page_no, book, s))     # the printed page number
                continue
            cands = candidates(s, prev_end, prev_roy)
            if len(cands) != 1:
                raise SystemExit(f'page {page_no} book {book}: cannot read row {s!r} after CE {prev_end}, '
                                 f'Ganguli {prev_roy}: candidates {[c[2] for c in cands]}')
            ce, roy, norm = cands[0]
            if norm != s:
                respaced.append((book, s, norm))
            rows.append({'book': book, **ce, **roy, 'raw': norm})
            prev_end = (ce['c2'], ce['v2'])
            if roy['r1'] is not None:
                prev_roy = roy['r2']
            if book == 18 and prev_end == (CE_CHAPTERS[18], None):
                done = True
                break
    if book != 18 or prev_end != (CE_CHAPTERS[18], None):
        raise SystemExit(f'extraction ended in book {book} at {prev_end}; the table is incomplete')
    return rows, respaced, skipped


def verify(rows):
    """Contiguity per book, verse gaps, non-monotonic Ganguli references."""
    report = []
    by_book = defaultdict(list)
    for r in rows:
        by_book[r['book']].append(r)
    for b in range(1, 19):
        rs = by_book[b]
        if not rs:
            raise SystemExit(f'book {b}: no rows')
        if rs[0]['c1'] != 1 or rs[-1]['c2'] != CE_CHAPTERS[b]:
            raise SystemExit(f'book {b}: rows cover {rs[0]["c1"]}..{rs[-1]["c2"]}, expected 1..{CE_CHAPTERS[b]}')
        last_roy = 0
        for prev, cur in zip(rs, rs[1:]):
            if cur['v1'] is not None and prev['c1'] == cur['c1'] and prev['v2'] is not None and cur['v1'] > prev['v2'] + 1:
                report.append(f'book {b}: verse gap {prev["c1"]}.{prev["v2"] + 1}-{cur["v1"] - 1} not in the table')
        for r in rs:
            if r['r1'] is not None:
                if r['r1'] < last_roy:
                    report.append(f'book {b}: row {r["raw"]!r} refers back to Ganguli {r["r1"]} after {last_roy} (printed as is; the build rejects it)')
                else:
                    last_roy = r['r2']
    return report


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    tmpdir = None
    if pdf_path is None:
        tmpdir = tempfile.mkdtemp(prefix='mbh_concordance_')
        pdf_path = os.path.join(tmpdir, 'concordance.pdf')
        print(f'downloading {PDF_URL}')
        urllib.request.urlretrieve(PDF_URL, pdf_path)
    rows, respaced, skipped = extract(pdf_path)
    report = verify(rows)
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        f.write('# Critical edition -> Ganguli/Roy concordance, transcribed by extract_mbh_concordance.py\n')
        f.write('# from the appendix of Brodbeck & Black (eds), Gender and Narrative in the Mahabharata, Routledge 2007.\n')
        f.write('# ce_verse_from/ce_verse_to are empty for whole-chapter rows; ganguli_from/ganguli_to are empty for "?" rows.\n')
        w = csv.writer(f)
        w.writerow(['book', 'ce_chapter_from', 'ce_verse_from', 'ce_chapter_to', 'ce_verse_to',
                    'ganguli_from', 'ganguli_to', 'printed'])
        for r in rows:
            w.writerow([r['book'], r['c1'], r['v1'] if r['v1'] is not None else '',
                        r['c2'], r['v2'] if r['v2'] is not None else '',
                        r['r1'] if r['r1'] is not None else '', r['r2'] if r['r2'] is not None else '',
                        r['raw']])
    print(f'wrote {OUT_CSV}: {len(rows)} rows, '
          f'{sum(1 for r in rows if r["v1"] is not None)} verse-level rows, '
          f'{sum(1 for r in rows if r["r1"] is None)} rows with "?"')
    per_book = defaultdict(int)
    for r in rows:
        per_book[r['book']] += 1
    print('rows per book:', dict(per_book))
    if respaced:
        print(f'{len(respaced)} rows re-spaced from the extraction:')
        for b, s, n in respaced:
            print(f'  book {b}: {s!r} -> {n!r}')
    if skipped:
        print(f'{len(skipped)} printed page numbers skipped: {[(p, s) for p, b, s in skipped]}')
    if report:
        print(f'{len(report)} notes:')
        for line in report:
            print('  ' + line)


if __name__ == '__main__':
    main()
