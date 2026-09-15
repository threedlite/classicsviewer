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


# Stanza is REQUIRED. LDT covers under 10% of tokens, so without Stanza every
# other token loses its "~ POS DEPREL HEAD sentPos sentId" block entirely.
#
# This used to be a warning, and the failure mode was ugly: a full run reported
# "Successful: 230, Failed: 0", exited 0, and finished in 20 seconds instead of
# an hour, having written 230 files with no POS data at all. The XML looked
# plausible and would have flowed into the DB, breaking the topical pack, the
# dependency-tree view and parse_interlinear_latin. Nothing failed loudly.
#
# The usual cause is invoking the generator with the system `python3` rather
# than the project venv, which is why the wrapper now checks too. Per CLAUDE.md,
# a required component that fails to load must fail the build, not warn.
try:
    import stanza  # type: ignore
    STANZA_AVAILABLE = True
except ImportError as _exc:
    raise ImportError(
        "Stanza is required for Latin interlinear generation but is not "
        "importable.\n"
        "Without it every token outside LDT coverage loses its POS, deprel "
        "and head fields, and the run still reports success.\n"
        "Run the generator with the project venv:\n"
        "  <repo>/venv/bin/python3 latin_interlinear_list.py ...\n"
        "or use run_latin_interlinear_no_sleep.sh, which now enforces this."
    ) from _exc


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
                    # HARD FAIL. Returning None here degrades every downstream
                    # gloss silently: the POS layer simply stops contributing
                    # and the run still "succeeds", producing a full set of
                    # XMLs with no Stanza tags in them. That is precisely the
                    # failure this build already shipped once, when the driver
                    # invoked bare `python3` and Stanza was not importable.
                    # CLAUDE.md: never use a warning for a critical component.
                    raise RuntimeError(
                        f"Stanza Latin pipeline ({_LA_PACKAGE}) failed to "
                        f"load: {e}\n"
                        f"The interlinear POS/lemma layer cannot run without "
                        f"it. Fetch the model with:\n"
                        f"  python3 -c \"import stanza; "
                        f"stanza.download('la', package='{_LA_PACKAGE}')\"\n"
                        f"Do NOT proceed without it -- the output would be "
                        f"silently degraded, not obviously broken."
                    ) from e
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
        # Reported, not raised: an offline machine with the model ALREADY
        # cached is a legitimate state, and the authoritative check is whether
        # the pipeline loads. get_stanza_nlp() raises if it does not, so a
        # genuinely missing model still fails the build -- one step later, and
        # on the condition that actually matters.
        print(f"NOTE: stanza.download('la', package={_LA_PACKAGE!r}) could not "
              f"refresh the model ({e}). Continuing only if it is already "
              f"cached; pipeline construction will fail hard if it is not.")
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
