package com.classicsviewer.app

import android.graphics.Typeface
import android.text.Html
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTranslationSegmentBinding
import com.classicsviewer.app.fragments.TranslationDisplayItem
import com.classicsviewer.app.utils.PreferencesManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder

/**
 * Tree data from sentence-aware dependency parsing.
 * Parsed from morph field format: "lemma morph ~ POS deprel head sentPos"
 */
private data class TreeData(
    val pos: String,      // UPOS tag (NOUN, VERB, ADJ, etc.)
    val deprel: String,   // Universal Dependencies relation (nsubj, obj, etc.)
    val head: Int,        // Sentence position of head word (0 = ROOT)
    val sentPos: Int      // This word's position in the full sentence
)

/**
 * Parse enhanced morph format: "lemma morph ~ POS deprel head sentPos"
 * Returns the display part (before ~) and optional tree data (after ~)
 */
private fun parseEnhancedMorph(morphField: String): Pair<String, TreeData?> {
    if (!morphField.contains(" ~ ")) {
        return Pair(morphField, null)  // Backward compatible
    }

    val parts = morphField.split(" ~ ")
    val displayMorph = parts[0].trim()

    if (parts.size < 2) {
        return Pair(displayMorph, null)
    }

    val treeParts = parts[1].trim().split(" ")
    if (treeParts.size < 3) {
        return Pair(displayMorph, null)
    }

    val treeData = TreeData(
        pos = treeParts[0],
        deprel = treeParts[1],
        head = treeParts[2].toIntOrNull() ?: 0,
        sentPos = treeParts.getOrNull(3)?.toIntOrNull() ?: 0
    )

    return Pair(displayMorph, treeData)
}

class TranslationAdapter(
    val items: List<TranslationDisplayItem>,
    private val invertColors: Boolean = false,
    private val onWordClick: ((String) -> Unit)? = null
) : RecyclerView.Adapter<TranslationAdapter.ViewHolder>() {
    
    // Maintain private reference for internal use
    private val segments: List<TranslationDisplayItem> = items
    
    class ViewHolder(val binding: ItemTranslationSegmentBinding) : RecyclerView.ViewHolder(binding.root)
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTranslationSegmentBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val segment = segments[position]
        
        // Apply saved font size
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.translationText.textSize = fontSize
        holder.binding.speakerName.textSize = fontSize * 1.5f
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.translationText.setTextColor(0xFF000000.toInt())
            holder.binding.lineRange.setTextColor(0xFF666666.toInt())
            holder.binding.translatorName.setTextColor(0xFF666666.toInt())
            holder.binding.speakerName.setTextColor(0xFF0066CC.toInt()) // Blue for speakers
        } else {
            // White on black (default)
            holder.binding.translationText.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.lineRange.setTextColor(0xFF999999.toInt())
            holder.binding.translatorName.setTextColor(0xFF999999.toInt())
            holder.binding.speakerName.setTextColor(0xFF66B2FF.toInt()) // Light blue for speakers
        }
        
        // Show line range
        val rangeText = if (segment.startLine == segment.endLine) {
            "Line ${segment.startLine}"
        } else {
            "Lines ${segment.startLine}-${segment.endLine}"
        }
        holder.binding.lineRange.text = rangeText
        
        // Show speaker if available and different from previous speaker
        val shouldShowSpeaker = !segment.speaker.isNullOrBlank() && 
                                (position == 0 || segments[position - 1].speaker != segment.speaker)
        
        if (shouldShowSpeaker) {
            holder.binding.speakerName.visibility = View.VISIBLE
            holder.binding.speakerName.text = segment.speaker
        } else {
            holder.binding.speakerName.visibility = View.GONE
        }
        
        // Show translation text
        // Check for interlinear format (contains Markdown tables with pipe syntax)
        // Only process as interlinear if translator is "Interlinear" to avoid processing other translations
        if (segment.text.contains("| ") && segment.translator?.contains("Interlinear") == true) {
            // This is interlinear format with Markdown tables
            // Hide TextView
            holder.binding.translationText.visibility = View.GONE

            // Check wrap preference
            val wrapEnabled = PreferencesManager.getWrapInterlinear(holder.itemView.context)

            // Parse Markdown tables once for both modes
            val tables = parseMarkdownTables(segment.text)

            if (wrapEnabled) {
                // Use wrapping container
                holder.binding.interlinearScrollView.visibility = View.GONE
                holder.binding.interlinearWrapContainer.visibility = View.VISIBLE
                holder.binding.interlinearWrapContainer.removeAllViews()

                // Create views for each word, passing all words for tree building
                tables.forEachIndexed { idx, rows ->
                    val table = createWordTable(rows, fontSize, invertColors, holder.itemView.context, tables, idx, position)
                    holder.binding.interlinearWrapContainer.addView(table)
                }
            } else {
                // Use horizontal scrolling container
                holder.binding.interlinearScrollView.visibility = View.VISIBLE
                holder.binding.interlinearWrapContainer.visibility = View.GONE
                holder.binding.interlinearContainer.removeAllViews()

                // Create views for each word, passing all words for tree building
                tables.forEachIndexed { idx, rows ->
                    val table = createWordTable(rows, fontSize, invertColors, holder.itemView.context, tables, idx, position)
                    holder.binding.interlinearContainer.addView(table)
                }
            }
        } else {
            // Regular translation text
            holder.binding.translationText.visibility = View.VISIBLE
            holder.binding.interlinearScrollView.visibility = View.GONE
            holder.binding.interlinearWrapContainer.visibility = View.GONE

            holder.binding.translationText.text = if (segment.text.contains("<")) {
                // Allow specific HTML tags: <hi rend="bold">, <b>
                val sanitized = segment.text
                    .replace("<hi rend=\"bold\">", "<b>")
                    .replace("</hi>", "</b>")
                Html.fromHtml(sanitized, Html.FROM_HTML_MODE_LEGACY)
            } else {
                segment.text  // Plain text if no formatting
            }
        }

        // Show translator if available
        if (!segment.translator.isNullOrBlank()) {
            holder.binding.translatorName.visibility = View.VISIBLE
            holder.binding.translatorName.text = "— ${segment.translator}"
        } else {
            holder.binding.translatorName.visibility = View.GONE
        }
    }
    
    override fun getItemCount() = segments.size

    /**
     * Parse Markdown table structure
     * Expected format: | greek |\n| **gloss** |\n| lemma morph |  (separated by double space for next word)
     * Only supports tables and bold (**text**) - no other Markdown syntax
     */
    private fun parseMarkdownTables(markdown: String): List<List<String>> {
        val tables = mutableListOf<List<String>>()

        // Split by double space to get individual word tables
        val wordTables = markdown.split("  ")

        for (wordTable in wordTables) {
            val rows = mutableListOf<String>()

            // Split by newline to get individual rows
            val lines = wordTable.trim().split("\n")

            for (line in lines) {
                // Extract content between pipes: | content |
                val match = Regex("""\|\s*(.*?)\s*\|""").find(line.trim())
                if (match != null) {
                    var content = match.groupValues[1].trim()

                    // Handle bold: **text** -> text (we'll apply bold styling in createWordTable)
                    // Only allow bold, nothing else
                    content = content.replace(Regex("""\*\*(.*?)\*\*"""), "$1")

                    rows.add(content)
                }
            }

            if (rows.size == 3) {  // Only add if we have exactly 3 rows (greek, gloss, morph)
                tables.add(rows)
            }
        }

        return tables
    }

    /**
     * Create a TableLayout view for a single word's interlinear data
     * rows[0] = Greek word
     * rows[1] = English gloss (bold)
     * rows[2] = lemma + morphology (may contain tree data after " ~ ")
     *
     * @param allWordsInLine All words in the line (for tree building)
     * @param wordIndex Index of this word in the line (0-based)
     * @param segmentPosition Position of this segment in the adapter (for finding adjacent segments)
     */
    private fun createWordTable(
        rows: List<String>,
        fontSize: Float,
        invertColors: Boolean,
        context: android.content.Context,
        allWordsInLine: List<List<String>>? = null,
        wordIndex: Int = 0,
        segmentPosition: Int = 0
    ): TableLayout {
        return TableLayout(context).apply {
            layoutParams = ViewGroup.MarginLayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                marginEnd = 16 // Space between word tables
            }

            // Add each row
            rows.forEachIndexed { index, text ->
                val row = TableRow(context).apply {
                    layoutParams = TableLayout.LayoutParams(
                        TableLayout.LayoutParams.WRAP_CONTENT,
                        TableLayout.LayoutParams.WRAP_CONTENT
                    )
                }

                val cell = TextView(context).apply {
                    // For morph row, parse out tree data
                    val displayText = if (index == 2) {
                        val (display, _) = parseEnhancedMorph(text)
                        display
                    } else {
                        text
                    }

                    this.text = displayText
                    this.textSize = when (index) {
                        0 -> fontSize * 1.1f  // Greek word - slightly larger
                        1 -> fontSize * 0.9f  // English gloss
                        else -> fontSize * 0.8f  // Morphology - smaller
                    }
                    this.gravity = Gravity.CENTER
                    setPadding(8, 4, 8, 4)

                    // Apply styling based on row
                    when (index) {
                        0 -> {
                            // Greek word - make clickable for dictionary
                            isClickable = true
                            isFocusable = true
                            setOnClickListener {
                                onWordClick?.invoke(text)
                            }
                        }
                        1 -> {
                            // English gloss - bold
                            setTypeface(null, Typeface.BOLD)
                        }
                        2 -> {
                            // Morphology - italic, clickable if tree data exists
                            setTypeface(null, Typeface.ITALIC)

                            val (_, treeData) = parseEnhancedMorph(text)
                            if (treeData != null && allWordsInLine != null) {
                                isClickable = true
                                isFocusable = true
                                setOnClickListener {
                                    showSentenceTreePopup(context, segmentPosition, treeData.sentPos, invertColors)
                                }
                            }
                        }
                    }

                    // Apply colors
                    if (invertColors) {
                        setTextColor(when (index) {
                            0 -> 0xFF000000.toInt()  // Greek - black
                            1 -> 0xFF000000.toInt()  // Gloss - black
                            else -> 0xFF666666.toInt()  // Morph - gray
                        })
                        setBackgroundColor(0xFFFFFFFF.toInt())
                    } else {
                        setTextColor(when (index) {
                            0 -> 0xFFFFFFFF.toInt()  // Greek - white
                            1 -> 0xFFFFFFFF.toInt()  // Gloss - white
                            else -> 0xFF999999.toInt()  // Morph - light gray
                        })
                        setBackgroundColor(0xFF000000.toInt())
                    }
                }

                row.addView(cell)
                addView(row)
            }

            // Add border around table
            if (invertColors) {
                setBackgroundColor(0xFFEEEEEE.toInt())
            } else {
                setBackgroundColor(0xFF222222.toInt())
            }
            setPadding(4, 4, 4, 4)
        }
    }

    /**
     * Launch full-screen activity to display sentence dependency tree structure.
     * Gathers words from all adjacent segments that are part of the same sentence.
     */
    private fun showSentenceTreePopup(
        context: android.content.Context,
        segmentPosition: Int,
        clickedWordSentPos: Int,
        invertColors: Boolean
    ) {
        // Gather all words from segments that form this sentence
        val allSentenceWords = gatherSentenceWords(segmentPosition)

        // Build tree structure from all sentence words
        val treeText = buildDependencyTree(allSentenceWords, clickedWordSentPos)

        // Launch full-screen activity
        val intent = android.content.Intent(context, SentenceTreeActivity::class.java).apply {
            putExtra(SentenceTreeActivity.EXTRA_TREE_TEXT, treeText)
            putExtra(SentenceTreeActivity.EXTRA_INVERT_COLORS, invertColors)
        }
        context.startActivity(intent)
    }

    /**
     * Gather all words from segments that form a complete sentence.
     * Expands backward and forward from the current segment until sentence boundaries are found.
     * Sentence boundaries are detected by gaps in sentPos numbering (new sentence starts at 1).
     *
     * Note: Segments alternate between English translations and Interlinear, so we must
     * skip non-interlinear segments when expanding.
     */
    private fun gatherSentenceWords(startSegmentPos: Int): List<List<String>> {
        val allWords = mutableListOf<List<String>>()
        val seenSentPositions = mutableSetOf<Int>()

        // Helper to check if a segment is interlinear
        fun isInterlinear(segmentPos: Int): Boolean {
            if (segmentPos < 0 || segmentPos >= segments.size) return false
            return segments[segmentPos].translator?.contains("Interlinear") == true
        }

        // Helper to parse words from a segment and extract tree data
        fun getWordsWithTreeData(segmentPos: Int): List<Triple<List<String>, Int, Int>> {
            if (!isInterlinear(segmentPos)) return emptyList()

            val tables = parseMarkdownTables(segments[segmentPos].text)
            val result = mutableListOf<Triple<List<String>, Int, Int>>()

            tables.forEach { rows ->
                if (rows.size >= 3) {
                    val (_, treeData) = parseEnhancedMorph(rows[2])
                    if (treeData != null && treeData.sentPos > 0) {
                        result.add(Triple(rows, treeData.sentPos, treeData.head))
                    }
                }
            }
            return result
        }

        // Start with current segment
        val currentWords = getWordsWithTreeData(startSegmentPos)
        if (currentWords.isEmpty()) return emptyList()

        // Add current segment words
        currentWords.forEach { (rows, sentPos, _) ->
            seenSentPositions.add(sentPos)
            allWords.add(rows)
        }

        val currentMinPos = currentWords.minOfOrNull { it.second } ?: 1
        val currentMaxPos = currentWords.maxOfOrNull { it.second } ?: 1

        // Expand backward to find sentence start (sentPos = 1)
        var prevSegment = startSegmentPos - 1
        var expectedMinPos = currentMinPos
        while (prevSegment >= 0 && expectedMinPos > 1) {
            // Skip non-interlinear segments
            if (!isInterlinear(prevSegment)) {
                prevSegment--
                continue
            }

            val prevWords = getWordsWithTreeData(prevSegment)
            if (prevWords.isEmpty()) {
                prevSegment--
                continue
            }

            val prevMaxPos = prevWords.maxOfOrNull { it.second } ?: 0
            val prevMinPos = prevWords.minOfOrNull { it.second } ?: 0

            // Check for sentence boundary: if prev segment has sentPos that doesn't connect
            if (prevMaxPos < expectedMinPos - 1 || prevMinPos > expectedMinPos) {
                break
            }

            // Add words from previous segment
            prevWords.forEach { (rows, sentPos, _) ->
                if (!seenSentPositions.contains(sentPos)) {
                    seenSentPositions.add(sentPos)
                    allWords.add(rows)
                }
            }
            expectedMinPos = prevMinPos
            prevSegment--
        }

        // Expand forward to find sentence end
        var nextSegment = startSegmentPos + 1
        var expectedMaxPos = currentMaxPos
        while (nextSegment < segments.size) {
            // Skip non-interlinear segments
            if (!isInterlinear(nextSegment)) {
                nextSegment++
                continue
            }

            val nextWords = getWordsWithTreeData(nextSegment)
            if (nextWords.isEmpty()) {
                nextSegment++
                continue
            }

            val nextMinPos = nextWords.minOfOrNull { it.second } ?: 0
            val nextMaxPos = nextWords.maxOfOrNull { it.second } ?: 0

            // Check for sentence boundary: if next segment starts at 1 or has a gap
            if (nextMinPos == 1 || nextMinPos > expectedMaxPos + 1) {
                break
            }

            // Add words from next segment
            nextWords.forEach { (rows, sentPos, _) ->
                if (!seenSentPositions.contains(sentPos)) {
                    seenSentPositions.add(sentPos)
                    allWords.add(rows)
                }
            }
            expectedMaxPos = nextMaxPos
            nextSegment++
        }

        // Sort by sentence position
        return allWords.sortedBy { rows ->
            if (rows.size >= 3) {
                val (_, treeData) = parseEnhancedMorph(rows[2])
                treeData?.sentPos ?: 0
            } else 0
        }
    }

    /**
     * Show legend popup explaining dependency relation labels
     */
    private fun showDeprelLegendPopup(context: android.content.Context, invertColors: Boolean) {
        val legendText = """
            |Dependency Relations (deprel):
            |
            |root      = root of the sentence (main verb)
            |nsubj     = nominal subject
            |obj       = direct object
            |iobj      = indirect object
            |obl       = oblique nominal (prepositional phrases)
            |nmod      = nominal modifier (genitive, predicate nom.)
            |amod      = adjectival modifier
            |advmod    = adverbial modifier
            |appos     = appositional modifier
            |conj      = conjunct (coordinated element)
            |cc        = coordinating conjunction (καί, τε, δέ)
            |det       = determiner
            |case      = case marker (preposition)
            |mark      = subordinating conjunction
            |aux       = auxiliary verb
            |advcl     = adverbial clause modifier
            |acl       = adnominal clause (relative clause)
            |xcomp     = open clausal complement
            |ccomp     = clausal complement
            |parataxis = loosely connected clause
            |vocative  = vocative (direct address)
            |discourse = discourse particle (δή, μέν, etc.)
            |punct     = punctuation
            |dep       = unspecified dependency
            |
            |Parts of Speech (POS):
            |
            |NOUN  = noun
            |VERB  = verb
            |ADJ   = adjective
            |ADV   = adverb
            |PRON  = pronoun
            |DET   = determiner
            |ADP   = adposition (preposition)
            |CCONJ = coordinating conjunction
            |SCONJ = subordinating conjunction
            |PART  = particle
            |NUM   = numeral
            |INTJ  = interjection
            |X     = other/unknown
        """.trimMargin()

        val scrollView = ScrollView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }

        val legendView = TextView(context).apply {
            text = legendText
            textSize = 13f
            typeface = Typeface.MONOSPACE
            setPadding(32, 32, 32, 32)
            if (invertColors) {
                setTextColor(0xFF000000.toInt())
                setBackgroundColor(0xFFFFFFFF.toInt())
            } else {
                setTextColor(0xFFFFFFFF.toInt())
                setBackgroundColor(0xFF000000.toInt())
            }
        }

        scrollView.addView(legendView)

        MaterialAlertDialogBuilder(context)
            .setTitle("Legend")
            .setView(scrollView)
            .setPositiveButton("Close", null)
            .show()
    }

    /**
     * Build a text representation of the dependency tree from full sentence words
     * @param words All words in the sentence (gathered from adjacent segments)
     * @param highlightSentPos The sentence position of the clicked word (to highlight)
     */
    private fun buildDependencyTree(words: List<List<String>>, highlightSentPos: Int): String {
        // Parse tree data from each word
        data class WordNode(
            val greek: String,
            val gloss: String,
            val pos: String,
            val deprel: String,
            val head: Int,           // Sentence position of head word (0 = ROOT)
            val sentPos: Int         // This word's position in full sentence
        )

        val nodes = mutableListOf<WordNode>()
        words.forEach { rows ->
            if (rows.size >= 3) {
                val (_, treeData) = parseEnhancedMorph(rows[2])
                if (treeData != null && treeData.sentPos > 0) {
                    nodes.add(WordNode(
                        greek = rows[0],
                        gloss = rows[1],
                        pos = treeData.pos,
                        deprel = treeData.deprel,
                        head = treeData.head,
                        sentPos = treeData.sentPos
                    ))
                }
            }
        }

        if (nodes.isEmpty()) {
            return "No tree data available for this sentence."
        }

        // Build tree text
        val sb = StringBuilder()
        sb.appendLine("=".repeat(50))
        sb.appendLine("Dependency Tree (${nodes.size} words)")
        sb.appendLine("=".repeat(50))
        sb.appendLine("ROOT")

        // Recursive function to print tree nodes
        fun printNode(node: WordNode, prefix: String, isLast: Boolean) {
            val connector = if (isLast) "└── " else "├── "
            val highlight = if (node.sentPos == highlightSentPos) " ◀" else ""
            sb.appendLine("$prefix$connector[${node.sentPos}] ${node.greek}$highlight (${node.pos}, ${node.deprel})")

            val childPrefix = prefix + if (isLast) "    " else "│   "
            val children = nodes.filter { it.head == node.sentPos }
            children.forEachIndexed { i, child ->
                printNode(child, childPrefix, i == children.lastIndex)
            }
        }

        // Find root nodes (head == 0) and print tree starting from each
        val roots = nodes.filter { it.head == 0 }
        if (roots.isEmpty()) {
            sb.appendLine("└── (no root found)")
            sb.appendLine()
            sb.appendLine("Words without tree structure:")
            nodes.sortedBy { it.sentPos }.forEach { node ->
                val highlight = if (node.sentPos == highlightSentPos) " ◀" else ""
                sb.appendLine("  [${node.sentPos}] ${node.greek}$highlight → head ${node.head}")
            }
        } else {
            roots.forEachIndexed { i, root ->
                printNode(root, "", i == roots.lastIndex)
            }
        }

        sb.appendLine("=".repeat(50))
        return sb.toString()
    }
}