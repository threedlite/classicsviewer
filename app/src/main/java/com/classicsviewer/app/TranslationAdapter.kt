package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTranslationSegmentBinding
import com.classicsviewer.app.fragments.TranslationDisplayItem
import com.classicsviewer.app.utils.PreferencesManager

class TranslationAdapter(
    private val segments: List<TranslationDisplayItem>,
    private val invertColors: Boolean = false
) : RecyclerView.Adapter<TranslationAdapter.ViewHolder>() {
    
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
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.translationText.setTextColor(0xFF000000.toInt())
            holder.binding.lineRange.setTextColor(0xFF666666.toInt())
            holder.binding.translatorName.setTextColor(0xFF666666.toInt())
        } else {
            // White on black (default)
            holder.binding.translationText.setTextColor(0xFFFFFFFF.toInt())
            holder.binding.lineRange.setTextColor(0xFF999999.toInt())
            holder.binding.translatorName.setTextColor(0xFF999999.toInt())
        }
        
        // Show line range
        val rangeText = if (segment.startLine == segment.endLine) {
            "Line ${segment.startLine}"
        } else {
            "Lines ${segment.startLine}-${segment.endLine}"
        }
        holder.binding.lineRange.text = rangeText
        
        // Show translation text
        holder.binding.translationText.text = segment.text
        
        // Show translator if available
        if (!segment.translator.isNullOrBlank()) {
            holder.binding.translatorName.visibility = View.VISIBLE
            holder.binding.translatorName.text = "— ${segment.translator}"
        } else {
            holder.binding.translatorName.visibility = View.GONE
        }
    }
    
    override fun getItemCount() = segments.size
}