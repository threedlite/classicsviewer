# Implementation Notes - Lemmatization System

## Key Technical Decisions

### 1. Normalization Strategy
**Decision**: Strip ALL punctuation during normalization
**Rationale**: Greek texts contain various punctuation marks (commas, apostrophes, Greek question marks) that prevented lemma matching
**Impact**: Unified 293,291 → 220,387 unique words

### 2. Multiple Lemma Architecture
**Decision**: Store multiple possible lemmas per word with confidence scores
**Rationale**: Greek words can have multiple valid interpretations (e.g., ἄλγε could be noun or verb)
**Implementation**:
```sql
PRIMARY KEY (word_form, lemma)  -- Allows multiple lemmas per word
confidence REAL                 -- Ranks alternatives
```

### 3. Confidence Scoring System
```python
if lemma == word:
    confidence = 0.9  # Exact match
elif word + 'οσ' == lemma or word + 'η' == lemma or word + 'ον' == lemma:
    confidence = 0.7  # Direct suffix (good for elided forms)
elif len(lemma) < len(word):
    confidence = 0.6  # Removed suffix (stem)
else:
    confidence = 0.5  # Other transformations
```

### 4. Source Hierarchy
1. **enwiktionary:ancient-greek** (0.95) - Most reliable
2. **elwiktionary:declension** (0.9-0.95) - Generated from templates
3. **generated** (0.8) - LSJ-based lemmatization
4. **algorithmic** (0.5-0.75) - Pattern-based guesses
   - 0.75: Patronymic patterns
   - 0.7: Direct suffix addition
   - 0.6: Stem extraction
   - 0.5: Other transformations

### 5. Algorithmic Generation Strategy
**Process ALL words, not just unmapped ones**
- Ensures multiple interpretations are captured
- Allows algorithm to propose alternatives to existing mappings
- Trade-off: Larger intermediate database, but optimized at the end

## Performance Characteristics

### Processing Times
- Wiktionary extraction: ~10 minutes per dump
- LSJ lemmatization: ~2 minutes
- Algorithmic generation: ~3 minutes for 220k words
- Full build: ~15 minutes

### Memory Usage
- Peak during Wiktionary parsing: ~2GB
- Database operations: ~500MB
- Safe for systems with 4GB+ RAM

### Storage
- Intermediate database: ~1.5GB
- Optimized database: ~774MB
- Compression ratio: ~50% when creating OBB

## Algorithm Details

### Greek Word Endings Handled
**Nouns**: ων, ου, ω, ον, ε, α, ασ, ησ, η, αν, ην, οι, αισ, οσ, εσ, ι, σι, των, τοσ, τησ, τον, την, τα, ται

**Verbs**: ει, εισ, ομεν, ετε, ουσι, ουσιν, ομαι, εται, ομεθα, εσθε, ονται, σω, σεισ, σει, σομεν, σετε, σουσι, σα, σασ, σε, σαμεν, σατε, σαν, κα, κασ, κε, καμεν, κατε, κασι

**Participles**: μενοσ, μενη, μενον, μενου, μενησ, μενω, ντοσ, ντι, ντα, ντεσ, ντων

**Patronymics**: ιδησ, ιαδησ, ιδου, ιαδεω, ιδη, ιαδη, ιδα, ιαδα (+ genitive ηοσ)

### Special Cases
1. **Augmented verbs**: ε- prefix removal (εθηκε → θηκε → τιθημι)
2. **Elided forms**: Try adding endings without removing (μυρι + οσ → μυριοσ)
3. **Final sigma**: Always normalize ς → σ
4. **Patronymic vowel changes**: η→ε when forming base names (πηληιαδεω → πηλευσ)
5. **Genitive -ηος**: Maps to -ευς names with possible consonant doubling (αχιληοσ → αχιλλευσ)

## Known Limitations

### Coverage Gaps
1. **Compound verbs**: Limited prefix handling (only augments)
2. **Rare/dialectal forms**: Not in Wiktionary or dictionaries
3. **Some particles**: Still missing (δ', γ', τ')
4. **Complex verb forms**: Some imperfects and subjunctives

### Addressed Limitations
1. **Proper names**: Now handled via Wiktionary supplements (e.g., Ἀτρεύς)
2. **Ionic/Epic forms**: Added via Wiktionary (e.g., νοῦσος)
3. **Aorist passive participles**: Now recognized algorithmically (-θεις pattern)
4. **Dual forms**: Some coverage via Wiktionary (e.g., σφωέ)

### Accuracy Issues
1. **Ambiguous forms**: Algorithm may generate incorrect alternatives
2. **Confidence scoring**: Simple heuristics, not linguistically informed
3. **No context**: Can't disambiguate based on sentence meaning

## Database Schema Details

### lemma_map Table
```sql
word_form TEXT NOT NULL,        -- Normalized inflected form
word_normalized TEXT NOT NULL,  -- Same as word_form (legacy)
lemma TEXT NOT NULL,           -- Dictionary headword (normalized)
confidence REAL DEFAULT 1.0,    -- 0.0-1.0 score
source TEXT,                    -- Data source identifier
morph_info TEXT,               -- Optional grammatical tags
PRIMARY KEY (word_form, lemma)
```

### Indexes
- `idx_lemma_map_word` ON word_form
- `idx_lemma_map_normalized` ON word_normalized
- `idx_lemma_map_lemma` ON lemma

## Testing Approach

### Test Corpus
Homer's Odyssey (first 100 lines) - chosen for:
- Representative sample size
- Mix of common and rare words
- Various grammatical forms
- Realistic text complexity

### Success Metrics
1. **Coverage**: % of words with at least one lemma
2. **Accuracy**: Correct lemma is highest confidence
3. **Completeness**: All reasonable alternatives included

### Results on Test Corpus
- **Homer's Odyssey (100 lines)**: 77.1% coverage
- Represents realistic performance on epic Greek text
- Most content words successfully mapped
- Remaining gaps: compound verbs, rare forms, proper names