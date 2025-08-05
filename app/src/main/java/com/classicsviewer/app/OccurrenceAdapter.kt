package com.classicsviewer.app

import android.text.SpannableString
import android.text.style.StyleSpan
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemOccurrenceBinding
import com.classicsviewer.app.models.Occurrence
import com.classicsviewer.app.utils.PreferencesManager

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
        
        // Highlight the word in the line text
        val lineText = occurrence.lineText
        val wordStart = lineText.indexOf(occurrence.wordForm, ignoreCase = true)
        
        if (wordStart >= 0) {
            val spannableString = SpannableString(lineText)
            spannableString.setSpan(
                StyleSpan(android.graphics.Typeface.BOLD),
                wordStart,
                wordStart + occurrence.wordForm.length,
                SpannableString.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            holder.binding.lineText.text = spannableString
        } else {
            holder.binding.lineText.text = lineText
        }
        
        holder.binding.root.setOnClickListener {
            onOccurrenceClick(occurrence)
        }
    }
    
    override fun getItemCount() = occurrences.size
}