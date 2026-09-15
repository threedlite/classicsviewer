# Latin gloss evaluation harness

`gloss_eval.py` answers one question: **does a dictionary change improve or
regress the Latin interlinear glosses?**

It is an evaluation tool, not part of the build. It reads
`latin/interlinear_output/*.perseus-eng99.xml` and never writes to any database.

## Use

```bash
# 1. Snapshot the current glosses BEFORE changing anything
venv/bin/python3 latin/tools/gloss_eval.py capture before_new_ls

# 2. Rebuild the Latin module + interlinear with the new dictionary, then
venv/bin/python3 latin/tools/gloss_eval.py capture after_new_ls

# 3. Diff them
venv/bin/python3 latin/tools/gloss_eval.py compare before_new_ls after_new_ls

# Suspicious glosses in one snapshot on their own
venv/bin/python3 latin/tools/gloss_eval.py flag after_new_ls
```

Snapshots land in `latin/tools/snapshots/<label>.json` (~19 MB each).

## Everything is weighted by corpus frequency

Counts of dictionary *entries* hide the failures that matter, because the
commonest words have the longest articles and so the most ways to pick the wrong
part of one. Every number this tool prints is **tokens of running Latin**, taken
from `latin/latin_texts_extended.db` (4.8 M words, 43 authors).

`LOST` is one regression number to watch: a word that had a gloss and now has
`???`. It must be 0 or individually explained.

**`LOST` and the flags are NOT the regression picture.** Both miss the most
common kind of regression: a gloss that changes from one plausible English
phrase to another that happens to be the wrong word. `genus` shipped as "knee"
(that is *genu*) and `multa` as "fine"; neither is blank, both are ordinary
English, so neither the LOST count nor any detector fires. They sat in the
CHANGED bucket, which was reported by size and never read.

A blank gloss is much better than a wrong one (`LATIN_GLOSS_PIPELINE.md` §8),
so a rise in the blank rate is not by itself a regression — it is one only if
the tokens that went blank had a *correct* gloss before. The mirror of that
rule: **`GAINED` needs reading too.** Every `???` -> gloss token is a new
assertion, and it is the only bucket where a build can be worse than its
predecessor under the ranking. Read its top surfaces by frequency and take a
token-weighted sample of its tail; neither `LOST` nor any flag sees it.

So before accepting any gloss change: **read the CHANGED bucket, frequency
first.** The top 150 surfaces cover about half the changed tokens and take
minutes to scan. Classify each as fix / regression / neutral by asking whether
the new gloss is the same WORD, not whether it looks like a definition. A
review that reports only LOST and flag counts is incomplete, and saying
otherwise overstates the evidence.

## The flags are for review, not rejection

The detectors went through three versions. The first two are recorded here
because both looked reasonable and both were wrong:

| version | rule | result |
|---|---|---|
| 1 | Latin suffixes (`-us -um -is -at -are`) | **useless.** English shares them all. Flagged `this`, `that`, `where`, `war, warfare`, `by (agent)` — 8.88% of tokens, top 50 almost all correct |
| 2 | token not in `/usr/share/dict/words` | better, but web2 has no inflected forms, so `others` read as Latin; and no gazetteer, so `Cicero`, `Scipio`, `Africa` read as Latin |
| 3 | lowercase token that is in the Latin corpus and not English (with inflection backoff), brackets stripped first | **0 false positives on 28 hand-labelled good glosses, 8/9 known-bad caught.** 0.31% of tokens |

Version 3 details:
- Latin cited inside `(...)` / `[...]` is normal (`some ... others (alii ... alii)`,
  `I, me (PERS)`), so brackets are stripped before the test.
- Only **lowercase** tokens can count as Latin. Capitalised ones are proper
  nouns, and a proper noun is a correct gloss for itself.
- English membership tries simple inflections (`others`→`other`, `carried`→`carry`).

Known miss: Latin words absent from our corpus (a misspelling like
`Troie Liviniaque`) are not recognised as Latin. The correctly-spelled text is.

`whitaker-caps-tag` and `gloss-equals-headword` are reported as
**informational, not errors** — Whitaker's `(by GENDER/NUMBER)` is a deliberate
convention, and `six, sex` / `speaker, orator` legitimately repeat the headword.

## Requires

`/usr/share/dict/words` (present on macOS). Without it `reads-as-latin` is
skipped and the tool says so; every other flag still works.
