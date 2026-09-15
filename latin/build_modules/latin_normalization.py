#!/usr/bin/env python3
"""
Shared Latin orthographic normalisation.

Single source of truth for turning a Latin headword or surface form into the
plain-ASCII key used by `dictionary_entries.headword` and joined against
`lemma_map`. Imported by `load_lewis_short.py`, `load_whitakers_latin.py` and
`build_modules/interlinear/latin_dictionary_lookup.py` — two divergent copies is
how Latin lookup silently half-works.

Design constraints (see latin/LEWIS_SHORT_PLAN.md §5.2):

  * Strip vowel-quantity marks. 81% of L&S <orth> spellings carry a macron or
    breve; Latin corpus tokens and Whitaker's headwords are pure ASCII.
  * Strip editorial hyphens. 14,309 L&S spellings are hyphenated ("ab-jungo");
    the hyphen marks a morpheme boundary, not part of the word.
  * Fold j -> i. L&S writes "jungo"; the corpus writes "iungo" (986 spellings).
  * Do NOT fold v -> u. L&S, Whitaker's and the corpus all use v
    (5,880 / 3,249 / 319,015). Folding would strand all three.
  * Do NOT lowercase. Proper nouns are legitimately capitalised in both L&S and
    Whitaker's, and the app already retries lowercase for non-Greek languages.

Everything here is a CLOSED CHARACTER CLASS rule. There are no word lists and
none may be added — per CLAUDE.md, a rule that misses cases gets fixed, it does
not acquire an exception table. `assert_ascii_headwords()` is what keeps that
honest: a residue class the rules miss fails the build instead of being patched.
"""

import unicodedata
from typing import Iterable, Optional

# Combining marks that encode vowel quantity or editorial hiatus. Stripped
# wholesale after NFD decomposition, so precomposed and decomposed input behave
# identically.
_COMBINING_MACRON = "̄"
_COMBINING_BREVE = "̆"

# The SAME two quantity marks, written in Perseus's ASCII notation: a trailing
# "_" for a long vowel and "^" for a short one ("Ru_bria" = Rūbria, "A^dam" =
# Ădam). They are not combining characters, so NFD leaves them untouched and
# they survive into the headword.
#
# 1,314 L&S headwords carried "^" and 74 carried "_", and because both are
# ASCII, assert_ascii_headwords() waved them through. The words affected are not
# obscure -- Asia, Adam, Arabia, Aprilis, Adrastus, Adria -- and NONE had a
# clean duplicate row, so each was simply unreachable by lookup.
_ASCII_QUANTITY_MARKS = {"^", "_"}

# Editorial punctuation that reaches the headword from stray or malformed
# markup ("adc.", "ha!", "viden'?", "fa/scea", "="). A closed punctuation class.
# The APOSTROPHE is deliberately absent: it is real orthography in elided forms
# such as "'st", and must survive.
_EDITORIAL_PUNCT = {".", "!", "?", "/", "=", ",", ";", ":"}

# Ligatures Unicode does not decompose under NFKD. This is a ligature rule, not
# a vocabulary list: it enumerates a closed set of characters, not words.
_LIGATURES = {
    "œ": "oe",  # œ LATIN SMALL LIGATURE OE
    "Œ": "Oe",  # Œ LATIN CAPITAL LIGATURE OE
    "æ": "ae",  # æ LATIN SMALL LETTER AE
    "Æ": "Ae",  # Æ LATIN CAPITAL LETTER AE
}

# Confusable homoglyphs: characters from other scripts that occupy the place of
# a Latin letter. The L&S source carries 1,593 spellings with Cyrillic small u
# where Latin y belongs, presumably from a transliteration pass over Greek
# upsilon. Mapped to their Latin skeleton, in the spirit of UTS #39.
_HOMOGLYPHS = {
    "у": "y",  # у CYRILLIC SMALL LETTER U
    "У": "Y",  # У CYRILLIC CAPITAL LETTER U
    "а": "a",  # а CYRILLIC SMALL LETTER A
    "е": "e",  # е CYRILLIC SMALL LETTER IE
    "о": "o",  # о CYRILLIC SMALL LETTER O
    "р": "p",  # р CYRILLIC SMALL LETTER ER
    "с": "c",  # с CYRILLIC SMALL LETTER ES
    "х": "x",  # х CYRILLIC SMALL LETTER HA
    "ο": "o",  # ο GREEK SMALL LETTER OMICRON
    "Α": "A",  # Α GREEK CAPITAL LETTER ALPHA
    "Ο": "O",  # Ο GREEK CAPITAL LETTER OMICRON
}

# Editorial marks carrying no orthographic content.
_EDITORIAL = {
    "†",  # † DAGGER (obelus: word attested only in late/suspect sources)
    "‡",  # ‡ DOUBLE DAGGER
    "—",  # — EM DASH
    "–",  # – EN DASH
    "-",  # - HYPHEN-MINUS (morpheme boundary in L&S headwords)
    "­",  # SOFT HYPHEN
    "*",       # L&S marks unattested/reconstructed forms with a leading asterisk
}


def normalize_latin_headword(text: Optional[str]) -> str:
    """Normalise a Latin headword or surface form to its plain-ASCII lookup key.

    Idempotent: normalize(normalize(x)) == normalize(x).
    Returns "" for None/empty input so callers can skip uniformly.
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Expand ligatures before decomposition — NFKD leaves them intact.
    for lig, repl in _LIGATURES.items():
        if lig in s:
            s = s.replace(lig, repl)

    # 2. Decompose, then drop every combining mark. This covers macrons and
    #    breves (vowel quantity), diaereses (hiatus), grave/acute accents, and
    #    the stray combining marks in the source, in one pass.
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # 3. Map confusable homoglyphs to their Latin skeleton — AFTER decomposition,
    #    not before. The source's Cyrillic character is ў U+045E SHORT U (1,593
    #    spellings), which is only recognisable as bare у U+0443 once its breve
    #    has been stripped. Mapping before this step silently misses every one.
    for glyph, repl in _HOMOGLYPHS.items():
        if glyph in s:
            s = s.replace(glyph, repl)

    # 4. Drop editorial marks, the ASCII quantity marks and stray punctuation.
    #    Digits are dropped too: they only ever appear as sense-numbering debris
    #    ("1" as a whole headword), never as orthography.
    _DROP = _EDITORIAL | _ASCII_QUANTITY_MARKS | _EDITORIAL_PUNCT
    if any(ch in _DROP or ch.isdigit() for ch in s):
        s = "".join(ch for ch in s if ch not in _DROP and not ch.isdigit())

    # 5. Fold j -> i (both cases). Deliberately NOT v -> u; see module docstring.
    s = s.replace("j", "i").replace("J", "I")

    # 6. Recompose and collapse any whitespace introduced by mark removal.
    s = unicodedata.normalize("NFC", s)
    return " ".join(s.split())


def assert_ascii_headwords(headwords: Iterable[str], context: str) -> None:
    """Fail the build if normalisation left any non-ASCII residue.

    This is what makes the closed-class rules above safe: a character class the
    rules do not cover surfaces here as a hard failure, rather than being
    papered over with a per-word exception (CLAUDE.md: no word-specific fixes,
    no silent warnings for required components).
    """
    import collections

    # The test is "letters only", NOT "ASCII only". An ASCII-only check passed
    # 1,314 headwords carrying Perseus's "^" quantity mark straight through, and
    # every one of them was unreachable by lookup. A residue class is a residue
    # class whether or not it happens to fall inside ASCII.
    def _is_allowed(ch: str) -> bool:
        return ch.isalpha() or ch in " '"

    bad = [h for h in headwords if h and not all(_is_allowed(c) for c in h)]
    if not bad:
        return

    chars = collections.Counter(
        ch for h in bad for ch in h if not _is_allowed(ch)
    )
    detail = ", ".join(
        f"{ch!r} U+{ord(ch):04X} {unicodedata.name(ch, '?')} x{n}"
        for ch, n in chars.most_common(12)
    )
    raise ValueError(
        f"{context}: {len(bad)} normalised headwords contain non-letter "
        f"characters. "
        f"Residue: {detail}. Add the missing CHARACTER CLASS to "
        f"latin_normalization.py — never a per-word exception."
    )


# Two lemma spellings count as the same lexeme when they agree on a stem this
# long. Four is short enough to catch bellum/bellus (stem "bellu") and long
# enough to reject sum/edo and nox/nota.
_LEMMA_STEM_CHARS = 4


def lemmas_related(a, b):
    """True when two lemma spellings plainly name the same lexeme.

    The case this exists for: Whitaker files some nouns under a citation form
    that is not the one the treebank uses, because the citation-form picker
    takes the masculine nominative for a neuter noun. The noun *bellum* "war"
    is stored under the headword "bellus"; likewise aurum/aurus, vitium/vitius,
    praesidium/praesidius. Those are one word written two ways.

    A plain prefix test is not enough -- neither "bellum" nor "bellus" is a
    prefix of the other -- so this compares the shared stem instead, and still
    accepts a true prefix pair (uterque/uter, sum/sumo).

    NOT the same test as _related() in load_ldt_lemmas.py, which compares a
    Whitaker STEM against a lemma and can use a plain prefix. Deliberately kept
    separate: changing that one would change which treebank rows get inserted.
    """
    a = normalize_latin_headword(a or "").lower()
    b = normalize_latin_headword(b or "").lower()
    if not a or not b:
        return False
    if a.startswith(b) or b.startswith(a):
        return True
    shared = 0
    for x, y in zip(a, b):
        if x != y:
            break
        shared += 1
    return shared >= _LEMMA_STEM_CHARS


if __name__ == "__main__":
    # Self-check on the cases the plan calls out. Not a test suite; a smoke test
    # so a broken edit is obvious when the module is run directly.
    cases = [
        ("ăbălĭēnātĭo", "abalienatio"),
        ("ab-jungo", "abiungo"),
        ("Hispā-nĭa", "Hispania"),
        ("Trōĭa", "Troia"),
        ("Jūno", "Iuno"),
        ("volo", "volo"),          # v preserved
        ("Ăărōn", "Aaron"),        # capital preserved
        ("œconomia", "oeconomia"),
        ("†abaso", "abaso"),
        ("sуlva", "sylva"),   # Cyrillic u -> y
        ("A^dam", "Adam"),          # Perseus ASCII breve
        ("Ru_bria", "Rubria"),      # Perseus ASCII macron
        ("rē^trō-versus", "retroversus"),
        ("Ā^sĭus", "Asius"),
        ("adc.", "adc"),            # stray editorial full stop
        ("ha!", "ha"),
        ("'st", "'st"),             # elision apostrophe SURVIVES
    ]
    ok = True
    for raw, want in cases:
        got = normalize_latin_headword(raw)
        flag = "ok " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  {flag} {raw!r} -> {got!r} (want {want!r})")
        assert normalize_latin_headword(got) == got, f"not idempotent: {got!r}"
    print("idempotent: ok")
    print("ALL PASS" if ok else "FAILURES ABOVE")
