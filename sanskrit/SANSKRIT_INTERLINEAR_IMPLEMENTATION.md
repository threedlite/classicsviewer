# Sanskrit Interlinear Implementation

## Executive Summary

The Sanskrit interlinear system uses DCS (Digital Corpus of Sanskrit) CoNLL-U files as the primary data source. Key findings:

- **DCS provides lemmas, POS tags, and morphological features for ALL 268+ works**
- **16 Vedic works** have full treebank data (HEAD/DEPREL) from DCS
- **252+ non-treebank works** get dependency parsing via **Stanza fallback**
- **CLTK is not required** - DCS provides all morphological data; CLTK 2.4.0 only has GenAI pipelines for Sanskrit

---

## Data Availability from DCS

### All Works (268+)

Every DCS CoNLL-U file contains these fields for each word:

| Field | Name | Status | Example |
|-------|------|--------|---------|
| 1 | ID | Always present | `1` |
| 2 | FORM | Always present | `ānvīkṣikī` |
| 3 | LEMMA | Always present | `ānvīkṣikī` |
| 4 | UPOS | Always present | `NOUN` |
| 5 | XPOS | Usually `_` | `_` |
| 6 | FEATS | Always present | `Case=Nom\|Gender=Fem\|Number=Sing` |
| 7 | **HEAD** | **Treebank only** | `2` or `_` |
| 8 | **DEPREL** | **Treebank only** | `obj` or `_` |
| 9 | DEPS | Usually `_` | `_` |
| 10 | MISC | Always present | `LemmaId=58545\|Unsandhied=ānvīkṣikī` |

---

## Works with Treebank Data (16 total)

Only these Vedic texts have HEAD/DEPREL populated in DCS:

| Category | Works |
|----------|-------|
| **Vedas** | Ṛgveda, Atharvaveda (Śaunaka) |
| **Upaniṣads** | Aitareyopaniṣad, Chāndogyopaniṣad, Muṇḍakopaniṣad, Śvetāśvataropaniṣad |
| **Sūtras** | Gautamadharmasūtra, Manusmṛti, Hiraṇyakeśigṛhyasūtra, Khādiragṛhyasūtra, Vaitānasūtra, Vārāhagṛhyasūtra, Āpastambagṛhyasūtra, Āśvālāyanaśrautasūtra |
| **Āraṇyakas** | Śāṅkhāyanāraṇyaka |
| **Philosophy** | Nyāyabindu |

### Limitations

- **Partial Coverage**: Only 16 works have treebank data vs 268 total DCS works
- **Vedic Focus**: Primarily Vedic texts; Classical Sanskrit (Kālidāsa, etc.) not included
- **No Epic Coverage**: Mahābhārata, Rāmāyaṇa not in treebank

---

## Sample Treebank Data (Ṛgveda 1.1.1)

```
# text = agnim īḍe purohitam yajñasya devam ṛtvijam hotāram ratna dhātamam

1  agnim      agni      NOUN  Case=Acc|...  2  obj        "I praise Agni"
2  īḍe        īḍ        VERB  Mood=Ind|...  0  root       (root of sentence)
3  purohitam  purohita  NOUN  Case=Acc|...  1  nmod:appos "the priest"
4  yajñasya   yajña     NOUN  Case=Gen|...  3  nmod       "of the sacrifice"
5  devam      deva      NOUN  Case=Acc|...  3  conj       "the god"
6  ṛtvijam    ṛtvij     NOUN  Case=Acc|...  3  conj       "the officiator"
7  hotāram    hotṛ      NOUN  Case=Acc|...  3  conj       "the invoker"
8  ratna      ratna     NOUN  Case=Cpd|...  9  obj        "treasure"
9  dhātamam   dhātama   ADJ   Case=Acc|...  7  acl        "the best bestower"
```

The tree structure shows:
- Word 2 (īḍe "I praise") is the **root**
- Word 1 (agnim "Agni") is the **obj** (object) of word 2
- Words 3-7 are appositional modifiers cascading from word 1
- Word 9 is an adjectival clause (acl) modifying word 7

---

## Dependency Relations Used

The Sanskrit treebank uses Universal Dependencies (UD) relations:

### Core Arguments
- `nsubj` - nominal subject
- `obj` - direct object
- `iobj` - indirect object

### Modifiers
- `nmod` - nominal modifier
- `nmod:appos` - appositional modifier
- `amod` - adjectival modifier
- `advmod` - adverbial modifier
- `acl` - adjectival clause

### Coordination & Function
- `conj` - conjunct
- `cc` - coordinating conjunction
- `case` - case marking (postpositions)
- `cop` - copula
- `discourse` - discourse particle

### Other
- `vocative` - vocative
- `root` - sentence root
- `dep` - unspecified dependency

---

## Interlinear Output Format

### Works WITH Treebank Data (16 works)

Full tree information displayed:
```
| lemma ~ POS deprel head sent_pos |
```

Example (Ṛgveda 1.1.1):
```
| agni ~ NOUN obj 2 1 |
| īḍ ~ VERB root 0 2 |
| purohita ~ NOUN nmod:appos 1 3 |
```

### Works WITHOUT Treebank Data (252+ works)

With Stanza fallback (tree data available):
```
| lemma ~ POS deprel head sent_pos |
```

The Stanza fallback reconstructs unsandhied text from DCS tokens to ensure word counts match, handling sandhi compounds like `daṇḍanītiśceti` → `daṇḍanītiḥ ca iti`.

---

## Implementation Status

### Data Flow

```
CoNLL-U Files (DCS)
       ↓
create_sanskrit_database_interlinear.py
  - Parses fields 0-9 including HEAD (6), DEPREL (7)
  - For non-treebank works: Stanza fallback for HEAD/DEPREL
  - Stores in words table with tree columns
       ↓
sanskrit_texts.db
  - words table: word, book_id, line_number, head, deprel, pos_tag, sentence_position
       ↓
generate_sanskrit_interlinear.py
  - Reads tree data from database
  - Outputs XML with tree info: | lemma ~ POS deprel head sent_pos |
```

### Modified Files

1. **`sanskrit/create_sanskrit_database_interlinear.py`** - Database creation
   - `words` table schema extended with `head`, `deprel`, `pos_tag`, `sentence_position` columns
   - CoNLL-U parsing extracts fields 6 (HEAD) and 7 (DEPREL) during import
   - Stanza fallback for non-treebank works

2. **`sanskrit/generate_sanskrit_interlinear.py`** - Interlinear generator
   - `WordData` class extended with tree fields
   - `get_line_words()` reads tree data directly from database
   - XML output format includes tree data
   - Statistics tracking for treebank-enhanced words

3. **`sanskrit/sanskrit_treebank_loader.py`** - Standalone loader (optional)
   - Can be used for analysis or direct CoNLL-U access
   - Not required for interlinear generation (data comes from database)

### Database Schema Extensions

```sql
-- Extended words table
CREATE TABLE words (
    ...
    head INTEGER,              -- Head word position (0=root)
    deprel TEXT,               -- Dependency relation
    pos_tag TEXT,              -- Universal POS tag
    sentence_position INTEGER  -- Position in sentence
);
```

---

## Stanza Fallback for Non-Treebank Works

### Why Stanza?

**Stanza 1.11.0** supports Sanskrit dependency parsing directly, providing HEAD/DEPREL for the 252+ works without DCS treebank data.

**Note**: CLTK 2.4.0 only has GenAI pipelines for Sanskrit (requires LLM API). Stanza provides offline dependency parsing.

### Accuracy Evaluation (50 Ṛgveda sentences, 347 words)

Evaluated against DCS Vedic Treebank gold standard:

| Metric | Score |
|--------|-------|
| **UAS (Unlabeled Attachment)** | 79.8% |
| **LAS (Labeled Attachment)** | 67.1% |
| **Label Accuracy** | 72.0% |

**Post-processing coordination fixes** are applied to improve accuracy:
- Accusative cascade: Series of accusatives → conj
- Locative repetition: Repeated locatives → conj
- Nominative predicates: Parallel nominatives → conj
- Adjective coordination: Sequential adjectives → conj

**Remaining error patterns**:
- Fine-grained relations - Confuses `nmod:appos` vs `amod`, `obj` vs `obl`
- Non-consecutive coordination - Words separated by other material

### Sample Comparison (Ṛgveda 1.1.1)

```
Form         DCS             Stanza (fixed)  Match
agnim        2/obj           2/obj           ✓
īḍe          0/root          0/root          ✓
purohitam    1/nmod:appos    1/amod          ~ (HEAD correct)
yajñasya     3/nmod          3/nmod          ✓
devam        3/conj          3/conj          ✓ (coordination fix applied)
ṛtvijam      3/conj          3/conj          ✓ (coordination fix applied)
hotāram      3/conj          3/conj          ✓ (coordination fix applied)
```

Tree structure after fix:
```
īḍe (root)
└── agnim (obj)
    └── purohitam (nmod:appos)
        ├── yajñasya (nmod)
        ├── devam (conj)
        ├── ṛtvijam (conj)
        └── hotāram (conj)
```

### Alignment Handling (Two-Pass Approach)

**Problem**: Stanza tokenization differs from DCS:
- DCS tokens are "unsandhied" (compounds split, e.g., `daṇḍanītiśceti` → 3 tokens)
- Stanza tokenizes raw sandhied text differently (keeps compounds as 1 token)
- Punctuation handling differs (dandas, etc.)
- Stanza may split into multiple sentences

**Solution**: Reconstruct unsandhied text from DCS's `Unsandhied=` field:
- Join DCS unsandhied forms with spaces
- Pass reconstructed text to Stanza (word counts now match)
- Apply two-pass HEAD remapping (similar to Greek treebank processing):

```python
def parse_with_stanza(text_iast: str, dcs_words: list = None) -> list:
    """
    Two-pass approach to handle:
    1. Punctuation filtering (exclude dandas, etc. from position counting)
    2. HEAD position remapping (sentence-local → global → non-punct)
    3. Multiple sentence handling (Stanza may split one DCS sentence)
    """
    doc = nlp(text_iast)

    # Pass 1: Build mapping from original positions to non-punct positions
    orig_to_nopunct = {}  # {global_orig_pos: nopunct_pos}
    nopunct_pos = 0
    global_offset = 0

    for sent in doc.sentences:
        for word in sent.words:
            global_pos = global_offset + word.id

            # Skip punctuation in position counting
            if not is_punctuation(word):
                nopunct_pos += 1
                orig_to_nopunct[global_pos] = nopunct_pos

        global_offset += len(sent.words)

    # Pass 2: Remap HEAD values to non-punct positions
    # HEAD=0 (root) stays 0, others get remapped
```

**Validation**:
- Only use Stanza if `len(stanza_result) == len(dcs_words)`
- Reject if word counts don't match (sandhi differences)

### Hybrid Data Strategy

| Source | Lemma | POS | HEAD | DEPREL |
|--------|-------|-----|------|--------|
| Treebank works (16) | DCS | DCS | DCS | DCS |
| Non-treebank works | DCS | DCS | **Stanza** | **Stanza** |

**Benefits**:
- DCS lemmas are gold-standard (manually verified)
- Stanza provides reasonable dependency structure for all works

---

## CLTK Analysis

### Why CLTK Is Not Used

CLTK 2.4.0 provides two Sanskrit pipelines:
1. **ClassicalSanskritGenAIPipeline**
2. **VedicSanskritGenAIPipeline**

Both are GenAI-based and require an LLM backend:

| Backend | Requirement |
|---------|-------------|
| `stanza` | Not available for Sanskrit in CLTK |
| `openai` | Requires `OPENAI_API_KEY` |
| `ollama` | Requires local Ollama server |
| `ollama-cloud` | Requires `OLLAMA_CLOUD_API_KEY` |
| `mistral` | Requires Mistral API key |

**Conclusion**: CLTK cannot provide offline morphological analysis for Sanskrit. Since DCS already provides all morphological data, CLTK is not needed.

---

## Comparison with Greek

| Aspect | Greek | Sanskrit |
|--------|-------|----------|
| Primary Data Source | Perseus XML + Morphology | DCS CoNLL-U |
| Lemmas | From dictionary lookup | From DCS (field 3) |
| POS Tags | From morphology tables | From DCS (field 4) |
| Morph Features | From morphology tables | From DCS (field 6) |
| Treebank Coverage | ~50 works (AGDT) | 16 works (Vedic) + Stanza fallback |
| Treebank Format | Custom XML | Universal Dependencies |
| Fallback Parser | CLTK Stanza (offline) | Stanza direct (offline) |

### Greek Flow (for reference)

1. **With treebank**: Use AGDT XML for HEAD/DEPREL
2. **Without treebank**: Use CLTK Stanza for lemmatization/POS

### Sanskrit Flow (implemented)

1. **All works**: Use DCS CoNLL-U for lemma, POS, features
2. **Treebank works (16)**: Also extract HEAD/DEPREL from DCS
3. **Non-treebank works (252+)**: Use Stanza for HEAD/DEPREL

---

## File Locations

- **Database Creator**: `sanskrit/create_sanskrit_database_interlinear.py`
- **Interlinear Generator**: `sanskrit/generate_sanskrit_interlinear.py`
- **Treebank Loader**: `sanskrit/sanskrit_treebank_loader.py`
- **Build Script**: `sanskrit/rebuild_sanskrit_pipeline.sh`
- **Test Script**: `sanskrit/test_stanza_alignment.py`
- **DCS CoNLL-U**: `data-sources/sanskrit/dcs/data/conllu/files/`
- **Greek Treebank (reference)**: `data-prep/build_modules/generate_interlinear/treebank_loader.py`

---

## Venv Setup

The Sanskrit build uses a dedicated virtual environment:

```bash
cd sanskrit
source venv/bin/activate

# Packages installed:
# - stanza>=1.8.0 (for dependency parsing fallback)
# - cltk>=2.4.0 (for future use)
# - indic-transliteration (IAST/Devanagari conversion)
# - Other dependencies in requirements.txt
```

The `rebuild_sanskrit_pipeline.sh` script automatically:
1. Creates venv if not present
2. Installs dependencies including Stanza
3. Downloads Stanza Sanskrit model
4. Uses venv Python for all build steps

---

## What Users Gain

### For Treebank-Enabled Works (16 Vedic texts)

1. **Sentence structure visualization** - See dependency trees
2. **Grammatical analysis** - Identify subjects, objects, modifiers
3. **Vedic syntax study** - Understand archaic Sanskrit constructions
4. **Learning aid** - See how complex sentences parse

### For All Works (268+)

1. **Lemma lookup** - Dictionary headword for each form
2. **POS tagging** - Grammatical category identification
3. **Morphological analysis** - Case, gender, number, tense, etc.
4. **Dependency structure** - Via Stanza fallback (when word counts match)

---

## Recommendations

1. **Continue using DCS data** - Provides comprehensive morphological analysis for all works

2. **Use Stanza fallback** - Provides dependency parsing for non-treebank works

3. **Keep CLTK in requirements** - Future versions may add offline Sanskrit support

4. **Display available data** - Show lemma + POS for all works, tree structure where available

5. **Document limitations** - Clearly indicate which works have full tree visualization vs Stanza-generated
