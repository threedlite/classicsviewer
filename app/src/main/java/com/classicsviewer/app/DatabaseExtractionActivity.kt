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
import com.google.android.play.core.assetpacks.model.AssetPackStatus
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
        lifecycleScope.launch {
            val assetPackHelper = AssetPackDatabaseHelper(this@DatabaseExtractionActivity)
            
            // Check if pack is ready (fast-follow packs may need to be downloaded in local testing)
            val isReady = assetPackHelper.isAssetPackReady()
            android.util.Log.d("DatabaseExtractionActivity", "Asset pack ready: $isReady")
            
            if (!isReady) {
                binding.extractionMessage.text = "Downloading database..."
                
                // Request pack download for fast-follow in local testing
                val status = assetPackHelper.requestPackIfNeeded()
                android.util.Log.d("DatabaseExtractionActivity", "Pack request status: $status")
                
                // Register listener for download progress
                assetPackHelper.registerListener { packState ->
                    runOnUiThread {
                        when (packState.status()) {
                            com.google.android.play.core.assetpacks.model.AssetPackStatus.DOWNLOADING -> {
                                val downloadProgress = if (packState.totalBytesToDownload() > 0) {
                                    (packState.bytesDownloaded() * 100 / packState.totalBytesToDownload()).toInt()
                                } else {
                                    0
                                }
                                binding.extractionProgress.progress = downloadProgress
                                binding.progressText.text = "$downloadProgress%"
                                binding.extractionMessage.text = "Downloading database..."
                            }
                            com.google.android.play.core.assetpacks.model.AssetPackStatus.COMPLETED -> {
                                // Pack downloaded, now extract
                                lifecycleScope.launch {
                                    extractDatabase()
                                }
                            }
                            com.google.android.play.core.assetpacks.model.AssetPackStatus.FAILED -> {
                                binding.extractionMessage.text = "Failed to download database. Please check your connection."
                                binding.progressText.text = "Error"
                            }
                        }
                    }
                }
                
                // If already completed, extract immediately
                if (status == AssetPackStatus.COMPLETED) {
                    extractDatabase()
                }
            } else {
                // Pack already available, extract immediately
                extractDatabase()
            }
        }
    }
    
    private suspend fun extractDatabase() {
        val assetPackHelper = AssetPackDatabaseHelper(this@DatabaseExtractionActivity)
        
        binding.extractionMessage.text = "Extracting database..."
        
        val success = assetPackHelper.copyDatabaseFromAssetPack { progress ->
            runOnUiThread {
                val percentage = (progress * 100).toInt()
                binding.extractionProgress.progress = percentage
                binding.progressText.text = "$percentage%"
            }
        }
        
        if (success) {
            // Start MainActivity after successful extraction
            val intent = Intent(this@DatabaseExtractionActivity, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        } else {
            // Show error
            binding.extractionMessage.text = "Failed to extract database from asset pack. Please reinstall the app."
            binding.progressText.text = "Error"
        }
    }
    
    override fun onBackPressed() {
        // Prevent back during extraction
    }
}