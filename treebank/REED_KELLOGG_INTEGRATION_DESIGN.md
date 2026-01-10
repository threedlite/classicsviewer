# Reed-Kellogg Diagram Integration Design

## Overview

Generate Reed-Kellogg sentence diagrams dynamically in the Android app by:
1. **Build time**: Run CLTK dependency parsing and add to interlinear XML files
2. **Runtime**: Render diagrams from interlinear data using Kotlin/Android Canvas

## Scope

- **Greek texts only** - no Latin
- **Extended database only** - not included in sample DB
- **No schema changes** - data stored in existing interlinear XML format

## Why This Approach

- CLTK requires Python + large ML models (~500MB) - cannot run on Android
- Interlinear XML already has form, lemma, morphology per word
- Just need to add dependency parse data (deprel, head)
- No database schema changes required

## Current Interlinear XML Format

Each word entry has 3 lines:

```xml
| Σωκράτει |
| **Socrates** |
| Σωκράτης dat s |
```

- Line 1: Surface form
- Line 2: Definition (bold)
- Line 3: Lemma + morphology

## Extended Format with CLTK Parse

Add a 4th line with dependency relation and head position:

```xml
| Σωκράτει |
| **Socrates** |
| Σωκράτης dat s |
| obl 4 |
```

- Line 4: `deprel head_position`
  - `deprel`: Universal Dependencies relation (nsubj, obj, obl, advmod, etc.)
  - `head_position`: 1-based position of head word (0 = root)

## Full Example

Line 2 of Phaedo:

```
αὐτός ὦ Φαίδων παρεγένου Σωκράτει ἐκείνῃ τῇ ἡμέρᾳ...
```

Would become:

```xml
| αὐτός |
| **the very one, the same** |
| αὐτός |
| nsubj 4 |

| ὦ |
| **O! oh!** |
| ὦ 1 s pres subj act |
| vocative 0 |

| Φαίδων |
| **Phaedo** |
| Φαίδων |
| vocative 2 |

| παρεγένου |
| **To be beside, be in attendance upon** |
| παραγίγνομαι |
| root 0 |

| Σωκράτει |
| **Socrates** |
| Σωκράτης dat s |
| obl 4 |

| ἐκείνῃ |
| **the person there, that person** |
| ἐκεῖνος f dat s |
| det 8 |

| τῇ |
| **here, there** |
| τῇ f dat s |
| det 8 |

| ἡμέρᾳ |
| **day** |
| ἡμέρα dative singular feminine |
| obl 4 |
```

## Dependency Relations (deprel) Reference

`deprel` is the Universal Dependencies relation type. It describes how each word syntactically relates to its head word.

### Core Relations for RK Diagrams

| deprel | Meaning | RK Diagram Position |
|--------|---------|---------------------|
| `root` | Main verb/predicate | Center of main baseline |
| `nsubj` | Nominal subject | Left of verb on baseline |
| `obj` | Direct object | Right of verb on baseline |
| `iobj` | Indirect object | On pedestal below verb |
| `obl` | Oblique argument (prep phrases) | Descending line from verb |

### Modifier Relations

| deprel | Meaning | RK Diagram Position |
|--------|---------|---------------------|
| `advmod` | Adverb modifying verb | Slanted line below verb |
| `amod` | Adjective modifying noun | Slanted line below noun |
| `det` | Determiner (ὁ, ἡ, τό) | Slanted line below noun |
| `nmod` | Noun modifier (genitive) | Slanted line below noun |
| `nummod` | Numeric modifier | Slanted line below noun |
| `case` | Preposition/postposition | On the obl descending line |

### Clause Relations

| deprel | Meaning | RK Diagram Position |
|--------|---------|---------------------|
| `advcl` | Adverbial clause | Subordinate baseline below |
| `ccomp` | Clausal complement | Subordinate baseline below |
| `xcomp` | Open clausal complement | Subordinate baseline below |
| `acl` | Adjectival clause (relative) | Subordinate baseline, linked to noun |
| `csubj` | Clausal subject | Subordinate clause as subject |

### Coordination

| deprel | Meaning | RK Diagram Position |
|--------|---------|---------------------|
| `cc` | Coordinating conjunction (καί, ἤ) | Dashed line linking clauses |
| `conj` | Conjunct (2nd item in coordination) | Parallel structure |

### Other

| deprel | Meaning | RK Diagram Position |
|--------|---------|---------------------|
| `vocative` | Direct address (ὦ Φαίδων) | Floated above baseline in brackets |
| `punct` | Punctuation | Ignored |
| `discourse` | Discourse particle (γάρ, δή) | Slanted line as modifier |
| `aux` | Auxiliary verb | Combined with main verb |
| `cop` | Copula (εἰμί) | Verb position on baseline |

### How Head Works

The `head` number is the 1-based position of the word this word depends on:

```
Word:     αὐτός   ὦ    Φαίδων   παρεγένου   Σωκράτει
Position:   1     2      3         4           5
deprel:   nsubj  voc   voc       root        obl
head:       4     0      2         0           4
```

- `αὐτός` (head=4): subject of παρεγένου
- `ὦ` (head=0): vocative, no syntactic head
- `Φαίδων` (head=2): vocative attached to ὦ
- `παρεγένου` (head=0): root verb, no head
- `Σωκράτει` (head=4): oblique argument of παρεγένου

### Mapping to RK Structure

```
deprel → RK role:
  root     → verb (center of baseline)
  nsubj    → subject (left of divider)
  obj      → direct_object (right of verb)
  iobj     → indirect_object (pedestal)
  obl+case → prepositional_phrase (descender)
  advmod   → verb_modifier (slant below verb)
  amod/det → noun_modifier (slant below noun)
  advcl    → subordinate_clause (lower baseline)
  acl      → relative_clause (lower baseline, linked)
  conj+cc  → coordinated_clause (parallel baseline)
```

## Data Requirements for RK Diagrams

The renderer needs per word:

| Field | Source | Example |
|-------|--------|---------|
| form | Line 1 | παρεγένου |
| lemma | Line 3 (before space) | παραγίγνομαι |
| pos | Derived from morphology or CLTK | VERB |
| case | Line 3 (morphology) | dat |
| deprel | Line 4 | obl |
| head | Line 4 | 4 |
| position | Word order in line | 5 |

## Build Process

### Modified Interlinear Generation

Update `build_modules/generate_interlinear/` to:

1. After generating lines 1-3 for each word
2. Run CLTK analysis on the full line text
3. Append line 4 with deprel + head for each word

### CLTK Integration

```python
from cltk import NLP

nlp = NLP(language_code='grc', suppress_banner=True)

def get_parse_for_line(line_text: str) -> List[Tuple[str, int]]:
    """Returns list of (deprel, head) for each word."""
    doc = nlp.analyze(line_text)
    results = []
    for word in doc.words:
        deprel = word.dependency_relation
        head = word.governor + 1 if word.governor is not None else 0
        results.append((deprel, head))
    return results
```

### Processing Time

- CLTK parsing: ~50-100 words/second per worker
- Extended Greek: ~35M words
- With 8 workers: ~12-24 hours (similar to current interlinear generation)
- Can run as part of existing interlinear generation pass

## Android App Integration

### Parsing Interlinear Data

When loading interlinear for a line, parse the 4th line if present:

```kotlin
data class InterlinearWord(
    val form: String,
    val definition: String,
    val lemma: String,
    val morphology: String?,
    val deprel: String?,      // null if no parse data
    val head: Int?            // null if no parse data
)

fun parseInterlinearLine(xml: String): List<InterlinearWord> {
    // Parse existing 3 lines
    // If 4th line exists, extract deprel and head
}
```

### RK Rendering

```kotlin
class ReedKelloggRenderer(private val context: Context) {

    fun canRender(words: List<InterlinearWord>): Boolean {
        return words.all { it.deprel != null && it.head != null }
    }

    fun render(canvas: Canvas, words: List<InterlinearWord>, bounds: RectF) {
        if (!canRender(words)) return

        val structure = buildStructure(words)
        drawDiagram(canvas, structure, bounds)
    }

    private fun buildStructure(words: List<InterlinearWord>): RKStructure {
        // Port logic from Python reed_kellogg.py
        // Find root verb, subject, object, modifiers, subordinate clauses
    }
}
```

### UI Integration

In text reading view, show diagram toggle only when parse data exists:

```kotlin
private fun updateDiagramButton() {
    val interlinear = viewModel.getCurrentInterlinear()
    val hasParseData = interlinear?.all { it.deprel != null } == true
    diagramButton.isVisible = hasParseData
}
```

## Phased Implementation

### Phase 1: Interlinear Extension (Python)
1. Modify interlinear generator to run CLTK
2. Add 4th line to XML output
3. Test on subset of Greek texts
4. Run full generation for extended DB

### Phase 2: Android Parsing (Kotlin)
1. Update interlinear parser to handle 4th line
2. Add InterlinearWord fields for deprel/head
3. Test data loading

### Phase 3: Rendering Engine (Kotlin)
1. Port RK structure analysis from Python
2. Implement Canvas-based diagram rendering
3. Handle Greek text measurement

### Phase 4: UI Integration
1. Add diagram toggle button
2. Diagram view with zoom/pan
3. Graceful fallback when no parse data

## Size Impact

The 4th line adds ~10-15 bytes per word (e.g., `| nsubj 4 |`).

- Extended Greek: ~35M words
- Additional size: ~350-525 MB uncompressed
- Compressed: ~50-100 MB additional in ZIP

This is acceptable within the existing extended database size (~2.7GB compressed).

## Fallback Behavior

- **Sample DB**: No parse data, no RK diagrams available
- **Extended DB, Greek texts**: RK diagrams available
- **Extended DB, non-Greek texts**: No parse data, no RK diagrams

UI shows diagram button only when parse data exists for current text.

## Dependencies

### Build Time
- CLTK with Greek models (~500MB)
- Existing interlinear generation infrastructure

### Runtime
- Android Canvas API (built-in)
- No new external dependencies
- No database schema changes

## Files Required

### Build-time (Python) - Modify Existing

```
data-prep/build_modules/generate_interlinear/
├── generate_interlinear_multi.py    # Add CLTK parse call, append 4th line
└── cltk_parser.py                   # NEW: CLTK wrapper for dependency parsing
```

### Runtime (Android/Kotlin) - New Files

```
app/src/main/java/com/classicsviewer/app/diagram/
├── ReedKelloggStructure.kt          # Data classes (RKWord, RKClause, RKStructure)
├── SentenceAnalyzer.kt              # Build RK structure from parse data
└── ReedKelloggRenderer.kt           # Canvas drawing logic

app/src/main/java/com/classicsviewer/app/ui/
└── ReedKelloggView.kt               # Custom View for diagram display
```

### Runtime (Android/Kotlin) - Modify Existing

```
app/src/main/java/com/classicsviewer/app/
├── ui/reading/
│   └── TextReadingFragment.kt       # Add diagram toggle button
└── data/
    └── InterlinearParser.kt         # Parse 4th line (deprel, head)
```

### Reference (Port to Kotlin)

```
treebank/src/visualization/
└── reed_kellogg.py                  # Port structure analysis + layout logic
```

### Summary

| Type | New | Modified |
|------|-----|----------|
| Python (build) | 1 | 1 |
| Kotlin (runtime) | 4 | 2-3 |
| **Total** | **5** | **3-4** |

## Next Steps

1. Review and approve design
2. Modify interlinear generator to add CLTK parse
3. Test on Phaedo or small subset
4. Run full Greek interlinear + parse generation
5. Implement Android rendering
