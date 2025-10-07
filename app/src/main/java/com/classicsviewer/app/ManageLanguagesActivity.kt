package com.classicsviewer.app

import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Button
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
        // Add button
        binding.addLanguageButton.setOnClickListener {
            showAddEditDialog(null)
        }
    }

    private fun showAddEditDialog(existingLanguage: CustomLanguageConfig?) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_add_edit_language, null)

        val languageIdInput = dialogView.findViewById<com.google.android.material.textfield.TextInputEditText>(R.id.languageIdInput)
        val languageNameInput = dialogView.findViewById<com.google.android.material.textfield.TextInputEditText>(R.id.languageNameInput)
        val colorPreview = dialogView.findViewById<View>(R.id.colorPreview)
        val pickColorButton = dialogView.findViewById<Button>(R.id.pickColorButton)
        val languagePreviewCard = dialogView.findViewById<MaterialCardView>(R.id.languagePreviewCard)
        val languagePreviewText = dialogView.findViewById<TextView>(R.id.languagePreviewText)

        var selectedColor = existingLanguage?.color ?: 0xFF808080.toInt()

        // Pre-fill if editing
        if (existingLanguage != null) {
            languageIdInput.setText(existingLanguage.id)
            languageIdInput.isEnabled = false // Don't allow changing ID when editing
            languageNameInput.setText(existingLanguage.displayName)
        }

        // Update preview function
        val updatePreview = {
            val displayName = languageNameInput.text?.toString() ?: "Language"
            languagePreviewText.text = displayName
            colorPreview.setBackgroundColor(selectedColor)
            languagePreviewCard.setCardBackgroundColor(selectedColor)

            val brightness = getBrightness(selectedColor)
            val textColor = if (brightness > 128) Color.BLACK else Color.WHITE
            languagePreviewText.setTextColor(textColor)
        }

        updatePreview()

        // Auto-populate display name from language ID (only when adding new)
        if (existingLanguage == null) {
            languageIdInput.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    val displayName = languageNameInput.text?.toString()
                    if (displayName.isNullOrBlank() && !s.isNullOrBlank()) {
                        val autoDisplayName = convertLanguageIdToDisplayName(s.toString())
                        languageNameInput.setText(autoDisplayName)
                        updatePreview()
                    }
                }
            })
        }

        // Update preview when name changes
        languageNameInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                updatePreview()
            }
        })

        // Color picker button
        pickColorButton.setOnClickListener {
            showColorPickerDialog(selectedColor) { newColor ->
                selectedColor = newColor
                updatePreview()
            }
        }

        // Create dialog
        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle(if (existingLanguage != null) "Edit Language" else "Add Language")
            .setView(dialogView)
            .setPositiveButton("Save") { _, _ ->
                val languageId = languageIdInput.text?.toString()?.trim()?.lowercase()
                val displayName = languageNameInput.text?.toString()?.trim()

                if (languageId.isNullOrEmpty()) {
                    Toast.makeText(this, "Please enter a language ID", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }

                if (displayName.isNullOrEmpty()) {
                    Toast.makeText(this, "Please enter a display name", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }

                val customLanguage = CustomLanguageConfig(languageId, displayName, selectedColor)
                PreferencesManager.addCustomLanguage(this, customLanguage)

                Toast.makeText(this, "Language saved", Toast.LENGTH_SHORT).show()
                loadCustomLanguages()
            }
            .setNegativeButton("Cancel", null)
            .create()

        dialog.show()
    }

    private fun convertLanguageIdToDisplayName(languageId: String): String {
        // Replace underscores with spaces, then capitalize each word
        return languageId.replace('_', ' ')
            .split(' ')
            .joinToString(" ") { word ->
                word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
            }
    }

    private fun showColorPickerDialog(currentColor: Int, onColorSelected: (Int) -> Unit) {
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
        val red = Color.red(currentColor)
        val green = Color.green(currentColor)
        val blue = Color.blue(currentColor)

        redSeekBar.progress = red
        greenSeekBar.progress = green
        blueSeekBar.progress = blue
        redValue.text = red.toString()
        greenValue.text = green.toString()
        blueValue.text = blue.toString()
        colorPreview.setBackgroundColor(currentColor)
        hexValue.text = String.format("#%06X", 0xFFFFFF and currentColor)

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
                val selectedColor = Color.rgb(
                    redSeekBar.progress,
                    greenSeekBar.progress,
                    blueSeekBar.progress
                )
                onColorSelected(selectedColor)
            }
            .setNegativeButton("Cancel", null)
            .create()

        dialog.show()
    }

    private fun getBrightness(color: Int): Int {
        val red = Color.red(color)
        val green = Color.green(color)
        val blue = Color.blue(color)
        // Calculate perceived brightness using standard formula
        return ((red * 299) + (green * 587) + (blue * 114)) / 1000
    }

    private fun loadCustomLanguages() {
        val customLanguages = PreferencesManager.getCustomLanguages(this).toMutableList()

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

        customLanguagesAdapter = CustomLanguagesAdapter(
            customLanguages,
            onEditClick = { language -> showAddEditDialog(language) },
            onDeleteClick = { language -> showDeleteConfirmation(language) },
            onOrderChanged = { newOrder ->
                PreferencesManager.setCustomLanguagesOrder(this, newOrder)
            },
            onStartDrag = { viewHolder ->
                itemTouchHelper.startDrag(viewHolder)
            }
        )

        binding.customLanguagesRecyclerView.layoutManager = LinearLayoutManager(this)
        binding.customLanguagesRecyclerView.adapter = customLanguagesAdapter

        itemTouchHelper.attachToRecyclerView(binding.customLanguagesRecyclerView)
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