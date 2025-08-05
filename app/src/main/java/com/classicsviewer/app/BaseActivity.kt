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
                // Go back to author list
                val language = intent.getStringExtra("language") ?: ""
                val languageName = intent.getStringExtra("language_name") ?: ""
                val intent = Intent(this, AuthorListActivity::class.java).apply {
                    putExtra("language", language)
                    putExtra("language_name", languageName)
                    // Reconstruct navigation path
                    putExtra(NavigationHelper.EXTRA_NAVIGATION_PATH, "Home")
                }
                startActivity(intent)
                finish()
            }
            is BookListActivity -> {
                // Go back to work list
                val language = intent.getStringExtra("language") ?: ""
                val languageName = intent.getStringExtra("language_name") ?: ""
                val authorId = intent.getStringExtra("author_id") ?: ""
                val authorName = intent.getStringExtra("author_name") ?: ""
                val intent = Intent(this, WorkListActivity::class.java).apply {
                    putExtra("language", language)
                    putExtra("language_name", languageName)
                    putExtra("author_id", authorId)
                    putExtra("author_name", authorName)
                    // Reconstruct navigation path
                    putExtra(NavigationHelper.EXTRA_NAVIGATION_PATH, "Home > $languageName")
                }
                startActivity(intent)
                finish()
            }
            is TextViewerActivity, is TextViewerPagerActivity -> {
                // Check if we came from occurrences
                if (intent.getBooleanExtra("from_occurrences", false)) {
                    // Just finish to go back to occurrences
                    finish()
                } else {
                    // Go back to book list
                    val language = intent.getStringExtra("language") ?: ""
                    val languageName = intent.getStringExtra("language_name") ?: ""
                    val authorId = intent.getStringExtra("author_id") ?: ""
                    val authorName = intent.getStringExtra("author_name") ?: ""
                    val workId = intent.getStringExtra("work_id") ?: ""
                    val workTitle = intent.getStringExtra("work_title") ?: ""
                    val intent = Intent(this, BookListActivity::class.java).apply {
                        putExtra("language", language)
                        putExtra("language_name", languageName)
                        putExtra("author_id", authorId)
                        putExtra("author_name", authorName)
                        putExtra("work_id", workId)
                        putExtra("work_title", workTitle)
                        // Reconstruct navigation path
                        putExtra(NavigationHelper.EXTRA_NAVIGATION_PATH, "Home > $languageName > $authorName")
                    }
                    startActivity(intent)
                    finish()
                }
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