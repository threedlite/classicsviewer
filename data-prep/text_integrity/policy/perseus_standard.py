"""Generic Perseus policy — the default fallback for Perseus Greek/Latin works.

Most Perseus TEI documents follow consistent conventions; this module captures
them. Specific authors with idiosyncratic structures (Aristotle / Plato /
drama / patristic commentary) get their own sub-policies that override or
extend this one.
"""
from __future__ import annotations


# Perseus-specific additions to the generic exclusion list.
#
# Note: do NOT add "app" here. The apparatus container wraps a chosen
# reading <lem> plus rejected variants <rdg>/<witDetail>. We want to KEEP
# the <lem> text and DROP the variants. <rdg> and <witDetail> are already
# in GENERIC_EXCLUDE; <lem> is in GENERIC_STRIP_KEEP_TEXT. If we excluded
# <app> here, the entire subtree (including <lem>) would be dropped
# before either rule could apply, silently losing the editor's chosen
# reading from canonical text.
ADD_EXCLUDE = frozenset({
    "del",       # editor's deletion markers
    "head",      # division headings — typically editorial, not source-author text
    "argument",  # argument summaries prefacing books — editorial paratext
    "speaker",   # speaker labels — stored in text_lines.speaker, not line_text
    "stage",     # stage directions in drama — Perseus marks them as editorial
})

# Nothing to remove from the generic baseline for perseus_standard.
REMOVE_EXCLUDE = frozenset()

# Perseus generally puts the regularized form in <choice><reg/>, and the
# original (manuscript) form in <choice><orig/>. We use the regularized form
# by default since that's what users read.
CHOICE_HANDLING = "reg"

# <supplied> = editor-restored text in lacunae. Include it as part of the
# canonical text (it's the readable form). Future sub-policies could mark
# with brackets, but for hashing we just include the bare text.
SUPPLIED_HANDLING = "include"

# Marker emitted for <gap reason="lost"/>. Empty by default so canonical
# text matches what the build stores (the build does not emit a marker for
# gaps). If a future audit needs to detect lost-text markers, override per
# work or per sub-policy.
GAP_MARKER = ""

# Most Perseus works are line-addressed (<l n="123">) or section-addressed
# (<div type="textpart" subtype="section" n="1">). The extractor picks the
# right addressable unit based on what's actually present in the XML.
ADDRESSING = "line"


def ref_from_db(row) -> str:
    """Build canonical ref from a books+text_lines join row.

    For most Perseus works the book_id format is `<work>.<book_number_padded>`
    and the line addressing is direct (`<book_number>.<line_number>`). The
    line_number column in text_lines is the same n value the XML produced.
    """
    return f"{row['book_number']}.{row['line_number']}"
