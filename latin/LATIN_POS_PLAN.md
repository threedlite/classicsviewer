# Latin POS plan — LDT first, Stanza fallback

Status: design only. No code changes yet. Companion to
`sanskrit/SANSKRIT_INTERLINEAR_IMPLEMENTATION_PLAN.md`, which this directly
mirrors — Latin has no part-of-speech tags today, Sanskrit was in the same
state before its interlinear was rebuilt with DCS-treebank-primary + Stanza-
fallback. Apply that same pattern here.

## 1. Goal

Give every Latin interlinear segment a POS tag (and dependency relation + head
where possible), comparable in shape to Greek's treebank-derived format. This
unlocks:

1. **POS-driven content-lemma filtering** in `topical/build_topical_pack.py` —
   today `parse_interlinear_latin` falls back to `.isalpha()` because Latin has
   no POS column. With POS we filter to `NOUN/PROPN/VERB/ADJ` like Greek does,
   which improves both TF-IDF quality and the same-author-bias evaluation.
2. **The `entity` kind** for Latin (planned in `TOPICAL.md` Part 1 §5.5).
   Without POS we have no way to pull `PROPN` tokens. With POS we get
   PerseusLDT-quality on the canonical authors, Stanza-quality everywhere else.
3. **Latin dependency-tree views** in the reader screen (the same feature
   Greek and Sanskrit already support).

## 2. Non-goals (this plan)

- Not changing the Greek interlinear pipeline.
- Not changing how the Latin interlinear's **gloss** (English) is generated —
  the dictionary-lookup path stays.
- Not adding a third Latin treebank source (e.g. LASLA, ITTB, LLCT). LDT +
  Stanza is the scope.
- Not adding a Latin equivalent of `OGA` / `GLAUx` as standalone data sources —
  LDT is the only gold corpus we ingest.

## 3. Today's state

### 3.1 Latin interlinear pipeline

Lives at `latin/build_modules/interlinear/`:

- `generate_latin_interlinear.py` — the actual generator. Walks each Latin work,
  parses surface tokens, looks up lemma + English gloss via the Latin
  dictionary, writes a `translation_segments` row per text line under the
  translator string `Interlinear (Beta, AI-generated from app dictionary)`.
- `latin_dictionary_lookup.py` — wraps the Latin dictionary (Lewis & Short
  derivative). Returns `(lemma, morphology, gloss)` per surface form. **Does
  not return POS.**
- `latin_interlinear_list.py` — per-work driver, multiprocessing.
- `INTERLINEAR_ALL_LATIN_WITH_IDS.csv` — list of every Latin work to process.
- `run_latin_interlinear_no_sleep.sh` — bash wrapper (caffeinate on macOS).

### 3.2 Output format today

Per token, inside `translation_segments.translation_text`:

```
| surface | | **gloss** | | LEMMA MORPH … |
```

No POS, no dependency, no `~` marker.

Compare Greek (post-OGA):

```
| LEMMA MORPH ~ POS DEPREL HEAD sentPos sentId |
```

And Sanskrit (post-DCS + Stanza), which already uses both markers:

```
| LEMMA MORPH ~* POS DEPREL HEAD sent_pos sent_id |   (DCS treebank, gold)
| LEMMA MORPH ~  POS DEPREL HEAD sent_pos sent_id |   (Stanza fallback)
```

The Latin target format is **exactly the Sanskrit shape**, swapping LDT for
DCS as the treebank source.

### 3.3 What `topical/build_topical_pack.py` sees

`parse_interlinear_latin` currently iterates the existing fields and emits
a content-lemma bag using `.isalpha()` and a `LIGHT_LEMMATA` stop-list as
substitutes for POS. After this plan, it can use the new `~/~*` markers and
the `POS` field — same code path as `parse_interlinear_greek`.

## 4. Reference pattern — Sanskrit

The Sanskrit interlinear pipeline already implements LDT-equivalent + Stanza
fallback. Anything called out below is already proven in `sanskrit/`:

- `generate_sanskrit_interlinear.py` reads DCS CoNLL-U treebank first, falls
  back to Stanza for every passage DCS doesn't cover.
- Stanza is loaded **once per worker process** via a lazy singleton
  (`get_stanza_nlp()`), thread-safe with a lock, then reused.
- Each emitted token is tagged `~*` if it came from the treebank, `~` if from
  Stanza.
- Both DCS and Stanza paths produce: lemma, morph features, POS, deprel,
  head, sentence position, sentence id. The renderer doesn't care which
  source.
- Multiprocessing parallelises *across works*, not within a single Stanza
  pipeline invocation (Stanza is heavy — each worker owns one model in RAM).
- `requirements.txt` pins `stanza==<version>` and the post-install step runs
  `stanza.download('<lang>', verbose=False)` once before any worker starts.

The Latin plan should reuse this control flow line-for-line and only change
the language code (`sa` → `la`) and the treebank loader (DCS → LDT).

## 5. Data sources

### 5.1 Perseus LDT (Latin Dependency Treebank)

- Upstream: `github.com/PerseusDL/treebank_data`, branch `master`, path
  `v2.1/Latin/data/*.tb.xml`.
- Format: Perseus's own TEI-treebank XML. Each `<sentence>` carries
  `document_id`, `subdoc` (canonical citation like `1.1.1`), and `<word>`
  elements with `id`, `form`, `lemma`, `postag`, `head`, `relation`, `cite`
  (CTS URN).
- `postag` is Perseus's 9-letter scheme. Letter 1 = POS (`n` noun, `v` verb,
  `a` adjective, `p` pronoun, `c` conjunction, `r` preposition, `m` numeral,
  `i` interjection, `d` adverb, `e` exclamation, `u` punctuation). Letter 8 =
  whether the word is a proper noun (`p` for proper). We convert this to
  Universal Dependencies (`NOUN/PROPN/VERB/ADJ/...`) at load time.
- Coverage: ~53k tokens across ~15-20 partial works. Confirmed authors include
  Caesar (BG 1), Cicero (Cat 1, Pro Archia, a few letters), Vergil (Aen 6),
  Ovid (Met 1), Sallust (Catiline), Phaedrus, Petronius, Propertius (1),
  Augustine (Civ Dei selections), Vulgate (small set). The rest of the Latin
  canon (Tacitus, Lucretius, Horace, Seneca, Pliny, most of Cicero,
  remainder of Vergil/Ovid/Caesar) is **not in LDT** and stays with Stanza.

### 5.2 Stanza Latin model

- Library: `stanza` (already in venv for Sanskrit; same dependency).
- Model: `stanza.Pipeline('la', processors='tokenize,pos,lemma,depparse')`.
- Default `la` model in current stanza is **PROIEL** (~250k tokens from NT
  Vulgate Latin + classical authors, broad-coverage). Better choices for
  classical-canon recall:
  - `la_proiel` — broad classical Latin (default; best general fit)
  - `la_perseus` — same data as LDT, would *replace* not supplement LDT; not
    useful for fallback
  - `la_ittb` — Aquinas only, wrong register for our canon
  - `la_llct` — Late Latin charters, wrong register
- Pick `la_proiel`. Documented in the plan; pinned in `requirements.txt`.

### 5.3 Where data lives on disk

**LDT is already present** at
`data-sources/treebank_data/`. The Latin XML lives at:

```
data-sources/treebank_data/v2.1/Latin/*.tb.xml   ← primary, what we'll use
data-sources/treebank_data/v2.0/Latin/*.tb.xml   ← older versioned drop
data-sources/treebank_data/v1.6/latin/*.xml      ← older still
data-sources/treebank_data/v1/latin/*.xml        ← oldest
```

We read **v2.1/Latin** as the canonical source. No new clone needed; the
build script just walks that directory.

Per `CLAUDE.md`, `data-sources/` is **read-only** for our purposes — we
parse the XML, write nothing back. No `git pull` step in the build script.
If the upstream repo ever needs updating, that's a manual user action,
out of scope for this plan.

Stanza models download lazily to `~/stanza_resources/la_proiel/` on first use.

## 6. Files to add / modify

### 6.1 New files

| File | Purpose | LOC est. |
|---|---|---|
| `latin/build_modules/interlinear/latin_treebank_loader.py` | Parse LDT TEI XML, expose `LdtLoader.lookup(book_id, line, surface) -> (lemma, morph, pos, deprel, head, sent_pos, sent_id) \| None` | ~250 |
| `latin/build_modules/interlinear/latin_stanza_nlp.py` | Lazy singleton around `stanza.Pipeline('la_proiel', …)`; mirrors `sanskrit/`'s wrapper | ~80 |
| `latin/LATIN_POS_BUILD.md` | Build instructions: clone LDT, install stanza, download model, rebuild Latin interlinear, regenerate extended DB and Latin topical pack | ~120 |

### 6.2 Modified files

| File | Change | LOC est. |
|---|---|---|
| `latin/build_modules/interlinear/generate_latin_interlinear.py` | (a) Try LDT first per-token via `LdtLoader`; (b) fall back to Stanza per-sentence (batched); (c) emit new format with `~*` / `~` marker + POS + deprel + head + sent_pos + sent_id; (d) thread-safe Stanza singleton like Sanskrit | ~150 net |
| `latin/build_modules/interlinear/latin_dictionary_lookup.py` | No change to dictionary lookup itself; but pipeline now consumes lemma from LDT/Stanza when available and only uses dict-lemma when neither has it (rare) | ~30 net |
| `latin/build_modules/interlinear/latin_interlinear_list.py` | Pass LDT loader handle + stanza-ready flag to workers | ~20 |
| `latin/build_modules/interlinear/run_latin_interlinear_no_sleep.sh` | Run a pre-step that downloads the Stanza model if missing, the way `sanskrit/rebuild_sanskrit_pipeline.sh` does | ~15 |
| `topical/build_topical_pack.py` | `parse_interlinear_latin` switches to POS-based filtering, same shape as `parse_interlinear_greek`. The `LIGHT_LEMMATA_LATIN` stop-list shrinks to only catch what the POS filter misses | ~30 net |
| `app/src/main/java/com/classicsviewer/app/topical/LemmaBagBuilder.kt` | `parseLatin` updated to match the new Python parser (POS-based). Even though the build's `bags.bin` makes this runtime-irrelevant for topical TF-IDF, the parser is still used by other features | ~30 net |
| `ios/ClassicsViewer/Database/LemmaBagBuilder.swift` | Same as Kotlin | ~30 net |
| `requirements.txt` | Pin `stanza==<version>` (probably already there for Sanskrit) | 1 |
| `BUILD.md` | Add the new Latin POS section; update build-order to put LDT clone + stanza download before Latin interlinear regeneration | ~40 |

Total: ~750 LOC across ~12 files. Most of it in `generate_latin_interlinear.py`
and the new `latin_treebank_loader.py`.

### 6.3 Files **not** modified

- `data-prep/` build scripts — no changes. Latin interlinear regen happens
  before the extended DB rebuild, same as today.
- Anything Greek (`greek/build_modules/`) — untouched.
- Anything Sanskrit — untouched (reused as the reference model only).
- iOS app project files — adding Swift sources is build-side only; no
  `.xcodeproj` regeneration (per project rules).

## 7. Build pipeline integration

### 7.1 New build-order step

Slot a new step into the extended-mode end-to-end sequence in `BUILD.md`,
**before** Latin interlinear regeneration:

```
... existing steps ...
8. (NEW) Clone PerseusDL/treebank_data into data-sources/ if not present
9. (NEW) Verify stanza.la_proiel is downloaded
   $ python -c "import stanza; stanza.download('la', package='proiel')"
10. Regenerate Latin interlinear (existing step, now uses LDT + Stanza)
11. Rebuild extended DB (existing)
12. Rebuild Latin topical pack (existing)
```

Steps 8 and 9 are idempotent — they noop if the clone and model are already
present.

### 7.2 Determinism

- **LDT**: clone is pinned to a tagged commit (recorded in `BUILD.md`). Same
  XML in → same output.
- **Stanza model**: pin `stanza` library version and `la_proiel` model version
  in `BUILD.md`. Stanza's `download(...)` is version-tagged on the resource
  side; passing `processors='tokenize,pos,lemma,depparse'` and not setting
  any sampling temperature means inference is deterministic for a given input.
- **Sentence batching**: Stanza is run per-sentence within a work. Sentence
  boundaries are recovered from Perseus text segmentation (line-as-sentence
  is fine for prose; for verse we group by punctuation). Whatever rule we
  pick, document it in the build script so it's reproducible.

### 7.3 Parallelism

- Workers parallelise across **works**, like the Latin pipeline does today.
- Each worker keeps **one** `stanza.Pipeline` instance, lazily initialised on
  first use. ~1.5 GB RAM per worker for `la_proiel`, so 8 workers ≈ 12 GB
  resident — fits a 32 GB dev machine but is the new peak.
- LDT is loaded **once** in the parent process, then shared via copy-on-write
  fork to workers (~50 MB).

## 8. Order of operations (proposed)

0. **Take a text-integrity baseline snapshot — BEFORE any changes** (~30 min).

   The build pipeline already has a strict-read-only audit at
   `data-prep/text_integrity/` (`audit.py`). It verifies every byte of source
   text and English translation that enters the pipeline survives intact into
   the DB. Run it on the extended DB **right now**, save the report under
   `data-prep/text_integrity/reports/`, and **commit the report path / SHA
   into this plan's appendix** before any code change.

   ```bash
   cd data-prep
   python3 -m text_integrity.audit \
       --db perseus_texts_extended.db \
       --corpus all
   ```

   Output lands in `data-prep/text_integrity/reports/<timestamp>_extended_*.md`
   and a `.json` sidecar. After the Latin POS rebuild, **rerun the same
   audit** and diff against this baseline. Any per-work pass/fail that
   regresses points at a Latin pipeline change that broke text integrity
   somewhere else — exactly the failure mode this tool exists to catch.

   This is a non-optional gate. The plan is to add POS to Latin interlinear,
   not to disturb the original Latin or English text. The audit confirms we
   haven't.

1. **Land the data sources** (~10 min)
   - **LDT is already on disk** at `data-sources/treebank_data/v2.1/Latin/`.
     Verify the file count and that `*.tb.xml` parses with a 5-line smoke
     script.
   - Verify `stanza` is in venv; `stanza.download('la', package='proiel')`.
2. **Write LDT loader** (~3 hours)
   - Parse TEI-treebank XML, map LDT's CTS-URN-based references to our
     `text_lines (book_id, line_number)`.
   - Build an in-memory index: `(book_id, line_number) -> [(token_idx, lemma,
     pos, …)]`.
   - The alignment is the brittle part. Strategy: (a) for each LDT word with a
     `cite` URN, look up the matching `text_lines` row by URN→book_id;
     (b) within that line, match LDT's surface form to our tokenisation by
     ordered string-equality, falling back to first unmatched token if
     surface forms diverge (LDT and Perseus tokenise enclitics
     differently in a small number of cases).
3. **Write Stanza wrapper** (~1 hour)
   - Copy `sanskrit/`'s lazy singleton pattern verbatim, swap language code.
4. **Wire into `generate_latin_interlinear.py`** (~4 hours)
   - For each line: ask LDT first; for tokens LDT didn't cover, batch through
     Stanza; emit in the new format with `~*` / `~` markers.
   - Keep the existing dictionary-gloss path for English glosses.
5. **Update Latin parser in `topical/build_topical_pack.py`** (~1 hour)
   - Mirror `parse_interlinear_greek`'s POS filter. Shrink `LIGHT_LEMMATA_LATIN`.
6. **Update Kotlin + Swift `LemmaBagBuilder.parseLatin`** (~1 hour)
   - Match the Python parser exactly.
7. **Regenerate Latin interlinear** (~30–60 min wall, 8 workers)
   - One-shot rerun of `run_latin_interlinear_no_sleep.sh`.
8. **Regenerate extended DB** (~28 min)
   - `python3 create_perseus_database.py extended`. The new interlinear gets
     pulled into `translation_segments`.
9. **Rebuild Latin topical pack** (~3 min)
   - `python3 topical/build_topical_pack.py latin --lda-k-topics 1000 --lda-iter 200`.
10. **Spot-check** (~30 min)
    - Run a Latin equivalent of `SPOTCHECK_11.md` on a half-dozen Latin works,
      both LDT-covered (Vergil Aen 6, Cicero Cat 1) and Stanza-only
      (Tacitus Annales 1, Lucretius DRN 1). Confirm POS filtering improves
      the visible cluster quality.
11. **Build APK + redeploy** (~5 min).

Cumulative wall-clock: **~10–12 hours of code + ~1 hour of builds** spread
across 2 working days.

## 9. Validation gates

Build fails red if any of these miss — copy the gate machinery from
`sanskrit/verify_interlinear_ready.py`. Gate #0 is the new one for this plan:

**Gate #0 — text-integrity diff (load-bearing).** The post-rebuild
`data-prep/text_integrity/audit.py` report **must match the pre-rebuild
baseline at the per-work level for every non-Latin corpus**, and the Latin
audit must show no regressions in source-text or English-translation
integrity (only the interlinear translator's segments are allowed to
change). Any unexpected per-work pass→fail outside Latin interlinear means
we mutated something we shouldn't have; the release is blocked until the
delta is explained.

1. **LDT alignment rate** ≥ 80 % of LDT's ~53k tokens map to a Perseus
   `text_lines` row. (Below this, alignment is broken and we'd be silently
   dropping treebank data.)
2. **Stanza coverage** = 100 % of non-LDT Latin lines emit at least one
   POS-tagged token. (Below this, Stanza isn't running on something.)
3. **POS distribution** — across all Latin interlinear rows, the share of
   `NOUN/PROPN/VERB/ADJ` tokens is in [0.45, 0.65]. (Outside this range
   suggests a tagger configuration regression.)
4. **Determinism** — building twice in a row produces byte-identical
   interlinear output for any single work that's wholly in LDT. (Stanza
   sentences should also be deterministic given the same input and pinned
   model version; if they aren't, fail and pin harder.)
5. **Topical-pack rebuild** doesn't regress the existing `ivf_recall@30`
   gate (≥ 0.95).

## 10. Open questions to resolve during implementation

1. **LDT version pin.** `treebank_data` has had recent commits — pick a
   tagged release. v2.1 is the last formal versioned drop; verify it has the
   Latin data we expect, or pin to a recent `master` SHA.
2. **CTS URN → `book_id` mapping table.** Perseus's URN scheme
   (`urn:cts:latinLit:phi0631.phi001.perseus-lat2:1.1`) needs an authoritative
   mapping to our `book_id` strings. Build it from `data-sources/perseus_catalog`
   if possible; hand-curate a small JSON otherwise.
3. **Sentence segmentation for Stanza.** Use Perseus's existing line
   boundaries as sentence boundaries? Or rebuild sentence-splitting via
   Stanza's tokenizer? The Sanskrit pipeline uses per-line sentences; copy
   that unless we see degraded POS quality on long Latin periods.
4. **What to do for tokens neither LDT nor Stanza covered.** Emit with no
   POS marker (current behaviour), or drop entirely? Probably emit no marker
   so the dictionary gloss still renders for the reader.
5. **Light-lemma stop-list** can probably shrink significantly with real POS,
   but should not be deleted — POS doesn't catch every function word
   (`autem`, `enim`, `quidem`).
6. **Should the dictionary-lemma column be authoritative when it disagrees
   with LDT/Stanza?** Current Sanskrit prefers treebank's lemma. Do the same
   for Latin — LDT > Stanza > dictionary.

## 11. Honest scope summary

| Item | Estimate |
|---|---|
| Pre-rebuild text-integrity baseline audit | ~30 min wall |
| LDT loader + alignment | ~1 day (alignment is the wildcard) |
| Stanza integration | ~½ day |
| Latin pipeline + format rewrite | ~½ day |
| Topical parser updates (Python + Kotlin + Swift) | ~½ day |
| Regenerate Latin interlinear | ~1 hour wall |
| Rebuild extended DB | ~28 min |
| Rebuild Latin topical pack | ~3 min |
| Post-rebuild text-integrity audit + baseline diff | ~30 min wall |
| Spot-check + iteration | ~½ day |
| **Total** | **~2.5 working days + ~2 hours of builds / audits** |

Latin POS coverage after this plan:
- **LDT gold tags:** ~5–8 % of Latin tokens (canonical authors, partial)
- **Stanza tags:** ~95 % of Latin tokens
- **Neither:** small residual (typos, rare characters, fragmentary works)

The entity kind for Latin becomes possible immediately after step 9.

## 12. Rollout

**Ship LDT and Stanza together in one release.** No staged "Stanza only first,
LDT later" — both go in the same rebuild so the canonical authors get gold
tags from day one and we only pay for one extended-DB rebuild + one Latin
topical rebuild.

Order is exactly §8: baseline text-integrity snapshot → land sources → code
→ regenerate Latin interlinear → regenerate extended DB → rebuild Latin
topical pack → **rerun text-integrity audit and diff against baseline** →
spot-check → APK + deploy.

The text-integrity diff is the load-bearing safety net for this rebuild. Any
per-work regression in that audit means we touched something we didn't
intend to and the release is held until the regression is explained or
reversed.

---

## Appendix A — pre-rebuild baselines (executed)

These are the frozen baselines captured before any code change. The
post-rebuild audit (§8 step #34, §9 Gate #0) diffs against them; any
non-Latin regression, or any Latin regression on source text / English
translation integrity, blocks release.

### Text-integrity audit (Gate #0 baseline)

- Command: `python3 -m text_integrity.audit extended --corpus all`
- Wall time: 58 s
- Report: `data-prep/text_integrity/reports/20260530_170209_extended_all.md`
- JSON sidecar: `data-prep/text_integrity/reports/20260530_170209_extended_all.json`
- Headline: **260 passing of 2743 works** (the failing residue is
  policy-gap noise per the audit's README — that's expected. What matters
  is the **identity of the 260 passing works**; the post-rebuild audit
  must show the same 260 passing, with no regression and no additions
  outside the Latin-interlinear scope.)

### Stanza Latin model

- `stanza == 1.11.1` (already in `venv/`)
- `package='proiel'` downloaded via `stanza.download('la', package='proiel')`
- Smoke test on Aeneid 1.1 (`Arma virumque cano, Troiae qui primus ab oris…`)
  produced UPOS + lemma + head + deprel for all 14 tokens. Known caveat:
  punctuation glues to tokens (`cano,` was tagged as a single NOUN).
  The generator must pre-strip punctuation before feeding Stanza.

### LDT v2.1 Latin inventory

`data-sources/treebank_data/v2.1/Latin/texts/` contains **12** `.xml`
files:

| File | Work |
|---|---|
| `phi0448.phi001.perseus-lat1.tb.xml` | Caesar, *Bellum Gallicum* (book 7 area) |
| `phi0474.phi013.perseus-lat1.tb.xml` | Cicero, Orations (partial) |
| `phi0620.phi001.perseus-lat1.tb.xml` | Tibullus, *Elegies* |
| `phi0631.phi001.perseus-lat1.tb.xml` | Sallust, *Catilina / Iugurtha / Historiae* excerpts |
| `phi0690.phi003.perseus-lat1.tb.xml` | Vergil, *Aeneid* (book 6, lines 1–295) |
| `phi0959.phi006.perseus-lat1.tb.xml` | Ovid, *Metamorphoses* |
| `phi0972.phi001.perseus-lat1.xml` | Phaedrus, *Fabulae* |
| `phi0975.phi001.perseus-lat1.tb.xml` | Petronius, *Satyricon* |
| `phi1221.phi007.perseus-lat1.tb.xml` | Propertius |
| `phi1348.abo012.perseus-lat1.tb.xml` | Augustine, *De Civitate Dei* (selections) |
| `phi1351.phi005.perseus-lat1.tb.xml` | Tacitus, *Annales* |
| `tlg0031.tlg027.perseus-lat1.tb.xml` | Vulgate NT (selections) |

LDT XML structure confirmed: `<sentence id document_id subdoc>` carries
the CTS URN + canonical citation; `<word id form lemma postag relation
head/>` per token. `postag` is the Harrington 9-character Perseus scheme
(position 0 = POS, position 7 = proper/common for nouns).

### LDT alignment scope — v1 (verified against extended DB)

Discovered during loader implementation: **`text_lines.line_number` is a
sequential paragraph/sentence counter within the book, not the canonical
citation reference**. For prose works, `subdoc="2.5"` is canonical
"book 2 section 5" but extended-DB `line_number=5` for book 2 is
typically a different paragraph (verified by spot-checking Caesar BG line
5 = section 2.1, Sallust Cat line 2 = section 1.2, etc).

Only **verse works** where `verse number == line_number` mechanically
align in v1. Aligning the prose works requires parsing the inline `[N.M]`
canonical-ref markers embedded in `text_lines.line_text` and building a
per-work `(book, canonical_ref) → line_number` lookup. **That's v2 work.**

**v1 aligning works (the only LDT data we actually use in the first ship):**

| URN id | Work | LDT sentences | Covered lines |
|---|---|---|---|
| `phi0690.phi003` | Vergil, *Aeneid* (book 6, lines 1–295) | 177 | up to ~295 |
| `phi0959.phi006` | Ovid, *Metamorphoses* (book 1 partial) | 317 | up to ~848 |
| **v1 total** | | **494** | **~1100 unique** |

**v1 unalignable (Stanza covers all of these):**

| URN id | Work | LDT sentences (all dropped in v1) | Reason |
|---|---|---|---|
| `phi0448.phi001` | Caesar BG | 71 | text_lines paragraph counter ≠ canonical section |
| `phi0474.phi013` | Cicero orations | 326 | SECT.SUBSECT scheme not mechanical |
| `phi0620.phi001` | Tibullus | 364 | BOOK.LINE but unverified text_lines mapping |
| `phi0631.phi001` | Sallust Cat | 699 | same as Caesar |
| `phi0972.phi001` | Petronius | 1120 | chapter int ≠ text_lines paragraph |
| `phi0975.phi001` | Phaedrus | 583 | BOOK:LINE colon scheme unverified |
| `phi1221.phi007` | Propertius | 116 | empty subdocs (format-broken) |
| `phi1348.abo012` | Augustine | 347 | single whole-work range (format-broken) |
| `phi1351.phi005` | Tacitus | 197 | empty subdocs (format-broken) |
| `tlg0031.tlg027` | Vulgate | 618 | single int ≠ text_lines paragraph |
| **dropped from v1** | | **4441** | |

LDT v2.1's gold-tag yield in v1 is therefore **~494 sentences** (~5–10k
tokens) out of LDT's ~5k sentences (~53k tokens). The remaining 90 % is
recovered in v2 by the canonical-ref alignment work. Stanza covers
everything else in both v1 and v2, so coverage in the user-facing sense
is 100% either way; the LDT layer is only a quality bump for the
canonical authors.

---

*End of plan.*
