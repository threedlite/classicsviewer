package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextBinding
import com.classicsviewer.app.models.Work
import com.classicsviewer.app.utils.PreferencesManager

class WorkAdapter(
    private val works: List<Work>,
    private val invertColors: Boolean = false,
    private val onWorkClick: (Work) -> Unit
) : RecyclerView.Adapter<WorkAdapter.ViewHolder>() {
    
    class ViewHolder(val binding: ItemTextBinding) : RecyclerView.ViewHolder(binding.root)
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTextBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val work = works[position]
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.itemText.textSize = fontSize
        holder.binding.itemText.text = work.title
        
        // Bold text for works with translations
        if (work.hasTranslation) {
            holder.binding.itemText.setTypeface(holder.binding.itemText.typeface, android.graphics.Typeface.BOLD)
        } else {
            holder.binding.itemText.setTypeface(holder.binding.itemText.typeface, android.graphics.Typeface.NORMAL)
        }
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.itemText.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            holder.binding.itemText.setTextColor(0xFFFFFFFF.toInt())
        }
        
        holder.binding.root.setOnClickListener { onWorkClick(work) }
    }
    
    override fun getItemCount() = works.size
}