package com.classicsviewer.app

import android.text.SpannableString
import android.text.TextPaint
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextLineWithSpeakerBinding
import com.classicsviewer.app.models.TextLine
import com.classicsviewer.app.utils.PreferencesManager

class TextLineWithSpeakerAdapter(
    private val lines: List<TextLine>,
    private val onWordClick: (String) -> Unit,
    private val invertColors: Boolean = false
) : RecyclerView.Adapter<TextLineWithSpeakerAdapter.ViewHolder>() {
    
    class ViewHolder(val binding: ItemTextLineWithSpeakerBinding) : RecyclerView.ViewHolder(binding.root)
    
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
        val binding = ItemTextLineWithSpeakerBinding.inflate(
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
        holder.binding.speakerName.textSize = fontSize + 2 // Speaker slightly larger
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.lineText.setTextColor(0xFF000000.toInt())
            holder.binding.lineNumber.setTextColor(0xFF666666.toInt())
            holder.binding.speakerName.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            holder.binding.lineText.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.lineNumber.setTextColor(0xFF999999.toInt())
            holder.binding.speakerName.setTextColor(0xFFFFFFFF.toInt())
        }
        
        // Show speaker name if this is the first line by this speaker
        val showSpeaker = shouldShowSpeaker(position)
        android.util.Log.d("TextLineAdapter", "Line ${line.lineNumber}: speaker=${line.speaker}, showSpeaker=$showSpeaker")
        
        if (showSpeaker && !line.speaker.isNullOrBlank()) {
            holder.binding.speakerName.visibility = View.VISIBLE
            
            // Make speaker name clickable
            val speakerSpannable = SpannableString(line.speaker)
            speakerSpannable.setSpan(
                NoUnderlineClickableSpan {
                    // For speaker names
                    onWordClick(line.speaker)
                },
                0,
                line.speaker.length,
                SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            holder.binding.speakerName.text = speakerSpannable
            holder.binding.speakerName.movementMethod = LinkMovementMethod.getInstance()
            android.util.Log.d("TextLineAdapter", "Showing speaker: ${line.speaker}")
        } else {
            holder.binding.speakerName.visibility = View.GONE
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
    
    private fun shouldShowSpeaker(position: Int): Boolean {
        val currentLine = lines[position]
        
        // Don't show if no speaker
        if (currentLine.speaker.isNullOrBlank()) return false
        
        // Always show for first line
        if (position == 0) return true
        
        // Show if speaker changed from previous line
        val previousLine = lines[position - 1]
        return currentLine.speaker != previousLine.speaker
    }
    
    override fun getItemCount() = lines.size
}