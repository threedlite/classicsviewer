package com.classicsviewer.app.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.R
import com.classicsviewer.app.database.entities.BookmarkEntity
import java.text.SimpleDateFormat
import java.util.*

class BookmarksAdapter(
    private val onBookmarkClick: (BookmarkEntity) -> Unit,
    private val onBookmarkLongClick: (BookmarkEntity) -> Unit
) : ListAdapter<BookmarkEntity, BookmarksAdapter.BookmarkViewHolder>(BookmarkDiffCallback()) {
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): BookmarkViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_bookmark, parent, false)
        return BookmarkViewHolder(view)
    }
    
    override fun onBindViewHolder(holder: BookmarkViewHolder, position: Int) {
        holder.bind(getItem(position))
    }
    
    inner class BookmarkViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val titleText: TextView = itemView.findViewById(R.id.bookmarkTitle)
        private val subtitleText: TextView = itemView.findViewById(R.id.bookmarkSubtitle)
        private val lineText: TextView = itemView.findViewById(R.id.bookmarkLineText)
        private val noteText: TextView = itemView.findViewById(R.id.bookmarkNote)
        private val dateText: TextView = itemView.findViewById(R.id.bookmarkDate)
        
        fun bind(bookmark: BookmarkEntity) {
            // Title: Author - Work
            titleText.text = "${bookmark.authorName} - ${bookmark.workTitle}"
            
            // Subtitle: Book X, Line Y
            val bookInfo = bookmark.bookLabel?.let { "Book $it" } ?: "Book"
            subtitleText.text = "$bookInfo, Line ${bookmark.lineNumber}"
            
            // Line text preview
            lineText.text = bookmark.lineText
            
            // Note (if present)
            if (!bookmark.note.isNullOrEmpty()) {
                noteText.visibility = View.VISIBLE
                noteText.text = bookmark.note
            } else {
                noteText.visibility = View.GONE
            }
            
            // Date
            val dateFormat = SimpleDateFormat("MMM d, yyyy", Locale.getDefault())
            dateText.text = dateFormat.format(Date(bookmark.createdAt))
            
            // Click listeners
            itemView.setOnClickListener { onBookmarkClick(bookmark) }
            itemView.setOnLongClickListener {
                onBookmarkLongClick(bookmark)
                true
            }
        }
    }
    
    class BookmarkDiffCallback : DiffUtil.ItemCallback<BookmarkEntity>() {
        override fun areItemsTheSame(oldItem: BookmarkEntity, newItem: BookmarkEntity): Boolean {
            return oldItem.id == newItem.id
        }
        
        override fun areContentsTheSame(oldItem: BookmarkEntity, newItem: BookmarkEntity): Boolean {
            return oldItem == newItem
        }
    }
}