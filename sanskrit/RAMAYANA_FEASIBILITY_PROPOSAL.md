# Rāmāyaṇa in the Sanskrit module: feasibility proposal

**Date:** 2026-09-15 (revised the same day for the exact-alignment requirement;
see section 10)
**Scope:** Sanskrit text + English translation for Vālmīki's Rāmāyaṇa,
restricted to sources whose licence permits commercial redistribution inside
the app.
**Requirements set by the user (2026-09-15):**
1. the translation must be aligned to the Sanskrit **exactly**, no
   proportional or approximate mapping;
2. **no human review will be available**, the pipeline must be fully
   automatic;
3. **gaps are acceptable**: a sarga may end up without a translation of its
   own;
4. **no text may be dropped**: every sentence of the translation must appear
   in the output, in order.
**Status:** proposal, nothing implemented. Section 5.5 is the design that
meets all four requirements; sections 5.2 and 5.4 are kept for the record.
**Companion:** `MAHABHARATA_FEASIBILITY_PROPOSAL.md`; its sections 6.1 and
6.3 are shared prerequisites.

Claims are marked **[verified]** or **[inferred]** as in the companion.

**Reviewed 2026-09-27.** Every DB and DCS count was re-measured, Smith's
`Ram01–07.txt` and the five Gutenberg texts were downloaded and re-counted,
the licence pages were re-fetched, and the build-script claims were re-read
with line numbers. Corrections are marked in place; section 10 lists them.

---

## 1. Summary

The Rāmāyaṇa is **already in the full Sanskrit build** as a DCS work, but in
a form that is unusable for reading:

- one `text_lines` row per *sarga* (606 rows, up to 16,350 characters), no
  English; [verified]
- the seven kāṇḍas are stored as books numbered **5745, 5905, 38109, 58797,
  63303, 74697, 83703** ("Book 5745" …), sorted as Araṇya, Ayodhyā,
  Kiṣkindhā, Uttara, Bāla, Yuddha, Sundara. The numbers are Python `hash()`
  values of the DCS kāṇḍa abbreviations. [verified]

**What exact alignment can mean with licensed sources.** [verified, section 5]

| Granularity | Achievable? | Why |
|---|---|---|
| Verse-exact | **No** | Neither public-domain translation (Dutt, Griffith) carries verse numbers. The only verse-numbered complete translations (Goldman, Debroy) are under copyright. |
| Sarga-exact | **Yes** | The critical edition's sarga boundaries coincide with the vulgate's in almost every case (Bāla pilot: 74 of 76, with a one-sarga offset from sarga 9 on). Sanskrit Wikisource carries a verse-numbered vulgate under CC BY-SA, so a CE-sarga → vulgate-sarga concordance can be **computed from the Sanskrit text itself and verified mechanically**. Dutt's sections are vulgate sargas; where his numbering differs from Wikisource's (four kāṇḍas) the section-to-sarga step is content-matched and signed off by hand. |

The feasible path is:

1. **Keep the DCS text** (CC BY 4.0). Its sarga structure matches the Baroda
   critical edition exactly (606 sargas) and per-sarga verse numbering
   matches in 596 of 606 sargas. Fix the loader (verse-level lines, 18,715;
   deterministic book identity). [verified counts; loader change not
   written]
2. **Add Manmatha Nath Dutt's prose translation (1891–94)**, public domain,
   complete, from Project Gutenberg, attached **sarga-exactly** by the
   two-step concordance in section 5, with a build-time validator.
3. Griffith (1870–74) is public domain but omits cantos and gives the
   Uttarakāṇḍa only as a prose summary; secondary at best.

No Room schema change is needed.

---

## 2. Current state [verified]

From `sanskrit/sanskrit_texts.db` (built 2026-05-21) and
`data-sources/sanskrit/dcs/data/conllu/files/Rāmāyaṇa/` (DCS clone at commit
`04e0778d`, 2026-03-05).

| Item | Value |
|---|---|
| Work id / author id | `Rāmāyaṇa` / `Rāmāyaṇa` |
| Books | 7, numbered 5745 … 83703 |
| `text_lines` rows | 606 (one per sarga) |
| Longest line | 16,350 characters |
| `words` rows | 261,568 |
| `translation_segments` | 606, all interlinear glosses, **no English** |
| DCS CoNLL-U files | 606 |
| DCS sentences (`# text =`) | 38,004 |
| Sentences with `# sent_counter` | 37,954 (50 lack it) |
| Distinct (sarga, `sent_counter`) pairs | **18,715** |

Book identification in the built DB, by line count and first line:

| `book_number` | Kāṇḍa | Lines | First line (DCS, unsandhied) |
|---|---|---|---|
| 63303 | 1 Bāla | 76 | tapas svādhyāya niratam … |
| 5905 | 2 Ayodhyā | 111 | |
| 5745 | 3 Araṇya | 71 | |
| 38109 | 4 Kiṣkindhā | 66 | sa tām puṣkariṇīm gatvā … |
| 83703 | 5 Sundara | 66 | tatas rāvaṇa nītāyāḥ sītāyāḥ … |
| 74697 | 6 Yuddha | 116 | |
| 58797 | 7 Uttara | 100 | |

### 2.1 Why the book numbers are garbage

`worker_parse_citation_part` (`create_sanskrit_database_interlinear.py:1173-1183`)
tries `int()`, then `int(float())`, then `abs(hash(part_str)) % 100000`;
the books INSERT (`:1515-1523`) then writes `id = "<work>.<hash>"` and
`label = "Book <hash>"`. Python salts `str.__hash__` per process unless
`PYTHONHASHSEED` is set; nothing in the build sets it (`run_build.sh` has
no such line). [verified; cross-build instability inferred] A consequence
not stated before: because `books.id` embeds the hash, **every rebuild can
give these 34 works new book ids**, so a bookmark on any of them already
breaks at the next rebuild today; the fix in 6.1 does not make that worse,
it ends it. In the built DB **34 works** have
hash-valued book numbers (Rāmāyaṇa, Carakasaṃhitā, Suśrutasaṃhitā,
Aṣṭāṅgahṛdayasaṃhitā, Āyurvedadīpikā, Rājanighaṇṭu with 21 books,
Toḍalatantra, Tantrasāra, Haṭhayogapradīpikā, Meghadūta, Ṛtusaṃhāra,
Spandakārikā, Gṛhastharatnākara, Rasaratnākara, Śivapurāṇa, Skandapurāṇa
(Revākhaṇḍa), Mṛgendratantra and 17 more). [verified by query]

### 2.2 DCS matches the Baroda critical edition [verified]

| Kāṇḍa | DCS sargas | Smith CE sargas | DCS verses | Smith CE verses |
|---|---|---|---|---|
| 1 Bāla | 76 | 76 | 1,938 | 1,941 |
| 2 Ayodhyā | 111 | 111 | 3,122 | 3,160 |
| 3 Araṇya | 71 | 71 | 2,060 | 2,060 |
| 4 Kiṣkindhā | 66 | 66 | 1,984 | 1,987 |
| 5 Sundara | 66 | 66 | 2,488 | 2,487 |
| 6 Yuddha | 116 | 116 | 4,435 | 4,436 |
| 7 Uttara | 100 | 100 | 2,688 | 2,690 |
| **Total** | **606** | **606** | **18,715** | **18,761** |

The "DCS verses" column counts distinct `(sarga, sent_counter)` pairs; the
per-sarga maxima sum to 18,737 (Bāla 1,940, Ayodhyā 3,142), so 22 verse
numbers are skipped inside sargas. The "Smith CE verses" column counts
distinct verse ids. [re-measured 2026-09-27 from the downloaded files;
every figure in the table confirmed]

Per-sarga maximum verse numbers are identical in **596 of 606 sargas**; the
ten exceptions are 1.70, 2.1 (DCS 20 / CE 37, a prose passage), 2.65, 4.11,
4.19, 4.54, 5.15, 6.105, 7.37, 7.100, all but 2.1 off by one. The DCS file
sequence (`-0000-` … `-0605-`) is in canonical kāṇḍa order (Kiṣkindhā 1 is
file 0258, Sundara 1 is file 0324). [verified]

---

## 3. Sanskrit text sources: licence review

| Source | Edition / numbering | Licence as stated by the source | Role |
|---|---|---|---|
| **DCS** (Hellwig) | Baroda critical edition numbering (2.2); lemma, POS, `Unsandhied`, verse ids | CC BY 4.0 in `data/readme.md` and `data/conllu/readme.md` [verified] | **The reading text.** Already shipped and attributed. |
| **Sanskrit Wikisource** रामायणम् | Vulgate (Bombay-type) numbering: Bāla 77 (re-verified 2026-09-27 from the kāṇḍa index), Ayodhyā 119, Araṇya 75, Kiṣkindhā 67, Sundara 68, Yuddha **131** by the sarga-page navigation (the kāṇḍa index page lists 128), Uttara 111. Verse-numbered; marker formats vary by page (`॥१-४०-१॥` in early Bāla, `॥१॥` elsewhere). Edition not stated. | CC BY-SA **4.0** (footer links `creativecommons.org/licenses/by-sa/4.0`) [re-verified 2026-09-27] | **The alignment bridge** (section 5). Not shipped; used at build time only, so share-alike is not triggered for the app text. [inferred: share-alike attaches to distributed adaptations of the work, and only the derived concordance table, a table of sarga numbers, would be distributed]. Three further facts bear on decision 3: the Sanskrit text itself is ancient and public domain, and Wikisource's licence covers what contributors added, not the underlying work; `sanskrit/LICENSE_COMPLIANCE.md:190` already lists CC BY-SA among the accepted licences; and the app already ships the Wikisource Bhagavadgītā text under CC BY-SA 4.0 (`:82`, `:203`). So even if share-alike were held to apply, it would not be a new kind of obligation for this app. |
| **John Smith / Tokunaga e-text** (bombay.indology.info/ramayana) | Critical edition, sandhied; "final form" 2026-06-14 but "still far from correct" per the site | File header has **no copyright line at all**; no licence grant. [verified] | Reference only; used this session to verify DCS counts. |
| **GRETIL** `ram_01_u.htm` | Same text | "FOR REFERENCE PURPOSES ONLY … TERMS OF USAGE AS FOR SOURCE FILE." [verified] | No. |
| valmikiramayan.net | Vulgate with glosses | Site shows a hosting-suspension notice; terms not retrievable [verified] | No. |
| IWLV-Ramayana (arXiv 2604.13078, HF `insightpublica/ramayana-indic`) | Sarga-aligned multilingual corpus with English | Paper links to a licence; HF API licence field empty; dataset page 401 [verified] | No, until a licence is readable. |

---

## 4. English translation sources: licence review

| Translation | Years | Basis | Verse numbers? | Licence | Availability | Usable for exact alignment? |
|---|---|---|---|---|---|---|
| **Manmatha Nath Dutt**, prose | 1891–1894, Calcutta | Vulgate; footnotes cite "the Bengal text" as a variant [inferred: main text is a non-Bengal recension] | **No** [re-verified 2026-09-27: no numbered paragraphs in any of the four files] | Public domain. Gutenberg asserts only "Public domain in the USA"; worldwide status rests on the translator's death (1912, per the PG author record), which clears life + 70 and life + 100 terms everywhere. [verified] | Gutenberg **57265** (Vol. 1, Bāla + Ayodhyā), **57826** (Vol. 2, Āraṇya + Kiṣkindhā + Sundara), **60188** (Vol. 3, Yuddha), **62496** (Vol. 4, Uttara); clean UTF-8 with footnotes; 3,655,426 bytes together [titles and sizes re-verified 2026-09-27] | **Sarga-exact.** Recommended. |
| **Ralph T. H. Griffith**, verse | 1870–1874 | Bombay edition; cantos omitted; Book VII prose summary only [verified] | No | Public domain (Griffith d. 1906; same reasoning as for Dutt) [verified] | Gutenberg **24869** [verified] | Sarga-exact where a canto exists; Books I 75 of 77 cantos, V 55 of 66, VI 101 of 130 (the review of 2026-09-27 re-confirmed Books II 119, III 76 and V 55/66 with a simple heading parser; Books I and VI were not re-derived). Secondary. |
| Hari Prasad Shastri | 1952–1959 | — | — | Copyright (author 1882–1956) | scans | No. |
| Goldman et al., Princeton | 1984–2017 | Critical edition | yes | Copyright | — | No. |
| Bibek Debroy, Penguin | 2017 | Critical edition | yes | Copyright | — | No. [verified via publisher listing] |

Section counts by last numeral [verified]:

| Kāṇḍa | CE sargas (DCS = Smith) | Dutt last section | Wikisource sargas | Griffith cantos present / last numeral |
|---|---|---|---|---|
| Bāla | 76 | 77 | 77 | 75 / 77 |
| Ayodhyā | 111 | 118 | 119 | 119 / 119 |
| Araṇya | 71 | 75 | 75 | 76 / 76 |
| Kiṣkindhā | 66 | 67 | 67 | 67 / 67 |
| Sundara | 66 | 67 | 68 | 55 / 66 |
| Yuddha | 116 | 130 | 131 (index page: 128) | 101 / 130 |
| Uttara | 100 | 124 | 111 | summary only |
| **Total** | **606** | **658** | **648** | |

Dutt's transcription has misprinted numerals (Bāla: `XXXN` for XXXII,
`LXXII` twice, no `XLIII`; Yuddha has three repeated numerals and Uttara
nine), so the parser must number sections by order of appearance and
report anomalies. [re-verified 2026-09-27 on the downloaded files: every
"last section" numeral in the table above confirmed, 658 in total]

---

## 5. Exact alignment: what the data supports

### 5.1 Pilot: critical-edition sargas against the Wikisource vulgate, Bālakāṇḍa [verified]

Method: DCS `# text` half-verses transliterated to Devanagari; Wikisource
verses split on their `॥…॥` markers; both normalised (punctuation, digits,
spaces and avagraha removed; homorganic nasals folded to anusvāra). All 77
Wikisource Bāla pages fetched.

| Measure | Result |
|---|---|
| CE sarga openings that coincide with a Wikisource sarga opening (similarity ≥ 0.85 on the first 40 characters) | **61 of 76** |
| CE openings at 0.79–0.85 with the expected one-sarga offset (wording variants in the first half-verse) | 13 |
| CE openings with **no** vulgate counterpart at the same position | 2 (CE 1.7, similarity 0.44; CE 1.36, 0.63) |
| Offset pattern | CE 1–5 = vulgate 1–5; CE 9 = vulgate 10 and so on: vulgate 9 has no CE counterpart |
| CE half-verses found verbatim anywhere in Wikisource Bāla | 1,733 of 3,939 (44%) with the crude normaliser; the rest differ in wording or orthography and need fuzzy matching |

So sarga boundaries can be paired mechanically for all but a handful of
sargas per kāṇḍa, and the handful is listed by the tool rather than
discovered by accident.

### 5.2 Sarga-exact procedure

1. **CE sarga → vulgate sarga (mechanical).** Monotonic sequence alignment
   of DCS sargas against Wikisource sargas per kāṇḍa, scored on the opening
   verse and on fuzzy half-verse overlap. Output: a concordance CSV with a
   score per row and a residual list (CE sargas with no vulgate opening at
   the expected place, vulgate-only sargas). Residuals reviewed by hand and
   recorded.
2. **Vulgate sarga → Dutt section.** Where Dutt's count equals Wikisource's
   (Bāla 77, Araṇya 75, Kiṣkindhā 67) the mapping is by number and is
   checked, not assumed: the speaker cue and proper names in each Dutt
   section's first sentence must match the vulgate sarga's opening verse.
   Where counts differ (Ayodhyā 118 vs 119, Sundara 67 vs 68, Yuddha 130 vs
   131, Uttara 124 vs 111) the same cue matching drives a monotonic
   alignment and every unmatched section or sarga is reviewed by hand.
3. **Straddles.** Where a CE sarga boundary falls inside a Dutt section
   (Bāla pilot suggests two such places in that kāṇḍa; the tool will count
   them for the others), a human marks the split sentence, stored as an
   offset in a hand-maintained split file. Where a vulgate-only sarga has no
   CE counterpart, its Dutt section is simply not attached.
4. **Validation, every build:** every CE sarga has exactly one segment;
   sections used monotonically; speaker-cue agreement for every sarga after
   a name table (Vālmīki, Nārada, Daśaratha, Viśvāmitra, …); any failure
   blocks the build until acknowledged in the split file.
5. **Human sign-off** of residuals and splits, recorded in the repo.

### 5.3 What is not on offer

Proportional mapping; verse-level alignment of Dutt or Griffith (no verse
markers); the copyrighted CE-based translations.

### 5.4 Reusing the sibling Diodorus pipeline (`~/git/diodorus`) [verified 2026-09-15]

See the Mahābhārata proposal, section 5.4, for the pipeline description and
the Gītā pilots (embedding baseline 9% verse top-1; DCS-gloss lexical
overlap 20%; DCS name-lemma entity anchoring 396 of 483 names matched on
the correct chapter against 63 on a wrong one). For the Rāmāyaṇa the fit is
better than for the Mahābhārata, because the task is a sequential, mostly
1:1-with-insertions alignment of 606 CE sargas to 658 Dutt sections per
kāṇḍa, which is exactly Diodorus's segmental DP problem, and because the
epic is dense in proper names (Rāma, Sītā, Lakṣmaṇa, Hanumān, Rāvaṇa,
Sugrīva, Daśaratha, Viśvāmitra …) so the entity signal is strong in most
sargas.

Proposed use: run Diodorus's DP (with a `sanskrit` branch: DCS lemmas for
entities, DCS glosses as the initial lexical table, the multilingual
baseline or a trained Sanskrit model for embeddings) as a **second,
independent** CE-sarga → Dutt-section alignment. The first is the
Sanskrit-text concordance of 5.2 (CE ↔ Wikisource vulgate ↔ Dutt by number
or cue). Where the two agree, the pairing is accepted; every disagreement
and every Diodorus low-confidence sarga goes to the human review list. Its
refinement step proposes the split sentence wherever a Dutt section
straddles two CE sargas. Its integrity checker guarantees that no Dutt text
is dropped or reordered.

As for the Mahābhārata, Diodorus does not certify correctness; it scores
it. The exactness still rests on two independent methods agreeing plus
human sign-off of the residue.

### 5.5 Fully automatic design: anchors and intervals (meets requirements 1–4)

**Principle** (same as the Mahābhārata proposal, 5.5): a Dutt section is
attached to a single CE sarga only when the pairing is known; every other
section is attached to the interval of sargas between the nearest known
pairings. Nothing dropped, nothing placed where it cannot belong,
uncertainty appears as coarser granularity. No human.

**What counts as "known" for the Rāmāyaṇa.** There is no published
concordance, so anchors come from two mechanical sources, and a pairing is
an anchor only when **both** agree:

1. **CE sarga → vulgate sarga by Sanskrit text identity** (5.1, 5.2 step 1):
   accepted when the CE sarga's opening half-verse matches a Wikisource sarga
   opening at ≥ 0.85 similarity **and** the two sargas share ≥ 60% of their
   half-verses at ≥ 0.85 (thresholds to be fixed once on the Gītā/Rig Veda
   calibration data below, then frozen). Bāla pilot: 61 of 76 openings pass
   the first test at 0.85. [verified]
2. **Vulgate sarga → Dutt section**: by number where the kāṇḍa counts agree
   (Bāla 77/77, Araṇya 75/75, Kiṣkindhā 67/67), otherwise by monotonic
   alignment on the entity score; in both cases accepted only when the
   entity check (IDF-weighted, size-normalised, both directions, 25% margin)
   confirms it.

Measured on Bāla with the offset mapping from the pilot and Dutt's sections
parsed by order: 21 of 75 pairings confirmed by the entity check (28%), 14
best but without margin, 40 with a neighbour scoring higher. [verified]
Part of the 40 is the scorer's weakness on short sargas and part may be
the pilot's own offset assumption; either way, **on this evidence roughly a
quarter to a third of sargas would become anchors and the rest would be
covered by intervals of a few sargas each.** Adding the gloss-lexical and
embedding signals of 5.4 should raise the anchor rate; how far is
unknown until measured.

**Calibration without humans.** Thresholds are chosen on alignments that
are known by construction: the Gītā (DCS `BhaGī` verses ↔ Besant by verse
number) and the Rig Veda (DCS ↔ Griffith by hymn and stanza), and, for
sarga-sized units, the Mahābhārata concordance's whole-chapter rows. The
rule is fixed as the strictest setting that produces **zero** wrong
acceptances on the calibration data, then frozen and applied to the
Rāmāyaṇa. This is an empirical guarantee, not a proof; the interval
fallback is what keeps a residual error from placing text where it cannot
belong.

**Output shape and validation** as in the Mahābhārata proposal 5.5: every
Dutt section emitted once in order (hash check), every CE sarga covered by
an interval, intervals monotonic; vulgate-only sargas (e.g. Bāla 9) carry
their Dutt section within the enclosing interval so nothing is dropped.

---

## 6. Proposed pipeline changes

All in `create_sanskrit_database_interlinear.py` and its inputs; no manual
steps beyond `./run_build.sh`. The Wikisource pages, the derived concordance
CSV and the split file are checked-in inputs.

### 6.1 Deterministic books and chapters for non-numeric DCS labels

Replace the `hash()` fallback with ordering by DCS file sequence and a
general abbreviation → name table (`Bā` → Bālakāṇḍa, `Sū.` → Sūtrasthāna,
`BhaGī` → Bhagavadgītā). Verify on all 34 affected works.

### 6.2 Verse-level lines for 3-part citations

Shared with the Mahābhārata proposal: 606 lines become 18,715; the 50
unnumbered sentences attach to the preceding verse and are reported.

### 6.3 Wikisource download and Dutt import

- Download script for the seven Wikisource kāṇḍa indexes and 648 sarga
  pages with a descriptive `User-Agent` (the default one intermittently
  returns Wikimedia error pages) [verified], and for the four Gutenberg
  files.
- Wikisource parser tolerant of both marker formats; pages with no verses
  fail the build.
- Dutt parser: strip PG boilerplate; kāṇḍa headings and `SECTION` lines;
  number by order; footnotes per decision.
- Concordance builder and validator as in 5.2, run inside the main build.
- The existing external-translation path yields zero rows for every work it
  is configured for: the worker keys translations by `int`
  (`create_sanskrit_database_interlinear.py:1347-1351`), the writer looks
  up `str(...)` (`:1569-1570`), and `has_translations` is set from the file
  path alone (`:1494-1498`); see the companion, 6.3. [verified 2026-09-27
  with line numbers]; fix first.

### 6.4 Documentation and attribution

`LICENSE_COMPLIANCE.md` (Dutt; Wikisource as build-time bridge, CC BY-SA,
with the share-alike reasoning stated), `LicenseActivity.kt`,
`DCS_TEXTS_CATALOG.md`, `README.md`.

### 6.5 Testing

`test`-mode build with `DCS,Rāmāyaṇa` only: 7 books numbered 1–7 with
labels; per-book line counts equal 2.2; validator passes; residual list
signed off; ten sargas spread across the kāṇḍas read correctly. Record
before/after per-work line and word counts for the Sanskrit DB
(`audit.py` does not cover it) [verified].

---

## 7. Effort and risk

| Work item | Estimate | Risk |
|---|---|---|
| 6.1 book/chapter identity fix | 1 day | Changes `books.id` for 34 works. Bookmarks key on `book_id` on both platforms, so existing bookmarks on these works will not resolve after the change; but those ids already change on every rebuild today (2.1), so no working bookmark is lost that a rebuild would not have lost anyway. [inferred from the code; not tested on a device] |
| 6.2 verse-level loader | shared | Medium. |
| Wikisource fetch + parser | 1 day | Marker-format variety; rate limiting. |
| Concordance builder + validator | 3–4 days | The fuzzy matcher must be tuned so residuals are few but complete. |
| Dutt parser | 1 day | Low. |
| Manual review of residuals and straddles | 1–3 days of a Sanskrit reader | Exactness rests here; Yuddha and Uttara are the hard kāṇḍas. |
| Full rebuild | ~3 h today | Not measured after row growth. |

Dutt adds about 3.7 MB of English uncompressed. [verified]

---

## 8. Decisions needed from the user

1. **Translation**: Dutt only, or Dutt plus Griffith where his cantos exist.
2. **Footnotes**: drop, inline, or separate segments.
3. **Wikisource as a build-time bridge** under CC BY-SA 4.0: accept the
   reasoning in section 3 or get it checked. Note that the project already
   accepts CC BY-SA (`sanskrit/LICENSE_COMPLIANCE.md:190`) and already
   ships Wikisource text under it (the Gītā), so this decision is about
   consistency of the attribution text, not about a new licence class.
4. **Book id change** for 34 works; anything persisted on device?
5. **Who reviews and signs off** the residual list and the splits.
6. **Underlying e-text rights** (Tokunaga/Smith text carries no rights
   statement; DCS relicenses CC BY 4.0; the app already ships it).

---

## 9. Verification log (2026-09-15)

Local: `sanskrit/sanskrit_texts.db` (counts, book identities by first line,
hash-numbered books, translators present); DCS Rāmāyaṇa files (headers,
counts, per-sarga maxima, file-sequence positions); the build script
(`worker_parse_citation_part`, book insert, `write_parsed_work_to_db`,
`translation_map`); `run_build.sh` (no `PYTHONHASHSEED`).

Web (fetched this session): bombay.indology.info Rāmāyaṇa welcome,
statement and `text/UD/Ram01–07.txt`; GRETIL `ram_01_u.htm`;
sa.wikisource.org रामायणम्, the seven kāṇḍa index pages, all 77 Bāla sarga
pages and sample pages from every other kāṇḍa (Ayodhyā 2 and 60, Araṇya 1,
Kiṣkindhā 1, Sundara 1, Yuddha 1 and 100, Uttara 1 and 111);
gutenberg.org author 7984, ebook 62496, files 57265/57826/60188/62496 and
24869, licence page; en.wikisource.org The_Ramayana; arXiv 2604.13078 and
the HuggingFace API; valmikiramayan.net; search results for Shastri, Debroy
and the Baroda edition.

Not found: any published concordance between the Baroda critical edition
and Dutt or the Bombay vulgate. The one proposed here is computed.

---

## 10. Revision history

**Re-check (same day).** Corrected: hash fallback affects 34 works, not 14;
Kiṣkindhā/Sundara identities confirmed by text; Dutt section counts by
numeral (658); Griffith omissions made explicit; per-sarga verse agreement
measured (596 of 606); IWLV and valmikiramayan.net descriptions limited to
what was observed; Wikisource sarga counts parsed directly.

**Exact-alignment revision.** Replaced the four alignment options with the
sarga-exact two-step procedure in 5.2, backed by the Bālakāṇḍa pilot
(61 of 76 openings coincide at ≥ 0.85, two genuine non-coincidences,
vulgate 1.9 has no CE counterpart, 44% verbatim half-verse overlap with a
crude normaliser). Added the Wikisource marker-format finding, the Yuddha
count discrepancy (128 vs 131), and the statement that verse-exact
alignment is not achievable with any licensed translation.

**Diodorus revision.** Added 5.4: the sibling Diodorus pipeline as a second,
independent aligner whose agreement with the Sanskrit-text concordance is
required before a pairing is accepted.

**No-human revision.** Requirements 2–4 recorded. Added 5.5, the
anchors-and-intervals design: anchors only where the Sanskrit-text
concordance and the entity check agree, intervals elsewhere, thresholds
calibrated once on known-by-construction data; Bāla pilot gives 28%
anchors with the entity check alone.

**Review, 2026-09-27.** Re-measured and confirmed: all section 2 counts
(606 files, 38,004 sentences, 50 unnumbered, 18,715 verses, the seven hash
book numbers and their line counts, 34 hash-numbered works); the Smith
critical edition's 606 sargas and 18,761 verse ids per kāṇḍa, 596 of 606
per-sarga maxima identical with the same ten exceptions; Dutt's section
counts (77, 118, 75, 67, 67, 130, 124; 658) and the Bāla misprints;
Griffith Books II, III and V; the Wikisource CC BY-SA 4.0 footer and
Bālakāṇḍa's 77 sargas; the four Dutt and one Griffith Gutenberg records
(3.7 MB and 2.4 MB); the Smith `Ram07.txt` header without a copyright line;
the IWLV arXiv record and the HuggingFace 401. Corrected or added: the
licence version (4.0); the `DCS verses` column's definition; the fact that
hash-valued `books.id` values already change per rebuild, which settles the
bookmark question in 7; line numbers for the parser, the books INSERT and
the translation-path defect; the Dutt volume-to-kāṇḍa mapping; worldwide
public-domain reasoning for Dutt and Griffith; the project's existing
acceptance of CC BY-SA and shipping of Wikisource text.
