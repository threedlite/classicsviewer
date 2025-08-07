package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.view.MenuItem
import androidx.appcompat.app.AppCompatActivity
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager

abstract class BaseActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupActionBar()
    }
    
    override fun onResume() {
        super.onResume()
        // Navigation state persistence has been removed - app always starts fresh
    }
    
    private fun setupActionBar() {
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
        }
    }
    
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                handleBackNavigation()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    override fun onBackPressed() {
        handleBackNavigation()
    }
    
    private fun handleBackNavigation() {
        // Determine where to navigate based on current activity
        when (this) {
            is AuthorListActivity -> {
                // Go back to main screen
                navigateToMain()
            }
            is WorkListActivity -> {
                // Just finish to go back to author list
                finish()
            }
            is BookListActivity -> {
                // Just finish to go back to work list
                finish()
            }
            is TextViewerActivity, is TextViewerPagerActivity -> {
                // Just finish to go back
                finish()
            }
            is DictionaryActivity, is LemmaOccurrencesActivity -> {
                // For dictionary and occurrences, just finish to go back
                finish()
            }
            is SettingsActivity -> {
                // For settings, just finish to go back
                finish()
            }
            else -> {
                // Unknown activity, go to main
                navigateToMain()
            }
        }
    }
    
    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
        }
        startActivity(intent)
        finish()
    }
}