#!/usr/bin/env python3
"""
Create Classical Chinese database for ClassicsViewer

Sources:
- Zhuangzi: Chinese Wikisource (CC BY-SA 4.0), Herbert Giles translation (1889, PD)
- Dao De Jing: Chinese Wikisource Wang Bi edition (CC BY-SA 4.0), James Legge translation (1891, PD)

Usage:
  python3 create_chinese_database.py
"""

import sqlite3
import json
import os
import re
import zipfile
import urllib.request
import urllib.parse
import time
import html as html_module

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data-sources")
DB_PATH = os.path.join(SCRIPT_DIR, "chinese_texts.db")
ZIP_PATH = os.path.join(SCRIPT_DIR, "chinese_texts.db.zip")
MAX_LINE_SIZE = 2000  # Display limit

USER_AGENT = "ClassicsViewer/1.0 (Classical Chinese text reader; contact: classicsviewer@example.com)"

# ─── Zhuangzi Chapter Data ───────────────────────────────────────────────────

# The 33 chapters of the Zhuangzi
# (chapter_number, chinese_title_for_wikisource_url, english_title_from_giles, section)
ZHUANGZI_CHAPTERS = [
    # Inner Chapters (內篇) 1-7
    (1, "逍遙遊", "Transcendental Bliss", "Inner"),
    (2, "齊物論", "The Identity of Contraries", "Inner"),
    (3, "養生主", "Nourishment of the Soul", "Inner"),
    (4, "人間世", "Man Among Men", "Inner"),
    (5, "德充符", "Seal of Virtue Complete", "Inner"),
    (6, "大宗師", "The Great Supreme", "Inner"),
    (7, "應帝王", "How to Govern", "Inner"),
    # Outer Chapters (外篇) 8-22
    (8, "駢拇", "Joined Toes", "Outer"),
    (9, "馬蹄", "Horses' Hoofs", "Outer"),
    (10, "胠篋", "Opening Trunks", "Outer"),
    (11, "在宥", "On Tolerance", "Outer"),
    (12, "天地", "Heaven and Earth", "Outer"),
    (13, "天道", "The Way of Heaven", "Outer"),
    (14, "天運", "The Revolution of Heaven", "Outer"),
    (15, "刻意", "Ingrained Ideas", "Outer"),
    (16, "繕性", "Correcting the Nature", "Outer"),
    (17, "秋水", "Autumn Floods", "Outer"),
    (18, "至樂", "Perfect Enjoyment", "Outer"),
    (19, "達生", "The Secret of Life", "Outer"),
    (20, "山木", "The Tree on the Mountain", "Outer"),
    (21, "田子方", "Tien Tzu-fang", "Outer"),
    (22, "知北遊", "Knowledge Travels North", "Outer"),
    # Miscellaneous Chapters (雜篇) 23-33
    (23, "庚桑楚", "Keng-sang Ch'u", "Miscellaneous"),
    (24, "徐無鬼", "Hsü Wu-kuei", "Miscellaneous"),
    (25, "則陽", "Tse-yang", "Miscellaneous"),
    (26, "外物", "External Things", "Miscellaneous"),
    (27, "寓言", "Metaphors", "Miscellaneous"),
    (28, "讓王", "Kings Who Have Wished to Resign the Throne", "Miscellaneous"),
    (29, "盜跖", "The Robber Chê", "Miscellaneous"),
    (30, "說劍", "On Swords", "Miscellaneous"),
    (31, "漁父", "The Old Fisherman", "Miscellaneous"),
    (32, "列禦寇", "Lieh Yü-k'ou", "Miscellaneous"),
    (33, "天下", "The Empire", "Miscellaneous"),
]

# Chinese number words for parsing Dao De Jing chapter headings
CHINESE_NUMS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
    '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
    '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24, '二十五': 25,
    '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30,
    '三十一': 31, '三十二': 32, '三十三': 33, '三十四': 34, '三十五': 35,
    '三十六': 36, '三十七': 37, '三十八': 38, '三十九': 39, '四十': 40,
    '四十一': 41, '四十二': 42, '四十三': 43, '四十四': 44, '四十五': 45,
    '四十六': 46, '四十七': 47, '四十八': 48, '四十九': 49, '五十': 50,
    '五十一': 51, '五十二': 52, '五十三': 53, '五十四': 54, '五十五': 55,
    '五十六': 56, '五十七': 57, '五十八': 58, '五十九': 59, '六十': 60,
    '六十一': 61, '六十二': 62, '六十三': 63, '六十四': 64, '六十五': 65,
    '六十六': 66, '六十七': 67, '六十八': 68, '六十九': 69, '七十': 70,
    '七十一': 71, '七十二': 72, '七十三': 73, '七十四': 74, '七十五': 75,
    '七十六': 76, '七十七': 77, '七十八': 78, '七十九': 79, '八十': 80,
    '八十一': 81,
}


def create_database(db_path):
    """Create the database schema (matches Greek/Latin/Sanskrit/Norse schema)"""
    print(f"Creating database: {db_path}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Creating tables...")

    cursor.execute('''
        CREATE TABLE authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE milestone_line_ranges (
            work_id TEXT,
            milestone TEXT,
            start_line INTEGER,
            end_line INTEGER,
            PRIMARY KEY (work_id, milestone)
        )
    ''')

    cursor.execute('''
        CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE normalization_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            pattern TEXT NOT NULL,
            replacement TEXT NOT NULL,
            description TEXT,
            priority INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE prefix_assimilation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            base_prefix TEXT NOT NULL,
            assimilated_form TEXT NOT NULL,
            meaning TEXT,
            phonological_rule TEXT,
            priority INTEGER NOT NULL,
            examples TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes
    print("Creating indexes...")
    cursor.execute('CREATE INDEX idx_authors_language ON authors(language)')
    cursor.execute('CREATE INDEX idx_works_author ON works(author_id)')
    cursor.execute('CREATE INDEX idx_books_work ON books(work_id)')
    cursor.execute('CREATE INDEX idx_text_lines_book ON text_lines(book_id)')
    cursor.execute('CREATE INDEX idx_text_lines_sequence ON text_lines(book_id, sequence_number)')
    cursor.execute('CREATE INDEX idx_words_word ON words(word)')
    cursor.execute('CREATE INDEX idx_words_book_line_seq ON words(book_id, line_number, sequence_number)')
    cursor.execute('CREATE INDEX idx_translation_segments_book ON translation_segments(book_id)')
    cursor.execute('CREATE INDEX idx_translation_segments_lines ON translation_segments(book_id, start_line)')
    cursor.execute('CREATE INDEX idx_dictionary_headword ON dictionary_entries(headword, language)')
    cursor.execute('CREATE INDEX idx_dictionary_headword_ultra ON dictionary_entries(headword_normalized_ultra, language)')
    cursor.execute('CREATE INDEX idx_lemma_map_word ON lemma_map(word_form)')
    cursor.execute('CREATE INDEX idx_lemma_map_word_ultra ON lemma_map(word_form_normalized_ultra)')
    cursor.execute('CREATE INDEX idx_lemma_map_lemma ON lemma_map(lemma)')
    cursor.execute('CREATE INDEX idx_normalization_language ON normalization_patterns(language, priority)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_language ON prefix_assimilation_rules(language)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_base ON prefix_assimilation_rules(base_prefix)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_form ON prefix_assimilation_rules(assimilated_form)')
    cursor.execute('CREATE INDEX idx_prefix_assimilation_lang_priority ON prefix_assimilation_rules(language, priority)')
    cursor.execute('CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)')
    cursor.execute('CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)')

    conn.commit()
    return conn


# ─── Download ────────────────────────────────────────────────────────────────

def fetch_url(url):
    """Fetch a URL with proper User-Agent header"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def download_cached(cache_path, url, description):
    """Download a URL to a cache file if not already cached. Returns the cached file path."""
    if os.path.exists(cache_path):
        print(f"  [cached] {description}")
        return cache_path

    print(f"  Downloading {description}...")
    try:
        data = fetch_url(url)
        parsed = json.loads(data)
        if "error" in parsed:
            raise RuntimeError(f"API error: {parsed['error']}")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(data)
        time.sleep(1)  # Rate limit
        return cache_path
    except Exception as e:
        raise RuntimeError(f"Failed to download {description}: {e}")


def download_zhuangzi_chinese():
    """Download all 33 Chinese chapters from zh.wikisource.org"""
    os.makedirs(DATA_DIR, exist_ok=True)
    print("Downloading Zhuangzi Chinese text from zh.wikisource.org...")

    for ch_num, ch_title, _, _ in ZHUANGZI_CHAPTERS:
        cache_path = os.path.join(DATA_DIR, f"zhuangzi_zh_{ch_num:02d}.json")
        page = urllib.parse.quote(f"莊子/{ch_title}", safe="/")
        url = f"https://zh.wikisource.org/w/api.php?action=parse&page={page}&format=json"
        download_cached(cache_path, url, f"Chapter {ch_num}: {ch_title}")

    print(f"  ✓ All {len(ZHUANGZI_CHAPTERS)} Zhuangzi Chinese chapters downloaded")


def download_zhuangzi_english():
    """Download all 33 English chapters (Giles 1889) from en.wikisource.org"""
    os.makedirs(DATA_DIR, exist_ok=True)
    print("Downloading Zhuangzi English translation from en.wikisource.org...")

    for ch_num, _, _, _ in ZHUANGZI_CHAPTERS:
        cache_path = os.path.join(DATA_DIR, f"zhuangzi_en_{ch_num:02d}.json")
        # Note: Tzŭ has a u-breve (ŭ)
        page = urllib.parse.quote(f"Chuang Tzŭ (Giles)/Chapter {ch_num}", safe="/() ")
        page = page.replace(" ", "_")
        url = f"https://en.wikisource.org/w/api.php?action=parse&page={page}&format=json"
        download_cached(cache_path, url, f"English Chapter {ch_num}")

    print(f"  ✓ All {len(ZHUANGZI_CHAPTERS)} Zhuangzi English chapters downloaded")


def download_daodejing_chinese():
    """Download Dao De Jing Chinese text (Wang Bi edition) — single page, all 81 chapters."""
    os.makedirs(DATA_DIR, exist_ok=True)
    print("Downloading Dao De Jing Chinese text from zh.wikisource.org...")

    cache_path = os.path.join(DATA_DIR, "daodejing_zh.json")
    page = urllib.parse.quote("道德經_(王弼本)", safe="/()")
    url = f"https://zh.wikisource.org/w/api.php?action=parse&page={page}&format=json"
    download_cached(cache_path, url, "道德經 (Wang Bi edition)")

    print("  ✓ Dao De Jing Chinese text downloaded")


def download_daodejing_english():
    """Download Dao De Jing English translation (Legge 1891) — single page, all 81 chapters."""
    os.makedirs(DATA_DIR, exist_ok=True)
    print("Downloading Dao De Jing English translation from en.wikisource.org...")

    cache_path = os.path.join(DATA_DIR, "daodejing_en.json")
    # Note: circumflex on â in Tâo
    page = urllib.parse.quote("Tâo Teh King", safe="")
    url = f"https://en.wikisource.org/w/api.php?action=parse&page={page}&format=json"
    download_cached(cache_path, url, "Tâo Teh King (Legge 1891)")

    print("  ✓ Dao De Jing English translation downloaded")


# ─── HTML Parsing ────────────────────────────────────────────────────────────

def strip_html_tags(text):
    """Strip all HTML tags from text and decode entities."""
    clean = re.sub(r'<[^>]+>', '', text)
    return html_module.unescape(clean)


def parse_chinese_html(html_text):
    """Parse Chinese Wikisource HTML into a list of paragraph strings.

    Complexity: LOW — extract <p> tags, strip markup, done.
    """
    # Remove <style> blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)

    # Remove navigation tables (ws-header)
    text = re.sub(r'<table[^>]*class="[^"]*ws-header[^"]*"[^>]*>.*?</table>', '', text, flags=re.DOTALL)

    # Remove footer tables
    text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL)

    # Remove heading divs (mw-heading)
    text = re.sub(r'<div[^>]*class="[^"]*mw-heading[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)

    # Remove edit section spans
    text = re.sub(r'<span[^>]*class="[^"]*mw-editsection[^"]*"[^>]*>.*?</span>', '', text, flags=re.DOTALL)

    # Remove sister/noexport sections
    text = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ul[^>]*class="[^"]*plainSister[^"]*"[^>]*>.*?</ul>', '', text, flags=re.DOTALL)

    # Extract paragraphs
    paragraphs = re.findall(r'<p>(.*?)</p>', text, re.DOTALL)

    result = []
    for p in paragraphs:
        # Strip all HTML tags
        clean = strip_html_tags(p)
        # Strip ideographic spaces (U+3000) and regular whitespace
        clean = clean.replace('\u3000', '').strip()
        # Collapse whitespace
        clean = re.sub(r'\s+', '', clean)  # Classical Chinese has no spaces
        if clean:
            result.append(clean)

    return result


def parse_english_html(html_text):
    """Parse English Wikisource HTML (Giles Zhuangzi translation) into paragraph strings.

    Complexity: MODERATE — handle page markers, drop initials, translator notes, etc.
    """
    # Remove <style> blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)

    # Remove header/navigation
    text = re.sub(r'<div[^>]*class="[^"]*ws-header[^"]*"[^>]*>.*?</div>\s*</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div[^>]*id="ws-data"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ul[^>]*class="[^"]*plainSister[^"]*"[^>]*>.*?</ul>', '', text, flags=re.DOTALL)

    # Remove page number markers (zero-width space spans inline in text)
    text = re.sub(r'<span[^>]*class="[^"]*pagenum[^"]*"[^>]*>.*?</span>', '', text, flags=re.DOTALL)

    # Handle drop initials: <span class="dropinitial">...<span class="dropinitial-initial">X</span></span>REST
    # Extract the initial letter and merge with following text
    text = re.sub(
        r'<span[^>]*class="[^"]*dropinitial[^"]*"[^>]*>.*?<span[^>]*class="[^"]*dropinitial-initial[^"]*"[^>]*>(.*?)</span>.*?</span>',
        r'\1', text, flags=re.DOTALL
    )

    # Remove translator's notes (<dl><dd> blocks with small font)
    text = re.sub(r'<dl>\s*<dd>.*?</dd>\s*</dl>', '', text, flags=re.DOTALL)

    # Remove chapter title/centered divs
    text = re.sub(r'<div[^>]*class="[^"]*wst-center[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)

    # Remove hanging-indent divs (argument/summary)
    text = re.sub(r'<div[^>]*class="[^"]*wst-hanging-indent[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)

    # Remove nop divs
    text = re.sub(r'<div[^>]*class="[^"]*wst-nop[^"]*"[^>]*>\s*</div>', '', text, flags=re.DOTALL)

    # Remove <hr> tags
    text = re.sub(r'<hr\s*/?>', '', text)

    # Extract paragraphs
    paragraphs = re.findall(r'<p>(.*?)</p>', text, re.DOTALL)

    result = []
    for p in paragraphs:
        # Strip all remaining HTML tags
        clean = strip_html_tags(p)
        # Remove zero-width spaces
        clean = clean.replace('\u200b', '')
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean:
            continue
        # Skip Wikisource publication metadata lines
        if re.match(r'^Bernard Quaritch,\s+London,\s+pages?\s+', clean):
            continue
        if clean:
            result.append(clean)

    return result


def parse_daodejing_chinese_html(html_text):
    """Parse Dao De Jing Wang Bi edition from zh.wikisource.org.

    Single page with h2 headings for each chapter (X章).
    Wang Bi commentary is in {{*|...}} templates — rendered as specific HTML that we strip.
    Returns dict of {chapter_number: [paragraph_strings]}.
    """
    # Remove <style> blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)

    # Remove navigation tables
    text = re.sub(r'<table[^>]*class="[^"]*ws-header[^"]*"[^>]*>.*?</table>', '', text, flags=re.DOTALL)
    text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL)

    # Remove noexport/sister sections
    text = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ul[^>]*class="[^"]*plainSister[^"]*"[^>]*>.*?</ul>', '', text, flags=re.DOTALL)

    # Remove edit section spans
    text = re.sub(r'<span[^>]*class="[^"]*mw-editsection[^"]*"[^>]*>.*?</span>', '', text, flags=re.DOTALL)

    # Split by chapter headings. Wang Bi edition uses h2 for chapters: <h2>X章</h2>
    # Match heading tags (h1-h3) containing Chinese number + 章
    chapter_pattern = re.compile(
        r'<(?:h[1-3])[^>]*id="([^"]*章)"[^>]*>.*?</(?:h[1-3])>',
        re.DOTALL
    )

    # Find all heading positions
    headings = []
    for m in chapter_pattern.finditer(text):
        heading_id = m.group(1)
        # Parse Chinese number from heading id (e.g., "二十五章" -> 25)
        num_str = heading_id.replace('章', '')
        ch_num = CHINESE_NUMS.get(num_str)
        if ch_num:
            headings.append((ch_num, m.end()))

    if not headings:
        raise RuntimeError("No chapter headings found in Dao De Jing Chinese text")

    # Find the end of chapter text — the Wang Bi edition has colophon (跋) sections
    # after chapter 81 as h1 headings. Find the first non-chapter heading after the last chapter.
    end_of_text = len(text)
    # Look for colophon h1 headings (跋, 晁說之跋, etc.) or footer markers
    for pattern in [r'<h1[^>]*id="[^"]*跋', r'<div[^>]*class="[^"]*catlinks',
                    r'<div[^>]*class="[^"]*printfooter']:
        m = re.search(pattern, text)
        if m and m.start() < end_of_text:
            # Back up to the mw-heading div that wraps it
            search_start = max(0, m.start() - 500)
            div_match = re.search(r'<div[^>]*class="[^"]*mw-heading[^"]*"[^>]*>', text[search_start:m.start()])
            if div_match:
                end_of_text = search_start + div_match.start()
            else:
                end_of_text = m.start()

    chapters = {}
    for i, (ch_num, start_pos) in enumerate(headings):
        if i + 1 < len(headings):
            # Find the start of the NEXT heading's div (which precedes the h tag)
            next_heading_start = headings[i + 1][1]
            search_start = max(start_pos, next_heading_start - 500)
            div_match = re.search(r'<div[^>]*class="[^"]*mw-heading[^"]*"[^>]*>', text[search_start:next_heading_start])
            if div_match:
                end_pos = search_start + div_match.start()
            else:
                end_pos = next_heading_start
        else:
            end_pos = end_of_text

        chunk = text[start_pos:end_pos]
        # Remove heading divs
        chunk = re.sub(r'<div[^>]*class="[^"]*mw-heading[^"]*"[^>]*>.*?</div>', '', chunk, flags=re.DOTALL)
        # Remove Wang Bi commentary blocks (<dl><dd><small> between paragraphs)
        chunk = re.sub(r'<dl>\s*<dd>.*?</dd>\s*</dl>', '', chunk, flags=re.DOTALL)

        # Extract paragraphs
        paragraphs = re.findall(r'<p>(.*?)</p>', chunk, re.DOTALL)

        result = []
        for p in paragraphs:
            clean = strip_html_tags(p)
            clean = clean.replace('\u3000', '').strip()
            clean = re.sub(r'\s+', '', clean)
            if clean:
                result.append(clean)

        if result:
            chapters[ch_num] = result

    return chapters


def parse_daodejing_english_html(html_text):
    """Parse Legge's Tâo Teh King from en.wikisource.org.

    Single page with h3 headings numbered 1-81. Very simple HTML — mostly just
    text and </br> tags for verse line breaks.
    Returns dict of {chapter_number: translation_text}.
    """
    # Remove <style> blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)

    # Remove header/navigation
    text = re.sub(r'<div[^>]*class="[^"]*ws-header[^"]*"[^>]*>.*?</div>\s*</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div[^>]*class="[^"]*ws-noexport[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ul[^>]*class="[^"]*plainSister[^"]*"[^>]*>.*?</ul>', '', text, flags=re.DOTALL)

    # Remove edit section spans
    text = re.sub(r'<span[^>]*class="[^"]*mw-editsection[^"]*"[^>]*>.*?</span>', '', text, flags=re.DOTALL)

    # Find chapter headings: h3 tags with numeric ids "1" through "81"
    # Pattern: <h3 id="1">...</h3> or within <div class="mw-heading mw-heading3"><h3 id="1">
    heading_pattern = re.compile(
        r'<h3[^>]*id="(\d+)"[^>]*>.*?</h3>',
        re.DOTALL
    )

    headings = []
    for m in heading_pattern.finditer(text):
        ch_num = int(m.group(1))
        if 1 <= ch_num <= 81:
            headings.append((ch_num, m.end()))

    if not headings:
        raise RuntimeError("No chapter headings found in Dao De Jing English text")

    chapters = {}
    for i, (ch_num, start_pos) in enumerate(headings):
        end_pos = headings[i + 1][1] if i + 1 < len(headings) else len(text)
        chunk = text[start_pos:end_pos]
        # Remove heading divs
        chunk = re.sub(r'<div[^>]*class="[^"]*mw-heading[^"]*"[^>]*>.*?</div>', '', chunk, flags=re.DOTALL)

        # Extract paragraphs
        paragraphs = re.findall(r'<p>(.*?)</p>', chunk, re.DOTALL)

        parts = []
        for p in paragraphs:
            # Convert <br> to newlines for verse formatting
            clean = re.sub(r'<br\s*/?>', '\n', p)
            clean = strip_html_tags(clean)
            clean = clean.replace('\u200b', '')
            # Collapse runs of spaces (but keep newlines for verse)
            clean = re.sub(r'[ \t]+', ' ', clean).strip()
            if clean:
                parts.append(clean)

        if parts:
            chapters[ch_num] = "\n\n".join(parts)

    return chapters


# ─── Text Processing ─────────────────────────────────────────────────────────

def is_cjk_character(char):
    """Check if a character is a CJK ideograph"""
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF) or      # CJK Unified Ideographs
        (0x3400 <= cp <= 0x4DBF) or      # CJK Extension A
        (0x20000 <= cp <= 0x2A6DF) or    # CJK Extension B
        (0xF900 <= cp <= 0xFAFF) or      # CJK Compatibility Ideographs
        (0x2F800 <= cp <= 0x2FA1F)       # CJK Compatibility Supplement
    )


def tokenize_chinese(text):
    """Tokenize Classical Chinese text character by character.

    Returns list of individual CJK characters (excludes punctuation).
    """
    return [ch for ch in text if is_cjk_character(ch)]


def split_long_lines(text, max_size=MAX_LINE_SIZE):
    """Split text that exceeds max_size at sentence boundaries."""
    if len(text) <= max_size:
        return [text]

    lines = []
    remaining = text

    while len(remaining) > max_size:
        # Try to split at Chinese sentence-ending punctuation
        split_pos = -1
        for punct in ['。', '！', '？', '；']:
            pos = remaining.rfind(punct, 0, max_size)
            if pos > 0 and pos > split_pos:
                split_pos = pos

        if split_pos <= 0:
            # Try clause boundaries
            for punct in ['，', '、', '：']:
                pos = remaining.rfind(punct, 0, max_size)
                if pos > 0 and pos > split_pos:
                    split_pos = pos

        if split_pos <= 0:
            # Force split at max_size
            split_pos = max_size - 1

        lines.append(remaining[:split_pos + 1])
        remaining = remaining[split_pos + 1:]

    if remaining:
        lines.append(remaining)

    return lines


def insert_book_text(cursor, book_id, work_id, book_number, label, paragraphs):
    """Insert a book's text lines and words. Returns (line_count, word_count)."""
    # Split long paragraphs
    lines = []
    for para in paragraphs:
        lines.extend(split_long_lines(para))

    if not lines:
        return 0, 0

    line_count = len(lines)

    cursor.execute('''
        INSERT INTO books (id, work_id, book_number, label, start_line, end_line, line_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (book_id, work_id, book_number, label, 1, line_count, line_count))

    total_words = 0
    seq_num = 0
    for line_num, line_text in enumerate(lines, 1):
        seq_num += 1
        cursor.execute('''
            INSERT INTO text_lines (book_id, line_number, sequence_number, line_text, line_xml, speaker)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (book_id, line_num, seq_num, line_text, None, None))

        chars = tokenize_chinese(line_text)
        for word_pos, char in enumerate(chars, 1):
            cursor.execute('''
                INSERT INTO words (word, book_id, line_number, sequence_number, word_position)
                VALUES (?, ?, ?, ?, ?)
            ''', (char, book_id, line_num, seq_num, word_pos))

        total_words += len(chars)

    return line_count, total_words


def insert_translation(cursor, book_id, translation_text, translator):
    """Insert a translation segment for a book. Returns True if inserted."""
    cursor.execute('SELECT line_count FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    if not row:
        return False
    line_count = row[0]

    cursor.execute('''
        INSERT INTO translation_segments (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (book_id, 1, line_count, 1, translation_text, translator, None))

    segment_id = cursor.lastrowid

    for line_num in range(1, line_count + 1):
        cursor.execute('''
            INSERT INTO translation_lookup (book_id, line_number, segment_id)
            VALUES (?, ?, ?)
        ''', (book_id, line_num, segment_id))

    return True


# ─── Zhuangzi Population ─────────────────────────────────────────────────────

def populate_zhuangzi(conn):
    """Import Zhuangzi text and translations."""
    cursor = conn.cursor()
    print("\n=== Zhuangzi (莊子) ===")

    # Insert author
    author_id = 'zhuangzi'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, '莊子', 'Zhuangzi', 'chinese', 1))

    # Insert work
    work_id = 'zhuangzi_zhuangzi'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, '莊子', None, 'Zhuangzi',
          'philosophy', None,
          'The Zhuangzi, foundational Daoist philosophical text. '
          '33 chapters: Inner (1-7), Outer (8-22), Miscellaneous (23-33). '
          'Source: Chinese Wikisource. Translation: Herbert Giles (1889).'))

    total_lines = 0
    total_words = 0

    # Import Chinese text
    print("\nImporting Chinese text...")
    for ch_num, ch_title, en_title, section in ZHUANGZI_CHAPTERS:
        book_id = f"zhuangzi_zhuangzi_{ch_num:02d}"
        label = f"{ch_title} — {en_title}"

        cache_path = os.path.join(DATA_DIR, f"zhuangzi_zh_{ch_num:02d}.json")
        with open(cache_path, "r", encoding="utf-8") as f:
            api_data = json.load(f)

        html_text = api_data["parse"]["text"]["*"]
        paragraphs = parse_chinese_html(html_text)

        if not paragraphs:
            raise RuntimeError(f"No text extracted for Zhuangzi chapter {ch_num} ({ch_title})")

        lc, wc = insert_book_text(cursor, book_id, work_id, ch_num, label, paragraphs)
        total_lines += lc
        total_words += wc
        print(f"  Chapter {ch_num:2d} ({ch_title}): {lc} lines, {wc} characters")

    # Import English translations
    print("\nImporting English translation (Giles 1889)...")
    trans_count = 0
    for ch_num, ch_title, en_title, section in ZHUANGZI_CHAPTERS:
        book_id = f"zhuangzi_zhuangzi_{ch_num:02d}"

        cache_path = os.path.join(DATA_DIR, f"zhuangzi_en_{ch_num:02d}.json")
        with open(cache_path, "r", encoding="utf-8") as f:
            api_data = json.load(f)

        html_text = api_data["parse"]["text"]["*"]
        paragraphs = parse_english_html(html_text)

        if not paragraphs:
            print(f"  WARNING: No English translation for chapter {ch_num}")
            continue

        translation_text = "\n\n".join(paragraphs)
        if insert_translation(cursor, book_id, translation_text, 'Herbert Giles (1889)'):
            trans_count += 1
            print(f"  Chapter {ch_num:2d}: {len(paragraphs)} paragraphs, {len(translation_text)} chars")

    conn.commit()
    print(f"\n  Zhuangzi: {len(ZHUANGZI_CHAPTERS)} chapters, {total_lines} lines, {total_words} characters, {trans_count} translations")
    return {"chapters": len(ZHUANGZI_CHAPTERS), "lines": total_lines, "words": total_words, "translations": trans_count}


# ─── Dao De Jing Population ──────────────────────────────────────────────────

def populate_daodejing(conn):
    """Import Dao De Jing text and translations."""
    cursor = conn.cursor()
    print("\n=== Dao De Jing (道德經) ===")

    # Insert author
    author_id = 'laozi'
    cursor.execute('''
        INSERT INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', (author_id, '老子', 'Laozi', 'chinese', 1))

    # Insert work
    work_id = 'laozi_daodejing'
    cursor.execute('''
        INSERT INTO works (id, author_id, title, title_alt, title_english, type, urn, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, author_id, '道德經', None, 'Dao De Jing',
          'philosophy', None,
          'The Dao De Jing (Tao Te Ching), foundational Daoist text attributed to Laozi. '
          '81 chapters in two parts: Dao Jing (道經, 1-37) and De Jing (德經, 38-81). '
          'Source: Chinese Wikisource (Wang Bi edition). Translation: James Legge (1891).'))

    # Parse Chinese text
    print("\nImporting Chinese text (Wang Bi edition)...")
    cache_path = os.path.join(DATA_DIR, "daodejing_zh.json")
    with open(cache_path, "r", encoding="utf-8") as f:
        api_data = json.load(f)

    html_text = api_data["parse"]["text"]["*"]
    zh_chapters = parse_daodejing_chinese_html(html_text)

    if not zh_chapters:
        raise RuntimeError("No chapters extracted from Dao De Jing Chinese text")

    # Parse English text
    print("Parsing English translation (Legge 1891)...")
    cache_path = os.path.join(DATA_DIR, "daodejing_en.json")
    with open(cache_path, "r", encoding="utf-8") as f:
        api_data = json.load(f)

    html_text = api_data["parse"]["text"]["*"]
    en_chapters = parse_daodejing_english_html(html_text)

    if not en_chapters:
        raise RuntimeError("No chapters extracted from Dao De Jing English text")

    total_lines = 0
    total_words = 0
    trans_count = 0

    for ch_num in range(1, 82):
        book_id = f"laozi_daodejing_{ch_num:02d}"
        label = f"第{ch_num}章"

        # Chinese text
        paragraphs = zh_chapters.get(ch_num)
        if not paragraphs:
            print(f"  WARNING: No Chinese text for chapter {ch_num}")
            continue

        lc, wc = insert_book_text(cursor, book_id, work_id, ch_num, label, paragraphs)
        total_lines += lc
        total_words += wc

        # English translation
        en_text = en_chapters.get(ch_num)
        if en_text:
            if insert_translation(cursor, book_id, en_text, 'James Legge (1891)'):
                trans_count += 1

        print(f"  Chapter {ch_num:2d}: {lc} lines, {wc} chars" +
              (f", translation {len(en_text)} chars" if en_text else ", NO translation"))

    conn.commit()
    print(f"\n  Dao De Jing: 81 chapters, {total_lines} lines, {total_words} characters, {trans_count} translations")
    return {"chapters": 81, "lines": total_lines, "words": total_words, "translations": trans_count}


# ─── Compression ──────────────────────────────────────────────────────────────

def compress_database(db_path, zip_path):
    """Compress the database to a ZIP file."""
    print(f"\nCompressing database to {zip_path}...")

    if os.path.exists(zip_path):
        os.remove(zip_path)

    db_size = os.path.getsize(db_path)
    db_name = os.path.basename(db_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(db_path, db_name)

    zip_size = os.path.getsize(zip_path)
    ratio = (1 - zip_size / db_size) * 100 if db_size > 0 else 0

    print(f"  Database: {db_size / 1024 / 1024:.1f} MB")
    print(f"  ZIP:      {zip_size / 1024 / 1024:.1f} MB ({ratio:.0f}% compression)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ClassicsViewer — Chinese Database Builder")
    print("=" * 60)
    print()
    print("Works:")
    print("  1. Zhuangzi (莊子) — 33 chapters")
    print("     Chinese: zh.wikisource.org (CC BY-SA 4.0)")
    print("     English: Herbert Giles (1889), Public Domain")
    print("  2. Dao De Jing (道德經) — 81 chapters")
    print("     Chinese: zh.wikisource.org, Wang Bi edition (CC BY-SA 4.0)")
    print("     English: James Legge (1891), Public Domain")
    print()

    # Step 1: Download all sources
    download_zhuangzi_chinese()
    download_zhuangzi_english()
    download_daodejing_chinese()
    download_daodejing_english()

    # Step 2: Create database
    print()
    conn = create_database(DB_PATH)

    # Step 3: Populate works
    zz_stats = populate_zhuangzi(conn)
    ddj_stats = populate_daodejing(conn)

    # Step 4: Close and compress
    conn.close()
    compress_database(DB_PATH, ZIP_PATH)

    # Summary
    total_chapters = zz_stats['chapters'] + ddj_stats['chapters']
    total_lines = zz_stats['lines'] + ddj_stats['lines']
    total_words = zz_stats['words'] + ddj_stats['words']
    total_trans = zz_stats['translations'] + ddj_stats['translations']

    print()
    print("=" * 60)
    print("Build complete!")
    print(f"  Authors:     2 (Zhuangzi, Laozi)")
    print(f"  Chapters:    {total_chapters} ({zz_stats['chapters']} + {ddj_stats['chapters']})")
    print(f"  Lines:       {total_lines}")
    print(f"  Characters:  {total_words}")
    print(f"  Translations: {total_trans} chapters")
    print()
    print("License:")
    print("  Chinese text: CC BY-SA 4.0 (Wikisource)")
    print("  Zhuangzi English: Public Domain (Herbert Giles, 1889)")
    print("  Dao De Jing English: Public Domain (James Legge, 1891)")
    print("=" * 60)


if __name__ == "__main__":
    main()
