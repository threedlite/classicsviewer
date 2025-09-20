package com.classicsviewer.app

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextBinding
import com.classicsviewer.app.models.Book
import com.classicsviewer.app.utils.PreferencesManager

class BookAdapter(
    private val books: List<Book>,
    private val invertColors: Boolean = false,
    private val onBookClick: (Book) -> Unit
) : RecyclerView.Adapter<BookAdapter.ViewHolder>() {
    
    class ViewHolder(val binding: ItemTextBinding) : RecyclerView.ViewHolder(binding.root)
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTextBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val book = books[position]
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.itemText.textSize = fontSize
        holder.binding.itemText.text = "${book.number} (${book.lineCount} lines)"
        
        // Apply color inversion
        if (invertColors) {
            // Black on white
            holder.binding.itemText.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            holder.binding.itemText.setTextColor(0xFFFFFFFF.toInt())
        }
        
        holder.binding.root.setOnClickListener { onBookClick(book) }
    }
    
    override fun getItemCount() = books.size
}