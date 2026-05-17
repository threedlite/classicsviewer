"""Tests for extract.py — the canonical-text walker.

These lock in the Phase 0 behavior so policy refinements can't silently
regress the basic XML-handling rules: <note> excluded, <lem> kept, tail
text after excluded elements preserved, choice resolved per policy, etc.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

# Make the `text_integrity` package importable as a top-level name when this
# file is run via `python3 -m unittest` from data-prep/ (since data-prep
# itself is not a valid Python package name — the hyphen prevents it).
_DATA_PREP = Path(__file__).resolve().parents[2]
if str(_DATA_PREP) not in sys.path:
    sys.path.insert(0, str(_DATA_PREP))

from text_integrity import extract  # noqa: E402
from text_integrity.policy import resolve_policy_for_work  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"


def _default_policy(**overrides):
    """Build a perseus_standard-equivalent Policy for tests, with overrides."""
    p = resolve_policy_for_work("phi0690.phi003")  # any plain Perseus work_id
    # Tests can override via dataclasses.replace if they need to twiddle.
    if overrides:
        from dataclasses import replace
        return replace(p, **overrides)
    return p


class ExtractLineAddressed(unittest.TestCase):
    """<l n=...> works under <div type=textpart subtype=book>."""

    def setUp(self):
        self.sections = extract.extract_canonical_text(
            FIXTURES / "line_addressed.xml", _default_policy(),
        )

    def test_emits_one_section_per_line(self):
        # 3 lines in book 1 + 1 line in book 2 = 4 sections
        self.assertEqual(len(self.sections), 4)

    def test_ref_format(self):
        # book.line format
        refs = [s.ref for s in self.sections]
        self.assertEqual(refs, ["1.1", "1.2", "1.3", "2.1"])

    def test_note_is_excluded(self):
        # The <note>editorial note must be dropped</note> must not appear
        for s in self.sections:
            self.assertNotIn("editorial note", s.text)
            self.assertNotIn("must be dropped", s.text)

    def test_teiheader_is_excluded(self):
        # The header title must not show up anywhere
        for s in self.sections:
            self.assertNotIn("Header content", s.text)

    def test_hi_keeps_text(self):
        # <hi rend="bold">Ἄϊδι</hi> — the wrapper drops but the text stays
        text = self.sections[2].text  # 1.3
        self.assertIn("Ἄϊδι", text)
        self.assertNotIn("<hi", text)
        self.assertNotIn("rend=", text)

    def test_text_preserved_in_order(self):
        # 1.1 should contain "μῆνιν ἄειδε" before "Ἀχιλῆος"
        text = self.sections[0].text
        i_menin = text.find("μῆνιν")
        i_achi = text.find("Ἀχιλῆος")
        self.assertGreaterEqual(i_menin, 0)
        self.assertGreater(i_achi, i_menin)


class ExtractSectionAddressed(unittest.TestCase):
    """No <l>; addressing is by leaf <div type=textpart>."""

    def setUp(self):
        self.sections = extract.extract_canonical_text(
            FIXTURES / "section_addressed.xml", _default_policy(),
        )

    def test_one_section_per_leaf_textpart(self):
        self.assertEqual(len(self.sections), 2)

    def test_refs_compose_hierarchically(self):
        refs = [s.ref for s in self.sections]
        self.assertEqual(refs, ["1.1", "1.2"])

    def test_foreign_kept_inline(self):
        # <foreign> is in STRIP_KEEP_TEXT — text stays, wrapper drops
        text = self.sections[0].text
        self.assertIn("foreign word", text)

    def test_ref_is_excluded(self):
        # <ref> is in GENERIC_EXCLUDE — content dropped, tail kept
        text = self.sections[1].text
        self.assertNotIn("cross-ref dropped", text)
        # But the tail "and trailing text." must remain
        self.assertIn("and trailing text", text)


class ExtractChoiceAndSupplied(unittest.TestCase):
    """<choice>, <supplied>, <gap> handling."""

    def setUp(self):
        self.sections = extract.extract_canonical_text(
            FIXTURES / "choice_and_supplied.xml", _default_policy(),
        )

    def test_choice_default_is_reg(self):
        # default policy.choice_handling = "reg" — should yield "canō" not "cano"
        text = self.sections[0].text
        self.assertIn("canō", text)
        self.assertNotIn("cano ", text)  # the orig form, with trailing space

    def test_choice_with_orig_policy(self):
        from dataclasses import replace
        p = _default_policy(choice_handling="orig")
        sections = extract.extract_canonical_text(
            FIXTURES / "choice_and_supplied.xml", p,
        )
        text = sections[0].text
        self.assertIn("cano", text)
        self.assertNotIn("canō", text)

    def test_supplied_included(self):
        # <supplied>Italiam</supplied> should appear in output
        text = self.sections[1].text
        self.assertIn("Italiam", text)

    def test_gap_marker_empty_by_default(self):
        # GAP_MARKER = "" in perseus_standard — nothing emitted for <gap/>
        text = self.sections[2].text
        # The surrounding text "litora" and "Lavinia" stay
        self.assertIn("litora", text)
        self.assertIn("Lavinia", text)
        # No "[…]" or "[gap]" marker
        self.assertNotIn("[", text)


class ExtractAppWithLem(unittest.TestCase):
    """<app><lem>...</lem><rdg>...</rdg></app> — keep lemma, drop variants."""

    def setUp(self):
        self.sections = extract.extract_canonical_text(
            FIXTURES / "app_with_lem.xml", _default_policy(),
        )

    def test_lem_text_kept(self):
        text_l1 = self.sections[0].text
        text_l2 = self.sections[1].text
        self.assertIn("μέν", text_l1)
        self.assertIn("καλόν", text_l2)

    def test_rdg_dropped(self):
        text_l1 = self.sections[0].text
        text_l2 = self.sections[1].text
        # rdg is the variant reading — must NOT appear
        self.assertNotIn("δὲ", text_l1)
        self.assertNotIn("κακόν", text_l2)

    def test_witdetail_dropped(self):
        text_l1 = self.sections[0].text
        self.assertNotIn("marginal note", text_l1)


class ExtractTailTextPreservation(unittest.TestCase):
    """Tail text after an excluded element must still be emitted."""

    def setUp(self):
        self.sections = extract.extract_canonical_text(
            FIXTURES / "tail_text.xml", _default_policy(),
        )

    def test_tail_after_excluded_note_is_kept(self):
        text = self.sections[0].text
        # The <note>EXCLUDED</note> content must be gone
        self.assertNotIn("EXCLUDED", text)
        # But its tail "tail of note." must remain
        self.assertIn("tail of note", text)

    def test_text_after_strip_keep_element_is_kept(self):
        text = self.sections[0].text
        # <hi>kept</hi> after hi.  → both "kept" and "after hi." remain
        self.assertIn("kept", text)
        self.assertIn("after hi", text)

    def test_leading_text_before_first_child_is_kept(self):
        text = self.sections[0].text
        self.assertIn("Leading text", text)


if __name__ == "__main__":
    unittest.main()
