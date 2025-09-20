package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextBinding
import com.classicsviewer.app.models.Author
import com.classicsviewer.app.utils.PreferencesManager
import java.util.Locale

class FilterableAuthorAdapter(
    private val allAuthors: List<Author>,
    private val invertColors: Boolean = false,
    private val onAuthorClick: (Author) -> Unit
) : RecyclerView.Adapter<FilterableAuthorAdapter.ViewHolder>() {

    private var filteredAuthors: MutableList<Author> = allAuthors.toMutableList()
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
        val author = filteredAuthors[position]
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.itemText.textSize = fontSize
        holder.binding.itemText.text = author.name

        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.itemText.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            holder.binding.itemText.setTextColor(0xFFFFFFFF.toInt())
        }

        // Make authors with translations bold
        if (author.hasTranslatedWorks) {
            holder.binding.itemText.setTypeface(null, android.graphics.Typeface.BOLD)
        } else {
            holder.binding.itemText.setTypeface(null, android.graphics.Typeface.NORMAL)
        }

        holder.binding.root.setOnClickListener { onAuthorClick(author) }
    }

    override fun getItemCount() = filteredAuthors.size

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
        filteredAuthors.clear()

        val searchResults = if (searchQuery.isEmpty()) {
            allAuthors
        } else {
            allAuthors.filter { author ->
                author.name.lowercase(Locale.getDefault()).contains(searchQuery)
            }
        }

        val finalResults = if (showOnlyTranslated) {
            searchResults.filter { it.hasTranslatedWorks }
        } else {
            searchResults
        }

        filteredAuthors.addAll(finalResults)
        notifyDataSetChanged()
    }

    fun getFilteredCount(): Int = filteredAuthors.size

    fun getTotalCount(): Int = allAuthors.size
}