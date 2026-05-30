package com.classicsviewer.app.topical

import android.graphics.Color
import android.graphics.Typeface
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.R

/** One related-passage row, fully hydrated from the loaded perseus_texts.db. */
data class RelatedPassage(
    val reference: String,          // "Homer, Iliad  Book 1.15" (English)
    val originalSnippet: String,    // limited Greek/Latin
    val translationSnippet: String?, // limited aligned English translation (nullable)
    val similarity: Float,
    val kind: String,               // "tfidf" or "lda" (used by caller, not rendered)
    // navigation into the reader:
    val workId: String,
    val bookId: String,
    val bookLabel: String,
    val lineNumber: Int,
    val sequenceNumber: Int,
    val language: String,
    val authorName: String,
    val workTitle: String
)

/**
 * Standalone adapter for the Topical Links screen. Does not reuse
 * OccurrenceAdapter. No per-row kind badge — the selected kind is shown once in
 * the screen header (the dropdown), not on every row.
 */
class RelatedPassageAdapter(
    private val items: List<RelatedPassage>,
    private val fontSize: Float,
    inverted: Boolean,
    private val onClick: (RelatedPassage) -> Unit
) : RecyclerView.Adapter<RelatedPassageAdapter.VH>() {

    private val refColor = if (inverted) Color.parseColor("#666666") else Color.parseColor("#999999")
    private val textColor = if (inverted) Color.BLACK else Color.WHITE
    private val transColor = if (inverted) Color.parseColor("#555555") else Color.parseColor("#BBBBBB")

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val reference: TextView = v.findViewById(R.id.referenceText)
        val original: TextView = v.findViewById(R.id.originalText)
        val translation: TextView = v.findViewById(R.id.translationText)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_topical, parent, false)
        return VH(v)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]

        holder.reference.text = item.reference
        holder.reference.setTextColor(refColor)
        holder.reference.textSize = fontSize * 0.8f
        holder.reference.setTypeface(Typeface.DEFAULT, Typeface.BOLD)

        holder.original.text = item.originalSnippet
        holder.original.setTextColor(textColor)
        holder.original.textSize = fontSize
        holder.original.setTypeface(Typeface.DEFAULT, Typeface.NORMAL)

        val trans = item.translationSnippet
        if (trans.isNullOrBlank()) {
            holder.translation.visibility = View.GONE
        } else {
            holder.translation.visibility = View.VISIBLE
            holder.translation.text = trans
            holder.translation.setTextColor(transColor)
            holder.translation.textSize = fontSize * 0.85f
            holder.translation.setTypeface(Typeface.DEFAULT, Typeface.ITALIC)
        }

        holder.itemView.setOnClickListener { onClick(item) }
    }
}
