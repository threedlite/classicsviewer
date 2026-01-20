# Sanskrit Interlinear Generation - Quick Reference

> **See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for complete details.**

## Overview

Sanskrit interlinear translations are generated automatically as part of the main build pipeline. The system creates word-by-word glosses with morphological data using the DCS dictionary and Stanza NLP.

## Quick Start

Interlinear is generated automatically during the full build:

```bash
cd /Users/user1/git/classicsviewer/sanskrit
./run_build.sh
```

The build pipeline:
1. Creates database with all 270 works (~75 min)
2. Imports lexicon from `dcs_sanskrit_lexicon.zip` (~2 min)
3. **Generates interlinear with Stanza NLP** (~20 min)
4. Imports interlinear into database (~2 min)
5. Compresses to ZIP (~1 min)

## Current Coverage

**Dictionary Lookup**: 95.9% coverage
**Morph Data**: Available for all words processed by Stanza NLP

## Files Generated

For each work, two files are created in `interlinear_output/`:
- `*.interlinear.txt` - Plain text word-by-word glosses
- `*.dcs-eng99.xml` - TEI XML with morph data

## Output Format

**Plain text (*.interlinear.txt)**:
```
1. ॐ | श्रीपरमात्मने | नमः | अथ
a word of solemn affirmation and | ? | bow | now
```

**XML format includes morph data**:
```
| पूर्व voc s m ~ ADJ conj 1 3 |
```
Where:
- `वoc s m` = vocative singular masculine (case/number/gender)
- `ADJ` = adjective (POS tag)
- `conj 1 3` = conjunction relation, head word 1, sentence position 3 (dependency)

## Technical Details

### Stanza NLP Integration

The build uses `fork` multiprocessing so workers inherit loaded Stanza models:
- Pre-loads `stanza.Pipeline('sa', processors='tokenize,pos,lemma,depparse')` before spawning
- Uses `mp.set_start_method('fork')` for model sharing
- 8 parallel workers process works concurrently

### Key Components

- `batch_generate_interlinear.py` - Parallel orchestrator with Stanza pre-loading
- `generate_sanskrit_interlinear.py` - Per-work XML/text generator
- `sanskrit_dictionary_lookup.py` - Dictionary lookup with sandhi splitting

### Data Files Required

- `dcs_sanskrit_lexicon.zip` (35 MB) - Pre-built and included in repo
  - Contains dictionary.csv and morphology.csv

## Statistics

- **270 works** processed
- **203,713 interlinear segments** generated
- **~20 minutes** generation time with 8 workers
- **95.9%** dictionary coverage

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Workers use system Python | Use `./run_build.sh` instead of `source venv/bin/activate` |
| Missing morph data | Verify Stanza models are downloaded |
| Low coverage | Check `dcs_sanskrit_lexicon.zip` is present |
| Build timeout | Monitor with `tail -f build_sanskrit.log` |

---

**Status**: ✅ Production Ready
**Last Updated**: January 2026
