package com.classicsviewer.app.audio

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.RadioButton
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.classicsviewer.app.R
import java.text.SimpleDateFormat
import java.util.*

class AudioPackageAdapter(
    private val packages: List<AudioPackage>,
    private val onPackageSelected: (Long) -> Unit,
    private val onPackageDeleted: (Long) -> Unit
) : RecyclerView.Adapter<AudioPackageAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val radioButton: RadioButton = view.findViewById(R.id.radioActive)
        val textPackageName: TextView = view.findViewById(R.id.textPackageName)
        val textPackageInfo: TextView = view.findViewById(R.id.textPackageInfo)
        val textImportDate: TextView = view.findViewById(R.id.textImportDate)
        val buttonDelete: ImageButton = view.findViewById(R.id.buttonDelete)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_audio_package, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val audioPackage = packages[position]
        
        holder.radioButton.isChecked = audioPackage.isActive
        holder.textPackageName.text = audioPackage.packageName
        
        // Format package info
        val fileSize = formatFileSize(audioPackage.fileSizeBytes)
        holder.textPackageInfo.text = "${audioPackage.totalFiles} files • $fileSize"
        
        // Format import date
        val dateFormat = SimpleDateFormat("MMM d, yyyy", Locale.getDefault())
        holder.textImportDate.text = "Imported: ${dateFormat.format(Date(audioPackage.importDate))}"
        
        // Handle radio button click
        holder.radioButton.setOnClickListener {
            if (!audioPackage.isActive) {
                onPackageSelected(audioPackage.id)
            }
        }
        
        // Handle row click
        holder.itemView.setOnClickListener {
            if (!audioPackage.isActive) {
                onPackageSelected(audioPackage.id)
            }
        }
        
        // Handle delete button - disable for bundled package
        if (audioPackage.id == -1L) {
            // This is the bundled package, don't allow deletion
            holder.buttonDelete.visibility = View.GONE
        } else {
            holder.buttonDelete.visibility = View.VISIBLE
            holder.buttonDelete.setOnClickListener {
                onPackageDeleted(audioPackage.id)
            }
        }
    }

    override fun getItemCount() = packages.size
    
    private fun formatFileSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> String.format("%.1f KB", bytes / 1024.0)
            bytes < 1024 * 1024 * 1024 -> String.format("%.1f MB", bytes / (1024.0 * 1024))
            else -> String.format("%.1f GB", bytes / (1024.0 * 1024 * 1024))
        }
    }
}