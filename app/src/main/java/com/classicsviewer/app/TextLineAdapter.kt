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
    
    // Custom ClickableSpan that can optionally show underline
    private inner class CustomClickableSpan(
        private val clickAction: () -> Unit,
        private val showUnderline: Boolean
    ) : ClickableSpan() {
        override fun onClick(widget: View) {
            clickAction()
        }
        
        override fun updateDrawState(ds: TextPaint) {
            if (showUnderline) {
                super.updateDrawState(ds)
                // Keep underline but remove color change
                ds.color = ds.linkColor
            } else {
                // Don't call super to avoid default underline and color
                // Keep the original text appearance
            }
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
        val showUnderlines = PreferencesManager.getShowWordUnderlines(holder.itemView.context)
        
        // Always use character-by-character parsing for reliability
        // Process character by character to find word boundaries
            var wordStart = -1
            var i = 0
            
            while (i < line.text.length) {
                val char = line.text[i]
                val isWordChar = char.isLetter() || (char == '\'' && i > 0 && i < line.text.length - 1 && 
                                                      line.text[i-1].isLetter() && line.text[i+1].isLetter())
                
                if (isWordChar && wordStart == -1) {
                    // Start of a new word
                    wordStart = i
                } else if (!isWordChar && wordStart != -1) {
                    // End of current word
                    val wordEnd = i
                    val word = line.text.substring(wordStart, wordEnd)
                    
                    if (word.isNotEmpty()) {
                        spannableString.setSpan(
                            CustomClickableSpan(
                                clickAction = {
                                    onWordClick(word)
                                },
                                showUnderline = showUnderlines
                            ),
                            wordStart,
                            wordEnd,
                            SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                        )
                    }
                    wordStart = -1
                }
                i++
            }
            
            // Handle last word if line ends with a word character
            if (wordStart != -1) {
                val word = line.text.substring(wordStart)
                if (word.isNotEmpty()) {
                    spannableString.setSpan(
                        CustomClickableSpan(
                            clickAction = {
                                onWordClick(word)
                            },
                            showUnderline = showUnderlines
                        ),
                        wordStart,
                        line.text.length,
                        SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
                    )
                }
            }
        
        holder.binding.lineText.text = spannableString
        holder.binding.lineText.movementMethod = LinkMovementMethod.getInstance()
    }
    
    override fun getItemCount() = lines.size
}