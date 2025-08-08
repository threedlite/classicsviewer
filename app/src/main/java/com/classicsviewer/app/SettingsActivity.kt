package com.classicsviewer.app

import android.content.Intent
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
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.title = "Settings"
        
        setupFontSizeControl()
        setupColorInversionControl()
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
        
        AlertDialog.Builder(this)
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
    }
    
}