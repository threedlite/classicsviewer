package com.classicsviewer.app

import android.content.Intent
import android.graphics.Typeface
import android.os.Bundle
import android.widget.SeekBar
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.databinding.ActivitySettingsBinding
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class SettingsActivity : BaseActivity() {
    
    private lateinit var binding: ActivitySettingsBinding
    private var sinaiticusTypeface: Typeface? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.title = "Settings"
        
        // Load Sinaiticus font
        try {
            sinaiticusTypeface = Typeface.createFromAsset(assets, "fonts/sinaiticus.ttf")
        } catch (e: Exception) {
            // Font loading failed, will use system font
        }
        
        setupFontSizeControl()
        setupColorInversionControl()
        setupOccurrenceLimitControl()
        setupButtons()
        setupBuildInfo()
        setupDatabaseInfo()
    }
    
    private fun setupFontSizeControl() {
        val currentSize = PreferencesManager.getFontSize(this)
        
        // Set initial values
        binding.fontSizeSeekBar.progress = (currentSize - 12).toInt() // Min size 12
        binding.fontSizeValue.text = "${currentSize.toInt()}sp"
        binding.fontSizePreview.textSize = currentSize
        
        binding.fontSizeSeekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val newSize = progress + 12f // Min size 12
                binding.fontSizeValue.text = "${newSize.toInt()}sp"
                binding.fontSizePreview.textSize = newSize
                PreferencesManager.setFontSize(this@SettingsActivity, newSize)
            }
            
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
    }
    
    private fun setupColorInversionControl() {
        val isInverted = PreferencesManager.getInvertColors(this)
        binding.invertColorsSwitch.isChecked = isInverted
        
        binding.invertColorsSwitch.setOnCheckedChangeListener { _, isChecked ->
            PreferencesManager.setInvertColors(this, isChecked)
            updatePreviewColors(isChecked)
        }
        
        // Apply initial preview colors
        updatePreviewColors(isInverted)
        
        // Setup word underlines switch
        val showUnderlines = PreferencesManager.getShowWordUnderlines(this)
        binding.showWordUnderlinesSwitch.isChecked = showUnderlines
        
        binding.showWordUnderlinesSwitch.setOnCheckedChangeListener { _, isChecked ->
            PreferencesManager.setShowWordUnderlines(this, isChecked)
        }
        
        // Setup Sinaiticus font switch
        val useSinaiticusFont = PreferencesManager.getUseSinaiticusFont(this)
        binding.useSinaiticusFontSwitch.isChecked = useSinaiticusFont
        
        binding.useSinaiticusFontSwitch.setOnCheckedChangeListener { _, isChecked ->
            PreferencesManager.setUseSinaiticusFont(this, isChecked)
            updatePreviewFont(isChecked)
        }
        
        // Apply initial font
        updatePreviewFont(useSinaiticusFont)

        // Setup interlinear first switch
        val interlinearFirst = PreferencesManager.getInterlinearFirst(this)
        binding.interlinearFirstSwitch.isChecked = interlinearFirst

        binding.interlinearFirstSwitch.setOnCheckedChangeListener { _, isChecked ->
            PreferencesManager.setInterlinearFirst(this, isChecked)
        }

        // Setup dependency tree switch (experimental)
        val enableDependencyTree = PreferencesManager.getEnableDependencyTree(this)
        binding.enableDependencyTreeSwitch.isChecked = enableDependencyTree

        binding.enableDependencyTreeSwitch.setOnCheckedChangeListener { _, isChecked ->
            PreferencesManager.setEnableDependencyTree(this, isChecked)
        }

        // Setup case coloring switch
        val caseColoring = PreferencesManager.getCaseColoring(this)
        binding.caseColoringSwitch.isChecked = caseColoring

        binding.caseColoringSwitch.setOnCheckedChangeListener { _, isChecked ->
            PreferencesManager.setCaseColoring(this, isChecked)
        }
    }

    private fun updatePreviewColors(inverted: Boolean) {
        if (inverted) {
            // Black on white
            binding.fontSizePreview.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.fontSizePreview.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            binding.fontSizePreview.setBackgroundColor(0xFF000000.toInt())
            binding.fontSizePreview.setTextColor(0xFFFFFFFF.toInt())
        }
    }
    
    private fun updatePreviewFont(useSinaiticus: Boolean) {
        if (useSinaiticus && sinaiticusTypeface != null) {
            binding.fontSizePreview.typeface = sinaiticusTypeface
        } else {
            binding.fontSizePreview.typeface = Typeface.DEFAULT
        }
    }
    
    private fun setupOccurrenceLimitControl() {
        val currentLimit = PreferencesManager.getOccurrenceLimit(this)
        
        // Map limit values to seekbar positions
        val limitValues = intArrayOf(500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000)
        val currentPosition = limitValues.indexOf(currentLimit).takeIf { it >= 0 } ?: 0
        
        // Set initial values
        binding.occurrenceLimitSeekBar.progress = currentPosition
        binding.occurrenceLimitValue.text = currentLimit.toString()
        
        binding.occurrenceLimitSeekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val newLimit = limitValues[progress]
                binding.occurrenceLimitValue.text = newLimit.toString()
                PreferencesManager.setOccurrenceLimit(this@SettingsActivity, newLimit)
            }
            
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
    }
    
    private fun setupButtons() {
        binding.licensesButton.setOnClickListener {
            startActivity(Intent(this, LicenseActivity::class.java))
        }
        
        binding.refreshDatabaseButton.setOnClickListener {
            refreshDatabase()
        }
    }
    
    private fun setupBuildInfo() {
        // Set version info
        val versionName = BuildConfig.VERSION_NAME
        val versionCode = BuildConfig.VERSION_CODE
        binding.buildVersion.text = "Version $versionName (build $versionCode)"
        
        // Set build time
        binding.buildTime.text = "Built: ${BuildConfig.BUILD_TIME}"
    }
    
    private fun setupDatabaseInfo() {
        // Check for external database first
        val externalDbUri = PreferencesManager.getExternalDatabaseUri(this)
        if (externalDbUri != null) {
            val uri = android.net.Uri.parse(externalDbUri)
            val fileName = uri.lastPathSegment ?: "Unknown"
            
            // Check if the external database copy exists
            val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
            if (externalDbFile.exists()) {
                val sizeInMB = externalDbFile.length() / (1024 * 1024)
                binding.obbPathValue.text = "Using EXTERNAL database:\n$fileName\n\nCached at:\n${externalDbFile.absolutePath}\n\nSize: ${sizeInMB}MB"
            } else {
                binding.obbPathValue.text = "External database configured but not yet loaded:\n$fileName"
            }
            return
        }
        
        val dbFile = getDatabasePath("perseus_texts.db")
        
        // Show database file info
        if (dbFile.exists()) {
            val sizeInMB = dbFile.length() / (1024 * 1024)
            val path = dbFile.absolutePath
            binding.obbPathValue.text = "Database location:\n$path\n\nSize: ${sizeInMB}MB"
        } else {
            binding.obbPathValue.text = "Database not yet extracted"
        }
    }
    
    private fun refreshDatabase() {
        // Check if using external database
        val externalDbUri = PreferencesManager.getExternalDatabaseUri(this)
        
        val message = if (externalDbUri != null) {
            "This will reload the external database. Continue?"
        } else {
            "This will refresh the bundled database. Continue?"
        }
        
        val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Refresh Database")
            .setMessage(message)
            .setPositiveButton("Yes") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        // Force close any existing database instance
                        PerseusDatabase.destroyInstance()

                        if (externalDbUri != null) {
                            // Delete the cached external database
                            val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
                            if (externalDbFile.exists()) {
                                externalDbFile.delete()
                            }
                        } else {
                            // Delete the bundled database
                            val dbFile = getDatabasePath("perseus_texts.db")
                            if (dbFile.exists()) {
                                dbFile.delete()
                            }
                        }

                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@SettingsActivity,
                                "Database will be refreshed on next launch. Please restart the app.",
                                Toast.LENGTH_LONG).show()

                            // Force app restart
                            val intent = packageManager.getLaunchIntentForPackage(packageName)
                            intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                            startActivity(intent)
                            finishAffinity()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@SettingsActivity,
                                "Error: ${e.message}",
                                Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()

        // Set button text colors for better visibility
        dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
        dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
    }
    
}