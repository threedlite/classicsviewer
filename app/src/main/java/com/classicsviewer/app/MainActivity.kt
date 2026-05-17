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
import com.classicsviewer.app.models.CustomLanguageConfig
import com.classicsviewer.app.data.AssetPackDatabaseHelper
import com.classicsviewer.app.alphabet.AlphabetGameActivity

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
            
            // Database ready, auto-detect languages from database
            autoDetectLanguages()

            checkDatabaseSource()
            setupLanguageSelection()

            // Extract default audio if needed (in background)
            extractDefaultAudioIfNeeded()
        }
    }
    
    private fun autoDetectLanguages() {
        lifecycleScope.launch {
            try {
                // Preferred order for auto-detected languages
                val preferredOrder = listOf(
                    "greek",
                    "latin",
                    "sumerian",
                    "akkadian",
                    "sanskrit",
                    "persian",
                    "hebrew",
                    "arabic",
                    "coptic",
                    "syriac",
                    "italian",
                    "pali",
                    "norse",
                    "old_english"
                )

                // One-time migration: fix any existing ordering issues
                if (!PreferencesManager.hasFixedLanguageOrder(this@MainActivity)) {
                    android.util.Log.d("MainActivity", "Running one-time language order fix")
                    PreferencesManager.reorderLanguagesByPreferredOrder(this@MainActivity, preferredOrder)
                    PreferencesManager.setHasFixedLanguageOrder(this@MainActivity)
                }

                // Get all distinct languages from the database
                val db = PerseusDatabase.getInstance(this@MainActivity)
                val allLanguages = withContext(Dispatchers.IO) {
                    db.authorDao().getAllLanguages()
                }

                android.util.Log.d("MainActivity", "Auto-detecting languages from database: $allLanguages")

                // Get existing custom languages and suppressed languages
                val existingCustomLanguages = PreferencesManager.getCustomLanguages(this@MainActivity)
                val existingLanguageIds = existingCustomLanguages.map { it.id }.toSet()
                val suppressedLanguages = PreferencesManager.getSuppressedLanguages(this@MainActivity)

                android.util.Log.d("MainActivity", "Existing languages: $existingLanguageIds")
                android.util.Log.d("MainActivity", "Suppressed languages: $suppressedLanguages")

                var languagesAdded = false

                // First, add languages in preferred order if they exist in database and not already added
                preferredOrder.forEach { languageId ->
                    if (allLanguages.contains(languageId)
                        && !existingLanguageIds.contains(languageId)
                        && !suppressedLanguages.contains(languageId)) {
                        val displayName = convertLanguageIdToDisplayName(languageId)
                        val color = generateDefaultColor(languageId)

                        val customLanguage = CustomLanguageConfig(languageId, displayName, color)
                        PreferencesManager.addCustomLanguage(this@MainActivity, customLanguage)

                        android.util.Log.d("MainActivity", "Auto-added language: $languageId -> $displayName (color: ${String.format("#%06X", 0xFFFFFF and color)})")
                        languagesAdded = true
                    }
                }

                // Then add any remaining languages not in preferred order
                allLanguages.forEach { languageId ->
                    if (!preferredOrder.contains(languageId)
                        && !existingLanguageIds.contains(languageId)
                        && !suppressedLanguages.contains(languageId)) {
                        val displayName = convertLanguageIdToDisplayName(languageId)
                        val color = generateDefaultColor(languageId)

                        val customLanguage = CustomLanguageConfig(languageId, displayName, color)
                        PreferencesManager.addCustomLanguage(this@MainActivity, customLanguage)

                        android.util.Log.d("MainActivity", "Auto-added language (not in preferred order): $languageId -> $displayName (color: ${String.format("#%06X", 0xFFFFFF and color)})")
                        languagesAdded = true
                    }
                }

                // If languages were added, reorder by preferred order
                if (languagesAdded) {
                    PreferencesManager.reorderLanguagesByPreferredOrder(this@MainActivity, preferredOrder)
                }

                // Refresh the UI
                withContext(Dispatchers.Main) {
                    setupLanguageSelection()
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Error auto-detecting languages", e)
            }
        }
    }

    private fun convertLanguageIdToDisplayName(languageId: String): String {
        // Replace underscores with spaces, then capitalize each word
        return languageId.replace('_', ' ')
            .split(' ')
            .joinToString(" ") { word ->
                word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
            }
    }

    private fun generateDefaultColor(languageId: String): Int {
        // Generate colors with reduced saturation to match Greek/Latin aesthetic
        return when (languageId.lowercase()) {
            "greek" -> 0xFF5A8A5C.toInt()     // Loeb Greek green
            "latin" -> 0xFFB85450.toInt()     // Loeb Latin red
            "sanskrit" -> 0xFFC39B5A.toInt()  // Desaturated saffron
            "hebrew" -> 0xFF6B7BA8.toInt()    // Desaturated indigo
            "arabic" -> 0xFFDCDCDC.toInt()    // Light grey/white
            "persian" -> 0xFF9B7BA8.toInt()   // Desaturated purple
            "sumerian" -> 0xFF5A73AA.toInt()  // Desaturated blue
            "akkadian" -> 0xFFAF9B7D.toInt()  // Desaturated tan
            "coptic" -> 0xFF5A9B8A.toInt()    // Egyptian teal
            "syriac" -> 0xFF9B7B5A.toInt()    // Florentine brown
            "italian" -> 0xFFA8727B.toInt()   // Dusty rose
            "pali" -> 0xFF7EABC9.toInt()      // Light blue
            "norse" -> 0xFF5A5A5A.toInt()     // Dark grey
            "chinese" -> 0xFFFECD21.toInt()  // Chinese gold
            "old_english" -> 0xFFB78700.toInt() // Gold
            else -> 0xFF808080.toInt()        // Grey for unknown languages
        }
    }

    private fun setupLanguageSelection() {
        // Get custom languages from preferences (includes order and customizations)
        val customLanguages = PreferencesManager.getCustomLanguages(this)

        val languages = mutableListOf<Language>()

        // Add all custom languages in their saved order
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
                confirmResetToBundledDatabase()
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
            R.id.action_download_full_database -> {
                showDownloadFullDatabaseConfirmation()
                true
            }
            R.id.action_download_full_audio -> {
                val intent = Intent(this, AudioDownloadActivity::class.java)
                startActivity(intent)
                true
            }
            R.id.action_practice_alphabets -> {
                startActivity(Intent(this, AlphabetGameActivity::class.java))
                true
            }
            R.id.action_rhetoric -> {
                startActivity(Intent(this, com.classicsviewer.app.rhetoric.RhetoricActivity::class.java))
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
    
    private fun showDownloadFullDatabaseConfirmation() {
        val downloadManager = com.classicsviewer.app.data.FullDatabaseDownloadManager(this)

        // Check if already downloaded and extracted
        if (downloadManager.isFullDatabaseActive()) {
            // Already have it - go directly to management screen
            startActivity(Intent(this, FullDatabaseDownloadActivity::class.java))
            return
        }

        // Check if downloaded but not extracted
        if (downloadManager.isFullDatabaseDownloaded()) {
            startActivity(Intent(this, FullDatabaseDownloadActivity::class.java))
            return
        }

        // Not downloaded yet - show confirmation dialog
        val availableGB = downloadManager.getAvailableSpaceGB()
        val hasEnoughSpace = downloadManager.hasEnoughFreeSpace()

        // Determine current database type for display
        val currentDbType = when {
            downloadManager.isExternalDatabaseActive() -> "External (user-imported)"
            downloadManager.isFullDatabaseActive() -> "Full"
            else -> "Sample (bundled)"
        }

        // Warn if external database will be replaced
        val externalWarning = if (downloadManager.isExternalDatabaseActive()) {
            "\n\nNote: Your external database will be replaced."
        } else ""

        val message = if (hasEnoughSpace) {
            """
            The full database contains all Greek and Latin authors from Perseus Digital Library.

            Requirements:
            - 25GB free storage space
            - You have ${availableGB}GB available
            - WiFi recommended for download

            Current database: $currentDbType
            Full database: ~300MB download, ~1.4GB extracted$externalWarning

            Continue with download?
            """.trimIndent()
        } else {
            """
            Insufficient storage space!

            Required: 25GB free space
            Available: ${availableGB}GB

            Please free up storage space before downloading the full database.
            """.trimIndent()
        }

        val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Download Full Database")
            .setMessage(message)
            .setPositiveButton(if (hasEnoughSpace) "Download" else "OK") { _, _ ->
                if (hasEnoughSpace) {
                    startActivity(Intent(this, FullDatabaseDownloadActivity::class.java))
                }
            }
            .setNegativeButton("Cancel", null)
            .show()

        dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
        dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
    }

    private fun selectExternalDatabase() {
        val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
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

        // Set button text colors for better visibility
        dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
        dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
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
    
    private fun confirmResetToBundledDatabase() {
        val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Reset to Bundled Database")
            .setMessage("This will remove any external database and reset to the app's bundled database. The app will restart. Continue?")
            .setPositiveButton("Reset") { _, _ ->
                resetToBundledDatabase()
            }
            .setNegativeButton("Cancel", null)
            .show()

        // Make buttons visible on all devices
        dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
        dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
            resources.getColor(android.R.color.holo_blue_light, null)
        )
    }

    private fun resetToBundledDatabase() {
        // Show progress dialog
        val progressDialog = ProgressDialog(this).apply {
            setMessage("Restoring bundled database...")
            setCancelable(false)
            show()
        }

        lifecycleScope.launch {
            try {
                // Clear preferences
                PreferencesManager.clearExternalDatabaseUri(this@MainActivity)
                PreferencesManager.setUseFullDatabase(this@MainActivity, false)

                // Close database
                PerseusDatabase.destroyInstance()

                // Delete external database copy
                val externalDbFile = File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
                if (externalDbFile.exists()) {
                    externalDbFile.delete()
                }

                // Delete main database and related files
                val mainDbFile = getDatabasePath("perseus_texts.db")
                if (mainDbFile.exists()) {
                    mainDbFile.delete()
                }
                File(mainDbFile.path + "-wal").delete()
                File(mainDbFile.path + "-shm").delete()
                File(mainDbFile.path + "-journal").delete()

                // Re-extract sample database from APK assets
                val assetPackHelper = AssetPackDatabaseHelper(this@MainActivity)
                val success = assetPackHelper.copyDatabaseFromAssetPack { progress ->
                    runOnUiThread {
                        val percent = (progress * 100).toInt()
                        progressDialog.setMessage("Restoring bundled database... $percent%")
                    }
                }

                withContext(Dispatchers.Main) {
                    progressDialog.dismiss()

                    if (success) {
                        Toast.makeText(this@MainActivity, "Database restored! Restarting...", Toast.LENGTH_SHORT).show()

                        // Restart the app
                        val intent = packageManager.getLaunchIntentForPackage(packageName)
                        intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                        startActivity(intent)

                        finishAndRemoveTask()

                        Handler(Looper.getMainLooper()).postDelayed({
                            System.exit(0)
                        }, 100)
                    } else {
                        Toast.makeText(this@MainActivity, "Failed to restore database", Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    progressDialog.dismiss()
                    Toast.makeText(this@MainActivity, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}

data class Language(val name: String, val code: String)