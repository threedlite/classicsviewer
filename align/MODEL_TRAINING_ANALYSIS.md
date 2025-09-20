# Alignment Model Training Data Analysis

## Overview
The Greek-English text alignment system uses a Random Forest classifier trained on parallel texts from the Perseus Digital Library. This document details exactly what data the model trains on and how training examples are generated.

## Training Data Source

### Perseus Digital Library Collection
- **Repository**: `canonical-greekLit`
- **Greek texts**: 814 files (`*-grc*.xml`)
- **English translations**: 788 files (`*-eng*.xml`)
- **Format**: TEI-compliant XML with structured text segments

## Training Data Generation

### Total Training Examples
- **41,102 total examples**
  - 24,679 positive examples (60%) - actual aligned segments
  - 16,423 negative examples (40%) - randomly misaligned pairs

### Process for Creating Training Pairs

For each Greek-English text pair in Perseus:

#### 1. Structure Analysis
The system first analyzes both texts to determine the alignment strategy:

- **Direct-line alignment**: Used for poetry (e.g., Homer's Iliad)
  - Line numbers match directly (line 1 ↔ line 1)
  - Confidence: 0.95

- **Direct-section alignment**: Used for prose with matching sections
  - Section references match (e.g., 2.3 ↔ 2.3)
  - Confidence: 0.90

- **Proportional alignment**: Used when segment counts differ
  - Maps segments proportionally based on ratio
  - Confidence: 0.70

#### 2. Positive Example Generation
Extracts actual aligned pairs based on the determined strategy:
```python
# Example: Direct line alignment for poetry
if greek_seg.get('ref') == english_seg.get('ref'):
    features = extract_features(greek_seg, english_seg)
    training_pair = {
        'features': features,
        'label': 1,  # Aligned
        'confidence': 0.95
    }
```

#### 3. Negative Example Generation
Creates non-aligned pairs by random sampling:
```python
# Randomly pair segments that shouldn't align
greek_idx = random(0, len(greek_segments))
english_idx = random(0, len(english_segments))
# Ensure they're far from actual alignment
if not actually_aligned(greek_idx, english_idx):
    training_pair = {
        'features': features,
        'label': 0,  # Not aligned
        'confidence': 0.0
    }
```

## Feature Extraction

Each training example consists of 10 features:

### Feature Importance (from trained model)
1. **proper_noun_overlap** (31.7%) - Matching names between texts
2. **char_ratio** (29.4%) - Character length ratio
3. **word_ratio** (21.0%) - Word count ratio
4. **sentence_ratio** (10.0%) - Sentence count ratio
5. **punctuation_similarity** (6.3%) - Punctuation pattern similarity
6. **number_overlap** (1.5%) - Matching numbers
7. **starts_similarly** (<1%) - Similar beginning patterns
8. **has_dialogue** (<1%) - Dialogue indicators
9. **position_difference** (<1%) - Position in document
10. **is_sequential** (<1%) - Sequential alignment

## Authors and Texts in Training Data

### Major Contributors
Based on processing logs, the training data includes:

- **tlg0014 - Demosthenes**: 60+ political speeches
  - Well-aligned prose with section numbers
  - High-quality 19th century translations

- **tlg0013 - Aeschylus**: Greek tragedies
  - Line-by-line verse translations
  - Some texts have no segments (chorus parts)

- **tlg0012 - Homer**: Iliad and Odyssey
  - Epic poetry with consistent line numbering
  - Multiple translation versions

- **tlg0627 - Hippocrates**: Medical treatises
  - Technical prose with varied structure
  - Section-based alignment

- **tlg0085 - Aeschines**: Attic orations
  - Political speeches similar to Demosthenes
  - Clear section divisions

- **tlg0551 - Appian**: Historical texts
  - Narrative prose with book/chapter structure

- **tlg0526 - Arrian**: Historical and philosophical works
  - Including Epictetus's Discourses
  - Mixed alignment strategies

## Training Process

### Data Collection
1. Scans Perseus directory for all Greek files
2. Finds matching English translations by filename patterns
3. Processes each pair to extract training examples
4. Balances positive/negative examples (max 100 negatives per text)

### Model Training
- **Algorithm**: Random Forest Classifier
  - 100 trees
  - Max depth: 10
  - Min samples split: 5
- **Train/Test Split**: 80/20 with stratification
- **Training Examples**: ~33,000 (80% of 41,102)
- **Test Examples**: ~8,200 (20% of 41,102)

### Performance on Test Set
- **Overall Accuracy**: 71.9%
- **Aligned Pairs**: Precision 0.74, Recall 0.83, F1 0.78
- **Non-Aligned Pairs**: Precision 0.68, Recall 0.55, F1 0.61

## Key Insights

### Why Proper Names Matter Most (31.7% importance)
- Names are consistent across translations (Socrates → Σωκράτης)
- Strong indicator of content alignment
- Robust to different translation styles

### Character/Word Ratios (50.4% combined)
- English typically 1.5-2x longer than Greek
- Consistent ratio indicates alignment
- Deviations suggest commentary or missing text

### Challenges in Training Data
1. **Imbalanced texts**: Some Perseus texts have many more segments
2. **Variable quality**: Translation quality varies by century and translator
3. **Structural differences**: Poetry vs. prose requires different strategies
4. **Missing alignments**: Some texts (like Aeschylus) have empty segments

## Application to First1K Texts

When applied to First1K Greek texts:
- **Success rate**: 52.4% (22 of 42 texts)
- **Common failures**:
  - Non-translations (commentary, notes)
  - Wrong language (Latin instead of English)
  - Extreme length mismatches (summaries vs. full text)

The model correctly rejects texts that aren't actual translations, maintaining high precision even when recall is lower.