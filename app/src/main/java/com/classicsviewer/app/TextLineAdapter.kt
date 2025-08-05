package com.classicsviewer.app

import android.text.SpannableString
import android.text.TextPaint
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextLineBinding
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.utils.PreferencesManager

class TextLineAdapter(
    private val lines: List<TextLine>,
    private val onWordClick: (String) -> Unit,
    private val invertColors: Boolean = false
) : RecyclerView.Adapter<TextLineAdapter.ViewHolder>() {
    
    class ViewHolder(val binding: ItemTextLineBinding) : RecyclerView.ViewHolder(binding.root)
    
    // Custom ClickableSpan that doesn't show underline or color
    private inner class NoUnderlineClickableSpan(
        private val clickAction: () -> Unit
    ) : ClickableSpan() {
        override fun onClick(widget: View) {
            clickAction()
        }
        
        override fun updateDrawState(ds: TextPaint) {
            // Don't call super to avoid default underline and color
            // Keep the original text appearance
        }
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTextLineBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val line = lines[position]
        holder.binding.lineNumber.text = line.lineNumber.toString()
        
        // Apply saved font size
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.lineText.textSize = fontSize
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.lineText.setTextColor(0xFF000000.toInt())
            holder.binding.lineNumber.setTextColor(0xFF666666.toInt())
        } else {
            // White on black (default)
            holder.binding.lineText.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.lineNumber.setTextColor(0xFF999999.toInt())
        }
        
        // Make text clickable by word
        val spannableString = SpannableString(line.text)
        
        // Use the word information from the database if available
        if (line.words.isNotEmpty()) {
            for (word in line.words) {
                if (word.startOffset < line.text.length && word.endOffset <= line.text.length) {
                    spannableString.setSpan(
                        NoUnderlineClickableSpan {
                            // Pass the original word
                            onWordClick(word.text)
                        },
                        word.startOffset,
                        word.endOffset,
                        SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                    )
                }
            }
        } else {
            // Fallback to simple word splitting if no word data
            val words = line.text.split(Regex("\\s+"))
            var currentPos = 0
            
            for (word in words) {
                if (word.isNotEmpty()) {
                    val wordStart = line.text.indexOf(word, currentPos)
                    if (wordStart >= 0) {
                        val wordEnd = wordStart + word.length
                        
                        spannableString.setSpan(
                            NoUnderlineClickableSpan {
                                val cleanWord = word.replace(Regex("[.,;:!?·]"), "")
                                onWordClick(cleanWord)
                            },
                            wordStart,
                            wordEnd,
                            SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                        )
                        
                        currentPos = wordEnd
                    }
                }
            }
        }
        
        holder.binding.lineText.text = spannableString
        holder.binding.lineText.movementMethod = LinkMovementMethod.getInstance()
    }
    
    override fun getItemCount() = lines.size
}