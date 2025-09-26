package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemLanguageBinding
import com.google.android.material.card.MaterialCardView
import com.classicsviewer.app.models.CustomLanguageConfig

class LanguageAdapter(
    private val languages: List<Language>,
    private val invertColors: Boolean = false,
    private val customLanguages: List<CustomLanguageConfig> = emptyList(),
    private val onLanguageClick: (Language) -> Unit
) : RecyclerView.Adapter<LanguageAdapter.ViewHolder>() {
    
    class ViewHolder(val binding: ItemLanguageBinding) : RecyclerView.ViewHolder(binding.root)
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemLanguageBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val language = languages[position]
        holder.binding.languageName.text = language.name
        holder.binding.languageName.setTypeface(holder.binding.languageName.typeface, android.graphics.Typeface.BOLD)

        // Check if it's a custom language first
        val customLang = customLanguages.find { it.id == language.code }
        if (customLang != null) {
            // Apply custom language color
            (holder.binding.root as MaterialCardView).setCardBackgroundColor(customLang.color)

            // Set text color based on background brightness
            val brightness = getBrightness(customLang.color)
            val textColor = if (brightness > 128) 0xFF000000.toInt() else 0xFFFFFFFF.toInt()
            holder.binding.languageName.setTextColor(textColor)
        } else {
            // Apply Loeb Classical Library colors for built-in languages
            when (language.code) {
                "greek" -> {
                    // Loeb Greek green - less saturated, more pastel
                    (holder.binding.root as MaterialCardView).setCardBackgroundColor(0xFF5A8A5C.toInt())
                    holder.binding.languageName.setTextColor(0xFFFFFFFF.toInt())
                }
                "latin" -> {
                    // Loeb Latin red - less saturated, more pastel
                    (holder.binding.root as MaterialCardView).setCardBackgroundColor(0xFFB85450.toInt())
                    holder.binding.languageName.setTextColor(0xFFFFFFFF.toInt())
                }
            }
        }

        holder.binding.root.setOnClickListener { onLanguageClick(language) }
    }

    private fun getBrightness(color: Int): Int {
        val red = android.graphics.Color.red(color)
        val green = android.graphics.Color.green(color)
        val blue = android.graphics.Color.blue(color)
        return ((red * 299) + (green * 587) + (blue * 114)) / 1000
    }
    
    override fun getItemCount() = languages.size
}