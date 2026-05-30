#!/usr/bin/env python3
"""Build a topical-link database for the Classics Viewer "Topical Links" feature.

NEW APPROACH (Greek-internal, 2026-05-29). NO diodorus dependency: no torch /
sentence-transformers, no diodorus models, no diodorus venv. Runs in the project
./venv with scikit-learn (which pulls scipy + numpy).

For one language it:
  1. reads the assembled extended DB (READ-ONLY; never modified),
  2. enumerates every bookmark position (book_id, line_number, sequence_number),
     collapsing duplicate triples,
  3. groups each book's positions into fixed, non-overlapping N-position passages,
  4. builds a per-passage content-lemma bag from the interlinear stored in
     translation_segments (translator "Interlinear (Beta, …treebank)"), parsing
     the pipe format for (lemma, POS), keeping content POS only
     (NOUN/PROPN/VERB/ADJ), NFC-normalising lemmata, and dropping a small
     light-verb stoplist,
  5. TF-IDF-vectorises the passages and computes the top-K most cosine-similar
     passages by sparse chunked matmul, excluding same-work (default) neighbours,
  6. writes a standalone topical_<language>.db (+ .zip) into the output dir and
     copies the zip into the app asset locations (Android debug + main, iOS
     Resources); fails loudly if a destination is missing.

Usage:
    build_topical_links.py <language> [--max-books N] [--source-db PATH]
        [--n 10] [--k 50] [--min-sim X] [--exclude-scope book|work|none]
        [--chunk 256] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.preprocessing import normalize

HERE = Path(__file__).resolve().parent          # .../topical
REPO = HERE.parent                               # repo root
DEFAULT_SOURCE_DB = REPO / "data-prep" / "perseus_texts_extended.db"
DEFAULT_OUT_DIR = HERE / "dist"

# Where the built zip must be placed so the apps bundle it. Missing = fail loudly.
#  - topical_pack/src/main/assets/: source of truth for the on-demand Play asset
#    pack (release AAB).
#  - app/src/debug/assets/topical/: same files for local debug APK builds
#    (asset packs are AAB-only, so debug APKs need a copy in their own assets).
#  - ios/ClassicsViewer/Resources/: iOS bundle.
ANDROID_ASSET_DIRS = [
    REPO / "topical_pack" / "src" / "main" / "assets",
    REPO / "app" / "src" / "debug" / "assets" / "topical",
]
IOS_RESOURCES_DIR = REPO / "ios" / "ClassicsViewer" / "Resources"

# Single source of truth: language code -> {authors_language code, output db
# filename, interlinear translator to read, lemma parser to use}. No
# model_path: the embed step is now a language-internal lemma bag + TF-IDF,
# with no per-language model dependency.
LANGUAGE_REGISTRY = {
    "greek": {
        "authors_language": "greek",
        "db_file": "topical_greek.db",
        # Greek has Stanza-tagged treebank interlinear with explicit POS.
        "translator": "Interlinear (Beta, generated from app dictionary and treebank)",
        "parser": "greek",
    },
    "latin": {
        "authors_language": "latin",
        "db_file": "topical_latin.db",
        # Latin has only the AI-generated interlinear (no Stanza POS tags); the
        # lemma sits in the field immediately following each **gloss** block.
        "translator": "Interlinear (Beta, AI-generated from app dictionary)",
        "parser": "latin",
    },
}

# Greek interlinear has explicit POS; keep these (drop AUX/DET/PRON/ADP/…).
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ"}

# Corpus-ubiquitous lemmata that inflate cosine without carrying topical
# content. NFC-normalised at definition so byte-level membership matches the
# interlinear's lemmas (which we also NFC). For Greek these survive the POS
# filter; for Latin (no POS filter) they take the place of POS filtering.
LIGHT_LEMMATA = {
    unicodedata.normalize("NFC", w) for w in (
        # Greek light/function lemmata
        "εἰμί ἔχω λέγω ποιέω γίγνομαι φημί δύναμαι βούλομαι δοκέω οἶδα "
        "πολύς πᾶς αὐτός οὗτος ὅδε ἐκεῖνος τυγχάνω πάρειμι ὁράω "
        # Latin: prepositions, conjunctions, pronouns, light verbs, ubiquitous
        # adjectives / adverbs / particles. The Latin parser has no POS filter,
        # so this list bears more of the load (assisted by TfidfVectorizer's
        # max_df / min_df).
        "et sed atque ac neque nec ut ne si nisi cum dum quia quod quoniam "
        "quamquam quamvis "
        "in ex e ab a ad per pro sub super inter intra ante post propter "
        "sine apud circum contra erga "
        "ego tu is hic ille ipse idem qui quis quae quod qualis quantus tantus "
        "talis quidam aliquis nullus ullus uterque uter "
        "non haud nec aut vel sive an num quoque etiam autem enim igitur ergo "
        "iam tum tunc nunc semper saepe nondum adhuc "
        "sum habeo dico facio do ago fero possum debeo video volo nolo malo "
        "eo venio fio uolo "
        "magnus multus omnis alius alter primus secundus medius totus".split()
    )
}

SCHEMA_TABLES = """
CREATE TABLE bookmark_positions (
    position_id      INTEGER PRIMARY KEY NOT NULL,
    book_id          TEXT    NOT NULL,
    line_number      INTEGER NOT NULL,
    sequence_number  INTEGER NOT NULL,
    author_id        TEXT    NOT NULL,
    work_id          TEXT    NOT NULL,
    passage_id       INTEGER NOT NULL,
    UNIQUE (book_id, line_number, sequence_number)
);
CREATE TABLE topical_links (
    source_passage_id  INTEGER NOT NULL,
    target_passage_id  INTEGER NOT NULL,
    kind               TEXT    NOT NULL,   -- 'tfidf' | 'lda'
    rank               INTEGER NOT NULL,   -- 1 = best within its kind
    similarity         REAL    NOT NULL,
    PRIMARY KEY (source_passage_id, target_passage_id, kind)
);
CREATE TABLE meta (key TEXT PRIMARY KEY NOT NULL, value TEXT);
"""

SCHEMA_INDEXES = """
CREATE INDEX idx_bookmark_positions_lookup
    ON bookmark_positions (book_id, line_number, sequence_number);
CREATE INDEX idx_bookmark_positions_passage
    ON bookmark_positions (passage_id);
CREATE INDEX idx_bookmark_positions_work
    ON bookmark_positions (work_id);
CREATE INDEX idx_topical_links_source
    ON topical_links (source_passage_id, rank);
CREATE INDEX idx_topical_links_source_kind
    ON topical_links (source_passage_id, kind, rank);
"""


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Interlinear parsing
# --------------------------------------------------------------------------- #
def parse_interlinear_greek(text: str) -> list[str]:
    """Greek (treebank): tokens are ``| LEMMA MORPH ~[*] POS DEPREL HEAD … |``.
    Keep only content POS; NFC-normalise lemma; drop ``?`` / light lemmata."""
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
        if not lem or lem in ("?", "???", "-") or lem in LIGHT_LEMMATA:
            continue
        out.append(lem)
    return out


def parse_interlinear_latin(text: str) -> list[str]:
    """Latin (AI-generated): no explicit POS. The layout repeats per token:
    ``| surface | | **gloss** | | LEMMA MORPH … |``. We take the lemma as the
    first token of the field immediately following each ``**gloss**`` field.
    POS filtering is replaced by the (much larger) Latin LIGHT_LEMMATA stoplist
    plus TfidfVectorizer max_df/min_df."""
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
                if len(lem) >= 2 and lem.isalpha() and lem not in LIGHT_LEMMATA:
                    out.append(lem)
            next_is_lemma = False
    return out


PARSERS = {"greek": parse_interlinear_greek, "latin": parse_interlinear_latin}


# --------------------------------------------------------------------------- #
# Enumerate positions per book; build N-position passages and content-lemma bags
# --------------------------------------------------------------------------- #
def enumerate_positions_and_passages(src, out, lang_val, n, max_books,
                                     translator, parse_lemmas):
    """Per-book pass: stream positions (dedup duplicate triples), fetch the
    book's interlinear segments, slice positions into N-windows, distribute
    interlinear lemmata to each passage by its line range, and emit
    bookmark_positions rows.

    Returns (passage_bags, passage_book_ord, passage_work_ord, num_positions).
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

    passage_bags: list[list[str]] = []
    passage_book: list[int] = []
    passage_work: list[int] = []
    pos_batch: list[tuple] = []
    work_ords: dict[str, int] = {}

    position_id = 0
    passage_id = 0
    book_ord = -1
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
        book_ord += 1
        work_ord = work_ords.setdefault(work_id, len(work_ords))
        for start in range(0, len(positions), n):
            window = positions[start:start + n]
            pid = passage_id
            passage_id += 1
            min_ln = window[0][0]
            max_ln = window[-1][0]
            bag: list[str] = []
            for ln in range(min_ln, max_ln + 1):
                if ln in il:
                    bag.extend(il[ln])
            passage_bags.append(bag)
            passage_book.append(book_ord)
            passage_work.append(work_ord)
            for ln, seq in window:
                pos_batch.append(
                    (position_id, book_id, ln, seq, author_id, work_id, pid))
                position_id += 1

        if len(pos_batch) >= 10000:
            out.executemany(
                "INSERT INTO bookmark_positions VALUES (?,?,?,?,?,?,?)", pos_batch)
            pos_batch.clear()

        n_books_done += 1
        if n_books_done % 5000 == 0:
            log(f"  processed {n_books_done:,} books  positions={position_id:,}  "
                f"passages={passage_id:,}  elapsed={time.time()-t_books:.0f}s")

    if pos_batch:
        out.executemany(
            "INSERT INTO bookmark_positions VALUES (?,?,?,?,?,?,?)", pos_batch)
        pos_batch.clear()
    out.commit()
    if dup_skipped:
        log(f"  collapsed {dup_skipped} duplicate position triples (kept first)")
    return passage_bags, passage_book, passage_work, position_id


# --------------------------------------------------------------------------- #
# Vectorisation over content-lemma bags
#
# A single CountVectorizer feeds both stages so the corpus is tokenised once:
#   - X_tfidf : sparse L2-normalised TF-IDF matrix (for the lexical KNN)
#   - X_counts: sparse integer counts (input to LDA)
# Passages with fewer than ``min_bag`` content lemmata are treated as empty so
# their rows are zero in both matrices and they never source or target a link.
# --------------------------------------------------------------------------- #
def vectorize(passage_bags, min_bag):
    bags_eff = [b if len(b) >= min_bag else [] for b in passage_bags]
    cv = CountVectorizer(
        analyzer=lambda x: x,
        max_df=0.30, min_df=3, dtype=np.int32,
    )
    X_counts = cv.fit_transform(bags_eff)
    tfidf = TfidfTransformer(sublinear_tf=True)
    X_tfidf = tfidf.fit_transform(X_counts).astype(np.float32)
    X_tfidf = normalize(X_tfidf, norm="l2", axis=1, copy=False)
    n_dropped = sum(1 for b in passage_bags if len(b) < min_bag)
    return X_counts, X_tfidf, cv.get_feature_names_out().tolist(), n_dropped


def train_lda(X_counts, passage_bags, min_bag, k_topics, seed,
              lib="sklearn", vocab=None, iterations=10):
    """Train LDA via `lib` (sklearn or tomotopy) and return an L2-normalised
    topic matrix (P x K) suitable for cosine KNN. Rows for tiny bags are
    explicitly zeroed so they are inert in the nearest-neighbour pass."""
    if lib == "sklearn":
        log(f"  training LDA via sklearn K_topics={k_topics} seed={seed} ...")
        t0 = time.time()
        lda = LatentDirichletAllocation(
            n_components=k_topics,
            learning_method="online",
            batch_size=2048,
            max_iter=iterations,
            random_state=seed,
            n_jobs=-1,
            verbose=0,
        )
        T = lda.fit_transform(X_counts).astype(np.float32)
    elif lib == "tomotopy":
        import tomotopy as tp
        if vocab is None:
            die("tomotopy backend requires vocab list (CountVectorizer features)")
        log(f"  training LDA via tomotopy K_topics={k_topics} seed={seed} "
            f"iter={iterations} ...")
        t0 = time.time()
        vocab_set = set(vocab)
        mdl = tp.LDAModel(k=k_topics, alpha=50.0 / k_topics, eta=0.01, seed=seed)
        # added[i] = True if passage_bags[i] was given to tomotopy, in order.
        # tomotopy's mdl.docs[int] indexing is unreliable in 0.14; iterate instead.
        added: list[bool] = []
        for bag in passage_bags:
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
        log(f"    added {n_added:,} docs of {len(passage_bags):,}; "
            f"corpus build in {time.time()-t0:.1f}s")
        t1 = time.time()
        mdl.train(iterations, workers=0)  # 0 = use all available cores
        log(f"    Gibbs sampling: {iterations} iter in "
            f"{(time.time()-t1)/60:.1f} min  "
            f"log-likelihood={mdl.ll_per_word:.4f}")
        T = np.zeros((len(passage_bags), k_topics), dtype=np.float32)
        doc_iter = iter(mdl.docs)
        for i, was_added in enumerate(added):
            if not was_added:
                continue
            T[i] = next(doc_iter).get_topic_dist()
    else:
        die(f"unknown LDA library: {lib}")
    sizes = np.fromiter((len(b) for b in passage_bags), dtype=np.int32,
                        count=len(passage_bags))
    T[sizes < min_bag] = 0.0
    T = normalize(T, norm="l2", axis=1, copy=False)
    log(f"  LDA trained+transformed in {(time.time()-t0)/60:.1f} min; "
        f"T.shape={T.shape}")
    return T


# --------------------------------------------------------------------------- #
# Top-K nearest neighbours via chunked cosine — accepts sparse (TF-IDF) or
# dense (LDA topic) matrices and writes rows tagged with `kind`.
# --------------------------------------------------------------------------- #
def compute_and_write_links(out, X, passage_book, passage_work, k,
                            exclude_scope, min_sim, chunk, kind):
    P = X.shape[0]
    if P < 2:
        log(f"  [{kind}] fewer than 2 passages; no links")
        return 0
    if exclude_scope == "work":
        groups = np.asarray(passage_work, dtype=np.int32)
    elif exclude_scope == "book":
        groups = np.asarray(passage_book, dtype=np.int32)
    else:
        groups = None

    is_sparse = sp.issparse(X)
    if is_sparse:
        XT = X.T.tocsr()
    buf: list[tuple] = []
    total = 0
    t0 = time.time()
    k_eff = min(k, P)

    for i in range(0, P, chunk):
        Q = X[i:i + chunk]
        if is_sparse:
            sims = (Q @ XT).toarray()
        else:
            sims = Q @ X.T              # dense matmul
        if groups is not None:
            cb = groups[i:i + chunk]
            mask = cb[:, None] == groups[None, :]
            sims[mask] = -1.0
        else:
            rows = np.arange(Q.shape[0])
            sims[rows, i + rows] = -1.0
        if k_eff < P:
            part = np.argpartition(-sims, kth=k_eff - 1, axis=1)[:, :k_eff]
        else:
            part = np.tile(np.arange(P), (Q.shape[0], 1))
        for r in range(Q.shape[0]):
            src = i + r
            row_idx = part[r]
            row_sims = sims[r, row_idx]
            order = np.argsort(-row_sims)
            row_idx = row_idx[order]
            row_sims = row_sims[order]
            rank = 0
            for ti, ts in zip(row_idx, row_sims):
                ts = float(ts)
                if ts <= 0.0:
                    break
                if min_sim is not None and ts < min_sim:
                    break
                rank += 1
                buf.append((src, int(ti), kind, rank, ts))
                if rank >= k:
                    break
        if len(buf) >= 200000:
            out.executemany(
                "INSERT OR IGNORE INTO topical_links VALUES (?,?,?,?,?)", buf)
            total += len(buf)
            buf.clear()
        done = min(i + chunk, P)
        if (i // chunk) % 25 == 0 or done == P:
            rate = done / max(time.time() - t0, 1e-6)
            log(f"  {kind}-knn {done}/{P} ({rate:.1f} src/s)")
    if buf:
        out.executemany(
            "INSERT OR IGNORE INTO topical_links VALUES (?,?,?,?,?)", buf)
        total += len(buf)
        buf.clear()
    out.commit()
    return total


# --------------------------------------------------------------------------- #
# Asset placement + source-db build-time meta
# --------------------------------------------------------------------------- #
def place_in_app_assets(zip_path: Path, zip_name: str) -> None:
    """Copy the built zip into the app asset locations (Android debug + main,
    iOS Resources). Fail loudly if any destination directory is missing."""
    dests = ANDROID_ASSET_DIRS + [IOS_RESOURCES_DIR]
    # topical_pack/src/main/assets/ and app/src/debug/assets/topical/ are
    # gitignored and may not exist on a fresh clone; create them.
    for d in dests:
        d.mkdir(parents=True, exist_ok=True)
    for d in dests:
        shutil.copy2(zip_path, d / zip_name)
        log(f"  placed -> {d / zip_name}")


def read_source_build_time(src) -> str:
    try:
        row = src.execute(
            "SELECT entry_xml FROM dictionary_entries "
            "WHERE source = 'database_build_metadata' AND headword = 'build_time' "
            "LIMIT 1"
        ).fetchone()
        return row[0] if row else ""
    except sqlite3.Error:
        return ""


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build a topical-link database (Greek/Latin-internal: "
                    "TF-IDF over interlinear content lemmas).")
    ap.add_argument("language", help="registered language, e.g. greek or latin")
    ap.add_argument("--source-db", default=str(DEFAULT_SOURCE_DB))
    ap.add_argument("--max-books", type=int, default=0,
                    help="dev only: limit to the first N books (0 = all)")
    ap.add_argument("--n", type=int, default=10, help="passage window size")
    ap.add_argument("--exclude-scope", choices=["book", "work", "none"],
                    default="work")
    ap.add_argument("--chunk", type=int, default=256,
                    help="KNN chunk size (Q rows per matmul)")
    ap.add_argument("--min-bag", type=int, default=8,
                    help="drop passages whose content-lemma bag is smaller than "
                         "this from BOTH KNN passes (typically book headers / "
                         "tiny scholia fragments)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))

    # TF-IDF KNN params
    ap.add_argument("--tfidf-k", type=int, default=50,
                    help="links stored per passage from the TF-IDF KNN")
    ap.add_argument("--tfidf-min-sim", type=float, default=0.15,
                    help="cosine floor for TF-IDF links (default: 0.15)")

    # LDA KNN params
    ap.add_argument("--no-lda", action="store_true",
                    help="skip the LDA stage (TF-IDF only)")
    ap.add_argument("--lda-k", type=int, default=30,
                    help="links stored per passage from the LDA KNN")
    ap.add_argument("--lda-k-topics", type=int, default=200,
                    help="number of LDA topics")
    ap.add_argument("--lda-min-sim", type=float, default=0.5,
                    help="cosine floor for LDA links (default: 0.5)")
    ap.add_argument("--lda-seed", type=int, default=0,
                    help="random seed for LDA training")
    ap.add_argument("--lda-lib", choices=["sklearn", "tomotopy"],
                    default="sklearn",
                    help="LDA library backend (tomotopy is much faster at K>=500)")
    ap.add_argument("--lda-iter", type=int, default=10,
                    help="LDA iterations (sklearn max_iter / tomotopy gibbs iter)")

    args = ap.parse_args()

    lang = args.language.lower()
    if lang not in LANGUAGE_REGISTRY:
        die(f"unknown language '{lang}'. Registered: "
            f"{', '.join(sorted(LANGUAGE_REGISTRY))}")
    entry = LANGUAGE_REGISTRY[lang]

    source_db = Path(args.source_db)
    if not source_db.is_file():
        die(f"source database missing: {source_db}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_db = out_dir / entry["db_file"]
    if out_db.exists():
        out_db.unlink()

    log(f"language={lang}  source={source_db.name}  N={args.n}  "
        f"exclude={args.exclude_scope}  max_books={args.max_books or 'all'}")
    log(f"  tfidf: k={args.tfidf_k} min_sim={args.tfidf_min_sim}")
    if args.no_lda:
        log("  lda  : DISABLED (--no-lda)")
    else:
        log(f"  lda  : k={args.lda_k} K_topics={args.lda_k_topics} "
            f"min_sim={args.lda_min_sim} seed={args.lda_seed}")

    t_start = time.time()
    src = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    build_time = read_source_build_time(src)

    out = sqlite3.connect(str(out_db))
    out.execute("PRAGMA journal_mode = OFF")
    out.execute("PRAGMA synchronous = OFF")
    out.execute("PRAGMA temp_store = MEMORY")
    out.executescript(SCHEMA_TABLES)

    log(f"enumerating positions, forming passages, parsing interlinear lemmas "
        f"({entry['parser']} parser) ...")
    bags, p_book, p_work, num_pos = enumerate_positions_and_passages(
        src, out, entry["authors_language"], args.n, args.max_books,
        entry["translator"], PARSERS[entry["parser"]])
    num_passages = len(bags)
    nonempty = sum(1 for b in bags if b)
    log(f"  positions={num_pos:,}  passages={num_passages:,}  "
        f"non-empty bags={nonempty:,}")
    if num_passages == 0:
        die("no passages produced")
    if nonempty == 0:
        die("no passages have any content lemmas -- interlinear lookup is broken")

    log(f"vectorising (counts + TF-IDF over content lemmas, "
        f"min_bag={args.min_bag}) ...")
    X_counts, X_tfidf, vocab, n_dropped = vectorize(bags, args.min_bag)
    log(f"  vocab={len(vocab):,}  X.shape={X_tfidf.shape}  nnz={X_tfidf.nnz:,}  "
        f"density={X_tfidf.nnz/(X_tfidf.shape[0]*max(X_tfidf.shape[1],1)):.4f}  "
        f"dropped_tiny_passages={n_dropped:,}")

    log("computing TF-IDF nearest neighbours (sparse chunked cosine) ...")
    num_links_tfidf = compute_and_write_links(
        out, X_tfidf, p_book, p_work, args.tfidf_k, args.exclude_scope,
        args.tfidf_min_sim, args.chunk, kind="tfidf")
    log(f"  tfidf links written={num_links_tfidf:,}")

    num_links_lda = 0
    if not args.no_lda:
        T = train_lda(X_counts, bags, args.min_bag,
                      args.lda_k_topics, args.lda_seed,
                      lib=args.lda_lib, vocab=vocab,
                      iterations=args.lda_iter)
        log("computing LDA nearest neighbours (dense chunked cosine) ...")
        num_links_lda = compute_and_write_links(
            out, T, p_book, p_work, args.lda_k, args.exclude_scope,
            args.lda_min_sim, args.chunk, kind="lda")
        log(f"  lda links written={num_links_lda:,}")

    num_links = num_links_tfidf + num_links_lda
    log(f"  total links written={num_links:,} "
        f"(tfidf={num_links_tfidf:,} lda={num_links_lda:,})")

    log("creating indexes ...")
    out.executescript(SCHEMA_INDEXES)

    meta = {
        "language": lang,
        "authors_language": entry["authors_language"],
        "source_db": source_db.name,
        "source_build_time": build_time,
        "window_n": str(args.n),
        "exclude_scope": args.exclude_scope,
        "approach": "tfidf+lda-content-lemma-greek-internal",
        "interlinear_translator": entry["translator"],
        "interlinear_parser": entry["parser"],
        "vocab_size": str(len(vocab)),
        "min_bag": str(args.min_bag),
        "dropped_tiny_passages": str(n_dropped),
        "num_positions": str(num_pos),
        "num_passages": str(num_passages),
        "num_links": str(num_links),
        "num_links_tfidf": str(num_links_tfidf),
        "num_links_lda": str(num_links_lda),
        "tfidf_k": str(args.tfidf_k),
        "tfidf_min_sim": str(args.tfidf_min_sim),
        "lda_enabled": "0" if args.no_lda else "1",
        "lda_k": str(args.lda_k),
        "lda_k_topics": str(args.lda_k_topics),
        "lda_min_sim": str(args.lda_min_sim),
        "lda_seed": str(args.lda_seed),
        "max_books": str(args.max_books),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out.executemany("INSERT INTO meta VALUES (?,?)", list(meta.items()))
    out.commit()
    out.execute("ANALYZE")
    out.commit()
    out.close()
    src.close()

    db_bytes = out_db.stat().st_size
    zip_path = out_dir / (entry["db_file"] + ".zip")
    log(f"compressing {out_db.name} ({db_bytes/1e6:.1f} MB) -> "
        f"{zip_path.name} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(out_db, arcname=entry["db_file"])
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:
            die("zip integrity check failed")
    zip_bytes = zip_path.stat().st_size

    if args.max_books:
        log(f"  (dev slice: --max-books={args.max_books}; NOT placing into app assets)")
    else:
        place_in_app_assets(zip_path, entry["db_file"] + ".zip")

    log(f"DONE in {(time.time() - t_start)/60:.1f} min")
    log(f"  db : {out_db}  ({db_bytes/1e6:.1f} MB)")
    log(f"  zip: {zip_path}  ({zip_bytes/1e6:.1f} MB)")
    if not args.max_books:
        log("  placed into app assets (Android debug + main, iOS Resources)")


if __name__ == "__main__":
    main()
