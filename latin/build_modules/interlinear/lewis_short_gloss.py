#!/usr/bin/env python3
"""
Extract a short interlinear gloss from a rendered Lewis & Short article.

`extract_gloss()` in latin_dictionary_lookup.py is built for Whitaker's terse
"(n.) shore, coast;" shape and produces nonsense from an L&S article — it cuts
at the first comma, which for L&S is usually inside the headword line or a
citation.

The hard part is that L&S's first sense is frequently NOT a definition. It
routinely opens with orthographic or morphological apparatus:

    deus  ->  "I. voc. sing. deus, Vulg. Psa. 22, 3 al. ; but, dee, Tert. ..."
    audio ->  "I. imperf. audibat, Ov F. 3, 507: audibant. Cat. 84, 8 ; ..."

whereas other entries lead with a clean definition:

    ora   ->  "I. the extremity of a thing; the border, brim, edge, ..."
    iacto ->  "I. to throw, cast, hurl."

What separates them is measurable and needs no vocabulary list: **apparatus is
dense in citation numerals, definitions are not.** So candidate lines are scored
on digit density and alphabetic content, and the first line that reads as prose
wins. This is a class rule — it does not know or care which word it is looking
at, per CLAUDE.md's prohibition on word-specific fixes.
"""

import re
import unicodedata
from typing import Optional

# A sense line is rejected as apparatus if more than this share of its
# characters are digits. Citation runs ("Ov. F. 3, 507; Cat. 84, 8") sit well
# above it; running prose sits far below.
_MAX_DIGIT_RATIO = 0.045

# Minimum letters for a line to count as a definition at all.
_MIN_LETTERS = 12

# Longest gloss we will emit. The interlinear shows this under each word, so it
# has to stay short; Whitaker's own glosses average well under this.
try:
    from .latin_dictionary_lookup import first_sense, balance_brackets
except ImportError:  # direct execution (testing)
    from latin_dictionary_lookup import first_sense, balance_brackets

_MAX_GLOSS_CHARS = 60

# Leading sense label: "I. ", "A. ", "1. ", "a. " etc., possibly indented.
_LABEL_RE = re.compile(r"^\s*(?:[IVXLC]+|[A-Za-z]|\d+)\s*\.\s*")

# A parenthetical or bracketed aside, dropped wholesale.
_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")

# Citation tail: a capitalised abbreviation followed by numbers, to end of line.
_CITATION_RE = re.compile(r"[,;:]?\s*\b[A-Z][A-Za-z]{0,9}\.\s*[A-Z]?[a-z]*\.?\s*\d.*$")


# Apparatus is dense in abbreviations ("imperf.", "perf. mansti", "Lucil. ap.",
# "v. n."); running prose is not. Counting abbreviation-shaped tokens is a
# structural test, not a vocabulary one — it never asks WHICH abbreviation.
_ABBREV_RE = re.compile(r"\b[A-Za-z]{1,6}\.")
_MAX_ABBREVS = 1


# ---------------------------------------------------------------------------
# L&S rubrics
# ---------------------------------------------------------------------------
# Beneath its sense numbering L&S carries a second layer of structural labels.
# They are typographically part of the sense line, so they arrive glued to the
# front of the definition -- or, worse, standing alone where no definition
# follows:
#
#   "In gen., that is above , upper , higher"   <- label + real definition
#   "Lit. , to make one thing like another"     <- label + real definition
#   "Special combinations"                      <- label, nothing follows
#   "Of living objects"                         <- scope note, nothing follows
#   "With atque or et"                          <- scope note, nothing follows
#
# Measured over all 76,119 headwords, 8.4% of the glosses produced were one of
# these rather than a meaning. Most of that 8.4% is the first kind, where a
# usable definition sits directly behind the label, so stripping recovers them
# instead of discarding them.
#
# TWO kinds, handled differently:
#
# 1. LABELS ("In gen.", "Lit.", "Transf.") -- fixed abbreviations from the
#    dictionary's own markup vocabulary. Stripped outright, repeatedly, since
#    they nest ("Lit. Trop. ...").
#
# 2. SCOPE NOTES ("Of living objects", "With in and acc") -- these state WHERE a
#    sense applies, never what it means. They cannot be stripped blindly,
#    because a genuine definition may also open with "of":
#
#        "of or belonging to a garden , garden"      <- a real gloss
#        "Of living objects"                         <- a rubric
#
#    What separates them is L&S's own typography: it CAPITALISES a rubric and
#    lowercases running definition text. So a capitalised leading "Of"/"With"
#    marks a scope note. Its extent is the run up to the first comma; if a
#    definition follows that comma we keep it ("Of time, nearer , later"), and
#    if nothing follows, the line carried no meaning and we decline.
#
# Both rules key on the dictionary's markup conventions -- a closed set of its
# own labels, and its capitalisation practice. Neither inspects which word is
# being looked up, per CLAUDE.md's ban on word-specific fixes.

# Kind 1: sense-qualifier labels, stripped wholesale.
#
# The second group is GRAMMATICAL tagging -- gender, number, case, tense. L&S
# puts it in front of a sense the same way it puts "In gen." there, and the same
# strip-then-retest handles it, because the two shapes separate themselves:
#
#   "Masc. , a river in Germany , now the Ems"  -> "a river in Germany..."  KEEP
#   "gen. Archimedi"                            -> "Archimedi"    too short, DROP
#
# So no extra rule is needed to tell an informative tag from a bare cited form:
# stripping the tag leaves a definition in the first case and a lone Latin word
# in the second, and _MIN_LETTERS already rejects the latter. POS tags (adj.,
# adv., subst.) are in the same list for the same reason -- "adj., of or
# belonging to Liber" keeps its definition and passes.
_RUBRIC_LABEL_RE = re.compile(
    r"^\s*(?:"
    r"In\s+gen\.|In\s+partic\.|Esp\.|Absol\.|Lit\.|Trop\.|Transf\.|"
    r"Meton\.|Poet\.|Hence|Neutr\.|Act\.|Pass\.|Impers\.|Adv\.|Subst\.|"
    # Gender / number / part-of-speech. These QUALIFY A SENSE, so a definition
    # follows and stripping them exposes it.
    r"masc\.|fem\.|neut\.|neutr\.|sing\.|plur\.|pl\.|"
    r"adj\.|interj\.|conj\.|prep\.|pron\.|num\.|dim\."
    r")\s*[,.;:]?\s*",
    re.I,
)

# Case and tense tags are different in kind, and must NOT be stripped.
#
# A gender or POS tag qualifies a sense: "Masc. , a river in Germany" has a
# definition behind it. A case or tense tag announces a cited FORM, and what
# follows is Latin, not English:
#
#   "gen. magnai for magnae"   <- a variant genitive of magnus
#   "gen. Archimedi"           <- a genitive
#   "voc. sing. deus, Vulg."   <- a vocative
#
# Stripping these leaves Latin word-forms that read as though they were a
# definition -- "magnai for magnae" as the gloss for magnus, which is worse than
# declining. So the whole line is rejected and the next one is tried; for
# magnus that yields "of physical size or quantity, great, large".
_FORM_TAG_RE = re.compile(
    r"^\s*(?:gen|dat|acc|abl|voc|nom|perf|imperf|fut|praes|inf|part|sup|"
    r"comp|superl|collat|contr)\b\.?",
    re.I,
)

# Kind 2: capitalised scope note. Capitalisation is the discriminator; the flag
# is deliberately NOT re.I.
# "In" is deliberately NOT in this list. "In gen." / "In partic." are already
# removed by _RUBRIC_LABEL_RE above, and every remaining capitalised "In ..."
# tested as content, not scope ("In poets sometimes a goddess"). Including it
# changed the yield by 22 headwords in 76,143 (0.03%) while silently eating
# those lines, so the conservative reading wins.
_RUBRIC_SCOPE_RE = re.compile(r"^(?:Of|With)\b[^,]*")

# A line that is nothing but a structural announcement.
_RUBRIC_BARE_RE = re.compile(
    r"^\s*(?:Special\s+combinations?|In\s+gen|In\s+partic|Absol|Hence)\s*\.?\s*$",
    re.I,
)


def _strip_rubrics(s: str) -> str:
    """Remove L&S structural labels, returning the definition text behind them.

    Returns "" when the line was a rubric with no definition following it --
    the caller then moves to the next line rather than emitting the rubric.
    """
    if _RUBRIC_BARE_RE.match(s):
        return ""

    # A cited inflected form, not a sense. Reject the line outright.
    if _FORM_TAG_RE.match(s):
        return ""

    # Kind 1, repeatedly: labels nest.
    prev = None
    while prev != s:
        prev = s
        s = _RUBRIC_LABEL_RE.sub("", s, count=1)
    s = s.strip()

    if _RUBRIC_BARE_RE.match(s):
        return ""

    # Kind 2: a capitalised scope note consumes text up to the first comma.
    m = _RUBRIC_SCOPE_RE.match(s)
    if m:
        rest = s[m.end():].lstrip(" ,;:")
        # No comma -> the scope note WAS the whole line; it states no meaning.
        return rest.strip()

    return s.strip()


# L&S prints Latin in its typographic form, with vowel-quantity marks; its
# English definitions carry none. So a candidate line whose FIRST word is
# macronised is quoting a Latin form, not defining the headword -- almost always
# a derived word introduced under the entry:
#
#     Asia     ->  "Ā^sĭus , a, um , adj. , Asiatic"       (defines Asius)
#     Abraham  ->  "Abrāhămĭdes , ae , m. , a descendant"  (defines Abrahamides)
#     hic      ->  "More emphatic, in the original full form, hīce , haece"
#
# Anchored to the first word deliberately. A macron deeper in the line is
# usually a proper noun inside a genuine definition, which must be kept:
#
#     Aeginium ->  "a fortress in Thessaly , now Stagūs"   (good, kept)
#
# Measured: 2.26% of produced glosses contain a macron anywhere; restricting to
# the leading word is what separates the paradigm lines from the real ones.
_QUANTITY_MARKS = ("\u0304", "\u0306")  # combining macron, combining breve


def _leads_with_latin(s: str) -> bool:
    """True if the first word carries vowel-quantity marks (a quoted Latin form)."""
    first = s.strip().split(" ", 1)[0] if s.strip() else ""
    if not first:
        return False
    decomposed = unicodedata.normalize("NFD", first)
    return any(m in decomposed for m in _QUANTITY_MARKS)


def _abbrev_count(s: str) -> int:
    return len(_ABBREV_RE.findall(s))


def _digit_ratio(s: str) -> float:
    if not s:
        return 1.0
    return sum(c.isdigit() for c in s) / len(s)


def _clean_line(line: str) -> str:
    """Strip the sense label, parentheticals and any trailing citation run."""
    s = _LABEL_RE.sub("", line)
    s = _PAREN_RE.sub(" ", s)
    s = _CITATION_RE.sub("", s)
    # Definitions are frequently followed by ": <Latin example>". Cut there.
    if ":" in s:
        s = s.split(":", 1)[0]
    return " ".join(s.split())


def _trim(s: str) -> str:
    """Cut to the first sense group, then to length, on a word boundary."""
    # L&S separates near-synonyms with commas and distinct senses with
    # semicolons. Keep the first semicolon group — that is one sense. The split
    # is bracket-aware (shared with the Whitaker path) because L&S also puts
    # semicolons inside parenthetical examples, and cutting there leaves an
    # unterminated quotation presented as a definition.
    s = first_sense(s, ";")
    s = s.strip(" ,.;:—-")
    if len(s) <= _MAX_GLOSS_CHARS:
        return balance_brackets(s)
    cut = s[:_MAX_GLOSS_CHARS]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return balance_brackets(cut.rstrip(" ,.;:")) + "…"


def extract_ls_gloss(entry_plain: Optional[str]) -> Optional[str]:
    """Return a short gloss, or None if the article yields nothing usable.

    Returning None is a legitimate outcome — the caller falls back rather than
    printing apparatus. Never invent a gloss.
    """
    if not entry_plain:
        return None

    lines = entry_plain.split("\n")
    # Line 0 is the orthography line emitted by the loader; never a definition.
    for line in lines[1:]:
        if not line.strip():
            continue
        candidate = _clean_line(line)
        # Drop L&S's structural labels. An empty result means the line was a
        # rubric with no definition behind it -- fall through to the next line
        # rather than printing "Special combinations" as a meaning.
        candidate = _strip_rubrics(candidate)
        if len(re.sub(r"[^A-Za-z]", "", candidate)) < _MIN_LETTERS:
            continue
        if _digit_ratio(candidate) > _MAX_DIGIT_RATIO:
            continue
        # Abbreviation-dense lines are apparatus or citation runs, never
        # definitions. Declining here is deliberate: the caller falls back, and
        # a "???" is better for the reader than "imperf. audibat, Ov".
        if _abbrev_count(candidate) > _MAX_ABBREVS:
            continue
        # Opens by quoting a Latin form -> this line introduces a DIFFERENT word.
        if _leads_with_latin(candidate):
            continue
        # A cross-reference stub ("v. 1. Tros, B. 2.") carries no meaning.
        if re.match(r"^(?:v\.|cf\.|see\b|id\.)", candidate, re.I):
            continue
        trimmed = _trim(candidate)
        if len(re.sub(r"[^A-Za-z]", "", trimmed)) >= _MIN_LETTERS:
            return trimmed
    return None


if __name__ == "__main__":
    import sqlite3
    import sys

    db = sys.argv[1] if len(sys.argv) > 1 else None
    if not db:
        print("usage: lewis_short_gloss.py <db-with-lewis-short-rows> [N]")
        raise SystemExit(2)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    cur = sqlite3.connect(db).cursor()
    rows = cur.execute(
        "SELECT headword, entry_plain FROM dictionary_entries "
        "WHERE source = 'Lewis-Short' GROUP BY headword LIMIT ?", (n,)
    ).fetchall()
    hit = 0
    for hw, plain in rows:
        g = extract_ls_gloss(plain)
        if g:
            hit += 1
        print(f"  {hw:22s} {g if g else '(none)'}")
    print(f"\n{hit}/{len(rows)} produced a gloss")
