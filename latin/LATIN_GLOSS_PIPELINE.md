# Latin interlinear gloss pipeline — how a word gets its meaning

Companion to `WHITAKER_DATA_FIXES.md`, which covers the **loader** (what goes
into the database). This covers the **reader**: how one Latin surface form in a
text is turned into one short English gloss, and the changes made to that path.

Status: implemented and measured. Not released.

**Ranking that governs every change here: a blank gloss is much better than
a wrong one.** Stated 2026-09-01. See section 8 for what it means in practice
and what it measures to.

---

## 1. The path

```
surface form in the text
  -> get_all_dictionary_entries()          latin_dictionary_lookup.py
       1. exact headword match             <- short-circuits everything below
       2. lowercased headword
       2b. case-preserving orthographic normalisation (j/i, v/u)
       3. lemma_map (inflected form -> lemma -> entry)
  -> first candidate carrying a real definition       _cached_lookup_word()
  -> package fallback where that produced nothing
  -> refine_glosses_with_pos()             generate_latin_interlinear.py
       re-pick using the token's OWN part of speech and lemma
  -> extract_gloss()                       shorten to fit under a word
```

Two properties of this path cause most of its defects, and both are worth
holding in mind before changing anything:

**Step 1 short-circuits.** `get_all_dictionary_entries` gates its `lemma_map`
step on `if not entries`. So when a surface form *happens to be some other
word's dictionary headword*, lemma resolution never runs. `bello` is the
headword of the verb *bello* "wage war" and also the ablative of *bellum*
"war"; the verb wins and the treebank's answer is never consulted.

**Only `refine_glosses_with_pos` knows the token.** Everything before it is
keyed on the surface string alone and is `lru_cache`d, so the same string gets
the same answer everywhere in the corpus. The token's part of speech and lemma
exist only in the refine step, which is therefore the only place a
context-dependent correction can be made.

---

## 2. Sense splitting is bracket-aware, and shared

Whitaker separates senses with `;` `,` `/` — and uses the same punctuation
inside bracketed examples:

```
night [prima nocte => early in the night; multa nocte => late at night]
rise (sun/river)
```

Splitting on the first separator regardless of depth produced
`night [prima nocte : early in the night` — an unterminated quotation shown to
the reader as a definition. 7,185 tokens across 387 surfaces.

There were **three** sense-splitters: `extract_gloss` (bracket-unaware),
`_first_sense` in the generator (bracket-aware, correct), and `_trim` in
`lewis_short_gloss.py` (bracket-unaware). The pipeline ran the broken one first
and the correct one afterwards, over text already cut.

Now one implementation — `first_sense()` and `balance_brackets()` in
`latin_dictionary_lookup.py`, over a single depth scanner. `_first_sense` is a
three-line wrapper kept only because its callers need `None` rather than `""`.

`balance_brackets()` also repairs an unmatched **closer**, which Whitaker's
source contains: `(n.) small pot for cooking/preserving);` leaves an orphan `)`
once the part-of-speech marker is stripped.

Verified: `first_sense()` is byte-identical to the old `_first_sense` on all
39,338 Whitaker definitions. Unbalanced glosses 426 -> 0, and none became `???`.

---

## 3. `form of X` is a placeholder, not a definition

When `lemma_map` resolves a lemma but no dictionary entry exists for it, the
lookup synthesises `form of <lemma>`. No real entry begins with that string, so
it is unambiguous to detect.

It has to be treated as **absent** in two places:
- the selection loop, which otherwise accepts it and stops searching
- the gloss output, which otherwise shows it to the reader

The release build shipped 161,151 tokens displaying `form of X`.

---

## 4. Retry against the token's lemma

Fixes the step-1 short-circuit above. In `refine_glosses_with_pos`: when **no
candidate carries the token's lemma**, look the lemma up directly and let the
same selector choose among its entries.

Deliberately **Whitaker-only**. Pulling package entries here is what made `a`
gloss as "departure from a fixed point" instead of "by (agent)"; supplying
package glosses is §5's job, and conflating the two costs high-frequency words.

The guard is `has_lemma`: if any candidate already names the treebank's lemma,
the existing pick stands. Without it the retry fires on `sunt`, whose candidate
*is* correct but carries no Whitaker part-of-speech marker, and replaces "to be,
exist, live" with "take up" (*sumo*) for 13,655 tokens.

---

## 5. The imported dictionary package

`load_gloss_package.py` reads the app's own three-CSV import format
(`DICTIONARY_IMPORT_FORMAT.md`) at build time, so the interlinear can gloss from
it. The file is consumed **unmodified** — the format must stay byte-identical to
what the shipped app accepts.

It exists because Whitaker's data files contain **no `sum`** at all: the Ada
program handles irregular verbs in code. So `est`, `sunt`, `esse`, `sit` and the
rest resolved to a lemma with no entry, and the selector fell through to
whatever else shared the surface — `edo` "eat", `sitio` "be thirsty", `sino`
"allow", `sumo` "take up". `est` shipped as **"eject/emit"** for 55,286 tokens.

### It is NOT in `DEFAULT_GLOSS_SOURCES`, and must not be

Letting it compete on a straight headword match wrecked ~46,000 tokens of common
words, because it carries headwords for the prefixes `se-` and `re-` and for
`huc`:

```
se   15,263 tokens   "him/her/it/ones-self" -> "sine, without, aside"
hoc  13,837          "this"                 -> "to this place, hither"
te   12,991          "you (sing.)"          -> "pronominal suffix"
re    4,100          "thing"                -> "to stand back"
```

None of that is detectable by an automated check — it is fluent English, just
the wrong word. It is consulted only where it can help: to fill a blank, and to
supply a lemma Whitaker genuinely does not define.

### Self-mappings carry no information

The package maps every form it knows to itself (`hoc -> hoc`). Those become
`form of hoc` placeholders. Treating a placeholder that names *the surface
itself* as evidence about which word this is blocked Whitaker's correct entry —
`hoc` lost "this", `te` lost "you (sing.)". Only a placeholder naming a
**different** lemma is evidence.

### The package is also visible on the dictionary screen — kept, deliberately

`dictionary_entries` holds both L&S products, and `DictionaryDao` does not
filter by source, so a tapped word can show:

```
Whitaker               'strength/power; courage/bravery; worth/manliness…'
Lewis-Short            'virtūs  I. gen. plur. virtutium, App. Mag. 73…'   <- the dictionary
Lewis & Short glosses  'manliness, manhood, virtue, worth'                <- this package
```

They are the same dictionary by different routes: `Lewis-Short` (93,640 rows)
is the 1879 text from the Perseus TEI via `load_lewis_short.py`; this package
(50,828 rows) is a one-line summary of it, arriving as the app's own
three-CSV user-dictionary zip via `load_gloss_package.py`, and it exists for
the INTERLINEAR, not for the dictionary screen.

`PerseusRepository` ranks Whitaker 0, Lewis-Short 1, everything else 3, and
`DictionaryActivity` keeps five rows — so the package row appears only on words
with few competing entries, where it takes a slot.

**Decision 2026-09-08: keep it.** Noted here because two consequences are easy
to mistake for defects later: the label reads as a second Lewis & Short entry
when it is a summary of the first, and on a short word such as `rex` the reader
sees Whitaker "king", the real L&S entry, and "ruler of a country" as though
they were three independent authorities.

### Build integrity

Row-count floors (45,000 definitions, 1,400,000 forms) and a `Package check:`
count in the build log, mirroring the existing Whitaker and LDT checks. Missing
file, missing member, missing column, short file, and files nested in a folder
each fail the build loudly — all five verified.

---

## 6. What is deliberately NOT fixed

**The treebank overlay covers ~6.5% of available gold annotations.** Ten of
twelve LDT files contribute zero tokens. This is a documented v1 scope decision
in `latin_treebank_loader.py`, not a defect: for prose works
`text_lines.line_number` is a paragraph counter, not the canonical section
number, and three files have empty or whole-range subdocs.

**The promotion test that file prescribes does not work.** "Subdoc N's first
token equals line N's first token" scores the *Aeneid* at 8% — a work that
demonstrably aligns and supplies most of the gold tags in the build. LDT records
where a sentence *starts*, and in verse sentences usually start mid-line. A
valid test must compare the sentence's whole token multiset against the span of
lines it covers. Until one exists, no resolver should be promoted: a wrong
resolver silently attaches gold annotations to the wrong words, which is worse
than falling back to Stanza.

**Stanza supplies invented lemmas.** `virumque` displays lemma `virusque`,
`profugus` displays `profundo`. The gloss can be right while the lemma shown
beside it is not a word. Untouched.

---

## 7. Reviewing a gloss change

`LOST` counts and suspicious-gloss flags are **not** a regression review. Both
are blind to the commonest failure: a gloss changing from one plausible English
phrase to another that is the wrong word. `genus` -> "knee" is not blank and is
ordinary English, so nothing flags it.

Read the CHANGED bucket, frequency first — the top 150 surfaces cover about half
the changed tokens. Ask whether the new gloss is the same **word**, not whether
it looks like a definition. Tooling and method: `latin/tools/README.md`.

---

## 8. Blank beats wrong

**Ranking, decided 2026-09-01: a missing gloss is much better than a wrong
one.** This is not a tie-breaker, it is an ordering. Where a change trades
blanks against wrong answers, it is judged on the wrong answers alone.

The reason is what the reader can do with each. `???` tells them the tool has
nothing and sends them to the dictionary. `est` glossed "eject/emit" is fluent,
confident and indistinguishable from a real answer, so it is believed.

Two consequences for how work here is measured:

- **A rise in the blank rate is not a regression.** It is a regression only if
  the tokens that went blank previously carried a *correct* gloss.
- **The `GAINED` bucket needs review as much as `CHANGED`.** Every token that
  moves from `???` to a gloss is a new assertion, and it is the only bucket
  where this build can be worse than its predecessor under the ranking.

### Measured: this build vs the released extended DB

Both snapshots cover the same 4,817,905 Latin tokens and the same 282,448
surfaces (`latin/tools/snapshots/release.json` vs `final_variant_fix.json`).

| | release | this build |
|---|---|---|
| blank (`???`) | 405,181 (8.41%) | 172,747 (3.59%) |
| `form of X` placeholder | 161,151 (3.34%) | 2 |
| mechanically flagged | 24,053 (0.50%) | 2,757 (0.06%) |
| **wrong word, hand-read (top 140 changed surfaces)** | **427,713** | — |
| **wrong word newly asserted** | — | **~16,000** |

The ~16,000 is 9,080 tokens of confirmed regression (`suo`, `meo`, `armis`,
`vobis`, `plus`) plus ~7,100 projected from the `GAINED` tail — see below. The
427,713 is a hand-read of the top 140 changed surfaces only (45% of the changed
tokens); the rest is unread, so that number is a floor, not a total.

### The GAINED bucket, audited

238,740 tokens (36,962 surfaces) gained a gloss. Mechanical flags catch 1,237
tokens (0.52%), all proper nouns glossed thinly (`'Roman nomen'`).

- **Top 300 surfaces** (106,455 tokens, 45%) — read in full, essentially all
  correct. It is one family: the `sum` perfect stem, the `i`/`j` and `u`/`v`
  words (`iure`, `iudices`, `Iovis`), the numerals, the `-dam` indefinites.
  These were blank in the release because of the variant gap now fixed.
- **Tail** (36,662 surfaces, 132,285 tokens) — 120 token-weighted samples read
  by hand: 88.3% correct, 6.3% weak (`Picenum` -> "district"), **5.4% the wrong
  word** (`Libys` -> "cake, pancake", `Iuba` -> "mane of a horse",
  `ducentiens` -> "lead, command"). Mostly proper nouns colliding with a common
  noun. Projected: **~7,100 tokens**, sample of 120, so ±3 points.

### Dual glosses are the remaining wrong-assertion surface

`_dual_gloss` prints a second and third reading for a form LDT annotates more
than one way — the `ora` -> "shore, beg" case. Measured against the shipped
build:

```
LDT gate fires (>=2 readings, 2nd >= 15%)   2,108 surfaces   542,507 tokens  11.26%
_dual_gloss returns a value                1,020 surfaces   315,305 tokens   6.54%
that value is what shipped                   799 surfaces   271,300 tokens   5.63%
```

The top 80 of those cover 79% of the shipped dual-gloss tokens. Read by hand:

| | surfaces | tokens |
|---|---|---|
| both readings legitimate (`malum` "bad, apple", `leges` "law, read") | 67 | 177,841 |
| second reading spurious, **leading sense still correct** | 11 | 33,248 |
| **wrong reading leads** | 2 | 2,308 |

The 11: `ne` "…, spin", `ante` "…, rows (pl.) (vines)", `magis` "…, wise",
`tua` "…, see", `castra` "…, castrate", `vis` "…, visit", `circa` "…, race
course, precious stone", `mei` "…, urinate", `pariter` "…, make ready",
`qualis` "…, wicker basket", `sin` "…, allow".

Under the ranking these are a real but bounded cost: the reader still gets the
right word first. The two that lead with the wrong reading are the ones worth
fixing:

- **`armis` (1,604 tokens)** -> "forequarter (of an animal), arms (pl.)". LDT
  attests `arma` 81% and `armus` 19%, and `add()` is called in share order, so
  the 19% reading should not be first. The ordering does not follow the
  evidence — a defect in the selection, not in the dual-gloss policy.
- **`futurum` (704 tokens)** -> "take up, about to be". `sumo` should not lead
  a future participle of `sum`.

### What this means for a future change

- **A second reading must be backed by attested usage, never by morphological
  possibility alone.** That is already the gate: step 2 of `_dual_gloss` runs
  only where LDT is itself split. Loosening it was measured once — it polluted
  10.7% of glosses to help 8.4%. Do not loosen it again.
- **Where nothing can be chosen on evidence, print nothing.** A guess costs
  more than a blank.
- **Report the GAINED bucket in every gloss review**, with a token-weighted
  hand-read sample of its tail. `LOST` and the flags do not see it.

### Reproducing these numbers

```bash
venv/bin/python3 latin/tools/gloss_eval.py compare release final_variant_fix
venv/bin/python3 latin/tools/gloss_eval.py flag    final_variant_fix
```
The GAINED and dual-gloss figures come from the snapshots plus `LdtLexicon` and
`LatinInterlinearGenerator._dual_gloss` read directly; both are in-tree, no
extra script is kept.

---

## 9. The dual-gloss ordering defect, and four rules that did not work

Two shipped glosses led with a reading the evidence ranked *second*: `armis`
"forequarter (of an animal), arms (pl.)" (LDT: `arma` 81%, `armus` 19%) and
`futurum` "take up, about to be". Five candidate rules were measured offline
against all 2,108 surfaces the dual-gloss gate touches, before any code changed.
Four were rejected on their own numbers. Recorded so they are not retried.

**A — resolve a treebank lemma as a headword, not as a surface form.**
`_dual_gloss` falls back to `get_all_dictionary_entries(lemma)`, which runs the
lemma string through `lemma_map`; Whitaker's row `sum -> sumo` is why `futurum`
said "take up". Restricting that fallback to headword matches fixes it —
and breaks `summa`/`summum`/`summis` (2,700 tokens), because Whitaker's
headword is `superus`, not `summus`, so "highest" disappears. **The same
citation-form mismatch that causes the `armis` bug.** Rejected: 2,700 tokens
damaged to fix 1,100.

**C — exclusive assignment.** When a reading finds no entry, give it the
same-POS candidate left over once every other reading's lemma is set aside.
Forced-choice, no lists. It guesses wrong: `remis` "oar, party in law suit"
becomes "party in law suit, oar" — the wrong reading now *leads*; `esto`
becomes "eat, eject"; `beati` becomes "happiness, happy, bless". This is the
guess `select_entry_for_pos` rule (4) already refuses. Rejected.

**E — let the package rescue fire on surfaces Whitaker does define, whenever
LDT names a lemma Whitaker lacks.** 316 surfaces, 39,827 tokens. It fixes the
copula (`eris`, `ero`, `simus`, `sitis` -> "to be, exist, live") and breaks
every adverb whose lemma is its adjective: `facile` "easily" -> "easy",
`libenter` "willingly" -> "it pleases", `similiter` "similarly" -> "like,
resembling", `fortiter`, `repente`, `leviter`, `plerumque`. Rejected.

**E' — E, but only where the LDT lemma is not the same lexeme as the Whitaker
headword.** 124 surfaces, 22,161 tokens. Keeps the copula fix and the good
`v` -> "fifth", `natus` -> "to be born"; still regresses `lino` -> "son of
Apollo", `quacumque` "wherever" -> "whoever", `quolibet`; and rewords ~14,000
tokens neutrally, all of which would need re-reviewing. Rejected: ~3,400 tokens
gained against ~4,600 lost plus the churn.

### What that leaves unfixed, on purpose

~~**~1,100 tokens of copula forms keep another word's gloss**~~ — **FIXED at
the source instead.** `eris`, `ero`, `simus`, `sitis`, `futurus` -> "take up"
were all downstream of one hole: Whitaker's data files have no `sum` entry,
because his BUILD inserts it (`makedict_main.adb`, "This version inserts ESSE
when D_K = GEN") and we reproduced the files but not the build. The loader now
parses that entry out of his Ada source and generates the whole paradigm, so
the copula resolves through the ordinary Whitaker path with correct
morphology. See `WHITAKER_DATA_FIXES.md`, "ESSE is not in the data files".

The lesson generalises past this entry: four rules above were rejected for
trying to patch a selection that was working correctly on a lexicon with a
hole in it. The hole was the defect.

Scale for context: of the tokens LDT or L&S call forms of *sum*, 151,776 are
already glossed correctly and 2,230 are not.

## 10. Two changes that were made

**Change D — a dual gloss must not override a package rescue.**
`generate_latin_interlinear.py`, `refine_glosses_with_pos`. The rescue fires
only where Whitaker has no entry for the treebank's lemma; `_dual_gloss` is
built entirely from Whitaker entries; so on a rescued token every reading it
can print belongs to some other word. It was overwriting the rescue on **26
surfaces / 4,062 tokens, all of them for the worse**:

```
esto, eras, futura   'take up, eject, eat'            -> 'to be, exist, live'
armis                'forequarter (of an animal), …'  -> 'defensive armor and weapons'
qualis, quale        'what kind, wicker basket'       -> 'of what sort, kind'
complures            'many (pl.), many'               -> 'more than one, several'
oriente              'rise (sun/river), daybreak'     -> 'to rise, appear, originate'
memores              'remembering, remember'          -> 'remembering a thing'
dulcis               'pleasant, sweet drink'          -> 'sweet, pleasant, agreeable'
binas                'two by two, duplicate'          -> 'two at a time'
```

**Change B — order integrity in `_dual_gloss`.** The list it prints is ordered
by annotator agreement, and the reader cannot see when the most-attested
reading dropped out — which is what happens when the two lexica cite a word
differently (LDT `arma` vs Whitaker `armum`). The leftover minority reading
then sits first and reads as the majority one. So: if the top reading
contributes no sense, print no list and let the single-gloss path answer.
19 shipped surfaces, ~7,000 tokens. Sixteen improve (`liber` "children (pl.),
**nibble**" -> "children (pl.)"; `remis` "oar, **party in law suit**" -> "oar";
`quale` -> "what kind/sort/condition (of)"; `licuit` "**be in molten**, it is
permitted" -> "it is permitted, one may"). Two do not: `superis` loses "gods
(pl.) on high" for "above, high", and `Iulia` goes blank — acceptable under §8.

Neither change touches a dual gloss whose top reading resolves, so the
deliberate ones are unaffected: `ora` "shore, beg", `malum` "bad, apple",
`leges` "law, read", `solis` "sun, only, bottom" all verified unchanged.

---

## 11. Root cause of the ~1,600 regressed tokens (2026-09-02)

The build that fixed 155,000 tokens also moved ~1,600 the wrong way. Traced to
completion, because "net positive" is not the same as "understood".

### Attribution

Each surface was re-run with one change disabled at a time, against the shipped
DB, using the `(lemma, POS)` the corpus actually carries — read from the
generated XML, not approximated.

| surface | tokens | cause |
|---|---|---|
| `vestrum` | 357 | D — suppressed dual "your (pl.), you (pl.)" |
| `praesens` | 326 | D — suppressed dual "be in charge, present" |
| `patere` | 107 | D — suppressed dual "stand open, suffer" |
| `potentes`/`potentem`, `mortuum`/`mortua`, `coeptis`, `monitis`, `pensi` | ~420 | D |
| `licuit` | 179 | B |
| `superis` | 140 | B |
| `bos` family | 492 | source-scoped cutoff — "ox, bull, cow" -> "ox", thinner |
| `euge` | 24 | source-scoped cutoff — "well done! bravo!" -> "oh" |

**A measurement error of mine is worth recording.** The first estimate of D's
radius (26 surfaces / 4,062 tokens) used `LdtLexicon.lemma_for()` as a stand-in
for the token's lemma. Tokens whose lemma comes from Stanza were therefore
never sampled, and every surface in the table above is one of those. The true
radius is **42 surfaces / 5,942 tokens** — ~4,730 better, ~1,212 worse. Measure
selection rules against the lemmas the corpus carries, not against a lexicon
that covers a quarter of it.

### B's early return also skips step 2

`licuit` and `superis` are one mechanism. B returns as soon as the top LDT
reading yields no sense — which also skips the Whitaker-possibility pass, and
that pass was supplying the correct sense:

```
licuit   LDT: licet 50%, liqueo 50%
         licet  -> nothing (Whitaker's `licet` headword is the CONJUNCTION,
                   "although, granted that", so no VERB candidate matches)
         liqueo -> "be in molten"
         step 2 added "it is permitted"; the early return runs first
```

**B' — carry on instead of returning — was measured and rejected.** It restores
39 surfaces / 21,870 tokens of dual gloss, and they are the junk B exists to
suppress: `armis` "forequarter (of an animal), arms (pl.)" (the defect that
started this), `meis` "my (personal possession), **urinate**", `mea` "...,
**go along**", `liber` "children (pl.), **nibble**", `quale` "what kind,
**wicker basket**", `remis` "oar, **party in law suit**". Only `licuit` and
`superis` gain. 319 tokens of cost against 21,551 of suppressed junk: B stays
as written.

### The three real causes

None of the residue is a defect in the new rules. All three are pre-existing
data problems that the rules stopped **masking** — a dual gloss that happens to
contain the right sense alongside a wrong one was hiding them, which is exactly
what §8 says not to count as correct.

1. **Wrong lemma upstream.** `licuit` -> `liqueo` (should be *licet*), `patere`
   -> `patior` (should be *pateo*), `superis` -> `supera`. The gloss is derived
   faithfully from the wrong word. Not fixable in the gloss layer.
2. **Bad package entries.** `vos` -> "thou, you, you (singular)" (wrong number
   for a plural pronoun), `praesens` -> "to be before a thing" (that is
   *praesum*), `monitis` -> "punish, chastise", `pensi` -> "to hang down".
   These win because Whitaker's only row for the lemma is a `form of X`
   placeholder, so `_whitaker_defines` is correctly False and the rescue fires.
   The package's systematic infinitive phrasing ("to bear", "to die", "to be
   able") is also wrong for the many tokens that are adjectives, participles or
   nouns — a candidate for a future measured change, not patched here.
3. **Whitaker's first sense is terser than the package's.** `bos` "ox" vs
   "ox, bull, cow"; `euge` "oh" vs "well done! good! bravo!". A direct
   consequence of preferring Whitaker, which is the decision of record.

---

## 12. Proper nouns glossed as the common noun — measured, deliberately not fixed

Found by a 150-surface token-weighted sample of the shipped build (2026-09-02).
Whitaker capitalises proper-name headwords, so a capitalised `PROPN` token that
resolves to a **lowercase** headword is the common noun standing in for the
name:

```
Lentulus  164  'somewhat slow'            Balbus    67  'stammering'
Galba     150  'small worm, ash borer'    Albinus   64  'plasterer'
Catulus    91  'young dog, puppy, whelp'  Scaurus   73  'with swollen ankles'
Pansa      91  'splay-footed'             Torquatus 71  'wearing a collar'
```

**Size: 2,165 surfaces / 12,685 tokens**, 6.8% of capitalised PROPN tokens
carrying a gloss, 0.27% of the corpus.

The class is **not uniformly wrong**, which is why it stays. The same condition
catches `Aurora` "dawn, daybreak", `Musa` "muse", `Fortunae` "chance, luck,
fate", `Concordiae` "harmony", `F` -> "son" and `R` -> "Roman", all correct and
useful. Roughly 70% wrong / 30% right by a hand-read of the top 45.

Two candidate separators were tested and neither works:

- **Part of speech of the supplying entry.** The adjective bucket (549
  surfaces / 4,749 tokens) is ~87% wrong, but contains `R` -> "Roman" and the
  `Magnus` family; the noun bucket (1,431 / 7,294) mixes `Galba`, `Catulus`,
  `Latro`, `Nepos` (wrong) with `Aurora`, `Musa`, `Fortuna` (right).
- **Whether the word is ever used lowercase in the corpus.** This answers "does
  this word have a common-noun life", not "is this token a name". `Latro` (28
  lowercase uses), `Nepos` (56), `Curio`, `Catulus` all pass it and are still
  people in these texts. Once the tagger says `PROPN`, the word's common-noun
  career elsewhere is the wrong question.

**Decision 2026-09-02: leave it alone.** Every affected token is a capitalised
proper noun a reader recognises as a name unaided, and no rule tested separates
the misleading glosses from the useful ones without a word list. Do not
"fix" this by suppressing the class: it would take `Aurora` "dawn" and `Musa`
"muse" with it.

---

## 13. Enclitic surfaces: the stripper is short-circuited (measured, not yet fixed)

Sized 2026-09-03 from the shipped build.

A *true* enclitic surface is one ending `-que`/`-ve` whose base is itself a
known word. (`-ne` is excluded: too many ordinary words end in it — `bene`,
`sine`, `omne`, `nomine`.)

```
true enclitic surfaces                     5,925 surfaces   85,629 tokens
  with a fabricated lemma                  4,151 surfaces   24,736 tokens
    gloss marks the enclitic ("+ and")       429 surfaces    3,158 tokens
    gloss does NOT                         3,722 surfaces   21,578 tokens
```

For scale, the whole fabricated-lemma class — a lemma that is a headword in no
Latin source and a lemma in no lexicon — is 82,399 surfaces / 248,963 tokens
(5.27%). Most of it is display noise: `moenia`, `pocula`, `Veneris` all carry a
correct gloss and only an invented lemma in the morph line.

### Cause

The L&S glosses package contributes `lemma_map` rows **keyed on the full
enclitic surface**. Those satisfy lemma resolution, so `_strip_enclitic` never
runs:

```
idque      no lemma_map row                      -> stripper runs -> "he/she/it/they + and"  OK
eaque      L&S glosses: eaque -> ea              -> stripper skipped -> "he, she, it"
semperque  L&S glosses: semperque -> semper      -> stripper skipped -> "always"
magisque   L&S glosses: magisque -> magus/maga/magis -> picks magus -> "magian, learned
                                                        Persian magician"
```

Same shape as the step-1 short-circuit in §1, one layer down. Two consequences:
the "+ and" is lost, and where the package offers several lemmas for the
surface the selector can take the wrong one. `idque` shows the machinery works
when it is allowed to run.

### Blast radius of the candidate fix

Fix: when a surface ends `-que`/`-ve` and its base is a known word, the
enclitic analysis takes precedence over a `lemma_map` row keyed on the full
surface. Simulated against the shipped DB, resolving the base through the same
lookup and POS refine:

```
would touch                    3,695 surfaces   19,256 tokens
  base resolves to nothing       130 surfaces      182 tokens  <- ALREADY blank today,
                                                                  so nothing is lost
  only "+ and" added           1,277 surfaces    4,604 tokens
  gloss text changes           2,288 surfaces   14,470 tokens
```

Hand-read of the top 40 changed (~4,100 tokens, 28% of that bucket):

- **fixes** the wrong-word cases: `magisque` "magian…" -> "to greater extent,
  wise + and"; `eosque` "dawn" -> "he/she/it/they + and"; `suaque` "swine" ->
  "his men (pl.), his friends + and"; `multoque` "to punish with something" ->
  "much, many things (pl.), punish + and"
- **regresses** ~12% of sampled tokens: `multaque` "much, great, many" ->
  "fine + and" (175), `omniaque` (121), `rursusque` (115), `populoque`
  "people, nation, State" -> "ravage, devastate, lay waste" (86)

Those four are the existing homograph problem resurfacing on the base word
(*multa* "fine" vs "much", *populo* the verb vs *populus* the noun), not
something the fix introduces — the base inherits whatever the pipeline already
does with that surface.

**Status: measured, not implemented.** Verifying it needs an interlinear pass,
a Latin module build and an assembly (~80 min), then `gloss_eval compare` and
the text-integrity audit.

### Implemented 2026-09-03, and what it measured to

The split now runs as step **2c**, after the direct-headword steps and before
`lemma_map`, for `-que` and `-ve` only. `-ne` stays at the last-resort step.

Guard against fused words, in `_has_fused_enclitic_lemma`: in `quisque`
("each") and `uterque` ("both") the -que is part of the word. The test is the
lexicon's own lemma, not a word list — a fused form's lemma itself ends in -que
(`quaeque -> quisque`), a real enclitic's never does (`semperque -> semper`,
`magnoque -> magnus`, `iamque -> jam`). Verified by running the pre-change file
side by side with the new one: `quaeque`, `utrumque`, `utraque`, `cuiusque`,
`quique`, `utrisque`, `neque`, `atque`, `quoque`, `itaque`, `denique`, `usque`,
`utique`, `bene`, `sine`, `omne`, `nomine` are all byte-identical.

Build result vs `esse_usable_fix`:

```
gained "+ and" / "+ or"          12,254 surfaces   49,086 tokens
  base gloss identical            9,113 surfaces   36,579 tokens   pure gain
  base gloss also changed         3,141 surfaces   12,507 tokens   ~8.5% worse by 90-sample
changed for other reasons           184 surfaces      544 tokens   mostly truncation shift
LOST                                                     2 tokens
newly flagged suspicious              4 surfaces       10 tokens
text integrity                2,743 works, 260 passing, 0 regressed, 0 hashes changed
```

Wrong-word cases fixed: `eosque` "dawn" -> "he/she/it/they", `suaque` "swine"
-> "his men", `satisque` "Hebrew measure of corn" -> "enough", `letumque`
"mountain in Liguria" -> "death", `ensesque` "thing" -> "sword", `Manisque`
"hand, handhold" -> "spirits of the dead", `magisque` "wise/learned man" ->
"to greater extent".

### Known residue, recorded not patched

- **`quisque` forms with no fused lemma recorded**: `quamque`, `quidque`,
  `quantumque`, `quidve` (~450 tokens) still split. Fixing them needs a word
  list, so they stay.
- **`-ve` false splits**, ~139 tokens of 1,066: `prave` "wrongly" -> "funeral
  pile", `intempestive` -> "unseasonable stormy", `Ioue` (Jupiter) -> "joyful
  exclamation", `curve`, `Remove`, `love`. Kept because the same branch splits
  ~900 tokens correctly (`quidve`, `tresve`, `minusve`, `postve`).
- **~8.5% of the changed bucket lands worse** for the pre-existing homograph
  reason: `patriaeque` -> "of or belonging", `subitoque` -> "to come or go",
  `soloque` -> "solace, console", `portumque` -> "city gate". The base word
  inherits whatever the pipeline already does with it.

---

## 14. The treebank overlay: a valid alignment test, and what it found

§6 said the promotion test in `latin_treebank_loader.py` is invalid and that no
resolver should be promoted until a real one exists. Written and run 2026-09-03.

### The test

Compare each subdoc GROUP's whole token multiset against the span of lines it
covers — that is what the loader actually does with the annotation. Two things
had to be fixed before it validated:

- **LDT splits enclitics.** The treebank has `classi` + `-que`; the DB has
  `classique`. Tokens beginning "-" are rejoined.
- **A subdoc names a chunk, not a line.** Seven Aeneid sentences share subdoc
  `6.1` and run to about line 13. Sentences are grouped by subdoc and the
  window sized to the group.

Chance level comes from the same measurement with the window shifted. The test
is only trustworthy because it scores the two known-good works correctly:

```
Ovid Metamorphoses   0.90  vs 0.04 chance      (enabled today)
Vergil Aeneid        0.99  vs 0.13 chance      (enabled today; the OLD test scored it 0.08)
```

### Result: the subdoc route is a dead end, and it is now verified

```
Caesar     0.41 vs 0.00      real but partial
Cicero     0.43 vs 0.33      weak
Tibullus   0.26 vs 0.28      none
Sallust    0.24 vs 0.26      none
Petronius  0.24 vs 0.27      none
Phaedrus   0.18 vs 0.21      none
```

Caesar rises to **0.82 vs 0.27** with the canonical-ref index the §6 note
describes — its `text_lines` carry `[1.1]`-style prefixes on 2,150 of 2,464
lines. It is the ONLY work that does: every other work has zero.

So `_unalignable` was the right call for these works, and that is now measured
rather than assumed.

### But the subdoc is the wrong thing to align on

Ignore the citation scheme and find the sentence's text in the work itself.
Candidates come from a 5-gram index; a match counts only when the WHOLE
sentence is recovered in order (>=90% of tokens, small gaps allowed) and no
rival position 10+ tokens away scores as well.

```
work                sentences  aligned   gold words
Vergil Aeneid (control)  145     94.5%      2,000
Caesar                    63    100.0%      1,292
Cicero                   277     96.0%      5,234
Tibullus                 285     77.5%      3,085
Sallust                  612     75.3%      7,640
Petronius                736     87.9%      8,376
Phaedrus                 370     84.1%      3,768
Augustine                325     92.0%      6,616
                                          -------
                                           38,011      ambiguous matches: 0
```

**38,011 gold words against the 5,143 in use today — 7.4x**, with no ambiguous
match anywhere in the set.

Two works stay out, for reasons that are not fixable here:

- **Tacitus** (`phi1351.phi005`): 1 sentence of 180 locatable. The DB text is a
  different edition; its 715 nested book ids are a separate structure problem.
- **Vulgate** (`tlg0031.tlg027`): the DB holds no Latin text for this id at all.

### Status

Measured, NOT implemented. Implementing means giving the loader a content
matcher — build a 5-gram index per work at generation time, locate each
sentence, attach the gold lemma and POS to the tokens it covers — and it
replaces the resolver table rather than extending it. Worth roughly 38,000
tokens of hand-annotated lemma and POS in place of Stanza's guesses, which is
about 0.8% of Latin corpus tokens.

### Implemented 2026-09-04

`LdtLoader` now takes a `db_path` and locates each sentence by CONTENT before
falling back to the subdoc resolvers. The fallback is kept deliberately: the
Aeneid and Ovid resolve mechanically, and sentences shorter than 7 tokens are
below the matcher's evidence threshold, so nothing that aligns today is lost.

A matched span also yields the EXACT line range, replacing the
next-sentence-start guess the subdoc route has to make.

```
gold words loaded          8,041  ->  49,945      (+41,904)
books with treebank data       2  ->      11
tokens carrying gold data  ~5,100 ->  40,868      0.86% of analysed tokens
works with gold data           2  ->       9
loader time                            0.7 s
```

Verified before building: across all 2,702 kept sentences the words really are
inside the lines they were mapped to — mean coverage 0.95, and 0.94-0.99 on
every content-matched work. Cicero's opening now reads `abutere` -> lemma
*abutor*, `nostra` -> *noster*, with dependency roles.

Build result: interlinear 228 works / 0 tracebacks / 47.8 min; zip OK; text
integrity 2,743 works, 260 passing, **0 regressed, 0 text hashes changed**;
glosses essentially unmoved (261 tokens changed, 5 LOST) because the overlay
carries lemma/POS/dependency, not gloss text.

Still out, and why:

- **Propertius** `phi1221.phi007` — no text for this work in the DB at all.
- **Tacitus** `phi1351.phi005` — 1 sentence of 180 locatable; the DB holds a
  different edition, and its 715 nested book ids are a separate problem.
- **Vulgate** `tlg0031.tlg027` — no Latin text under this id.

Known weakness carried over: sentences that still come through the subdoc
fallback map to a loose range whose lines contain about half the sentence's
words (Aeneid 0.47, Ovid 0.74 mean coverage, against 0.97 for content-matched).
`lookup_token` matches on surface form so the damage is bounded, but a repeated
surface can take a wrong dependency head. Pre-existing, not introduced here.

---

## 15. Release review, and the three fixes of 2026-09-08

Nothing has shipped since May. Every "0 regressions" check before this point
compared against a build from days earlier, none of which shipped. The
reference that matters is `perseus_texts_extended.db.zip.release` in the repo
root, whose glosses are captured as the `release` snapshot.

**Text is unchanged since the release, and since May.** Against the May 30,
Aug 19, Aug 20 and Aug 21 reports alike: 2,743 works, 260 passing, 0 regressed,
0 works whose DB text hash or line count changed.

**Glosses accumulated a large diff.** release -> treebank_content:

```
unchanged   3,107,542      changed  1,465,182   (30% of Latin tokens)
gained        239,012      LOST         6,169
blank rate     8.41%  ->  3.58%
```

Reviewed by reading the top 150 changed surfaces (671,083 tokens, 46% of the
changed set) plus a 110-surface token-weighted sample of the tail:

```
              top 150     tail sample
fixes          64.8%       85.5% (fix or neutral)
mixed          18.7%       12.3%
neutral        15.2%          --
regressions     1.3%        2.2%
```

### Where the regressions came from

**Not from the work in this document.** Every regression against the release —
`suo`, `plus`, `vobis`, `meo`, `tuo`, `sinu`, `tutum`, `adversariis`,
`remissis` — was already present in the build that preceded §8, introduced by
the variant fix in `WHITAKER_DATA_FIXES.md` §7. Only `populoque` (86 tokens)
came from the enclitic change. All 2,534 tokens that lost a real gloss were
likewise already blank.

The variant fix's own note claims the tokens it stopped resolving "are all
indeclinables that remain direct headwords with the correct gloss." **That is
false** and should not be relied on: `suo`, `meo`, `tuo` are not indeclinables
and did not keep a correct gloss.

### Fix 1 — DET must accept adjective entries

`UPOS_TO_WHITAKER_MARKER` mapped `DET` to `(pron.)` alone. Latin has no
determiner class: the treebank tags possessives and demonstratives `DET`, and
Whitaker files them as `(adj.)`. Nothing matched, so the lookup fell through to
whatever else owned the surface:

```
suo  lemma suus, tagged DET  ->  'sew together/up, stitch'
meo  lemma meus, tagged DET  ->  'go along, pass, travel'
tuo  lemma tuus, tagged DET  ->  'see, look at'
```

`DET` now maps to `("(pron.)", "(adj.)")`, tried in order, so a genuine pronoun
entry still wins where one exists and every other POS behaves exactly as
before. Verified by running the pre-change file beside the new one: `hic`,
`se`, `qui`, `est`, `ora`, `bellum`, `magna` all byte-identical.

### Fix 2 — quotation marks glued to a word

`text_lines` keeps the punctuation attached, so the surface reaching the lookup
is `“non`, `‘o`, `M’`, `est”`. None matched; all came out blank. 7,277 blank
tokens carry a quote mark and 3,415 resolve once it is stripped.

Stripped from the ENDS only, at the single entry point every lookup passes
through. A token that is ONLY punctuation (`”` alone, 2,270 tokens) strips to
empty and correctly stays blank — it is not a word.

### Fix 3 — the loader had no ADV branch

`parse_inflects` read V, VPAR, N, ADJ and PRON. **Adverbs were never parsed and
never generated.** Whitaker stores an adverb's three degrees as three STEMS and
emits them with zero-length endings:

```
bene       melius       optime           ADV X
generose   generosius   generosissime    ADV X
stulte                                   ADV POS      <- one stem only
```

387 of 2,204 ADV entries carry a comparative or superlative stem; all were
dropped. Now generated exactly as the patterns specify, and `stulte` still
yields one form — nothing is invented.

### Every other POS was checked

| POS | entries | patterns | verdict |
|---|---|---|---|
| `NUM` | 127 | 127 | real gap, worth **15 tokens** — most numerals are indeclinable or covered by an ADJ entry. Not implemented. |
| `VPAR` | 0 | 346 | handled inside the verb branch |
| `INTERJ`, `CONJ`, `PREP` | 106 / 102 / 93 | 1 / 1 / 3 | zero-ending patterns; indeclinable, headwords match directly |
| `PACK` | 73 | 0 | nothing to generate |
| `SUPINE` | 0 | 2 | no entries; supines come off verb stems |

### What was deliberately NOT fixed

**The ~2,200 remaining blank losses cannot be recovered correctly.** They were
reachable in the release only because bare word-STEMS were headwords then
(`Mercuri` is the stem of `Mercurius`), or because the pre-variant-fix
morphology applied a wrong variant's ending to a stem and happened to land on a
real Latin word — `stultius` is exactly that: `stultus` is `ADJ 1 1 POS` and
`stulte` is `ADV POS`, so **Whitaker's data contains no comparative for it.**

Restoring stem matching brings back `Mercuri`, `praemi` and `Kalend` — and also
`IX` -> "ringtail" (it is the numeral 9), `us` -> "use", `ant` -> "square
pilasters", `Ide` -> "idea" (Mount Ida). At the safest setting tested (stem >= 5
characters, only where one word owns that stem) it recovers **366 tokens, about
a fifth of them wrong**, and reopens the defect that made `tibi` mean "flute,
pipe" (`WHITAKER_DATA_FIXES.md` §3). Under §8's ranking that is a net loss.

Decision 2026-09-08: leave them blank. Do not "fix" this by restoring bare-stem
lookup.

---

## 16. The L&S package re-tested, 2026-09-08 — arrangement unchanged

§5's decision (package behind Whitaker, never competing) was made against a
Whitaker that had no `sum` entry, no adverb forms, a broken `DET` marker and
quote-glued surfaces. All four are fixed, so the decision was re-tested rather
than assumed.

### Where the package sits today, measured

Token-weighted sample of 350 surfaces (1.06 M tokens):

```
gloss comes from a Whitaker entry      87.7%
gloss comes from the L&S package        1.3%
gloss arrived via the lemma route      11.0%
```

The package is not a gap-filler. It has an entry for nearly every surface —
it differs from the shipped gloss on 95.6% of tokens, and there are **zero**
surfaces where the build is blank and the package has something. It is a
complete alternative dictionary sitting behind the current one.

It also contributes **1,543,203 `lemma_map` rows against Whitaker's
1,497,813**, so it already shapes much of that 87.7% indirectly by deciding
which lemma a surface resolves to.

### The three recorded reasons still hold

1. **Prefix and letter collisions.** Reproduced exactly: `a` -> "first letter of
   Latin alphabet" (18,044 tokens), `se` -> "sine, without, aside" (15,263),
   `hoc` -> "to this place, hither" (13,837), `te` -> "pronominal suffix"
   (12,991), `ac` -> "sharp, quick" (12,768).
2. **Self-mappings.** Still leaking: `Romani` -> "form of romanus".
3. **Apparatus.** This one has IMPROVED. No `imperf. audibat, Ov` appeared in a
   300-surface tail sample; the shipped package is much cleaner than the
   extractor behind the 30-40% figure in `LATIN_GLOSS_PLAN.md` §5.2.

### The measurement protocol failed, and that is the finding

The test was built around `gloss_eval`'s detectors, sampling the tail rather
than the head, reporting regressions before wins. It reported **0.1% of package
glosses flagged and ZERO flagged regressions** — a clean pass.

Hand-reading the same fourteen changes it passed:

```
suo      'his, his men, his property'  -> 'to stitch, join'                    2,602
L        'Lucius (Roman praenomen)'    -> 'eleventh letter of Latin alphabet'  2,584
multa    'much, fine, punish'          -> 'penalty involving loss of property' 2,747
Romani   'Roman'                       -> 'form of romanus'                    2,097
ob       'on account of, for the sake' -> 'to, toward, before'                 2,104
sive     'or if'                       -> 'disjunctive conditional particle'   2,022
```

Six of fourteen wrong; the detectors passed all fourteen. `latin/tools/README.md`
already says why — the commonest failure is a gloss changing to another
plausible English phrase that is the wrong word, and no detector sees it.

**No automated gate can decide this question.** Any future attempt must
hand-read a token-weighted sample of every affected surface.

### Where the package IS better

Function words where Whitaker is terse:

```
itaque   'thus, so'                 ->  'and thus, therefore, consequently'
ergo     'therefore'                ->  'consequently, therefore, thus'
item     'likewise'                 ->  'also, likewise, additionally'
senatus  'senate'                   ->  'senate, council of elders'
aliquid  'anyone/anybody/anything'  ->  'some one, something'
ut       'to (+ subjunctive)'       ->  'how, in what manner'
enim     'namely (postpos.)'        ->  'indeed, truly, in fact'
```

### Decision 2026-09-08: arrangement unchanged

Not because the package is poor — it is better than when §5 was written — but
because roughly 40% of the changes in the sample are wrong and nothing
mechanical separates them. If it is revisited, the only shape worth testing is
narrow: prefer the package **only** where Whitaker's entry is a bare marker or
a single word, and only for surfaces of 4+ letters that are not abbreviations —
which excludes `L`, `ob` and `suo` by construction. That is new work with its
own hand-verification, not a configuration change.
