package com.classicsviewer.app

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.MenuItem
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.classicsviewer.app.utils.NavigationHelper
import com.classicsviewer.app.utils.PreferencesManager

abstract class BaseActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        // Enable edge-to-edge display for Android 15+ compatibility
        // This must be called before super.onCreate()
        enableEdgeToEdge()
        
        super.onCreate(savedInstanceState)
        setupActionBar()
        
        // Setup back navigation using the modern OnBackPressedCallback
        setupBackNavigation()
    }
    
    override fun onPostCreate(savedInstanceState: Bundle?) {
        super.onPostCreate(savedInstanceState)
        // Apply window insets after content view is set and all views are initialized
        // This is called after onCreate completes, ensuring views are ready
        applyWindowInsets()
    }
    
    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Dictionary and Lemma activities should use default back behavior
                if (this@BaseActivity is DictionaryActivity || this@BaseActivity is LemmaOccurrencesActivity) {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                } else {
                    handleBackNavigation()
                }
            }
        })
    }
    
    protected open fun applyWindowInsets() {
        // Default implementation - can be overridden by subclasses
        // This ensures content doesn't get hidden behind system bars
        val rootView = window.decorView.findViewById<android.view.View>(android.R.id.content)
        rootView?.let { view ->
            ViewCompat.setOnApplyWindowInsetsListener(view) { v, insets ->
                val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
                v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
                insets
            }
        }
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
                // Use the onBackPressedDispatcher for back navigation
                onBackPressedDispatcher.onBackPressed()
                true
            }
            else -> super.onOptionsItemSelected(item)
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
            val authorIntent = Intent(this, AuthorListActivity::class.java).apply {
                putExtra("language", language)
                putExtra("language_name", this@BaseActivity.intent.getStringExtra("language_name"))
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(authorIntent)
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
            val workIntent = Intent(this, WorkListActivity::class.java).apply {
                putExtra("author_id", authorId)
                putExtra("author_name", this@BaseActivity.intent.getStringExtra("author_name"))
                putExtra("language", this@BaseActivity.intent.getStringExtra("language"))
                putExtra("language_name", this@BaseActivity.intent.getStringExtra("language_name"))
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(workIntent)
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
            val bookIntent = Intent(this, BookListActivity::class.java).apply {
                putExtra("work_id", workId)
                putExtra("work_title", this@BaseActivity.intent.getStringExtra("work_title"))
                putExtra("author_id", this@BaseActivity.intent.getStringExtra("author_id"))
                putExtra("author_name", this@BaseActivity.intent.getStringExtra("author_name"))
                putExtra("language", this@BaseActivity.intent.getStringExtra("language"))
                putExtra("language_name", this@BaseActivity.intent.getStringExtra("language_name"))
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(bookIntent)
        } else {
            navigateToWorkList()
        }
        finish()
    }
}