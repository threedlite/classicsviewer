# Critical Apparatus and Variant Readings in First1K and PTA Texts

## Overview

The database build process handles critical apparatus (scholarly annotations and textual variants) from First1KGreek and PTA (Patristic Text Archive) texts. A bug fix in commit 68035f8 corrected duplicate text extraction that was causing inflated line lengths.

## Impact Summary

| Metric | Before Fix | After Fix | Change |
|--------|------------|-----------|--------|
| Database Size | 17.3GB / 3.5GB | 13.1GB / 2.7GB | -4.2GB / -800MB |
| Total Lines | 3,847,949 | 3,102,465 | -745,484 (19%) |
| Greek Words | 54.8M | 34.9M | -19.9M (36%) |
| Max Line Length | Up to 139,292 chars | Typically < 5,000 chars | -96% |

## Greek Variant Readings Structure

PTA texts contain extensive textual variants using TEI `<app>` elements:

```xml
<app type="variants">
  <lem wit="#A #E #V"/>
  <rdg wit="#B #F #M #P #W #I" type="addition">τοῦ μακαρίου</rdg>
</app>
<app type="variants">
  <lem wit="#M #P #W #E #V">θεοδωρήτου</lem>
  <rdg wit="#B" cause="orthographic">θεοδωρητου</rdg>
  <rdg wit="#A #F #I" cause="orthographic">θεοδωρίτου</rdg>
</app>
```

### Variant Types Found

| Type | Example | Description |
|------|---------|-------------|
| Orthographic | θεοδωρήτου / θεοδωρητου / θεοδωρίτου | Spelling variants |
| Addition | τοῦ μακαρίου | Text present in some manuscripts |
| Omission | `<rdg type="omission"/>` | Text absent from some manuscripts |
| Substitution | ἑρμηνεία / ὑπόμνημα | Different words |
| Case variants | προφήτην / προφήτα | Grammatical variants |

### Files with Most Variants (>100 `<app>` tags)

All files with significant variant apparatus are from PTA, not First1KGreek:

| App Tags | File |
|----------|------|
| 20,256 | pta0004.pta001.pta-grcBibex (Theodoret on Daniel) |
| 4,086 | pta0022.pta001.pta-grc1 |
| 3,332 | pta0003.pta020.pta-grcBibex3 |
| 2,375 | pta0003.pta017.pta-grc1 |
| 1,626 | pta0001.pta026.pta-grcBibex |
| 1,144 | pta9999.pta065.pta-grc1 |
| 1,139 | pta0003.pta020.pta-grcBibex2 |
| 1,084 | pta9999.pta067.pta-grc1 |
| 931 | pta9999.pta064.pta-grc1 |
| 829 | pta9999.pta063.pta-grc1 |
| 776 | pta0022.pta002.pta-grc1 |
| 773 | pta9999.pta066.pta-grc1 |
| 710 | pta0200.pta001.pta-syc1 (Syriac) |
| 654 | pta0039.pta001.pta-grc2 |
| 502 | pta0001.pta001.pta-grcBibex |
| 476 | pta0003.pta020.pta-grcBibex1 |
| 472 | pta0001.pta028.pta-grcBibex |
| 441 | pta9999.pta089.pta-grc1 |
| 335 | pta9999.pta069.pta-grc1 |
| 330 | pta0040.pta001.pta-grc1 |

**Note:** First1KGreek texts use `<note type="footnote">` for apparatus (filtered out). PTA uses structured `<app>/<lem>/<rdg>` markup where only `<lem>` (accepted reading) is extracted; `<rdg>` variants are filtered.

## What Is Currently Extracted

**Included in database:**
- `<lem>` (lemma) - accepted/main reading chosen by the editor
- All Greek text outside of variant apparatus

**Excluded from database:**

| Tag | Purpose | Why Filtered |
|-----|---------|--------------|
| `<rdg>` | Variant readings from manuscripts | Only `<lem>` (accepted reading) kept |
| `<note>` | Editorial notes in Latin/English | Not primary text |
| `<foreign>` | Non-Greek insertions | Often Latin commentary |
| `<ref>` | Cross-references | Navigation metadata |
| `<bibl>` | Bibliographic citations | Scholarly apparatus |
| `<editorialDecl>` | Editorial declarations | Metadata |
| `<teiHeader>` | Document header | Metadata |
| `<gloss>` | Glossary entries | Supplementary |
| `<title>` | Title elements | Metadata |

## Bug Fix Details (Commit 68035f8)

The commit "remove variant readings from first1k/pta" actually fixed a **tail text duplication bug**, not filtering:

**Before:** Text after child elements (tail text) was being extracted multiple times due to incorrect recursive handling, causing:
- Lines with 139,000+ characters
- Same Greek text appearing multiple times
- Inflated word counts

**After:** Tail text is handled correctly at each level of recursion:
```python
def extract_text_from_first1k_element(elem, include_tail=True):
    # Pass include_tail=False for recursive calls
    child_text = extract_text_from_first1k_element(child, include_tail=False)
    # Parent handles child.tail separately
    if child.tail:
        text_parts.append(child.tail)
```

## Example: Editorial Notes (Filtered)

First1KGreek texts contain Latin scholarly notes:

```xml
<note type="footnote">Adnotatio ad fr. 1. Verba δύναται —ϲφόδρα per parenthesin
dicta accipienda sunt (cf. E. Gud. 1, 18); pro παρὰ τὸ βάλλειν εἰϲ γῆν ποτὲ δὲ
καὶ τὸ ἀναιρεῖν lin. 6 scripsi ex E. M. 3, 28...</note>
```

These contain:
- Editorial comments ("Adnotatio ad fr. X...")
- Manuscript variant explanations in Latin
- Source citations and cross-references
- Emendation justifications

Example: Aelius Herodianus tlg009 has **749 footnotes**.

## Current Behavior Summary

1. **Only accepted readings extracted** - `<lem>` content kept, `<rdg>` variants filtered
2. **Editorial notes in Latin/English filtered** - `<note>` tags excluded
3. **Text is no longer duplicated** - tail text bug fixed
4. **Clean readable Greek** - only the editor's preferred text appears

## Future Considerations

For scholarly use cases:
1. **Separate variants display**: Store `<lem>` vs `<rdg>` separately, show main text with hover/tap for variants
2. **Apparatus toggle**: Optional view showing full critical apparatus
3. **Manuscript siglum display**: Show which manuscripts (A, B, F, etc.) support each reading
4. **Variant highlighting**: Color-code variant readings in text display
