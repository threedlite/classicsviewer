package com.classicsviewer.app

import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.databinding.ActivityManageLanguagesBinding
import com.classicsviewer.app.utils.PreferencesManager
import com.google.android.material.card.MaterialCardView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.classicsviewer.app.models.CustomLanguageConfig
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.recyclerview.widget.ItemTouchHelper
import androidx.recyclerview.widget.RecyclerView
import android.widget.ScrollView
import android.text.TextWatcher
import android.text.Editable

class ManageLanguagesActivity : BaseActivity() {

    private lateinit var binding: ActivityManageLanguagesBinding
    private var selectedColor: Int = 0xFF808080.toInt() // Default gray color
    private lateinit var customLanguagesAdapter: CustomLanguagesAdapter


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityManageLanguagesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = "Manage Languages"

        setupUI()
        loadCustomLanguages()
    }


    private fun setupUI() {
        // Initialize with default color
        updateColorPreview(selectedColor)

        // Color picker button
        binding.pickColorButton.setOnClickListener {
            showColorPicker()
        }

        // Save button
        binding.saveButton.setOnClickListener {
            saveLanguageConfiguration()
        }

        // Update preview when name changes
        binding.languageNameInput.setOnEditorActionListener { _, _, _ ->
            updateLanguagePreview()
            false
        }

        // Auto-populate display name from language ID
        binding.languageIdInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                // Only auto-populate if display name is empty
                val displayName = binding.languageNameInput.text?.toString()
                if (displayName.isNullOrBlank() && !s.isNullOrBlank()) {
                    val autoDisplayName = convertLanguageIdToDisplayName(s.toString())
                    binding.languageNameInput.setText(autoDisplayName)
                    updateLanguagePreview()
                }
            }
        })
    }

    private fun convertLanguageIdToDisplayName(languageId: String): String {
        // Replace underscores with spaces, then capitalize each word
        return languageId.replace('_', ' ')
            .split(' ')
            .joinToString(" ") { word ->
                word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
            }
    }

    private fun showColorPicker() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_color_picker, null)
        val colorPreview = dialogView.findViewById<View>(R.id.colorPreview)
        val redSeekBar = dialogView.findViewById<SeekBar>(R.id.redSeekBar)
        val greenSeekBar = dialogView.findViewById<SeekBar>(R.id.greenSeekBar)
        val blueSeekBar = dialogView.findViewById<SeekBar>(R.id.blueSeekBar)
        val redValue = dialogView.findViewById<TextView>(R.id.redValue)
        val greenValue = dialogView.findViewById<TextView>(R.id.greenValue)
        val blueValue = dialogView.findViewById<TextView>(R.id.blueValue)
        val hexValue = dialogView.findViewById<TextView>(R.id.hexValue)

        // Set initial values from current color
        val red = Color.red(selectedColor)
        val green = Color.green(selectedColor)
        val blue = Color.blue(selectedColor)

        redSeekBar.progress = red
        greenSeekBar.progress = green
        blueSeekBar.progress = blue
        redValue.text = red.toString()
        greenValue.text = green.toString()
        blueValue.text = blue.toString()
        colorPreview.setBackgroundColor(selectedColor)
        hexValue.text = String.format("#%06X", 0xFFFFFF and selectedColor)

        val updateColor = {
            val newColor = Color.rgb(
                redSeekBar.progress,
                greenSeekBar.progress,
                blueSeekBar.progress
            )
            colorPreview.setBackgroundColor(newColor)
            redValue.text = redSeekBar.progress.toString()
            greenValue.text = greenSeekBar.progress.toString()
            blueValue.text = blueSeekBar.progress.toString()
            hexValue.text = String.format("#%06X", 0xFFFFFF and newColor)
        }

        val seekBarListener = object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                updateColor()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        }

        redSeekBar.setOnSeekBarChangeListener(seekBarListener)
        greenSeekBar.setOnSeekBarChangeListener(seekBarListener)
        blueSeekBar.setOnSeekBarChangeListener(seekBarListener)

        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle("Pick Button Color")
            .setView(dialogView)
            .setPositiveButton("OK") { _, _ ->
                selectedColor = Color.rgb(
                    redSeekBar.progress,
                    greenSeekBar.progress,
                    blueSeekBar.progress
                )
                updateColorPreview(selectedColor)
                updateLanguagePreview()
            }
            .setNegativeButton("Cancel", null)
            .create()

        dialog.show()
    }

    private fun updateColorPreview(color: Int) {
        binding.colorPreview.setBackgroundColor(color)
        binding.languagePreviewCard.setCardBackgroundColor(color)
    }

    private fun updateLanguagePreview() {
        val displayName = binding.languageNameInput.text?.toString() ?: "Language"
        binding.languagePreviewText.text = displayName

        // Set text color based on background brightness
        val brightness = getBrightness(selectedColor)
        val textColor = if (brightness > 128) Color.BLACK else Color.WHITE
        binding.languagePreviewText.setTextColor(textColor)
    }

    private fun getBrightness(color: Int): Int {
        val red = Color.red(color)
        val green = Color.green(color)
        val blue = Color.blue(color)
        // Calculate perceived brightness using standard formula
        return ((red * 299) + (green * 587) + (blue * 114)) / 1000
    }

    private fun saveLanguageConfiguration() {
        val languageId = binding.languageIdInput.text?.toString()?.trim()?.lowercase()
        val displayName = binding.languageNameInput.text?.toString()?.trim()

        if (languageId.isNullOrEmpty()) {
            Toast.makeText(this, "Please enter a language ID", Toast.LENGTH_SHORT).show()
            return
        }

        if (displayName.isNullOrEmpty()) {
            Toast.makeText(this, "Please enter a display name", Toast.LENGTH_SHORT).show()
            return
        }

        // Save the custom language configuration
        val customLanguage = CustomLanguageConfig(languageId, displayName, selectedColor)
        PreferencesManager.addCustomLanguage(this, customLanguage)

        Toast.makeText(this, "Language configuration saved", Toast.LENGTH_SHORT).show()

        // Reset form
        binding.languageIdInput.setText("")
        binding.languageNameInput.setText("")
        selectedColor = 0xFF808080.toInt()
        updateColorPreview(selectedColor)
        updateLanguagePreview()

        // Reload the list
        loadCustomLanguages()
    }

    private fun loadCustomLanguages() {
        val customLanguages = PreferencesManager.getCustomLanguages(this).toMutableList()
        customLanguagesAdapter = CustomLanguagesAdapter(
            customLanguages,
            onEditClick = { language -> showEditDialog(language) },
            onDeleteClick = { language -> showDeleteConfirmation(language) },
            onOrderChanged = { newOrder ->
                PreferencesManager.setCustomLanguagesOrder(this, newOrder)
            }
        )

        binding.customLanguagesRecyclerView.layoutManager = LinearLayoutManager(this)
        binding.customLanguagesRecyclerView.adapter = customLanguagesAdapter

        // Add drag-and-drop support
        val itemTouchHelper = ItemTouchHelper(object : ItemTouchHelper.SimpleCallback(
            ItemTouchHelper.UP or ItemTouchHelper.DOWN, 0
        ) {
            override fun onMove(
                recyclerView: RecyclerView,
                viewHolder: RecyclerView.ViewHolder,
                target: RecyclerView.ViewHolder
            ): Boolean {
                val fromPos = viewHolder.adapterPosition
                val toPos = target.adapterPosition
                customLanguagesAdapter.onItemMove(fromPos, toPos)
                return true
            }

            override fun onSwiped(viewHolder: RecyclerView.ViewHolder, direction: Int) {
                // Not used
            }
        })

        itemTouchHelper.attachToRecyclerView(binding.customLanguagesRecyclerView)
    }

    private fun showEditDialog(language: CustomLanguageConfig) {
        // Pre-fill the form with existing values
        binding.languageIdInput.setText(language.id)
        binding.languageNameInput.setText(language.displayName)
        selectedColor = language.color
        updateColorPreview(selectedColor)
        updateLanguagePreview()

        // Scroll to top so user sees the form
        binding.languageIdInput.requestFocus()
    }

    private fun showDeleteConfirmation(language: CustomLanguageConfig) {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete Language")
            .setMessage("Delete ${language.displayName}?")
            .setPositiveButton("Delete") { _, _ ->
                PreferencesManager.removeCustomLanguage(this, language.id)
                loadCustomLanguages()
                Toast.makeText(this, "Language deleted", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}