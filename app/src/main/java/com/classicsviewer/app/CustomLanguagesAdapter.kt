package com.classicsviewer.app

import android.graphics.Color
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.classicsviewer.app.models.CustomLanguageConfig
import java.util.Collections

class CustomLanguagesAdapter(
    private val languages: MutableList<CustomLanguageConfig>,
    private val onEditClick: (CustomLanguageConfig) -> Unit,
    private val onDeleteClick: (CustomLanguageConfig) -> Unit,
    private val onOrderChanged: (List<CustomLanguageConfig>) -> Unit,
    private val onStartDrag: (RecyclerView.ViewHolder) -> Unit
) : RecyclerView.Adapter<CustomLanguagesAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val card: MaterialCardView = view.findViewById(R.id.customLanguageCard)
        val nameText: TextView = view.findViewById(R.id.customLanguageName)
        val idText: TextView = view.findViewById(R.id.customLanguageId)
        val editButton: Button = view.findViewById(R.id.editLanguageButton)
        val deleteButton: Button = view.findViewById(R.id.deleteLanguageButton)
        val dragHandle: ImageView = view.findViewById(R.id.dragHandle)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_custom_language, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val language = languages[position]

        holder.nameText.text = language.displayName
        holder.idText.text = "ID: ${language.id}"
        holder.card.setCardBackgroundColor(language.color)

        // Set text color based on background brightness
        val brightness = getBrightness(language.color)
        val textColor = if (brightness > 128) Color.BLACK else Color.WHITE
        holder.nameText.setTextColor(textColor)
        holder.idText.setTextColor(textColor)

        holder.editButton.setOnClickListener {
            onEditClick(language)
        }

        holder.deleteButton.setOnClickListener {
            onDeleteClick(language)
        }

        // Set up drag handle
        holder.dragHandle.setOnTouchListener { _, event ->
            if (event.actionMasked == MotionEvent.ACTION_DOWN) {
                onStartDrag(holder)
            }
            false
        }
    }

    fun onItemMove(fromPosition: Int, toPosition: Int) {
        if (fromPosition < toPosition) {
            for (i in fromPosition until toPosition) {
                Collections.swap(languages, i, i + 1)
            }
        } else {
            for (i in fromPosition downTo toPosition + 1) {
                Collections.swap(languages, i, i - 1)
            }
        }
        notifyItemMoved(fromPosition, toPosition)
        onOrderChanged(languages)
    }

    override fun getItemCount() = languages.size

    private fun getBrightness(color: Int): Int {
        val red = Color.red(color)
        val green = Color.green(color)
        val blue = Color.blue(color)
        return ((red * 299) + (green * 587) + (blue * 114)) / 1000
    }
}