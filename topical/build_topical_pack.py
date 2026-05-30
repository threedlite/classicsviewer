#!/usr/bin/env python3
"""
Build the topical-link pack as a set of mmap-friendly binary files. NO SQLITE
in the pack. Implements the design in TOPICAL.md Part 1.

Output layout under topical/dist/<lang>/ (then zipped to topical_<lang>.zip):

    positions.bin    sorted-array reverse position lookup
    rowmeta.bin      per-passage author/work indices + anchor pos + name pools
    T.f16            P x K_topics float16 row-major LDA topic matrix
    invidx.bin       TF-IDF sparse inverted index, per term -> (row_idx, tfidf)
    vocab.bin        term strings + idf
    manifest.json    file shas, params, kinds_available, kind_labels

Usage:
    ./venv/bin/python3 topical/build_topical_pack.py greek
                                                     [--lda-k-topics 1000]
                                                     [--lda-seed 0]
                                                     [--lda-iter 200]
                                                     [--min-bag 8]
                                                     [--n 10]
                                                     [--source-db <path>]
                                                     [--max-books N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sqlite3
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.preprocessing import normalize

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO / "data-prep" / "perseus_texts_extended.db"
DEFAULT_OUT_DIR = REPO / "topical" / "dist"
PACK_DEST_DIRS = [
    REPO / "topical_pack" / "src" / "main" / "assets",
    REPO / "app" / "src" / "debug" / "assets" / "topical",
    REPO / "ios" / "ClassicsViewer" / "Resources",
]

LANGUAGE_REGISTRY = {
    "greek": {
        "authors_language": "greek",
        "db_file_stem": "topical_greek",
        "translator": "Interlinear (Beta, generated from app dictionary and treebank)",
        "parser": "greek",
    },
    "latin": {
        "authors_language": "latin",
        "db_file_stem": "topical_latin",
        "translator": "Interlinear (Beta, AI-generated from app dictionary)",
        "parser": "latin",
    },
}

CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ"}

LIGHT_LEMMATA_GREEK = {
    unicodedata.normalize("NFC", w) for w in [
        "εἰμί", "ἔχω", "γίγνομαι", "λέγω", "ποιέω", "ὁράω", "ἔρχομαι",
        "φημί", "οἶδα", "βούλομαι", "δοκέω", "δίδωμι", "λαμβάνω",
        "δύναμαι", "γιγνώσκω", "θέλω", "ἀκούω", "ζάω", "πάσχω",
        "καλέω", "τίθημι", "ἵστημι", "ἡγέομαι", "νομίζω",
    ]
}
LIGHT_LEMMATA_LATIN = {
    "sum", "habeo", "facio", "dico", "video", "do", "duco", "ago",
    "venio", "eo", "puto", "scio", "volo", "possum", "debeo",
    "oporteo", "necesse", "res", "homo", "vir", "pars", "modo",
}


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #
def die(msg: str) -> None:
    sys.stderr.write(f"FATAL: {msg}\n")
    sys.exit(1)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Interlinear parsing — content lemmata
# --------------------------------------------------------------------------- #
def parse_interlinear_greek(text: str) -> list[str]:
    out: list[str] = []
    for part in text.split("|"):
        if "~" not in part:
            continue
        left, right = part.split("~", 1)
        lt = left.split()
        rt = right.lstrip("*").split()
        if not lt or not rt or rt[0] not in CONTENT_POS:
            continue
        lem = unicodedata.normalize("NFC", lt[0])
        if not lem or lem in ("?", "???", "-") or lem in LIGHT_LEMMATA_GREEK:
            continue
        out.append(lem)
    return out


def parse_interlinear_latin(text: str) -> list[str]:
    out: list[str] = []
    next_is_lemma = False
    for part in text.split("|"):
        ps = part.strip()
        if not ps:
            continue
        if ps.startswith("**") and ps.endswith("**"):
            next_is_lemma = True
            continue
        if next_is_lemma:
            toks = ps.split()
            if toks:
                lem = unicodedata.normalize("NFC", toks[0]).lower()
                if len(lem) >= 2 and lem.isalpha() and lem not in LIGHT_LEMMATA_LATIN:
                    out.append(lem)
            next_is_lemma = False
    return out


PARSERS = {"greek": parse_interlinear_greek, "latin": parse_interlinear_latin}


# --------------------------------------------------------------------------- #
# Step 1: enumerate positions, form passages, build content-lemma bags
# --------------------------------------------------------------------------- #
def enumerate_and_passage(src, lang_val, n, max_books, translator, parse_lemmas):
    """For each book in `lang_val`, yield per-book lists of:
      - positions: [(book_id, line_number, sequence_number)]
      - passage rows: [(book_id_idx, line, seq, row_idx)] flattened to one row per
        passage's anchor position
      - bag for each passage
      - author_id, work_id, anchor book_id, anchor line/seq per row
    Returns:
      positions_list: list of (book_id_str, line, seq, row_idx) sorted globally
      passage_rows: list of (author_id, work_id, anchor_book_id, anchor_line, anchor_seq)
      bags: list of list[str] per passage
    """
    if max_books:
        books_cur = src.execute(
            "SELECT b.id, w.id, w.author_id FROM books b "
            "JOIN works w ON w.id = b.work_id "
            "JOIN authors a ON a.id = w.author_id "
            "WHERE a.language = ? ORDER BY b.id LIMIT ?",
            (lang_val, max_books),
        )
    else:
        books_cur = src.execute(
            "SELECT b.id, w.id, w.author_id FROM books b "
            "JOIN works w ON w.id = b.work_id "
            "JOIN authors a ON a.id = w.author_id "
            "WHERE a.language = ? ORDER BY b.id",
            (lang_val,),
        )

    positions_out: list[tuple[str, int, int, int]] = []  # (book_id, line, seq, row_idx)
    rowmeta_out: list[tuple[str, str, str, int, int]] = []  # (author_id, work_id, anchor_book_id, anchor_line, anchor_seq)
    bags_out: list[list[str]] = []
    row_idx_counter = 0
    dup_skipped = 0
    n_books_done = 0
    t_books = time.time()

    for book_id, work_id, author_id in books_cur:
        # 1) per-book positions (collapse duplicate triples)
        positions: list[tuple[int, int]] = []
        last_key = None
        for ln, seq in src.execute(
            "SELECT line_number, sequence_number FROM text_lines "
            "WHERE book_id = ? ORDER BY line_number, sequence_number, id",
            (book_id,),
        ):
            key = (ln, seq)
            if key == last_key:
                dup_skipped += 1
                continue
            last_key = key
            positions.append((ln, seq))
        if not positions:
            continue

        # 2) per-book interlinear: line_number -> content lemmas
        il: dict[int, list[str]] = {}
        for ln, txt in src.execute(
            "SELECT start_line, translation_text FROM translation_segments "
            "WHERE book_id = ? AND translator = ?",
            (book_id, translator),
        ):
            lems = parse_lemmas(txt)
            if lems:
                il.setdefault(ln, []).extend(lems)

        # 3) windows of N consecutive positions -> passages
        for start in range(0, len(positions), n):
            window = positions[start:start + n]
            anchor_line, anchor_seq = window[0]
            min_ln, max_ln = window[0][0], window[-1][0]
            bag: list[str] = []
            for ln in range(min_ln, max_ln + 1):
                if ln in il:
                    bag.extend(il[ln])
            row_idx = row_idx_counter
            row_idx_counter += 1
            bags_out.append(bag)
            rowmeta_out.append((author_id, work_id, book_id, anchor_line, anchor_seq))
            # Map ALL positions in window to this row_idx so position lookups for
            # any line in the window resolve to the same passage.
            for ln, seq in window:
                positions_out.append((book_id, ln, seq, row_idx))

        n_books_done += 1
        if n_books_done % 5000 == 0:
            log(f"  processed {n_books_done:,} books  "
                f"positions={len(positions_out):,}  passages={row_idx_counter:,}  "
                f"elapsed={time.time()-t_books:.0f}s")
    if dup_skipped:
        log(f"  collapsed {dup_skipped} duplicate position triples (kept first)")
    log(f"  totals: positions={len(positions_out):,}  passages={row_idx_counter:,}  "
        f"non-empty bags={sum(1 for b in bags_out if b):,}")
    return positions_out, rowmeta_out, bags_out


# --------------------------------------------------------------------------- #
# Step 2: vectorise once -> count matrix + L2-normalised TF-IDF + vocab list
# --------------------------------------------------------------------------- #
def vectorize(bags: list[list[str]], min_bag: int):
    bags_eff = [b if len(b) >= min_bag else [] for b in bags]
    cv = CountVectorizer(analyzer=lambda x: x, max_df=0.30, min_df=3, dtype=np.int32)
    X_counts = cv.fit_transform(bags_eff)
    tfidf = TfidfTransformer(sublinear_tf=True)
    X_tfidf = tfidf.fit_transform(X_counts).astype(np.float32)
    X_tfidf = normalize(X_tfidf, norm="l2", axis=1, copy=False)
    vocab = cv.get_feature_names_out().tolist()
    idf = tfidf.idf_.astype(np.float32)
    n_dropped = sum(1 for b in bags if len(b) < min_bag)
    return X_counts, X_tfidf, vocab, idf, n_dropped


# --------------------------------------------------------------------------- #
# Step 3: train LDA via tomotopy, return P x K_topics L2-normalised float32
# --------------------------------------------------------------------------- #
def train_lda_tomotopy(bags: list[list[str]], min_bag: int, vocab: list[str],
                       k_topics: int, seed: int, iterations: int) -> np.ndarray:
    import tomotopy as tp
    log(f"  training LDA via tomotopy K_topics={k_topics} seed={seed} iter={iterations}")
    vocab_set = set(vocab)
    mdl = tp.LDAModel(k=k_topics, alpha=50.0 / k_topics, eta=0.01, seed=seed)
    added: list[bool] = []
    t0 = time.time()
    for bag in bags:
        if len(bag) < min_bag:
            added.append(False)
            continue
        filtered = [t for t in bag if t in vocab_set]
        if not filtered:
            added.append(False)
            continue
        mdl.add_doc(filtered)
        added.append(True)
    n_added = sum(added)
    log(f"    added {n_added:,} docs of {len(bags):,}; corpus build in {time.time()-t0:.1f}s")
    t1 = time.time()
    mdl.train(iterations, workers=0)
    log(f"    Gibbs sampling: {iterations} iter in {(time.time()-t1)/60:.1f} min  "
        f"log-likelihood={mdl.ll_per_word:.4f}")
    T = np.zeros((len(bags), k_topics), dtype=np.float32)
    it = iter(mdl.docs)
    for i, was_added in enumerate(added):
        if not was_added:
            continue
        T[i] = next(it).get_topic_dist()
    T = normalize(T, norm="l2", axis=1, copy=False)
    return T


# --------------------------------------------------------------------------- #
# Step 4: write positions.bin
#
# Header (32 bytes):
#   u32  magic = 0x504F5331 ("POS1")
#   u32  schema_version = 1
#   u32  record_count
#   u32  record_stride = 16
#   u32  book_id_pool_offset
#   u32  book_id_pool_bytes
#   u32  book_id_count
#   u32  reserved = 0
# Records (16 bytes each, sorted by (book_id_idx asc, line asc, seq asc)):
#   u32  book_id_idx
#   i32  line
#   i32  seq
#   i32  row_idx                 (-1 = not in any passage, but we don't emit those)
# Pool layout starts at book_id_pool_offset:
#   u32  count
#   for each i: u16 byte_length; UTF-8 bytes
# --------------------------------------------------------------------------- #
def write_positions(out: Path, positions: list[tuple[str, int, int, int]]) -> int:
    # Build deduped book_id pool sorted by book_id string for binary search.
    book_ids_sorted = sorted({p[0] for p in positions})
    book_id_to_idx = {bid: i for i, bid in enumerate(book_ids_sorted)}
    # Convert records to (book_id_idx, line, seq, row_idx).
    rows = sorted(
        ((book_id_to_idx[bid], ln, seq, row_idx) for (bid, ln, seq, row_idx) in positions),
        key=lambda r: (r[0], r[1], r[2]),
    )
    HEADER_SIZE = 32
    REC_STRIDE = 16
    rec_bytes = len(rows) * REC_STRIDE

    # Build pool bytes
    pool = bytearray()
    pool += struct.pack("<I", len(book_ids_sorted))
    for bid in book_ids_sorted:
        b = bid.encode("utf-8")
        pool += struct.pack("<H", len(b))
        pool += b
    pool_bytes = bytes(pool)
    pool_offset = HEADER_SIZE + rec_bytes

    # Records
    rec_buf = bytearray(rec_bytes)
    mv = memoryview(rec_buf)
    for i, (bidx, ln, seq, row_idx) in enumerate(rows):
        struct.pack_into("<IiiI", mv, i * REC_STRIDE, bidx, ln, seq, row_idx)

    # Header
    header = struct.pack(
        "<IIIIIIII",
        0x504F5331, 1, len(rows), REC_STRIDE,
        pool_offset, len(pool_bytes), len(book_ids_sorted), 0,
    )
    with open(out, "wb") as f:
        f.write(header)
        f.write(rec_buf)
        f.write(pool_bytes)
    return out.stat().st_size


# --------------------------------------------------------------------------- #
# Step 5: write rowmeta.bin
#
# Header (16 bytes):
#   u32 magic = 0x524F4D31 ("ROM1")
#   u32 schema_version = 1
#   u32 record_count
#   u32 record_stride = 20
# Records (20 bytes each, indexed by row_idx 0..P-1):
#   u32 author_idx
#   u32 work_idx
#   u32 anchor_book_id_idx
#   i32 anchor_line
#   i32 anchor_seq
# After records, three pools follow:
#   author pool:  u32 count; { u16 byte_length; UTF-8 bytes }*
#   work pool:    u32 count; { u16 byte_length; UTF-8 bytes }*
#   book pool:    u32 count; { u16 byte_length; UTF-8 bytes }*  (subset, kept in
#                                                                same order as positions.bin
#                                                                for reuse)
# Pool offsets are recorded at the very end (4 × u32) so the reader can find
# them: author_off, work_off, book_off, file_end_marker.
# --------------------------------------------------------------------------- #
def write_rowmeta(out: Path,
                  rowmeta: list[tuple[str, str, str, int, int]],
                  position_book_id_index: dict[str, int]) -> int:
    # Dedupe author_id, work_id in insertion order so indices are stable.
    authors_sorted: list[str] = []
    author_to_idx: dict[str, int] = {}
    works_sorted: list[str] = []
    work_to_idx: dict[str, int] = {}
    for aid, wid, _bid, _ln, _seq in rowmeta:
        if aid not in author_to_idx:
            author_to_idx[aid] = len(authors_sorted)
            authors_sorted.append(aid)
        if wid not in work_to_idx:
            work_to_idx[wid] = len(works_sorted)
            works_sorted.append(wid)

    HEADER_SIZE = 16
    REC_STRIDE = 20
    rec_bytes = len(rowmeta) * REC_STRIDE
    rec_buf = bytearray(rec_bytes)
    mv = memoryview(rec_buf)
    for i, (aid, wid, bid, ln, seq) in enumerate(rowmeta):
        bidx = position_book_id_index[bid]
        struct.pack_into(
            "<IIIii", mv, i * REC_STRIDE,
            author_to_idx[aid], work_to_idx[wid], bidx, ln, seq,
        )

    def pack_pool(strs):
        buf = bytearray()
        buf += struct.pack("<I", len(strs))
        for s in strs:
            b = s.encode("utf-8")
            buf += struct.pack("<H", len(b))
            buf += b
        return bytes(buf)

    author_pool = pack_pool(authors_sorted)
    work_pool = pack_pool(works_sorted)
    # We don't duplicate book_ids — the reader uses positions.bin's pool.

    header = struct.pack("<IIII", 0x524F4D31, 1, len(rowmeta), REC_STRIDE)
    author_off = HEADER_SIZE + rec_bytes
    work_off = author_off + len(author_pool)
    book_off = work_off + len(work_pool)  # not used (reuse positions.bin)
    footer = struct.pack("<IIII", author_off, work_off, book_off, 0xDEADBEEF)

    with open(out, "wb") as f:
        f.write(header)
        f.write(rec_buf)
        f.write(author_pool)
        f.write(work_pool)
        f.write(footer)
    return out.stat().st_size


# --------------------------------------------------------------------------- #
# Step 6: write T.f16 — P x K row-major float16, no header
# --------------------------------------------------------------------------- #
def write_t_f16(out: Path, T: np.ndarray) -> int:
    T16 = T.astype(np.float16, copy=False)
    T16.tofile(out)
    return out.stat().st_size


# --------------------------------------------------------------------------- #
# Step 6b: IVF — k-means on T to nlist=sqrt(P) centroids, plus per-centroid
# sorted inverted lists of row_idx. Powers the fast LDA KNN at query time:
# the reader scores q against `nlist` centroids and only walks the `nprobe`
# nearest ones (~10 of 576 for Greek), reducing scored rows by ~57x.
#
# ivf.centroids layout: nlist × K × 2 bytes float16, row-major, no header.
# ivf.lists layout:
#   Header (16 bytes):
#     u32 magic = 0x49564631 ("IVF1")
#     u32 schema_version = 1
#     u32 nlist
#     u32 list_offsets_offset  (byte offset of the offsets array)
#   Then nlist+1 u32 offsets (as indices into the row-idx array, not bytes).
#   Then a flat u32 array of row_idx values, ordered by centroid.
# --------------------------------------------------------------------------- #
def write_ivf(centroids_out: Path, lists_out: Path,
              T: np.ndarray, passage_bags: list[list[str]], min_bag: int,
              seed: int) -> tuple[int, int, int]:
    """Train k-means on rows of T whose source bag is large enough (skip the
    zeroed tiny-bag rows so they don't pollute centroids). Returns (centroid
    bytes, list bytes, nlist)."""
    P = T.shape[0]
    K = T.shape[1]
    nlist = max(16, int(round(np.sqrt(P))))
    sizes = np.fromiter((len(b) for b in passage_bags), dtype=np.int32, count=P)
    valid_mask = sizes >= min_bag
    valid_rows = np.where(valid_mask)[0]
    log(f"  training MiniBatchKMeans nlist={nlist} on {len(valid_rows):,}/{P:,} non-zero rows ...")
    t0 = time.time()
    km = MiniBatchKMeans(
        n_clusters=nlist,
        random_state=seed,
        batch_size=4096,
        max_iter=30,
        n_init=3,
        reassignment_ratio=0.01,
        verbose=0,
    )
    km.fit(T[valid_rows])
    log(f"  k-means fit in {(time.time()-t0)/60:.1f} min  inertia={km.inertia_:.1f}")

    # Assign every valid row; tiny-bag rows are excluded from lists (they have
    # zero topic vectors and would always lose at query time anyway).
    assignments = km.predict(T[valid_rows])

    # Build inverted lists.
    # Order: centroid 0 rows, centroid 1 rows, ... each sorted ascending.
    sorted_rows_per_centroid: list[np.ndarray] = [None] * nlist  # type: ignore
    for c in range(nlist):
        idx_in_valid = np.where(assignments == c)[0]
        sorted_rows_per_centroid[c] = np.sort(valid_rows[idx_in_valid]).astype(np.uint32)

    # Centroids file
    centroids = km.cluster_centers_.astype(np.float16)
    centroids.tofile(centroids_out)
    cb = centroids_out.stat().st_size

    # Lists file
    HEADER_SIZE = 16
    list_offsets = np.empty(nlist + 1, dtype=np.uint32)
    list_offsets[0] = 0
    for c in range(nlist):
        list_offsets[c + 1] = list_offsets[c] + len(sorted_rows_per_centroid[c])
    flat = np.concatenate(sorted_rows_per_centroid) if nlist > 0 else np.array([], dtype=np.uint32)
    offsets_offset = HEADER_SIZE  # offsets follow immediately
    with open(lists_out, "wb") as f:
        f.write(struct.pack("<IIII", 0x49564631, 1, nlist, offsets_offset))
        f.write(list_offsets.tobytes())
        f.write(flat.tobytes())
    lb = lists_out.stat().st_size
    return cb, lb, nlist


# --------------------------------------------------------------------------- #
# Step 6c: write bags.bin — per-row sparse (term_idx, tf) lists
#
# Lets the runtime build a TF-IDF query for the source passage WITHOUT
# re-parsing the main DB's interlinear (which the sample tier lacks). The bag
# is exactly the source row's nonzero columns of X_counts.
#
# Layout:
#   Header (16 bytes):
#     u32 magic = 0x42414731 ("BAG1")
#     u32 schema_version = 1
#     u32 record_count        // = P
#     u32 entries_offset      // byte offset where the (term,tf) entries begin
#   Then P+1 u32 row offsets (entry indices, not bytes), so row r's entries
#   live in entries[row_offsets[r] .. row_offsets[r+1]).
#   Then a flat array of entries: each entry is (u32 term_idx, u16 tf), 6 bytes.
# --------------------------------------------------------------------------- #
def write_bags(out: Path, X_counts: sp.csr_matrix) -> int:
    P = X_counts.shape[0]
    HEADER_SIZE = 16
    offsets_bytes = (P + 1) * 4
    entries_offset = HEADER_SIZE + offsets_bytes

    X = X_counts.tocsr(copy=False)
    indptr = X.indptr.astype(np.int64)
    indices = X.indices.astype(np.uint32)
    data = X.data.astype(np.int64)
    # cap tf at u16 max so the encoded entry fits in 6 bytes
    np.clip(data, 0, 0xFFFF, out=data)
    data = data.astype(np.uint16)

    n_entries = int(indptr[-1])
    entries = np.zeros(n_entries, dtype=[("t", "<u4"), ("v", "<u2")])
    entries["t"] = indices
    entries["v"] = data

    # Row offsets are *entry indices*, i.e., the same as indptr.
    row_offsets = indptr.astype(np.uint32)

    with open(out, "wb") as f:
        f.write(struct.pack("<IIII", 0x42414731, 1, P, entries_offset))
        f.write(row_offsets.tobytes())
        f.write(entries.tobytes())
    return out.stat().st_size


# --------------------------------------------------------------------------- #
# Step 7: write invidx.bin + vocab.bin
#
# invidx.bin layout:
#   Header (16 bytes):
#     u32 magic = 0x494E5631 ("INV1")
#     u32 schema_version = 1
#     u32 vocab_size
#     u32 postings_offset
#   Then vocab_size+1 u32 offsets (byte offsets within postings section).
#   Then postings: per term, ascending row_idx, entry = (u32 row_idx, f16 tfidf).
#
# vocab.bin layout:
#   Header (12 bytes):
#     u32 magic = 0x564F4331 ("VOC1")
#     u32 schema_version = 1
#     u32 vocab_size
#   Then per term: u16 byte_length; UTF-8 term; f16 idf
#   Then vocab_size+1 u32 byte-offsets at the tail for random access.
# --------------------------------------------------------------------------- #
def write_invidx_and_vocab(invidx_out: Path, vocab_out: Path,
                            X_tfidf: sp.csr_matrix, vocab: list[str],
                            idf: np.ndarray) -> tuple[int, int]:
    X_csc = X_tfidf.tocsc(copy=False)
    n_terms = len(vocab)
    # Build per-term postings byte buffer
    postings_bufs: list[bytes] = []
    offsets: list[int] = []
    cur = 0
    for t in range(n_terms):
        start, end = X_csc.indptr[t], X_csc.indptr[t + 1]
        rows = X_csc.indices[start:end].astype(np.int64)
        vals = X_csc.data[start:end].astype(np.float16)
        # sort by row_idx ascending
        order = np.argsort(rows, kind="stable")
        rows = rows[order]
        vals = vals[order]
        # encode (u32 row_idx, f16 tfidf) entries
        entry_bytes = bytearray(len(rows) * 6)
        mv = memoryview(entry_bytes)
        for j in range(len(rows)):
            struct.pack_into("<I", mv, j * 6, int(rows[j]))
            # f16 little-endian: numpy already little on x86/arm64
        # Write the f16 values directly using numpy view (4 bytes for row, 2 for f16)
        # We'll use a different approach: pack ints and floats separately.
        # Use np.empty with structured dtype.
        recs = np.zeros(len(rows), dtype=[("r", "<u4"), ("v", "<f2")])
        recs["r"] = rows.astype(np.uint32)
        recs["v"] = vals
        b = recs.tobytes()
        postings_bufs.append(b)
        offsets.append(cur)
        cur += len(b)
    offsets.append(cur)  # sentinel for last+1

    HEADER_SIZE = 16
    offsets_size = (n_terms + 1) * 4
    postings_offset = HEADER_SIZE + offsets_size

    with open(invidx_out, "wb") as f:
        f.write(struct.pack("<IIII", 0x494E5631, 1, n_terms, postings_offset))
        f.write(np.asarray(offsets, dtype="<u4").tobytes())
        for b in postings_bufs:
            f.write(b)

    # vocab.bin: per term entries first, then byte-offsets at the tail
    body = bytearray()
    entry_offsets: list[int] = []
    for t, term in enumerate(vocab):
        entry_offsets.append(len(body))
        b = term.encode("utf-8")
        body += struct.pack("<H", len(b))
        body += b
        body += np.float16(idf[t]).tobytes()
    entry_offsets.append(len(body))

    VOCAB_HEADER_SIZE = 12
    with open(vocab_out, "wb") as f:
        f.write(struct.pack("<III", 0x564F4331, 1, n_terms))
        # Adjust offsets to absolute bytes within the file.
        abs_offs = [VOCAB_HEADER_SIZE + o for o in entry_offsets]
        f.write(bytes(body))
        f.write(np.asarray(abs_offs, dtype="<u4").tobytes())

    return invidx_out.stat().st_size, vocab_out.stat().st_size


# --------------------------------------------------------------------------- #
# Step 8: sha256 + manifest.json
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(out_dir: Path, language: str, params: dict,
                   file_names: list[str]) -> Path:
    files = {}
    for name in file_names:
        p = out_dir / name
        files[name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}

    bid_blob = json.dumps({
        "schema_version": params["schema_version"],
        "language": language,
        "lda_seeds": params["lda_seeds"],
        "lda_topics": params["lda_topics"],
        "vocab_size": params["vocab_size"],
        "min_bag": params["min_bag"],
        "sklearn_version": params["sklearn_version"],
        "tomotopy_version": params["tomotopy_version"],
        "text_build_time": params["text_build_time"],
    }, sort_keys=True).encode("utf-8")
    build_id = hashlib.sha256(bid_blob).hexdigest()

    manifest = {
        "schema_version": params["schema_version"],
        "language": language,
        "build_id": build_id,
        "text_build_time": params["text_build_time"],
        "topical_build_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sklearn_version": params["sklearn_version"],
        "tomotopy_version": params["tomotopy_version"],
        "vocab_size": params["vocab_size"],
        "passage_count": params["passage_count"],
        "lda_topics": params["lda_topics"],
        "lda_seeds": params["lda_seeds"],
        "lda_iter": params["lda_iter"],
        "min_bag": params["min_bag"],
        "n": params["n"],
        "kinds_available": ["lda", "tfidf"],
        "kind_labels": {
            "lda": {
                "ui": "Topical",
                "hint": "Shared latent topics — cross-author thematic neighbours",
            },
            "tfidf": {
                "ui": "Lexical",
                "hint": "Shared content vocabulary — same case / treatise / lexicon references",
            },
        },
        "default_kind": "lda",
        "tfidf_min_sim": params["tfidf_min_sim"],
        "lda_min_sim": params["lda_min_sim"],
        "exclude_scope": params["exclude_scope"],
        "ivf_nlist": params["ivf_nlist"],
        "ivf_nprobe": params["ivf_nprobe"],
        "files": files,
    }
    mpath = out_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return mpath


# --------------------------------------------------------------------------- #
# Step 9: zip + place
# --------------------------------------------------------------------------- #
def zip_dir(stage_dir: Path, zip_out: Path) -> int:
    if zip_out.exists():
        zip_out.unlink()
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(stage_dir.iterdir()):
            if p.is_file():
                z.write(p, arcname=p.name)
    with zipfile.ZipFile(zip_out) as z:
        if z.testzip() is not None:
            die(f"zip integrity check failed: {zip_out}")
    return zip_out.stat().st_size


def place_pack(zip_path: Path, zip_name: str) -> None:
    for dest in PACK_DEST_DIRS:
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / zip_name
        if target.exists():
            target.unlink()
        # hardlink not portable; just copy
        import shutil
        shutil.copyfile(zip_path, target)
        log(f"    placed -> {target}")


def read_source_build_time(src) -> str:
    """Best-effort lookup of the extended DB's build timestamp; falls back to
    the file's mtime if there is no `meta` table."""
    try:
        cur = src.execute("SELECT value FROM meta WHERE key = 'build_time' LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
    except sqlite3.OperationalError:
        pass
    return "unknown"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("language", help="greek or latin")
    ap.add_argument("--source-db", default=str(DEFAULT_SOURCE))
    ap.add_argument("--max-books", type=int, default=0,
                    help="dev only: limit to the first N books (0 = all)")
    ap.add_argument("--n", type=int, default=10, help="passage window size")
    ap.add_argument("--min-bag", type=int, default=8,
                    help="drop passages whose content-lemma bag is smaller")
    ap.add_argument("--lda-k-topics", type=int, default=1000)
    ap.add_argument("--lda-seed", type=int, default=0)
    ap.add_argument("--lda-seeds", type=int, nargs="+", default=None,
                    help="if set, average multiple seeds (concatenate topic blocks); "
                         "otherwise single seed from --lda-seed")
    ap.add_argument("--lda-iter", type=int, default=200)
    ap.add_argument("--tfidf-min-sim", type=float, default=0.15)
    ap.add_argument("--lda-min-sim", type=float, default=0.5)
    ap.add_argument("--exclude-scope", choices=["book", "work", "none"], default="work")
    ap.add_argument("--ivf-nprobe", type=int, default=10,
                    help="runtime IVF probe count (build-time default the reader respects)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()

    lang = args.language.lower()
    if lang not in LANGUAGE_REGISTRY:
        die(f"unknown language '{lang}'. Registered: {', '.join(sorted(LANGUAGE_REGISTRY))}")
    entry = LANGUAGE_REGISTRY[lang]

    source_db = Path(args.source_db)
    if not source_db.is_file():
        die(f"source database missing: {source_db}")

    out_dir = Path(args.out_dir) / lang
    if out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = args.lda_seeds if args.lda_seeds else [args.lda_seed]

    log(f"language={lang}  source={source_db.name}  N={args.n}  "
        f"max_books={args.max_books or 'all'}")
    log(f"  lda: K_topics={args.lda_k_topics} seeds={seeds} iter={args.lda_iter}")
    log(f"  cutoffs: tfidf_min_sim={args.tfidf_min_sim} lda_min_sim={args.lda_min_sim}")

    t_start = time.time()
    src = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    text_build_time = read_source_build_time(src)

    log(f"enumerating positions, parsing interlinear ({entry['parser']}) ...")
    positions, rowmeta, bags = enumerate_and_passage(
        src, entry["authors_language"], args.n, args.max_books,
        entry["translator"], PARSERS[entry["parser"]],
    )
    src.close()
    if not positions:
        die("no positions enumerated -- source DB or language filter wrong")
    if not any(bags):
        die("no passages have any content lemmas -- interlinear lookup is broken")

    log(f"vectorising ...")
    X_counts, X_tfidf, vocab, idf, n_dropped = vectorize(bags, args.min_bag)
    log(f"  vocab={len(vocab):,}  X.shape={X_tfidf.shape}  nnz={X_tfidf.nnz:,}  "
        f"dropped_tiny={n_dropped:,}")

    log("training LDA ...")
    if len(seeds) == 1:
        T = train_lda_tomotopy(bags, args.min_bag, vocab,
                               args.lda_k_topics, seeds[0], args.lda_iter)
    else:
        blocks = []
        for s in seeds:
            Ts = train_lda_tomotopy(bags, args.min_bag, vocab,
                                    args.lda_k_topics, s, args.lda_iter)
            blocks.append(Ts)
        T = np.concatenate(blocks, axis=1)
        T = normalize(T, norm="l2", axis=1, copy=False)
    log(f"  T.shape={T.shape}  dtype={T.dtype}")

    log("writing binary files ...")
    p_positions = out_dir / "positions.bin"
    sz_pos = write_positions(p_positions, positions)
    log(f"  positions.bin  {sz_pos/1e6:.1f} MB")

    book_id_to_idx = {bid: i for i, bid in enumerate(sorted({p[0] for p in positions}))}
    p_rowmeta = out_dir / "rowmeta.bin"
    sz_rm = write_rowmeta(p_rowmeta, rowmeta, book_id_to_idx)
    log(f"  rowmeta.bin    {sz_rm/1e6:.1f} MB")

    p_t = out_dir / "T.f16"
    sz_t = write_t_f16(p_t, T)
    log(f"  T.f16          {sz_t/1e6:.1f} MB ({T.shape[0]:,} x {T.shape[1]:,} f16)")

    p_ivf_c = out_dir / "ivf.centroids"
    p_ivf_l = out_dir / "ivf.lists"
    sz_ivfc, sz_ivfl, nlist = write_ivf(p_ivf_c, p_ivf_l, T, bags, args.min_bag,
                                        args.lda_seed)
    log(f"  ivf.centroids  {sz_ivfc/1e6:.1f} MB (nlist={nlist})")
    log(f"  ivf.lists      {sz_ivfl/1e6:.1f} MB")

    p_bags = out_dir / "bags.bin"
    sz_bags = write_bags(p_bags, X_counts)
    log(f"  bags.bin       {sz_bags/1e6:.1f} MB")

    p_invidx = out_dir / "invidx.bin"
    p_vocab = out_dir / "vocab.bin"
    sz_iv, sz_vb = write_invidx_and_vocab(p_invidx, p_vocab, X_tfidf, vocab, idf)
    log(f"  invidx.bin     {sz_iv/1e6:.1f} MB")
    log(f"  vocab.bin      {sz_vb/1e6:.1f} MB")

    # tomotopy version
    try:
        import tomotopy as tp
        tp_ver = tp.__version__
    except Exception:
        tp_ver = "unknown"
    import sklearn
    params = {
        "schema_version": 1,
        "lda_seeds": list(seeds),
        "lda_topics": args.lda_k_topics * (len(seeds)),  # effective stacked width
        "lda_iter": args.lda_iter,
        "vocab_size": len(vocab),
        "passage_count": T.shape[0],
        "min_bag": args.min_bag,
        "n": args.n,
        "tfidf_min_sim": args.tfidf_min_sim,
        "lda_min_sim": args.lda_min_sim,
        "exclude_scope": args.exclude_scope,
        "text_build_time": text_build_time,
        "sklearn_version": sklearn.__version__,
        "tomotopy_version": tp_ver,
        "ivf_nlist": nlist,
        "ivf_nprobe": args.ivf_nprobe,
    }
    manifest_path = write_manifest(
        out_dir, lang, params,
        ["positions.bin", "rowmeta.bin", "T.f16",
         "ivf.centroids", "ivf.lists",
         "bags.bin", "invidx.bin", "vocab.bin"],
    )
    log(f"  manifest.json  ({manifest_path.stat().st_size} bytes)")

    zip_name = f"{entry['db_file_stem']}.zip"
    # historical convention: app reads topical_<lang>.db.zip; keep that name so
    # the existing TopicalPackManager / debug-asset paths don't need to change.
    zip_name_compat = f"{entry['db_file_stem']}.db.zip"
    zip_out = out_dir.parent / zip_name_compat
    log(f"zipping -> {zip_out.name} ...")
    sz_zip = zip_dir(out_dir, zip_out)
    log(f"  zip            {sz_zip/1e6:.1f} MB")

    if not args.max_books:
        place_pack(zip_out, zip_name_compat)

    log(f"DONE in {(time.time() - t_start)/60:.1f} min")
    log(f"  stage dir : {out_dir}")
    log(f"  zip       : {zip_out}  ({sz_zip/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
