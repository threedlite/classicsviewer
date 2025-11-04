package com.classicsviewer.app

import android.graphics.Typeface
import android.text.Html
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTranslationSegmentBinding
import com.classicsviewer.app.fragments.TranslationDisplayItem
import com.classicsviewer.app.utils.PreferencesManager

class TranslationAdapter(
    val items: List<TranslationDisplayItem>,
    private val invertColors: Boolean = false
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
            // Hide TextView, show interlinear container
            holder.binding.translationText.visibility = View.GONE
            holder.binding.interlinearScrollView.visibility = View.VISIBLE

            // Clear previous content
            holder.binding.interlinearContainer.removeAllViews()

            // Parse Markdown tables and create views
            val tables = parseMarkdownTables(segment.text)
            tables.forEach { rows ->
                val table = createWordTable(rows, fontSize, invertColors, holder.itemView.context)
                holder.binding.interlinearContainer.addView(table)
            }
        } else {
            // Regular translation text
            holder.binding.translationText.visibility = View.VISIBLE
            holder.binding.interlinearScrollView.visibility = View.GONE

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
     * rows[2] = lemma + morphology
     */
    private fun createWordTable(rows: List<String>, fontSize: Float, invertColors: Boolean, context: android.content.Context): TableLayout {
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
                    this.text = text
                    this.textSize = when (index) {
                        0 -> fontSize * 1.1f  // Greek word - slightly larger
                        1 -> fontSize * 0.9f  // English gloss
                        else -> fontSize * 0.8f  // Morphology - smaller
                    }
                    this.gravity = Gravity.CENTER
                    setPadding(8, 4, 8, 4)

                    // Apply styling based on row
                    when (index) {
                        1 -> {
                            // English gloss - bold
                            setTypeface(null, Typeface.BOLD)
                        }
                        2 -> {
                            // Morphology - italic
                            setTypeface(null, Typeface.ITALIC)
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
}