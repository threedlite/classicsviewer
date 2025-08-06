package com.classicsviewer.app

import android.graphics.Typeface
import android.text.SpannableString
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.BackgroundColorSpan
import android.text.style.StyleSpan
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemOccurrenceBinding
import com.classicsviewer.app.models.Occurrence
import com.classicsviewer.app.utils.PreferencesManager
import java.text.Normalizer

class OccurrenceAdapter(
    private val occurrences: List<Occurrence>,
    private val invertColors: Boolean = false,
    private val onOccurrenceClick: (Occurrence) -> Unit
) : RecyclerView.Adapter<OccurrenceAdapter.ViewHolder>() {
    
    class ViewHolder(val binding: ItemOccurrenceBinding) : RecyclerView.ViewHolder(binding.root)
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemOccurrenceBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val occurrence = occurrences[position]
        
        // Apply saved font size
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.lineText.textSize = fontSize
        holder.binding.referenceText.textSize = fontSize * 0.875f // Slightly smaller for reference
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.lineText.setTextColor(0xFF000000.toInt())
            holder.binding.referenceText.setTextColor(0xFF666666.toInt())
        } else {
            // White on black (default)
            holder.binding.lineText.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.referenceText.setTextColor(0xFF999999.toInt())
        }
        
        holder.binding.referenceText.text = "${occurrence.author}, ${occurrence.work} ${occurrence.book}.${occurrence.lineNumber}"
        
        // Highlight matching words based on their word positions
        if (occurrence.matchingWords.isNotEmpty()) {
            holder.binding.lineText.text = highlightMatchingWords(occurrence.lineText, occurrence.matchingWords, invertColors)
        } else {
            holder.binding.lineText.text = occurrence.lineText
        }
        
        holder.binding.root.setOnClickListener {
            onOccurrenceClick(occurrence)
        }
    }
    
    override fun getItemCount() = occurrences.size
    
    private fun normalizeGreek(text: String): String {
        // First remove punctuation (comma, period, semicolon, raised dot)
        val noPunctuation = text.replace(Regex("[,;.·:!?]"), "")
        
        // Match the normalization used in the database
        val nfd = Normalizer.normalize(noPunctuation, Normalizer.Form.NFD)
        
        // Remove combining marks
        val noCombining = nfd.toCharArray().filter { char ->
            val type = Character.getType(char)
            type != Character.NON_SPACING_MARK.toInt() &&
            type != Character.ENCLOSING_MARK.toInt() &&
            type != Character.COMBINING_SPACING_MARK.toInt()
        }.joinToString("")
        
        // Convert to lowercase and replace final sigma
        val lowercased = noCombining.lowercase()
        val normalizedSigma = lowercased.replace("ς", "σ")
        
        // Keep only Greek letters
        return normalizedSigma.filter { char ->
            char.isLetter() && (char in '\u0370'..'\u03ff' || char in '\u1f00'..'\u1fff')
        }
    }
    
    private fun highlightMatchingWords(lineText: String, matchingWords: List<com.classicsviewer.app.models.WordMatch>, invertColors: Boolean): SpannableStringBuilder {
        val spannable = SpannableStringBuilder(lineText)
        val words = lineText.split("\\s+".toRegex())
        
        // Create a set of positions that should be highlighted
        val positionsToHighlight = matchingWords.map { it.position }.toSet()
        
        var currentPos = 0
        words.forEachIndexed { index, word ->
            val wordPosition = index + 1 // Word positions are 1-based in database
            
            if (positionsToHighlight.contains(wordPosition)) {
                val wordStart = currentPos
                val wordEnd = currentPos + word.length
                
                // Apply highlighting - background color and bold
                val highlightColor = if (invertColors) {
                    0xFFFFFF00.toInt() // Yellow background for inverted mode (black text)
                } else {
                    0xFF444400.toInt() // Dark yellow background for normal mode (white text)
                }
                
                spannable.setSpan(
                    BackgroundColorSpan(highlightColor),
                    wordStart,
                    wordEnd,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                
                spannable.setSpan(
                    StyleSpan(Typeface.BOLD),
                    wordStart,
                    wordEnd,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
            
            // Move to next word position (word + space)
            currentPos += word.length
            if (index < words.size - 1) {
                // Find the actual space(s) between words
                while (currentPos < lineText.length && lineText[currentPos].isWhitespace()) {
                    currentPos++
                }
            }
        }
        
        return spannable
    }
}