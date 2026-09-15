# Latin POS plan — LDT first, Stanza fallback

Status: **implemented and shipped.** `latin_treebank_loader.py`,
`latin_stanza_nlp.py`, the rewritten `generate_latin_interlinear.py`, and the
`topical`/Kotlin/Swift parser updates are all committed (0.8.129, files dated
2026-05-30). The shipped `latin_texts_extended.db` carries 358,806 POS-bearing
interlinear segments. Three items from §6 were **not** done — see §0.4.

Revision 2 (2026-08-16). Revision 1 was written as "design only. No code changes
yet" and was never updated after the work landed, so its §3 "Today's state"
described a world that no longer existed. It was also re-verified claim by claim
against the LDT XML, the shipped DB, and the code that was actually written.
**Several of its factual claims were wrong, and one of them was implemented
verbatim and is a live bug (§0.2 item 1).**

Companion to `latin/LEWIS_SHORT_PLAN.md` and to
`sanskrit/SANSKRIT_INTERLINEAR_IMPLEMENTATION_PLAN.md`, which this mirrors.

## 0. Corrections to revision 1

### 0.1 The document was stale

Revision 1's header said "design only. No code changes yet." All of the
following were already committed when that line was still in the file:

| Revision 1 called it | Reality |
|---|---|
| `latin_treebank_loader.py` — "new file, ~250 LOC" | Exists, 20,320 bytes, git-tracked |
| `latin_stanza_nlp.py` — "new file, ~80 LOC" | Exists, 5,186 bytes, git-tracked |
| `generate_latin_interlinear.py` — "to modify" | Rewritten (29,717 bytes) |
| `topical/build_topical_pack.py:parse_interlinear_latin` — "to modify" | Done; its docstring cites this plan as completed |
| `LemmaBagBuilder.kt:parseLatin` / `.swift` — "to modify" | Both done |
| §3.2 "No POS, no dependency, no `~` marker" | The DB has carried `~ POS DEPREL HEAD sentPos sentId` since the 0.8.129 rebuild |
| §3.1 translator string `Interlinear (Beta, AI-generated from app dictionary)` | Actual string is `Interlinear (Beta, generated from app dictionary and treebank)` |

Anyone following revision 1's §8 order of operations would have re-implemented
finished work against a design that differs from what shipped.

### 0.2 Factual errors — one of them shipped as a bug

1. **`postag` position 8 is CASE, not proper/common — and the code believes
   otherwise.** Revision 1 §5.1: *"Letter 8 = whether the word is a proper noun
   (`p` for proper)."* The authoritative `TAGSET.txt`, sitting in the same
   directory the loader reads from
   (`data-sources/treebank_data/v2.1/Latin/TAGSET.txt`), says position 8 is
   **case** with values `n g d a v b l`. There is no proper-noun flag anywhere
   in the Latin 9-character scheme, and no `p` occurs at position 8 anywhere in
   the corpus (measured distribution: `-` 41,499, `a` 11,836, `n` 10,665,
   `b` 8,253, `g` 4,099, `d` 2,203, `v` 311, `_` 71, `l` 44).

   `latin_treebank_loader.py:74-77` implements the wrong claim:

   ```python
   if p0 == "n":
       if len(postag) > 7 and postag[7] == "p":
           return "PROPN"
       return "NOUN"
   ```

   `postag[7]` is position 8, i.e. case. The branch is dead. Running
   `perseus_postag_to_upos` over all 79,670 LDT tokens produces **PROPN 0
   times**; all 19,630 LDT nouns come back `NOUN`.

   The comment above it (`# For nouns, position 7 = type: c=common, p=proper`,
   example `"n-s---fap-"`) is a 10-character tag from a different tagset; every
   real tag in this corpus is exactly 9 characters (78,981 of them; the other
   689 tokens have no `postag` at all).

   **Consequence for §1 goal 2:** the `entity` kind cannot get PROPN from LDT,
   in this or any future alignment version. Every one of the 97,133 PROPN-
   bearing segments in the shipped DB came from Stanza. That is not a disaster —
   Stanza covers 99.7% of segments anyway — but the plan sold LDT as giving
   "PerseusLDT-quality" proper nouns on the canonical authors, and LDT has no
   proper-noun annotation to give.

   **This is a live code defect, left unfixed pending a decision** — see §0.5.

2. **LDT token count understated by ~50%.** Revision 1 §5.1: "~53k tokens".
   Measured: **79,670 `<word>` elements**, of which 11,905 are punctuation
   (`postag[0] == 'u'`), so **67,765 linguistic tokens**. Also 664 tokens carry
   no `lemma` and 689 no `postag`; the plan never mentions either case.

3. **Five of the twelve work identifications are wrong, and the appendix's two
   tables contradict each other.** Verified from each file's own TEI header:

   | File | Revision 1 said | Header says |
   |---|---|---|
   | `phi0620.phi001` | Tibullus, *Elegies* | **Propertius**, *Elegies* |
   | `phi1221.phi007` | Propertius | **Augustus, *Res Gestae*** |
   | `phi1348.abo012` | Augustine, *De Civitate Dei* | **Suetonius, *Divus Augustus*** |
   | `phi0972.phi001` | Phaedrus, *Fabulae* (first table) / Petronius (second) | **Petronius** |
   | `phi0975.phi001` | Petronius, *Satyricon* (first table) / Phaedrus (second) | **Phaedrus, *Fabulae Aesopiae*** |

   Phaedrus and Petronius are simply swapped between the appendix's two tables,
   and the first table is the wrong one for both. §5.1's author list also omits
   Tibullus/Propertius and Tacitus, which the appendix includes.

4. **Caesar is *Bellum Gallicum* book 2, not book 1 or "book 7 area".** §5.1
   says "Caesar (BG 1)", the appendix says "book 7 area". The 71 sentences carry
   subdocs `2.1` through `2.33`.

5. **The file glob in §5.3 would silently drop the largest LDT file.** §5.3
   gives the path as `data-sources/treebank_data/v2.1/Latin/*.tb.xml`. The files
   are one level deeper, in `v2.1/Latin/texts/`, **and one of the twelve is
   named `phi0972.phi001.perseus-lat1.xml` with no `.tb`** — Petronius, 1.45 MB,
   1,120 sentences, the biggest single file in the set. A `*.tb.xml` glob drops
   it without error. (The implementation used `*.xml` and is not affected; the
   documented path was wrong, not the code.)

6. **"Ovid mechanically aligns because verse number == line_number" is wrong for
   72% of its sentences.** 227 of Ovid's 317 subdocs are *ranges*
   (`1.1-1.2`, `1.5-1.7`, `1.775-1.778`), not single lines. Only 90 are single
   references. Vergil is the only file in the set whose subdocs are uniformly
   one line each (`6.1` … `6.295`). The shipped loader handles ranges by taking
   the head (`subdoc.split("-", 1)[0]`, lines 95/107/118), which is a reasonable
   approximation but drops the tail lines of every range — worth stating, since
   revision 1 presented Ovid as clean.

7. **Sentence counts:** Cicero is **327**, not 326, so the "dropped from v1"
   total is 4,442, not 4,441. Everything else in that column matches. Corpus
   total is 4,936 sentences.

8. **`phi0620` is book.POEM, not BOOK.LINE.** Revision 1 lists it as
   "BOOK.LINE but unverified". Subdocs run `1.1` … `1.22` over 364 sentences —
   book 1, poems 1-22. It could never have aligned against `line_number`.

9. **LDT gold-tag share overstated by 4× to 40×.** §11 claims "LDT gold tags:
   ~5–8% of Latin tokens". Against the Latin corpus of **4,813,689 tokens**:

   | | Tokens | Share |
   |---|---|---|
   | All twelve LDT files, if every one aligned | 67,765 | **1.41%** |
   | What actually shipped (Vergil Aen. 6 + Ovid Met. 1) | 6,676 | **0.14%** |

   Not 5-8% under any reading.

10. **`~/stanza_resources/la_proiel/` is not where Stanza puts the model.**
    §5.3. Stanza's layout is `~/stanza_resources/<lang>/<processor>/<package>`,
    i.e. `~/stanza_resources/la/`. On this machine that directory **does not
    exist** — only `grc` and `sa` are present — so a Latin interlinear rebuild
    today would need `ensure_model_downloaded()` to fetch it first. The
    implementation passes `download_method=None` to `Pipeline`, so a worker that
    reaches Stanza without that pre-step fails rather than silently downloading.

11. **`stanza.Pipeline('la_proiel', …)` is not a valid call.** §6.1. Stanza takes
    `lang='la', package='proiel'`. The implementation
    (`latin_stanza_nlp.py:82-88`) does it correctly; only the plan was wrong.

12. **Two cited artefacts do not exist.** §8 step 10 cites `SPOTCHECK_11.md` —
    no file of that name exists in the repo. §9 gate 5 cites "the existing
    `ivf_recall@30` gate (≥ 0.95)" — the string `ivf_recall` appears **nowhere
    in the repository except this plan**.

13. **The audit command in §8 is not a valid invocation.** §8 step 0 gives
    `python3 -m text_integrity.audit --db perseus_texts_extended.db --corpus all`.
    `audit.py` takes the mode as a **positional** argument and has no `--db`
    flag. Appendix A's form (`… audit extended --corpus all`) is the correct one;
    the two contradict each other.

14. Appendix A references "§8 step #34". §8 has eleven steps.

### 0.3 Confirmed correct

LDT present at `data-sources/treebank_data` with 12 Latin files under
`v2.1/Latin/texts/` ✓; ~4,936 sentences ("~5k") ✓; sentence counts for the other
eleven files ✓; empty-subdoc diagnosis for `phi1221` (116/116) and `phi1351`
(197/197) ✓; Tacitus = `phi1351.phi005` *Annales* ✓; Vergil = Aeneid 6.1-6.295 ✓;
`postag` position 1 = POS with the listed letter values ✓ (only position 8 was
wrong); `<sentence id document_id subdoc>` / `<word id form lemma postag relation
head>` structure ✓; prose `line_number` being a paragraph counter rather than a
canonical reference ✓ — this was the key insight and it held up; `stanza ==
1.11.1` ✓; the cited baseline report
`20260530_170209_extended_all.{md,json}` exists ✓ with headline **260 passing of
2,743 works** ✓; `sanskrit/verify_interlinear_ready.py` and
`sanskrit/rebuild_sanskrit_pipeline.sh` both exist ✓; the `treebank_data` clone
line is in `BUILD.md:55` ✓.

### 0.4 What shipped, and what did not

Done: both new Python modules, the generator rewrite, the topical parser, the
Kotlin and Swift parsers, and the post-rebuild integrity audit (§0.6).

**Still outstanding:**

- **`latin/LATIN_POS_BUILD.md` was never written** (§6.1 listed it as a
  deliverable). There is no document telling anyone how to rebuild this.
- **`BUILD.md` — partly updated since, still incomplete.** The `treebank_data`
  clone was already there (line 55). `BUILD.md` and `CLAUDE.md` have since
  gained the correct Latin generation command and a "Latin interlinear — a
  separate generator, in the Latin module" subsection, which also fixed two
  false statements (see `LATIN_GLOSS_PLAN.md` §6.2 items 2-4).

  **Still missing: the Stanza prerequisite.** Stanza is now mentioned in that
  new subsection, but only descriptively — there is still no download step
  alongside the other Step 2 prerequisites, and `~/stanza_resources/la/` does
  not exist on this machine. Since `latin_stanza_nlp.py` builds its pipeline
  with `download_method=None`, a clean-machine rebuild still fails at the
  generator rather than self-fetching. That step is `LATIN_GLOSS_PLAN.md` §7.
- **The PROPN bug** (§0.2 item 1).
- **v2 canonical-ref alignment**, which is where 90% of the LDT data still is.

### 0.5 The PROPN defect — not fixed here

`latin_treebank_loader.py:74-77` is wrong and does nothing. The fix is to delete
the dead branch, because **there is no correct version of it** — LDT carries no
proper-noun annotation. That is a one-line change to shipped Latin build code
and it would alter the interlinear output for the two aligned books on the next
rebuild, so it is recorded here rather than applied. See §10 question 1.

Note the fix does not change the shipped DB's PROPN counts at all (the branch
never fired), so it is safe to defer; it only removes a misleading claim from
the code.

### 0.6 Gate #0 result — it passed

Revision 1 made the text-integrity diff the load-bearing gate. It was run, and
it passed:

| | Report | Works audited | Passing |
|---|---|---|---|
| Pre-rebuild baseline | `20260530_170209_extended_all.md` | 2,743 | 260 |
| Post-rebuild | `20260530_184354_extended_all.md` | 2,743 | 260 |

The post-rebuild report is now the repository baseline —
`data-prep/text_integrity/reports/baseline_extended_all.{md,json}` symlinks to
`20260530_184354_*`, not to the report Appendix A names. Anyone diffing against
Appendix A's path is diffing against the superseded pre-rebuild snapshot.

## 1. Goal (as shipped)

Give every Latin interlinear segment a POS tag, plus dependency relation and
head where available, in the same shape as Greek's treebank-derived format.

1. **POS-driven content-lemma filtering** in `topical/build_topical_pack.py` —
   done. `parse_interlinear_latin` now filters on `CONTENT_POS` from the `~`
   field instead of `.isalpha()`.
2. **The `entity` kind** for Latin (`topical/TOPICAL.md` — revision 1 cited
   "`TOPICAL.md` Part 1 §5.5"; the file is at `topical/TOPICAL.md` and has no
   §5.5, though the `entity` kind itself is real and documented there) —
   **verified working and already shipped, and sourced entirely from Stanza.**
   LDT contributes no PROPN at all (§0.2 item 1). See §1.1.
3. **Latin dependency-tree views** in the reader screen — the data is present
   (`DEPREL HEAD sentPos sentId` per token).


### 1.1 The `entity` kind for Latin — verified end to end

Checked against the code, the shipped data and the built pack, because
revision 1 described this as merely "possible".

**It works and it is built.** `topical/dist/latin/` contains `entity_bags.bin`,
`entity_vocab.bin` and `entity_invidx.bin`; the manifest lists
`kinds_available: ["lda", "tfidf", "entity"]` with `entity_vocab_size: 7527`
over 36,639 passages. Greek's equivalent pack has 14,743.

**It is Stanza-only, exactly as §0.2 item 1 predicts.** Measured on
`latin_texts_extended.db`:

| Interlinear segments carrying… | Count |
|---|---|
| a Stanza-tagged PROPN (`~ PROPN`) | **97,133** |
| a treebank-tagged PROPN (`~* PROPN`) | **0** |

`parse_entities_latin` (`topical/build_topical_pack.py:220`) gates on
`POS == "PROPN"` directly, and its own comment records why that is safe for
Latin but not Greek: "Stanza's UD-Latin output distinguishes PROPN from NOUN, so
we can gate on `POS == 'PROPN'` directly", whereas Greek approximates it with an
uppercase-initial heuristic because OGA/GLAUx do not tag PROPN either.

**Quality caveat: the entity vocabulary inherits the lemmatiser's errors.**
Parsing every Latin interlinear segment yields 18,211 distinct entity lemmas
(7,527 survive the pack's `min_df` filter). Testing each against the L&S
headword set:

| | Types | Tokens |
|---|---|---|
| Attested as an L&S headword | 4,789 (26.3%) | 70,015 (62.9%) |
| Not attested | 13,422 (73.7%) | 41,311 (37.1%) |

The unattested set mixes two different things and cannot be cleanly split
without ground truth: **fabricated lemmas** (`troias`, `iunus`, `iunonae`,
`iove` — where `Troia` and `Iuno` are the real forms and both *are* in L&S) and
**genuine L&S gaps** (`Etruria`, `Democritus`, `Lucretius`, `Verginius` are real
names L&S does not carry as headwords).

**The single largest defect is concrete:** the most frequent "entity" in the
Latin pack is `paior` at 2,331 occurrences — more common than `caesar` (1,472)
or `roma` (1,103). Every one of them comes from the surface form **`p`**, the
praenomen abbreviation *P.* (Publius), which Stanza lemmatises as `paior` and
tags PROPN. `LATIN_ENTITY_STOPLIST` stops grammatical abbreviations (`gen`,
`nom`, `acc`…) but not praenomen abbreviations.

**The fix must not be a longer stoplist** (CLAUDE.md; `LATIN_GLOSS_PLAN.md`
§1.2). Two general rules would cover it: require the *surface* form to have ≥2
letters — the parser currently applies that test to the lemma, so a 1-character
surface with a 5-character hallucinated lemma passes — and/or require the entity
lemma to be attested as a dictionary headword. Either is a class rule with no
vocabulary attached. Not proposed here; recorded for whoever owns the topical
pack.

## 2. Non-goals

- Not changing the Greek interlinear pipeline.
- Not changing how the Latin interlinear's **gloss** (English) is generated.
  Note that `latin_dictionary_lookup.py`'s docstring calls the Latin dictionary
  a "Lewis & Short derivative" — **that is false**, and revision 1 §3.1 repeated
  it. The DB has only ever held Whitaker's Words; see
  `latin/LEWIS_SHORT_PLAN.md` §8, which records the same wrong docstring.
- Not adding a third Latin treebank source (LASLA, ITTB, LLCT).
- Not adding a Latin equivalent of `OGA` / `GLAUx`.

## 3. State as shipped

### 3.1 Latin interlinear pipeline

`latin/build_modules/interlinear/`:

| File | Role |
|---|---|
| `generate_latin_interlinear.py` | Generator. LDT first, Stanza fallback, emits the POS format |
| `latin_treebank_loader.py` | Parses `v2.1/Latin/texts/*.xml`, indexes by `(book_id, line)` |
| `latin_stanza_nlp.py` | Thread-safe lazy singleton over `stanza.Pipeline('la', package='proiel', processors='tokenize,pos,lemma,depparse', download_method=None)` |
| `latin_dictionary_lookup.py` | English gloss + fallback lemma (Whitaker's, not L&S) |
| `latin_interlinear_list.py` | Per-work driver, multiprocessing |
| `INTERLINEAR_ALL_LATIN_WITH_IDS.csv` | Work list |
| `run_latin_interlinear_no_sleep.sh` | Bash wrapper |

### 3.2 Output format as shipped

Translator string: `Interlinear (Beta, generated from app dictionary and treebank)`.

```
| surface |
| **gloss** |
| LEMMA MORPH ~  POS DEPREL HEAD sentPos sentId |   (Stanza)
| LEMMA MORPH ~* POS DEPREL HEAD sentPos sentId |   (LDT gold)
```

Real row from the shipped DB:

```
| Vt | | **form of u** | | ut pos:N ~ SCONJ advmod 5 1 L1 |
```

This is the Sanskrit shape with LDT substituted for DCS, as intended.

### 3.3 Measured coverage in the shipped extended DB

Latin module: 360,007 `text_lines`, 4,813,689 `words`, 358,806 interlinear
segments.

| | Segments | Share |
|---|---|---|
| Carrying a Stanza (`~`) tag | 357,800 | 99.7% |
| Carrying an LDT (`~*`) gold tag | **846** | **0.24%** |

The 846 land in exactly two books:

| Book | Work | Lines |
|---|---|---|
| `phi0959.phi006.001` | Ovid, *Metamorphoses* 1 | 552 |
| `phi0690.phi003.006` | Vergil, *Aeneid* 6 | 294 |

Token-weighted, LDT supplies 6,676 of 4,813,689 Latin tokens — **0.14%**.
Revision 1 §11 claimed 5-8%.

**This should be read plainly: the shipped feature is a Stanza POS overlay.**
The LDT layer is real but currently decorative — two books out of the Latin
corpus. That is not a failure of the design; it is the v1 scope the appendix
correctly identified. It is a failure of §11, which described the result as
though the LDT layer were substantial.

## 4. Reference pattern — Sanskrit

Unchanged and confirmed: `sanskrit/generate_sanskrit_interlinear.py` reads DCS
CoNLL-U first and falls back to Stanza; one lazily-initialised pipeline per
worker; `~*` for treebank, `~` for Stanza; parallelism across works, not within
a pipeline. `latin_stanza_nlp.py` follows it.

## 5. Data sources

### 5.1 Perseus LDT — corrected inventory

Upstream `github.com/PerseusDL/treebank_data`, on disk at
`data-sources/treebank_data/v2.1/Latin/texts/`. **Twelve files. Note that one
lacks the `.tb` infix — glob `*.xml`, never `*.tb.xml`** (§0.2 item 5).

`postag` is Perseus's 9-character Harrington scheme. Positions, per
`v2.1/Latin/TAGSET.txt`:

| Pos | Field | Values |
|---|---|---|
| 1 | part of speech | `n v a d c r p m i e u` |
| 2 | person | `1 2 3` |
| 3 | number | `s p` |
| 4 | tense | `p i r l t f` |
| 5 | mood | `i s n m p d g` |
| 6 | voice | `a p d` |
| 7 | gender | `m f n` |
| 8 | **case** | `n g d a v b l` — **not proper/common** |
| 9 | degree | `p c s` |

**There is no proper-noun annotation in this tagset.** UPOS mapping can produce
`NOUN VERB ADJ ADV CCONJ ADP PRON NUM INTJ PUNCT` and nothing else.

Corrected inventory, from each file's own TEI header:

| File | Author / work | Sentences | `<word>` | Subdoc form |
|---|---|---|---|---|
| `phi0448.phi001.perseus-lat1.tb.xml` | Caesar, *Bellum Gallicum* **book 2** | 71 | 1,556 | `2.1`–`2.33` |
| `phi0474.phi013.perseus-lat1.tb.xml` | Cicero, *Orationes* | **327** | 6,652 | `1.1`… (1 empty) |
| `phi0620.phi001.perseus-lat1.tb.xml` | **Propertius**, *Elegies* | 364 | 5,297 | `1.1`–`1.22` = book.**poem** |
| `phi0631.phi001.perseus-lat1.tb.xml` | Sallust, *Catilina / Iugurtha / Historiae* | 699 | 13,177 | bare int |
| `phi0690.phi003.perseus-lat1.tb.xml` | Vergil, *Aeneid* 6 | 177 | 2,839 | `6.1`–`6.295`, one line each |
| `phi0959.phi006.perseus-lat1.tb.xml` | Ovid, *Metamorphoses* 1 | 317 | 5,202 | **227 of 317 are ranges** |
| `phi0972.phi001.perseus-lat1.xml` | **Petronius** *(no `.tb` in filename)* | 1,120 | 14,171 | bare int (chapter) |
| `phi0975.phi001.perseus-lat1.tb.xml` | **Phaedrus**, *Fabulae Aesopiae* | 583 | 6,588 | `1:prologus` colon scheme |
| `phi1221.phi007.perseus-lat1.tb.xml` | **Augustus, *Res Gestae*** | 116 | 3,035 | **all 116 empty** |
| `phi1348.abo012.perseus-lat1.tb.xml` | **Suetonius, *Divus Augustus*** | 347 | 8,313 | single range `1.1-154.4` |
| `phi1351.phi005.perseus-lat1.tb.xml` | Tacitus, *Annales* | 197 | 3,531 | **all 197 empty** |
| `tlg0031.tlg027.perseus-lat1.tb.xml` | Vulgate (Jerome) | 618 | 9,309 | bare int |
| **Total** | | **4,936** | **79,670** | 11,905 punctuation → **67,765 linguistic** |

689 tokens carry no `postag`; 664 carry no `lemma`.

### 5.2 Stanza Latin model

`stanza == 1.11.1`. `stanza.Pipeline(lang='la', package='proiel',
processors='tokenize,pos,lemma,depparse', download_method=None)`.

`la_proiel` is the right pick for the classical canon: `la_perseus` is the same
data as LDT (would replace, not supplement), `la_ittb` is Aquinas, `la_llct` is
late-Latin charters.

**The model is not currently cached on this machine.** `~/stanza_resources/`
holds `grc` and `sa` only; there is no `la`. Because the pipeline is constructed
with `download_method=None`, a worker that reaches Stanza without a prior
`ensure_model_downloaded()` will fail rather than fetch. This is correct
fail-loud behaviour, but it means **a Latin interlinear rebuild on this machine
today requires the download step first** — and that step is documented nowhere
outside this file (§0.4).

Revision 1's `~/stanza_resources/la_proiel/` is not a path Stanza uses.

### 5.3 Known Stanza caveat (from Appendix A, still valid)

Punctuation glues to tokens (`cano,` tagged as one NOUN). The generator
pre-strips punctuation before feeding Stanza; the Kotlin and Swift parsers also
`trimEnd` punctuation defensively.

## 6. Files — final state

### 6.1 Delivered

| File | Status |
|---|---|
| `latin/build_modules/interlinear/latin_treebank_loader.py` | shipped (20 KB) — **contains the §0.5 dead branch** |
| `latin/build_modules/interlinear/latin_stanza_nlp.py` | shipped (5 KB) |
| `latin/build_modules/interlinear/generate_latin_interlinear.py` | rewritten (30 KB) |
| `topical/build_topical_pack.py:parse_interlinear_latin` | shipped, POS-based |
| `app/.../topical/LemmaBagBuilder.kt:parseLatin` | shipped, POS-based |
| `ios/ClassicsViewer/Database/LemmaBagBuilder.swift:parseLatin` | shipped, POS-based |

### 6.2 Not delivered

| File | Status |
|---|---|
| `latin/LATIN_POS_BUILD.md` | **never written** |
| `BUILD.md` Latin POS section + build-order steps | **never added**; no Stanza mention outside Sanskrit |

## 7. Build pipeline integration — still to document

`BUILD.md` needs, before the Latin interlinear step:

```
N.  treebank_data clone present (already at BUILD.md:55)
N+1 Stanza Latin model present:
    $ ./venv/bin/python3 -c "import stanza; stanza.download('la', package='proiel')"
    (idempotent; required — the pipeline uses download_method=None and will
     not self-fetch inside a worker)
N+2 Regenerate Latin interlinear
N+3 Rebuild extended DB
N+4 Rebuild Latin topical pack
```

Determinism: LDT is static XML on disk. Stanza is pinned at 1.11.1 with a named
package and no sampling, so inference is deterministic for identical input.
Sentence segmentation is per line, copied from Sanskrit.

Parallelism: across works. Each worker holds one pipeline (~1.5 GB resident, so
8 workers ≈ 12 GB). LDT is loaded once in the parent and inherited copy-on-write.

**Rebuild wall-clock is unmeasured.** Revision 1 estimated "~30-60 min, 8
workers", but `CLAUDE.md` records the pre-POS Latin interlinear as **~17
seconds**, so the estimate was a projection of the Stanza cost, not a
measurement, and it was never checked against the run that actually happened.
Time it and record the real figure the next time the Latin interlinear is
regenerated.

## 8. Validation gates

**Gate #0 — text-integrity diff.** Ran, passed: 260/2,743 before and after
(§0.6). The current repository baseline is `baseline_extended_all.*` →
`20260530_184354_*`, **not** the pre-rebuild report Appendix A names. Correct
invocation is positional:

```bash
cd data-prep && python3 -m text_integrity.audit extended --corpus all
```

There is no `--db` flag; revision 1 §8 step 0 was not a runnable command.

Remaining gates, restated against measured reality:

1. **LDT alignment rate.** Revision 1 set "≥ 80% of LDT's ~53k tokens map to a
   `text_lines` row". As shipped the rate is **~10% of sentences (494 of 4,936
   attempted; 846 lines actually written)**, i.e. the gate as written would fail
   the build that shipped. It should be restated as a v1 floor — "≥ 2 works and
   ≥ 800 lines" — and raised when v2 alignment lands. A gate nobody can pass is
   not a gate.
2. **Stanza coverage** = every non-LDT Latin line emits at least one POS-tagged
   token. Shipped: 357,800 of 358,806 segments (99.7%) carry a `~`.
3. **POS distribution** — share of `NOUN/PROPN/VERB/ADJ` in [0.45, 0.65].
   Unverified; measure before relying on it.
4. **Determinism** — two consecutive builds produce byte-identical output for a
   wholly-LDT work. Unverified.
5. ~~Topical `ivf_recall@30` ≥ 0.95~~ — **no such gate exists**. The string
   appears nowhere in the repo outside this plan (§0.2 item 12). Either build
   the gate or drop the line.

## 9. What v2 would actually take

The appendix's core diagnosis was right and is worth restating precisely,
because it is the whole of the remaining work:

`text_lines.line_number` is a sequential paragraph/sentence counter within a
book, **not** the canonical citation. LDT's `subdoc` is canonical. They coincide
only where the canonical reference is itself a verse line number — which, across
the twelve files, is **Vergil alone**, plus the 90 non-range Ovid subdocs.

v2 means building a per-work `(book, canonical_ref) → line_number` index by
parsing the inline `[N.M]` markers embedded in `text_lines.line_text`, then
re-running alignment. That recovers up to 4,442 of the 4,936 sentences —
roughly 61,000 more gold tokens, taking LDT from 0.14% to ~1.4% of the Latin
corpus. Even fully realised it stays a small quality bump on a handful of works;
it is worth doing for the canonical authors, not for coverage.

Additional per-file obstacles v2 must handle, which the appendix listed as bare
"format-broken" and are worth naming:

- `phi1221` (Res Gestae) and `phi1351` (Tacitus): **every** subdoc is empty —
  no citation to align to at all. These cannot be recovered by ref-parsing;
  they need positional alignment or nothing.
- `phi1348` (Suetonius): all 347 sentences share the single range
  `1.1-154.4`, which carries no per-sentence information.
- `phi0975` (Phaedrus): `1:prologus` — colon-separated with non-numeric parts.
- `phi0620` (Propertius): book.**poem**, not book.line.

So of the 4,442 dropped sentences, **660 (Res Gestae + Tacitus + Suetonius) are
unrecoverable by ref-parsing alone**, not merely deferred.

### 9.1 v2 alignment — the plan's approach only works for one work

Measured 2026-08-16, prompted by the observation that the treebank lemmas we
already have should be usable beyond Aeneid 6.

**The prize is large.** Of 67,765 linguistic LDT tokens on disk, only ~6,676
(10%) reach the interlinear — Vergil Aen. 6 and Ovid Met. 1. The other ~61,000
are dropped at alignment. Gold lemmas are exactly what fixes the residual gloss
errors in `LATIN_GLOSS_PLAN.md` §10.2: `oris` glosses correctly in Aeneid 6
(treebank lemma) and wrongly in Aeneid 1 (Stanza lemma).

**§9's proposed method - parsing inline `[N.M]` canonical markers out of
`text_lines.line_text` - works for exactly one work.** Surveyed all twelve:

| Work | Lines | Carry `[N.M]` markers |
|---|---|---|
| **Caesar, *BG*** | 2,464 | **87%** — `[1.1]`, `[1.2]`, `[2.1]` … |
| Cicero, Propertius, Sallust, Petronius, Phaedrus, Suetonius, Tacitus | 504-3,993 each | **0%** |
| Res Gestae, Vulgate | — | **no `text_lines` at all** |
| Vergil, Ovid | — | 0% (already aligned by verse number) |

So marker-parsing recovers Caesar's 71 sentences and nothing else.

**A scheme-independent method does work: match on the text itself.** LDT stores
the surface form of every word, so a sentence can be located by finding the
`text_lines` row containing its opening words - no citation scheme involved.
Tested on the first 6 sentences of three works:

| Work | Located by matching first 4 content words |
|---|---|
| Sallust | **6/6** |
| Cicero | **5/6** |
| Tacitus | **0/6** — needs investigation (likely a different edition or orthography) |

Sallust and Cicero are both works that citation-matching cannot touch, so this
is the more promising route. It would need proper sequence alignment rather than
a first-4-words probe, and Tacitus shows it is not universal.

**Recorded as a finding, not implemented.** It is a separate piece of work from
the gloss fix, and the estimate in §9 ("recovers up to 4,442 of the 4,936
sentences" by ref-parsing) should be read as **wrong about the method**, though
the prize it names is real.

### 9.2 Use LDT as a lexicon, not just a per-line overlay

Measured 2026-08-16. **This is a larger and cheaper win than the §9.1 alignment
work, and it needs no alignment at all.**

The current design applies LDT only to lines it can align to a `(book_id,
line_number)`, which is why gold lemmas reach 0.14% of tokens. But a
surface-form -> lemma mapping is not location-dependent. `oris -> ora` learned
in Aeneid 6 is just as true in Aeneid 1.

Building that table from all 12 files gives **67,108 tokens over 18,897 distinct
surface forms**, of which **83% have exactly one lemma**.

Coverage of the actual corpus:

| | Aeneid 1 | All Latin (4,813,689 tokens) |
|---|---|---|
| LDT has the surface form | 55.6% | **62.6%** |
| …and gives exactly one lemma | 17.0% | **14.8%** |
| Treebank lemmas reaching the interlinear today | — | **0.14%** |

So a safe, unambiguous-only lookup takes gold lemma coverage from 0.14% to
~15% - roughly 100x. Taking the majority lemma where LDT disagrees with itself
would reach ~62%, with more risk.

Examples, with LDT's own counts:

| Surface | LDT lemmas | Note |
|---|---|---|
| `alto` | `altus1` | unambiguous, correct |
| `casus` | `casus1` | unambiguous, correct |
| `fidem` | `fides1` x20, `fides2` x1 | strong majority, would fix a known regression |
| `oris` | `ora1` x4, `os1` x1 | majority correct - this is the Aeneid 1.1 case |
| `ora` | `os1` x12, `ora1` x3 | **majority is wrong** for some contexts |
| `tutum` | `tueor` x2 | LDT agrees with Stanza; genuinely ambiguous, not a tagger error |

**Caveats.** Only ~15% of tokens are unambiguous by TOKEN count even though 83%
of distinct forms are, because the common words are the ambiguous ones. Majority
voting ignores context and `ora` shows it can pick wrong. And it does not fix
`tutum` - `LATIN_GLOSS_PLAN.md` §10.2 case 1 attributes that to a tagger error,
which this measurement contradicts: LDT assigns `tueor` too.

**Not implemented.** Recorded because it changes the priority: §9.1's alignment
work recovers ~61,000 gold tokens after real sequence-alignment engineering,
whereas this recovers a comparable signal from data already parsed, with a
dictionary lookup.

## 10. Open questions

1. **Fix the PROPN dead branch** (§0.5)? The correct fix is deletion, since LDT
   has no proper-noun layer. It changes no shipped output (the branch never
   fired) but does touch Latin build code, so it needs a call before the next
   interlinear regeneration.
2. **Write `LATIN_POS_BUILD.md` and the `BUILD.md` section** (§0.4, §7)? Right
   now there is no documented way to rebuild this, and the Stanza model is not
   on disk, so the pipeline is not reproducible on a clean machine.
3. **Restate or delete the unmeetable gates** (§8 items 1 and 5)?
4. **Is v2 alignment worth ~1 day** for a rise from 0.14% to ~1.4% of Latin
   tokens (§9)? The honest framing is that this is a quality bump on ten works,
   not a coverage change.
5. **Fix the `latin_dictionary_lookup.py` docstring** claiming Lewis & Short
   (§2)? Tracked in both this plan and `LEWIS_SHORT_PLAN.md` §8; still wrong in
   the code.

## 11. Honest scope summary — replaces revision 1's §11

Latin POS coverage as shipped, against 4,813,689 corpus tokens:

| | Share |
|---|---|
| **LDT gold tags** | **0.14%** (2 books; revision 1 claimed 5-8%) |
| **LDT gold tags if v2 alignment lands** | ~1.4% |
| **Stanza tags** | 99.7% of interlinear segments |
| **Neither** | small residual |

The `entity` kind for Latin is available now, from Stanza's PROPN only.

## 12. How revision 2's numbers were obtained

- **LDT statistics**: stdlib `xml.etree` over
  `data-sources/treebank_data/v2.1/Latin/texts/*.xml` — `<sentence>` and
  `<word>` counts, `subdoc` values, `postag` position histograms. Work identity
  read from each file's own `<title>`/`<author>` TEI header, not from the
  filename.
- **Tagset**: `data-sources/treebank_data/v2.1/Latin/TAGSET.txt`, verbatim.
- **PROPN test**: imported `perseus_postag_to_upos` from the shipped
  `latin_treebank_loader.py` and ran it over all 79,670 tokens.
- **Shipped coverage**: `latin/latin_texts_extended.db` —
  `translation_segments` filtered on `translator LIKE 'Interlinear%'` and
  `translation_text LIKE '%~*%'` / `'% ~ %'`, grouped by `book_id`.
- **Corpus scale**: `COUNT(*)` on `text_lines`, `words`, `translation_segments`.
- **Audit headlines**: `grep` on the two report `.md` files; baseline symlink
  target from `ls -la`.
- **Stanza**: `venv/bin/python3 -c "import stanza; print(stanza.__version__)"`
  and `ls ~/stanza_resources/`.

---

*End of plan.*
