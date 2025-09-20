# First1K Translation Alignment Report

Generated: 2025-09-18T19:02:08.131103

## Summary
- Total texts processed: 42
- Successfully aligned: 22 (52.4%)
- Failed: 20 (47.6%)
- Total runtime: 77.144 seconds

## Model Training Performance
*Using trained RandomForest model*

### Model Test Set Performance:
- **Overall Accuracy**: 71.6%

#### Aligned Pairs:
- **Precision**: 0.73
- **Recall**: 0.83
- **F1-Score**: 0.78

#### Non-Aligned Pairs:
- **Precision**: 0.68
- **Recall**: 0.55
- **F1-Score**: 0.61

### Feature Importance:
- **proper_noun_overlap**: 33.5%
- **char_ratio**: 28.7%
- **word_ratio**: 19.7%
- **sentence_ratio**: 10.0%
- **punctuation_similarity**: 6.5%
- *Other features*: < 1.4% each

### Alignment Statistics
- Total alignments attempted: 2848
- Alignments accepted: 2357
- Alignments rejected: 491
- Average confidence: 0.735
- Min confidence: 0.300
- Max confidence: 0.950

### Confidence Distribution
- Very Low (< 0.3): 0
- Low (0.3-0.5): 109
- Medium (0.5-0.7): 929
- High (0.7-0.9): 1500
- Very High (≥ 0.9): 310

## By Author

### tlg0018 - Philo Judaeus
- Total works: 31
- Successful: 20
- Failed: 11
  - ✅ **tlg009 (grc1)** - tlg009: success
    - Alignments: 156
    - Runtime: 0.039s
  - ❌ **tlg031 (grc1)** - tlg031: failed
    - Reason: Not a valid translation: English file does not appear to be in English
  - ✅ **tlg007 (grc1)** - tlg007: success
    - Alignments: 58
    - Runtime: 0.015s
  - ❌ **tlg001 (grc1)** - tlg001: failed
    - Reason: No alignments above confidence threshold 0.6
  - ✅ **tlg006 (grc1)** - tlg006: success
    - Alignments: 146
    - Runtime: 0.045s
  - ❌ **tlg030 (grc1)** - tlg030: failed
    - Reason: Not a valid translation: Overall score too low: 0.269
  - ✅ **tlg008 (grc1)** - tlg008: success
    - Alignments: 155
    - Runtime: 0.039s
  - ✅ **tlg015 (grc1)** - tlg015: success
    - Alignments: 19
    - Runtime: 1.79s
  - ✅ **tlg012 (grc1)** - tlg012: success
    - Alignments: 59
    - Runtime: 0.016s
  - ❌ **tlg024 (grc1)** - tlg024: failed
    - Reason: Not a valid translation: English file does not appear to be in English
  - ✅ **tlg023 (grc1)** - tlg023: success
    - Alignments: 22
    - Runtime: 0.683s
  - ✅ **tlg022 (grc1)** - tlg022: success
    - Alignments: 307
    - Runtime: 0.116s
  - ❌ **tlg025 (grc1)** - tlg025: failed
    - Reason: Not a valid translation: English file does not appear to be in English
  - ❌ **tlg013 (grc1)** - tlg013: failed
    - Reason: No alignments above confidence threshold 0.6
  - ❌ **tlg014 (grc1)** - tlg014: failed
    - Reason: No alignments above confidence threshold 0.6
  - ✅ **tlg003 (grc1)** - tlg003: success
    - Alignments: 113
    - Runtime: 0.033s
  - ✅ **tlg004 (grc1)** - tlg004: success
    - Alignments: 121
    - Runtime: 0.039s
  - ✅ **tlg005 (grc1)** - tlg005: success
    - Alignments: 146
    - Runtime: 0.044s
  - ✅ **tlg002 (grc1)** - tlg002: success
    - Alignments: 7
    - Runtime: 32.788s
  - ❌ **tlg011 (grc1)** - tlg011: failed
    - Reason: No alignments above confidence threshold 0.6
  - ✅ **tlg016 (grc1)** - tlg016: success
    - Alignments: 152
    - Runtime: 0.041s
  - ❌ **tlg029 (grc1)** - tlg029: failed
    - Reason: Not a valid translation: Overall score too low: 0.244
  - ✅ **tlg020 (grc1)** - tlg020: success
    - Alignments: 27
    - Runtime: 1.398s
  - ❌ **tlg027 (grc1)** - tlg027: failed
    - Reason: Not a valid translation: Overall score too low: 0.300
  - ✅ **tlg018 (grc1)** - tlg018: success
    - Alignments: 16
    - Runtime: 1.273s
  - ✅ **tlg026 (grc1)** - tlg026: success
    - Alignments: 163
    - Runtime: 0.041s
  - ✅ **tlg019 (grc1)** - tlg019: success
    - Alignments: 8
    - Runtime: 33.26s
  - ✅ **tlg021 (grc1)** - tlg021: success
    - Alignments: 244
    - Runtime: 0.059s
  - ✅ **tlg017 (grc1)** - tlg017: success
    - Alignments: 18
    - Runtime: 0.842s
  - ❌ **tlg028 (grc1)** - tlg028: failed
    - Reason: Not a valid translation: Overall score too low: 0.282
  - ✅ **tlg010 (grc1)** - tlg010: success
    - Alignments: 152
    - Runtime: 0.039s

### tlg0094 - Dinarchus
- Total works: 1
- Successful: 1
- Failed: 0
  - ✅ **tlg001 (grc1)** - Against Demosthenes: success
    - Alignments: 2
    - Runtime: 0.853s

### tlg0317 - Aristaenetus
- Total works: 1
- Successful: 0
- Failed: 1
  - ❌ **tlg001 (grc1)** - Love Letters: failed
    - Reason: Not a valid translation: Overall score too low: 0.197

### tlg0527 - Epictetus
- Total works: 2
- Successful: 0
- Failed: 2
  - ❌ **tlg048 (grc2)** - Enchiridion: failed
    - Reason: Not a valid translation: Length ratio too extreme: 0.06
  - ❌ **tlg048 (grc1)** - Enchiridion: failed
    - Reason: Not a valid translation: Length ratio too extreme: 0.06

### tlg0544 - Aesopus
- Total works: 1
- Successful: 0
- Failed: 1
  - ❌ **tlg001 (grc1)** - Fables: failed
    - Reason: No alignments above confidence threshold 0.6

### tlg1553 - Apollodorus
- Total works: 1
- Successful: 0
- Failed: 1
  - ❌ **tlg001 (grc1)** - Library: failed
    - Reason: Not a valid translation: Overall score too low: 0.180

### tlg2018 - Eusebius of Caesarea
- Total works: 2
- Successful: 1
- Failed: 1
  - ❌ **tlg002 (grc2)** - Ecclesiastical History: failed
    - Reason: Not a valid translation: Overall score too low: 0.245
  - ✅ **tlg002 (grc1)** - Ecclesiastical History: success
    - Alignments: 266
    - Runtime: 2.019s

### tlg2038 - Theophilus of Antioch
- Total works: 1
- Successful: 0
- Failed: 1
  - ❌ **tlg001 (grc1)** - To Autolycus: failed
    - Reason: Not a valid translation: Overall score too low: 0.256

### tlg2948 - Methodius
- Total works: 1
- Successful: 0
- Failed: 1
  - ❌ **tlg001 (grc1)** - Symposium: failed
    - Reason: Not a valid translation: Overall score too low: 0.298

### tlg4037 - Maximus Confessor
- Total works: 1
- Successful: 0
- Failed: 1
  - ❌ **tlg001 (grc1)** - Ambigua: failed
    - Reason: Not a valid translation: Overall score too low: 0.271

## Failed Alignments Details

### tlg0527.tlg048 - Epictetus: Enchiridion
- Greek file: tlg0527.tlg048.1st1K-grc2.xml
- English file: tlg0527.tlg048.1st1K-eng1b.xml
- Reason: Not a valid translation: Length ratio too extreme: 0.06

### tlg0527.tlg048 - Epictetus: Enchiridion
- Greek file: tlg0527.tlg048.1st1K-grc1.xml
- English file: tlg0527.tlg048.1st1K-eng1b.xml
- Reason: Not a valid translation: Length ratio too extreme: 0.06

### tlg2018.tlg002 - Eusebius of Caesarea: Ecclesiastical History
- Greek file: tlg2018.tlg002.1st1K-grc2.xml
- English file: tlg2018.tlg002.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.245

### tlg0544.tlg001 - Aesopus: Fables
- Greek file: tlg0544.tlg001.1st1K-grc1.xml
- English file: tlg0544.tlg001.1st1K-eng1.xml
- Reason: No alignments above confidence threshold 0.6
- Greek segments: 1703
- English segments: 1665

### tlg4037.tlg001 - Maximus Confessor: Ambigua
- Greek file: tlg4037.tlg001.1st1K-grc1.xml
- English file: tlg4037.tlg001.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.271

### tlg2948.tlg001 - Methodius: Symposium
- Greek file: tlg2948.tlg001.1st1K-grc1.xml
- English file: tlg2948.tlg001.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.298

### tlg0018.tlg031 - Philo Judaeus: tlg031
- Greek file: tlg0018.tlg031.1st1K-grc1.xml
- English file: tlg0018.tlg031.1st1K-eng1.xml
- Reason: Not a valid translation: English file does not appear to be in English

### tlg0018.tlg001 - Philo Judaeus: tlg001
- Greek file: tlg0018.tlg001.1st1K-grc1.xml
- English file: tlg0018.tlg001.1st1K-eng1.xml
- Reason: No alignments above confidence threshold 0.6
- Greek segments: 170
- English segments: 171

### tlg0018.tlg030 - Philo Judaeus: tlg030
- Greek file: tlg0018.tlg030.1st1K-grc1.xml
- English file: tlg0018.tlg030.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.269

### tlg0018.tlg024 - Philo Judaeus: tlg024
- Greek file: tlg0018.tlg024.1st1K-grc1.xml
- English file: tlg0018.tlg024.1st1K-eng1.xml
- Reason: Not a valid translation: English file does not appear to be in English

### tlg0018.tlg025 - Philo Judaeus: tlg025
- Greek file: tlg0018.tlg025.1st1K-grc1.xml
- English file: tlg0018.tlg025.1st1K-eng1.xml
- Reason: Not a valid translation: English file does not appear to be in English

### tlg0018.tlg013 - Philo Judaeus: tlg013
- Greek file: tlg0018.tlg013.1st1K-grc1.xml
- English file: tlg0018.tlg013.1st1K-eng1.xml
- Reason: No alignments above confidence threshold 0.6
- Greek segments: 196
- English segments: 197

### tlg0018.tlg014 - Philo Judaeus: tlg014
- Greek file: tlg0018.tlg014.1st1K-grc1.xml
- English file: tlg0018.tlg014.1st1K-eng1.xml
- Reason: No alignments above confidence threshold 0.6
- Greek segments: 223
- English segments: 224

### tlg0018.tlg011 - Philo Judaeus: tlg011
- Greek file: tlg0018.tlg011.1st1K-grc1.xml
- English file: tlg0018.tlg011.1st1K-eng1.xml
- Reason: No alignments above confidence threshold 0.6
- Greek segments: 221
- English segments: 223

### tlg0018.tlg029 - Philo Judaeus: tlg029
- Greek file: tlg0018.tlg029.1st1K-grc1.xml
- English file: tlg0018.tlg029.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.244

### tlg0018.tlg027 - Philo Judaeus: tlg027
- Greek file: tlg0018.tlg027.1st1K-grc1.xml
- English file: tlg0018.tlg027.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.300

### tlg0018.tlg028 - Philo Judaeus: tlg028
- Greek file: tlg0018.tlg028.1st1K-grc1.xml
- English file: tlg0018.tlg028.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.282

### tlg1553.tlg001 - Apollodorus: Library
- Greek file: tlg1553.tlg001.1st1K-grc1.xml
- English file: tlg1553.tlg001.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.180

### tlg2038.tlg001 - Theophilus of Antioch: To Autolycus
- Greek file: tlg2038.tlg001.1st1K-grc1.xml
- English file: tlg2038.tlg001.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.256

### tlg0317.tlg001 - Aristaenetus: Love Letters
- Greek file: tlg0317.tlg001.1st1K-grc1.xml
- English file: tlg0317.tlg001.1st1K-eng1.xml
- Reason: Not a valid translation: Overall score too low: 0.197

## Performance Statistics
- Average runtime per text: 1.807s
- Fastest: 0.001s
- Slowest: 33.260s