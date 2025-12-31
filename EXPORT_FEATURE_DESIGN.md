# PDF/TXT Export Feature Design

## Overview

Add an export function to the text viewer page that exports the **currently viewed content** (Greek/Latin source, translation, or interlinear) to either TXT or PDF format. Users can export the entire document or a specific line range.

## Requirements

1. Export whatever is currently being viewed:
   - Greek/Latin source text (page 0 of ViewPager)
   - English translation (pages 1+ of ViewPager)
   - Interlinear view (when interlinear mode is active)

2. Export scope options:
   - **Entire book** - all lines from line 1 to `totalLines`
   - **Line range** - user-specified start and end lines

3. Export formats:
   - **TXT** - plain text, lightweight, universal compatibility
   - **PDF** - formatted document with proper Greek/Latin font support

## User Flow

```
User taps Export menu item
         │
         ▼
┌─────────────────────────────┐
│   Export Dialog             │
│                             │
│   Format:                   │
│   ○ TXT                     │
│   ○ PDF                     │
│                             │
│   Range:                    │
│   ○ Entire Book (1-2847)    │
│   ○ Custom Range            │
│     [  1  ] - [ 100 ]       │
│                             │
│   [Cancel]        [Export]  │
└─────────────────────────────┘
         │
         ▼
    SAF file picker
    (user chooses save location)
         │
         ▼
    Export in background
    with progress indicator
         │
         ▼
    Snackbar: "Exported successfully"
    with [Open] action
```

## UI Design

### Menu Integration

Add to `res/menu/menu_text_viewer.xml`:
```xml
<item
    android:id="@+id/action_export"
    android:icon="@drawable/ic_export"
    android:title="@string/export"
    app:showAsAction="never" />
```

### Export Dialog Layout

Create `res/layout/dialog_export.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:padding="24dp">

    <!-- Format Selection -->
    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Format"
        android:textAppearance="?attr/textAppearanceSubtitle1" />

    <RadioGroup
        android:id="@+id/formatGroup"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal">

        <RadioButton
            android:id="@+id/formatTxt"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="TXT"
            android:checked="true" />

        <RadioButton
            android:id="@+id/formatPdf"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginStart="24dp"
            android:text="PDF" />
    </RadioGroup>

    <View
        android:layout_width="match_parent"
        android:layout_height="1dp"
        android:layout_marginVertical="16dp"
        android:background="?android:attr/listDivider" />

    <!-- Range Selection -->
    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Range"
        android:textAppearance="?attr/textAppearanceSubtitle1" />

    <RadioGroup
        android:id="@+id/rangeGroup"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical">

        <RadioButton
            android:id="@+id/rangeEntireBook"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Entire Book (lines 1-2847)"
            android:checked="true" />

        <RadioButton
            android:id="@+id/rangeCustom"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Custom Range" />
    </RadioGroup>

    <!-- Custom Range Inputs (shown when Custom Range selected) -->
    <LinearLayout
        android:id="@+id/customRangeContainer"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginStart="32dp"
        android:layout_marginTop="8dp"
        android:orientation="horizontal"
        android:visibility="gone">

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:hint="From">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/startLineInput"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="number" />
        </com.google.android.material.textfield.TextInputLayout>

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_gravity="center"
            android:layout_marginHorizontal="16dp"
            android:text="—" />

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:hint="To">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/endLineInput"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="number" />
        </com.google.android.material.textfield.TextInputLayout>
    </LinearLayout>

</LinearLayout>
```

## Export Content Types

### 1. Source Text Export (Greek/Latin)

When viewing page 0 of the ViewPager (source text):

**Data Source:**
```kotlin
repository.getTextLines(workId, bookId, startLine, endLine)
```

**TXT Format:**
```
Homer - Iliad
Book 1, Lines 1-100
Exported from Classics Viewer

1    Μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος
2    οὐλομένην, ἣ μυρί᾽ Ἀχαιοῖς ἄλγε᾽ ἔθηκε,
3    πολλὰς δ᾽ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν
...
```

**PDF Format:**
- Title: `{Author} - {Work Title}`
- Subtitle: `Book {N}, Lines {start}-{end}`
- Body: Line numbers in margin, text in Noto Serif (supports Greek/Latin)
- Include speakers in italics if present (for dramatic texts)

### 2. Translation Export

When viewing pages 1+ (English translation):

**Data Source:**
```kotlin
repository.getTranslationSegmentsByTranslator(bookId, translator, startLine, endLine)
```

**TXT Format:**
```
Homer - Iliad
Book 1, Lines 1-100
Translation by Samuel Butler
Exported from Classics Viewer

[1-5] Sing, O goddess, the anger of Achilles son of Peleus,
that brought countless ills upon the Achaeans.

[6-10] Many a brave soul did it send hurrying down to Hades...
```

**PDF Format:**
- Same header structure
- Add translator attribution
- Line range markers in brackets

### 3. Interlinear Export

When interlinear mode is active:

**Data Source:**
```kotlin
// Get both source and word-by-word glosses
repository.getTextLines(workId, bookId, startLine, endLine)
repository.getInterlinearData(bookId, startLine, endLine)
```

**TXT Format:**
```
Homer - Iliad
Book 1, Lines 1-100 (Interlinear)
Exported from Classics Viewer

1    Μῆνιν    ἄειδε    θεὰ    Πηληϊάδεω    Ἀχιλῆος
     wrath    sing     goddess of-Peleus   of-Achilles

2    οὐλομένην,    ἣ       μυρί᾽     Ἀχαιοῖς    ἄλγε᾽    ἔθηκε,
     destructive   which   countless to-Achaeans pains    caused
...
```

**PDF Format:**
- Two-row layout per line: source word above, gloss below
- Aligned columns where practical
- Smaller font for glosses

## Implementation

### Files to Create

#### 1. `app/src/main/java/com/classicsviewer/app/export/TextExporter.kt`

```kotlin
package com.classicsviewer.app.export

import android.content.Context
import android.net.Uri
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.models.TranslationSegment
import java.io.OutputStream

enum class ExportFormat { TXT, PDF }
enum class ContentType { SOURCE, TRANSLATION, INTERLINEAR }

data class ExportRequest(
    val format: ExportFormat,
    val contentType: ContentType,
    val authorName: String,
    val workTitle: String,
    val bookLabel: String,
    val startLine: Int,
    val endLine: Int,
    val translator: String? = null  // For translation exports
)

class TextExporter(private val context: Context) {

    suspend fun exportToTxt(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>? = null,
        translations: List<TranslationSegment>? = null,
        interlinearData: List<InterlinearLine>? = null
    ) {
        outputStream.bufferedWriter().use { writer ->
            // Write header
            writer.appendLine("${request.authorName} - ${request.workTitle}")
            writer.appendLine("${request.bookLabel}, Lines ${request.startLine}-${request.endLine}")
            if (request.translator != null) {
                writer.appendLine("Translation by ${request.translator}")
            }
            if (request.contentType == ContentType.INTERLINEAR) {
                writer.appendLine("(Interlinear)")
            }
            writer.appendLine("Exported from Classics Viewer")
            writer.appendLine()

            // Write content based on type
            when (request.contentType) {
                ContentType.SOURCE -> writeSourceLines(writer, lines!!)
                ContentType.TRANSLATION -> writeTranslation(writer, translations!!)
                ContentType.INTERLINEAR -> writeInterlinear(writer, interlinearData!!)
            }
        }
    }

    suspend fun exportToPdf(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>? = null,
        translations: List<TranslationSegment>? = null,
        interlinearData: List<InterlinearLine>? = null
    ) {
        // Use Android's PdfDocument API or iText library
        // See PDF Generation section below
    }

    private fun writeSourceLines(writer: java.io.BufferedWriter, lines: List<TextLine>) {
        for (line in lines) {
            val speaker = if (line.speaker != null) "[${line.speaker}] " else ""
            writer.appendLine("${line.lineNumber.toString().padStart(5)}  $speaker${line.text}")
        }
    }

    private fun writeTranslation(writer: java.io.BufferedWriter, segments: List<TranslationSegment>) {
        for (segment in segments) {
            val range = if (segment.endLine != null && segment.endLine != segment.startLine) {
                "[${segment.startLine}-${segment.endLine}]"
            } else {
                "[${segment.startLine}]"
            }
            val speaker = if (segment.speaker != null) "[${segment.speaker}] " else ""
            writer.appendLine("$range $speaker${segment.translationText}")
            writer.appendLine()
        }
    }

    private fun writeInterlinear(writer: java.io.BufferedWriter, data: List<InterlinearLine>) {
        for (line in data) {
            // Source line
            writer.appendLine("${line.lineNumber.toString().padStart(5)}  ${line.sourceWords.joinToString("  ")}")
            // Gloss line (aligned)
            writer.appendLine("       ${line.glossWords.joinToString("  ")}")
            writer.appendLine()
        }
    }
}
```

#### 2. `app/src/main/java/com/classicsviewer/app/export/PdfGenerator.kt`

```kotlin
package com.classicsviewer.app.export

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.graphics.pdf.PdfDocument.PageInfo
import java.io.OutputStream

class PdfGenerator(private val context: Context) {

    companion object {
        private const val PAGE_WIDTH = 595   // A4 width in points
        private const val PAGE_HEIGHT = 842  // A4 height in points
        private const val MARGIN = 50f
        private const val LINE_HEIGHT = 16f
        private const val TITLE_SIZE = 18f
        private const val BODY_SIZE = 12f
    }

    private val greekFont: Typeface by lazy {
        // Use Noto Serif for Greek support
        Typeface.createFromAsset(context.assets, "fonts/NotoSerif-Regular.ttf")
    }

    fun generate(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>? = null,
        translations: List<TranslationSegment>? = null,
        interlinearData: List<InterlinearLine>? = null
    ) {
        val document = PdfDocument()
        var pageNumber = 1
        var yPosition = MARGIN
        var currentPage: PdfDocument.Page? = null
        var canvas: Canvas? = null

        val titlePaint = Paint().apply {
            typeface = greekFont
            textSize = TITLE_SIZE
            isAntiAlias = true
        }

        val bodyPaint = Paint().apply {
            typeface = greekFont
            textSize = BODY_SIZE
            isAntiAlias = true
        }

        fun startNewPage(): Canvas {
            currentPage?.let { document.finishPage(it) }
            val pageInfo = PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber++).create()
            currentPage = document.startPage(pageInfo)
            yPosition = MARGIN
            return currentPage!!.canvas
        }

        fun ensureSpace(needed: Float): Canvas {
            if (yPosition + needed > PAGE_HEIGHT - MARGIN) {
                return startNewPage()
            }
            return canvas!!
        }

        canvas = startNewPage()

        // Draw title
        canvas.drawText("${request.authorName} - ${request.workTitle}", MARGIN, yPosition, titlePaint)
        yPosition += LINE_HEIGHT * 1.5f

        canvas.drawText("${request.bookLabel}, Lines ${request.startLine}-${request.endLine}", MARGIN, yPosition, bodyPaint)
        yPosition += LINE_HEIGHT

        if (request.translator != null) {
            canvas.drawText("Translation by ${request.translator}", MARGIN, yPosition, bodyPaint)
            yPosition += LINE_HEIGHT
        }

        yPosition += LINE_HEIGHT * 2  // Space before content

        // Draw content
        when (request.contentType) {
            ContentType.SOURCE -> {
                lines?.forEach { line ->
                    canvas = ensureSpace(LINE_HEIGHT)
                    val text = "${line.lineNumber.toString().padStart(5)}  ${line.text}"
                    canvas!!.drawText(text, MARGIN, yPosition, bodyPaint)
                    yPosition += LINE_HEIGHT
                }
            }
            ContentType.TRANSLATION -> {
                translations?.forEach { segment ->
                    val neededHeight = estimateTextHeight(segment.translationText, bodyPaint) + LINE_HEIGHT
                    canvas = ensureSpace(neededHeight)
                    // Draw translation with word wrap
                    drawWrappedText(canvas!!, segment, bodyPaint, yPosition)
                    yPosition += neededHeight
                }
            }
            ContentType.INTERLINEAR -> {
                interlinearData?.forEach { line ->
                    canvas = ensureSpace(LINE_HEIGHT * 3)
                    // Source line
                    canvas!!.drawText("${line.lineNumber}  ${line.sourceWords.joinToString("  ")}", MARGIN, yPosition, bodyPaint)
                    yPosition += LINE_HEIGHT
                    // Gloss line
                    val glossPaint = Paint(bodyPaint).apply { textSize = BODY_SIZE * 0.9f }
                    canvas!!.drawText("     ${line.glossWords.joinToString("  ")}", MARGIN, yPosition, glossPaint)
                    yPosition += LINE_HEIGHT * 1.5f
                }
            }
        }

        currentPage?.let { document.finishPage(it) }
        document.writeTo(outputStream)
        document.close()
    }

    private fun estimateTextHeight(text: String, paint: Paint): Float {
        val maxWidth = PAGE_WIDTH - (MARGIN * 2)
        val words = text.split(" ")
        var lines = 1
        var currentWidth = 0f

        for (word in words) {
            val wordWidth = paint.measureText("$word ")
            if (currentWidth + wordWidth > maxWidth) {
                lines++
                currentWidth = wordWidth
            } else {
                currentWidth += wordWidth
            }
        }

        return lines * LINE_HEIGHT
    }

    private fun drawWrappedText(canvas: Canvas, segment: TranslationSegment, paint: Paint, startY: Float) {
        // Implementation for word-wrapped text drawing
        // ...
    }
}
```

### Files to Modify

#### 1. `app/src/main/res/menu/menu_text_viewer.xml`

Add export menu item:
```xml
<item
    android:id="@+id/action_export"
    android:icon="@drawable/ic_file_download"
    android:title="@string/export_text"
    app:showAsAction="never" />
```

#### 2. `app/src/main/java/com/classicsviewer/app/TextViewerPagerActivity.kt`

Add in `onOptionsItemSelected()`:
```kotlin
R.id.action_export -> {
    showExportDialog()
    true
}
```

Add export dialog method:
```kotlin
private fun showExportDialog() {
    val dialogView = layoutInflater.inflate(R.layout.dialog_export, null)
    val formatGroup = dialogView.findViewById<RadioGroup>(R.id.formatGroup)
    val rangeGroup = dialogView.findViewById<RadioGroup>(R.id.rangeGroup)
    val customRangeContainer = dialogView.findViewById<LinearLayout>(R.id.customRangeContainer)
    val startLineInput = dialogView.findViewById<TextInputEditText>(R.id.startLineInput)
    val endLineInput = dialogView.findViewById<TextInputEditText>(R.id.endLineInput)
    val entireBookRadio = dialogView.findViewById<RadioButton>(R.id.rangeEntireBook)

    // Update "Entire Book" label with actual line count
    entireBookRadio.text = "Entire Book (lines 1-$totalLines)"

    // Pre-fill custom range with current view
    startLineInput.setText(currentStartLine.toString())
    endLineInput.setText(currentEndLine.toString())

    // Show/hide custom range inputs
    rangeGroup.setOnCheckedChangeListener { _, checkedId ->
        customRangeContainer.visibility = if (checkedId == R.id.rangeCustom) View.VISIBLE else View.GONE
    }

    MaterialAlertDialogBuilder(this)
        .setTitle("Export")
        .setView(dialogView)
        .setPositiveButton("Export") { _, _ ->
            val format = if (formatGroup.checkedRadioButtonId == R.id.formatTxt)
                ExportFormat.TXT else ExportFormat.PDF

            val (startLine, endLine) = if (rangeGroup.checkedRadioButtonId == R.id.rangeEntireBook) {
                1 to totalLines
            } else {
                val start = startLineInput.text.toString().toIntOrNull() ?: 1
                val end = endLineInput.text.toString().toIntOrNull() ?: totalLines
                start.coerceIn(1, totalLines) to end.coerceIn(1, totalLines)
            }

            launchExport(format, startLine, endLine)
        }
        .setNegativeButton("Cancel", null)
        .show()
}

private fun launchExport(format: ExportFormat, startLine: Int, endLine: Int) {
    // Determine content type from current ViewPager position
    val contentType = when {
        binding.viewPager.currentItem == 0 && isInterlinearMode -> ContentType.INTERLINEAR
        binding.viewPager.currentItem == 0 -> ContentType.SOURCE
        else -> ContentType.TRANSLATION
    }

    // Get translator name if viewing translation
    val translator = if (contentType == ContentType.TRANSLATION) {
        translators.getOrNull(binding.viewPager.currentItem - 1)
    } else null

    // Build filename
    val extension = if (format == ExportFormat.TXT) "txt" else "pdf"
    val sanitizedTitle = workTitle.replace(Regex("[^a-zA-Z0-9]"), "_")
    val filename = "${sanitizedTitle}_${bookLabel}_${startLine}-${endLine}.$extension"

    // Launch SAF file picker
    val mimeType = if (format == ExportFormat.TXT) "text/plain" else "application/pdf"
    val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
        addCategory(Intent.CATEGORY_OPENABLE)
        type = mimeType
        putExtra(Intent.EXTRA_TITLE, filename)
    }

    // Store export params for result handler
    pendingExportRequest = ExportRequest(
        format = format,
        contentType = contentType,
        authorName = authorName,
        workTitle = workTitle,
        bookLabel = bookLabel,
        startLine = startLine,
        endLine = endLine,
        translator = translator
    )

    exportFileLauncher.launch(intent)
}

// Activity result launcher for SAF
private val exportFileLauncher = registerForActivityResult(
    ActivityResultContracts.StartActivityForResult()
) { result ->
    if (result.resultCode == RESULT_OK) {
        result.data?.data?.let { uri ->
            performExport(uri)
        }
    }
}

private fun performExport(uri: Uri) {
    val request = pendingExportRequest ?: return

    lifecycleScope.launch {
        try {
            // Show progress
            val progressDialog = MaterialAlertDialogBuilder(this@TextViewerPagerActivity)
                .setMessage("Exporting...")
                .setCancelable(false)
                .create()
            progressDialog.show()

            withContext(Dispatchers.IO) {
                // Fetch data based on content type
                val lines = if (request.contentType == ContentType.SOURCE ||
                               request.contentType == ContentType.INTERLINEAR) {
                    repository.getTextLines(workId, bookId, request.startLine, request.endLine)
                } else null

                val translations = if (request.contentType == ContentType.TRANSLATION) {
                    repository.getTranslationSegmentsByTranslator(
                        bookId, request.translator!!, request.startLine, request.endLine
                    )
                } else null

                val interlinear = if (request.contentType == ContentType.INTERLINEAR) {
                    repository.getInterlinearData(bookId, request.startLine, request.endLine)
                } else null

                // Write to file
                contentResolver.openOutputStream(uri)?.use { outputStream ->
                    val exporter = TextExporter(this@TextViewerPagerActivity)
                    when (request.format) {
                        ExportFormat.TXT -> exporter.exportToTxt(
                            outputStream, request, lines, translations, interlinear
                        )
                        ExportFormat.PDF -> exporter.exportToPdf(
                            outputStream, request, lines, translations, interlinear
                        )
                    }
                }
            }

            progressDialog.dismiss()

            // Show success with open action
            Snackbar.make(binding.root, "Export complete", Snackbar.LENGTH_LONG)
                .setAction("Open") {
                    val openIntent = Intent(Intent.ACTION_VIEW).apply {
                        setDataAndType(uri, if (request.format == ExportFormat.TXT) "text/plain" else "application/pdf")
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    startActivity(Intent.createChooser(openIntent, "Open with"))
                }
                .show()

        } catch (e: Exception) {
            Log.e("Export", "Export failed", e)
            Snackbar.make(binding.root, "Export failed: ${e.message}", Snackbar.LENGTH_LONG).show()
        }
    }
}
```

#### 3. `app/src/main/res/values/strings.xml`

Add:
```xml
<string name="export_text">Export</string>
<string name="export_format">Format</string>
<string name="export_range">Range</string>
<string name="export_entire_book">Entire Book</string>
<string name="export_custom_range">Custom Range</string>
<string name="export_from">From</string>
<string name="export_to">To</string>
<string name="exporting">Exporting...</string>
<string name="export_complete">Export complete</string>
<string name="export_failed">Export failed</string>
```

## Technical Considerations

### Font Support for Greek/Latin

The PDF export must properly render Greek characters. Options:

1. **Android's PdfDocument API** (recommended for simplicity)
   - Uses system fonts, Greek support depends on device
   - Embed Noto Serif font from assets for consistency

2. **iText 7** (if more control needed)
   - AGPL license - must comply with open source requirements
   - Full Unicode support, font embedding

3. **Apache PDFBox** (alternative)
   - Apache 2.0 license
   - Android port available

### File Size Estimates

| Content Type | Format | 1000 Lines | 10,000 Lines |
|-------------|--------|------------|--------------|
| Source Text | TXT | ~50 KB | ~500 KB |
| Source Text | PDF | ~100 KB | ~800 KB |
| Translation | TXT | ~80 KB | ~800 KB |
| Translation | PDF | ~150 KB | ~1.2 MB |
| Interlinear | TXT | ~120 KB | ~1.2 MB |
| Interlinear | PDF | ~200 KB | ~1.8 MB |

### Error Handling

1. **Invalid line range**: Clamp to valid range (1 to totalLines)
2. **No content**: Show error if selected range has no text
3. **File write failure**: Show error with retry option
4. **Out of memory**: Stream large exports, don't load all at once

### Performance

- Use Kotlin coroutines for background processing
- Stream content to file (don't buffer entire document in memory)
- Show progress indicator for exports > 1000 lines
- Cancel support for long exports

## Testing Checklist

- [ ] Export Greek source text to TXT
- [ ] Export Greek source text to PDF (verify Greek renders correctly)
- [ ] Export Latin source text to TXT
- [ ] Export Latin source text to PDF
- [ ] Export English translation to TXT
- [ ] Export English translation to PDF
- [ ] Export interlinear view to TXT
- [ ] Export interlinear view to PDF
- [ ] Export entire book (large file)
- [ ] Export custom line range
- [ ] Verify line range validation (start > end, out of bounds)
- [ ] Test file picker cancellation
- [ ] Test "Open" action after export
- [ ] Verify speaker labels included for dramatic texts
- [ ] Test with color inversion mode (dialog should respect theme)
- [ ] Test export while offline (should work, no network needed)

---

# iOS Implementation

## Overview

The iOS app uses **SwiftUI** with **MVVM** architecture. The text viewer is `ReaderView.swift` with `ReaderViewModel`. Export follows the existing bookmark CSV export pattern using SwiftUI's `.fileExporter()` modifier.

## iOS User Flow

```
User taps ••• menu in toolbar
         │
         ▼
┌─────────────────────────────┐
│   Menu                      │
│   ├── Export Current Page   │
│   ├── Export Custom Range   │
│   └── Export Entire Book    │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Export Options Sheet      │
│                             │
│   Format:  [TXT] [PDF]      │
│                             │
│   Range: 1 - 2847           │
│   (editable for custom)     │
│                             │
│   [Cancel]        [Export]  │
└─────────────────────────────┘
         │
         ▼
    iOS Share Sheet / File Picker
         │
         ▼
    Success banner
```

## iOS Architecture

### Data Flow
```
ReaderView → ReaderViewModel → LineDAO/TranslationDAO → DatabaseManagerAsync → SQLite
```

### Key Models (from `DatabaseModels.swift`)
```swift
struct TextLine: Identifiable {
    let id: Int
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int
    let lineText: String
    let lineXml: String?
    let speaker: String?
}

struct TranslationSegment: Identifiable {
    let id: Int
    let bookId: String
    let startLine: Int
    let endLine: Int?
    let translationText: String
    let translator: String?
    let speaker: String?
}
```

## iOS Files to Create

### 1. `ios/ClassicsViewer/Utilities/TextExporter.swift`

```swift
import Foundation
import PDFKit
import UIKit

enum ExportFormat {
    case txt
    case pdf
}

enum ExportContentType {
    case source
    case translation
    case interlinear
}

struct ExportRequest {
    let format: ExportFormat
    let contentType: ExportContentType
    let authorName: String
    let workTitle: String
    let bookLabel: String
    let startLine: Int
    let endLine: Int
    let translator: String?
}

class TextExporter {

    // MARK: - TXT Export

    static func generateTxtContent(
        request: ExportRequest,
        lines: [TextLine]? = nil,
        translations: [TranslationSegment]? = nil,
        interlinearData: [InterlinearLine]? = nil
    ) -> String {
        var content = ""

        // Header
        content += "\(request.authorName) - \(request.workTitle)\n"
        content += "\(request.bookLabel), Lines \(request.startLine)-\(request.endLine)\n"
        if let translator = request.translator {
            content += "Translation by \(translator)\n"
        }
        if request.contentType == .interlinear {
            content += "(Interlinear)\n"
        }
        content += "Exported from Classics Viewer\n\n"

        // Content
        switch request.contentType {
        case .source:
            if let lines = lines {
                for line in lines {
                    let lineNum = String(line.lineNumber).padding(toLength: 5, withPad: " ", startingAt: 0)
                    let speaker = line.speaker.map { "[\($0)] " } ?? ""
                    content += "\(lineNum)  \(speaker)\(line.lineText)\n"
                }
            }

        case .translation:
            if let translations = translations {
                for segment in translations {
                    let range: String
                    if let endLine = segment.endLine, endLine != segment.startLine {
                        range = "[\(segment.startLine)-\(endLine)]"
                    } else {
                        range = "[\(segment.startLine)]"
                    }
                    let speaker = segment.speaker.map { "[\($0)] " } ?? ""
                    content += "\(range) \(speaker)\(segment.translationText)\n\n"
                }
            }

        case .interlinear:
            if let data = interlinearData {
                for line in data {
                    let lineNum = String(line.lineNumber).padding(toLength: 5, withPad: " ", startingAt: 0)
                    content += "\(lineNum)  \(line.sourceWords.joined(separator: "  "))\n"
                    content += "       \(line.glossWords.joined(separator: "  "))\n\n"
                }
            }
        }

        return content
    }

    // MARK: - PDF Export

    static func generatePdf(
        request: ExportRequest,
        lines: [TextLine]? = nil,
        translations: [TranslationSegment]? = nil,
        interlinearData: [InterlinearLine]? = nil
    ) -> Data? {
        let pageWidth: CGFloat = 595  // A4
        let pageHeight: CGFloat = 842
        let margin: CGFloat = 50
        let contentWidth = pageWidth - (margin * 2)

        let pdfMetaData = [
            kCGPDFContextCreator: "Classics Viewer",
            kCGPDFContextAuthor: request.authorName,
            kCGPDFContextTitle: "\(request.workTitle) - \(request.bookLabel)"
        ]

        let format = UIGraphicsPDFRendererFormat()
        format.documentInfo = pdfMetaData as [String: Any]

        let renderer = UIGraphicsPDFRenderer(
            bounds: CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight),
            format: format
        )

        let titleFont = UIFont(name: "NotoSerif-Bold", size: 18) ?? UIFont.boldSystemFont(ofSize: 18)
        let bodyFont = UIFont(name: "NotoSerif-Regular", size: 12) ?? UIFont.systemFont(ofSize: 12)
        let smallFont = UIFont(name: "NotoSerif-Regular", size: 10) ?? UIFont.systemFont(ofSize: 10)

        let titleAttributes: [NSAttributedString.Key: Any] = [
            .font: titleFont,
            .foregroundColor: UIColor.black
        ]

        let bodyAttributes: [NSAttributedString.Key: Any] = [
            .font: bodyFont,
            .foregroundColor: UIColor.black
        ]

        let data = renderer.pdfData { context in
            var yPosition: CGFloat = margin

            func startNewPage() {
                context.beginPage()
                yPosition = margin
            }

            func ensureSpace(_ needed: CGFloat) {
                if yPosition + needed > pageHeight - margin {
                    startNewPage()
                }
            }

            func drawText(_ text: String, attributes: [NSAttributedString.Key: Any], maxWidth: CGFloat) -> CGFloat {
                let attributedString = NSAttributedString(string: text, attributes: attributes)
                let textRect = CGRect(x: margin, y: yPosition, width: maxWidth, height: .greatestFiniteMagnitude)
                let boundingRect = attributedString.boundingRect(with: CGSize(width: maxWidth, height: .greatestFiniteMagnitude),
                                                                  options: [.usesLineFragmentOrigin, .usesFontLeading],
                                                                  context: nil)
                ensureSpace(boundingRect.height)
                attributedString.draw(in: CGRect(x: margin, y: yPosition, width: maxWidth, height: boundingRect.height))
                return boundingRect.height
            }

            startNewPage()

            // Title
            yPosition += drawText("\(request.authorName) - \(request.workTitle)", attributes: titleAttributes, maxWidth: contentWidth)
            yPosition += 8

            // Subtitle
            var subtitle = "\(request.bookLabel), Lines \(request.startLine)-\(request.endLine)"
            if let translator = request.translator {
                subtitle += "\nTranslation by \(translator)"
            }
            yPosition += drawText(subtitle, attributes: bodyAttributes, maxWidth: contentWidth)
            yPosition += 24

            // Content
            switch request.contentType {
            case .source:
                lines?.forEach { line in
                    let lineNum = String(format: "%5d", line.lineNumber)
                    let speaker = line.speaker.map { "[\($0)] " } ?? ""
                    let text = "\(lineNum)  \(speaker)\(line.lineText)"
                    yPosition += drawText(text, attributes: bodyAttributes, maxWidth: contentWidth)
                    yPosition += 4
                }

            case .translation:
                translations?.forEach { segment in
                    let range = segment.endLine != nil && segment.endLine != segment.startLine
                        ? "[\(segment.startLine)-\(segment.endLine!)]"
                        : "[\(segment.startLine)]"
                    let speaker = segment.speaker.map { "[\($0)] " } ?? ""
                    let text = "\(range) \(speaker)\(segment.translationText)"
                    yPosition += drawText(text, attributes: bodyAttributes, maxWidth: contentWidth)
                    yPosition += 12
                }

            case .interlinear:
                interlinearData?.forEach { line in
                    let lineNum = String(format: "%5d", line.lineNumber)
                    yPosition += drawText("\(lineNum)  \(line.sourceWords.joined(separator: "  "))", attributes: bodyAttributes, maxWidth: contentWidth)
                    yPosition += drawText("       \(line.glossWords.joined(separator: "  "))", attributes: [.font: smallFont, .foregroundColor: UIColor.darkGray], maxWidth: contentWidth)
                    yPosition += 8
                }
            }
        }

        return data
    }
}
```

### 2. `ios/ClassicsViewer/Utilities/ExportDocument.swift`

```swift
import SwiftUI
import UniformTypeIdentifiers

// TXT Document for file export
struct TxtDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.plainText] }

    var content: String

    init(content: String) {
        self.content = content
    }

    init(configuration: ReadConfiguration) throws {
        if let data = configuration.file.regularFileContents {
            content = String(data: data, encoding: .utf8) ?? ""
        } else {
            content = ""
        }
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        let data = content.data(using: .utf8) ?? Data()
        return FileWrapper(regularFileWithContents: data)
    }
}

// PDF Document for file export
struct PdfDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.pdf] }

    var data: Data

    init(data: Data) {
        self.data = data
    }

    init(configuration: ReadConfiguration) throws {
        data = configuration.file.regularFileContents ?? Data()
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}
```

### 3. `ios/ClassicsViewer/Views/ExportOptionsView.swift`

```swift
import SwiftUI

struct ExportOptionsView: View {
    @Environment(\.dismiss) private var dismiss

    let authorName: String
    let workTitle: String
    let bookLabel: String
    let totalLines: Int
    let contentType: ExportContentType
    let translator: String?
    let onExport: (ExportFormat, Int, Int) -> Void

    @State private var selectedFormat: ExportFormat = .txt
    @State private var startLine: Int
    @State private var endLine: Int
    @State private var useEntireBook: Bool

    init(
        authorName: String,
        workTitle: String,
        bookLabel: String,
        totalLines: Int,
        currentStartLine: Int,
        currentEndLine: Int,
        contentType: ExportContentType,
        translator: String?,
        entireBook: Bool = false,
        onExport: @escaping (ExportFormat, Int, Int) -> Void
    ) {
        self.authorName = authorName
        self.workTitle = workTitle
        self.bookLabel = bookLabel
        self.totalLines = totalLines
        self.contentType = contentType
        self.translator = translator
        self.onExport = onExport

        _startLine = State(initialValue: entireBook ? 1 : currentStartLine)
        _endLine = State(initialValue: entireBook ? totalLines : currentEndLine)
        _useEntireBook = State(initialValue: entireBook)
    }

    var body: some View {
        NavigationView {
            Form {
                // Format Selection
                Section("Format") {
                    Picker("Format", selection: $selectedFormat) {
                        Text("TXT").tag(ExportFormat.txt)
                        Text("PDF").tag(ExportFormat.pdf)
                    }
                    .pickerStyle(.segmented)
                }

                // Range Selection
                Section("Line Range") {
                    Toggle("Entire Book (1-\(totalLines))", isOn: $useEntireBook)
                        .onChange(of: useEntireBook) { newValue in
                            if newValue {
                                startLine = 1
                                endLine = totalLines
                            }
                        }

                    if !useEntireBook {
                        HStack {
                            Text("From")
                            TextField("Start", value: $startLine, format: .number)
                                .textFieldStyle(.roundedBorder)
                                .keyboardType(.numberPad)
                                .frame(width: 80)

                            Text("to")

                            TextField("End", value: $endLine, format: .number)
                                .textFieldStyle(.roundedBorder)
                                .keyboardType(.numberPad)
                                .frame(width: 80)
                        }
                    }
                }

                // Preview Info
                Section("Export Preview") {
                    LabeledContent("Author", value: authorName)
                    LabeledContent("Work", value: workTitle)
                    LabeledContent("Book", value: bookLabel)
                    LabeledContent("Lines", value: "\(startLine)-\(endLine) (\(endLine - startLine + 1) lines)")
                    if let translator = translator {
                        LabeledContent("Translator", value: translator)
                    }
                    LabeledContent("Content", value: contentTypeLabel)
                }
            }
            .navigationTitle("Export")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Export") {
                        let validStart = max(1, min(startLine, totalLines))
                        let validEnd = max(validStart, min(endLine, totalLines))
                        onExport(selectedFormat, validStart, validEnd)
                        dismiss()
                    }
                }
            }
        }
    }

    private var contentTypeLabel: String {
        switch contentType {
        case .source: return "Source Text"
        case .translation: return "Translation"
        case .interlinear: return "Interlinear"
        }
    }
}
```

## iOS Files to Modify

### 1. `ios/ClassicsViewer/Views/ReaderView.swift`

Add state variables near other `@State` declarations (~line 30):
```swift
// Export state
@State private var showingExportOptions = false
@State private var exportEntireBook = false
@State private var showingTxtExporter = false
@State private var showingPdfExporter = false
@State private var txtDocument: TxtDocument?
@State private var pdfDocument: PdfDocument?
@State private var exportFilename = ""
```

Add menu button to toolbar (in `.toolbar` modifier):
```swift
ToolbarItemGroup(placement: .navigationBarTrailing) {
    // Existing buttons...

    Menu {
        Button(action: { showExportCurrentPage() }) {
            Label("Export Current Page", systemImage: "doc.text")
        }
        Button(action: { showExportCustomRange() }) {
            Label("Export Custom Range...", systemImage: "doc.badge.ellipsis")
        }
        Button(action: { showExportEntireBook() }) {
            Label("Export Entire Book", systemImage: "doc.on.doc")
        }
    } label: {
        Image(systemName: "square.and.arrow.up")
    }
}
```

Add sheet modifiers (after existing `.sheet` modifiers):
```swift
.sheet(isPresented: $showingExportOptions) {
    ExportOptionsView(
        authorName: viewModel.author?.name ?? "Unknown",
        workTitle: viewModel.work?.title ?? "Unknown",
        bookLabel: viewModel.book?.label ?? "Book",
        totalLines: viewModel.totalLines,
        currentStartLine: viewModel.currentStartLine,
        currentEndLine: viewModel.currentEndLine,
        contentType: currentExportContentType,
        translator: currentTranslator,
        entireBook: exportEntireBook,
        onExport: performExport
    )
}
.fileExporter(
    isPresented: $showingTxtExporter,
    document: txtDocument,
    contentType: .plainText,
    defaultFilename: exportFilename
) { result in
    handleExportResult(result)
}
.fileExporter(
    isPresented: $showingPdfExporter,
    document: pdfDocument,
    contentType: .pdf,
    defaultFilename: exportFilename
) { result in
    handleExportResult(result)
}
```

Add export methods:
```swift
// MARK: - Export Methods

private var currentExportContentType: ExportContentType {
    if viewModel.showInterlinear {
        return .interlinear
    } else if viewModel.currentTranslatorIndex > 0 {
        return .translation
    } else {
        return .source
    }
}

private var currentTranslator: String? {
    guard viewModel.currentTranslatorIndex > 0 else { return nil }
    let translators = viewModel.availableTranslators
    let index = viewModel.currentTranslatorIndex - 1
    return index < translators.count ? translators[index] : nil
}

private func showExportCurrentPage() {
    exportEntireBook = false
    showingExportOptions = true
}

private func showExportCustomRange() {
    exportEntireBook = false
    showingExportOptions = true
}

private func showExportEntireBook() {
    exportEntireBook = true
    showingExportOptions = true
}

private func performExport(format: ExportFormat, startLine: Int, endLine: Int) {
    Task {
        let request = ExportRequest(
            format: format,
            contentType: currentExportContentType,
            authorName: viewModel.author?.name ?? "Unknown",
            workTitle: viewModel.work?.title ?? "Unknown",
            bookLabel: viewModel.book?.label ?? "Book",
            startLine: startLine,
            endLine: endLine,
            translator: currentTranslator
        )

        // Fetch data based on content type
        let lines: [TextLine]?
        let translations: [TranslationSegment]?
        let interlinear: [InterlinearLine]?

        switch request.contentType {
        case .source:
            lines = try? await viewModel.getLines(startLine: startLine, endLine: endLine)
            translations = nil
            interlinear = nil

        case .translation:
            lines = nil
            translations = try? await viewModel.getTranslations(
                translator: request.translator!,
                startLine: startLine,
                endLine: endLine
            )
            interlinear = nil

        case .interlinear:
            lines = try? await viewModel.getLines(startLine: startLine, endLine: endLine)
            translations = nil
            interlinear = try? await viewModel.getInterlinearData(startLine: startLine, endLine: endLine)
        }

        // Generate filename
        let sanitizedTitle = request.workTitle.replacingOccurrences(of: "[^a-zA-Z0-9]", with: "_", options: .regularExpression)
        let ext = format == .txt ? "txt" : "pdf"
        exportFilename = "\(sanitizedTitle)_\(request.bookLabel)_\(startLine)-\(endLine).\(ext)"

        await MainActor.run {
            switch format {
            case .txt:
                let content = TextExporter.generateTxtContent(
                    request: request,
                    lines: lines,
                    translations: translations,
                    interlinearData: interlinear
                )
                txtDocument = TxtDocument(content: content)
                showingTxtExporter = true

            case .pdf:
                if let data = TextExporter.generatePdf(
                    request: request,
                    lines: lines,
                    translations: translations,
                    interlinearData: interlinear
                ) {
                    pdfDocument = PdfDocument(data: data)
                    showingPdfExporter = true
                }
            }
        }
    }
}

private func handleExportResult(_ result: Result<URL, Error>) {
    switch result {
    case .success(let url):
        print("Exported to: \(url)")
        // Could show a success banner here
    case .failure(let error):
        print("Export failed: \(error.localizedDescription)")
        // Could show an error alert here
    }
}
```

### 2. `ios/ClassicsViewer/ViewModels/ReaderViewModel.swift`

Add methods to fetch data for export (if not already available):
```swift
// MARK: - Export Data Access

func getLines(startLine: Int, endLine: Int) async throws -> [TextLine] {
    guard let bookId = book?.id else { return [] }
    return try await LineDAO.shared.getLines(bookId: bookId, startLine: startLine, endLine: endLine)
}

func getTranslations(translator: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment] {
    guard let bookId = book?.id else { return [] }
    return try await TranslationDAO.shared.getSegmentsByTranslator(
        bookId: bookId,
        translator: translator,
        startLine: startLine,
        endLine: endLine
    )
}

func getInterlinearData(startLine: Int, endLine: Int) async throws -> [InterlinearLine] {
    guard let bookId = book?.id else { return [] }
    return try await InterlinearDAO.shared.getLines(bookId: bookId, startLine: startLine, endLine: endLine)
}
```

## iOS Technical Considerations

### Font Support

iOS has excellent Unicode support. For PDF generation:
- System fonts support Greek/Latin out of the box
- For consistency, bundle Noto Serif font in the app
- Add to `Info.plist` under `UIAppFonts` if bundling custom fonts

### File Export Options

iOS provides two approaches:

1. **`.fileExporter()` modifier** (recommended)
   - Native SwiftUI integration
   - User chooses save location
   - Works with Files app, iCloud, etc.

2. **`UIActivityViewController`** (share sheet)
   - More flexible sharing options
   - Can share to other apps, AirDrop, etc.
   - Good for "share" vs "save" distinction

### Memory Considerations

For large exports (10,000+ lines):
- Stream data to file if possible
- Show activity indicator during generation
- Consider chunking PDF page generation

## iOS Testing Checklist

- [ ] Export Greek source text to TXT
- [ ] Export Greek source text to PDF
- [ ] Export Latin source text to TXT
- [ ] Export Latin source text to PDF
- [ ] Export English translation to TXT
- [ ] Export English translation to PDF
- [ ] Export interlinear view to TXT
- [ ] Export interlinear view to PDF
- [ ] Export entire book (large file)
- [ ] Export custom line range
- [ ] Line range validation (start > end, out of bounds)
- [ ] Cancel file picker
- [ ] Save to Files app
- [ ] Save to iCloud Drive
- [ ] Share via AirDrop
- [ ] Verify Greek characters render in PDF
- [ ] Test on iPad (larger screen layout)
- [ ] Test Dark Mode (dialog appearance)

---

## Future Enhancements

1. **Share directly**: Add share option in addition to save
2. **Multiple formats**: EPUB, HTML export
3. **Side-by-side export**: Greek + translation in parallel columns (PDF only)
4. **Bookmarked sections**: Export all bookmarked passages
5. **Custom formatting**: Font size, margins in PDF
6. **Batch export**: Export multiple books at once
