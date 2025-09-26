package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
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
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.audio.DefaultAudioExtractor
import android.app.ProgressDialog
import android.os.Handler
import android.os.Looper
import java.util.zip.ZipInputStream
import java.io.BufferedInputStream

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    
    private val databaseFilePicker = registerForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        uri?.let { handleDatabaseSelection(it) }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        // Enable edge-to-edge display for Android 15+ compatibility
        enableEdgeToEdge()
        
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Apply window insets to avoid content being hidden behind system bars
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
        
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
            // Validate external database if one is being used
            if (!validateExternalDatabase()) {
                // External database failed validation, reset to bundled
                PreferencesManager.clearExternalDatabaseUri(this)
                Toast.makeText(this, "External database schema mismatch. Reverting to bundled database.", Toast.LENGTH_LONG).show()
                // Re-check if extraction is needed after clearing external DB
                if (needsDatabaseExtraction()) {
                    val intent = Intent(this, DatabaseExtractionActivity::class.java)
                    startActivity(intent)
                    finish()
                    return
                }
            }
            
            // Try to open the database to check for schema issues
            try {
                val db = PerseusDatabase.getInstance(this)
                android.util.Log.d("MainActivity", "Database opened successfully")
            } catch (e: com.classicsviewer.app.database.DatabaseFatalException) {
                // Database has fatal error, the error activity was already launched
                android.util.Log.e("MainActivity", "Database fatal error caught, finishing activity")
                finish()
                return
            }
            
            // Database ready, show language selection
            checkDatabaseSource()
            setupLanguageSelection()
            
            // Extract default audio if needed (in background)
            extractDefaultAudioIfNeeded()
        }
    }
    
    private fun setupLanguageSelection() {
        val languages = mutableListOf(
            Language("Greek", "greek"),
            Language("Latin", "latin")
        )

        // Add custom languages from preferences
        val customLanguages = PreferencesManager.getCustomLanguages(this)
        customLanguages.forEach { customLang ->
            languages.add(Language(customLang.displayName, customLang.id))
        }

        val inverted = PreferencesManager.getInvertColors(this)
        val adapter = LanguageAdapter(languages, inverted, customLanguages) { language ->
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
    
    private fun extractDefaultAudioIfNeeded() {
        // Extract default audio in background
        lifecycleScope.launch {
            try {
                val audioExtractor = DefaultAudioExtractor(this@MainActivity)
                
                // Check if extraction is needed
                if (audioExtractor.needsExtraction()) {
                    android.util.Log.d("MainActivity", "Extracting default audio package...")
                    
                    // Only extract if we have the audio in assets
                    if (audioExtractor.hasDefaultAudioInAssets()) {
                        val success = audioExtractor.extractDefaultAudio()
                        if (success) {
                            android.util.Log.d("MainActivity", "Default audio extracted successfully")
                            // Don't show toast to avoid interrupting user
                        } else {
                            android.util.Log.e("MainActivity", "Failed to extract default audio")
                        }
                    } else {
                        android.util.Log.d("MainActivity", "Default audio not found in assets, skipping extraction")
                    }
                } else {
                    android.util.Log.d("MainActivity", "Default audio already extracted")
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Error checking/extracting default audio", e)
                // Don't crash the app if audio extraction fails
            }
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
            R.id.action_manage_audio -> {
                startActivity(Intent(this, com.classicsviewer.app.audio.AudioManagementActivity::class.java))
                true
            }
            R.id.action_manage_dictionary -> {
                startActivity(Intent(this, com.classicsviewer.app.ui.UserDictionaryImportActivity::class.java))
                true
            }
            R.id.action_manage_languages -> {
                startActivity(Intent(this, ManageLanguagesActivity::class.java))
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
    
    private fun validateExternalDatabase(): Boolean {
        val externalDbUri = PreferencesManager.getExternalDatabaseUri(this) ?: return true // No external DB, validation passes
        
        // First ensure bundled database is extracted for comparison
        val bundledDbFile = getDatabasePath("perseus_texts.db")
        if (!bundledDbFile.exists()) {
            // Need to extract bundled DB first to compare schemas
            return true // Let normal flow handle extraction
        }
        
        // Check if external database has already been extracted and copied
        val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
        if (!externalDbFile.exists()) {
            // External database not yet extracted/copied, validation will happen during selection
            return true
        }
        
        try {
            // Validate the extracted external database file against bundled schema
            val validationResult = DatabaseValidator.validateDatabase(this, externalDbFile)
            
            if (!validationResult.isValid) {
                android.util.Log.e("MainActivity", "External database validation failed: ${validationResult.errorMessage}")
                return false
            }
            
            return true
        } catch (e: Exception) {
            android.util.Log.e("MainActivity", "Error validating external database", e)
            return false
        }
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
        com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Select External Database")
            .setMessage("Select a SQLite database file (*.db) or compressed database (*.zip) from your device. The database schema will be validated before use.")
            .setPositiveButton("Select") { _, _ ->
                // Filter for database and zip files
                databaseFilePicker.launch(arrayOf(
                    "application/x-sqlite3",
                    "application/vnd.sqlite3", 
                    "application/zip",
                    "application/x-zip-compressed",
                    "application/octet-stream",
                    "*/*"
                ))
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    private fun handleDatabaseSelection(uri: Uri) {
        // First check if it's a .db or .zip file
        val fileName = getFileName(uri)
        val isZipFile = fileName.endsWith(".zip", ignoreCase = true)
        val isDbFile = fileName.endsWith(".db", ignoreCase = true)
        
        if (!isZipFile && !isDbFile) {
            Toast.makeText(this, "Please select a SQLite database file (*.db) or compressed database (*.zip)", Toast.LENGTH_LONG).show()
            return
        }
        
        // Show progress dialog during validation and copy
        val progressDialog = ProgressDialog(this).apply {
            setMessage(if (isZipFile) "Extracting compressed database..." else "Validating database schema...")
            setCancelable(false)
            show()
        }
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Take persistent permissions first
                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                // Copy the database to app's database directory
                val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
                
                // Delete existing file to ensure fresh copy
                if (externalDbFile.exists()) {
                    externalDbFile.delete()
                }
                
                if (isZipFile) {
                    // Extract ZIP file
                    withContext(Dispatchers.Main) {
                        progressDialog.setMessage("Extracting database from ZIP... This may take a minute...")
                    }
                    
                    contentResolver.openInputStream(uri)?.use { input ->
                        ZipInputStream(BufferedInputStream(input)).use { zipStream ->
                            var extractedDb = false
                            
                            while (true) {
                                val entry = zipStream.nextEntry ?: break
                                
                                // Look for .db files in the ZIP
                                if (entry.name.endsWith(".db", ignoreCase = true) && !entry.isDirectory) {
                                    android.util.Log.d("MainActivity", "Extracting: ${entry.name}")
                                    android.util.Log.d("MainActivity", "Entry size: ${entry.size} bytes")

                                    var totalBytes = 0L
                                    externalDbFile.outputStream().buffered(8192).use { output ->
                                        val buffer = ByteArray(8192)
                                        var bytes = zipStream.read(buffer)
                                        while (bytes >= 0) {
                                            output.write(buffer, 0, bytes)
                                            totalBytes += bytes
                                            bytes = zipStream.read(buffer)
                                        }
                                    }
                                    android.util.Log.d("MainActivity", "Extracted ${totalBytes} bytes")
                                    extractedDb = true
                                    break // Only extract the first .db file found
                                }
                                
                                zipStream.closeEntry()
                            }
                            
                            if (!extractedDb) {
                                throw Exception("No database file found in ZIP archive")
                            }
                        }
                    }
                } else {
                    // Copy uncompressed database
                    withContext(Dispatchers.Main) {
                        progressDialog.setMessage("Copying database... This may take a minute...")
                    }
                    
                    contentResolver.openInputStream(uri)?.use { input ->
                        externalDbFile.outputStream().use { output ->
                            input.copyTo(output)
                        }
                    }
                }
                
                // Now validate the extracted/copied database
                withContext(Dispatchers.Main) {
                    progressDialog.setMessage("Validating database schema...")
                }
                
                val validationResult = DatabaseValidator.validateDatabase(this@MainActivity, externalDbFile)
                
                if (validationResult.isValid) {
                    
                    val fileSizeMB = externalDbFile.length() / (1024 * 1024)
                    android.util.Log.d("MainActivity", "External database copied, size: ${fileSizeMB}MB")
                    
                    // Verify the copy - minimum 1KB (sanity check for corrupted copies)
                    if (externalDbFile.length() < 1000) {
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
                        com.google.android.material.dialog.MaterialAlertDialogBuilder(this@MainActivity)
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