#!/usr/bin/env python3
"""
English translations for DCS works, fetched from Project Gutenberg and
English Wikisource, parsed into tab-separated files that the build attaches
to the DCS text (create_sanskrit_database_interlinear.py, translation_map).

Each entry in SOURCES names a DCS work, where its translation comes from,
and a parser that turns the fetched text into rows

    (book_label, chapter_label, verse_label, text)

using the DCS labels of that work (book = the second part of the DCS
"## chapter:" header, chapter = the remaining parts joined with '.', or '1'
for 2-part headers).  The build writes one translation segment per DCS
chapter whose label matches, numbering the verses with the labels given.

Output: generated/<slug>.tsv with '@' header lines followed by
    book<TAB>chapter<TAB>verse<TAB>text
Fetched pages are cached under generated/gutenberg/ and generated/wikisource/;
everything under generated/ is git-ignored and rebuilt on demand.

Licence policy (LICENSE_COMPLIANCE.md): Project Gutenberg texts are included
on that basis; Wikisource transcriptions are public-domain translations
under Wikisource's CC BY-SA terms; no NonCommercial source; no OCR.

Run `python3 translation_sources.py --check [work ...]` to fetch, parse and
compare each work's keys with the DCS chapter labels without touching the
database.
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
GEN_DIR = os.path.join(HERE, 'generated')
DCS_FILES = os.path.join(HERE, '..', '..', 'data-sources', 'sanskrit', 'dcs', 'data', 'conllu', 'files')
UA = 'classicsviewer-build/1.0 (https://github.com/threedlite/classicsviewer)'
WS_API = 'https://en.wikisource.org/w/api.php'

ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def roman_to_int(s):
    total, prev = 0, 0
    for ch in reversed(s.upper()):
        n = ROMAN[ch]
        total = total - n if n < prev else total + n
        prev = max(prev, n)
    return total


ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth',
            'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth',
            'eighteenth', 'nineteenth', 'twentieth']


# ---------------------------------------------------------------------------
# fetching and caching
# ---------------------------------------------------------------------------

def _get(url, retries=5):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def gutenberg_lines(number):
    """Lines of the Gutenberg text between its START and END markers."""
    path = os.path.join(GEN_DIR, 'gutenberg', f'pg{number}.txt')
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = _get(f'https://www.gutenberg.org/cache/epub/{number}/pg{number}.txt')
        with open(path, 'wb') as f:
            f.write(data)
    text = open(path, 'rb').read().decode('utf-8-sig').replace('\r\n', '\n')
    starts = [m.end() for m in re.finditer(r'^\*\*\* START OF.*$', text, re.M)]
    ends = [m.start() for m in re.finditer(r'^\*\*\* END OF', text, re.M)]
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError(f'pg{number}: expected one START and one END marker')
    return text[starts[0] + 1:ends[0]].split('\n')


def wikisource_html(title):
    """Rendered HTML of one Wikisource page (parse API), cached."""
    slug = re.sub(r'[^A-Za-z0-9._-]+', '_', title)[:150]
    path = os.path.join(GEN_DIR, 'wikisource', slug + '.html')
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        q = urllib.parse.urlencode({'action': 'parse', 'page': title, 'prop': 'text', 'format': 'json', 'disabletoc': '1'})
        d = json.loads(_get(WS_API + '?' + q))
        if 'parse' not in d:
            raise ValueError(f'Wikisource page not found: {title}')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(d['parse']['text']['*'])
        time.sleep(0.2)
    return open(path, encoding='utf-8').read()


def wikisource_allpages(prefix):
    out, cont = [], {}
    while True:
        q = urllib.parse.urlencode({'action': 'query', 'list': 'allpages', 'apprefix': prefix, 'aplimit': '500', 'format': 'json', **cont})
        d = json.loads(_get(WS_API + '?' + q))
        out += [p['title'] for p in d['query']['allpages']]
        if 'continue' in d:
            cont = {'apcontinue': d['continue']['apcontinue']}
        else:
            break
    return out


def html_lines(h):
    """Rendered Wikisource HTML -> clean text lines (footnotes and page markers removed)."""
    h = re.sub(r'<style\b[^>]*>.*?</style>', '', h, flags=re.S)
    cut = h.find('<ol class="references">')
    if cut > 0:
        h = h[:cut]
    # drop the navigation header: everything up to the end of the ws-data block
    k = h.find('id="ws-data"')
    if k > 0:
        h = h[h.find('</div>', k) + 6:]
    h = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', h, flags=re.S)
    h = re.sub(r'<span[^>]*class="pagenum[^"]*"[^>]*>.*?</span>\s*</span>', '', h, flags=re.S)
    h = re.sub(r'<br\s*/?>|</?(?:p|div|pre|h\d|li|tr|table)\b[^>]*>', '\n', h)
    h = re.sub(r'<[^>]+>', ' ', h, flags=re.S)
    text = html.unescape(h).replace('​', '')
    text = re.sub(r'<[^>]+>', ' ', text)
    lines = [re.sub(r'\s+', ' ', l).strip() for l in text.split('\n')]
    # drop the page header block (everything up to and including the ws-data ids)
    return [l for l in lines if l]


def paragraphs(lines):
    """Join consecutive non-blank lines; blank lines separate paragraphs."""
    paras, cur = [], []
    for l in lines:
        if l.strip():
            cur.append(l.strip())
        elif cur:
            paras.append(' '.join(cur))
            cur = []
    if cur:
        paras.append(' '.join(cur))
    return paras


def strip_ws_header(lines):
    """Drop Wikisource's navigation header lines (before the article id line)."""
    for i, l in enumerate(lines[:12]):
        if re.search(r'\b\d{4,}\b', l) and ('→' in l or '←' in l or 'sister projects' in l):
            return lines[i + 1:]
    return lines


# ---------------------------------------------------------------------------
# parsers (each returns a list of (book, chapter, verse, text))
# ---------------------------------------------------------------------------

def gutenberg_sections(lines, heading_re, body_start_re=None):
    """
    Cut a Gutenberg text at heading lines.  Returns [(heading_match, text)].
    A heading counts only when the line is the heading alone (table-of-
    contents entries carry titles or dot leaders after the numeral).
    """
    start = 0
    if body_start_re:
        hits = [i for i, l in enumerate(lines) if re.match(body_start_re, l.strip())]
        if not hits:
            raise ValueError(f'body start {body_start_re!r} not found')
        start = hits[-1]
    out = []
    cur = None
    buf = []
    for l in lines[start:]:
        m = re.match(heading_re, l.strip())
        if m:
            if cur is not None:
                out.append((cur, '\n\n'.join(paragraphs(buf))))
            cur, buf = m, []
        elif cur is not None:
            buf.append(l)
    if cur is not None:
        out.append((cur, '\n\n'.join(paragraphs(buf))))
    return out


def parse_dutt_vishnupurana():
    """Dutt, Vishnupuranam (Gutenberg 66208): PART I-VI, SECTION I-N; one segment per chapter."""
    lines = gutenberg_lines(66208)
    rows, part, expected = [], None, 1
    for m, text in gutenberg_sections(lines, r'^(PART ([IVX]+)\.|SECTION ([IVXLC]+)\.)$'):
        if m.group(2):
            part, expected = roman_to_int(m.group(2)), 1
        elif part is not None and text:
            n = roman_to_int(m.group(3))
            if n < expected:          # misprinted numeral (Part V prints XXVIII for XXXVIII)
                n = expected
            rows.append((str(part), str(n), '1', text))
            expected = n + 1
    return rows


def parse_kern_lotus():
    """Kern, Saddharma-Pundarika (SBE 21, Wikisource): one page per chapter; DCS has 2-part headers (book = chapter)."""
    rows = []
    for n in range(1, 28):
        lines = strip_ws_header(html_lines(wikisource_html(f'Sacred Books of the East/Volume 21/Chapter {n}')))
        # text starts after the chapter heading ("C H A P T E R III." and a title line)
        idx = next((i for i, l in enumerate(lines) if re.fullmatch(r'C\s?H\s?A\s?P\s?T\s?E\s?R\s+[IVXLC]+\.?', l, flags=re.I)), None)
        if idx is None:
            raise ValueError(f'Lotus chapter {n}: heading not found')
        body = lines[idx + 1:]
        if body and body[0].isupper():
            body = body[1:]
        rows.append((str(n), '1', '1', '\n\n'.join(body)))
    return rows


def parse_whitney_atharvaveda():
    """Whitney, Atharva-Veda Samhita (Wikisource): numbered stanza paragraphs; commentary paragraphs are unnumbered and dropped."""
    # Page titles: "Book VII/Hymn 109 (114)" gives Whitney's own hymn number
    # first (the Roth-Whitney numbering the DCS follows) and the vulgate
    # number in parentheses.  Books XV and XVI are divided into paryāyas,
    # "Book XV/Paryaya 1", laid out like the hymns.  "Hymn X"-style titles
    # are redirects to the arabic-numbered pages; "Book N" pages are indexes.
    titles = []
    for t in wikisource_allpages('Atharva-Veda Samhita/Book '):
        m = re.search(r'/Book ([IVXL]+)/(?:Hymn|Paryaya) (\d+)', t)
        if m:
            titles.append((roman_to_int(m.group(1)), int(m.group(2)), t))
        elif not re.search(r'/Book [IVXL]+(?:/Hymn [IVXLC]+)?$', t):
            print(f'  Whitney: page title not understood, skipped: {t}')
    rows = []
    for book, hymn, t in sorted(titles):
        lines = strip_ws_header(html_lines(wikisource_html(t)))
        # Whitney heads each hymn with "<hymn number>. <title>." and then
        # numbers the stanzas from 1.  Where his numbering differs from the
        # vulgate (Book VII) the vulgate number follows in parentheses:
        # "6 (6, 7). Praise of Aditi." / "3 (7. 1). The well-preserving...".
        # The stanzas are the numbered lines after the title line, in
        # increasing order; a stanza whose number the transcription dropped
        # is simply absent (never the title).
        # A few titles have no period after the parenthesis: "33 (34) For blessings".
        numbered = [(int(m.group(1)), m.group(2).strip()) for l in lines for m in [re.match(r'^(\d+)(?:\s*\([^)]*\)\.?|\.)\s+(.*)$', l)] if m]
        title_idx = next((i for i, (n, _) in enumerate(numbered) if n == hymn), None)
        if title_idx is None:
            print(f'  Whitney: title line not found on {t}; page skipped')
            continue
        last = 0
        for n, text in numbered[title_idx + 1:]:
            if n <= last:
                break               # numbering restarted: commentary, not stanzas
            rows.append((str(book), str(hymn), str(n), text))
            last = n
    return rows


def parse_tawney_kathasaritsagara():
    """Tawney, Katha Sarit Sagara (Wikisource, 124 continuous chapters with BOOK headings): DCS numbers tarangas within each lambaka."""
    rows, book, within = [], 0, 0
    for n in range(1, 125):
        lines = strip_ws_header(html_lines(wikisource_html(f'The Katha Sarit Sagara/Chapter {n}')))
        # the transcription spells one heading "CHAPTEE XX."
        idx = next((i for i, l in enumerate(lines) if re.match(r'^CHAPTE[A-Z] [IVXLC]+[.,]?$', l)), None)
        if idx is None:
            raise ValueError(f'KSS chapter {n}: heading not found')
        if any(re.match(r'^(BOOK [IVXL]+\.?|PART I\.)$', l) for l in lines[:idx]):
            book += 1
            within = 0
        within += 1
        rows.append((str(book), str(within), '1', '\n\n'.join(lines[idx + 1:])))
    return rows


def parse_shamasastry_arthashastra():
    """Shamasastry, Arthashastra (Wikisource, one page per book): CHAPTER headings; "CHAPTER I & II" serves both chapters."""
    rows = []
    for t in wikisource_allpages('Arthashastra/Book '):
        book = roman_to_int(t.rsplit(' ', 1)[1])
        lines = strip_ws_header(html_lines(wikisource_html(t)))
        cur, buf = None, []
        def flush():
            if cur and buf:
                for ch in cur:
                    rows.append((str(book), str(ch), '1', '\n\n'.join(buf)))
        for l in lines:
            m = re.match(r'^CHAPTER ([IVXLC]+)(?:\s*(?:&|AND|,)\s*([IVXLC]+))?\.', l)
            if m:
                flush()
                cur = [roman_to_int(m.group(1))] + ([roman_to_int(m.group(2))] if m.group(2) else [])
                buf = []
            elif cur:
                buf.append(l)
        flush()
    return rows


def parse_burton_kamasutra():
    """Burton and Arbuthnot, Kama Sutra (Wikisource): Part p / Chapter c pages match the DCS adhikarana / adhyaya."""
    rows = []
    for t in wikisource_allpages('Kama Sutra (Burton)/Part '):
        m = re.search(r'Part (\d+)/Chapter (\d+)$', t)
        if not m:
            continue
        lines = strip_ws_header(html_lines(wikisource_html(t)))
        idx = next((i for i, l in enumerate(lines) if re.match(r'^CHAPTER [IVXLC]+', l)), 0)
        rows.append((m.group(1), m.group(2), '1', '\n\n'.join(lines[idx + 1:])))
    return rows


def parse_bhishagratna_sushruta():
    """Bhishagratna, Sushruta Samhita (Wikisource, partial): the section named on each page maps to the DCS section label."""
    sections = {'SUTRASTH': 'Sū.', 'NIDANA': 'Nid.', 'SARIRA': 'Śār.', 'CHIKITSA': 'Cik.', 'KALPA': 'Ka.', 'UTTARA': 'Utt.'}
    rows = []
    pages = []
    for t in wikisource_allpages('Sushruta Samhita, Volume '):
        m = re.search(r'Volume (\d+)/Chapter (\d+)$', t)
        if m:
            pages.append((int(m.group(1)), int(m.group(2)), t))
    label = None
    volume = None
    for vol, chap, t in sorted(pages):
        lines = strip_ws_header(html_lines(wikisource_html(t)))
        if vol != volume:
            # each volume holds one section in the pages transcribed so far;
            # its first page names it, later pages may name other sections
            # in passing and are not used for the label
            volume = vol
            head = ' '.join(lines[:6]).upper().replace('Ā', 'A')
            label = next((v for k, v in sections.items() if k in head), None)
        if label is None:
            raise ValueError(f'Sushruta page {t}: section not recognised in {head[:80]!r}')
        idx = next((i for i, l in enumerate(lines) if re.match(r'^CHAPTER [IVXLC]+\.?$', l)), 0)
        rows.append((label, str(chap), '1', '\n\n'.join(lines[idx + 1:])))
    return rows


def parse_johnston_yogasutra():
    """Johnston, Yoga Sutras (Gutenberg 2526): BOOK I-IV; each sutra is a numbered paragraph followed by commentary paragraphs."""
    lines = gutenberg_lines(2526)
    rows, book = [], None
    for m, text in gutenberg_sections(lines, r'^BOOK ([IV]+)$', body_start_re=r'^BOOK I$'):
        book = roman_to_int(m.group(1))
        for para in text.split('\n\n'):
            pm = re.match(r'^(\d+)\.\s+(.*)$', para)
            if pm:
                rows.append((str(book), '1', pm.group(1), pm.group(2).strip()))
    return rows


def parse_griffith_kumarasambhava():
    """Griffith, The Birth of the War-God (Gutenberg 31968): Cantos First-Seventh, unnumbered stanzas; one segment per canto."""
    lines = gutenberg_lines(31968)
    rows = []
    for m, text in gutenberg_sections(lines, r'^Canto ([A-Za-z]+)\.$'):
        canto = ORDINALS.index(m.group(1).lower()) + 1
        text = re.split(r'\n\n(?:NOTES|FOOTNOTES)\.?\n', text)[0]
        rows.append((str(canto), '1', '1', text))
    return rows


def parse_arnold_gitagovinda():
    """
    Arnold, The Indian Song of Songs (Gutenberg 25965).  The table of
    contents lists "Sarga the First--The Sports of Krishna" ...; in the body
    each sarga is headed by its title in capitals ("THE SPORTS OF KRISHNA.").
    One segment per sarga; Arnold has eleven sargas for Jayadeva's twelve,
    so DCS sarga 12 stays without translation.
    """
    lines = gutenberg_lines(25965)
    toc = [(ORDINALS.index(m.group(1).lower()) + 1, m.group(2).strip().upper())
           for l in lines for m in [re.match(r'^\s*Sarga the ([A-Za-z]+)--(.*?)\s*\d*\s*$', l)] if m]
    if not toc:
        raise ValueError('Gita Govinda: table of contents not found')
    # the body heading that follows the last sarga (next table-of-contents entry)
    toc_lines = [l.strip() for l in lines if re.match(r'^\s*\S.*\s\d+\s*$', l)]
    after = None
    for i, l in enumerate(toc_lines):
        if l.startswith('Sarga the Eleventh') and i + 1 < len(toc_lines):
            after = re.sub(r'\s*\d+\s*$', '', toc_lines[i + 1]).strip().upper()
    titles = {t: n for n, t in toc}
    rows, cur, buf = [], None, []
    for l in lines:
        st = l.strip().rstrip('.').upper()
        if st in titles and not re.search(r'\d\s*$', l):
            if cur is not None:
                rows.append((str(cur), '1', '1', '\n\n'.join(paragraphs(buf))))
            cur, buf = titles[st], []
        elif after and st == after.rstrip('.') and cur is not None:
            rows.append((str(cur), '1', '1', '\n\n'.join(paragraphs(buf))))
            cur = None
            break
        elif cur is not None:
            buf.append(l)
    if cur is not None:
        rows.append((str(cur), '1', '1', '\n\n'.join(paragraphs(buf))))
    return rows


def parse_cowell_sarvadarsana():
    """Cowell and Gough, Sarva-darsana-samgraha (Gutenberg 34125): the DCS has only the Raseśvara chapter (Cowell's chapter IX)."""
    lines = gutenberg_lines(34125)
    for m, text in gutenberg_sections(lines, r'^CHAPTER ([IVX]+)\.$'):
        if roman_to_int(m.group(1)) == 9:
            text = re.sub(r'\[\d+\]', '', text)
            return [('Rāseśvaradarśana', '1', '1', text)]
    raise ValueError('Cowell chapter IX not found')


def parse_arnold_hitopadesa():
    """
    Arnold, The Book of Good Counsels (in Gutenberg 13268 "Hindu Literature"),
    an abridged Hitopadesa: five top-level divisions in the order of the
    DCS books 0-4 (introduction, then the four books); story subheadings
    stay inside their book.  One segment per book.
    """
    lines = gutenberg_lines(13268)
    tops = ['INTRODUCTION', 'THE WINNING OF FRIENDS', 'THE PARTING OF FRIENDS', 'WAR', 'PEACE']
    start = [i for i, l in enumerate(lines) if l.strip() == 'THE BOOK OF GOOD COUNSELS'][-1]
    end = next(i for i, l in enumerate(lines) if l.strip() == 'NALA AND DAMAYANTI' and i > start)
    rows, cur, buf = [], None, []
    for l in lines[start:end]:
        st = l.strip()
        if st in tops:
            if cur is not None:
                rows.append((str(tops.index(cur)), '1', '1', '\n\n'.join(paragraphs(buf))))
            cur, buf = st, []
        elif cur is not None:
            buf.append(l)
    rows.append((str(tops.index(cur)), '1', '1', '\n\n'.join(paragraphs(buf))))
    return rows


# Registry: DCS work name -> source specification
SOURCES = OrderedDict([
    ('Viṣṇupurāṇa', dict(translator='Manmatha Nath Dutt', source='Project Gutenberg 66208', licence='Public Domain', parse=parse_dutt_vishnupurana)),
    ('Saddharmapuṇḍarīkasūtra', dict(translator='Hendrik Kern', source='English Wikisource, Sacred Books of the East vol. 21', licence='Public Domain', parse=parse_kern_lotus)),
    ('Atharvaveda (Śaunaka)', dict(translator='William Dwight Whitney', source='English Wikisource, Atharva-Veda Samhita (1905)', licence='Public Domain', parse=parse_whitney_atharvaveda)),
    ('Kathāsaritsāgara', dict(translator='C. H. Tawney', source='English Wikisource, The Katha Sarit Sagara (1880-84)', licence='Public Domain', parse=parse_tawney_kathasaritsagara)),
    ('Arthaśāstra', dict(translator='R. Shamasastry', source='English Wikisource, Arthashastra (1915)', licence='Public Domain', parse=parse_shamasastry_arthashastra)),
    ('Kāmasūtra', dict(translator='Richard Burton and F. F. Arbuthnot', source='English Wikisource, Kama Sutra (1883)', licence='Public Domain', parse=parse_burton_kamasutra)),
    ('Suśrutasaṃhitā', dict(translator='Kaviraj Kunja Lal Bhishagratna', source='English Wikisource, Sushruta Samhita (1907-16), partial', licence='Public Domain', parse=parse_bhishagratna_sushruta)),
    ('Yogasūtra', dict(translator='Charles Johnston', source='Project Gutenberg 2526', licence='Public Domain', parse=parse_johnston_yogasutra)),
    ('Kumārasaṃbhava', dict(translator='Ralph T.H. Griffith', source='Project Gutenberg 31968', licence='Public Domain', parse=parse_griffith_kumarasambhava)),
    ('Gītagovinda', dict(translator='Edwin Arnold', source='Project Gutenberg 25965', licence='Public Domain', parse=parse_arnold_gitagovinda)),
    ('Sarvadarśanasaṃgraha', dict(translator='E. B. Cowell and A. E. Gough', source='Project Gutenberg 34125', licence='Public Domain', parse=parse_cowell_sarvadarsana)),
    ('Hitopadeśa', dict(translator='Edwin Arnold (abridged)', source='Project Gutenberg 13268', licence='Public Domain', parse=parse_arnold_hitopadesa)),
    ('Rāmāyaṇa', dict(translator='Manmatha Nath Dutt', source='Project Gutenberg 57265, 57826, 60188, 62496; sarga pairing via Sanskrit Wikisource रामायणम्', licence='Public Domain',
                      parse=lambda: __import__('ramayana_dutt').parse())),
])


def slug(work):
    import unicodedata
    base = ''.join(c for c in unicodedata.normalize('NFD', work) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_') or 'work'


def ensure_translation(work):
    """Fetch, parse and write generated/<slug>.tsv for a registered work; returns (path, translator)."""
    spec = SOURCES[work]
    path = os.path.join(GEN_DIR, slug(work) + '.tsv')
    if not os.path.isfile(path):
        print(f'  fetching and parsing translation for {work} ({spec["source"]})...')
        rows = spec['parse']()
        if not rows:
            raise ValueError(f'{work}: parser produced no rows')
        os.makedirs(GEN_DIR, exist_ok=True)
        with open(path + '.part', 'w', encoding='utf-8') as f:
            f.write(f'@text={work}\n@translator={spec["translator"]}\n@source={spec["source"]}\n@licence={spec["licence"]}\n')
            for b, c, v, t in rows:
                # tabs cannot occur inside the text; line breaks are written as
                # the two characters "\\n" and restored by the build
                f.write(f'{b}\t{c}\t{v}\t{t.replace(chr(9), " ").replace(chr(10), chr(92) + "n")}\n')
        os.replace(path + '.part', path)
        print(f'  wrote {path}: {len(rows)} rows')
    return path, spec['translator']


# ---------------------------------------------------------------------------
# --check: compare parser keys with DCS labels
# ---------------------------------------------------------------------------

def dcs_structure(work):
    import glob
    books = OrderedDict()
    for f in sorted(x for x in glob.glob(os.path.join(DCS_FILES, work, '*.conllu')) if not x.endswith('_parsed')):
        for line in open(f, encoding='utf-8'):
            if line.startswith('## chapter:'):
                p = [x.strip() for x in line[11:].split(',')]
                books.setdefault(p[1], []).append('.'.join(p[2:]) or '1')
                break
    return books


def check(works):
    for work in works:
        try:
            rows = SOURCES[work]['parse']()
        except Exception as e:
            print(f'== {work}: PARSE FAILED: {e}')
            continue
        dcs = dcs_structure(work)
        dcs_keys = {(b, c) for b, chs in dcs.items() for c in chs}
        keys = {(b, c) for b, c, _, _ in rows}
        matched = keys & dcs_keys
        print(f'== {work}: {len(rows)} rows; translation (book,chapter) keys {len(keys)}; DCS chapters {len(dcs_keys)}; '
              f'matched {len(matched)}; translation-only {sorted(keys - dcs_keys)[:8]}; DCS-only {sorted(dcs_keys - keys)[:8]}')
        empty = [(b, c, v) for b, c, v, t in rows if len(t) < 20]
        if empty:
            print(f'   short/empty texts: {empty[:6]}')
        if rows:
            print(f'   sample: {rows[0][:3]} {rows[0][3][:100]!r}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--check':
        check(args[1:] or list(SOURCES))
    else:
        for w in (args or list(SOURCES)):
            ensure_translation(w)
