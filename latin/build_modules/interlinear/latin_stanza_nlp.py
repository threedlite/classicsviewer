#!/usr/bin/env python3
"""
Thread-safe lazy singleton around `stanza.Pipeline('la', package='proiel', ...)`.

Mirrors the pattern in `sanskrit/generate_sanskrit_interlinear.py`. Each
multiprocessing worker process owns its own Stanza pipeline (post-fork
globals are independent); the lock + check-twice pattern guards against
concurrent first-time loads within a single worker.

`get_stanza_nlp()` returns the loaded pipeline, or None if Stanza is not
available. After the first successful call subsequent calls are
lock-free.

Punctuation handling: the build_topical / interlinear caller is expected
to **pre-strip surface punctuation** before passing text in. Classical
Latin lacks consistent whitespace before commas/periods, which makes
Stanza's tokenizer fuse "cano," into a single token tagged NOUN instead
of `cano` (VERB) + `,` (PUNCT). Pre-stripping at the caller side avoids
this and is also faster.
"""

from __future__ import annotations

import threading


# Stanza is *required* for full Latin POS coverage (LDT covers <10% of
# tokens in v1). If it isn't installed the generator's --strict mode
# should fail; non-strict mode emits interlinear without POS tags.
try:
    import stanza  # type: ignore
    STANZA_AVAILABLE = True
except ImportError:
    print("WARNING: Stanza not installed. Latin interlinear will be missing "
          "POS / dependency tags for all tokens outside LDT coverage.")
    STANZA_AVAILABLE = False


# Per-process singleton state. After multiprocessing fork these are reset
# to the child's own globals (None / False); each worker initialises its
# own pipeline lazily.
_stanza_nlp = None
_stanza_lock = threading.Lock()
_stanza_initialized = False

# Package selection: PROIEL has the broadest Latin coverage (NT Vulgate +
# classical authors via the original Pragmatic Resources for Indo-European
# Languages project). Other options:
#   - 'perseus': same data as LDT (not useful as a fallback for LDT)
#   - 'ittb': Aquinas (wrong register for our canon)
#   - 'llct': Late Latin charters (wrong register)
#   - 'udante': Dante's Latin works (wrong register)
_LA_PACKAGE = "proiel"


def get_stanza_nlp():
    """Get or create the Stanza Latin pipeline (singleton per process).
    Thread-safe within a process. Returns None if Stanza is not installed
    or model loading fails."""
    global _stanza_nlp, _stanza_initialized

    if not STANZA_AVAILABLE:
        return None

    if _stanza_nlp is None and not _stanza_initialized:
        with _stanza_lock:
            if _stanza_nlp is None and not _stanza_initialized:
                try:
                    # download_method=None means "don't try to fetch the
                    # model on the fly during pipeline construction" — this
                    # avoids a race when many worker processes all try to
                    # download the same model into the same cache dir.
                    # The model must already be present (run
                    # `stanza.download('la', package='proiel')` once before
                    # any worker starts).
                    # tokenize_pretokenized=True: the caller passes a list of
                    # token strings (one inner list per sentence). Stanza skips
                    # its own tokenizer entirely, which matters because Latin
                    # has no consistent whitespace before commas/periods —
                    # letting Stanza tokenize would fuse "cano," into one
                    # token tagged NOUN instead of `cano` (VERB) + `,` (PUNCT).
                    _stanza_nlp = stanza.Pipeline(
                        "la",
                        package=_LA_PACKAGE,
                        processors="tokenize,pos,lemma,depparse",
                        tokenize_pretokenized=True,
                        verbose=False,
                        download_method=None,
                    )
                except Exception as e:
                    print(f"WARNING: Failed to load Stanza Latin pipeline: {e}")
                _stanza_initialized = True

    return _stanza_nlp


def ensure_model_downloaded() -> bool:
    """Pre-download the Stanza Latin model. Call this once from the build
    driver before forking multiprocessing workers — avoids the download
    race and surfaces network failures before the parallel phase. Returns
    True on success."""
    if not STANZA_AVAILABLE:
        return False
    try:
        stanza.download("la", package=_LA_PACKAGE, verbose=False)
        return True
    except Exception as e:
        print(f"WARNING: stanza.download('la', package={_LA_PACKAGE!r}) failed: {e}")
        return False


if __name__ == "__main__":
    # Smoke: download (no-op if cached), load, parse one sentence.
    if not ensure_model_downloaded():
        raise SystemExit(1)
    nlp = get_stanza_nlp()
    if nlp is None:
        raise SystemExit(1)
    doc = nlp("Arma virumque cano Troiae qui primus ab oris Italiam venit.")
    for sent in doc.sentences:
        for w in sent.words:
            print(f"  {w.text:14}  lemma={w.lemma or '?':14}  "
                  f"upos={w.upos or '?':6}  head={w.head}  "
                  f"deprel={w.deprel or '?'}")
