package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.widget.SeekBar
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import com.classicsviewer.app.data.ObbDatabaseHelper
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.databinding.ActivitySettingsBinding
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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
        setupObbInfo()
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
            refreshDatabaseFromObb()
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
    
    private fun setupObbInfo() {
        val obbHelper = ObbDatabaseHelper(this)
        val obbPath = obbHelper.getObbDatabasePath()
        
        if (obbPath != null && obbPath.exists()) {
            binding.obbPathValue.text = obbPath.absolutePath
            // Also show file size
            val sizeInMB = obbPath.length() / (1024 * 1024)
            binding.obbPathValue.text = "${obbPath.absolutePath}\n(${sizeInMB}MB)"
        } else {
            val expectedPath = "/storage/emulated/0/Android/obb/${packageName}/main.1.${packageName}.obb"
            binding.obbPathValue.text = "Not found\nExpected at: $expectedPath"
        }
    }
    
    private fun refreshDatabaseFromObb() {
        val obbHelper = ObbDatabaseHelper(this)
        
        // Debug logging
        val obbPath = obbHelper.getObbDatabasePath()
        android.util.Log.d("SettingsActivity", "Looking for OBB at: ${obbPath?.absolutePath ?: "null"}")
        android.util.Log.d("SettingsActivity", "OBB exists: ${obbPath?.exists() ?: false}")
        android.util.Log.d("SettingsActivity", "OBB readable: ${obbPath?.canRead() ?: false}")
        
        if (!obbHelper.isObbAvailable()) {
            val expectedPath = "/sdcard/Android/obb/${packageName}/main.1.${packageName}.obb"
            Toast.makeText(this, "No OBB file found at:\n$expectedPath", Toast.LENGTH_LONG).show()
            return
        }
        
        AlertDialog.Builder(this)
            .setTitle("Refresh Database")
            .setMessage("This will replace the current database with the one from the OBB file. Continue?")
            .setPositiveButton("Yes") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        // Delete existing database
                        val dbFile = getDatabasePath("perseus_texts.db")
                        if (dbFile.exists()) {
                            dbFile.delete()
                        }
                        
                        // Force close any existing database instance
                        PerseusDatabase.destroyInstance()
                        
                        // Extract from OBB
                        val success = obbHelper.extractDatabaseFromObb()
                        
                        withContext(Dispatchers.Main) {
                            if (success) {
                                Toast.makeText(this@SettingsActivity, 
                                    "Database refreshed successfully. Please restart the app.", 
                                    Toast.LENGTH_LONG).show()
                                
                                // Force app restart
                                finishAffinity()
                            } else {
                                Toast.makeText(this@SettingsActivity, 
                                    "Failed to extract database from OBB", 
                                    Toast.LENGTH_SHORT).show()
                            }
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