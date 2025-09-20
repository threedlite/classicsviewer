package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemLanguageBinding
import com.google.android.material.card.MaterialCardView

class LanguageAdapter(
    private val languages: List<Language>,
    private val invertColors: Boolean = false,
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
        
        // Apply Loeb Classical Library colors regardless of invert setting
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
        
        holder.binding.root.setOnClickListener { onLanguageClick(language) }
    }
    
    override fun getItemCount() = languages.size
}