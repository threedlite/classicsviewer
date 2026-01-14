# Ancient Greek Sentence Diagram Analyzer

Generate Reed-Kellogg diagrams and dependency visualizations for Ancient Greek using CLTK with morphology-based corrections.

## Setup

```bash
cd treebank
python3 -m venv venv
source venv/bin/activate
pip install cltk
```

## Run

```bash
python scripts/reed_kellogg_analyzer.py
```

## Output

Generates 5 files per sentence in `output/reed_kellogg/`:

| File | Description |
|------|-------------|
| `phaedo_002_rk.svg` | Reed-Kellogg sentence diagram |
| `phaedo_002_graph.svg` | Dependency arc diagram |
| `phaedo_002_tree.txt` | ASCII dependency tree |
| `phaedo_002_annotated.txt` | Tree with correction annotations |
| `phaedo_002_table.txt` | Before/after parse comparison |

## Morphology-Based Corrections

The analyzer applies automatic corrections to CLTK parses using morphological agreement from the database (12.7M entries in `lemma_map` table):

1. **Demonstrative attachment**: Fixes demonstratives (ἐκεῖνος, οὗτος, ὅδε) attaching to wrong nouns by matching case/gender/number
2. **Main clause coordination**: Fixes coordinated verbs wrongly attached to subordinate clauses

Corrections use a score threshold (default 1.0) to filter out low-confidence fixes:
- Score = sum of matching features (case +1, gender +1, number +1)
- Only corrections with score >= threshold are applied

Example output:
```
ROOT
└── [6] παρεγένου (VERB, root)
    ├── [10] ἡμέρᾳ (NOUN, obl)
    │   ├── [9] τῇ (DET, det)
    │   │   └── [8] ἐκείνῃ (ADJ, nmod) ← corrected: was under Σωκράτει
    ├── [19] ἢ (CCONJ, cc) ← corrected: was under ἔπιεν
    └── [22] ἤκουσας (VERB, conj) ← corrected: was under ἔπιεν
```

## Configuration

Edit `scripts/reed_kellogg_analyzer.py` to change:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `db_path` | `../data-prep/perseus_texts_extended.db` | Database with texts and morphology |
| `book_id` | `tlg0059.tlg004.001` | Work to analyze (Plato's Phaedo) |
| `num_lines` | `20` | Number of lines to process |
| `min_score` | `1.0` | Minimum score for corrections |

## Project Structure

```
treebank/
├── scripts/
│   └── reed_kellogg_analyzer.py  # Main analyzer script
├── output/
│   └── reed_kellogg/             # Generated diagrams
└── venv/                         # Python virtual environment
```
