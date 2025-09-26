package com.classicsviewer.app

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.classicsviewer.app.models.CustomLanguageConfig

class CustomLanguagesAdapter(
    private val languages: List<CustomLanguageConfig>,
    private val onDeleteClick: (CustomLanguageConfig) -> Unit
) : RecyclerView.Adapter<CustomLanguagesAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val card: MaterialCardView = view.findViewById(R.id.customLanguageCard)
        val nameText: TextView = view.findViewById(R.id.customLanguageName)
        val idText: TextView = view.findViewById(R.id.customLanguageId)
        val deleteButton: Button = view.findViewById(R.id.deleteLanguageButton)
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

        holder.deleteButton.setOnClickListener {
            onDeleteClick(language)
        }
    }

    override fun getItemCount() = languages.size

    private fun getBrightness(color: Int): Int {
        val red = Color.red(color)
        val green = Color.green(color)
        val blue = Color.blue(color)
        return ((red * 299) + (green * 587) + (blue * 114)) / 1000
    }
}