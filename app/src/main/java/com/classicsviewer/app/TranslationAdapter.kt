package com.classicsviewer.app

import android.text.Html
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
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
        
        // Show translation text - safely render only <hi rend="bold"> as bold
        holder.binding.translationText.text = if (segment.text.contains("<hi rend=\"bold\">")) {
            // Extract and escape segments, only allowing our specific bold tags
            val parts = segment.text.split("<hi rend=\"bold\">")
            val result = StringBuilder()

            for ((index, part) in parts.withIndex()) {
                if (index == 0) {
                    // First part - just escape and add
                    result.append(android.text.TextUtils.htmlEncode(part))
                } else {
                    // Part after opening tag - find closing tag
                    val closeIndex = part.indexOf("</hi>")
                    if (closeIndex != -1) {
                        val boldText = part.substring(0, closeIndex)
                        val afterBold = part.substring(closeIndex + 5)
                        result.append("<b>")
                        result.append(android.text.TextUtils.htmlEncode(boldText))
                        result.append("</b>")
                        result.append(android.text.TextUtils.htmlEncode(afterBold))
                    } else {
                        // Malformed - just escape it all
                        result.append(android.text.TextUtils.htmlEncode(part))
                    }
                }
            }

            Html.fromHtml(result.toString(), Html.FROM_HTML_MODE_LEGACY)
        } else {
            segment.text  // Plain text if no formatting
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
}