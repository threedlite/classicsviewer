"""Reconstruct a work's canonical text sequence from the built DB.

Joins text_lines for a work in (book_number, line_number, sequence_number)
order, then applies the same normalization the canonical extractor uses,
so the resulting (ref, text) sequence can be hash-compared.

Read-only — the DB connection must have been opened with mode=ro.
"""
from __future__ import annotations
from sqlite3 import Connection

from .extract import Section
from .normalize import normalize_text
from .policy import Policy


def reconstruct_from_db(conn: Connection, work_id: str, policy: Policy) -> list[Section]:
    """Read every text_lines row for `work_id` and return as Section list.

    Section refs are produced by the policy's `ref_from_db` method, so
    they match whatever the canonical extractor produces for the same
    XML structure.
    """
    rows = conn.execute(
        """
        SELECT
            b.id            AS book_id,
            b.work_id       AS work_id,
            b.book_number   AS book_number,
            b.label         AS label,
            t.line_number   AS line_number,
            t.sequence_number AS sequence_number,
            t.line_text     AS line_text
        FROM books b
        JOIN text_lines t ON t.book_id = b.id
        WHERE b.work_id = ?
        ORDER BY b.book_number, t.line_number, t.sequence_number
        """,
        (work_id,),
    ).fetchall()

    out: list[Section] = []
    for row in rows:
        ref = policy.ref_from_db(row)
        text = normalize_text(row["line_text"], policy.normalization)
        if text:
            out.append(Section(ref=ref, text=text))
    return out
