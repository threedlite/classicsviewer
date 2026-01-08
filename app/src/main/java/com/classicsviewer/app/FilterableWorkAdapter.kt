package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextBinding
import com.classicsviewer.app.models.Work
import com.classicsviewer.app.utils.PreferencesManager
import java.util.Locale

class FilterableWorkAdapter(
    private val allWorks: List<Work>,
    private val invertColors: Boolean = false,
    private val onWorkClick: (Work) -> Unit
) : RecyclerView.Adapter<FilterableWorkAdapter.ViewHolder>() {

    private var filteredWorks: MutableList<Work> = allWorks.toMutableList()
    private var searchQuery: String = ""
    private var showOnlyTranslated: Boolean = false

    class ViewHolder(val binding: ItemTextBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTextBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val work = filteredWorks[position]
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.itemText.textSize = fontSize
        holder.binding.itemText.text = work.title

        // Bold text for works with translations
        // Use null for typeface to ensure proper reset when views are recycled
        if (work.hasTranslation) {
            holder.binding.itemText.setTypeface(null, android.graphics.Typeface.BOLD)
        } else {
            holder.binding.itemText.setTypeface(null, android.graphics.Typeface.NORMAL)
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

    override fun getItemCount() = filteredWorks.size

    fun filter(query: String, onlyTranslated: Boolean) {
        searchQuery = query.lowercase(Locale.getDefault())
        showOnlyTranslated = onlyTranslated
        applyFilters()
    }

    fun setTranslationFilter(onlyTranslated: Boolean) {
        showOnlyTranslated = onlyTranslated
        applyFilters()
    }

    fun setSearchQuery(query: String) {
        searchQuery = query.lowercase(Locale.getDefault())
        applyFilters()
    }

    private fun applyFilters() {
        filteredWorks.clear()

        val searchResults = if (searchQuery.isEmpty()) {
            allWorks
        } else {
            allWorks.filter { work ->
                work.title.lowercase(Locale.getDefault()).contains(searchQuery)
            }
        }

        val finalResults = if (showOnlyTranslated) {
            searchResults.filter { it.hasTranslation }
        } else {
            searchResults
        }

        filteredWorks.addAll(finalResults)
        notifyDataSetChanged()
    }

    fun getFilteredCount(): Int = filteredWorks.size

    fun getTotalCount(): Int = allWorks.size
}