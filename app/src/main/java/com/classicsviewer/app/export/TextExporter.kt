package com.classicsviewer.app.export

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.models.TranslationSegment
import java.io.OutputStream

enum class ExportFormat { PDF, TXT, CSV }
enum class ContentType { SOURCE, TRANSLATION }

data class ExportRequest(
    val format: ExportFormat,
    val contentType: ContentType,
    val authorName: String,
    val workTitle: String,
    val bookLabel: String,
    val workId: String,
    val startLine: Int,
    val endLine: Int,
    val translator: String? = null,
    val language: String = "greek"
)

class TextExporter(private val context: Context) {

    fun exportToTxt(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>? = null,
        translations: List<TranslationSegment>? = null
    ) {
        outputStream.bufferedWriter(Charsets.UTF_8).use { writer ->
            // Write header
            writer.appendLine("${request.authorName} - ${request.workTitle}")
            writer.appendLine("${request.bookLabel}, Lines ${request.startLine}-${request.endLine}")
            if (request.translator != null) {
                writer.appendLine("Translation by ${request.translator}")
            }
            writer.appendLine("Exported from ${request.workId}")
            writer.appendLine()

            // Write content based on type
            when (request.contentType) {
                ContentType.SOURCE -> writeSourceLines(writer, lines ?: emptyList())
                ContentType.TRANSLATION -> writeTranslation(writer, translations ?: emptyList())
            }
        }
    }

    private fun writeSourceLines(writer: java.io.BufferedWriter, lines: List<TextLine>) {
        for (line in lines) {
            val lineNum = line.lineNumber.toString().padStart(5)
            val speaker = if (!line.speaker.isNullOrEmpty()) "[${line.speaker}] " else ""
            writer.appendLine("$lineNum  $speaker${line.text}")
        }
    }

    private fun writeTranslation(writer: java.io.BufferedWriter, segments: List<TranslationSegment>) {
        for (segment in segments) {
            val range = if (segment.endLine != null && segment.endLine != segment.startLine) {
                "[${segment.startLine}-${segment.endLine}]"
            } else {
                "[${segment.startLine}]"
            }
            val speaker = if (!segment.speaker.isNullOrEmpty()) "[${segment.speaker}] " else ""
            writer.appendLine("$range $speaker${segment.translationText}")
            writer.appendLine()
        }
    }

    fun exportToCsv(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>? = null,
        translations: List<TranslationSegment>? = null
    ) {
        outputStream.bufferedWriter(Charsets.UTF_8).use { writer ->
            // CSV header
            writer.appendLine("line_number,text")

            // Write content based on type
            when (request.contentType) {
                ContentType.SOURCE -> {
                    lines?.forEach { line ->
                        val text = csvEscape(line.text)
                        writer.appendLine("${line.lineNumber},$text")
                    }
                }
                ContentType.TRANSLATION -> {
                    translations?.forEach { segment ->
                        val lineNum = if (segment.endLine != null && segment.endLine != segment.startLine) {
                            "${segment.startLine}-${segment.endLine}"
                        } else {
                            "${segment.startLine}"
                        }
                        val text = csvEscape(segment.translationText)
                        writer.appendLine("$lineNum,$text")
                    }
                }
            }
        }
    }

    private fun csvEscape(text: String): String {
        // If text contains comma, quote, or newline, wrap in quotes and escape quotes
        return if (text.contains(",") || text.contains("\"") || text.contains("\n")) {
            val escaped = text.replace("\"", "\"\"")
            "\"$escaped\""
        } else {
            text
        }
    }

    fun exportToPdf(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>? = null,
        translations: List<TranslationSegment>? = null
    ) {
        val generator = PdfGenerator(context)
        generator.generate(outputStream, request, lines, translations)
    }
}

class PdfGenerator(private val context: Context) {

    companion object {
        private const val PAGE_WIDTH = 595   // A4 width in points
        private const val PAGE_HEIGHT = 842  // A4 height in points
        private const val MARGIN = 50f
        private const val LINE_HEIGHT = 18f
        private const val TITLE_SIZE = 18f
        private const val SUBTITLE_SIZE = 12f
        private const val BODY_SIZE = 11f
    }

    private val defaultFont: Typeface = Typeface.create("serif", Typeface.NORMAL)
    private val boldFont: Typeface = Typeface.create("serif", Typeface.BOLD)

    fun generate(
        outputStream: OutputStream,
        request: ExportRequest,
        lines: List<TextLine>?,
        translations: List<TranslationSegment>?
    ) {
        val document = PdfDocument()
        var pageNumber = 1
        var yPosition = MARGIN
        var currentPage: PdfDocument.Page? = null
        var canvas: Canvas? = null

        val titlePaint = Paint().apply {
            typeface = boldFont
            textSize = TITLE_SIZE
            isAntiAlias = true
            color = 0xFF000000.toInt()
        }

        val subtitlePaint = Paint().apply {
            typeface = defaultFont
            textSize = SUBTITLE_SIZE
            isAntiAlias = true
            color = 0xFF444444.toInt()
        }

        val bodyPaint = Paint().apply {
            typeface = defaultFont
            textSize = BODY_SIZE
            isAntiAlias = true
            color = 0xFF000000.toInt()
        }

        val speakerPaint = Paint().apply {
            typeface = Typeface.create("serif", Typeface.ITALIC)
            textSize = BODY_SIZE
            isAntiAlias = true
            color = 0xFF666666.toInt()
        }

        fun startNewPage(): Canvas {
            currentPage?.let { document.finishPage(it) }
            val pageInfo = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber++).create()
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
        canvas.drawText("${request.authorName} - ${request.workTitle}", MARGIN, yPosition + TITLE_SIZE, titlePaint)
        yPosition += TITLE_SIZE + 8

        // Draw subtitle
        var subtitle = "${request.bookLabel}, Lines ${request.startLine}-${request.endLine}"
        canvas.drawText(subtitle, MARGIN, yPosition + SUBTITLE_SIZE, subtitlePaint)
        yPosition += SUBTITLE_SIZE + 4

        if (request.translator != null) {
            canvas.drawText("Translation by ${request.translator}", MARGIN, yPosition + SUBTITLE_SIZE, subtitlePaint)
            yPosition += SUBTITLE_SIZE + 4
        }

        canvas.drawText("Exported from ${request.workId}", MARGIN, yPosition + SUBTITLE_SIZE, subtitlePaint)
        yPosition += SUBTITLE_SIZE + 24  // Space before content

        // Draw content
        when (request.contentType) {
            ContentType.SOURCE -> {
                lines?.forEach { line ->
                    canvas = ensureSpace(LINE_HEIGHT)
                    val lineNum = line.lineNumber.toString().padStart(5)

                    // Draw line number
                    canvas!!.drawText(lineNum, MARGIN, yPosition + BODY_SIZE, bodyPaint)

                    // Draw speaker if present
                    var xOffset = MARGIN + 45f
                    if (!line.speaker.isNullOrEmpty()) {
                        val speakerText = "[${line.speaker}] "
                        canvas!!.drawText(speakerText, xOffset, yPosition + BODY_SIZE, speakerPaint)
                        xOffset += speakerPaint.measureText(speakerText)
                    }

                    // Draw text with word wrapping
                    val availableWidth = PAGE_WIDTH - xOffset - MARGIN
                    val wrappedLines = wrapText(line.text, bodyPaint, availableWidth)

                    wrappedLines.forEachIndexed { index, wrappedLine ->
                        if (index > 0) {
                            yPosition += LINE_HEIGHT
                            canvas = ensureSpace(LINE_HEIGHT)
                            xOffset = MARGIN + 45f
                        }
                        canvas!!.drawText(wrappedLine, xOffset, yPosition + BODY_SIZE, bodyPaint)
                    }

                    yPosition += LINE_HEIGHT
                }
            }
            ContentType.TRANSLATION -> {
                translations?.forEach { segment ->
                    val range = if (segment.endLine != null && segment.endLine != segment.startLine) {
                        "[${segment.startLine}-${segment.endLine}]"
                    } else {
                        "[${segment.startLine}]"
                    }

                    // Calculate needed height for this segment
                    val fullText = if (!segment.speaker.isNullOrEmpty()) {
                        "$range [${segment.speaker}] ${segment.translationText}"
                    } else {
                        "$range ${segment.translationText}"
                    }

                    val availableWidth = PAGE_WIDTH - (MARGIN * 2)
                    val wrappedLines = wrapText(fullText, bodyPaint, availableWidth)

                    wrappedLines.forEachIndexed { index, wrappedLine ->
                        canvas = ensureSpace(LINE_HEIGHT)
                        canvas!!.drawText(wrappedLine, MARGIN, yPosition + BODY_SIZE, bodyPaint)
                        yPosition += LINE_HEIGHT
                    }

                    yPosition += LINE_HEIGHT * 0.5f // Extra space between segments
                }
            }
        }

        currentPage?.let { document.finishPage(it) }
        document.writeTo(outputStream)
        document.close()
    }

    private fun wrapText(text: String, paint: Paint, maxWidth: Float): List<String> {
        val words = text.split(" ")
        val lines = mutableListOf<String>()
        var currentLine = StringBuilder()

        for (word in words) {
            val testLine = if (currentLine.isEmpty()) word else "${currentLine} $word"
            val testWidth = paint.measureText(testLine)

            if (testWidth > maxWidth && currentLine.isNotEmpty()) {
                lines.add(currentLine.toString())
                currentLine = StringBuilder(word)
            } else {
                currentLine = StringBuilder(testLine)
            }
        }

        if (currentLine.isNotEmpty()) {
            lines.add(currentLine.toString())
        }

        return lines.ifEmpty { listOf("") }
    }
}
