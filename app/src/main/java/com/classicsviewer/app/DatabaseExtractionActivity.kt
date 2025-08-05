package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.data.ObbDatabaseHelper
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
        lifecycleScope.launch {
            val obbHelper = ObbDatabaseHelper(this@DatabaseExtractionActivity)
            
            val success = obbHelper.extractDatabaseFromObb { progress ->
                runOnUiThread {
                    val percentage = (progress * 100).toInt()
                    binding.extractionProgress.progress = percentage
                    binding.progressText.text = "$percentage%"
                }
            }
            
            if (success) {
                // Return to previous activity
                finish()
            } else {
                // Show error
                binding.extractionMessage.text = "Failed to extract database. Please reinstall the app."
                binding.progressText.text = "Error"
            }
        }
    }
    
    override fun onBackPressed() {
        // Prevent back during extraction
    }
}