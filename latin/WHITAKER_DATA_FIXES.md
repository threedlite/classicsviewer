# Whitaker's Words — data-format fixes

`latin/build_modules/load_whitakers_latin.py`

Whitaker's Words ships as flat data files (`DICTLINE.GEN`, `INFLECTS.LAT`,
`UNIQUES.LAT`) plus an Ada program that interprets them. We read the data files
and reimplement the interpretation. Everything below is a case where our reading
of the format was wrong — the fixes are about **how the source is parsed**, not
about Latin.

Status: implemented and measured in the Latin module build. Not released.

---

## 1. `zzz` is a null marker, not a word

`DICTLINE.GEN` gives four principal-part stem columns per entry and writes `zzz`
where a principal part **does not exist**:

```
abarc     abarc     zzz    zzz    V  2 1 TRANS     <- no perfect/supine
abbatiz   abbatiz   zzz    zzz    V  1 1 INTRANS
zzz       Ad                      N  1 1 M         <- no nominative stem
zzz       mult                    N  1 1 F
zzz       deterius  deterrime     ADV X
```

**2,170 of 39,338 entries** carry it. We treated it as a stem, with two results:

- Forms were generated as `zzz` + ending, minting nonsense word forms.
- In **23 entries** `zzz` occupies column 1, and the loader took
  `lemma = stems[0]` — so 23 unrelated defective words collapsed onto a single
  junk lemma `zzz`, which accumulated **1,349 `lemma_map` rows and 23 dictionary
  entries**.

The 23 are exactly the words whose first principal part is suppletive: *Adam*,
*multa* ("a fine"), *deterius* (comparative with no positive), and similar.

**Visible symptom.** The interlinear resolved that pile arbitrarily.
`multum` in *Aeneid* 1.3 was glossed **"much, fine, Adam"**. 1,575 segments
carried an `", Adam"` tail.

**Fix.** `_parse_stems()` replaces `zzz` with `None` **in place** — positions
must be preserved, because inflection patterns index stems by `stem_pos` and
compacting the list would silently shift every later stem onto the wrong column.
The lemma becomes the first *real* stem, so *Adam* keys on `Ad` and *multa* on
`mult` rather than both landing on `zzz`.

A pre-existing pronoun-block bug was fixed at the same time: it already filtered
`zzz` but did so by compacting, which is exactly the shifting error described
above.

---

## 2. `X` is a zero ending, not a letter

`INFLECTS.LAT` writes `X` in the ending column to mean *no suffix — the form is
the bare stem*. **32 of 1,645 patterns** use it. The loader concatenated it:

```
vis + X  -> visX          os + X -> osX          abac + X -> abacX
```

**26,048 such rows** were in `lemma_map`. Harmless while lemmas were stems —
nothing looked them up — but they surfaced as lemmas once §3 landed, and they
polluted the Lewis & Short bridge, which matches `lemma_map.word_form` against
L&S headwords.

**Fix.** Endings equal to `X` are blanked once, after `parse_inflects()`.

Deliberately **not** done by stripping a trailing `X` from finished forms:
**33,701 real Latin corpus tokens end in capital X** (Roman numerals).

---

## 3. Entries are keyed on stems, not dictionary forms

This is the structural one. `dictionary_entries.headword` held Whitaker stems —
`mult`, `ed`, `qu`, `sit`, `sum`. Three consequences, measured against the
corpus:

| | |
|---|---|
| Latin tokens whose surface equals some stem | 1,449,084 (30.1%) |
| — a direct hit **short-circuits** lemma resolution entirely | |
| tokens that resolved to a genuinely unrelated word | 142,199 (3.0%) |

```
est   -> stem `ed` (edo)     -> "eject/emit"
tibi  -> stem of tibia       -> "flute, pipe"
sit   -> stem of situs       -> "situation, position, site"
mult  -> multus/multa/multo  -> "much, fine, punish"
```

**Fix.** Each entry is keyed on its **citation form** — 1st person singular
present active indicative for verbs, nominative singular for nominals — derived
from the paradigm the loader already generates. Recoverable for **29,371 of
29,562 stems (99.4%)**; the 191 exceptions are indeclinables and abbreviations
(`A`, `Abba`, `Adonai`, `Baal`) that already are their own citation form.

Computed **per entry, not per stem**: one stem serves several entries with
different parts of speech, and a per-stem map picks the wrong one — `mult` maps
to `multo` rather than `multus`, `tu` to `tuo`.

Renaming *sumo*'s entry from `sum` to `sumo` frees the string `sum`, which is
what makes the *est* → "to be" fix possible at all (§5).

**Effect on collisions:**

| surface | headword rows before | after |
|---|---|---|
| `tibi` | 1 | 0 |
| `sit` | 2 | 0 |
| `vi` | 2 | 0 |
| `sum` | 3 | 0 |

---

## 4. Missing sources were warnings, not failures

`DICTLINE.GEN`, `INFLECTS.LAT` and `UNIQUES.LAT` absences printed a warning and
returned, producing a database with no Latin dictionary at all and a clean exit
code. `create_latin_database.py` checked only that the *directory* existed, so
an incomplete checkout reached the loader.

`UNIQUES.LAT` and `INFLECTS.LAT` were additionally wrapped in
`if path.exists():` at the call site — a missing required input became a no-op
twice over.

**Fix.** All three raise. `parse_inflects()` is called unconditionally. A
post-load count check in `create_latin_database.py` fails the build below
25,000 dictionary entries or 1,000,000 `lemma_map` rows — floors set well under
the measured 39,414 / 1,899,457 so they catch "nothing loaded" rather than
normal drift.

---

## 5. What Whitaker cannot supply: irregular verbs

Whitaker handles `sum`, `possum`, `eo`, `fero`, `volo` in **program code**, not
in its data files. `DICTLINE.GEN` and `UNIQUES.LAT` contain no paradigm for
`sum`, so there was no route from `est` to `sum` at all — `est` fell through to
the stem `ed` (*edo*).

That is not a parsing bug and cannot be fixed here. It is supplied from the
Perseus Latin Dependency Treebank; see `latin/build_modules/load_ldt_lemmas.py`
and `LATIN_GLOSS_PLAN.md` §12.3.3.

---

## 6. Measured result

Current built state (`latin/latin_texts_extended.db`):

```
lemma_map total          1,899,457     (was 1,955,715)
  lemma = 'zzz'                  0     (was 1,349)
  word_form 'zzz…'               0     (was ~67,900)
  word_form '…X'                 0     (was 26,048)
Whitaker dictionary entries 39,414     (unchanged — re-keyed, none lost)
L&S bridge coverage          76.5%     (was 76.0%)
```

Roughly 95,000 junk `lemma_map` rows removed, no dictionary entries lost.

Gloss effect across the 400 commonest Latin surfaces (1,777,193 tokens),
combined with §5's treebank rows:

```
est    28,971  "eject/emit"               -> "As a verb substantive, to be"
esse   18,024  "eject/emit"               -> "As a verb substantive, to be"
sunt    8,814  ???                        -> "As a verb substantive, to be"
sit     6,395  "situation, position"      -> "As a verb substantive, to be"
iam    10,556  "out of, from"             -> "now, already, by/even now"
tibi    7,563  "flute, pipe"              -> "you (sing.)"
se     14,884  "form of s"                -> "him/her/it/ones-self"
res     4,909  "res"                      -> "thing"
rem     3,982  "oar"                      -> "thing"
```

32,356 tokens gained a gloss; 310,641 changed; the only loss is one malformed
token (`sit,`) whose previous gloss was wrong anyway.

---

## 7. Inflection patterns are keyed on (declension, VARIANT), not declension

`INFLECTS.LAT` keys every pattern on a declension **and a variant**. Declension
2 has ten variants, and they do not share a nominative ending:

```
N 2 1 NOM S      us      dominus
N 2 2 NOM S N    um      bellum
N 2 3 NOM S   <none>     vir, puer     <- the nominative IS the stem
N 2 4 NOM S C    us
N 2 4 NOM S N    um
```

The noun, adjective and verb blocks filtered on declension alone. Every entry
was therefore given every variant's endings.

`DICTLINE.GEN` has three entries with the **identical stem** `vir vir`,
separated only by variant:

```
vir vir  N 2 1 N  venom (sg.)
vir vir  N 2 2 N  virus
vir vir  N 2 3 M  man; husband; hero
```

All three produced the same form soup, so the citation-form picker (§3) had to
guess which nominative belonged to which entry. It guessed backwards: "man" was
filed under the headword `virus` and "venom" under `virum`, so *viri*, *viros*
and *virorum* glossed as **"venom"**. The same gap filed *bellum* "war" under
`bellus` (which is the adjective "pretty") and *genus* under a headword that
collided with *genu* "knee", so `genus`, `genere`, `genera` and `generis` all
glossed as **"knee"**.

### The larger half of the defect

Wrong headwords were the visible symptom. The invisible half was ~375,000
**forms that do not exist** inserted into `lemma_map`, generated by applying one
variant's endings to another variant's stem. Those shadowed correct entries,
because a `lemma_map` hit routes the lookup to whatever lemma it names:

```
aut  18,556 tokens  ->  autus  "increase, enlargement"   (it is the conjunction "or")
sit   6,395         ->  sitio  "be thirsty"
vel   5,899         ->  velum  "sail"
an    4,604         ->  anus   "old woman"
at    2,707         ->  aio    "say"
dum   3,378         ->  dumus  "bramble"
unde  1,589         ->  unda   "wave"
```

`sit` glossing as "be thirsty" was blamed on the gloss selector for some time.
It was never the selector. It was this.

### The fix

Filter patterns by variant in the N, ADJ and V blocks. Variant `0` means
"applies to every variant" and is always kept — the same idiom the **PRON block
in this file has always used**. The other blocks simply never adopted it.

Checked before changing: every `(pos, declension, variant)` combination
appearing in `DICTLINE.GEN` has a matching pattern in `INFLECTS.LAT`, so no
entry loses its morphology. Checked after: `lemma_map` drops from 1,894,580 to
1,494,813 rows, and the 66,469 corpus tokens that stop resolving are all
indeclinables that remain **direct headwords** with the correct gloss — a direct
headword match runs before `lemma_map`, so those rows were pure noise.

### Gender is now a tie-break, not a workaround

§3's citation-form picker was given a gender preference to stop *bellum* being
filed under `bellus`. That was a workaround for this defect: gender correlates
with the `-um` pattern for regular neuters, which is why it appeared to work,
and it failed on irregulars — it is what filed *vir* under `virus`. With variant
filtering each entry generates only its own variant's forms, so the preference
now only separates the genuine case of one variant carrying two genders
(`N 2 4` has both `NOM S C -us` and `NOM S N -um`).

---

## 8. The common shape

All of these are the same mistake: **a field in the source format not read as
the format defines it.** `zzz` means "absent", `X` means "no ending", a stem is
a key not a word, a missing file means stop, and a pattern is keyed on
(declension, variant) not declension. In each case the build succeeded and
shipped something wrong rather than failing.

Several were invisible for as long as they existed because nothing looked at
the affected rows. §1 and §2 became visible only when §3 changed what the lemma
column meant; §7's spurious `lemma_map` rows were invisible because a direct
headword match usually overrode them, and surfaced only where no such match
existed.

§7 is worth a second look for a different reason. The wrong glosses it caused
(`viri` "venom", `sit` "be thirsty", `bello` "fight, wage war") were attacked
five times in the gloss **selector** before anyone checked the loader. Each
attempt fixed two words and broke two others, because the selector was choosing
correctly from candidates that were wrong before it ever ran. The pattern to
notice: **when a fix keeps trading one case for another, the defect is upstream
of where you are editing.**

The corrective is mechanical — for any wrong gloss, check in this order:
1. Is the dictionary entry keyed on the right headword? (§3, §7)
2. Does `lemma_map` contain forms that should not exist? (§7)
3. Only then, is the selector choosing wrongly among correct candidates?

---

## ESSE is not in the data files — Whitaker's build inserts it

`sum` has no entry in `DICTLINE.GEN`. Checked exhaustively: no `TO_BE` row, no
stems `s`/`e`/`fu`/`fut`, nothing in `UNIQUES.LAT` (all 76 entries), nothing in
`ADDONS.LAT`. Line 36414 is *sumo* "take up", which is why the string `sum`
resolves there.

It is not missing from Whitaker's dictionary. It is inserted by his build.
`src/commands/makedict_main.adb` prints

```
This version inserts ESSE when D_K = GEN
```

and constructs the entry in code before writing DICTFILE:

```ada
Be_Ve      : constant Verb_Entry := (Con => (5, 1), Kind => To_Be);
Mean_To_Be : constant Meaning_Type :=
   Head ("be; exist; (also used to form verb perfect passive tenses)"
         & " with NOM PERF PPL", Max_Meaning_Size);
...
--  First construct ESSE
De.Stems (1) := "s";   De.Stems (2) := "";
De.Stems (3) := "fu";  De.Stems (4) := "fut";
De.Part := (V, Be_Ve);
De.Tran := (X, X, X, A, X);
De.Mean := Mean_To_Be;
```

`words_engine-parse.adb:306` carries the same paradigm a second way, as
`Is_Sum` — a mood x tense x number x person table of every finite form.

**We reproduced his data files but not his build**, so the commonest verb in
Latin arrived with no entry, and the selector fell through to whatever else
shared the surface: `est` -> *edo* "eject/emit" (55,286 tokens), `sit` ->
*sitio*, `sint` -> *sino*, `esto`/`eris`/`ero` -> *sumo* "take up". Every one
of those symptoms is this single hole.

### The fix

`load_whitakers_latin.py` now does what `makedict_main.adb` does: it **parses**
the entry out of the Ada source (stems, conjugation, `Tran` flags, meaning) and
renders one DICTLINE-format row, read by the same parser as the other 39,338.
Nothing is transcribed by hand — the values stay Whitaker's, and the build
fails loudly if the Ada file is absent or its shape has changed, rather than
silently reverting to the hole.

The inflection engine does the rest. Conjugation (5, 1) with those stems is
what it already applies to the compounds *absum*, *adsum*, *desum*, *insum*,
*intersum*, which ARE in DICTLINE. Output: **105 forms with morphology.**

```
sum   1 s pres active ind     fui      3 s perf active ind
es    2 s pres active ind     erat     3 s impf active ind
est   3 s pres active ind     sit      3 s pres active sub
sunt  3 p pres active ind     esse     0 pres active inf
ero   1 s fut active ind      futurus  nom s m fut active part
```

Two supporting defects had to be fixed for that row to parse:

**The meaning terminated at the first `;`.** The gloss is `"be; exist; ..."`, so
a semicolon terminator truncated it to `be`. The Ada is now read to
`Max_Meaning_Size`.

**Blank stem columns shifted every later stem left.** `_parse_stems` splits on
whitespace, so ESSE's deliberately blank second principal part vanished and
`fu`/`fut` slid into positions 2 and 3, generating `fuest`, `fuesse`,
`futisse`, `futeram`. Stems are now read by COLUMN
(`_parse_stem_columns`): an interior blank is a real zero-length stem — it is
what produces `es`, `est`, `eram`, `ero`, `esse` — and a trailing blank is an
unused column, as in every two-stem noun. The `if not stem_to_use` guard became
`if stem_to_use is None` for the same reason: `""` is a stem, `"zzz"` is not.

Verified safe for existing data: **0 of 39,338 DICTLINE rows have an interior
blank stem column**, so no entry that the file already contains parses
differently.

### Consequence to expect

`est`, `sunt`, `erat` and the rest now gloss as Whitaker's own **"be"**, where
they previously read "to be, exist, live" from the L&S glosses package (the
package filled the blank precisely because Whitaker had none). ~151,776 tokens
change wording. Decided 2026-09-01: take Whitaker's, since Whitaker is the
gloss source and the package exists only to fill blanks. Those tokens also gain
person/number/tense morphology they did not have.

### Measured outcome (build of 2026-09-02)

The entry alone was not enough. Whitaker's first sense for `sum` is **"be"** —
two characters — and `_usable_gloss` in `generate_latin_interlinear.py`
discarded any gloss of two characters or fewer. So the first build after this
change shipped unchanged: the ESSE entry loaded, generated its 105 forms and
was selected correctly by POS and lemma, then was thrown away, and
`_whitaker_defines("sum")` answered False for the same reason, leaving the
package rescue in charge.

That cutoff is now **source-scoped** rather than removed. Measured over the
module DB, 96 entries have a gloss of two characters or fewer: 70 Lewis-Short
and 10 package entries that are headword echoes and truncation artifacts
(`ad` -> "ad", `accumulate` -> "in"), against 16 Whitaker entries that are
ordinary English (`sum` -> "be", `nulla` -> "no", `bos` -> "ox", `bito` ->
"go"). No entry from any source has a gloss of one character.

Result, weighted by corpus tokens:

```
copula now resolving to Whitaker's own entry     154,450 tokens
  of which flatly WRONG before:                      902
     eris   'hedgehog'                    -> 'be'
     ero    'kind of basket made w/reeds' -> 'be'
     simus  'flatnosed, snub-nosed'       -> 'be'
     sitis  'thirst'                      -> 'be'
```

Every `eris`, `ero`, `simus` and `sitis` token in the corpus carries treebank
lemma `sum`, so nothing genuine was displaced — which is also why all 902 were
wrong before.

Costs the source-scoping brought with it, all small and all recorded rather
than patched:

```
bos family    'ox, bull, cow' -> 'ox'          492 tokens, thinner
euge          'well done! bravo!' -> 'oh'       24 tokens, worse
nullus family 'no one' -> 'no'                3,684 tokens, better for the
                                              adjectival forms, which is most
46 tokens LOST  quote-glued surfaces (`sum"`, `'est`) that the package used to
                fill and Whitaker's headword does not reach. Blank, not wrong.
```

Text integrity vs baseline: **2,743 works, 260 passing, 0 regressed, 0 works
whose DB text hash or line count changed.** The change is gloss-only.

---

## Adverbs generated no morphology at all

`parse_inflects` handled `V`, `VPAR`, `N`, `ADJ` and `PRON`. `ADV` was in
neither the pattern parser nor the form generator, so every adverb contributed
only its headword.

Whitaker stores an adverb's three degrees as three STEMS, and the patterns emit
each with a zero-length ending:

```
ADV    X 1 0        ADV    POS 1 0
ADV    X 2 0        ADV    COMP 1 0
ADV    X 3 0        ADV    SUPER 1 0

bene       melius       optime           ADV X     <- three stems
generose   generosius   generosissime    ADV X
stulte                                   ADV POS   <- one stem
```

387 of 2,204 ADV entries carry a comparative or superlative stem. All were
dropped. Added 2026-09-08: an `ADV` branch in both the parser and the
generator, matching the entry's declared degree. An `ADV POS` entry still
yields one form, so nothing is invented — `stultius` correctly remains absent,
because Whitaker has no comparative for `stultus` or `stulte`.

Worth ~115 corpus tokens directly. Recorded because the absence was structural,
not a data limitation.
