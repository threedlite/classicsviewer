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

        // Don't allow overriding Greek or Latin
        if (languageId == "greek" || languageId == "latin") {
            Toast.makeText(this, "Cannot override built-in languages", Toast.LENGTH_SHORT).show()
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
        val customLanguages = PreferencesManager.getCustomLanguages(this)
        customLanguagesAdapter = CustomLanguagesAdapter(customLanguages) { language ->
            // Handle delete
            showDeleteConfirmation(language)
        }

        binding.customLanguagesRecyclerView.layoutManager = LinearLayoutManager(this)
        binding.customLanguagesRecyclerView.adapter = customLanguagesAdapter
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