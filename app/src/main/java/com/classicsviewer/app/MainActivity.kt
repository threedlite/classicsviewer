package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.classicsviewer.app.data.AssetPackDatabaseHelper
import com.classicsviewer.app.databinding.ActivityMainBinding
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.title = "Classics Viewer"
        
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
        val assetPackHelper = AssetPackDatabaseHelper(this)
        val dbFile = getDatabasePath("perseus_texts.db")
        
        when {
            assetPackHelper.isAssetPackReady() && !dbFile.exists() -> {
                Toast.makeText(this, "Database will be loaded from asset pack", Toast.LENGTH_LONG).show()
            }
            assetPackHelper.isAssetPackReady() && dbFile.exists() -> {
                Toast.makeText(this, "Using database from asset pack (already extracted)", Toast.LENGTH_SHORT).show()
            }
            !assetPackHelper.isAssetPackReady() && dbFile.exists() -> {
                Toast.makeText(this, "Using database from internal storage", Toast.LENGTH_SHORT).show()
            }
            else -> {
                Toast.makeText(this, "Asset pack not found - please reinstall", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                startActivity(Intent(this, SettingsActivity::class.java))
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun needsDatabaseExtraction(): Boolean {
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
}

data class Language(val name: String, val code: String)