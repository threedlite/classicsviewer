#!/usr/bin/env python3
"""
Manmatha Nath Dutt's prose Ramayana (1891-94, Project Gutenberg 57265,
57826, 60188, 62496) attached sarga by sarga to the DCS Ramayana (Baroda
critical edition, 606 sargas).

Used through translation_sources.py (entry 'Rāmāyaṇa'); not a standalone
script, except for `--check`.

Why a bridge is needed.  Dutt's sections follow the vulgate numbering; the
DCS follows the critical edition, which drops or merges some vulgate sargas.
The Sanskrit vulgate on Sanskrit Wikisource (रामायणम्, 654 sarga pages,
CC BY-SA) carries verse ids like ॥१-१-१॥, so each critical-edition sarga
can be paired with the vulgate sarga whose first verse it shares.  This
module does exactly that, mechanically:

1. For every DCS sarga, its first sentence (IAST -> Devanagari).
2. For every vulgate sarga, the first verse line of its page.
3. Per kanda, the largest monotonic one-to-one matching in which every
   pair has normalised-text similarity >= SIMILARITY on the first
   PREFIX characters (difflib ratio).  Nothing below the threshold is
   paired; the threshold is fixed here and not tuned per text.
4. Dutt's section n is the vulgate's sarga n in the kandas where Dutt's
   section count equals the vulgate's sarga count (Bala 77, Aranya 75,
   Kishkindha 67).  In the other kandas (Ayodhya 118 vs 119, Sundara 67
   vs 68, Yuddha 130 vs 128, Uttara 124 vs 111) no exact pairing of
   Dutt's sections with the vulgate exists; there vulgate sarga v gets
   the Dutt section at the same proportional position, round(v * D / V)
   for D sections and V sargas, and every English segment in such a
   kanda begins with a note saying that the alignment is approximate and
   why (decided 2026-10-10).
5. A DCS sarga paired with vulgate sarga v gets Dutt's section for v;
   sections whose sarga was not paired, and sargas without a pair, are
   listed in the report.

Dutt's section headings "SECTION N." are read by their printed numeral;
a numeral missing from the transcription leaves its text with the
preceding section, which then covers both numerals (as with Ganguli).
"""

import difflib
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translation_sources as ts  # noqa: E402

SA_API = 'https://sa.wikisource.org/w/api.php'
GEN = os.path.join(HERE, 'generated', 'ramayana')

SIMILARITY = 0.85
PREFIX = 40

# DCS kanda label -> (Sanskrit Wikisource folder, Dutt heading word, Gutenberg volume)
KANDAS = OrderedDict([
    ('Bā', ('बालकाण्डम्', 'BALA', 57265)),
    ('Ay', ('अयोध्याकाण्डम्', 'AYODHYA', 57265)),
    ('Ār', ('अरण्यकाण्डम्', 'ARANYA', 57826)),
    ('Ki', ('किष्किन्धाकाण्डम्', 'KISHKINDHA', 57826)),
    ('Su', ('सुन्दरकाण्डम्', 'SUNDARA', 57826)),
    ('Yu', ('युद्धकाण्डम्', 'YUDDHA', 60188)),
    ('Utt', ('उत्तरकाण्डम्', 'UTTARA', 62496)),
])
DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')


# ---------------------------------------------------------------------------
# Sanskrit normalisation and similarity
# ---------------------------------------------------------------------------

VOWEL_SIGNS = {'अ': '', 'आ': 'ा', 'इ': 'ि', 'ई': 'ी', 'उ': 'ु', 'ऊ': 'ू', 'ऋ': 'ृ', 'ए': 'े', 'ऐ': 'ै', 'ओ': 'ो', 'औ': 'ौ'}


def normalise(s):
    """
    Make the unsandhied DCS text and the sandhied vulgate comparable:
    drop punctuation, digits and spaces; join a final consonant to a
    following independent vowel (म् + आ -> मा); write class nasals before
    stops and final म् as anusvara; write final स् as visarga.
    """
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'[।॥\d०-९\s\-\.,;:\'"()\[\]ऽ]', '', s)
    s = re.sub(r'्([अआइईउऊऋएऐओऔ])', lambda m: VOWEL_SIGNS[m.group(1)], s)
    s = re.sub(r'[ङञणनम]्(?=[कखगघचछजझटठडढतथदधपफबभ])', 'ं', s)
    s = s.replace('म्', 'ं').replace('स्', 'ः').replace('र्', 'ः')
    return s


def similar(a, b):
    """a: one DCS opening sentence; b: a list of the vulgate sarga's first half-verses (or one string)."""
    if isinstance(b, str):
        b = [b]
    a = normalise(a)[:PREFIX]
    if not a:
        return 0.0
    best = 0.0
    for line in b:
        x = normalise(line)[:PREFIX]
        if x:
            best = max(best, difflib.SequenceMatcher(None, a, x).ratio())
    return best


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def dcs_openings():
    """{kanda: [first sentence of sarga 1, 2, ...]} in Devanagari, from the DCS CoNLL-U files."""
    import glob
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    out = {k: {} for k in KANDAS}
    for f in sorted(x for x in glob.glob(os.path.join(ts.DCS_FILES, 'Rāmāyaṇa', '*.conllu')) if not x.endswith('_parsed')):
        hdr, first = None, None
        for line in open(f, encoding='utf-8'):
            if line.startswith('## chapter:'):
                p = [x.strip() for x in line[11:].split(',')]
                hdr = (p[1], int(p[2]))
            elif line.startswith('# text ='):
                first = line.split('=', 1)[1].strip()
                break
        out[hdr[0]][hdr[1]] = transliterate(first, sanscript.IAST, sanscript.DEVANAGARI)
    return {k: [v[i] for i in sorted(v)] for k, v in out.items()}


def vulgate_openings():
    """{kanda: [first verse line of sarga 1, 2, ...]} from Sanskrit Wikisource, cached."""
    cache = os.path.join(GEN, 'vulgate_openings.json')
    if os.path.isfile(cache):
        return json.load(open(cache, encoding='utf-8'))
    import html as H
    import urllib.parse
    titles = []
    cont = {}
    while True:
        q = urllib.parse.urlencode({'action': 'query', 'list': 'allpages', 'apprefix': 'रामायणम्/', 'aplimit': '500', 'format': 'json', **cont})
        d = json.loads(ts._get(SA_API + '?' + q))
        titles += [p['title'] for p in d['query']['allpages']]
        if 'continue' in d:
            cont = {'apcontinue': d['continue']['apcontinue']}
        else:
            break
    folder_to_kanda = {v[0]: k for k, v in KANDAS.items()}
    sargas = {k: {} for k in KANDAS}
    for t in titles:
        m = re.match(r'^रामायणम्/([^/]+)/सर्गः ([०-९]+)$', t)
        if not m or m.group(1) not in folder_to_kanda:
            continue
        k = folder_to_kanda[m.group(1)]
        n = int(m.group(2).translate(DEVANAGARI_DIGITS))
        page_cache = os.path.join(GEN, 'pages', f'{k}_{n}.html')
        if os.path.isfile(page_cache):
            h = open(page_cache, encoding='utf-8').read()
        else:
            q = urllib.parse.urlencode({'action': 'parse', 'page': t, 'prop': 'text', 'format': 'json', 'disabletoc': '1'})
            d = json.loads(ts._get(SA_API + '?' + q))
            h = d['parse']['text']['*']
            os.makedirs(os.path.dirname(page_cache), exist_ok=True)
            with open(page_cache, 'w', encoding='utf-8') as f:
                f.write(h)
            import time
            time.sleep(0.2)
        text = H.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<style.*?</style>', '', h, flags=re.S)))
        lines = [re.sub(r'\s+', ' ', l).strip() for l in text.splitlines() if l.strip()]
        # verse markers read "॥१-१-१॥" or "।। ७.१.१ ।।"; the first verse ends
        # at the first marker whose verse number is 1, and its first half-verse
        # is the line before it.  Keep the first three half-verse lines: the
        # critical edition sometimes starts a sarga at the vulgate's second
        # verse.
        # the separator between the numbers is a hyphen, another dash
        # character, or a full stop depending on the kanda
        # verse markers read "॥१-१-१॥", "।। ७.१.१ ।।" or "॥ १॥" depending on
        # the kanda; the last number is the verse number.  Lines naming the
        # sarga ("... प्रथमः सर्गः ॥४-१॥") are not verses.
        marker = re.compile(r'[।॥]{1,2}\s*(?:[०-९\d]+[-‐‑–—.])*([०-९\d]+)\s*[।॥]{1,2}')
        idx = None
        for i, l in enumerate(lines):
            m = marker.search(l)
            if m and 'सर्ग' not in l and m.group(1).translate(DEVANAGARI_DIGITS) == '1':
                idx = i
                break
        if idx is None:
            sargas[k][n] = []
        else:
            start = idx - 1 if idx > 0 and not marker.search(lines[idx - 1]) else idx
            sargas[k][n] = [re.sub(marker, '', l).strip() for l in lines[start:start + 3]]
        import time
        time.sleep(0.2)
    for k, v in sargas.items():
        if sorted(v) != list(range(1, len(v) + 1)):
            raise ValueError(f'vulgate {k}: sarga numbers {sorted(v)[:5]}... not 1..N')
    out = {k: [v[i] for i in sorted(v)] for k, v in sargas.items()}
    empty = sum(1 for k in out for x in out[k] if not x)
    if empty:
        print(f'  vulgate: {empty} sarga pages without a recognised first verse')
    os.makedirs(GEN, exist_ok=True)
    json.dump(out, open(cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out


def dutt_sections():
    """{kanda: {section_numeral: text}} from the four Gutenberg volumes."""
    out = {k: OrderedDict() for k in KANDAS}
    for number in sorted({v[2] for v in KANDAS.values()}):
        lines = ts.gutenberg_lines(number)
        kanda = None
        cur, buf = None, []
        heading_word_to_kanda = {v[1]: k for k, v in KANDAS.items()}

        def flush():
            if kanda and cur is not None:
                out[kanda][cur] = '\n\n'.join(ts.paragraphs(buf))
        for i, l in enumerate(lines):
            st = l.strip()
            m = re.match(r'^([A-Z]+) ?K[AĀ]NDAM?\.?$', st)
            if m and m.group(1) in heading_word_to_kanda and any(re.match(r'^SECTION I\.?$', x.strip()) for x in lines[i + 1:i + 8]):
                flush()
                kanda, cur, buf = heading_word_to_kanda[m.group(1)], None, []
                continue
            m = re.match(r'^SECTION ([IVXLC]+)\.?$', st)
            if m and kanda:
                flush()
                cur, buf = ts.roman_to_int(m.group(1)), []
            elif kanda and cur is not None:
                buf.append(l)
        flush()
    return out


# ---------------------------------------------------------------------------
# alignment
# ---------------------------------------------------------------------------

def monotonic_matching(a, b):
    """
    Largest set of index pairs (i, j), strictly increasing in both, with
    similar(a[i], b[j]) >= SIMILARITY.  Standard LCS-style dynamic programme
    over the similarity matrix.
    """
    n, m = len(a), len(b)
    ok = [[similar(a[i], b[j]) >= SIMILARITY for j in range(m)] for i in range(n)]
    best = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best[i][j] = max(best[i + 1][j], best[i][j + 1], (1 + best[i + 1][j + 1]) if ok[i][j] else 0)
    pairs = []
    i = j = 0
    while i < n and j < m:
        if ok[i][j] and best[i][j] == 1 + best[i + 1][j + 1]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif best[i + 1][j] >= best[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def align(report=None):
    """Returns rows [(kanda, sarga, '1', text)] and appends report lines."""
    report = report if report is not None else []
    dcs = dcs_openings()
    vul = vulgate_openings()
    dutt = dutt_sections()
    rows = []
    for k, (folder, word, number) in KANDAS.items():
        ce, vg, sections = dcs[k], vul[k], dutt[k]
        pairs = monotonic_matching(ce, vg)
        ce_to_vul = {i + 1: j + 1 for i, j in pairs}
        unmatched_ce = [i for i in range(1, len(ce) + 1) if i not in ce_to_vul]
        matched_vul = {j + 1 for _, j in pairs}
        report.append(f'Rāmāyaṇa {k}: DCS sargas {len(ce)}, vulgate sargas {len(vg)}, Dutt sections {len(sections)} '
                      f'(last numeral {max(sections) if sections else 0}); DCS sargas paired with a vulgate sarga: {len(pairs)}; '
                      f'unpaired DCS sargas: {unmatched_ce[:12]}{"..." if len(unmatched_ce) > 12 else ""}')
        if not sections:
            raise ValueError(f'Rāmāyaṇa {k}: no Dutt sections found')
        D, V = max(sections), len(vg)
        approximate = D != V
        if approximate:
            report.append(f'Rāmāyaṇa {k}: Dutt section count {D} differs from the vulgate sarga count {V}; '
                          f'sections are attached by proportional position and each segment carries a note that the alignment is approximate')

        def section_for(v):
            return v if not approximate else max(1, min(D, int(v * D / V + 0.5)))
        # Dutt units by numeral: a missing numeral's text stays with the preceding section
        present = sorted(sections)
        unit_of = {}
        for a, b in zip(present, present[1:] + [D + 1]):
            for n in range(a, b):
                unit_of[n] = a
        missing = [n for n in range(1, D + 1) if n not in sections]
        if missing:
            report.append(f'Rāmāyaṇa {k}: Dutt section numerals {missing} missing from the transcription; text stays with the preceding section')
        used = set()
        for sarga in range(1, len(ce) + 1):
            v = ce_to_vul.get(sarga)
            if v is None:
                continue
            d = section_for(v)
            unit = unit_of[d]
            text = sections[unit]
            if approximate:
                text = (f'[Alignment approximate. In this kāṇḍa Dutt\'s translation has {D} sections and the vulgate '
                        f'Sanskrit text {V} sargas, so sections and sargas cannot be paired one to one. This critical-edition '
                        f'sarga opens with the same verse as vulgate sarga {v}; Dutt\'s section {unit} is shown because it '
                        f'stands at the same proportional position among his sections. The matching passage may lie in a '
                        f'neighbouring section.]\n\n') + text
            rows.append((k, str(sarga), '1', text))
            used.add(unit)
        unused = [u for u in present if u not in used]
        if unused:
            report.append(f'Rāmāyaṇa {k}: Dutt sections {unused[:12]}{"..." if len(unused) > 12 else ""} correspond to no paired critical-edition sarga and are not written')
    return rows, report


def parse():
    rows, report = align()
    for line in report:
        print('  ' + line)
    return rows


if __name__ == '__main__':
    rows, report = align()
    print('\n'.join(report))
    print(f'{len(rows)} sargas with a Dutt section')
