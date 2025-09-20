# Greek-English Text Alignment System

A self-contained alignment system for Greek-English parallel texts, specifically designed for Perseus and First1K Greek collections. The system uses rule-based alignment with machine learning enhancement, achieving strong results without requiring external language models or transliteration.

Output folder has transformed xml from the First1k project (see license)
This has not been integrated into the main ClassicsViewer project yet.


## Quick Start

```bash
# Set up environment (one-time setup)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run complete pipeline (train model + apply alignments)
python run_alignment.py \
  --perseus-dir ../data-sources/canonical-greekLit \
  --first1k-dir ../data-sources/First1KGreek \
  --min-confidence 0.5

# Or skip training and use existing model (faster)
python run_alignment.py \
  --perseus-dir ../data-sources/canonical-greekLit \
  --first1k-dir ../data-sources/First1KGreek \
  --min-confidence 0.5 \
  --skip-training
```

### What happens when you run it:
1. **Analyzes** First1K texts to identify those needing alignment (~1 min)
2. **Generates** author/work name mappings automatically
3. **Aligns** Greek and English texts using windowed search (~70 sec)
4. **Creates** comprehensive reports with success/failure details

### Output files (all in `output/` directory):
- `alignment_report.md` - Human-readable report with author names
- `alignment_report.json` - Machine-readable results
- `alignments/*.json` - Individual JSON alignment files
- `alignments/*.aligned.xml` - Enhanced XML files with milestones
- `first1k_analysis.json` - Text analysis data
- `models/alignment_model.pkl` - Trained ML model

## Key Features

- **No external dependencies**: Works directly with Greek Unicode, no transliteration needed
- **Self-contained ML**: Trains on Perseus texts, applies to First1K
- **Smart windowed search**: O(n) complexity by comparing only nearby segments (±10% window)
- **Comprehensive reporting**: Detailed success/failure analysis with author and work names
- **Multiple alignment strategies**:
  - Direct line-to-line alignment for poetry
  - Section-based alignment for prose
  - Proportional mapping for different granularities
  - Content similarity with feature extraction

## Integrated Pipeline

The `run_alignment.py` script handles the complete workflow:

1. **Trains** alignment model on Perseus texts (optional)
2. **Analyzes** First1K texts to identify alignment candidates
3. **Generates** author/work mappings from metadata
4. **Applies** alignment to First1K texts
5. **Creates** comprehensive reports with timing and statistics

The pipeline automatically:
- Generates author and work name mappings from First1K metadata
- Produces detailed markdown and JSON reports
- Tracks success/failure reasons and runtime metrics
- Handles all TEI XML variations in both corpora

## Usage Options

The single `run_alignment.py` script handles the complete workflow:

```bash
python run_alignment.py --help
```

Options:
- `--perseus-dir`: Directory containing Perseus Greek texts (required)
- `--first1k-dir`: Directory containing First1K Greek texts (required)
- `--output-dir`: Output directory for all results (default: output)
- `--min-confidence`: Minimum confidence threshold (default: 0.6)
- `--skip-training`: Skip training and use existing model
- `--verbose`: Enable verbose logging

## Performance Statistics

- **Success Rate**: 76% (32/42 texts)
- **Average Runtime**: 1.7 seconds per text
- **Total Runtime**: ~72 seconds for 42 texts
- **Window Size**: Compares segments within ±10% position window (O(n) complexity)

### By Author Success Rates:
- Philo Judaeus: 74% (23/31 works)
- Smaller collections: 90%+ success

## Output Files

The pipeline generates:

- `output/models/alignment_model.pkl` - Trained ML model
- `output/alignments/*.json` - Individual alignment results
- `output/alignment_report.md` - Human-readable report with author/work names
- `output/alignment_report.json` - Machine-readable report data
- `output/first1k_analysis.json` - Text analysis results
- `author_work_mapping.json` - Auto-generated name mappings

## Technical Implementation

### Why No Greek Transliteration?

The system works directly with Greek Unicode characters. Transliteration is NOT needed for:
- Machine learning feature extraction
- Text similarity comparison
- Alignment scoring

Transliteration is only used for:
- Limited proper noun matching in feature extraction
- This is a minor feature, not core to the alignment

### Alignment Algorithm

1. **Feature Extraction**:
   - Text length ratios
   - Punctuation patterns
   - Structural similarity
   - Limited proper noun overlap

2. **Strategy Selection**:
   - Automatic detection of text type (poetry/prose)
   - Selection of optimal alignment strategy
   - Fallback to content similarity

3. **Windowed Search**:
   - Avoids O(n²) complexity
   - Compares only segments within ±10% position window
   - Maintains high accuracy while ensuring fast performance

## Project Structure

```
align/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── run_alignment.py                    # Main integrated pipeline
├── src/                               # Core library code
│   ├── xml_parser/                    # TEI XML parsing
│   │   ├── tei_reader.py             # Main parser
│   │   └── structure_analyzer.py     # Text structure detection
│   ├── alignment/                     # Alignment algorithms
│   │   ├── predictor.py              # ML predictor
│   │   ├── rule_based_aligner.py     # Rule-based alignment
│   │   └── feature_extractor.py      # Feature extraction
│   └── xml_writer/                    # XML enhancement
│       └── xml_enhancer.py           # Add alignments to XML
├── scripts/                           # Pipeline scripts
│   ├── train_aligner.py              # Train on Perseus
│   ├── analyze_first1k.py           # Analyze First1K
│   ├── apply_to_first1k_with_report.py # Apply with reporting
│   └── generate_author_work_mapping.py # Generate name mappings
├── models/                            # Trained models
└── output/                            # Results
    ├── alignments/                    # JSON alignment files
    └── alignment_report.md            # Final report
```

## Example Report Output

```markdown
# First1K Translation Alignment Report

## Summary
- Total texts processed: 42
- Successfully aligned: 32 (76.2%)
- Failed: 10 (23.8%)
- Total runtime: 71.812 seconds

## By Author

### tlg0018 - Philo Judaeus
- Total works: 31
- Successful: 23
- Failed: 8
  - ✅ **tlg009** - De agricultura: success
    - Alignments: 153
    - Runtime: 0.021s
  - ❌ **tlg001** - De opificio mundi: failed
    - Reason: No alignments above confidence threshold 0.5
```

## Limitations

- Currently optimized for Greek-English pairs only
- Requires TEI XML format
- Best results with well-structured texts
- May struggle with heavily fragmented or commentary texts

## Future Improvements

- Support for Latin texts
- Multi-language alignment
- Interactive alignment correction interface
- Deep learning models for improved accuracy
