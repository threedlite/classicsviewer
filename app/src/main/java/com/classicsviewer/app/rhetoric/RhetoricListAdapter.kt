package com.classicsviewer.app.rhetoric

import android.graphics.Typeface
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.databinding.ItemTextBinding
import com.classicsviewer.app.utils.PreferencesManager

/**
 * Shared list adapter for the rhetoric section list and entry list. Reuses the
 * app's item_text.xml row so the screens look like the rest of the app.
 */
class RhetoricListAdapter(
    private val items: List<RhetoricListItem>,
    private val invertColors: Boolean,
    private val bold: Boolean = false,
    private val onClick: (RhetoricListItem) -> Unit
) : RecyclerView.Adapter<RhetoricListAdapter.ViewHolder>() {

    class ViewHolder(val binding: ItemTextBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTextBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        val fontSize = PreferencesManager.getFontSize(holder.itemView.context)
        holder.binding.itemText.textSize = fontSize
        holder.binding.itemText.text = item.label
        holder.binding.itemText.setTypeface(null, if (bold) Typeface.BOLD else Typeface.NORMAL)
        holder.binding.itemText.setTextColor(
            if (invertColors) 0xFF000000.toInt() else 0xFFFFFFFF.toInt()
        )
        holder.binding.root.setOnClickListener { onClick(item) }
    }

    override fun getItemCount(): Int = items.size
}
