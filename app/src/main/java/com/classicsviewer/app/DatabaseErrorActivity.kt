package com.classicsviewer.app

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.classicsviewer.app.databinding.ActivityDatabaseErrorBinding
import com.classicsviewer.app.utils.PreferencesManager

class DatabaseErrorActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityDatabaseErrorBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        // Enable edge-to-edge display for Android 15+ compatibility
        enableEdgeToEdge()

        super.onCreate(savedInstanceState)
        binding = ActivityDatabaseErrorBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.hide()

        // Apply window insets to avoid content being hidden behind system bars
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.errorTitle.setTextColor(0xFF000000.toInt())
            binding.errorMessage.setTextColor(0xFF000000.toInt())
            binding.okButton.setTextColor(0xFF000000.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
            binding.errorTitle.setTextColor(0xFFFFFFFF.toInt())
            binding.errorMessage.setTextColor(0xFFFFFFFF.toInt())
            binding.okButton.setTextColor(0xFFFFFFFF.toInt())
        }
        
        // Get error details from intent
        val isExternalDb = intent.getBooleanExtra("is_external_db", false)
        val errorDetails = intent.getStringExtra("error_details")
        
        // Log the error details for debugging
        android.util.Log.e("DatabaseErrorActivity", "Error details: $errorDetails")
        
        // Set appropriate title and message
        if (isExternalDb) {
            binding.errorTitle.text = "External Database Incompatible"
            binding.errorMessage.text = """
                The selected database file has an incompatible structure.
                
                Please select a different database file or use the bundled database.
                
                You may need to clear app data in Settings > Apps > Classics Viewer > Storage.
            """.trimIndent()
        } else {
            binding.errorTitle.text = "Database Update Required"
            binding.errorMessage.text = "Please uninstall and reinstall the app."
        }
        
        // OK button exits the app
        binding.okButton.setOnClickListener {
            finishAffinity()
            System.exit(0)
        }
    }
    
    override fun onBackPressed() {
        // Prevent going back - force user to click OK
    }
}