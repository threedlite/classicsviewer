package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.data.AssetPackDatabaseHelper
import com.classicsviewer.app.databinding.ActivityDatabaseExtractionBinding
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

class DatabaseExtractionActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityDatabaseExtractionBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDatabaseExtractionBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.hide()
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.extractionTitle.setTextColor(0xFF000000.toInt())
            binding.extractionMessage.setTextColor(0xFF000000.toInt())
            binding.progressText.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
            binding.extractionTitle.setTextColor(0xFFFFFFFF.toInt())
            binding.extractionMessage.setTextColor(0xFFFFFFFF.toInt())
            binding.progressText.setTextColor(0xFFFFFFFF.toInt())
        }
        
        startExtraction()
    }
    
    private fun startExtraction() {
        android.util.Log.d("DatabaseExtractionActivity", "startExtraction called")
        
        // Update UI with initial status
        binding.extractionTitle.text = "Preparing Database"
        binding.extractionMessage.text = "Checking database availability..."
        binding.progressText.text = "Please wait..."
        
        lifecycleScope.launch {
            val assetPackHelper = AssetPackDatabaseHelper(this@DatabaseExtractionActivity)
            
            // Database is now in APK assets, always ready
            val isReady = assetPackHelper.isAssetPackReady()
            android.util.Log.d("DatabaseExtractionActivity", "Database ready: $isReady")
            
            if (isReady) {
                // Extract immediately
                extractDatabase()
            } else {
                // Should not happen with APK assets
                binding.extractionMessage.text = "Database not found in app. Please reinstall."
                binding.progressText.text = "Error"
            }
        }
    }
    
    private suspend fun extractDatabase() {
        val assetPackHelper = AssetPackDatabaseHelper(this@DatabaseExtractionActivity)
        
        binding.extractionMessage.text = "Extracting database..."
        binding.progressText.text = "Locating asset pack..."
        
        android.util.Log.e("DatabaseExtractionActivity", "Starting database extraction...")
        val success = try {
            assetPackHelper.copyDatabaseFromAssetPack { progress ->
                runOnUiThread {
                    val percentage = (progress * 100).toInt()
                    binding.extractionProgress.progress = percentage
                    binding.progressText.text = "$percentage%"
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("DatabaseExtractionActivity", "Exception during extraction", e)
            false
        }
        
        android.util.Log.e("DatabaseExtractionActivity", "Extraction result: $success")
        
        if (success) {
            // Start MainActivity after successful extraction
            val intent = Intent(this@DatabaseExtractionActivity, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        } else {
            // Show error
            // Collect diagnostic information
            val diagnosticInfo = StringBuilder()
            
            // Package info
            diagnosticInfo.append("Package: ${packageName}\n")
            diagnosticInfo.append("Version: ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})\n")
            diagnosticInfo.append("Debug: ${BuildConfig.DEBUG}\n\n")
            
            // Check APK assets
            try {
                assets.open("perseus_texts.db.zip").use { stream ->
                    diagnosticInfo.append("Database found in APK assets\n")
                    diagnosticInfo.append("Available size: ${stream.available() / 1024 / 1024} MB\n")
                }
            } catch (e: Exception) {
                diagnosticInfo.append("Database NOT found in APK assets!\n")
                diagnosticInfo.append("Error: ${e.message}\n")
            }
            
            binding.extractionMessage.text = """
                Database extraction failed
                
                === Debug Info ===
                $diagnosticInfo
                
                The database was not found in the app package.
                
                Please report this with a screenshot.
            """.trimIndent()
            binding.progressText.text = "Error"
        }
    }
    
    override fun onBackPressed() {
        // Prevent back during extraction
    }
}