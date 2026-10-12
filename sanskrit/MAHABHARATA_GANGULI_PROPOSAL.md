# Mahābhārata with the Ganguli translation: implementation proposal

**Date:** 2026-10-09
**Status:** implemented 2026-10-09 (same day); see section 11 for what was
built and where it departs from the plan below.
**Builds on:** `sanskrit/MAHABHARATA_FEASIBILITY_PROPOSAL.md` (2026-09-15, reviewed
2026-09-27). That document holds the measurements of the DCS text, the
concordance, and the alignment design. This one answers two narrower
questions:

1. Do the Sanskrit text sources listed in `maha.txt` (repo root) change the
   choice of Sanskrit text?
2. What exactly is built to add the Mahābhārata with the Project Gutenberg
   edition of Kisari Mohan Ganguli's English translation?

Every claim is marked **[verified]** (checked today against the repo, the
built DB, the files on disk, or a page fetched today) or **[inferred]**.
Where a fact comes from the September document and was not re-measured, it
is marked **[Sept, not re-measured]**.

**Standing requirements** (recorded 2026-09-15 in the feasibility proposal
and assumed to still hold): exact alignment only, no proportional mapping;
fully automatic pipeline, no human review; gaps acceptable; no translation
text dropped.

---

## 1. Summary

- **Nothing changed in the repo since September.** The Sanskrit build
  script, `run_build.sh` and `LICENSE_COMPLIANCE.md` have no commits since
  2026-09-15, the DCS clone is still at `04e0778d` (2026-03-05), and the
  built DB is still the 2026-05-21 one with the Mahābhārata collapsed to
  1,995 chapter-long lines and no English. [verified]
- **None of the five sources in `maha.txt` replaces DCS.** Two of the
  claims in `maha.txt` are contradicted by the sources themselves
  (section 2). SARIT's Mahābhārata is genuinely CC BY-SA 3.0, which
  corrects an entry in `LICENSE_COMPLIANCE.md`, but it is the Southern
  recension (Kumbhakonam 1906–10), with 2,318 chapters against the critical
  edition's 1,995, so it aligns neither with the DCS annotation nor with the
  published critical-edition → Ganguli concordance. [verified]
- **Recommendation:** keep the DCS text (CC BY 4.0, already shipped), load
  it at verse granularity, and attach Ganguli's translation from Gutenberg
  15474–15477 chapter-exactly using the concordance, with the
  anchors-and-intervals rule from the feasibility proposal's section 5.5.
  No Room schema change. [design; sizes verified]
- The one unresolved licence question remains the BORI notice on the
  electronic critical edition that DCS derives from. No source in
  `maha.txt` resolves it; sanskritdocuments.org states outright that "BORI
  holds copyright on the text". [verified]

---

## 2. The sources named in `maha.txt`, checked

`maha.txt` is an unattributed summary. Each of its five claims was checked
against the live site today.

| # | `maha.txt` says | What the source actually says today | Edition | Usable as the app's text? |
|---|---|---|---|---|
| 1a | Internet Sacred Text Archive hosts the Tokunaga/Smith text and it is "explicitly designated as Public Domain" | The index page (archived copy, 2024; the live site is behind a Cloudflare challenge) says only that the text "is derived from electronic files created by Prof. Muneo Tokunaga of Kyoto and edited by John D. Smith". **No public-domain designation appears on the index page, the chapter pages, or the site's copyright page for this text.** The site's general copyright page says "most of the files at this site are in the public domain in the United States" and that some files "are copyrighted but released by their copyright holders for non-commercial use", without saying which group this text is in. The same index page notes it could not cross-reference the chapters to Ganguli "due to the mismatch in number of chapters per book". The Devanagari on the chapter pages is a machine conversion with defects (e.g. नरॊत्तमम for नरोत्तमम्, dropped final virāma). [verified] | Critical edition (Tokunaga/Smith) | **No.** The claim is not supported, and the text is the same BORI-derived e-text with the same open question. The conversion defects would also need repair. |
| 1b | sanskritdocuments.org hosts the same data "as open-access, raw e-text files" | The Mahābhārata page says the files are the CSX files "prepared by Prof. John Smith based on the original encoding of Mahabharata by Prof. Muneo Tokunaga", converted in 1998. The site FAQ says: "BORI holds copyright on the text", that texts are "meant to be used for personal" study, and not for "commercial purpose without permission". [verified] | Critical edition (1998 conversion, older than Smith's current files) | **No.** The site itself asserts BORI's copyright and a personal-use restriction. |
| 2 | SARIT distributes the Southern Recension under CC BY-SA 3.0 Unported, commercial use permitted | **Confirmed.** `mahabharata-devanagari.xml` in `github.com/sarit/SARIT-corpus` carries a TEI `<availability>` naming CC BY-SA 3.0 Unported. Source: T. R. Krishnacharya's Kumbhakonam edition, 1906–1910, 17 volumes. 38.6 MB; 18 parvans; **2,318 chapters** (Ādi 260, Sabhā 103, Āraṇya 315, Virāṭa 78, Udyoga 196, Bhīṣma 122, Droṇa 203, Karṇa 104, Śalya 67, Sauptika 18, Strī 27, Śānti 375, Anuśāsana 274, Āśvamedhika 118, Mausala 9, Āśramavāsika 41, Mahāprasthānika 3, Svargārohaṇa 5); 98,676 `<lg>` verse groups. The header warns that the verse ids "are just unique", not guaranteed correct. [verified] | Southern recension | **Licence yes, edition no.** Chapter counts match the Sanskrit Wikisource text (2,315 chapters, same per-parvan figures except Karṇa and Śalya), so Wikisource appears to be the same edition [inferred]. Neither matches the critical edition (1,995 chapters) that DCS annotates, nor Ganguli's vulgate (Ādi 236 sections), nor the concordance. There is no published Kumbhakonam → Ganguli concordance. |
| 3a | Internet Archive provides "full text-dumps (.txt), ePUB, and OCR files of all 18 Parvas of the Sanskrit BORI edition" | The INDOLOGY thread of March 2024 lists the 19 BORI volumes on archive.org as **PDF scans** from the Digital Library of India. The .txt/ePUB that archive.org derives from a scan is its own OCR output; for Devanagari critical-apparatus pages that is not an e-text, and no one on the thread claims otherwise. The thread's view on copyright is one member's reading of the Indian Copyright Act for volumes published before 1958, not a statement by BORI. [verified] | Critical edition, printed | **No.** Scans, not text. |
| 3b | Maharishi University of Management offers a "complete, unencumbered Public Domain PDF compilation" | `vedicreserve.miu.edu` offers 18 per-parvan PDFs. Mausalaparvan (20 pages, 101 KB) opens with the critical edition's 16.1.1 (*ṣaṭtriṃśe tv atha saṃprāpte varṣe kauravanandanaḥ*), so the text is the critical edition [inferred from the first verse]. The PDF uses a legacy non-Unicode Devanagari font: extracted text is unreadable glyph codes. **No licence, copyright or public-domain statement appears on the index or the itihāsa page.** [verified] | Critical edition, typeset | **No.** Not extractable without a font-encoding conversion, no licence statement, and the same BORI question. |

**Conclusion.** DCS remains the only Sanskrit text that is (a) licensed for
commercial redistribution by its publisher, (b) in the critical edition's
numbering, which the only usable Ganguli concordance is keyed to, and (c)
morphologically annotated, which the interlinear layer needs. Section 3 of
the feasibility proposal already reached this conclusion for DCS, Smith,
GRETIL and Wikisource; `maha.txt` adds SARIT and MIU, and neither changes it.

**Documentation correction.** `LICENSE_COMPLIANCE.md:177-179` lists SARIT as
"CC BY-NC-SA". The SARIT Mahābhārata file is CC BY-SA 3.0, no NC. The entry
should be corrected to say that SARIT files carry per-file licences and
that this one is CC BY-SA 3.0, while keeping the "not used" status for the
edition reason above. [verified]

---

## 3. The translation: Ganguli on Project Gutenberg [verified today]

| Gutenberg # | Title | Books | Plain-text size | `SECTION` headings | `[n]` footnote markers |
|---|---|---|---|---|---|
| 15474 | The Mahabharata of Krishna-Dwaipayana Vyasa, Volume 1 | 1–3 | 3.78 MB | 627 | 122 |
| 15475 | Volume 2 | 4–7 | 4.05 MB | 595 | 840 |
| 15476 | Volume 3 | 8–12 | 4.86 MB | 363 | 1,944 |
| 15477 | Volume 4 | 13–18 | 2.62 MB | 299 | 916 |
| | | | **15.3 MB** | **1,884** | **3,822** |

Translator: Kisari Mohan Ganguli (1883–1896); Gutenberg marks each
"Public domain in the USA"; Ganguli died in 1908 [Sept, not re-measured],
which clears life + 70 and life + 100 terms. Gutenberg's terms: strip the
header, the licence and the Project Gutenberg name and the text is
unrestricted. The build must do the stripping; the app must not use the
name.

Gutenberg also carries five older per-book releases of the same
translation (7864 Ādi, 7965 Sabhā, 11894 Vana part 1, 12333 Vana part 2,
12058 Virāṭa). They add nothing; the four volumes are complete. [verified]

Structure of the plain-text files, from today's download:

- `*** START OF` / `*** END OF` markers, one each per file.
- `BOOK n` heading lines for every book 1–18 across the four files.
- A `<NAME> PARVA` heading after each `BOOK n` line (Ādi has two, one in the
  front matter).
- `SECTION <roman>` lines, 1,884 in all, each on its own line with no other
  text.
- Footnotes: inline markers `[n]` in the prose, resolved in `FOOTNOTES`
  blocks (`1. …`, `2. …`) that appear at least at parva ends; eleven such
  blocks were found by a line-start match, fewer than the 18 parvas, so
  blocks also occur elsewhere and the parser must not assume one per parva.
  [verified by count; placement inferred]

Section counts per parva by last numeral (Ādi 236, Sabhā 80, Vana 313,
Udyoga 199, Bhīṣma 124, Droṇa 203, Śānti 365, Āśvamedhika 92,
Āśramavāsika 39) are from the September measurement. [Sept, not
re-measured]

---

## 4. The Sanskrit text: DCS, loaded at verse level

Facts carried from the feasibility proposal and re-checked today where
cheap:

- 1,995 CoNLL-U files under
  `data-sources/sanskrit/dcs/data/conllu/files/Mahābhārata/` (plus 1,995
  `.conllu_parsed` siblings). [verified]
- Each sentence carries `# sent_counter` (verse within chapter) and
  `# sent_subcounter` (pāda within verse); the loader ignores both and
  keys every sentence of a three-part chapter header on
  `(book, chapter, chapter)`, which is why each chapter is one line
  (`create_sanskrit_database_interlinear.py:1222-1243`). [verified]
- The displayed line is built from the `Unsandhied` word tokens, not from
  the `# text =` line (`:1533-1540`). The reader therefore sees
  sandhi-split, compound-split text (जयति पराशर सूनुः … rather than
  जयति पराशरसूनुः …). This is how every DCS work is shown today and is
  **not changed by this proposal**; it is noted because `maha.txt`'s
  sources are all sandhied texts and someone comparing them will notice
  the difference. [verified]
- 73,202 distinct numbered verses against 73,815 verse ids in Smith's
  electronic critical edition; 519 sentences without `sent_counter`;
  extra file `MBh, 2, 0`; no file for critical-edition chapter 7.173 (107
  verses); 40 prose chapters cut into sentences differently from the
  printed edition; the 18 Gītā chapters labelled `BhaGī 1–18` and placed
  by `hash()`. So DCS is the critical edition nearly complete, not the
  longer vulgate Ganguli translated. [Sept, not re-measured]
- **DCS has no English translation of the Mahābhārata.** The 17 files in
  `data-sources/sanskrit/translations/` cover Upaniṣads, gṛhyasūtras and
  similar works, none of them the epic. In the built DB the only
  `translation_segments` rows for the Mahābhārata are the 1,995
  machine-generated interlinear glosses, one per chapter. [verified]

**Display precedent for chapter and verse.** The Rig Veda, the one
three-level work already loaded verse-per-line, carries its citation
inside `line_text` as a prefix: `[1.1.1] अग्निम् ईले …`
(`create_sanskrit_database_interlinear.py:885`; verified in the DB). The
Android and iOS code does not parse that prefix; it is displayed as part of
the line. [verified by grep of `app/src/main/java`] The Mahābhārata will
use the same convention, `[parvan.chapter.verse]`, so no app change is
needed for the citation to be visible. `milestone_line_ranges` remains
unused, as before.

---

## 5. Design

### 5.1 Data shape

| Table | Rows for the Mahābhārata | Notes |
|---|---|---|
| `authors` / `works` | unchanged ids `Mahābhārata` | `has_translations` set to 1 **only after** Ganguli rows are written, not from a file path (fixes the `:1494-1498` pattern). |
| `books` | 18 (parvans), unchanged | |
| `text_lines` | ~73,200 (one per DCS verse; the 519 unnumbered sentences join the preceding verse) | `line_number` continuous within a parvan, as the Rig Veda does within a maṇḍala; `line_text` prefixed `[p.c.v]`. |
| `words` | ~1.15 M, unchanged in count | `line_number` and `word_position` now refer to verse lines. |
| `translation_segments` | one per Ganguli section, ~1,884, `translator = 'Kisari Mohan Ganguli'` | `start_line`/`end_line` span the verse lines of the chapter interval the section is attached to. |
| `translation_lookup` | one row per (line, segment) in each interval | This is what lets a section serve two chapters without being duplicated. |

### 5.2 Alignment: anchors and intervals (feasibility proposal 5.5)

- **Input:** a checked-in CSV, `sanskrit/data-sources/mbh_ce_ganguli_concordance.csv`,
  columns `book, ce_chapter_from, ce_verse_from, ce_chapter_to, ce_verse_to, ganguli_section_from, ganguli_section_to`,
  transcribed from the Brodbeck & Black appendix (the PDF is at
  `list.indology.info/pipermail/indology/attachments/20190702/f7d5e428/attachment.pdf`,
  54 pages; re-downloaded today). September measured 388 rows, 201
  whole-chapter and 187 verse-split, 88 chapters straddled. A quick
  re-extraction today reproduced the two-column artefacts the September
  document describes (e.g. `11–14 6 –9`), so the transcription must be done
  column-aware and the per-book row counts checked against the printed
  table. [PDF verified; counts Sept]
- **Whole-chapter rows:** the section (or run of sections) is attached to
  the chapter (or run of chapters) the row names.
- **Verse-split rows:** the section is attached to **both** chapters it
  straddles. No automatic splitting of the English, no scoring, no
  threshold.
- **Unmapped sections** (any Ganguli section no row names): attached to
  the interval between the nearest mapped sections on either side, so
  nothing is dropped and nothing is placed outside the chapters it can
  belong to.
- **Special cases, handled by rule, not by name:** a chapter with no row and
  no section (DCS `2,0`) gets no segment; a Ganguli section whose
  concordance chapter has no DCS file (critical-edition 7.173) is attached
  to the interval ending at the last existing chapter before it. Both are
  listed in the build report.
- **The Gītā:** DCS files `BhaGī 1–18` are ordered by DCS file sequence
  number (they sit between 6.22 and 6.41 in the sequence) and so become
  chapters 6.23–6.40 by position. Ganguli's Bhīṣma sections 25–42 then
  attach to them through the concordance like any other chapter. Besant's
  verse-level Gītā translation already in the build stays on the
  Wikisource Gītā work; attaching it to the epic's chapters as well is
  possible later but is **not** part of this proposal.

### 5.2a What the alignment gives, and what it does not

**Chapter level, yes. Verse level, no.** Ganguli's prose carries no verse
numbers, and he translated the vulgate, whose divisions differ from the
critical edition that DCS follows (Ādi: 236 Ganguli sections against 225
critical-edition chapters). No licensed translation keyed to the critical
edition exists, so verse-by-verse pairing is not achievable with this
source. [verified: Ganguli files; Sept: section counts]

The chapter-level result, with the 388-row concordance as the sole source
of pairings [Sept]:

| Case | Chapters | What the reader sees |
|---|---|---|
| Whole-chapter rows (201 rows) | most of the 1,995 | The chapter's own section, or the run of sections that covers it. |
| Verse-split rows (187 rows) | 88 | The straddling section is attached to both chapters, so the translation block covers two chapters. |
| Section named by no row | — | Attached to the block of chapters between its mapped neighbours. Never dropped, never outside the chapters it can belong to. |
| Vulgate passages Ganguli translates that the critical edition omits | — | English with no matching Sanskrit on screen, inside the block of the nearest mapped chapters. |
| Critical-edition 7.173, absent from DCS | 1 | Its Ganguli section attaches to the block ending at 7.172: English with no matching Sanskrit. |
| DCS `2,0` (invocation only) | 1 | No translation of its own. |

What the reader will notice compared with the Rig Veda and the Gītā, which
are verse-aligned in the app: every verse line of a chapter shows the
translation of the whole chapter, not of that verse, and in the 88
straddled chapters the block spans two chapters.

This is exact in the sense recorded on 2026-09-15: every pairing comes
from the published concordance, nothing is scored or guessed, and
uncertainty appears only as a coarser block, never as a wrong pairing.
The exactness of the result rests entirely on transcribing the
concordance correctly, which is why validation 6.4 checks row counts per
book against the printed table.

### 5.3 Footnotes

Ganguli's 3,822 footnotes are the translator's, often citing Nīlakaṇṭha.
Proposal: keep them, appended to the owning section's segment text after
the prose as `[n] …` paragraphs, so no text is dropped and the reader sees
them with the section. Marker `[n]` stays inline. The build fails on any
marker that has no footnote in the file or any footnote with no marker.
(Alternative: drop them. This needs a decision, section 9.)

### 5.4 Verse-level loading of other DCS works

The verse-level change in 6.1 applies to the parser, not to the
Mahābhārata alone. September counted 97 DCS works with three-part chapter
headers that collapse the same way, plus the works whose non-numeric labels
go through `hash()`. [Sept] The change is therefore corpus-wide, which is
the project's default, and the per-work line counts of every DCS work will
change in the next full build. That is the main regression surface
(section 7).

---

## 6. Pipeline changes

All code goes into `create_sanskrit_database_interlinear.py`. No standalone
fix scripts; `./run_build.sh full` produces the result from scratch.

### 6.1 Parser: verses, order, labels

- For three-part `## chapter:` headers, key sentences on
  `(book, chapter, sent_counter)`; a sentence with no `sent_counter` joins
  the current verse.
- Replace the `hash()` fallback in `worker_parse_citation_part` for
  ordering purposes with the DCS file sequence number (`-0000-` …) and
  keep the label string for the citation prefix. This removes the
  build-to-build instability that `PYTHONHASHSEED` causes.
- Emit `[book.chapter.verse]` prefixes in `line_text` for three-part works,
  matching the Rig Veda convention.

### 6.2 Translation path

- The existing `translation_map` path writes zero rows for all nine mapped
  works because the worker keys chapters as `int` and the writer looks
  them up as `str` (`:1347-1351` vs `:1569-1570`). [Sept, verified with line
  numbers then; file unchanged since] Fix it first, and make the build
  **fail** when a mapped translation yields zero segments, instead of
  silently setting `has_translations`.
- Add a Ganguli loader, invoked when the DCS work `Mahābhārata` is
  processed:
  1. read the four Gutenberg files from `sanskrit/data-sources/ganguli/`
     (fail if any is missing or its `*** START OF` / `*** END OF` markers
     are not found exactly once);
  2. cut at the markers, drop everything outside them;
  3. split on `BOOK n`, `<NAME> PARVA`, `SECTION <roman>`; resolve
     footnotes per 5.3;
  4. apply the concordance CSV per 5.2;
  5. write `translation_segments` and `translation_lookup`.

### 6.3 Inputs and where they live

Following the Gītā precedent (`sanskrit/data-sources/SOURCES.md`,
`download_bhagavad_gita_*.sh`):

- `sanskrit/data-sources/download_ganguli.sh`: fetches
  `https://www.gutenberg.org/cache/epub/<n>/pg<n>.txt` for 15474–15477
  into `sanskrit/data-sources/ganguli/`, and verifies a recorded SHA-256
  for each.
- The four text files (15.3 MB) are **checked in**, as the Gītā HTML is, so
  a clone builds without network access. This needs a decision (section 9)
  because it is the largest text payload in `sanskrit/data-sources/` so
  far.
- `sanskrit/data-sources/mbh_ce_ganguli_concordance.csv`, checked in.
- `SOURCES.md` gains a Ganguli section with URLs, download date, licence
  and the stripping rule.

### 6.4 Validation (mechanical, blocks the build)

1. Every `SECTION` in the stripped Gutenberg text appears in exactly one
   segment, in file order; the concatenation of all segment prose equals
   the stripped text (hash comparison).
2. Every DCS chapter except those listed as unmappable (`2,0`) is covered
   by at least one interval.
3. Intervals are monotonic and non-crossing within each parvan.
4. Concordance row count per book equals the count recorded in the CSV
   header comment from the printed table.
5. Per-parvan verse-line counts equal the DCS distinct
   `(chapter, sent_counter)` counts plus the chapters without counters.
6. Book 6: the chapters at positions 23–40 are the `BhaGī` files in order
   1–18.
7. Zero segments for any mapped translation is an error.

### 6.5 Attribution

`LICENSE_COMPLIANCE.md` (Ganguli, public domain; SARIT correction from
section 2), `LicenseActivity.kt`, `DCS_TEXTS_CATALOG.md`, `README.md`, and
the Mahābhārata `works.description` (which currently reads "Mahābhārata
from the Digital Corpus of Sanskrit") to name the translation and the
absent chapter 7.173.

### 6.6 Build order

Unchanged: `./run_build.sh full` runs the DB creation, interlinear
generation, interlinear import and ZIP in one pass. The Ganguli loader runs
inside the DB-creation step. Before any build, check for running processes
as `CLAUDE.md` requires.

---

## 7. Testing

1. **Custom CSV build first.** `Source,Work` / `DCS,Mahābhārata` in a test
   CSV, built with the test path, before any full build. Check: 18 books;
   ~73,200 lines; Book 6 positions 23–40 are the Gītā; validation 6.4
   passes; ten chapters spread across the epic read against the Gutenberg
   text by eye (chapter 1.1, 2.1, 6.23, 7.172, 12.1, 18.5 among them).
2. **Regression on the other DCS works.** Record per-work `text_lines` and
   `words` counts from the current `sanskrit_texts.db` before the change
   and diff after. `words` counts must be unchanged for every work;
   `text_lines` counts will rise for the 97 three-part works and must
   equal their DCS verse counts. `data-prep/text_integrity/audit.py` does
   not cover the Sanskrit DB [Sept], so this diff is the integrity check.
3. **App check on device** after a full build: open Mahābhārata Book 1,
   swipe to translation, confirm Ganguli Section I appears for the first
   chapter and that a straddled chapter shows the shared section.

---

## 8. Effort and risk

| Item | Estimate | Risk |
|---|---|---|
| 6.1 verse-level parser and ordering | 2–3 days | Medium: changes 97 works and all hash-labelled works. |
| 6.2 translation-path fix | 0.5–1 day | Prerequisite; nine currently silent works start producing rows or failing. |
| Concordance CSV transcription, column-aware | 1 day | The accuracy of the whole alignment rests on it; checked by per-book counts only. |
| Ganguli parser, footnotes, validator | 2 days | Low. |
| Full rebuild and regression diff | ~3 h build plus review | Build time after 36× more Mahābhārata lines not measured. |

Size: about 14 MB more English text uncompressed; ZIP growth not
measured. [inferred from the 15.3 MB download]

---

## 9. Decisions needed

1. **BORI notice.** Proceed on DCS's CC BY 4.0 as the licence of record, or
   ask BORI / John Smith first. `maha.txt` did not supply a source that
   avoids the question; sanskritdocuments.org states BORI holds copyright.
2. **Footnotes:** keep appended to the section (proposed) or drop.
3. **Check in the Gutenberg texts** (15.3 MB) or fetch at build time.
4. **Concordance transcription:** confirm that transcribing the Brodbeck &
   Black table as factual data is acceptable (the September document lays
   out the considerations in its section 8).
5. **Corpus-wide verse-level change:** confirm that all 97 three-part DCS
   works change in the same build.

---

## 11. Implementation record (2026-10-09)

Everything lives under `sanskrit/`; nothing outside it was changed.

| File | Role |
|---|---|
| `data-sources/download_ganguli.sh` | Fetches Gutenberg 15474–15477 into `data-sources/ganguli/` (git-ignored; the build runs the script when the files are missing). |
| `data-sources/extract_mbh_concordance.py` | Transcribes the Brodbeck & Black appendix PDF into `data-sources/mbh_ce_ganguli_concordance.csv` (checked in) using text coordinates; verifies contiguous chapter coverage per book. |
| `data-sources/mbh_ce_ganguli_concordance.csv` | 397 rows, 189 verse-level, 3 `?` rows. September's figure of 388 came from a plain-text extraction with column artefacts. |
| `mahabharata_ganguli.py` | Verifies and parses the Gutenberg text, loads the CSV, computes the chapter spans, writes `translation_segments`. |
| `create_sanskrit_database_interlinear.py` | Verse-level lines and file-order chapters for 3-part and longer headers; book numbering without `hash()`; `[b.c.v]` prefix; translation-path key fix; zero-segment and write-error failures; optional `works.csv name` arguments. |
| `run_build.sh` | Passes the optional CSV and name through. |
| `SANSKRIT_MAHABHARATA_TEST.csv` | Mahābhārata + Rāmāyaṇa + Aitareyopaniṣad test list. |
| Docs | `data-sources/SOURCES.md`, `LICENSE_COMPLIANCE.md`, `README.md`, `BUILD_INSTRUCTIONS.md`, `DCS_TEXTS_CATALOG.md`. |

Departures from the plan above, all found by measuring the files:

- **Ganguli section headings are not uniform.** Books 8–11 and 16–18 use a
  bare arabic number on its own line instead of `SECTION <roman>`. Eight
  headings are missing from the transcription (1.177, 2.67, 7.54, 7.55,
  7.189, 12.34, 12.35, 12.364); the text is present and stays with the
  preceding section, which is then attached to the chapters of every
  numeral it covers. The translation therefore has 2,106 section units,
  not 1,884 `SECTION` lines.
- **Footnotes are numbered per book**, cited inline as `[n]` and listed
  after `FOOTNOTES` at the end of each book (none in Books 8–11 and
  16–18). Notes may span paragraphs. Two markers are reused (12.384,
  13.414) and two note numbers are listed twice (12.8, 12.19); all texts are
  kept and reported. Decision 2 in section 9 is resolved as "keep,
  appended to the citing section".
- **Concordance rows pairing n chapters with n sections** (`14–18 → 16–20`)
  are read one-to-one; rows with unequal counts attach the whole section
  run to the whole chapter run.
- **Row `13.99 → 58`** is printed out of order and is not used; chapter
  13.99 is covered by extending its neighbouring sections.
- **Three `?` rows** (4.58, 7.23, 7.24.1–17) are handled by the same
  extension rule.
- **The Gutenberg files are not checked in** (decision 3): the download
  script and a content hash make the build repeatable; this matches how
  the Gītā HTML is handled.
- `LicenseActivity.kt` (section 6.5) is outside `sanskrit/` and was not
  touched; the attribution text to add is in `LICENSE_COMPLIANCE.md`.

**Test build** (`./run_build.sh full SANSKRIT_MAHABHARATA_TEST.csv mbhtest`,
2026-10-09, 60 minutes end to end: 38 minutes DCS parsing with Stanza,
the rest interlinear generation, import and ZIP; `sanskrit_texts_mbhtest.db`
1.13 GB, ZIP 264 MB, `unzip -t` clean). All measured in the built DB:

| Check | Result |
|---|---|
| Mahābhārata lines / words | 73,214 / 1,147,887 (was 1,995 / 1,147,887: words identical) |
| Rāmāyaṇa lines / words | 18,717 / 261,568 (was 606 / 261,568); books 1–7 labelled Bā, Ay, Ār, Ki, Su, Yu, Utt in canonical order |
| Aitareyopaniṣad | unchanged 13 lines / 848 words; 5 Olivelle segments where the old build wrote none (the file's chapter numbering matches only the first chapter of books 2 and 3). The licence status of the nine `translation_map` files is recorded in `LICENSE_COMPLIANCE.md` section 8 for the owner's decision |
| Gītā | Book 6 lines run `[6.22.*]`, `[6.BhaGī 1.1]` … `[6.BhaGī 18.78]`, `[6.41.1]` |
| Ganguli segments | 2,106 (one per section unit); `has_translations` = 1 |
| Coverage | every one of the 73,214 Mahābhārata lines has at least one Ganguli segment through `translation_lookup` |
| Spot reads | 1.1 ↔ Section 1 over lines 1–214; 1.13 ↔ Sections 13, 14, 15; Gītā 1 ↔ Bhīṣma Section 25; 12.1 ↔ Śānti Section 1 ("Having offered oblations of water…"); 18.5 ↔ Svargārohaṇa Sections 5 and 6; Droṇa Sections 201–203 end at line 8,043 (chapter 7.172), where the absent 7.173 attaches |
| Interlinear | 73,214 + 18,717 + 13 per-line segments regenerated, 100 % dictionary coverage reported |

The build log prints the alignment report quoted in section 5.2a for every
book. The `resource_tracker` warning about leaked semaphores at exit is
Python's multiprocessing on macOS and predates this change.

Not yet done: a full `./run_build.sh full` rebuild of `sanskrit_texts.db`
(about three hours, changes 122 works' line counts) and the device check
of section 7, step 3.

## 10. Verification log (2026-10-09)

Local: `git log` on the Sanskrit build files; `sanskrit_texts.db` (tables,
Mahābhārata books and line lengths, Rig Veda prefix, translator row
counts); DCS clone commit and Mahābhārata directory; build script lines
885, 1222–1250, 1525–1545, 2312–2330; `LICENSE_COMPLIANCE.md:165-200`;
`sanskrit/data-sources/SOURCES.md`; grep of `app/src/main/java` for
citation-prefix parsing.

Fetched today: sacred-texts `hin/mbs/index.htm`, `hin/mbs/mbs01001.htm`,
`cnote.htm`, `hin/index.htm` (all via the Wayback Machine's 2024 captures;
the live site returns a Cloudflare challenge); sanskritdocuments.org
`mirrors/mahabharata/mahabharata-bori.html` and `sanskritfaq.html`; SARIT
`mahabharata-devanagari.xml` (38.6 MB, counted); INDOLOGY March 2024
thread on archive.org volumes; `vedicreserve.miu.edu` index, `itihas.htm`
and `mahabharata16_mausala.pdf`; `bombay.indology.info/mahabharata/statement.html`;
Gutenberg 15474–15477 catalogue pages and plain-text files (downloaded and
counted), 7864, 7965, 11894, 12058, 12333 catalogue pages, and the
Gutenberg search results; the INDOLOGY July 2019 concordance thread and
its PDF attachment. Not reachable: `mahabharata.manipal.edu` (connection
timed out).
