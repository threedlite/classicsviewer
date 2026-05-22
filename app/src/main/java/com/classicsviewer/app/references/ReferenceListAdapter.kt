package com.classicsviewer.app.references

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.R
import com.classicsviewer.app.data.ReferenceEntry
import com.classicsviewer.app.utils.PreferencesManager

class ReferenceListAdapter(
    private val context: Context,
    private val entries: List<ReferenceEntry>,
    private val onClick: (ReferenceEntry) -> Unit,
) : RecyclerView.Adapter<ReferenceListAdapter.VH>() {

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.referenceTitle)
        val author: TextView = view.findViewById(R.id.referenceAuthor)
        val meta: TextView = view.findViewById(R.id.referenceMeta)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_reference, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val entry = entries[position]
        holder.title.text = entry.title
        holder.author.text = entry.author
        val lastPage = PreferencesManager.getLastReadPage(context, entry.id)
        holder.meta.text = if (lastPage != null) {
            context.getString(R.string.references_meta_with_last, entry.pageCount, lastPage + 1)
        } else {
            context.getString(R.string.references_meta_pages_only, entry.pageCount)
        }
        holder.itemView.setOnClickListener { onClick(entry) }
    }

    override fun getItemCount(): Int = entries.size
}
