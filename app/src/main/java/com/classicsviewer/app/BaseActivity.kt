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
                // Dictionary and Lemma activities should use default back behavior
                if (this is DictionaryActivity || this is LemmaOccurrencesActivity) {
                    onBackPressed()
                } else {
                    handleBackNavigation()
                }
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    override fun onBackPressed() {
        // Dictionary and Lemma activities should use default back behavior
        if (this is DictionaryActivity || this is LemmaOccurrencesActivity) {
            super.onBackPressed()
        } else {
            handleBackNavigation()
        }
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
                navigateToAuthorList()
            }
            is BookListActivity -> {
                // Go back to work list
                navigateToWorkList()
            }
            is TextViewerActivity, is TextViewerPagerActivity -> {
                // Go back to book list
                navigateToBookList()
            }
            is com.classicsviewer.app.ui.BookmarksActivity -> {
                // Bookmarks can be accessed from menu or from a specific work
                // Check if we have work context to determine where to go
                val workId = intent.getStringExtra("work_id")
                if (workId != null) {
                    // Came from a specific work context, go back to book list
                    navigateToBookList()
                } else {
                    // Came from menu, go to author list
                    navigateToAuthorList()
                }
            }
            is SettingsActivity -> {
                // For settings, go back to author list
                navigateToAuthorList()
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
    
    private fun navigateToAuthorList() {
        // Try to get language from current intent, otherwise go to main to select language
        val language = intent.getStringExtra("language")
        if (language != null) {
            val intent = Intent(this, AuthorListActivity::class.java).apply {
                putExtra("language", language)
                putExtra("language_name", intent.getStringExtra("language_name"))
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(intent)
            finish()
        } else {
            // No language context, go to main screen
            navigateToMain()
        }
    }
    
    private fun navigateToWorkList() {
        // We need author information to go back to work list
        // If we don't have it, go to author list instead
        val authorId = intent.getStringExtra("author_id")
        if (authorId != null) {
            val intent = Intent(this, WorkListActivity::class.java).apply {
                putExtra("author_id", authorId)
                putExtra("author_name", intent.getStringExtra("author_name"))
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(intent)
        } else {
            navigateToAuthorList()
        }
        finish()
    }
    
    private fun navigateToBookList() {
        // We need work information to go back to book list
        // If we don't have it, go to work list (or author list if no author info)
        val workId = intent.getStringExtra("work_id")
        if (workId != null) {
            val intent = Intent(this, BookListActivity::class.java).apply {
                putExtra("work_id", workId)
                putExtra("work_title", intent.getStringExtra("work_title"))
                putExtra("author_id", intent.getStringExtra("author_id"))
                putExtra("author_name", intent.getStringExtra("author_name"))
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(intent)
        } else {
            navigateToWorkList()
        }
        finish()
    }
}