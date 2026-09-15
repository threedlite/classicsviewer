#!/usr/bin/env python3
"""
Generate line-by-line interlinear translation for Latin works.

POS / dependency tagging strategy (mirrors `sanskrit/generate_sanskrit_interlinear.py`):

  1. Run Stanza UD-Latin on every line (PROIEL package) to get a baseline
     POS / lemma / head / deprel for every token. Stanza covers 100% of
     the Latin corpus.
  2. Overlay Perseus LDT v2.1 gold annotations on the works it aligns
     (Vergil Aeneid book 6 + Ovid Metamorphoses book 1 in v1 — see
     `latin/LATIN_POS_PLAN.md` §Appendix A for the alignment scope).
     Where LDT has a token, its lemma / POS / deprel / head replace
     Stanza's and the emitted format uses `~*` instead of `~`.

  3. English glosses still come from the dictionary lookup as before.
     Only POS / lemma / dependency structure is sourced from LDT/Stanza.

Output formats:
  - Plain text (`.interlinear.txt`)
  - TEI XML (`.perseus-eng99.xml`) — per-token table is now:
        | surface |
        | **gloss** |
        | LEMMA MORPH ~  POS DEPREL HEAD sent_pos sent_id |    (Stanza)
        | LEMMA MORPH ~* POS DEPREL HEAD sent_pos sent_id |    (LDT)

This matches the Greek treebank-derived format and the Sanskrit format,
so `topical/build_topical_pack.py`'s parser can use the same POS gate
across all three languages.
"""

import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Optional
import html
from functools import lru_cache
import time

# Import the Latin dictionary lookup
try:
    from .latin_dictionary_lookup import (
        LatinRepository, DictionaryEntry, extract_gloss, select_entry_for_pos,
        first_sense, lemmas_related, normalize_latin_headword,
    )
    from .latin_treebank_loader import LdtLoader, LdtWord, LdtLexicon
    from .latin_stanza_nlp import (
        get_stanza_nlp,
        ensure_model_downloaded,
        STANZA_AVAILABLE,
    )
except ImportError:
    # Fallback for direct execution (testing)
    from latin_dictionary_lookup import (
        LatinRepository, DictionaryEntry, extract_gloss, select_entry_for_pos,
        first_sense, lemmas_related, normalize_latin_headword,
    )
    from latin_treebank_loader import LdtLoader, LdtWord, LdtLexicon
    from latin_stanza_nlp import (
        get_stanza_nlp,
        ensure_model_downloaded,
        STANZA_AVAILABLE,
    )


# Pre-download the Stanza Latin model at module-import time. This avoids the
# race where N parallel workers all try to fetch the same model into the
# same cache dir. ensure_model_downloaded() is idempotent (no-op if cached).
if STANZA_AVAILABLE:
    ensure_model_downloaded()
    # Prove the model is USABLE in the parent before forking workers. Without
    # this, a missing model surfaces once per worker, mid-run, after the build
    # has already been going for hours. get_stanza_nlp() raises on failure.
    if get_stanza_nlp() is None:
        raise RuntimeError(
            "Stanza Latin pipeline is unavailable and the interlinear POS "
            "layer would silently produce nothing. Refusing to start."
        )


# Module-level LDT loader — load once per process, share via singleton.
_ldt_loader: Optional[LdtLoader] = None


def get_ldt_loader(db_path: Optional[str] = None) -> LdtLoader:
    """Process-singleton LDT loader; lazy-init on first call.

    `db_path` lets the loader align sentences by CONTENT -- finding a
    sentence's own words in the work's text -- instead of trusting the subdoc
    citation, which only maps to line numbers for 2 of the 12 LDT works.
    Without it the loader still works and falls back to the subdoc resolvers.
    """
    global _ldt_loader
    if _ldt_loader is None:
        _ldt_loader = LdtLoader(db_path=db_path or DB_PATH)
        _ldt_loader.load()
    return _ldt_loader


# Database path - will be set when called from build script
DB_PATH = None


_LDT_LEXICON = None
_LDT_LEXICON_TRIED = False


def get_ldt_lexicon():
    """Process-wide LdtLexicon, built once per worker.

    Returns None if LDT is unavailable, so the generator degrades to Stanza
    lemmas rather than failing - the lexicon is an improvement, not a
    prerequisite.
    """
    global _LDT_LEXICON, _LDT_LEXICON_TRIED
    if _LDT_LEXICON_TRIED:
        return _LDT_LEXICON
    _LDT_LEXICON_TRIED = True
    try:
        lex = LdtLexicon()
        lex.load()
        print(f"  [LDT lexicon] {lex.stats['kept']:,} surface forms "
              f"at >={lex.stats['min_agreement_pct']}% annotator agreement "
              f"(from {lex.stats['tokens']:,} treebank tokens)")
        _LDT_LEXICON = lex
    except Exception as exc:
        print(f"  [LDT lexicon] unavailable ({exc}); using Stanza lemmas only")
        _LDT_LEXICON = None
    return _LDT_LEXICON


class LatinInterlinearGenerator:

    # Imported dictionary package (DICTIONARY_IMPORT_FORMAT.md), loaded at build
    # time by load_gloss_package.py. Deliberately NOT in DEFAULT_GLOSS_SOURCES:
    # letting it compete on a straight headword match wrecked ~46,000 tokens of
    # common words, because it carries headwords for the prefixes se-/re- and
    # for huc that shadow Whitaker's pronouns. It is consulted only where it can
    # help -- to fill a blank, and to supply the treebank's lemma when Whitaker
    # has no entry for it.
    PACKAGE_SOURCES = (LatinRepository.GLOSS_PACKAGE_SOURCE,)

    # A synthesised "form of X" is a PLACEHOLDER, not a definition.
    # latin_dictionary_lookup emits it when lemma_map resolves a lemma but the
    # join finds no dictionary entry for it under the gloss sources. Zero real
    # entries in dictionary_entries begin with that string, so treating it as
    # an absent gloss is unambiguous.
    _PLACEHOLDER_PREFIX = "form of "

    @classmethod
    def _usable_gloss(cls, gloss, source=None):
        """The gloss if it is a real definition, else None.

        The two-character cutoff is SOURCE-SCOPED, and that matters. Measured
        over the Latin module DB, 96 entries have a gloss of two characters or
        fewer, and they fall into two unlike groups:

            Lewis-Short (70)        ad -> "ad", as -> "as", ah -> "ah"
            L&S package (10)        accumulate -> "in", catulinus2 -> "of"
            Whitaker (13 + 3)       sum -> "be", bos -> "ox", nulla -> "no",
                                    bito -> "go", cata -> "by", eugae -> "oh"

        The first two are echoes of the headword and truncation artifacts, and
        suppressing them is what this cutoff is for. Whitaker's are ordinary
        English words.

        Applying one length rule to both discarded Whitaker's gloss for the
        commonest verb in Latin. `sum` -> "be" is two characters, so the ESSE
        entry loaded, generated its 105 forms, and was selected correctly by
        POS and lemma -- then was thrown away here. 154,368 tokens of the
        copula fell through to *edo*, *sitio*, *erus* and the package as a
        result, and `_whitaker_defines("sum")` answered False for the same
        reason, so the package rescue kept firing for the word the fix was
        supposed to hand back to Whitaker.

        No entry from any source has a gloss of ONE character, so nothing is
        protected below two.
        """
        if not gloss or gloss == "???":
            return None
        # A gloss whose only content is the enclitic marker says nothing. It
        # survives every other test here because "+ and" is seven characters,
        # and it reached the reader: `eoque` shipped as literally "+ and" for
        # 397 tokens, because one `eo` entry reads "(adv.) ; there, ..." and
        # the first sense before that ";" is empty.
        body = re.sub(r"\+\s*(and|or|\?)\s*$", "", gloss).strip(" ,;")
        if not body:
            return None
        if len(gloss) <= 2 and not (source or "").startswith("Whitaker"):
            return None
        if gloss.startswith(cls._PLACEHOLDER_PREFIX):
            return None
        return gloss

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.repo = LatinRepository(db_path)
        # surface -> form handed to Stanza (see _tagging_form)
        self._enclitic_tagging_cache: Dict[str, str] = {}
        # Performance tracking
        self.lookup_count = 0
        self.total_db_time = 0.0

    def __enter__(self):
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        if self.repo and self.repo.conn:
            self.repo.conn.close()

    def get_latin_lines(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Extract Latin text lines from database"""
        start_time = time.time()
        cursor = self.conn.cursor()
        query = """
        SELECT line_number, line_text
        FROM text_lines
        WHERE book_id = ? AND line_number BETWEEN ? AND ?
        ORDER BY line_number
        """
        cursor.execute(query, (book_id, start_line, end_line))

        lines = []
        for row in cursor.fetchall():
            lines.append({
                'line_number': row['line_number'],
                'text_content': row['line_text']
            })

        query_time = time.time() - start_time
        if query_time > 0.1:  # Log queries slower than 100ms
            print(f"  [PERF] text_lines query for {book_id}: {query_time:.3f}s")

        return lines

    def tokenize_latin(self, text: str) -> List[str]:
        """
        Simple Latin tokenization - split on whitespace and remove punctuation.

        Latin is simpler than Greek - no breathing marks or complex diacritics.
        Just handle standard punctuation and enclitic markers.
        """
        # Remove common punctuation but keep Latin text
        text = re.sub(r'[,;.?!—\[\]():\'\"""«»]', ' ', text)
        tokens = text.split()
        return [t.strip() for t in tokens if t.strip()]

    def extract_gloss_from_entry(self, entry: DictionaryEntry) -> str:
        """Extract a simple English gloss from a DictionaryEntry."""
        return extract_gloss(entry)

    @lru_cache(maxsize=36000)
    def _cached_lookup_word(self, word: str) -> tuple:
        """
        Cache word lookups - returns (gloss, lemma, morph) tuple.

        LRU cache means common words like et, in, ad, etc.
        are only looked up once and then retrieved from cache instantly.

        Dictionary entries are sorted by frequency during database creation,
        so the first result is the most common meaning.
        """
        # Database lookup
        start_time = time.time()
        entries = self.repo.get_all_dictionary_entries(word, "latin")

        # If no results and word starts with uppercase, try lowercase
        if (not entries or len(entries) == 0) and word and word[0].isupper():
            entries = self.repo.get_all_dictionary_entries(word.lower(), "latin")

        db_time = time.time() - start_time

        self.lookup_count += 1
        self.total_db_time += db_time

        # Log cache stats every 1000 lookups
        if self.lookup_count % 1000 == 0:
            cache_info = self._cached_lookup_word.cache_info()
            hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses) * 100 if (cache_info.hits + cache_info.misses) > 0 else 0
            avg_db_time = (self.total_db_time / self.lookup_count) * 1000  # Convert to ms
            print(f"  [PERF] Cache: {hit_rate:.1f}% hit rate, {cache_info.currsize}/30000 entries, avg DB time: {avg_db_time:.2f}ms")

        # Process entries to extract gloss, lemma, morph
        gloss = None
        lemma = None
        morph = None

        if entries and len(entries) > 0:
            # Get morph info from database
            preferred_morph = self.repo.get_morph_info(word)

            # Find the best entry that carries a real definition.
            #
            # Entries come back with treebank-resolved rows first, and the
            # treebank sometimes names a lemma Whitaker files under a different
            # headword: the noun *bellum* is stored as "bellus", because the
            # citation-form picker takes the masculine nominative for a neuter
            # noun. Looking up "bellum" therefore yields the LDT row first,
            # which synthesises "form of bellum", while the Whitaker row two
            # places later holds "war, warfare".
            #
            # So a placeholder must not end the search -- but falling through
            # unconditionally is worse. For "est" the treebank says `sum`,
            # Whitaker has no `sum` entry at all, and the next candidate is
            # `edo` "eject/emit": a real analysis of the surface, but the wrong
            # word, and it is 28,971 tokens. Whitaker's own paradigm gap for
            # `sum` is the whole reason the treebank rows were added.
            #
            # A later entry may therefore stand in only if it names the SAME
            # lexeme as the treebank lemma. bellum/bellus qualifies; sum/edo
            # does not. Where nothing qualifies the word stays blank, which is
            # the correct outcome: Whitaker simply has no entry for it.
            placeholder_lemma = None
            for entry in entries:
                raw = self.extract_gloss_from_entry(entry)
                if raw and raw.startswith(self._PLACEHOLDER_PREFIX):
                    named = (raw[len(self._PLACEHOLDER_PREFIX):].strip()
                             or entry.lemma or "")
                    # A placeholder that names the surface itself is a
                    # self-mapping and says nothing about which word this is.
                    # An imported package supplies one for every form it knows
                    # (hoc -> hoc, te -> te, me -> me), and letting those
                    # constrain the search blocked Whitaker's correct entry:
                    # `hoc` lost "this" to hic being judged unrelated to hoc,
                    # `te` lost "you (sing.)". Only a placeholder naming a
                    # DIFFERENT lemma is evidence -- that is the `est` -> `sum`
                    # case this guard exists for.
                    if (placeholder_lemma is None and named
                            and normalize_latin_headword(named).lower()
                            != normalize_latin_headword(word).lower()):
                        placeholder_lemma = named
                    continue
                extracted_gloss = self._usable_gloss(raw, entry.source)
                if not extracted_gloss:
                    continue
                if placeholder_lemma and not lemmas_related(
                        entry.lemma, placeholder_lemma):
                    continue
                lemma = entry.lemma
                morph = entry.morph_info
                gloss = extracted_gloss
                break

            # If still no good gloss, use first entry's lemma at least
            if not gloss and entries:
                first_entry = entries[0]
                lemma = first_entry.lemma
                morph = first_entry.morph_info
                gloss = self.extract_gloss_from_entry(first_entry)

            # Use preferred morphology if we didn't get it from entries
            if not morph:
                morph = preferred_morph

        # "form of X" is a PLACEHOLDER, not a definition.
        # latin_dictionary_lookup synthesises it when lemma_map resolves a
        # lemma but the join finds no dictionary entry for it under the gloss
        # sources. Zero real entries in dictionary_entries begin with that
        # string, so treating it as an absent gloss is unambiguous.
        #
        # It matters because Whitaker's data has no entry for several very
        # common lemmas -- above all `sum`, whose paradigm Whitaker handles in
        # program code rather than in DICTLINE. Once the treebank routes `est`
        # to `sum`, the join finds nothing and invents "form of sum".
        #
        # Latin glosses come from Whitaker's ONLY, deliberately and for now.
        #
        # A Lewis & Short fallback used to sit here, consulted wherever
        # Whitaker's produced nothing. It was taken out to establish a clean
        # Whitaker-only baseline that can be compared against the shipped
        # release, so the Whitaker parsing fixes can be measured on their own
        # rather than through an L&S layer that moved at the same time.
        #
        # L&S is expected back, but as an imported dictionary package
        # (DICTIONARY_IMPORT_FORMAT.md) rather than as an article scraper. The
        # scraper is why it has to go: an L&S article's opening line is as
        # often a Latin quotation or a section rubric as it is a definition --
        # "colla" -> "nec collos mihi Calvus persuas", "utrumque" -> "Esp., in
        # apposit. with nouns", "sunt" -> "As a verb substantive, to be".
        #
        # Cost of removing it, measured over Aeneid / Gallic War / Pro Milone /
        # Epodi: blanks rise about 2-3 points (Aeneid 3.84% -> 6.89%).
        #
        # Re-adding a gloss source here means re-running the comparison in
        # latin/tools/README.md, not just restoring the code.
        if gloss and gloss.startswith("form of "):
            gloss = None

        # Package fallback: consulted ONLY where Whitaker produced nothing, so
        # it cannot displace an existing gloss -- it can only fill a blank.
        if not gloss or gloss == "???":
            pkg = self.repo.get_all_dictionary_entries(
                word, "latin", sources=self.PACKAGE_SOURCES)
            if not pkg and word and word[0].isupper():
                pkg = self.repo.get_all_dictionary_entries(
                    word.lower(), "latin", sources=self.PACKAGE_SOURCES)
            for entry in pkg:
                cand = self._usable_gloss(
                    self.extract_gloss_from_entry(entry), entry.source)
                if cand:
                    gloss = cand
                    if not lemma:
                        lemma = entry.lemma
                    break

        # Fallback if no gloss found
        if not gloss or gloss == "???":
            gloss = "???"

        return (gloss, lemma, morph)

    def lookup_word(self, word: str, book_id: str, line_number: int, position: int) -> Dict:
        """
        Lookup word using cached dictionary lookup.
        Returns a dict with latin, position, gloss, lemma, morph.
        POS / deprel / head get filled in later by resolve_line_pos_tags().
        """
        # Get cached result (gloss, lemma, morph) - instant for repeated words!
        gloss, lemma, morph = self._cached_lookup_word(word)

        return {
            'latin': word,
            'position': position,
            'gloss': gloss,
            'lemma': lemma,
            'morph': morph,
            # Default POS fields — overwritten by resolve_line_pos_tags below.
            'pos': '',
            'deprel': '',
            'head': 0,
            'sent_pos': position,
            'sent_id': '',
            'is_treebank': False,
        }

    def _whitaker_defines(self, lemma):
        """True when Whitaker really defines this lemma.

        Two traps, both hit while getting `sum` right:

        - The package must be excluded. It supplies `sum`, so asking "does any
          source define this?" answers yes and the rescue never fires for the
          word it exists for.
        - Row count is not enough. Querying Whitaker for lemma `sum` returns
          five rows, but four are `sumo` ("take up") reached through lemma_map
          and the fifth is a synthesised "form of sum" placeholder. So the test
          is: a row KEYED on this lemma that carries a real definition.
        """
        target = normalize_latin_headword(lemma or "").lower()
        for e in self.repo.get_all_dictionary_entries(
                lemma, "latin",
                sources=LatinRepository.DEFAULT_GLOSS_SOURCES):
            if (normalize_latin_headword(e.lemma or "").lower() == target
                    and self._usable_gloss(
                        self.extract_gloss_from_entry(e), e.source)):
                return True
        return False

    def _tagging_form(self, surface: str) -> str:
        """The form to hand Stanza: an enclitic's BASE, else the surface.

        Stanza never splits `-que`. It sees `virumque` as one unseen word and
        guesses a lemma from the `-um` -> `-us` noun pattern, producing
        `virusque` -- not a Latin word -- and tagging it ADJ. That fake lemma
        then blocks every lemma-keyed correction downstream, which is why
        Aeneid 1.1 glossed `virumque` as "poison, venom" while plain `virum`
        on line 10 came out "man": Stanza lemmatises `virum` correctly as
        `vir`.

        Sending the base keeps the 1:1 token mapping Stanza requires (one
        token in, one word out) while giving it a word it knows. The surface
        the reader sees is unchanged, and the gloss path already appends the
        enclitic's meaning.

        Guarded by the same test as the lookup: a fused word whose own lemma
        ends in -que (`quisque`, `uterque`) is left alone. `-ne` is excluded
        for the same reason it is excluded there.
        """
        if not surface or len(surface) < 5:
            return surface
        cached = self._enclitic_tagging_cache.get(surface)
        if cached is not None:
            return cached
        out = surface
        try:
            info = self.repo._strip_enclitic(self.repo.normalize_latin(surface))
            if (info and info[1] != '-ne (?)'
                    and not self.repo._has_fused_enclitic_lemma(surface)):
                base = info[0]
                if self.repo.get_all_dictionary_entries(base, "latin"):
                    # Keep the original capitalisation: Stanza uses it to
                    # decide PROPN, so `Troiaeque` must not become `troiae`.
                    out = base.capitalize() if surface[:1].isupper() else base
        except sqlite3.Error:
            pass
        self._enclitic_tagging_cache[surface] = out
        return out

    def _enclitic_suffix(self, surface: str) -> Optional[str]:
        """"and" / "or" if this surface is a true enclitic form, else None."""
        if self._tagging_form(surface) == surface:
            return None
        try:
            info = self.repo._strip_enclitic(self.repo.normalize_latin(surface))
        except sqlite3.Error:
            return None
        if not info:
            return None
        return {"-que (and)": "and", "-ve (or)": "or"}.get(info[1])

    def refine_glosses_with_pos(self, words: List[Dict]) -> None:
        """Re-pick each token's gloss using its resolved POS and lemma.

        Conservative by construction — it can only choose differently WITHIN the
        candidate set the original lookup already returned:
          * no candidates, no POS, or no candidate carrying that POS -> unchanged
          * exactly one candidate of that POS -> forced, no judgement involved
          * several -> tie-broken by the stem that best prefixes the lemma
        So a token whose gloss is already right cannot be made wrong by a
        selection that has nothing to select between.
        """
        for w in words:
            surface = w.get('latin')
            upos = w.get('pos')
            if not surface or not upos:
                continue
            try:
                entries = self.repo.get_all_dictionary_entries(surface, "latin")
            except sqlite3.Error:
                # Narrowed from `except Exception`. A DB error on one surface is
                # survivable, but the blanket form also swallowed TypeError,
                # AttributeError and the like -- i.e. real code defects in the
                # lookup path -- and every affected word silently became "???".
                # Anything that is not a DB error now propagates.
                continue
            picked = select_entry_for_pos(entries, upos, w.get('lemma'))

            # A surface that is ALSO another word's headword never reaches
            # lemma resolution: get_all_dictionary_entries() gates its
            # lemma_map step on `if not entries`, so the direct match wins and
            # the treebank's answer is never consulted. `bello` is the headword
            # of the VERB bello, so an ablative of bellum "war" glossed as
            # "fight, wage war"; likewise animo -> "animate", populo ->
            # "ravage", multa -> "fine", meo -> "go along", tuo -> "see".
            #
            # Detectable here and nowhere else: this is the only place the
            # token's own POS and lemma are known. When no candidate carries
            # the token's POS, look the LEMMA up instead and let the same
            # selector choose among its entries. Requires a different lemma and
            # a usable result, so a token whose gloss is already right is
            # untouched.
            # Retry against the token's own lemma when NO candidate carries it.
            #
            # Two ways that happens, both because the surface is some other
            # word's headword and so the direct match short-circuits before
            # lemma_map is ever consulted:
            #   - nothing was picked (bello: only the verb *bello* matched)
            #   - something was picked, but it is a different word (virum: the
            #     rare N-2-2 entry glossed "virus" beat the accusative of *vir*)
            # The retry is Whitaker-only, so it cannot pull in a package gloss;
            # that is the package rescue's job further down, and conflating the
            # two is what made `a` gloss as "departure from a fixed point".
            # `has_lemma` below is the whole guard: if any candidate already
            # names the treebank's lemma, the pick stands.
            lem = w.get('lemma')
            target = normalize_latin_headword(lem or "").lower()
            has_lemma = any(
                normalize_latin_headword(e.lemma or "").lower() == target
                for e in entries)
            if lem and not has_lemma and lem.lower() != surface.lower():
                try:
                    by_lemma = self.repo.get_all_dictionary_entries(
                        lem, "latin")
                except sqlite3.Error:
                    by_lemma = []
                alt = select_entry_for_pos(by_lemma, upos, lem)
                if alt is not None and self._usable_gloss(
                        self.extract_gloss_from_entry(alt), alt.source):
                    picked = alt

            # When every POS-matching candidate names a DIFFERENT word from the
            # one the treebank resolved, Whitaker has no entry for that lemma
            # and the pick is a guess. That is how `est` shipped as "eject/emit"
            # (edo) for 55,286 tokens, `sit` as "be thirsty" (sitio) and `sint`
            # as "allow, permit" (sino): the treebank said `sum` every time, and
            # Whitaker's data files carry no `sum` at all.
            #
            # Prefer an exact headword match from the package. Failing that,
            # decline rather than guess. This cannot touch a token whose
            # Whitaker candidate already agrees with the treebank, so
            # bellum/bellus, Asia/Asia and pietas/pietas are unaffected.
            # Two cases only, so the rescue cannot displace a good Whitaker
            # gloss the lookup already found: the POS pick names a different
            # word from the treebank's lemma, or there was no pick at all AND
            # the token is still blank.
            tok_lemma = w.get('lemma')
            current = w.get('gloss')
            blank_now = not current or current == "???"
            rescued = False
            # An EXACT lemma match beats a merely prefix-related one.
            #
            # lemmas_related() answers "same lexeme?" generously so that
            # bellum/bellus and aurum/aurus pass. That generosity let `sumo`
            # stand in for `sum` -- "sum" is a prefix of "sumo" -- so the
            # surface *sum* tagged AUX glossed as "take up". Whitaker has no
            # `sum` at all, which is exactly the gap the package fills, but the
            # rescue never fired because the wrong candidate looked related.
            # Package rescue.
            #
            # Narrow on purpose: it fires ONLY where Whitaker has no usable
            # definition keyed on the treebank's lemma AND the surface itself
            # is not a Whitaker headword. That is the `sum` hole -- Whitaker's
            # Ada program handles the verb in code, so `sum`, `est`, `sunt` and
            # the rest resolve to a lemma with no entry and the selector falls
            # through to whatever else shares the surface (`edo`, `sitio`,
            # `sino`, `sumo`).
            #
            # Five earlier versions of this condition each fixed two cases and
            # broke two others, because they asked about lemma SHAPE --
            # exact-match, prefix-relatedness, whether the pick differed from
            # the lemma. Shape cannot separate these: `sum`/`sumo` and
            # `potius`/`potis` look identical to any prefix test, but in the
            # first Whitaker has nothing and in the second it has the right
            # adverb already. Asking about the DATA instead ("does Whitaker
            # actually define this?") separates them cleanly and needs no
            # special cases.
            #
            # Consequence worth stating: where Whitaker defines the surface,
            # its gloss stands even if the package's is arguably better
            # (`Cotta` keeps "Cotta"). That is the conservative direction --
            # this rescue has already caused two regressions by being eager.
            # For an enclitic the meaningful surface is its BASE: `seque` is
            # not a Whitaker headword, so the rescue fired and handed back the
            # package's `se-` PREFIX entry, turning "him/her/it/ones-self" into
            # "sine, without, aside". Judge the base instead.
            rescue_surface = self._tagging_form(surface)
            # An enclitic whose base already produced a usable gloss is done.
            # Letting the rescue run anyway handed `seque` the package's `se-`
            # PREFIX entry -- "sine, without, aside" in place of
            # "him/her/it/ones-self". The rescue exists to fill blanks, not to
            # overrule a Whitaker answer the split already found.
            enclitic_resolved = (rescue_surface != surface and not blank_now)
            if (tok_lemma and not enclitic_resolved
                    and not self._whitaker_defines(tok_lemma)
                    and not self._whitaker_defines(rescue_surface)):
                rescue = next(
                    (e for e in self.repo.get_all_dictionary_entries(
                        tok_lemma, "latin", sources=self.PACKAGE_SOURCES)
                     if self._usable_gloss(
                         self.extract_gloss_from_entry(e), e.source)),
                    None)
                if rescue is not None:
                    picked = rescue
                    rescued = True
                elif picked is not None and tok_lemma and not lemmas_related(
                        picked.lemma, tok_lemma):
                    # Pick names a different word and nothing can replace it.
                    continue

            if picked is None:
                continue
            new_gloss = self.extract_gloss_from_entry(picked)
            # An entry whose definition opens with a separator -- `eo` has
            # "(adv.) ; there, to/toward that place" -- extracts to an empty
            # first sense. Empty is truthy enough to survive the checks below
            # and the enclitic marker was then appended to nothing, so `eoque`
            # shipped as literally "+ and" for 397 tokens. Gate on the same
            # usability test the rest of the pipeline uses.
            if not self._usable_gloss(new_gloss, getattr(picked, "source", None)):
                new_gloss = None


            # Genuinely ambiguous forms get BOTH readings, first sense each.
            #
            # `ora` is annotated `os` (mouth) 81% of the time and `ora` (shore)
            # 19% in LDT, and both are common in Vergil - only context
            # separates them, which a lexicon does not have. Printing "mouth,
            # shore" tells the reader the form is ambiguous instead of
            # silently committing to the majority and being wrong 19% of the
            # time. Applies to ~5.8% of corpus tokens.
            # ...but not on a token the package rescued. The rescue fires
            # only where Whitaker has no entry for the treebank's lemma, and
            # `_dual_gloss` is built ENTIRELY from Whitaker entries, so every
            # reading it could print for such a token belongs to some other
            # word. Letting it run overwrote the rescue on 26 surfaces /
            # 4,062 tokens, every one of them for the worse: `esto` and `eras`
            # "to be, exist, live" -> "take up, eject, eat", `armis`
            # "defensive armor and weapons" -> "forequarter (of an animal)",
            # `qualis` "of what sort" -> "what kind, wicker basket".
            dual = None if rescued else self._dual_gloss(w.get('latin'), entries)
            if dual:
                new_gloss = dual

            # The lemma retry swaps in an entry keyed on the BASE word, which
            # carries no enclitic marker — so `virumque` came out "man" rather
            # than "man + and". Re-attach it.
            enc = self._enclitic_suffix(surface)
            if (enc and new_gloss and new_gloss != "???"
                    and not re.search(r"\+\s*(and|or)\s*$", new_gloss)):
                new_gloss = f"{new_gloss} + {enc}"

            if new_gloss and new_gloss != "???":
                w['gloss'] = new_gloss
                # Keep lemma and morph consistent with the entry that supplied
                # the gloss, unless the treebank already gave a gold lemma.
                if not w.get('is_treebank'):
                    if picked.morph_info:
                        w['morph'] = picked.morph_info

    # A second reading below this share is treated as noise, not ambiguity.
    DUAL_GLOSS_MIN_SHARE = 0.15

    # Cap on readings shown. The interlinear gloss sits under each word and
    # has to stay short; beyond three it stops being a gloss.
    MAX_READINGS = 3

    @staticmethod
    def _first_sense(gloss: Optional[str]) -> Optional[str]:
        """First sense only - see first_sense() in latin_dictionary_lookup.

        Kept as a thin wrapper because callers here pass Optional[str] and
        expect None (not "") for an empty result.
        """
        if not gloss:
            return None
        return first_sense(gloss) or None

    def _dual_gloss(self, surface: Optional[str], entries) -> Optional[str]:
        """"mouth, shore" for a form LDT annotates two different ways.

        Returns None unless there really are two readings, each above
        DUAL_GLOSS_MIN_SHARE, that resolve to two DIFFERENT glosses. So an
        unambiguous form is untouched, and a form whose two readings happen to
        share a gloss does not get it printed twice.
        """
        if not surface:
            return None
        lexicon = get_ldt_lexicon()
        if lexicon is None:
            return None
        senses: List[str] = []

        def add(lemma, upos):
            """Append this reading's first sense. True if it contributed one."""
            if len(senses) >= self.MAX_READINGS:
                return False
            entry = select_entry_for_pos(entries, upos, lemma)
            if entry is None:
                by_lemma = self.repo.get_all_dictionary_entries(lemma, "latin")
                entry = select_entry_for_pos(by_lemma, upos, lemma)
            sense = self._first_sense(
                self.extract_gloss_from_entry(entry) if entry else None)
            if sense and sense != "???" and sense.lower() not in {
                    x.lower() for x in senses}:
                senses.append(sense)
                return True
            return False

        # 1) Readings LDT actually attests, ranked by annotator agreement.
        #    This is evidence of USAGE.
        readings = lexicon.readings_for(surface)
        for i, (lemma, upos, share) in enumerate(readings):
            if share >= self.DUAL_GLOSS_MIN_SHARE:
                got = add(lemma, upos)
                # ORDER INTEGRITY. What this prints is a list ordered by
                # annotator agreement, and the reader has no way to see that
                # the most-attested reading dropped out. It drops out when the
                # two lexica cite the same word differently -- LDT says `arma`,
                # Whitaker's headword is `armum`, and nothing joins them -- so
                # the leftover minority reading ends up first and looks like
                # the majority one. `armis` printed "forequarter (of an
                # animal), arms (pl.)" for the 19% reading. When the top
                # reading contributes nothing the order means nothing, so
                # print no list at all and let the single-gloss path answer.
                # Measured: 19 shipped surfaces, ~7,000 tokens, e.g. `liber`
                # "children (pl.), nibble" -> "children (pl.)", `remis`
                # "oar, party in law suit" -> "oar", `quale` "what kind,
                # wicker basket" -> "what kind/sort/condition (of)".
                if i == 0 and not got:
                    return None

        # 2) Readings Whitaker's inflection engine considers morphologically
        #    possible but LDT's works never happened to contain. This is
        #    evidence of POSSIBILITY, not of usage.
        #
        #    ONLY when LDT is genuinely split. Measured on a 996-token Vergil
        #    sample, adding these unconditionally polluted 10.7% of glosses
        #    while helping 8.4%: `furor` became "madness, steal", `venientem`
        #    "go for sale, come", `volvis` "womb, roll", `obversus` "enemy
        #    (pl.), turn or direct towards". Whitaker's stems collapse
        #    unrelated words, so a possibility with no attested usage behind it
        #    is usually just a different word.
        #
        #    Where LDT IS split it is already telling us the form is ambiguous
        #    in practice, and a further possible reading is worth showing -
        #    that is the `ora` case ("mouth, shore, beg"), where "pray" is real
        #    but absent from LDT's five works.
        if len(readings) >= 2 and readings[1][2] >= self.DUAL_GLOSS_MIN_SHARE:
            for lemma, upos in self._whitaker_readings(surface):
                add(lemma, upos)

        return ", ".join(senses) if len(senses) >= 2 else None

    # POS implied by a Whitaker morph string. Verb markers are checked first
    # because a verb morph never carries a case, but a participle carries both.
    _MORPH_VERB = re.compile(
        r"\b(pres|perf|fut|impf|imp|ind|sub|inf|part|active|passive)\b")
    _MORPH_CASE = re.compile(r"\b(nom|acc|gen|dat|abl|voc|loc)\b")

    def _whitaker_readings(self, surface: str):
        """(lemma, POS) pairs Whitaker's inflection engine allows for a form.

        Read from lemma_map.morph_info, which is what the engine generated, so
        these are morphologically checked rather than guessed.
        """
        out = []
        try:
            cur = self.repo.conn.cursor()
            cur.execute(
                "SELECT lemma, morph_info FROM lemma_map "
                "WHERE word_form = ? AND source = 'Whitaker'", (surface,))
            for lemma, morph in cur.fetchall():
                if not morph:
                    continue
                if self._MORPH_VERB.search(morph):
                    out.append((lemma, "VERB"))
                elif self._MORPH_CASE.search(morph):
                    out.append((lemma, "NOUN"))
        except (AttributeError, TypeError, ValueError):
            # Narrowed from `except Exception`, which returned a PARTIAL list
            # and let the caller treat it as complete. Restricted to the parse
            # errors malformed morph strings actually raise; anything else is a
            # defect and must surface.
            pass
        return out

    def resolve_line_pos_tags(
        self,
        book_id: str,
        line_number: int,
        words: List[Dict],
    ) -> None:
        """
        Mutate each word dict in `words` with POS / lemma / deprel / head /
        sent_pos / sent_id / is_treebank, sourced from Stanza for every token
        and overlaid with Perseus LDT where it covers this (book_id, line).

        Words whose `latin` field has no Latin letters (numbers, milestone
        markers like "[1.1]") are left untouched — they have no linguistic
        POS to assign.

        Strategy:
          - Pretokenize the line's Latin tokens and pass them to Stanza as
            a single sentence. Stanza returns per-token POS / lemma / head /
            deprel.
          - For each token position, check the LDT loader: if an LDT word
            matches the surface form for (book_id, line_number), use its
            lemma / postag / deprel / head and mark is_treebank=True.
          - sent_id is "L<line_number>" (one sentence per line in v1).
        """
        # Collect the Latin-letter-bearing tokens that need linguistic
        # analysis, preserving their indices in `words` so we can copy
        # results back.
        analyzable = [
            (i, w['latin']) for i, w in enumerate(words)
            if re.search(r'[a-zA-ZāēīōūĀĒĪŌŪ]', w['latin'])
        ]
        if not analyzable:
            return

        token_strings = [t for _, t in analyzable]
        # Enclitics are resolved BEFORE tagging, not after — see _tagging_form.
        tagging_strings = [self._tagging_form(t) for t in token_strings]
        sent_id = f"L{line_number}"

        # --- 1) Stanza baseline pass ---
        nlp = get_stanza_nlp()
        stanza_words = []
        if nlp is not None:
            try:
                doc = nlp([tagging_strings])
                # Pretokenized + one input sentence → exactly one sentence
                # out, with words 1:1 to our tokens.
                if doc.sentences:
                    stanza_words = list(doc.sentences[0].words)
            except Exception as e:
                # Stanza failure for one line: leave POS fields blank rather
                # than crash the whole work.
                print(f"  [stanza] WARN: failed on {book_id} L{line_number}: {e}")

        for sent_pos, (orig_idx, _surface) in enumerate(analyzable, 1):
            if sent_pos - 1 < len(stanza_words):
                sw = stanza_words[sent_pos - 1]
                # Stanza's `head` is 1-based within the sentence; 0 = root.
                # We keep the same convention.
                words[orig_idx]['pos'] = sw.upos or ''
                # Don't overwrite the dictionary lemma if Stanza's is blank.
                if sw.lemma:
                    words[orig_idx]['lemma'] = sw.lemma
                words[orig_idx]['deprel'] = sw.deprel or ''
                words[orig_idx]['head'] = sw.head if sw.head is not None else 0
            words[orig_idx]['sent_pos'] = sent_pos
            words[orig_idx]['sent_id'] = sent_id

        # --- 2) LDT overlay ---
        loader = get_ldt_loader(self.db_path)
        for orig_idx, surface in analyzable:
            ldt_word = loader.lookup_token(book_id, line_number, surface)
            if ldt_word is None:
                continue
            if ldt_word.upos:
                words[orig_idx]['pos'] = ldt_word.upos
            if ldt_word.lemma:
                words[orig_idx]['lemma'] = ldt_word.lemma
            if ldt_word.deprel:
                words[orig_idx]['deprel'] = ldt_word.deprel
            words[orig_idx]['head'] = ldt_word.head
            # The morph field stays as the dictionary's morph string — LDT's
            # postag would be more accurate, but the dictionary morph is
            # already validated by downstream code. Future v2: convert
            # ldt_word.postag → UD-style morph features ("Case=Acc|Num=Sing").
            words[orig_idx]['is_treebank'] = True

        # --- 3) LDT lexicon pass -------------------------------------------
        # The overlay above only reaches lines whose canonical citation happens
        # to match text_lines.line_number, which is 0.14% of Latin tokens. But
        # a hand-annotated surface -> lemma mapping is not location-dependent:
        # "oris -> ora", annotated in Aeneid 6, is equally true in Aeneid 1.
        #
        # So for every token the overlay did NOT cover, prefer LDT's lemma for
        # that surface form over Stanza's guess. In-context treebank data still
        # wins - this only replaces a machine guess with a human annotation.
        # Raises gold-lemma reach from 0.14% to ~28% of tokens at the default
        # 80% agreement threshold. See LdtLexicon and LATIN_POS_PLAN.md §9.2.
        lexicon = get_ldt_lexicon()
        if lexicon is not None:
            for w in words:
                if w.get('is_treebank'):
                    continue
                surface = w.get('latin')
                if not surface:
                    continue
                lex_lemma = lexicon.lemma_for(surface)
                if lex_lemma and lex_lemma != w.get('lemma'):
                    w['lemma'] = lex_lemma

    def generate_interlinear(self, book_id: str, start_line: int, end_line: int) -> List[Dict]:
        """Main function to generate interlinear translation"""

        # Step 1: Get Latin text
        t0 = time.time()
        latin_lines = self.get_latin_lines(book_id, start_line, end_line)
        text_fetch_time = time.time() - t0

        if not latin_lines:
            print(f"  WARNING: No Latin text found for {book_id} lines {start_line}-{end_line}")
            return []

        # Step 2: Process each line
        t1 = time.time()
        lines_data = []

        for line in latin_lines:
            line_num = line['line_number']
            text = line['text_content']

            # Tokenize
            tokens = self.tokenize_latin(text)

            # Lookup each word (gloss + dictionary lemma/morph).
            words = []
            for pos, token in enumerate(tokens, 1):
                # Skip non-Latin tokens (numbers, milestone references).
                # Any token without Latin letter characters is a reference
                # marker, not a word to gloss.
                if not re.search(r'[a-zA-ZāēīōūĀĒĪŌŪ]', token):
                    word_data = {
                        'latin': token,
                        'position': pos,
                        'gloss': '',
                        'lemma': '',
                        'morph': '',
                        'pos': '',
                        'deprel': '',
                        'head': 0,
                        'sent_pos': pos,
                        'sent_id': '',
                        'is_treebank': False,
                    }
                else:
                    word_data = self.lookup_word(token, book_id, line_num, pos)
                words.append(word_data)

            # Stanza POS pass + LDT overlay. Single call per line; safe to
            # invoke even if Stanza is unavailable (fields stay blank).
            self.resolve_line_pos_tags(book_id, line_num, words)

            # Re-select each gloss now that POS and lemma are known.
            #
            # `_cached_lookup_word` is keyed on the surface form alone and runs
            # BEFORE this point, so it had to pick blind — entries[0] — from a
            # candidate set where Whitaker's stems collapse unrelated words.
            # That is why Aeneid 1.1 glossed `oris` as "rise (sun/river)" and
            # 1.3 glossed `alto` as "wing". Now that resolve_line_pos_tags has
            # filled in POS and the LDT/Stanza lemma, the choice can be made on
            # evidence. See latin/LATIN_GLOSS_PLAN.md §5.2-5.3.
            self.refine_glosses_with_pos(words)

            # Create word-by-word gloss
            word_gloss = ' '.join([w['gloss'] if w['gloss'] else '???' for w in words])

            lines_data.append({
                'line_number': line_num,
                'latin_text': text,
                'words': words,
                'word_gloss': word_gloss
            })

        processing_time = time.time() - t1
        total_time = time.time() - t0

        return lines_data


def generate_latin_interlinear_translations(db_path: Path, output_dir: Path, work_ids=None):
    """
    Generate interlinear translations for Latin works

    Args:
        db_path: Path to the Perseus database
        output_dir: Directory where XML files will be written
        work_ids: List of PHI work IDs to process (e.g., ['phi0690.phi003']).
                  If None, defaults to Virgil's Aeneid.
    """
    global DB_PATH
    DB_PATH = db_path

    if work_ids is None:
        # Default to Virgil's Aeneid
        work_ids = ['phi0690.phi003']
    elif isinstance(work_ids, str):
        work_ids = [work_ids]

    output_dir.mkdir(parents=True, exist_ok=True)

    total_works = len(work_ids)
    for work_idx, work_id in enumerate(work_ids, 1):
        work_percent = (work_idx - 1) / total_works * 100
        print(f"\n{'=' * 80}")
        print(f"LATIN WORK {work_idx}/{total_works} - {work_percent:.1f}% complete: {work_id}")
        print(f"{'=' * 80}")
        _generate_latin_work(work_id, output_dir)
        work_percent = work_idx / total_works * 100
        print(f"\nWork {work_id} done ({work_percent:.1f}% of all works)")


def _write_xml_header(f, work_id: str, work_title: str, author_name: str):
    """Write XML header and TEI metadata (streaming helper)"""
    work_title_escaped = html.escape(work_title)
    author_name_escaped = html.escape(author_name)
    work_id_escaped = html.escape(work_id)

    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<?xml-model href="http://www.stoa.org/epidoc/schema/8.19/tei-epidoc.rng"\n')
    f.write('  schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
    f.write('<TEI xmlns="http://www.tei-c.org/ns/1.0">\n')
    f.write('    <teiHeader>\n')
    f.write('        <fileDesc>\n')
    f.write('            <titleStmt>\n')
    f.write(f'                <title>{work_title_escaped} - Interlinear Translation</title>\n')
    f.write(f'                <author>{author_name_escaped}</author>\n')
    # Translator string matches the Greek convention exactly, because the
    # token format is now also identical (LEMMA MORPH ~/~* POS DEPREL HEAD
    # sent_pos sent_id). Greek and Latin can share parser code at the
    # client end (see app/.../topical/LemmaBagBuilder.kt parseLatin
    # post-LATIN_POS_PLAN.md).
    f.write('                <editor role="translator">Interlinear (Beta, AI-generated from app dictionary and treebank)</editor>\n')
    f.write('                <sponsor>Derived from Whitaker\'s Words, Perseus LDT v2.1, Stanza UD-Latin (PROIEL)</sponsor>\n')
    f.write('                <principal></principal>\n')
    f.write('                <respStmt>\n')
    f.write('                    <resp>AI-generated interlinear translation</resp>\n')
    f.write('                    <name>Claude Code</name>\n')
    f.write('                </respStmt>\n')
    f.write('            </titleStmt>\n')
    f.write('            <extent>AI-generated interlinear</extent>\n')
    f.write('            <publicationStmt>\n')
    f.write('                <publisher></publisher>\n')
    f.write('                <pubPlace></pubPlace>\n')
    f.write('                <authority></authority>\n')
    f.write('            </publicationStmt>\n')
    f.write('            <notesStmt>\n')
    f.write('                <note anchored="true">AI-generated word-by-word interlinear translation derived from Whitaker\'s Words dictionary.</note>\n')
    f.write('            </notesStmt>\n')
    f.write('            <sourceDesc>\n')
    f.write('                <biblStruct>\n')
    f.write('                    <monogr>\n')
    f.write(f'                        <author>{author_name_escaped}</author>\n')
    f.write(f'                        <title>{work_title_escaped}</title>\n')
    f.write('                        <title type="sub">Interlinear Translation</title>\n')
    f.write('                        <editor role="translator">AI-generated</editor>\n')
    f.write('                        <imprint>\n')
    f.write('                            <date>2025</date>\n')
    f.write('                        </imprint>\n')
    f.write('                    </monogr>\n')
    f.write('                </biblStruct>\n')
    f.write('            </sourceDesc>\n')
    f.write('        </fileDesc>\n')
    f.write('        <encodingDesc>\n')
    f.write('            <refsDecl n="CTS">\n')
    f.write('                <cRefPattern n="line" matchPattern="(\\w+).(\\w+)"\n')
    f.write('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\']//tei:l[@n=\'$2\'])">\n')
    f.write('                    <p>This pointer pattern extracts book and line</p>\n')
    f.write('                </cRefPattern>\n')
    f.write('                <cRefPattern n="book" matchPattern="(\\w+)"\n')
    f.write('                    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n=\'$1\'])">\n')
    f.write('                    <p>This pointer pattern extracts book</p>\n')
    f.write('                </cRefPattern>\n')
    f.write('            </refsDecl>\n')
    f.write('            <refsDecl>\n')
    f.write('                <refState unit="book" delim="."/>\n')
    f.write('                <refState unit="line"/>\n')
    f.write('            </refsDecl>\n')
    f.write('        </encodingDesc>\n')
    f.write('        <profileDesc>\n')
    f.write('            <langUsage>\n')
    f.write('                <language ident="eng">English</language>\n')
    f.write('                <language ident="lat">Latin</language>\n')
    f.write('            </langUsage>\n')
    f.write('        </profileDesc>\n')
    f.write('        <revisionDesc>\n')
    f.write('            <change when="20251201" who="Claude Code">Generated Latin interlinear translation.</change>\n')
    f.write('        </revisionDesc>\n')
    f.write('    </teiHeader>\n')
    f.write('    <text xml:lang="eng">\n')
    f.write('        <body>\n')
    f.write(f'            <div type="translation" n="urn:cts:latinLit:{work_id_escaped}.perseus-eng99" xml:lang="eng">\n')


def _write_book_to_xml(f, book_num: int, book_results: List[Dict]):
    """Write a single book to XML file (streaming helper)"""
    f.write(f'                <div type="textpart" subtype="Book" n="{book_num}">\n')

    for line_data in book_results:
        line_num = line_data['line_number']

        # Build interlinear text efficiently using list comprehension.
        word_tables = []
        for w in line_data['words']:
            latin = w['latin'] if w['latin'] else '???'
            gloss = w['gloss'] if w['gloss'] else '???'
            lemma = w['lemma'] if w['lemma'] else '?'
            morph = w['morph'] if w['morph'] else ''

            # POS / dep fields (filled by resolve_line_pos_tags). For tokens
            # that aren't real Latin (milestones, numerals) these stay blank
            # and we emit the dictionary-only format.
            pos = w.get('pos') or ''
            deprel = w.get('deprel') or ''
            head = w.get('head', 0)
            sent_pos = w.get('sent_pos', 0)
            sent_id = w.get('sent_id') or ''
            is_treebank = w.get('is_treebank', False)
            marker = '~*' if is_treebank else '~'

            # Escape XML special chars; Latin texts have <word>...</word>
            # editorial markers that would otherwise break the XML.
            latin = html.escape(latin, quote=False)
            gloss = html.escape(gloss, quote=False)
            lemma = html.escape(lemma, quote=False)
            morph = html.escape(morph, quote=False)
            pos_esc = html.escape(pos, quote=False)
            deprel_esc = html.escape(deprel, quote=False)
            sent_id_esc = html.escape(sent_id, quote=False)

            lemma_morph = f'{lemma} {morph}' if morph else lemma
            if pos_esc:
                # New POS-bearing format. Matches the Sanskrit shape:
                #     LEMMA MORPH ~  POS DEPREL HEAD sent_pos sent_id   (Stanza)
                #     LEMMA MORPH ~* POS DEPREL HEAD sent_pos sent_id   (LDT)
                lemma_block = (
                    f'{lemma_morph} {marker} {pos_esc} {deprel_esc} '
                    f'{head} {sent_pos} {sent_id_esc}'
                )
            else:
                # No POS available (Stanza failed or token wasn't analyzable).
                # Fall back to the old format with just lemma + morph.
                lemma_block = lemma_morph

            table = f'| {latin} |\n| **{gloss}** |\n| {lemma_block} |'
            word_tables.append(table)

        interlinear_text = '  '.join(word_tables)
        f.write(f'                    <l n="{line_num}">{interlinear_text}</l>\n')

    f.write('                </div>\n')


def _write_xml_footer(f):
    """Write XML footer (streaming helper)"""
    f.write('            </div>\n')
    f.write('        </body>\n')
    f.write('    </text>\n')
    f.write('</TEI>\n')


def _write_book_to_txt(f, book_num: int, book_results: List[Dict]):
    """Write a single book to text file (streaming helper)"""
    f.write(f"\n{'=' * 80}\n")
    f.write(f"BOOK {book_num}\n")
    f.write(f"{'=' * 80}\n\n")

    for line_data in book_results:
        line_num = line_data['line_number']
        latin_words = [w['latin'] for w in line_data['words']]
        glosses = [w['gloss'] for w in line_data['words']]

        f.write(f"{line_num}. {' | '.join(latin_words)}\n")
        f.write(f"{' | '.join(glosses)}\n\n")


def _generate_latin_work(work_id: str, output_dir: Path):
    """
    Generate interlinear translation for a single Latin work using PHI ID.

    Uses STREAMING architecture: processes and writes one book at a time
    to minimize memory usage and ensure all files are written correctly.
    """

    print("=" * 80)
    print(f"LATIN INTERLINEAR TRANSLATION GENERATOR")
    print("=" * 80)
    print(f"Work ID: {work_id}")
    print(f"Database: {DB_PATH}")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"\n  FATAL ERROR: Database not found at {DB_PATH}")
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # Get all books for this work
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    book_pattern = f"{work_id}.%"
    cursor.execute("SELECT DISTINCT book_id FROM text_lines WHERE book_id LIKE ? ORDER BY book_id", (book_pattern,))
    book_ids = [row[0] for row in cursor.fetchall()]

    # Get work metadata for XML
    cursor.execute("""
        SELECT DISTINCT w.title_english, a.name
        FROM works w
        JOIN authors a ON w.author_id = a.id
        WHERE w.id = ?
    """, (work_id,))
    work_metadata = cursor.fetchone()
    conn.close()

    if not book_ids:
        print(f"\n  WARNING: No books found for work ID {work_id}")
        print(f"  Skipping this work.")
        return

    if work_metadata:
        work_title, author_name = work_metadata
    else:
        work_title = work_id
        author_name = "Unknown"

    print(f"\nFound {len(book_ids)} books to process")
    print(f"Work: {work_title} by {author_name}")
    print("=" * 80)

    # Generate output filenames
    txt_filename = f"{work_id}.interlinear.txt"
    xml_filename = f"{work_id}.perseus-eng99.xml"
    output_file = output_dir / txt_filename
    xml_output_file = output_dir / xml_filename

    total_lines = 0

    try:
        # Open BOTH output files at the start - streaming architecture
        with open(output_file, 'w', encoding='utf-8') as txt_file, \
             open(xml_output_file, 'w', encoding='utf-8') as xml_file, \
             LatinInterlinearGenerator(str(DB_PATH)) as generator:

            # Write XML header once at start
            _write_xml_header(xml_file, work_id, work_title, author_name)

            # Process each book ONE AT A TIME - memory efficient streaming
            for idx, book_id in enumerate(book_ids, 1):
                # Query book_number from database - handles hierarchical IDs (e.g., 1001 for Book 1, Chapter 1)
                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT book_number FROM books WHERE id = ?", (book_id,))
                result = cursor.fetchone()
                if result:
                    book_num = result[0]
                else:
                    # Fallback for simple numeric IDs
                    try:
                        book_num = int(book_id.split('.')[-1])
                    except ValueError:
                        print(f"  ⚠️  Skipping book with unparseable ID: {book_id}")
                        conn.close()
                        continue
                percent_complete = (idx - 1) / len(book_ids) * 100

                # Get line range for this book
                cursor.execute("SELECT MIN(line_number), MAX(line_number) FROM text_lines WHERE book_id = ?", (book_id,))
                start_line, end_line = cursor.fetchone()
                conn.close()

                # Generate interlinear for THIS book only
                book_results = generator.generate_interlinear(book_id, start_line, end_line)

                # IMMEDIATELY write to both files - streaming!
                _write_book_to_txt(txt_file, book_num, book_results)
                _write_book_to_xml(xml_file, book_num, book_results)

                # Track progress
                total_lines += len(book_results)

            # Write XML footer once at end
            _write_xml_footer(xml_file)

        # Files are closed and flushed - guaranteed written to disk
        print(f"\n\n{'=' * 80}")
        print("COMPLETE!")
        print("=" * 80)
        print(f"Processed {len(book_ids)} books, {total_lines} lines")
        print(f"\nText output: {output_file}")
        print(f"XML output: {xml_output_file}")
        print("=" * 80)

    except Exception as e:
        # Clean up partial files on error
        if output_file.exists():
            output_file.unlink()
        if xml_output_file.exists():
            xml_output_file.unlink()
        print(f"\n{'=' * 80}")
        print(f"  FAILED: Work {work_id}")
        print(f"{'=' * 80}")
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 80}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python generate_latin_interlinear.py <database_path> <output_dir> [work_id]")
        print("Example: python generate_latin_interlinear.py ../../perseus_texts_sample.db ../../interlinear_output phi0690.phi003")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    work_ids = [sys.argv[3]] if len(sys.argv) > 3 else None

    generate_latin_interlinear_translations(db_path, output_dir, work_ids)
