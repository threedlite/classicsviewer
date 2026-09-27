# Mahābhārata in the Sanskrit module: feasibility proposal

**Date:** 2026-09-15 (revised the same day for the exact-alignment requirement;
see section 10)
**Scope:** Sanskrit text + English translation for the Mahābhārata, restricted to
sources whose licence permits commercial redistribution inside the app.
**Requirements set by the user (2026-09-15):**
1. the translation must be aligned to the Sanskrit **exactly**, no
   proportional or approximate mapping;
2. **no human review will be available**, the pipeline must be fully
   automatic;
3. **gaps are acceptable**: a chapter may end up without a translation of its
   own;
4. **no text may be dropped**: every sentence of the translation must appear
   in the output, in order.
**Status:** proposal, nothing implemented. Section 5.5 is the design that
meets all four requirements; sections 5.2 and 5.4 are kept for the record.

Every claim is marked **[verified]** (checked against the repo, the built DB,
the DCS files on disk, or the live web page named in the verification log)
or **[inferred]**.

**Reviewed 2026-09-27.** Every DB and DCS count was re-measured, the Smith
critical-edition files and the nine Gutenberg texts were downloaded and
re-counted, the licence pages were re-fetched, and the build-script claims
were re-read with line numbers. Corrections are marked "Corrected
2026-09-27" in place; section 10 lists them.

---

## 1. Summary

The Mahābhārata is **already in the full Sanskrit build** as a DCS work, but
in a form that is not usable for reading:

- one `text_lines` row per *chapter* (1,995 rows, up to 41,643 characters
  each) and **no English translation**; [verified]
- the 18 Bhagavadgītā chapters (critical edition 6.23–6.40) are stored at the
  **end** of Book 6, lines 100–117, in scrambled order, because DCS labels
  them `MBh, 6, BhaGī 1` … `BhaGī 18` and the loader turns non-numeric
  chapter labels into hash values. [verified in DB]

**What exact alignment can mean with licensed sources.** [verified, section 5]

| Granularity | Achievable? | Why |
|---|---|---|
| Verse-exact | **No** | Ganguli has no verse numbers. Dutt's prose is verse-numbered but exists only as poor OCR of a Calcutta-edition translation, and no free Calcutta e-text exists to bridge its numbering to the critical edition. Every critical-edition-based translation is under copyright. |
| Chapter-exact | **Yes** | The published critical-edition → Ganguli concordance maps every CE chapter to its Ganguli section(s), with verse-level boundaries where a section straddles two chapters. 88 CE chapters need the Ganguli prose split by hand at the boundary the concordance gives. |

The feasible path is:

1. **Keep the DCS text** (CC BY 4.0). Fix the loader so each verse becomes a
   line (73,202 lines instead of 1,995) and so chapter order follows the DCS
   file sequence, which puts the Gītā back in place.
2. **Add Kisari Mohan Ganguli's translation (1883–96)**, public domain, from
   Project Gutenberg, attached **chapter-exactly** via the concordance, with
   the 88 straddling sections split by hand and a build-time validator that
   rejects any chapter without exactly one aligned segment.

No Room schema change is needed. The DCS text derives from the BORI
electronic text, which BORI marks "(C) 1999" without a public licence; DCS
relicenses it CC BY 4.0, and the app already ships it (section 8).

---

## 2. Current state [verified]

Measured from `sanskrit/sanskrit_texts.db` (built 2026-05-21) and the DCS
CoNLL-U files under `data-sources/sanskrit/dcs/data/conllu/files/Mahābhārata/`
(DCS clone at commit `04e0778d`, 2026-03-05).

| Item | Value |
|---|---|
| Work id / author id | `Mahābhārata` / `Mahābhārata` |
| Books (parvans) | 18 |
| `text_lines` rows | 1,995 (one per DCS chapter file) |
| Longest line | 41,643 characters |
| `words` rows | 1,147,887 |
| `translation_segments` rows | 1,995, all interlinear glosses, **no English** |
| DCS CoNLL-U files | 1,995 (one per chapter) |
| DCS sentences (`# text =`) | 168,167 |
| Sentences with `# sent_counter` | 167,648 (519 lack it; 204 of those are the whole of four chapters, 2.15, 2.53, 2.54 and 2.55, which carry no verse numbers at all) |
| Distinct (chapter, `sent_counter`) pairs | **73,202** |
| `sent_subcounter` values | 1–20 (pādas/lines within a verse) |

Why it collapses to chapters: in `create_sanskrit_database_interlinear.py`
the `## chapter:` header `MBh, 1, 1` has three parts, so the parser sets
`verse_num = chapter_num` and `verse_counter = None`, and every sentence in
the file is appended to a single `(book, chapter, chapter)` key. The
per-sentence `# sent_counter` (verse number within the chapter) and
`# sent_subcounter` (pāda within the verse) are never read. [verified]

Judged by the first file of each of the 270 DCS work directories, 153 works
have 2-part citations (verse-per-line today), 97 have 3-part citations and
20 have 4-part citations. All 3-part works are collapsed the same way.
[verified]

### 2.1 How DCS chapters relate to the BORI critical edition [verified]

Chapter files per parvan, DCS vs. John Smith's electronic critical edition
(downloaded 2026-09-15 from bombay.indology.info):

| Parvan | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DCS files | 225 | **73** | 299 | 67 | 197 | 117 | **172** | 69 | 64 | 18 | 27 | 353 | 154 | 96 | 47 | 9 | 3 | 5 | 1,995 |
| Smith CE | 225 | **72** | 299 | 67 | 197 | 117 | **173** | 69 | 64 | 18 | 27 | 353 | 154 | 96 | 47 | 9 | 3 | 5 | 1,995 |

The totals match by coincidence, not chapter for chapter:

- DCS has an extra file `MBh, 2, 0` holding only the Sabhāparvan invocation
  verse (`nārāyaṇaṃ namaskṛtya …`), which the CE prints as an unnumbered
  header.
- DCS has **no** chapter 7.173 (107 verses in Smith's text). DCS 7.172 ends
  at the same verse as Smith's 7.172, so the chapter is missing, not merged.
- The 18 Gītā chapters are labelled `MBh, 6, BhaGī 1` … `18` instead of
  6.23–6.40. Their per-chapter verse counts match Smith's 6.23–6.40 as a
  set.

Verse numbering: comparing the maximum verse number per chapter, DCS and
Smith agree in **1,932 of the 1,972 chapters that can be compared**. Of the
1,995 DCS files, 18 are the Gītā (paired as a set, below), one is `2,0`
(no CE chapter) and four (2.15, 2.53–2.55) have no `sent_counter` at all,
leaving 1,972; 40 differ. They are mostly prose chapters, where DCS cuts
sentences differently (1.3: DCS 140 vs CE 195; 1.90: 30 vs 96; 2.52: 14 vs
37; 9.45: 25 vs 95; 13.135: 50 vs 142). In 1.1, DCS folds the 20
preliminary maṅgala sentences and the `nārāyaṇaṃ namaskṛtya` verse into
verse 1, so CE 1.1.1 is DCS 1.1.2 (DCS maximum 214, CE 210). Smith's text
has 73,815 verse ids (plus one `000` header id, 01001000); DCS has 73,202
distinct numbered verses, but its per-chapter maxima sum to 73,318, so 116
of the gap are numbers DCS skips inside chapters. Of the remaining 497,
the missing 7.173 accounts for 107 and the net difference in the 40
divergent chapters for 304 (CE higher in most); 86 remain unexplained.
[re-measured 2026-09-27 from the downloaded `MBh01–18.txt`; Corrected: the
earlier text said 1,976 pairable, 44 differing, and 217 for the maxima.]

Consequence: the concordance's verse-level split points (section 5) must be
located in the DCS text **by the Sanskrit words at the boundary**, not by
DCS verse number alone, in the 44 chapters where numbering diverges, and
always in chapters 1.1 and 2.0.

The DCS Ādiparvan opens with the same preliminary maṅgala verses that
GRETIL/Smith label `01,000.000*0001` onward, which confirms DCS took its
text from the Tokunaga/Smith e-text rather than from a vulgate. [verified]

### 2.2 The Gītā chapters in the built DB [verified]

`worker_parse_citation_part("BhaGī 4")` (`create_sanskrit_database_interlinear.py:1173-1183`;
a second copy, `parse_citation_part` at `:917-945`, belongs to the
never-called `load_dcs_text`) falls through `int()` and `int(float())` to
`abs(hash(part_str)) % 100000`. The chapter keys are then sorted with
`key=lambda x: int(x) if str(x).isdigit() else x` (`:1527`). The hash
values are already integers in 0–99,999, so they sort *among* the real
chapter numbers by value, not after them; they landed after 117 in this
build because every hash happened to exceed 117, which for a random value
in that range fails about 0.1 % of the time per label. In the built DB,
Book 6 lines 1–22 are CE 6.1–6.22, lines 23–99 are CE 6.41–6.117, and
lines 100–117 are the Gītā in hash order (line 100 is Gītā 18, line 117 is
Gītā 12; re-verified by first words 2026-09-27). Python salts `str` hashes
per process unless `PYTHONHASHSEED` is set, and nothing in the build sets
it (`run_build.sh`, 43 lines, has no such line), so the order can change
between builds. [DB placement verified; cross-build instability inferred
from documented Python behaviour; Corrected 2026-09-27: "sort after" was
the mechanism claimed before.]

The same fallback produces hash-valued **book** numbers for 34 works in the
built DB; see the Rāmāyaṇa proposal.

---

## 3. Sanskrit text sources: licence review

| Source | Edition / numbering | Licence as stated by the source | Usable? |
|---|---|---|---|
| **DCS** (Hellwig), CoNLL-U dump on GitHub | BORI critical edition numbering (see 2.1); sandhi-split tokens, lemma, POS, `Unsandhied` forms, verse ids | `data/readme.md` and `data/conllu/readme.md`: "licensed under the Creative Commons BY 4.0 (CC BY 4.0)". Website impressum (Feb 2026) says CC BY 3.0 Unported. [verified] | **Yes.** Already used and attributed in the app. |
| **John Smith / BORI electronic text** (bombay.indology.info) | The critical edition itself, sandhied, `PPCCCVVVx` ids, "final form" since 2026-06-14 (the Ādiparvan file header nevertheless reads "Last updated: Thu Aug 22 2026") | File header: "Electronic text (C) Bhandarkar Oriental Research Institute, Pune, India, 1999". Site: "made available with BORI's agreement". **No licence grant, no permitted-use statement anywhere on the site.** [re-verified 2026-09-27] | **Not without written permission from BORI.** The notice is a claim of rights, not proof that any exist: whether a faithful transcription of a 1933–66 printed edition attracts its own copyright depends on jurisdiction, and this document does not decide that. |
| **GRETIL** Mahābhārata (Tokunaga/Smith text re-hosted) | Same CE text | File header: "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE." The GRETIL site itself states no licence. GRETIL's Zenodo deposit of the same files (record 6467313, 2022) is tagged CC BY 4.0 with creator "autores varii". [verified] | **Conflicting.** Do not rely on the Zenodo tag. |
| **Sanskrit Wikisource** महाभारतम् | 18 parvans, **2,315** chapters (Ādi 260, Sabhā 103, Āraṇyaka 315, Virāṭa 78, Udyoga 196, Bhīṣma 122, Droṇa 203, Karṇa 101, Śalya 66, Sauptika 18, Strī 27, Śānti 375, Anuśāsana 274, Āśvamedhika 118, Āśramavāsika 41, Mausala 9, Mahāprasthānika 3, Svargārohaṇa 6). Chapter pages carry pāda ids (`1-1-5a`), passages in back-quotes, and a commentary block. Edition not stated and not identified; it is neither the critical edition nor the numbering Ganguli follows (Ganguli's Ādi has 236 sections). In chapter 1.1, 245 of 690 DCS half-verses occur verbatim; in 1.2, 367 of 960. | Footer: CC BY-SA 4.0 [verified] | Licence fine, but it bridges to nothing: not to DCS, not to Ganguli. No morphological annotation. |
| sanskritdocuments.org, SARIT (Kumbhakonam), TITUS | Southern recension / restricted | NC or personal-use terms (per `LICENSE_COMPLIANCE.md`) | No. |

**Conclusion:** DCS is the only text that is both licensed for commercial use
and aligned to a citable edition, and it is what the app already ships.

Note on `sanskrit/LICENSE_COMPLIANCE.md` (that is its path; there is no
copy at the repo root): it lists GRETIL as CC BY-NC-SA 4.0 (`:173-175`).
The live GRETIL page carries no licence text at all, and its Zenodo deposit
says CC BY 4.0. Neither confirms the document's claim. The same file's
verification checklist (`:190`) accepts "Public Domain, CC0, CC BY, CC
BY-SA, MIT", and the app already ships the Wikisource Gītā under CC BY-SA
4.0 (`:82`, `:203`), which matters for the Wikisource question in the
Rāmāyaṇa proposal.

---

## 4. English translation sources: licence review

| Translation | Years | Basis | Verse numbers? | Licence | Availability | Usable for exact alignment? |
|---|---|---|---|---|---|---|
| **Kisari Mohan Ganguli** (publ. P. C. Roy) | 1883–1896 | Vulgate (Calcutta/Bombay), prose, numbered "Sections" per parva | **No** [verified] | Public domain. Gutenberg asserts only "Public domain in the USA"; worldwide status rests on the translator's death (Ganguli d. 1908), which clears life + 70 and life + 100 terms everywhere. [verified: PG pages; death year from PG author record] | Project Gutenberg **15474** (Vol. 1, Books 1–3), **15475** (Vol. 2), **15476** (Vol. 3), **15477** (Vol. 4) [titles and files re-verified 2026-09-27; 15,262,892 bytes together] | **Chapter-exact only**, via the concordance (section 5). |
| **Manmatha Nath Dutt** | 1895–1905 | Calcutta edition, prose | **Yes**: verse-numbered paragraphs ("243.", "244." …) [verified in OCR] | Public domain (author 1855–1912) | archive.org Google-OCR only (e.g. `in.ernet.dli.2015.142209`, Ādi Parva, 4.0 MB of text); OCR quality poor ("Bralmiatias"), chapter headings partly lost [verified] | In principle the only route to verse-exact, but it needs full OCR correction of 18 parvas **and** a Calcutta-edition → CE verse concordance, which does not exist and cannot be built without a licensed Calcutta e-text. Not proposed. |
| J. A. B. van Buitenen (Chicago) | 1973– | Critical edition | yes | Copyright | 4 of 10 volumes | No. |
| Clay Sanskrit Library | 2005–2009 | Vulgate | yes | Copyright | 15 of 32 volumes | No. |
| Bibek Debroy (Penguin) | 2010–2014 | Critical edition, complete | yes | Copyright | — | No. |
| P. Lal | 1999–2020 [dates not verified] | — | — | Copyright | — | No. |

Project Gutenberg terms [verified]: strip the PG header, licence and name
and the text is unrestricted. The build must do that; the app must not use
the PG name.

---

## 5. Exact alignment: what the data supports

### 5.1 The concordance [verified from the extracted PDF]

*Concordance of Critical Edition and Ganguli/Roy translation*, appendix to
Brodbeck & Black (eds), *Gender and Narrative in the Mahābhārata*, Routledge
2007, pp. 279 ff. (attribution confirmed by the Routledge catalogue; the PDF
circulated on the INDOLOGY list, 2019-07-02). It is one-directional (CE →
Ganguli) and says so: Ganguli translates vulgate passages that the CE
relegates to its apparatus, and those are not traced.

| Measure | Value |
|---|---|
| Mapping rows, Books 1–18 | 388 |
| Rows mapping whole CE chapter ranges to whole section ranges | 201 |
| Rows with a verse-level boundary (e.g. `13.1–28 → 13`, `13.29–34 → 14`) | 187 |
| **Distinct CE chapters that contain a Ganguli section boundary** | **88** |

Split rows per book: 1: 28, 2: 14, 3: 22, 4: 8, 5: 7, 6: 16, 7: 22, 8: 38,
9: 1, 11: 1, 12: 24, 13: 4, 14: 2; Books 10 and 15–18 have none.

Ganguli section counts by last section numeral (heading counts run one to
three lower where headings are indented or missing in the transcription):
Ādi 236, Sabhā 80, Vana 313, Udyoga 199, Bhīṣma 124, Droṇa 203, Śānti 365,
Āśvamedhika 92, Āśramavāsika 39; about 1,883 section headings across the
four volumes. [verified]

### 5.2 Chapter-exact procedure

1. **Concordance as data.** A CSV `ce_chapter, ce_verse_from, ce_verse_to,
   ganguli_section` with 388 rows, consumed by the main build script. Its
   source is the user's decision (section 8): transcribe the published table,
   or rebuild it by hand chapter by chapter.
2. **Whole-chapter rows (201 rows).** The section text becomes the segment
   for the chapter(s) it covers. A CE chapter covered by a section that also
   covers a neighbouring chapter gets that section as its segment; the
   segment is shared, not duplicated, via `translation_lookup`.
3. **Straddling sections (88 chapters).** The concordance names the CE
   verse at which the Ganguli section crosses into the next chapter. A
   human reads the Ganguli section and marks the sentence where that verse
   begins, using the Sanskrit of that verse (from DCS, located by its words
   because of the numbering caveat in 2.1). The mark is stored as a
   character offset in a hand-maintained split file that the build reads;
   the build fails if a split offset does not fall on a sentence boundary
   or if any straddling section lacks a mark.
4. **Validation, mechanical, every build:**
   - every CE chapter (1,995 files, including `2,0` and the 18 Gītā
     chapters) has exactly one segment;
   - section numbers used are monotonic within each parva and every section
     is used at least once;
   - speaker-cue check: where a CE chapter opens with `X uvāca` and the
     mapped Ganguli text opens with "X said/continued", the names must
     agree after a fixed name table (Vaiśampāyana/Vaisampayana, Sauti,
     Janamejaya, …). Mismatches are listed and block the build until
     acknowledged in the split file.
5. **Human sign-off** of the 88 splits and of every speaker-cue mismatch,
   recorded in the repo.

Estimated manual effort for step 3: 88 chapters at roughly 15–30 minutes
each, 25–45 hours, by someone who can read the Sanskrit verse at the
boundary. [inferred]

### 5.3 What is not on offer

- Proportional or nearest-neighbour mapping (rejected by the requirement).
- Verse-level alignment of Ganguli: the prose has no verse markers, and
  splitting 73,202 verses by hand is not a realistic task.
- Using Sanskrit Wikisource as a bridge: its numbering matches neither side
  (section 3).

### 5.4 Reusing the sibling Diodorus pipeline (`~/git/diodorus`) [verified 2026-09-15]

Diodorus aligns Greek/Latin sections to public-domain English by: CTS-number
anchors → segmental monotonic DP over section embeddings plus a length prior
→ entity anchoring (capitalised Greek names, transliterated, fuzzy-matched
against English names) → a PMI lexical table learned from the first pass →
refinement that splits an English section at sentence boundaries to serve
several source sections → integrity check (no text lost or reordered) →
clickable quality heatmap. Its own rules state that "imprecise matches are
acceptable" and its quality is reported per section, not guaranteed: with a
purpose-trained Greek model its high-confidence share ranges from 100%
(Marcus Aurelius) to 65% (Diodorus) to 3% (Aristophanes). It is a best-effort
engine with honest scoring, not an exact aligner. [verified from
`CLAUDE.md`, `PROJECT_DOCUMENTATION.md`, `final/alignment_quality_summary.txt`]

What transfers to Sanskrit, measured on the Gītā (DCS `BhaGī` chapters,
verse-numbered, against Besant's verse-numbered translation):

| Diodorus signal | Sanskrit adaptation | Pilot result |
|---|---|---|
| Embedding similarity | No Sanskrit model exists. Baseline `paraphrase-multilingual-MiniLM-L12-v2` | Verse top-1 retrieval 9.0% overall, 25% within chapter; chapter-level 9 of 18. Weak but non-zero (the same baseline scored 0.4% on Greek). |
| Lexical overlap (PMI table) | DCS dictionary glosses (164,553 lemmas, 100% coverage of Gītā lemmas) used directly as the translation table | Verse top-1 19.8% overall, 43% within chapter (crude IDF scoring). |
| Entity anchoring | 35,523 DCS lemmas whose gloss reads "name of …", `unidecode` on the IAST lemma, `rapidfuzz.partial_ratio ≥ 85` against capitalised English words | CE 1.1 vs Ganguli section 1: 396 of 483 name-lemmas matched, 63 against a wrong section. 1.2: 374 vs 82. 1.3: 54 vs 5. Short chapters are weaker: 1.4: 10 vs 6; 1.5: 37 vs 27. |
| CTS anchors / `concordance.json` forced matches | The concordance CSV of 5.1, expressed as English `cts_ref`s | Supported by the existing `try_cts_match` (DP mode) and `_load_concordance` (pairwise mode). |
| Refinement (`_refine_group` / `_optimal_split`) | Sentence-split the 88 straddling Ganguli sections, choose the split by embedding + entity bonus | Not run; this is the step that would *propose* the 88 splits for human confirmation. |
| Integrity checker | Unchanged | Guarantees completeness and order, not correctness of pairing. |

A Sanskrit embedding model could be trained with Diodorus's documented
recipe (XLM-R MLM continued pre-training, then contrastive fine-tuning on
~19k parallel pairs, ~10.5 h on an M4). Free parallel data at section level:
Gītā (700 × 2 translations), Rig Veda (10,218 Griffith stanzas), the DCS
Atharvaveda translations, Bühler's Manusmṛti, the SBE Upaniṣads, plus the
chapter-level epic pairs produced by the concordance itself. Whether that
reaches Greek's 95% top-1 is unknown until tried. [inferred]

**Conclusion for the exactness requirement.** Diodorus can serve as the
*proposal engine* and as an *independent second opinion* (its DP with the
concordance as fixed anchors, entity anchoring from DCS name-lemmas, and its
refinement step to propose the 88 split points), and its integrity checker
and heatmap direct the human review. It cannot replace the concordance or
the human sign-off, because nothing in it certifies a pairing as correct; it
only scores it. The procedure in 5.2 stands, with Diodorus reducing step 3
from "find the split" to "confirm the proposed split".

Practical notes: Diodorus's `source_language` accepts only `greek`/`latin`
and its entity regex assumes Greek capitals, so a `sanskrit` branch is needed
(DCS lemma list as the name source, no capitalisation); its output is
Perseus TEI (`*.perseus-eng80.xml`) plus JSON alignments, and no ingestion
path for those exists in the Sanskrit module (nothing in `sanskrit/` or
`greek/build_modules` reads `eng80` files) [verified by grep]; the
alignment JSON would be consumed by the Sanskrit build directly.

### 5.5 Fully automatic design: anchors and intervals (meets requirements 1–4)

**Principle.** A translation section is attached to a single CE chapter only
when that pairing is *known*, not scored. Every other section is attached to
the **interval of chapters between the nearest known pairings on either
side**. Because both texts are in narrative order, a section that lies
between two known anchors in the English can only translate chapters that
lie between the same anchors in the Sanskrit. So every section is placed
(nothing dropped), no section is placed where it cannot belong (never
wrong), and uncertainty shows up only as coarser granularity (a gap, in the
user's sense: the chapter has no translation of its own, but the reader
sees the block that contains it). No threshold, no judgement, no human.

**What counts as "known" for the Mahābhārata.**

| Source of anchor | Chapters | Nature |
|---|---|---|
| Concordance whole-chapter rows (201 rows) | In the 13 books whose PDF text extracts cleanly (1–10, 12–14: 1,904 chapters), **1,817** chapters map to a whole section or run of sections and coverage is complete. Books 11 and 15–18 (91 chapters) extract with two-column artefacts (page numbers and neighbouring-column figures read as rows; 10 chapters of Books 15–16 left uncovered) and need a column-aware extraction of the same PDF, which is mechanical. [verified] | Published scholarship transcribed mechanically from the PDF (section 5.1). Exact at chapter granularity. |
| Concordance verse-split rows (187 rows) | **87** chapters in the clean books, 88 overall, share a section with a neighbour | The section is attached to **both** chapters (an interval of two). Exact as a superset; no automatic splitting. |
| The Gītā (18 chapters) | 6.23–6.40 | Besant's verse-numbered translation is already in the build and could be attached verse-exactly by number; Ganguli's section is attached to the interval as well. |
| `MBh, 2, 0` and the absent 7.173 | 2 | `2,0` receives no segment of its own (its invocation is untranslated by Ganguli as a separate unit); Ganguli's text for 7.173 is attached to the interval ending at 7.172. Nothing dropped. |

With the concordance accepted as data, the Mahābhārata needs **no machine
scoring at all**: in the cleanly extracted books, 1,817 chapters at chapter
granularity and 87 at two-chapter granularity, deterministically; the
remaining 91 chapters follow once the five short books are re-extracted
column-aware. [counts verified from the extracted concordance rows]

**Machine self-verification of the concordance (optional safeguard).**
Because no human will check the transcription, the build can run the
entity check of 5.4 on every whole-chapter row and *flag* rows where the
assigned section is not the best-scoring neighbour in both directions.
Measured on Ādiparvan's 199 usable 1:1 rows with an IDF-weighted,
size-normalised name score and a 25% margin: 37 confirmed (19%), 50 best
but without margin, 112 with a neighbour scoring higher, the last group
dominated by Ganguli's two opening index sections that name everyone in
the epic. [verified] The signal is therefore **not** strong enough to
override the concordance automatically, only to list suspicious rows in
the build report. The concordance remains the authority; its transcription
is checked by re-extracting the PDF text and comparing row counts per book
(28/29, 14/8, … as listed in 5.1).

**Output shape.** `translation_segments` rows with `start_line`/`end_line`
spanning the interval's verse lines; `translation_lookup` rows for every
line in the interval. This is the existing schema; no Room change.

**Build validation (mechanical, blocks the build).**
- every Ganguli section appears exactly once, in order (hash of the
  concatenated segments equals the hash of the stripped Gutenberg text, as
  Diodorus's integrity checker does);
- every CE chapter is covered by at least one interval;
- intervals are monotonic and non-crossing;
- concordance row count per book equals the count extracted from the PDF.

---

## 6. Proposed pipeline changes

All changes go into `create_sanskrit_database_interlinear.py` and the files
it reads. No standalone scripts. No manual steps beyond `./run_build.sh`
(the hand-made split file and concordance CSV are inputs, checked in).

### 6.1 Verse-level lines and canonical chapter order for DCS works

- For 3-part `## chapter:` headers, read `# sent_counter` as the verse
  number and group sentences by `(book, chapter, sent_counter)`.
- Sentences with no `sent_counter` (519 in the Mahābhārata) attach to the
  preceding verse and are counted in the build report.
- Replace the `hash()` fallback for non-numeric labels with ordering by the
  DCS file sequence number (`-0000-` … `-1994-`; `MBh, 2, 0` is file 0225,
  the Gītā files sit between 6.22 and 6.41), keeping the label string for
  display. No Gītā-specific code.
- Store the chapter/verse citation for display. `milestone_line_ranges
  (work_id, milestone, start_line, end_line)` is created by the Sanskrit
  build (`:547-554`) but never written to, and **neither the Android app nor
  the iOS app reads it** (no match in `app/src` or `ios/`). Using it for
  chapter display therefore needs app work on both platforms, or another
  carrier for the citation. [verified 2026-09-27; Corrected: was
  "needs checking"]
- This changes all 97 three-part works and every hash-labelled work.

### 6.2 Ganguli import

Download script for the four Gutenberg files; strip PG boilerplate; split on
parva headings and `SECTION <roman>` lines (allow leading whitespace); apply
the concordance CSV and the split file; emit `translator = "Kisari Mohan
Ganguli"` segments and `translation_lookup` rows for shared sections;
footnotes handled per decision in section 8.

### 6.3 The existing external-translation path does not work [verified]

The build maps nine DCS works to translation files (`translation_map`,
`:2315-2325`: Olivelle, Oldenberg, Eggeling, Griffith for the
Vājasaneyisaṃhitā). In the built DB **none of those translators has a
single `translation_segments` row**; only Besant (697), Arnold (18),
Griffith for the Rig Veda (10,473) and the interlinear generator (210,204)
are present, yet `authors.has_translations` is 1 for **eight** of the nine
works. Cause, now read in the code: the worker loads the file with `int`
keys (`book = int(...)`, `chapter = int(...)`, `:1347-1351`) and the writer
looks up `str(book_num_int)` and `str(chapter_num_int)` (`:1569-1570`), so
the INSERT at `:1575-1578` is unreachable; `has_translations` is set from
the file path alone before any row is written (`:1494-1498`). The ninth,
`Vājasaneyīsaṃhitā` (long ī, no parenthetical), never matches the file's
`## text:` header `Vājasaneyisaṃhitā (Mādhyandina)`, so it gets no file and
is not flagged either. Besant, Arnold and Griffith (RV) work because they go
through `load_bhagavad_gita` (`:630`) and `load_rigveda` (`:762`), which
keep `int` keys on both sides. [outcome and cause verified 2026-09-27;
Corrected: "nine" flagged was wrong, and the cause was marked inferred]
Ganguli would go through the same path, so this is fixed first, and the
build must fail when a mapped translation yields zero segments.

### 6.4 Documentation and attribution

`LICENSE_COMPLIANCE.md` (Ganguli; DCS/BORI derivation note),
`LicenseActivity.kt`, `DCS_TEXTS_CATALOG.md`, `README.md`.

### 6.5 Testing

- `test`-mode build with a CSV of `DCS,Mahābhārata` only. Verify per-book
  line counts against DCS verse counts; Book 6 lines 23–40 are the Gītā in
  order; the validator in 5.2 passes; ten chapters spread across the epic
  read correctly against the Gutenberg text.
- `data-prep/text_integrity/audit.py` covers only the Perseus-family
  corpora [verified]; record before/after per-work line and word counts for
  the Sanskrit DB in the change review.

---

## 7. Effort and risk

| Work item | Estimate | Risk |
|---|---|---|
| 6.1 verse-level loader + ordering fix | 2–3 days | Medium: 97 works plus hash-labelled works; `2,0`, absent 7.173 and the 519 unnumbered sentences need explicit handling. |
| 6.3 fix translation path | 0.5–1 day | Prerequisite. |
| Concordance CSV | 0.5 day (transcription) or weeks (rebuild by hand) | Copyright decision. |
| 6.2 Ganguli parser + validator | 2 days | Low. |
| 88 manual splits + sign-off | 25–45 hours of a Sanskrit reader | The exactness of the result rests on this step. |
| Full rebuild | ~3 h today | Not measured after row growth. |

Ganguli adds about 14 MB of English uncompressed (the four Gutenberg files
total 15.3 MB with boilerplate). [verified]

---

## 8. Decisions needed from the user

1. **BORI copyright on the underlying e-text**: accept DCS's CC BY 4.0 as
   sufficient, or ask BORI / John Smith before making the epic prominent.
2. **Concordance source**: transcribe the Brodbeck & Black table (copyright
   judgement) or rebuild it by hand. Facts to weigh, not legal advice: the
   table records which CE chapter corresponds to which Ganguli section,
   which is factual correspondence rather than expression; in the US such
   facts are not protected (Feist, 1991), and any thin copyright would lie
   in selection or arrangement, of which a complete one-to-one concordance
   has little. The UK/EU sui generis database right, if it applied to a
   2007 Routledge appendix at all, runs 15 years from publication and so
   ended in 2022. The book's table of contents confirms the appendix
   ("Appendix: Concordance of Critical Edition and Ganguli/Roy
   translation"; Routledge catalogue, re-fetched 2026-09-27).
3. **Ganguli footnotes**: drop, inline, or separate segments.
4. **Who does the 88 splits** and signs them off.
5. **Missing CE 7.173**: leave the gap and say so in the work description.
6. **Scope of 6.1**: it changes every 3-part DCS work and every
   hash-labelled work.

---

## 9. Verification log (2026-09-15)

Local: `sanskrit/sanskrit_texts.db` (counts; Book 6 Gītā placement;
translators present; hash-numbered books); DCS clone `04e0778d` (headers of
270 works, per-chapter maximum `sent_counter`, `BhaGī` headers, `MBh, 2, 0`,
absence of 7.173); `create_sanskrit_database_interlinear.py` (parser,
`worker_parse_citation_part`, translation loading, `write_parsed_work_to_db`,
`translation_map`); `data-prep/text_integrity/audit.py`.

Web (fetched this session): bombay.indology.info Mahābhārata statement,
welcome and `text/UD/MBh01–18.txt`; GRETIL `gretil.html` and
`mbh_01_u.htm`; Zenodo record 6467313 API; DCS impressum;
sa.wikisource.org महाभारतम् (per-parvan counts), `महाभारतम्-01-आदिपर्व-001`
and `-002` (format, commentary, verbatim overlap with DCS);
en.wikisource.org The_Mahabharata; Gutenberg 15474–15477 and the licence
page; the INDOLOGY concordance PDF (text-extracted, rows counted) and the
Routledge catalogue entry; archive.org metadata and `_djvu.txt` of
`in.ernet.dli.2015.142209` (Dutt, Ādi Parva); shreevatsa.net survey.

Not reachable: sacred-texts.com (Cloudflare). Wikisource pages must be
fetched with a descriptive `User-Agent`; the default one intermittently
returns Wikimedia error pages. [verified]

---

## 10. Revision history

**Re-check (same day).** Corrected: chapter counts "match except two
parvans" (they match in total only: extra `2,0`, missing 7.173, `BhaGī`
labels); "verse numbers match" (1,932 of 1,976); the Gītā placement; Ganguli
section counts (by numeral); Wikisource chapter total (2,315); the
translation-path finding (zero rows, not one row); concordance attribution.

**Exact-alignment revision.** Replaced the four alignment options with the
chapter-exact procedure in 5.2, added the measured concordance structure
(388 rows, 187 verse-split rows, 88 straddled chapters), the Wikisource
Mahābhārata format and overlap measurements, and the Dutt OCR findings, and
stated plainly that verse-exact alignment is not achievable with any
licensed translation.

**Diodorus revision.** Added 5.4: what the sibling Diodorus alignment
pipeline can and cannot contribute, with three Gītā pilots (embedding
baseline, DCS-gloss lexical overlap, DCS name-lemma entity anchoring).

**No-human revision.** Requirements 2–4 recorded. Added 5.5, the
anchors-and-intervals design: concordance rows as anchors, straddled
chapters as two-chapter intervals, no automatic splitting, no thresholds;
entity self-verification measured (19% confirmed on Ādi) and demoted to a
report-only safeguard.

**Review, 2026-09-27.** Re-measured and confirmed: all section 2 counts
(1,995 files, 168,167 sentences, 519 unnumbered, 73,202 verses, per-parvan
file counts, `2,0`, absent 7.173, Gītā between 6.22 and 6.41, 153/97/20
header split); Smith's 1,995 chapters (72 in Book 2, 173 in Book 7),
73,815 verse ids, 107 verses in 7.173; DB rows, longest line, `words`,
Gītā placement at lines 100–117; Ganguli's 1,883 section headings and the
last numerals per parva; the Zenodo `cc-by-4.0` tag with creator "autores
varii"; the DCS impressum's CC BY 3.0; the BORI notice and statement; the
Wikisource CC BY-SA 4.0 footer and Ādiparvan's 260 chapters; the four
Gutenberg records and their 15.3 MB. Corrected: 1,972 comparable chapters
and 40 divergent, not 1,976 and 44, with four chapters lacking verse
numbers entirely; the 613-verse decomposition; the hash sort mechanism;
eight, not nine, works flagged `has_translations`; the translation-path
cause is now verified with line numbers; `milestone_line_ranges` is
written by nothing and read by neither app; `LICENSE_COMPLIANCE.md` lives
under `sanskrit/`. Added: worldwide public-domain reasoning for Ganguli;
facts on the concordance's legal status; the Ādiparvan file's August 2026
update date.
