#!/usr/bin/env python3
"""
Download Ralph T. H. Griffith's translation of the Rig Veda (The Hymns of
the Rigveda, 2nd ed. 1896; public domain) from English Wikisource, one
rendered page per hymn, via the MediaWiki API.

    https://en.wikisource.org/wiki/The_Hymns_of_the_Rigveda

The hymn pages are discovered with the API (list=allpages, prefix "The Hymns
of the Rigveda/Book "), so nothing about the hymn counts is assumed here;
parse_rigveda_griffith.py checks them against the Sanskrit text.  Files are
written to wikisource/rigveda/book<N>_hymn<M>.html; existing files are kept,
so an interrupted run resumes.  The build runs this script itself when the
parsed translation file is missing.
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'wikisource', 'rigveda')
API = 'https://en.wikisource.org/w/api.php'
UA = 'classicsviewer-build/1.0 (https://github.com/threedlite/classicsviewer)'
PREFIX = 'The Hymns of the Rigveda/Book '


def api(params):
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers={'User-Agent': UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:          # transient network / rate limit
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))


def list_hymn_pages():
    titles = []
    cont = {}
    while True:
        d = api({'action': 'query', 'list': 'allpages', 'apprefix': PREFIX, 'aplimit': '500', 'format': 'json', **cont})
        titles += [p['title'] for p in d['query']['allpages']]
        if 'continue' in d:
            cont = {'apcontinue': d['continue']['apcontinue']}
        else:
            break
    hymns = []
    for t in titles:
        m = re.match(r'^The Hymns of the Rigveda/Book (\d+)/Hymn (\d+)$', t)
        if m:
            hymns.append((int(m.group(1)), int(m.group(2)), t))
    return sorted(hymns)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    hymns = list_hymn_pages()
    print(f'{len(hymns)} hymn pages listed on Wikisource')
    done = 0
    for book, hymn, title in hymns:
        out = os.path.join(OUT_DIR, f'book{book}_hymn{hymn}.html')
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            continue
        d = api({'action': 'parse', 'page': title, 'prop': 'text', 'format': 'json', 'disabletoc': '1'})
        with open(out + '.part', 'w', encoding='utf-8') as f:
            f.write(d['parse']['text']['*'])
        os.replace(out + '.part', out)
        done += 1
        if done % 50 == 0:
            print(f'  downloaded {done} pages (last {book}.{hymn})')
            sys.stdout.flush()
        time.sleep(0.2)
    print(f'downloaded {done} new pages; {len(hymns)} present in {OUT_DIR}')


if __name__ == '__main__':
    main()
