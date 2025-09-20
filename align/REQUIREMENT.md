# XML Output Format Requirements

## Core Requirement
The output XML file must be exactly the same as the input XML, except with the addition of the alignment information.

## Implementation Details

### 1. Exact Preservation
The XMLEnhancer class preserves the original XML structure completely:
- **Original formatting**: All indentation, whitespace, and line breaks are preserved
- **XML declaration**: The original XML declaration format is maintained exactly
- **Comments**: All comments are preserved in their original positions
- **Namespaces**: All original namespaces are maintained
- **Attributes**: All original attributes remain unchanged
- **Text content**: All Greek/English text remains exactly as in the original

### 2. Alignment Additions
The only modifications made to the XML are the insertion of alignment milestones:

```xml
<milestone xmlns:ns1="http://classicsviewer.github.io/alignment/v1"
           n="align-1"
           unit="alignment"
           resp="ML-align-v1"
           cert="high"
           ns1:method="direct"
           ns1:greek-ref="1"
           ns1:english-ref="1"/>
```

### 3. Milestone Placement
Milestones are inserted at the beginning of the referenced element:
- For lines (`<l n="1">`): Milestone inserted as first child
- For divisions (`<div n="1">`): Milestone inserted as first child
- For paragraphs (`<p n="1">`): Milestone inserted as first child
- Original text is preserved as the tail of the milestone element

### 4. Milestone Attributes
Each milestone contains:
- `n`: Unique identifier (e.g., "align-1", "align-2")
- `unit`: Always set to "alignment"
- `resp`: Identifies the alignment system version ("ML-align-v1")
- `cert`: Confidence level ("high", "medium", or "low" based on confidence score)
- `align:method`: The alignment method used (e.g., "direct", "section", "content")
- `align:greek-ref`: Reference to the Greek text element
- `align:english-ref`: Reference to the English text element

### 5. Confidence Mapping
- confidence > 0.8: cert="high"
- confidence > 0.6: cert="medium"
- confidence <= 0.6: cert="low"

### 6. Namespace Declaration
The alignment namespace is added only when milestones are present:
- Namespace URI: `http://classicsviewer.github.io/alignment/v1`
- Prefix: `align` (though may appear as `ns1` in output due to lxml serialization)

### 7. File Naming Convention
Enhanced files are saved with `.aligned.xml` suffix:
- Input: `tlg0018.tlg001.First1K-grc1.xml`
- Output: `tlg0018.tlg001.First1K-grc1.aligned.xml`

### 8. No Alignment Case
If no alignments are found or all are below the confidence threshold:
- The original XML file is copied exactly without any modifications
- No milestones are added
- No namespace declarations are added

## Validation
The system ensures preservation by:
1. Reading the original XML as text to capture exact formatting
2. Using non-destructive XML parsing (preserve comments, entities, blank text)
3. Maintaining the original XML declaration if present
4. Only inserting milestone elements without modifying existing content
5. Testing with `test_xml_preservation.py` to verify exact preservation

## Example

### Original XML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <text>
        <body>
            <l n="1">μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος</l>
        </body>
    </text>
</TEI>
```

### Enhanced XML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <text>
        <body>
            <l n="1"><milestone xmlns:ns1="http://classicsviewer.github.io/alignment/v1" n="align-1" unit="alignment" resp="ML-align-v1" cert="high" ns1:method="direct" ns1:greek-ref="1" ns1:english-ref="1"/>μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος</l>
        </body>
    </text>
</TEI>
```

The only difference is the inserted milestone element - all other content, formatting, and structure remains exactly the same.
