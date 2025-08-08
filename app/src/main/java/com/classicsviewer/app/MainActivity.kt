package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.databinding.ActivityMainBinding
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager
import com.classicsviewer.app.utils.DatabaseValidator
import com.classicsviewer.app.database.PerseusDatabase
import java.io.File
import android.graphics.Typeface
import android.text.SpannableString
import android.text.Spanned
import android.text.style.StyleSpan
import android.text.style.RelativeSizeSpan
import androidx.activity.result.contract.ActivityResultContracts
import android.net.Uri
import androidx.appcompat.app.AlertDialog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import android.app.ProgressDialog
import android.os.Handler
import android.os.Looper

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    
    private val databaseFilePicker = registerForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        uri?.let { handleDatabaseSelection(it) }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Create custom title with styled alpha
        val title = SpannableString("α  Classics Viewer")
        // Make alpha larger and bold
        title.setSpan(RelativeSizeSpan(1.5f), 0, 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        title.setSpan(StyleSpan(Typeface.BOLD), 0, 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        supportActionBar?.title = title
        
        
        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
        }
        
        // Check if database extraction is needed
        if (needsDatabaseExtraction()) {
            val intent = Intent(this, DatabaseExtractionActivity::class.java)
            startActivity(intent)
            finish() // Close MainActivity so user can't go back
        } else {
            // Database ready, show language selection
            checkDatabaseSource()
            setupLanguageSelection()
        }
    }
    
    private fun setupLanguageSelection() {
        val languages = listOf(
            Language("Greek", "greek"),
            Language("Latin", "latin")
        )
        
        val inverted = PreferencesManager.getInvertColors(this)
        val adapter = LanguageAdapter(languages, inverted) { language ->
            val intent = Intent(this, AuthorListActivity::class.java)
            intent.putExtra("language", language.code)
            intent.putExtra("language_name", language.name)
            startActivity(intent)
        }
        
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter
    }
    
    
    private fun checkDatabaseSource() {
        val externalDbUri = PreferencesManager.getExternalDatabaseUri(this)
        
        if (externalDbUri != null) {
            val fileName = Uri.parse(externalDbUri).lastPathSegment ?: "external database"
            Toast.makeText(this, "Using external database: $fileName", Toast.LENGTH_LONG).show()
            return
        }
        
        val dbFile = getDatabasePath("perseus_texts.db")
        
        if (dbFile.exists()) {
            Toast.makeText(this, "Using bundled database", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Database will be extracted on first use", Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_bookmarks -> {
                startActivity(Intent(this, com.classicsviewer.app.ui.BookmarksActivity::class.java))
                true
            }
            R.id.action_settings -> {
                startActivity(Intent(this, SettingsActivity::class.java))
                true
            }
            R.id.action_select_database -> {
                selectExternalDatabase()
                true
            }
            R.id.action_reset_database -> {
                resetToBundledDatabase()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun needsDatabaseExtraction(): Boolean {
        // If using external database, no extraction needed
        if (PreferencesManager.getExternalDatabaseUri(this) != null) {
            return false
        }
        
        val dbFile = getDatabasePath("perseus_texts.db")
        // Need extraction if database doesn't exist
        return !dbFile.exists()
    }
    
    override fun onResume() {
        super.onResume()
        
        // Reapply color inversion setting in case it changed
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            // Black on white
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
        } else {
            // White on black (default)
            binding.root.setBackgroundColor(0xFF000000.toInt())
        }
        
        // Refresh the adapter with current color setting
        setupLanguageSelection()
    }
    
    override fun onBackPressed() {
        // Never exit the app - MainActivity is the root
        // Optionally, you could show a toast or do nothing
        // For now, we'll just do nothing to prevent accidental exits
    }
    
    private fun selectExternalDatabase() {
        AlertDialog.Builder(this)
            .setTitle("Select External Database")
            .setMessage("Select a SQLite database file (*.db) from your device. The database schema will be validated before use.")
            .setPositiveButton("Select") { _, _ ->
                // Filter for database files
                databaseFilePicker.launch(arrayOf(
                    "application/x-sqlite3",
                    "application/vnd.sqlite3", 
                    "application/octet-stream",
                    "*/*"
                ))
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    private fun handleDatabaseSelection(uri: Uri) {
        // First check if it's a .db file
        val fileName = getFileName(uri)
        if (!fileName.endsWith(".db", ignoreCase = true)) {
            Toast.makeText(this, "Please select a SQLite database file (*.db)", Toast.LENGTH_LONG).show()
            return
        }
        
        // Show progress dialog during validation and copy
        val progressDialog = ProgressDialog(this).apply {
            setMessage("Validating database schema...")
            setCancelable(false)
            show()
        }
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Take persistent permissions first
                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                // Validate the database
                val validationResult = DatabaseValidator.validateDatabase(this@MainActivity, uri)
                
                if (validationResult.isValid) {
                    withContext(Dispatchers.Main) {
                        progressDialog.setMessage("Copying database... This may take a minute...")
                    }
                    
                    // Copy the database to app's database directory
                    val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
                    
                    // Delete existing file to ensure fresh copy
                    if (externalDbFile.exists()) {
                        externalDbFile.delete()
                    }
                    
                    // Copy the database
                    contentResolver.openInputStream(uri)?.use { input ->
                        externalDbFile.outputStream().use { output ->
                            input.copyTo(output)
                        }
                    }
                    
                    val fileSizeMB = externalDbFile.length() / (1024 * 1024)
                    android.util.Log.d("MainActivity", "External database copied, size: ${fileSizeMB}MB")
                    
                    // Verify the copy
                    if (externalDbFile.length() < 1000000) {
                        throw Exception("Database copy failed - file too small: ${externalDbFile.length()} bytes")
                    }
                    
                    // Save the URI to preferences
                    PreferencesManager.setExternalDatabaseUri(this@MainActivity, uri.toString())
                    
                    withContext(Dispatchers.Main) {
                        progressDialog.dismiss()
                        
                        // Show success toast
                        Toast.makeText(this@MainActivity, "Database copied! Restarting...", Toast.LENGTH_SHORT).show()
                        
                        // Close all resources
                        PerseusDatabase.destroyInstance()
                        progressDialog.dismiss()
                        
                        // Restart the app
                        val intent = packageManager.getLaunchIntentForPackage(packageName)
                        intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                        startActivity(intent)
                        
                        // Exclude from recents and finish
                        if (android.os.Build.VERSION.SDK_INT >= 21) {
                            finishAndRemoveTask()
                        } else {
                            finish()
                        }
                        
                        // Delay to ensure cleanup, then exit
                        android.os.Handler(Looper.getMainLooper()).postDelayed({
                            System.exit(0)
                        }, 100)
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        progressDialog.dismiss()
                        
                        // Show validation error
                        AlertDialog.Builder(this@MainActivity)
                            .setTitle("Database Validation Failed")
                            .setMessage(validationResult.errorMessage ?: "Unknown validation error")
                            .setPositiveButton("OK", null)
                            .show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    progressDialog.dismiss()
                    Toast.makeText(this@MainActivity, "Failed to validate database: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    
    private fun getFileName(uri: Uri): String {
        var result = ""
        val cursor = contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            if (it.moveToFirst()) {
                val displayNameIndex = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                if (displayNameIndex != -1) {
                    result = it.getString(displayNameIndex)
                }
            }
        }
        return result.ifEmpty { uri.lastPathSegment ?: "" }
    }
    
    private fun resetToBundledDatabase() {
        // Clear the external database preference
        PreferencesManager.clearExternalDatabaseUri(this)
        
        // Close all resources
        PerseusDatabase.destroyInstance()
        
        // Delete the external database copy
        val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
        if (externalDbFile.exists()) {
            externalDbFile.delete()
        }
        
        // Show a quick toast and restart
        Toast.makeText(this, "Resetting to bundled database...", Toast.LENGTH_SHORT).show()
        
        // Restart the app
        val intent = packageManager.getLaunchIntentForPackage(packageName)
        intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        startActivity(intent)
        
        // Exclude from recents and finish
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            finishAndRemoveTask()
        } else {
            finish()
        }
        
        // Delay to ensure cleanup, then exit
        android.os.Handler(Looper.getMainLooper()).postDelayed({
            System.exit(0)
        }, 100)
    }
}

data class Language(val name: String, val code: String)