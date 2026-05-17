#!/usr/bin/env python3
"""One-time OCR pass over the Silva Rhetoricae Greek-name GIFs.

Reads figures/rhetoric.byu.edu/Images/Greek/*.gif, recognizes the polytonic
Greek with Tesseract (tessdata_best `grc` model), and emits:

  - greek_terms.csv           gif_name, greek_unicode   (authoritative after review)
  - greek_terms_review.html   side-by-side image + OCR text, for human review

This is a first-pass aid only -- run once, review the HTML, capture corrections.
It is NOT part of the repeatable build (build_rhetoric_db.py).

Preprocessing per GIF: grayscale -> upscale 6x LANCZOS -> Otsu binarize ->
20px white border.

Tesseract is run with --psm 13 (raw line). --psm 7 (single text line) applies
line-layout heuristics that systematically misread a leading epsilon as omicron
(e.g. ekphrasis -> omicron-kappa... instead of epsilon-kappa...); --psm 13
bypasses those heuristics and reads the leading letter correctly.

Two post-OCR cleanup stages, both repeatable (reruns reproduce the same CSV):

  1. Edge trim -- strip leading/trailing characters that are not letters
     (stray breathing marks, apostrophes, commas, periods Tesseract adds).
  2. Corrections file -- greek_terms_corrections.csv holds human-reviewed fixes
     for genuine in-word misreads that no algorithm can repair. Each row
     (gif_name, corrected_greek) overrides that GIF's OCR result. This captures
     review without it being lost when the script is re-run.
"""
import csv
import html
import subprocess
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
GIF_DIR = HERE / "rhetoric.byu.edu" / "Images" / "Greek"
TESSDATA = HERE / "tessdata"
CSV_OUT = HERE / "greek_terms.csv"
HTML_OUT = HERE / "greek_terms_review.html"
CORRECTIONS_CSV = HERE / "greek_terms_corrections.csv"

UPSCALE = 6  # 4-6x range


def otsu_threshold(img):
    """Otsu's method: pick the grayscale cutoff that maximizes inter-class variance."""
    hist = img.histogram()[:256]
    total = sum(hist)
    sum_total = sum(i * hist[i] for i in range(256))
    sum_b = w_b = 0
    max_var = -1.0
    threshold = 127
    for i in range(256):
        w_b += hist[i]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += i * hist[i]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > max_var:
            max_var = var
            threshold = i
    return threshold


def preprocess(path):
    img = Image.open(path).convert("L")                     # 1. grayscale
    w, h = img.size
    img = img.resize((w * UPSCALE, h * UPSCALE), Image.LANCZOS)  # 2. upscale
    t = otsu_threshold(img)
    img = img.point(lambda p: 255 if p > t else 0, mode="1").convert("L")  # 3. binarize
    img = ImageOps.expand(img, border=20, fill=255)         # 4. pad white border
    return img


def trim_edges(text):
    """Strip leading/trailing chars that are not letters or combining marks.

    Removes OCR edge noise -- stray breathing marks (U+1FBF), apostrophes,
    commas, periods -- without touching internal spaces of multi-word terms.
    """
    def keep(c):
        return c.isalpha() or unicodedata.category(c).startswith("M")
    chars = list(text)
    while chars and not keep(chars[0]):
        chars.pop(0)
    while chars and not keep(chars[-1]):
        chars.pop()
    return "".join(chars).strip()


def ocr(img):
    proc = preprocess(img) if isinstance(img, (str, Path)) else img
    tmp = HERE / "_ocr_tmp.png"
    proc.save(tmp)
    try:
        out = subprocess.run(
            ["tesseract", str(tmp), "stdout",
             "--tessdata-dir", str(TESSDATA),
             "-l", "grc", "--psm", "13"],
            capture_output=True, text=True,
        )
    finally:
        tmp.unlink(missing_ok=True)
    text = unicodedata.normalize("NFC", out.stdout.strip())
    return trim_edges(text)


def load_corrections(known_names):
    """Read greek_terms_corrections.csv -> {gif_name: corrected_greek}."""
    if not CORRECTIONS_CSV.exists():
        return {}
    with CORRECTIONS_CSV.open(encoding="utf-8") as f:
        rows = [r for r in csv.reader(f) if r and len(r) >= 2]
    corrections = {r[0].strip(): unicodedata.normalize("NFC", r[1].strip())
                   for r in rows[1:]}
    stale = sorted(set(corrections) - known_names)
    if stale:
        sys.exit(f"ERROR: {CORRECTIONS_CSV.name} references unknown GIFs: {stale}")
    return corrections


def main():
    gifs = sorted(GIF_DIR.glob("*.gif"))
    if not gifs:
        sys.exit(f"No GIFs found under {GIF_DIR}")
    print(f"OCR over {len(gifs)} GIFs using {TESSDATA}/grc.traineddata ...")

    ocr_text = {}
    for i, gif in enumerate(gifs, 1):
        ocr_text[gif.name] = ocr(gif)
        if i % 25 == 0 or i == len(gifs):
            print(f"  {i}/{len(gifs)}")

    corrections = load_corrections(set(ocr_text))
    rows = []          # (name, final_text, was_corrected)
    for gif in gifs:
        name = gif.name
        raw = ocr_text[name]
        if name in corrections and corrections[name] != raw:
            rows.append((name, corrections[name], True))
        else:
            rows.append((name, raw, False))
    print(f"Applied {sum(c for _, _, c in rows)} correction(s) "
          f"from {CORRECTIONS_CSV.name}")

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gif_name", "greek_unicode"])
        w.writerows((name, text) for name, text, _ in rows)
    print(f"Wrote {CSV_OUT}")

    rel = "rhetoric.byu.edu/Images/Greek"
    parts = ["<!doctype html><meta charset='utf-8'>",
             "<title>Greek term OCR review</title>",
             "<style>body{font-family:sans-serif}"
             "table{border-collapse:collapse}"
             "td,th{border:1px solid #ccc;padding:8px 12px;vertical-align:middle}"
             "img{background:#fff}"
             ".gk{font-size:28px}.empty{color:#c00;font-style:italic}</style>",
             f"<h1>Greek term OCR review &mdash; {len(rows)} GIFs</h1>",
             "<p>Compare each image with its text. Fix edge noise via "
             "<code>trim_edges()</code>; record in-word misreads in "
             "<code>greek_terms_corrections.csv</code>.</p>",
             "<table><tr><th>GIF</th><th>Image</th><th>Text</th></tr>"]
    blank = 0
    for name, text, _ in rows:
        if not text:
            blank += 1
        cell = (f"<span class='gk'>{html.escape(text)}</span>"
                if text else "<span class='empty'>(blank)</span>")
        parts.append(
            f"<tr><td><code>{html.escape(name)}</code></td>"
            f"<td><img src='{rel}/{html.escape(name)}'></td>"
            f"<td>{cell}</td></tr>")
    parts.append("</table>")
    HTML_OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {HTML_OUT}  ({blank} blank results)")


if __name__ == "__main__":
    main()
