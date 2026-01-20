# Dependency Parsing Limitations (Stanza via CLTK)

## Issue Summary

The interlinear generation uses CLTK for dependency parsing, which internally wraps **Stanza** for Ancient Greek NLP. Stanza's statistical dependency parser (`perseus_nocharlm` model) can produce incorrect parse trees for complex Greek sentences, particularly those with coordination structures spanning long distances.

### Technical Stack

```
Interlinear Generation (generate_interlinear.py)
    └── CLTK 2.x (wrapper)
            └── Stanza 1.x (actual NLP engine)
                    └── perseus_nocharlm model (trained on Perseus Treebank)
```

When CLTK analyzes Greek text, Stanza loads these processors:
- `tokenize`: perseus
- `pos`: perseus_nocharlm
- `lemma`: perseus_nocharlm
- `depparse`: perseus_nocharlm  ← Source of dependency parsing errors

## Example: Plato's Phaedo, Line 2

**Greek text:**
> αὐτός ὦ Φαίδων παρεγένου Σωκράτει ἐκείνῃ τῇ ἡμέρᾳ ᾗ τὸ φάρμακον ἔπιεν ἐν τῷ δεσμωτηρίῳ ἢ ἄλλου του ἤκουσας

**Translation:**
> "Were you yourself present with Socrates, O Phaedo, on that day when he drank the poison in the prison, or did you hear from someone else?"

### The Bug

Word 19 (ἤκουσας "you heard") incorrectly points to word 12 (ἔπιεν "he drank") as its head.

**Stanza (via CLTK) output:**
```
 4. παρεγένου       deprel=root       head=0   ← Main verb (correct)
12. ἔπιεν           deprel=acl        head=8   ← "he drank" modifying ἡμέρᾳ (correct)
16. ἢ               deprel=cc         head=12  ← "or" pointing to ἔπιεν (WRONG)
19. ἤκουσας         deprel=conj       head=12  ← "you heard" as conjunct of ἔπιεν (WRONG)
```

**Correct parse should be:**
- ἤκουσας (word 19) should have head=4 (παρεγένου), as a conjunct of the main verb
- The sentence has two coordinate main clauses: "were you present... OR did you hear"

### Why This Happens

1. Stanza's `perseus_nocharlm` model is a statistical neural network trained on Perseus Treebank data
2. The parser sees ἢ ("or") immediately preceding the ἄλλου του ἤκουσας phrase
3. It incorrectly attaches the coordination to the nearest verb (ἔπιεν) rather than the main verb (παρεγένου)
4. Long-distance coordination structures are challenging for statistical parsers

## When Stanza Is Used vs. Perseus Treebank

The interlinear generation system prefers human-verified Perseus Treebank data when available:

| Work | Treebank Available | Parser Used |
|------|-------------------|-------------|
| Homer's Iliad | No | Stanza (via CLTK) |
| Homer's Odyssey | No | Stanza (via CLTK) |
| Plato's Euthyphro (tlg0059.tlg001) | Yes | Perseus Treebank |
| Plato's Phaedo (tlg0059.tlg004) | No | Stanza (via CLTK) |
| Sophocles' Ajax | Yes | Perseus Treebank |
| Most other works | No | Stanza (via CLTK) |

Perseus Treebank coverage is limited to select works. See `data-sources/treebank_data/v1/greek/data/` for available treebanks.

## Impact

- Sentence tree visualizations may show incorrect dependency structures
- Head pointers may connect semantically unrelated words
- Coordination structures (ἢ, καί, τε) are particularly prone to errors
- The glosses and morphology are still correct; only the tree structure is affected

## Potential Future Solutions

1. **Add post-processing heuristics** - Detect common coordination patterns and correct them
2. **Disable tree for non-treebank works** - Show "no tree data available" instead of potentially wrong data

## Technical Details

- CLTK version: 2.4.0 (wrapper around Stanza)
- Stanza version: 1.11.0 (actual NLP engine)
- Model: `perseus_nocharlm` for POS, lemma, and depparse
- Interlinear generation code: `data-prep/build_modules/generate_interlinear/generate_interlinear.py`
- Treebank loader: `data-prep/build_modules/generate_interlinear/treebank_loader.py`
- Tree display: `app/src/main/java/com/classicsviewer/app/TranslationAdapter.kt`

## Date Identified

2025-01-20
